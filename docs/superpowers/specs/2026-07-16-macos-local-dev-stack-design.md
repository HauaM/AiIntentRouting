# macOS Local Development Stack Design

## Goal

Provide a single zsh-based command that starts the complete local development stack on macOS while preserving the functional behavior of `scripts/run_local_dev_stack.sh`. Backend and frontend output must remain distinguishable in one terminal through stable colors and text prefixes.

## User Interface

The entry point is `scripts/run_local_dev_stack_macos.sh` with a `#!/usr/bin/env zsh` shebang. A developer runs it from any directory:

```zsh
./scripts/run_local_dev_stack_macos.sh
```

The script prints backend lines with a cyan `[backend]` prefix and frontend lines with a magenta `[frontend]` prefix. General orchestration messages use `[local]` without a service color. If standard output is not a terminal or `NO_COLOR` is set, ANSI color sequences are disabled while prefixes remain.

`Ctrl+C` stops the backend, frontend, and log follower processes started by the script. It does not stop PostgreSQL or remove its volume.

## Configuration

The script loads `${ROOT_DIR}/.env` automatically when it exists. Values explicitly exported by the caller before starting the script take precedence over values in `.env`; missing values fall back to the same local defaults as the Linux script and `.env.example`.

The default endpoints remain:

- Admin UI: `http://127.0.0.1:30140`
- Backend API: `http://127.0.0.1:30141`
- PostgreSQL: `postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing`

The `.env` file is parsed as shell-compatible zsh assignments. This repository's example values must remain compatible with that contract.

## macOS Runtime Behavior

The script verifies it is running on Darwin and fails with a concise message on other platforms. It requires `uv`, `curl`, `docker`, `lsof`, and either `pnpm` or `corepack`. It also requires Colima for the default Compose-managed database.

For the default database URL, the script:

1. Starts Colima when it is installed but not running.
2. Selects the `colima` Docker context when needed.
3. Resolves Compose as `docker compose` when available, otherwise `docker-compose`.
4. Reuses a healthy project PostgreSQL container or starts it.
5. Detects a conflicting container already publishing host port `30142`.
6. Waits for `pg_isready` before migrations.

For a custom `DATABASE_URL`, Compose and Colima database management are skipped, matching the Linux script's behavior.

## Application Startup

After the database is ready, the script preserves the Linux workflow:

1. Stop stale listeners on backend port `30141` and frontend port `30140`.
2. Stop stale log follower processes created by previous macOS script runs.
3. Run Alembic migrations.
4. Preserve the single-system-admin ownership rule and prepare startup provisioning.
5. Start Uvicorn and wait for `/healthz`.
6. Seed the default Admin UI service when absent.
7. Start the frontend with its API proxy pointed at the backend.
8. Remain attached until either application exits or the user presses `Ctrl+C`.

The script writes raw service output to `var/logs/local-dev-stack/backend.log` and `frontend.log`, then follows both files with colored prefixes. Raw log files do not contain ANSI escape sequences.

## Process and Error Handling

The script records only process IDs it starts. Cleanup is idempotent and signals those processes on normal exit, interruption, or termination. Existing listeners on the configured application ports receive `TERM`, followed by `KILL` only if they remain alive after a bounded wait.

Failures identify the failed prerequisite or phase, including unsupported operating system, unavailable Colima, unavailable Compose, port conflict, PostgreSQL timeout, migration failure, backend readiness failure, and missing frontend package runner.

Secrets are not printed. Database URLs are not echoed in full. The script never deletes Docker volumes or invokes `docker compose down -v`.

## Files

- Create `scripts/run_local_dev_stack_macos.sh` for macOS orchestration.
- Create `tests/unit/test_macos_local_dev_stack_script.py` for static contract and zsh syntax tests.
- Modify `README.md` to make the macOS one-command path the primary macOS workflow while retaining the manual diagnostic workflow.
- Modify `docs/ops/macos-colima-docker-setup.md` to document the new command, colored logs, cleanup, and troubleshooting.

## Verification

Automated verification covers:

- executable zsh shebang and `zsh -n` syntax validation;
- Darwin guard and Colima lifecycle contract;
- Compose command fallback;
- `.env` auto-loading with caller-exported variable precedence;
- port cleanup and child-process cleanup;
- backend/frontend prefixes, exact colors, and `NO_COLOR` behavior;
- database, migration, provisioning, seeding, and frontend proxy workflow markers;
- README and macOS runbook references.

Manual verification runs the script on macOS with Colima and confirms PostgreSQL readiness, backend readiness, Admin UI availability, distinct service colors, successful local-admin login, and clean shutdown with `Ctrl+C`.
