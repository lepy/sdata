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
#   CI_MODE=full ci/local-ci.sh             # zusätzlich: alle Extras, nur Tests
#
# CI_MODE=full installiert alle optionalen Backends (h5py, pint, rdflib, Pillow,
# PyTables, …) in eine eigene venv (.venv-ci-full) und führt die Suite ohne
# Coverage-Bericht aus. Der Modus fängt Tests, die stillschweigend ein fehlendes
# Extra voraussetzen, und Fehler, die nur mit installiertem Backend auftreten.
# Die Coverage misst weiterhin der Basismodus.
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"
CI_MODE="${CI_MODE:-base}"
case "$CI_MODE" in
  base) DEFAULT_VENV="$ROOT/.venv-ci" ;;
  full) DEFAULT_VENV="$ROOT/.venv-ci-full" ;;
  *) echo "[ci] unbekannter CI_MODE: $CI_MODE (base|full)" >&2; exit 2 ;;
esac
VENV="${VENV_DIR:-$DEFAULT_VENV}"
PYBIN="$VENV/bin/python"

if [[ ! -x "$PYBIN" ]]; then
  echo "[ci] erstelle venv: $VENV"
  if ! "$PYTHON" -m venv "$VENV" 2>/dev/null; then
    # z. B. Debian/Ubuntu ohne python3-venv: auf uv ausweichen, falls vorhanden
    if command -v uv >/dev/null 2>&1; then
      rm -rf "$VENV"
      uv venv --seed --python "$PYTHON" "$VENV"
    else
      echo "[ci] venv-Erstellung fehlgeschlagen (python3-venv oder uv installieren)" >&2
      exit 1
    fi
  fi
fi

# Bewusst OHNE [http]: 'requests' ist optional. Das CI validiert den
# urllib-Fallback (Standardbibliothek); das requests-Backend ist über ein
# injiziertes Fake-Modul in tests/test_http_backend.py abgedeckt.
echo "[ci] installiere/aktualisiere Abhängigkeiten (sdata[did,parquet,blob,sql] + Test-Tools)"
"$PYBIN" -m pip install --quiet --upgrade pip
# [sql] (SQLAlchemy) für den SqlWriter-Interop-Test (RFC 0007); [rdf] bewusst NICHT
# installiert — die rdflib-only-Zweige des GraphWriter sind `# pragma: no cover`.
if [[ "$CI_MODE" == full ]]; then
  echo "[ci] CI_MODE=full: zusätzlich alle Extras + Pillow/PyTables"
  "$PYBIN" -m pip install --quiet -e ".[did,http,excel,hdf,sql,parquet,blob,units,rdf,schema]" \
    pillow tables pytest
else
  "$PYBIN" -m pip install --quiet -e ".[did,parquet,blob,sql]" pytest coverage
fi

# Testziel: durchgereichte Argumente oder – wenn keine – die komplette Suite.
TARGETS=("$@")
if [[ ${#TARGETS[@]} -eq 0 ]]; then
  TARGETS=(tests/)
fi

echo "[ci] führe Tests aus: ${TARGETS[*]}"
if [[ "$CI_MODE" == full ]]; then
  "$PYBIN" -m pytest --continue-on-collection-errors -rs "${TARGETS[@]}"
  echo "[ci] OK (full)"
  exit 0
fi
# --continue-on-collection-errors: ein kaputtes Testmodul soll nicht die
# Ausführung aller übrigen Tests verhindern (Fehler werden trotzdem rot gemeldet).
"$PYBIN" -m coverage run -m pytest --continue-on-collection-errors "${TARGETS[@]}"

echo
echo "[ci] Coverage (Produktcode, ohne vendored contrib — siehe pyproject.toml):"
"$PYBIN" -m coverage report || true

echo "[ci] OK"
