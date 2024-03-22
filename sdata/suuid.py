import uuid
import base64
import hashlib
import os

"""
SUUID
"""



class SUUID:
    """ SUUID = b64(class_name, name, uuid)

        >>> uid = sdata.SUUID.from_name(class_name="MyClass", name="MyName")
        >>> uid.to_dict()

        (MyClass|MyName|78bc2bf739005a7bbc14019f767dbdc1)

        >>> uid.id (== uid.suuid)
        b'MzAxM2UxOGRmOTE4NDY4ZTg0MmZkMzI3YzA4ZDVkMTNEYXRhfGE='

        >>> uid.idstr
        'MTFhMDg3ZDBmZWYxNDE2ZWE1M2QyODZmODFlN2MzNTdEYXRhfGE='

        >>> uid.to_dict()
        {'class_name': 'MyClass',
         'name': 'MyName',
         'huuid': '78bc2bf739005a7bbc14019f767dbdc1',
         'suuid': 'NzhiYzJiZjczOTAwNWE3YmJjMTQwMTlmNzY3ZGJkYzFNeUNsYXNzfE15TmFtZQ=='}
    """

    def __init__(self, class_name, name=None, huuid=None):
        """generate SUUID ('DATA'|'Name'|'e1e9eaa45eba5cc1b5f035317771b22c')


        :param class_name: name of the class, e.g. 'Data'
        :param class_name: name of the object, e.g. 'Otto'
        :param huuid: uuid.hex,  e.g. 'e1e9eaa45eba5cc1b5f035317771b22c'
        :return: suuid

        """
        try:
            class_name = class_name
        except Exception as exp:
            pass

        self.class_name = class_name

        if huuid is None:
            huuid = uuid.uuid4().hex

        self.huuid = huuid

        if name is None:
            name = ""

        self.name = self._clean_name(name)

    @staticmethod
    def _clean_name(name):
        rs = ["|", ";"]
        for r in rs:
            name = name.replace(r, "")
        return name

    def __str__(self):
        return f"({self.class_name}|{self.name}|{self.huuid})"

    def __repr__(self):
        return f"({self.class_name}|{self.name}|{self.huuid})"

    @property
    def uuid(self):
        """uuid object from suuid.huuid"""
        return uuid.UUID(hex=self.huuid)

    @property
    def hex(self):
        return self.huuid

    def to_list(self):
        return [self.idstr, self.class_name, self.name, self.huuid]
    def to_dict(self):
        return {"class_name":self.class_name,
                "name": self.name,
                "huuid": self.huuid,
                "suuid": self.idstr}

    @property
    def idstr(self):
        return self.id.decode().strip()

    @property
    def id(self):
        s = "".join([self.huuid, self.class_name + "|" + self.name])
        return base64.b64encode(s.encode())

    @property
    def sname(self):
        s = "|".join([self.class_name, self.name, self.huuid])
        return s

    @property
    def suuid(self):
        s = "".join([self.huuid, self.class_name + "|" + self.name])
        return base64.b64encode(s.encode())

    @classmethod
    def from_uuid(cls, class_name, uuid_obj):
        """generate suuid from classname and uuid object

        :param class_name: 'otto'
        :param uuid_string: uuid
        :return: suuid
        """

        return cls(class_name, huuid=uuid_obj.hex)

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
        name = cls._clean_name(name)
        uid = cls.get_uuid_from_name(name=name, ns_name=ns_name)
        suuid = cls(class_name=class_name, name=name, huuid=uid.hex)
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
        name = cls._clean_name(name)
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

        sh = hashlib.sha3_256()
        with open(filepath, "rb") as fh:
            sh.update(fh.read())
        basename = os.path.basename(filepath)
        suuid = cls.from_name(class_name=class_name, name=sh.hexdigest(), ns_name=ns_name)
        suuid.name = basename
        return suuid

    @classmethod
    def from_str(cls, class_name, s, ns_name=None):
        """generate uuid from string and ns_string

            SUUID.from_str(class_name="Data", s="text", ns_name="project_xy")

        :param class_name: e.g. "otto"
        :param s: e.g. "a_nice_txt"
        :param ns_string: e.g. projectname "MyProject"
        :return: suuid
        """
        sh = hashlib.sha3_256()
        sh.update(s.encode('utf-8', errors="replace"))
        suuid = cls.from_name(class_name=class_name, name=sh.hexdigest(), ns_name=ns_name)
        return suuid

    @classmethod
    def from_suuid_bytes(cls, bytestring):
        """
        :param bytestring: 'MTNhNjMxMWNjZDFlNDFiOGI2MzJhNGY0ZTIzMjdiNTFQYXJ0fG15dGVzdG5hbWUwMQ=='
        """
        id_string = base64.b64decode(bytestring).decode()
        return cls.from_idstr(id_string)

    @classmethod
    def from_suuid_str(cls, string):
        """
        :param string: 'MTNhNjMxMWNjZDFlNDFiOGI2MzJhNGY0ZTIzMjdiNTFQYXJ0fG15dGVzdG5hbWUwMQ=='

        """

        id_string = base64.b64decode(string.encode()).decode()
        return cls.from_idstr(id_string)


    @classmethod
    def from_suuid_sname(cls, s):
        """
        :param string: 'Part|mytestname01|22a476e75a68486a92764eb830395923'

        """
        class_name, name, huuid = s.split("|")
        return cls(class_name=class_name, name=name, huuid=huuid)

    @classmethod
    def from_idstr(cls, id_string):
        try:
            class_name, name = id_string[32:].split("|", maxsplit=1)
        except:
            class_name = id_string[32:]
            name = ""

        s = cls(class_name=class_name, name=name, huuid=id_string[:32])
        return s

if __name__ == '__main__':
    sid = SUUID.from_name(class_name="DATA", name="otto")
    print(sid)
    print(sid.id)
