# Sprint 003 blueprint — Scoped rankings and research prediction foundation

## Ranking views
Load the canonical official Division I ordering first. Assign subdivision and conference counters in that order, then apply subdivision, conference, and team-search filters. The production ranking score and combined D-I order remain unchanged.

## Hybrid core
Use shrunk current-season offense/defense profiles:
- offense = (points scored + kappa * season mean team points) / (games + kappa)
- defense = (points allowed + kappa * season mean team points) / (games + kappa)
- home base = (home offense + away defense) / 2
- away base = (away offense + home defense) / 2
- hybrid margin = 0.40 * rank-gap margin + 0.60 * offense/defense margin
- projected total comes from the offense/defense matchup.

The initial reproducible kappa is 3 pseudo-games. This is a research configuration, not an official predictor change.

## Shadow ledger
Store research rows in research_prediction_snapshots, separate from prediction_snapshots. A research row may lock only if it was created no later than kickoff. Run research locking before provider access. Catch research failures so they cannot block the official worker.

## Score rendering
Keep continuous scores for evaluation. If either score is negative, translate both upward equally until the lower score is zero. For display, round half-up and prevent a displayed tie when the continuous margin is non-zero.

## Context variants
Larry context constants are implemented only in research:
- stadium A/B/C/D/F = +7/+5/+3/+1/+0 to the true home team;
- neutral site removes stadium points;
- time-zone travel = -7 per crossing to the traveling team, with capped variants available for evaluation;
- meaningful altitude disadvantage = -7 to the affected traveler;
- rain/snow = -7 to each offense.

Conference-relative stadium grades use current-season season-ticket sell-through inputs. Missing sell-through stays missing/neutral. Attendance and stadium capacity are not substitutes.

Dynamic venue/weather/ticket data ingestion is a follow-up gate: no context-adjusted shadow row should lock until its feature values are captured pre-kickoff with provenance.
