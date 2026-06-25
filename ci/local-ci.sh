#!/usr/bin/env bash
#
# Lokale CI für sdata — bewusst OHNE GitHub Actions / Online-CI.
#
# Erstellt eine isolierte venv, installiert das Paket inkl. optionalem
# [did]-Extra sowie die Test-Tools und führt die Testsuite mit Coverage aus.
# Es findet KEIN Upload/keine Kommunikation mit externen CI-Diensten statt.
#
# Nutzung:
#   ci/local-ci.sh                          # komplette Suite (tests/)
#   ci/local-ci.sh tests/test_did.py -q     # gezielt; Argumente werden durchgereicht
#   PYTHON=python3.11 ci/local-ci.sh        # anderen Interpreter wählen
#   VENV_DIR=/pfad/zur/venv ci/local-ci.sh  # venv-Ort überschreiben
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"
VENV="${VENV_DIR:-$ROOT/.venv-ci}"
PYBIN="$VENV/bin/python"

if [[ ! -x "$PYBIN" ]]; then
  echo "[ci] erstelle venv: $VENV"
  "$PYTHON" -m venv "$VENV"
fi

echo "[ci] installiere/aktualisiere Abhängigkeiten (sdata[did] + Test-Tools)"
"$PYBIN" -m pip install --quiet --upgrade pip
"$PYBIN" -m pip install --quiet -e ".[did]" pytest coverage

# Testziel: durchgereichte Argumente oder – wenn keine – die komplette Suite.
TARGETS=("$@")
if [[ ${#TARGETS[@]} -eq 0 ]]; then
  TARGETS=(tests/)
fi

echo "[ci] führe Tests aus: ${TARGETS[*]}"
# --continue-on-collection-errors: ein kaputtes Testmodul soll nicht die
# Ausführung aller übrigen Tests verhindern (Fehler werden trotzdem rot gemeldet).
"$PYBIN" -m coverage run -m pytest --continue-on-collection-errors "${TARGETS[@]}"

echo
echo "[ci] Coverage (Produktcode, ohne vendored contrib — siehe pyproject.toml):"
"$PYBIN" -m coverage report || true

echo "[ci] OK"
