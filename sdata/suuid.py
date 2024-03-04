import uuid
import base64
import hashlib

class SUUID:

    def __init__(self, class_name, huuid=None):
        """generate SUUID (b'DATA'|b'e1e9eaa45eba5cc1b5f035317771b22c')


        :param class_name: name of the class, e.g. b'Data'
        :param huuid: uuid.hex,  e.g. b'e1e9eaa45eba5cc1b5f035317771b22c'
        :return: suuid

        """
        try:
            class_name = class_name.encode()
        except Exception as exp:
            pass

        self.class_name = class_name

        if huuid is None:
            huuid = uuid.uuid4().hex.encode()

        self.huuid = huuid

    def __str__(self):
        return f"({self.class_name}|{self.huuid})"

    def __repr__(self):
        return f"({self.class_name}|{self.huuid})"

    @property
    def uuid(self):
        s = self.huuid.decode()
        return uuid.UUID(s)

    @property
    def hex(self):
        return self.huuid.decode()

    @property
    def idstr(self):
        return self.id.decode().strip()

    @property
    def id(self):
        s = b"".join([self.huuid, self.class_name])
        return base64.encodebytes(s)

    @property
    def suuid(self):
        s = b"".join([self.huuid, self.class_name])
        return base64.encodebytes(s)

    def from_uuid(cls, class_name, uuid_string):
        return cls(class_name.encode(), uuid_string.hex.encode())

    @classmethod
    def get_namespace_from_name(cls, name):
        """generate namespace uuid from string

        :param string:
        :return: uuid
        """
        nsuuid = uuid.uuid5(uuid.NAMESPACE_OID, name.upper())
        return nsuuid

    @classmethod
    def get_uuid_from_name(cls, name, ns_name=None):
        """generate uuid from string and ns_string

            SUUID.get_uuid_from_str(string="otto", ns_name="project_xy")

            nsuuid = uuid.uuid5(uuid.NAMESPACE_OID, ns_string.upper())
            uid = uuid.uuid5(nsuuid, name.upper())

        :param string: e.g. "otto"
        :param ns_string: nsuuid = SUUID.get_namespace_from_str(ns_string)
        :return: uuid
        """
        if ns_name is None:
            nsuuid = uuid.NAMESPACE_OID
        else:
            nsuuid = uuid.uuid5(uuid.NAMESPACE_OID, ns_name.upper())

        uid = uuid.uuid5(nsuuid, name.upper())
        return uid

    @classmethod
    def from_name(cls, class_name, name, ns_name=None):
        """generate uuid from string and ns_string

            SUUID.get_uuid_from_str(string="otto", ns_name="project_xy")

            nsuuid = uuid.uuid5(uuid.NAMESPACE_OID, ns_string.upper())
            uid = uuid.uuid5(nsuuid, name.upper())

        :param class_name: e.g. "otto"
        :param name: e.g. "otto"
        :param ns_string: e.g. projectname "MyProject"
        :return: suuid
        """
        uid = cls.get_uuid_from_name(name=name, ns_name=ns_name)
        suuid = cls(class_name=class_name, huuid=uid.hex.encode())
        return suuid

    @classmethod
    def get_suuid_from_name(cls, class_name, name, ns_name=None):
        """generate uuid from string and ns_string

            SUUID.get_uuid_from_str(string="otto", ns_name="project_xy")

            nsuuid = uuid.uuid5(uuid.NAMESPACE_OID, ns_string.upper())
            uid = uuid.uuid5(nsuuid, name.upper())

        :param class_name: e.g. "otto"
        :param name: e.g. "otto"
        :param ns_string: e.g. projectname "MyProject"
        :return: suuid
        """
        suuid = cls.from_name(class_name, name=name, ns_name=ns_name)
        return suuid.id

    @classmethod
    def from_file(cls, class_name, filepath, ns_name=None):
        """generate uuid from string and ns_string

            SUUID.get_uuid_from_str(string="otto", ns_name="project_xy")

            nsuuid = uuid.uuid5(uuid.NAMESPACE_OID, ns_string.upper())
            uid = uuid.uuid5(nsuuid, name.upper())

        :param class_name: e.g. "otto"
        :param filename: e.g. "a_nice.png"
        :param ns_string: e.g. projectname "MyProject"
        :return: suuid
        """

        s = hashlib.sha3_256()
        with open(filepath, "rb") as fh:
            s.update(fh.read())
        # hash_ = s#.hexdigest()
        suuid = cls.from_name(class_name=class_name, name=s.hexdigest(), ns_name=ns_name)

        return suuid

    # @classmethod
    # def from_name(cls, class_name, name):
    #     huuid = uuid.uuid5(uuid.NAMESPACE_OID, name)
    #     s = cls(class_name=class_name, huuid=huuid.hex.encode())
    #     return s

    @classmethod
    def from_suuid_bytes(cls, bytestring):
        """
        b'NTcxYzNlY2E1NGYwNWNlY2E4MzFlOGNkNjYxNjMwOWFDTE5fQ1M=\n'
        """

        id_string = base64.decodebytes(bytestring)
        s = cls(class_name=id_string[32:], huuid=id_string[:32])
        return s

    @classmethod
    def from_suuid_str(cls, string):
        """
        'NTcxYzNlY2E1NGYwNWNlY2E4MzFlOGNkNjYxNjMwOWFDTE5fQ1M=\n'
        """

        id_string = base64.decodebytes(string.encode())
        s = cls(class_name=id_string[32:], huuid=id_string[:32])
        return s

if __name__ == '__main__':
    sid = SUUID.from_name(class_name="DATA", name="otto")
    print(sid)
    print(sid.id)
