# Permissions

v0.4.0 is a read-only public website. There are no public write actions, user accounts, or administrative web permissions.

Operational writes occur only through the server-side worker and PostgreSQL connection. Secrets live in `/volume1/rankings/.env` on the NAS and are not exposed through the application.
