# PostHog Engineering Impact — 90 Days

Live dashboard: see repo Pages URL.

**Question:** who are the most impactful engineers at PostHog, and how would you check?

## Data
Every merged PR in `PostHog/posthog` for 2026-06-17 → 2026-09-16 — **15,162 PRs**, fetched from the
GitHub GraphQL API **one day at a time** so nothing is lost to the API's 1,000-result search cap.
Completeness is asserted per day (`expected == fetched`); all 91 days matched with zero mismatches.
File-level data comes from a treeless clone of the repo (`git log --name-only`): **14,831 commits,
150,300 file touches**, joined to PR authorship by the `(#NNNNN)` squash-merge reference at a **99.7%**
join rate — more complete than the API's `files` connection, which truncates at 100 files.

## The finding that shapes everything
**39% of merged PRs (5,955) are authored by PostHog's own AI agent (`stamphog`)** and merged under a
human account; one account merged 121 in a single day. Any volume metric now measures agent throughput.
Agent PRs are counted and labelled, but excluded from the shipping pillar.

## Impact model
Four pillars, each a cohort percentile, combined 35/25/25/15. Volume metrics contribute **zero**.
- **Review leverage (35%)** — distinct engineers unblocked + substantive (non-rubber-stamp) reviews.
- **Blast radius (25%)** — shared-surface files touched + distinct engineers co-editing them.
- **Consequential shipping (25%)** — merged work weighted by review attention attracted, capped per PR.
- **Work mix & load (15%)** — fix/perf share + breadth of work types.

Every number drills down to the actual PRs. Limitations (glue work, long-cycle work, greenfield
penalty, new hires, and why SPACE/DORA/Deming say individual ranking is unsound) are stated on the page.

## Run it
```
python3 scripts/fetch_prs.py 2026-06-17 2026-09-16 data/raw/prs.jsonl
python3 scripts/score.py && python3 scripts/build.py
```
