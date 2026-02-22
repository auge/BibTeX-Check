#/usr/bin/env bash

set -e

uv venv venv --allow-existing
. venv/bin/activate
uv pip install pre-commit
uv run pre-commit run --all-files
