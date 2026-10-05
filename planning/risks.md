# Risks

- CFBD availability, endpoint behavior, and quotas are external dependencies.
- A postponed/canceled game may prevent automatic week-complete detection if the provider leaves it incomplete; manual operational handling may be needed.
- Team naming/classification corrections from the source can require reconciliation against bundled snapshots.
- Early-season score prediction calibration has a small sample and should be interpreted accordingly.
- Official prediction accuracy only becomes meaningful after the deployed service has actually created pregame predictions.
- Synology reverse-proxy/TLS configuration is outside the container and must be configured in DSM if public HTTPS access is desired.

- Manual score entry is an operational override of provider data. Incorrect manual finals can freeze a week with incorrect inputs, so the score desk is admin-only, audited, and blocked after the week snapshot is frozen.
- The manual score desk uses HTTP Basic credentials from `.env`; production access should remain behind HTTPS, and the admin password must be protected like the CFBD/database secrets.


- Research context features can leak postgame information if weather, ticket, venue, or other dynamic values are captured after kickoff. Context-adjusted shadow predictions must use immutable pre-kickoff feature snapshots with provenance.
- Season-ticket sell-through is not available from one standardized source for every Division I program. Missing values must remain explicit and neutral; attendance or stadium capacity must not be substituted silently.
- Large fixed travel/context constants can overfit or overstate real effects. Larry-rule variants should be compared against capped/fitted ablations on the same locked games before any promotion decision.
