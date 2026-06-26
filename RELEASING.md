# Releasing sdata

Releases gehen über **OIDC Trusted Publishing** (kein `PYPI_API_TOKEN`-Secret).
Das Veröffentlichen eines GitHub Release löst `.github/workflows/release.yml` aus:
ein `build`-Job (`uv build` + `uvx twine check`) und ein `publish`-Job
(`pypa/gh-action-pypi-publish`, `environment: pypi`, `permissions: id-token: write`).

> Hinweis: Es gibt bewusst **kein** Test-CI auf GitHub. Die Testsuite läuft
> ausschließlich lokal über `ci/local-ci.sh`. Dieser Workflow baut/prüft/lädt nur.

## Versionsquelle

Die Version steht an **einer** Stelle:

- `sdata/__init__.py` → `__version__`

`setup.py` liest sie von dort; `pyproject.toml` enthält keine eigene Version.

## Einmalige Voraussetzung (PyPI-seitig)

Auf PyPI (und für die Generalprobe auf TestPyPI) je einen **Trusted Publisher**
für das Projekt `sdata` registrieren:

| Feld          | Production (pypi.org)        | TestPyPI (test.pypi.org)        |
| ------------- | --------------------------- | ------------------------------- |
| Owner         | `lepy`                      | `lepy`                          |
| Repository    | `sdata`                     | `sdata`                         |
| Workflow      | `release.yml`               | `release-testpypi.yml`          |
| Environment   | `pypi`                      | `testpypi`                      |

## Generalprobe (TestPyPI)

```bash
gh workflow run release-testpypi.yml
gh run watch
```

Lädt den aktuellen `master`-Stand nach test.pypi.org. Installations-Check:

```bash
pip install -i https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ "sdata==X.Y.Z"
```

## Release (Production-PyPI)

```bash
# 1. Version in sdata/__init__.py bumpen, committen, pushen:
git commit -am "release: vX.Y.Z" && git push

# 2. GitHub Release + Tag anlegen -> triggert release.yml:
gh release create vX.Y.Z --title vX.Y.Z --generate-notes
gh run watch
```

Existiert der Tag bereits (z. B. vorab `git tag` gesetzt), erstellt
`gh release create vX.Y.Z` das Release auf dem vorhandenen Tag und löst den
Upload aus.
