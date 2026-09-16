Dashboard: https://iamsorenl.github.io/posthog-impact-dashboard/
Source: https://github.com/iamsorenl/posthog-impact-dashboard

## Where I started

The interesting work in this assignment is the definition, not the dashboard, so I spent the first stretch deciding what to throw away.

The test I applied to every available signal was the same one: if I weighted this, what behaviour would it reward, and is that the behaviour I actually want? Lines changed rewards verbosity and punishes deletion, though deletion is often the better pull request. Commit count measures commit hygiene habits. Files touched rewards sprawl and punishes focus. Time to merge mostly measures reviewer availability and timezone overlap rather than anything about the author. Pull request count rewards splitting work into smaller pieces, which is a formatting choice, not a contribution.

Every one of them had an obvious way to score well without being useful, so every one of them contributes exactly zero to the score. They are still computed and shown on the page, because a reader should be able to see for themselves that a high-volume engineer and a low-volume engineer can land in nearly the same place. Hiding the volume numbers would turn the argument into an assertion.

What survived had to pass a different test: would an engineering leader who knows this team recognise the person it ranks highly? That question pointed at four things, each measuring a different kind of contribution so that they do not collapse into one another.

## What I ended up measuring

**Review leverage** is the largest component. It asks how many different teammates you actually unblocked, and how substantively. Reviewing one person fifty times is a different contribution from reviewing fifty people once, so it counts distinct people rather than review volume. A bare approval scores nothing at all and does not count as unblocking anyone, because a rubber stamp is not review work. This is the pillar that catches the senior engineer whose main output is other people's velocity, which is precisely the contribution that volume metrics erase.

**Blast radius** asks whether your work lands where other people work. A file that many engineers change is a shared surface, and touching it means your decisions constrain theirs. A large change in an isolated corner scores near zero here, while a small change in a heavily shared path scores high. The point is to separate consequence from size.

**Reviewed throughput** measures what you shipped, weighted not by how big it was but by how much human scrutiny it drew. The reasoning is that the organisation's own attention is a better proxy for consequence than diff size: a large pull request nobody read is less consequential than a small one several engineers argued over. I named this pillar for what it actually measures rather than what I wanted it to measure. It correlates strongly with raw output, so calling it "consequential shipping", as I did in an earlier draft, would have been overclaiming.

**Work mix** is the smallest component and credits the person carrying the unglamorous load: the share of work that is fixes and performance rather than features, plus the breadth of work types covered. Feature-count framing systematically misses the person quietly keeping production healthy.

Each of these is converted into a percentile within the cohort of eligible contributors before being combined, so a score reads as "higher than this share of your peers on this dimension" rather than as an arbitrary point total. Percentiles are also bounded and resistant to outliers, which matters in a repository where one engineer's raw output is several times anyone else's.

## The thing I did not expect to find

Partway through I chased a number that looked wrong: one account had merged more than a hundred pull requests in a single day. That turned out not to be a bug.

PostHog has largely automated its own code review. Roughly a third of merged pull requests carry a label whose own description reads "Request AI approval (no full review)", meaning the author asked a bot to approve rather than waiting for a human. Most review activity in the repository is now performed by bots, and the single highest-volume reviewer is an automated approver rather than a person.

This reframed the whole exercise. It is not a data-cleanliness footnote. It means every conventional engineering metric in this repository now moves with automation rather than with engineering, and it quietly changes what the word "reviewed" means, since a substantial share of merged work never met a human reviewer. I think this is the most useful thing in the submission, more than the ranking itself, because it is specific to how this team works right now and it is not something a leader would necessarily know.

It also forced a real correction in my own method. I had been treating review comments and threads as a measure of scrutiny without filtering who wrote them. Because AI reviewers comment roughly in proportion to how large a diff is, lines of code had been quietly re-entering the model through the very pillar I had built to replace it. I rewrote that measure to count only human reviewers and human comments.

I also got the finding itself wrong the first time, reading the label as marking AI-authored pull requests rather than AI-approved ones, and inflating it by combining it with a second label that means close to the opposite. An independent verification pass against the label API caught it. The corrected reading is what the dashboard now shows, and the mistake is documented on the page rather than quietly removed.

## Getting the data right

The window is the full ninety days and the data is complete rather than sampled. The GitHub search API caps any single query at a thousand results, which is well below this repository's volume, so I fetched day by day and asserted after each day that the number of records returned matched the number the API said existed. Every day in the window matched with no gaps and no mismatches.

File-level data came from a treeless clone of the repository and its commit history rather than from the API. Asking the API which files each pull request touched would have meant tens of thousands of extra calls and would have silently truncated the largest changes, whereas the git history gives the complete picture in one pass at no API cost. I joined that history back to pull request authorship through the reference that PostHog's squash-merge commits carry.

A second pass backfilled every pull request whose review history exceeded what a single API page returns, so nothing is truncated at the edges. That pass is the reason the human-versus-bot analysis above is possible at all.

## Making it checkable rather than impressive

The brief warns against numbers a reader cannot interrogate, and I treated that as the main design constraint.

The page is a single self-contained HTML file with the data inlined, no framework and no build step, which is also why it loads in a fraction of a second. It opens with repository-level context before it names any individual: overall merge volume, how long work takes to get reviewed, how much of the review load is human, and the balance of fixes to features. A leader sees the system before they see people, which is the framing the research on this actually supports, and it shows the baseline that every percentile is measured against.

Every pillar, every score and every piece of jargon on the page is clickable. One click gives a plain sentence explaining what the number means, the real formula, and that engineer's own inputs substituted into it, so the answer to "why is this person's number what it is" never requires reading a methodology essay. The formulas are read directly from the scoring output rather than written into the page by hand, so the explanation cannot drift away from the calculation.

Each of the top five carries a generated line naming what that person actually owns and their strongest supporting fact, including the unflattering one where it applies. The top-ranked engineer's own card states that the large majority of the reviews he gave were bare approvals. I would rather a reader meet the weakest part of a result immediately than discover it and conclude I had hidden it.

## Judgment calls I made deliberately

The highest-output engineer in the repository ends up ranked first, which invites the objection that this is just a volume metric in disguise. I tried three separate times to change the model so that he would not be, and rejected all three, because in each case I had chosen the change for its effect on one person rather than on its merits. Independent review called that out and was right to. Even excluding every AI-approved pull request, his human-reviewed output is several times larger than anyone else's, so the ranking is defensible. Where he does score poorly is review leverage, and his card says so.

One sub-metric was deleted rather than tuned, after I checked how much it actually discriminated and found that nearly every active engineer scored almost the same on it. It was measuring presence in the codebase rather than impact while carrying a meaningful share of the total score, so removing it was more honest than reweighting it.

## What it cannot see, stated on the page rather than buried

Glue work is invisible here: design documents, mentoring, incident response, the support rotation, and the conversations that stop bad work from being started. Long-cycle work that lands as a single large change is undercounted. There is a structural penalty for greenfield work, since a blast-radius measure necessarily rewards crowded files, so an engineer alone in a new product area scores low by construction. New joiners are disadvantaged by percentile scoring over a fixed window.

Most importantly, the composite still tracks raw output more closely than I would like, even with volume weighted at zero, because percentiles of per-pull-request sums partly encode how many pull requests there were. Filtering automation out of the scrutiny measure reduced that substantially but did not eliminate it. That is disclosed on the page itself rather than in a footnote.

There is also a broader point I did not want to skate past. The research on developer productivity is consistent that ranking individuals on delivery telemetry is unsound, and that most variation belongs to the system rather than the person inside it. I was asked to produce a ranking and I produced one, but the page is built to be argued with: every score opens into the specific pull requests, files and people behind it, so a leader can check it against what they already know rather than take it on faith.
