# Sprint 002 handoff prompt — Manual score desk

Implement the approved manual score desk without changing ranking or prediction formulas. Read AGENTS.md and all required source-of-truth files first.

Keep the public site read-only. Protect `/admin/games` with environment-backed admin credentials and CSRF protection. Manual overrides take precedence over provider score fields until explicitly released. Do not permit an admin score edit or release after the active production ranking model has frozen that week. Preserve append-only audit history for manual changes.

Use the existing text-first Weekbook visual language. Run the full pytest suite through GitHub Actions and update release/version documentation.
