#!/urs/bin/env python3

import shutil 
import os

modulepath = os.path.dirname(__file__)

packagepath = modulepath
keywordpath = os.path.join(packagepath)

dstpath = os.path.expanduser("/tmp/sdata")
if not os.path.exists(dstpath):
    os.makedirs(dstpath)

def copy_source_files(keywordpath):
    for root, dirs, files in os.walk(keywordpath, topdown=False):
        for filename in files:
            if filename.endswith(".py") or filename.endswith(".md") :
                print("_"*80)
                pycsrc = os.path.join(root, filename)
                print(pycsrc)
                relpath = os.path.relpath(os.path.dirname(pycsrc), packagepath)
                pycdst = os.path.abspath(os.path.join(dstpath, relpath, filename))
                print(pycdst)
                print(relpath)
                if os.path.exists(pycsrc):
                    # print("_"*80)
                    # print("src: %s" % pycsrc)
                    # print("dst: %s" % pycdst)
                    if not os.path.exists(os.path.dirname(pycdst)):
                        print("create path %s" % os.path.dirname(pycdst))
                        os.makedirs(os.path.dirname(pycdst))
                    shutil.copy(pycsrc, pycdst)
                else:
                    print("ERROR: %s" % pycsrc)

copy_source_files(keywordpath)
shutil.copy(os.path.join(packagepath, "setup.py"), os.path.join(dstpath, "setup.py"))

os.system("cd %s; pwd; ls;python3 setup.py bdist_egg --exclude-source-files" % (dstpath))

# cmd = "cp %s/dist/scale.fem*.egg %s" % (dstpath, eggdst)
# print(cmd)
# os.system(cmd)
# try:
#     os.system("cp %s/dist/scale.fem*.egg %s" % (dstpath, "/home/ingolf.lepenies/dyna/dynprojekte/honda/outgoing/sfpi/1.0/src/scale.fem-py2.7.egg"))
# except Exception as exp:
#     print(exp)
