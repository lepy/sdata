from sdata import SUUID, Base
import os

class File(Base):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def exists(self, path):
        filepath = os.path.join(path, self.name)
        return os.path.exists(path)

class Directory(Base):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.path = kwargs.get("path", os.getcwd())
        self.files = {}

    def register_files(self, path):
        self.path = path
        for f in os.listdir(self.path):
            self.add(File(name=f))

    def add(self, f):
        """

        """
        self.files[f.name] = f

    def ls(self):
        """

        """
        return list(self.files.keys())

if __name__ == '__main__':
    f = File(name="a.txt")
    print(f)

    d = Directory(name="/folder")
    d.add(f)
    print(d.ls())
    print(d)