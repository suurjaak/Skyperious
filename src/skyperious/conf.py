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
@modified    10.05.2025
------------------------------------------------------------------------------
"""
try: from ConfigParser import RawConfigParser                 # Py2
except ImportError: from configparser import RawConfigParser  # Py3
import copy
import datetime
import json
import os
import sys

try: import appdirs
except ImportError: appdirs = None

"""Program title, version number and version date."""
Title = "Skyperious"
Version = "5.9.1"
VersionDate = "10.05.2025"

Frozen, Snapped = getattr(sys, "frozen", False), (sys.executable or "").startswith("/snap/")
if Frozen:
    # Running as a pyinstaller executable
    ApplicationDirectory = os.path.dirname(sys.executable)
    ResourceDirectory = os.path.join(getattr(sys, "_MEIPASS", ""), "res")
else:
    ApplicationDirectory = os.path.abspath(os.path.dirname(__file__))
    ResourceDirectory = os.path.join(ApplicationDirectory, "res")

"""Directory for variable content like login tokens and created databases."""
VarDirectory = os.path.join(ApplicationDirectory, "var")

"""Name of file where FileDirectives are kept."""
ConfigFile = "%s.ini" % os.path.join(ApplicationDirectory, Title.lower())

"""Whether to ignore user-specific config paths."""
ConfigFileStatic = False

"""List of attribute names that can be saved to and loaded from ConfigFile."""
FileDirectives = ["ConsoleHistoryCommands", "DBDoBackup",  "DBFiles", "DBSort",
    "LastActivePage", "LastSearchResults", "LastSelectedFiles",
    "LastUpdateCheck", "Login", "RecentFiles", "SearchHistory",
    "SearchInChatInfo", "SearchInContacts", "SearchInMessages",
    "SearchInTables", "SearchUseNewTab", "SQLWindowTexts", "TrayIconEnabled",
    "UpdateCheckAutomatic", "WindowIconized", "WindowPosition", "WindowSize",
]
"""List of attributes saved if changed from default."""
OptionalFileDirectives = [
    "EmoticonsPlotWidth", "ExportChatTemplate", "ExportContactsTemplate", "ExportDbTemplate",
    "ExportFileAutoOpen", "HistoryFontSize", "HistoryZoom", "LiveSyncAutoDownload",
    "LiveSyncAuthRateLimitDelay", "LiveSyncRateLimit", "LiveSyncRateWindow", "LiveSyncRetryDelay",
    "LiveSyncRetryLimit", "LogFile", "LogSQL", "LogToFile", "MaxConsoleHistory",
    "MaxHistoryInitialMessages", "MaxRecentFiles", "MaxSearchHistory", "MaxSearchMessages",
    "MaxSearchTableRows", "MinWindowSize", "PlotDaysColour", "PlotDaysUnitSize", "PlotHoursColour",
    "PlotHoursUnitSize", "PopupUnexpectedErrors", "SearchResultsChunk",
    "SharedAudioVideoAutoDownload", "SharedContentPromptAutoLogin", "SharedFileAutoDownload",
    "SharedImageAutoDownload", "ShareDirectoryEnabled", "ShareDirectoryTemplate",
    "StatisticsPlotWidth", "StatusFlashLength", "UpdateCheckInterval", "WordCloudCountMin",
    "WordCloudLengthMin", "WordCloudWordsAuthorMax", "WordCloudWordsMax",
]
Defaults = {}

"""---------------------------- FileDirectives: ----------------------------"""

"""History of commands entered in console."""
ConsoleHistoryCommands = []

"""Whether a backup copy is made of a database before it's changed."""
DBDoBackup = False

"""All detected/added databases."""
DBFiles = []

"""Database list sort state, [col, ascending]."""
DBSort = []

"""Index of last active page in database tab, {db path: index}."""
LastActivePage = {}

"""HTMLs of last search result, {db path: {"content", "info", "title"}}."""
LastSearchResults = {}

"""Files selected in the database lists on last run."""
LastSelectedFiles = []

"""Date string of last time updates were checked."""
LastUpdateCheck = None

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

"""Whether to search in all columns of all tables."""
SearchInTables = False

"""Whether to create a new tab for each search or reuse current."""
SearchUseNewTab = True

"""Texts in SQL window, loaded on reopening a database {filename: text, }."""
SQLWindowTexts = {}

"""Whether the program tray icon is used."""
TrayIconEnabled = True

"""Whether the program checks for updates every UpdateCheckInterval if UpdateCheckEnabled."""
UpdateCheckAutomatic = True

"""Whether the program has been minimized and hidden."""
WindowIconized = False

"""Main window position, (x, y)."""
WindowPosition = None

"""Main window size in pixels, [w, h] or [-1, -1] for maximized."""
WindowSize = (1080, 710)

"""---------------------------- /FileDirectives ----------------------------"""

"""------------------------ OptionalFileDirectives: ------------------------"""

"""Width of the chat emoticons plots, in pixels."""
EmoticonsPlotWidth = 200

"""Chat export filename template, format can use Skype.Conversations data."""
ExportChatTemplate = u"Skype %(title_long_lc)s"

"""Database contacts export filename template, format can use Skype.Accounts data."""
ExportContactsTemplate = u"Skype contacts for %(name)s"

"""Database export filename template, format can use Skype.Accounts data."""
ExportDbTemplate = u"Export from %(name)s"

"""Automatically open exported files and directories in registered application."""
ExportFileAutoOpen = True

"""Font size in chat history."""
HistoryFontSize = 10

"""Text zoom level in chat history, defaults to 1.0 (100%)."""
HistoryZoom = 1.0

"""Sleep interval upon hitting server rate limit, in seconds."""
LiveSyncAuthRateLimitDelay = 20

"""Download shared files and media to local share folder automatically during live sync."""
LiveSyncAutoDownload = True

"""Max number of requests in rate window."""
LiveSyncRateLimit = 10

"""Length of rate window, in seconds."""
LiveSyncRateWindow = 60

"""Sleep interval between retries, in seconds."""
LiveSyncRetryDelay = 20

"""Number of attempts to overcome rate limit and transient I/O errors."""
LiveSyncRetryLimit = 3

"""Path to log file on disk."""
LogFile = os.path.join(VarDirectory, "%s.log" % Title.lower())

"""Whether to log all SQL statements to log window."""
LogSQL = False

"""Whether to write log to file as well."""
LogToFile = True

"""Maximum number of console history commands to store."""
MaxConsoleHistory = 1000

"""Maximum number of messages shown initially in chat history."""
MaxHistoryInitialMessages = 1500

"""How many items in the Recent Files menu."""
MaxRecentFiles = 20

"""Maximum number of search texts to store."""
MaxSearchHistory = 500

"""Maximum number of messages to show in search results."""
MaxSearchMessages = 500

"""Maximum number of table rows to show in search results."""
MaxSearchTableRows = 500

"""Minimum allowed size for the main window, as (width, height)."""
MinWindowSize = (600, 400)

"""Colour for date histogram plot foreground, as HTML colour string."""
PlotDaysColour = "#2d8b57"

"""Date histogram bar single rectangle size as (width, height)."""
PlotDaysUnitSize = (13, 30)

"""Colour for 24h histogram plot foreground, as HTML colour string."""
PlotHoursColour = "#2d578b"

"""24h histogram bar single rectangle size as (width, height)."""
PlotHoursUnitSize = (4, 30)

"""Whether to pop up message dialogs for unhandled errors."""
PopupUnexpectedErrors = True

"""Number of search results to yield in one chunk from search thread."""
SearchResultsChunk = 50

"""Download shared audio & video from Skype online service for HTML export."""
SharedAudioVideoAutoDownload = True

"""Prompt to log in to Skype online automatically to download shared content during export."""
SharedContentPromptAutoLogin = False

"""Download shared files from Skype online service for HTML export."""
SharedFileAutoDownload = True

"""Download shared images from Skype online service for HTML export."""
SharedImageAutoDownload = True

"""Use local folder for storing files shared in chats."""
ShareDirectoryEnabled = True

"""Template for local shared files folder name, format can use "filename" parameter."""
ShareDirectoryTemplate = "%(filename)s files"

"""Width of the chat statistics plots, in pixels."""
StatisticsPlotWidth = 150

"""Duration of status message on program statusbar, in milliseconds."""
StatusFlashLength = 30000

"""Days between automatic update checks."""
UpdateCheckInterval = 7

"""Minimum occurrence count for words to be included in word cloud."""
WordCloudCountMin = 2

"""Minimum length of words to include in word cloud."""
WordCloudLengthMin = 2

"""Maximum number of words to include in per-author word cloud."""
WordCloudWordsAuthorMax = 50

"""Maximum number of words to include in word cloud."""
WordCloudWordsMax = 100

"""------------------------ /OptionalFileDirectives ------------------------"""

"""Is program running in command-line interface mode."""
IsCLI = False

"""Is command-line interface verbose."""
IsCLIVerbose = False

"""
Is command-line interface using output suitable for non-terminals
like piping to a file, skips progress bars and user interaction.
"""
IsCLINonTerminal = True

"""Whether logging to log window is enabled."""
LogEnabled = True

"""Number of unhandled errors encountered during current runtime."""
UnexpectedErrorCount = 0

"""URLs for download list, changelog, and homepage."""
DownloadURL  = "https://erki.lap.ee/downloads/Skyperious/"
ChangelogURL = "https://suurjaak.github.io/Skyperious/changelog.html"
ReportURL    = "https://erki.lap.ee/downloads/Skyperious/feedback"
HomeURL      = "https://suurjaak.github.io/Skyperious/"

"""Maximum number of error reports sent per day."""
ErrorReportsPerDay = 5

"""Maximum number of error hashes and report days to keep."""
ErrorsStoredMax = 1000

"""Console window size in pixels, (width, height)."""
ConsoleSize = (800, 300)

"""Whether the program supports automatic update check and download."""
UpdateCheckEnabled = True

"""Maximum length of a tab title, overflow will be cut on the left."""
MaxTabTitleLength = 60

"""Name of font used in chat history."""
HistoryFontName = "Tahoma"

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

"""Colour for shares plot in chat statistics."""
PlotSharesColour = "#FFB333"

"""Background colour for plots in chat statistics."""
PlotBgColour = "#DDDDDD"

"""
Width and height tuple of the avatar image, shown in chat data and export HTML
statistics."""
AvatarImageSize = (32, 32)

"""Width and height tuple of the large avatar image, shown in HTML export."""
AvatarImageLargeSize = (96, 96)

"""
Earliest message date to download shared content from Skype online service.
Content from Skype's peer-to-peer era is unavailable for download.
"""
SharedContentDownloadMinDate = datetime.datetime(2017, 4, 1)

"""Font files used for measuring text extent in export."""
FontXlsxFile = os.path.join(ResourceDirectory, "Carlito.ttf")
FontXlsxBoldFile = os.path.join(ResourceDirectory, "CarlitoBold.ttf")

"""Path for licences of bundled open-source software."""
LicenseFile = os.path.join(ResourceDirectory, "3rd-party licenses.txt") \
              if Frozen or Snapped else None


def load(configfile=None):
    """
    Loads FileDirectives into this module's attributes.

    @param   configfile  name of configuration file to use from now if not module defaults
    """
    global Defaults, VarDirectory, LogFile, ConfigFile, ConfigFileStatic

    try: VARTYPES = (basestring, bool, float, int, long, list, tuple, dict, type(None))        # Py2
    except Exception: VARTYPES = (bytes, str, bool, float, int, list, tuple, dict, type(None)) # Py3

    def safecopy(v):
        """Tries to return a deep copy, or a shallow copy, or given value if copy fails."""
        for f in (copy.deepcopy, copy.copy, lambda x: x):
            try: return f(v)
            except Exception: pass

    if configfile:
        ConfigFile, ConfigFileStatic = configfile, True
    configpaths = [ConfigFile]
    if not Defaults and not ConfigFileStatic:
        # Instantiate OS- and user-specific paths
        title = Title if "nt" == os.name else Title.lower()
        try:
            p = appdirs.user_config_dir(title, appauthor=False)
            userpath = os.path.join(p, "%s.ini" % Title.lower())
            # Try user-specific path first, then path under application folder
            if userpath not in configpaths: configpaths.insert(0, userpath)
        except Exception: pass
        try:
            VarDirectory = appdirs.user_data_dir(title, appauthor=False)
            LogFile = os.path.join(VarDirectory, "%s.log" % Title.lower())
        except Exception: pass

    section = "*"
    module = sys.modules[__name__]
    Defaults = {k: safecopy(v) for k, v in vars(module).items()
                if not k.startswith("_") and isinstance(v, VARTYPES)}

    parser = RawConfigParser()
    parser.optionxform = str # Force case-sensitivity on names
    try:
        for path in configpaths:
            if os.path.isfile(path) and parser.read(path):
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

        for name in FileDirectives + OptionalFileDirectives:
            [setattr(module, name, v) for v, s in [parse_value(name)] if s]
    except Exception:
        pass # Fail silently


def save(configfile=None):
    """
    Saves FileDirectives into configuration file.

    @param   configfile  name of configuration file to use if not module defaults
    """
    configpaths = [configfile] if configfile else [ConfigFile]
    if not configfile and not ConfigFileStatic:
        title = Title if "nt" == os.name else Title.lower()
        try:
            p = appdirs.user_config_dir(title, appauthor=False)
            userpath = os.path.join(p, "%s.ini" % Title.lower())
            # Pick only userpath if exists, else try application folder first
            if os.path.isfile(userpath): configpaths = [userpath]
            elif userpath not in configpaths: configpaths.append(userpath)
        except Exception: pass

    section = "*"
    module = sys.modules[__name__]
    parser = RawConfigParser()
    parser.optionxform = str # Force case-sensitivity on names
    parser.add_section(section)
    try:
        for path in configpaths:
            try: os.makedirs(os.path.dirname(path))
            except Exception: pass
            try: f = open(path, "w")
            except Exception: continue # for path
            else: break # for path

        f.write("# %s configuration written on %s.\n" %
                (Title, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
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
