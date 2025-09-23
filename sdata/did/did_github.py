from __future__ import annotations

import os
import re
import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional, Tuple, List

import requests


DID_GITHUB_METHOD = "did:github"
RAW_BASE = "https://raw.githubusercontent.com"


@dataclass(frozen=True)
class DidGithub:
    """Interne Repräsentation von did:github Identifiers."""
    user: str
    repo: str
    ref: Optional[str] = None           # z.B. "main", "master", Tag oder Commit
    subpath: Optional[str] = None       # optionaler Unterordner innerhalb des Repos

    @property
    def did(self) -> str:
        parts = [DID_GITHUB_METHOD, self.user, self.repo]
        if self.ref:
            parts.append(self.ref)
        if self.subpath:
            parts.append(self.subpath)
        return ":".join(parts)


def parse_did_github(did: str) -> DidGithub:
    """
    Erwartete Formen:
      - did:github:<user>:<repo>
      - did:github:<user>:<repo>:<ref>
      - did:github:<user>:<repo>:<ref>:<subpath-with-slashes-replaced-by-__>
      - oder mit beliebigen weiteren :... Segmenten → subpath kann Doppelpunkte enthalten,
        wir mappen diese später auf '/'. Praktischer ist unten make_subpath().
    """
    if not did.startswith(DID_GITHUB_METHOD + ":"):
        raise ValueError("Kein did:github Identifier")

    parts = did.split(":")
    if len(parts) < 4:
        raise ValueError("Form: did:github:<user>:<repo>[:<ref>[:<subpath>]]")

    _, _, user, repo, *rest = parts
    ref = rest[0] if rest else None
    subpath = ":".join(rest[1:]) if len(rest) > 1 else None

    # Optionales Mapping: Erlaube __ als Slash-Ersatz im subpath (CLI-freundlich)
    subpath = make_subpath(subpath)
    return DidGithub(user=user, repo=repo, ref=ref, subpath=subpath)


def make_subpath(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    # Erlaube zwei Schreibweisen:
    # 1) raw enthält echte Slashes → übernehmen
    # 2) raw verwendet "__" als Platzhalter für '/' → zurückmappen
    return raw.replace("__", "/")


def candidate_paths(dg: DidGithub) -> List[Tuple[str, str]]:
    """
    Liefert eine geordnete Liste (ref, path) von Kandidaten
    für die Auflösung. path ist der Pfad *im Repo*.
    """
    well_known = ".well-known/did.json"
    root = "did.json"

    # Wenn Subpath angegeben: dort zuerst suchen
    sub_candidates = []
    if dg.subpath:
        sub_candidates = [f"{dg.subpath.rstrip('/')}/{well_known}",
                          f"{dg.subpath.rstrip('/')}/{root}"]

    base_candidates = [well_known, root]

    paths = sub_candidates + base_candidates

    # Branch-/Ref-Reihenfolge
    refs = [r for r in [dg.ref, "main", "master"] if r]

    return [(r, p) for r in refs for p in paths]


def _raw_url(user: str, repo: str, ref: str, path: str) -> str:
    return f"{RAW_BASE}/{user}/{repo}/{ref}/{path}"


def _headers() -> dict:
    h = {"Accept": "application/json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        # Höhere Ratenlimits und private Repos (falls Token Zugriff hat)
        h["Authorization"] = f"Bearer {token}"
    return h


@lru_cache(maxsize=256)
def fetch_json(url: str) -> Optional[dict]:
    resp = requests.get(url, headers=_headers(), timeout=10)
    if resp.status_code == 200:
        try:
            return json.loads(resp.text)
        except json.JSONDecodeError:
            # Manchmal ist die Datei als JSON-LD mit Kommentaren gespeichert → optional säubern
            cleaned = _strip_json_comments(resp.text)
            return json.loads(cleaned)
    return None


def _strip_json_comments(text: str) -> str:
    # rudimentär: entferne // ... und /* ... */ (nur für einfache Fälle)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//.*?$", "", text, flags=re.M)
    return text


def resolve_did_github(did: str) -> dict:
    """
    Gibt das DID-Dokument (dict) zurück oder wirft ValueError.
    Validiert minimale DID-Core-Felder.
    """
    dg = parse_did_github(did)
    tried = []

    for ref, path in candidate_paths(dg):
        url = _raw_url(dg.user, dg.repo, ref, path)
        tried.append(url)
        doc = fetch_json(url)
        if doc is None:
            continue

        # Minimale Validierung
        if "@context" not in doc:
            raise ValueError(f"DID-Dokument gefunden, aber @context fehlt ({url})")
        if "id" not in doc:
            raise ValueError(f"DID-Dokument gefunden, aber id fehlt ({url})")

        # Optional: Konsistenzprüfung der id
        # Wir tolerieren Abweichungen, warnen aber per Exception-Message, wenn strenger Modus gewünscht ist
        # Hier permissiv:
        return doc

    raise ValueError(
        "did:github konnte nicht aufgelöst werden.\n"
        f"Versuchte URLs:\n- " + "\n- ".join(tried)
    )


# ---------- Beispielnutzung ----------
if __name__ == "__main__":
    # Beispiele:
    did = "did:github:lepy:cudi2"
    did = "did:github:lepy:cudi2:main"
    # did = "did:github:lepy:cudi2:main:did"          # sucht did/.well-known/did.json etc.
    # did = "did:github:orgname:repo123:v1.2.3"
    #did = os.environ.get("DID_EXAMPLE", "did:github:someone:some-repo")

    try:
        doc = resolve_did_github(did)
        print(json.dumps(doc, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Fehler: {e}")
