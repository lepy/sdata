# Lokale CI/Tests für sdata — bewusst OHNE GitHub Actions / Online-CI.
#
#   make ci        # komplette lokale CI: venv anlegen, installieren, alle Tests + Coverage
#   make did-test  # nur die DID-Tests
#   make test      # alle Tests (setzt eine via `make ci` eingerichtete venv voraus)
#   make clean-ci  # venv + Coverage-Artefakte entfernen
.PHONY: ci test did-test clean-ci help

VENV ?= .venv-ci
PYBIN := $(VENV)/bin/python

help:
	@grep -E '^[a-zA-Z0-9_-]+:.*#' $(MAKEFILE_LIST) | sed 's/:.*#/\t-/'

ci: ## komplette lokale CI (venv, install, alle Tests + Coverage)
	./ci/local-ci.sh

did-test: ## nur die DID-Tests
	./ci/local-ci.sh tests/test_did.py -q

test: ## alle Tests (benötigt eingerichtete venv aus `make ci`)
	$(PYBIN) -m pytest tests/

clean-ci: ## venv + Coverage-Artefakte entfernen
	rm -rf $(VENV) .coverage

# --- leporis-docs: 1.6.0 -------------------------------------
# Von /leporis-docs:init eingefügt. Port ist repo-fest vergeben (politik.json).
DOCS_PORT ?= 9285
DOCS_HOST ?= 127.0.0.1
# Repo mit pyproject.toml:  uv run mkdocs
# Repo ohne (reines Doku-Repo, Stufe 0):  uvx --with mkdocs-material mkdocs
MKDOCS    ?= uv run mkdocs

.PHONY: docs mkdocs_serve docs-offline-check

docs:  ## Doku statisch bauen (--strict; bricht bei Warnungen ab)
	$(MKDOCS) build --strict

mkdocs_serve:  ## Doku lokal servieren auf $(DOCS_HOST):$(DOCS_PORT)
	$(MKDOCS) serve --dev-addr $(DOCS_HOST):$(DOCS_PORT)

docs-offline-check: docs  ## Bricht ab, wenn die gebaute Site etwas aus dem Netz lädt
	python3 scripts/check_offline.py site

# --- Ende leporis-docs ------------------------------------------------------
