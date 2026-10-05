# Sprint 003 handoff prompt — Context data gates

Continue from v0.10.0 without changing division_i_weighted_v5 or rank_gap_v3.

The scoped ranking views, hybrid_core_v1 shadow ledger, score-normalization rules, metrics, and research context engine are already implemented. The remaining work is data provenance and feature capture.

Add static venue/team time-zone and elevation data, current-season season-ticket sell-through snapshots, and pregame weather forecast snapshots. Every dynamic value used by a locked shadow prediction must have an as-of time no later than kickoff and a source/provenance field. Do not substitute attendance or stadium capacity for season-ticket sell-through. Keep missing data neutral and explicit.

Only after those data gates have tests should the worker create context-adjusted shadow variants. Official Game Book predictions remain rank_gap_v3.
