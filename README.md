# Weave take-home — Engineering Impact Dashboard

Private. Prompt: **`takehome-prompt.md`** is the authoritative full text. `takehome-prompt.pdf` is
the original print and is truncated at the page break (loses everything from "What to Submit" on).
Assessment `asmt_eD1bGr5o2Ea75Z0p0gnhglFW`, received 2026-09-15, due ~2026-09-18.

## The ask, digested

Build an analysis + interactive dashboard over the **PostHog/posthog** GitHub repo that names the
**top 5 most impactful engineers and why**, then host it at a URL Weave can open.

- **Graded on one thing: the impact definition.** Their words: "ugly UI with creative analysis
  beats beautiful UI with LOC / commit counts / files changed." Do not ship a volume metric.
- **Audience:** a busy PostHog eng leader. Knows the codebase at a basic level, will not read PRs.
  Every number needs a one-line "so what."
- **Constraints:** ≥ last 90 days of data (from **2026-06-17** onward), single laptop-screen page,
  interactive, hosted.
- **Time box: 90 minutes, self-timed.** Start the timer when work begins, stop when done, report it.
  Setup in this repo (scaffold, brief) was done *before* the timer. Data pull, analysis, and
  dashboard happen *inside* it.

## What to submit (from the assessment page, via the button at the bottom of it)

1. Dashboard URL
2. A short description of your approach
3. How long it took, straight from the timer
4. An export of your coding agent **sessions**

**The code is not submitted.** No repo link is asked for. So this repo stays private and the
hosted page is the ONLY artifact they see. The impact definition must live on the page.

Deadline: **within 3 days of receiving**, i.e. by ~2026-09-18. Assignment received 2026-09-15.
Trouble with the form, or need an extension: kevin@workweave.ai.

## Evaluation criteria (their words)

| Criterion | Their phrasing | What it forces |
|---|---|---|
| Thoughtfulness | "Can we understand it at a glance? Can we validate the findings?" | Every claim links to the PRs/reviews behind it. Auditability is graded. |
| Technical execution | "Does it work? Is it clear?" | No broken states, no console errors. |
| Communication | "Is your approach and reasoning clear?" | The definition and weights are visible on the page, not in a README. |
| Pragmatism | "Did you scope appropriately for 1.5 hours?" | Over-building is penalized. Ship the small version. |

"We're not expecting perfection. We want to see how you approach problems and communicate."

## Red flags (their list) → engineering constraints

| Red flag | What it means for the build |
|---|---|
| Link not accessible or doesn't load | Deploy early, then redeploy. Open the URL in a private window before submitting. |
| Incorrect, incomplete or missing data | Paginate the full 90-day window. Do not sample the base data. Verify the earliest merge date. |
| Buggy or broken UI | One self-contained page, no framework, no build step. Click everything once. |
| **>10s to load** | **Pre-compute everything and inline the JSON. No GitHub API calls at page load. No giant chart libs.** |
| Does not answer "who are the most impactful engineers" | The five names are the largest thing on the page, above everything else. |
| "Shows numbers with no way to understand how they were calculated (e.g. 'Score: 207')" | **No bare composite score.** Every number decomposes into its signals, each with its formula in plain words and the underlying PRs reachable. |

The last one is the whole assignment restated as a warning. A composite score with a visible
derivation is the deliverable; a composite score without one is an automatic red flag.

## Deliverables (their list)

1. A written definition of "impact" for software engineers.
2. Data pulled from PostHog/posthog covering ≥ 90 days.
3. Analysis.
4. Interactive dashboard: top 5 + why.
5. Hosted URL.
6. Export of the coding-agent session (`/export` at the end). Note they say *sessions*, plural.

## Impact definition — candidate signals (pick 4–6, weight them, show the weights)

The pitch: impact = **leverage** (how much others depend on what you did) × **risk you absorbed**
× **how much you unblocked others**, not how much you typed.

| Signal | What it captures | Source |
|---|---|---|
| Review leverage | PRs you reviewed that merged, weighted by their size; turnaround time | PR reviews |
| Blast radius | Merged PRs touching hot / widely-imported paths (ingestion, billing, query engine) vs docs/tests | PR files + path map |
| Breadth | Distinct subsystems (top-level dirs) touched; touching code you don't "own" | PR files |
| Durability | Merged PRs *not* followed by a revert/hotfix on the same files within N days | commits + PR titles |
| Unblocking | Issues closed via PR, bug-labeled PRs, responding on others' PRs | PR ↔ issue links, labels |
| Difficulty | Review rounds, comments, time-to-merge on your PRs (higher = harder, up to a point) | PR timeline |

Anti-signals to exclude or discount: bot accounts, auto-generated/lockfile diffs, mass-rename PRs.

## Plan for the 90 min

| min | step |
|---|---|
| 0–10 | Write impact definition (README §above → final wording). Decide weights. |
| 10–35 | `scripts/fetch.py`: GraphQL, merged PRs since 2026-06-17 with files, reviews, labels, linked issues → `data/prs.json` |
| 35–60 | `scripts/analyze.py`: per-author signals, normalize, weighted score → `data/scores.json` |
| 60–85 | `dashboard/index.html`: single file, Chart.js from CDN, data inlined. Top-5 cards + why, weight sliders, signal breakdown. |
| 85–90 | Host. Record timer. `/export` session → `docs/agent-session.md`, commit. |

## Hosting

Repo stays private, so GitHub Pages is out on the free plan. Cheapest paths for a single static file:
`npx netlify-cli deploy --prod --dir dashboard` or `npx wrangler pages deploy dashboard`
(both need a one-time login), or a throwaway *public* `weave-dashboard` repo with just `index.html`
on Pages.

## Timer log

| started | stopped | elapsed |
|---|---|---|
| | | |
