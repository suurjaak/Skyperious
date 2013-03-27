"""
Simple small script for generating a nicely formatted Python module with
embedded images and docstrings.

@author    Erki Suurjaak
@created   07.02.2012
@modified  22.03.2013
"""
import base64
import datetime
import os
import shutil
import wx.tools.img2py

"""Target Python script to write."""
TARGET = os.path.join("..", "images.py")

Q3 = '"""'

"""Application icons of different size and colour depth."""
APPICONS = {
  #"Icon.ico": "Skyperious application iconset, with 16x16 and 32x32 icons.",
  "Icon8bit16x16.png": "Skyperious application 16x16 icon, 8-bit colour.",
  "Icon8bit32x32.png": "Skyperious application 16x16 icon, 8-bit colour.",
  "Icon32bit16x16.png": "Skyperious application 32x32 icon, 32-bit colour.",
  "Icon32bit32x32.png": "Skyperious application 32x32 icon, 32-bit colour.",
}
IMAGES = {
    "AvatarDefault.png":
        "Default avatar image for contacts without one.",
    "AvatarDefaultLarge.png":
        "Default large avatar image for contacts.",
    "ExportClock.png":
        "Clock image icon for new days in exported chat HTML.",
    "IconChats.png":
        "Icon for the Chats page in a database tab.",
    "IconContacts.png":
        "Icon for the Contacts+ page in a database tab, and\n"
        "Merge Contacts page in a merger tab.",
    "IconDatabase.png":
        "Icon for the Database page in a database tab.",
    "IconInfo.png":
        "Icon for the Info page in a database tab.",
    "IconMergeAll.png":
        "Icon for the Merge All page in a merger tab.",
    "IconMergeChats.png":
        "Icon for the Merge Chats page in a merger tab.",
    "IconSearch.png":
        "Icon for the Search page in a database tab.",
    "IconSQL.png":
        "Icon for the SQL Window page in a database tab.",
    "ToolbarCommit.png":
        "Toolbar icon for commit button in database table grids.",
    "ToolbarContact.png":
        "Toolbar icon for contacts button on search page.",
    "ToolbarDelete.png":
        "Toolbar icon for delete button in database table grids.",
    "ToolbarFilter.png":
        "Toolbar icon for filter chat button in chat page.",
    "ToolbarInsert.png":
        "Toolbar icon for insert button in database table grids.",
    "ToolbarMaximize.png":
        "Toolbar icon for maximize chat button in chat page.",
    "ToolbarMessage.png":
        "Toolbar icon for message toggle button on search page.",
    "ToolbarRollback.png":
        "Toolbar icon for rollback button in database table grids.",
    "ToolbarStats.png":
        "Toolbar icon for stats button in chat page.",
    "ToolbarStop.png":
        "Toolbar icon for stop button on search page.",
    "ToolbarStopped.png":
        "Toolbar icon for inactive stop button on search page.",
    "ToolbarTabs.png":
        "Toolbar icon for tabs toggle button on search page.",
    "ToolbarTitle.png":
        "Toolbar icon for title toggle button on search page.",
}
HEADER = """%s
Contains embedded image and icon resources for Skyperious. Auto-generated.

@author    Erki Suurjaak
@created   07.02.2012
@modified  %s
%s
from base64 import b64decode
from cStringIO import StringIO
from wx.lib.embeddedimage import PyEmbeddedImage
import wx""" % (Q3, datetime.date.today().strftime("%d.%m.%Y"), Q3)


def create_py(target):
    global HEADER, APPICONS, IMAGES
    f = open(target, "w")
    f.write(HEADER)
    icons = [os.path.splitext(i)[0] for i in sorted(APPICONS.keys())]
    f.write("\n\n%s%s%s\ndef get_appicons():\n    icons = wx.IconBundle()\n"
            "    [icons.AddIcon(wx.IconFromBitmap(i.GetBitmap())) "
            "for i in [\n        %s\n    ]]\n    return icons\n" % (Q3,
        "Returns the application icon bundle, "
        "for several sizes and colour depths.",
        Q3, str(icons).replace("'", "").replace("[", "").replace("]", "")
    ))
    for filename, desc in sorted(APPICONS.items()):
        name, extension = os.path.splitext(filename)
        f.write("\n\n%s%s%s\n%s = PyEmbeddedImage(\n" % (Q3, desc, Q3, name))
        data = base64.b64encode(open(filename, "rb").read())
        while data:
            f.write("    \"%s\"\n" % data[:72])
            data = data[72:]
        f.write(")\n")
    for filename, desc in sorted(IMAGES.items()):
        name, extension = os.path.splitext(filename)
        f.write("\n\n%s%s%s\n%s = PyEmbeddedImage(\n" % (Q3, desc, Q3, name))
        data = base64.b64encode(open(filename, "rb").read())
        while data:
            f.write("    \"%s\"\n" % data[:72])
            data = data[72:]
        f.write(")\n")
    f.close()


if "__main__" == __name__:
    create_py(TARGET)
