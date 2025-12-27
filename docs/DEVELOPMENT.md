# Development

How to run tests and work on RTL-HAOS locally.

## Local dev environment

To set up the project’s isolated pytest virtualenv without running tests (handy for editors/linters and iterative work):

```bash
./scripts/pytest_venv.sh --no-run
source .venv-pytest/bin/activate
```

After activating, you can run tests normally:

```bash
pytest
```

To leave the venv:

```bash
deactivate
```

## Testing

### Unit tests (default)

Run the normal unit test suite (fast, deterministic):

```bash
pytest
```

### Opt-in `rtl_433` integration tests

These tests execute the external `rtl_433` binary and are **skipped by default** (so GitHub Actions / CI stays green).

Run the integration tests:

```bash
RUN_RTL433_TESTS=1 pytest -m integration
```

Run only the replay test:

```bash
RUN_RTL433_TESTS=1 pytest -m integration -k rtl433_replay
```

#### Recording a replay fixture (recommended)

Replay fixtures live in `tests/fixtures/rtl433/` (see `tests/fixtures/rtl433/README.md`). Capture files like `.cu8` are intentionally **gitignored**.

Record a short capture:

```bash
mkdir -p tests/fixtures/rtl433
./scripts/record_rtl433_fixture.sh 433.92M 250k 20 tests/fixtures/rtl433/sample.cu8
```

Sanity-check the capture decodes:

```bash
rtl_433 -r tests/fixtures/rtl433/sample.cu8 -F json | head
```

### Opt-in hardware smoke tests (RTL-SDR required)

These require an RTL-SDR device available to the test host. They do **not** require receiving RF events; they only verify `rtl_433` starts and exits cleanly.

```bash
RUN_HARDWARE_TESTS=1 pytest -m hardware
```

### Run everything locally (unit + integration + hardware)

```bash
RUN_RTL433_TESTS=1 RUN_HARDWARE_TESTS=1 pytest
```

### Script argument guardrails (no hardware)

The fixture-recording script supports unit suffixes and a dry-run mode:

```bash
./scripts/record_rtl433_fixture.sh --dry-run 433.92M 250k 10 tests/fixtures/rtl433/test.cu8
```

If you forget a suffix (e.g. `433.92` instead of `433.92M`, or `250` instead of `250k`), the script will fail fast with a helpful hint.

---

## Deploy to Home Assistant OS (HAOS)

RTL-HAOS can be developed as a **local Home Assistant add-on**. Use the single helper script:

- **`scripts/haos.sh`** — deploy / uninstall / logs / status

It reads the add-on slug from `config.yaml` and deploys to:

- `/addons/local/<slug>` (HAOS local add-ons)

### Prereqs

- A Home Assistant OS machine reachable on your network.
- SSH access into HAOS (commonly via the **Terminal & SSH** add-on).
- Password auth can work, but SSH keys are recommended.

Make it executable once:

```bash
chmod +x scripts/haos.sh
```

### Deploy

Sync repo contents to HAOS:

```bash
./scripts/haos.sh deploy --host homeassistant.local
```

Deploy, rebuild, restart, then print logs:

```bash
./scripts/haos.sh deploy --host 192.168.1.109 --rebuild --restart --logs
```

If you see an error like “Addon … does not exist in the store”, run once in the HA UI:

**Settings → Add-ons → Add-on store → (⋮) Check for updates**

Then install it under **Local add-ons**. After that, CLI rebuild/restart works reliably.

### Logs

```bash
./scripts/haos.sh logs --host 192.168.1.109
./scripts/haos.sh logs --host 192.168.1.109 --follow
```

### Status / Debug

```bash
./scripts/haos.sh status --host 192.168.1.109
```

### Uninstall

Uninstall (if installed) and remove remote add-on folder(s) under `/addons`:

```bash
./scripts/haos.sh uninstall --host 192.168.1.109
```

Also remove the add-on’s optional `/share/<slug>` directory:

```bash
./scripts/haos.sh uninstall --host 192.168.1.109 --rm-share --yes
```

### Optional: sync a local data folder to /share

Mirror a local folder into HAOS `/share/<slug>`:

```bash
./scripts/haos.sh deploy --host 192.168.1.109 --share ./tx_files
```

### Configuration via environment variables

```bash
export HA_HOST=192.168.1.109
export HA_USER=root
export HA_PORT=22
# export HA_KEY=~/.ssh/haos_ed25519   # recommended
./scripts/haos.sh deploy --rebuild --restart --logs
```

