# -*- coding: utf-8 -*-
"""
Application settings, and functionality to save/load some of them from
an external file. Configuration file has simple INI file format,
and all values are kept in JSON.

------------------------------------------------------------------------------
This file is part of Skyperious - a Skype database viewer and merger.
Released under the MIT License.

@author      Erki Suurjaak
@created     26.11.2011
@modified    20.09.2013
------------------------------------------------------------------------------
"""
from ConfigParser import RawConfigParser
import datetime
import json
import os
import sys
import urllib
import wx

"""Program title, version number and version date."""
Title = "Skyperious"
Version = "2.1.2"
VersionDate = "20.09.2013"

if getattr(sys, 'frozen', False):
    # Running as a pyinstaller executable
    ApplicationDirectory = os.path.dirname(sys.executable)
    ApplicationFile = os.path.realpath(sys.executable)
else:
    ApplicationDirectory = os.path.dirname(os.path.dirname(__file__))
    ApplicationFile = os.path.join(ApplicationDirectory, "main.py")

"""Name of file where FileDirectives are kept."""
ConfigFile = "%s.ini" % os.path.join(ApplicationDirectory, Title.lower())

"""List of attribute names that can be saved to and loaded from ConfigFile."""
FileDirectives = ["ConsoleHistoryCommands", "DBDoBackup",  "DBFiles",
    "ErrorsReportedOnDay", "ErrorReportsAutomatic", "ErrorReportHashes",
    "LastActivePage", "LastSearchResults", "LastSelectedFiles",
    "LastUpdateCheck", "RecentFiles", "SearchHistory", "SearchInChatInfo",
    "SearchInContacts", "SearchInMessageBody", "SearchInNewTab",
    "SearchInTables", "SQLWindowTexts", "WindowPosition", "WindowSize",
]

"""---------------------------- FileDirectives: ----------------------------"""

"""Whether a backup copy is made of a database before it's changed."""
DBDoBackup = False

"""All detected/added databases."""
DBFiles = []

"""History of commands entered in console."""
ConsoleHistoryCommands = []

"""Whether caught errors are reported automatically to author."""
ErrorReportsAutomatic = False

"""Errors reported on day X, e.g. {'20130530': 4, '20130531': 1, }."""
ErrorsReportedOnDay = {}

"""Saved hashes of automatically reported errors."""
ErrorReportHashes = []

"""Index of last active page in database tab, {db path: index}."""
LastActivePage = {}

"""HTMLs of last search result, {db path: {"content", "info", "title"}}."""
LastSearchResults = {}

"""Files selected in the database lists on last run."""
LastSelectedFiles = ["", ""]

"""Contents of Recent Files menu."""
RecentFiles = []

"""
Texts entered in chat global search, used for drop down auto-complete.
Last value can be an empty string: search box had no text.
"""
SearchHistory = []

"""Whether to search in chat title and participants."""
SearchInChatInfo = False

"""Whether to search in contact information."""
SearchInContacts = False

"""Whether to search in message body."""
SearchInMessageBody = True

"""Whether to create a new tab for each search or reuse current."""
SearchInNewTab = True

"""Whether to search in all columns of all tables."""
SearchInTables = False

"""Texts in SQL window, loaded on reopening a database {filename: text, }."""
SQLWindowTexts = {}

"""Main window position, (x, y)."""
WindowPosition = None

"""Main window size in pixels, [w, h] or [-1, -1] for maximized."""
WindowSize = [1080, 710]

"""---------------------------- /FileDirectives ----------------------------"""

"""Whether logging to log window is enabled."""
LogEnabled = True

"""Whether to log all SQL statements."""
LogSQL = False

"""URLs for download list, changelog and submitting feedback."""
DownloadURL  = "http://erki.lap.ee/downloads/Skyperious/"
ChangelogURL = "http://suurjaak.github.com/Skyperious/changelog.html"
ReportURL    = "http://erki.lap.ee/downloads/Skyperious/feedback"

"""Maximum number of error reports sent per day."""
ErrorReportsPerDay = 5

"""Maximum number of error hashes and report days to keep."""
ErrorsStoredMax = 1000

"""Minimum allowed size of the main window (w, h)."""
WindowSizeMin = (950, 650) if "linux2" != sys.platform else (950, 810)

"""Console window size in pixels, (w, h)."""
ConsoleSize = (800, 300)

"""Maximum number of commands to store for console history."""
ConsoleHistoryMax = 1000

"""Maximum number of search texts to remember."""
SearchHistoryMax = 500

"""Time interval to keep between update checks, a datetime.timedelta."""
UpdateCheckInterval = datetime.timedelta(days=7)

"""Date string of last time updates were checked."""
LastUpdateCheck = None

"""
Maximum number of messages shown in the chat history initially, before user
filtering.
"""
MaxHistoryInitialMessages = 1500

"""Maximum length of a tab title, overflow will be cut on the left."""
MaxTabTitleLength = 60

"""
Maximum number of messages to show in search results (wx.html.HtmlWindow has
trouble showing long documents).
"""
SearchMessagesMax = 500

"""Maximum number of table rows to show in search results."""
SearchTableRowsMax = 500

"""How many search results to yield in one chunk from search thread."""
SearchResultsChunk = 50

"""
How many contact search results to yield in one chunk from contacts search
thread.
"""
ContactResultsChunk = 10

"""Name of font used in chat history."""
HistoryFontName = "Tahoma"

"""Font size in chat history."""
HistoryFontSize = 8

"""Foreground colour for gauges."""
GaugeColour = "#008000"

DBListBackgroundColour = "#ECF4FC"

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

"""Colour used for contact field names in search results."""
ResultContactFieldColour = "#727272"

"""Background colour of opened items in lists."""
ListOpenedBgColour = "pink"

"""Foreground colour for error labels."""
LabelErrorColour = "#CC3232"

"""Color set to database table list tables that have been changed."""
DBTableChangedColour = "red"

"""Color set to the database table list table that is currently open."""
DBTableOpenedColour = "pink"

"""Colour set to table/list rows that have been changed."""
GridRowChangedColour = "#FFCCCC"

"""Colour set to table/list rows that have been inserted."""
GridRowInsertedColour = "#88DDFF"

"""Colour set to table/list cells that have been changed."""
GridCellChangedColour = "#FF7777"

"""Colour set to chat diff list rows with identical sides."""
DiffIdenticalColour = "#666666"

"""Skyperious homepage URL."""
HomeUrl = "http://suurjaak.github.com/Skyperious/"

"""Background colour for merge page HtmlWindow with scan results."""
MergeHtmlBackgroundColour = "#ECF4FC"

"""
Width and height tuple of the avatar image, shown in chat data and export HTML
statistics."""
AvatarImageSize = (32, 32)

"""Width and height tuple of the large avatar image, shown in HTML export."""
AvatarImageLargeSize = (96, 96)

"""Colour for messages plot in chat statistics."""
PlotMessagesColour = "#3399FF"

"""Colour for SMSes plot in chat statistics."""
PlotSMSesColour = "#FFB333"

"""Colour for calls plot in chat statistics."""
PlotCallsColour = "#FF6C91"

"""Colour for files plot in chat statistics."""
PlotFilesColour = "#33DD66"

"""Background colour for plots in chat statistics."""
PlotBgColour = "#DDDDDD"

"""Length of the chat statistics plots, in pixels."""
PlotWidth = 350

"""Duration of "flashed" status message on StatusBar, in milliseconds."""
StatusFlashLength = 30000

"""How many items in the Recent Files menu."""
MaxRecentFiles = 20


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
