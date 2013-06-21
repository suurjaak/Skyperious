# -*- coding: utf-8 -*-
"""
Application settings, and functionality to save/load some of them from
an external file. Configuration file has simple INI file format,
and all values are kept in JSON.

@author      Erki Suurjaak
@created     26.11.2011
@modified    21.06.2013
"""
from ConfigParser import RawConfigParser
import datetime
import json
import os
import sys
import urllib
import wx

"""Program title."""
Title = "Skyperious"

Version = "1.5.1"

VersionDate = "21.06.2013"

if getattr(sys, 'frozen', False):
    # Running as a pyinstaller executable
    ApplicationDirectory = os.path.dirname(sys.executable)
    ApplicationFile = os.path.realpath(sys.executable)
else:
    ApplicationDirectory = os.path.dirname(__file__)
    ApplicationFile = os.path.join(ApplicationDirectory, "main.py")

"""List of attribute names that can be saved to and loaded from ConfigFile."""
FileDirectives = ["AllowMultipleInstances", "ConsoleHistoryCommands",
    "DBDoBackup",  "DBFiles", "ErrorsReportedOnDay", "ErrorReportsAutomatic",
    "ErrorReportHashes", "LastSelectedFiles", "LastUpdateCheck", "RecentFiles",
    "SearchInChatInfo", "SearchInContacts", "SearchInMessageBody",
    "SearchInNewTab", "SQLWindowTexts", "WindowPosition", "WindowSize",
]

"""Whether logging to log window is enabled."""
LogEnabled = True

"""URLs for download list, changelog and submitting feedback."""
DownloadURL  = "http://erki.lap.ee/downloads/Skyperious/"
ChangelogURL = "http://suurjaak.github.com/Skyperious/changelog.html"
ReportURL    = "http://erki.lap.ee/downloads/Skyperious/feedback"

"""Name of file where FileDirectives are kept."""
ConfigFile = "%s.ini" % os.path.join(ApplicationDirectory, Title.lower())

"""Whether multiple instances of Skyperious can be running."""
AllowMultipleInstances = True

"""
Port for inter-process communication, receiving data from other
launched instances if not AllowMultipleInstances.
"""
IPCPort = 59987

"""Identifier for inter-process communication."""
IPCName = urllib.quote_plus("%s-%s" % (wx.GetUserId(), ApplicationFile))

"""Whether caught errors are reported automatically to author."""
ErrorReportsAutomatic = False

"""Errors reported on day X, e.g. {'20130530': 4, '20130531': 1, }."""
ErrorsReportedOnDay = {}

"""Maximum number of error reports sent per day."""
ErrorReportsPerDay = 5

"""Saved hashes of automatically reported errors."""
ErrorReportHashes = []

"""Maximum number of error hashes and report days to keep."""
ErrorsStoredMax = 1000

"""Main window position, (x, y)."""
WindowPosition = None

"""Main window size in pixels, (w, h)."""
WindowSize = (1080, 645)

"""Console window size in pixels, (w, h)."""
ConsoleSize = (800, 300)

"""Maximum number of commands to store for console history."""
ConsoleHistoryMax = 1000

"""History of commands entered in console."""
ConsoleHistoryCommands = []

"""Files selected in the database lists on last run."""
LastSelectedFiles = ["", ""]

"""Whether to search in message body."""
SearchInMessageBody = True

"""Whether to search in chat title and participants."""
SearchInChatInfo = False

"""Whether to search in contact information."""
SearchInContacts = False

"""Whether to create a new tab for each search or reuse current."""
SearchInNewTab = False

"""Time interval to keep between update checks, a datetime.timedelta."""
UpdateCheckInterval = datetime.timedelta(days=7)

"""Date string of last time updates were checked."""
LastUpdateCheck = None

"""Texts in SQL window, loaded on reopening a database {filename: text, }."""
SQLWindowTexts = {}

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
SearchMessagesMax = 1000

"""How many search results to yield in one chunk from search thread."""
SearchResultsChunk = 50

"""How many diff results to yield in one chunk from diff thread."""
DiffResultsChunk = 5

"""
How many contact search results to yield in one chunk from contacts search
thread.
"""
ContactResultsChunk = 10

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

"""Colour used for contact field names in search results."""
ResultContactFieldColour = "#727272"

"""Background colour of opened items in lists."""
ListOpenedBgColour = "pink"

"""Color set to database file list rows that have been opened."""
DBFileOpenedColour = "blue"

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

"""Copyright symbol and year string."""
CopyrightSymbol = u"\xA9"

"""Copyright symbol and year string."""
Copyright = u"%s 2011-2013" % CopyrightSymbol

"""Text shown in Help -> About dialog (HTML content)."""
AboutText = """
<font size='2' face='Tahoma'>
<table cellpadding='0' cellspacing='0'><tr><td valign='top'>
<img src="memory:skyperious.png" /></td><td width='10'></td><td valign='center'>
<b>%(name)s version %(ver)s</b>, released %(date)s.<br /><br />

%(name)s is written in Python, released as free open source software
under the MIT License.
</td></tr></table><br /><br />


%(copyright)s, Erki Suurjaak.
<a href='%(link)s'>suurjaak.github.com/Skyperious</a><br /><br /><br />



%(name)s has been built using the following open source software:
<ul>
<li>wxPython 2.9.4, <a href='http://wxpython.org'>wxpython.org</a></li>
<li>BeautifulSoup 3.2.1, <a href='http://crummy.com/software/BeautifulSoup'>
    crummy.com/software/BeautifulSoup</a></li>
<li>step, Simple Template Engine for Python,
    <a href='https://github.com/dotpy/step'>github.com/dotpy/step</a></li>
<li>dateutil, <a href='https://pypi.python.org/pypi/python-dateutil'>
    pypi.python.org/pypi/python-dateutil</a></li>
<li>Skype4Py, <a href='https://github.com/awahlig/skype4py'>
    github.com/awahlig/skype4py</a></li>
%(plus)s
</ul><br /><br /><br />



Emoticons in HTML export are property of Skype Limited, %(copy)s 2004-2006,
released under the Skype Component License 1.0.<br /><br />


Default avatar icon from Fancy Avatars, %(copy)s 2009 Brandon Mathis<br />
<a href='http://brandonmathis.com/projects/fancy-avatars/'>
brandonmathis.com/projects/fancy-avatars</a><br /><br />


Several toolbar icons from Fugue Icons, %(copy)s 2010 Yusuke Kamiyamane<br />
<a href='http://p.yusukekamiyamane.com/'>p.yusukekamiyamane.com/</a>
</font>
""" % {"copy": CopyrightSymbol, "copyright": Copyright, "ver": Version,
       "date": VersionDate, "name": Title, "link": HomeUrl,
       "plus": "<li>Python 2.7.5, <a href='http://www.python.org'>" \
               "www.python.org</a></li>" \
               "<li>PyInstaller 2.0, <a href='http://www.pyinstaller.org'>" \
               "www.pyinstaller.org</a></li>"
               if getattr(sys, 'frozen', False) else ""
}

"""Information text shown on the first page."""
InfoText = """
Open a Skype message database to browse its contents, search over all chats, export chats as HTML.
Select two databases to compare their chats, and restore missing messages.

Creating a backup of the database file is recommended before making any changes.""" % {
    "title": Title, "ver": Version, "date": VersionDate}

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

"""Size of the messages plot in chat statistics, as (w, h)."""
MessagePlotSize = (450, 300)

"""Duration of "flashed" status message on StatusBar, in milliseconds."""
StatusFlashLength = 30000

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
