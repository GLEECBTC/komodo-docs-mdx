# KDF Response Harvesting Script - Guide

This document explains what the `utils/py/harvest_responses.sh` script does, its prerequisites, how to run it, and where to find the outputs.

## Prerequisites

- Docker and Docker Compose v2 (script uses `docker compose`).
- A working Python virtual environment located at `utils/py/.venv`.
  - The script activates it automatically with: `source utils/py/.venv/bin/activate`.
- Internet access to pull images and reach external nodes where applicable.

## What the script does (step-by-step)

1. Ensures it is executing from the repository root and validates presence of `docker-compose.yml`.
2. Activates the Python virtual environment at `utils/py/.venv`.
3. Syncs request examples with the latest coin server URLs:
   - `python utils/py/batch_update_nodes.py --directory src/data/requests/kdf`
4. Syncs request examples into the KDF method registries and Postman data:
   - `python utils/py/generate_postman.py --sync-examples --output-dir postman/generated`
5. Sets the KDF branch used by downstream tasks:
   - `export KDF_BRANCH="dev"`
6. Starts KDF services required for harvesting responses (runs in the background):
   - `docker compose up kdf-native-hd kdf-native-nonhd -d`
7. Waits briefly for services to become ready (`sleep 10`).
8. Prepares a clean slate by disabling all enabled coins:
   - `python utils/py/clean_slate.py`
9. Generates Postman collections (across methods and flows):
   - `python utils/py/generate_postman.py --all`
10. Runs sequence-based response harvesting, which also integrates address collection:
    - `cd utils/py && python lib/managers/sequence_responses_manager.py --update-files && cd ../..`
11. Cleans up older Newman reports, keeping only the two most recent reports in `postman/reports/`.
12. Stops the KDF Docker services:
    - `docker compose down`
13. Prints a summary of where results were written.

## How to run

From the repository root:

```bash
bash utils/py/harvest_responses.sh
```

Optional:
- You can override the KDF branch before running, for example:

```bash
export KDF_BRANCH="dev"   # or a different branch if supported by your environment
bash utils/py/harvest_responses.sh
```

## Outputs

- `postman/generated/reports/` — Unified response manager output from the sequence-based harvester.
- `postman/reports/` — Newman run results. The script cleans older reports and keeps the two most recent.
- `src/data/responses/` — Updated response JSON files used by documentation components.
- `src/data/requests/` — Request example JSON files synced and used by components and tooling.

## Troubleshooting

- Virtual environment missing:
  - Ensure the venv exists at `utils/py/.venv` and contains all required dependencies.
  - If needed, recreate the venv and install project requirements per your local setup instructions.
- Docker not available or not running:
  - Ensure Docker Desktop/Engine is installed and running.
  - Confirm `docker compose` is available (Compose v2 CLI).
- Network or node connectivity issues:
  - The batch update and harvesting steps may require external connectivity to nodes.
  - Retry after verifying network access and node availability.
- Port conflicts:
  - If the KDF services fail to start, check for port conflicts and stop/reconfigure competing services.

## Notes

- The script uses `set -e` and will exit on the first error. Check the console output for the failing step.
- The harvesting flow is designed to be reproducible; re-running will update requests/responses and generated artifacts. 

