Dashboard: https://iamsorenl.github.io/posthog-impact-dashboard/
Source: https://github.com/iamsorenl/posthog-impact-dashboard

## Where I started

The interesting work in this assignment is the definition, not the dashboard, so I spent the first stretch deciding what to throw away.

The test I applied to every signal was the same: if I weighted this, what behaviour would it reward, and is that what I want? Lines changed rewards verbosity and punishes deletion, though deletion is often the better pull request. Commit count measures commit hygiene. Files touched rewards sprawl and punishes focus. Time to merge measures reviewer availability and timezone overlap, not the author. Pull request count rewards splitting work up, which is a formatting choice, not a contribution.

Every one had an obvious way to score well without being useful, so every one contributes exactly zero. They are still shown on the page, because a reader should be able to see for themselves that a high-volume and a low-volume engineer can land in nearly the same place. Hiding them would turn the argument into an assertion.

What survived had to pass a different test: would an engineering leader who knows this team recognise the person it ranks highly? That question pointed at four things, each measuring a different kind of contribution so that they do not collapse into one another.

## What I ended up measuring

**Review leverage** is the largest component. It asks how many different teammates you unblocked, and how substantively. Reviewing one person fifty times differs from reviewing fifty people once, so it counts distinct people, not review volume. A bare approval scores nothing and does not count as unblocking anyone, because a rubber stamp is not review work. This catches the senior engineer whose main output is other people's velocity, the contribution volume metrics erase.

**Blast radius** asks whether your work lands where other people work. A file that many engineers change is a shared surface, and touching it means your decisions constrain theirs. A large change in an isolated corner scores near zero here, while a small change in a heavily shared path scores high. The point is to separate consequence from size.

**Reviewed throughput** measures what you shipped, weighted not by how big it was but by how much human scrutiny it drew. The reasoning is that the organisation's own attention is a better proxy for consequence than diff size: a large pull request nobody read is less consequential than a small one several engineers argued over. I named this pillar for what it actually measures rather than what I wanted it to measure. It correlates strongly with raw output, so calling it "consequential shipping", as I did in an earlier draft, would have been overclaiming.

**Work mix** is the smallest component and credits the person carrying the unglamorous load: the share of work that is fixes and performance rather than features, plus the breadth of work types covered. Feature-count framing systematically misses the person quietly keeping production healthy.

Each is converted into a percentile within the eligible cohort before being combined, so a score reads as "higher than this share of your peers" rather than an arbitrary point total. Percentiles are also bounded and outlier-resistant, which matters where one engineer's raw output is several times anyone else's.

## The thing I did not expect to find

Partway through I chased a number that looked wrong: one account had merged more than a hundred pull requests in a single day. That turned out not to be a bug.

PostHog has largely automated its own code review. Roughly a third of merged pull requests carry a label whose own description reads "Request AI approval (no full review)", meaning the author asked a bot to approve rather than waiting for a human. Most review activity in the repository is now performed by bots, and the single highest-volume reviewer is an automated approver rather than a person.

This reframed the exercise. It is not a data-cleanliness footnote: every conventional engineering metric here now moves with automation rather than engineering, and it changes what "reviewed" means, since much merged work never met a human reviewer. I think it is the most useful thing in the submission, more than the ranking, because it is specific to how this team works now and not something a leader would necessarily know.

It also forced a real correction in my own method. I had been treating review comments and threads as a measure of scrutiny without filtering who wrote them. Because AI reviewers comment roughly in proportion to how large a diff is, lines of code had been quietly re-entering the model through the very pillar I had built to replace it. I rewrote that measure to count only human reviewers and human comments.

I got the finding itself wrong at first, reading the label as marking AI-authored pull requests rather than AI-approved ones, and inflating it by combining it with a second label meaning close to the opposite. An independent verification pass caught it. The corrected reading is what the dashboard shows, and the mistake is documented on the page rather than quietly removed.

## Getting the data right

The window is the full ninety days and the data is complete rather than sampled. The GitHub search API caps any single query at a thousand results, which is well below this repository's volume, so I fetched day by day and asserted after each day that the number of records returned matched the number the API said existed. Every day in the window matched with no gaps and no mismatches.

File-level data came from a treeless clone and its commit history rather than the API. Asking the API which files each pull request touched would have meant tens of thousands of extra calls and silently truncated the largest changes, whereas git gives the complete picture in one pass at no API cost. I joined that history back to authorship through the reference PostHog's squash-merge commits carry.

A second pass backfilled every pull request whose review history exceeded one API page, so nothing is truncated at the edges. That pass is what makes the human-versus-bot analysis above possible.

## Making it checkable rather than impressive

The brief warns against numbers a reader cannot interrogate, and I treated that as the main design constraint. The page is a single self-contained HTML file with the data inlined, no framework and no build step, which is why it loads in a fraction of a second. It opens with repository-level context before naming any individual: merge volume, how long work waits for review, how much of the review load is human, and the balance of fixes to features. A leader sees the system before the people, which is the framing the research supports, and it shows the baseline every percentile is measured against.

Every pillar, score and piece of jargon is clickable. One click gives a plain sentence on what the number means, the real formula, and that engineer's own inputs substituted in, so "why is this number what it is" never requires a methodology essay. Formulas are read from the scoring output rather than written by hand, so the explanation cannot drift from the calculation.

Each of the top five carries a generated line naming what that person actually owns and their strongest supporting fact, including the unflattering one where it applies. The top-ranked engineer's own card states that the large majority of the reviews he gave were bare approvals. I would rather a reader meet the weakest part of a result immediately than discover it and conclude I had hidden it.

## Judgment calls I made deliberately

The highest-output engineer ranks first, which invites the objection that this is a volume metric in disguise. I tried three times to change the model so he would not, and rejected all three, because each time I had chosen the change for its effect on one person rather than on its merits. Independent review called that out and was right to. Even excluding every AI-approved pull request his human-reviewed output is several times anyone else's, so the result stands. Where he scores poorly is review leverage, and his card says so.

One sub-metric was deleted rather than tuned, after I checked how much it actually discriminated and found that nearly every active engineer scored almost the same on it. It was measuring presence in the codebase rather than impact while carrying a meaningful share of the total score, so removing it was more honest than reweighting it.

## What it cannot see, stated on the page rather than buried

Glue work is invisible here: design documents, mentoring, incident response, the support rotation, and the conversations that stop bad work from being started. Long-cycle work that lands as a single large change is undercounted. There is a structural penalty for greenfield work, since a blast-radius measure necessarily rewards crowded files, so an engineer alone in a new product area scores low by construction. New joiners are disadvantaged by percentile scoring over a fixed window.

Most importantly, the composite still tracks raw output more closely than I would like even with volume weighted at zero, because percentiles of per-pull-request sums partly encode how many there were. Filtering automation out of the scrutiny measure reduced that but did not eliminate it. It is disclosed on the page, not in a footnote.

There is also a broader point I did not want to skate past. The research on developer productivity is consistent that ranking individuals on delivery telemetry is unsound, and that most variation belongs to the system rather than the person inside it. I was asked to produce a ranking and I produced one, but the page is built to be argued with: every score opens into the specific pull requests, files and people behind it, so a leader can check it against what they already know rather than take it on faith.
