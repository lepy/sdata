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
