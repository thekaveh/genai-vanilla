# Troubleshooting

Common startup problems and their fixes. If you hit something not covered here, open an issue.

## "Refusing to run as root"

```
start.sh: refusing to run as root.
```

You ran `sudo ./start.sh` (or `sudo sh start.sh`). The wizard runs as your user — only `/etc/hosts` editing needs root, and `--setup-hosts` handles that internally with its own `sudo` prompt for that single write.

**Fix:** drop the `sudo`:

```bash
./start.sh              # normal use
./start.sh --setup-hosts # if you want host entries set up up front
```

## Recovering from a prior `sudo ./start.sh`

If you ran the script under `sudo` on a version before the guard landed, root will own files the next non-sudo run can't overwrite. Symptoms:

```
error: Project virtual environment directory `.../bootstrapper/.venv` cannot be used because it is not a valid Python environment (no Python executable was found)
```

or:

```
Failed to write Kong configuration: [Errno 13] Permission denied: '.../volumes/api/kong-dynamic.yml'
```

**Find every root-owned file in the tree:**

```bash
find . -uid 0 -not -path './.git/*'
```

**Take ownership back:**

```bash
sudo chown -R "$(whoami):staff" volumes bootstrapper
```

On Linux substitute `staff` with your primary group (e.g. `$(id -gn)`).

**Then nuke the broken venv** (uv will recreate it on the next run):

```bash
rm -rf bootstrapper/.venv
```

**Re-launch normally** (no sudo):

```bash
./start.sh
```

## "Permission denied" writing `kong-dynamic.yml`

Same root cause as above. `volumes/api/kong-dynamic.yml` is regenerated at every startup, so it can also be safely deleted:

```bash
sudo rm -f volumes/api/kong-dynamic.yml
```

## Apache Airflow build fails with `ResolutionImpossible`

```
ERROR: Cannot install apache-airflow-providers-amazon>=9.30.0 because these package versions have conflicting dependencies.
The user requested apache-airflow-providers-amazon>=9.30.0
The user requested (constraint) apache-airflow-providers-amazon==9.29.0
```

The pin in `services/airflow/build/requirements.txt` was above the floor the upstream Airflow constraints file allows. The pin has been relaxed to `>=9.29.0` on main; pull the latest:

```bash
git checkout main && git pull
```

Then re-run:

```bash
./start.sh
```

## n8n container restart-loops with `Command start not found`

The n8n data volume is corrupted (usually after an interrupted upgrade). Wipe just that one volume rather than the whole stack:

```bash
docker volume rm atlas-n8n-data
./start.sh
```

## Cold start when things just won't reconcile

When in doubt:

```bash
./stop.sh --cold   # remove all containers + volumes
./start.sh         # rebuild from scratch
```

This is destructive (drops all stack data — including any Supabase DB content, model selections, n8n workflows) so use it as a last resort.
