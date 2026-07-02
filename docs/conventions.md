# Contributor conventions

Working agreements for the sdata codebase. They resolve the inconsistencies flagged
in [RFC 0008](rfc/0008-bestandsaufnahme-roadmap.md) (Paket C) and apply to **new and
touched** code — not as a big-bang rewrite, but whenever a file is edited.

## Language (RFC 0008 C2)

sdata targets an international open-science audience, so **code and user-facing text
are English**; German remains the working language for design discussion.

| Artifact | Language |
|----------|----------|
| Identifiers (modules, classes, functions, variables) | **English** |
| Docstrings (public API) | **English** |
| User-facing docs (`README`, `docs/usage/*`, API reference) | **English** |
| Inline code comments | **English** (state a constraint, not a translation) |
| RFCs / design documents (`docs/rfc/*`) | **German** (the working language) — allowed |
| Commit messages / PR descriptions | **German** — allowed (match the existing history) |

**When you touch a file with German docstrings/comments, migrate the parts you
touch to English.** Don't rewrite untouched code just to translate it — that churns
history without changing behaviour. A known data bug from mixed language (a German
topology-class value that failed to resolve) was fixed in RFC 0008 A6; new
domain/ontology **values** must use the English canonical terms.

## Type annotations (RFC 0008 C3)

New and touched code carries **type annotations** — at minimum a return type and
typed parameters on every public function/method.

* **New modules:** fully annotated.
* **Touched functions:** annotate the signature you edit (don't leave a half-typed
  file, but don't annotate untouched neighbours just to be thorough).
* **Priority modules:** `sdata/dtypes.py` (the dtype single-source) and
  `sdata/metadata.py` had almost no return annotations (RFC 0008 §4). Their public
  API is being annotated incrementally — `dtypes` public functions and the
  high-traffic `Metadata`/`Attribute` methods first.
* There is **no** `mypy` gate in CI yet; annotations are documentation and IDE
  support. Keep them correct even though nothing type-checks them — a wrong
  annotation is worse than none.

## Error policy (RFC 0008 C4)

sdata coerces values by dtype (`sdata.dtypes`). The default is **lenient**: an
invalid value is logged and left unchanged rather than raising. Pass **`strict=True`**
(e.g. `metadata.add(..., strict=True)`, `Attribute(..., strict=True)`) to raise
`DtypeError` instead.

* **Library code** should not silently swallow errors beyond this documented lenient
  path; prefer a clear exception or a logged warning with context.
* Making `strict=True` the **default** is a candidate for the next major (2.0) — it
  is a behaviour change and belongs in a release that may break callers.

## Scope

These conventions are additive guidance; they do not change any runtime behaviour.
