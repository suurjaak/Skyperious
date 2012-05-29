# -*- coding: utf-8 -*-
"""
Application settings, and functionality to save/load some of them from
an external file. Configuration file has simple INI file format,
and all values are kept in JSON.

@author      Erki Suurjaak
@created     26.11.2011
@modified    29.05.2012
"""
from ConfigParser import RawConfigParser
import datetime
import json
import os
import sys

if getattr(sys, 'frozen', False):
    # Running as a pyinstaller executable
    ApplicationDirectory = os.path.dirname(sys.executable)
else:
    ApplicationDirectory = os.path.dirname(__file__)

"""List of attribute names that can be saved to and loaded from ConfigFile."""
FileDirectives = ["ConsoleHistoryCommands", "DBDoBackup", "RecentFiles",
    "DBFiles", "LastSelectedFiles"
]

"""Whether logging is enabled."""
LogEnabled = True

"""Program title."""
Title = "Skyperious"

"""Module containing application main window class."""
MainWindowModule = "skyperious"

Version = "0.10.0a"

VersionDate = "29.05.2012"

"""Name of file where FileDirectives are kept."""
ConfigFile = "%s.ini" % os.path.join(ApplicationDirectory, Title.lower())

"""Main window size in pixels, (w, h)."""
WindowSize = (1080, 640)

"""Console window size in pixels, (w, h)."""
ConsoleSize = (800, 300)

"""Maximum number of commands to store for console history."""
ConsoleHistoryMax = 1000

"""History of commands entered in console."""
ConsoleHistoryCommands = []

"""Files selected in the database lists on last run."""
LastSelectedFiles = ["", ""]

"""
Maximum number of messages shown in the chat history initially, before user
filtering.
"""
MaxHistoryInitialMessages = 1500

"""Maximum length of a tab title, overflow will be cut on the left."""
MaxTabTitleLength = 616

"""
Maximum number of messages to show in search results (wx.html.HtmlWindow has
trouble showing long documents).
"""
SearchMessagesMax = 400

"""How many search results to yield in one chunk from search thread."""
SearchResultsChunk = 50

"""How many diff results to yield in one chunk from diff thread."""
DiffResultsChunk = 5

"""Name of font used in chat history."""
HistoryFontName = "Tahoma"

"""Font size in chat history."""
HistoryFontSize = 8

"""Default colour in chat history."""
HistoryDefaultColour = "#202020"

"""Background colour of exported chat history."""
HistoryBackgroundColour = "#8CBEFF"

"""Colour used for timestamps in chat history."""
HistoryTimestampColour = "#999999"

"""Colour used for remote authors in chat history."""
HistoryRemoteAuthorColour = "#3399FF"

"""Colour used for local authors in chat history."""
HistoryLocalAuthorColour = "#999999"

"""Colour used for greyed items in chat history."""
HistoryGreyColour = "#999999"

"""Colour used for clickable links in chat history"""
HistoryLinkColour = "#3399FF"

"""Default colour in chat history."""
HistoryLineColour = "#E4E8ED"

"""Descriptive text shown in chat history searchbox."""
HistorySearchDescription = "Search for.."

"""Background colour of the chat history searchbox if no matches found."""
HistorySearchNoMatchBgColour = "#FF6666"

"""Colour used for contact field names in search results."""
ResultContactFieldColour = "#727272"

"""Background colour of opened items in lists."""
ListOpenedBgColour = "pink"

"""Color set to database file list rows that have been opened."""
DBFileOpenedColour = "blue"

"""Color set to database table list tables that have been changed."""
DBTableChangedColour = "red"

"""Color set to the database table list table that is currently open."""
DBTableOpenedColour = "blue"

"""Colour set to table/list rows that have been changed."""
GridRowChangedColour = "#FFCCCC"#"#FFAA22"#"#FFDAFF"

"""Colour set to table/list rows that have been inserted."""
GridRowInsertedColour = "#88DDFF"#"#22AAFF"#"#FFDAFF"

"""Colour set to table/list cells that have been changed."""
GridCellChangedColour = "#FF7777"

"""Colour set to chat diff list rows with identical sides."""
DiffIdenticalColour = "#666666"

"""Copyright symbol and year string."""
Copyright = "\xA9 2011-2012"

"""Large information text shown on the first page."""
InfoText = """
%(name)s can open local Skype SQLite databases and look at their contents:
- search across all messages and contacts
- browse, filter and export chat histories, see chat statistics
- view any database table and and export their data
- change, add or delete data in any table
- execute direct SQL queries

%(name)s can also compare two Skype databases, show the differences in chat
histories, and copy any differences from one database to another.
Skype uses local database files to keep its chat history, and older messages
tend to get lost as computers get upgraded or changed.

%(copy)s, Erki Suurjaak. Version %(ver)s, %(date)s.
""" % {"copy": Copyright, "name": Title, "ver": Version, "date": VersionDate}

"""Width and height tuple of the avatar image, shown in chat data."""
AvatarImageSize = (32, 32)

"""Colour for files plot in chat statistics."""
PlotMessagesColour = "#3399FF"

"""Colour for files plot in chat statistics."""
PlotSMSesColour = "#FFB333"

"""Colour for files plot in chat statistics."""
PlotFilesColour = "#33DD66"

"""Background colour for plots in chat statistics."""
PlotBgColour = "#DDDDDD"

"""Length of the chat statistics plots, in pixels."""
PlotWidth = 200

"""Whether a backup copy is made of a database before it's changed."""
DBDoBackup = False

"""How many items in the Recent Files menu."""
MaxRecentFiles = 20

"""Contents of Recent Files menu."""
RecentFiles = []

"""All detected/added databases."""
DBFiles = []


def load():
    """Loads FileDirectives from ConfigFile into this module's attributes."""
    section = "*"
    module = sys.modules[__name__]
    parser = RawConfigParser()
    parser.optionxform = str # Force case-sensitivity on names
    try:
        parser.read(ConfigFile)
        for name in FileDirectives:
            try: # parser.get can throw an error if not found
                value_raw = parser.get(section, name)
                success = False
                # First, try to interpret as JSON
                try:
                    value = json.loads(value_raw)
                    success = True
                except:
                    pass
                if not success:
                    # JSON failed, try to eval it
                    try:
                        value = eval(value_raw)
                        success = True
                    except:
                        # JSON and eval failed, fall back to string
                        value = value_raw
                        success = True
                if success:
                    setattr(module, name, value)
            except:
                pass
    except Exception, e:
        pass # Fail silently


def save():
    """Saves FileDirectives into ConfigFile."""
    section = "*"
    module = sys.modules[__name__]
    parser = RawConfigParser()
    parser.optionxform = str # Force case-sensitivity on names
    parser.add_section(section)
    try:
        f = open(ConfigFile, "wb")
        f.write("# %s configuration autowritten on %s.\n" % (
            ConfigFile, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        for name in FileDirectives:
            try:
                value = getattr(module, name)
                parser.set(section, name, json.dumps(value))
            except:
                pass
        parser.write(f)
        f.close()
    except Exception, e:
        pass # Fail silently
