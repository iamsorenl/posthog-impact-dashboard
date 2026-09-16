#!/usr/bin/env python3
"""Score PostHog engineers on four impact pillars. Reads data/raw/*, writes data.json."""
import json, re, glob, math, collections, statistics, datetime as dt, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
WINDOW = ("2026-06-18", "2026-09-16")

BOT_RE = re.compile(
    r"\[bot\]$|dependabot|renovate|github-actions|scheduled-actions|^posthog$|-bot$|^bot-"
    r"|greptile|trunk-io|coderabbit|sourcery|codecov|sentry-io|snyk|imgbot|netlify|vercel"
    r"|allcontributors|stale|mergify|semantic-release"
    # AI review/approval accounts verified against this repo's own review volume
    r"|^stamphog$|veria-ai|parameterai|chatgpt-codex|codex-connector|copilot|graphite-app"
    r"|mendral|talyn|force-merge|posthog-local-dev|-ai$|-app$|-apps$", re.I)
PR_IN_SUBJECT = re.compile(r"\(#(\d+)\)")

WEIGHTS = {"leverage": 0.35, "blast": 0.25, "shipping": 0.25, "workmix": 0.15}
MIN_PRS, MIN_REVIEWS = 3, 5          # eligibility floor
ATT_CAP = 15.0                       # per-PR attention ceiling: contentiousness != consequence
CORE_FILE_MIN_AUTHORS = 5            # a file >=5 distinct engineers touched is a shared surface
AI_APPROVAL_LABEL = "stamphog"   # GitHub label desc: "Request AI approval (no full review)"


def is_bot(login, typename=None):
    return not login or typename == "Bot" or bool(BOT_RE.search(login))


def pct(values):
    """map {key: raw} -> {key: percentile 0-100}; ties share the midpoint rank."""
    if not values:
        return {}
    ordered = sorted(values.items(), key=lambda kv: kv[1])
    n = len(ordered)
    out, i = {}, 0
    while i < n:
        j = i
        while j + 1 < n and ordered[j + 1][1] == ordered[i][1]:
            j += 1
        rank = (i + j) / 2.0
        p = 100.0 * rank / (n - 1) if n > 1 else 100.0
        for k in range(i, j + 1):
            out[ordered[k][0]] = round(p, 1)
        i = j + 1
    return out


PREFIX_RE = re.compile(r"^\s*(feat|feature|fix|perf|chore|docs?|refactor|test|ci|build|revert)\b", re.I)
PREFIX_MAP = {"feature": "feat", "doc": "docs", "chore": "infra", "ci": "infra", "build": "infra"}
KEYWORDS = [
    ("revert",   r"\brevert\b"),
    ("perf",     r"\bperf\b|performance|optimi|speed ?up|faster|latency"),
    ("fix",      r"\bfix(es|ed)?\b|\bbug\b|hotfix|regression|\bbroken\b"),
    ("infra",    r"\binfra\b|\bci\b|\bdeploy\b|migration|docker|terraform|\bdeps\b"),
    ("docs",     r"\bdocs?\b|documentation|readme"),
    ("refactor", r"refactor|clean ?up|\btidy\b|\brename\b|dead code"),
    ("test",     r"\btests?\b|\bspec\b|\be2e\b|flaky"),
    ("feat",     r"\bfeat\b|\badds?\b|implement|introduce|\bsupport\b"),
]
KEYWORDS = [(k, re.compile(v, re.I)) for k, v in KEYWORDS]


def classify(title, labels):
    """Conventional-commit prefix wins; keyword match (word-bounded) is the fallback."""
    t = title or ""
    m = PREFIX_RE.match(t)
    if m:
        k = m.group(1).lower()
        return PREFIX_MAP.get(k, k)
    blob = t + " " + " ".join(labels)
    for key, rx in KEYWORDS:
        if rx.search(blob):
            return key
    return "other"


# ---------- load PRs ----------
prs = []
for path in sorted(glob.glob(os.path.join(RAW, "prs_*.jsonl"))):
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                prs.append(json.loads(line))
seen, uniq = set(), []
for p in prs:
    if p["number"] not in seen:
        seen.add(p["number"])
        uniq.append(p)
prs = uniq

# ---------- load enrichment: complete reviews + comment authorship ----------
ENR = {}
for path in sorted(glob.glob(os.path.join(RAW, "enr_*.jsonl"))):
    with open(path) as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                ENR[r["number"]] = r

# ---------- load git file history, join to PR authors ----------
file_authors = collections.defaultdict(set)   # path -> {login}
eng_files = collections.defaultdict(set)      # login -> {path}
git_stats = {"commits": 0, "joined": 0}
git_path = os.path.join(RAW, "git_log.txt")
pr_author = {}
for p in prs:
    a = p.get("author") or {}
    if not is_bot(a.get("login"), a.get("__typename")):
        pr_author[p["number"]] = a["login"]

if os.path.exists(git_path):
    txt = open(git_path, encoding="utf-8", errors="replace").read()
    for block in txt.split("@@@")[1:]:
        lines = block.split("\n")
        head = lines[0].split("\t")
        if len(head) < 5:
            continue
        git_stats["commits"] += 1
        m = PR_IN_SUBJECT.search(head[4])
        login = pr_author.get(int(m.group(1))) if m else None
        if not login:
            continue
        git_stats["joined"] += 1
        for fp in (l.strip() for l in lines[1:]):
            if fp:
                file_authors[fp].add(login)
                eng_files[login].add(fp)

file_centrality = {f: len(a) for f, a in file_authors.items()}

# ---------- per-engineer accumulation ----------
E = collections.defaultdict(lambda: {
    "merged": 0, "attention_sum": 0.0, "high_attention": 0,
    "reviews_given": 0, "substantive_reviews": 0, "helped": set(),
    "reviewers_received": set(), "mix": collections.Counter(), "agent": 0,
    "top_prs": [], "reviewed_counts": collections.Counter(),
    "first_seen": None, "last_seen": None,
})

all_attention = []
for p in prs:
    a = p.get("author") or {}
    author = a.get("login")
    author_ok = not is_bot(author, a.get("__typename"))
    enr = ENR.get(p["number"])
    src = enr if enr else p
    rev_nodes = [r for r in src["reviews"]["nodes"] if r and (r.get("author") or {}).get("login")]
    distinct_reviewers = {r["author"]["login"] for r in rev_nodes
                          if not is_bot(r["author"]["login"]) and r["author"]["login"] != author}
    # inline review comments written by human reviewers other than the author
    threads = sum((r.get("comments") or {}).get("totalCount", 0) for r in rev_nodes
                  if not is_bot(r["author"]["login"]) and r["author"]["login"] != author)
    if enr:
        comments = sum(1 for c in enr["comments"]["nodes"]
                       if c and (c.get("author") or {}).get("login")
                       and not is_bot(c["author"]["login"]) and c["author"]["login"] != author)
    else:
        comments = 0
    attention = min(len(distinct_reviewers) + 0.5 * threads + 0.25 * comments, ATT_CAP)
    all_attention.append(attention)

    labels = [l["name"] for l in p["labels"]["nodes"]]
    ai_approved = AI_APPROVAL_LABEL in labels   # skipped full human review
    if author_ok:
        e = E[author]
        e["merged"] += 1
        if ai_approved:
            e["agent"] += 1
        e["attention_sum"] += attention
        e["reviewers_received"] |= distinct_reviewers
        e["mix"][classify(p["title"], labels)] += 1
        e["top_prs"].append({
            "n": p["number"], "t": p["title"][:120], "a": round(attention, 1),
            "r": len(distinct_reviewers), "th": threads, "c": comments,
            "d": (p["mergedAt"] or "")[:10], "ag": 1 if ai_approved else 0,
        })
        d = (p["mergedAt"] or "")[:10]
        e["first_seen"] = min(e["first_seen"] or d, d)
        e["last_seen"] = max(e["last_seen"] or d, d)

    for r in rev_nodes:
        v = r["author"]["login"]
        if is_bot(v) or v == author or not author_ok:
            continue
        ev = E[v]
        ev["reviews_given"] += 1
        ev["helped"].add(author)
        ev["reviewed_counts"][author] += 1
        if r["state"] in ("CHANGES_REQUESTED", "COMMENTED"):
            ev["substantive_reviews"] += 1

ATT_HIGH = statistics.quantiles(all_attention, n=10)[-1] if len(all_attention) > 10 else 1
for login, e in E.items():
    e["high_attention"] = sum(1 for p in e["top_prs"] if p["a"] >= ATT_HIGH)

# ---------- eligibility ----------
elig = {l for l, e in E.items() if e["merged"] >= MIN_PRS or e["reviews_given"] >= MIN_REVIEWS}

# ---------- raw sub-metrics ----------
raw = {l: {} for l in elig}
for l in elig:
    e = E[l]
    files = eng_files.get(l, set())
    core = [f for f in files if file_centrality.get(f, 0) >= CORE_FILE_MIN_AUTHORS]
    neighbors = set()
    for f in files:
        neighbors |= file_authors.get(f, set())
    neighbors.discard(l)
    raw[l] = {
        "distinct_helped": len(e["helped"]),
        "substantive_reviews": e["substantive_reviews"],
        "core_files": len(core),
        "co_engineers": len(neighbors),
        "attention_sum": round(e["attention_sum"], 1),
        "high_attention_prs": e["high_attention"],
        "fixperf_share": (e["mix"]["fix"] + e["mix"]["perf"]) / max(e["merged"], 1),
        "type_breadth": sum(1 for k, v in e["mix"].items() if v > 0 and k != "other"),
        "files_touched": len(files),
        "merged": e["merged"],
        "ai_approved_prs": e["agent"],
        "ai_approved_share": e["agent"] / max(e["merged"], 1),
        "fully_reviewed_prs": e["merged"] - e["agent"],
        "reviews_given": e["reviews_given"],
    }

P = {k: pct({l: raw[l][k] for l in elig}) for k in
     ("distinct_helped", "substantive_reviews", "core_files", "co_engineers",
      "attention_sum", "high_attention_prs", "fixperf_share", "type_breadth")}

engineers = []
for l in elig:
    e, r = E[l], raw[l]
    pillars = {
        "leverage": round(0.6 * P["distinct_helped"][l] + 0.4 * P["substantive_reviews"][l], 1),
        "blast":    round(0.5 * P["core_files"][l] + 0.5 * P["co_engineers"][l], 1),
        "shipping": round(0.5 * P["attention_sum"][l] + 0.5 * P["high_attention_prs"][l], 1),
        "workmix":  round(0.6 * P["fixperf_share"][l] + 0.4 * P["type_breadth"][l], 1),
    }
    score = round(sum(pillars[k] * w for k, w in WEIGHTS.items()), 1)
    top_files = sorted(((f, file_centrality.get(f, 0)) for f in eng_files.get(l, set())),
                       key=lambda x: -x[1])[:6]
    engineers.append({
        "login": l, "score": score, "pillars": pillars, "raw": r,
        "mix": dict(e["mix"]),
        "top_prs": sorted(e["top_prs"], key=lambda p: -p["a"])[:6],
        "top_files": [{"f": f, "c": c} for f, c in top_files],
        "reviewed": [{"who": w, "n": n} for w, n in e["reviewed_counts"].most_common(6)],
        "active": [e["first_seen"], e["last_seen"]],
    })

engineers.sort(key=lambda x: -x["score"])
out = {
    "meta": {
        "repo": "PostHog/posthog", "window": WINDOW,
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "merged_prs": len(prs),
        "human_prs": sum(1 for p in prs if not is_bot((p.get("author") or {}).get("login"),
                                                      (p.get("author") or {}).get("__typename"))),
        "contributors_total": len(E), "contributors_eligible": len(elig),
        "git_commits": git_stats["commits"], "git_joined_to_pr": git_stats["joined"],
        "files_tracked": len(file_centrality),
        "weights": WEIGHTS, "attention_high_threshold": round(ATT_HIGH, 2),
        "eligibility": f"merged>={MIN_PRS} or reviews>={MIN_REVIEWS}",
        "core_file_min_authors": CORE_FILE_MIN_AUTHORS, "attention_cap": ATT_CAP, "enriched_prs": len(ENR), "attention_basis": "human reviewers, human inline review comments, human issue comments",
        "ai_approved_prs": sum(1 for p in prs if AI_APPROVAL_LABEL in {l["name"] for l in p["labels"]["nodes"]}),
    },
    "engineers": engineers[:150],
}
with open(os.path.join(ROOT, "data.json"), "w") as f:
    json.dump(out, f, separators=(",", ":"))

print(json.dumps(out["meta"], indent=2))
print("\nTOP 10:")
for e in engineers[:10]:
    print(f"  {e['score']:5.1f}  {e['login']:22s} L{e['pillars']['leverage']:5.1f} "
          f"B{e['pillars']['blast']:5.1f} S{e['pillars']['shipping']:5.1f} W{e['pillars']['workmix']:5.1f} "
          f"| {e['raw']['merged']}pr ({e['raw']['ai_approved_prs']} ai-appr) {e['raw']['reviews_given']}rev {e['raw']['distinct_helped']}helped")
print(f"\ndata.json bytes={os.path.getsize(os.path.join(ROOT,'data.json'))}")
