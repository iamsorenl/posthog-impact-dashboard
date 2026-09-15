# Weave take-home — Engineering Impact Dashboard

Private. Prompt: `takehome-prompt.pdf` (assessment `asmt_eD1bGr5o2Ea75Z0p0gnhglFW`, received 2026-09-15).

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

## Deliverables (their list)

1. A written definition of "impact" for software engineers.
2. Data pulled from PostHog/posthog covering ≥ 90 days.
3. Analysis.
4. Interactive dashboard: top 5 + why.
5. Hosted URL.

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
| 85–90 | Host. Record timer. |

## Hosting

Repo stays private, so GitHub Pages is out on the free plan. Cheapest paths for a single static file:
`npx netlify-cli deploy --prod --dir dashboard` or `npx wrangler pages deploy dashboard`
(both need a one-time login), or a throwaway *public* `weave-dashboard` repo with just `index.html`
on Pages.

## Timer log

| started | stopped | elapsed |
|---|---|---|
| | | |
