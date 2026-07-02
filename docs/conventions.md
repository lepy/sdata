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

## Scope

These conventions are additive guidance; they do not change any runtime behaviour.
Later sections (typing, error policy) are added by RFC 0008 C3/C4.
