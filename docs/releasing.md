# Releasing

Releases publish to PyPI via **OIDC Trusted Publishing** (no API-token secret).
Publishing a GitHub Release triggers `.github/workflows/release.yml`: a `build`
job (`uv build` + `uvx twine check`) and a `publish` job
(`pypa/gh-action-pypi-publish`, `environment: pypi`, `permissions: id-token: write`).

!!! note "No test CI on GitHub"
    There is deliberately **no test CI** on GitHub. The test suite runs only
    locally via `ci/local-ci.sh`. The release and docs workflows build, check and
    publish — they do not run the tests.

## Version source

The version lives in **one** place: `sdata/__init__.py` → `__version__`.
`setup.py` reads it from there; `pyproject.toml` carries no version.

## Dry run (TestPyPI)

```bash
gh workflow run release-testpypi.yml
gh run watch
```

## Release (production PyPI)

```bash
# 1. bump __version__ in sdata/__init__.py, commit, push
git commit -am "release: vX.Y.Z" && git push

# 2. create the GitHub Release + tag -> triggers release.yml
gh release create vX.Y.Z --title vX.Y.Z --generate-notes
gh run watch
```

The full procedure (including the one-time PyPI/TestPyPI Trusted-Publisher setup)
is documented in [`RELEASING.md`](https://github.com/lepy/sdata/blob/master/RELEASING.md).
