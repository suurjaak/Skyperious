# -*- mode: python -*-
"""
Pyinstaller spec file for Skyperious, produces a 32-bit or 64-bit executable,
depending on Python environment.

Pyinstaller-provided names and variables: Analysis, EXE, PYZ, SPEC, TOC.

@created   03.04.2012
@modified  23.11.2020
"""
import os
import struct
import sys

NAME        = "skyperious"
DO_DEBUGVER = False
DO_64BIT    = (struct.calcsize("P") * 8 == 64)

BUILDPATH = os.path.dirname(os.path.abspath(SPEC))
APPPATH   = os.path.join(os.path.dirname(BUILDPATH), NAME)
ROOTPATH  = os.path.dirname(APPPATH)
os.chdir(ROOTPATH)
sys.path.append(APPPATH)

import conf

app_file = "%s_%s%s%s" % (NAME, conf.Version, "_x64" if DO_64BIT else "",
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
a.datas += [("conf.py",             "%s/conf.py" % NAME,             "DATA"), # For configuration docstrings
            ("res/Carlito.ttf",     "%s/res/Carlito.ttf" % NAME,     "DATA"),
            ("res/CarlitoBold.ttf", "%s/res/CarlitoBold.ttf" % NAME, "DATA"),
            ("res/emoticons.zip",   "%s/res/emoticons.zip" % NAME,   "DATA"), ]
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
    console=False, # Use the Windows subsystem executable instead of the console one
)

try: os.remove(entrypoint)
except Exception: pass
