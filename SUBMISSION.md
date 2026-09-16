# Submission — Engineering Impact Dashboard

**Dashboard:** https://iamsorenl.github.io/posthog-impact-dashboard/
**Source:** https://github.com/iamsorenl/posthog-impact-dashboard
**Time:** ~95 minutes (over the 90-minute budget; the dashboard was live and correct at ~85, the rest was a rendering fix and validation)

## Approach

**The question I actually answered.** Not "who commits most" but "whose absence would the team feel first." Lines, commits, PR count and files changed are all present in the dataset and all contribute **zero** to the score — each has an obvious degenerate case, and one of them turned out to be actively broken at PostHog (below).

**The finding that reshaped the model.** 39% of merged PRs in the window (5,955 of 15,162) are authored by PostHog's own AI agent, `stamphog`, and merged under human accounts — one account merged 121 in a single day. Any volume-based metric at PostHog today is measuring agent throughput, not engineering. Agent PRs are counted and labelled on the dashboard, but excluded from the shipping pillar, since they aren't the human's shipping judgment.

**Four pillars**, each a cohort percentile, combined 35/25/25/15:

- **Review leverage (35%)** — distinct engineers whose PRs you reviewed, plus substantive (non-rubber-stamp) reviews. Bare approvals score zero. Measures the multiplier effect.
- **Blast radius (25%)** — shared-surface files you touched (files ≥5 distinct engineers also touched) and distinct engineers co-editing them. A big diff in an isolated corner scores near zero.
- **Consequential shipping (25%)** — merged work weighted by the review attention it attracted, capped per PR so one flamewar can't carry someone. Uses the org's own scrutiny as the proxy for consequence rather than diff size.
- **Work mix & load (15%)** — fix/perf share and breadth of work types. Credits the person keeping production healthy.

Every score opens into the named PRs, files and people behind it, so the ranking is falsifiable rather than asserted.

## Data

Every merged PR in `PostHog/posthog` for 2026-06-18 → 2026-09-16: **15,162 PRs**, fetched from the GitHub GraphQL API **one day at a time** to stay under the API's 1,000-result search cap. Completeness is asserted per day (`expected == fetched`); all 91 days matched with **zero mismatches** — complete, not sampled.

File-level data comes from a treeless clone plus `git log --name-only`: **14,831 commits, 150,300 file touches**, joined to PR authorship via the `(#NNNNN)` squash reference at a **99.7%** join rate. This is more complete than the API's `files` connection, which truncates at 100 files, and it cost zero API calls.

Dashboard is a single self-contained 266 KB HTML file with the scored data inlined as JSON — no framework, no build step, no network calls after load. **Loads in ~0.17s.**

## What it cannot see — stated on the page, not buried

Glue work (RFCs, design review, mentoring), the support-hero rotation, long-cycle work that lands as one PR, and a structural greenfield penalty: blast radius rewards crowded files, so anyone alone in a new product area scores low by construction. Percentile scoring also disadvantages new hires.

More fundamentally: SPACE (Forsgren et al. 2021), DORA and Deming are consistent that ranking individuals on delivery telemetry is unsound — those frameworks scope deliberately to teams and systems. The dashboard presents as evidence to check, not a verdict to accept.

**Known weakness I'd fix next:** `attention_sum` is a sum over PRs, so volume re-enters through the side door — an engineer with 966 human PRs accumulates attention that 100 excellent PRs can't match. The fix is to blend the sum with a per-PR median so consistency counts alongside quantity.

## Feedback on the format

Far better than a Leetcode round — it surfaced a real judgment call (the agent-authored PR problem) that no algorithm question would have. The 90-minute budget is tight for "gather + analyze + build + host": data acquisition alone was ~25 minutes, and the interesting analytical work is what gets squeezed.
