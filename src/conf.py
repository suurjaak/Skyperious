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
@modified    02.03.2014
------------------------------------------------------------------------------
"""
from ConfigParser import RawConfigParser
import datetime
import json
import os
import sys
import urllib

import util

"""Program title, version number and version date."""
Title = "Skyperious"
Version = "3.1"
VersionDate = "02.03.2014"

if getattr(sys, "frozen", False):
    # Running as a pyinstaller executable
    ApplicationDirectory = os.path.dirname(sys.executable)
    ResourceDirectory = os.path.join(getattr(sys, "_MEIPASS", ""), "res")
else:
    ApplicationDirectory = os.path.dirname(os.path.dirname(__file__))
    ResourceDirectory = os.path.join(ApplicationDirectory, "res")

"""Name of file where FileDirectives are kept."""
ConfigFile = "%s.ini" % os.path.join(ApplicationDirectory, Title.lower())

"""List of attribute names that can be saved to and loaded from ConfigFile."""
FileDirectives = ["ConsoleHistoryCommands", "DBDoBackup",  "DBFiles",
    "ErrorsReportedOnDay", "ErrorReportsAutomatic", "ErrorReportHashes",
    "LastActivePage", "LastSearchResults", "LastSelectedFiles",
    "LastUpdateCheck", "RecentFiles", "SearchHistory", "SearchInChatInfo",
    "SearchInContacts", "SearchInMessages", "SearchUseNewTab",
    "SearchInTables", "SQLWindowTexts", "TrayIconEnabled",
    "UpdateCheckAutomatic", "WindowIconized", "WindowPosition", "WindowSize",
]
"""Map of attribute names from old version to new, retain values on upgrade."""
FileDirectiveCompatiblity = {
    "SearchInNewTab" : "SearchUseNewTab",
    "SearchInMessageBody": "SearchInMessages",
}

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
SearchInMessages = True

"""Whether to create a new tab for each search or reuse current."""
SearchUseNewTab = True

"""Whether to search in all columns of all tables."""
SearchInTables = False

"""Texts in SQL window, loaded on reopening a database {filename: text, }."""
SQLWindowTexts = {}

"""Whether the program tray icon is used."""
TrayIconEnabled = True

"""Whether the program checks for updates every UpdateCheckInterval."""
UpdateCheckAutomatic = True

"""Whether the program has been minimized and hidden."""
WindowIconized = False

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

"""Window background colour."""
BgColour = "#FFFFFF"

"""Text colour."""
FgColour = "#000000"

"""Main screen background colour."""
MainBgColour = "#FFFFFF"

"""Widget (button etc) background colour."""
WidgetColour = "#D4D0C8"

"""Default text colour for chat messages."""
MessageTextColour = "#202020"

"""Foreground colour for gauges."""
GaugeColour = "#008000"

"""Disabled text colour."""
DisabledColour = "#808080"

"""Table border colour in search help."""
HelpBorderColour = "#D4D0C8"

"""Code element text colour in search help."""
HelpCodeColour = "#006600"

"""Colour for clickable links."""
LinkColour = "#0000FF"

"""Colour for in-message links in export."""
ExportLinkColour = "#3399FF"

"""Colours for main screen database list."""
DBListBackgroundColour = "#ECF4FC"
DBListForegroundColour = "#000000"

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
SkypeLinkColour = "#3399FF"

"""Default colour in chat history."""
HistoryLineColour = "#E4E8ED"

"""Descriptive text shown in chat history searchbox."""
HistorySearchDescription = "Search for.."

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

"""Background colour for merge page HtmlWindow with scan results."""
MergeHtmlBackgroundColour = "#ECF4FC"

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

"""Skyperious homepage URL."""
HomeUrl = "http://suurjaak.github.com/Skyperious/"

"""
Width and height tuple of the avatar image, shown in chat data and export HTML
statistics."""
AvatarImageSize = (32, 32)

"""Width and height tuple of the large avatar image, shown in HTML export."""
AvatarImageLargeSize = (96, 96)

"""Length of the chat statistics plots, in pixels."""
PlotWidth = 350

"""Duration of "flashed" status message on StatusBar, in milliseconds."""
StatusFlashLength = 30000

"""How many items in the Recent Files menu."""
MaxRecentFiles = 20

"""Font files used for measuring text extent in export."""
FontXlsxFile = os.path.join(ResourceDirectory, "Carlito.ttf")
FontXlsxBoldFile = os.path.join(ResourceDirectory, "CarlitoBold.ttf")


def load():
    """Loads FileDirectives from ConfigFile into this module's attributes."""
    section = "*"
    module = sys.modules[__name__]
    parser = RawConfigParser()
    parser.optionxform = str # Force case-sensitivity on names
    try:
        parser.read(ConfigFile)

        def parse_value(name):
            try: # parser.get can throw an error if not found
                value_raw = parser.get(section, name)
            except Exception:
                return False, None
            # First, try to interpret as JSON
            try:
                value = json.loads(value_raw)
            except ValueError: # JSON failed, try to eval it
                try:
                    value = eval(value_raw)
                except SyntaxError: # Fall back to string
                    value = value_raw
            return True, value

        for oldname, name in FileDirectiveCompatiblity.items():
            [setattr(module, name, v) for s, v in [parse_value(oldname)] if s]
        for name in FileDirectives:
            [setattr(module, name, v) for s, v in [parse_value(name)] if s]
    except Exception:
        pass # Fail silently


def save():
    """Saves FileDirectives into ConfigFile."""
    section = "*"
    module = sys.modules[__name__]
    parser = RawConfigParser()
    parser.optionxform = str # Force case-sensitivity on names
    parser.add_section(section)
    try:
        f, fname = open(ConfigFile, "wb"), util.longpath(ConfigFile)
        f.write("# %s configuration autowritten on %s.\n" %
                (fname, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        for name in FileDirectives:
            try:
                value = getattr(module, name)
                parser.set(section, name, json.dumps(value))
            except Exception:
                pass
        parser.write(f)
        f.close()
    except Exception:
        pass # Fail silently
