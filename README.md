# PostHog Engineering Impact — 90 Days

Live dashboard: **https://iamsorenl.github.io/posthog-impact-dashboard/**

**Question:** who are the most impactful engineers at PostHog, and how would you check?

## Data
Every merged PR in `PostHog/posthog` for 2026-06-18 → 2026-09-16 — **15,162 PRs**, fetched from the
GitHub GraphQL API **one day at a time** so nothing is lost to the API's 1,000-result search cap.
Completeness is asserted per day (`expected == fetched`); all 91 days matched with zero mismatches.
File-level data comes from a treeless clone of the repo (`git log --name-only`): **14,831 commits,
150,300 file touches**, joined to PR authorship by the `(#NNNNN)` squash-merge reference: **99.7%** of commits carry that
reference and **90.0%** resolve to a known human PR author, the rest being bot-authored or out-of-window.
More complete than the API's `files` connection, which truncates at 100 files, and it cost zero API calls.

## The finding that shapes everything
**35.3% of merged PRs (5,359) carry the `stamphog` label**, which GitHub describes as
*"Request AI approval (no full review)"* — the author asked a bot to approve rather than waiting on a full
human review. And **five of the seven highest-volume reviewers in the repo are bots**; `stamphog` alone left
8,460 reviews, more than any human. Counting PRs or reviews here measures automation, not engineering.

(An earlier build read `stamphog` as "AI-authored" and inflated the figure by unioning it with
`skip-agent-review`, a label meaning roughly the opposite. An independent verification pass against the
GitHub label API caught it.)

## Impact model
Four pillars, each a cohort percentile, combined 35/25/25/15. Volume metrics contribute **zero**.
- **Review leverage (35%)** — `0.6 × pct(engineers given a substantive review) + 0.4 × pct(substantive reviews)`.
  A bare approval scores zero and does not count as unblocking anyone.
- **Blast radius (25%)** — `pct(shared-surface files touched)`, files 5+ distinct engineers also changed.
  A co-editing term was deleted: its cohort median was 128 with the top twenty spanning 138-169, so it
  measured presence rather than impact while carrying 12.5% of the score.
- **Reviewed throughput (25%)** — `0.5 × pct(attention sum) + 0.5 × pct(top-decile PRs)`, where per-PR
  attention counts only human reviewers and human comments, capped at 15. Named for what it measures:
  it correlates 0.86 with PR count, so calling it "consequence" would overclaim.
- **Work mix (15%)** — `0.6 × pct(fix+perf share) + 0.4 × pct(work-type breadth)`.

Every pillar, score and jargon term on the page is clickable: one click gives a plain-English sentence,
the real formula, and that engineer's own inputs substituted into it.

**Stated honestly on the page:** the composite still correlates ρ=0.90 with merged-PR count even though
PR count is weighted zero, because percentiles of per-PR sums are partly rank transforms of PR count.

Every number drills down to the actual PRs. Limitations (glue work, long-cycle work, greenfield
penalty, new hires, and why SPACE/DORA/Deming say individual ranking is unsound) are stated on the page.

## Run it
```
python3 scripts/fetch_prs.py 2026-06-18 2026-09-16 data/raw/prs.jsonl
python3 scripts/score.py && python3 scripts/build.py
```
