Dashboard: https://iamsorenl.github.io/posthog-impact-dashboard/
Source: https://github.com/iamsorenl/posthog-impact-dashboard

## The finding worth more than the ranking

PostHog has largely automated its own code review. 35.3% of merged PRs (5,359 of 15,162) carry the `stamphog` label, which GitHub's own description defines as "Request AI approval (no full review)". Only 39% of review activity in the repo is human. Five of the seven busiest reviewers are bots, and `stamphog` alone left 8,460 reviews, more than any person.

That is not a data-hygiene footnote. Every conventional engineering metric in this repo now moves with bot activity: PR counts, commit counts, review counts, comment counts. It also quietly changes what "reviewed" means, since a third of merged work never met a human reviewer.

I found it by chasing an implausible number, one account merging 121 PRs in a single day, and I initially misread it as "AI-authored PRs" before an independent check against the GitHub label API corrected me.

## What I mean by impact

Not "who commits most" but "whose absence would the team feel first." Lines changed, commits, PR count and files touched are all present in the dataset and all contribute exactly zero to the score.

Four pillars, each converted to a percentile within the 158-engineer eligible cohort (>=3 merged PRs or >=5 reviews):

Score = 0.35 x Leverage + 0.25 x Blast radius + 0.25 x Reviewed throughput + 0.15 x Work mix

**Review leverage (35%)** = 0.6 x pct(engineers given a substantive review) + 0.4 x pct(substantive reviews). Substantive means changes requested, or a review carrying at least one inline comment. A bare approval is a rubber stamp: it scores zero and does not count as unblocking anyone. This is the multiplier signal, the senior who spends the morning in review rather than shipping.

**Blast radius (25%)** = pct(shared-surface files touched), where a shared surface is a file 5 or more distinct engineers also changed in the window. A big diff in an isolated corner scores near zero; a small diff in a hot path scores high.

**Reviewed throughput (25%)** = 0.5 x pct(attention sum) + 0.5 x pct(top-decile PRs). Per-PR attention = min(human reviewers + 0.5 x human inline comments + 0.25 x human issue comments, 15). This uses the organisation's own scrutiny as the proxy for consequence instead of diff size: a 2,000-line PR nobody read scores below a 20-line PR five engineers argued over. It is named for what it measures. At 0.86 correlation with PR count, calling it "consequence" would overclaim.

**Work mix (15%)** = 0.6 x pct(fix+perf share) + 0.4 x pct(work-type breadth). Credits the person quietly keeping production healthy, which feature-count metrics systematically miss.

## Data

Every merged PR in PostHog/posthog for 2026-06-18 to 2026-09-16: **15,162 PRs**, fetched from the GitHub GraphQL API one day at a time so nothing is lost to the API's 1,000-result search cap. Completeness is asserted per day (expected == fetched) and all 91 days matched with zero mismatches. Complete, not sampled.

File-level data comes from a treeless clone plus `git log --name-only`: 14,831 commits and 150,300 file touches, joined to PR authorship by the `(#NNNNN)` squash-merge reference. 99.7% of commits carry that reference and 90.0% resolve to a known human PR author. This is more complete than the API's `files` connection, which truncates at 100 files, and it cost zero API calls.

A second enrichment pass backfilled every PR that exceeded the API's 30-review page limit, so review and comment records are complete rather than silently truncated.

## The dashboard

A single self-contained HTML file with the scored data inlined as JSON. No framework, no build step, no network calls beyond avatars. Loads in about 0.1 seconds.

It opens with a repo-level system strip (merged PRs by week, median time to merge, human share of review activity, AI-only approval rate, fix-to-feature ratio) so a leader sees team health before any individual is named. That ordering is deliberate: it is the framing SPACE and DORA actually support, and it shows the baseline every percentile is measured against.

Every pillar, every score and every piece of jargon is clickable. One click gives a plain-English sentence, the real formula, and that engineer's own inputs substituted into it. For example, Leverage for the top-ranked engineer reads: 0.6 x 89 (11 engineers) + 0.4 x 74 (25 reviews) = 83rd pct. The formulas are read from the scoring output rather than transcribed, so the explanation cannot drift from the score.

Each of the top five carries a generated "why" line naming what that person owns and their strongest supporting fact, including the unflattering one where it applies. The #1 card reads: "Owns data warehouse: 5 of 6 highest-scrutiny PRs are scoped data-warehouse; 77 of 2,414 merged PRs drew top-decile human scrutiny; but 374 of 399 reviews given were bare approvals."

Top 5: Gilbert09, pauldambra, haacked, tatoalo, skoob13.

## On the #1 result

Gilbert09 tops the list on 2,414 merged PRs, which invites the obvious objection that this is PR count with extra steps. Worth answering directly. Strip out every AI-approved PR and he still has 994 fully human-reviewed PRs against 184 for the next ranked engineer, a 5.4x gap on the subset that got real human scrutiny. The volume is real, concentrated in the data warehouse, and reviewed.

Where he scores poorly is review leverage: 25 substantive reviews, 11 engineers unblocked. He is a builder, not a multiplier, and the pillar breakdown says so on his card rather than hiding it.

I tried three times to engineer him out of the top slot and rejected all three attempts, because each was chosen by its effect on one account rather than on its merits. The residual bias is disclosed instead.

## What it cannot see, stated on the page

Glue work (RFCs, design review, mentoring, unblocking in Slack), the support-hero rotation, and long-cycle work that lands as one or two PRs are all invisible here. There is a structural greenfield penalty: blast radius rewards crowded files, so an engineer alone in a new product area scores low by construction. Percentile scoring over a fixed window disadvantages new hires.

The composite still correlates 0.90 with merged-PR count despite PR count carrying zero explicit weight, because percentiles of per-PR sums are partly rank transforms of PR count. Filtering bots out of "attention" cut that pillar from 0.98 to 0.86. Reduced, not solved, and said plainly on the page rather than in a footnote.

More fundamentally, ranking individuals on delivery telemetry is contested. SPACE (Forsgren et al. 2021) does define individual-level metrics but warns against relying on any single one, especially activity counts. DORA's four keys are explicitly team and org level. Deming's argument against merit rating applies directly, since much of what this score reflects is what review culture routes toward a person rather than what they did. The dashboard presents as evidence to check, not a verdict to accept, and every number opens into the PRs behind it.

## Corrections made under review

Independent review passes caught several errors, and the process is part of the submission:

- `stamphog` was misread as "AI-authored", and the figure was further inflated by unioning it with `skip-agent-review`, a label meaning roughly the opposite. Corrected to 35.3%.
- "Attention" was counting bot-authored comments. Bots write 71% of issue comments and AI reviewers comment roughly in proportion to diff size, so lines-of-code was re-entering through the very pillar built to replace it. Now human-only.
- "Unblocking" counted bare approvals, contradicting the page's own stated rule that a rubber stamp scores nothing. Now requires a substantive review.
- A proposed per-PR median density term was tested and rejected: only 26 distinct values across 154 engineers, -0.28 correlation with the mechanism it claimed to capture, benefits concentrated on engineers with two to five PRs, and it penalised requesting AI approval on trivial changes, which is PostHog's own documented triage.
- Blast radius originally blended in a co-editing term. Its cohort median was 128 with the top twenty spanning 138 to 169, so it measured "do you work here" rather than impact while carrying 12.5% of every score. Deleted rather than reweighted.
