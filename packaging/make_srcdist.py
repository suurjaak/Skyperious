"""
Creates Skyperious source distribution archive from current version in src\.
Sets execute flag permission on .sh files.

@author    Erki Suurjaak
@created   12.12.2013
@modified  28.02.2014
"""
import glob
import os
import sys
import time
import zipfile
import zlib


if "__main__" == __name__:
    INITIAL_DIR = os.getcwd()
    PACKAGING_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__)))
    os.chdir(os.path.join(os.path.dirname(__file__), ".."))
    sys.path.append("src")
    import conf

    BASE_DIR = ""
    ZIP_DIR = "skyperious_%s" % conf.Version
    DEST_FILE = "skyperious_%s-src.zip" % conf.Version
    print("Creating source distribution %s.\n" % DEST_FILE)

    def pathjoin(*args):
        # Cannot have ZIP system UNIX with paths like Windows
        return "/".join(filter(None, args))

    def add_files(zf, filenames, subdir="", subdir_local=None):
        global BASE_DIR
        size = 0
        for filename in filenames:
            fullpath = os.path.join(BASE_DIR,
                subdir_local if subdir_local is not None else subdir, filename)
            zi = zipfile.ZipInfo()
            zi.filename = pathjoin(ZIP_DIR, subdir, filename)
            zi.date_time = time.localtime(os.path.getmtime(fullpath))[:6]
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.create_system = 3 # UNIX
            zi.external_attr = 0644 << 16L # Permission flag -rw-r--r--
            if os.path.splitext(filename)[-1] in [".sh"]:
                zi.external_attr = 0755 << 16L # Permission flag -rwxr-xr-x
            print("Adding %s, %s bytes" % (zi.filename, os.path.getsize(fullpath)))
            zf.writestr(zi, open(fullpath, "rb").read())
            size += os.path.getsize(fullpath)
        return size

    with zipfile.ZipFile(os.path.join(INITIAL_DIR, DEST_FILE), mode="w") as zf:
        size = 0
        for subdir, wildcard in [("res", "*"),
        (pathjoin("res", "emoticons"), "*"), ("src", "*.py"),
        ("packaging", "*"), (pathjoin("src", "third_party"), "*.py")]:
            entries = glob.glob(os.path.join(BASE_DIR, subdir, wildcard))
            files = sorted([os.path.basename(x) for x in entries
                          if os.path.isfile(x)], key=str.lower)
            files = filter(lambda x: not x.lower().endswith(".zip"), files)
            size += add_files(zf, files, subdir)
        rootfiles = ["CHANGELOG.md", "LICENSE.md", "README.md",
                     "requirements.txt", "skyperious.bat", "skyperious.sh"]
        size += add_files(zf, rootfiles)
        size += add_files(zf, ["skyperious.ini"],
                          subdir_local=os.path.split(PACKAGING_DIR)[-1])

    os.chdir(INITIAL_DIR)
    size_zip = os.path.getsize(DEST_FILE)
    print ("\nCreated %s, %s bytes (from %s, %.2f compression ratio)." % 
           (DEST_FILE, size_zip, size, float(size_zip) / size))
