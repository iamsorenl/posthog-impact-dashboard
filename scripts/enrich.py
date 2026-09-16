#!/usr/bin/env python3
"""Enrichment pass: linked issues, comment records, per-review comment depth, mergedBy.

Requests first:10 on nested connections (GitHub bills requested nodes, not returned),
records totalCount, then BACKFILLS any PR whose totalCount exceeds 10 with a dedicated
per-PR query. No sampling: every PR ends up with complete reviews + comments.

Usage: enrich.py START END OUT.jsonl
"""
import json, subprocess, sys, time, urllib.request, datetime as dt

REPO = "PostHog/posthog"
TOKEN = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True).stdout.strip()
N = 10

PAGE_Q = """
query($q:String!, $after:String){
  search(query:$q, type:ISSUE, first:100, after:$after){
    issueCount pageInfo{ hasNextPage endCursor }
    nodes{ ... on PullRequest {
      number url mergedBy{login} baseRefName
      closingIssuesReferences(first:10){ totalCount nodes{ number title url } }
      reviews(first:%d){ totalCount nodes{ author{login} state submittedAt comments(first:0){totalCount} } }
      comments(first:%d){ totalCount nodes{ author{login} createdAt } }
    }}
  }
  rateLimit{ cost remaining resetAt }
}""" % (N, N)

FULL_Q = """
query($num:Int!, $ra:String, $ca:String){
  repository(owner:"PostHog", name:"posthog"){ pullRequest(number:$num){
    reviews(first:100, after:$ra){ pageInfo{hasNextPage endCursor} nodes{ author{login} state submittedAt comments(first:0){totalCount} } }
    comments(first:100, after:$ca){ pageInfo{hasNextPage endCursor} nodes{ author{login} createdAt } }
  }}
  rateLimit{ remaining }
}"""


def gql(query, variables, tries=5):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body,
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                d = json.loads(r.read())
            if "errors" in d:
                msg = str(d["errors"])
                if "RATE_LIMITED" in msg or "rate limit" in msg.lower():
                    time.sleep(60); continue
                raise RuntimeError(msg)
            return d["data"]
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(2 ** i)


def backfill(rec):
    """Page a single PR to completeness when it overflowed the first:10 request."""
    need_r = rec["reviews"]["totalCount"] > len(rec["reviews"]["nodes"])
    need_c = rec["comments"]["totalCount"] > len(rec["comments"]["nodes"])
    if not (need_r or need_c):
        return rec
    reviews, comments, ra, ca = [], [], None, None
    while True:
        d = gql(FULL_Q, {"num": rec["number"], "ra": ra, "ca": ca})["repository"]["pullRequest"]
        if d is None:
            return rec
        reviews += [n for n in d["reviews"]["nodes"] if n]
        comments += [n for n in d["comments"]["nodes"] if n]
        rp, cp = d["reviews"]["pageInfo"], d["comments"]["pageInfo"]
        ra = rp["endCursor"] if rp["hasNextPage"] else None
        ca = cp["endCursor"] if cp["hasNextPage"] else None
        if not ra and not ca:
            break
    rec["reviews"]["nodes"] = reviews
    rec["comments"]["nodes"] = comments
    rec["backfilled"] = True
    return rec


def main():
    start, end, out = sys.argv[1], sys.argv[2], sys.argv[3]
    d0, d1 = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    manifest, total, filled = {}, 0, 0
    with open(out, "w") as f:
        day = d0
        while day <= d1:
            q = f"repo:{REPO} is:pr is:merged merged:{day.isoformat()}"
            after, got, expected, rl = None, 0, None, None
            while True:
                data = gql(PAGE_Q, {"q": q, "after": after})
                s = data["search"]; rl = data["rateLimit"]
                if expected is None:
                    expected = s["issueCount"]
                for n in s["nodes"]:
                    if not n:
                        continue
                    before = n.get("backfilled")
                    n = backfill(n)
                    if n.get("backfilled") and not before:
                        filled += 1
                    f.write(json.dumps(n) + "\n"); got += 1
                if not s["pageInfo"]["hasNextPage"]:
                    break
                after = s["pageInfo"]["endCursor"]
            manifest[day.isoformat()] = {"expected": expected, "fetched": got}
            total += got
            print(f"{day} exp={expected} got={got} backfilled={filled} rl={rl['remaining']}", flush=True)
            day += dt.timedelta(days=1)
    json.dump({"range": [start, end], "total": total, "backfilled": filled, "days": manifest},
              open(out + ".manifest.json", "w"), indent=2)
    bad = {k: v for k, v in manifest.items() if v["expected"] != v["fetched"]}
    print(f"TOTAL={total} BACKFILLED={filled} MISMATCHED_DAYS={bad}")


main()
