# Synology deployment

## Required NAS software
- Synology Container Manager
- SSH access for installation/update
- outbound HTTPS access to GitHub, Python package indexes during image build, and CollegeFootballData

## Paths

```text
/volume1/rankings/.env
/volume1/rankings/app
/volume1/rankings/postgres
/volume1/rankings/backups
```

## Install

```bash
sudo -i
curl -fsSL https://raw.githubusercontent.com/larrybillinger/NCAA_BCS_RANKING_CALCULATOR/main/scripts/synology-install.sh -o /tmp/install-rankings.sh
sh /tmp/install-rankings.sh
```

Default port: `8765`.

The installer also generates a manual score-desk credential in `/volume1/rankings/.env`. Retrieve it as root with:

```bash
grep '^ADMIN_' /volume1/rankings/.env
```

The protected score desk is available at `/admin/games`. Use it through the HTTPS reverse-proxy hostname, not a public unencrypted HTTP connection.

## Container Manager project
After the SSH install, Container Manager will show the Compose project named `ncaa-rankings` with `db`, `web`, and `worker` services.

## Reverse proxy
For public HTTPS, create a DSM reverse proxy from the chosen hostname to:

```text
http://127.0.0.1:8765
```

Use a DSM-managed certificate for the public hostname. No public port needs to be exposed directly from the container if DSM reverse proxy is used.

## Update

```bash
sudo sh /volume1/rankings/app/scripts/synology-update.sh
```

For an older install that does not yet have admin credentials, the updater adds `ADMIN_USERNAME=admin` and generates a random `ADMIN_PASSWORD` once. Future updates preserve the same credential.

## Logs

```bash
cd /volume1/rankings/app
docker compose --env-file /volume1/rankings/.env logs -f web
docker compose --env-file /volume1/rankings/.env logs -f worker
```
