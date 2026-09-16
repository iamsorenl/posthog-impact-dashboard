# Submission — Engineering Impact Dashboard

**Dashboard:** https://iamsorenl.github.io/posthog-impact-dashboard/
**Source:** https://github.com/iamsorenl/posthog-impact-dashboard
**Time:** 2h 08m 44s (128:44), against a 90-minute limit. Over by 38 minutes, and worth saying why.

**A complete, working dashboard was live 21 minutes after the first commit of the session** (`b7ac880` starts the work, `ba6a2b1` ships the dashboard, and GitHub Pages served it 18 seconds later; the interval is checkable in the public repo history). So the deliverable existed comfortably inside the budget. The overrun was correctness work that independent review forced, and I judged shipping a confidently wrong dashboard worse than going long. A verification pass caught a misread GitHub label that had become the page's headline claim, corrected from "39% AI-authored" to "35.3% took AI-only approval." A measurement bug was counting bot-authored comments as human review scrutiny, letting diff size back into the pillar built to replace it. And a proposed per-PR median term was tested and rejected on evidence rather than shipped because it sounded right.

## The finding worth more than the ranking

The ranking answers the question asked. This is the part a PostHog leader probably does not already know: **the repo has largely automated its own code review.** 35.3% of merged PRs (5,359 of 15,162) carry `stamphog`, which GitHub describes as "Request AI approval (no full review)". Only 39% of review activity is human. Five of the seven busiest reviewers are bots, and `stamphog` alone left 8,460 reviews, more than any person.

That is not a footnote about data hygiene. It means every conventional engineering metric in this repo is now measuring automation throughput: PR counts, commit counts, review counts and comment counts all move with bot activity. It also quietly changes what "reviewed" means, since a third of merged work never met a human reviewer.

It is also the reason this dashboard scores none of those things, and why "attention" counts only human reviewers and human comments. I found it by chasing an implausible number (one account merging 121 PRs in a day) and initially misread it as AI-authored PRs before an independent check against the label API corrected me.

## Approach

**The question I actually answered.** Not "who commits most" but "whose absence would the team feel first." Lines, commits, PR count and files changed are all present in the dataset and all contribute **zero** to the score — each has an obvious degenerate case, and one of them turned out to be actively broken at PostHog (below).

**The finding that reshaped the model.** Volume metrics don't just fail in principle at PostHog, they fail mechanically. **35.3% of merged PRs (5,359 of 15,162) carry the `stamphog` label** — GitHub's own description: *"Request AI approval (no full review)"* — meaning the author asked a bot to approve rather than waiting on full human review. And **five of the seven highest-volume reviewers in the repo are bots**; `stamphog` alone left 8,460 reviews, more than any human. Counting PRs or reviews in this repo measures automation, not engineering, so the model scores neither.

*(I got this wrong first: an earlier build read `stamphog` as "AI-authored" and inflated the figure by unioning it with `skip-agent-review`, a label meaning roughly the opposite. An independent verification pass against the GitHub label API caught it. The corrected reading is on the dashboard, and the same audit exposed a leaky bot filter that was counting ~19k AI reviews as human activity.)*

**Four pillars**, each a cohort percentile, combined 35/25/25/15:

- **Review leverage (35%)** — distinct engineers you gave a *substantive* review, plus your count of substantive reviews. A bare approval is a rubber stamp: it scores zero and does not count as unblocking anyone. Measures the multiplier effect.
- **Blast radius (25%)** — shared-surface files you touched: files that 5 or more distinct engineers also changed in the window. A big diff in an isolated corner scores near zero. Single term; see the deleted sub-metric below.
- **Reviewed throughput (25%)** — merged work weighted by the human review attention it attracted (human reviewers, human inline review comments, human issue comments, all excluding the author), capped per PR so one flamewar can't carry someone. Named for what it measures, not "consequence": it still correlates rho=0.86 with merged-PR count (below).
- **Work mix & load (15%)** — fix/perf share and breadth of work types. Credits the person keeping production healthy.

Every score opens into the named PRs, files and people behind it, so the ranking is falsifiable rather than asserted.

## Data

Every merged PR in `PostHog/posthog` for 2026-06-18 → 2026-09-16: **15,162 PRs**, fetched from the GitHub GraphQL API **one day at a time** to stay under the API's 1,000-result search cap. Completeness is asserted per day (`expected == fetched`); all 91 days matched with **zero mismatches** — complete, not sampled.

File-level data comes from a treeless clone plus `git log --name-only`: **14,831 commits, 150,300 file touches**, joined to PR authorship via the `(#NNNNN)` squash reference. 99.7% of commits carry that reference; **90.0%** of all commits (13,351/14,831) resolve to a known human PR author, the rest belong to bot-authored or out-of-window PRs. This is more complete than the API's `files` connection, which truncates at 100 files, and it cost zero API calls.

Of 230 total contributors, 158 clear the eligibility floor (≥3 merged PRs or ≥5 reviews). All 158 are inlined and individually inspectable in the page.

Dashboard is a single self-contained ~283 KB HTML file with the scored data inlined as JSON — no framework, no build step. It does still load engineer avatars from `github.com` after load, so it isn't fully offline.

**One sub-metric was deleted, not tuned.** Blast radius originally blended shared-surface files with a count of engineers co-editing them. That second term had almost no discriminating power: cohort median 128, with the top twenty engineers spanning just 138 to 169. In a monorepo, anyone active co-edits files with roughly 140 people, so it measured "do you work here" rather than impact while carrying 12.5% of every score. It was removed rather than reweighted. Blast radius is now a single term, shared-surface files, which has a median of 61 against a top-twenty range of 107 to 428.

## Why the #1 result is what it is

Gilbert09 tops the list with 2,414 merged PRs, and a reasonable first reaction is that this is a PR-count leaderboard wearing a percentile costume. Worth addressing directly, because it is the obvious objection.

Strip out every AI-approved PR and he still has **994 fully human-reviewed PRs against 184 for the next ranked engineer** — 5.4x, on the subset that got real human scrutiny. He also has 77 top-decile-attention PRs and touches 410 shared-surface files. The volume is real, it is concentrated in the data warehouse, and it is reviewed.

Where he scores poorly is review leverage: 25 substantive reviews, 11 engineers unblocked. He is a builder, not a multiplier, and the pillar breakdown says so on the card rather than hiding it.

I tried three times to engineer him out of the top slot and rejected all three, because each was chosen by its effect on one account rather than on its merits. Independent review called that out, correctly. The residual volume sensitivity is disclosed instead: the composite correlates rho=0.90 with merged-PR count. That number is on the page, not in a footnote.

## What it cannot see — stated on the page, not buried

**Volume still wins on the back door.** No pillar weights PR count, yet `corr(log(merged PRs), score) ≈ 0.89` across the 158 ranked engineers, because percentiles of per-PR sums are partly rank transforms of PR count. This is the biggest gap between what the model claims to measure and what it rewards.

*What I did about it:* attention originally counted *all* reviewers, threads and comments, including bots. Bots author roughly 71% of issue comments and over half of inline review comments in this repo, and AI reviewers comment roughly in proportion to diff size, so raw comment/thread totals were quietly letting lines-of-code back in through the pillar built to replace it. Attention now counts only human reviewers, human inline review comments and human issue comments, excluding the PR author. That dropped reviewed-throughput's correlation with PR count from 0.98 to 0.86 and the top-decile attention threshold from 6.5 to 2.5.

*What I tested and rejected:* blending `attention_sum` with a per-PR **median**, so consistency would count alongside quantity. Killed on inspection: the median took only ~26 distinct values across the eligible pool, so one comment on one PR could swing a score more than the gap between 1st and 3rd place; it correlated just −0.28 with AI-approval share, so the mechanism it was meant to counteract was mostly absent; its biggest beneficiaries were engineers with two to five merged PRs, not the profile it targeted; and it penalized requesting AI approval on trivial changes, which is PostHog's own documented triage, not a shortcut. Peak-based and reweighted variants changed essentially nothing either. Fixing the input, not bolting on a second statistic, was the right lever.

Glue work (RFCs, design review, mentoring), the support-hero rotation, long-cycle work that lands as one PR, and a structural greenfield penalty: blast radius rewards crowded files, so anyone alone in a new product area scores low by construction. Percentile scoring also disadvantages new hires.

More fundamentally: ranking individuals on delivery telemetry is contested. SPACE (Forsgren et al. 2021) does define individual-level metrics, but warns against using any single one, especially activity counts, as a productivity proxy — this dashboard uses several dimensions but is still one composite score per person. DORA's four keys are explicitly team/org-level, not individual, so they don't directly license a leaderboard like this at all. And Deming's argument against merit rating (attributing system-level outcomes to individuals) applies squarely: a lot of what this score reflects is what code review culture and team structure route toward someone, not just what they did. The dashboard presents as evidence to check, not a verdict to accept.

## Feedback on the format

Far better than a Leetcode round — it surfaced a real judgment call (AI approval quietly replacing human review, and bots dominating review volume) that no algorithm question would have. The 90-minute budget is tight for "gather + analyze + build + host": a large chunk goes to data acquisition alone, and the interesting analytical work is what gets squeezed.
