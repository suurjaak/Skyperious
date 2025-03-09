# -*- mode: python -*-
"""
Pyinstaller spec file for Skyperious, produces a 32-bit or 64-bit executable,
depending on Python environment.

Pyinstaller-provided names and variables: Analysis, EXE, PYZ, SPEC, TOC.

@created   03.04.2012
@modified  09.03.2025
"""
import os
import struct
import sys

NAME        = "skyperious"
DO_DEBUGVER = False
DO_64BIT    = (struct.calcsize("P") * 8 == 64)

BUILDPATH = os.path.dirname(os.path.abspath(SPEC))
ROOTPATH  = os.path.dirname(BUILDPATH)
APPPATH   = os.path.join(ROOTPATH, "src")
os.chdir(ROOTPATH)
sys.path.insert(0, APPPATH)

from skyperious import conf

app_file = "%s_%s%s%s" % (NAME, conf.Version, "" if DO_64BIT else "_x86",
                          ".exe" if "nt" == os.name else "")
entrypoint = os.path.join(ROOTPATH, "launch.py")

with open(entrypoint, "w") as f:
    f.write("from %s import main; main.run()" % NAME)


a = Analysis(
    [entrypoint],
    excludes=["FixTk", "numpy", "tcl", "tk", "_tkinter", "tkinter", "Tkinter"],
    hiddenimports=["imghdr", "mimetypes",   # Imported within templates
                   "ijson.backends.python"] # ijson imports backends indirectly
)
a.datas += [("conf.py",                    "src/%s/conf.py"             % NAME, "DATA"), # For configuration docstrings
            ("res/3rd-party licenses.txt", "build/3rd-party licenses.txt", "DATA"),
            ("res/Carlito.ttf",            "src/%s/res/Carlito.ttf"     % NAME, "DATA"),
            ("res/CarlitoBold.ttf",        "src/%s/res/CarlitoBold.ttf" % NAME, "DATA"),
            ("res/emoticons.zip",          "src/%s/res/emoticons.zip"   % NAME, "DATA"), ]
a.binaries = a.binaries - TOC([
    ('tcl85.dll', None, None), ('tk85.dll',  None, None), ('_tkinter',  None, None)
])
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts + ([("v", "", "OPTION")] if DO_DEBUGVER else []),
    a.binaries,
    a.zipfiles,
    a.datas,
    name=os.path.join("build", app_file),

    debug=DO_DEBUGVER, # Verbose or non-verbose debug statements printed
    strip=False,  # EXE and all shared libraries run through cygwin's strip, tends to render Win32 DLLs unusable
    upx=True, # Using Ultimate Packer for eXecutables
    icon=os.path.join(ROOTPATH, "res", "Icon.ico"),
    console=DO_DEBUGVER, # Use the Windows subsystem executable instead of the console one
)

try: os.remove(entrypoint)
except Exception: pass
