# Sprint 004 requirements — Dynamic context snapshots

## Goal
Populate the dynamic and neutral-site context data required to evaluate context-adjusted shadow predictions without changing the official predictor.

## In scope
- resolve neutral-site venue time zone and elevation when the venue is not either participant's normal home venue;
- store current-season season-ticket sell-through snapshots with source, as-of time, numerator, and offered-inventory denominator when available;
- assign conference-relative A/B/C/D/F stadium grades from sell-through only;
- store pregame weather forecast snapshots with source and as-of time;
- create context-adjusted shadow variants only from feature snapshots captured before kickoff;
- compare Larry-rule, capped/fitted, and single-factor variants on the same locked games.

## Out of scope
- changing division_i_weighted_v5;
- changing rank_gap_v3;
- using attendance or stadium capacity as a substitute for season-ticket sell-through;
- using observed post-kickoff weather as a pregame feature;
- promoting a context model to the official Game Book without a separate explicit decision.
