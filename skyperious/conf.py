# -*- coding: utf-8 -*-
"""
Application settings, and functionality to save/load some of them from
an external file. Configuration file has simple INI file format,
and all values are kept in JSON.

------------------------------------------------------------------------------
This file is part of Skyperious - Skype chat history tool.
Released under the MIT License.

@author      Erki Suurjaak
@created     26.11.2011
@modified    04.08.2020
------------------------------------------------------------------------------
"""
from ConfigParser import RawConfigParser
import datetime
import json
import os
import sys

import appdirs


"""Program title, version number and version date."""
Title = "Skyperious"
Version = "4.1"
VersionDate = "04.08.2020"

if getattr(sys, "frozen", False):
    # Running as a pyinstaller executable
    ApplicationDirectory = os.path.dirname(sys.executable)
    ResourceDirectory = os.path.join(getattr(sys, "_MEIPASS", ""), "res")
else:
    ApplicationDirectory = os.path.abspath(os.path.dirname(__file__))
    ResourceDirectory = os.path.join(ApplicationDirectory, "res")

"""Directory for variable content like login tokens."""
VarDirectory = os.path.join(ApplicationDirectory, "var")

"""Name of file where FileDirectives are kept."""
ConfigFile = "%s.ini" % os.path.join(ApplicationDirectory, Title.lower())

"""List of attribute names that can be saved to and loaded from ConfigFile."""
FileDirectives = ["ConsoleHistoryCommands", "DBDoBackup",  "DBFiles", "DBSort",
    "LastActivePage", "LastSearchResults", "LastSelectedFiles",
    "LastUpdateCheck", "Login", "RecentFiles", "SearchHistory",
    "SearchInChatInfo", "SearchInContacts", "SearchInMessages",
    "SearchUseNewTab", "SearchInTables", "SQLWindowTexts", "TrayIconEnabled",
    "UpdateCheckAutomatic", "WindowIconized", "WindowPosition", "WindowSize",
]
"""List of attributes saved if changed from default."""
OptionalFileDirectives = ["EmoticonsPlotWidth", "ExportChatTemplate",
    "ExportDbTemplate", "HistoryFontSize", "LogSQL", "MinWindowSize",
    "MaxConsoleHistory", "MaxHistoryInitialMessages", "MaxRecentFiles",
    "MaxSearchHistory", "MaxSearchMessages", "MaxSearchTableRows",
    "PlotDaysColour", "PlotDaysUnitSize", "PlotHoursColour", "PlotHoursUnitSize",
    "PopupUnexpectedErrors", "SearchResultsChunk", "SharedImageAutoDownload",
    "StatisticsPlotWidth", "StatusFlashLength", "UpdateCheckInterval",
    "WordCloudLengthMin", "WordCloudCountMin", "WordCloudWordsMax",
    "WordCloudWordsAuthorMax"
]
Defaults = {}

"""---------------------------- FileDirectives: ----------------------------"""

"""Whether a backup copy is made of a database before it's changed."""
DBDoBackup = False

"""All detected/added databases."""
DBFiles = []

"""Database list sort state, [col, ascending]."""
DBSort = []

"""History of commands entered in console."""
ConsoleHistoryCommands = []

"""Is program running in command-line interface mode."""
IsCLI = False

"""Is command-line interface verbose."""
IsCLIVerbose = False

"""Index of last active page in database tab, {db path: index}."""
LastActivePage = {}

"""HTMLs of last search result, {db path: {"content", "info", "title"}}."""
LastSearchResults = {}

"""Files selected in the database lists on last run."""
LastSelectedFiles = ["", ""]

"""Skype login settings, {db path: {"store", "auto", "password"}}."""
Login = {}

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

"""Chat export filename template, format can use Skype.Conversations data."""
ExportChatTemplate = u"Skype %(title_long_lc)s"

"""Database export filename template, format can use Skype.Accounts data."""
ExportDbTemplate = u"Export from %(fullname)s"

"""Whether the program tray icon is used."""
TrayIconEnabled = True

"""Whether the program checks for updates every UpdateCheckInterval."""
UpdateCheckAutomatic = True

"""Whether the program has been minimized and hidden."""
WindowIconized = False

"""Main window position, (x, y)."""
WindowPosition = None

"""Main window size in pixels, [w, h] or [-1, -1] for maximized."""
WindowSize = (1080, 710)

"""---------------------------- /FileDirectives ----------------------------"""

"""Whether logging to log window is enabled."""
LogEnabled = True

"""Whether to log all SQL statements to log window."""
LogSQL = False

"""Whether to pop up message dialogs for unhandled errors."""
PopupUnexpectedErrors = True

"""Number of unhandled errors encountered during current runtime."""
UnexpectedErrorCount = 0

"""URLs for download list, changelog, and homepage."""
DownloadURL  = "https://erki.lap.ee/downloads/Skyperious/"
ChangelogURL = "https://suurjaak.github.io/Skyperious/changelog.html"
ReportURL    = "https://erki.lap.ee/downloads/Skyperious/feedback"
HomeUrl = "https://suurjaak.github.io/Skyperious/"

"""Maximum number of error reports sent per day."""
ErrorReportsPerDay = 5

"""Maximum number of error hashes and report days to keep."""
ErrorsStoredMax = 1000

"""Minimum allowed size for the main window, as (width, height)."""
MinWindowSize = (600, 400)

"""Console window size in pixels, (width, height)."""
ConsoleSize = (800, 300)

"""Days between automatic update checks."""
UpdateCheckInterval = 7

"""Date string of last time updates were checked."""
LastUpdateCheck = None

"""Maximum number of console history commands to store."""
MaxConsoleHistory = 1000

"""Maximum number of search texts to store."""
MaxSearchHistory = 500

"""Maximum number of messages shown initially in chat history."""
MaxHistoryInitialMessages = 1500

"""Maximum length of a tab title, overflow will be cut on the left."""
MaxTabTitleLength = 60

"""
Maximum number of messages to show in search results.
"""
MaxSearchMessages = 500

"""Maximum number of table rows to show in search results."""
MaxSearchTableRows = 500

"""Number of search results to yield in one chunk from search thread."""
SearchResultsChunk = 50

"""Name of font used in chat history."""
HistoryFontName = "Tahoma"

"""Font size in chat history."""
HistoryFontSize = 10

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

"""Foreground colour for error labels."""
LabelErrorColour = "#CC3232"

"""Color set to database table list tables that have been changed."""
DBTableChangedColour = "blue"

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

"""Colour for 24h histogram plot foreground, as HTML colour string."""
PlotHoursColour = "#2d578b"

"""Colour for date histogram plot foreground, as HTML colour string."""
PlotDaysColour = "#2d8b57"

"""24h histogram bar single rectangle size as (width, height)."""
PlotHoursUnitSize = (4, 30)

"""Date histogram bar single rectangle size as (width, height)."""
PlotDaysUnitSize = (13, 30)

"""
Width and height tuple of the avatar image, shown in chat data and export HTML
statistics."""
AvatarImageSize = (32, 32)

"""Width and height tuple of the large avatar image, shown in HTML export."""
AvatarImageLargeSize = (96, 96)

"""Width of the chat statistics plots, in pixels."""
StatisticsPlotWidth = 150

"""Width of the chat emoticons plots, in pixels."""
EmoticonsPlotWidth = 200

"""
Download shared images from Skype online service for HTML export.
"""
SharedImageAutoDownload = True

"""Duration of status message on program statusbar, in milliseconds."""
StatusFlashLength = 30000

"""How many items in the Recent Files menu."""
MaxRecentFiles = 20

"""Font files used for measuring text extent in export."""
FontXlsxFile = os.path.join(ResourceDirectory, "Carlito.ttf")
FontXlsxBoldFile = os.path.join(ResourceDirectory, "CarlitoBold.ttf")

"""Minimum length of words to include in word cloud."""
WordCloudLengthMin = 2

"""Minimum occurrence count for words to be included in word cloud."""
WordCloudCountMin = 2

"""Maximum number of words to include in word cloud."""
WordCloudWordsMax = 100

"""Maximum number of words to include in per-author word cloud."""
WordCloudWordsAuthorMax = 50


def load():
    """Loads FileDirectives from ConfigFile into this module's attributes."""
    global Defaults, VarDirectory, ConfigFile

    configpaths = [ConfigFile]
    if not Defaults:
        # Instantiate OS- and user-specific paths
        try:
            p = appdirs.user_config_dir(Title, False)
            configpaths.append(os.path.join(p, "%s.ini" % Title.lower()))
        except Exception: pass
        try: VarDirectory = appdirs.user_data_dir(Title, False)
        except Exception: pass

    section = "*"
    module = sys.modules[__name__]
    VARTYPES = (basestring, bool, int, long, list, tuple, dict, type(None))
    Defaults = {k: v for k, v in vars(module).items() if not k.startswith("_")
                and isinstance(v, VARTYPES)}

    parser = RawConfigParser()
    parser.optionxform = str # Force case-sensitivity on names
    try:
        # Try user-specific path first, then path under application folder
        for path in configpaths[::-1]:
            if os.path.isfile(path) and parser.read(ConfigFile):
                break # for path

        def parse_value(name):
            try: # parser.get can throw an error if value not found
                value_raw = parser.get(section, name)
            except Exception:
                return None, False
            try: # Try to interpret as JSON, fall back on raw string
                value = json.loads(value_raw)
            except ValueError:
                value = value_raw
            return value, True

        for name in FileDirectives:
            [setattr(module, name, v) for v, s in [parse_value(name)] if s]
        for name in OptionalFileDirectives:
            [setattr(module, name, v) for v, s in [parse_value(name)] if s]
    except Exception:
        pass # Fail silently


def save():
    """Saves FileDirectives into ConfigFile."""
    configpaths = [ConfigFile]
    try:
        p = appdirs.user_config_dir(Title, False)
        configpaths.append(os.path.join(p, "%s.ini" % Title.lower()))
    except Exception: pass

    section = "*"
    module = sys.modules[__name__]
    parser = RawConfigParser()
    parser.optionxform = str # Force case-sensitivity on names
    parser.add_section(section)
    try:
        for path in configpaths:
            # Try path under application folder first, then user-specific path
            try: os.makedirs(os.path.split(path)[0])
            except Exception: pass
            try: f = open(path, "wb")
            except Exception: continue # for path
            else: break # for path

        f.write("# %s %s configuration written on %s.\n" % (Title, Version,
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        for name in FileDirectives:
            try: parser.set(section, name, json.dumps(getattr(module, name)))
            except Exception: pass
        for name in OptionalFileDirectives:
            try:
                value = getattr(module, name, None)
                if Defaults.get(name) != value:
                    parser.set(section, name, json.dumps(value))
            except Exception: pass
        parser.write(f)
        f.close()
    except Exception:
        pass # Fail silently
