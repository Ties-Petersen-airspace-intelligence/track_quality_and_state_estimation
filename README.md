# Project Track Quality and State Estimation

This project investigates how our correlation and fusion services turn aircraft position reports from many sources into one trajectory per aircraft, and where that process goes wrong. 

We are looking at whether a state estimator could do the job better, producing tracks that are smooth, physically plausible and honest about their own uncertainty, especially in the rare cases where today's output shows impossible jumps, false altitudes or the same aircraft twice. 

It is a research effort: we document how the current pipeline behaves, build a replay harness to compare alternatives against it on real data, and work out what a good track actually is.

## Resources

Notion: https://app.notion.com/p/airspaceintelligence/Project-Track-Quality-and-State-Estimation-3d4bd6d804a880afaaeaff451f583474?source=copy_link

Linear: https://linear.app/airspace-intelligence/project/create-state-estimator-mvp-9cc5fe4cbe40/overview

## What is in this repo

- `src/data/case_finder/`: scans a day of production fusion output for things that cannot be true and lets you review and mark the hits as test cases. Its own README explains the rules.
- `src/data/cases/<case>/`: one folder per test case with the raw plots of every source, the production fusion output for the same hour, the SQL that pulled them, and the runs of every strategy on it.
- `src/harness/`: replays a case through a strategy and shows the result next to production in a local viewer. Its README explains the strategy interface and the viewer.

Python is managed with uv. Run things from `src/` with `uv run`.
