# -*- mode: python -*-
"""
Pyinstaller spec file for Skyperious, produces a 32-bit or 64-bit executable,
depending on current environment.

@created   03.04.2012
@modified  06.07.2020
"""
import os
import struct
import sys

os.chdir("..")
APPPATH = os.path.join(os.getcwd(), "skyperious")
ROOTPATH  = os.path.dirname(APPPATH)
sys.path.append(APPPATH)

import conf


DO_DEBUG_VERSION = False
DO_WINDOWS = ("nt" == os.name)

def do_64bit():
    return (struct.calcsize("P") * 8 == 64)


app_file = "skyperious_%s%s" % (conf.Version, "_x64" if do_64bit() else "")
if DO_WINDOWS:
    app_file += ".exe"

a = Analysis(
    [os.path.join(ROOTPATH, "launch.py")],
    excludes=["FixTk", "numpy", "tcl", "tk", "_tkinter", "tkinter", "Tkinter"],
)
a.datas += [("conf.py", "skyperious/conf.py", "DATA"), # For configuration docstrings
            ("res/Carlito.ttf", "skyperious/res/Carlito.ttf", "DATA"),
            ("res/CarlitoBold.ttf", "skyperious/res/CarlitoBold.ttf", "DATA"), ]
a.binaries = a.binaries - TOC([
    ('tcl85.dll', None, None),
    ('tk85.dll',  None, None),
    ('_tkinter',  None, None)
])
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts + ([("v", "", "OPTION")] if DO_DEBUG_VERSION else []),
    a.binaries,
    a.zipfiles,
    a.datas,
    name=os.path.join("dist", app_file),
    debug=DO_DEBUG_VERSION, # Verbose or non-verbose debug statements printed
    strip=False,  # EXE and all shared libraries run through cygwin's strip, tends to render Win32 DLLs unusable
    upx=True, # Using Ultimate Packer for eXecutables
    icon=os.path.join(APPPATH, "..", "res", "Icon.ico"),
    console=False, # Use the Windows subsystem executable instead of the console one
)
