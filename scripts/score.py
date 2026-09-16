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
# Generated/lock/snapshot files are touched by everyone and owned by no one. Counting them as
# "shared surfaces" made every engineer's evidence panel show an identical file list.
GENERATED_RE = re.compile(
    r"generated|__snapshots__|snapshots?\.(ya?ml|json)$|\.snap$|-lock\.(json|ya?ml)$"
    r"|(package-lock\.json|pnpm-lock\.ya?ml|poetry\.lock|Cargo\.lock|yarn\.lock|go\.sum)$"
    r"|\.min\.(js|css)$|(^|/)(dist|build|vendor|node_modules)/", re.I)

WEIGHTS = {"leverage": 0.35, "blast": 0.25, "shipping": 0.25, "workmix": 0.15}
# pillar = sum(w * percentile(sub-metric)); exported to the page so the explain popovers show the real formula
PILLARS = {
    "leverage": (("distinct_helped", 0.6), ("substantive_reviews", 0.4)),
    # co_engineers dropped: cohort median 128, top-20 range 138-169. In a monorepo everyone active
    # co-edits files with ~140 people, so it measured "do you work here", not impact, while carrying
    # 12.5% of the score. core_files (median 61, top-20 107-428) actually discriminates.
    "blast":    (("core_files", 1.0),),
    "shipping": (("attention_sum", 0.5), ("high_attention_prs", 0.5)),
    "workmix":  (("fixperf_share", 0.6), ("type_breadth", 0.4)),
}
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


SCOPE_RE = re.compile(r"^\s*\w+\(([\w./-]+)\)")            # feat(data-warehouse): ...
SCOPE_LABEL = {"flags": "feature flags", "ci": "CI", "devex": "developer experience",
               "hogql": "HogQL", "llma": "LLM analytics", "ee": "enterprise"}
PILLAR_FACT = {   # strongest supporting fact, keyed by the engineer's best pillar
    "leverage": lambda r, e: f"{r['substantive_reviews']} substantive reviews across {r['distinct_helped']} engineers"
                             + (f", {e['reviewed'][0]['n']} of them for {e['reviewed'][0]['who']}" if e["reviewed"] else ""),
    "blast":    lambda r, e: f"touched {r['core_files']} shared-surface files (files 5+ engineers also changed)",
    "shipping": lambda r, e: f"{r['high_attention_prs']} of {r['merged']:,} merged PRs drew top-decile human scrutiny",
    "workmix":  lambda r, e: f"{round(100 * r['fixperf_share'])}% of {r['merged']} merged PRs are fixes or perf work",
}


def scope_of(title):
    m = SCOPE_RE.match(title or "")
    return m.group(1).lower() if m else None


def why_line(e):
    """One plain-English line: what territory this person owns, the strongest fact, the honest caveat."""
    r, top = e["raw"], e["top_prs"]
    top_scopes = collections.Counter(s for s in map(scope_of, (p["t"] for p in top)) if s)
    all_scopes = collections.Counter(s for s in e["all_scopes"] if s)
    label = lambda s: SCOPE_LABEL.get(s, s.replace("-", " "))
    if top_scopes and top_scopes.most_common(1)[0][1] >= 3:
        s, k = top_scopes.most_common(1)[0]
        territory = f"Owns {label(s)}: {k} of {len(top)} highest-scrutiny PRs are scoped {s}"
    elif all_scopes and all_scopes.most_common(1)[0][1] >= 0.3 * r["merged"]:
        s, k = all_scopes.most_common(1)[0]
        territory = f"Mostly {label(s)}: {k} of {r['merged']:,} merged PRs are scoped {s}"
    elif len(top_scopes) >= 3:
        territory = "No single area: highest-scrutiny PRs span " + ", ".join(s for s, _ in top_scopes.most_common(4))
    elif e["top_files"]:
        dirs = collections.Counter("/".join(x["f"].split("/")[:2]) for x in e["top_files"])
        d, k = dirs.most_common(1)[0]
        territory = f"Territory is {d}/: {k} of {len(e['top_files'])} most-owned shared files live there"
    else:
        territory = "No merged PRs in window; on the list for review work alone"
    best = max(e["pillars"], key=e["pillars"].get)
    line = f"{territory}; {PILLAR_FACT[best](r, e)}"
    bare = r["reviews_given"] - r["substantive_reviews"]
    if r["reviews_given"] >= 20 and bare > 0.75 * r["reviews_given"]:
        line += f"; but {bare} of {r['reviews_given']} reviews given were bare approvals"
    return line + "."


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
file_touches = collections.Counter()          # path -> total touches by anyone
eng_file_touches = collections.defaultdict(collections.Counter)  # login -> path -> touches
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
            if fp and not GENERATED_RE.search(fp):
                file_authors[fp].add(login)
                eng_files[login].add(fp)
                file_touches[fp] += 1
                eng_file_touches[login][fp] += 1

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
        # The page states a bare approval is a rubber stamp that scores nothing. It must therefore
        # not count as "unblocking" someone either. Substantive = changes requested, or a review
        # that actually carried inline comments (enrichment gives us per-review comment counts).
        substantive = (r["state"] == "CHANGES_REQUESTED"
                       or (r.get("comments") or {}).get("totalCount", 0) > 0)
        if substantive:
            ev["substantive_reviews"] += 1
            ev["helped"].add(author)
            ev["reviewed_counts"][author] += 1

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
    pillars = {k: round(sum(w * P[m][l] for m, w in parts), 1) for k, parts in PILLARS.items()}
    score = round(sum(pillars[k] * w for k, w in WEIGHTS.items()), 1)
    # Territory: how much of this file is theirs (damped by file volume),
    # scaled by how many other engineers share it. Display only.
    rows = []
    for f, n in eng_file_touches.get(l, {}).items():
        c = file_centrality.get(f, 0)
        if c < 2 or f.endswith(".lock"):
            continue
        rows.append(((n / math.sqrt(file_touches[f])) * math.log2(c), f, n, c))
    rows.sort(key=lambda r: (-r[0], r[1]))   # path tiebreak keeps reruns stable
    top_files = [{"f": f, "c": c, "n": n} for _, f, n, c in rows[:6]]
    rec = {
        "login": l, "score": score, "pillars": pillars, "raw": r,
        "pcts": {k: P[k][l] for k in P},   # sub-metric percentiles, so the page can show the substituted formula
        "mix": dict(e["mix"]),
        "top_prs": sorted(e["top_prs"], key=lambda p: -p["a"])[:6],
        "top_files": top_files,
        "reviewed": [{"who": w, "n": n} for w, n in e["reviewed_counts"].most_common(6)],
        "active": [e["first_seen"], e["last_seen"]],
        "all_scopes": [scope_of(p["t"]) for p in e["top_prs"]],   # display-only input to why_line
    }
    rec["why"] = why_line(rec)
    del rec["all_scopes"]
    engineers.append(rec)

engineers.sort(key=lambda x: (-x["score"], x["login"]))   # login tiebreak: reruns stable

# ---------- repo-level system view (SPACE: show the system before naming anyone) ----------
_ts = lambda s: dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
_start = dt.date.fromisoformat(WINDOW[0])
weekly = [0] * 13
merge_hours, first_review_hours, repo_mix = [], [], collections.Counter()
rev_act = {"human": 0, "bot": 0}
for p in prs:
    weekly[min((_ts(p["mergedAt"]).date() - _start).days // 7, 12)] += 1
    merge_hours.append((_ts(p["mergedAt"]) - _ts(p["createdAt"])).total_seconds() / 3600)
    repo_mix[classify(p["title"], [l["name"] for l in p["labels"]["nodes"]])] += 1
    author = (p.get("author") or {}).get("login")
    src = ENR.get(p["number"], p)
    nodes = [r for r in src["reviews"]["nodes"] if r and (r.get("author") or {}).get("login")]
    if p["number"] in ENR:
        nodes += [c for c in ENR[p["number"]]["comments"]["nodes"] if c and (c.get("author") or {}).get("login")]
    for r in nodes:
        rev_act["bot" if is_bot(r["author"]["login"]) else "human"] += 1
    human_at = [_ts(r["submittedAt"]) for r in src["reviews"]["nodes"]
                if r and (r.get("author") or {}).get("login") and r.get("submittedAt")
                and not is_bot(r["author"]["login"]) and r["author"]["login"] != author]
    if human_at:
        first_review_hours.append((min(human_at) - _ts(p["createdAt"])).total_seconds() / 3600)
system = {
    "weekly_merged": weekly,
    "median_merge_hours": round(statistics.median(merge_hours), 1),
    "median_first_human_review_hours": round(statistics.median(first_review_hours), 1),
    "human_reviewed_prs": len(first_review_hours),
    "review_activity": rev_act,          # reviews + issue comments, by author type
    "repo_mix": dict(repo_mix),
}
assert sum(weekly) == len(prs) and rev_act["human"] > 0

out = {
    "meta": {
        "repo": "PostHog/posthog", "window": WINDOW,
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "merged_prs": len(prs),
        "human_prs": sum(1 for p in prs if not is_bot((p.get("author") or {}).get("login"),
                                                      (p.get("author") or {}).get("__typename"))),
        "contributors_total": len(E), "contributors_eligible": len(elig),
        "git_commits": git_stats["commits"], "git_joined_to_pr": git_stats["joined"],
        "files_tracked": len(file_centrality), "generated_files_excluded": True,
        "weights": WEIGHTS, "pillar_formula": PILLARS, "attention_high_threshold": round(ATT_HIGH, 2),
        "eligibility": f"merged>={MIN_PRS} or reviews>={MIN_REVIEWS}",
        "core_file_min_authors": CORE_FILE_MIN_AUTHORS, "attention_cap": ATT_CAP, "enriched_prs": len(ENR), "attention_basis": "human reviewers, human inline review comments, human issue comments",
        "ai_approved_prs": sum(1 for p in prs if AI_APPROVAL_LABEL in {l["name"] for l in p["labels"]["nodes"]}),
        "system": system,
    },
    "engineers": engineers,   # the whole eligible cohort; the page paginates
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
