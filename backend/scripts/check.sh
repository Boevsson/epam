#!/usr/bin/env sh
# One quality gate for local runs, Docker and CI: lint, format, types, architecture rules, tests.
# Extra arguments are passed to pytest, e.g. `sh scripts/check.sh -k fusion`.
set -eu

echo "--> ruff check" && ruff check .
echo "--> ruff format --check" && ruff format --check .
echo "--> mypy (strict)" && mypy
echo "--> import-linter (architecture rules)" && lint-imports
echo "--> pytest" && pytest "$@"
