# Risks

- CFBD availability, endpoint behavior, and quotas are external dependencies.
- A postponed/canceled game may prevent automatic week-complete detection if the provider leaves it incomplete; manual operational handling may be needed.
- Team naming/classification corrections from the source can require reconciliation against bundled snapshots.
- Early-season score prediction calibration has a small sample and should be interpreted accordingly.
- Official prediction accuracy only becomes meaningful after the deployed service has actually created pregame predictions.
- Synology reverse-proxy/TLS configuration is outside the container and must be configured in DSM if public HTTPS access is desired.
