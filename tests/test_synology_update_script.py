from pathlib import Path
import subprocess


SCRIPT_PATH = Path("scripts/synology-update.sh")


def _script() -> str:
    return SCRIPT_PATH.read_text(encoding="utf-8")


def test_synology_update_script_has_valid_shell_syntax():
    subprocess.run(["sh", "-n", str(SCRIPT_PATH)], check=True)


def test_updater_pins_a_stable_compose_project_name():
    script = _script()
    assert 'COMPOSE_PROJECT="ncaa-rankings"' in script
    assert 'docker compose -p "$COMPOSE_PROJECT"' in script
    assert 'docker-compose -p "$COMPOSE_PROJECT"' in script


def test_legacy_database_is_backed_up_before_container_migration():
    script = _script()
    backup = script.index('echo "Backing up PostgreSQL..."')
    migration = script.index('echo "Migrating containers to stable Compose project')
    assert backup < migration
    assert 'docker exec "$DB_CONTAINER" sh -c' in script
    assert 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' in script


def test_container_migration_preserves_bind_mounted_postgres_data():
    script = _script()
    assert '/volume1/rankings/postgres:/var/lib/postgresql/data' in script
    assert 'remove_container_if_present "$WORKER_CONTAINER"' in script
    assert 'remove_container_if_present "$WEB_CONTAINER"' in script
    assert 'remove_container_if_present "$DB_CONTAINER"' in script
    assert 'rm -rf "$ROOT/postgres"' not in script
    assert 'docker volume rm' not in script


def test_updater_waits_for_recreated_postgres_before_repair():
    script = _script()
    start = script.index('compose --env-file "$ENV_FILE" up -d db', script.index('Migrating containers'))
    ready = script.index('wait_for_postgres', start)
    repair = script.index('python -m ncaa_rankings.web.repair_team_identity --apply', ready)
    assert start < ready < repair
