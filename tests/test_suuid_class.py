import pytest
import uuid
import base64
import hashlib
import os
import tempfile

from sdata.suuid import SUUID  # Angenommen, der Code ist in suuid.py gespeichert

@pytest.fixture
def temp_file():
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"test content")
        tmp_path = tmp.name
    yield tmp_path
    os.unlink(tmp_path)

class TestSUUID:

    def test_init_valid(self):
        sid = SUUID(class_name="Test", name="name", huuid="1234567890abcdef1234567890abcdef")
        assert sid.class_name == "Test"
        assert sid.name == "name"
        assert sid.huuid == "1234567890abcdef1234567890abcdef"

    def test_init_default_huuid(self):
        sid = SUUID(class_name="Test")
        assert len(sid.huuid) == 32
        assert all(c in '0123456789abcdefABCDEF' for c in sid.huuid)
        assert sid.name == "noname"

    def test_init_invalid_class_name(self):
        with pytest.raises(ValueError, match="class_name muss ein nicht-leerer String sein"):
            SUUID(class_name="")
        with pytest.raises(ValueError, match="class_name muss ein nicht-leerer String sein"):
            SUUID(class_name=123)

    def test_init_invalid_huuid(self):
        with pytest.raises(ValueError, match="huuid muss ein 32-Zeichen langer Hex-String sein"):
            SUUID(class_name="Test", huuid="invalid")
        with pytest.raises(ValueError, match="huuid muss ein 32-Zeichen langer Hex-String sein"):
            SUUID(class_name="Test", huuid="1234567890abcdef1234567890abcde")  # Zu kurz

    def test_clean_name(self):
        assert SUUID.generate_safe_filename("name@|;\n\rbad") == "name_bad"
        assert SUUID.generate_safe_filename("") == "noname"
        assert SUUID.generate_safe_filename("clean") == "clean"

    def test_str_and_repr(self):
        sid = SUUID(class_name="Test", name="name", huuid="1234567890abcdef1234567890abcdef")
        assert str(sid) == "(Test@name@1234567890abcdef1234567890abcdef)"
        assert repr(sid) == "(Test@name@1234567890abcdef1234567890abcdef)"

    def test_uuid_property(self):
        sid = SUUID(class_name="Test", huuid="1234567890abcdef1234567890abcdef")
        assert isinstance(sid.get_uuid(), uuid.UUID)
        assert sid.get_uuid().hex == "1234567890abcdef1234567890abcdef"

    def test_hex_property(self):
        sid = SUUID(class_name="Test", huuid="1234567890abcdef1234567890abcdef")
        assert sid.hex == "1234567890abcdef1234567890abcdef"

    def test_to_list(self):
        sid = SUUID(class_name="Test", name="name", huuid="1234567890abcdef1234567890abcdef")
        expected_suuid_str = "MTIzNDU2Nzg5MGFiY2RlZjEyMzQ1Njc4OTBhYmNkZWZUZXN0QG5hbWU="
        assert sid.to_list() == [expected_suuid_str, "Test", "name", "1234567890abcdef1234567890abcdef"]

    def test_to_dict(self):
        sid = SUUID(class_name="Test", name="name", huuid="1234567890abcdef1234567890abcdef")
        expected_suuid_str = "MTIzNDU2Nzg5MGFiY2RlZjEyMzQ1Njc4OTBhYmNkZWZUZXN0QG5hbWU="
        assert sid.to_dict() == {
            "class_name": "Test",
            "name": "name",
            "huuid": "1234567890abcdef1234567890abcdef",
            "suuid": expected_suuid_str
        }

    def test_sname(self):
        sid = SUUID(class_name="Test", name="name", huuid="1234567890abcdef1234567890abcdef")
        assert sid.sname == "Test@name@1234567890abcdef1234567890abcdef"

    def test_suuid_and_suuid_str(self):
        sid = SUUID(class_name="Test", name="name", huuid="1234567890abcdef1234567890abcdef")
        expected_s = "1234567890abcdef1234567890abcdefTest@name"
        expected_bytes = base64.b64encode(expected_s.encode())
        assert sid.suuid_bytes == expected_bytes
        assert sid.suuid_str == expected_bytes.decode().strip()

    def test_from_uuid(self):
        u = uuid.UUID("1234567890abcdef1234567890abcdef")
        sid = SUUID.from_uuid(class_name="Test", uuid_obj=u)
        assert sid.class_name == "Test"
        assert sid.huuid == "1234567890abcdef1234567890abcdef"
        assert sid.name == "noname"

    def test_get_namespace_from_name(self):
        ns = SUUID.get_namespace_from_name("project_xy")
        assert ns == uuid.uuid5(uuid.NAMESPACE_OID, "PROJECT_XY")

    def test_get_uuid_from_name(self):
        uid = SUUID.get_uuid_from_name(name="DATAotto")
        assert uid.hex == "96da1780e6225b33b9186e41838d2e2c"

        uid_ns = SUUID.get_uuid_from_name(name="DATAotto", ns_name="project_xy")
        assert uid_ns.hex == "903649d7c1f9529f9c4ba45eb79751f4"

    def test_from_name(self):
        sid = SUUID.from_name(class_name="DATA", name="otto")
        assert sid.huuid == "96da1780e6225b33b9186e41838d2e2c"
        assert sid.class_name == "DATA"
        assert sid.name == "otto"
        assert sid.suuid_str == "OTZkYTE3ODBlNjIyNWIzM2I5MTg2ZTQxODM4ZDJlMmNEQVRBQG90dG8="

    def test_from_name_with_ns(self):
        sid = SUUID.from_name(class_name="DATA", name="otto", ns_name="project_xy")
        assert sid.huuid == "903649d7c1f9529f9c4ba45eb79751f4"
        assert sid.suuid_str == "OTAzNjQ5ZDdjMWY5NTI5ZjljNGJhNDVlYjc5NzUxZjREQVRBQG90dG8="

    def test_get_suuid_from_name(self):
        suuid_bytes = SUUID.get_suuid_from_name(class_name="DATA", name="otto")
        assert suuid_bytes == b'OTZkYTE3ODBlNjIyNWIzM2I5MTg2ZTQxODM4ZDJlMmNEQVRBQG90dG8='

    def test_get_sname_from_name(self):
        sname = SUUID.get_sname_from_name(class_name="DATA", name="otto")
        assert sname == "DATA@otto@96da1780e6225b33b9186e41838d2e2c"

    def test_from_str(self):
        sid = SUUID.from_str(class_name="Data", s="test text")
        expected_hash = '_08487142e9585eb2a39f4b8c9f64d4b60dc420af4ee136472d252d0c68d99974'
        assert sid.name == expected_hash
        # huuid basierend auf "Data" + hash
        expected_input = "Data" + expected_hash
        expected_uid = uuid.uuid5(uuid.NAMESPACE_OID, expected_input.upper())
        assert sid.huuid == expected_uid.hex

    # def test_from_file(self, temp_file):
    #     sid = SUUID.from_file(class_name="File", filepath=temp_file)
    #     expected_hash = hashlib.sha3_256(b"test content").hexdigest()
    #     assert sid.name == "temp.txt"  # Da NamedTemporaryFile auf Windows/Linux .txt haben kann, aber anpassen wenn nötig
    #     expected_input = "File" + expected_hash
    #     expected_uid = uuid.uuid5(uuid.NAMESPACE_OID, expected_input.upper())
    #     assert sid.huuid == expected_uid.hex

    def test_from_suuid_bytes(self):
        example_bytes = b'OTZkYTE3ODBlNjIyNWIzM2I5MTg2ZTQxODM4ZDJlMmNEQVRBQG90dG8='
        sid = SUUID.from_suuid_bytes(example_bytes)
        assert sid.huuid == "96da1780e6225b33b9186e41838d2e2c"
        assert sid.class_name == "DATA"
        assert sid.name == "otto"

    def test_from_suuid_str(self):
        example_str = "OTZkYTE3ODBlNjIyNWIzM2I5MTg2ZTQxODM4ZDJlMmNEQVRBQG90dG8="
        sid = SUUID.from_suuid_str(example_str)
        assert sid.huuid == "96da1780e6225b33b9186e41838d2e2c"
        assert sid.class_name == "DATA"
        assert sid.name == "otto"

    def test_from_suuid_sname(self):
        sname = "DATA@otto@96da1780e6225b33b9186e41838d2e2c"
        sid = SUUID.from_suuid_sname(sname)
        assert sid.class_name == "DATA"
        assert sid.name == "otto"
        assert sid.huuid == "96da1780e6225b33b9186e41838d2e2c"

    def test_from_suuid_sname_invalid(self):
        with pytest.raises(ValueError, match="Ungültiger sname-Format"):
            SUUID.from_suuid_sname("invalid@format")

    def test_from_idstr(self):
        id_string = "96da1780e6225b33b9186e41838d2e2cDATA@otto"
        sid = SUUID.from_idstr(id_string)
        assert sid.huuid == "96da1780e6225b33b9186e41838d2e2c"
        assert sid.class_name == "DATA"
        assert sid.name == "otto"

    def test_from_idstr_no_name(self):
        id_string = "96da1780e6225b33b9186e41838d2e2cDATA"
        sid = SUUID.from_idstr(id_string)
        assert sid.class_name == "DATA"
        assert sid.name == "noname"

    def test_from_idstr_short(self):
        with pytest.raises(ValueError, match="Ungültiger id_string: Zu kurz"):
            SUUID.from_idstr("short")