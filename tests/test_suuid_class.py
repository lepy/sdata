# -*- coding: utf-8 -*-
"""Tests für den sdata.suuid-Adapter über das eigenständige ``suuid``-Package.

Der Adapter erbt Format, Determinismus und die 100% S3-sichere Normalisierung von
``suuid``; getestet wird hier die sdata-Kompat-Fläche (Alias-Namen, Signaturen).
Die huuid-Goldenwerte bleiben gegenüber der alten Implementierung gültig (gleicher
uuid5-Algorithmus); ``sname``/``suuid_str`` tragen jetzt das ``__``-Format.
"""
import re
import uuid

import pytest

from sdata.suuid import SUUID

HEX = "1234567890abcdef1234567890abcdef"
S3_SAFE = re.compile(r"[A-Za-z0-9_]+")


class TestSUUID:

    # --- Konstruktion / Komponenten -------------------------------------
    def test_direct_construction(self):
        sid = SUUID(class_name="Test", name="name", huuid=HEX)
        assert (sid.class_name, sid.name, sid.huuid) == ("Test", "name", HEX)

    def test_huuid_required_and_validated(self):
        with pytest.raises(ValueError):
            SUUID(class_name="Test", name="x", huuid="invalid")
        with pytest.raises(ValueError):
            SUUID(class_name="", name="x", huuid=HEX)

    # --- from_name: deterministisch, huuid-Vertrag erhalten -------------
    def test_from_name_deterministic(self):
        sid = SUUID.from_name("DATA", "otto")
        assert sid.huuid == "96da1780e6225b33b9186e41838d2e2c"   # golden (unverändert)
        assert sid.class_name == "DATA" and sid.name == "otto"
        assert sid.sname == f"DATA__otto__{sid.huuid}"
        assert SUUID.from_name("DATA", "otto") == sid

    def test_from_name_with_ns(self):
        sid = SUUID.from_name("DATA", "otto", ns_name="project_xy")
        assert sid.huuid == "903649d7c1f9529f9c4ba45eb79751f4"   # golden (unverändert)
        assert sid != SUUID.from_name("DATA", "otto")            # Scoping wirkt

    # --- Aliasse / Properties -------------------------------------------
    def test_aliases(self):
        sid = SUUID.from_name("DATA", "otto")
        assert sid.suuid_str == sid.compact_token
        assert sid.suuid_bytes == sid.compact_token.encode()
        assert sid.uuid == sid.as_uuid() == sid.get_uuid()
        assert isinstance(sid.uuid, uuid.UUID)
        assert sid.hex == sid.huuid

    def test_to_list_and_dict(self):
        sid = SUUID.from_name("DATA", "otto")
        assert sid.to_list() == [sid.sname, sid.suuid_str, "DATA", "otto", sid.huuid]
        d = sid.to_dict()
        assert d["sname"] == sid.sname
        assert d["suuid"] == sid.suuid_str
        assert d["huuid"] == sid.huuid

    # --- Roundtrips -----------------------------------------------------
    def test_roundtrip_str_bytes_sname(self):
        sid = SUUID.from_name("DATA", "otto")
        assert SUUID.from_suuid_str(sid.suuid_str) == sid
        assert SUUID.from_suuid_bytes(sid.suuid_bytes) == sid
        assert SUUID.from_suuid_sname(sid.sname) == sid

    def test_from_suuid_sname_lenient(self):
        assert SUUID.from_suuid_sname("kaputt") is None          # Default strict=False
        assert SUUID.from_suuid_sname("a__b", strict=False) is None
        with pytest.raises(ValueError):
            SUUID.from_suuid_sname("a__b", strict=True)

    def test_from_uuid(self):
        sid = SUUID.from_uuid("Test", uuid.UUID(HEX))
        assert sid.class_name == "Test" and sid.huuid == HEX

    def test_from_obj(self):
        sid = SUUID.from_name("DATA", "otto")
        assert SUUID.from_obj(sid) == sid
        assert SUUID.from_obj(sid.sname) == sid
        assert SUUID.from_obj(None) is None

    # --- content-adressiert ---------------------------------------------
    def test_from_str_content_addressed(self):
        a = SUUID.from_str("Data", "test text")
        b = SUUID.from_str("Data", "test text")
        assert a == b
        assert a.content_hash and len(a.content_hash) == 64

    def test_from_file(self, tmp_path):
        p = tmp_path / "doc.txt"
        p.write_bytes(b"test content")
        sid = SUUID.from_file("File", str(p))
        assert sid.name == "doc_txt"          # Basename, S3-sicher normalisiert
        assert sid.content_hash

    # --- 100% S3-Sicherheit ---------------------------------------------
    @pytest.mark.parametrize("cn, n", [
        ("Data", "name@|;bad"),
        ("Über", "Größe @ 2026.csv"),
        ("Run", "2026_digit_start"),
        ("Path", r"a/b\c:d*e"),
    ])
    def test_safe_filename_and_sname_are_s3_safe(self, cn, n):
        safe = SUUID.generate_safe_filename(n)
        assert safe == "" or (S3_SAFE.fullmatch(safe) and not safe.startswith("_"))
        assert "@" not in safe
        s = SUUID.from_name(cn, n).sname
        assert S3_SAFE.fullmatch(s) and not s.startswith("_") and "@" not in s

    def test_generate_safe_filename_examples(self):
        assert SUUID.generate_safe_filename("name@|;bad") == "name_bad"
        assert SUUID.generate_safe_filename("clean") == "clean"

    def test_is_valid_suuid_str(self):
        sid = SUUID.from_name("DATA", "otto")
        assert SUUID.is_valid_suuid_str(sid.suuid_str) is True
        assert SUUID.is_valid_suuid_str("nope") is False
