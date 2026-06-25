# -*- coding: utf-8 -*-
"""``did:github``: DID-Dokumente aus GitHub-Repositories auflösen.

Eine ``did:github``-DID verweist auf ein ``did.json`` in einem GitHub-Repo und
wird über ``raw.githubusercontent.com`` geladen. Formen::

    did:github:<user>:<repo>
    did:github:<user>:<repo>:<ref>
    did:github:<user>:<repo>:<ref>:<subpath>

Im ``subpath`` darf ``__`` als ``/``-Ersatz verwendet werden (CLI-freundlich).
Gesucht werden ``<subpath>/.well-known/did.json``, ``<subpath>/did.json`` sowie
die Repo-Wurzel – in dieser Reihenfolge, für die Refs ``<ref>``, ``main``, ``master``.

Ein optionales ``GITHUB_TOKEN`` (Umgebungsvariable) erhöht das Rate-Limit und
erlaubt Zugriff auf private Repos.

.. note::
   ``did:github`` ist **keine** registrierte W3C-DID-Methode, sondern eine
   pragmatische, projektspezifische Auflösung über GitHub-Rohinhalte.
"""
from __future__ import annotations

import os
import re
import json
import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import List, Optional, Tuple

from ._http import http_get
from .errors import EncodingError, ResolutionError

logger = logging.getLogger(__name__)

__all__ = ["DidGithub", "parse_did_github", "resolve_did_github"]

DID_GITHUB_METHOD = "did:github"
RAW_BASE = "https://raw.githubusercontent.com"
HTTP_TIMEOUT = 10


@dataclass(frozen=True)
class DidGithub:
    """Geparste ``did:github``-Identität."""
    user: str
    repo: str
    ref: Optional[str] = None       # z. B. "main", "master", Tag oder Commit
    subpath: Optional[str] = None   # optionaler Unterordner im Repo

    @property
    def did(self) -> str:
        parts = [DID_GITHUB_METHOD, self.user, self.repo]
        if self.ref:
            parts.append(self.ref)
        if self.subpath:
            parts.append(self.subpath)
        return ":".join(parts)


def make_subpath(raw: Optional[str]) -> Optional[str]:
    """Mappe ``__`` auf ``/`` (echte Slashes bleiben erhalten)."""
    if not raw:
        return None
    return raw.replace("__", "/")


def parse_did_github(did: str) -> DidGithub:
    """Parse eine ``did:github``-DID.

    Raises:
        EncodingError: wenn ``did`` keine gültige ``did:github``-DID ist.
    """
    if not did.startswith(DID_GITHUB_METHOD + ":"):
        raise EncodingError("kein did:github-Identifier")
    parts = did.split(":")
    if len(parts) < 4:
        raise EncodingError("Form: did:github:<user>:<repo>[:<ref>[:<subpath>]]")
    _, _, user, repo, *rest = parts
    ref = rest[0] if rest else None
    subpath = make_subpath(":".join(rest[1:]) if len(rest) > 1 else None)
    return DidGithub(user=user, repo=repo, ref=ref, subpath=subpath)


def candidate_paths(dg: DidGithub) -> List[Tuple[str, str]]:
    """Geordnete ``(ref, path)``-Kandidaten für die Auflösung."""
    well_known, root = ".well-known/did.json", "did.json"
    sub_candidates = []
    if dg.subpath:
        base = dg.subpath.rstrip("/")
        sub_candidates = ["{}/{}".format(base, well_known), "{}/{}".format(base, root)]
    paths = sub_candidates + [well_known, root]
    refs = [r for r in [dg.ref, "main", "master"] if r]
    return [(r, p) for r in refs for p in paths]


def _raw_url(user: str, repo: str, ref: str, path: str) -> str:
    return "{}/{}/{}/{}/{}".format(RAW_BASE, user, repo, ref, path)


def _headers() -> dict:
    headers = {"Accept": "application/json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer {}".format(token)
    return headers


def _strip_json_comments(text: str) -> str:
    """Entferne ``/* … */`` und ``// …`` (rudimentär, für einfache Fälle)."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//.*?$", "", text, flags=re.M)
    return text


@lru_cache(maxsize=256)
def fetch_json(url: str) -> Optional[dict]:
    """Lade JSON von ``url`` (mit kleinem Cache); ``None`` bei Status != 200."""
    status, text = http_get(url, headers=_headers(), timeout=HTTP_TIMEOUT)
    if status != 200:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return json.loads(_strip_json_comments(text))


def resolve_did_github(did: str) -> dict:
    """Löse eine ``did:github``-DID zum DID-Dokument auf.

    Raises:
        EncodingError: bei ungültiger DID.
        ResolutionError: wenn kein gültiges ``did.json`` gefunden wird.
        EncodingError: wenn ein gefundenes Dokument ``@context``/``id`` vermisst.
    """
    dg = parse_did_github(did)
    tried = []
    for ref, path in candidate_paths(dg):
        url = _raw_url(dg.user, dg.repo, ref, path)
        tried.append(url)
        doc = fetch_json(url)
        if doc is None:
            continue
        if "@context" not in doc:
            raise EncodingError("DID-Dokument ohne @context ({})".format(url))
        if "id" not in doc:
            raise EncodingError("DID-Dokument ohne id ({})".format(url))
        logger.debug("did:github aufgelöst via %s", url)
        return doc
    raise ResolutionError(
        "did:github konnte nicht aufgelöst werden. Versucht:\n- " + "\n- ".join(tried))
