from pathlib import Path


def test_release_owned_environment_migration_preflights_duplicate_release_rows() -> None:
    migration = Path(
        "alembic/versions/0012_release_owned_environment.py"
    ).read_text(encoding="utf-8")

    preflight_index = migration.index("def _raise_if_duplicate_release_test_runs")
    constraint_index = migration.index("op.create_unique_constraint")

    assert preflight_index < constraint_index
    assert "GROUP BY service_id, environment, test_run_id" in migration
    assert "HAVING COUNT(*) > 1" in migration
    assert "Duplicate release rows block upgrade" in migration
    assert "delete or re-register" in migration
