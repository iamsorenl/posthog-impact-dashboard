#!/usr/bin/env python3
"""Fetch merged PRs for a date range, one day per search slice (dodges the 1000-result cap).

Usage: fetch_prs.py START_DATE END_DATE OUT.jsonl   (dates inclusive, YYYY-MM-DD)
Writes JSONL of PR records + OUT.manifest.json mapping day -> {expected, fetched}.
"""
import json, subprocess, sys, time, urllib.request, datetime as dt

REPO = "PostHog/posthog"
TOKEN = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True).stdout.strip()

QUERY = """
query($q:String!, $after:String){
  search(query:$q, type:ISSUE, first:100, after:$after){
    issueCount
    pageInfo{ hasNextPage endCursor }
    nodes{ ... on PullRequest {
      number title createdAt mergedAt additions deletions changedFiles
      author{ login __typename }
      labels(first:10){ nodes{ name } }
      reviews(first:30){ totalCount nodes{ author{login} state submittedAt } }
      reviewThreads(first:0){ totalCount }
      comments(first:0){ totalCount }
    }}
  }
  rateLimit{ remaining resetAt }
}"""


def gql(q, after=None, tries=5):
    body = json.dumps({"query": QUERY, "variables": {"q": q, "after": after}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql", data=body,
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.loads(r.read())
            if "errors" in d:
                raise RuntimeError(d["errors"])
            return d["data"]
        except Exception as e:
            if i == tries - 1:
                raise
            time.sleep(2 ** i)


def main():
    start, end, out = sys.argv[1], sys.argv[2], sys.argv[3]
    d0 = dt.date.fromisoformat(start)
    d1 = dt.date.fromisoformat(end)
    manifest, total = {}, 0
    with open(out, "w") as f:
        day = d0
        while day <= d1:
            q = f"repo:{REPO} is:pr is:merged merged:{day.isoformat()}"
            after, got, expected = None, 0, None
            while True:
                data = gql(q, after)
                s = data["search"]
                if expected is None:
                    expected = s["issueCount"]
                for n in s["nodes"]:
                    if not n:
                        continue
                    f.write(json.dumps(n) + "\n")
                    got += 1
                if not s["pageInfo"]["hasNextPage"]:
                    break
                after = s["pageInfo"]["endCursor"]
            manifest[day.isoformat()] = {"expected": expected, "fetched": got}
            total += got
            print(f"{day} expected={expected} fetched={got} rl={data['rateLimit']['remaining']}", flush=True)
            day += dt.timedelta(days=1)
    with open(out + ".manifest.json", "w") as f:
        json.dump({"range": [start, end], "total": total, "days": manifest}, f, indent=2)
    bad = {k: v for k, v in manifest.items() if v["expected"] != v["fetched"]}
    print(f"TOTAL={total} MISMATCHED_DAYS={bad}")


main()
