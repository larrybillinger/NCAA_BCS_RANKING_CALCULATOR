# Sprint 003 requirements — Scoped rankings and research prediction foundation

## Goal
Add public ranking views and a leakage-safe research prediction path without changing production ranking or official prediction rules.

## In scope
- sequential FBS and FCS ranks derived from the combined Division I national order;
- sequential conference ranks derived from national order, not conference record;
- conference filtering on the ranking page;
- research-only hybrid offense/defense predictor;
- separate research prediction persistence;
- pre-kickoff shadow locking independent of provider availability;
- nonnegative equal-shift score normalization;
- winner-consistent integer score rendering;
- total-score MAE and display-tie metrics;
- research-only context adjustment engine for stadium demand, time-zone travel, altitude, and rain/snow.

## Out of scope
- changing division_i_weighted_v5;
- changing or replacing rank_gap_v3;
- allowing a context adjustment to become an official Game Book prediction;
- using observed postgame weather in a pregame model;
- substituting attendance/capacity for season-ticket sell-through;
- claiming a context model is production-ready before a locked shadow sample exists.

## Data rule
Dynamic context must have a pre-kickoff snapshot and provenance before a locked shadow model may consume it. Missing context remains missing/neutral; it is not inferred from unrelated fields.
