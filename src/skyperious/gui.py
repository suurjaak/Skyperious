# -*- coding: utf-8 -*-
"""
Skyperious UI application main window class and project-specific UI classes.

------------------------------------------------------------------------------
This file is part of Skyperious - Skype chat history tool.
Released under the MIT License.

@author      Erki Suurjaak
@created     26.11.2011
@modified    02.04.2022
------------------------------------------------------------------------------
"""
import ast
import calendar
import collections
import copy
import datetime
import functools
import hashlib
import inspect
import logging
import math
import os
import re
import shutil
import string
import sys
import textwrap
import time
import traceback
import webbrowser

import six
from six.moves import urllib
import wx
import wx.adv
import wx.grid
import wx.html
import wx.lib
import wx.lib.agw.fmresources
import wx.lib.agw.genericmessagedialog
import wx.lib.agw.labelbook
import wx.lib.agw.flatmenu
import wx.lib.agw.flatnotebook
import wx.lib.agw.ultimatelistctrl
import wx.lib.gizmos
import wx.lib.newevent
import wx.lib.scrolledpanel
import wx.stc

from . lib import controls
from . lib.controls import ColourManager
from . lib import util
from . lib import wx_accel
from . lib.vendor import step

from . import conf
from . import emoticons
from . import export
from . import guibase
from . import images
from . import live
from . import skypedata
from . import support
from . import templates
from . import workers


"""Custom application events for worker results."""
WorkerEvent, EVT_WORKER = wx.lib.newevent.NewEvent()
DetectionWorkerEvent, EVT_DETECTION_WORKER = wx.lib.newevent.NewEvent()
OpenDatabaseEvent, EVT_OPEN_DATABASE = wx.lib.newevent.NewEvent()

logger = logging.getLogger(__name__)


class MainWindow(guibase.TemplateFrameMixIn, wx.Frame):
    """Skyperious main window."""

    TRAY_ICON = (images.Icon16x16_32bit if "linux" not in sys.platform 
                 else images.Icon24x24_32bit)

    def __init__(self):
        wx.Frame.__init__(self, parent=None, title=conf.Title, size=conf.WindowSize)
        guibase.TemplateFrameMixIn.__init__(self)

        ColourManager.Init(self, conf, colourmap={
            "FgColour":                  wx.SYS_COLOUR_BTNTEXT,
            "BgColour":                  wx.SYS_COLOUR_WINDOW,
            "DisabledColour":            wx.SYS_COLOUR_GRAYTEXT,
            "MainBgColour":              wx.SYS_COLOUR_WINDOW,
            "WidgetColour":              wx.SYS_COLOUR_BTNFACE,
        }, darkcolourmap={
            "DBListForegroundColour":    wx.SYS_COLOUR_BTNTEXT,
            "DBListBackgroundColour":    wx.SYS_COLOUR_WINDOW,
            "LinkColour":                wx.SYS_COLOUR_HOTLIGHT,
            "SkypeLinkColour":           wx.SYS_COLOUR_HOTLIGHT,
            "MessageTextColour":         wx.SYS_COLOUR_BTNTEXT,
            "MainBgColour":              wx.SYS_COLOUR_BTNFACE,
            "HelpCodeColour":            wx.SYS_COLOUR_HIGHLIGHT,
            "HelpBorderColour":          wx.SYS_COLOUR_ACTIVEBORDER,
            "MergeHtmlBackgroundColour": wx.SYS_COLOUR_WINDOW,
        })

        self.db_filename = None # Current selected file in main list
        self.db_filenames = {}  # added DBs {filename: {size, last_modified,
                                #            account, chats, messages, error},}
        self.dbs = {}           # Open databases {filename: SkypeDatabase, }
        self.db_pages = {}      # {DatabasePage: SkypeDatabase, }
        self.db_filter = "" # Current database list filter
        self.db_filter_timer = None # Database list filter callback timer
        self.merger_pages = {}  # {MergerPage: (SkypeDatabase, SkypeDatabase),}
        self.page_merge_latest = None # Last opened merger page
        self.page_db_latest = None    # Last opened database page
        # List of Notebook pages user has visited, used for choosing page to
        # show when closing one.
        self.pages_visited = []
        self.db_drag_start = None

        icons = images.get_appicons()
        self.SetIcons(icons)

        self.trayicon = wx.adv.TaskBarIcon()
        if self.trayicon.IsAvailable():
            if conf.TrayIconEnabled:
                self.trayicon.SetIcon(self.TRAY_ICON.Icon, conf.Title)
            self.trayicon.Bind(wx.adv.EVT_TASKBAR_LEFT_DCLICK, self.on_toggle_iconize)
            self.trayicon.Bind(wx.adv.EVT_TASKBAR_LEFT_DOWN, self.on_open_tray_search)
            self.trayicon.Bind(wx.adv.EVT_TASKBAR_RIGHT_DOWN, self.on_open_tray_menu)
        else:
            conf.WindowIconized = False

        panel = self.panel_main = wx.Panel(self)
        sizer = panel.Sizer = wx.BoxSizer(wx.VERTICAL)

        self.frame_console.SetIcons(icons)

        notebook = self.notebook = wx.lib.agw.flatnotebook.FlatNotebook(
            parent=panel, style=wx.NB_TOP,
            agwStyle=wx.lib.agw.flatnotebook.FNB_NODRAG |
                     wx.lib.agw.flatnotebook.FNB_NO_X_BUTTON |
                     wx.lib.agw.flatnotebook.FNB_MOUSE_MIDDLE_CLOSES_TABS |
                     wx.lib.agw.flatnotebook.FNB_NO_TAB_FOCUS |
                     wx.lib.agw.flatnotebook.FNB_FF2)
        ColourManager.Manage(notebook, "ActiveTabColour",        wx.SYS_COLOUR_WINDOW)
        ColourManager.Manage(notebook, "ActiveTabTextColour",    wx.SYS_COLOUR_BTNTEXT)
        ColourManager.Manage(notebook, "NonActiveTabTextColour", wx.SYS_COLOUR_BTNTEXT)
        ColourManager.Manage(notebook, "TabAreaColour",          wx.SYS_COLOUR_BTNFACE)
        ColourManager.Manage(notebook, "GradientColourBorder",   wx.SYS_COLOUR_BTNSHADOW)
        ColourManager.Manage(notebook, "GradientColourTo",       wx.SYS_COLOUR_ACTIVECAPTION)
        ColourManager.Manage(notebook, "ForegroundColour",       wx.SYS_COLOUR_BTNTEXT)
        ColourManager.Manage(notebook, "BackgroundColour",       wx.SYS_COLOUR_WINDOW)

        self.create_page_main(notebook)
        self.page_log = self.create_log_panel(notebook)
        notebook.AddPage(self.page_log, "Log")
        notebook.RemovePage(self.notebook.GetPageCount() - 1) # Hide log window
        # Kludge for being able to close log window repeatedly, as DatabasePage
        # or MergerPage get automatically deleted on closing.
        self.page_log.is_hidden = True

        sizer.Add(notebook, proportion=1, flag=wx.GROW | wx.RIGHT | wx.BOTTOM)
        self.create_menu()

        self.dialog_selectfolder = wx.DirDialog(parent=self,
            message="Choose a directory where to search for databases",
            style=wx.DD_DIR_MUST_EXIST | wx.RESIZE_BORDER)
        self.dialog_openfile = wx.FileDialog(
            parent=self, message="Open database",
            wildcard="SQLite database (*.db)|*.db|All files|*.*",
            style=wx.FD_FILE_MUST_EXIST | wx.FD_OPEN | wx.RESIZE_BORDER)
        self.dialog_openexport = wx.FileDialog(
            parent=self, message="Open Skype export archive",
            wildcard="Skype export (*.json;*.tar)|*.json;*.tar|"
                     "JSON file (*.json)|*.json|TAR archive (*.tar)|*.tar|"
                     "All files|*.*",
            style=wx.FD_FILE_MUST_EXIST | wx.FD_OPEN | wx.RESIZE_BORDER)
        self.dialog_savefile = wx.FileDialog(
            parent=self, style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT | wx.RESIZE_BORDER)
        # Need separate dialog w/o overwrite prompt, cannot swap style in Linux
        self.dialog_savefile_ow = wx.FileDialog(
            parent=self, style=wx.FD_SAVE | wx.RESIZE_BORDER)
        self.dialog_search = controls.EntryDialog(
            parent=self, title="Find in %s" % conf.Title, label="Search:",
            emptyvalue="Find in last database..",
            tooltip="Find in last database..")
        self.dialog_search.Bind(wx.EVT_COMMAND_ENTER, self.on_tray_search)
        if conf.SearchHistory and conf.SearchHistory[-1:] != [""]:
            self.dialog_search.Value = conf.SearchHistory[-1]
        self.dialog_search.SetChoices(list(filter(bool, conf.SearchHistory)))
        self.dialog_search.SetIcons(icons)

        # Memory file system for showing images in wx.HtmlWindow
        self.memoryfs = {"files": {}, "handler": wx.MemoryFSHandler()}
        wx.FileSystem.AddHandler(self.memoryfs["handler"])
        self.load_fs_images()
        self.adapt_colours()

        self.worker_detection = \
            workers.DetectDatabaseThread(self.on_detect_databases_callback)
        self.workers_import = {} # [database path: SkypeArchiveThread, ]
        self.Bind(EVT_DETECTION_WORKER, self.on_detect_databases_result)
        self.Bind(EVT_OPEN_DATABASE, self.on_open_database_event)

        self.Bind(wx.EVT_SYS_COLOUR_CHANGED, self.on_sys_colour_change)
        self.Bind(wx.EVT_CLOSE, self.on_exit)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_MOVE, self.on_move)
        notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_change_page)
        notebook.Bind(wx.lib.agw.flatnotebook.EVT_FLATNOTEBOOK_PAGE_CLOSING,
                      self.on_close_page)

        # Register Ctrl-F4 and Ctrl-W close handlers, and Ctrl-1..9 tab handlers
        def on_close_hotkey(event):
            notebook and notebook.DeletePage(notebook.GetSelection())
        def on_tab_hotkey(number, event):
            if notebook and notebook.GetSelection() != number \
            and number < notebook.GetPageCount():
                notebook.SetSelection(number)
                self.on_change_page(None)

        id_close = wx.NewIdRef().Id
        accelerators = [(wx.ACCEL_CMD, k, id_close) for k in (ord('W'), wx.WXK_F4)]
        for i in range(9):
            id_tab = wx.NewIdRef().Id
            accelerators += [(wx.ACCEL_CMD, ord(str(i + 1)), id_tab)]
            notebook.Bind(wx.EVT_MENU, functools.partial(on_tab_hotkey, i), id=id_tab)
        notebook.SetAcceleratorTable(wx.AcceleratorTable(accelerators))
        notebook.Bind(wx.EVT_MENU, on_close_hotkey, id=id_close)


        class FileDrop(wx.FileDropTarget):
            """A simple file drag-and-drop handler for application window."""
            def __init__(self, window):
                wx.FileDropTarget.__init__(self)
                self.window = window

            def OnDropFiles(self, x, y, filenames):
                # CallAfter to allow UI to clear up the dragged icons
                wx.CallAfter(self.ProcessFiles, filenames)
                return True

            def ProcessFiles(self, filenames):
                for filename in filenames:
                    self.window.update_database_list(filename)
                for filename in filenames:
                    self.window.load_database_page(filename)

        self.DropTarget = FileDrop(self)
        self.notebook.DropTarget = FileDrop(self)

        self.MinSize = conf.MinWindowSize
        if conf.WindowPosition and conf.WindowSize:
            if [-1, -1] != conf.WindowSize:
                self.Size = conf.WindowSize
                if not conf.WindowIconized:
                    self.Position = conf.WindowPosition
            else:
                self.Maximize()
        else:
            self.Center(wx.HORIZONTAL)
            self.Position.top = 50
        if self.list_db.GetItemCount() > 1:
            self.list_db.SetFocus()

        if conf.WindowIconized:
            conf.WindowIconized = False
            wx.CallAfter(self.on_toggle_iconize)
        else:
            self.Show(True)
        wx.CallLater(20000, self.update_check)
        wx.CallLater(1, self.populate_database_list)


    def create_page_main(self, notebook):
        """Creates the main page with database list and buttons."""
        page = self.page_main = wx.Panel(notebook)
        ColourManager.Manage(page, "BackgroundColour", "MainBgColour")
        notebook.AddPage(page, "Databases")
        sizer = page.Sizer = wx.BoxSizer(wx.VERTICAL)

        splitter = self.splitter = wx.SplitterWindow(page, style=wx.BORDER_NONE)
        splitter.SetMinimumPaneSize(300)

        panel_left = wx.Panel(splitter)
        panel_left.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_header = wx.BoxSizer(wx.HORIZONTAL)

        label_count = self.label_count = wx.StaticText(panel_left)
        edit_filter = self.edit_filter = controls.HintedTextCtrl(panel_left, "Filter list",
                                                                 style=wx.TE_PROCESS_ENTER)
        edit_filter.ToolTip = "Filter database list (%s-F)" % controls.KEYS.NAME_CTRL

        list_db = self.list_db = controls.SortableUltimateListCtrl(panel_left,
            agwStyle=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_NONE)
        list_db.MinSize = 400, -1 # Maximize-restore would resize width to 100
        list_db.InsertColumn(0, "")

        columns = [("name", "Name"), ("last_modified", "Modified"), ("size", "Size")]
        frmt_dt = lambda r, c: r[c].strftime("%Y-%m-%d %H:%M:%S") if r.get(c) else ""
        frmt_sz = lambda r, c: util.format_bytes(r[c]) if r.get(c) is not None else ""
        formatters = {"last_modified": frmt_dt, "size": frmt_sz}
        list_db.SetColumns(columns)
        list_db.SetColumnFormatters(formatters)
        list_db.SetColumnAlignment(2, wx.lib.agw.ultimatelistctrl.ULC_FORMAT_RIGHT)

        list_db.AssignImages([images.ButtonHome.Bitmap, images.ButtonListDatabase.Bitmap])
        ColourManager.Manage(list_db, "ForegroundColour", "DBListForegroundColour")
        ColourManager.Manage(list_db, "BackgroundColour", "DBListBackgroundColour")
        topdata = collections.defaultdict(lambda: None, name="Home")
        list_db.SetTopRow(topdata, [0])

        panel_right = wx.lib.scrolledpanel.ScrolledPanel(splitter)
        panel_right.Sizer = wx.BoxSizer(wx.HORIZONTAL)

        panel_main = self.panel_db_main = wx.Panel(panel_right)
        panel_detail = self.panel_db_detail = wx.Panel(panel_right)
        panel_main.Sizer = wx.BoxSizer(wx.VERTICAL)
        panel_detail.Sizer = wx.BoxSizer(wx.VERTICAL)

        # Create main page label and buttons
        label_main = wx.StaticText(panel_main,
                                   label="Welcome to %s" % conf.Title)
        ColourManager.Manage(label_main, "ForegroundColour", "SkypeLinkColour")
        label_main.Font = wx.Font(14, wx.FONTFAMILY_SWISS,
            wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, faceName=self.Font.FaceName)
        newextra = ", or populated from a Skype source" if live.skpy or live.ijson else ""
        BUTTONS_MAIN = [
            ("button_opena", "&Open a database..", images.ButtonOpenA, 
             "Choose a database from your computer to open."),
            ("button_detect", "Detect databases", images.ButtonDetect,
             "Auto-detect Skype databases from user folders."),
            ("button_folder", "&Import from folder.", images.ButtonFolder,
             "Select a folder where to look for SQLite databases "
             "(*.db files)."),
            ("button_new", "Create a &new Skype database", images.ButtonNew,
             "Create a blank database%s." % newextra),
            ("button_clear", "&Remove..", images.ButtonClear,
             "Select category to remove from database list."), ]
        for name, label, img, note in BUTTONS_MAIN:
            button = controls.NoteButton(panel_main, label, note, img.Bitmap)
            setattr(self, name, button)
        self.button_clear.Hide()

        # Create detail page labels, values and buttons
        label_db = self.label_db = wx.TextCtrl(parent=panel_detail, value="",
            style=wx.NO_BORDER | wx.TE_MULTILINE | wx.TE_RICH)
        label_db.Font = wx.Font(12, wx.FONTFAMILY_SWISS,
            wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, faceName=self.Font.FaceName)
        ColourManager.Manage(label_db, "BackgroundColour", "WidgetColour")
        label_db.SetEditable(False)

        sizer_labels = wx.FlexGridSizer(cols=2, vgap=3, hgap=10)
        LABELS = [("path", "Location"), ("size", "Size"),
                  ("modified", "Last modified"), ("account", "Skype user"),
                  ("chats", "Conversations"), ("messages", "Messages")]
        for field, title in LABELS:
            lbltext = wx.StaticText(parent=panel_detail, label="%s:" % title)
            valtext = wx.TextCtrl(parent=panel_detail, value="",
                                  size=(300, -1), style=wx.NO_BORDER)
            ColourManager.Manage(valtext, "BackgroundColour", "WidgetColour")
            ColourManager.Manage(valtext, "ForegroundColour", wx.SYS_COLOUR_WINDOWTEXT)
            valtext.SetEditable(False)
            ColourManager.Manage(lbltext, "ForegroundColour", "DisabledColour")
            sizer_labels.Add(lbltext, border=5, flag=wx.LEFT)
            sizer_labels.Add(valtext, proportion=1, flag=wx.GROW)
            setattr(self, "label_" + field, valtext)

        BUTTONS_DETAIL = [
            ("button_open", "&Open", images.ButtonOpen, 
             "Open the database for reading."),
            ("button_compare", "Compare and &merge", images.ButtonCompare,
             "Choose another Skype database to compare with, in order to merge "
             "their differences."),
            ("button_export", "&Export messages", images.ButtonExport,
             "Export all conversations from the database as "
             "HTML, text or spreadsheet."),
            ("button_saveas", "Save &as..", images.ButtonSaveAs,
             "Save a copy of the database under another name."),
            ("button_remove", "&Remove", images.ButtonRemoveType,
             "Remove this database from the list."),
            ("button_delete", "Delete", images.ButtonDelete,
             "Delete this database from disk."), ]
        for name, label, img, note in BUTTONS_DETAIL:
            button = controls.NoteButton(panel_detail, label, note, img.Bitmap)
            setattr(self, name, button)

        children = list(panel_main.Children) + list(panel_detail.Children)
        for c in [panel_main, panel_detail] + children:
            ColourManager.Manage(c, "BackgroundColour", "MainBgColour")
        panel_right.SetupScrolling(scroll_x=False)
        panel_detail.Hide()

        edit_filter.Bind(wx.EVT_TEXT_ENTER,        self.on_filter_list_db)
        list_db.Bind(wx.EVT_LIST_ITEM_SELECTED,    self.on_select_list_db)
        list_db.Bind(wx.EVT_LIST_ITEM_ACTIVATED,   self.on_open_from_list_db)
        list_db.Bind(wx.EVT_CHAR_HOOK,             self.on_list_db_key)
        list_db.Bind(wx.EVT_LIST_COL_CLICK,        self.on_sort_list_db)
        list_db.Bind(wx.lib.agw.ultimatelistctrl.EVT_LIST_END_DRAG, self.on_drag_list_db)

        self.button_opena.Bind(wx.EVT_BUTTON,   self.on_open_database)
        self.button_detect.Bind(wx.EVT_BUTTON,  self.on_detect_databases)
        self.button_folder.Bind(wx.EVT_BUTTON,  self.on_add_from_folder)
        self.button_new.Bind(wx.EVT_BUTTON,     self.on_new_database)
        self.button_clear.Bind(wx.EVT_BUTTON,   self.on_remove_databases)
        self.button_open.Bind(wx.EVT_BUTTON,    self.on_open_current_database)
        self.button_compare.Bind(wx.EVT_BUTTON, self.on_compare_databases)
        self.button_export.Bind(wx.EVT_BUTTON,  self.on_export_database_menu)
        self.button_saveas.Bind(wx.EVT_BUTTON,  self.on_save_database_as)
        self.button_remove.Bind(wx.EVT_BUTTON,  self.on_remove_database)
        self.button_delete.Bind(wx.EVT_BUTTON,  self.on_delete_database)

        sizer_header.Add(label_count, flag=wx.ALIGN_BOTTOM)
        sizer_header.AddStretchSpacer()
        sizer_header.Add(edit_filter)
        panel_left.Sizer.Add(sizer_header, border=5, flag=wx.BOTTOM | wx.GROW)
        panel_left.Sizer.Add(list_db, proportion=1, flag=wx.GROW)

        panel_main.Sizer.Add(label_main, border=10, flag=wx.ALL)
        panel_main.Sizer.Add((0, 10))
        panel_main.Sizer.Add(self.button_opena,  flag=wx.GROW)
        panel_main.Sizer.Add(self.button_detect, flag=wx.GROW)
        panel_main.Sizer.Add(self.button_folder, flag=wx.GROW)
        panel_main.Sizer.Add(self.button_new,    flag=wx.GROW)
        panel_main.Sizer.AddStretchSpacer()
        panel_main.Sizer.Add(self.button_clear,   flag=wx.GROW)

        panel_detail.Sizer.Add(label_db, border=10, flag=wx.ALL | wx.GROW)
        panel_detail.Sizer.Add(sizer_labels, border=10, flag=wx.ALL | wx.GROW)
        panel_detail.Sizer.Add((0, 10))
        panel_detail.Sizer.Add(self.button_open,    flag=wx.GROW)
        panel_detail.Sizer.Add(self.button_compare, flag=wx.GROW)
        panel_detail.Sizer.Add(self.button_export,  flag=wx.GROW)
        panel_detail.Sizer.AddStretchSpacer()
        panel_detail.Sizer.Add(self.button_saveas, flag=wx.GROW)
        panel_detail.Sizer.Add(self.button_remove, flag=wx.GROW)
        panel_detail.Sizer.Add(self.button_delete, flag=wx.GROW)

        panel_right.Sizer.Add(panel_main,   border=10, proportion=1, flag=wx.LEFT | wx.GROW)
        panel_right.Sizer.Add(panel_detail, border=10, proportion=1, flag=wx.LEFT | wx.GROW)
        sizer.Add(splitter, border=10, proportion=1, flag=wx.ALL | wx.GROW)
        splitter.SplitVertically(panel_left, panel_right, sashPosition=self.Size[0] * 4 // 7)


    def create_menu(self):
        """Creates the program menu."""
        menu = wx.MenuBar()
        self.SetMenuBar(menu)

        menu_file = wx.Menu()
        menu.Append(menu_file, "&File")

        menu_new = self.menu_new = wx.Menu()
        menu_file.AppendSubMenu(menu_new, "&New database ..")
        menu_new_blank = self.menu_new_blank = menu_new.Append(
            wx.ID_ANY, "&Blank with username",
            "Create a blank Skype database, populated with username only"
        )
        menu_new_live = self.menu_new_live = menu_new.Append(
            wx.ID_ANY, "From Skype on&line",
            "Create a new Skype database, by logging in to Skype online service and downloading chat history"
        ) if live.skpy else None
        menu_new_export = self.menu_new_export = menu_new.Append(
            wx.ID_ANY, "From Skype &export",
            "Create a new Skype database from a Skype chat history export archive"
        ) if live.ijson else None

        menu_open_database = self.menu_open_database = menu_file.Append(
            wx.ID_ANY, "&Open database...\tCtrl-O",
            "Choose a database file to open."
        )
        menu_recent = self.menu_recent = wx.Menu()
        menu_file.AppendSubMenu(menu_recent, "&Recent databases",
            "Recently opened databases.")
        menu_file.AppendSeparator()
        menu_options = self.menu_options = \
            menu_file.Append(wx.ID_ANY, "&Advanced options",
                "Edit advanced program options")
        if self.trayicon.IsAvailable():
            menu_iconize = self.menu_iconize = \
                menu_file.Append(wx.ID_ANY, "Minimize to &tray",
                    "Minimize %s window to notification area" % conf.Title)
        menu_exit = self.menu_exit = \
            menu_file.Append(wx.ID_ANY, "E&xit\tAlt-X", "Exit")

        menu_help = wx.Menu()
        menu.Append(menu_help, "&Help")

        menu_update = self.menu_update = menu_help.Append(wx.ID_ANY,
            "Check for &updates",
            "Check whether a new version of %s is available" % conf.Title)
        menu_feedback = self.menu_feedback = menu_help.Append(wx.ID_ANY,
            "Send &feedback",
            "Send feedback or report a problem to program author")
        menu_homepage = self.menu_homepage = menu_help.Append(wx.ID_ANY,
            "Go to &homepage",
            "Open the %s homepage, %s" % (conf.Title, conf.HomeUrl))
        menu_help.AppendSeparator()
        menu_log = self.menu_log = menu_help.Append(wx.ID_ANY,
            "Show &log window", "Show/hide the log messages window", wx.ITEM_CHECK)
        menu_console = self.menu_console = menu_help.Append(wx.ID_ANY,
            "Show Python &console\tCtrl-E",
            "Show/hide a Python shell environment window", wx.ITEM_CHECK)
        menu_help.AppendSeparator()
        if self.trayicon.IsAvailable():
            menu_tray = self.menu_tray = menu_help.Append(wx.ID_ANY,
                "Display &icon in notification area",
                "Show/hide %s icon in system tray" % conf.Title, wx.ITEM_CHECK)
        menu_autoupdate_check = self.menu_autoupdate_check = menu_help.Append(wx.ID_ANY,
            "Automatic up&date check",
            "Automatically check for program updates periodically", wx.ITEM_CHECK)
        menu_help.AppendSeparator()
        menu_about = self.menu_about = menu_help.Append(
            wx.ID_ANY, "&About %s" % conf.Title,
            "Show program information and copyright")

        self.history_file = wx.FileHistory(conf.MaxRecentFiles)
        self.history_file.UseMenu(menu_recent)
        # Reverse list, as FileHistory works like a stack
        [self.history_file.AddFileToHistory(f) for f in conf.RecentFiles[::-1]]
        self.Bind(wx.EVT_MENU_RANGE, self.on_recent_file, id=wx.ID_FILE1,
                  id2=wx.ID_FILE1 + conf.MaxRecentFiles)
        if self.trayicon.IsAvailable():
            menu_tray.Check(conf.TrayIconEnabled)
        menu_autoupdate_check.Check(conf.UpdateCheckAutomatic)

        self.Bind(wx.EVT_MENU, self.on_new_blank,               menu_new_blank)
        if menu_new_live:
            self.Bind(wx.EVT_MENU, self.on_new_live,            menu_new_live)
        if menu_new_export:
            self.Bind(wx.EVT_MENU, self.on_new_export,          menu_new_export)
        self.Bind(wx.EVT_MENU, self.on_open_database,           menu_open_database)
        self.Bind(wx.EVT_MENU, self.on_open_options,            menu_options)
        self.Bind(wx.EVT_MENU, self.on_exit,                    menu_exit)
        self.Bind(wx.EVT_MENU, self.on_check_update,            menu_update)
        self.Bind(wx.EVT_MENU, self.on_open_feedback,           menu_feedback)
        if self.trayicon.IsAvailable():
            self.Bind(wx.EVT_MENU, self.on_toggle_iconize,      menu_iconize)
            self.Bind(wx.EVT_MENU, self.on_toggle_trayicon,     menu_tray)
        self.Bind(wx.EVT_MENU, self.on_menu_homepage,           menu_homepage)
        self.Bind(wx.EVT_MENU, self.on_showhide_log,            menu_log)
        self.Bind(wx.EVT_MENU, self.on_showhide_console,        menu_console)
        self.Bind(wx.EVT_MENU, self.on_toggle_autoupdate_check, menu_autoupdate_check)
        self.Bind(wx.EVT_MENU, self.on_about,                   menu_about)


    def update_check(self):
        """
        Checks for an updated Skyperious version if sufficient time
        from last check has passed, and opens a dialog for upgrading
        if new version available. Schedules a new check on due date.
        """
        if self or not conf.UpdateCheckAutomatic: return

        interval = datetime.timedelta(days=conf.UpdateCheckInterval)
        due_date = datetime.datetime.now() - interval
        if not (conf.WindowIconized or support.update_window) \
        and conf.LastUpdateCheck < due_date.strftime("%Y%m%d"):
            callback = lambda resp: self.on_check_update_callback(resp, False)
            support.check_newest_version(callback)
        elif not support.update_window:
            try:
                dt = datetime.datetime.strptime(conf.LastUpdateCheck, "%Y%m%d")
                interval = (dt + interval) - datetime.datetime.now()
            except (TypeError, ValueError): pass

        # Schedule a check for next due date, should the program run that long.
        millis = min(sys.maxsize, util.timedelta_seconds(interval) * 1000)
        wx.CallLater(millis, self.update_check)


    def on_tray_search(self, event):
        """Handler for searching from tray dialog, launches search."""
        if self.dialog_search.Value.strip():
            self.dialog_search.Hide()
            if self.IsIconized() and not self.Shown:
                self.on_toggle_iconize()
            else:
                self.Iconize(False), self.Show(), self.Raise()
            page = self.page_db_latest
            if not page:
                filename = self.db_filename not in self.workers_import and self.db_filename
                if not filename: filename = next((x for x in list(self.dbs) + conf.RecentFiles
                                                  if x not in self.workers_import), None)
                if filename: page = self.load_database_page(filename)
            if page:
                page.edit_searchall.Value = self.dialog_search.Value
                page.on_searchall(None)
                for i in range(self.notebook.GetPageCount()):
                    if self.notebook.GetPage(i) == page:
                        if self.notebook.GetSelection() != i:
                            self.notebook.SetSelection(i)
                            self.update_notebook_header()
                        break # for i
            else:
                wx.MessageBox("No database to search from.", conf.Title)


    def on_toggle_iconize(self, event=None):
        """Handler for toggling main window to tray and back."""
        self.dialog_search.Hide()
        conf.WindowIconized = not conf.WindowIconized
        if conf.WindowIconized:
            self.Iconize(), self.Hide()
            conf.WindowPosition = self.Position[:]
            if not conf.TrayIconEnabled:
                conf.TrayIconEnabled = True
                self.trayicon.SetIcon(self.TRAY_ICON.Icon, conf.Title)
        else:
            self.Iconize(False), self.Show(), self.Raise()


    def on_toggle_trayicon(self, event=None):
        """
        Handler for toggling tray icon, removes or adds it to the tray area.

        @param   event  if not given or false, tray icon is toggled on
        """
        conf.TrayIconEnabled = event.IsChecked() if event else True
        self.menu_tray.Check(conf.TrayIconEnabled)
        if conf.TrayIconEnabled:
            self.trayicon.SetIcon(self.TRAY_ICON.Icon, conf.Title)
        else:
            self.trayicon.RemoveIcon()
        if conf.WindowIconized:
            self.on_toggle_iconize()


    def on_open_tray_search(self, event):
        """Opens the search entry dialog."""
        self.dialog_search.Show(not self.dialog_search.Shown)


    def on_open_tray_menu(self, event):
        """Creates and opens a popup menu for the tray icon."""
        menu = wx.Menu()
        item_search = wx.MenuItem(menu, -1, "&Search for..")
        font = item_search.Font
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        font.SetFaceName(self.Font.FaceName)
        font.SetPointSize(self.Font.PointSize)
        item_search.Font = font
        label = ["Minimize to", "Restore from"][conf.WindowIconized] + " &tray"
        item_toggle = wx.MenuItem(menu, -1, label)
        item_icon = wx.MenuItem(menu, -1, kind=wx.ITEM_CHECK,
                                text="Show &icon in notification area")
        item_console = wx.MenuItem(menu, -1, kind=wx.ITEM_CHECK,
                                   text="Show Python &console")
        item_exit = wx.MenuItem(menu, -1, "E&xit %s" % conf.Title)

        menu.Append(item_search)
        menu.Append(item_toggle)
        menu.AppendSeparator()
        menu.Append(item_icon)
        menu.Append(item_console)
        menu.AppendSeparator()
        menu.Append(item_exit)
        item_icon.Check(True)
        item_console.Check(self.frame_console.Shown)

        menu.Bind(wx.EVT_MENU, self.on_open_tray_search, id=item_search.GetId())
        menu.Bind(wx.EVT_MENU, self.on_toggle_iconize, id=item_toggle.GetId())
        menu.Bind(wx.EVT_MENU, self.on_toggle_trayicon, id=item_icon.GetId())
        menu.Bind(wx.EVT_MENU, self.on_showhide_console, id=item_console.GetId())
        menu.Bind(wx.EVT_MENU, self.on_exit, id=item_exit.GetId())
        self.trayicon.PopupMenu(menu)


    def on_change_page(self, event):
        """
        Handler for changing a page in the main Notebook, remembers the visit.
        """
        p = self.notebook.GetPage(self.notebook.GetSelection())
        if not self.pages_visited or self.pages_visited[-1] != p:
            self.pages_visited.append(p)
        self.Title = conf.Title
        if hasattr(p, "title"):
            subtitle = p.title
            if isinstance(p, DatabasePage): # Use parent/file.db or C:/file.db
                path, file = os.path.split(p.db.filename)
                subtitle = os.path.join(os.path.split(path)[-1] or path, file)
            self.Title += " - " + subtitle
        self.update_notebook_header()
        if event: event.Skip() # Pass event along to next handler


    def on_size(self, event):
        """Handler for window size event, tweaks controls and saves size."""
        event.Skip()
        conf.WindowSize = [-1, -1] if self.IsMaximized() else self.Size[:]
        util.run_once(conf.save)
        self.list_db.SendSizeEvent()


    def on_move(self, event):
        """Handler for window move event, saves position."""
        event.Skip()
        if not self.IsIconized():
            conf.WindowPosition = event.Position[:]
            util.run_once(conf.save)


    def on_sys_colour_change(self, event):
        """Handler for system colour change, updates filesystem images."""
        event.Skip()
        self.adapt_colours()
        def after():
            self.load_fs_images()
            for i in range(self.list_db.GetItemCount()):
                self.list_db.SetItemTextColour(i,       self.list_db.ForegroundColour)
                self.list_db.SetItemBackgroundColour(i, self.list_db.BackgroundColour)
        wx.CallAfter(after) # Postpone to allow conf update


    def adapt_colours(self):
        """Adapts configuration colours to better fit current theme."""
        COLOURS = ["GridRowInsertedColour", "GridRowChangedColour",
                   "GridCellChangedColour"]
        frgb = tuple(ColourManager.GetColour(wx.SYS_COLOUR_BTNTEXT))[:3]
        brgb = tuple(ColourManager.GetColour(wx.SYS_COLOUR_WINDOW ))[:3]
        for n in COLOURS:
            rgb = tuple(wx.Colour(conf.Defaults.get(n)))[:3]
            delta = tuple(255 - x for x in rgb)
            direction = 1 if (sum(frgb) > sum(brgb)) else -1
            rgb2 = tuple(a + int(b * direction) for a, b in zip(brgb, delta))
            rgb2 = tuple(min(255, max(0, x)) for x in rgb2)
            setattr(conf, n, wx.Colour(rgb2).GetAsString(wx.C2S_HTML_SYNTAX))


    def load_fs_images(self):
        """Loads content to MemoryFS."""
        if not self: return
        abouticon = "%s.png" % conf.Title.lower() # Program icon shown in About window
        img = images.Icon48x48_32bit.Image
        if abouticon in self.memoryfs["files"]:
            self.memoryfs["handler"].RemoveFile(abouticon)
        self.memoryfs["handler"].AddFile(abouticon, img, wx.BITMAP_TYPE_PNG)
        self.memoryfs["files"][abouticon] = 1

        fn = "blank.gif"
        if fn not in self.memoryfs["files"]:
            img = images.TransparentPixel.Image
            self.memoryfs["handler"].AddFile(fn, img, wx.BITMAP_TYPE_GIF)
            self.memoryfs["files"][fn] = 1

        # Screenshots look better with colouring if system has off-white colour
        tint_colour = wx.Colour(conf.BgColour)
        tint_factor = [((4 * x) % 256) / 255. for x in tint_colour]
        # Images shown on the default search content page
        for name in ["HelpSearch", "HelpChats", "HelpContacts", "HelpInfo", "HelpTables",
                     "HelpSQL", "HelpOnline"]:
            embedded = getattr(images, name, None)
            if not embedded: continue # for name
            img = embedded.Image.AdjustChannels(*tint_factor)
            filename = "%s.png" % name
            if filename in self.memoryfs["files"]:
                self.memoryfs["handler"].RemoveFile(filename)
            self.memoryfs["handler"].AddFile(filename, img, wx.BITMAP_TYPE_PNG)
            self.memoryfs["files"][filename] = 1


    def update_notebook_header(self):
        """
        Removes or adds X to notebook tab style, depending on whether current
        page can be closed.
        """
        if not self:
            return
        p = self.notebook.GetPage(self.notebook.GetSelection())
        style = self.notebook.GetAGWWindowStyleFlag()
        if isinstance(p, (DatabasePage, MergerPage)):
            if p.ready_to_close \
            and not (style & wx.lib.agw.flatnotebook.FNB_X_ON_TAB):
                style |= wx.lib.agw.flatnotebook.FNB_X_ON_TAB
            elif not p.ready_to_close \
            and (style & wx.lib.agw.flatnotebook.FNB_X_ON_TAB):
                style ^= wx.lib.agw.flatnotebook.FNB_X_ON_TAB
        elif self.page_log == p:
            style |= wx.lib.agw.flatnotebook.FNB_X_ON_TAB
        elif style & wx.lib.agw.flatnotebook.FNB_X_ON_TAB: # Hide close box
            style ^= wx.lib.agw.flatnotebook.FNB_X_ON_TAB  # on main page
        if style != self.notebook.GetAGWWindowStyleFlag():
            self.notebook.SetAGWWindowStyleFlag(style)


    def on_toggle_autoupdate_check(self, event):
        """Handler for toggling automatic update checking, changes conf."""
        conf.UpdateCheckAutomatic = event.IsChecked()
        util.run_once(conf.save)


    def on_list_db_key(self, event):
        """
        Handler for pressing a key in dblist, loads selected database on Enter
        removes from list on Delete, refreshes columns on F5,
        and focuses filter on Ctrl-F.
        """
        if event.KeyCode in [wx.WXK_F5]:
            items, selected_files, selected_home = [], [], False
            selected = self.list_db.GetFirstSelected()
            while selected >= 0:
                if selected:
                    selected_files.append(self.list_db.GetItemText(selected))
                else: selected_home = True
                selected = self.list_db.GetNextSelected(selected)

            for filename in conf.DBFiles:
                data = collections.defaultdict(lambda: None, name=filename)
                if os.path.exists(filename):
                    if filename in self.dbs:
                        self.dbs[filename].update_fileinfo()
                        data["size"] = self.dbs[filename].filesize
                        data["last_modified"] = self.dbs[filename].last_modified
                    else:
                        data["size"] = os.path.getsize(filename)
                        data["last_modified"] = datetime.datetime.fromtimestamp(
                                                os.path.getmtime(filename))
                self.db_filenames[filename].update(data)
                items.append(data)
            self.list_db.Populate(items, [1])
            if selected_home: self.list_db.Select(0)
            if selected_files:
                for i in range(1, self.list_db.GetItemCount()):
                    if self.list_db.GetItemText(i) in selected_files:
                        self.list_db.Select(i)
                self.update_database_detail()
        elif event.KeyCode in [ord("F")] and event.CmdDown():
            self.edit_filter.SetFocus()
        if self.list_db.GetFirstSelected() > 0 and not event.AltDown() \
        and event.KeyCode in [wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER]:
            self.load_database_page(self.db_filename)
        elif event.KeyCode in [wx.WXK_DELETE] and self.db_filename:
            self.on_remove_database(None)
        event.Skip()


    def on_sort_list_db(self, event):
        """Handler for sorting dblist, saves sort state."""
        event.Skip()
        def save_sort_state():
            if not self: return
            conf.DBSort = self.list_db.GetSortState()
            util.run_once(conf.save)
        wx.CallAfter(save_sort_state) # Allow list to update sort state


    def on_drag_list_db(self, event):
        """Handler for dragging items around in dblist, saves file order."""
        event.Skip()
        def save_list_order():
            conf.DBFiles = [self.list_db.GetItemText(i)
                            for i in range(1, self.list_db.GetItemCountFull())]
            util.run_once(conf.save)
        wx.CallAfter(save_list_order) # Allow list to update items


    def on_filter_list_db(self, event):
        """Handler for filtering dblist, applies search filter after timeout."""
        event.Skip()
        search = event.String.strip()
        if search == self.db_filter: return

        def do_filter(search):
            if not self: return
            self.db_filter_timer = None
            if search != self.db_filter: return
            self.list_db.SetFilter(search)
            self.update_database_list()

        if self.db_filter_timer: self.db_filter_timer.Stop()
        self.db_filter = search
        if search: self.db_filter_timer = wx.CallLater(200, do_filter, search)
        else: do_filter(search)


    def on_open_feedback(self, event=None):
        """Handler for clicking to send feedback, opens the feedback form."""
        if not self: return

        if support.feedback_window:
            if not support.feedback_window.Shown:
                support.feedback_window.Show()
            support.feedback_window.Raise()
        else:
            support.feedback_window = support.FeedbackDialog(self)


    def on_menu_homepage(self, event):
        """Handler for opening Skyperious webpage from menu,"""
        webbrowser.open(conf.HomeUrl)


    def on_about(self, event):
        """
        Handler for clicking "About Skyperious" menu, opens a small info frame.
        """
        maketext = lambda: step.Template(templates.ABOUT_TEXT).expand()
        AboutDialog(self, maketext).ShowModal()


    def on_check_update(self, event):
        """
        Handler for checking for updates, starts a background process for
        checking for and downloading the newest version.
        """
        if not support.update_window:
            guibase.status("Checking for new version of %s.", conf.Title)
            wx.CallAfter(support.check_newest_version,
                         self.on_check_update_callback)
        elif hasattr(support.update_window, "Raise"):
            support.update_window.Raise()


    def on_check_update_callback(self, check_result, full_response=True):
        """
        Callback function for processing update check result, offers new
        version for download if available.

        @param   full_response  if False, show message only if update available
        """
        if not self: return

        support.update_window = True
        guibase.status()
        if check_result:
            version, url, changes = check_result
            MAX = 1000
            changes = changes[:MAX] + ".." if len(changes) > MAX else changes
            guibase.status("New %s version %s available.", conf.Title, version)
            if wx.OK == wx.MessageBox(
                "Newer version (%s) available. You are currently on "
                "version %s.%s\nDownload and install %s %s?" %
                (version, conf.Version, "\n\n%s\n" % changes,
                 conf.Title, version),
                "Update information", wx.OK | wx.CANCEL | wx.ICON_INFORMATION
            ):
                wx.CallAfter(support.download_and_install, url)
        elif full_response and check_result is not None:
            wx.MessageBox("You are using the latest version of %s, %s.\n\n " %
                (conf.Title, conf.Version), "Update information",
                wx.OK | wx.ICON_INFORMATION)
        elif full_response:
            wx.MessageBox("Could not contact download server.",
                          "Update information", wx.OK | wx.ICON_WARNING)
        if check_result is not None:
            conf.LastUpdateCheck = datetime.date.today().strftime("%Y%m%d")
            util.run_once(conf.save)
        support.update_window = None


    def on_detect_databases(self, event):
        """
        Handler for clicking to auto-detect databases, starts or stops the
        detection in a background thread.
        """
        if self.worker_detection.is_working():
            self.worker_detection.stop_work()
            self.button_detect.Label = "Detect databases"
            guibase.status("Stopped detecting databases.", log=True)
        else:
            guibase.status("Searching local computer for Skype databases..", log=True)
            self.button_detect.Label = "Stop detecting databases"
            self.worker_detection.work(True)


    def on_detect_databases_callback(self, result):
        """Callback for DetectDatabaseThread, posts the data to self."""
        if self: # Check if instance is still valid (i.e. not destroyed by wx)
            wx.PostEvent(self, DetectionWorkerEvent(result=result))


    def on_detect_databases_result(self, event):
        """
        Handler for getting results from database detection thread, adds the
        results to the database list.
        """
        result = event.result
        if "filenames" in result:
            for f in result["filenames"]:
                if self.update_database_list(f):
                    logger.info("Detected database %s.", f)
        if "count" in result:
            name = ("" if result["count"] else "additional ") + "database"
            guibase.status("Detected %s.", util.plural(name, result["count"]), log=True)
        if result.get("done", False):
            self.button_detect.Label = "Detect databases"
            self.list_db.SendSizeEvent()
            wx.Bell()


    def populate_database_list(self):
        """Inserts all databases into the list, updates UI buttons."""
        if not self: return
        items, selected_files = [], []
        for filename in conf.DBFiles:
            filename = util.to_unicode(filename)
            data = collections.defaultdict(lambda: None, name=filename)
            if os.path.exists(filename):
                data["size"] = os.path.getsize(filename)
                data["last_modified"] = datetime.datetime.fromtimestamp(
                                        os.path.getmtime(filename))
            self.db_filenames[filename] = data
            items.append(data)
            if filename in conf.LastSelectedFiles: selected_files += [filename]

        self.list_db.Populate(items, [1])
        if conf.DBSort and conf.DBSort[0] >= 0:
            self.list_db.SortListItems(*conf.DBSort)

        if selected_files:
            idx = -1
            for i in range(1, self.list_db.GetItemCount()):
                if self.list_db.GetItemText(i) in selected_files:
                    if idx < 0: idx = i
                    self.list_db.Select(i)
            self.list_db.EnsureVisible(idx)
            self.list_db.SetFocus()
        else:
            self.list_db.Select(0)

        self.button_clear.Show(bool(items))
        self.panel_db_main.Layout()
        self.update_database_count()
        if selected_files: wx.CallLater(100, self.update_database_detail)


    def update_database_list(self, filename=""):
        """
        Inserts the database into the list, if not there already, and updates
        UI buttons.

        @param   filename  possibly new filename, if any
        @return            True if was file was new or changed, False otherwise
        """
        result = False
        # Insert into database lists, if not already there
        if filename:
            filename = util.to_unicode(filename)
            if filename not in conf.DBFiles:
                conf.DBFiles.append(filename)
                util.run_once(conf.save)
            data = collections.defaultdict(lambda: None, name=filename)
            if os.path.exists(filename):
                data["size"] = os.path.getsize(filename)
                data["last_modified"] = datetime.datetime.fromtimestamp(
                                        os.path.getmtime(filename))
            data_old = self.db_filenames.get(filename)
            if not data_old or data_old["size"] != data["size"] \
            or data_old["last_modified"] != data["last_modified"]:
                self.db_filenames.setdefault(filename, data).update(data)
                if not data_old: self.list_db.AppendRow(data, [1])
                result = True

        has_items = self.list_db.GetItemCount() > 1
        if self.button_clear.Shown != has_items:
            self.button_clear.Show(has_items)
            self.panel_db_main.Layout()
        self.update_database_count()
        return result


    def update_database_count(self):
        """Updates database count label."""
        count = self.list_db.GetItemCount() - 1
        total = self.list_db.GetItemCountFull() - 1
        text = ""
        if total: text = util.plural("file", count)
        if count != total: text += " visible (%s in total)" % total
        self.label_count.Label = text


    def on_remove_databases(self, event):
        """Handler for clicking to remove databases, opens popup menu."""
        menu = wx.lib.agw.flatmenu.FlatMenu()
        item_missing  = menu.AppendItem(wx.lib.agw.flatmenu.FlatMenuItem(menu, wx.ID_ANY,
                                       "Remove &missing files"))
        item_skype    = menu.AppendItem(wx.lib.agw.flatmenu.FlatMenuItem(menu, wx.ID_ANY,
                                       "Remove &Skype databases"))
        item_nonskype = menu.AppendItem(wx.lib.agw.flatmenu.FlatMenuItem(menu, wx.ID_ANY,
                                       "Remove &non-Skype databases"))
        item_clear   = menu.AppendItem(wx.lib.agw.flatmenu.FlatMenuItem(menu, wx.ID_ANY,
                                       "Remove &all"))

        self.Bind(wx.EVT_MENU, self.on_remove_missing,  item_missing)
        self.Bind(wx.EVT_MENU, functools.partial(self.on_remove_type, other=False), item_skype)
        self.Bind(wx.EVT_MENU, self.on_remove_type,     item_nonskype)
        self.Bind(wx.EVT_MENU, self.on_clear_databases, item_clear)

        btn = self.button_clear
        sz_btn, pt_btn = btn.Size, btn.Position
        pt_btn = btn.Parent.ClientToScreen(pt_btn)
        menu.SetOwnerHeight(sz_btn.y)
        if menu.Size.width < sz_btn.width:
            menu.Size = sz_btn.width, menu.Size.height
        menu.Popup((pt_btn), self)


    def on_clear_databases(self, event):
        """Handler for clicking to clear the database list."""
        is_full = self.list_db.GetItemCount() == self.list_db.GetItemCountFull()
        if self.list_db.GetItemCount() < 2 or wx.OK != wx.MessageBox(
            "Are you sure you want to clear the list of all%s databases?" %
            ("" if is_full else " currently shown"),
            conf.Title, wx.OK | wx.CANCEL | wx.ICON_QUESTION
        ): return

        count = self.list_db.GetItemCount() - 1
        if is_full:
            self.list_db.Populate([])
            del conf.DBFiles[:]
            del conf.LastSelectedFiles[:]
            del conf.RecentFiles[:]
            conf.LastSearchResults.clear()
            while self.history_file.Count:
                self.history_file.RemoveFileFromHistory(0)
            self.db_filenames.clear()
        else:
            selecteds = range(1, self.list_db.GetItemCount())
            filenames = list(map(self.list_db.GetItemText, selecteds))
            self.remove_databases(filenames)

        util.run_once(conf.save)
        self.update_database_list()
        guibase.status("Removed %s from database list.", util.plural("database", count))


    def on_remove_database(self, event):
        """Handler for clicking to remove an item from the database list."""
        filename = self.db_filename
        if not filename or wx.OK != wx.MessageBox(
            "Remove %s from database list?" % filename,
            conf.Title, wx.OK | wx.CANCEL | wx.ICON_QUESTION
        ): return

        self.remove_databases([filename])
        self.db_filename = None
        self.list_db.Select(0)
        self.panel_db_main.Layout()
        util.run_once(conf.save)


    def on_remove_missing(self, event):
        """Handler to remove nonexistent files from the database list."""
        selecteds = range(1, self.list_db.GetItemCount())
        filter_func = lambda i: not os.path.exists(self.list_db.GetItemText(i))
        selecteds = list(filter(filter_func, selecteds))
        filenames = list(map(self.list_db.GetItemText, selecteds))
        if not filenames: return

        self.remove_databases(filenames)
        util.run_once(conf.save)
        guibase.status("Removed %s from database list.",
                       util.plural("non-existing file", filenames))


    def on_remove_type(self, event, other=True):
        """Handler for type selection to remove files from the database list."""
        selecteds = range(1, self.list_db.GetItemCount())
        filter_func = lambda i: (
          other ^ skypedata.is_skype_database(self.list_db.GetItemText(i), log_error=False))
        selecteds = list(filter(filter_func, selecteds))
        filenames = list(map(self.list_db.GetItemText, selecteds))
        if not filenames: return

        self.remove_databases(filenames)
        util.run_once(conf.save)
        t = util.plural("%sSkype database" % ("non-" if other else ""), filenames)
        guibase.status("Removed %s from database list.", t)


    def on_delete_database(self, event):
        """Handler for clicking to delete a database."""
        filename = self.db_filename
        if not filename or wx.OK != wx.MessageBox(
            "Delete %s from disk?" % filename,
            conf.Title, wx.OK | wx.CANCEL | wx.ICON_QUESTION
        ): return

        if filename in self.dbs:
            return wx.MessageBox("%s is currently open in %s, cannot delete." %
                                 (filename, conf.Title), conf.Title, wx.OK)
        if filename in self.workers_import:
            return wx.MessageBox("%s is currently being imported to, cannot delete." % 
                                 filename, conf.Title, wx.OK | wx.ICON_WARNING)

        try: os.unlink(filename)
        except Exception as e:
            logger.exception("Error deleting %s.", filename)
            return wx.MessageBox("Failed to delete %s:\n\n%s" %
                                 (filename, util.format_exc(e)),
                                 conf.Title, wx.OK | wx.ICON_ERROR)
        self.remove_databases([filename])
        self.db_filename = None
        self.list_db.Select(0)
        self.panel_db_main.Layout()
        util.run_once(conf.save)


    def remove_databases(self, filenames):
        """Removes given file from database list and all data structures."""
        for filename in filenames:
            idx = self.list_db.FindItem(filename)
            if idx > 0: self.list_db.DeleteItem(idx)
            for lst in conf.DBFiles, conf.RecentFiles, conf.LastSelectedFiles:
                if filename in lst: lst.remove(filename)
            for dct in conf.LastSearchResults, self.db_filenames:
                dct.pop(filename, None)
            conf.Login.pop(filename, None)

        # Remove from recent file history
        historyfiles = [(i, self.history_file.GetHistoryFile(i))
                        for i in range(self.history_file.Count)]
        for i, f in historyfiles[::-1]: # Work upwards to have unchanged index
            if f in filenames: self.history_file.RemoveFileFromHistory(i)
        self.update_database_list()


    def on_save_database_as(self, event):
        """Handler for clicking to save a copy of a database in the list."""
        original = self.db_filename
        if not os.path.exists(original):
            wx.MessageBox(
                'The file "%s" does not exist on this computer.' % original,
                conf.Title, wx.OK | wx.ICON_INFORMATION
            )
            return

        if original in self.workers_import:
            return wx.MessageBox("%s is currently being imported to, cannot save." % 
                                 original, conf.Title, wx.OK | wx.ICON_WARNING)

        dialog = wx.FileDialog(parent=self, message="Save a copy..",
            defaultDir=os.path.dirname(original),
            defaultFile=os.path.basename(original),
            wildcard="SQLite database (*.db)|*.db|All files|*.*",
            style=wx.FD_OVERWRITE_PROMPT | wx.FD_SAVE | wx.RESIZE_BORDER
        )
        if wx.ID_OK != dialog.ShowModal(): return

        wx.YieldIfNeeded() # Allow UI to refresh
        newpath = controls.get_dialog_path(dialog)
        success = False
        try:
            shutil.copyfile(original, newpath)
            success = True
        except Exception as e:
            guibase.status("Error trying to copy %s to %s: %s",
                           original, newpath, util.format_exc(e))
            logger.exception("Error trying to copy %s to %s.", original, newpath)
            wx.MessageBox('Failed to copy "%s" to "%s".' % (original, newpath),
                          conf.Title, wx.OK | wx.ICON_WARNING)
        if success:
            guibase.status("Saved a copy of %s as %s.", original, newpath,
                           log=True)
            self.update_database_list(newpath)
            for k in ("LastActivePage", "LastSearchResults", "Login", "SQLWindowTexts"):
                dct = getattr(conf, k, {})
                if dct.get(original): dct[newpath] = copy.deepcopy(dct[original])
            idx = self.list_db.FindItem(newpath)
            if idx > 0: self.list_db.Select(idx)
            util.run_once(conf.save)


    def on_showhide_log(self, event):
        """Handler for clicking to show/hide the log window."""
        if self.notebook.GetPageIndex(self.page_log) < 0:
            self.notebook.AddPage(self.page_log, "Log")
            self.page_log.is_hidden = False
            self.page_log.Show()
            self.notebook.SetSelection(self.notebook.GetPageCount() - 1)
            self.on_change_page(None)
            self.menu_log.Check(True)
        elif event and self.notebook.GetPageIndex(self.page_log) != self.notebook.GetSelection():
            self.notebook.SetSelection(self.notebook.GetPageCount() - 1)
            self.on_change_page(None)
            self.menu_log.Check(True)
        else:
            self.page_log.is_hidden = True
            self.notebook.RemovePage(self.notebook.GetPageIndex(self.page_log))
            self.menu_log.Check(False)


    def on_export_database_menu(self, event):
        if not export.xlsxwriter:
            return self.on_export_database(None)

        menu = wx.lib.agw.flatmenu.FlatMenu()
        item_sel = wx.lib.agw.flatmenu.FlatMenuItem(menu, wx.ID_ANY, "Export "
            "into separate &files in one folder (HTML, text, Excel, or CSV)")
        menu.AppendItem(item_sel)
        item_all = wx.lib.agw.flatmenu.FlatMenuItem(menu, wx.ID_ANY,
            label="Export into a single &Excel workbook, with separate sheets")
        menu.AppendItem(item_all)
        for item in menu.GetMenuItems():
            self.Bind(wx.EVT_MENU, self.on_export_database, item)

        btn = self.button_export
        sz_btn, pt_btn = btn.Size, btn.Position
        pt_btn = btn.Parent.ClientToScreen(pt_btn)
        menu.SetOwnerHeight(sz_btn.y)
        if menu.Size.width < sz_btn.width:
            menu.Size = sz_btn.width, menu.Size.height
        menu.Popup(pt_btn, self)


    def on_export_database(self, event):
        """
        Handler for clicking to export a whole database, lets the user
        specify a directory where to save chat files and exports all chats.
        """
        do_singlefile = False
        if event:
            nitems = enumerate(event.EventObject.GetMenuItems())
            index = next((i for i, m in nitems if m.GetId() == event.Id), None)
            do_singlefile = index > 0

        if self.db_filename in self.workers_import:
            return wx.MessageBox("%s is currently being imported to, cannot export." % 
                                 self.db_filename, conf.Title, wx.OK | wx.ICON_WARNING)

        focused_control = self.FindFocus()
        self.button_export.Enabled = False

        dialog = self.dialog_savefile if do_singlefile else self.dialog_savefile_ow
        dialog.Message = "Choose folder where to save chat files"
        dialog.Filename = "Filename will be ignored"
        dialog.Wildcard = export.CHAT_WILDCARD
        if do_singlefile:
            db = self.load_database(self.db_filename)
            formatargs = collections.defaultdict(str)
            formatargs["skypename"] = os.path.basename(self.db_filename)
            if db and db.account: formatargs.update(db.account)
            default = util.safe_filename(conf.ExportDbTemplate % formatargs)
            dialog.Filename = default
            dialog.Message = "Save chats file"
            dialog.Wildcard = export.CHAT_WILDCARD_SINGLEFILE

        if wx.ID_OK != dialog.ShowModal():
            self.button_export.Enabled = True
            if focused_control: focused_control.SetFocus()
            return

        db, files, count, message_count, media_folder = None, [], 0, 0, False
        error, errormsg, errormsg_short = False, None, None

        db = self.load_database(self.db_filename)
        path = controls.get_dialog_path(dialog)
        if not db:
            error = True
        elif "conversations" not in db.tables:
            error = True
            errormsg = "Cannot export %s. Not a valid Skype database?" % db
        if not error and not do_singlefile:
            format = export.CHAT_EXTS[dialog.FilterIndex]
            media_folder = "html" == format and dialog.FilterIndex
            if media_folder and not check_media_export_login(db):
                self.button_export.Enabled = True
                if focused_control: focused_control.SetFocus()
                return

            formatargs = collections.defaultdict(str)
            formatargs["skypename"] = os.path.basename(self.db_filename)
            if db.account: formatargs.update(db.account)
            folder = util.safe_filename(conf.ExportDbTemplate % formatargs)
            path = util.unique_path(os.path.join(os.path.dirname(path), folder))
            try:
                os.mkdir(path)
            except Exception as e:
                errormsg_short = "Failed to create directory %s: %s" % (
                                 path, util.format_exc(e))
                errormsg = "Failed to create directory %s:\n\n%s" % \
                           (path, traceback.format_exc())
                error = True
        elif not error:
            format = export.CHAT_EXTS_SINGLEFILE[dialog.FilterIndex]


        if not error:
            chats = db.get_conversations()
            busy = controls.BusyPanel(
                self, 'Exporting all chats from "%s"\nas %s under %s.' %
                (db.filename, format.upper(), path))
            wx.SafeYield() # Allow UI to refresh
            try:
                db.get_conversations_stats(chats)
                progressfunc = lambda *args: wx.SafeYield()
                opts = dict(multi=not do_singlefile, progress=progressfunc)
                if media_folder: opts["media_folder"] = True
                result = export.export_chats(chats, path, format, db, opts)
                files, count, message_count = result
                page = next((k for k, v in self.db_pages.items() if v is db), None)
                if page: wx.CallAfter(page.update_liveinfo)
            except Exception as e:
                errormsg_short = "Error exporting chats: %s" % util.format_exc(e)
                errormsg = "Error exporting chats:\n\n%s" % traceback.format_exc()
                error = True
            busy.Close()
        if not error:
            guibase.status("Exported %s and %s from %s as %s under %s.",
                           util.plural("chat", count, sep=","),
                           util.plural("message", message_count, sep=","),
                           db.filename, format.upper(), path, log=True)
        elif errormsg:
            guibase.status(errormsg_short or errormsg, log=True)
            wx.MessageBox(errormsg, conf.Title, wx.OK | wx.ICON_WARNING)
        if db and not db.has_consumers():
            self.dbs.pop(db.filename, None)
            db.close()
        if db and not error:
            util.start_file(files[0] if do_singlefile else path)
        self.button_export.Enabled = True
        if focused_control: focused_control.SetFocus()


    def on_compare_menu(self, event):
        """
        Handler for choosing a file from the compare popup menu, loads both
        databases and opens the merger page.
        """
        filename1, filename2 = self.db_filename, None
        # Find menuitem index and label from original menu by event ID
        nitems = enumerate(event.EventObject.GetMenuItems())
        indexitem = [(i, m) for i, m in nitems if m.GetId() == event.Id]
        i, item = indexitem[0] if indexitem else (-1, None)
        has_export = bool(live.ijson)
        is_export = has_export and (i == 1)
        if i > has_export and item:
            filename2 = item.GetLabel().split(" ", 1).pop()
        elif is_export: # Second menu item: open a Skype export archive from computer
            if wx.ID_OK == self.dialog_openexport.ShowModal():
                filename2 = self.dialog_openexport.GetPath()
        else: # First menu item: open a file from computer
            if wx.ID_OK == self.dialog_openfile.ShowModal():
                filename2 = self.dialog_openfile.GetPath()
        if filename1 == filename2:
            wx.MessageBox("Cannot compare %s with itself." % (filename1),
                          conf.Title, wx.OK | wx.ICON_WARNING)
        else:
            self.compare_databases(filename1, filename2, is_export)


    def compare_databases(self, filename1, filename2, is_export=False):
        """Opens the two databases for comparison, if possible."""
        if not filename1 or not filename2: return

        if filename1 in self.workers_import:
            return wx.MessageBox("%s is currently being imported to, cannot open." % 
                                 filename1, conf.Title, wx.OK | wx.ICON_WARNING)
        if filename2 in self.workers_import:
            return wx.MessageBox("%s is currently being imported to, cannot open." % 
                                 filename2, conf.Title, wx.OK | wx.ICON_WARNING)

        title = "Database comparison"
        db1, db2, page = None, None, None
        if is_export:
            db2 = live.SkypeExport(filename2)
            db1 = self.load_database(filename1)
            title = "Merge from Skype export"
        if not db1 and not is_export:
            db1 = self.load_database(filename1)
        if db1 and not db2:
            db2 = self.load_database(filename2)
        if db1 and db2:
            dbset = set(map(str, (db1, db2)))
            page = next((x for x in self.merger_pages
                         if x and set(map(str, (x.db1, x.db2))) == dbset), None)
            if not page:
                logger.info("Merge page for %s and %s.", db1, db2)
                page = MergerPage(self.notebook, db2, db1,
                       self.get_unique_tab_title(title))
                self.merger_pages[page] = (db1, db2)
                self.UpdateAccelerators()
                util.run_once(conf.save)
        elif db1 or db2:
            # Close DB with no owner
            for db in filter(bool, [db1, db2]):
                if not db.has_consumers():
                    logger.info("Closed database %s.", db.filename)
                    self.dbs.pop(db.filename, None)
                    db.close()
        if page:
            for i in range(self.notebook.GetPageCount()):
                if self.notebook.GetPage(i) == page:
                    self.notebook.SetSelection(i)
                    self.update_notebook_header()
                    break # for i


    def on_compare_databases(self, event):
        """
        Handler for clicking to compare a selected database with another, shows
        a popup menu for choosing the second database file.
        """
        fm = wx.lib.agw.flatmenu
        menu = fm.FlatMenu()
        item = fm.FlatMenuItem(menu, wx.ID_ANY,
                               "&Select a file from your computer..")
        menu.AppendItem(item)
        if live.ijson:
            item = fm.FlatMenuItem(menu, wx.ID_ANY,
                                   "Select a Skype chat history &export archive from your computer..")
            menu.AppendItem(item)
        recents = [f for f in conf.RecentFiles if f != self.db_filename][:5]
        others = [f for f in conf.DBFiles
                  if f not in recents and f != self.db_filename]
        if recents or others:
            menu.AppendSeparator()
        if recents:
            item = fm.FlatMenuItem(menu, wx.ID_ANY, "Recent files")
            item.Enable(False)
            menu.AppendItem(item)
            for i, f in enumerate(recents, 1):
                menu.AppendItem(
                    fm.FlatMenuItem(menu, wx.ID_ANY, "&%s %s" % (i, f)))
            if others:
                menu.AppendSeparator()
                item = fm.FlatMenuItem(menu, wx.ID_ANY, "Rest of list")
                item.Enable(False)
                menu.AppendItem(item)
        for i, f in enumerate(sorted(others)):
            menu.AppendItem(fm.FlatMenuItem(
                            menu, wx.ID_ANY, "&%s %s" % (chr(97+i%26), f)))
        for item in menu.GetMenuItems():
            self.Bind(wx.EVT_MENU, self.on_compare_menu, item)

        btn = self.button_compare
        sz_btn, pt_btn = btn.Size, btn.Position
        pt_btn = btn.Parent.ClientToScreen(pt_btn)
        menu.SetOwnerHeight(sz_btn.y)
        if menu.Size.width < sz_btn.width:
            menu.Size = sz_btn.width, menu.Size.height
        menu.Popup(pt_btn, self)


    def on_open_options(self, event):
        """
        Handler for opening advanced options, creates the property dialog
        and saves values.
        """
        dialog = controls.PropertyDialog(self, title="Advanced options")

        try: source = inspect.getsource(conf)
        except Exception:
            try:
                with open(os.path.join(conf.ResourceDirectory, "..", "conf.py")) as f:
                    source = f.read()
            except Exception: source = ""

        def get_field_doc(name, tree=ast.parse(source)):
            """Returns the docstring immediately before name assignment."""
            for i, node in enumerate(tree.body):
                if i and isinstance(node, ast.Assign) and node.targets[0].id == name:
                    prev = tree.body[i - 1]
                    if isinstance(prev, ast.Expr) \
                    and isinstance(prev.value, (ast.Str, ast.Constant)):  # Py2: Str, Py3: Constant
                        return prev.value.s.strip()
            return ""

        def typelist(mytype):
            def convert(v):
                v = ast.literal_eval(v) if isinstance(v, six.string_types) else v
                if not isinstance(v, (list, tuple)): v = tuple([v])
                if not v: raise ValueError("Empty collection")
                return tuple(map(mytype, v))
            convert.__name__ = "tuple(%s)" % mytype.__name__
            return convert

        for name in sorted(conf.OptionalFileDirectives):
            value, help = getattr(conf, name, None), get_field_doc(name)
            default = conf.Defaults.get(name)
            if value is None and default is None:
                continue # for name

            kind = type(value)
            if isinstance(value, (tuple, list)):
                kind = typelist(type(value[0]))
                default = kind(default)
            dialog.AddProperty(name, value, help, default, kind)
        dialog.Realize()

        if wx.ID_OK == dialog.ShowModal():
            for k, v in dialog.GetProperties():
                # Keep numbers in sane regions
                if type(v) in six.integer_types: v = max(1, min(sys.maxsize, v))
                setattr(conf, k, v)
            util.run_once(conf.save)
            self.MinSize = conf.MinWindowSize


    def on_new_database(self, event):
        """Handler for clicking new-button on main screen, opens popup menu."""
        if not live.skpy and not live.ijson: return self.on_new_blank(event)
        menu = wx.lib.agw.flatmenu.FlatMenu()
        item_blank  = menu.AppendItem(wx.lib.agw.flatmenu.FlatMenuItem(menu, wx.ID_ANY,
                                      "&Blank Skype database, populated with username only"))
        item_live   = menu.AppendItem(wx.lib.agw.flatmenu.FlatMenuItem(menu, wx.ID_ANY,
                                      "From Skype on&line service, by logging in "
                                      "and downloading available history"
        )) if live.skpy else None
        item_export = menu.AppendItem(wx.lib.agw.flatmenu.FlatMenuItem(menu, wx.ID_ANY,
                                     "From a Skype &export archive (*.json;*.tar)"
        )) if live.ijson else None
        self.Bind(wx.EVT_MENU, self.on_new_blank, item_blank)
        if item_live:   self.Bind(wx.EVT_MENU, self.on_new_live,   item_live)
        if item_export: self.Bind(wx.EVT_MENU, self.on_new_export, item_export)

        btn = self.button_new
        sz_btn, pt_btn = btn.Size, btn.Position
        pt_btn = btn.Parent.ClientToScreen(pt_btn)
        menu.SetOwnerHeight(sz_btn.y)
        if menu.Size.width < sz_btn.width:
            menu.Size = sz_btn.width, menu.Size.height
        menu.Popup((pt_btn), self)


    def on_new_blank(self, event):
        """
        Handler for creating a new blank database, asks for username, 
        populates a new database and opens the database page.
        """
        dialog1 = wx.TextEntryDialog(self, "Enter Skype username for new database:",
                                     conf.Title, style=wx.OK | wx.CANCEL)
        dialog1.CenterOnParent()
        if wx.ID_OK != dialog1.ShowModal(): return
        user = dialog1.GetValue().strip()
        if not user: return

        filename0 = live.make_db_path(user)
        util.try_ignore(os.makedirs, os.path.dirname(filename0))
        dialog2 = wx.FileDialog(parent=self, message="Save new database",
            defaultDir=os.path.dirname(filename0),
            defaultFile=os.path.basename(filename0),
            wildcard="SQLite database (*.db)|*.db|All files|*.*",
            style=wx.FD_OVERWRITE_PROMPT | wx.FD_SAVE | wx.RESIZE_BORDER
        )
        if wx.ID_OK != dialog2.ShowModal(): return

        wx.YieldIfNeeded() # Allow UI to refresh
        filename = controls.get_dialog_path(dialog2)

        if filename in self.dbs or filename in self.workers_import:
            return wx.MessageBox("%s is currently open in %s, cannot overwrite." % 
                                 (filename, conf.Title), conf.Title, wx.OK)

        busy = controls.BusyPanel(self, "Creating new database..")
        try:
            logger.info("Creating new blank database %s for user '%s'.", filename, user)
            db = skypedata.SkypeDatabase(filename, truncate=True)
            db.ensure_schema()
            db.insert_account({"skypename": user})
            db.tables_list = None # Force reload
            db.update_accountinfo()
        except Exception:
            _, e, tb = sys.exc_info()
            util.try_ignore(os.unlink, filename)
            six.reraise(type(e), e, tb)
        finally: busy.Close()

        self.load_database(filename, db)
        self.update_database_list(filename)
        self.load_database_page(filename)


    def on_new_live(self, event):
        """
        Handler for creating new database from live, asks for username and
        password, opens database page and starts syncing data.
        """
        dialog1 = LoginDialog(self, title="Log in to Skype online")
        if wx.ID_OK != dialog1.ShowModal(): return
        user, pw = dialog1.Username, dialog1.Password
        if not user or not pw: return

        filename0 = live.make_db_path(user)
        util.try_ignore(os.makedirs, os.path.dirname(filename0))
        dialog2 = wx.FileDialog(parent=self, message="Save new database",
            defaultDir=os.path.dirname(filename0),
            defaultFile=os.path.basename(filename0),
            wildcard="SQLite database (*.db)|*.db|All files|*.*",
            style=wx.FD_OVERWRITE_PROMPT | wx.FD_SAVE | wx.RESIZE_BORDER
        )
        if wx.ID_OK != dialog2.ShowModal(): return

        wx.YieldIfNeeded() # Allow UI to refresh
        filename = controls.get_dialog_path(dialog2)

        if filename in self.dbs or filename in self.workers_import:
            return wx.MessageBox("%s is currently open in %s, cannot overwrite." % 
                                 (filename, conf.Title), conf.Title, wx.OK)

        skype = live.SkypeLogin()
        busy = controls.BusyPanel(self, "Logging in as '%s'." % user)
        self.Refresh()
        try:
            try: skype.login(user, pw, token=False, init_db=False)
            except Exception as e:
                busy.Close()
                return wx.MessageBox("Failed to log in as '%s':\n\n%s" % 
                                     (user, util.format_exc(e)),
                                     conf.Title, wx.OK | wx.ICON_ERROR)

            conf.Login.setdefault(filename, {})["password"] = util.obfuscate(pw)
            try:
                logger.info("Creating new Skype database file %s from Skype online "
                            "for user '%s'.", filename, user)
                skype.init_db(filename, truncate=True)
                skype.save("accounts", skype.skype.user)
                skype.db.tables_list = None # Force reload
                skype.db.update_accountinfo()
            except Exception:
                _, e, tb = sys.exc_info()
                util.try_ignore(skype.db and skype.db.close)
                util.try_ignore(os.unlink, filename)
                logger.exception("Error saving account %r.", skype.skype.user)
                six.reraise(type(e), e, tb)
        finally: busy.Close()

        conf.Login.setdefault(filename, {})["sync_older"] = False
        self.load_database(filename, skype.db)
        self.update_database_list(filename)
        page = self.load_database_page(filename)
        if not page: return

        if not conf.Login.get(filename, {}).get("store"):
            conf.Login.get(filename, {}).pop("password", None)
        page.notebook.Selection = page.pageorder[page.page_live]
        if not conf.Login.get(filename, {}).get("sync"):
            page.on_live_result(action="login", opts={"sync": True})


    def on_new_export(self, event):
        """
        Handler for creating a new blank database from Skype export,
        opens dialogs for choosing export file and database location.
        """
        dialog1 = self.dialog_openexport
        dialog1.ShowModal()
        efilename = dialog1.GetPath()
        if not efilename: return

        user = live.SkypeExport.export_get_account(efilename)
        if not user: return wx.MessageBox("No Skype username found in %s." % efilename, 
                                          conf.Title, wx.OK | wx.ICON_WARNING)

        filename0 = live.make_db_path(user)
        util.try_ignore(os.makedirs, os.path.dirname(filename0))
        dialog2 = wx.FileDialog(parent=self, message="Save new database",
            defaultDir=os.path.dirname(filename0),
            defaultFile=os.path.basename(filename0),
            wildcard="SQLite database (*.db)|*.db|All files|*.*",
            style=wx.FD_OVERWRITE_PROMPT | wx.FD_SAVE | wx.RESIZE_BORDER
        )
        if wx.ID_OK != dialog2.ShowModal(): return

        wx.YieldIfNeeded() # Allow UI to refresh
        filename = controls.get_dialog_path(dialog2)

        if filename in self.dbs or filename in self.workers_import:
            return wx.MessageBox("%s is currently open in %s, cannot overwrite." % 
                                 (filename, conf.Title), conf.Title, wx.OK)

        def on_cancel():
            result = wx.OK == wx.MessageBox("Cancel import?", conf.Title, wx.OK | wx.CANCEL)
            if result:
                worker.stop(drop_results=False)
                self.workers_import.pop(filename, None)
            return result

        def on_progress(result):
            if result.get("error") or result.get("stop"):
                util.try_ignore(lambda: db.close())
                util.try_ignore(os.unlink, filename)
            if result.get("done"):
                worker.stop()
                self.workers_import.pop(filename, None)

            def after():
                if not self: return

                if result.get("error"):
                    dlg.Destroy()
                    guibase.status("Error parsing Skype export")
                    wx.MessageBox("Error parsing Skype export:\n%s" % result["error_short"],
                                  conf.Title, wx.OK | wx.ICON_ERROR)
                elif result.get("stop"):
                    dlg.Destroy()
                    guibase.status()
                elif result.get("done"):
                    dlg.Destroy()
                    guibase.status()
                    db.close()
                    self.update_database_list(filename)
                    self.load_database_page(filename)
                else:
                    t = ", ".join(util.plural(x[:-1], result["counts"][x], sep=",")
                                  for x in sorted(result["counts"]))
                    dlg.Message = "Parsed %s." % t

            wx.CallAfter(after)

        try:
            db = live.SkypeExport(efilename, filename)
        except Exception:
            _, e, tb = sys.exc_info()
            util.try_ignore(os.unlink, filename)
            six.reraise(type(e), e, tb)

        dlg = controls.ProgressWindow(self, "Import progress",
                                      cancel=on_cancel, agwStyle=wx.ALIGN_CENTER)
        dlg.Position = [self.Position[i] + a - b for i, (a, b) in enumerate(zip(self.Size, dlg.Size))]
        dlg.Pulse()
        guibase.status("Creating new database from Skype export.")
        logger.info("Creating new database %s from Skype export %s, user '%s'.",
                    filename, efilename, user)
        worker = workers.SkypeArchiveThread(on_progress)
        self.workers_import[filename] = worker
        worker.work({"action": "parse", "db": db})


    def on_open_database(self, event):
        """
        Handler for open database menu or button, displays a file dialog and
        loads the chosen database.
        """
        if wx.ID_OK == self.dialog_openfile.ShowModal():
            filename = self.dialog_openfile.GetPath()
            if filename:
                self.update_database_list(filename)
                self.load_database_page(filename)


    def on_open_database_event(self, event):
        """
        Handler for OpenDatabaseEvent, updates db list and loads the event
        database.
        """
        filename = os.path.realpath(event.file)
        self.update_database_list(filename)
        self.load_database_page(filename)


    def on_recent_file(self, event):
        """Handler for clicking an entry in Recent Files menu."""
        filename = self.history_file.GetHistoryFile(event.Id - wx.ID_FILE1)
        self.update_database_list(filename)
        self.load_database_page(filename)


    def on_add_from_folder(self, event):
        """
        Handler for clicking to select folder where to search for databases,
        updates database list.
        """
        if self.dialog_selectfolder.ShowModal() == wx.ID_OK:
            if self.button_folder.FindFocus() == self.button_folder:
                self.list_db.SetFocus()
            self.button_folder.Enabled = False
            folder = self.dialog_selectfolder.GetPath()
            guibase.status("Detecting databases under %s.", folder, log=True)
            wx.YieldIfNeeded()
            count = 0
            for filename in skypedata.find_databases(folder):
                if filename not in self.db_filenames:
                    logger.info("Detected database %s.", filename)
                    self.update_database_list(filename)
                    count += 1
            self.button_folder.Enabled = True
            guibase.status("Detected %s under %s.",
                           util.plural("new database", count), folder, log=True)


    def on_open_current_database(self, event):
        """Handler for clicking to open selected files from database list."""
        if self.db_filename:
            self.load_database_page(self.db_filename)


    def on_open_from_list_db(self, event):
        """Handler for clicking to open selected files from database list."""
        if event.GetIndex() > 0:
            self.load_database_page(self.list_db.GetItemText(event.GetIndex()))


    def update_database_stats(self, filename):
        """Opens the database and updates main page UI with database info."""
        db = None
        try:
            db = self.dbs.get(filename) or skypedata.SkypeDatabase(filename)
        except Exception as e:
            self.label_account.Value = "(database not readable)"
            self.label_messages.Value = "Error text: %s" % util.format_exc(e)
            self.label_account.ForegroundColour = conf.LabelErrorColour 
            self.label_chats.ForegroundColour = conf.LabelErrorColour
            logger.exception("Error opening %s.", filename)
            return
        try:
            stats = db.get_general_statistics(full=False)
            if "username" in stats:
                text = stats["username"]
                if "name" in stats and stats["name"] != text:
                    text = "%s (%s)" % (stats["name"], text)
                self.label_account.Value = text
            text = util.plural("chat", stats["chats"], sep=",")
            if stats.get("lastmessage_chat"):
                text += ", latest %(lastmessage_chat)s" % stats
            self.label_chats.Value = text
            text = util.plural("message", stats["messages"], sep=",")
            if stats.get("lastmessage_dt"):
                text += ", last at %(lastmessage_dt)s" % stats
            self.label_messages.Value = text
            data = self.db_filenames.get(filename, {})
            data["account"] = self.label_account.Value
            data["chats"] = self.label_chats.Value
            data["messages"] = self.label_messages.Value
        except Exception as e:
            if not self.label_account.Value:
                self.label_account.Value = "(not recognized as a Skype database)"
                self.label_account.ForegroundColour = conf.LabelErrorColour
            self.label_chats.Value = "Error text: %s" % util.format_exc(e)
            self.label_chats.ForegroundColour = conf.LabelErrorColour
            logger.exception("Error loading data from %s.", filename)
        if db and not db.has_consumers():
            db.close()
            self.dbs.pop(filename, None)


    def update_database_detail(self):
        """Updates database detail panel with current database information."""
        if not self or not self.db_filename: return

        filename = self.db_filename
        path, tail = os.path.split(filename)
        self.label_db.Value = tail
        self.label_path.Value = path
        self.label_size.Value = self.label_modified.Value = ""
        self.label_account.Value = self.label_chats.Value = ""
        self.label_messages.Value = ""
        self.label_account.ForegroundColour = self.ForegroundColour
        self.label_size.ForegroundColour = self.ForegroundColour
        self.label_chats.ForegroundColour = self.ForegroundColour
        if not self.panel_db_detail.Shown:
            self.panel_db_main.Hide()
            self.panel_db_detail.Show()
            self.panel_db_detail.Parent.Layout()
        if os.path.exists(filename):
            sz = os.path.getsize(filename)
            dt = datetime.datetime.fromtimestamp(os.path.getmtime(filename))
            self.label_size.Value = util.format_bytes(sz)
            self.label_modified.Value = dt.strftime("%Y-%m-%d %H:%M:%S")
            data = self.db_filenames[filename]
            if data["size"] == sz and data["last_modified"] == dt \
            and data["messages"]:
                # File does not seem changed: use cached values
                self.label_account.Value = data["account"]
                self.label_chats.Value = data["chats"]
                self.label_messages.Value = data["messages"]
            else:
                idx = self.list_db.FindItem(filename)
                if idx > 0: self.list_db.RefreshRow(idx)
                wx.CallLater(10, self.update_database_stats, filename)
        else:
            self.label_size.Value = "File does not exist."
            self.label_size.ForegroundColour = conf.LabelErrorColour


    def on_select_list_db(self, event):
        """Handler for selecting an item in main list, updates info panel."""
        filename = self.list_db.GetItemText(event.GetIndex())
        if event.GetIndex() > 0 \
        and filename != self.db_filename:
            self.db_filename = filename
            self.update_database_detail()
        elif event.GetIndex() == 0 and not self.panel_db_main.Shown:
            self.db_filename = None
            self.panel_db_main.Show()
            self.panel_db_detail.Hide()
            self.panel_db_main.Parent.Layout()
        # Save last selected files in db lists, to reselect them on rerun
        del conf.LastSelectedFiles[:]
        selected = self.list_db.GetFirstSelected()
        while selected > 0:
            filename = self.list_db.GetItemText(selected)
            conf.LastSelectedFiles.append(filename)
            selected = self.list_db.GetNextSelected(selected)
        util.run_once(conf.save)


    def on_exit(self, event):
        """
        Handler on application exit, asks about unsaved changes, if any.
        """
        if not self: return
        do_exit = True
        unsaved_pages = {} # {DatabasePage: filename, }
        syncing_pages = {} # {DatabasePage: filename, }
        merging_pages = [] # [MergerPage title, ]

        if any(x.is_alive() for x in self.workers_import.values()):
            if wx.OK != wx.MessageBox(
                "Import is currently in progress.\n\nExit anyway?",
                conf.Title, wx.OK | wx.CANCEL | wx.ICON_WARNING
            ): do_exit = False

        for page, db in self.db_pages.items() if do_exit else ():
            if page and db.live.is_logged_in() and page.worker_live.is_working():
                syncing_pages[page] = db.filename
        if syncing_pages:
            if wx.OK != wx.MessageBox(
                "Live syncing is currently in progress in %s.\n\nExit anyway?" % 
                "\n".join(textwrap.wrap(", ".join(syncing_pages.values()))),
                conf.Title, wx.OK | wx.CANCEL | wx.ICON_WARNING
            ): do_exit = False

        for page, db in self.db_pages.items() if do_exit else ():
            if page and page.get_unsaved_grids():
                unsaved_pages[page] = db.filename
        if unsaved_pages:
            response = wx.MessageBox(
                "There are unsaved changes in data grids\n(%s).\n\n"
                "Save changes before closing?" %
                "\n".join(textwrap.wrap(", ".join(unsaved_pages.values()))),
                conf.Title, wx.YES | wx.NO | wx.CANCEL | wx.ICON_INFORMATION
            )
            do_exit = (wx.CANCEL != response)
            if wx.YES == response:
                do_exit = all(p.save_unsaved_grids() for p in unsaved_pages)
        if do_exit:
            merging_pages = [x.title for x in self.merger_pages 
                             if x.is_merging and x.title]
        if merging_pages:
            response = wx.MessageBox(
                "Merging is currently in progress in %s.\n\nExit anyway? "
                "This can result in corrupt data." % 
                "\n".join(textwrap.wrap(", ".join(merging_pages))),
                conf.Title, wx.OK | wx.CANCEL | wx.ICON_WARNING)
            do_exit = (wx.CANCEL != response)
        if do_exit:
            for x in self.workers_import.values(): x.stop(drop_results=False)
            for page in self.db_pages:
                if not page: continue # for page, if dead object
                active_idx = page.notebook.Selection
                if active_idx:
                    conf.LastActivePage[page.db.filename] = active_idx
                elif page.db.filename in conf.LastActivePage:
                    del conf.LastActivePage[page.db.filename]
                page.save_page_conf()
                page.worker_live.stop()
                for worker in page.workers_search.values(): worker.stop()
                page.db.close()
            for page in self.merger_pages:
                page.worker_merge.stop(), page.worker_import.stop()
                page.db1.close(), page.db2.close()
            self.worker_detection.stop()

            # Save last selected files in db lists, to reselect them on rerun
            del conf.LastSelectedFiles[:]
            selected = self.list_db.GetFirstSelected()
            while selected > 0:
                filename = self.list_db.GetItemText(selected)
                conf.LastSelectedFiles.append(filename)
                selected = self.list_db.GetNextSelected(selected)
            if not conf.WindowIconized:
                conf.WindowPosition = self.Position[:]
            conf.WindowSize = [-1, -1] if self.IsMaximized() else self.Size[:]
            conf.save()
            try: self.trayicon.Destroy()
            except Exception: pass
            for x in self.workers_import.values(): x.join()
            sys.exit()


    def on_close_page(self, event):
        """
        Handler for closing a page, asks the user about saving unsaved data,
        if any, removes page from main notebook and updates accelerators.
        """
        if event.EventObject == self.notebook:
            page = self.notebook.GetPage(event.GetSelection())
        else:
            page = event.EventObject
            page.Show(False)
        if self.page_log == page:
            if not self.page_log.is_hidden:
                event.Veto() # Veto delete event
                self.on_showhide_log(None) # Fire remove event
            self.pages_visited = [x for x in self.pages_visited if x != page]
            self.page_log.Show(False)
            return
        elif (not isinstance(page, (DatabasePage, MergerPage))
        or not page.ready_to_close):
            return event.Veto()

        # Remove page from MainWindow data structures
        if isinstance(page, DatabasePage):
            do_close = True

            if page.db.live.is_logged_in() and page.worker_live.is_working():
                if wx.OK != wx.MessageBox(
                    "Live syncing is currently in progress.\n\nClose anyway?",
                    conf.Title, wx.OK | wx.CANCEL | wx.ICON_WARNING
                ): do_close = False

            unsaved = page.get_unsaved_grids() if do_close else []
            if unsaved:
                response = wx.MessageBox(
                    "Some tables in %s have unsaved data (%s).\n\n"
                    "Save changes before closing?" % (
                        page.db, ", ".join(sorted(x.table for x in unsaved))
                    ), conf.Title,
                    wx.YES | wx.NO | wx.CANCEL | wx.ICON_INFORMATION
                )
                if wx.YES == response:
                    do_close = page.save_unsaved_grids()
                elif wx.CANCEL == response:
                    do_close = False
            if not do_close:
                return event.Veto()

            if page.notebook.Selection:
                conf.LastActivePage[page.db.filename] = page.notebook.Selection
            elif page.db.filename in conf.LastActivePage:
                del conf.LastActivePage[page.db.filename]

            for worker in page.workers_search.values(): worker.stop()
            page.worker_live.stop()
            page.save_page_conf()

            if page in self.db_pages:
                del self.db_pages[page]
            page_dbs = [page.db]
            guibase.status("Closed database tab for %s.", page.db, log=True)
            util.run_once(conf.save)
        else:
            if page.is_merging:
                response = wx.MessageBox(
                    "Merging is currently in progress in %s.\n\nClose anyway? "
                    "This can result in corrupt data." % page.title,
                    conf.Title, wx.OK | wx.CANCEL | wx.ICON_WARNING)
                if wx.CANCEL == response:
                    return event.Veto()

            page.worker_merge.stop()
            page.worker_import.stop()
            if page.worker_merge.is_alive(): page.worker_merge.join()
            if page.worker_import.is_alive(): page.worker_import.join()
            if page in self.merger_pages:
                del self.merger_pages[page]
            page_dbs = [page.db1, page.db2]
            guibase.status("Closed comparison tab for %s and %s.",
                           page.db1, page.db2, log=True)

        # Close databases, if not used in any other page
        for db in page_dbs:
            db.unregister_consumer(page)
            if not db.has_consumers():
                self.dbs.pop(db.filename, None)
                db.close()
                logger.info("Closed database %s.", db.filename)
        # Remove any dangling references
        if self.page_merge_latest == page:
            self.page_merge_latest = None
        if self.page_db_latest == page:
            self.page_db_latest = next((i for i in self.pages_visited[::-1]
                                        if isinstance(i, DatabasePage)), None)
        self.SendSizeEvent() # Multiline wx.Notebooks need redrawing
        self.UpdateAccelerators() # Remove page accelerators

        # Remove page from visited pages order
        self.pages_visited = [x for x in self.pages_visited if x != page]
        index_new = 0
        if self.pages_visited:
            for i in range(self.notebook.GetPageCount()):
                if self.notebook.GetPage(i) == self.pages_visited[-1]:
                    index_new = i
                    break
        self.notebook.SetSelection(index_new)


    def on_clear_searchall(self, event):
        """
        Handler for clicking to clear search history in a database page,
        confirms action and clears history globally.
        """
        choice = wx.MessageBox("Clear search history?", conf.Title,
                               wx.OK | wx.CANCEL | wx.ICON_WARNING)
        if wx.OK == choice:
            conf.SearchHistory = []
            for page in self.db_pages:
                page.edit_searchall.SetChoices(conf.SearchHistory)
                page.edit_searchall.ShowDropDown(False)
            self.dialog_search.SetChoices(conf.SearchHistory)
            util.run_once(conf.save)


    def get_unique_tab_title(self, title):
        """
        Returns a title that is unique for the current notebook - if the
        specified title already exists, appends a counter to the end,
        e.g. "Database comparison (1)". Title is shortened from the left
        if longer than allowed.
        """
        if len(title) > conf.MaxTabTitleLength:
            title = "..%s" % title[-conf.MaxTabTitleLength:]
        unique = title_base = title
        all_titles = [self.notebook.GetPageText(i)
                      for i in range(self.notebook.GetPageCount())]
        i = 1 # Start counter from 1
        while unique in all_titles:
            unique = "%s (%d)" % (title_base, i)
            i += 1
        return unique


    def load_database(self, filename, db=None):
        """
        Tries to load the specified database, if not already open,
        and returns it.
        """
        db0 = self.dbs.get(filename)
        if db0: db = db0
        elif not os.path.exists(filename):
            wx.MessageBox("Nonexistent file: %s." % filename,
                          conf.Title, wx.OK | wx.ICON_WARNING)
        else:
            try:
                db = db or skypedata.SkypeDatabase(filename)
            except Exception:
                is_accessible = False
                try:
                    with open(filename, "rb"):
                        is_accessible = True
                except Exception:
                    pass
                if not is_accessible:
                    wx.MessageBox(
                        "Could not open %s.\n\n"
                        "Some other process may be using the file."
                        % filename, conf.Title, wx.OK | wx.ICON_WARNING)
                else:
                    wx.MessageBox(
                        "Could not open %s.\n\n"
                        "Not a valid SQLITE database?" % filename,
                        conf.Title, wx.OK | wx.ICON_WARNING)
            if db:
                if not db0:
                    logger.info("Opened %s (%s).", db, util.format_bytes(
                                db.filesize))
                    guibase.status("Reading database file %s.", db)
                self.dbs[filename] = db
                # Add filename to Recent Files menu and conf, if needed
                if filename in conf.RecentFiles: # Remove earlier position
                    idx = conf.RecentFiles.index(filename)
                    try: self.history_file.RemoveFileFromHistory(idx)
                    except Exception: pass
                self.history_file.AddFileToHistory(filename)
                util.add_unique(conf.RecentFiles, filename, -1,
                                conf.MaxRecentFiles)
                util.run_once(conf.save)
        return db


    def load_database_page(self, filename):
        """
        Tries to load the specified database, if not already open, create a
        subpage for it, if not already created, and focuses the subpage.

        @return  database page instance
        """
        page, db = None, self.dbs.get(filename)
        if db and db in self.db_pages.values():
            page = next((x for x in self.db_pages if x and x.db == db), None)
        if not page:
            if filename in self.workers_import:
                wx.MessageBox("%s is currently being imported to, cannot open." % 
                              filename, conf.Title, wx.OK | wx.ICON_WARNING)
                return

            if not db:
                db = self.load_database(filename)
            if db:
                guibase.status("Opening database file %s." % db)
                tab_title = self.get_unique_tab_title(db.filename)
                page = DatabasePage(self.notebook, tab_title, db, self.memoryfs)
                self.db_pages[page] = db
                self.UpdateAccelerators()
                util.run_once(conf.save)
                self.Bind(wx.EVT_LIST_DELETE_ALL_ITEMS,
                          self.on_clear_searchall, page.edit_searchall)
        if page:
            idx0 = self.list_db.GetFirstSelected()
            idx  = self.list_db.FindItem(filename)
            if idx0 >= 0 and idx0 != idx: self.list_db.Select(idx0, False)
            if idx > 0 and idx != idx0:
                self.list_db.Select(idx, True)
                self.list_db.EnsureVisible(idx)
            for i in range(self.notebook.GetPageCount()):
                if self.notebook.GetPage(i) == page:
                    self.notebook.SetSelection(i)
                    self.update_notebook_header()
                    break # for i
        return page



class DatabasePage(wx.Panel):
    """
    A wx.Notebook page for managing a single database file, has its own
    Notebook with a number of pages for searching, browsing chat history and
    database tables, information and contact import.
    """

    def __init__(self, parent_notebook, title, db, memoryfs):
        wx.Panel.__init__(self, parent=parent_notebook)
        self.parent_notebook = parent_notebook
        self.title = title

        self.pageorder = {} # {page: notebook index, }
        self.ready_to_close = False
        self.db = db
        self.db.register_consumer(self)
        self.db_grids = {} # {"tablename": SqliteGridBase, }
        self.memoryfs = memoryfs
        self.timeline_timer = None # Timeline highlight callback timer
        parent_notebook.InsertPage(1, self, title)
        busy = controls.BusyPanel(self, "Loading \"%s\"." % db.filename)
        self.counter = lambda x={"c": 0}: x.update(c=1+x["c"]) or x["c"]
        ColourManager.Manage(self, "BackgroundColour", "WidgetColour")
        self.Bind(wx.EVT_SYS_COLOUR_CHANGED, self.on_sys_colour_change)

        self.chat = None # Currently viewed chat
        self.chats = []  # All chats in database
        self.chat_filter = { # Filter for currently shown chat history
            "daterange": None,      # Current date range
            "startdaterange": None, # Initial date range
            "text": "",             # Text in message content
            "participants": None    # Messages from [skype name, ]
        }
        self.contact = None # Currently viewed contact
        self.contacts = []  # All contacts in database
        self.contact_sort_field = "last_message_datetime"
        self.imagecache = {} # {("contact", contact ID): wx.Image}
        self.stats_sort_field = "name"
        self.stats_expand = {"clouds": False, "emoticons": False,
                             "shared_media": False}

        # Create search structures and threads
        self.Bind(EVT_WORKER, self.on_searchall_result)
        self.workers_search = {} # {search ID: workers.SearchThread, }
        self.db.live.progress = self.on_live_result
        self.worker_live = workers.LiveThread(self.on_live_result, self.db.live)

        sizer = self.Sizer = wx.BoxSizer(wx.VERTICAL)

        sizer_header = wx.BoxSizer(wx.HORIZONTAL)
        label_title = self.label_title = wx.StaticText(parent=self, label="")
        sizer_header.Add(label_title, flag=wx.ALIGN_CENTER_VERTICAL)
        sizer_header.AddStretchSpacer()


        self.label_search = wx.StaticText(self, -1, "&Search in messages:")
        sizer_header.Add(self.label_search, border=5,
                         flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        edit_search = self.edit_searchall = controls.TextCtrlAutoComplete(
            self, description=conf.HistorySearchDescription,
            size=(300, -1), style=wx.TE_PROCESS_ENTER)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_searchall, edit_search)
        tb = self.tb_search = wx.ToolBar(parent=self,
                                         style=wx.TB_FLAT | wx.TB_NODIVIDER)

        bmp = wx.ArtProvider.GetBitmap(wx.ART_GO_FORWARD, wx.ART_TOOLBAR,
                                       (16, 16))
        tb.SetToolBitmapSize(bmp.Size)
        tb.AddTool(wx.ID_FIND, "", bitmap=bmp, shortHelp="Start search")
        tb.Realize()
        self.Bind(wx.EVT_TOOL, self.on_searchall, id=wx.ID_FIND)
        sizer_header.Add(edit_search, border=5, flag=wx.RIGHT)
        sizer_header.Add(tb, flag=wx.GROW)
        sizer.Add(sizer_header,
                  border=5, flag=wx.LEFT | wx.RIGHT | wx.TOP | wx.GROW)
        sizer.Layout() # To avoid searchbox moving around during page creation

        notebook = self.notebook = wx.lib.agw.labelbook.FlatImageBook(
            parent=self, agwStyle=wx.lib.agw.fmresources.INB_LEFT, style=wx.BORDER_STATIC)

        il = wx.ImageList(32, 32)
        idx1 = il.Add(images.PageSearch.Bitmap)
        idx2 = il.Add(images.PageChats.Bitmap)
        idx3 = il.Add(images.PageContacts.Bitmap)
        idx4 = il.Add(images.PageInfo.Bitmap)
        idx5 = il.Add(images.PageTables.Bitmap)
        idx6 = il.Add(images.PageSQL.Bitmap)
        idx7 = il.Add(images.PageOnline.Bitmap)
        notebook.AssignImageList(il)

        self.create_page_search(notebook)
        self.create_page_chats(notebook)
        self.create_page_contacts(notebook)
        self.create_page_info(notebook)
        self.create_page_tables(notebook)
        self.create_page_sql(notebook)
        self.create_page_live(notebook)

        notebook.SetPageImage(0, idx1)
        notebook.SetPageImage(1, idx2)
        notebook.SetPageImage(2, idx3)
        notebook.SetPageImage(3, idx4)
        notebook.SetPageImage(4, idx5)
        notebook.SetPageImage(5, idx6)
        notebook.SetPageImage(6, idx7)

        sizer.Add(notebook, proportion=1, border=5, flag=wx.GROW | wx.ALL)

        self.dialog_savefile = wx.FileDialog(
            parent=self, style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT | wx.RESIZE_BORDER)
        # Need separate dialog w/o overwrite prompt, cannot swap style in Linux
        self.dialog_savefile_ow = wx.FileDialog(
            parent=self, style=wx.FD_SAVE | wx.RESIZE_BORDER)
        self.dialog_saveimage = wx.FileDialog(self,
                message="Save image as", wildcard=export.IMAGE_WILDCARD,
                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT | wx.FD_CHANGE_DIR | wx.RESIZE_BORDER)

        self.TopLevelParent.page_db_latest = self
        self.TopLevelParent.run_console(
            "page = self.page_db_latest # Database tab")
        self.TopLevelParent.run_console("db = page.db # SQLite database wrapper")

        self.Layout()
        self.toggle_filter(True)
        # Hack to get info-page multiline TextCtrls to layout without quirks.
        self.notebook.SetSelection(self.pageorder[self.page_info])
        # Hack to get chats-page filter split window to layout without quirks.
        self.notebook.SetSelection(self.pageorder[self.page_chats])
        self.notebook.SetSelection(self.pageorder[self.page_search])
        # Restore last active page
        if db.filename in conf.LastActivePage \
        and conf.LastActivePage[db.filename] != self.notebook.Selection:
            self.notebook.SetSelection(conf.LastActivePage[db.filename])

        try:
            self.load_data()
        finally:
            busy.Close()
        self.edit_searchall.SetFocus()
        wx.CallAfter(self.edit_searchall.SelectAll)


    def create_page_chats(self, notebook):
        """Creates a page for listing and reading chats."""
        page = self.page_chats = wx.Panel(parent=notebook)
        self.pageorder[page] = len(self.pageorder)
        notebook.AddPage(page, "Chats")
        sizer = page.Sizer = wx.BoxSizer(wx.VERTICAL)
        splitter = self.splitter_chats = wx.SplitterWindow(
            parent=page, style=wx.BORDER_NONE
        )
        splitter.SetMinimumPaneSize(100)

        panel1 = self.panel_chats1 = wx.Panel(parent=splitter)
        sizer1 = panel1.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_top = wx.BoxSizer(wx.HORIZONTAL)
        sizer_top.Add(
            wx.StaticText(panel1, label="A&ll chat entries in database:"),
            proportion=1, border=5, flag=wx.ALIGN_BOTTOM)
        list_chats = self.list_chats = controls.SortableListView(
            parent=panel1, style=wx.LC_REPORT)
        columns = [("title", "Chat"), ("message_count", "Messages"),
                   ("created_datetime", "Created"),
                   ("first_message_datetime", "First message"),
                   ("last_message_datetime", "Last message"),
                   ("type_name", "Type"), ("people", "People"), ]
        frmt = lambda r, c: r[c].strftime("%Y-%m-%d %H:%M") if r.get(c) else ""
        frmt_dt = lambda r, c: r[c].strftime("%Y-%m-%d") if r.get(c) else ""
        formatters = {"created_datetime": frmt_dt,
                      "first_message_datetime": frmt,
                      "last_message_datetime": frmt, }
        list_chats.SetColumns(columns)
        list_chats.SetColumnFormatters(formatters)
        list_chats.SetColumnsMaxWidth(300)
        edit_chatfilter = self.edit_chatfilter = controls.HintedTextCtrl(
            panel1, "Filter list", size=(75, -1))
        edit_chatfilter.SetToolTip("Filter items in chat list")
        self.Bind(wx.EVT_TEXT_ENTER, self.on_change_chatfilter, edit_chatfilter)
        sizer_top.Add(edit_chatfilter, flag=wx.RIGHT, border=15)
        button_export_chats = self.button_export_chats = \
            wx.Button(parent=panel1, label="Exp&ort chats")
        sizer_top.Add(button_export_chats)
        self.Bind(wx.EVT_BUTTON, self.on_export_chats_menu, button_export_chats)
        sizer1.Add(sizer_top, border=5,
                   flag=wx.RIGHT | wx.LEFT | wx.BOTTOM | wx.GROW)

        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED,
                  self.on_change_list_chats, list_chats)
        list_chats.Bind(wx.EVT_CONTEXT_MENU, self.on_menu_list_chats)
        sizer1.Add(list_chats, proportion=1, border=5,
                   flag=wx.GROW | wx.LEFT | wx.RIGHT)

        panel2 = self.panel_chats2 = wx.Panel(parent=splitter)
        sizer2 = panel2.Sizer = wx.BoxSizer(wx.VERTICAL)

        splitter_stc = self.splitter_stc = \
            wx.SplitterWindow(parent=panel2, style=wx.BORDER_NONE)
        splitter_stc.SetMinimumPaneSize(100)
        panel_stc1 = self.panel_stc1 = wx.Panel(parent=splitter_stc)
        panel_stc2 = self.panel_stc2 = wx.Panel(parent=splitter_stc)
        sizer_stc1 = panel_stc1.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_stc2 = panel_stc2.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_stc  = wx.BoxSizer(wx.HORIZONTAL)

        sizer_header = wx.BoxSizer(wx.HORIZONTAL)
        label_chat = self.label_chat = wx.StaticText(
            parent=panel_stc1, label="&Chat:", name="chat_history_label")

        tb = self.tb_chat = \
            wx.ToolBar(parent=panel_stc1, style=wx.TB_FLAT | wx.TB_NODIVIDER)
        tb.SetToolBitmapSize((24, 24))
        tb.AddCheckTool(wx.ID_JUMP_TO, "", bitmap1=images.ToolbarTimeline.Bitmap,
                        shortHelp="Toggle timeline panel  (Alt-J)")
        tb.AddCheckTool(wx.ID_ZOOM_100, "",
                        bitmap1=images.ToolbarMaximize.Bitmap,
                        shortHelp="Maximize chat panel  (Alt-M)")
        tb.AddCheckTool(wx.ID_PROPERTIES, "",
                        bitmap1=images.ToolbarStats.Bitmap,
                        shortHelp="Toggle chat statistics  (Alt-I)")
        tb.AddCheckTool(wx.ID_MORE, "", bitmap1=images.ToolbarFilter.Bitmap,
                        shortHelp="Toggle filter panel  (Alt-G)")
        tb.Realize()
        self.Bind(wx.EVT_TOOL, self.on_toggle_timeline, id=wx.ID_JUMP_TO)
        self.Bind(wx.EVT_TOOL, self.on_toggle_maximize, id=wx.ID_ZOOM_100)
        self.Bind(wx.EVT_TOOL, self.on_toggle_stats,    id=wx.ID_PROPERTIES)
        self.Bind(wx.EVT_TOOL, self.on_toggle_filter,   id=wx.ID_MORE)

        button_rename = self.button_rename = \
            wx.Button(parent=panel_stc1, label="Re&name..")
        button_export = self.button_export_chat = \
            wx.Button(parent=panel_stc1, label="&Export messages to file")
        button_rename.SetToolTip(
            "Set new name for the conversation or a participant")
        button_export.SetToolTip(
            "Export currently shown messages to a file")
        self.Bind(wx.EVT_BUTTON, self.on_rename_item, button_rename)
        self.Bind(wx.EVT_BUTTON, self.on_export_chat, button_export)
        sizer_header.Add(label_chat, proportion=1, border=5, flag=wx.LEFT |
                         wx.ALIGN_BOTTOM)
        sizer_header.Add(tb, flag=wx.ALIGN_CENTER_VERTICAL)
        sizer_header.Add(button_rename, border=15, flag=wx.LEFT |
                         wx.ALIGN_CENTER_VERTICAL)
        sizer_header.Add(button_export, border=5, flag=wx.LEFT |
                         wx.ALIGN_CENTER_VERTICAL)

        timeline = self.list_timeline = ChatContentTimeline(panel_stc1, size=(150, -1))
        timeline.Hide()
        self.Bind(wx.EVT_LISTBOX, self.on_select_timeline, timeline)
        timeline.Bind(wx.EVT_KILL_FOCUS, self.on_blur_timeline)
        stc = self.stc_history = ChatContentSTC(
            parent=panel_stc1, style=wx.BORDER_STATIC, name="chat_history")
        stc.SetDatabasePage(self)
        stc.STC.Bind(wx.stc.EVT_STC_UPDATEUI, self.on_scroll_chat_history)
        html_stats = self.html_stats = wx.html.HtmlWindow(parent=panel_stc1)
        html_stats.Bind(wx.html.EVT_HTML_LINK_CLICKED,
                        self.on_click_html_stats)
        html_stats.Bind(wx.EVT_SCROLLWIN, self.on_scroll_html_stats)
        html_stats.Bind(wx.EVT_SIZE, self.on_size_html_stats)
        html_stats.Hide()

        sizer_stc.Add(timeline, flag=wx.GROW)
        sizer_stc.Add(stc, proportion=1, flag=wx.GROW)
        sizer_stc1.Add(sizer_header, border=5, flag=wx.GROW | wx.RIGHT |
                       wx.BOTTOM)
        sizer_stc1.Add(sizer_stc, proportion=1, border=5, flag=wx.GROW)
        sizer_stc1.Add(html_stats, proportion=1, flag=wx.GROW)

        label_filter = \
            wx.StaticText(parent=panel_stc2, label="Find messages with &text:")
        edit_filter = self.edit_filtertext = wx.TextCtrl(
            parent=panel_stc2, size=(100, -1), style=wx.TE_PROCESS_ENTER)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_filter_chat, edit_filter)
        edit_filter.SetToolTip("Find messages containing the exact text")
        label_range = wx.StaticText(
            parent=panel_stc2, label="Show messages from time perio&d:")
        date1 = self.edit_filterdate1 = controls.DatePickerCtrl(panel_stc2, size=(90 * controls.COMBO_WIDTH_FACTOR, -1))
        date2 = self.edit_filterdate2 = controls.DatePickerCtrl(panel_stc2, size=(90 * controls.COMBO_WIDTH_FACTOR, -1))
        date1.Format = date2.Format = "%Y-%m-%d"
        date2.SetPopupAnchor(wx.RIGHT)
        date1.SetToolTip("Date in the form YYYY-MM-DD")
        date2.SetToolTip("Date in the form YYYY-MM-DD")
        self.Bind(wx.EVT_TEXT, self.on_change_filterdate, date1)
        self.Bind(wx.EVT_TEXT, self.on_change_filterdate, date2)
        controls.RangeSlider.MARKER_LABEL_SHOW = False
        range_date = self.range_date = \
            controls.RangeSlider(parent=panel_stc2, fmt="%Y-%m-%d")
        range_date.SetRange(None, None)
        range_date.Bind(wx.EVT_SLIDER, self.on_change_range_date)
        label_list = \
            wx.StaticText(parent=panel_stc2, label="Sho&w messages from:")
        agw_style = (wx.LC_REPORT | wx.LC_NO_HEADER | wx.LC_SINGLE_SEL |
                     wx.lib.agw.ultimatelistctrl.ULC_NO_HIGHLIGHT |
                     wx.lib.agw.ultimatelistctrl.ULC_HRULES |
                     wx.lib.agw.ultimatelistctrl.ULC_SHOW_TOOLTIPS)
        if hasattr(wx.lib.agw.ultimatelistctrl, "ULC_USER_ROW_HEIGHT"):
            agw_style |= wx.lib.agw.ultimatelistctrl.ULC_USER_ROW_HEIGHT
        list_participants = self.list_participants = \
            wx.lib.agw.ultimatelistctrl.UltimateListCtrl(parent=panel_stc2,
                                                         agwStyle=agw_style)
        ColourManager.Manage(list_participants, "ForegroundColour", wx.SYS_COLOUR_BTNTEXT)
        ColourManager.Manage(list_participants, "BackgroundColour", wx.SYS_COLOUR_WINDOW)
        try:
            ColourManager.Manage(list_participants._headerWin, "ForegroundColour", wx.SYS_COLOUR_BTNTEXT)
            ColourManager.Manage(list_participants._mainWin,   "BackgroundColour", wx.SYS_COLOUR_WINDOW)
        except Exception: pass
        list_participants.InsertColumn(0, "")
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_select_participant,
                  list_participants)
        if hasattr(list_participants, "SetUserLineHeight"):
            list_participants.SetUserLineHeight(conf.AvatarImageSize[1] + 2)
        sizer_dates = wx.BoxSizer(wx.HORIZONTAL)
        sizer_filter_buttons = wx.BoxSizer(wx.HORIZONTAL)
        button_filter_apply = self.button_chat_applyfilter = \
            wx.Button(parent=panel_stc2, label="A&pply filter")
        button_filter_export = self.button_chat_exportfilter = \
            wx.Button(parent=panel_stc2, label="Expo&rt filter")
        button_filter_reset = self.button_chat_unfilter = \
            wx.Button(parent=panel_stc2, label="Restore i&nitial")
        self.Bind(wx.EVT_BUTTON, self.on_filter_chat, button_filter_apply)
        self.Bind(wx.EVT_BUTTON, self.on_filterexport_chat,
                  button_filter_export)
        self.Bind(wx.EVT_BUTTON, self.on_filterreset_chat, button_filter_reset)
        button_filter_apply.SetToolTip(
            "Filters the conversation by the specified text, "
            "date range and participants.")
        button_filter_export.SetToolTip(
            "Exports filtered messages straight to file, "
            "without showing them (showing thousands of messages gets slow).")
        button_filter_reset.SetToolTip(
            "Restores filter controls to initial values and reapplies filter.")
        sizer_filter_buttons.Add(button_filter_apply)
        sizer_filter_buttons.AddSpacer(5)
        sizer_filter_buttons.Add(button_filter_export)
        sizer_filter_buttons.AddSpacer(5)
        sizer_filter_buttons.Add(button_filter_reset)
        sizer_filter_buttons.AddSpacer(5)
        sizer_dates.Add(date1)
        sizer_dates.AddStretchSpacer()
        sizer_dates.Add(date2)
        sizer_stc2.Add(label_filter, border=5, flag=wx.LEFT)
        sizer_stc2.Add(edit_filter, border=5, flag=wx.GROW | wx.LEFT)
        sizer_stc2.AddSpacer(5)
        sizer_stc2.Add(label_range, border=5, flag=wx.LEFT)
        sizer_stc2.Add(sizer_dates, border=5, flag=wx.GROW | wx.LEFT | wx.BOTTOM)
        sizer_stc2.Add(range_date, border=5, flag=wx.GROW | wx.LEFT)
        sizer_stc2.AddSpacer(5)
        sizer_stc2.Add(label_list, border=5, flag=wx.LEFT)
        sizer_stc2.Add(list_participants, proportion=1, border=5,
                       flag=wx.GROW | wx.LEFT)
        sizer_stc2.AddSpacer(5)
        sizer_stc2.Add(sizer_filter_buttons, proportion=0, border=5,
                       flag=wx.GROW | wx.LEFT | wx.RIGHT)

        splitter_stc.SplitVertically(panel_stc1, panel_stc2, sashPosition=0)
        splitter_stc.Unsplit(panel_stc2) # Hide filter panel
        sizer2.Add(splitter_stc, proportion=1, border=5, flag=wx.GROW | wx.ALL)

        sizer.AddSpacer(10)
        sizer.Add(splitter, proportion=1, flag=wx.GROW)
        splitter.SplitHorizontally(panel1, panel2, sashPosition=self.Size[1] // 3)
        panel2.Enabled = False


    def create_page_contacts(self, notebook):
        """Creates a page for viewing contacts."""
        page = self.page_contacts = wx.Panel(parent=notebook)
        self.pageorder[page] = len(self.pageorder)
        notebook.AddPage(page, "Contacts")
        sizer = page.Sizer = wx.BoxSizer(wx.VERTICAL)
        splitter = self.splitter_contacts = wx.SplitterWindow(
            parent=page, style=wx.BORDER_NONE
        )
        splitter.SetMinimumPaneSize(100)

        panel1 = self.panel_contacts1 = wx.Panel(parent=splitter)
        sizer1 = panel1.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_top = wx.BoxSizer(wx.HORIZONTAL)
        sizer_top.Add(
            wx.StaticText(panel1, label="A&ll contacts in database:"),
            proportion=1, border=5, flag=wx.ALIGN_BOTTOM)
        list_contacts = self.list_contacts = controls.SortableListView(
            parent=panel1, style=wx.LC_REPORT)
        columns = [("identity", "Account"), ("name", "Name"), ("phone", "Phone"),
                   ("first_message_datetime", "First message"),
                   ("last_message_datetime", "Last message"),
                   ("message_count_single", "1:1 messages"),
                   ("message_count_group", "Group chat messages"), ]
        frmt = lambda r, c: r[c].strftime("%Y-%m-%d %H:%M") if r.get(c) else ""
        formatters = {"first_message_datetime": frmt,
                      "last_message_datetime": frmt, }
        list_contacts.SetColumns(columns)
        list_contacts.SetColumnFormatters(formatters)
        list_contacts.SetColumnsMaxWidth(300)
        edit_contactfilter = self.edit_contactfilter = controls.HintedTextCtrl(
            panel1, "Filter list", size=(75, -1))
        edit_contactfilter.SetToolTip("Filter items in contacts list")
        self.Bind(wx.EVT_TEXT_ENTER, self.on_change_contactfilter, edit_contactfilter)
        sizer_top.Add(edit_contactfilter, flag=wx.RIGHT, border=15)
        button_export_contacts = self.button_export_contacts = \
            wx.Button(parent=panel1, label="Exp&ort contacts")
        sizer_top.Add(button_export_contacts)
        self.Bind(wx.EVT_BUTTON, self.on_export_contacts, button_export_contacts)
        sizer1.Add(sizer_top, border=5,
                   flag=wx.RIGHT | wx.LEFT | wx.BOTTOM | wx.GROW)

        panel2 = self.panel_contacts2 = wx.Panel(parent=splitter)
        sizer2 = panel2.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer2_top = wx.BoxSizer(wx.HORIZONTAL)
        label_contact = self.label_contact = wx.StaticText(parent=panel2)
        button_rename = self.button_rename_contacts = wx.Button(
            parent=panel2, label="&Rename")
        button_export = self.button_export_contact_chats = wx.Button(
            parent=panel2, label="&Export contact chats")
        html_contact = self.html_contact = wx.html.HtmlWindow(parent=panel2)
        html_contact.BackgroundColour = ColourManager.GetColour(wx.SYS_COLOUR_WINDOW)
        panel2.Disable()
        button_rename.Bind(wx.EVT_BUTTON, lambda e: self.on_rename_contact(self.contact, e))
        button_export.Bind(wx.EVT_BUTTON, self.on_export_contact_chats_menu)
        html_contact.Bind(wx.html.EVT_HTML_LINK_CLICKED, self.on_click_html_contact)

        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_change_list_contacts, list_contacts)
        sizer1.Add(list_contacts, proportion=1, border=5, flag=wx.GROW | wx.LEFT | wx.RIGHT)
        sizer2_top.Add(label_contact, border=5, flag=wx.GROW | wx.TOP)
        sizer2_top.AddStretchSpacer()
        sizer2_top.Add(button_rename, border=5, flag=wx.BOTTOM | wx.RIGHT)
        sizer2_top.Add(button_export, border=5, flag=wx.BOTTOM)
        sizer2.Add(sizer2_top, border=5, flag=wx.GROW | wx.ALL ^ wx.BOTTOM)
        sizer2.Add(html_contact,  border=5, flag=wx.GROW | wx.ALL ^ wx.TOP, proportion=1)

        sizer.AddSpacer(10)
        sizer.Add(splitter, proportion=1, flag=wx.GROW)
        splitter.SplitHorizontally(panel1, panel2, sashPosition=self.Size[1] // 3)


    def create_page_search(self, notebook):
        """Creates a page for searching chats."""
        page = self.page_search = wx.Panel(parent=notebook)
        self.pageorder[page] = len(self.pageorder)
        notebook.AddPage(page, "Search")
        sizer = page.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_top = wx.BoxSizer(wx.HORIZONTAL)

        label_html = self.label_html = \
            wx.html.HtmlWindow(page, style=wx.html.HW_SCROLLBAR_NEVER)
        label_html.SetFonts(normal_face=self.Font.FaceName,
                            fixed_face=self.Font.FaceName, sizes=[8] * 7)
        label_html.SetPage(step.Template(templates.SEARCH_HELP_SHORT).expand())

        tb = self.tb_search_settings = \
            wx.ToolBar(parent=page, style=wx.TB_FLAT | wx.TB_NODIVIDER)
        tb.MinSize = (195, -1)
        tb.SetToolBitmapSize((24, 24))
        tb.AddRadioTool(wx.ID_INDEX, "", bitmap1=images.ToolbarMessage.Bitmap,
            shortHelp="Search in message body")
        tb.AddRadioTool(wx.ID_PREVIEW, "", bitmap1=images.ToolbarContact.Bitmap,
            shortHelp="Search in contact information")
        tb.AddRadioTool(wx.ID_ABOUT, "", bitmap1=images.ToolbarTitle.Bitmap,
            shortHelp="Search in chat title and participants")
        tb.AddRadioTool(wx.ID_STATIC, "", bitmap1=images.ToolbarTables.Bitmap,
            shortHelp="Search in all columns of all database tables")
        tb.AddSeparator()
        tb.AddCheckTool(wx.ID_NEW, "", bitmap1=images.ToolbarTabs.Bitmap,
            shortHelp="New tab for each search  (Alt-N)", longHelp="")
        tb.AddTool(wx.ID_STOP, "", bitmap=images.ToolbarStopped.Bitmap,
            shortHelp="Stop current search, if any")
        tb.Realize()
        tb.ToggleTool(wx.ID_INDEX, conf.SearchInMessages)
        tb.ToggleTool(wx.ID_ABOUT, conf.SearchInChatInfo)
        tb.ToggleTool(wx.ID_PREVIEW, conf.SearchInContacts)
        tb.ToggleTool(wx.ID_STATIC, conf.SearchInTables)
        tb.ToggleTool(wx.ID_NEW, conf.SearchUseNewTab)
        for id in [wx.ID_INDEX, wx.ID_ABOUT, wx.ID_PREVIEW, wx.ID_STATIC,
                   wx.ID_NEW]:
            self.Bind(wx.EVT_TOOL, self.on_searchall_toggle_toolbar, id=id)
        self.Bind(wx.EVT_TOOL, self.on_searchall_stop, id=wx.ID_STOP)

        if conf.SearchInChatInfo:
            self.label_search.Label = "&Search in chat info:"
        elif conf.SearchInContacts:
            self.label_search.Label = "&Search in contacts:"
        elif conf.SearchInTables:
            self.label_search.Label = "&Search in all tables:"

        html = self.html_searchall = controls.TabbedHtmlWindow(parent=page)
        ColourManager.Manage(html, "TabAreaColour", "WidgetColour")
        default = step.Template(templates.SEARCH_WELCOME_HTML).expand()
        html.SetDefaultPage(default)
        html.SetDeleteCallback(self.on_delete_tab_callback)
        label_html.Bind(wx.html.EVT_HTML_LINK_CLICKED,
                        self.on_click_html_link)
        html.Bind(wx.html.EVT_HTML_LINK_CLICKED,
                  self.on_click_html_link)
        html._html.Bind(wx.EVT_RIGHT_UP, self.on_rightclick_searchall)
        html.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_change_searchall_tab)
        html.Bind(controls.EVT_TAB_LEFT_DCLICK, self.on_dclick_searchall_tab)
        html.Font.PixelSize = (0, 8)

        ColourManager.Manage(label_html, "BackgroundColour", "WidgetColour")

        sizer_top.Add(label_html, proportion=1, flag=wx.GROW)
        sizer_top.Add(tb, border=5, flag=wx.TOP | wx.RIGHT |
                      wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(sizer_top, border=5, flag=wx.TOP | wx.RIGHT | wx.GROW)
        sizer.Add(html, border=5, proportion=1,
                  flag=wx.GROW | wx.LEFT | wx.RIGHT | wx.BOTTOM)
        wx.CallAfter(lambda: label_html and label_html.Show())


    def create_page_tables(self, notebook):
        """Creates a page for listing and browsing tables."""
        page = self.page_tables = wx.Panel(parent=notebook)
        self.pageorder[page] = len(self.pageorder)
        notebook.AddPage(page, "Data tables")
        sizer = page.Sizer = wx.BoxSizer(wx.HORIZONTAL)
        splitter = self.splitter_tables = wx.SplitterWindow(
            parent=page, style=wx.BORDER_NONE
        )
        splitter.SetMinimumPaneSize(100)

        panel1 = wx.Panel(parent=splitter)
        sizer1 = panel1.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_topleft = wx.BoxSizer(wx.HORIZONTAL)
        sizer_topleft.Add(wx.StaticText(parent=panel1, label="&Tables:"),
                          flag=wx.ALIGN_CENTER_VERTICAL)
        button_refresh = self.button_refresh_tables = \
            wx.Button(panel1, label="Refresh")
        sizer_topleft.AddStretchSpacer()
        sizer_topleft.Add(button_refresh)
        tree = self.tree_tables = wx.lib.gizmos.TreeListCtrl(panel1,
            agwStyle=wx.TR_DEFAULT_STYLE | wx.TR_FULL_ROW_HIGHLIGHT
        )
        ColourManager.Manage(tree, "BackgroundColour", wx.SYS_COLOUR_WINDOW)
        ColourManager.Manage(tree, "ForegroundColour", wx.SYS_COLOUR_BTNTEXT)
        tree.AddColumn("Table")
        tree.AddColumn("Info")
        tree.AddRoot("Loading data..")
        tree.SetMainColumn(0)
        tree.SetColumnAlignment(1, wx.ALIGN_RIGHT)
        self.Bind(wx.EVT_BUTTON, self.on_refresh_tables, button_refresh)
        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.on_change_tree_tables, tree)

        sizer1.Add(sizer_topleft, border=5, flag=wx.GROW | wx.LEFT | wx.TOP)
        sizer1.Add(tree, proportion=1,
                   border=5, flag=wx.GROW | wx.LEFT | wx.TOP | wx.BOTTOM)

        panel2 = wx.Panel(parent=splitter)
        sizer2 = panel2.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_tb = wx.BoxSizer(wx.HORIZONTAL)
        tb = self.tb_grid = wx.ToolBar(
            parent=panel2, style=wx.TB_FLAT | wx.TB_NODIVIDER)
        bmp_tb = images.ToolbarInsert.Bitmap
        tb.SetToolBitmapSize(bmp_tb.Size)
        tb.AddTool(wx.ID_ADD, "Insert new row.",
                   bitmap=bmp_tb, shortHelp="Add new row.")
        tb.AddTool(wx.ID_DELETE, "Delete current row.",
            bitmap=images.ToolbarDelete.Bitmap, shortHelp="Delete row.")
        tb.AddSeparator()
        tb.AddTool(wx.ID_SAVE, "Commit", bitmap=images.ToolbarCommit.Bitmap,
                   shortHelp="Commit changes to database.")
        tb.AddTool(wx.ID_UNDO, "Rollback", bitmap=images.ToolbarRollback.Bitmap,
                   shortHelp="Rollback changes and restore original values.")
        tb.EnableTool(wx.ID_ADD, False)
        tb.EnableTool(wx.ID_DELETE, False)
        tb.EnableTool(wx.ID_UNDO, False)
        tb.EnableTool(wx.ID_SAVE, False)
        self.Bind(wx.EVT_TOOL, handler=self.on_insert_row, id=wx.ID_ADD)
        self.Bind(wx.EVT_TOOL, handler=self.on_delete_row, id=wx.ID_DELETE)
        self.Bind(wx.EVT_TOOL, handler=self.on_commit_table, id=wx.ID_SAVE)
        self.Bind(wx.EVT_TOOL, handler=self.on_rollback_table, id=wx.ID_UNDO)
        tb.Realize() # should be called after adding tools
        label_table = self.label_table = wx.StaticText(parent=panel2, label="")
        button_reset = self.button_reset_grid_table = \
            wx.Button(parent=panel2, label="&Reset filter/sort")
        button_reset.SetToolTip("Resets all applied sorting "
                                      "and filtering.")
        button_reset.Bind(wx.EVT_BUTTON, self.on_button_reset_grid)
        button_reset.Enabled = False
        button_export = self.button_export_table = \
            wx.Button(parent=panel2, label="&Export to file")
        button_export.MinSize = (100, -1)
        button_export.SetToolTip("Export rows to a file.")
        button_export.Bind(wx.EVT_BUTTON, self.on_button_export_grid)
        button_export.Enabled = False
        sizer_tb.Add(label_table, flag=wx.ALIGN_CENTER_VERTICAL)
        sizer_tb.AddStretchSpacer()
        sizer_tb.Add(button_reset, border=5, flag=wx.BOTTOM | wx.RIGHT |
                     wx.ALIGN_CENTER_VERTICAL)
        sizer_tb.Add(button_export, border=5, flag=wx.BOTTOM | wx.RIGHT |
                     wx.ALIGN_CENTER_VERTICAL)
        sizer_tb.Add(tb)
        grid = self.grid_table = wx.grid.Grid(parent=panel2)
        ColourManager.Manage(grid, "DefaultCellBackgroundColour", wx.SYS_COLOUR_WINDOW)
        ColourManager.Manage(grid, "DefaultCellTextColour",       wx.SYS_COLOUR_WINDOWTEXT)
        ColourManager.Manage(grid, "LabelBackgroundColour",       wx.SYS_COLOUR_BTNFACE)
        ColourManager.Manage(grid, "LabelTextColour",             wx.SYS_COLOUR_WINDOWTEXT)
        grid.SetDefaultCellFitMode(wx.grid.GridFitMode.Clip())
        grid.Bind(wx.grid.EVT_GRID_LABEL_LEFT_DCLICK, self.on_sort_grid_column)
        grid.GridWindow.Bind(wx.EVT_MOTION, self.on_mouse_over_grid)
        grid.Bind(wx.grid.EVT_GRID_LABEL_RIGHT_CLICK,
                  self.on_filter_grid_column)
        grid.Bind(wx.grid.EVT_GRID_CELL_CHANGED, self.on_change_table)
        label_help = wx.StaticText(panel2, label="Double-click on column "
                                   "header to sort, right click to filter.")
        ColourManager.Manage(label_help, "ForegroundColour", "DisabledColour")
        sizer2.Add(sizer_tb, border=5, flag=wx.GROW | wx.LEFT | wx.TOP)
        sizer2.Add(grid, border=5, proportion=2,
                   flag=wx.GROW | wx.LEFT | wx.RIGHT)
        sizer2.Add(label_help, border=5, flag=wx.LEFT | wx.TOP)

        sizer.Add(splitter, proportion=1, flag=wx.GROW)
        splitter.SplitVertically(panel1, panel2, 270)


    def create_page_sql(self, notebook):
        """Creates a page for executing arbitrary SQL."""
        page = self.page_sql = wx.Panel(parent=notebook)
        self.pageorder[page] = len(self.pageorder)
        notebook.AddPage(page, "SQL window")
        sizer = page.Sizer = wx.BoxSizer(wx.VERTICAL)
        splitter = self.splitter_sql = \
            wx.SplitterWindow(parent=page, style=wx.BORDER_NONE)
        splitter.SetMinimumPaneSize(100)

        panel1 = self.panel_sql1 = wx.Panel(parent=splitter)
        sizer1 = panel1.Sizer = wx.BoxSizer(wx.VERTICAL)
        label_stc = wx.StaticText(parent=panel1, label="SQ&L:")
        stc = self.stc_sql = controls.SQLiteTextCtrl(parent=panel1,
            style=wx.BORDER_STATIC | wx.TE_PROCESS_TAB | wx.TE_PROCESS_ENTER)
        stc.Bind(wx.EVT_KEY_DOWN, self.on_keydown_sql)
        stc.SetText(conf.SQLWindowTexts.get(self.db.filename, ""))
        stc.EmptyUndoBuffer() # So that undo does not clear the STC
        sizer1.Add(label_stc, border=5, flag=wx.ALL)
        sizer1.Add(stc, border=5, proportion=1, flag=wx.GROW | wx.LEFT)

        panel2 = self.panel_sql2 = wx.Panel(parent=splitter)
        sizer2 = panel2.Sizer = wx.BoxSizer(wx.VERTICAL)
        label_help = wx.StaticText(panel2, label=
            "Alt-Enter runs the query contained in currently selected text or "
            "on the current line. Ctrl-Space shows autocompletion list.")
        ColourManager.Manage(label_help, "ForegroundColour", "DisabledColour")
        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        button_sql = self.button_sql = wx.Button(panel2, label="Execute S&QL")
        button_script = self.button_script = wx.Button(panel2, 
                                                       label="Execute scrip&t")
        button_sql.SetToolTip("Execute a single statement "
                                    "from the SQL window")
        button_script.SetToolTip("Execute multiple SQL statements, "
                                       "separated by semicolons")
        self.Bind(wx.EVT_BUTTON, self.on_button_sql, button_sql)
        self.Bind(wx.EVT_BUTTON, self.on_button_script, button_script)
        button_reset = self.button_reset_grid_sql = \
            wx.Button(parent=panel2, label="&Reset filter/sort")
        button_reset.SetToolTip("Resets all applied sorting "
                                      "and filtering.")
        button_reset.Bind(wx.EVT_BUTTON, self.on_button_reset_grid)
        button_reset.Enabled = False
        button_export = self.button_export_sql = \
            wx.Button(parent=panel2, label="&Export to file")
        button_export.SetToolTip("Export result to a file.")
        button_export.Bind(wx.EVT_BUTTON, self.on_button_export_grid)
        button_export.Enabled = False
        sizer_buttons.Add(button_sql, flag=wx.ALIGN_LEFT)
        sizer_buttons.Add(button_script, border=5, flag=wx.LEFT | wx.ALIGN_LEFT)
        sizer_buttons.AddStretchSpacer()
        sizer_buttons.Add(button_reset, border=5, flag=wx.RIGHT)
        sizer_buttons.Add(button_export)
        grid = self.grid_sql = wx.grid.Grid(parent=panel2)
        ColourManager.Manage(grid, "DefaultCellBackgroundColour", wx.SYS_COLOUR_WINDOW)
        ColourManager.Manage(grid, "DefaultCellTextColour",       wx.SYS_COLOUR_WINDOWTEXT)
        ColourManager.Manage(grid, "LabelBackgroundColour",       wx.SYS_COLOUR_BTNFACE)
        ColourManager.Manage(grid, "LabelTextColour",             wx.SYS_COLOUR_WINDOWTEXT)
        grid.SetDefaultCellFitMode(wx.grid.GridFitMode.Clip())
        grid.Bind(wx.grid.EVT_GRID_LABEL_LEFT_DCLICK,
                  self.on_sort_grid_column)
        grid.Bind(wx.grid.EVT_GRID_LABEL_RIGHT_CLICK,
                  self.on_filter_grid_column)
        grid.Bind(wx.EVT_SCROLLWIN, self.on_scroll_grid_sql)
        grid.Bind(wx.EVT_SCROLL_THUMBRELEASE, self.on_scroll_grid_sql)
        grid.Bind(wx.EVT_SCROLL_CHANGED, self.on_scroll_grid_sql)
        grid.Bind(wx.EVT_KEY_DOWN, self.on_scroll_grid_sql)
        grid.GridWindow.Bind(wx.EVT_MOTION, self.on_mouse_over_grid)
        label_help_grid = wx.StaticText(panel2, label="Double-click on column "
                                        "header to sort, right click to filter.")
        ColourManager.Manage(label_help_grid, "ForegroundColour", "DisabledColour")

        sizer2.Add(label_help, border=5, flag=wx.GROW | wx.LEFT | wx.BOTTOM)
        sizer2.Add(sizer_buttons, border=5, flag=wx.GROW | wx.ALL)
        sizer2.Add(grid, border=5, proportion=2,
                   flag=wx.GROW | wx.LEFT | wx.RIGHT)
        sizer2.Add(label_help_grid, border=5, flag=wx.GROW | wx.LEFT | wx.TOP)

        sizer.Add(splitter, proportion=1, flag=wx.GROW)
        sash_pos = self.Size[1] // 3
        splitter.SplitHorizontally(panel1, panel2, sashPosition=sash_pos)


    def create_page_info(self, notebook):
        """Creates a page for seeing general database information."""
        page = self.page_info = wx.lib.scrolledpanel.ScrolledPanel(notebook)
        self.pageorder[page] = len(self.pageorder)
        notebook.AddPage(page, "Information")
        sizer = page.Sizer = wx.BoxSizer(wx.HORIZONTAL)

        panel1 = self.panel_accountinfo = wx.Panel(parent=page)
        panel2 = wx.Panel(parent=page)
        ColourManager.Manage(panel1, "BackgroundColour", "BgColour")
        ColourManager.Manage(panel2, "BackgroundColour", "BgColour")
        sizer1 = panel1.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_account = wx.BoxSizer(wx.HORIZONTAL)
        label_account = wx.StaticText(parent=panel1,
                                      label="Main account information")
        label_account.Font = wx.Font(10, wx.FONTFAMILY_SWISS,
            wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, faceName=self.Font.FaceName)
        sizer1.Add(label_account, border=5, flag=wx.ALL)

        bmp_panel = wx.Panel(parent=panel1)
        bmp_panel.Sizer = wx.BoxSizer(wx.VERTICAL)
        bmp = images.AvatarDefaultLarge.Bitmap
        bmp_static = self.bmp_account = wx.StaticBitmap(bmp_panel, bitmap=bmp)
        sizer_accountinfo = wx.FlexGridSizer(cols=2, vgap=3, hgap=10)
        self.sizer_accountinfo = sizer_accountinfo
        sizer_accountinfo.AddGrowableCol(1, 1)

        bmp_panel.Sizer.Add(bmp_static, border=2, flag=wx.GROW | wx.TOP)
        sizer_account.Add(bmp_panel, border=10, flag=wx.LEFT | wx.RIGHT)
        sizer_account.Add(sizer_accountinfo, proportion=1, flag=wx.GROW)
        sizer1.Add(sizer_account, border=20, proportion=1,
                   flag=wx.TOP | wx.GROW)

        sizer2 = panel2.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_file = wx.FlexGridSizer(cols=2, vgap=3, hgap=10)
        label_file = wx.StaticText(parent=panel2, label="Database information")
        label_file.Font = wx.Font(10, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL,
                                  wx.FONTWEIGHT_BOLD, faceName=self.Font.FaceName)
        sizer2.Add(label_file, border=5, flag=wx.ALL)

        names = ["edit_info_chats", "edit_info_contacts",
                 "edit_info_transfers", "edit_info_messages",
                 "edit_info_lastmessage", "edit_info_firstmessage", "",
                 "edit_info_path", "edit_info_size", "edit_info_modified",
                 "edit_info_sha1", "edit_info_md5", ]
        labels = ["Conversations", "Contacts", "File transfers", "Messages",
                  "Last message", "First message", "", 
                  "Full path", "File size", "Last modified",
                  "SHA-1 checksum", "MD5 checksum",  ]
        for name, label in zip(names, labels):
            if not name and not label:
                sizer_file.AddSpacer(20), sizer_file.AddSpacer(20)
                continue # for name, label
            labeltext = wx.StaticText(parent=panel2, label="%s:" % label)
            ColourManager.Manage(labeltext, "ForegroundColour", "DisabledColour")
            valuetext = wx.TextCtrl(parent=panel2, value="Analyzing..",
                style=wx.NO_BORDER | wx.TE_MULTILINE | wx.TE_RICH)
            valuetext.MinSize = (-1, 35)
            ColourManager.Manage(valuetext, "BackgroundColour", "BgColour")
            valuetext.SetEditable(False)
            sizer_file.Add(labeltext, border=5, flag=wx.LEFT)
            sizer_file.Add(valuetext, proportion=1, flag=wx.GROW)
            setattr(self, name, valuetext)
        self.edit_info_path.Value = self.db.filename

        button_check = self.button_check_integrity = \
            wx.Button(parent=panel2, label="Check for corruption")
        button_refresh = self.button_refresh_fileinfo = \
            wx.Button(parent=panel2, label="Refresh")
        button_check.Enabled = button_refresh.Enabled = False
        button_check.SetToolTip("Check database integrity for corruption and recovery.")
        sizer_file.Add(button_check)
        sizer_file.Add(button_refresh, border=15,
                       flag=wx.ALIGN_RIGHT | wx.RIGHT)
        self.Bind(wx.EVT_BUTTON, self.on_check_integrity, button_check)
        self.Bind(wx.EVT_BUTTON, lambda e: self.update_info_page(),
                  button_refresh)

        sizer_file.AddGrowableCol(1, 1)
        sizer2.Add(sizer_file, border=20, proportion=1, flag=wx.TOP | wx.GROW)

        sizer.Add(panel1, proportion=1, border=5,
                  flag=wx.LEFT  | wx.TOP | wx.BOTTOM | wx.GROW)
        sizer.Add(panel2, proportion=1, border=5,
                  flag=wx.RIGHT | wx.TOP | wx.BOTTOM | wx.GROW)
        self.update_accountinfo()
        page.SetupScrolling()


    def create_page_live(self, notebook):
        """Creates a page for handling communication with Skype online login."""
        page = self.page_live = wx.Panel(notebook)
        self.pageorder[page] = len(self.pageorder)
        notebook.AddPage(page, "Online")

        splitter = self.splitter_live = wx.SplitterWindow(
            parent=page, style=wx.BORDER_NONE
        )
        splitter.SetMinimumPaneSize(300)
        panel1 = self.panel_login = wx.Panel(splitter)
        panel2 = self.panel_sync  = wx.Panel(splitter)
        splitter_sync = self.splitter_sync = wx.SplitterWindow(
            parent=panel2, style=wx.BORDER_NONE
        )
        splitter_sync.SetMinimumPaneSize(100)
        panel_sync1 = wx.Panel(splitter_sync)
        panel_sync2 = wx.Panel(splitter_sync)

        label_login  = wx.StaticText(panel1, label="Log in to Skype online account")
        label_user   = wx.StaticText(panel1, label="Username:")
        edit_user    = wx.TextCtrl(panel1)
        button_user  = wx.Button(panel1, label="Change")
        label_pw     = wx.StaticText(panel1, label="&Password:", name="label_live_pw")
        edit_pw      = wx.TextCtrl(panel1, style=wx.TE_PASSWORD | wx.TE_PROCESS_ENTER, name="live_pw")
        check_store  = wx.CheckBox(panel1, label="&Remember password")
        check_login  = wx.CheckBox(panel1, label="Log &in &automatically")
        check_sync   = wx.CheckBox(panel1, label="Synchronize history &automatically")
        edit_status  = wx.TextCtrl(panel1, size=(-1, 30), style=wx.TE_MULTILINE | wx.TE_NO_VSCROLL | wx.BORDER_NONE)
        button_login = controls.NoteButton(panel1, bmp=images.ButtonLogin.Bitmap)
        label_info   = wx.html.HtmlWindow(panel1)

        label_sync = wx.StaticText(parent=panel2, label="Update database from Skype online")
        list_chats = controls.SortableListView(parent=panel_sync1, style=wx.LC_REPORT)
        gauge = wx.Gauge(panel_sync2, size=(300, 15), style=wx.GA_HORIZONTAL | wx.PD_SMOOTH)
        label_progress   = wx.StaticText(panel_sync2)
        edit_sync_status = wx.TextCtrl(panel_sync2, size=(-1, 50), style=wx.TE_MULTILINE)
        check_contacts   = wx.CheckBox(panel_sync2, label="Update existing &contact information")
        check_older      = wx.CheckBox(panel_sync2, label="Check &older database chats for messages to sync")
        button_sync      = controls.NoteButton(panel_sync2, bmp=images.ButtonMergeLeftMulti.Bitmap)
        button_sync_sel  = controls.NoteButton(panel_sync2, bmp=images.ButtonMergeLeft.Bitmap)
        button_sync_stop = controls.NoteButton(panel_sync2, bmp=images.ButtonStop.Bitmap)

        ColourManager.Manage(panel1, "BackgroundColour", "BgColour")
        ColourManager.Manage(panel2, "BackgroundColour", "BgColour")
        label_user.Disable()
        edit_user.Disable()
        label_login.Font = wx.Font(10, wx.FONTFAMILY_SWISS,
            wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, faceName=self.Font.FaceName)
        check_store.ToolTip = "Store password for this database locally"
        check_login.ToolTip = "Log in to Skype online service automatically " \
                              "on opening this database next time"
        check_sync.ToolTip  = "Update database from Skype online service " \
                              "automatically on opening this database next time"
        check_login.Enabled = check_sync.Enabled = False
        ColourManager.Manage(edit_status, "ForegroundColour", "DisabledColour")
        ColourManager.Manage(edit_status, "BackgroundColour", "BgColour")
        edit_status.SetEditable(False)
        ColourManager.Manage(button_login, "BackgroundColour", "BgColour")
        button_login.Label = "&Log in as '%s'" % self.db.username
        button_login.Note = "After login, local database can be updated from " \
                            "Skype online service.\nAdditionally, HTML export " \
                            "can download and include shared media."
        label_info.SetFonts(normal_face=self.Font.FaceName, fixed_face=self.Font.FaceName, sizes=[8] * 7)
        label_info.SetPage(step.Template(templates.LOGIN_FAIL_INFO).expand())
        label_info.Hide()

        label_sync.Font = wx.Font(10, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL,
                                  wx.FONTWEIGHT_BOLD, faceName=self.Font.FaceName)
        columns = [("title", "Chat"), ("message_count", "Updates"),
                   ("first_message_datetime", "From"),
                   ("last_message_datetime", "Until") ]
        frmt = lambda r, c: r[c].strftime("%Y-%m-%d") if r.get(c) else ""
        formatters = {"first_message_datetime": frmt,
                      "last_message_datetime": frmt, }
        list_chats.SetColumns(columns)
        list_chats.SetColumnFormatters(formatters)
        list_chats.SetColumnsMaxWidth(300)
        ColourManager.Manage(edit_sync_status, "ForegroundColour", "DisabledColour")
        ColourManager.Manage(edit_sync_status, "BackgroundColour", "BgColour")
        edit_sync_status.SetEditable(False)
        check_contacts.ToolTip = "Update profile fields of existing contacts from online data"
        check_older.ToolTip = "Check all older chats in database for messages " \
                              "to sync from online, may take a long while"
        check_contacts.Value   = check_older.Value   = True
        check_contacts.Enabled = check_older.Enabled = False
        ColourManager.Manage(button_sync,      "BackgroundColour", "BgColour")
        ColourManager.Manage(button_sync_sel,  "BackgroundColour", "BgColour")
        ColourManager.Manage(button_sync_stop, "BackgroundColour", "BgColour")
        button_sync.Label = "S&ynchronize history in local database"
        button_sync.Note  = "Query Skype online services for new messages and save them in local database."
        button_sync_sel.Label = "Synchronize selec&ted chats"
        button_sync_sel.Note  = "Select specific chats to synchronize in local database."
        button_sync_stop.Label = "Stop synchronizing"
        button_sync_stop.Note = "Cease querying the online service."
        for c in controls.get_controls(panel2): c.Disable()
        if not live.skpy:
            edit_status.Value = "Login unavailable: SkPy module not installed"
            button_login.Disable()
            page.Disable()

        self.Bind(wx.EVT_BUTTON,     self.on_change_live_user,  button_user)
        self.Bind(wx.EVT_TEXT,       self.on_change_ctrl_login, edit_pw)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_live_login,        edit_pw)
        self.Bind(wx.EVT_CHECKBOX,   self.on_change_ctrl_login, check_store)
        self.Bind(wx.EVT_CHECKBOX,   self.on_change_ctrl_login, check_login)
        self.Bind(wx.EVT_CHECKBOX,   self.on_change_ctrl_login, check_sync)
        self.Bind(wx.EVT_CHECKBOX,   self.on_change_ctrl_login, check_contacts)
        self.Bind(wx.EVT_CHECKBOX,   self.on_change_ctrl_login, check_older)
        self.Bind(wx.EVT_BUTTON,     self.on_live_login,        button_login)
        self.Bind(wx.EVT_BUTTON,     self.on_live_sync,         button_sync)
        self.Bind(wx.EVT_BUTTON,     self.on_live_sync_sel,     button_sync_sel)
        self.Bind(wx.EVT_BUTTON,     self.on_live_sync_stop,    button_sync_stop)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_change_list_chats_sync, list_chats)
        label_info.Bind(wx.html.EVT_HTML_LINK_CLICKED,
                        lambda e: webbrowser.open(e.GetLinkInfo().Href))

        self.edit_user           = edit_user
        self.button_user         = button_user
        self.edit_pw             = edit_pw
        self.check_login_store   = check_store
        self.check_login_auto    = check_login
        self.check_login_sync    = check_sync
        self.edit_login_status   = edit_status
        self.button_login        = button_login
        self.label_login_fail    = label_info
        self.list_chats_sync     = list_chats
        self.gauge_sync          = gauge
        self.label_sync_progress = label_progress
        self.edit_sync_status    = edit_sync_status
        self.check_sync_contacts = check_contacts
        self.check_sync_older    = check_older
        self.button_sync         = button_sync
        self.button_sync_sel     = button_sync_sel
        self.button_sync_stop    = button_sync_stop

        sizer = page.Sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer1 = panel1.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer2 = panel2.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_login = wx.FlexGridSizer(cols=2, vgap=0, hgap=10)
        sizer_login.AddGrowableCol(1, 1)
        sizer_user  = wx.BoxSizer(wx.HORIZONTAL)
        sizer_sync1 = panel_sync1.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_sync2 = panel_sync2.Sizer = wx.BoxSizer(wx.VERTICAL)

        sizer_user.Add(edit_user,    flag=wx.GROW, proportion=1)
        sizer_user.Add(button_user,  border=10, flag=wx.LEFT)

        sizer_login.Add(label_user,  border=5, flag=wx.ALL)
        sizer_login.Add(sizer_user,  border=5, flag=wx.ALL | wx.GROW)
        sizer_login.Add(label_pw,    border=5, flag=wx.ALL)
        sizer_login.Add(edit_pw,     border=5, flag=wx.ALL | wx.GROW)
        sizer_login.AddSpacer(5)
        sizer_login.Add(check_store, border=5, flag=wx.ALL | wx.GROW)
        sizer_login.AddSpacer(5)
        sizer_login.Add(check_login, border=5, flag=wx.ALL | wx.GROW)
        sizer_login.AddSpacer(5)
        sizer_login.Add(check_sync,  border=5, flag=wx.ALL | wx.GROW)

        sizer1.Add(label_login,  border=5,  flag=wx.ALL)
        sizer1.Add(sizer_login,  border=20, flag=wx.TOP | wx.GROW)
        sizer1.Add(edit_status,  border=10, flag=wx.TOP | wx.LEFT | wx.RIGHT | wx.GROW)
        sizer1.Add(button_login, border=5,  flag=wx.ALL | wx.GROW)
        sizer1.Add(label_info,   border=15, flag=wx.ALL | wx.GROW, proportion=1)

        sizer2.Add(label_sync, border=5, flag=wx.ALL | wx.GROW)

        sizer_sync1.Add(list_chats, proportion=1, border=5, flag=wx.ALL | wx.GROW)
        sizer_sync2.Add(gauge, border=5, flag=wx.ALL | wx.ALIGN_CENTER_HORIZONTAL)
        sizer_sync2.Add(label_progress, border=5, flag=wx.ALL | wx.ALIGN_CENTER_HORIZONTAL)
        sizer_sync2.Add(edit_sync_status, proportion=1, border=5, flag=wx.ALL | wx.GROW)
        sizer_sync2.Add(check_contacts, border=5, flag=wx.ALL | wx.GROW)
        sizer_sync2.Add(check_older,    border=5, flag=wx.ALL | wx.GROW)
        sizer_sync2.Add(button_sync, border=5, flag=wx.ALL | wx.GROW)
        sizer_sync2.Add(button_sync_sel, border=5, flag=wx.ALL | wx.GROW)
        sizer_sync2.Add(button_sync_stop, border=5, flag=wx.ALL | wx.GROW)

        sizer2.Add(splitter_sync, proportion=1, flag=wx.GROW)

        sizer.Add(splitter, border=5, proportion=1, flag=wx.ALL | wx.GROW)
        splitter.SplitVertically(panel1, panel2)
        pos = self.Size[1] // 4
        splitter_sync.SplitHorizontally(panel_sync1, panel_sync2, sashPosition=pos)


    def on_sys_colour_change(self, event):
        """Handler for system colour change, refreshes content."""
        event.Skip()
        def dorefresh():
            if not self: return

            self.label_html.SetPage(step.Template(templates.SEARCH_HELP_SHORT).expand())
            self.label_html.BackgroundColour = ColourManager.GetColour(wx.SYS_COLOUR_BTNFACE)
            self.label_html.ForegroundColour = ColourManager.GetColour(wx.SYS_COLOUR_BTNTEXT)
            self.label_login_fail.SetPage(step.Template(templates.LOGIN_FAIL_INFO).expand())
            default = step.Template(templates.SEARCH_WELCOME_HTML).expand()
            self.html_searchall.SetDefaultPage(default)
            self.load_tables_data()
            self.list_timeline.RefreshItems()
            self.populate_chat_statistics()
            util.try_ignore(lambda: self.grid_table.Table.ClearAttrs())
            util.try_ignore(lambda: self.grid_sql.Table.ClearAttrs())

            for lst in (self.list_chats, self.list_contacts,
                        self.list_chats_sync, self.list_participants):
                for i in range(lst.GetItemCount()):
                    lst.SetItemTextColour(i,       lst.ForegroundColour)
                    lst.SetItemBackgroundColour(i, lst.BackgroundColour)
            self.load_contact(self.contact)

        wx.CallAfter(dorefresh) # Postpone to allow conf update


    def update_liveinfo(self):
        """Refreshes account settings in login-page from configuration."""
        if not self: return
        opts = conf.Login.get(self.db.filename) or {}
        self.edit_user.Value = self.db.username if self.db.username else ""
        self.button_login.Label = "&Log in as '%s'" % self.edit_user.Value
        try: self.edit_pw.ChangeValue(util.deobfuscate(opts.get("password", "")))
        except Exception as e: logger.error("Error decoding stored password: %s", util.format_exc(e))
        self.check_login_store.Value = opts.get("store", False)
        self.check_login_auto.Value  = opts.get("auto",  False) and self.check_login_store.Value
        self.check_login_sync.Value  = opts.get("sync",  False) and self.check_login_auto .Value
        self.check_login_auto.Enable(self.check_login_store.Value)
        self.check_login_sync.Enable(self.check_login_auto .Value)
        self.check_sync_contacts.Value = opts.get("sync_contacts", True)
        self.check_sync_older.Value    = opts.get("sync_older",    True)
        if self.db.live.is_logged_in() and self.button_login.Enabled:
            # Probable auto-login during HTML export
            self.edit_login_status.Value = 'Logged in to Skype as "%s"' % self.db.username
            self.button_login.Disable() 
            self.label_login_fail.Hide()
            for c in controls.get_controls(self.panel_sync): c.Enable()
            self.button_sync_stop.Disable()


    def on_change_live_user(self, event):
        """Handler for clicking to change live login name, opens input dialog."""
        msg = "Specify another login name for Skype online.\n\n" \
              "This should be the username that works for Microsoft Live login:"
        dlg = wx.TextEntryDialog(self, msg, conf.Title, value=self.db.username or "",
                                 style=wx.OK | wx.CANCEL)
        dlg.CenterOnParent()
        if wx.ID_OK != dlg.ShowModal(): return

        v = dlg.GetValue().strip()
        if not v: return

        if v == self.db.id and v != self.db.username: v = None
        self.db.update_row("accounts", {"liveid_membername": v}, self.db.account)
        self.db.account["liveid_membername"] = v
        self.db.username = v or self.db.id
        self.edit_user.Value = self.db.username
        self.button_login.Label = "&Log in as '%s'" % self.db.username
        self.update_accountinfo()


    def on_change_ctrl_login(self, event):
        """Handler for changing a login control like password or checkboxes, updates conf."""
        ctrl, value = event.EventObject, event.EventObject.Value
        if ctrl is self.edit_pw:
            name, value = "password", util.obfuscate(value)
        elif ctrl is self.check_login_store:   name = "store"
        elif ctrl is self.check_login_auto:    name = "auto"
        elif ctrl is self.check_login_sync:    name = "sync"
        elif ctrl is self.check_sync_contacts: name = "sync_contacts"
        elif ctrl is self.check_sync_older:    name = "sync_older"
        if not self.check_login_store.Value: self.check_login_auto.Value = False
        if not self.check_login_auto .Value: self.check_login_sync.Value = False
        self.check_login_auto.Enable(self.check_login_store.Value)
        self.check_login_sync.Enable(self.check_login_auto.Value)
        conf.Login.setdefault(self.db.filename, {})[name] = value
        if "store" == name and value and self.edit_pw.Value:
            pw = util.obfuscate(self.edit_pw.Value)
            conf.Login[self.db.filename]["password"] = pw
        if not self.check_login_store.Value:
            self.check_login_auto.Value = self.check_login_sync.Value = False
            conf.Login[self.db.filename].pop("store",    None)
            conf.Login[self.db.filename].pop("auto",     None)
            conf.Login[self.db.filename].pop("sync",     None)
            conf.Login[self.db.filename].pop("password", None)
        if not self.check_login_auto.Value:
            self.check_login_sync.Value = False
            conf.Login[self.db.filename].pop("auto",     None)
            conf.Login[self.db.filename].pop("sync",     None)
        if not self.check_login_sync.Value:
            conf.Login[self.db.filename].pop("sync",     None)
        if self.check_sync_contacts.Value:
            conf.Login[self.db.filename].pop("sync_contacts", None)
        if self.check_sync_older.Value:
            conf.Login[self.db.filename].pop("sync_older", None)
        if not conf.Login[self.db.filename]: conf.Login.pop(self.db.filename)
        util.run_once(conf.save)


    def on_menu_list_chats(self, event):
        """Handler for right-clicking  or context-menu-keying chatlist, opens popup menu."""
        chats, selecteds = [], []
        selected = self.list_chats.GetFirstSelected()
        while selected >= 0:
            selecteds.append(selected)
            chats.append(self.list_chats.GetItemMappedData(selected))
            selected = self.list_chats.GetNextSelected(selected)
        if isinstance(event, wx.ListEvent) and event.GetIndex() >= 0 \
        and event.GetIndex() not in selecteds:
            chats = [self.list_chats.GetItemMappedData(event.GetIndex())]
        if not chats: return

        name = ("Open %s " % chats[0]["title_long_lc"]) if len(chats) < 2 \
               else util.plural("chat", chats)

        menu = wx.Menu()
        item_name    = wx.MenuItem(menu, -1, name)
        item_copy    = wx.MenuItem(menu, -1, "&Copy %s" %
                                   util.plural("title", chats, numbers=False))
        item_copycon = wx.MenuItem(menu, -1, "Copy %s" %
                                   util.plural("con&tact name",
                                   chats[0]["participants"][1:] if len(chats) < 2 else chats,
                                   numbers=False))
        item_rename  = wx.MenuItem(menu, -1, "Re&name")
        item_export  = wx.MenuItem(menu, -1, "&Export to %s" %
                                   util.plural("file", chats, numbers=False))
        item_exportm = item_datesm = None
        if export.xlsxwriter and len(chats) > 1:
            item_exportm = wx.MenuItem(menu, -1, "Export to a single Excel &workbook, "
                                                 "with separate sheets")
            item_datesm  = wx.MenuItem(menu, -1, "Export date &range a single Excel workbook, "
                                                 "with separate sheets")
        item_dates   = wx.MenuItem(menu, -1, "Export &date range to file")
        item_delete  = wx.MenuItem(menu, -1, "Delete from database")

        boldfont = wx.Font(item_name.Font)
        boldfont.SetWeight(wx.FONTWEIGHT_BOLD)
        boldfont.SetFaceName(self.Font.FaceName)
        boldfont.SetPointSize(self.Font.PointSize)
        item_name.Font = boldfont
        if len(chats) > 1: item_name.Enabled = item_rename.Enabled = False

        menu.Append(item_name)
        menu.AppendSeparator()
        menu.Append(item_copy)
        menu.Append(item_copycon)
        menu.Append(item_rename)
        menu.AppendSeparator()
        menu.Append(item_export)
        if item_exportm: menu.Append(item_exportm)
        menu.Append(item_dates)
        if item_datesm: menu.Append(item_datesm)
        menu.AppendSeparator()
        menu.Append(item_delete)

        def clipboardize(category):
            if "title" == category:
                text = "\n".join(c["title"] for c in chats)
            else:
                namer = lambda p: p["identity"] if p["contact"].get("name") \
                                  and p["identity"] == p["contact"]["name"] \
                                  else "%s (%s)" % (p["contact"]["name"], p["identity"])
                if len(chats) < 2: # name1\nname2
                    text = "\n".join(namer(p) for p in chats[0]["participants"]
                                     if p["identity"] != self.db.id)
                else: text = "\n\n".join("%s:\n  %s" % (c["title_long"], "\n  ".join(
                    namer(p) for p in c["participants"] if p["identity"] != self.db.id
                )) for c in chats) # Group chat A:\n  name1\nname2\n\nGroup chat B..
            if wx.TheClipboard.Open():
                d = wx.TextDataObject(text)
                wx.TheClipboard.SetData(d), wx.TheClipboard.Close()

        def exporter(do_singlefile=False, do_timerange=False):
            self.on_export_chats(chats, False, do_singlefile, do_timerange)

        menu.Bind(wx.EVT_MENU, lambda e: self.load_chat(chats[0]), item_name)
        menu.Bind(wx.EVT_MENU, lambda e: clipboardize("title"),    item_copy)
        menu.Bind(wx.EVT_MENU, lambda e: clipboardize("contact"),  item_copycon)
        menu.Bind(wx.EVT_MENU, lambda e: self.on_rename_chat(chat=chats[0]), item_rename)
        menu.Bind(wx.EVT_MENU, lambda e: exporter(False, False), item_export)
        menu.Bind(wx.EVT_MENU, lambda e: exporter(False, True),  item_dates)
        if item_exportm:
            menu.Bind(wx.EVT_MENU, lambda e: exporter(True,  False), item_exportm)
        if item_datesm:
            menu.Bind(wx.EVT_MENU, lambda e: exporter(True,  True),  item_datesm)
        menu.Bind(wx.EVT_MENU, lambda e: self.delete_chats(chats), item_delete)

        # Needs callback, actions can modify list while mouse event ongoing
        wx.CallAfter(self.list_chats.PopupMenu, menu)


    def on_change_list_chats_sync(self, event):
        """
        Handler for selecting an item in the synced chats list, loads the
        messages in chats-page.
        """
        c = self.list_chats_sync.GetItemMappedData(event.Index)
        chat = next((x for x in self.chats if x["identity"] == c["identity"]), None)
        if chat:
            self.notebook.Selection = self.pageorder[self.page_chats]
            self.load_chat(chat)
            self.stc_history.SetFocus()


    def on_live_login(self, event=None, sync=False):
        """
        Attempts to login to Skype online service.

        @param   sync  whether sync should start automatically after login
        """
        if not self or not self.edit_pw.Value or not live.skpy: return
        self.edit_login_status.Value = "Logging in to Skype.."
        for c in self.panel_login.Children:
            if c is self.edit_pw or isinstance(c, wx.CheckBox): c.Disable()
        self.button_user.Disable() 
        self.button_login.Disable() 
        self.panel_login.Refresh()
        action = {"action": "login", "password": self.edit_pw.Value, "sync": sync}
        self.worker_live.work(action)


    def on_live_sync(self, event=None):
        """Starts synchronizing local database from Skype online service."""
        self.label_sync_progress.Label = "Updating local database from Skype online service.."
        self.list_chats_sync.DeleteAllItems()
        self.gauge_sync.Pulse()
        self.button_sync.Disable()
        self.button_sync_sel.Disable()
        self.button_sync_stop.Enable()
        self.gauge_sync.ContainingSizer.Layout()
        self.worker_live.work({"action": "populate"})


    def on_live_sync_sel(self, event=None):
        """
        Opens choice dialog for selecting chats and starts synchronizing
        local database from Skype online service.
        """
        FIELDS = ["identity", "title", "title_long", "type"]
        chats = sorted(self.chats, key=lambda x: (x["type"], x["title"].lower()))
        chats = [{k: x.get(k) for k in FIELDS} for x in chats]
        for x in chats:
            t = x["title"] if skypedata.CHATS_TYPE_SINGLE == x["type"] else x["title_long"]
            if len(t) > 60:
                t = "%s.." % t[:60]
                if skypedata.CHATS_TYPE_SINGLE != x["type"]: t += '"'
            if skypedata.CHATS_TYPE_SINGLE == x["type"] and x["identity"] != x["title"]:
                t += " (%s)" % x["identity"]
            x["title"] = t

        dlg = wx.MultiChoiceDialog(self, "Select chats to synchronize:",
                                   conf.Title, [x["title"] for x in chats])
        if wx.ID_OK != dlg.ShowModal() or not dlg.GetSelections(): return

        selchats = [chats[i] for i in dlg.GetSelections()]
        slabel = "Updating %s (%s) from Skype online service.." % (
                 util.plural("chat", selchats, sep=","), ", ".join(x["title"] for x in selchats))
        plabel = "Updating %s from Skype online service.." % util.plural("chat", selchats, sep=",")
        self.edit_sync_status.Value += ("\n\n" if self.edit_sync_status.Value else "") + slabel
        self.edit_sync_status.ShowPosition(self.edit_sync_status.LastPosition)
        self.label_sync_progress.Label = plabel
        self.list_chats_sync.DeleteAllItems()
        self.gauge_sync.Pulse()
        self.button_sync.Disable()
        self.button_sync_sel.Disable()
        self.button_sync_stop.Enable()
        self.gauge_sync.ContainingSizer.Layout()
        self.worker_live.work({"action": "populate", "chats": [x["identity"] for x in selchats]})


    def on_live_sync_stop(self, event=None):
        """Stops synchronizing local database from Skype online service."""
        if wx.OK != wx.MessageBox("Are you sure you want to stop synchronization?",
            conf.Title, wx.ICON_QUESTION | wx.OK | wx.CANCEL
        ) or not self.worker_live.is_working(): return
        self.gauge_sync.Value = self.gauge_sync.Value # Stop pulse, if any
        self.button_sync.Enable()
        self.button_sync_sel.Enable()
        self.button_sync_stop.Disable()
        self.gauge_sync.ContainingSizer.Layout()
        self.worker_live.stop_work()


    def on_live_result(self, result=None, **kwargs):
        """Callback for workers.LiveThread results."""

        def after(result):
            if not self or not result or "action" not in result: return

            if "populate" == result["action"]:
                plabel, slabel = None, None
                if "error" in result:
                    err = "Error syncing from Skype online service:\n\n%s" % result["error"]
                    logger.error(err)
                    plabel = "Error syncing from Skype online service."
                    slabel = err
                    self.gauge_sync.Value = self.gauge_sync.Value # Stop pulse, if any
                    self.button_sync.Enable()
                    self.button_sync_sel.Enable()
                    self.button_sync_stop.Disable()
                    wx.Bell()
                    self.update_info_page()
                elif result.get("done"):
                    self.gauge_sync.Value = self.gauge_sync.Value # Stop pulse, if any
                    if result.get("stop"):
                        plabel = slabel = "Stopped by user."
                    else:
                        plabel = slabel = "Synchronization complete."
                        self.gauge_sync.Value = 100
                    self.button_sync.Enable()
                    self.button_sync_sel.Enable()
                    self.button_sync_stop.Disable()
                    if not self.get_unsaved_grids(): self.on_refresh_tables()
                    wx.Bell()
                    self.update_info_page()
                else:
                    plabel = u"Synchronizing %s" % result["table"]
                    if "messages" == result["table"] and result.get("chat"):
                        chat = next((c for c in self.chats if c["identity"] == result["chat"]), None)
                        if not chat:
                            cc = self.db.get_conversations(chatidentities=[result["chat"]], reload=True, log=False)
                            self.chats.extend(cc)
                            if cc: chat = cc[0]

                        title = chat["title_long_lc"] if chat else result["chat"]
                        if len(title) > 35:
                            title = title[:35] + ".."
                            if chat and skypedata.CHATS_TYPE_GROUP == chat["type"]: title += '"'
                        plabel += " in %s" % title

                    if result.get("count"):
                        clabel = ", %s processed" % result["count"]
                        for k in "new", "updated":
                            if result.get(k): clabel += ", %s %s" % (result[k], k)
                        plabel += clabel + "."
                    elif result.get("start") and "messages" != result["table"] and self.worker_live.is_working():
                        plabel = slabel = "Synchronizing messages.."

                    if result.get("end"):
                        slabel = "Synchronized %s" % result["table"]
                        if "chats" == result["table"]:
                            slabel = "Synchronized %s%s: %s in total%s." % (
                                util.plural("chat", result["count"], sep=",") if result["count"] else "chats",
                                " (%s new)" % result["new"] if result["new"] else "",
                                util.plural("new message", result["message_count_new"], sep=","),
                                ", %s updated" % result["message_count_updated"] if result["message_count_updated"] else ""
                            )
                            if result["contact_count_new"] or result["contact_count_updated"]:
                                slabel += "\n%s." % ", ".join(filter(bool, [
                                    util.plural("new contact", result["contact_count_new"], sep=",")
                                    if result["contact_count_new"] else "",
                                    util.plural("contact", result["contact_count_updated"], sep=",") + " updated"
                                    if result["contact_count_updated"] else "",
                                ]))

                            self.chats = self.db.get_conversations(reload=True, log=False)
                            def after2():
                                if self: self.db.get_conversations_stats(self.chats)
                                if self: self.list_chats.Populate(self.chats)
                            wx.CallAfter(after2)

                        if "messages" == result["table"]:
                            slabel += " in %s" % (chat["title_long_lc"] if chat else result["chat"])

                            if chat and (result.get("new") or result.get("updated")):
                                row = dict(title=chat["title"], identity=chat["identity"],
                                           first_message_datetime=result["first"],
                                           last_message_datetime=result["last"],
                                           message_count=result["new"] + result["updated"])
                                self.list_chats_sync.AppendRow(row)
                                self.list_chats_sync.ResetColumnWidths()
                                chat["message_count" ] = (chat["message_count"] or 0) + result["new"]
                                chat["first_message_datetime"]  = min(chat["first_message_datetime"] or result["first"], result["first"])
                                chat["last_message_datetime"]   = max(chat["last_message_datetime"]  or result["first"], result["last"])
                                chat["last_activity_datetime"]  = max(chat["last_activity_datetime"] or result["last"],  result["last"])
                                for k in "first_message", "last_message", "last_activity":
                                    chat[k + "_timestamp"] = util.datetime_to_epoch(chat[k + "_datetime"])
                                self.list_chats.Populate(self.chats)

                            if not any(result[k] for k in ("new", "updated")):
                                slabel = None
                            else:
                                slabel += ": %s new" % result["new"]
                                if result["updated"]: slabel += ", %s updated" % result["updated"]
                                slabel += "."

                if plabel:
                    self.label_sync_progress.Label = plabel
                if slabel:
                    self.edit_sync_status.Value += ("\n\n" if self.edit_sync_status.Value else "") + slabel
                    self.edit_sync_status.ShowPosition(self.edit_sync_status.LastPosition)
                self.gauge_sync.ContainingSizer.Layout()
            elif "login"  == result["action"]:
                for c in self.panel_login.Children:
                    if c is self.edit_pw or isinstance(c, wx.CheckBox): c.Enable()
                if "error" in result:
                    logger.error('Error logging in to Skype as "%s":\n\n%s', self.db.username, result["error"])
                    self.edit_login_status.Value = result.get("error_short", result["error"])
                    self.button_user.Enable() 
                    self.button_login.Enable() 
                    self.label_login_fail.Show()
                    self.label_login_fail.ContainingSizer.Layout()
                else:
                    self.edit_login_status.Value = 'Logged in to Skype as "%s"' % self.db.username
                    self.button_login.Disable() 
                    self.label_login_fail.Hide()
                    for c in controls.get_controls(self.panel_sync): c.Enable()
                    self.button_sync_stop.Disable()
                    if result.get("opts", {}).get("sync"): wx.CallAfter(self.on_live_sync)
                self.check_login_auto.Enable(self.check_login_store.Value)
                self.check_login_sync.Enable(self.check_login_auto .Value)
            elif "info" == result["action"] and "message" in result:
                self.label_sync_progress.Label = result["message"] or ""
                if "index" in result and "count" in result:
                    percent = min(100, math.ceil(100 * util.safedivf(result["index"], result["count"])))
                    self.gauge_sync.Value = percent
                self.gauge_sync.ContainingSizer.Layout()

        if self: wx.CallAfter(after, result or kwargs)
        return bool(self and self.worker_live.is_working())


    def on_check_integrity(self, event):
        """
        Handler for checking database integrity, offers to save a fixed
        database if corruption detected.
        """
        msg = "Checking integrity of %s." % self.db.filename
        guibase.status(msg)
        busy = controls.BusyPanel(self, msg)
        wx.YieldIfNeeded()
        try:
            errors = self.db.check_integrity()
        except Exception as e:
            errors = e.args[:]
        busy.Close()
        guibase.status()
        if not errors:
            wx.MessageBox("No database errors detected.",
                          conf.Title, wx.ICON_INFORMATION)
        else:
            err = "\n- ".join(errors)
            logger.info("Errors found in %s: %s", self.db, err)
            err = err[:500] + ".." if len(err) > 500 else err
            msg = "A number of errors were found in %s:\n\n- %s\n\n" \
                  "Recover as much as possible to a new database?" % \
                  (self.db, err)
            if wx.YES == wx.MessageBox(msg, conf.Title,
                                       wx.ICON_INFORMATION | wx.YES | wx.NO):
                directory, filename = os.path.split(self.db.filename)
                base = os.path.splitext(filename)[0]
                self.dialog_savefile.Directory = directory
                self.dialog_savefile.Filename = "%s (recovered)" % base
                self.dialog_savefile.Message = "Save recovered data as"
                self.dialog_savefile.Wildcard = "SQLite database (*.db)|*.db|All files|*.*"
                if wx.ID_OK == self.dialog_savefile.ShowModal():
                    newfile = controls.get_dialog_path(self.dialog_savefile)
                    if newfile != self.db.filename:
                        guibase.status("Recovering data from %s to %s.",
                                       self.db.filename, newfile)
                        m = "Recovering data from %s\nto %s."
                        busy = controls.BusyPanel(self, m % (self.db, newfile))
                        wx.YieldIfNeeded()
                        try:
                            copyerrors = self.db.recover_data(newfile)
                        finally:
                            busy.Close()
                        err = ("\n\nErrors occurred during the recovery, "
                              "more details in log window:\n\n- "
                              + "\n- ".join(copyerrors)) if copyerrors else ""
                        err = err[:500] + ".." if len(err) > 500 else err
                        guibase.status("Recovery to %s complete." % newfile)
                        wx.MessageBox("Recovery to %s complete.%s" %
                                      (newfile, err), conf.Title,
                                      wx.ICON_INFORMATION)
                        util.start_file(os.path.dirname(newfile))
                    else:
                        wx.MessageBox("Cannot recover data from %s to itself."
                                      % self.db, conf.Title, wx.ICON_WARNING)


    def update_accountinfo(self):
        """Updates the account information page, clearing its former data."""
        sizer, panel = self.sizer_accountinfo, self.panel_accountinfo
        panel.Freeze()
        account = self.db.account or {}
        img = skypedata.get_avatar(account)
        img = img.ConvertToBitmap() if img else images.AvatarDefaultLarge.Bitmap
        self.bmp_account.SetBitmap(img)
        ctrls = []
        for x in sizer.Children: ctrls.append(x.Window), sizer.Remove(0)
        for x in ctrls: x.Destroy()

        for field in skypedata.ACCOUNT_FIELD_TITLES:
            value = skypedata.format_contact_field(account, field)
            if value is None: continue # for field

            title = skypedata.ACCOUNT_FIELD_TITLES.get(field, field)
            lbltext = wx.StaticText(parent=panel, label="%s:" % title)
            valtext = wx.TextCtrl(parent=panel, value=value,
                style=wx.NO_BORDER | wx.TE_MULTILINE | wx.TE_RICH)
            ColourManager.Manage(valtext, "BackgroundColour", "BgColour")
            valtext.MinSize = (-1, 35)
            valtext.SetEditable(False)
            ColourManager.Manage(lbltext, "ForegroundColour", "DisabledColour")
            sizer.Add(lbltext, border=5, flag=wx.LEFT)
            sizer.Add(valtext, proportion=1, flag=wx.GROW)
        panel.Layout()
        panel.Thaw()


    def save_page_conf(self):
        """Saves page last configuration like search text and results."""

        # Save search box state
        if conf.SearchHistory[-1:] == [""]: # Clear empty search flag
            conf.SearchHistory = conf.SearchHistory[:-1]
        util.add_unique(conf.SearchHistory, self.edit_searchall.Value,
                        1, conf.MaxSearchHistory)

        # Save last search results HTML
        search_data = self.html_searchall.GetActiveTabData()
        if search_data:
            info = {}
            if search_data.get("info"):
                info["map"] = search_data["info"].get("map")
                info["text"] = search_data["info"].get("text")
            data = {"content": search_data["content"],
                    "id": search_data["id"], "info": info,
                    "title": search_data["title"], }
            conf.LastSearchResults[self.db.filename] = data
        elif self.db.filename in conf.LastSearchResults:
            del conf.LastSearchResults[self.db.filename]

        # Save page SQL window content, if changed from previous value
        sql_text = self.stc_sql.Text
        if sql_text != conf.SQLWindowTexts.get(self.db.filename, ""):
            if sql_text:
                conf.SQLWindowTexts[self.db.filename] = sql_text
            elif self.db.filename in conf.SQLWindowTexts:
                del conf.SQLWindowTexts[self.db.filename]


    def update_info_page(self, reload=True):
        """Updates the Information page with current data."""
        if not self: return
        self.button_refresh_fileinfo.Enabled = False
        if reload:
            self.db.clear_cache()
            self.db.update_fileinfo()
            self.db.update_accountinfo()
            self.update_accountinfo()
        for name in ["chats", "contacts", "messages", "transfers",
        "lastmessage", "firstmessage", "size", "modified", "sha1", "md5"]:
            getattr(self, "edit_info_%s" % name).Value = ""
        stats = {}
        try:
            stats = self.db.get_general_statistics()
        except Exception: pass
        if stats:
            self.edit_info_chats.Value     = '{:,}'.format(stats["chats"])
            self.edit_info_contacts.Value  = '{:,}'.format(stats["contacts"])
            self.edit_info_messages.Value  = '{:,}'.format(stats["messages"])
            self.edit_info_transfers.Value = '{:,}'.format(stats["transfers"])
        if "messages_from" in stats:
            self.edit_info_messages.Value += " ({:,} sent and {:,} received)".format(
                stats.get("messages_from") or 0, stats.get("messages_to") or 0)
        text = ""
        if "lastmessage_dt" in stats:
            text = "%(lastmessage_dt)s %(lastmessage_from)s" % stats
            if stats.get("lastmessage_skypename") == self.db.id \
            or skypedata.CHATS_TYPE_SINGLE != stats.get("lastmessage_chattype"):
                text += " in %(lastmessage_chat)s" % stats
        self.edit_info_lastmessage.Value = text
        text = ""
        if "firstmessage_dt" in stats:
            text = "%(firstmessage_dt)s %(firstmessage_from)s" % stats
            if stats.get("firstmessage_chat") \
            and (stats.get("firstmessage_skypename") == self.db.id
            or skypedata.CHATS_TYPE_SINGLE != stats.get("firstmessage_chattype")):
                text += " in %(firstmessage_chat)s" % stats
        self.edit_info_firstmessage.Value = text

        self.edit_info_size.Value = "%s (%s)" % \
            (util.format_bytes(self.db.filesize),
             util.format_bytes(self.db.filesize, max_units=False))
        self.edit_info_modified.Value = \
            self.db.last_modified.strftime("%Y-%m-%d %H:%M:%S")
        BLOCKSIZE = 1048576
        sha1, md5 = hashlib.sha1(), hashlib.md5()
        try:
            with open(self.db.filename, "rb") as f:
                buf = f.read(BLOCKSIZE)
                while len(buf):
                    sha1.update(buf), md5.update(buf)
                    buf = f.read(BLOCKSIZE)
            self.edit_info_sha1.Value = sha1.hexdigest()
            self.edit_info_md5.Value = md5.hexdigest()
        except Exception as e:
            self.edit_info_sha1.Value = self.edit_info_md5.Value = util.format_exc(e)
        self.button_check_integrity.Enabled = True
        self.button_refresh_fileinfo.Enabled = True


    def on_refresh_tables(self, event=None):
        """
        Refreshes the table tree and open table data. Asks for confirmation
        if there are uncommitted changes.
        """
        do_refresh, unsaved = True, self.get_unsaved_grids()
        if unsaved:
            response = wx.MessageBox("Some tables have unsaved data (%s).\n\n"
                "Save before refreshing (changes will be lost otherwise)?"
                % (", ".join(sorted(x.table for x in unsaved))), conf.Title,
                wx.YES | wx.NO | wx.CANCEL | wx.ICON_INFORMATION)
            if wx.YES == response:
                do_refresh = self.save_unsaved_grids()
            elif wx.CANCEL == response:
                do_refresh = False
        if not do_refresh: return

        self.db.clear_cache()
        self.load_tables_data(reload=True)
        if self.grid_table.Table:
            grid, table_name = self.grid_table, self.grid_table.Table.table
            scrollpos = map(grid.GetScrollPos, [wx.HORIZONTAL, wx.VERTICAL])
            cursorpos = grid.GridCursorCol, grid.GridCursorRow
            self.on_change_table(None)
            grid.Table = None # Reset grid data to empty
            grid.Freeze()
            self.db_grids.clear()

            tableitem = None
            table_name = table_name.lower()
            table = next((t for t in self.db.get_tables()
                          if t["name"].lower() == table_name), None)
            item = self.tree_tables.GetNext(self.tree_tables.GetRootItem())
            while table and item and item.IsOk():
                table2 = self.tree_tables.GetItemPyData(item)
                if table2 and table2.lower() == table["name"].lower():
                    tableitem = item
                    break # break while table and item and itek.IsOk()
                item = self.tree_tables.GetNextSibling(item)
            if tableitem:
                # Only way to create state change in wx.lib.gizmos.TreeListCtrl
                class HackEvent(object):
                    def __init__(self, item): self._item = item
                    def GetItem(self):        return self._item
                self.on_change_tree_tables(HackEvent(tableitem))
                self.tree_tables.SelectItem(tableitem)
                grid.Scroll(*scrollpos)
                grid.SetGridCursor(*cursorpos)
            else:
                self.label_table.Label = ""
                for x in [wx.ID_ADD, wx.ID_DELETE, wx.ID_UNDO, wx.ID_SAVE]:
                    self.tb_grid.EnableTool(x, False)
                self.button_reset_grid_table.Enabled = False
                self.button_export_table.Enabled = False
            grid.Thaw()
            self.page_tables.Refresh()


    def on_change_range_date(self, event):
        """
        Handler for value change in chat filter date range, updates date 
        editboxes.
        """
        try:
            v1, v2 = [d.strftime("%Y-%m-%d") for d in self.range_date.Values]
        except Exception:
            v1, v2 = "", ""
        for e, v in [(self.edit_filterdate1, v1), (self.edit_filterdate2, v2)]:
            if v and e.Enabled and e.Value != v:
                sel = e.GetSelection()
                e.Value = v
                e.SetSelection(*sel)


    def on_change_filterdate(self, event):
        """
        Handler for changing a chat date filter editbox, updates date range
        slider.
        """
        datestr = re.sub("\\D", "", event.String)[:8]
        try:
            assert len(datestr) == 8
            date = datetime.datetime.strptime(datestr, "%Y%m%d").date()
        except (AssertionError, TypeError, ValueError):
            date = None
        if date:
            side = (event.EventObject == self.edit_filterdate2)
            if self.range_date.GetValue(side) != date:
                self.range_date.SetValue(side, date)
                date2 = self.range_date.GetValue(side)
                if datestr != date2.strftime("%Y%m%d"):
                    sel = event.EventObject.Selection
                    event.EventObject.Value = date2.strftime("%Y-%m-%d")
                    event.EventObject.SetSelection(*sel)


    def on_change_chatfilter(self, event):
        """Handler for changing text in chat filter box, filters chat list."""
        clist = self.list_chats
        clist.SetFilter(event.String.strip())
        for i in range(clist.ItemCount) if self.chat else ():
            if clist.GetItemMappedData(i) == self.chat:
                f = clist.Font; f.SetWeight(wx.FONTWEIGHT_BOLD)
                clist.SetItemFont(i, f)
                break # for i


    def on_change_contactfilter(self, event):
        """Handler for changing text in chat filter box, filters chat list."""
        clist = self.list_contacts
        clist.SetFilter(event.String.strip())
        for i in range(clist.ItemCount) if self.chat else ():
            if clist.GetItemMappedData(i) == self.contact:
                f = clist.Font; f.SetWeight(wx.FONTWEIGHT_BOLD)
                clist.SetItemFont(i, f)
                break # for i


    def on_rename_item(self, event):
        """
        Handler for clicking to rename the chat or a participant, opens a submenu.
        """
        chat_cols = self.db.get_table_columns("conversations")
        contact_cols = self.db.get_table_columns("contacts")

        menu  = wx.Menu()
        pmenu = wx.Menu()

        for p in self.chat["participants"]:
            item = wx.MenuItem(menu, -1, "%(name)s (%(identity)s)" % p["contact"])
            pmenu.Append(item)
            pmenu.Bind(wx.EVT_MENU, functools.partial(self.on_rename_contact, p["contact"]),
                       id=item.GetId())

        item_chat = wx.MenuItem(menu, -1, "Rename &chat")
        menu.Bind(wx.EVT_MENU, self.on_rename_chat, id=item_chat.GetId())

        menu.Append(item_chat)
        item_participants = menu.AppendSubMenu(pmenu, "Rename &participant")

        item_participants.Enable(any(x["name"] == "given_displayname" for x in contact_cols))
        item_chat.Enable(any(x["name"] == "given_displayname" for x in chat_cols))

        self.button_rename.PopupMenu(menu, (0, self.button_rename.Size[1]))


    def on_rename_chat(self, event=None, chat=None):
        """
        Handler for clicking to rename a chat, opens a text entry dialog
        and saves entered value as Conversations.given_displayname.
        """
        chat = chat or self.chat
        dlg = wx.TextEntryDialog(self, "Give new display name for the conversation",
                                 conf.Title, value=chat["title"],
                                 style=wx.OK | wx.CANCEL)
        dlg.CenterOnParent()
        if wx.ID_OK != dlg.ShowModal(): return

        v = dlg.GetValue().strip()
        if v == chat["title"] \
        or not v and not chat.get("given_displayname"): return

        PREFS = ["displayname", "meta_topic", "identity"]
        key0, name0 = next((k, chat[k]) for k in PREFS if chat.get(k))
        if not v:
            if wx.OK != wx.MessageBox(
                'Remove given display name, falling back to %s "%s"?' % 
                (key0, name0), conf.Title, wx.OK | wx.CANCEL
            ): return
            v = None

        self.db.update_row("conversations", {"given_displayname": v}, chat)
        chat["given_displayname"] = v
        chat["title"] = v or name0

        ltitle = ("Chat with %s" if skypedata.CHATS_TYPE_SINGLE == chat["type"]
                  else 'Group chat "%s"') % (v or name0)
        chat["title_long"] = ltitle
        chat["title_long_lc"] = ltitle[0].lower() + ltitle[1:]

        scrollpos = self.list_chats.GetScrollPos(wx.VERTICAL)
        self.list_chats.RefreshRows()
        self.list_chats.ScrollLines(scrollpos)
        if chat is not self.chat: return

        # Add shortcut key flag to chat label
        self.label_chat.Label = self.chat["title_long"].replace(
            "chat", "&chat"
        ).replace("Chat", "&Chat") + ":"
        self.label_chat.Parent.Layout()
        self.populate_chat_statistics()
        if self.html_stats.Shown:
            self.show_stats(True) # To restore scroll position
        self.load_contact(self.contact)


    def on_rename_contact(self, contact, event):
        """
        Handler for clicking to rename a contact, opens a text entry dialog
        and saves entered value as Contacts.given_displayname.
        """
        label = "database account" if contact["identity"] == self.db.id else "contact"
        dlg = wx.TextEntryDialog(self, 'Give new display name for %s "%s":' %
                                 (label, contact["identity"]),
                                 conf.Title, value=contact["name"],
                                 style=wx.OK | wx.CANCEL)
        dlg.CenterOnParent()
        if wx.ID_OK != dlg.ShowModal(): return

        v = dlg.GetValue().strip()
        if v == contact["name"] \
        or not v and not contact.get("given_displayname") \
        or not v and contact["identity"] == self.db.id \
        and not self.db.account.get("given_displayname"): return

        PREFS = ["fullname", "displayname", "skypename", "pstnnumber"]
        key0, name0 = next((k, contact[k]) for k in PREFS if contact.get(k))
        if not v:
            if wx.OK != wx.MessageBox(
                'Remove given display name from "%s", falling back to %s "%s"?' % 
                (contact["identity"], key0, name0),
                conf.Title, wx.OK | wx.CANCEL
            ): return
            v = None

        if contact["identity"] != self.db.id:
            self.db.update_row("contacts", {"given_displayname": v}, contact)
        contact["given_displayname"] = v
        contact["name"] = v or name0

        if contact["identity"] == self.db.id:
            self.db.update_row("accounts", {"given_displayname": v}, self.db.account)
            self.db.account["given_displayname"] = v
            self.db.account["name"] = v or name0
            self.update_accountinfo()

        idx = next((i for i in range(self.list_participants.GetItemCount())
                    if self.list_participants.GetItemData(i)["contact"] is contact), None)
        if idx is not None:
            self.list_participants.SetItemText(idx, "%(name)s (%(identity)s)" % contact)
            self.stc_history.RefreshMessages()
            self.populate_chat_statistics()
            if self.html_stats.Shown:
                self.show_stats(True) # To restore scroll position
        self.list_contacts.RefreshRows()
        self.load_contact(self.contact)


    def on_export_chat(self, event):
        """
        Handler for clicking to export a chat, displays a save file dialog and
        saves the current messages to file.
        """
        formatargs = collections.defaultdict(str); formatargs.update(self.chat)
        default = util.safe_filename(conf.ExportChatTemplate % formatargs)
        self.dialog_savefile.Filename = default
        self.dialog_savefile.Message = "Save chat"
        self.dialog_savefile.Wildcard = export.CHAT_WILDCARD
        if wx.ID_OK != self.dialog_savefile.ShowModal(): return

        filepath = controls.get_dialog_path(self.dialog_savefile)
        format = export.CHAT_EXTS[self.dialog_savefile.FilterIndex]
        media_folder = "html" == format and self.dialog_savefile.FilterIndex
        if media_folder and not check_media_export_login(self.db): return

        busy = controls.BusyPanel(self, 'Exporting "%s".' % self.chat["title"])
        guibase.status("Exporting to %s.", filepath)
        try:
            messages = self.stc_history.GetMessages()
            progressfunc = lambda *args: wx.SafeYield()
            opts = dict(progress=progressfunc, noskip=True, messages=messages)
            if media_folder: opts["media_folder"] = True
            result = export.export_chats([self.chat], filepath, format, self.db, opts)
            files, count, message_count = result
            guibase.status("Exported %s to %s.",
                           util.plural("message", message_count, sep=","), filepath, log=True)
            try: util.start_file(filepath)
            except Exception:
                logger.exception("Error starting %s.", filepath)
            wx.CallAfter(self.update_liveinfo)
        except Exception:
            logger.exception("Error saving %s.", filepath)
            guibase.status("Error saving %s.", filepath)
            errormsg = "Error saving %s:\n\n%s" % \
                       (filepath, traceback.format_exc())
            wx.MessageBox(errormsg, conf.Title, wx.OK | wx.ICON_WARNING)
            wx.CallAfter(util.try_ignore, os.unlink, filepath)
        finally:
            busy.Close()


    def on_export_chats_menu(self, event):
        """
        Handler for clicking to export selected or all chats, displays a 
        submenu with choices to export selected chats or all chats.
        """
        selected, selecteds = self.list_chats.GetFirstSelected(), []
        while selected >= 0:
            selecteds.append(selected)
            selected = self.list_chats.GetNextSelected(selected)

        def handler(do_all=False, do_singlefile=False, do_timerange=False):
            chats = [self.list_chats.GetItemMappedData(i)
                     for i in (range(self.list_chats.ItemCount) if do_all else selecteds)]
            return functools.partial(self.on_export_chats,
                                     chats, do_all, do_singlefile, do_timerange)

        menu = wx.lib.agw.flatmenu.FlatMenu()
        menu_sel  = wx.lib.agw.flatmenu.FlatMenu()
        menu_all  = wx.lib.agw.flatmenu.FlatMenu()
        menu_date = wx.lib.agw.flatmenu.FlatMenu()

        item_sel = wx.lib.agw.flatmenu.FlatMenuItem(
            menu, wx.ID_ANY, "Export &selected chats", subMenu=menu_sel)
        item_all = wx.lib.agw.flatmenu.FlatMenuItem(
            menu, wx.ID_ANY, "Export &all chats", subMenu=menu_all)
        item_date = wx.lib.agw.flatmenu.FlatMenuItem(
            menu, wx.ID_ANY, "Export &date range", subMenu=menu_date)
        item_sel.Enable(len(selecteds))
        item_all.Enable(bool(self.list_chats.GetItemCount()))
        item_date.Enable(bool(self.list_chats.GetItemCount()))

        item_sel_multi = wx.lib.agw.flatmenu.FlatMenuItem(
            menu_sel, wx.ID_ANY, "Into individual &files")
        menu_sel.AppendItem(item_sel_multi)
        self.Bind(wx.EVT_MENU, handler(), item_sel_multi)
        if export.xlsxwriter:
            item_sel_single = wx.lib.agw.flatmenu.FlatMenuItem(
                menu_sel, wx.ID_ANY, "Into a single &Excel workbook, "
                "with separate sheets")
            menu_sel.AppendItem(item_sel_single)
            self.Bind(wx.EVT_MENU, handler(do_singlefile=True), item_sel_single)

        item_all_multi = wx.lib.agw.flatmenu.FlatMenuItem(
            menu_all, wx.ID_ANY, "Into individual &files")
        menu_all.AppendItem(item_all_multi)
        self.Bind(wx.EVT_MENU, handler(do_all=True), item_all_multi)
        if export.xlsxwriter:
            item_all_single = wx.lib.agw.flatmenu.FlatMenuItem(
                menu_all, wx.ID_ANY, "Into a single &Excel workbook, "
                "with separate sheets")
            menu_all.AppendItem(item_all_single)
            myhandler = handler(do_all=True, do_singlefile=True)
            self.Bind(wx.EVT_MENU, myhandler, item_all_single)

        item_sel_date_multi = wx.lib.agw.flatmenu.FlatMenuItem(
            menu_date, wx.ID_ANY, "Selected chats into individual &files")
        menu_date.AppendItem(item_sel_date_multi)
        item_sel_date_multi.Enable(len(selecteds))
        self.Bind(wx.EVT_MENU, handler(do_timerange=True), item_sel_date_multi)
        if export.xlsxwriter:
            item_sel_date_single = wx.lib.agw.flatmenu.FlatMenuItem(
                menu_sel, wx.ID_ANY, "Selected chats into a single &Excel workbook, "
                "with separate sheets")
            menu_date.AppendItem(item_sel_date_single)
            item_sel_date_single.Enable(len(selecteds))
            myhandler = handler(do_singlefile=True, do_timerange=True)
            self.Bind(wx.EVT_MENU, myhandler, item_sel_date_single)
        menu_date.AppendSeparator()
        item_all_date_multi = wx.lib.agw.flatmenu.FlatMenuItem(
            menu_date, wx.ID_ANY, "All chats into &individual files")
        menu_date.AppendItem(item_all_date_multi)
        self.Bind(wx.EVT_MENU, handler(do_all=True, do_timerange=True), item_all_date_multi)
        if export.xlsxwriter:
            item_all_date_single = wx.lib.agw.flatmenu.FlatMenuItem(
                menu_all, wx.ID_ANY, "&All chats into a single Excel workbook, "
                "with separate sheets")
            menu_date.AppendItem(item_all_date_single)
            myhandler = handler(do_all=True, do_singlefile=True, do_timerange=True)
            self.Bind(wx.EVT_MENU, myhandler, item_all_date_single)

        menu.AppendItem(item_sel)
        menu.AppendItem(item_all)
        menu.AppendItem(item_date)

        sz_btn, pt_btn = event.EventObject.Size, event.EventObject.Position
        pt_btn = event.EventObject.Parent.ClientToScreen(pt_btn)
        menu.SetOwnerHeight(sz_btn.y)
        if menu.Size.width < sz_btn.width:
            menu.Size = sz_btn.width, menu.Size.height
        menu.Popup(pt_btn, self)


    def on_export_contact_chats_menu(self, event):
        """
        Handler for clicking to export contact chats, displays a submenu with choices.
        """
        def handler(do_singlefile=False):
            chatmap = {x["id"]: x for x in self.chats}
            chats = [chatmap[x["id"]] for x in self.contact.get("conversations") or []]
            if do_singlefile:
                do_singlefile = "Chats with %s" % (self.contact["name"] or self.contact["identity"])
            return functools.partial(self.on_export_chats,
                                     chats, False, do_singlefile, False)

        menu = wx.lib.agw.flatmenu.FlatMenu()

        item_multi = wx.lib.agw.flatmenu.FlatMenuItem(
            menu, wx.ID_ANY, "Into individual &files")
        menu.AppendItem(item_multi)
        self.Bind(wx.EVT_MENU, handler(), item_multi)
        if export.xlsxwriter:
            item_single = wx.lib.agw.flatmenu.FlatMenuItem(
                menu, wx.ID_ANY, "Into a single &Excel workbook, with separate sheets")
            menu.AppendItem(item_single)
            self.Bind(wx.EVT_MENU, handler(do_singlefile=True), item_single)

        sz_btn, pt_btn = event.EventObject.Size, event.EventObject.Position
        pt_btn = event.EventObject.Parent.ClientToScreen(pt_btn)
        menu.SetOwnerHeight(sz_btn.y)
        if menu.Size.width < sz_btn.width:
            menu.Size = sz_btn.width, menu.Size.height
        menu.Popup(pt_btn, self)


    def on_export_contacts(self, event):
        """
        Handler for clicking to export contacts, display file dialog and saves spreadsheet.
        """
        if not self.contacts: return

        dialog = wx.FileDialog(parent=self, message="Save contacts",
            defaultFile="Skype contact list",
            style=wx.FD_OVERWRITE_PROMPT | wx.FD_SAVE | wx.RESIZE_BORDER
        )
        dialog.Wildcard = export.CONTACT_WILDCARD
        if wx.ID_OK != dialog.ShowModal(): return

        filepath = controls.get_dialog_path(dialog)
        format = export.CONTACT_EXTS[dialog.FilterIndex]
        guibase.status("Exporting %s.", filepath, log=True)
        export.export_contacts(self.contacts, filepath, format, self.db)
        util.start_file(filepath)


    def on_export_chats(self, chats, do_all=False, do_singlefile=False, do_timerange=False, event=None):
        """
        Handler for clicking to export selected or all chats, displays a select
        folder dialog and exports chats to individual files under the folder.

        @param   chats          list of conversations to export
        @param   do_all         whether to export all chats, even those with no messages
        @param   do_singlefile  whether to export a single-file XLSX,
                                optionally containing the file name
        @param   do_timerange   whether to pop up dialogs to select export date range
        """
        if not chats: return

        timerange = None
        if do_timerange:
            timerange = []
            for label in ("start", "end"):
                extra = "end at last" if "end" == label else "start from first"
                dialog = wx.TextEntryDialog(self,
                    "Enter %s date as YYYY-MM-DD, or leave blank to %s:" % (label, extra),
                    "Date range", style=wx.OK | wx.CANCEL)
                dialog.CenterOnParent()
                if wx.ID_OK != dialog.ShowModal(): return

                v, dt = dialog.GetValue().strip(), None
                try:
                    if v: dt = datetime.datetime.strptime(v, "%Y-%m-%d").date()
                except Exception:
                    return wx.MessageBox("Invalid date value: '%s'." % v,
                                         conf.Title, wx.OK | wx.ICON_WARNING)
                timerange.append(util.datetime_to_epoch(dt))

        dialog = self.dialog_savefile if do_singlefile or len(chats) == 1 \
                 else self.dialog_savefile_ow

        dialog.Message = "Choose folder where to save chat files"
        dialog.Filename = "Filename will be ignored"
        dialog.Wildcard = export.CHAT_WILDCARD
        if do_singlefile:
            if isinstance(do_singlefile, six.string_types):
                default = do_singlefile
            else:
                formatargs = collections.defaultdict(str)
                formatargs["skypename"] = os.path.basename(self.db.filename)
                formatargs.update(self.db.account or {})
                default = conf.ExportDbTemplate % formatargs
            dialog.Filename = util.safe_filename(default)
            dialog.Message = "Save chats file"
            dialog.Wildcard = export.CHAT_WILDCARD_SINGLEFILE
        elif len(chats) == 1:
            formatargs = collections.defaultdict(str); formatargs.update(chats[0])
            default = util.safe_filename(conf.ExportChatTemplate % formatargs)
            dialog.Filename = default
            dialog.Message = "Save chat"
        if wx.ID_OK != dialog.ShowModal(): return

        path, media_folder = controls.get_dialog_path(dialog), False
        if do_singlefile:
            format = export.CHAT_EXTS_SINGLEFILE[dialog.FilterIndex]
        else:
            if len(chats) > 1: path = os.path.dirname(path)
            format = export.CHAT_EXTS[dialog.FilterIndex]
            media_folder = "html" == format and dialog.FilterIndex

        if media_folder and not check_media_export_login(self.db): return

        msg = 'Exporting to %s.' % path if len(chats) == 1 and not do_singlefile \
        else  'Exporting %schats from "%s"\nas %s under %s.' % \
              ("all " if do_all else "", self.db.filename, format.upper(), path)
        busy = controls.BusyPanel(self, msg)
        guibase.status(msg, log=True)
        files, count, message_count, errormsg, errormsg_short = [], 0, 0, None, None
        try:
            progressfunc = lambda *args: wx.SafeYield()
            opts = dict(multi=not do_singlefile and len(chats) > 1, noskip=not do_all,
                        progress=progressfunc, timerange=timerange)
            if media_folder: opts["media_folder"] = True
            result = export.export_chats(chats, path, format, self.db, opts)
            files, count, message_count = result
        except Exception as e:
            errormsg_short = "Error exporting chats: %s" % util.format_exc(e)
            errormsg = "Error exporting chats:\n\n%s" % \
                       traceback.format_exc()
        busy.Close()
        wx.CallAfter(self.update_liveinfo)
        if not errormsg:
            if len(chats) == 1 and not do_singlefile:
                guibase.status("Exported %s to %s.",
                               util.plural("message", message_count, sep=","),
                               path, log=True)
            else: guibase.status("Exported %s and %s from %s as %s under %s.",
                                 util.plural("chat", count, sep=","), 
                                 util.plural("message", message_count, sep=","), self.db,
                                 format.upper(), path, log=True)
            util.start_file(files[0] if do_singlefile or len(chats) == 1 else path)
        else:
            guibase.status(errormsg_short or errormsg)
            wx.MessageBox(errormsg, conf.Title, wx.OK | wx.ICON_WARNING)


    def on_filterexport_chat(self, event):
        """
        Handler for clicking to export a chat filtering straight to file,
        displays a save file dialog and saves all filtered messages to file.
        """
        formatargs = collections.defaultdict(str); formatargs.update(self.chat)
        default = conf.ExportChatTemplate % formatargs
        self.dialog_savefile.Filename = util.safe_filename(default)
        self.dialog_savefile.Message = "Save chat"
        self.dialog_savefile.Wildcard = export.CHAT_WILDCARD
        if wx.ID_OK != self.dialog_savefile.ShowModal(): return

        filepath = controls.get_dialog_path(self.dialog_savefile)
        format = export.CHAT_EXTS[self.dialog_savefile.FilterIndex]
        media_folder = "html" == format and self.dialog_savefile.FilterIndex
        if media_folder and not check_media_export_login(self.db): return

        busy = controls.BusyPanel(self, 'Filtering and exporting "%s".' % 
                                  self.chat["title"])
        try:
            filter_new = self.build_filter()
            filter_backup = self.stc_history.GetFilter()
            self.stc_history.SetFilter(filter_new)
            self.stc_history.RetrieveMessagesIfNeeded()
            messages_all = self.stc_history.GetRetrievedMessages()
            messages = [m for m in messages_all
                        if not self.stc_history.IsMessageFilteredOut(m)]
            self.stc_history.SetFilter(filter_backup)
            if messages:
                guibase.status("Filtering and exporting to %s.", filepath, log=True)
                progressfunc = lambda *args: wx.SafeYield()
                opts = dict(messages=messages, progress=progressfunc)
                if media_folder: opts["media_folder"] = True
                result = export.export_chats([self.chat], filepath, format, self.db, opts)
                files, count, message_count = result
                guibase.status("Exported %s to %s.",
                               util.plural("message", message_count, sep=","),
                               filepath, log=True)
                util.start_file(filepath)
                wx.CallAfter(self.update_liveinfo)
            else:
                wx.MessageBox("Current filter leaves no data to export.",
                              conf.Title, wx.OK | wx.ICON_INFORMATION)
        except Exception as e:
            guibase.status("Error saving %s: %s", filepath, util.format_exc(e))
            logger.exception("Error saving %s.", filepath)
            errormsg = "Error saving %s:\n\n%s" % \
                       (filepath, traceback.format_exc())
            wx.MessageBox(errormsg, conf.Title, wx.OK | wx.ICON_WARNING)
        finally:
            busy.Close()


    def on_size_html_stats(self, event):
        """Handler for sizing html_stats, sets new scroll position based
        previously stored one (HtmlWindow loses its scroll position on resize).
        """
        html = self.html_stats
        if hasattr(html, "_last_scroll_pos"):
            for i in range(2):
                orient = wx.VERTICAL if i else wx.HORIZONTAL
                # Division can be > 1 on first resizings, bound it to 1.
                ratio = min(1, util.safedivf(html._last_scroll_pos[i],
                    html._last_scroll_range[i]
                ))
                html._last_scroll_pos[i] = ratio * html.GetScrollRange(orient)
            # Execute scroll later as something resets it after this handler
            scroll_func = lambda: html and html.Scroll(*html._last_scroll_pos)
            wx.CallLater(50, scroll_func)
        event.Skip() # Allow event to propagate wx handler


    def on_select_participant(self, event):
        """
        Handler for selecting an item the in the participants list, toggles
        its checked state.
        """
        idx = event.GetIndex()
        if idx < self.list_participants.GetItemCount():
            c = self.list_participants.GetItem(idx)
            c.Check(not c.IsChecked())
            self.list_participants.SetItem(c)
            self.list_participants.Refresh() # Notify list of data change


    def on_scroll_grid_sql(self, event):
        """
        Handler for scrolling the SQL grid, seeks ahead if nearing the end of
        retrieved rows.
        """
        event.Skip()
        # Execute seek later, to give scroll position time to update
        wx.CallLater(50, self.seekahead_grid_sql)


    def seekahead_grid_sql(self):
        """Seeks ahead on the SQL grid if scroll position nearing the end."""
        SEEKAHEAD_POS_RATIO = 0.8
        scrollpos = self.grid_sql.GetScrollPos(wx.VERTICAL)
        scrollrange = self.grid_sql.GetScrollRange(wx.VERTICAL)
        if scrollpos > scrollrange * SEEKAHEAD_POS_RATIO:
            scrollpage = self.grid_sql.GetScrollPageSize(wx.VERTICAL)
            to_end = (scrollpos + scrollpage == scrollrange)
            # Seek to end if scrolled to the very bottom
            self.grid_sql.Table.SeekAhead(to_end)


    def on_scroll_html_stats(self, event):
        """
        Handler for scrolling the HTML stats, stores scroll position
        (HtmlWindow loses it on resize).
        """
        wx.CallAfter(self.store_html_stats_scroll)
        event.Skip() # Allow event to propagate wx handler


    def store_html_stats_scroll(self):
        """
        Stores the statistics HTML scroll position, needed for getting around
        its quirky scroll updating.
        """
        if not self:
            return
        self.html_stats._last_scroll_pos = [
            self.html_stats.GetScrollPos(wx.HORIZONTAL),
            self.html_stats.GetScrollPos(wx.VERTICAL)
        ]
        self.html_stats._last_scroll_range = [
            self.html_stats.GetScrollRange(wx.HORIZONTAL),
            self.html_stats.GetScrollRange(wx.VERTICAL)
        ]


    def on_click_html_stats(self, event):
        """
        Handler for clicking a link in chat history statistics, scrolls to
        anchor if anchor link, sorts the statistics if sort link, goes to
        specific message if transfer author link, otherwise shows the history
        and finds the word clicked in the word cloud.
        """
        href = event.GetLinkInfo().Href
        if href.startswith("#"):
            self.html_stats.ScrollToAnchor(href[1:])
            wx.CallAfter(self.store_html_stats_scroll)
        elif href.startswith("file://"):
            filepath = urllib.request.url2pathname(href[5:])
            if filepath and os.path.exists(filepath):
                util.start_file(filepath)
            else:
                messageBox(
                    "The file \"%s\" cannot be found on this computer."
                    % (filepath),
                    conf.Title, wx.OK | wx.ICON_INFORMATION
                )
        elif href.startswith("http:") or href.startswith("https:"):
            webbrowser.open(href)
        elif href.startswith("sort://"):
            self.stats_sort_field = href[7:]
            self.populate_chat_statistics()
        elif href.startswith("expand://"):
            section = href[9:]
            self.stats_expand[section] = not self.stats_expand[section]
            self.populate_chat_statistics()
        elif href.startswith("message:"):
            self.show_stats(False)
            self.stc_history.FocusMessage(int(href[8:]))
        else:
            self.stc_history.SearchBarVisible = True
            self.show_stats(False)
            self.stc_history.Search(href, flags=wx.stc.STC_FIND_WHOLEWORD)
            self.stc_history.SetFocusSearch()


    def on_click_html_contact(self, event):
        """
        Handler for clicking a link in contact page, sorts chats if sort link, goes to
        specific message if chat link, saves image if image link.
        """
        href = event.GetLinkInfo().Href
        if href == "avatar":
            imgkey = ("avatar", self.contact["id"])
            img = self.imagecache.get(imgkey)
            if not img: return

            self.dialog_saveimage.Filename = util.safe_filename(self.contact["name"])
            fmt = next((k for k, v in export.IMAGE_FORMATS.items() if v == img.Type), None)
            if fmt: self.dialog_saveimage.FilterIndex = export.IMAGE_EXTS.index(fmt)
            if wx.ID_OK != self.dialog_saveimage.ShowModal(): return

            filepath = controls.get_dialog_path(self.dialog_saveimage)
            guibase.status('Exporting "%s".', filepath)
            ext = os.path.splitext(filepath)[-1].lstrip(".").lower()
            # Make copy as SaveFile() converts image format
            img.Copy().SaveFile(filepath, export.IMAGE_FORMATS[ext])
            util.start_file(filepath)
        elif href.startswith("sort://"): # sort://field
            self.contact_sort_field = href[7:]
            self.load_contact(self.contact)
        elif href.startswith("export://"): # export://id
            chatid = int(href[href.index("://") + 3:])
            chat = next(x for x in self.chats if x["id"] == chatid)
            self.on_export_chats([chat])
        elif href.startswith("chat://"): # chat://id or chat://id/messageid
            path = href[href.index("://") + 3:]
            if "/" in path:
                chatid, messageid = map(int, path.split("/", 1))
            else:
                chatid, messageid = int(path), None
            chat = next((x for x in self.chats if chatid == x["id"]), None)
            if chat:
                self.show_stats(False)
                self.notebook.SetSelection(self.pageorder[self.page_chats])
                self.load_chat(chat, center_message_id=messageid)


    def on_rightclick_searchall(self, event):
        """
        Handler for right-clicking in HtmlWindow, sets up a temporary flag for
        HTML link click handler to check, in order to display a context menu.
        """
        self.html_searchall.is_rightclick = True
        def reset():
            if self.html_searchall.is_rightclick: # Flag still up: show menu
                def on_copy(event):
                    if wx.TheClipboard.Open():
                        text = self.html_searchall.SelectionToText()
                        d = wx.TextDataObject(text)
                        wx.TheClipboard.SetData(d), wx.TheClipboard.Close()

                def on_selectall(event):
                    self.html_searchall.SelectAll()
                self.html_searchall.is_rightclick = False
                menu = wx.Menu()
                item_selection = wx.MenuItem(menu, -1, "&Copy selection")
                item_selectall = wx.MenuItem(menu, -1, "&Select all")
                menu.Append(item_selection)
                menu.AppendSeparator()
                menu.Append(item_selectall)
                item_selection.Enable(bool(self.html_searchall.SelectionToText()))
                menu.Bind(wx.EVT_MENU, on_copy, id=item_selection.GetId())
                menu.Bind(wx.EVT_MENU, on_selectall, id=item_selectall.GetId())
                self.html_searchall.PopupMenu(menu)
        event.Skip(), wx.CallAfter(reset)


    def on_click_html_link(self, event):
        """
        Handler for clicking a link in HtmlWindow, opens the link inside
        program or in default browser, opens a popupmenu if right click.
        """
        href = event.GetLinkInfo().Href
        link_data, tab_data = None, None
        if event.EventObject != self.label_html:
            tab_data = self.html_searchall.GetActiveTabData()
        if tab_data and tab_data.get("info"):
            link_data = tab_data["info"]["map"].get(href, {})

        # Workaround for no separate wx.html.HtmlWindow link right click event
        if getattr(self.html_searchall, "is_rightclick", False):
            # Open a pop-up menu with options to copy or select text
            self.html_searchall.is_rightclick = False
            def clipboardize(text):
                if wx.TheClipboard.Open():
                    d = wx.TextDataObject(text)
                    wx.TheClipboard.SetData(d), wx.TheClipboard.Close()
            menutitle = None
            if link_data:
                msg_id, m = link_data.get("message"), None
                if msg_id:
                    menutitle = "C&opy message"
                    def handler(e):
                        if msg_id:
                            m = next(self.db.get_messages(additional_sql="id = :id", 
                                     additional_params={"id": msg_id}), None)
                        if m:
                            t = step.Template(templates.MESSAGE_CLIPBOARD)
                            p = {"m": m, "parser": skypedata.MessageParser(self.db)}
                            clipboardize(t.expand(p))
                else:
                    chat_id, chat = link_data.get("chat"), None
                    if chat_id:
                        chat = next((c for c in self.chats if c["id"] == chat_id), None)
                    if chat:
                        if skypedata.CHATS_TYPE_SINGLE == chat["type"]:
                            menutitle, cliptext = "C&opy contact", chat["identity"]
                        else:
                            menutitle, cliptext = "C&opy chat name", chat["title"]
                        def handler(e):
                            clipboardize(cliptext)
                    elif link_data.get("row"):
                        menutitle = "C&opy row"
                        def handler(e):
                            clipboardize(repr(link_data["row"]))
            else:
                menutitle = "C&opy link location"
                if href.startswith("file://"):
                    href = urllib.request.url2pathname(href[5:])
                    if any(href.startswith(x) for x in ["\\\\\\", "///"]):
                        href = href[3:] # Strip redundant filelink slashes
                    if isinstance(href, six.text_type):
                        # Workaround for wx.html.HtmlWindow double encoding
                        href = href.encode('latin1', errors="xmlcharrefreplace").decode("utf-8")
                    menutitle = "C&opy file location"
                elif href.startswith("mailto:"):
                    href = href[7:]
                    menutitle = "C&opy e-mail address"
                elif any(href.startswith(x) for x in ["callto:", "skype:", "tel:"]):
                    href = href[href.index(":") + 1:]
                    menutitle = "C&opy contact"
                def handler(e):
                    clipboardize(href)
            if menutitle:
                def on_copyselection(event):
                    clipboardize(self.html_searchall.SelectionToText())
                def on_selectall(event):
                    self.html_searchall.SelectAll()
                menu = wx.Menu()
                item_selection = wx.MenuItem(menu, -1, "&Copy selection")
                item_copy = wx.MenuItem(menu, -1, menutitle)
                item_selectall = wx.MenuItem(menu, -1, "&Select all")
                menu.Append(item_selection)
                menu.Append(item_copy)
                menu.Append(item_selectall)
                item_selection.Enable(bool(self.html_searchall.SelectionToText()))
                menu.Bind(wx.EVT_MENU, on_copyselection, id=item_selection.GetId())
                menu.Bind(wx.EVT_MENU, handler, id=item_copy.GetId())
                menu.Bind(wx.EVT_MENU, on_selectall, id=item_selectall.GetId())
                self.html_searchall.PopupMenu(menu)
        elif link_data or href.startswith("file://"):
            # Open the link, or file, or program internal link to chat or table
            chat_id = link_data.get("chat")
            msg_id = link_data.get("message")
            table_name, row = link_data.get("table"), link_data.get("row")
            if href.startswith("file://"):
                filename = path = urllib.request.url2pathname(href[5:])
                if any(path.startswith(x) for x in ["\\\\\\", "///"]):
                    filename = href = path[3:]
                if path and os.path.exists(path):
                    util.start_file(path)
                else:
                    e = "The file \"%s\" cannot be found on this computer." % \
                        filename
                    messageBox(e, conf.Title, wx.OK | wx.ICON_INFORMATION)
            elif chat_id:
                self.notebook.SetSelection(self.pageorder[self.page_chats])
                c = next((c for c in self.chats if chat_id == c["id"]), None)
                if c:
                    self.load_chat(c, center_message_id=msg_id)
                    self.show_stats(False)
                    self.stc_history.SetFocus()
            elif table_name and row:
                tableitem = None
                table_name = table_name.lower()
                table = next((t for t in self.db.get_tables()
                              if t["name"].lower() == table_name), None)
                item = self.tree_tables.GetNext(self.tree_tables.GetRootItem())
                while table and item and item.IsOk():
                    table2 = self.tree_tables.GetItemPyData(item)
                    if table2 and table2.lower() == table["name"].lower():
                        tableitem = item
                        break # break while table and item and itek.IsOk()
                    item = self.tree_tables.GetNextSibling(item)
                if tableitem:
                    self.notebook.SetSelection(self.pageorder[self.page_tables])
                    wx.YieldIfNeeded()
                    # Only way to create state change in wx.lib.gizmos.TreeListCtrl
                    class HackEvent(object):
                        def __init__(self, item): self._item = item
                        def GetItem(self):        return self._item
                    self.on_change_tree_tables(HackEvent(tableitem))
                    if self.tree_tables.GetSelection() != tableitem:
                        self.tree_tables.SelectItem(tableitem)
                        wx.YieldIfNeeded()
                    grid = self.grid_table
                    if grid.Table.filters:
                        grid.Table.ClearSort(refresh=False)
                        grid.Table.ClearFilter()
                    # Search for matching row and scroll to it.
                    table["columns"] = self.db.get_table_columns(table_name)
                    id_fields = [c["name"] for c in table["columns"] if c.get("pk")]
                    if not id_fields: # No primary key fields: take all
                        id_fields = [c["name"] for c in table["columns"]]
                    row_id = [row[c] for c in id_fields]
                    for i in range(grid.Table.GetNumberRows()):
                        row2 = grid.Table.GetRow(i)
                        row2_id = [row2[c] for c in id_fields]
                        if row_id == row2_id:
                            grid.MakeCellVisible(i, 0)
                            grid.SelectRow(i)
                            pagesize = grid.GetScrollPageSize(wx.VERTICAL)
                            pxls = grid.GetScrollPixelsPerUnit()
                            cell_coords = grid.CellToRect(i, 0)
                            y = cell_coords.y // (pxls[1] or 15)
                            x, y = 0, y - pagesize // 2
                            grid.Scroll(x, y)
                            break # for i
        elif href.startswith("page:"):
            # Go to database subpage
            page = href[5:]
            if "#help" == page:
                html = self.html_searchall
                if html.GetTabDataByID(0):
                    html.SetActiveTabByID(0)
                else:
                    h = step.Template(templates.SEARCH_HELP_LONG).expand()
                    html.InsertTab(html.GetTabCount(), "Search help", 0,
                                   h, None)
            elif "#search" == page:
                self.edit_searchall.SetFocus()
            else:
                thepage = getattr(self, "page_" + page, None)
                if thepage:
                    self.notebook.SetSelection(self.pageorder[thepage])
        elif href.startswith("contact:"):
            contactid = int(href[href.index(":") + 1:])
            contact = next((x for x in self.contacts if x["id"] == contactid), None)
            if contact:
                self.notebook.SetSelection(self.pageorder[self.page_contacts])
                self.load_contact(contact)
        elif href.startswith("#"): # In-page link
            event.Skip()
        elif not (href.startswith("chat:") or href.startswith("message:")
        or href.startswith("file:")):
            webbrowser.open(href)


    def on_searchall_toggle_toolbar(self, event):
        """Handler for toggling a setting in search toolbar."""
        if wx.ID_INDEX == event.Id:
            conf.SearchInMessages = True
            conf.SearchInTables = False
            conf.SearchInChatInfo = conf.SearchInContacts = False
            self.label_search.Label = "&Search in messages:"
        elif wx.ID_ABOUT == event.Id:
            conf.SearchInChatInfo = True
            conf.SearchInTables = False
            conf.SearchInMessages = conf.SearchInContacts = False
            self.label_search.Label = "&Search in chat info:"
        elif wx.ID_PREVIEW == event.Id:
            conf.SearchInContacts = True
            conf.SearchInTables = False
            conf.SearchInMessages = conf.SearchInChatInfo = False
            self.label_search.Label = "&Search in contacts:"
        elif wx.ID_STATIC == event.Id:
            conf.SearchInTables = True
            conf.SearchInContacts = False
            conf.SearchInMessages = conf.SearchInChatInfo = False
            self.label_search.Label = "&Search in tables:"
        self.label_search.ContainingSizer.Layout()
        if wx.ID_NEW == event.Id:
            conf.SearchUseNewTab = event.EventObject.GetToolState(event.Id)
        elif not event.EventObject.GetToolState(event.Id):
            # All others are radio tools and state might be toggled off by
            # shortkey key adapter
            event.EventObject.ToggleTool(event.Id, True)


    def on_searchall_stop(self, event):
        """
        Handler for clicking to stop a search, signals the search thread to
        close.
        """
        tab_data = self.html_searchall.GetActiveTabData()
        if tab_data and tab_data["id"] in self.workers_search:
            self.tb_search_settings.SetToolNormalBitmap(
                wx.ID_STOP, images.ToolbarStopped.Bitmap)
            self.workers_search[tab_data["id"]].stop()
            del self.workers_search[tab_data["id"]]


    def on_change_searchall_tab(self, event):
        """Handler for changing a tab in search window, updates stop button."""
        tab_data = self.html_searchall.GetActiveTabData()
        if tab_data and tab_data["id"] in self.workers_search:
            self.tb_search_settings.SetToolNormalBitmap(
                wx.ID_STOP, images.ToolbarStop.Bitmap)
        else:
            self.tb_search_settings.SetToolNormalBitmap(
                wx.ID_STOP, images.ToolbarStopped.Bitmap)


    def on_dclick_searchall_tab(self, event):
        """
        Handler for double-clicking a search tab header, sets the search box
        value to tab text.
        """
        text = event.Data.get("info", {}).get("text")
        if text:
            self.edit_searchall.Value = text
            self.edit_searchall.SetFocus()


    def on_searchall_result(self, event):
        """
        Handler for getting results from search thread, adds the results to
        the search window.
        """
        result = event.result
        search_id, search_done = result.get("search", {}).get("id"), False
        tab_data = self.html_searchall.GetTabDataByID(search_id)
        if tab_data:
            tab_data["info"]["map"].update(result.get("map", {}))
            tab_data["info"]["partial_html"] += result.get("output", "")
            html = tab_data["info"]["partial_html"]
            if "done" in result:
                search_done = True
            else:
                html += "</table></font>"
            text = tab_data["info"]["text"]
            title = text[:50] + ".." if len(text) > 50 else text
            title += " (%s)" % result.get("count", 0)
            self.html_searchall.SetTabDataByID(search_id, title, html,
                                               tab_data["info"])
        if search_done:
            guibase.status("Finished searching for \"%s\" in %s.",
                           result["search"]["text"], self.db.filename)
            self.tb_search_settings.SetToolNormalBitmap(
                wx.ID_STOP, images.ToolbarStopped.Bitmap)
            if search_id in self.workers_search:
                self.workers_search[search_id].stop()
                del self.workers_search[search_id]
        if "error" in result:
            logger.error("Error searching %s:\n\n%s", self.db, result["error"])
            errormsg = "Error searching %s:\n\n%s" % \
                       (self.db, result.get("error_short", result["error"]))
            wx.MessageBox(errormsg, conf.Title, wx.OK | wx.ICON_WARNING)


    def on_searchall_callback(self, result):
        """Callback function for SearchThread, posts the data to self."""
        if self: # Check if instance is still valid (i.e. not destroyed by wx)
            wx.PostEvent(self, WorkerEvent(result=result))


    def on_searchall(self, event):
        """
        Handler for clicking to global search the database.
        """
        text = self.edit_searchall.Value
        if text.strip():
            guibase.status("Searching for \"%s\" in %s.", text, self.db.filename)
            html = self.html_searchall
            data = {"id": self.counter(), "db": self.db, "text": text, "map": {},
                    "width": html.Size.width * 5 // 9, "table": "",
                    "partial_html": ""}
            fromtext = "" # "Searching for "text" in fromtext"
            if conf.SearchInMessages:
                data["table"] = "messages"
                fromtext = "messages"
            elif conf.SearchInChatInfo:
                data["table"] = "conversations"
                fromtext = "chat information"
            elif conf.SearchInContacts:
                data["table"] = "contacts"
                fromtext = "contact information"
            elif conf.SearchInTables:
                fromtext = data["table"] = "all tables"
            # Partially assembled HTML for current results
            template = step.Template(templates.SEARCH_HEADER_HTML, escape=True)
            data["partial_html"] = template.expand(locals())

            worker = workers.SearchThread(self.on_searchall_callback)
            self.workers_search[data["id"]] = worker
            worker.work(data)
            bmp = images.ToolbarStop.Bitmap
            self.tb_search_settings.SetToolNormalBitmap(wx.ID_STOP, bmp)

            title = text[:50] + ".." if len(text) > 50 else text
            content = data["partial_html"] + "</table></font>"
            if conf.SearchUseNewTab or not html.GetTabCount():
                html.InsertTab(0, title, data["id"], content, data)
            else:
                # Set new ID for the existing reused tab
                html.SetTabDataByID(html.GetActiveTabData()["id"], title,
                                    content, data, data["id"])

            self.notebook.SetSelection(self.pageorder[self.page_search])
            util.add_unique(conf.SearchHistory, text.strip(), 1,
                            conf.MaxSearchHistory)
            self.TopLevelParent.dialog_search.Value = conf.SearchHistory[-1]
            self.TopLevelParent.dialog_search.SetChoices(conf.SearchHistory)
            self.edit_searchall.SetChoices(conf.SearchHistory)
            self.edit_searchall.SetFocus()
            util.run_once(conf.save)


    def on_delete_tab_callback(self, tab):
        """
        Function called by html_searchall after deleting a tab, stops the
        ongoing search, if any.
        """
        tab_data = self.html_searchall.GetActiveTabData()
        if tab_data and tab_data["id"] == tab["id"]:
            self.tb_search_settings.SetToolNormalBitmap(
                wx.ID_STOP, images.ToolbarStopped.Bitmap)
        if tab["id"] in self.workers_search:
            self.workers_search[tab["id"]].stop()
            del self.workers_search[tab["id"]]


    def on_mouse_over_grid(self, event):
        """
        Handler for moving the mouse over a grid, shows datetime tooltip for
        UNIX timestamp cells.
        """
        tip = ""
        grid = event.EventObject.Parent
        prev_cell = getattr(grid, "_hovered_cell", None)
        x, y = grid.CalcUnscrolledPosition(event.X, event.Y)
        row, col = grid.XYToCell(x, y)
        if row >= 0 and col >= 0:
            value = grid.Table.GetValue(row, col)
            col_name = grid.Table.GetColLabelValue(col).lower()
            if type(value) is int and value > 100000000 \
            and ("time" in col_name or "history" in col_name):
                try:
                    tip = self.db.stamp_to_date(value).strftime(
                          "%Y-%m-%d %H:%M:%S")
                except Exception:
                    tip = util.to_unicode(value)
            else:
                tip = util.to_unicode(value)
            tip = tip if len(tip) < 1000 else tip[:1000] + ".."
        if (row, col) != prev_cell or not (event.EventObject.ToolTip) \
        or event.EventObject.ToolTip.Tip != tip:
            event.EventObject.SetToolTip(tip)
        grid._hovered_cell = (row, col)


    def on_participants_dclick(self, event):
        """
        Handler for double-clicking an item in the participants list,
        checks/unchecks (CheckListBox checks only when clicking on the
        checkbox icon itself).
        """
        checkeds = list(event.EventObject.Checked)
        do_check = not event.EventObject.IsChecked(event.Selection)
        if do_check and event.Selection not in checkeds:
            checkeds.append(event.Selection)
        elif not do_check and event.Selection in checkeds:
            checkeds.remove(event.Selection)
        event.EventObject.SetChecked(checkeds)


    def on_filterreset_chat(self, event):
        """
        Handler for clicking to reset current chat history filter, restores
        initial values to filter controls, and reapplies the filter, scrolling
        to the message displayed last, if possible.
        """
        self.edit_filtertext.Value = ""
        self.range_date.SetValues(*self.chat_filter["startdaterange"])
        for i in range(self.list_participants.GetItemCount()):
            c = self.list_participants.GetItem(i)
            c.Check(True)
            self.list_participants.SetItem(c)
        self.list_participants.Refresh()

        new_filter = self.build_filter()
        if self.cmp_filter(new_filter): return # Filter unchanged

        focus_message_id, selected = self.stc_history.GetFocusedMessage()
        self.on_filter_chat(event, new_filter)
        if focus_message_id is not None:
            self.stc_history.FocusMessage(focus_message_id, select=selected)


    def on_filter_chat(self, event, new_filter=None):
        """
        Handler for clicking to filter current chat history, applies the
        current filter to the chat messages.
        """
        focus_message_id = None
        if new_filter is None:
            new_filter = self.build_filter()
            if self.cmp_filter(new_filter): return # Filter unchanged
            focus_message_id, _ = self.stc_history.GetFocusedMessage(selectedonly=True)
        busy = controls.BusyPanel(self, "Filtering messages.")
        try:
            self.chat_filter.update(new_filter)
            self.stc_history.SetFilter(self.chat_filter)
            self.stc_history.RefreshMessages()
            self.populate_chat_statistics()
            self.list_timeline.Populate(*self.stc_history.GetTimelineData())
        finally:
            busy.Close()
        self.tb_chat.EnableTool(wx.ID_MORE, self.chat["message_count"] > 0)
        if focus_message_id is not None:
            self.stc_history.FocusMessage(focus_message_id)


    def build_filter(self):
        """Builds chat filter data from current control state."""
        # At least one participant must be selected: reset to previously
        # selected participants instead if nothing selected
        reselecteds = []
        for i in range(self.list_participants.GetItemCount()):
            # UltimateListCtrl does not expose checked state, have to
            # query it from each individual row
            if not self.list_participants.GetItem(i).IsChecked():
                identity = self.list_participants.GetItemData(i)["identity"]
                if identity in self.chat_filter["participants"]:
                    reselecteds.append(i)
        if reselecteds:
            for i in range(self.list_participants.GetItemCount()):
                identity = self.list_participants.GetItemData(i)["identity"]
                if identity in reselecteds:
                    c = self.list_participants.GetItem(i)
                    c.Check(True)
                    self.list_participants.SetItem(c)
            self.list_participants.Refresh()
        participants = []
        for i in range(self.list_participants.GetItemCount()):
            if self.list_participants.IsItemChecked(i):
                identity = self.list_participants.GetItemData(i)["identity"]
                participants.append(identity)
        filterdata = {
            "daterange": self.range_date.Values,
            "text": self.edit_filtertext.Value,
            "participants": participants
        }
        return filterdata


    def cmp_filter(self, filterdata):
        """Returns whether chat filter data is same as currently applied."""
        old_filter = self.stc_history.Filter
        if "text" not in old_filter: old_filter["text"] = ""
        if "participants" not in old_filter:
            everyone = [x["identity"] for x in self.chat["participants"]]
            old_filter["participants"] = everyone
        return util.cmp_dicts(filterdata, old_filter)


    def on_toggle_filter(self, event):
        """Handler for clicking to show/hide chat filter."""
        self.toggle_filter(not self.splitter_stc.IsSplit())


    def on_toggle_stats(self, event):
        """
        Handler for clicking to show/hide statistics for chat, toggles display
        between chat history window and statistics window.
        """
        html, stc = self.html_stats, self.stc_history
        self.show_stats(not html.Shown)
        (html if html.Shown else stc).SetFocus()


    def on_toggle_maximize(self, event):
        """Handler for toggling to maximize chat window and hide chat list."""
        splitter = self.splitter_chats
        if splitter.IsSplit():
            splitter._sashPosition = splitter.SashPosition
            splitter.Unsplit(self.panel_chats1)
            shorthelp = "Restore chat panel to default size  (Alt-M)"
        else:
            pos = getattr(splitter, "_sashPosition", self.Size[1] // 3)
            splitter.SplitHorizontally(self.panel_chats1, self.panel_chats2,
                                       sashPosition=pos)
            shorthelp = "Maximize chat panel  (Alt-M)"
        self.tb_chat.SetToolShortHelp(wx.ID_ZOOM_100, shorthelp)


    def on_toggle_timeline(self, event):
        """Handler for toggling to show/hide chat timeline."""
        self.panel_stc1.Freeze()
        try:
            self.list_timeline.Show(not self.list_timeline.Shown)
            self.list_timeline.ContainingSizer.Layout()
        finally: self.panel_stc1.Thaw()
        self.list_timeline.RefreshItems()


    def toggle_filter(self, on):
        """Toggles the chat filter panel on/off."""
        if self.splitter_stc.IsSplit() and not on:
            self.splitter_stc._sashPosition = self.splitter_stc.SashPosition
            self.splitter_stc.Unsplit(self.panel_stc2)
        elif not self.splitter_stc.IsSplit() and on:
            p = getattr(self.splitter_stc, "_sashPosition",
                self.splitter_stc.Size.width - self.panel_stc2.BestSize.width)
            self.splitter_stc.SplitVertically(self.panel_stc1, self.panel_stc2,
                                              sashPosition=p)
            list_participants = self.list_participants
            list_participants.SetColumnWidth(0, list_participants.Size.width)


    def on_select_timeline(self, event):
        """Handler for selecting a time in timeline control, focuses message in STC"""
        msg_id = self.list_timeline.GetMessage(event.Selection)
        if msg_id is not None:
            self.stc_history.FocusMessage(msg_id, select=False)


    def on_blur_timeline(self, event):
        """Handler for clicking out of timeline, clears selection (distracting)."""
        self.list_timeline.SetSelection(-1)


    def on_scroll_chat_history(self, event):
        """Handler for scrolling chat history, updates timeline highlight."""
        event.Skip()
        if self.timeline_timer: return

        def do_highlight():
            if not self: return
            self.timeline_timer = None
            self.list_timeline.HighlightRows(self.stc_history.GetVisibleMessages())
        self.timeline_timer = wx.CallLater(200, do_highlight)


    def show_stats(self, show=True):
        """Shows or hides the statistics window."""
        html, stc = self.html_stats, self.stc_history
        changed = False
        focus = False
        for i in [html, stc]:
            focus = focus or (i.Shown and i.FindFocus() == i)
        self.panel_stc1.Freeze()
        try:
            if not stc.Shown != show:
                stc.Show(not show)
                changed = True
            if html.Shown != show:
                html.Show(show)
                changed = True
            if changed:
                if show: self.list_timeline.Hide()
                elif self.tb_chat.GetToolState(wx.ID_JUMP_TO):
                    self.list_timeline.Show()
                self.tb_chat.EnableTool(wx.ID_JUMP_TO, not show)
                html.ContainingSizer.Layout()
                stc.ContainingSizer.Layout()
            if focus: # Switch focus to the other control if previous had focus
                (html if show else stc).SetFocus()
            if show:
                if hasattr(html, "_last_scroll_pos"):
                    html.Scroll(*html._last_scroll_pos)
                elif html.OpenedAnchor: html.ScrollToAnchor(html.OpenedAnchor)
            else:
                self.list_timeline.RefreshItems()
            self.tb_chat.ToggleTool(wx.ID_PROPERTIES, show)
        finally: self.panel_stc1.Thaw()


    def on_button_reset_grid(self, event):
        """
        Handler for clicking to remove sorting and filtering on a grid,
        resets the grid and its view.
        """
        is_table = (event.EventObject == self.button_reset_grid_table)
        grid = self.grid_table if is_table else self.grid_sql
        if grid.Table and isinstance(grid.Table, SqliteGridBase):
            grid.Table.ClearSort(refresh=False)
            grid.Table.ClearFilter()
            grid.ContainingSizer.Layout() # React to grid size change


    def on_button_export_grid(self, event):
        """
        Handler for clicking to export wx.Grid contents to file, allows the
        user to select filename and type and creates the file.
        """
        grid_source = self.grid_table
        sql = ""
        table = ""
        if event.EventObject is self.button_export_sql:
            grid_source = self.grid_sql
            sql = getattr(self, "last_sql", "")
        if grid_source.Table:
            if grid_source is self.grid_table:
                table = self.db.tables[grid_source.Table.table.lower()]["name"]
                title = "Table - \"%s\"" % table
                self.dialog_savefile.Wildcard = export.TABLE_WILDCARD
            else:
                title = "SQL query"
                self.dialog_savefile.Wildcard = export.QUERY_WILDCARD
                grid_source.Table.SeekAhead(True)
            self.dialog_savefile.Filename = util.safe_filename(title)
            self.dialog_savefile.Message = "Save table as"
            if wx.ID_OK == self.dialog_savefile.ShowModal():
                filename = controls.get_dialog_path(self.dialog_savefile)
                exts = export.TABLE_EXTS if grid_source is self.grid_table \
                       else export.QUERY_EXTS
                format = exts[self.dialog_savefile.FilterIndex]
                busy = controls.BusyPanel(self, "Exporting \"%s\"." % filename)
                guibase.status("Exporting \"%s\".", filename)
                try:
                    export.export_grid(grid_source, filename, title,
                                       self.db, sql, table)
                    guibase.status("Exported %s.", filename, log=True)
                    util.start_file(filename)
                except Exception as e:
                    guibase.status("Error saving %s: %s", filename, util.format_exc(e))
                    logger.exception("Error saving %s.", filename)
                    errormsg = "Error saving %s:\n\n%s" % \
                               (filename, traceback.format_exc())
                    wx.MessageBox(errormsg, conf.Title, wx.OK | wx.ICON_WARNING)
                finally:
                    busy.Close()


    def on_keydown_sql(self, event):
        """
        Handler for pressing a key in SQL editor, listens for Alt-Enter and
        executes the currently selected line, or currently active line.
        """
        stc = event.GetEventObject()
        if event.AltDown() and wx.WXK_RETURN == event.KeyCode:
            sql = (stc.SelectedText or stc.CurLine[0]).strip()
            if sql:
                self.execute_sql(sql)
        event.Skip() # Allow to propagate to other handlers


    def on_button_sql(self, event):
        """
        Handler for clicking to run an SQL query, runs the selected text or
        whole contents, displays its results, if any, and commits changes 
        done, if any.
        """
        sql = self.stc_sql.SelectedText.strip() or self.stc_sql.Text.strip()
        if sql:
            self.execute_sql(sql)


    def on_button_script(self, event):
        """
        Handler for clicking to run multiple SQL statements, runs the selected
        text or whole contents as an SQL script.
        """
        sql = self.stc_sql.SelectedText.strip() or self.stc_sql.Text.strip()
        try:
            if sql:
                logger.info("Executing SQL script \"%s\".", sql)
                self.db.connection.executescript(sql)
                self.grid_sql.SetTable(None)
                self.grid_sql.CreateGrid(1, 1)
                self.grid_sql.SetColLabelValue(0, "Affected rows")
                self.grid_sql.SetCellValue(0, 0, "-1")
                self.button_reset_grid_sql.Enabled = False
                self.button_export_sql.Enabled = False
                size = self.grid_sql.Size
                self.grid_sql.Fit()
                # Jiggle size by 1 pixel to refresh scrollbars
                self.grid_sql.Size = size[0], size[1]-1
                self.grid_sql.Size = size[0], size[1]
        except Exception as e:
            msg = util.format_exc(e)
            guibase.status(msg, log=True)
            wx.MessageBox(msg, conf.Title, wx.OK | wx.ICON_WARNING)


    def execute_sql(self, sql):
        """Executes the SQL query and populates the SQL grid with results."""
        try:
            grid_data = None
            if sql.lower().startswith(("select", "pragma", "explain")):
                # SELECT statement: populate grid with rows
                grid_data = SqliteGridBase(self.db, sql=sql)
                self.grid_sql.SetTable(grid_data, takeOwnership=True)
                self.button_reset_grid_sql.Enabled = True
                self.button_export_sql.Enabled = True
            else:
                # Assume action query
                affected_rows = self.db.execute_action(sql)
                self.grid_sql.SetTable(None)
                self.grid_sql.CreateGrid(1, 1)
                self.grid_sql.SetColLabelValue(0, "Affected rows")
                self.grid_sql.SetCellValue(0, 0, str(affected_rows))
                self.button_reset_grid_sql.Enabled = False
                self.button_export_sql.Enabled = False
            guibase.status("Executed SQL \"%s\" (%s).", sql, self.db, log=True)
            size = self.grid_sql.Size
            self.grid_sql.Fit()
            # Jiggle size by 1 pixel to refresh scrollbars
            self.grid_sql.Size = size[0], size[1]-1
            self.grid_sql.Size = size[0], size[1]
            self.last_sql = sql
            self.grid_sql.SetColMinimalAcceptableWidth(100)
            if grid_data:
                col_range = range(grid_data.GetNumberCols())
                [self.grid_sql.AutoSizeColLabelSize(x) for x in col_range]
        except Exception as e:
            msg = util.format_exc(e)
            guibase.status(msg, log=True)
            wx.MessageBox(msg, conf.Title, wx.OK | wx.ICON_WARNING)


    def get_unsaved_grids(self):
        """
        Returns a list of SqliteGridBase grids where changes have not been
        saved after changing.
        """
        return [g for g in self.db_grids.values() if g.IsChanged()]


    def save_unsaved_grids(self):
        """Saves all data in unsaved table grids, returns success/failure."""
        result = True
        for grid in (x for x in self.db_grids.values() if x.IsChanged()):
            try:
                grid.SaveChanges()
            except Exception as e:
                result = False
                guibase.status('Error saving table %s in "%s": %s',
                               grid.table, self.db, util.format_exc(e))
                logger.exception('Error saving table %s in "%s".',
                                 grid.table, self.db)
                errormsg = 'Error saving table %s in "%s":\n\n%s' % (
                           grid.table, self.db, traceback.format_exc())
                wx.MessageBox(errormsg, conf.Title, wx.OK | wx.ICON_WARNING)
                break # for grid
        return result


    def on_change_table(self, event):
        """
        Handler when table grid data is changed, refreshes icons,
        table lists and database display.
        """
        grid_data = self.grid_table.Table
        # Enable/disable commit and rollback icons
        self.tb_grid.EnableTool(wx.ID_SAVE, grid_data.IsChanged())
        self.tb_grid.EnableTool(wx.ID_UNDO, grid_data.IsChanged())
        # Highlight changed tables in the table list
        colour = conf.DBTableChangedColour if grid_data.IsChanged() \
                 else self.tree_tables.ForegroundColour
        item = self.tree_tables.GetNext(self.tree_tables.GetRootItem())
        while item and item.IsOk():
            list_table = self.tree_tables.GetItemPyData(item)
            if list_table:
                if list_table.lower() == grid_data.table.lower():
                    self.tree_tables.SetItemTextColour(item, colour)

                    break # break while item and item.IsOk()
            item = self.tree_tables.GetNextSibling(item)

        # Mark database as changed/pristine in the parent notebook tabs
        for i in range(self.parent_notebook.GetPageCount()):
            if self.parent_notebook.GetPage(i) == self:
                suffix = "*" if self.get_unsaved_grids() else ""
                title = self.title + suffix
                if self.parent_notebook.GetPageText(i) != title:
                    self.parent_notebook.SetPageText(i, title)
                break # for i


    def on_commit_table(self, event):
        """Handler for clicking to commit the changed database table."""
        info = self.grid_table.Table.GetChangedInfo()
        if wx.OK == wx.MessageBox(
            "Are you sure you want to commit these changes (%s)?" %
            info, conf.Title, wx.OK | wx.CANCEL | wx.ICON_QUESTION
        ):
            logger.info("Committing %s in table %s (%s).", info,
                        self.grid_table.Table.table, self.db)
            self.grid_table.Table.SaveChanges()
            self.on_change_table(None)
            # Refresh tables list with updated row counts
            tablemap = dict((t["name"], t) for t in self.db.get_tables(True))
            item = self.tree_tables.GetNext(self.tree_tables.GetRootItem())
            while item and item.IsOk():
                table = self.tree_tables.GetItemPyData(item)
                if table:
                    self.tree_tables.SetItemText(item, "%d row%s" % (
                        tablemap[table]["rows"],
                        "s" if tablemap[table]["rows"] != 1 else " "
                    ), 1)
                    if table == self.grid_table.Table.table:
                        self.tree_tables.SetItemBold(item,
                        self.grid_table.Table.IsChanged())
                item = self.tree_tables.GetNextSibling(item)
            self.grid_table.ForceRefresh()  # Refresh cell colours


    def on_rollback_table(self, event):
        """Handler for clicking to rollback the changed database table."""
        self.grid_table.Table.UndoChanges()
        self.on_change_table(None)
        self.grid_table.ContainingSizer.Layout()  # Refresh scrollbars
        self.grid_table.ForceRefresh() # Refresh cell colours


    def on_insert_row(self, event):
        """
        Handler for clicking to insert a table row, lets the user edit a new
        grid line.
        """
        self.grid_table.InsertRows(pos=0, numRows=1)
        self.grid_table.SetGridCursor(0, self.grid_table.GetGridCursorCol())
        self.grid_table.Scroll(self.grid_table.GetScrollPos(wx.HORIZONTAL), 0)
        self.grid_table.Refresh()
        self.on_change_table(None)
        self.grid_table.ContainingSizer.Layout()  # Refresh scrollbars


    def on_delete_row(self, event):
        """
        Handler for clicking to delete a table row, removes the row from grid.
        """
        selected_rows = self.grid_table.GetSelectedRows()
        cursor_row = self.grid_table.GetGridCursorRow()
        if cursor_row >= 0:
            selected_rows.append(cursor_row)
        for row in selected_rows:
            self.grid_table.DeleteRows(row)
        self.grid_table.ContainingSizer.Layout() # Refresh scrollbars
        self.on_change_table(None)


    def on_update_grid_table(self, event):
        """Refreshes the table grid UI components, like toolbar icons."""
        self.tb_grid.EnableTool(wx.ID_SAVE, self.grid_table.Table.IsChanged())
        self.tb_grid.EnableTool(wx.ID_UNDO, self.grid_table.Table.IsChanged())


    def on_change_tree_tables(self, event):
        """
        Handler for selecting an item in the tables list, loads the table data
        into the table grid.
        """
        table = None
        item = event.GetItem()
        if item and item.IsOk():
            table = self.tree_tables.GetItemPyData(item)
            lower = table.lower() if table else None
        if table and \
        (not self.grid_table.Table
         or self.grid_table.Table.table.lower() != lower):
            i = self.tree_tables.GetNext(self.tree_tables.GetRootItem())
            while i:
                text = self.tree_tables.GetItemText(i).lower()
                self.tree_tables.SetItemBold(i, text == lower)
                i = self.tree_tables.GetNextSibling(i)
            logger.info("Loading table %s (%s).", table, self.db)
            busy = controls.BusyPanel(self, "Loading table \"%s\"." % table)
            try:
                grid_data = self.db_grids.get(lower)
                if not grid_data:
                    grid_data = SqliteGridBase(self.db, table=table)
                    self.db_grids[lower] = grid_data
                self.label_table.Label = "Table \"%s\":" % table
                self.grid_table.SetTable(None)
                self.grid_table.SetTable(grid_data)
                self.page_tables.Layout() # React to grid size change
                self.grid_table.Scroll(0, 0)
                self.grid_table.SetColMinimalAcceptableWidth(100)
                col_range = range(grid_data.GetNumberCols())
                [self.grid_table.AutoSizeColLabelSize(x) for x in col_range]
                self.on_change_table(None)
                self.tb_grid.EnableTool(wx.ID_ADD, True)
                self.tb_grid.EnableTool(wx.ID_DELETE, True)
                self.button_export_table.Enabled = True
                self.button_reset_grid_table.Enabled = True
                busy.Close()
            except Exception as e:
                busy.Close()
                guibase.status("Could not load table %s: %s", table, util.format_exc(e))
                logger.exception("Could not load table %s.", table)
                errormsg = "Could not load table %s.\n\n%s" % \
                           (table, traceback.format_exc())
                wx.MessageBox(errormsg, conf.Title, wx.OK | wx.ICON_WARNING)


    def on_change_list_chats(self, event):
        """
        Handler for selecting an item in the chats list, loads the
        messages into the message log.
        """
        self.load_chat(self.list_chats.GetItemMappedData(event.Index))
        self.stc_history.SetFocus()


    def on_change_list_contacts(self, event):
        """Handler for selecting an item in the contacts list, loads contact info."""
        self.load_contact(self.list_contacts.GetItemMappedData(event.Index))


    def load_chat(self, chat, center_message_id=None):
        """Loads history of the specified chat (as returned from db)."""
        if not chat or (chat == self.chat and not center_message_id):
            return

        busy, clist, plist = None, self.list_chats, self.list_participants
        if chat != self.chat:
            # Update chat list colours and scroll to the opened chat
            logger.info("Opening %s.", chat["title_long_lc"])
            clist.Freeze()
            scrollpos = clist.GetScrollPos(wx.VERTICAL)
            index_selected = -1
            for i in range(clist.ItemCount):
                if clist.GetItemMappedData(i) == self.chat:
                    clist.SetItemFont(i, clist.Font)
                elif clist.GetItemMappedData(i) == chat:
                    index_selected = i
                    f = clist.Font; f.SetWeight(wx.FONTWEIGHT_BOLD)
                    clist.SetItemFont(i, f)
            if index_selected >= 0:
                delta = index_selected - scrollpos
                if delta < 0 or abs(delta) >= clist.CountPerPage:
                    nudge = -clist.CountPerPage // 2
                    clist.ScrollLines(delta + nudge)
            clist.Thaw()
            wx.YieldIfNeeded() # Allow display to refresh
            # Add shortcut key flag to chat label
            self.label_chat.Label = chat["title_long"].replace(
                "chat", "&chat"
            ).replace("Chat", "&Chat") + ":"
            self.label_chat.Parent.Layout()

        dates_range  = [None, None] # total available date range
        dates_values = [None, None] # currently filtered date range
        if chat != self.chat or (center_message_id
        and not self.stc_history.IsMessageShown(center_message_id)):
            busy = controls.BusyPanel(self, 
                "Loading history for %s." % chat["title_long_lc"])
            try:
                # Refresh last messages, in case database has updated
                self.db.get_conversations_stats([chat], log=False)
            except Exception:
                guibase.status("Notice: failed to refresh %s.",
                               chat["title_long_lc"])
                logger.exception("Notice: failed to refresh %s.",
                                 chat["title_long_lc"])
            self.edit_filtertext.Value = self.chat_filter["text"] = ""
            dts = "first_message_datetime", "last_message_datetime"
            date_range = [chat[n].date() if chat[n] else None for n in dts]
            self.chat_filter["daterange"] = date_range
            if chat != self.chat:
                self.chat_filter["startdaterange"] = date_range
            dates_range = dates_values = date_range
            avatar_default = images.AvatarDefault.Bitmap
            if chat != self.chat:
                # If chat has changed, load avatar images for the contacts
                plist.ClearAll()
                plist.InsertColumn(0, "")
                sz_avatar = conf.AvatarImageSize
                il = wx.ImageList(*sz_avatar)
                il.Add(avatar_default)
                plist.AssignImageList( il, wx.IMAGE_LIST_SMALL)
                index = 0

                nolog = wx.LogNull() # wx will otherwise open a warning dialog on image error
                for p in chat["participants"]:
                    b = 0
                    if not p["contact"].get("avatar_bitmap"):
                        img = skypedata.get_avatar(p["contact"], sz_avatar)
                        if img:
                            p["contact"]["avatar_bitmap"] = img.ConvertToBitmap()
                    if "avatar_bitmap" in p["contact"]:
                        b = il.Add(p["contact"]["avatar_bitmap"])
                    t = p["contact"]["name"]
                    if p["identity"] != p["contact"]["name"]:
                        t += " (%s)" % p["identity"]
                    t = t.replace("\n", " ")
                    try: plist.InsertImageStringItem(index, t, b, it_kind=1)
                    except Exception:
                        t = re.sub(r"[^\w %s]" % re.escape(string.punctuation),
                                   lambda m: "#%s" % ord(m.group(0)), t, re.U)
                        plist.InsertImageStringItem(index, t, b, it_kind=1)
                    plist.SetItemTextColour(index,       plist.ForegroundColour)
                    plist.SetItemBackgroundColour(index, plist.BackgroundColour)
                    c = plist.GetItem(index)
                    c.Check(True)
                    plist.SetItem(c)
                    plist.SetItemData(index, p)
                    index += 1
                del nolog # Restore default wx message logger
                plist.SetColumnWidth(0, wx.LIST_AUTOSIZE)
            self.chat_filter["participants"] = [
                p["identity"] for p in chat["participants"]]

        if center_message_id and self.chat == chat:
            if not self.stc_history.IsMessageShown(center_message_id):
                for i in range(plist.GetItemCount()):
                    c = plist.GetItem(i)
                    c.Check(True)
                    plist.SetItem(c)
                plist.Refresh()
                self.stc_history.SetFilter(self.chat_filter)
                self.stc_history.RefreshMessages(center_message_id)
            else:
                self.stc_history.FocusMessage(center_message_id)
        else:
            self.stc_history.SetFilter(self.chat_filter)
            try:
                self.stc_history.Populate(chat, self.db,
                    center_message_id=center_message_id)
                if center_message_id \
                and not self.stc_history.IsMessageShown(center_message_id):
                    self.stc_history.SetFilter(self.chat_filter)
                    self.stc_history.RefreshMessages(center_message_id)
                    self.stc_history.FocusMessage(center_message_id)
            except Exception as e:
                guibase.status("Error loading %s: %s",
                               chat["title_long_lc"], util.format_exc(e))
                logger.exception("Error loading %s.", chat["title_long_lc"])
                errormsg = "Error loading %s:\n\n%s" % \
                           (chat["title_long_lc"], traceback.format_exc())
                wx.MessageBox(errormsg, conf.Title, wx.OK | wx.ICON_WARNING)

        if self.stc_history.GetMessage(0):
            values = [self.stc_history.GetMessage(0)["datetime"],
                      self.stc_history.GetMessage(-1)["datetime"]]
            dates_values = [i.date() for i in values]
            if not any(filter(bool, dates_range)):
                dts = "first_message_datetime", "last_message_datetime"
                dates_range = [chat[n].date() if chat[n] else None for n in dts]
            if not any(filter(bool, dates_range)):
                dates_range = dates_values
            self.chat_filter["daterange"] = dates_range
            if chat != self.chat or not all(self.chat_filter["startdaterange"]):
                self.chat_filter["startdaterange"] = dates_values
        self.range_date.SetRange(*dates_range)
        self.edit_filterdate1.Range = self.edit_filterdate2.Range = dates_range
        self.range_date.SetValues(*dates_values)
        has_messages = bool(self.stc_history.GetMessage(0))
        self.tb_chat.EnableTool(wx.ID_MORE, has_messages)
        if not self.chat:
            # Very first load, toggle filter tool button on
            self.tb_chat.ToggleTool(wx.ID_MORE, self.splitter_stc.IsSplit())
        if self.chat != chat:
            self.chat = chat
        if busy:
            busy.Close()
        self.panel_chats2.Enabled = True
        self.list_timeline.Populate(*self.stc_history.GetTimelineData())
        self.populate_chat_statistics()
        if self.html_stats.Shown:
            self.show_stats(True) # To restore scroll position


    def load_contact(self, contact):
        """Loads contact information: avatar, profile, and chats data."""
        busy, clist = None, self.list_contacts
        if not contact:
            self.label_contact.Label = ""
            self.html_contact.SetPage("")
            self.html_contact.BackgroundColour = ColourManager.GetColour(wx.SYS_COLOUR_WINDOW)
            self.html_contact.Parent.Disable()
            for i in range(clist.ItemCount) if self.contact else ():
                if clist.GetItemMappedData(i) == self.contact:
                    clist.SetItemFont(i, clist.Font)
            self.contact = None
        if not contact:
            return

        # Update contact list colours and scroll to the opened contact
        if contact != self.contact:
            logger.info("Opening contact %s.", contact["name"])
            clist.Freeze()
            scrollpos = clist.GetScrollPos(wx.VERTICAL)
            index_selected = -1
            for i in range(clist.ItemCount):
                if clist.GetItemMappedData(i) == self.contact:
                    clist.SetItemFont(i, clist.Font)
                elif clist.GetItemMappedData(i) == contact:
                    index_selected = i
                    f = clist.Font; f.SetWeight(wx.FONTWEIGHT_BOLD)
                    clist.SetItemFont(i, f)
            if index_selected >= 0:
                delta = index_selected - scrollpos
                if delta < 0 or abs(delta) >= clist.CountPerPage:
                    nudge = -clist.CountPerPage // 2
                    clist.ScrollLines(delta + nudge)
            clist.Thaw()
            wx.YieldIfNeeded() # Allow display to refresh
            self.label_contact.Label = "&Contact %(name)s (%(identity)s):" % contact
            self.label_contact.Parent.Layout()

        titlemap = {x["id"]: x["title_long"] for x in self.chats}
        for data in contact.get("conversations", []):
            data["title_long"] = titlemap[data["id"]]
        MINS = {"message_count": -sys.maxsize, "ratio": -sys.maxsize,
                "first_message_datetime": datetime.datetime.min,
                "last_message_datetime": datetime.datetime.min}
        sortkey = lambda x: util.coalesce(x[self.contact_sort_field], MINS.get(self.contact_sort_field, ""))
        contact.get("conversations", []).sort(key=sortkey, reverse=True)

        avatar_path, avatar_size, avatar_raw = None, None, skypedata.get_avatar_raw(contact)
        if skypedata.get_avatar_data(contact):
            imgkey = ("avatar", contact["id"])
            img = self.imagecache.get(imgkey) or skypedata.get_avatar(contact)
            ext = next((k for k, v in export.IMAGE_FORMATS.items() if img and v == img.Type), "jpg")
            vals = (contact["identity"], self.db.filename.encode("utf-8"), ext)
            fn = "%s_%s_fullsize.%s" % tuple(map(urllib.parse.quote, vals))
            if img and fn not in self.memoryfs["files"]:
                self.memoryfs["handler"].AddFile(fn, img, img.Type)
                self.memoryfs["files"][fn] = 1
            if fn in self.memoryfs["files"]:
                avatar_path = fn
            if img:
                self.imagecache[imgkey] = img
                avatar_size = tuple(img.GetSize())
            defaultavatar = "avatar__default__large.png"
            if defaultavatar not in self.memoryfs["files"]:
                img = images.AvatarDefaultLarge.Image
                self.memoryfs["handler"].AddFile(defaultavatar, img, wx.BITMAP_TYPE_PNG)
                self.memoryfs["files"][defaultavatar] = 1

        data = {"contact": contact, "avatar": avatar_path, "avatar_size": avatar_size,
                "db": self.db, "sort_by": self.contact_sort_field}
        html = step.Template(templates.CONTACT_HTML, escape=True).expand(data)
        scrollpos = [self.html_contact.GetScrollPos(x) for x in (wx.HORIZONTAL, wx.VERTICAL)]
        self.html_contact.SetPage(html)
        self.html_contact.Scroll(*scrollpos)
        self.html_contact.BackgroundColour = ColourManager.GetColour(wx.SYS_COLOUR_WINDOW)
        self.html_contact.Parent.Enable()
        self.html_contact.Parent.Layout()
        self.contact = contact
        if busy:
            busy.Close()


    def populate_chat_statistics(self):
        """Populates html_stats with chat statistics and word cloud."""
        stats, html = self.stc_history.GetStatisticsData(), ""
        if stats:
            data = {"db": self.db, "participants": [],
                    "chat": self.chat, "sort_by": self.stats_sort_field,
                    "stats": stats, "images": {}, "authorimages": {},
                    "imagemaps": {}, "authorimagemaps": {},
                    "expand": self.stats_expand}
            # Fill avatar images
            fs, defaultavatar = self.memoryfs, "avatar__default.png"
            if defaultavatar not in fs["files"]:
                img = images.AvatarDefault.Image
                fs["handler"].AddFile(defaultavatar, img, wx.BITMAP_TYPE_PNG)
                fs["files"][defaultavatar] = 1
            contacts = dict((c["skypename"], c) for c in self.db.get_contacts())
            partics = dict((p["identity"], p) for p in self.chat["participants"])
            # There can be authors not among participants, and vice versa
            for author in stats["authors"].union(partics):
                contact = partics.get(author, {}).get("contact")
                contact = contact or contacts.get(author, {})
                contact = contact or {"identity": author, "name": author}
                if "avatar_bitmap" in contact:
                    vals = (author, self.db.filename.encode("utf-8"))
                    fn = "%s_%s.bmp" % tuple(map(urllib.parse.quote, vals))
                    if fn not in fs["files"]:
                        bmp = contact["avatar_bitmap"]
                        fs["handler"].AddFile(fn, bmp, wx.BITMAP_TYPE_BMP)
                        fs["files"][fn] = 1
                    data["authorimages"][author] = {"avatar": fn}
                else:
                    data["authorimages"][author] = {"avatar": defaultavatar}
                data["participants"].append(contact)

            # Fill chat total histogram plot images
            PLOTCONF = {"days": (conf.PlotDaysUnitSize, conf.PlotDaysColour,
                                 max(stats["totalhist"]["days"].values())),
                        "hours": (conf.PlotHoursUnitSize, conf.PlotHoursColour,
                                  max(stats["totalhist"]["hours"].values())),
                       } if stats["hists"] else {}
            for histtype, histdata in stats["totalhist"].items():
                if histtype not in ("hours", "days"): continue # for histtype..
                vals = (self.chat["identity"], histtype,
                        self.db.filename.encode("utf-8"))
                fn = "%s_%s_%s.png" % tuple(map(urllib.parse.quote, vals))
                if fn in fs["files"]:
                    fs["handler"].RemoveFile(fn)
                bardata = sorted(histdata.items())
                img, rects = controls.BuildHistogram(bardata, *PLOTCONF[histtype])
                fs["handler"].AddFile(fn, img, wx.BITMAP_TYPE_PNG)
                fs["files"][fn] = 1
                data["images"][histtype] = fn
                areas, msgs = [], stats["totalhist"]["%s-firsts" % histtype]
                for i, (interval, val) in enumerate(bardata):
                    if interval in msgs:
                        areas.append((rects[i], "message:%s" % msgs[interval]))
                data["imagemaps"][histtype] = areas
            # Fill author histogram plot images
            for author, hists in stats["hists"].items():
                for histtype, histdata in hists.items():
                    if histtype not in ("hours", "days"): continue # for histtype..
                    vals = (author, histtype, self.chat["identity"],
                            self.db.filename.encode("utf-8"))
                    fn = "%s_%s_%s_%s.png" % tuple(map(urllib.parse.quote, vals))
                    if fn in fs["files"]:
                        fs["handler"].RemoveFile(fn)
                    bardata = sorted(histdata.items())
                    img, rects = controls.BuildHistogram(bardata, *PLOTCONF[histtype])
                    fs["handler"].AddFile(fn, img, wx.BITMAP_TYPE_PNG)
                    fs["files"][fn] = 1
                    data["authorimages"][author][histtype] = fn
                    areas, msgs = [], hists["%s-firsts" % histtype]
                    for i, (interval, val) in enumerate(bardata):
                        if interval in msgs:
                            areas.append((rects[i], "message:%s" % msgs[interval]))
                    if author not in data["authorimagemaps"]:
                        data["authorimagemaps"][author] = {}
                    data["authorimagemaps"][author][histtype] = areas
            # Fill emoticon images
            fn = "emoticon_transparent.gif"
            if fn not in fs["files"]:
                img = images.TransparentPixel.Image
                fs["handler"].AddFile(fn, img, wx.BITMAP_TYPE_GIF)
                fs["files"][fn] = 1
            for emoticon in stats["emoticons"]:
                if not hasattr(emoticons, emoticon): continue # for emoticon
                img = getattr(emoticons, emoticon)
                fn = "emoticon_%s.gif" % emoticon
                if img and fn not in fs["files"]:
                    fs["handler"].AddFile(fn, img.Image, wx.BITMAP_TYPE_GIF)
                    fs["files"][fn] = 1

            html = step.Template(templates.STATS_HTML, escape=True).expand(data)

        previous_anchor = self.html_stats.OpenedAnchor
        previous_scrollpos = getattr(self.html_stats, "_last_scroll_pos", None)
        self.html_stats.Freeze()
        self.html_stats.SetPage(html)
        self.html_stats.BackgroundColour = ColourManager.GetColour(wx.SYS_COLOUR_WINDOW)
        if previous_scrollpos:
            self.html_stats.Scroll(*previous_scrollpos)
        elif previous_anchor:
            self.html_stats.ScrollToAnchor(previous_anchor)
        self.html_stats.Thaw()


    def close_chat(self):
        """Closes the currently open chat in ChatContentSTC."""
        if not self.chat: return

        self.chat = None
        self.chat_filter = {"daterange": None, "startdaterange": None,
                            "text": "", "participants": None}
        # Update chat list colours
        for i in range(self.list_chats.ItemCount):
            if self.list_chats.GetItemMappedData(i) == self.chat:
                self.list_chats.SetItemFont(i, self.list_chats.Font)

        # Clear filter controls
        self.label_chat.Label = ""
        self.edit_filtertext.Value = ""
        self.edit_filterdate1.Value = self.edit_filterdate2.Value = None
        self.range_date.SetRange(None, None)
        self.stc_history.Populate(None, self.db)
        self.stc_history.SetFilter(self.chat_filter)
        self.stc_history.ClearAll()
        self.list_participants.ClearAll()
        self.tb_chat.ToggleTool(wx.ID_MORE, False)

        # Clear and hide timeline
        if self.list_timeline.Shown:
            self.list_timeline.Hide()
            self.list_timeline.ContainingSizer.Layout()
            self.tb_chat.ToggleTool(wx.ID_JUMP_TO, False)
        self.list_timeline.Populate([], None)

        # Clear and hide statistics
        self.html_stats.SetPage("")
        if self.html_stats.Shown:
            self.html_stats.Hide()
            self.stc_history.Show()
            self.html_stats.ContainingSizer.Layout()
            self.stc_history.ContainingSizer.Layout()
            self.tb_chat.ToggleTool(wx.ID_PROPERTIES, False)

        self.panel_chats2.Enabled = False


    def delete_chats(self, chats):
        """Asks for confirmation and deletes specified chats from database."""
        if not chats: return
        ongoings = list(filter(bool, [self.worker_live.is_working() and "live sync",
                                     self.workers_search and "search"]))
        if ongoings: return wx.MessageBox("%s is currently ongoing, cannot delete." %
                                          " and ".join(ongoings).capitalize(),
                                          conf.Title, wx.ICON_INFORMATION | wx.OK)

        msg = "Are you sure you want to delete %s %s?\n\n  %s" % (
              "these" if len(chats) > 1 else "this",
              util.plural("chat", chats, single=""),
              "\n  ".join(c["title_long"] for c in chats))
        if wx.OK != wx.MessageBox(msg, conf.Title, wx.OK | wx.CANCEL): return

        cmap = {p["contact"]["identity"]: p["contact"]
                for c in chats for p in c["participants"]
                if p["identity"] != self.db.id and p["contact"].get("id")}
        contacts = sorted(cmap.values(), key=lambda x: x["name"].lower())

        chatids = [c["id"] for c in chats]
        otherchats = [c for c in self.db.get_conversations() if c["id"] not in chatids]
        purgables = [x for x in contacts if not any(
            any(p["contact"]["identity"] == x["identity"] for p in c["participants"])
            for c in otherchats
        )]

        if purgables:
            msg = "%s will have no more messages in the database " \
                  "after deleting %s %s. Delete %s %s also?\n\n  %s" % (
                  util.plural("contact", purgables, single="This"),
                  "these" if len(chats) > 1 else "this",
                  util.plural("chat", chats, single=""),
                  "these" if len(purgables) > 1 else "the",
                  util.plural("contact", purgables, single=""),
                  "\n  ".join(x["identity"] if x["identity"] == x["name"]
                              else "%s (%s)" % (x["name"], x["identity"])
                              for x in purgables))
            resp = wx.MessageBox(msg, conf.Title, wx.YES | wx.NO | wx.CANCEL)
            if wx.CANCEL == resp: return
            elif   wx.NO == resp: del purgables[:]

        TABLES = ["Calls", "Chats", "Conversations", "MediaDocuments", "Messages",
                  "Participants", "Transfers", "Videos", "Voicemails"]
        if purgables: TABLES.extend(["Contacts", "ContactGroups"])
        openeds, changeds = [], []
        for t in TABLES:
            if t.lower() in self.db_grids:
                openeds.append(t)
                if self.db_grids[t.lower()].IsChanged(): changeds.append(t)

        if changeds and wx.OK != wx.MessageBox("There are unsaved changes "
            "in open data grids for the following tables:\n  %s\n\n"
            "Discard changes and continue?" % "\n  ".join(changeds),
            conf.Title, wx.ICON_WARNING | wx.OK | wx.CANCEL): return

        # Close query cursors, discard table grids currently not visible
        if self.grid_sql.Table: self.grid_sql.Table.Close()
        if self.grid_table.Table and self.grid_table.Table.IsChanged():
            self.grid_table.Table.UndoChanges()
        for t in openeds:
            grid = self.db_grids[t.lower()]
            grid.Close()
            if grid is not self.grid_table.Table: self.db_grids.pop(t.lower())
        self.update_tabheader()

        busy = controls.BusyPanel(self, "Deleting..")
        try:
            if self.chat in chats: self.close_chat()

            self.db.delete_conversations(chats)
            self.db.delete_contacts(purgables)

            idxs = [i for i in range(self.list_chats.GetItemCount())
                    if self.list_chats.GetItemMappedData(i) in chats]
            for idx in idxs[::-1]: self.list_chats.DeleteItem(idx)
            self.chats = [c for c in self.chats if c not in chats]

            self.on_refresh_tables()
            wx.CallAfter(self.update_info_page)
        finally: busy.Close()


    def on_sort_grid_column(self, event):
        """
        Handler for clicking a table grid column, sorts table by the column.
        """
        grid = event.GetEventObject()
        if grid.Table and isinstance(grid.Table, SqliteGridBase):
            row, col = event.GetRow(), event.GetCol()
            # Remember scroll positions, as grid update loses them
            scroll_hor = grid.GetScrollPos(wx.HORIZONTAL)
            scroll_ver = grid.GetScrollPos(wx.VERTICAL)
            if row < 0: # Only react to clicks in the header
                grid.Table.SortColumn(col)
            grid.ContainingSizer.Layout() # React to grid size change
            grid.Scroll(scroll_hor, scroll_ver)


    def on_filter_grid_column(self, event):
        """
        Handler for right-clicking a table grid column, lets the user
        change the column filter.
        """
        grid = event.GetEventObject()
        if grid.Table and isinstance(grid.Table, SqliteGridBase):
            row, col = event.GetRow(), event.GetCol()
            # Remember scroll positions, as grid update loses them
            if row < 0: # Only react to clicks in the header
                grid_data = grid.Table
                current_filter = util.to_unicode(grid_data.filters[col]) \
                                 if col in grid_data.filters else ""
                dialog = wx.TextEntryDialog(self,
                    "Filter column \"%s\" by:" % grid_data.columns[col]["name"],
                    "Filter", value=current_filter,
                    style=wx.OK | wx.CANCEL)
                if wx.ID_OK == dialog.ShowModal():
                    new_filter = dialog.GetValue()
                    if len(new_filter):
                        busy = controls.BusyPanel(self.page_tables,
                            "Filtering column \"%s\" by \"%s\"." %
                            (grid_data.columns[col]["name"], new_filter))
                        grid_data.AddFilter(col, new_filter)
                        busy.Close()
                    else:
                        grid_data.RemoveFilter(col)
            grid.ContainingSizer.Layout() # React to grid size change


    def load_data(self):
        """Loads data from our SkypeDatabase."""
        self.label_title.Label = "Database \"%s\":" % self.db

        try:
            # Restore last search text, if any
            if conf.SearchHistory and conf.SearchHistory[-1] != "":
                self.edit_searchall.Value = conf.SearchHistory[-1]
            if conf.SearchHistory and conf.SearchHistory[-1] == "":
                # Clear the empty search flag
                conf.SearchHistory = conf.SearchHistory[:-1]
            self.edit_searchall.SetChoices(conf.SearchHistory)

            # Restore last cached search results page
            last_search = conf.LastSearchResults.get(self.db.filename)
            if last_search:
                title = last_search.get("title", "")
                html = last_search.get("content", "")
                info = last_search.get("info")
                tabid = self.counter() if 0 != last_search.get("id") else 0
                self.html_searchall.InsertTab(0, title, tabid, html, info)

            # Hide rename-button if given_displayname not available
            chat_cols = self.db.get_table_columns("conversations")
            contact_cols = self.db.get_table_columns("contacts")
            if  not any(x["name"] == "given_displayname" for x in chat_cols) \
            and not any(x["name"] == "given_displayname" for x in contact_cols):
                self.button_rename.Disable(), self.button_rename.Hide()

            # Populate the chats list
            self.chats = self.db.get_conversations()
            self.list_chats.Populate(self.chats)

            # Populate the contacts list
            self.contacts = self.db.get_contacts()
            self.list_contacts.Populate(self.contacts)
            self.list_contacts.SetColumnWidth(0, 150)
            self.list_contacts.SetColumnWidth(1, 250)

            wx.CallLater(100, self.load_later_data)
        except Exception:
            wx.CallAfter(self.update_tabheader)
            guibase.status("Could not load chat list from %s.", self.db)
            logger.exception("Could not load chat list from %s.", self.db)
        wx.CallLater(500, self.update_info_page, False)
        wx.CallLater(200, self.load_tables_data)
        self.update_liveinfo()
        if conf.Login.get(self.db.filename, {}).get("auto"):
            wx.CallLater(1000, self.on_live_login, sync=conf.Login[self.db.filename].get("sync"))


    def load_later_data(self):
        """
        Loads later data from the database, like table metainformation and
        statistics for all chats, used as a background callback to speed
        up page opening.
        """
        if not self: return

        try:
            # Load chat statistics and update the chat list
            self.db.get_conversations_stats(self.chats)
            if self.chat:
                # If the user already opened a chat while later data
                # was loading, update the date range control values.
                date_range = [self.chat["first_message_datetime"].date()
                              if self.chat["first_message_datetime"] else None,
                              self.chat["last_message_datetime"].date()
                              if self.chat["last_message_datetime"] else None ]
                self.range_date.SetRange(*date_range)
                self.edit_filterdate1.Range = date_range
                self.edit_filterdate2.Range = date_range
            # Load contact statistics and update the contact list
            self.db.get_contacts_stats(self.contacts, self.chats)
            if self.contact:
                # If the user already opened a contact while later data
                # was loading, update the page
                contact = next((x for x in self.contacts
                                if x["identity"] == self.contact["identity"]), None)
                if contact: self.load_contact(contact)
            guibase.status("Opened Skype database %s.", self.db)
        except Exception as e:
            if self:
                guibase.status("Error loading additional data from %s: %s",
                               self.db, util.format_exc(e))
                logger.exception("Error loading additional data from %s.", self.db)
        if self:
            # Refresh list from loaded data, sort by last message datetime
            sortfunc = lambda l: l and (l.ResetColumnWidths(),
                                        l.SortListItems(4, 0),
                                        (l.SetColumnWidth(0, 150), l.SetColumnWidth(1, 250))
                                         if l is self.list_contacts else None)
            wx.CallLater(1, sortfunc, self.list_chats)
            wx.CallLater(1, sortfunc, self.list_contacts)
            wx.CallAfter(self.update_tabheader)


    def load_tables_data(self, reload=False):
        """
        Loads table data into table tree and SQL editor,
        reloading schema and row counts if specified.
        """
        try:
            tables = self.db.get_tables(refresh=reload)
            # Fill table tree with information on row counts and columns
            self.tree_tables.DeleteAllItems()
            root = self.tree_tables.AddRoot("SQLITE")
            child = None
            for table in tables:
                child = self.tree_tables.AppendItem(root, table["name"])
                self.tree_tables.SetItemText(child, "%d row%s" % (
                    table["rows"], "s" if table["rows"] != 1 else " "
                ), 1)
                self.tree_tables.SetItemPyData(child, table["name"])
                self.tree_tables.SetItemTextColour(child, self.tree_tables.ForegroundColour)

                for col in self.db.get_table_columns(table["name"]):
                    subchild = self.tree_tables.AppendItem(child, col["name"])
                    self.tree_tables.SetItemText(subchild, col["type"], 1)
                    self.tree_tables.SetItemTextColour(subchild, self.tree_tables.ForegroundColour)
            self.tree_tables.Expand(root)
            if child:
                # Nudge columns to fit and fill the header exactly.
                self.tree_tables.Expand(child)
                self.tree_tables.SetColumnWidth(0, -1)
                self.tree_tables.SetColumnWidth(1, min(70,
                    self.tree_tables.Size.width -
                    self.tree_tables.GetColumnWidth(0) - 5))
                self.tree_tables.Collapse(child)

            # Add table and column names to SQL editor autocomplete
            for t in tables:
                coldata = self.db.get_table_columns(t["name"])
                fields = [c["name"] for c in coldata]
                self.stc_sql.AutoCompAddSubWords(t["name"], fields)
        except Exception:
            if self:
                logger.exception("Error loading table data from %s.", self.db)


    def update_tabheader(self):
        """Updates page tab header with option to close page."""
        if self:
            self.ready_to_close = True
        if self:
            self.TopLevelParent.update_notebook_header()



class MergerPage(wx.Panel):
    """
    A wx.Notebook page for comparing two Skype databases, has its own Notebook
    with one page for diffing/merging chats, and another for contacts.
    """

    """Notes for merge buttons where note changes with data."""
    MERGE_BUTTON_NOTE = ("Scan through the left database, find messages not "
                         "present on the right, and copy them to the database "
                         "on the right.")
    MERGE_CHAT_BUTTON_NOTE = "Copy new messages to the database on the right."

    def __init__(self, parent_notebook, db1, db2, title):
        wx.Panel.__init__(self, parent=parent_notebook)
        self.pageorder = {} # {page: notebook index, }
        self.parent_notebook = parent_notebook
        self.ready_to_close = False
        self.is_merging = False # Whether merging is currently underway
        self.is_scanning = False # Whether scanning is currently underway
        self.is_scanned = False # Whether global scan has been run
        self.db1 = db1
        self.db2 = db2
        guibase.status("Opening %s and %s.", self.db1, self.db2)
        self.db1.register_consumer(self), self.db2.register_consumer(self)
        self.title = title
        parent_notebook.InsertPage(1, self, title)
        ColourManager.Manage(self, "BackgroundColour", wx.SYS_COLOUR_BTNFACE)
        busy = controls.BusyPanel(
            self, "Comparing \"%s\"\n and \"%s\"." % (db1, db2))

        self.chats1 = None        # [chats in left database]
        self.chats2 = None        # [chats in right database]
        self.chat = None          # Chat opened on chats page
        self.chat_diff = None     # Open diff {"messages": [], "participants": []}
        self.compared = None      # Chat list, left-right data in keys "c1" & "c2"
        self.con1difflist = None  # Contact and contact group differences
        self.con2difflist = None  # Contact and contact group differences
        self.con1diff = None      # Contact differences for left
        self.con2diff = None      # Contact differences for right
        self.congroup1diff = None # Contact group differences for left
        self.congroup2diff = None # Contact group differences for right
        self.chats_nodiff = {}    # {identity of unchanged chat: {chat}, }
        # {identity of changed chat: {"chat": {}, "diff": [message ID, ]}, }
        self.chats_diffdata = {}

        self.contacts_list_columns = [
            ("identity", "Account"), ("name", "Name"),
            ("phone_mobile_normalized", "Mobile phone"),
            ("country", "Country"), ("city", "City"), ("about", "About"),
            ("__type", "Type"), ]
        self.chats_list_columns = [
            ("title", "Chat"), ("messages1", "Messages in left"),
            ("messages2", "Messages in right"),
            ("last_message_datetime1", "Last message in left"),
            ("last_message_datetime2", "Last message in right"),
            ("type_name", "Type"), ("people", "People"), ]
        self.Bind(EVT_WORKER, self.on_worker_merge_result)
        self.worker_merge = workers.MergeThread(self.on_worker_merge_callback)
        self.worker_import = workers.SkypeArchiveThread(self.on_worker_import_callback)

        sizer = self.Sizer = wx.BoxSizer(wx.VERTICAL)

        sizer_header = wx.BoxSizer(wx.HORIZONTAL)
        label = self.html_dblabel = wx.html.HtmlWindow(parent=self,
            size=(-1, 36), style=wx.html.HW_SCROLLBAR_NEVER)
        label.SetFonts(normal_face=self.Font.FaceName,
                       fixed_face=self.Font.FaceName, sizes=[8] * 7)
        self.Bind(wx.html.EVT_HTML_LINK_CLICKED, self.on_link_db, label)
        button_swap = self.button_swap = \
            wx.Button(parent=self, label="S&wap left-right")
        button_swap.Enabled = False
        button_swap.SetToolTip("Swaps left and right database, "
                               "changing merge direction.")
        self.Bind(wx.EVT_BUTTON, self.on_swap, button_swap)
        sizer_header.Add(label, border=5, proportion=1,
                         flag=wx.GROW | wx.TOP | wx.BOTTOM)
        sizer_header.Add(button_swap, border=5, flag=wx.LEFT | wx.RIGHT | 
                         wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(sizer_header, flag=wx.GROW)
        sizer.Layout() # To avoid header moving around during page creation

        notebook = self.notebook = wx.lib.agw.labelbook.FlatImageBook(
            parent=self, agwStyle=wx.lib.agw.fmresources.INB_LEFT, style=wx.BORDER_STATIC)
        sizer.Add(notebook, proportion=10, border=5,
                  flag=wx.GROW | wx.LEFT | wx.RIGHT | wx.BOTTOM)

        il = wx.ImageList(32, 32)
        idx1 = il.Add(images.PageMergeAll.Bitmap)
        idx2 = il.Add(images.PageMergeChats.Bitmap)
        idx3 = il.Add(images.PageMergeContacts.Bitmap)
        notebook.AssignImageList(il)

        self.create_page_merge_all(notebook)
        self.create_page_merge_chats(notebook)
        self.create_page_merge_contacts(notebook)

        notebook.SetPageImage(0, idx1)
        notebook.SetPageImage(1, idx2)
        notebook.SetPageImage(2, idx3)

        self.TopLevelParent.page_merge_latest = self
        self.TopLevelParent.run_console(
            "page12 = self.page_merge_latest # Merger tab")
        self.TopLevelParent.run_console(
            "db1, db2 = page12.db1, page12.db2 # Chosen databases")

        self.Layout()
        self.load_data()
        # Hack to get scrolled panels lay out properly
        notebook.SetSelection(1)
        self.page_merge_chats.Layout()
        notebook.SetSelection(2)
        self.page_merge_contacts.Layout()
        notebook.SetSelection(0)
        busy.Close()


    def create_page_merge_all(self, notebook):
        """Creates a page for merging all chats at once."""
        page = self.page_merge_all = wx.lib.scrolledpanel.ScrolledPanel(notebook)
        self.pageorder[page] = len(self.pageorder)
        notebook.AddPage(page, "Merge all")

        panel = wx.Panel(page, style=wx.BORDER_STATIC)
        label1 = self.label_all1 = wx.StaticText(panel, style=wx.ALIGN_RIGHT,
            label="%s\n\nAnalyzing..%s" % (self.db1, "\n" * 7))
        bmp_arrow = wx.StaticBitmap(panel, bitmap=images.MergeToRight.Bitmap)
        label2 = self.label_all2 = wx.StaticText(panel,
            label="%s\n\nAnalyzing..%s" % (self.db2, "\n" * 7))
        button_scan = self.button_scan_all = controls.NoteButton(panel,
            label="&Scan and report", note="Scan through the left database "
            "and find messages not present on the right.",
            bmp=images.ButtonScanDiff.Bitmap)
        button_merge = self.button_merge_all = controls.NoteButton(panel,
            label="&Merge to the right", note=self.MERGE_BUTTON_NOTE,
            bmp=images.ButtonMergeLeftMulti.Bitmap)
        panel_gauge = self.panel_gauge = wx.Panel(panel)
        label_gauge = self.label_gauge = wx.StaticText(panel_gauge, label="")
        gauge = self.gauge_progress = wx.Gauge(panel_gauge, size=(400, 15),
                                      style=wx.GA_HORIZONTAL | wx.PD_SMOOTH)
        html = self.html_report = \
            controls.ScrollingHtmlWindow(panel, style=wx.BORDER_SUNKEN)

        for c in [panel, button_scan, button_merge, panel_gauge]:
            ColourManager.Manage(c, "BackgroundColour", "BgColour")
        gauge.ForegroundColour = conf.GaugeColour
        button_scan.Enabled = button_merge.Enabled = False
        button_scan.MinSize = button_merge.MinSize = (400, -1)
        html.SetFonts(normal_face=self.Font.FaceName,
                      fixed_face=self.Font.FaceName, sizes=[8] * 7)
        ColourManager.Manage(html, "ForegroundColour", "FgColour")
        ColourManager.Manage(html, "BackgroundColour", "MergeHtmlBackgroundColour")
        html.Hide()
        panel_gauge.Hide()

        page.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer = panel.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_top = wx.GridBagSizer(vgap=5, hgap=30)
        panel_gauge.Sizer = wx.BoxSizer(wx.VERTICAL)

        page.Sizer.Add(panel, proportion=1, border=5, flag=wx.GROW | wx.LEFT)
        sizer_top.Add(label1, flag=wx.ALIGN_RIGHT, pos=(0, 0))
        sizer_top.Add(bmp_arrow, flag=wx.ALIGN_CENTER, pos=(0, 1))
        sizer_top.Add(label2, pos=(0, 2))
        sizer_top.Add(button_scan, border=25, flag=wx.TOP | wx.GROW, pos=(1, 1), span=(1, 2))
        sizer_top.Add(button_merge, flag=wx.GROW, pos=(2, 1), span=(1, 2))
        panel_gauge.Sizer.Add(label_gauge, flag=wx.ALIGN_CENTER)
        panel_gauge.Sizer.Add(gauge, flag=wx.ALIGN_CENTER)
        sizer.Add(sizer_top, border=10, flag=wx.ALL | wx.ALIGN_CENTER)
        sizer.Add(panel_gauge, border=10, flag=wx.ALL | wx.GROW)
        sizer.Add(html, proportion=1, border=30, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.GROW)
        sizer_top.AddGrowableCol(0)
        sizer_top.AddGrowableCol(2)
        page.SetupScrolling()

        button_scan.Bind(wx.EVT_BUTTON, self.on_scan_all)
        button_merge.Bind(wx.EVT_BUTTON, self.on_merge_all)
        html.Bind(wx.html.EVT_HTML_LINK_CLICKED, self.on_click_htmldiff)


    def create_page_merge_chats(self, notebook):
        """Creates a page for seeing and merging differing chats."""
        page = self.page_merge_chats = wx.Panel(parent=notebook)
        self.pageorder[page] = len(self.pageorder)
        notebook.AddPage(page, "Chats")
        sizer = page.Sizer = wx.BoxSizer(wx.VERTICAL)
        splitter = self.splitter_merge = wx.SplitterWindow(
            parent=page, style=wx.BORDER_NONE
        )
        splitter.SetMinimumPaneSize(100)
        panel1 = wx.Panel(parent=splitter)
        panel2 = wx.Panel(parent=splitter)
        sizer1 = panel1.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer2 = panel2.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_top = wx.BoxSizer(wx.HORIZONTAL)

        sizer_top.Add(wx.StaticText(parent=panel1, label="&Chat comparison:",
                      name="chats_label"), flag=wx.ALIGN_CENTER_VERTICAL)
        sizer_top.AddStretchSpacer()
        edit_chatfilter = self.edit_chatfilter = controls.HintedTextCtrl(
            panel1, "Filter chats", style=wx.TE_PROCESS_ENTER, size=(75, -1))
        edit_chatfilter.SetToolTip("Filter items in chat list")
        self.Bind(wx.EVT_TEXT_ENTER, self.on_change_chatfilter, edit_chatfilter)
        sizer_top.Add(edit_chatfilter, flag=wx.BOTTOM | wx.ALIGN_TOP, border=5)
        sizer_top.AddSpacer(20)
        self.button_merge_chats = wx.Button(panel1, label="Merge &selected")
        chats_tooltip = "Merge differences in selected chats to the right"
        self.button_merge_chats.SetToolTip(chats_tooltip)
        self.button_merge_chats.Enabled = False
        sizer_top.Add(self.button_merge_chats, flag=wx.ALIGN_TOP | wx.BOTTOM,
                      border=5)
        self.Bind(wx.EVT_BUTTON, self.on_merge_chats, self.button_merge_chats)
        sizer1.Add(sizer_top, flag=wx.GROW)

        list_chats = self.list_chats = controls.SortableListView(
            parent=panel1, style=wx.LC_REPORT, name="chats")
        list_chats.SetColumns(self.chats_list_columns)
        list_chats.SetColumnsMaxWidth(300)
        list_chats.SortListItems(3, 0) # Sort by last message in left
        list_chats.Enabled = False
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_change_list_chats,
                  list_chats)
        sizer1.Add(list_chats, proportion=1, flag=wx.GROW)

        label_chat = self.label_merge_chat = \
            wx.StaticText(parent=panel2, label="")
        splitter_diff = self.splitter_diff = wx.SplitterWindow(
            parent=panel2, style=wx.BORDER_NONE)
        splitter_diff.SetMinimumPaneSize(350)
        panel_stc1 = self.panel_stc1 = wx.Panel(parent=splitter_diff)
        panel_stc2 = self.panel_stc2 = wx.lib.scrolledpanel.ScrolledPanel(splitter_diff)
        ColourManager.Manage(panel_stc2, "BackgroundColour", "BgColour")
        sizer_stc1 = panel_stc1.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_stc2 = panel_stc2.Sizer = wx.BoxSizer(wx.VERTICAL)

        stc1 = self.stc_diff1 = ChatContentSTC(
            parent=panel_stc1, style=wx.BORDER_STATIC)
        stc1.SetAutoRetrieve(False)
        stc1.TEXT_NO_MESSAGES = "\nNo new messages to show."

        button_merge = self.button_merge_chat = controls.NoteButton(
            panel_stc2, label="&Merge to the right",
            note=self.MERGE_CHAT_BUTTON_NOTE, bmp=images.ButtonMergeLeft.Bitmap)
        button_export = self.button_export_chat = controls.NoteButton(
            panel_stc2, label="&Export messages",
            note="Export detected messages as HTML, text or spreadsheet.",
            bmp=images.ButtonExport.Bitmap)
        button_merge.Bind(wx.EVT_BUTTON, self.on_merge_chat)
        button_export.Bind(wx.EVT_BUTTON, self.on_export_chat)
        ColourManager.Manage(button_merge,  "BackgroundColour", "BgColour")
        ColourManager.Manage(button_export, "BackgroundColour", "BgColour")
        button_merge.Enabled = button_export.Enabled = False

        sizer_stc1.Add(stc1, proportion=1, flag=wx.GROW)
        sizer_stc2.AddStretchSpacer()
        sizer_stc2.Add(button_merge, border=5,  flag=wx.ALL | wx.GROW)
        sizer_stc2.Add(button_export, border=5, flag=wx.ALL | wx.GROW)
        sizer_stc2.AddStretchSpacer()
        sizer2.Add(label_chat, border=5, flag=wx.ALL)
        sizer2.Add(splitter_diff, proportion=1, flag=wx.GROW)

        sizer.AddSpacer(5)
        sizer.Add(splitter, border=5, proportion=1, flag=wx.GROW | wx.ALL)
        splitter_diff.SetSashGravity(0.5)
        splitter_diff.SplitVertically(panel_stc1, panel_stc2,
                                      sashPosition=self.Size.width)
        splitter.SplitHorizontally(panel1, panel2,
                                   sashPosition=self.Size.height // 3)
        panel_stc2.SetupScrolling(scroll_x=False)


    def create_page_merge_contacts(self, notebook):
        """Creates a page for seeing and merging differing contacts."""
        page = self.page_merge_contacts = wx.Panel(parent=notebook)
        self.pageorder[page] = len(self.pageorder)
        notebook.AddPage(page, "Contacts")
        sizer = page.Sizer = wx.BoxSizer(wx.VERTICAL)

        splitter = self.splitter_contacts = wx.SplitterWindow(
            parent=page, style=wx.BORDER_NONE
        )
        splitter.SetMinimumPaneSize(350)
        panel1 = wx.Panel(parent=splitter)
        panel2 = wx.lib.scrolledpanel.ScrolledPanel(splitter)
        ColourManager.Manage(panel2, "BackgroundColour", "BgColour")
        sizer1 = panel1.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer2 = panel2.Sizer = wx.BoxSizer(wx.VERTICAL)

        sizer_top = wx.BoxSizer(wx.HORIZONTAL)
        lbl = wx.StaticText(parent=panel1, label="New &contacts on the left:",
                            name="contact_list_label")
        sizer_top.Add(lbl, flag=wx.ALIGN_CENTER_VERTICAL)
        sizer_top.AddStretchSpacer()
        edit_contactfilter = self.edit_contactfilter = controls.HintedTextCtrl(
            panel1, "Filter contacts", style=wx.TE_PROCESS_ENTER, size=(90, -1))
        edit_contactfilter.SetToolTip("Filter items in contact lists")
        self.Bind(wx.EVT_TEXT_ENTER, self.on_change_contactfilter,
                  edit_contactfilter)
        sizer_top.Add(edit_contactfilter)

        list1 = self.list_contacts = controls.SortableListView(
            parent=panel1,  style=wx.LC_REPORT, name="contact_list")
        list1.SetColumns(self.contacts_list_columns)
        list1.SetColumnsMaxWidth(300)
        list1.Bind(wx.EVT_LIST_ITEM_SELECTED,   self.on_select_list_contacts)
        list1.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.on_select_list_contacts)
        list1.Bind(wx.EVT_LIST_ITEM_ACTIVATED,  self.on_merge_contacts)

        button1 = self.button_merge_contacts = controls.NoteButton(
            panel2, label="&Merge selected to the right",
            note="Copy selected contacts to the database on the right.",
            bmp=images.ButtonMergeLeft.Bitmap)
        button_all1 = self.button_merge_allcontacts = controls.NoteButton(
            panel2, label="Merge &all to the right",
            note="Copy all contacts to the database on the right.",
            bmp=images.ButtonMergeLeftMulti.Bitmap)
        ColourManager.Manage(button1,     "BackgroundColour", "BgColour")
        ColourManager.Manage(button_all1, "BackgroundColour", "BgColour")
        button1.Bind(wx.EVT_BUTTON, self.on_merge_contacts)
        button_all1.Bind(wx.EVT_BUTTON, self.on_merge_contacts)
        button1.Enabled = button_all1.Enabled = False
        sizer1.Add(sizer_top, flag=wx.GROW | wx.BOTTOM | wx.RIGHT, border=5)
        sizer1.Add(list1, proportion=1, flag=wx.GROW | wx.BOTTOM | wx.RIGHT,
                   border=5)
        sizer2.AddStretchSpacer()
        sizer2.Add(button1,     flag=wx.ALL | wx.GROW, border=5)
        sizer2.Add(button_all1, flag=wx.ALL | wx.GROW, border=5)
        sizer2.AddStretchSpacer()

        splitter.SplitVertically(panel1, panel2, sashPosition=self.Size.width)

        sizer.AddSpacer(10)
        sizer.Add(splitter, proportion=1, border=5,
                  flag=wx.GROW | wx.LEFT | wx.RIGHT)
        panel2.SetupScrolling(scroll_x=False)


    def on_export_chat(self, event):
        """
        Handler for clicking to export a chat diff, displays a save file dialog
        and saves the current messages to file.
        """
        formatargs = collections.defaultdict(str); formatargs.update(self.chat)
        default = "Diff of %s" % conf.ExportChatTemplate % formatargs
        dialog = wx.FileDialog(parent=self, message="Save new messages",
            defaultFile=util.safe_filename(default),
            style=wx.FD_OVERWRITE_PROMPT | wx.FD_SAVE | wx.RESIZE_BORDER
        )
        dialog.Wildcard = export.CHAT_WILDCARD
        if wx.ID_OK != dialog.ShowModal(): return

        filepath = controls.get_dialog_path(dialog)
        format = export.CHAT_EXTS[dialog.FilterIndex]
        media_folder = "html" == format and dialog.FilterIndex
        if media_folder and not check_media_export_login(self.db): return

        busy = controls.BusyPanel(self, 'Exporting "%s".' % self.chat["title"])
        guibase.status("Exporting to %s.", filepath, log=True)
        try:
            messages = self.db1.message_iterator(self.chat_diff["messages"])
            opts = dict(messages=messages, progress=lambda *args: wx.SafeYield())
            if media_folder: opts["media_folder"] = True
            result = export.export_chats([self.chat], filepath, format, self.db1, opts)
            files, count, message_count = result
            guibase.status("Exported %s to %s.",
                           util.plural("message", message_count, sep=","),
                           filepath, log=True)
            util.start_file(filepath)
        except Exception:
            guibase.status("Error saving %s.", filepath)
            logger.exception("Error saving %s.", filepath)
            errormsg = "Error saving %s:\n\n%s" % \
                       (filepath, traceback.format_exc())
            wx.MessageBox(errormsg, conf.Title, wx.OK | wx.ICON_WARNING)
        finally:
            busy.Close()


    def on_click_htmldiff(self, event):
        """
        Handler for clicking a chat link in diff overview, opens the chat
        comparison in Chats page.
        """
        href = event.GetLinkInfo().Href
        chat = None
        for c in self.compared:
            if c["identity"] == href:
                chat = c
                break # for c
        if chat and self.page_merge_chats.Enabled:
            self.on_change_list_chats(chat=chat)
            self.notebook.SetSelection(self.pageorder[self.page_merge_chats])


    def on_worker_merge_result(self, event):
        """Handler for worker_merge result callback, updates UI and texts."""
        if not self: return
        if event.result.get("type") in ["merge_left", "diff_merge_left"]:
            self.on_merge_all_result(event)
        elif "diff_left" == event.result.get("type"):
            self.on_scan_all_result(event)


    def on_worker_merge_callback(self, result):
        """Callback function for MergeThread, posts the data to self."""
        if self: wx.PostEvent(self, WorkerEvent(result=result))


    def on_worker_import_callback(self, result):
        """Callback function for SkypeArchiveThread, updates UI."""
        if not self: return

        def after(result):
            if not self: return

            if "counts" in result:

                t = ", ".join(util.plural(x[:-1], result["counts"][x], sep=",")
                              for x in sorted(result["counts"]))
                self.label_gauge.Label = "Parsed %s." % t
                self.panel_gauge.Layout()

            elif "error" in result:
                self.html_report.AppendToPage("<br /><br /> <b>Error parsing Skype export:</b>&nbsp;&nbsp;"
                                              + result["error_short"].replace("<", "&lt;"))
                self.html_report.Scroll(0, self.html_report.GetScrollRange(wx.VERTICAL))
                self.gauge_progress.Value = 0
                self.panel_gauge.Hide()
                self.page_merge_all.Layout()
            elif "done" in result:
                stats = self.db1.get_general_statistics()
                text = "<br /><br />Parsed %s, %s and %s." % tuple(
                    util.plural(x[:-1], stats[x], sep=",") for x in ("chats", "contacts", "messages")
                )
                self.html_report.AppendToPage(text)
                scrollpos = self.html_report.GetScrollRange(wx.VERTICAL)
                self.html_report.Scroll(0, scrollpos)
                self.gauge_progress.Value = 100
                self.panel_gauge.Hide()
                self.load_data()

        wx.CallAfter(after, result)


    def on_swap(self, event):
        """
        Handler for clicking to swap left and right databases, changes data
        structures and UI content.
        """
        self.db1, self.db2 = self.db2, self.db1
        namespace = {"db1": self.db1, "db2": self.db2}
        template = step.Template(templates.MERGE_DB_LINKS, escape=True)
        self.html_dblabel.SetPage(template.expand(namespace))
        self.html_dblabel.BackgroundColour = wx.NullColour
        self.con1diff, self.con2diff = self.con2diff, self.con1diff
        self.con1difflist, self.con2difflist = \
            self.con2difflist, self.con1difflist
        self.congroup1diff, self.congroup2diff = \
            self.congroup1diff, self.congroup2diff
        self.chats1, self.chats2 = self.chats2, self.chats1
        self.chats_diffdata.clear()
        self.chats_nodiff.clear()
        self.chat = None
        self.chat_diff = None
        self.is_scanned = False 

        for a, b in [(self.label_all1, self.label_all2)]:
            a.Label, b.Label = b.Label, a.Label

        self.label_merge_chat.Label = ""
        self.stc_diff1.ClearAll()
        self.button_merge_chat.Enabled = False
        self.button_export_chat.Enabled = False
        self.button_merge_chat.Note = self.MERGE_CHAT_BUTTON_NOTE

        # Swap left and right in data structures.
        for lst in [self.compared, self.con1diff, self.con2diff,
                    self.congroup1diff, self.congroup2diff]:
            for item in lst or []:
                for t in ["c", "messages", "g"]:
                    key1, key2 = "%s1" % t, "%s2" % t
                    if key1 in item and key2 in item:
                        item[key1], item[key2] = item[key2], item[key1]

        # Repopulate chat and contact lists
        self.list_contacts.Populate(self.con1difflist or [])
        self.list_chats.Populate(self.compared or [])

        # Update button states
        self.button_scan_all.Enabled = self.button_merge_all.Enabled = True
        self.button_merge_all.Note = self.MERGE_BUTTON_NOTE
        self.button_merge_contacts.Enabled = False
        self.button_merge_allcontacts.Enabled = self.list_contacts.ItemCount

        self.panel_gauge.Hide()
        self.html_report.Hide()

        self.Refresh()
        self.page_merge_all.Layout()
        self.Layout()


    def on_merge_chats(self, event):
        """Handler on choosing to merge the chats selected in chat list."""
        selected, selecteds = self.list_chats.GetFirstSelected(), []
        while selected >= 0:
            selecteds.append(self.list_chats.GetItemMappedData(selected)["c1"])
            selected = self.list_chats.GetNextSelected(selected)
        if selecteds:
            action = "Merge" if self.is_scanned else "Scan and merge"
            info = util.plural("selected chat", selecteds, sep=",")
            message = ("%s differences in %s\n\nfrom %s\n\ninto %s?" %
                       (action, info, self.db1, self.db2))
            if wx.OK == wx.MessageBox(message, conf.Title,
            wx.ICON_INFORMATION | wx.CANCEL):
                self.button_swap.Enabled = False
                self.button_merge_chats.Enabled = False
                self.button_scan_all.Enabled = False
                self.button_merge_all.Enabled = False
                self.page_merge_chats.Enabled = False
                self.page_merge_contacts.Enabled = False
                self.update_gauge(self.gauge_progress, 0,
                                  "%s 0%% complete." % action)
                if not self.html_report.Shown:
                    self.html_report.Show()
                    self.html_report.ContainingSizer.Layout()
                self.html_report.SetPage("<body bgcolor='%s'><font color='%s'><b>%s progress:"
                    "</b><br />" % (conf.MergeHtmlBackgroundColour, conf.FgColour, action))
                db1, db2 = self.db1, self.db2
                chats = list(filter(bool, selecteds))
                if self.is_scanned:
                    type = "merge_left"
                    cc = [self.chats_diffdata.get(c["identity"]) for c in chats]
                    chats = list(filter(bool, cc))
                else:
                    type = "diff_merge_left"
                params = locals()
                self.worker_merge.work(params)
                self.is_merging = True
                guibase.status("Merging %s from %s to %s.", info, db1, db2, log=True)
                self.notebook.SetSelection(0)


    def on_link_db(self, event):
        """Handler on clicking a database link, opens the database tab."""
        self.TopLevelParent.load_database_page(event.GetLinkInfo().Href)


    def on_select_list_contacts(self, event):
        """
        Handler for changing selection in contacts list, updates button states.
        """
        self.button_merge_contacts.Enabled = bool(self.list_contacts.SelectedItemCount)
        self.button_merge_contacts.Refresh()


    def on_click_link(self, event):
        """
        Handler for clicking a link in chat history, opens the link in system
        browser.
        """
        stc = event.EventObject
        if stc.GetStyleAt(event.Position) == self.stc_styles["link"]:
            # Go back and forth from position and get URL range.
            url_range = {-1: -1, 1: -1} # { start and end positions }
            for step in url_range:
                pos = event.Position
                while stc.GetStyleAt(pos + step) == self.stc_styles["link"]:
                    pos += step
                url_range[step] = pos
            url = stc.GetTextRange(url_range[-1], url_range[1] + 1)
            webbrowser.open(url)


    def on_change_chatfilter(self, event):
        """Handler for changing text in chat filter box, filters chat list."""
        self.list_chats.SetFilter(event.String.strip())


    def on_change_contactfilter(self, event):
        """
        Handler for changing text in chat filter box, filters contact lists.
        """
        self.list_contacts.SetFilter(event.String.strip())
        self.button_merge_contacts.Enabled = self.list_contacts.SelectedItemCount
        self.button_merge_allcontacts.Enabled = self.list_contacts.ItemCount


    def on_change_list_chats(self, event=None, chat=None):
        """
        Handler for activating an item in the differing chats list,
        goes through all messages of the chat in both databases and shows
        those messages that are missing or different, for both left and
        right.
        """
        c = chat or self.list_chats.GetItemMappedData(event.Index)
        if not self.chat or c["identity"] != self.chat["identity"]:
            self.label_merge_chat.Label = "New in %s:" \
                % c["title_long_lc"]
            logger.info("Comparing %s (%s vs %s).", c["title_long_lc"],
                        self.db1, self.db2)
            scrollpos = self.list_chats.GetScrollPos(wx.VERTICAL)
            index_selected = -1
            # Update item background in chats list
            for i in range(self.list_chats.ItemCount):
                if self.list_chats.GetItemMappedData(i) == self.chat:
                    self.list_chats.SetItemFont(i, self.list_chats.Font)
                elif self.list_chats.GetItemMappedData(i) == c:
                    index_selected = i
                    f = self.list_chats.Font; f.SetWeight(wx.FONTWEIGHT_BOLD)
                    self.list_chats.SetItemFont(i, f)
            if index_selected >= 0:
                delta = index_selected - scrollpos
                if delta < 0 or abs(delta) >= self.list_chats.CountPerPage:
                    nudge = -self.list_chats.CountPerPage // 2
                    self.list_chats.ScrollLines(delta + nudge)
            busy = controls.BusyPanel(
                self, "Diffing messages for %s." % c["title_long_lc"])

            try:
                diff = {"messages": [], "participants": []}
                data = self.chats_diffdata.get(c["identity"])
                if data:
                    diff = data["diff"] # Use cached diff if available
                elif not self.is_scanned \
                and c["identity"] not in self.chats_nodiff:
                    diff = self.worker_merge.get_chat_diff_left(c, self.db1,
                                                                self.db2)
                    data = {"chat": c, "diff": diff}
                    if any(diff.values()): # Cache new diff
                        self.chats_diffdata[c["identity"]] = data
                    else:
                        self.chats_nodiff[c["identity"]] = c
                elif c["identity"] not in self.chats_nodiff:
                    data = {"chat": c, "diff": diff}
                    self.chats_nodiff[c["identity"]] = data
                messages = list(self.db1.message_iterator(diff["messages"]))
                self.chat = c
                self.chat_diff = diff
                self.button_merge_chat.Enabled = len(messages)
                self.button_merge_chat.Note = self.MERGE_CHAT_BUTTON_NOTE
                self.button_export_chat.Enabled = len(messages)
                if messages:
                    self.button_merge_chat.Note = (
                        "Copy %s to the database on the right." % 
                        util.plural("chat message", messages, sep=","))
                    self.button_merge_chat.ContainingSizer.Layout()
                idx = -conf.MaxHistoryInitialMessages
                self.stc_diff1.Populate(c, self.db1, messages, from_index=idx)
                textlength = self.stc_diff1.TextLength
                self.stc_diff1.SetSelection(textlength, textlength)
            finally:
                busy.Close()


    def on_merge_contacts(self, event):
        """
        Handler for clicking to merge contacts from one database to the other,
        either selected or all contacts, depending on button clicked.
        """
        db_target, db_source = self.db2, self.db1
        list_source = self.list_contacts
        source = 0
        contacts, contactgroups, indices = [], [], []
        if event.Id == self.button_merge_allcontacts.Id:
            for i in range(list_source.ItemCount):
                data = list_source.GetItemMappedData(i)
                if "Contact" == data["__type"]:
                    contacts.append(data["__data"])
                else:
                    contactgroups.append(data["__data"])
                indices.append(i)
        else:
            selected = list_source.GetFirstSelected()
            while selected >= 0:
                data = list_source.GetItemMappedData(selected)
                if "Contact" == data["__type"]:
                    contacts.append(data["__data"])
                else:
                    contactgroups.append(data["__data"])
                indices.append(selected)
                selected = list_source.GetNextSelected(selected)
        # Contacts and contact groups are shown in the same list. If a contact
        # group is chosen, it can include contacts not yet in target database.
        contacts_target_final = dict([(c["identity"], c) for c in contacts])
        contacts_target_final.update(dict((c["identity"], c) 
                                          for c in db_target.get_contacts()))
        contacts_source = dict((c['identity'], c)
                               for c in db_source.get_contacts())
        for group in contactgroups:
            members = set(group["members"].split(" "))
            for new in members.difference(contacts_target_final):
                contacts.append(contacts_source[new])
        text_add = ""
        if contacts:
            text_add += util.plural("contact", contacts, sep=",")
        if contactgroups:
            text_add += (" and " if contacts else "") \
                       + util.plural("contact group", contactgroups, sep=",")
        if (contacts or contactgroups) and wx.OK == wx.MessageBox(
                "Copy %s\n\nfrom %s\n\ninto %s?" %
                (text_add, self.db1, self.db2),
                conf.Title, wx.OK | wx.CANCEL | wx.ICON_INFORMATION):
            self.is_merging = True
            try:
                if contacts:
                    db_target.insert_contacts(contacts, db_source)
                if contactgroups:
                    db_target.replace_contactgroups(contactgroups, db_source)
            finally:
                self.is_merging = False
            for i in sorted(indices)[::-1]:
                list_source.DeleteItem(i)
            condiff = [self.con1diff, self.con2diff][source]
            cgdiff = [self.congroup1diff, self.congroup1diff][source]
            difflist = [self.con1difflist, self.con1difflist][source]
            for c in [contacts, contactgroups]:
                [l.remove(c) for l in [condiff, cgdiff, difflist] if c in l]
            db_target.clear_cache()
            self.button_merge_contacts.Enabled = False
            self.button_merge_allcontacts.Enabled = list_source.ItemCount
            logger.info("Copied %s from %s into %s.", text_add, self.db1, self.db2)
            wx.MessageBox("Copied %s\n\nfrom %s\n\ninto %s." % (text_add,
                self.db1, self.db2), conf.Title, wx.OK | wx.ICON_INFORMATION)


    def on_scan_all(self, event):
        """
        Handler for clicking to scan for differences with the left database,
        starts scanning process.
        """
        guibase.status("Scanning differences between %s and %s.",
                       self.db1, self.db2, log=True)
        self.chats_diffdata.clear()
        self.button_merge_all.Enabled = False
        self.button_scan_all.Enabled = False
        self.button_swap.Enabled = False
        self.button_merge_chats.Enabled = False
        if not self.html_report.Shown:
            self.html_report.Show()
            self.html_report.ContainingSizer.Layout()
        html = ("<body bgcolor='%s'><font color='%s'><b>Scan results:</b>"
                "<br /><br />" %
                (conf.MergeHtmlBackgroundColour, conf.FgColour))
        self.html_report.SetPage(html)
        self.update_gauge(self.gauge_progress, 0, "Scanning messages.")
        params = {"db1": self.db1, "db2": self.db2, "type": "diff_left"}
        self.worker_merge.work(params)
        self.is_scanning = True


    def on_scan_all_result(self, event):
        """
        Handler for getting diff results from worker thread, adds the results
        to the diff windows.
        """
        result = event.result
        for d in result.get("chats", []):
            self.chats_diffdata[d["chat"]["identity"]] = d
        if result.get("output") and "done" not in result:
            self.html_report.AppendToPage(result["output"])
        if "status" in result:
            guibase.status(result["status"])
        if "index" in result:
            mindex, mcount = result["index"], result["count"]
            cindex, ccount = result["chatindex"], result["chatcount"]
            percent = min(100, math.ceil(100 * util.safedivf(mindex, mcount)))
            if percent == 100 and mindex < mcount: percent = 99
            msg = "Scan %d%% complete (%s of %s)." % \
                  (percent, cindex + 1, util.plural("conversation", ccount, sep=","))
            self.update_gauge(self.gauge_progress, percent, msg)
        if "done" in result:
            self.is_scanning = False
            self.is_scanned = True
            s1 = util.plural("differing chat", self.chats_diffdata)
            guibase.status("Found %s in %s.", s1, self.db1, log=True)
            self.button_swap.Enabled = True
            self.button_merge_chats.Enabled = True
            if self.chats_diffdata:
                count_msgs = util.plural(
                    "message", sum(len(d["diff"]["messages"])
                                   for d in self.chats_diffdata.values()), sep=",")
                count_chats = util.plural("chat", self.chats_diffdata, sep=",")
                noteinfo = "%s from %s" % (count_msgs, count_chats)
                self.button_merge_all.Note = (
                    "Copy %s to the database on the right." % noteinfo)
                self.button_merge_all.Enabled = True
                self.html_report.Freeze()
                self.html_report.AppendToPage(
                    "<br /><br />New in %s: %s in %s." % 
                    (self.db1, count_msgs, count_chats))
                scrollpos = self.html_report.GetScrollRange(wx.VERTICAL)
                self.html_report.Scroll(0, scrollpos)
                self.html_report.Thaw()
            else:
                self.html_report.SetPage("<body bgcolor='%s'><font color='%s'>"
                    "No new messages.</font></body>" % 
                    (conf.MergeHtmlBackgroundColour, conf.FgColour))
            self.update_gauge(self.gauge_progress, 100, "Scan complete.")
            wx.Bell()


    def on_merge_all(self, event):
        """
        Handler for clicking to copy all the differences to the other
        database, asks for final confirmation and executes.
        """
        db1, db2 = self.db1, self.db2
        if self.is_scanned:
            count_msgs = util.plural(
                "message", sum(len(d["diff"]["messages"])
                               for d in self.chats_diffdata.values()), sep=",")
            count_chats = util.plural("chat", self.chats_diffdata, sep=",")
            info = "%s in %s" % (count_msgs, count_chats)
            message = "Copy %s\n\nfrom %s\n\ninto %s?" % (info, db1, db2)
            type = "merge_left"
            chats = list(self.chats_diffdata.values())
        else:
            info = "any differences"
            message = ("Scan and merge chat differences\n\nfrom %s\n\ninto %s?"
                       % (db1, db2))
            type = "diff_merge_left"
        response = wx.MessageBox(message, conf.Title,
                                 wx.OK | wx.CANCEL | wx.ICON_INFORMATION)
        if wx.OK == response:
            self.update_gauge(self.gauge_progress, 0, "Merge 0% complete.")
            self.button_swap.Enabled = False
            self.button_merge_chats.Enabled = False
            self.button_scan_all.Enabled = self.button_merge_all.Enabled = False
            if not self.html_report.Shown:
                self.html_report.Show()
                self.html_report.ContainingSizer.Layout()
            self.html_report.SetPage("<body bgcolor='%s'><font color='%s'><b>Merge progress:"
                "</b><br />" % (conf.MergeHtmlBackgroundColour, conf.FgColour))
            self.page_merge_chats.Enabled = False
            self.page_merge_contacts.Enabled = False
            guibase.status("Merging %s from %s to %s.", info, db1, db2, log=True)
            params = locals()
            self.worker_merge.work(params)
            self.is_merging = True


    def on_merge_all_result(self, event):
        """
        Handler for getting merge results from worker thread, refreshes texts
        and UI controls.
        """
        result = event.result
        action = ("Merge" if "merge_left" == result["type"]
                  else "Scan and merge")
        if "index" in result:
            mindex, mcount = result["index"], result["count"]
            cindex, ccount = result["chatindex"], result["chatcount"]
            percent = min(100, math.ceil(100 * util.safedivf(mindex, mcount)))
            if percent == 100 and mindex < mcount: percent = 99
            msg = "%s %d%% complete (%s of %s)." % (action, percent,
                  cindex+1, util.plural("conversation", ccount, sep=","))
            self.update_gauge(self.gauge_progress, percent, msg)
            for chat in result.get("chats", []):
                if chat["identity"] in self.chats_diffdata:
                    del self.chats_diffdata[chat["identity"]]
        if "error" in result:
            self.is_merging = False
            self.update_gauge(self.gauge_progress, 0, "%s error." % action)
            logger.error("%s error.\n\n%s", action, result["error"])
            msg = "%s error.\n\n%s" % (action, 
                  result.get("error_short", result["error"]))
            self.html_report.Freeze()
            self.html_report.AppendToPage("<br /><br /> <b>Error merging chats:</b>&nbsp;&nbsp;"
                                          + result["error"].replace("<", "&lt;")
                                            .replace(" ", "&nbsp;").replace("\n", "<br />"))
            scrollpos = self.html_report.GetScrollRange(wx.VERTICAL)
            self.html_report.Scroll(0, scrollpos)
            self.html_report.Thaw()
            wx.MessageBox(msg, conf.Title, wx.OK | wx.ICON_WARNING)
        if "status" in result:
            guibase.status(result["status"])
        if "done" in result:
            self.is_merging = False
            self.page_merge_chats.Enabled = True
            self.page_merge_contacts.Enabled = True
            self.db2.clear_cache()
            self.stc_diff1.ClearAll()
            self.list_chats.DeleteAllItems()
            self.list_contacts.DeleteAllItems()
            self.label_merge_chat.Label = ""
            self.chat = None
            self.chat_diff = None
            self.chats2 = self.db2.get_conversations()
            info = result["output"]
            if "error" not in result:
                guibase.status(info, log=True)
                self.update_gauge(self.gauge_progress, 100, "Merge complete.")
                text = "<br /><br /> %s" % result["output"]
                self.html_report.Freeze()
                self.html_report.AppendToPage(text)
                scrollpos = self.html_report.GetScrollRange(wx.VERTICAL)
                self.html_report.Scroll(0, scrollpos)
                self.html_report.Thaw()
                wx.MessageBox(info, conf.Title, wx.OK | wx.ICON_INFORMATION)
            self.button_merge_all.Note = self.MERGE_BUTTON_NOTE
            self.button_swap.Enabled = True
            self.button_merge_chats.Enabled = True
            wx.CallLater(20, self.load_later_data)
            if self.is_scanned and self.chats_diffdata:
                count_msgs = util.plural(
                    "message", sum(len(d["diff"]["messages"])
                                   for d in self.chats_diffdata.values()), sep=",")
                count_chats = util.plural("chat", self.chats_diffdata, sep=",")
                noteinfo = "%s from %s" % (count_msgs, count_chats)
                self.button_merge_all.Note = (
                    "Copy %s to the database on the right." % noteinfo)
                self.button_merge_all.Enabled = True
        elif "output" in result and result["output"]:
            self.html_report.AppendToPage("<br /> %s" % result["output"])


    def update_gauge(self, gauge, value, message=""):
        """
        Updates the gauge value and message on page_merge_all. If value is
        None, hides gauge panel.
        """
        if value is None:
            gauge.Hide()
        else:
            gauge.Value = value
            for c in gauge.Parent.Children:
                if isinstance(c, wx.StaticText):
                    c.Label = message
                    break # for c
            gauge.Parent.Sizer.Layout()
            if not gauge.Parent.Shown:
                gauge.Parent.Show()
                gauge.Parent.ContainingSizer.Layout()


    def on_merge_chat(self, event):
        """
        Handler for clicking to merge a chat from left side db to the right
        side db.
        """
        if self.is_scanning or self.is_merging:
            wx.MessageBox("Global %(t)s is currently underway: single chat "
                          "merge temporarily disabled for data safety.\n\n"
                          "Please wait until the global %(t)s is finished."
                          % {"t": "merge" if self.is_merging else "scan"},
                          conf.Title, wx.OK | wx.ICON_WARNING)
            return
        db1, db2 = self.db1, self.db2
        chat, chat2 = self.chat["c1"], self.chat["c2"]
        messages = self.chat_diff["messages"]
        participants = self.chat_diff["participants"]
        condiff = self.con1diff
        contacts2 = []

        if messages or participants:
            info = ""
            parts = []
            new_chat = not chat2
            newstr = "" if new_chat else "new "
            if new_chat:
                info += "new chat with "
            if messages:
                parts.append(util.plural("%smessage" % newstr, messages, sep=","))
            if participants:
                # Add to contacts those that are new
                cc2 = [db1.id, db2.id] + \
                    [i["identity"] for i in db2.get_contacts()]
                contacts2 = [i["contact"] for i in participants
                    if "id" in i["contact"] and i["identity"] not in cc2]
                if contacts2:
                    parts.append(util.plural("new contact", contacts2, sep=","))
                parts.append(util.plural("%sparticipant" % newstr,
                                         participants, sep=","))
            for i in parts:
                info += ("" if i == parts[0] else (
                         " and " if i == parts[-1] else ", ")) + i

            proceed = wx.OK == wx.MessageBox(
                "Copy %s\n\nfrom %s\n\ninto %s?" % (info, db1, db2),
                conf.Title, wx.OK | wx.CANCEL | wx.ICON_INFORMATION)
            if proceed:
                self.is_merging = True
                try:
                    if not chat2:
                        chat2 = chat.copy()
                        self.chat["c2"] = chat2
                        chat2["id"] = db2.insert_conversation(chat2, db1)
                    if participants:
                        if contacts2:
                            db2.insert_contacts(contacts2, db1)
                        for p in participants:
                            if p in condiff:
                                condiff.remove(p)
                        db2.insert_participants(chat2, participants, db1)
                        del participants[:]
                    if messages:
                        db2.insert_messages(chat2, messages, db1, chat)
                        del messages[:]
                finally:
                    self.is_merging = False
                if chat["identity"] in self.chats_diffdata:
                    del self.chats_diffdata[chat["identity"]]
                db2.clear_cache()
                self.stc_diff1.ClearAll()
                self.button_merge_chat.Enabled = False
                self.button_export_chat.Enabled = False
                guibase.status("Merged %s of chat \"%s\" from %s to %s.",
                               info, chat2["title"], db1, db2, log=True)
                # Update chat list
                db2.get_conversations_stats([chat2], log=False)
                self.chat["messages2"] = chat2["message_count"]
                self.chat["last_message_datetime2"] = \
                    chat2["last_message_datetime"]
                for i in range(self.list_chats.ItemCount):
                    chat_i = self.list_chats.GetItemMappedData(i)
                    if chat_i == self.chat:
                        self.list_chats.SetItemBackgroundColour(
                            i, self.list_chats.BackgroundColour)
                self.list_chats.RefreshRows() # Update from loaded data
                infomsg = "Merged %s of chat \"%s\"\n\nfrom %s\n\nto %s." % \
                          (info, chat2["title"], db1, db2)
                wx.MessageBox(infomsg, conf.Title, wx.OK | wx.ICON_INFORMATION)


    def update_tabheader(self):
        """Updates page tab header with option to close page."""
        if self:
            self.ready_to_close = True
        if self:
            self.TopLevelParent.update_notebook_header()


    def load_data(self):
        """Loads data from our SkypeDatabases."""
        namespace = {"db1": self.db1, "db2": self.db2}
        template = step.Template(templates.MERGE_DB_LINKS, escape=True)
        self.html_dblabel.SetPage(template.expand(namespace))
        self.html_dblabel.BackgroundColour = wx.NullColour

        if isinstance(self.db1, live.SkypeExport) and not self.db1.export_parsed:
            self.button_swap.Hide()
            self.worker_import.work({"action": "parse", "db": self.db1})
            self.html_report.Show()

            html = ("<body bgcolor='%s'><font color='%s'>Parsing Skype chat history export %s .." %
                    (conf.MergeHtmlBackgroundColour, conf.FgColour, self.db1))
            self.html_report.SetPage(html)
            self.update_gauge(self.gauge_progress, 0)
            self.gauge_progress.Pulse()
            self.update_tabheader()

            for i in range(2):
                db = self.db2 if i else self.db1
                db.update_fileinfo()
                label = self.label_all2 if i else self.label_all1
                label.Label = "%s.\n\nSize %s.\nAnalyzing.." % (
                              db, util.format_bytes(db.filesize))
            return

        try:
            # Populate the chat comparison list
            chats1 = self.db1.get_conversations()
            chats2 = self.db2.get_conversations()
            c1map = dict((c["identity"], c) for c in chats1)
            c2map = dict((c["identity"], c) for c in chats2)
            for mm, cc in (c1map, chats1), (c2map, chats2):
                for c in (c for c in cc if c.get("__link")):
                    mm[c["__link"]["identity"]] = c
            def get_matched(cmap, c):
                x = cmap.get(c["identity"])
                x = x or c.get("__link") and cmap.get(c["__link"]["identity"])
                return x

            compared = []
            for c1 in chats1:
                c1["c1"], c1["c2"] = c1.copy(), get_matched(c2map, c1)
                compared.append(c1)
            for c2 in chats2:
                if not get_matched(c1map, c2):
                    c2["c1"], c2["c2"] = None, c2.copy()
                    compared.append(c2)
            for c in compared:
                c["last_message_datetime1"] = None
                c["last_message_datetime2"] = None
                c["messages1"] = c["messages2"] = c["people"] = None

            self.list_chats.Populate(compared)
            self.list_chats.SortListItems(3, 0) # Sort by last message in left
            self.compared = compared
            self.chats1 = chats1
            self.chats2 = chats2
            wx.CallLater(200, self.load_later_data)
        except Exception as e:
            wx.CallAfter(self.update_tabheader)
            guibase.status("Could not load chat lists from %s and %s: %s",
                           self.db1, self.db2, util.format_exc(e))
            logger.exception("Could not load chat lists from %s and %s.",
                             self.db1, self.db2)
            errormsg = "Could not load chat lists from %s and %s.\n\n%s" % \
                       (self.db1, self.db2, traceback.format_exc())
            wx.MessageBox(errormsg, conf.Title, wx.OK | wx.ICON_WARNING)


    def load_later_data(self):
        """
        Loads later data from the databases, like message counts and compared
        contacts, used as a background callback to speed up page opening.
        """

        try:
            chats1, chats2 = self.chats1, self.chats2
            self.db1.get_conversations_stats(chats1)
            self.db2.get_conversations_stats(chats2)
            c1map = dict((c["identity"], c) for c in chats1)
            c2map = dict((c["identity"], c) for c in chats2)

            if self.compared is None:
                compared = []
                for c1 in chats1:
                    c1["c1"], c1["c2"] = c1.copy(), c2map.get(c1["identity"])
                    compared.append(c1)
                for c2 in chats2:
                    if c2["identity"] not in c1map:
                        c2["c1"], c2["c2"] = None, c2.copy()
                        compared.append(c2)
                for c in compared:
                    c["last_message_datetime1"] = None
                    c["last_message_datetime2"] = None
                    c["messages1"] = c["messages2"] = c["people"] = None
                self.compared = compared
            for c in self.compared:
                for i in range(2):
                    cmap = c2map if i else c1map
                    if c["c%s" % (i + 1)] and c["identity"] in cmap:
                        c["messages%s" % (i + 1)] = \
                        c["c%s" % (i + 1)]["message_count"] = \
                            cmap[c["identity"]]["message_count"]
                        c["last_message_datetime%s" % (i + 1)] = \
                        c["c%s" % (i + 1)]["last_message_datetime%s" % (i + 1)] = \
                            cmap[c["identity"]]["last_message_datetime"]
                people = sorted([p["identity"] for p in c["participants"]])
                if skypedata.CHATS_TYPE_SINGLE != c["type"]:
                    c["people"] = "%s (%s)" % (len(people), ", ".join(people))
                else:
                    people = [p for p in people if p != self.db1.id]
                    c["people"] = ", ".join(people)

            self.list_chats.Enabled = True
            self.list_chats.Populate(self.compared)

            # Populate the contact comparison list
            contacts1 = self.db1.get_contacts()
            contacts2 = self.db2.get_contacts()
            contactgroups1 = self.db1.get_contactgroups()
            contactgroups2 = self.db2.get_contactgroups()
            con1map = dict((c["identity"], c) for c in contacts1)
            con2map = dict((c["identity"], c) for c in contacts2)
            con1diff, con2diff = [], []
            con1new, con2new = {}, {} # New contacts for dbs {skypename:row, }
            cg1diff, cg2diff = [], []
            cg1map = dict((g["name"], g) for g in contactgroups1)
            cg2map = dict((g["name"], g) for g in contactgroups2)
            for c1 in contacts1:
                c2 = con2map.get(c1["identity"])
                if not c2 and c1["identity"] not in con1new:
                    c = c1.copy()
                    c["c1"], c["c2"] = c1, c2
                    con1diff.append(c)
                    con1new[c1["identity"]] = True
            for c2 in contacts2:
                c1 = con1map.get(c2["identity"])
                if not c1 and c2["identity"] not in con2new:
                    c = c2.copy()
                    c["c1"], c["c2"] = c1, c2
                    con2diff.append(c)
                    con2new[c2["identity"]] = True
            for g1 in contactgroups1:
                g2 = cg2map.get(g1["name"])
                if not g2 or g2["members"] != g1["members"]:
                    g = g1.copy()
                    g["g1"] = g1
                    g["g2"] = g2
                    cg1diff.append(g)
            for g2 in contactgroups2:
                g1 = cg1map.get(g2["name"])
                if not g1 or g1["members"] != g2["members"]:
                    g = g2.copy()
                    g["g1"] = g1
                    g["g2"] = g2
                    cg2diff.append(g)
            dummy = {"__type": "Group", "phone_mobile_normalized": "",
                "country": "", "city": "", "about": "About"}
            con1difflist = [c.copy() for c in con1diff]
            [c.update({"__type": "Contact", "__data": c}) for c in con1difflist]
            for g in cg1diff:
                c = g.copy()
                c.update(dummy)
                c["identity"], c["__data"] = c["members"], g
                con1difflist.append(c)
            con2difflist = [c.copy() for c in con2diff]
            [c.update({"__type":"Contact", "__data": c}) for c in con2difflist]
            for g in cg2diff:
                c = g.copy()
                c.update(dummy)
                c["identity"], c["__data"] = c["members"], g
                con2difflist.append(c)
            self.list_contacts.Populate(con1difflist)
            self.button_merge_allcontacts.Enabled = self.list_contacts.ItemCount
            self.con1diff = con1diff
            self.con2diff = con2diff
            self.con1difflist = con1difflist
            self.con2difflist = con2difflist
            self.congroup1diff = cg1diff
            self.congroup2diff = cg2diff

            for i in range(2):
                db = self.db2 if i else self.db1
                db.update_fileinfo()
                label = self.label_all2 if i else self.label_all1
                label.Label = "%s.\n\nSize %s.\nLast modified %s.\n" % (
                              db, util.format_bytes(db.filesize),
                              db.last_modified.strftime("%Y-%m-%d %H:%M:%S"))
            for i in range(2):
                db = self.db2 if i else self.db1
                condiff = self.con2diff if i else self.con1diff
                contacts = contacts2 if i else contacts1
                db.update_fileinfo()
                label = self.label_all2 if i else self.label_all1
                label.Label = "%s.\n\nSize %s.\nLast modified %s.\n" % (
                              db, util.format_bytes(db.filesize),
                              db.last_modified.strftime("%Y-%m-%d %H:%M:%S"))
                chats = chats2 if i else chats1
                if chats:
                    t1 = list(filter(bool, [c["message_count"] for c in chats]))
                    count_messages = sum(t1) if t1 else 0
                    t2 = list(filter(bool, [c["first_message_datetime"] for c in chats]))
                    datetime_first = min(t2) if t2 else None
                    t3 = list(filter(bool, [c["last_message_datetime"] for c in chats]))
                    datetime_last = max(t3) if t3 else None
                    datetext_first = "" if not datetime_first \
                        else datetime_first.strftime("%Y-%m-%d %H:%M:%S")
                    datetext_last = "" if not datetime_last \
                        else datetime_last.strftime("%Y-%m-%d %H:%M:%S")
                    contacttext = util.plural("contact", contacts, sep=",")
                    if condiff:
                        contacttext += " (%d not present on the %s)" % (
                                       len(condiff), ["right", "left"][i])
                    label.Label += "%s.\n%s.\n%s.\nFirst message at %s.\n" \
                                   "Last message at %s." % (
                                   util.plural("conversation", chats, sep=","),
                                   util.plural("message", count_messages, sep=","), 
                                   contacttext, datetext_first, datetext_last)
        except Exception as e:
            # Database access can easily fail if the user closes the tab before
            # the later data has been loaded.
            if self:
                logger.exception("Error loading additional data from %s or %s.",
                                 self.db1, self.db2)
                wx.MessageBox("Error loading additional data from %s or %s."
                              "\n\nError: %s." % (self.db1, self.db2, util.format_exc(e)),
                              conf.Title, wx.OK | wx.ICON_WARNING)

        if self:
            self.button_swap.Enabled = True
            self.button_merge_chats.Enabled = True
            if not self.is_scanned:
                self.button_scan_all.Enabled = True
                self.button_merge_all.Enabled = True
            guibase.status("Opened %s and %s.", self.db1, self.db2)
            self.page_merge_all.Layout()
            self.Refresh()
            wx.CallAfter(self.update_tabheader)



class ChatContentSTC(controls.SearchableStyledTextCtrl):
    """A StyledTextCtrl for showing and filtering chat messages."""

    TEXT_NO_MESSAGES = "\nNo messages to show."

    def __init__(self, *args, **kwargs):
        controls.SearchableStyledTextCtrl.__init__(self, *args, **kwargs)
        self.SetUndoCollection(False)

        self._parser = None     # Current skypedata.MessageParser instance
        self._chat = None       # Currently shown chat
        self._db = None         # Database for currently shown messages
        self._page = None       # DatabasePage/MergerPage for action callbacks
        self._messages = None   # List of all retrieved messages
        self._messages_current = None  # List of currently shown messages
        self._message_positions = collections.OrderedDict() # {msg id: (start index, end index)}
        self._message_map = collections.OrderedDict() # {msg ID: {msg}}
        # If set, range is centered around the message with the specified ID
        self._center_message_id =    None
        # Index of the centered message in _messages
        self._center_message_index = None
        self._urllinks  = {} # {link start position: url}
        self._filelinks = {} # {link start position: file path}
        self._datelinks = {} # {link start position: two dates, }
        self._datelink_last = None # Title of clicked date link, if any
        # Currently set message filter {"daterange": (datetime, datetime),
        # "text": text in message, "participants": [skypename1, ],
        # "message_id": message ID to show, range shown will be centered
        # around it}
        self._filter = {}
        self._filtertext_rgx = None # Cached regex for filter["text"]
        self._auto_retrieve = True # Whether new messages retrieved on refresh

        self._styles = {"default": 10, "bold": 11, "timestamp": 12,
            "remote": 13, "local": 14, "link": 15, "tiny": 16,
            "special": 17, "bolddefault": 18, "boldlink": 19,
            "boldspecial": 20, "remoteweak": 21, "localweak": 22,
            "italic": 23, "strike": 24
        }
        self.SetWrapMode(True)
        self.SetMarginLeft(10)
        self.SetMarginWidth(1, 0) # Hide left margin
        self.SetReadOnly(True)
        self.SetStyleSpecs()

        self._stc.Bind(wx.stc.EVT_STC_HOTSPOT_CLICK, self.OnUrl)
        self._stc.Bind(wx.EVT_RIGHT_UP, self.OnMenu)
        self._stc.Bind(wx.EVT_CONTEXT_MENU, self.OnMenu)
        self._stc.Bind(wx.EVT_SYS_COLOUR_CHANGED, self.OnSysColourChange)
        # Hide caret
        self.SetCaretForeground(conf.BgColour), self.SetCaretWidth(0)


    def SetStyleSpecs(self):
        """Sets STC style colours."""
        stylespecs = {
            "default":      "face:%s,size:%d,fore:%s,back:%s" %
                            (conf.HistoryFontName, conf.HistoryFontSize,
                             conf.MessageTextColour, conf.BgColour),
            "bolddefault": "bold",
            "bold":        "bold",
            "timestamp":   "fore:%s" % conf.HistoryTimestampColour,
            "remote":      "fore:%s,bold" % conf.HistoryRemoteAuthorColour,
            "local":       "fore:%s,bold" % conf.HistoryLocalAuthorColour,
            "remoteweak":  "fore:%s" % conf.HistoryRemoteAuthorColour,
            "localweak":   "fore:%s" % conf.HistoryLocalAuthorColour,
            "link":        "fore:%s" % conf.SkypeLinkColour,
            "boldlink":    "fore:%s,bold" % conf.SkypeLinkColour,
            "tiny":        "size:1",
            "special":     "fore:%s" % conf.HistoryGreyColour,
            "boldspecial": "fore:%s,bold" % conf.HistoryGreyColour,
            "italic":      "italic",
            "strike":      "underline",
        }
        self.StyleSetSpec(wx.stc.STC_STYLE_DEFAULT, stylespecs["default"])
        self.StyleClearAll() # Apply the new default style to all styles
        for style, spec in stylespecs.items():
            self.StyleSetSpec(self._styles[style], spec)
        self.StyleSetHotSpot(self._styles["link"], True)
        self.StyleSetHotSpot(self._styles["boldlink"], True)


    def SetDatabasePage(self, page):
        self._page = page


    def GetUrlAtPosition(self, pos):
        """"Go back and forth from STC position, return URL and STC range."""
        url_range = {-1: -1, 1: -1} # { start and end positions }
        styles_link = [self._styles["link"], self._styles["boldlink"]]
        for step in url_range:
            while self._stc.GetStyleAt(pos + step) in styles_link:
                pos += step
            url_range[step] = pos
        url_range[1] += 1
        startstop = url_range[-1], url_range[1]
        return self._stc.GetTextRange(*startstop), startstop


    def OnSysColourChange(self, event):
        """Handler for system colour change, updates STC styling."""
        event.Skip()
        self.SetStyleSpecs()


    def OnMenu(self, event):
        """
        Handler for right-clicking (or pressing menu key), opens a custom context
        menu.
        """
        def clipboardize(text):
            if wx.TheClipboard.Open():
                d = wx.TextDataObject(text)
                wx.TheClipboard.SetData(d), wx.TheClipboard.Close()

        is_click = isinstance(event, wx.MouseEvent)
        pos = self._stc.PositionFromPoint(event.Position) if is_click else -1
        msg_id = msg = msg_idx = prevmsg_id = None
        for i, m_id in enumerate(self._message_positions) if pos >= 0 else []:
            m_pos = self._message_positions[m_id]
            if m_pos[0] <= pos <= m_pos[1]:
                msg_id, msg_idx = m_id, i
                break # for i, m_id
            elif i and self._message_positions[prevmsg_id][1] < pos \
            and m_pos[0] > pos:
                msg_id, msg_idx = prevmsg_id, i - 1
                break # for i, m_id
            elif m_pos[0] > pos:
                break # for i, m_id
            prevmsg_id = m_id
        if msg_id is None and not is_click:
            # Context menu event, pick focused or first visible message
            msg_id, _ = self.GetFocusedMessage()
            if msg_id is not None:
                msg_idx = list(self._message_map).index(msg_id)
        if msg_id is None and self._message_positions:
            m_id = self._messages_current[-1]["id"]
            if pos >= 0 and self._message_positions[m_id][1] < pos:
                msg_id, msg_idx = m_id, len(self._messages_current) - 1
        msg = self._message_map.get(msg_id)
        menu = wx.Menu()
        item_selection = wx.MenuItem(menu, -1, "&Copy selection")
        menu.Append(item_selection)
        menu.Bind(wx.EVT_MENU, lambda e: clipboardize(self._stc.SelectedText),
                  id=item_selection.GetId())
        item_selection.Enable(bool(self._stc.SelectedText))

        styles_link = [self._styles["link"], self._styles["boldlink"]]
        if msg and self._stc.GetStyleAt(pos) in styles_link:
            # Right-clicked a link inside a message
            def on_copyurl(event): clipboardize(url)
            (url, urlrange), urltype = self.GetUrlAtPosition(pos), "link"
            if urlrange[0] in self._filelinks:
                url, urltype = self._filelinks[urlrange[0]], "file"
                if any(url.startswith(x) for x in ["\\\\\\", "///"]):
                    url = url[3:] # Strip redundant filelink slashes
                if not isinstance(url, six.text_type):
                    url = util.to_unicode(url, "utf-8", errors="replace")
            elif urlrange[0] in self._urllinks:
                url = self._urllinks[urlrange[0]]
            item_link = wx.MenuItem(menu, -1, "C&opy %s location" % urltype)
            menu.Append(item_link)
            menu.Bind(wx.EVT_MENU, on_copyurl, id=item_link.GetId())
        else:
            opts = dict(current=msg_idx, author=(msg or {}).get("author"))
            def on_copymsg(event):
                t = step.Template(templates.MESSAGE_CLIPBOARD)
                clipboardize(t.expand({"m": msg, "parser": self._parser}))
                guibase.status("Copied message #%s to clipboard." % msg["id"])
            def on_selectall(event): self._stc.SelectAll()
            def on_search(event):
                self.SetSearchBarVisible()
                self._edit.SetFocus()
                self._edit.SelectAll()
            def on_filter_date(period):
                def do_filter(event):
                    dt = msg["datetime"].date()
                    if   "day"   == period: daterange = [dt, dt]
                    elif "week"  == period:
                        daterange = [dt - datetime.timedelta(days=dt.weekday()),
                                     dt + datetime.timedelta(days=6-dt.weekday())]
                    elif "month" == period:
                        maxd = calendar.monthrange(dt.year, dt.month)[1]
                        daterange = [datetime.date(dt.year, dt.month, 1),
                                     datetime.date(dt.year, dt.month, maxd)]
                    elif "year"  == period:
                        daterange = [datetime.date(dt.year,  1,  1),
                                     datetime.date(dt.year, 12, 31)]
                    self.ApplyFilter(daterange=daterange, text="")
                return do_filter
            def on_gotoauthor(direction):
                return lambda e: self.NextFromAuthor(direction=direction, **opts)
            def on_gototime(unit, direction):
                return lambda e: self.NextTime(unit, msg_idx, direction)

            item_msg = wx.MenuItem(menu, -1, "Copy &message")
            item_select = wx.MenuItem(menu, -1, "Select &all")
            menu.Append(item_msg), menu.Append(item_select)
            menu.AppendSeparator()

            item_search = wx.MenuItem(menu, -1, "&Search..")
            menu.Append(item_search)

            menu_filter = wx.Menu()
            item_day   = wx.MenuItem(menu_filter, -1, "Same &day")
            item_week  = wx.MenuItem(menu_filter, -1, "Same &week")
            item_month = wx.MenuItem(menu_filter, -1, "Same &month")
            item_year  = wx.MenuItem(menu_filter, -1, "Same &year")
            item_filter = menu.AppendSubMenu(menu_filter, "&Filter by date..")
            menu_filter.Append(item_day)
            menu_filter.Append(item_week)
            menu_filter.Append(item_month)
            menu_filter.Append(item_year)

            menu_goto = wx.Menu()

            item_prev = wx.MenuItem(menu_goto, -1, "&Previous from same author")
            item_next = wx.MenuItem(menu_goto, -1, "&Next from same author")
            item_prev_day   = wx.MenuItem(menu_goto, -1, "Previous &day")
            item_next_day   = wx.MenuItem(menu_goto, -1, "Next d&ay")
            item_prev_week  = wx.MenuItem(menu_goto, -1, "Previous &week")
            item_next_week  = wx.MenuItem(menu_goto, -1, "Next w&eek")
            item_prev_month = wx.MenuItem(menu_goto, -1, "Previous &month")
            item_next_month = wx.MenuItem(menu_goto, -1, "Next m&onth")

            item_goto = menu.AppendSubMenu(menu_goto, "&Go to..")
            menu_goto.Append(item_prev), menu_goto.Append(item_next)
            menu_goto.AppendSeparator()
            menu_goto.Append(item_prev_day), menu_goto.Append(item_next_day)
            menu_goto.AppendSeparator()
            menu_goto.Append(item_prev_week), menu_goto.Append(item_next_week)
            menu_goto.AppendSeparator()
            menu_goto.Append(item_prev_month), menu_goto.Append(item_next_month)

            item_msg.Enabled = item_filter.Enabled = item_goto.Enabled = bool(msg)
            if not self._auto_retrieve: item_filter.Enabled = False
            menu.Bind(wx.EVT_MENU, on_selectall,             id=item_select.GetId())
            menu.Bind(wx.EVT_MENU, on_copymsg,               id=item_msg.GetId())
            menu.Bind(wx.EVT_MENU, on_search,                id=item_search.GetId())
            menu.Bind(wx.EVT_MENU, on_filter_date("day"),    id=item_day.GetId())
            menu.Bind(wx.EVT_MENU, on_filter_date("week"),   id=item_week.GetId())
            menu.Bind(wx.EVT_MENU, on_filter_date("month"),  id=item_month.GetId())
            menu.Bind(wx.EVT_MENU, on_filter_date("year"),   id=item_year.GetId())
            menu.Bind(wx.EVT_MENU, on_gotoauthor(-1),        id=item_prev.GetId())
            menu.Bind(wx.EVT_MENU, on_gotoauthor(+1),        id=item_next.GetId())
            menu.Bind(wx.EVT_MENU, on_gototime("day", -1),   id=item_prev_day.GetId())
            menu.Bind(wx.EVT_MENU, on_gototime("day", +1),   id=item_next_day.GetId())
            menu.Bind(wx.EVT_MENU, on_gototime("week", -1),  id=item_prev_week.GetId())
            menu.Bind(wx.EVT_MENU, on_gototime("week", +1),  id=item_next_week.GetId())
            menu.Bind(wx.EVT_MENU, on_gototime("month", -1), id=item_prev_month.GetId())
            menu.Bind(wx.EVT_MENU, on_gototime("month", +1), id=item_next_month.GetId())
        self.PopupMenu(menu)


    def OnUrl(self, event):
        """
        Handler for clicking a link in chat history, opens URLs in system
        browser, starts file links, and handles internal links.
        """
        stc = event.EventObject
        styles_link = [self._styles["link"], self._styles["boldlink"]]
        if stc.GetStyleAt(event.Position) in styles_link:
            # Go back and forth from position and get URL range.
            url, url_range = self.GetUrlAtPosition(event.Position)
            function, args, kwargs = None, [], {}
            if url_range[0] in self._filelinks:
                def start_file(url):
                    if os.path.exists(url):
                        util.start_file(url)
                    else:
                        messageBox("The file \"%s\" cannot be found "
                                   "on this computer." % url,
                                   conf.Title, wx.OK | wx.ICON_INFORMATION)
                function, args = start_file, [self._filelinks[url_range[0]]]
            elif url_range[0] in self._datelinks:
                function = self.ApplyFilter
                kwargs = dict(daterange=self._datelinks[url_range[0]], datelabel=url)
            elif url_range[0] in self._urllinks:
                url = self._urllinks[url_range[0]]
                function, args = webbrowser.open, [url]
            elif "Scroll back more." == url:
                function = self.RetrieveMoreMessages
            elif url:
                function, args = webbrowser.open, [url]
            if function:
                # Calling function here immediately will cause STC to lose
                # MouseUp, resulting in autoselect mode from click position.
                wx.CallLater(100, function, *args, **kwargs)
        event.StopPropagation()


    def SetAutoRetrieve(self, retrieve):
        """
        Sets whether to auto-retrieve more messages,
        and allow date periods navigation and filtering.
        """
        self._auto_retrieve = retrieve


    def RetrieveMessagesIfNeeded(self):
        """
        Retrieves more messages if needed, for example if current filter
        specifies a larger date range than currently available.
        """
        if not self._messages_current and "daterange" in self._filter \
        and self._filter["daterange"][0]:
            # If date filtering was just applied, check if we need to
            # retrieve more messages from earlier (messages are retrieved
            # starting from latest).
            if not self._messages[0]["datetime"] \
            or self._messages[0]["datetime"].date() >= self._filter["daterange"][0]:
                mm, kws = [], dict(timestamp_from=self._messages[0]["timestamp"],
                                   ascending=False, use_cache=False)
                for m in self._db.get_messages(self._chat, **kws):
                    mm.append(m)
                    if m["datetime"].date() < self._filter["daterange"][0]:
                        break # for m
                self._messages[:0] = mm[::-1] # Insert ascending at front
        last_dt = self._chat.get("last_message_datetime")
        if self._messages and last_dt and self._messages[-1]["datetime"] < last_dt:
            # Last message timestamp is earlier than chat's last message
            # timestamp: new messages have arrived
            self._messages.extend(self._db.get_messages(self._chat,
                ascending=True, use_cache=False,
                timestamp_from=self._messages[-1]["timestamp"]
            ))


    def RetrieveMoreMessages(self, count=None):
        """
        Retrieves another N messages starting from current first.

        @param   count  maximum number of more messages to retrieve,
                        defaults to conf.MaxHistoryInitialMessages / 2
        """
        if count is None: count = max(1, conf.MaxHistoryInitialMessages // 2)
        if not count: return

        center_id, stamp_from = None, None
        if self._messages:
            if self._messages_current: center_id = self._messages_current[0]["id"]
            stamp_from = self._messages[0]["timestamp"]
        elif any(self._filter.get("daterange") or []):
            stamp_from = util.datetime_to_epoch(self._filter["daterange"][0])
        if stamp_from is None: return

        mm, kws = [], dict(timestamp_from=stamp_from,
                           ascending=False, use_cache=False)
        busy = controls.BusyPanel(self._page or self.Parent,
                                  "Retrieving more messages.")
        try:
            for i, m in enumerate(self._db.get_messages(self._chat, **kws)):
                mm.append(m)
                if i + 1 >= count: break # for i, m
            self._messages[:0] = mm[::-1] # Insert ascending at front
            self._center_message_id = self._center_message_index = None
            if self._messages:
                rng = [self._messages[x]["datetime"].date() for x in (0, -1)]
                self._filter["daterange"] = rng
                if self._page:
                    self._page.range_date.SetValues(*rng)
                    self._page.chat_filter["daterange"] = rng
            self.RefreshMessages()
            if self._page:
                self._page.populate_chat_statistics()
                self._page.list_timeline.Populate(*self.GetTimelineData())
        finally: busy.Close()
        if center_id is not None: self.FocusMessage(center_id, select=False)


    def RefreshMessages(self, center_message_id=None):
        """
        Clears content and redisplays messages of current chat.

        @param   center_message_id  if specified, message with the ID is
                                    focused and message range will center
                                    around it, staying within max number
        """
        self.SetReadOnly(False) # Can't modify while read-only
        self.ClearAll()
        self._parser = skypedata.MessageParser(self._db, self._chat, stats=True)
        if self._messages:
            if self._auto_retrieve:
                self.RetrieveMessagesIfNeeded()
            self.AppendText("Formatting messages..\n")
            self.Refresh()
            self.Freeze()
            self.ClearAll()

            if center_message_id:
                index = 0
                for m in self._messages:
                    if m["id"] == center_message_id:
                        self._center_message_id = center_message_id
                        self._center_message_index = index
                        break
                    index += 1

            colourmap = collections.defaultdict(lambda: "remote")
            colourmap[self._db.id] = "local"
            self._message_positions.clear()
            self._message_map.clear()
            previous_day = None
            count = 0
            focus_message_id = None
            self._urllinks.clear()
            self._filelinks.clear()
            self._datelinks.clear()
            # For accumulating various statistics
            rgx_highlight = re.compile(
                "(%s)" % re.escape(self._filter["text"]), re.I
            ) if ("text" in self._filter and self._filter["text"]) else None
            self._messages_current = []

            # Assemble messages to show
            for m in self._messages:
                count += 1
                if self.IsMessageFilteredOut(m):
                    continue # for m
                if self._center_message_index is not None \
                and count < self._center_message_index \
                - conf.MaxHistoryInitialMessages // 2:
                    # Skip messages before the range centered around a message
                    continue # for m
                if self._center_message_index is not None \
                and count > self._center_message_index \
                + conf.MaxHistoryInitialMessages // 2:
                    # Skip messages after the range centered around a message
                    break # for m

                self._messages_current.append(m)

            # Add date and count information, "Scroll back more", and links like "6 months"
            self._append_text("\n")
            if self._messages_current:
                m1, m2 = self._messages_current[0], self._messages_current[-1]
                self._append_text("History of  ")
                self._append_text(m1["datetime"].strftime("%d.%m.%Y"), "bold")
                if m1["datetime"].date() != m2["datetime"].date():
                    self._append_text(" to ")
                    self._append_text(
                        m2["datetime"].strftime("%d.%m.%Y"), "bold")
                self._append_text("  (%s). " % util.plural(
                                  "message", self._messages_current, sep=","))

            if self._chat["message_count"] and self._auto_retrieve and (not self._messages 
            or self._messages[0]["datetime"] > self._chat["first_message_datetime"]):
                self._append_text("Scroll back more.", "link")

            if self._chat["message_count"] and self._auto_retrieve:
                self._append_text("\nShow from:  ")
                date_first = self._chat["first_message_datetime"].date()
                date_last = self._chat["last_message_datetime"].date()
                date_until = datetime.date.today()
                dates_filter = self._filter.get("daterange")
                from_items = [] # [(title, [date_first, date_last])]

                for unit, count in [("day", 7), ("week", 2), ("day", 30),
                ("month", 3), ("month", 6), ("year", 1), ("year", 2)]:
                    date_from = util.date_shift(date_until, unit, -count)
                    if date_from >= date_first and date_from <= date_last:
                        title = util.plural(unit, count, sep=",")
                        from_items.append((title, [date_from, date_last]))
                date_2y = util.date_shift(date_until, "year", -2)
                date_4y = util.date_shift(date_until, "year", -4)
                if  date_2y > date_first and date_4y > date_first:
                    from_items.append(("2 to 4 years", [date_4y, date_2y]))
                if date_4y > date_first:
                    from_items.append(("4 years and older", [date_first, date_4y]))

                daterange = [date_first, date_last]
                from_items.append(("From the beginning", daterange))
                for i, (title, daterange) in enumerate(from_items):
                    is_active = center_message_id is None \
                                and ((title == self._datelink_last) 
                                     or (daterange == dates_filter))
                    if i:
                        self._append_text(u"  \u2022  ", "special") # bullet
                    if not is_active:
                        self._datelinks[self.STC.Length] = daterange
                    self._append_text(title, "bold" if is_active else "link")
            self._datelink_last = None
            self._append_text("\n\n")

            for i, m in enumerate(self._messages_current):
                if m["datetime"].date() != previous_day:
                    # Day has changed: insert a date header
                    previous_day = m["datetime"].date()
                    weekday, weekdate = util.get_locale_day_date(previous_day)
                    self._append_text("\n%s" % weekday, "bold")
                    self._append_text(", %s\n\n" % weekdate)

                dom = self._parser.parse(m)
                length_before = self.STC.Length
                time_value = m["datetime"].strftime("%H:%M")
                displayname = self._db.get_author_name(m)
                special_tag = dom.find("msgstatus")
                # Info messages like "/me is thirsty" -> author on same line.
                is_info = (skypedata.MESSAGE_TYPE_INFO == m["type"])

                if is_info:
                    stylebase = colourmap[m["author"]]
                    self._append_text(time_value, stylebase)
                    self._append_text("\n%s " % displayname, stylebase + "weak")
                elif special_tag is None:
                    self._append_text("%s %s\n" % (time_value, displayname),
                                                   colourmap[m["author"]])
                else:
                    self._append_text("%s %s" % (time_value, displayname),
                                                 colourmap[m["author"]])
                    self._append_text("%s\n" % special_tag.text, "special")

                self._write_element(dom, rgx_highlight)

                messagepos = (length_before, self.STC.Length - 2)
                self._message_positions[m["id"]] = messagepos
                self._message_map[m["id"]] = m
                if self._center_message_id == m["id"]:
                    focus_message_id = m["id"]
                if i and not i % conf.MaxHistoryInitialMessages:
                    wx.YieldIfNeeded() # To have responsive GUI

            # Reset the centered message data, as filtering should override it
            self._center_message_index = None
            self._center_message_id = None
            if focus_message_id:
                self.FocusMessage(focus_message_id)
            else:
                self.ScrollToLine(self.LineCount)
            self.Thaw()
        else:
            # No messages to show
            self.ClearAll()
            self._append_text(self.TEXT_NO_MESSAGES, "special")
        self.SetReadOnly(True)



    def _write_element(self, dom, rgx_highlight=None, tails_new=None):
        """
        Appends the message body to the StyledTextCtrl.

        @param   dom            xml.etree.cElementTree.Element instance
        @param   rgx_highlight  if set, substrings matching the regex are added
                                in highlighted style
        @param   tails_new      internal use, {element: modified tail str}
        """
        tagstyle_map = {"b": "bold", "i": "italic", "s": "strike",
                        "bodystatus": "special",  "quotefrom": "special",
                        "a": "link", "ss": "default", "at": "bold"}
        other_tags = ["blink", "font", "bodystatus", "i", "span", "flag", "pre"]
        to_skip = {} # {element to skip: True, }
        tails_new = {} if tails_new is None else tails_new
        linefeed_final = "\n\n" # Decreased if quotefrom is last

        for e in dom.getiterator():
            # Possible tags: a|b||i|s|bodystatus|quote|quotefrom|msgstatus|
            #                span|special|xml|font|blink
            if e in to_skip:
                continue
            style = tagstyle_map.get(e.tag, "default")
            text = e.text or ""
            tail = tails_new[e] if e in tails_new else (e.tail or "")
            children = []
            if isinstance(text, six.binary_type):
                text = text.decode("utf-8")
            if isinstance(text, six.binary_type):
                tail = tail.decode("utf-8")
            if "a" == e.tag:
                href = e.get("href")
                if href.startswith("file:"):
                    pathname = urllib.request.url2pathname(e.get("href")[5:])
                    self._filelinks[self.STC.Length] = pathname
                elif re.match("^[a-z]+%s" % re.escape("://"), href):
                    self._urllinks[self.STC.Length] = href
                linefeed_final = "\n\n"
            elif "ss" == e.tag:
                text = e.text
            elif "quote" == e.tag:
                text = "\"" + text
                children = e.getchildren()
                if len(children) > 1:
                    # Last element is always quotefrom
                    childtail = children[-2].tail if children[-2].tail else ""
                    tails_new[children[-2]] = childtail + "\""
                else:
                    text += "\""
                linefeed_final = "\n"
            elif "quotefrom" == e.tag:
                text = "\n%s\n" % text
            elif e.tag in ["xml", "b"]:
                linefeed_final = "\n\n"
            elif "at" == e.tag:
                if text and not text.startswith("@"): text = "@" + text
            elif "s" == e.tag:
                text = "~%s~" % text # STC does not support strikethrough style
            elif e.tag not in other_tags:
                text = ""
            if text:
                self._append_text(text, style, rgx_highlight)
            for i in children:
                self._write_element(i, rgx_highlight, tails_new)
                to_skip[i] = True
            if tail:
                self._append_text(tail, "default", rgx_highlight)
                linefeed_final = "\n\n"
        if "xml" == dom.tag:
            self._append_text(linefeed_final)


    def _append_text(self, text, style="default", rgx_highlight=None):
        """
        Appends text to the StyledTextCtrl in the specified style.

        @param   rgx_highlight  if set, substrings matching the regex are added
                                in highlighted style
        """
        text = text or ""
        if isinstance(text, six.text_type):
            text = text.encode("utf-8")
        text_parts = rgx_highlight.split(text) if rgx_highlight else [text]
        bold = "bold%s" % style if "bold%s" % style in self._styles else style
        len_self = self.GetTextLength()
        self.STC.AppendText(text)
        self.STC.StartStyling(len_self)
        self.STC.SetStyling(len(text), self._styles[style])
        for i, t in enumerate(text_parts):
            if i % 2:
                self.STC.StartStyling(len_self)
                self.STC.SetStyling(len(t), self._styles[bold])
            len_self += len(t)


    def _append_multiline(self, text, indent):
        """
        Appends text with new lines indented at the specified level.
        """
        if "\n" in text:
            for line in text.splitlines():
                self._append_text("%s\n" % line)
                if self.USE_COLUMNS:
                    self.SetLineIndentation(self.LineCount - 1, indent)
            if self.USE_COLUMNS:
                self.SetLineIndentation(self.LineCount - 1, 0)
        else:
            self._append_text(text)


    def Populate(self, chat, db, messages=None, center_message_id=None,
                 from_index=None):
        """
        Populates the chat history with messages from the specified chat.

        @param   chat               chat data, as returned from SkypeDatabase
        @param   db                 SkypeDatabase to use
        @param   messages           messages to show (if set, messages are not
                                    retrieved from database)
        @param   center_message_id  if set, specifies the message around which
                                    to center other messages in the shown range
        @param   from_index         index of message to show from, if messages given
        """
        self.ClearAll()
        self.Refresh()
        self._center_message_index = None
        self._center_message_id = None

        if chat is None:
            messages_current, message_range = [], []
        elif messages is None:
            mm, center_message_i = [], None
            for i, m in enumerate(db.get_messages(chat, ascending=False)):
                mm.append(m)
                if m["id"] == center_message_id:
                    self._center_message_id = center_message_id
                    center_message_i = i

                if self._center_message_id is not None:
                    if i + 1 - center_message_i >= conf.MaxHistoryInitialMessages // 2:
                        break # for i, m
                elif i + 1 >= conf.MaxHistoryInitialMessages: break # for i, m

            messages_current, message_range = mm[::-1], mm[::-1] # Set ascending
            if center_message_i is not None:
                self._center_message_index = len(mm) - center_message_i-1
        else:
            messages_current, message_range = messages[from_index or 0:], messages[:]

        self._chat = chat
        self._db = db
        self._messages_current = messages_current
        self._messages = message_range
        self._filter["daterange"] = [
            messages_current[ 0]["datetime"].date() if messages_current else None,
            messages_current[-1]["datetime"].date() if messages_current else None
        ]
        self.RefreshMessages(center_message_id)


    def NextFromAuthor(self, author, current, direction=+1):
        """
        Scrolls to another message from same author.

        @param   author     skypename of author to find
        @param   current    message index in current content to start from
        @param   direction  positive for forwards, negative for backwards
        """
        step = -1 if direction < 0 else +1
        idx, mm = current + step, self._messages_current or []
        msg = mm[idx] if 0 <= idx < len(mm) else None
        while msg:
            if msg["author"] == author:
                guibase.status()
                return self.FocusMessage(msg["id"])
            idx += step
            msg = mm[idx] if 0 <= idx < len(mm) else None
        label = "previous" if direction < 0 else "next"
        name = self._db.get_author_name({"author": author})
        guibase.status("No %s message from %s found in current view.", label, name)


    def NextTime(self, unit, current, direction=+1):
        """
        Scrolls to message from next time unit.

        @param   unit       "day" or "week" or "month"
        @param   current    message index in current content to start from
        @param   direction  positive for forwards, negative for backwards
        """
        if unit not in ("day", "week", "month"): return
        guibase.status()
        step = -1 if direction < 0 else +1
        idx, mm = current + step, self._messages_current or []
        msg0 = mm[current] if 0 <= current < len(mm) else None
        if not msg0: return

        def make_threshold(dt, step):
            dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
            if   "day"   == unit:
                result = dt + step * datetime.timedelta(days=1)
            elif "week"  == unit:
                dtmon = dt - datetime.timedelta(days=dt.weekday())
                result = dtmon + step * datetime.timedelta(days=7)
            elif "month" == unit:
                delta = datetime.timedelta(days=32 if step > 0 else 1)
                result = (dt.replace(day=1) + step * delta).replace(day=1)
            return result

        threshold, shifted = make_threshold(msg0["datetime"], step), False
        msg, prevmsg = (mm[idx] if 0 <= idx < len(mm) else None), None
        while step > 0 and msg:
            if msg["datetime"] >= threshold: return self.FocusMessage(msg["id"])
            idx += step
            msg = mm[idx] if 0 <= idx < len(mm) else None
        while step < 0 and msg:
            if msg["datetime"] < threshold and prevmsg:
                return self.FocusMessage(prevmsg["id"])
            if msg["datetime"] < threshold and not shifted:
                # Lacks immediate previous unit, reorient threshold
                threshold, shifted = make_threshold(msg["datetime"], step=0), True
            idx += step
            msg, prevmsg = (mm[idx] if 0 <= idx < len(mm) else None), msg
        if step < 0 and prevmsg and prevmsg["datetime"] >= threshold:
            # Corner case: content starts with threshold
            return self.FocusMessage(prevmsg["id"])
        label = "previous" if direction < 0 else "next"
        guibase.status("No %s %s found in current view.", label, unit)


    def FocusMessage(self, message_id, select=True):
        """Selects and scrolls the specified message into view."""
        if message_id not in self._message_positions: return
        linetopos, linenumber = self.PositionFromLine, self.DocLineFromVisible
        viewport = [linetopos(linenumber(self.FirstVisibleLine + x))
                    for x in [0, self.LinesOnScreen()]]
        if viewport[1] < 0: viewport[1] = self.LastPosition
        pos, padding = self._message_positions[message_id], 50
        if not viewport[0] <= pos[0] <= viewport[1]:
            for p in pos[::-1]:
                # Ensure that both ends of the selection are visible
                self.STC.CurrentPos = p + padding
                self.EnsureCaretVisible()
                padding = -padding
            self.STC.SetSelection(p, p)
        if select: self.STC.SetSelection(*pos)


    def GetFocusedMessage(self, selectedonly=False):
        """
        Returns the ID of the currently selected or the first visible message,
        and whether the message text was selected.

        @param   selectedonly  whether to look at selected message only
        @return  (message ID, is_selected)
        """
        linetopos, linenumber = self.PositionFromLine, self.DocLineFromVisible
        viewport = [linetopos(linenumber(self.FirstVisibleLine + x))
                    for x in [0, self.LinesOnScreen()]]
        if viewport[1] < 0: viewport[1] = self.LastPosition
        selection, curpos, selected = self.GetSelection(), None, False
        if selection[0] != selection[1] \
        and any(viewport[0] <= x <= viewport[1] for x in selection):
            curpos, selected = selection[0], True
        elif not selectedonly:
            curpos = viewport[0]
        if curpos is None: return None, False # No position to check

        for m_id in self._message_positions:
            if curpos < self._message_positions[m_id][1]: return m_id, selected
        return None, False


    def IsMessageFilteredOut(self, message):
        """
        Returns whether the specified message does not pass the current filter.
        """
        result = False
        if (self._filter.get("participants")
        and message["author"] not in self._filter["participants"]
        and set(self._filter["participants"]) != 
        set([p["identity"] for p in self._chat["participants"]])):
            # Last condition is to check if participants filter is applied.
            result = True
        elif (all(self._filter.get("daterange") or [0])
        and not (self._filter["daterange"][0] <= message["datetime"].date()
        <= self._filter["daterange"][1])):
            result = True
        elif "text" in self._filter and self._filter["text"]:
            if not self._filtertext_rgx:
                escaped = re.escape(self._filter["text"])
                self._filtertext_rgx = re.compile(escaped, re.IGNORECASE)
            if (not message["body_xml"]
            or not self._filtertext_rgx.search(message["body_xml"])):
                result = True
        return result


    def IsMessageShown(self, message_id):
        """Returns whether the specified message is currently shown."""
        return (message_id in self._message_positions)


    def GetMessage(self, index):
        """
        Returns the message at the specified index in the currently shown
        messages.

        @param   index  list index (negative starts from end)
        """
        if index < 0: index %= len(self._messages_current or [])
        if index >= len(self._messages_current or []): return None
        return self._messages_current[index]


    def GetMessages(self):
        """Returns a list of all the currently shown messages."""
        return list(self._messages_current or [])


    def GetRetrievedMessages(self):
        """Returns a list of all retrieved messages."""
        return list(self._messages or [])


    def GetVisibleMessages(self):
        """Returns a list of messages currently visible in viewport."""
        ids = []
        linetopos, linenumber = self.PositionFromLine, self.DocLineFromVisible
        viewport = [linetopos(linenumber(self.FirstVisibleLine + x))
                    for x in [0, self.LinesOnScreen()]]
        if viewport[1] < 0: viewport[1] = self.LastPosition
        for m_id in self._message_positions:
            m_pos = self._message_positions[m_id]
            if any(viewport[0] <= x <= viewport[1] for x in m_pos) \
            or m_pos[0] < viewport[0] and m_pos[1] > viewport[1]:
                ids.append(m_id)
            if m_pos[0] > viewport[1]: break # for m_id
        return map(self._message_map.get, ids)


    def SetFilter(self, filter_data):
        """
        Sets the filter to use for the current chat. Does not refresh messages.

        @param   filter_data  None or {"daterange":
                              (datetime, datetime), "text": text in message,
                              "participants": [skypename1, ]}
        """
        filter_data = filter_data or {}
        if not util.cmp_dicts(filter_data, self._filter):
            self._filter = copy.deepcopy(filter_data)
            self._filtertext_rgx = None
            self._messages_current = None
    def GetFilter(self):
        return copy.deepcopy(self._filter)
    Filter = property(GetFilter, SetFilter, doc=\
        """
        The filter to use for the current chat. {"daterange":
        (datetime, datetime), "text": text in message,
        "participants": [skypename1, ]}
        """
    )


    def ApplyFilter(self, daterange=None, text=None, participants=None,
                    datelabel=None):
        """
        Sets and applies filter for the current chat.

        @param   daterange     [date1, date2] or None to skip
        @param   text          search string or None to skip
        @param   participants  [identity, ] or None to skip
        @param   datelabel     datelinks label like "1 year", if any
        """
        myfilter = dict(daterange=daterange, text=text, participants=participants)
        myfilter = {k: v for k, v in myfilter.items() if v is not None}
        if not myfilter or util.cmp_dicts(myfilter, self._filter): return

        busy = controls.BusyPanel(self._page or self.Parent,
                                  "Filtering messages.")
        try:
            self._datelink_last = datelabel
            if self._page:
                if daterange:
                    self._page.range_date.SetValues(*daterange)
                    self._page.chat_filter["daterange"] = daterange
                if text is not None:
                    self._page.edit_filtertext.Value = text
                    self._page.chat_filter["text"]   = text
                if participants:
                    plist = self._page.list_participants
                    for i in range(plist.GetItemCount()):
                        identity = plist.GetItemData(i)["identity"]
                        c = plist.GetItem(i)
                        c.Check(identity in participants)
                        plist.SetItem(c)
                    plist.Refresh()
                    self._page.chat_filter["participants"] = participants
            self.Filter = dict(self.Filter, **myfilter)
            self.RefreshMessages(), self.ScrollToLine(0)
            if self._page:
                self._page.populate_chat_statistics()
                self._page.list_timeline.Populate(*self.GetTimelineData())
        finally:
            busy.Close()


    def GetStatisticsData(self):
        """
        Returns the statistics collected during last Populate(), or {}.
        """
        return self._parser.get_collected_stats() if self._parser else {}


    def GetTimelineData(self):
        """
        Returns the timeline collected during last Populate(), or {}.
        """
        return self._parser.get_timeline_stats() if self._parser else {}


    def ClearAll(self):
        """Delete all text in the document."""
        readonly_state = self.GetReadOnly()
        self.SetReadOnly(False)
        wx.stc.StyledTextCtrl.ClearAll(self.STC)
        self.SetReadOnly(readonly_state)



class SqliteGridBase(wx.grid.GridTableBase):
    """
    Table base for wx.grid.Grid, can take its data from a single table, or from
    the results of any SELECT query.
    """

    """How many rows to seek ahead for query grids."""
    SEEK_CHUNK_LENGTH = 100


    def __init__(self, db, table="", sql=""):
        super(SqliteGridBase, self).__init__()
        self.is_query = bool(sql)
        self.db = db
        self.sql = sql
        self.table = table
        # ID here is a unique value identifying rows in this object,
        # no relation to table data
        self.idx_all = [] # An ordered list of row identifiers in rows_all
        self.rows_all = {} # Unfiltered, unsorted rows {id: row, }
        self.rows_current = [] # Currently shown (filtered/sorted) rows
        self.rowids = {} # SQLite table rowids, used for UPDATE and DELETE
        self.idx_changed = set() # set of indices for changed rows in rows_all
        self.rows_backup = {} # For changed rows {id: original_row, }
        self.idx_new = [] # Unsaved added row indices
        self.rows_deleted = {} # Uncommitted deleted rows {id: deleted_row, }
        self.rowid_name = "ROWID%s" % int(time.time()) # Avoid collisions
        self.iterator_index = -1
        self.sort_ascending = False
        self.sort_column = None # Index of column currently sorted by
        self.filters = {} # {col: value, }
        self.attrs = {} # {"new": wx.grid.GridCellAttr, }

        if not self.is_query:
            self.sql = "SELECT rowid AS %s, * FROM %s" % (self.rowid_name, table)
        self.row_iterator = db.execute(self.sql)
        if self.is_query:
            self.columns = [{"name": c[0], "type": "TEXT"}
                            for c in self.row_iterator.description or ()]
            # Doing some trickery here: we can only know the row count when we have
            # retrieved all the rows, which is preferrable not to do at first,
            # since there is no telling how much time it can take. Instead, we
            # update the row count chunk by chunk.
            self.row_count = self.SEEK_CHUNK_LENGTH
            TYPES = dict((v, k) for k, vv in {"INTEGER": six.integer_types + (bool, ),
                         "REAL": (float, )}.items() for v in vv)
            # Seek ahead on rows and get column information from first values
            try: self.SeekToRow(self.SEEK_CHUNK_LENGTH - 1)
            except Exception: pass
            if self.rows_current:
                for col in self.columns:
                    value = self.rows_current[0][col["name"]]
                    col["type"] = TYPES.get(type(value), col["type"])
        else:
            self.columns = db.get_table_columns(table)
            self.row_count = next(db.execute("SELECT COUNT(*) AS rows FROM %s"
                                  % table))["rows"]


    def GetColLabelValue(self, col):
        label = self.columns[col]["name"]
        if col == self.sort_column:
            label += u" ↑" if self.sort_ascending else u" ↓"
        if col in self.filters:
            if "TEXT" == self.columns[col]["type"]:
                label += "\nlike \"%s\"" % self.filters[col]
            else:
                label += "\n= %s" % self.filters[col]
        return label


    def GetNumberRows(self):
        result = self.row_count
        if self.filters:
            result = len(self.rows_current)
        return result


    def GetNumberCols(self):
        return len(self.columns)


    def SeekAhead(self, to_end=False):
        """
        Seeks ahead on the query cursor, by the chunk length or until the end.

        @param   to_end  if True, retrieves all rows
        """
        seek_count = self.row_count + self.SEEK_CHUNK_LENGTH - 1
        if to_end:
            seek_count = sys.maxsize
        self.SeekToRow(seek_count)


    def SeekToRow(self, row):
        """Seeks ahead on the row iterator to the specified row."""
        rows_before = len(self.rows_all)
        while self.row_iterator and (self.iterator_index < row):
            rowdata = None
            try:
                rowdata = next(self.row_iterator)
            except Exception:
                pass
            if rowdata:
                idx = id(rowdata)
                if not self.is_query:
                    self.rowids[idx] = rowdata[self.rowid_name]
                    del rowdata[self.rowid_name]
                rowdata["__id__"] = idx
                rowdata["__changed__"] = False
                rowdata["__new__"] = False
                rowdata["__deleted__"] = False
                self.rows_all[idx] = rowdata
                self.rows_current.append(rowdata)
                self.idx_all.append(idx)
                self.iterator_index += 1
            else:
                self.row_iterator = None
        if self.is_query:
            if (self.row_count != self.iterator_index + 1):
                self.row_count = self.iterator_index + 1
                self.NotifyViewChange(rows_before)


    def GetValue(self, row, col):
        value = None
        if row < self.row_count:
            self.SeekToRow(row)
            if row < len(self.rows_current):
                value = self.rows_current[row][self.columns[col]["name"]]
                if sys.version_info < (3, ) and type(value) is buffer:  # Py2
                    value = str(value).decode("latin1")
        if value and "BLOB" == self.columns[col]["type"]:
            # Blobs need special handling, as the text editor does not
            # support control characters or null bytes.
            value = value.encode("unicode-escape").decode("latin1")
        return value if value is not None else ""


    def GetRow(self, row):
        """Returns the data dictionary of the specified row."""
        value = None
        if row < self.row_count:
            self.SeekToRow(row)
            if row < len(self.rows_current):
                value = self.rows_current[row]
        return value


    def GetRowIterator(self):
        """Returns a separate iterator producing all grid rows."""
        """
        Returns an iterator producing all grid rows, in current sort order and
        matching current filter, making an extra query if all not retrieved yet.
        """
        if self.row_iterator is None: return iter(self.rows_current) # All retrieved

        def generator(cursor):
            try:
                for row in self.rows_current: yield row

                row, index = next(cursor), 0
                while row and index < self.iterator_index + 1:
                    row, index = next(cursor), index + 1
                while row:
                    while row and not self._is_row_unfiltered(row): row = next(cursor)
                    if row: yield row
                    row = next(cursor)
            except (GeneratorExit, StopIteration): pass

        sql = self.sql if self.is_query else "SELECT * FROM %s" % self.table
        return generator(self.db.execute(sql))


    def SetValue(self, row, col, val):
        if not (self.is_query) and (row < self.row_count):
            accepted = False
            col_value = None
            if "INTEGER" == self.columns[col]["type"]:
                if not val: # Set column to NULL
                    accepted = True
                else:
                    try:
                        # Allow user to enter a comma for decimal separator.
                        valc = val.replace(",", ".")
                        col_value = float(valc) if ("." in valc) else int(val)
                        accepted = True
                    except Exception:
                        pass
            elif "BLOB" == self.columns[col]["type"]:
                # Blobs need special handling, as the text editor does not
                # support control characters or null bytes.
                try:
                    col_value = val.decode("unicode-escape")
                    accepted = True
                except UnicodeError: # Text is not valid escaped Unicode
                    pass
            else:
                col_value = val
                accepted = True
            if accepted:
                self.SeekToRow(row)
                data = self.rows_current[row]
                idx = data["__id__"]
                if not data["__new__"]:
                    if idx not in self.rows_backup:
                        # Backup only existing rows, new rows will be dropped
                        # on rollback anyway.
                        self.rows_backup[idx] = data.copy()
                    data["__changed__"] = True
                    self.idx_changed.add(idx)
                data[self.columns[col]["name"]] = col_value
                if self.View: self.View.Refresh()


    def IsChanged(self):
        """Returns whether there is uncommitted changed data in this grid."""
        lengths = map(len, [self.idx_changed, self.idx_new, self.rows_deleted])
        return any(lengths)


    def GetChangedInfo(self):
        """Returns an info string about the uncommited changes in this grid."""
        infolist = []
        values = {"new": len(self.idx_new), "changed": len(self.idx_changed),
                  "deleted": len(self.rows_deleted), }
        for label, count in values.items():
            if count:
                infolist.append("%s %s row%s"
                    % (count, label, "s" if count != 1 else ""))
        return ", ".join(infolist)


    def GetAttr(self, row, col, kind):
        if not self.attrs:
            for n in ["new", "default", "row_changed", "cell_changed",
            "newblob", "defaultblob", "row_changedblob", "cell_changedblob"]:
                self.attrs[n] = wx.grid.GridCellAttr()
            for n in ["new", "newblob"]:
                self.attrs[n].SetBackgroundColour(conf.GridRowInsertedColour)
            for n in ["row_changed", "row_changedblob"]:
                self.attrs[n].SetBackgroundColour(conf.GridRowChangedColour)
            for n in ["cell_changed", "cell_changedblob"]:
                self.attrs[n].SetBackgroundColour(conf.GridCellChangedColour)
            for n in ["newblob", "defaultblob",
            "row_changedblob", "cell_changedblob"]:
                self.attrs[n].SetEditor(wx.grid.GridCellAutoWrapStringEditor())
        # Sanity check, UI controls can still be referring to a previous table
        col = min(col, len(self.columns) - 1)

        blob = "blob" if (self.columns[col]["type"].lower() == "blob") else ""
        attr = self.attrs["default%s" % blob]
        if row < len(self.rows_current):
            if self.rows_current[row]["__changed__"]:
                idx = self.rows_current[row]["__id__"]
                value = self.rows_current[row][self.columns[col]["name"]]
                backup = self.rows_backup[idx][self.columns[col]["name"]]
                if backup != value:
                    attr = self.attrs["cell_changed%s" % blob]
                else:
                    attr = self.attrs["row_changed%s" % blob]
            elif self.rows_current[row]["__new__"]:
                attr = self.attrs["new%s" % blob]
        attr.IncRef()
        return attr


    def InsertRows(self, row, numRows):
        """Inserts new, unsaved rows at position 0 (row is ignored)."""
        rows_before = len(self.rows_current)
        for i in range(numRows):
            # Construct empty dict from column names
            rowdata = dict((col["name"], None) for col in self.columns)
            idx = id(rowdata)
            rowdata["__id__"] = idx
            rowdata["__changed__"] = False
            rowdata["__new__"] = True
            rowdata["__deleted__"] = False
            # Insert rows at the beginning, so that they can be edited
            # immediately, otherwise would need to retrieve all rows first.
            self.idx_all.insert(0, idx)
            self.rows_current.insert(0, rowdata)
            self.rows_all[idx] = rowdata
            self.idx_new.append(idx)
        self.row_count += numRows
        self.NotifyViewChange(rows_before)
        return True


    def DeleteRows(self, row, numRows):
        """Deletes rows from a specified position."""
        if row + numRows - 1 < self.row_count:
            self.SeekToRow(row + numRows - 1)
            rows_before = len(self.rows_current)
            for i in range(numRows):
                data = self.rows_current[row]
                idx = data["__id__"]
                del self.rows_current[row]
                if idx in self.rows_backup:
                    # If row was changed, switch to its backup data
                    data = self.rows_backup[idx]
                    del self.rows_backup[idx]
                    self.idx_changed.remove(idx)
                if not data["__new__"]:
                    # Drop new rows on delete, rollback can't restore them.
                    data["__changed__"] = False
                    data["__deleted__"] = True
                    self.rows_deleted[idx] = data
                else:
                    self.idx_new.remove(idx)
                    self.idx_all.remove(idx)
                    del self.rows_all[idx]
                self.row_count -= numRows
            self.NotifyViewChange(rows_before)
        return True


    def NotifyViewChange(self, rows_before):
        """
        Notifies the grid view of a change in the underlying grid table if
        current row count is different.
        """
        if self.View:
            args = None
            rows_now = len(self.rows_current)
            if rows_now < rows_before:
                args = [self, wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED,
                        rows_now, rows_before - rows_now]
            elif rows_now > rows_before:
                args = [self, wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED,
                        rows_now - rows_before]
            if args:
                self.View.ProcessTableMessage(wx.grid.GridTableMessage(*args))



    def AddFilter(self, col, val):
        """
        Adds a filter to the grid data on the specified column. Ignores the
        value if invalid for the column (e.g. a string for an integer column).

        @param   col   column index
        @param   val   a simple value for filtering. For numeric columns, the
                       value is matched exactly, and for text columns,
                       matched by substring.
        """
        accepted_value = None
        if "INTEGER" == self.columns[col]["type"]:
            try:
                # Allow user to enter a comma for decimal separator.
                accepted_value = float(val.replace(",", ".")) \
                                 if ("." in val or "," in val) \
                                 else int(val)
            except ValueError:
                pass
        else:
            accepted_value = val
        if accepted_value is not None:
            self.filters[col] = accepted_value
            self.Filter()


    def RemoveFilter(self, col):
        """Removes filter on the specified column, if any."""
        if col in self.filters:
            del self.filters[col]
        self.Filter()


    def ClearFilter(self, refresh=True):
        """Clears all added filters."""
        self.filters.clear()
        if refresh:
            self.Filter()


    def ClearSort(self, refresh=True):
        """Clears current sort."""
        self.sort_column = None
        if refresh:
            self.rows_current[:].sort(
                key=lambda x: self.idx_all.index(x["__id__"])
            )
            if self.View:
                self.View.ForceRefresh()


    def ClearAttrs(self):
        """Clears all current row attributes and refreshes grid."""
        self.attrs.clear()
        if not self.View: return
        for row in range(len(self.rows_current)):
            for col in range(len(self.columns)): self.View.RefreshAttr(row, col)
        self.View.Refresh()


    def Filter(self):
        """
        Filters the grid table with the currently added filters.
        """
        self.SeekToRow(self.row_count - 1)
        rows_before = len(self.rows_current)
        del self.rows_current[:]
        for idx in self.idx_all:
            row = self.rows_all[idx]
            if not row["__deleted__"] and self._is_row_unfiltered(row):
                self.rows_current.append(row)
        if self.sort_column is not None:
            self.sort_ascending = not self.sort_ascending
            self.SortColumn(self.sort_column)
        self.NotifyViewChange(rows_before)


    def SortColumn(self, col):
        """
        Sorts the grid data by the specified column, reversing the previous
        sort order, if any.
        """
        self.SeekToRow(self.row_count - 1)
        self.sort_ascending = not self.sort_ascending
        self.sort_column = col
        if 0 <= col < len(self.columns):
            name = self.columns[col]["name"]
            types = set(type(x[name]) for x in self.rows_current)
            if types - set(six.integer_types + (bool, type(None))):  # Not only numeric types
                key = lambda x: x[name].lower() if isinstance(x[name], six.string_types) else \
                                "" if x[name] is None else six.text_type(x[name])
            else:  # Only numeric types
                key = lambda x: -sys.maxsize if x[name] is None else x[name]
            self.rows_current.sort(key=key, reverse=self.sort_ascending)
        if self.View:
            self.View.ForceRefresh()


    def Close(self):
        """Closes the underlying query cursor, if any."""
        try: self.row_iterator.close()
        except Exception: pass
        self.row_iterator = None


    def SaveChanges(self):
        """
        Saves the rows that have been changed in this table. Drops undo-cache.
        """
        try:
            for idx in self.idx_changed.copy():
                row = self.rows_all[idx]
                self.db.update_row(self.table, row, self.rows_backup[idx],
                                   self.rowids.get(idx))
                row["__changed__"] = False
                self.idx_changed.remove(idx)
                del self.rows_backup[idx]
            # Save all newly inserted rows
            pks = [c["name"] for c in self.columns if c["pk"]]
            col_map = dict((c["name"], c) for c in self.columns)
            for idx in self.idx_new[:]:
                row = self.rows_all[idx]
                insert_id = self.db.insert_row(self.table, row)
                if len(pks) == 1 and row[pks[0]] in (None, ""):
                    if "INTEGER" == col_map[pks[0]]["type"]:
                        # Autoincremented row: update with new value
                        row[pks[0]] = insert_id
                    else: # For non-integers, insert returns ROWID
                        self.rowids[idx] = insert_id
                row["__new__"] = False
                self.idx_new.remove(idx)
            # Deleted all newly deleted rows
            for idx, row in self.rows_deleted.copy().items():
                self.db.delete_row(self.table, row, self.rowids.get(idx))
                del self.rows_deleted[idx]
                del self.rows_all[idx]
                self.idx_all.remove(idx)
        except Exception as e:
            guibase.status("Error saving changes in %s.", self.table)
            logger.exception("Error saving changes in %s.", self.table)
            wx.MessageBox(util.format_exc(e), conf.Title,
                          wx.OK | wx.ICON_WARNING)
        if self.View: self.View.Refresh()


    def UndoChanges(self):
        """Undoes the changes made to the rows in this table."""
        rows_before = len(self.rows_current)
        # Restore all changed row data from backup
        for idx in self.idx_changed.copy():
            row = self.rows_backup[idx]
            row["__changed__"] = False
            self.rows_all[idx].update(row)
            self.idx_changed.remove(idx)
            del self.rows_backup[idx]
        # Discard all newly inserted rows
        for idx in self.idx_new[:]:
            row = self.rows_all[idx]
            del self.rows_all[idx]
            if row in self.rows_current: self.rows_current.remove(row)
            self.idx_new.remove(idx)
            self.idx_all.remove(idx)
        # Undelete all newly deleted items
        for idx, row in self.rows_deleted.items():
            row["__deleted__"] = False
            del self.rows_deleted[idx]
            if self._is_row_unfiltered(row):
                self.rows_current.append(row)
            self.row_count += 1
        self.NotifyViewChange(rows_before)
        if self.View: self.View.Refresh()


    def _is_row_unfiltered(self, rowdata):
        """
        Returns whether the row is not filtered out by the current filtering
        criteria, if any.
        """
        is_unfiltered = True
        for col, filter_value in self.filters.items():
            column_data = self.columns[col]
            if "INTEGER" == column_data["type"]:
                is_unfiltered &= (filter_value == rowdata[column_data["name"]])
            elif "TEXT" == column_data["type"]:
                str_value = (rowdata[column_data["name"]] or "").lower()
                is_unfiltered &= str_value.find(filter_value.lower()) >= 0
        return is_unfiltered



class ChatContentTimeline(wx.html.SimpleHtmlListBox):
    """
    Listbox for showing quick date selection for ChatContentSTC.
    """
    LINE_FORMATS = {
        "year":  '<font color="%(FgColour)s" size=5><table width="100%%"><tr><td nowrap>%(label)s</td><td align="right"><font color="%(DisabledColour)s" size=1>%(count)s</font></td></tr></table></font>',
        "month": '<font color="%(FgColour)s"><table width="100%%"><tr><td nowrap><font size=4>&nbsp;%(label)s </font><font size=2>%(label2)s</font></td><td align="right"><font color="%(DisabledColour)s" size=1>%(count)s</font></td></tr></table></font>',
        "day":   '<font color="%(FgColour)s"><table width="100%%"><tr><td nowrap><font size=4>%(label)s </font><font size=2>%(label2)s</font></td><td align="right"><font color="%(DisabledColour)s" size=1>%(count)s</font></td></tr></table></font>',
        "date":  '<font color="%(FgColour)s" size=3><table width="100%%"><tr><td nowrap>&nbsp;&nbsp;&nbsp;&nbsp;%(label)s<sup>%(label2)s</sup></td><td align="right"><font color="%(DisabledColour)s" size=1>%(count)s</font></td></tr></table></font>',
        "hour":  '<font color="%(FgColour)s" size=3><table width="100%%"><tr><td nowrap>&nbsp;&nbsp;&nbsp;&nbsp;%(label)s</td><td align="right"><font color="%(DisabledColour)s" size=1>%(count)s</font></td></tr></table></font>',
        "week":  '<font color="%(FgColour)s" size=2><table width="100%%"><tr><td nowrap>&nbsp;&nbsp;&nbsp;&nbsp;%(label)s</td><td align="right"><font color="%(DisabledColour)s" size=1>%(count)s</font></td></tr></table></font>',
    }
    LINE_FORMATS_HIGHLIGHT = {
        "year":  '<font color="%(FgColour)s" size=5><table width="100%%"><tr><td nowrap><b>%(label)s</b></td><td align="right"><font color="%(DisabledColour)s" size=1>%(count)s</font></td></tr></table></font>',
        "month": '<font color="%(FgColour)s"><table width="100%%"><tr><td nowrap><font size=4>&nbsp;%(label)s </font><font size=2><b>%(label2)s</b></font></td><td align="right"><font color="%(DisabledColour)s" size=1>%(count)s</font></td></tr></table></font>',
        "day":   '<font color="%(FgColour)s"><table width="100%%"><tr><td nowrap><font size=4>%(label)s </font><font size=2><b>%(label2)s</b></font></td><td align="right"><font color="%(DisabledColour)s" size=1>%(count)s</font></td></tr></table></font>',
        "date":  '<font color="%(FgColour)s" size=3><table width="100%%"><tr><td nowrap>&nbsp;&nbsp;&nbsp;&nbsp;<b>%(label)s<sup>%(label2)s</b></sup></td><td align="right"><font color="%(DisabledColour)s" size=1>%(count)s</font></td></tr></table></font>',
        "hour":  '<font color="%(FgColour)s" size=3><table width="100%%"><tr><td nowrap>&nbsp;&nbsp;&nbsp;&nbsp;<b>%(label)s</b></td><td align="right"><font color="%(DisabledColour)s" size=1>%(count)s</font></td></tr></table></font>',
        "week":  '<font color="%(FgColour)s" size=2><table width="100%%"><tr><td nowrap>&nbsp;&nbsp;&nbsp;&nbsp;<b>%(label)s</b></td><td align="right"><font color="%(DisabledColour)s" size=1>%(count)s</font></td></tr></table></font>',
    }


    def __init__(self, parent, id=wx.ID_ANY, pos=wx.DefaultPosition,
                 size=wx.DefaultSize):
        super(ChatContentTimeline, self).__init__(parent, id, pos, size)
        self._timeline = []      # [{dt, label, unit, message, ?label2}, ]
        self._units = ()         # (top unit, ?subunit)
        self._highlights = set() # [index of highlighted row, ]
        self._tracking = True    # Scroll highlights into view
        ColourManager.Manage(self, "BackgroundColour", "BgColour")
        self.Bind(wx.EVT_LISTBOX, self._OnSelect)


    def Populate(self, timeline, units):
        """
        Populates timeline from parser stats.

        @param   timeline  [{dt, label, unit, messages, ?label2}]
        """
        self.Set([])
        self._highlights.clear()
        self._timeline[:] = [dict(x, message=x["messages"][0]) for x in timeline]
        self._units       = units
        for x in self._timeline: x.pop("messages")
        self.RefreshItems()


    def GetMessage(self, index):
        """Returns message ID for item at specified index."""
        if index < 0: index %= len(self._timeline)
        if index >= len(self._timeline): return None
        return self._timeline[index]["message"]


    def RefreshItems(self):
        """Redraws all current items."""
        if not self.IsShownOnScreen(): return

        count0, selected0 = self.RowCount, self.Selection
        pos0 = self.GetScrollPos(wx.VERTICAL)
        self.Freeze()
        try:
            self.Set([])
            for i, ddict in enumerate(self._timeline):
                FORMATS = self.LINE_FORMATS_HIGHLIGHT if i in self._highlights \
                          else self.LINE_FORMATS
                label = FORMATS[ddict["unit"]] % dict(vars(conf), **ddict)
                self.Append(label)
            if count0:
                self.Selection = selected0
                self.ScrollToRow(pos0)
            else: self.ScrollToRow(-1)
        finally: self.Thaw()


    def RefreshItem(self, index):
        """Redraws the specified row."""
        FORMATS = self.LINE_FORMATS_HIGHLIGHT if index in self._highlights \
                  else self.LINE_FORMATS
        ddict = self._timeline[index]
        label = FORMATS[ddict["unit"]] % dict(vars(conf), **ddict)
        self.SetString(index, label)


    def HighlightRows(self, messages):
        """Highlights the rows that cover message timestamps."""
        highlights, rooti = set(), None
        dates = [x["dt"] for x in self._timeline] + [datetime.datetime.max]
        for m in messages:
            for i, dt1 in enumerate(dates[:-1]):
                if self._timeline[i]["unit"] != self._units[-1]: rooti = i
                dt2 = dates[i + 1] if dates[i + 1] != dt1 else dates[i + 2]
                if dt1 <= m["datetime"] < dt2:
                    highlights.add(i)
                    if rooti is not None: highlights.add(rooti)
                if dates[i + 1] > m["datetime"]: break # for i, dt1
        if highlights == self._highlights: return

        unhighlight = self._highlights - highlights
        dohighlight = highlights - self._highlights
        self._highlights = highlights
        if not self.IsShownOnScreen(): return

        self.Freeze()
        try:
            for i in unhighlight: self.RefreshItem(i)
            for i in dohighlight: self.RefreshItem(i)
            if not self._tracking: return

            # Skip root lines, as they can have more children than fits in view
            tracklines = sorted(i for i in highlights
                                if self._timeline[i]["unit"] == self._units[-1])
            vspan = self.VisibleBegin, self.VisibleEnd
            # Scroll highlights into view, plus one row of padding
            if not all(vspan[0] <= i - 1 <= vspan[1] and 
                       vspan[0] <= i + 1 <= vspan[1] for i in tracklines):
                if all(vspan[0] < i for i in tracklines): # Downward
                    self.ScrollRows(tracklines[-1] - vspan[1] + 1)
                else: self.ScrollToRow(max(0, tracklines[0] - 1))
        finally: self.Thaw()


    def GetVisibleEnd(self):
        """Returns the index of the last fully visible row."""

        # GetVisibleEnd default implementation is imprecise
        h, maxh, lineprev = 0, self.Size.Height, self.FirstVisibleLine
        for line in range(self.FirstVisibleLine, self.RowCount):
            h += self.OnGetRowHeight(line)
            if h > maxh: return lineprev
            lineprev = line
        return lineprev
    VisibleEnd = property(GetVisibleEnd)


    def GetSelectedTextColour(self, *args, **kwargs):
        """Override virtual function to force proper highlight colour."""
        return ColourManager.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT)


    def _OnSelect(self, event):
        """Handler for selecting an item, skips scroll on next highlight."""
        event.Skip()
        self._tracking = False
        wx.CallLater(500, lambda: self and setattr(self, "_tracking", True))



class DayHourDialog(wx.Dialog):
    """Popup dialog for entering two values, days and hours."""

    def __init__(self, parent, message, caption, days, hours):
        wx.Dialog.__init__(self, parent=parent, title=caption, size=(250, 200))

        vbox = self.Sizer = wx.BoxSizer(wx.VERTICAL)

        self.text_days = wx.SpinCtrl(parent=self, style=wx.ALIGN_LEFT,
            size=(200, -1), value=str(days), min=-sys.maxsize, max=sys.maxsize
        )
        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        hbox1.AddStretchSpacer()
        hbox1.Add(wx.StaticText(parent=self, label="Days:"),
            flag=wx.ALIGN_CENTER_VERTICAL)
        hbox1.Add(self.text_days, border=5, flag=wx.LEFT)

        self.text_hours = wx.SpinCtrl(parent=self, style=wx.ALIGN_LEFT,
           size=(200, -1), value=str(hours), min=-sys.maxsize, max=sys.maxsize)
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        hbox2.AddStretchSpacer()
        hbox2.Add(wx.StaticText(parent=self, label="Hours:"),
                  flag=wx.ALIGN_CENTER_VERTICAL)
        hbox2.Add(self.text_hours, border=5, flag=wx.LEFT)

        button_ok = wx.Button(self, label="OK")
        button_cancel = wx.Button(self, label="Cancel", id=wx.ID_CANCEL)
        hbox3 = wx.BoxSizer(wx.HORIZONTAL)
        hbox3.AddStretchSpacer()
        hbox3.Add(button_ok, border=5, flag=wx.RIGHT)
        hbox3.Add(button_cancel, border=5, flag=wx.RIGHT)

        vbox.Add(
            wx.StaticText(parent=self, label=message), border=10, flag=wx.ALL)
        vbox.AddSpacer(5)
        vbox.Add(
            hbox1, border=5, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.GROW)
        vbox.Add(
            hbox2, border=5, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.GROW)
        vbox.Add(wx.StaticLine(self), border=5, proportion=1,
                 flag=wx.LEFT | wx.RIGHT | wx.GROW)
        vbox.Add(hbox3, border=5, flag=wx.ALL | wx.GROW)

        button_ok.SetDefault()
        button_ok.Bind(wx.EVT_BUTTON, lambda e: self.EndModal(wx.ID_OK))
        button_cancel.Bind(wx.EVT_BUTTON, lambda e:self.EndModal(wx.ID_CANCEL))

        self.Layout()
        self.Size = self.GetEffectiveMinSize()
        self.CenterOnParent()


    def GetValues(self):
        """Returns the entered days and hours as a tuple of integers."""
        days = self.text_days.Value
        hours = self.text_hours.Value
        return days, hours



class AboutDialog(wx.Dialog):
 
    def __init__(self, parent, content):
        wx.Dialog.__init__(self, parent, title="About %s" % conf.Title,
                           style=wx.CAPTION | wx.CLOSE_BOX)
        self.content = content
        html = self.html = wx.html.HtmlWindow(self)
        button_update = wx.Button(self, label="Check for &updates")
        button_feedback = wx.Button(self, label="Send &feedback")

        html.SetPage(content() if callable(content) else content)
        html.BackgroundColour = ColourManager.GetColour(wx.SYS_COLOUR_WINDOW)
        html.Bind(wx.html.EVT_HTML_LINK_CLICKED,
                  lambda e: webbrowser.open(e.GetLinkInfo().Href))
        button_update.Bind(wx.EVT_BUTTON, parent.on_check_update)
        button_feedback.Bind(wx.EVT_BUTTON, self.OnOpenFeedback)

        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.Sizer.Add(html, proportion=1, flag=wx.GROW)
        sizer_buttons = self.CreateButtonSizer(wx.OK)
        sizer_buttons.Insert(0, button_update, border=50, flag=wx.RIGHT)
        sizer_buttons.Insert(1, button_feedback, border=50, flag=wx.RIGHT)
        self.Sizer.Add(sizer_buttons, border=8, flag=wx.ALIGN_CENTER_HORIZONTAL | wx.ALL)
        self.Bind(wx.EVT_SYS_COLOUR_CHANGED, self.OnSysColourChange)

        self.Layout()
        self.Size = (self.Size[0], html.VirtualSize[1] + 70)
        self.CenterOnParent()


    def OnOpenFeedback(self, event):
        """Handler for feedback button, closes dialog and opens feedback dialog."""
        wx.CallAfter(self.Parent.on_open_feedback)
        self.Close()


    def OnSysColourChange(self, event):
        """Handler for system colour change, refreshes content."""
        event.Skip()
        def dorefresh():
            if not self: return
            self.html.SetPage(self.content() if callable(self.content) else self.content)
            self.html.BackgroundColour = ColourManager.GetColour(wx.SYS_COLOUR_WINDOW)
            self.html.ForegroundColour = ColourManager.GetColour(wx.SYS_COLOUR_BTNTEXT)
        wx.CallAfter(dorefresh) # Postpone to allow conf to update



class LoginDialog(wx.Dialog, wx_accel.AutoAcceleratorMixIn):
    """Dialog that asks for username and password."""
 
    def __init__(self, parent, title="Log in"):
        wx.Dialog.__init__(self, parent, title=title,
                           style=wx.CAPTION | wx.CLOSE_BOX)

        label_name = wx.StaticText(self, label="&Username:", name="label_user")
        edit_name  = self.edit_name = wx.TextCtrl(self, size=(200, -1), name="user")
        label_pass = wx.StaticText(self, label="&Password:", name="label_pass")
        edit_pass  = self.edit_pass = wx.TextCtrl(self, size=(200, -1), style=wx.TE_PASSWORD, name="pass")

        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_ctrls = wx.FlexGridSizer(cols=2, vgap=3, hgap=10)
        sizer_buttons = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        sizer_ctrls.Add(label_name, flag=wx.ALIGN_CENTER_VERTICAL)
        sizer_ctrls.Add(edit_name, flag=wx.GROW)
        sizer_ctrls.Add(label_pass, flag=wx.ALIGN_CENTER_VERTICAL)
        sizer_ctrls.Add(edit_pass, flag=wx.GROW)
        self.Sizer.Add(sizer_ctrls,   border=8, proportion=1, flag=wx.ALL | wx.GROW)
        self.Sizer.Add(sizer_buttons, border=8, flag=wx.ALIGN_CENTER_HORIZONTAL | wx.ALL)
        self.Layout()
        self.Fit()
        self.CenterOnParent()
        self.UpdateAccelerators()
        edit_name.SetFocus()


    def GetUsername(self):
        return self.edit_name.Value.strip()
    Username = property(GetUsername)


    def GetPassword(self):
        return self.edit_pass.Value.strip()
    Password = property(GetPassword)


def check_media_export_login(db):
    """
    Returns whether db can login to download shared files to subfolder for export
    or whether user confirms to proceed without login information.
    """
    if (conf.SharedImageAutoDownload or conf.SharedAudioVideoAutoDownload
        or conf.SharedFileAutoDownload) \
    and not db.live.is_logged_in() \
    and not conf.Login.get(db.filename, {}).get("password") and wx.OK != wx.MessageBox(
        "You have selected to export HTML with shared files in subfolder, "
        "but the database does not have login information "
        "for downloading media.\n\nAre you sure you want to continue?",
        conf.Title, wx.OK | wx.CANCEL | wx.ICON_INFORMATION
    ): return False
    return True


def messageBox(message, title, style):
    """
    Shows a non-native message box, with no bell sound for any style, returning
    the message box result code."""
    dlg = wx.lib.agw.genericmessagedialog.GenericMessageDialog(
        None, message, title, style
    )
    result = dlg.ShowModal()
    dlg.Destroy()
    return result
