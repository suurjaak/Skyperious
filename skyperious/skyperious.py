# -*- coding: utf-8 -*-
"""
Skyperious UI application main window class and project-specific UI classes.

------------------------------------------------------------------------------
This file is part of Skyperious - a Skype database viewer and merger.
Released under the MIT License.

@author      Erki Suurjaak
@created     26.11.2011
@modified    28.04.2015
------------------------------------------------------------------------------
"""
import ast
import base64
import collections
import copy
import datetime
import hashlib
import inspect
import math
import os
import re
import shutil
import sys
import textwrap
import time
import traceback
import urllib
import webbrowser

import wx
import wx.gizmos
import wx.grid
import wx.html
import wx.lib
import wx.lib.agw.fmresources
import wx.lib.agw.genericmessagedialog
import wx.lib.agw.labelbook
import wx.lib.agw.flatmenu
import wx.lib.agw.flatnotebook
import wx.lib.agw.ultimatelistctrl
import wx.lib.newevent
import wx.lib.scrolledpanel
import wx.stc

# Core functionality can work without these modules
try:
    import Skype4Py
except ImportError:
    Skype4Py = None
try:
    from dateutil.relativedelta import relativedelta
except ImportError:
    relativedelta = None

from third_party import step

import conf
import controls
import export
import guibase
import images
import main
import skypedata
import support
import templates
import util
import workers


"""Custom application events for worker results."""
WorkerEvent, EVT_WORKER = wx.lib.newevent.NewEvent()
ContactWorkerEvent, EVT_CONTACT_WORKER = wx.lib.newevent.NewEvent()
DetectionWorkerEvent, EVT_DETECTION_WORKER = wx.lib.newevent.NewEvent()
OpenDatabaseEvent, EVT_OPEN_DATABASE = wx.lib.newevent.NewEvent()


class MainWindow(guibase.TemplateFrameMixIn, wx.Frame):
    """Skyperious main window."""

    TRAY_ICON = (images.Icon16x16_32bit if "linux2" != sys.platform 
                 else images.Icon24x24_32bit)

    def __init__(self):
        wx.Frame.__init__(self, parent=None, title=conf.Title, size=conf.WindowSize)
        guibase.TemplateFrameMixIn.__init__(self)

        self.init_colours()
        self.db_filename = None # Current selected file in main list
        self.db_filenames = {}  # added DBs {filename: {size, last_modified,
                                #            account, chats, messages, error},}
        self.dbs = {}           # Open databases {filename: SkypeDatabase, }
        self.db_pages = {}      # {DatabasePage: SkypeDatabase, }
        self.merger_pages = {}  # {MergerPage: (SkypeDatabase, SkypeDatabase),}
        self.page_merge_latest = None # Last opened merger page
        self.page_db_latest = None    # Last opened database page
        # List of Notebook pages user has visited, used for choosing page to
        # show when closing one.
        self.pages_visited = []
        self.db_drag_start = None

        icons = images.get_appicons()
        self.SetIcons(icons)

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

        self.create_page_main(notebook)
        self.page_log = self.create_log_panel(notebook)
        notebook.AddPage(self.page_log, "Log")
        notebook.RemovePage(self.notebook.GetPageCount() - 1) # Hide log window
        # Kludge for being able to close log window repeatedly, as DatabasePage
        # or MergerPage get automatically deleted on closing.
        self.page_log.is_hidden = True

        sizer.Add(notebook, proportion=1, flag=wx.GROW | wx.RIGHT | wx.BOTTOM)
        self.create_menu()

        self.dialog_selectfolder = wx.DirDialog(
            parent=self,
            message="Choose a directory where to search for databases",
            defaultPath=os.getcwd(),
            style=wx.DD_DIR_MUST_EXIST | wx.RESIZE_BORDER)
        self.dialog_savefile = wx.FileDialog(
            parent=self, defaultDir=os.getcwd(), defaultFile="",
            style=wx.FD_SAVE | wx.RESIZE_BORDER)
        self.dialog_search = controls.EntryDialog(
            parent=self, title="Find in %s" % conf.Title, label="Search:",
            emptyvalue="Find in last database..",
            tooltip="Find in last database..")
        self.dialog_search.Bind(wx.EVT_COMMAND_ENTER, self.on_tray_search)
        if conf.SearchHistory and conf.SearchHistory[-1:] != [""]:
            self.dialog_search.Value = conf.SearchHistory[-1]
        self.dialog_search.SetChoices(list(filter(None, conf.SearchHistory)))
        self.dialog_search.SetIcons(icons)

        self.skype_handler = SkypeHandler() if Skype4Py else None
        # Memory file system for showing images in wx.HtmlWindow
        self.memoryfs = {"files": {}, "handler": wx.MemoryFSHandler()}
        wx.FileSystem_AddHandler(self.memoryfs["handler"])
        abouticon = "skyperious.png" # Program icon shown in About window
        raw = base64.b64decode(images.Icon48x48_32bit.data)
        self.memoryfs["handler"].AddFile(abouticon, raw, wx.BITMAP_TYPE_PNG)
        self.memoryfs["files"][abouticon] = 1
        # Screenshots look better with colouring if system has off-white colour
        tint_colour = wx.NamedColour(conf.BgColour)
        tint_factor = [((4 * x) % 256) / 255. for x in tint_colour]
        # Images shown on the default search content page
        for name in ["Search", "Chats", "Info", "Tables", "SQL", "Contacts"]:
            bmp = getattr(images, "Help" + name, None)
            if not bmp: continue # Continue for name in [..]
            bmp = bmp.Image.AdjustChannels(*tint_factor)
            raw = util.img_wx_to_raw(bmp)
            filename = "Help%s.png" % name
            self.memoryfs["handler"].AddFile(filename, raw, wx.BITMAP_TYPE_PNG)
            self.memoryfs["files"][filename] = 1

        self.worker_detection = \
            workers.DetectDatabaseThread(self.on_detect_databases_callback)
        self.Bind(EVT_DETECTION_WORKER, self.on_detect_databases_result)
        self.Bind(EVT_OPEN_DATABASE, self.on_open_database_event)

        self.Bind(wx.EVT_CLOSE, self.on_exit)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_MOVE, self.on_move)
        notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_change_page)
        notebook.Bind(wx.lib.agw.flatnotebook.EVT_FLATNOTEBOOK_PAGE_CLOSING,
                      self.on_close_page)
        # Register Ctrl-F4 and Ctrl-W close handlers
        id_close = wx.NewId()
        def on_close_hotkey(event):
            notebook and notebook.DeletePage(notebook.GetSelection())
        notebook.SetAcceleratorTable(wx.AcceleratorTable([
            (wx.ACCEL_CTRL, k, id_close) for k in (ord('W'), wx.WXK_F4)]))
        notebook.Bind(wx.EVT_MENU, on_close_hotkey, id=id_close)


        class FileDrop(wx.FileDropTarget):
            """A simple file drag-and-drop handler for application window."""
            def __init__(self, window):
                wx.FileDropTarget.__init__(self)
                self.window = window

            def OnDropFiles(self, x, y, filenames):
                # CallAfter to allow UI to clear up the dragged icons
                wx.CallAfter(self.ProcessFiles, filenames)

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
        else:
            self.button_detect.SetFocus()

        self.trayicon = wx.TaskBarIcon()
        if conf.TrayIconEnabled:
            self.trayicon.SetIcon(self.TRAY_ICON.Icon, conf.Title)
        self.trayicon.Bind(wx.EVT_TASKBAR_LEFT_DCLICK, self.on_toggle_iconize)
        self.trayicon.Bind(wx.EVT_TASKBAR_LEFT_DOWN, self.on_open_tray_search)
        self.trayicon.Bind(wx.EVT_TASKBAR_RIGHT_DOWN, self.on_open_tray_menu)

        if conf.WindowIconized:
            conf.WindowIconized = False
            wx.CallAfter(self.on_toggle_iconize)
        else:
            self.Show(True)
        wx.CallLater(20000, self.update_check)


    def init_colours(self):
        """Update configuration colours with current system theme values."""
        colourhex = lambda index: (wx.SystemSettings.GetColour(index)
                                   .GetAsString(wx.C2S_HTML_SYNTAX))
        conf.FgColour = colourhex(wx.SYS_COLOUR_BTNTEXT)
        conf.BgColour = colourhex(wx.SYS_COLOUR_WINDOW)
        conf.DisabledColour = colourhex(wx.SYS_COLOUR_GRAYTEXT)
        conf.WidgetColour = colourhex(wx.SYS_COLOUR_BTNFACE)
        if "#FFFFFF" != conf.BgColour: # Potential default colour mismatch
            conf.DBListForegroundColour = conf.FgColour
            conf.DBListBackgroundColour = conf.BgColour
            conf.LinkColour = colourhex(wx.SYS_COLOUR_HOTLIGHT)
            conf.SkypeLinkColour = colourhex(wx.SYS_COLOUR_HOTLIGHT)
            conf.MainBgColour = conf.WidgetColour
            conf.MessageTextColour = conf.FgColour
            conf.HelpCodeColour = colourhex(wx.SYS_COLOUR_HIGHLIGHT)
            conf.HelpBorderColour = colourhex(wx.SYS_COLOUR_ACTIVEBORDER)
            conf.MergeHtmlBackgroundColour = conf.BgColour

            # Hack: monkey-patch FlatImageBook with non-hardcoded background
            class HackContainer(wx.lib.agw.labelbook.ImageContainer):
                BRUSH1, BRUSH2 = wx.WHITE_BRUSH, wx.Brush(conf.BgColour)
                def OnPaint(self, event):
                    wx.WHITE_BRUSH = HackContainer.BRUSH2
                    try: result = HackContainer.__base__.OnPaint(self, event)
                    finally: wx.WHITE_BRUSH = HackContainer.BRUSH1
                    return result
            wx.lib.agw.labelbook.ImageContainer = HackContainer


    def update_check(self):
        """
        Checks for an updated Skyperious version if sufficient time
        from last check has passed, and opens a dialog for upgrading
        if new version available. Schedules a new check on due date.
        """
        if not conf.UpdateCheckAutomatic: 
            return
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
            except (TypeError, ValueError):
                pass
        # Schedule a check for due date, should the program run that long.
        millis = min(sys.maxint, util.timedelta_seconds(interval) * 1000)
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
                if self.db_filename: # Load database focused in dblist
                    page = self.load_database_page(self.db_filename)
                elif self.dbs: # Load an open database
                    page = self.load_database_page(list(self.dbs)[0])
                elif conf.RecentFiles:
                    page = self.load_database_page(conf.RecentFiles[0])
            if page:
                page.edit_searchall.Value = self.dialog_search.Value
                page.on_searchall(None)
                for i in range(self.notebook.GetPageCount()):
                    if self.notebook.GetPage(i) == page:
                        if self.notebook.GetSelection() != i:
                            self.notebook.SetSelection(i)
                            self.update_notebook_header()
                        break # break for i in range(self.notebook.GetPage..
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

        menu.AppendItem(item_search)
        menu.AppendItem(item_toggle)
        menu.AppendSeparator()
        menu.AppendItem(item_icon)
        menu.AppendItem(item_console)
        menu.AppendSeparator()
        menu.AppendItem(item_exit)
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
        conf.WindowSize = [-1, -1] if self.IsMaximized() else self.Size[:]
        conf.save()
        event.Skip()
        l, p = self.list_db, self.panel_db_main.Parent # Right panel scroll
        fn = lambda: self and (p.Layout(), l.SetColumnWidth(0, l.Size[1] - 5))
        wx.CallAfter(fn)


    def on_move(self, event):
        """Handler for window move event, saves position."""
        conf.WindowPosition = event.Position[:]
        conf.save()
        event.Skip()


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


    def on_dragstop_list_db(self, event):
        """Handler for stopping drag in the database list, rearranges list."""
        start, stop = self.db_drag_start, max(1, event.GetIndex())
        if start and start != stop:
            filename = self.list_db.GetItemText(start)
            self.list_db.DeleteItem(start)
            idx = stop if start > stop else stop - 1
            self.list_db.InsertImageStringItem(idx, filename, [1])
            fgcolour = wx.NamedColour(conf.DBListForegroundColour)
            bgcolour = wx.NamedColour(conf.DBListBackgroundColour)
            self.list_db.SetItemBackgroundColour(idx, bgcolour)
            self.list_db.SetItemTextColour(idx, fgcolour)
            self.list_db.Select(idx)
        self.db_drag_start = None


    def on_dragstart_list_db(self, event):
        """Handler for dragging items in the database list, cancels dragging."""
        if event.GetIndex():
            self.db_drag_start = event.GetIndex()
        else:
            self.db_drag_start = None
            self.on_cancel_drag_list_db(event)


    def on_cancel_drag_list_db(self, event):
        """Handler for dragging items in the database list, cancels dragging."""
        class HackEvent(object): # UltimateListCtrl hack to cancel drag.
            def __init__(self, pos=wx.Point()): self._position = pos
            def GetPosition(self): return self._position
        try:
            wx.CallAfter(self.list_db.Children[0].DragFinish, HackEvent())
        except: raise


    def create_page_main(self, notebook):
        """Creates the main page with database list and buttons."""
        page = self.page_main = wx.Panel(notebook)
        page.BackgroundColour = conf.MainBgColour
        notebook.AddPage(page, "Databases")
        sizer = page.Sizer = wx.BoxSizer(wx.HORIZONTAL)

        agw_style = (wx.LC_REPORT | wx.LC_NO_HEADER |
                     wx.LC_SINGLE_SEL | wx.BORDER_NONE)
        if hasattr(wx.lib.agw.ultimatelistctrl, "ULC_USER_ROW_HEIGHT"):
            agw_style |= wx.lib.agw.ultimatelistctrl.ULC_USER_ROW_HEIGHT
        list_db = self.list_db = wx.lib.agw.ultimatelistctrl. \
            UltimateListCtrl(parent=page, agwStyle=agw_style)
        list_db.MinSize = 400, -1 # Maximize-restore would resize width to 100
        list_db.InsertColumn(0, "")
        il = wx.ImageList(*images.ButtonHome.Bitmap.Size)
        il.Add(images.ButtonHome.Bitmap)
        il.Add(images.ButtonListDatabase.Bitmap)
        list_db.AssignImageList(il, wx.IMAGE_LIST_SMALL)
        list_db.InsertImageStringItem(0, "Home", [0])
        list_db.TextColour = wx.NamedColour(conf.DBListForegroundColour)
        list_bgcolour = wx.NamedColour(conf.DBListBackgroundColour)
        list_db.BackgroundColour = list_bgcolour
        list_db.SetItemBackgroundColour(0, list_bgcolour)
        if hasattr(list_db, "SetUserLineHeight"):
            h = images.ButtonListDatabase.Bitmap.Size[1]
            list_db.SetUserLineHeight(int(h * 1.5))
        list_db.Select(0)

        panel_right = wx.lib.scrolledpanel.ScrolledPanel(page)
        panel_right.Sizer = wx.BoxSizer(wx.HORIZONTAL)

        panel_main = self.panel_db_main = wx.Panel(panel_right)
        panel_detail = self.panel_db_detail = wx.Panel(panel_right)
        panel_main.Sizer = wx.BoxSizer(wx.VERTICAL)
        panel_detail.Sizer = wx.BoxSizer(wx.VERTICAL)

        # Create main page label and buttons
        label_main = wx.StaticText(panel_main,
                                   label="Welcome to %s" % conf.Title)
        label_main.SetForegroundColour(conf.SkypeLinkColour)
        label_main.Font = wx.Font(14, wx.FONTFAMILY_SWISS,
            wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, face=self.Font.FaceName)
        BUTTONS_MAIN = [
            ("opena", "&Open a database..", images.ButtonOpenA, 
             "Choose a database from your computer to open."),
            ("detect", "Detect databases", images.ButtonDetect,
             "Auto-detect databases from user folders."),
            ("folder", "&Import from folder.", images.ButtonFolder,
             "Select a folder where to look for SQLite databases "
             "(*.db files)."),
            ("missing", "Remove missing", images.ButtonRemoveMissing,
             "Remove non-existing files from the database list."),
            ("clear", "C&lear list", images.ButtonClear,
             "Clear the current database list."), ]
        for name, label, img, note in BUTTONS_MAIN:
            button = controls.NoteButton(panel_main, label, note, img.Bitmap)
            setattr(self, "button_" + name, button)
            exec("button_%s = self.button_%s" % (name, name)) in {}, locals()
        button_missing.Hide(); button_clear.Hide()

        # Create detail page labels, values and buttons
        label_db = self.label_db = wx.TextCtrl(parent=panel_detail, value="",
            style=wx.NO_BORDER | wx.TE_MULTILINE | wx.TE_RICH)
        label_db.Font = wx.Font(12, wx.FONTFAMILY_SWISS,
            wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, face=self.Font.FaceName)
        label_db.BackgroundColour = panel_detail.BackgroundColour
        label_db.SetEditable(False)

        sizer_labels = wx.FlexGridSizer(cols=2, vgap=3, hgap=10)
        LABELS = [("path", "Location"), ("size", "Size"),
                  ("modified", "Last modified"), ("account", "Skype user"),
                  ("chats", "Conversations"), ("messages", "Messages")]
        for field, title in LABELS:
            lbltext = wx.StaticText(parent=panel_detail, label="%s:" % title)
            valtext = wx.TextCtrl(parent=panel_detail, value="",
                                  size=(300, -1), style=wx.NO_BORDER)
            valtext.BackgroundColour = panel_detail.BackgroundColour
            valtext.SetEditable(False)
            lbltext.ForegroundColour = conf.DisabledColour
            sizer_labels.Add(lbltext, border=5, flag=wx.LEFT)
            sizer_labels.Add(valtext, proportion=1, flag=wx.GROW)
            setattr(self, "label_" + field, valtext)

        BUTTONS_DETAIL = [
            ("open", "&Open", images.ButtonOpen, 
             "Open the database for searching and exploring."),
            ("compare", "Compare and &merge", images.ButtonCompare,
             "Choose another database to compare with, in order to merge "
             "their differences."),
            ("export", "&Export messages", images.ButtonExport,
             "Export all conversations from the database as "
             "HTML, text or spreadsheet."),
            ("saveas", "Save &as..", images.ButtonSaveAs,
             "Save a copy of the database under another name."),
            ("remove", "Remove", images.ButtonRemove,
             "Remove this database from the list."), ]
        for name, label, img, note in BUTTONS_DETAIL:
            button = controls.NoteButton(panel_detail, label, note, img.Bitmap)
            setattr(self, "button_" + name, button)
            exec("button_%s = self.button_%s" % (name, name)) # Hack local name

        children = list(panel_main.Children) + list(panel_detail.Children)
        for c in [panel_main, panel_detail] + children:
            c.BackgroundColour = page.BackgroundColour 
        panel_right.SetupScrolling(scroll_x=False)
        panel_detail.Hide()

        list_db.Bind(wx.EVT_LIST_ITEM_SELECTED,  self.on_select_list_db)
        list_db.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_open_from_list_db)
        list_db.Bind(wx.EVT_CHAR_HOOK,           self.on_list_db_key)
        list_db.Bind(wx.lib.agw.ultimatelistctrl.EVT_LIST_BEGIN_DRAG,
                     self.on_dragstart_list_db)
        list_db.Bind(wx.lib.agw.ultimatelistctrl.EVT_LIST_END_DRAG,
                     self.on_dragstop_list_db)
        list_db.Bind(wx.lib.agw.ultimatelistctrl.EVT_LIST_BEGIN_RDRAG,
                     self.on_cancel_drag_list_db)
        button_opena.Bind(wx.EVT_BUTTON,         self.on_open_database)
        button_detect.Bind(wx.EVT_BUTTON,        self.on_detect_databases)
        button_folder.Bind(wx.EVT_BUTTON,        self.on_add_from_folder)
        button_missing.Bind(wx.EVT_BUTTON,       self.on_remove_missing)
        button_clear.Bind(wx.EVT_BUTTON,         self.on_clear_databases)
        button_open.Bind(wx.EVT_BUTTON,          self.on_open_current_database)
        button_compare.Bind(wx.EVT_BUTTON,       self.on_compare_databases)
        button_export.Bind(wx.EVT_BUTTON,        self.on_export_database_menu)
        button_saveas.Bind(wx.EVT_BUTTON,        self.on_save_database_as)
        button_remove.Bind(wx.EVT_BUTTON,        self.on_remove_database)

        panel_main.Sizer.Add(label_main, border=10, flag=wx.ALL)
        panel_main.Sizer.Add((0, 10))
        panel_main.Sizer.Add(button_opena, flag=wx.GROW)
        panel_main.Sizer.Add(button_detect, flag=wx.GROW)
        panel_main.Sizer.Add(button_folder, flag=wx.GROW)
        panel_main.Sizer.AddStretchSpacer()
        panel_main.Sizer.Add(button_missing, flag=wx.GROW)
        panel_main.Sizer.Add(button_clear, flag=wx.GROW)
        panel_detail.Sizer.Add(label_db, border=10, flag=wx.ALL | wx.GROW)
        panel_detail.Sizer.Add(sizer_labels, border=10, flag=wx.ALL | wx.GROW)
        panel_detail.Sizer.Add((0, 10))
        panel_detail.Sizer.Add(button_open, flag=wx.GROW)
        panel_detail.Sizer.Add(button_compare, flag=wx.GROW)
        panel_detail.Sizer.Add(button_export, flag=wx.GROW)
        panel_detail.Sizer.AddStretchSpacer()
        panel_detail.Sizer.Add(button_saveas, flag=wx.GROW)
        panel_detail.Sizer.Add(button_remove, flag=wx.GROW)
        panel_right.Sizer.Add(panel_main, proportion=1, flag=wx.GROW)
        panel_right.Sizer.Add(panel_detail, proportion=1, flag=wx.GROW)
        sizer.Add(list_db, border=10, proportion=6, flag=wx.ALL | wx.GROW)
        sizer.Add(panel_right, border=10, proportion=4, flag=wx.ALL | wx.GROW)
        for filename in conf.DBFiles:
            self.update_database_list(filename)


    def create_menu(self):
        """Creates the program menu."""
        menu = wx.MenuBar()
        self.SetMenuBar(menu)

        menu_file = wx.Menu()
        menu.Append(menu_file, "&File")

        menu_open_database = self.menu_open_database = menu_file.Append(
            id=wx.NewId(), text="&Open database...\tCtrl-O",
            help="Choose a database file to open."
        )
        menu_recent = self.menu_recent = wx.Menu()
        menu_file.AppendMenu(id=wx.NewId(), text="&Recent databases",
            submenu=menu_recent, help="Recently opened databases.")
        menu_file.AppendSeparator()
        menu_options = self.menu_options = \
            menu_file.Append(id=wx.NewId(), text="&Advanced options",
                help="Edit advanced program options")
        menu_iconize = self.menu_iconize = \
            menu_file.Append(id=wx.NewId(), text="Minimize to &tray",
                help="Minimize %s window to notification area" % conf.Title)
        menu_exit = self.menu_exit = \
            menu_file.Append(id=wx.NewId(), text="E&xit\tAlt-X", help="Exit")

        menu_help = wx.Menu()
        menu.Append(menu_help, "&Help")

        menu_update = self.menu_update = menu_help.Append(id=wx.NewId(),
            text="Check for &updates",
            help="Check whether a new version of %s is available" % conf.Title)
        menu_feedback = self.menu_feedback = menu_help.Append(id=wx.NewId(),
            text="Send &feedback",
            help="Send feedback or report a problem to program author")
        menu_homepage = self.menu_homepage = menu_help.Append(id=wx.NewId(),
            text="Go to &homepage",
            help="Open the %s homepage, %s" % (conf.Title, conf.HomeUrl))
        menu_help.AppendSeparator()
        menu_log = self.menu_log = menu_help.Append(id=wx.NewId(),
            kind=wx.ITEM_CHECK, text="Show &log window",
            help="Show/hide the log messages window")
        menu_console = self.menu_console = menu_help.Append(id=wx.NewId(),
            kind=wx.ITEM_CHECK, text="Show Python &console\tCtrl-E",
            help="Show/hide a Python shell environment window")
        menu_help.AppendSeparator()
        menu_tray = self.menu_tray = menu_help.Append(id=wx.NewId(),
            kind=wx.ITEM_CHECK, text="Display &icon in notification area",
            help="Show/hide %s icon in system tray" % conf.Title)
        menu_autoupdate_check = self.menu_autoupdate_check = menu_help.Append(
            id=wx.NewId(), kind=wx.ITEM_CHECK,
            text="Automatic up&date check",
            help="Automatically check for program updates periodically")
        menu_error_reporting = self.menu_error_reporting = menu_help.Append(
            id=wx.NewId(), kind=wx.ITEM_CHECK,
            text="Automatic &error reporting",
            help="Automatically report software errors to program author")
        menu_help.AppendSeparator()
        menu_about = self.menu_about = menu_help.Append(
            id=wx.NewId(), text="&About %s" % conf.Title,
            help="Show program information and copyright")

        self.history_file = wx.FileHistory(conf.MaxRecentFiles)
        self.history_file.UseMenu(menu_recent)
        # Reverse list, as FileHistory works like a stack
        [self.history_file.AddFileToHistory(f) for f in conf.RecentFiles[::-1]]
        wx.EVT_MENU_RANGE(self, wx.ID_FILE1, wx.ID_FILE1 + conf.MaxRecentFiles,
                          self.on_recent_file)
        menu_tray.Check(conf.TrayIconEnabled)
        menu_autoupdate_check.Check(conf.UpdateCheckAutomatic)
        menu_error_reporting.Check(conf.ErrorReportsAutomatic)

        self.Bind(wx.EVT_MENU, self.on_open_database, menu_open_database)
        self.Bind(wx.EVT_MENU, self.on_open_options, menu_options)
        self.Bind(wx.EVT_MENU, self.on_exit, menu_exit)
        self.Bind(wx.EVT_MENU, self.on_toggle_iconize, menu_iconize)
        self.Bind(wx.EVT_MENU, self.on_check_update, menu_update)
        self.Bind(wx.EVT_MENU, self.on_open_feedback, menu_feedback)
        self.Bind(wx.EVT_MENU, self.on_menu_homepage, menu_homepage)
        self.Bind(wx.EVT_MENU, self.on_showhide_log, menu_log)
        self.Bind(wx.EVT_MENU, self.on_showhide_console, menu_console)
        self.Bind(wx.EVT_MENU, self.on_toggle_trayicon, menu_tray)
        self.Bind(wx.EVT_MENU, self.on_toggle_autoupdate_check,
                  menu_autoupdate_check)
        self.Bind(wx.EVT_MENU, self.on_toggle_error_reporting,
                  menu_error_reporting)
        self.Bind(wx.EVT_MENU, self.on_about, menu_about)


    def on_toggle_error_reporting(self, event):
        """Handler for toggling automatic error reporting, changes conf."""
        conf.ErrorReportsAutomatic = event.IsChecked()
        conf.save()


    def on_toggle_autoupdate_check(self, event):
        """Handler for toggling automatic update checking, changes conf."""
        conf.UpdateCheckAutomatic = event.IsChecked()
        conf.save()


    def on_list_db_key(self, event):
        """
        Handler for pressing a key in dblist, loads selected database on Enter
        and removes from list on Delete.
        """
        if self.list_db.GetFirstSelected() > 0 and not event.AltDown() \
        and event.KeyCode in [wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER]:
            self.load_database_page(self.db_filename)
        elif event.KeyCode in [wx.WXK_DELETE] and self.db_filename:
            self.on_remove_database(None)
        event.Skip()


    def on_open_feedback(self, event):
        """Handler for clicking to send feedback, opens the feedback form."""
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
        text = step.Template(templates.ABOUT_TEXT).expand()
        AboutDialog(self, text).ShowModal()


    def on_check_update(self, event):
        """
        Handler for checking for updates, starts a background process for
        checking for and downloading the newest version.
        """
        if not support.update_window:
            main.status("Checking for new version of %s.", conf.Title)
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
        if not self:
            return
        support.update_window = True
        main.status("")
        if check_result:
            version, url, changes = check_result
            MAX = 1000
            changes = changes[:MAX] + ".." if len(changes) > MAX else changes
            main.status_flash("New %s version %s available.",
                              conf.Title, version)
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
            conf.save()
        support.update_window = None


    def on_detect_databases(self, event):
        """
        Handler for clicking to auto-detect databases, starts the
        detection in a background thread.
        """
        if self.button_detect.FindFocus() == self.button_detect:
            self.list_db.SetFocus()
        main.logstatus("Searching local computer for databases..")
        self.button_detect.Enabled = False
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
                    main.log("Detected database %s.", f)
        if "count" in result:
            name = ("" if result["count"] else "additional ") + "database"
            main.logstatus_flash("Detected %s.", 
                                  util.plural(name, result["count"]))
        if result.get("done", False):
            self.button_detect.Enabled = True
            wx.Bell()


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
                conf.save()
            data = collections.defaultdict(lambda: None)
            if os.path.exists(filename):
                data["size"] = os.path.getsize(filename)
                data["last_modified"] = datetime.datetime.fromtimestamp(
                                        os.path.getmtime(filename))
            data_old = self.db_filenames.get(filename)
            if not data_old or data_old["size"] != data["size"] \
            or data_old["last_modified"] != data["last_modified"]:
                if filename not in self.db_filenames:
                    self.db_filenames[filename] = data
                    idx = self.list_db.GetItemCount()
                    self.list_db.InsertImageStringItem(idx, filename, [1])
                    fgcolour = wx.NamedColour(conf.DBListForegroundColour)
                    bgcolour = wx.NamedColour(conf.DBListBackgroundColour)
                    self.list_db.SetItemBackgroundColour(idx, bgcolour)
                    self.list_db.SetItemTextColour(idx, fgcolour)
                    # self is not shown: form creation time, reselect last file
                    if not self.Shown and filename in conf.LastSelectedFiles:
                        self.list_db.Select(idx)
                        def scroll_to_selected():
                            if idx < self.list_db.GetCountPerPage(): return
                            lh = self.list_db.GetUserLineHeight()
                            dy = (idx - self.list_db.GetCountPerPage() / 2) * lh
                            self.list_db.ScrollList(0, dy)
                        wx.CallAfter(lambda: self and scroll_to_selected())
                    result = True

        self.button_missing.Shown = (self.list_db.GetItemCount() > 1)
        self.button_clear.Shown = (self.list_db.GetItemCount() > 1)
        if self.Shown:
            self.list_db.SetColumnWidth(0, self.list_db.Size.width - 5)
        return result


    def on_clear_databases(self, event):
        """Handler for clicking to clear the database list."""
        if (self.list_db.GetItemCount() > 1) and wx.OK == wx.MessageBox(
            "Are you sure you want to clear the list of all databases?",
            conf.Title, wx.OK | wx.CANCEL | wx.ICON_QUESTION
        ):
            while self.list_db.GetItemCount() > 1:
                self.list_db.DeleteItem(1)
            del conf.DBFiles[:]
            del conf.LastSelectedFiles[:]
            del conf.RecentFiles[:]
            conf.LastSearchResults.clear()
            while self.history_file.Count:
                self.history_file.RemoveFileFromHistory(0)
            self.db_filenames.clear()
            conf.save()
            self.update_database_list()


    def on_save_database_as(self, event):
        """Handler for clicking to save a copy of a database in the list."""
        original = self.db_filename
        if not os.path.exists(original):
            wx.MessageBox(
                "The file \"%s\" does not exist on this computer." % original,
                conf.Title, wx.OK | wx.ICON_INFORMATION
            )
            return

        dialog = wx.FileDialog(parent=self, message="Save a copy..",
            defaultDir=os.path.split(original)[0],
            defaultFile=os.path.basename(original),
            style=wx.FD_OVERWRITE_PROMPT | wx.FD_SAVE | wx.RESIZE_BORDER
        )
        if wx.ID_OK == dialog.ShowModal():
            wx.YieldIfNeeded() # Allow UI to refresh
            newpath = dialog.GetPath()
            success = False
            try:
                shutil.copyfile(original, newpath)
                success = True
            except Exception as e:
                main.log("%r when trying to copy %s to %s.",
                         e, original, newpath)
                if self.skype_handler and self.skype_handler.is_running():
                    response = wx.MessageBox(
                        "Could not save a copy of \"%s\" as \"%s\".\n\n"
                        "Probably because Skype is running. "
                        "Close Skype and try again?" % (original, newpath),
                        conf.Title, wx.OK | wx.CANCEL | wx.ICON_WARNING)
                    if wx.OK == response:
                        self.skype_handler.shutdown()
                        func = lambda: shutil.copyfile(original, newpath)
                        success, _ = util.try_until(func, count=3)
                        if not success:
                            wx.MessageBox(
                                "Still could not copy \"%s\" to \"%s\"." %
                                (original, newpath), conf.Title,
                                wx.OK | wx.ICON_WARNING)
                else:
                    wx.MessageBox("Failed to copy \"%s\" to \"%s\"." %
                                  (original, newpath), conf.Title,
                                  wx.OK | wx.ICON_WARNING)
            if success:
                main.logstatus_flash("Saved a copy of %s as %s.",
                                     original, newpath)
                self.update_database_list(newpath)


    def on_remove_database(self, event):
        """Handler for clicking to remove an item from the database list."""
        filename = self.db_filename
        if filename and wx.OK == wx.MessageBox(
            "Remove %s from database list?" % filename,
            conf.Title, wx.OK | wx.CANCEL | wx.ICON_QUESTION
        ):
            if filename in conf.DBFiles:
                conf.DBFiles.remove(filename)
            if filename in conf.LastSelectedFiles:
                conf.LastSelectedFiles.remove(filename)
            if filename in conf.LastSearchResults:
                del conf.LastSearchResults[filename]
            if filename in self.db_filenames:
                del self.db_filenames[filename]
            for i in range(self.list_db.GetItemCount()):
                if self.list_db.GetItemText(i) == filename:
                    self.list_db.DeleteItem(i)
                    break # break for i in range(self.list_db..
            # Remove from recent file history
            historyfiles = [(i, self.history_file.GetHistoryFile(i))
                            for i in range(self.history_file.Count)]
            for i in [i for i, f in historyfiles if f == filename]:
                self.history_file.RemoveFileFromHistory(i)
            self.db_filename = None
            self.list_db.Select(0)
            self.update_database_list()
            conf.save()


    def on_remove_missing(self, event):
        """Handler to remove nonexistent files from the database list."""
        selecteds = range(1, self.list_db.GetItemCount())
        filter_func = lambda i: not os.path.exists(self.list_db.GetItemText(i))
        selecteds = list(filter(filter_func, selecteds))
        filenames = list(map(self.list_db.GetItemText, selecteds))
        for i in range(len(selecteds)):
            # - i, as item count is getting smaller one by one
            selected = selecteds[i] - i
            filename = self.list_db.GetItemText(selected)
            if filename in conf.DBFiles:
                conf.DBFiles.remove(filename)
            if filename in conf.LastSelectedFiles:
                conf.LastSelectedFiles.remove(filename)
            if filename in self.db_filenames:
                del self.db_filenames[filename]
            self.list_db.DeleteItem(selected)
        # Remove from recent file history
        historyfiles = [(i, self.history_file.GetHistoryFile(i))
                        for i in range(self.history_file.Count)]
        for i, f in historyfiles[::-1]: # Work upwards to have unchanged index
            if f in filenames: self.history_file.RemoveFileFromHistory(i)
        conf.save()
        self.update_database_list()


    def on_showhide_log(self, event):
        """Handler for clicking to show/hide the log window."""
        if self.notebook.GetPageIndex(self.page_log) < 0:
            self.notebook.AddPage(self.page_log, "Log")
            self.page_log.is_hidden = False
            self.page_log.Show()
            self.notebook.SetSelection(self.notebook.GetPageCount() - 1)
            self.on_change_page(None)
        else:
            self.page_log.is_hidden = True
            self.notebook.RemovePage(self.notebook.GetPageIndex(self.page_log))
        self.menu_log.Check(not self.page_log.is_hidden)


    def on_export_database_menu(self, event):
        if not export.xlsxwriter:
            return self.on_export_database(None)

        menu = wx.lib.agw.flatmenu.FlatMenu()
        item_sel = wx.lib.agw.flatmenu.FlatMenuItem(menu, wx.NewId(),
               "Export into separate files in one folder "
               "(HTML, text, Excel, or CSV)")
        menu.AppendItem(item_sel)
        item_all = wx.lib.agw.flatmenu.FlatMenuItem(menu, wx.NewId(),
               "Export into a single Excel workbook, with separate sheets")
        menu.AppendItem(item_all)
        for item in menu.GetMenuItems():
            self.Bind(wx.EVT_MENU, self.on_export_database, item)

        sz_btn, pt_btn = event.EventObject.Size, event.EventObject.Position
        pt_btn = event.EventObject.Parent.ClientToScreen(pt_btn)
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

        focused_control = self.FindFocus()
        self.button_export.Enabled = False
        self.dialog_savefile.Message = "Choose folder where to save chat files"
        self.dialog_savefile.Filename = "Filename will be ignored"
        self.dialog_savefile.Wildcard = export.CHAT_WILDCARD
        self.dialog_savefile.WindowStyle ^= wx.FD_OVERWRITE_PROMPT
        if do_singlefile:
            db = self.load_database(self.db_filename)
            formatargs = collections.defaultdict(str)
            formatargs["skypename"] = os.path.basename(self.db_filename)
            if db and db.account: formatargs.update(db.account)
            default = util.safe_filename(conf.ExportDbTemplate % formatargs)
            self.dialog_savefile.Filename = default
            self.dialog_savefile.Message = "Save chats file"
            self.dialog_savefile.Wildcard = export.CHAT_WILDCARD_SINGLEFILE
            self.dialog_savefile.WindowStyle |= wx.FD_OVERWRITE_PROMPT

        if wx.ID_OK == self.dialog_savefile.ShowModal():
            db, files, count, error, errormsg = None, [], 0, False, None

            db = self.load_database(self.db_filename)
            dirname = os.path.dirname(self.dialog_savefile.GetPath())
            if not db:
                error = True
            elif "conversations" not in db.tables:
                error = True
                errormsg = "Cannot export %s. Not a valid Skype database?" % db
            if not error and not do_singlefile:
                extname = export.CHAT_EXTS[self.dialog_savefile.FilterIndex]
                format = extname
                formatargs = collections.defaultdict(str)
                formatargs["skypename"] = os.path.basename(self.db_filename)
                if db.account: formatargs.update(db.account)
                folder = util.safe_filename(conf.ExportDbTemplate % formatargs)
                export_dir = util.unique_path(os.path.join(dirname, folder))
                try:
                    os.mkdir(export_dir)
                except Exception:
                    errormsg = "Failed to create directory %s:\n\n%s" % \
                               (export_dir, traceback.format_exc())
                    error = True
            elif not error:
                index = self.dialog_savefile.FilterIndex
                extname = export.CHAT_EXTS_SINGLEFILE[index]
                format = os.path.basename(self.dialog_savefile.GetPath())
                export_dir = dirname


            if not error:
                chats = db.get_conversations()
                busy = controls.BusyPanel(
                    self, "Exporting all %s from \"%s\"\nas %s\nunder %s." %
                    (util.plural("chat", chats), db.filename,
                    extname.upper(), export_dir))
                wx.SafeYield() # Allow UI to refresh
                try:
                    if not db.has_consumers():
                        db.get_conversations_stats(chats)
                    progressfunc = lambda *args: wx.SafeYield()
                    result = export.export_chats(chats, export_dir, format, db,
                                                 progress=progressfunc)
                    files, count = result
                except Exception:
                    errormsg = "Error exporting chats:\n\n%s" % \
                               traceback.format_exc()
                    error = True
                busy.Close()
            if not error:
                main.logstatus_flash("Exported %s from %s as %s "
                    "under %s.", util.plural("chat", count), db.filename,
                    extname.upper(), export_dir)
            elif errormsg:
                main.logstatus_flash(errormsg)
                wx.MessageBox(errormsg, conf.Title, wx.OK | wx.ICON_WARNING)
                wx.CallAfter(support.report_error, errormsg)
            if db and not db.has_consumers():
                del self.dbs[db.filename]
                db.close()
            if db and not error:
                util.start_file(export_dir if len(files) > 1 else files[0])
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
        if i > 0 and item:
            filename2 = item.GetLabel()
        elif not i: # First menu item: open a file from computer
            dialog = wx.FileDialog(
                parent=self, message="Open", defaultFile="",
                wildcard="SQLite database (*.db)|*.db|All files|*.*",
                style=wx.FD_FILE_MUST_EXIST | wx.FD_OPEN | wx.RESIZE_BORDER)
            dialog.ShowModal()
            filename2 = dialog.GetPath()
        if filename1 == filename2:
            wx.MessageBox("Cannot compare %s with itself." % (filename1),
                          conf.Title, wx.OK | wx.ICON_WARNING)
        else:
            self.compare_databases(filename1, filename2)


    def compare_databases(self, filename1, filename2):
        """Opens the two databases for comparison, if possible."""
        db1, db2, page = None, None, None
        if filename1 and filename2:
            db1 =  self.load_database(filename1)
        if db1:
            db2 = self.load_database(filename2)
        if db1 and db2:
            dbset = set((db1, db2))
            page = next((x for x in self.merger_pages
                         if x and set([x.db1, x.db2]) == dbset), None)
            if not page:
                main.log("Merge page for %s and %s.", db1, db2)
                page = MergerPage(self.notebook, db1, db2,
                       self.get_unique_tab_title("Database comparison"))
                self.merger_pages[page] = (db1, db2)
                self.UpdateAccelerators()
                conf.save()
        elif db1 or db2:
            # Close DB with no owner
            for db in filter(None, [db1, db2]):
                if not db.has_consumers():
                    main.log("Closed database %s." % db.filename)
                    del self.dbs[db.filename]
                    db.close()
        if page:
            for i in range(self.notebook.GetPageCount()):
                if self.notebook.GetPage(i) == page:
                    self.notebook.SetSelection(i)
                    self.update_notebook_header()
                    break # break for i in range(self.notebook..


    def on_compare_databases(self, event):
        """
        Handler for clicking to compare a selected database with another, shows
        a popup menu for choosing the second database file.
        """
        menu = wx.lib.agw.flatmenu.FlatMenu()
        item = wx.lib.agw.flatmenu.FlatMenuItem(menu, wx.NewId(),
               "Select a file from your computer..")
        menu.AppendItem(item)
        recents = [f for f in conf.RecentFiles if f != self.db_filename][:5]
        others = [f for f in conf.DBFiles
                  if f not in recents and f != self.db_filename]
        if recents or others:
            menu.AppendSeparator()
        if recents:
            item = wx.lib.agw.flatmenu.FlatMenuItem(menu, wx.NewId(),
                                                    "Recent files")
            item.Enable(False)
            menu.AppendItem(item)
            for f in recents:
                i = wx.lib.agw.flatmenu.FlatMenuItem(menu, wx.NewId(), f)
                menu.AppendItem(i)
            if others:
                menu.AppendSeparator()
                item = wx.lib.agw.flatmenu.FlatMenuItem(menu, wx.NewId(),
                                                        "Rest of list")
                item.Enable(False)
                menu.AppendItem(item)
        for f in sorted(others):
            item = wx.lib.agw.flatmenu.FlatMenuItem(menu, wx.NewId(), f)
            menu.AppendItem(item)
        for item in menu.GetMenuItems():
            self.Bind(wx.EVT_MENU, self.on_compare_menu, item)

        sz_btn, pt_btn = event.EventObject.Size, event.EventObject.Position
        pt_btn = event.EventObject.Parent.ClientToScreen(pt_btn)
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
        def get_field_doc(name, tree=ast.parse(inspect.getsource(conf))):
            """Returns the docstring immediately before name assignment."""
            for i, node in enumerate(tree.body):
                if i and ast.Assign == type(node) and node.targets[0].id == name:
                    prev = tree.body[i - 1]
                    if ast.Expr == type(prev) and ast.Str == type(prev.value):
                        return prev.value.s.strip()
            return ""

        for name in sorted(conf.OptionalFileDirectives):
            value, help = getattr(conf, name, None), get_field_doc(name)
            default = conf.OptionalFileDirectiveDefaults.get(name)
            if value is None and default is None:
                continue # continue for name
            kind = wx.Size if isinstance(value, (tuple, list)) else type(value)
            dialog.AddProperty(name, value, help, default, kind)
        dialog.Realize()

        if wx.ID_OK == dialog.ShowModal():
            for k, v in dialog.GetProperties():
                # Keep numbers in sane regions
                if type(v) in [int, long]: v = max(1, min(sys.maxint, v))
                setattr(conf, k, v)
            conf.save()
            self.MinSize = conf.MinWindowSize


    def on_open_database(self, event):
        """
        Handler for open database menu or button, displays a file dialog and
        loads the chosen database.
        """
        dialog = wx.FileDialog(
            parent=self, message="Open", defaultFile="",
            wildcard="SQLite database (*.db)|*.db|All files|*.*",
            style=wx.FD_FILE_MUST_EXIST | wx.FD_OPEN | wx.RESIZE_BORDER
        )
        if wx.ID_OK == dialog.ShowModal():
            filename = dialog.GetPath()
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
            folder = self.dialog_selectfolder.GetPath()
            main.logstatus("Detecting databases under %s.", folder)
            count = 0
            for filename in skypedata.find_databases(folder):
                if filename not in self.db_filenames:
                    main.log("Detected database %s.", filename)
                    self.update_database_list(filename)
                    count += 1
            main.logstatus_flash("Detected %s under %s.",
                util.plural("new database", count), folder)


    def on_open_current_database(self, event):
        """Handler for clicking to open selected files from database list."""
        if self.db_filename:
            self.load_database_page(self.db_filename)


    def on_open_from_list_db(self, event):
        """Handler for clicking to open selected files from database list."""
        if event.GetIndex() > 0:
            self.load_database_page(event.GetText())


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
            main.log("Error opening %s.\n\n%s", filename,
                     traceback.format_exc())
            return
        try:
            stats = db.get_general_statistics(full=False)
            if "name" in stats and "skypename" in stats:
                self.label_account.Value = "%(name)s (%(skypename)s)" % stats
            text = "%(chats)s" % stats
            if "lastmessage_chat" in stats:
                text += ", latest %(lastmessage_chat)s" % stats
            self.label_chats.Value = text
            text = "%(messages)s" % stats
            if "lastmessage_dt" in stats:
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
            main.log("Error loading data from %s.\n\n%s", filename,
                     traceback.format_exc())
        if db and not db.has_consumers():
            db.close()
            if filename in self.dbs:
                del self.dbs[filename]


    def on_select_list_db(self, event):
        """Handler for selecting an item in main list, updates info panel."""
        if event.GetIndex() > 0 \
        and event.GetText() != self.db_filename:
            filename = self.db_filename = event.GetText()
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
                    wx.CallLater(10, self.update_database_stats, filename)
            else:
                self.label_size.Value = "File does not exist."
                self.label_size.ForegroundColour = conf.LabelErrorColour
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


    def on_exit(self, event):
        """
        Handler on application exit, asks about unsaved changes, if any.
        """
        do_exit = True
        unsaved_pages = {} # {DatabasePage: filename, }
        merging_pages = [] # [MergerPage title, ]
        for page, db in self.db_pages.items():
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
                "Merging is currently in progress in %s.\nExit anyway? "
                "This can result in corrupt data." % 
                "\n".join(textwrap.wrap(", ".join(merging_pages))),
                conf.Title, wx.OK | wx.CANCEL | wx.ICON_WARNING)
            do_exit = (wx.CANCEL != response)
        if do_exit:
            for page in self.db_pages:
                if not page: continue # continue for page, if dead object
                active_idx = page.notebook.Selection
                if active_idx:
                    conf.LastActivePage[page.db.filename] = active_idx
                elif page.db.filename in conf.LastActivePage:
                    del conf.LastActivePage[page.db.filename]
                page.save_page_conf()
                for worker in page.workers_search.values(): worker.stop()
                page.worker_search_contacts.stop()
            for page in self.merger_pages: page.worker_merge.stop()
            self.worker_detection.stop()

            # Save last selected files in db lists, to reselect them on rerun
            conf.DBFiles = [self.list_db.GetItemText(i)
                            for i in range(1, self.list_db.GetItemCount())]
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
            self.trayicon.Destroy()
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
            unsaved = page.get_unsaved_grids()
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
            page.worker_search_contacts.stop()
            page.save_page_conf()

            if page in self.db_pages:
                del self.db_pages[page]
            page_dbs = [page.db]
            main.log("Closed database tab for %s." % page.db)
            conf.save()
        else:
            if page.is_merging:
                response = wx.MessageBox(
                    "Merging is currently in progress in %s.\n\nClose anyway? "
                    "This can result in corrupt data." % page.title,
                    conf.Title, wx.OK | wx.CANCEL | wx.ICON_WARNING)
                if wx.CANCEL == response:
                    return event.Veto()

            if page in self.merger_pages:
                del self.merger_pages[page]
            page_dbs = [page.db1, page.db2]
            page.worker_merge.stop()
            main.log("Closed comparison tab for %s and %s.",
                     page.db1, page.db2)

        # Close databases, if not used in any other page
        for db in page_dbs:
            db.unregister_consumer(page)
            if not db.has_consumers():
                if db.filename in self.dbs:
                    del self.dbs[db.filename]
                db.close()
                main.log("Closed database %s." % db)
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
            conf.save()


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


    def load_database(self, filename):
        """
        Tries to load the specified database, if not already open, and returns
        it.
        """
        db = self.dbs.get(filename)
        if not db:
            db = None
            if os.path.exists(filename):
                try:
                    db = skypedata.SkypeDatabase(filename)
                except Exception:
                    is_accessible = False
                    try:
                        with open(filename, "rb"):
                            is_accessible = True
                    except Exception:
                        pass
                    if not is_accessible and self.skype_handler \
                    and self.skype_handler.is_running():
                        response = wx.MessageBox(
                            "Could not open %s.\n\n"
                            "Probably because Skype is running. "
                            "Close Skype and try again?" % filename,
                            conf.Title, wx.OK | wx.CANCEL | wx.ICON_WARNING)
                        if wx.OK == response:
                            self.skype_handler.shutdown()
                            try_result, db = util.try_until(lambda:
                                skypedata.SkypeDatabase(filename, False),
                                count=3)
                            if not try_result:
                                wx.MessageBox(
                                    "Still could not open %s." % filename,
                                    conf.Title, wx.OK | wx.ICON_WARNING)
                    elif not is_accessible:
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
                    main.log("Opened %s (%s).", db, util.format_bytes(
                             db.filesize))
                    main.status_flash("Reading database file %s.", db)
                    self.dbs[filename] = db
                    # Add filename to Recent Files menu and conf, if needed
                    if filename in conf.RecentFiles: # Remove earlier position
                        idx = conf.RecentFiles.index(filename)
                        try: self.history_file.RemoveFileFromHistory(idx)
                        except Exception: pass
                    self.history_file.AddFileToHistory(filename)
                    util.add_unique(conf.RecentFiles, filename, -1,
                                    conf.MaxRecentFiles)
                    conf.save()
                    self.check_future_dates(db)
            else:
                wx.MessageBox("Nonexistent file: %s." % filename,
                              conf.Title, wx.OK | wx.ICON_WARNING)
        return db


    def load_database_page(self, filename):
        """
        Tries to load the specified database, if not already open, create a
        subpage for it, if not already created, and focuses the subpage.

        @return  database page instance
        """
        db = None
        page = None
        if filename in self.dbs:
            db = self.dbs[filename]
        if db and db in self.db_pages.values():
            page = next((x for x in self.db_pages if x and x.db == db), None)
        if not page:
            if not db:
                db = self.load_database(filename)
            if db:
                main.status_flash("Opening database file %s." % db)
                tab_title = self.get_unique_tab_title(db.filename)
                page = DatabasePage(self.notebook, tab_title, db,
                                    self.memoryfs, self.skype_handler)
                self.db_pages[page] = db
                self.UpdateAccelerators()
                conf.save()
                self.Bind(wx.EVT_LIST_DELETE_ALL_ITEMS,
                          self.on_clear_searchall, page.edit_searchall)
        if page:
            for i in range(1, self.list_db.GetItemCount()):
                if self.list_db.GetItemText(i) == filename:
                    self.list_db.Select(i)
                    break # break for i
            for i in range(self.notebook.GetPageCount()):
                if self.notebook.GetPage(i) == page:
                    self.notebook.SetSelection(i)
                    self.update_notebook_header()
                    break # break for i in range(self.notebook..)
        return page


    def check_future_dates(self, db):
        """
        Checks the database for messages with a future date and asks the user
        about fixing them.
        """
        future_count, max_datetime = db.check_future_dates()
        if future_count:
            delta = datetime.datetime.now() - max_datetime
            dialog = DayHourDialog(parent=self,
                message="The database has %s with a "
                "future timestamp (last being %s).\nThis can "
                "happen if the computer\"s clock has been set "
                "to a future date when the messages were "
                "received.\n\n"
                "If you want to fix these messages, "
                "enter how many days/hours to move them:" %
                  (util.plural("message", future_count), max_datetime),
                caption=conf.Title, days=delta.days, hours=0)
            dialog_result = dialog.ShowModal()
            days, hours = dialog.GetValues()
            if (wx.ID_OK == dialog_result) and (days or hours):
                db.move_future_dates(days, hours)
                wx.MessageBox(
                    "Set timestamp of %s %s%s back." % (
                        util.plural("message", future_count),
                        util.plural("day", days) if days else "",
                        (" and " if days else "") +
                        util.plural("hour", hours) if hours else "",
                    ),
                    conf.Title, wx.OK)



class DatabasePage(wx.Panel):
    """
    A wx.Notebook page for managing a single database file, has its own
    Notebook with a number of pages for searching, browsing chat history and
    database tables, information and contact import.
    """

    def __init__(self, parent_notebook, title, db, memoryfs, skype_handler):
        wx.Panel.__init__(self, parent=parent_notebook)
        self.parent_notebook = parent_notebook
        self.title = title

        self.pageorder = {} # {page: notebook index, }
        self.ready_to_close = False
        self.db = db
        self.db.register_consumer(self)
        self.db_grids = {} # {"tablename": SqliteGridBase, }
        self.memoryfs = memoryfs
        self.skype_handler = skype_handler
        parent_notebook.InsertPage(1, self, title)
        busy = controls.BusyPanel(self, "Loading \"%s\"." % db.filename)

        self.chat = None # Currently viewed chat
        self.chats = []  # All chats in database
        self.chat_filter = { # Filter for currently shown chat history
            "daterange": None,      # Current date range
            "startdaterange": None, # Initial date range
            "text": "",             # Text in message content
            "participants": None    # Messages from [skype name, ]
        }
        self.stats_sort_field = "name"
        self.stats_expand_clouds = False # Expand individual author word clouds

        # Create search structures and threads
        self.Bind(EVT_WORKER, self.on_searchall_result)
        self.Bind(EVT_CONTACT_WORKER, self.on_search_contacts_result)
        self.workers_search = {} # {search ID: workers.SearchThread, }
        self.worker_search_contacts = \
            workers.ContactSearchThread(self.on_search_contacts_callback)
        self.search_data_contact = {"id": None} # Current contacts search data

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
        tb.AddLabelTool(wx.ID_FIND, "", bitmap=bmp, shortHelp="Start search")
        tb.Realize()
        self.Bind(wx.EVT_TOOL, self.on_searchall, id=wx.ID_FIND)
        sizer_header.Add(edit_search, border=5,
                     flag=wx.RIGHT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        sizer_header.Add(tb, flag=wx.ALIGN_RIGHT | wx.GROW)
        sizer.Add(sizer_header,
                  border=5, flag=wx.LEFT | wx.RIGHT | wx.TOP | wx.GROW)
        sizer.Layout() # To avoid searchbox moving around during page creation

        bookstyle = wx.lib.agw.fmresources.INB_LEFT
        if (wx.version().startswith("2.8") and sys.version_info[0:] == [2]
        and sys.version_info < (2, 7, 3)):
            # wx 2.8 + Python below 2.7.3: labelbook can partly cover tab area
            bookstyle |= wx.lib.agw.fmresources.INB_FIT_LABELTEXT
        notebook = self.notebook = wx.lib.agw.labelbook.FlatImageBook(
            parent=self, agwStyle=bookstyle, style=wx.BORDER_STATIC)

        il = wx.ImageList(32, 32)
        idx1 = il.Add(images.PageSearch.Bitmap)
        idx2 = il.Add(images.PageChats.Bitmap)
        idx3 = il.Add(images.PageInfo.Bitmap)
        idx4 = il.Add(images.PageTables.Bitmap)
        idx5 = il.Add(images.PageSQL.Bitmap)
        idx6 = il.Add(images.PageContacts.Bitmap)
        notebook.AssignImageList(il)

        self.create_page_search(notebook)
        self.create_page_chats(notebook)
        self.create_page_info(notebook)
        self.create_page_tables(notebook)
        self.create_page_sql(notebook)
        self.create_page_contacts(notebook)

        notebook.SetPageImage(0, idx1)
        notebook.SetPageImage(1, idx2)
        notebook.SetPageImage(2, idx3)
        notebook.SetPageImage(3, idx4)
        notebook.SetPageImage(4, idx5)
        notebook.SetPageImage(5, idx6)

        sizer.Add(notebook,proportion=1, border=5, flag=wx.GROW | wx.ALL)

        self.dialog_savefile = wx.FileDialog(
            parent=self,
            defaultDir=os.getcwd(),
            defaultFile="",
            style=wx.FD_SAVE | wx.RESIZE_BORDER)
        self.dialog_importfile = wx.FileDialog(
            parent=self,
            message="Select contacts file",
            defaultDir=os.getcwd(),
            wildcard="CSV spreadsheet (*.csv)|*.csv|All files (*.*)|*.*",
            style=wx.FD_FILE_MUST_EXIST | wx.FD_OPEN | wx.RESIZE_BORDER
        )

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
        if "linux2" == sys.platform and wx.version().startswith("2.8"):
            wx.CallAfter(self.split_panels)


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
        label_filter = wx.StaticText(panel1, label="Filter ch&ats:")
        sizer_top.Add(label_filter, flag=wx.ALIGN_CENTER | wx.RIGHT, border=5)
        edit_chatfilter = self.edit_chatfilter = wx.TextCtrl(
            parent=panel1, size=(75, -1))
        filter_tooltip = "Filter items in chat list"
        label_filter.SetToolTipString(filter_tooltip)
        edit_chatfilter.SetToolTipString(filter_tooltip)
        self.Bind(wx.EVT_TEXT, self.on_change_chatfilter, edit_chatfilter)
        sizer_top.Add(edit_chatfilter, flag=wx.RIGHT, border=15)
        button_export_chats = self.button_export_chats = \
            wx.Button(parent=panel1, label="Exp&ort chats")
        sizer_top.Add(button_export_chats, flag=wx.ALIGN_CENTER_HORIZONTAL)
        self.Bind(wx.EVT_BUTTON, self.on_export_chats_menu, button_export_chats)
        sizer1.Add(sizer_top, border=5,
                   flag=wx.RIGHT | wx.LEFT | wx.BOTTOM | wx.GROW)

        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED,
                  self.on_change_list_chats, list_chats)
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

        sizer_header = wx.BoxSizer(wx.HORIZONTAL)
        label_chat = self.label_chat = wx.StaticText(
            parent=panel_stc1, label="&Chat:", name="chat_history_label")

        tb = self.tb_chat = \
            wx.ToolBar(parent=panel_stc1, style=wx.TB_FLAT | wx.TB_NODIVIDER)
        tb.SetToolBitmapSize((24, 24))
        tb.AddCheckTool(wx.ID_ZOOM_100,
                        bitmap=images.ToolbarMaximize.Bitmap,
                        shortHelp="Maximize chat panel  (Alt-M)")
        tb.AddCheckTool(wx.ID_PROPERTIES,
                        bitmap=images.ToolbarStats.Bitmap,
                        shortHelp="Toggle chat statistics  (Alt-I)")
        tb.AddCheckTool(wx.ID_MORE, bitmap=images.ToolbarFilter.Bitmap,
                        shortHelp="Toggle filter panel  (Alt-G)")
        tb.Realize()
        self.Bind(wx.EVT_TOOL, self.on_toggle_maximize, id=wx.ID_ZOOM_100)
        self.Bind(wx.EVT_TOOL, self.on_toggle_stats,    id=wx.ID_PROPERTIES)
        self.Bind(wx.EVT_TOOL, self.on_toggle_filter,   id=wx.ID_MORE)

        button_export = self.button_export_chat = \
            wx.Button(parent=panel_stc1, label="&Export messages to file")
        button_export.SetToolTipString(
            "Export currently shown messages to a file")
        self.Bind(wx.EVT_BUTTON, self.on_export_chat, button_export)
        sizer_header.Add(label_chat, proportion=1, border=5, flag=wx.LEFT |
                         wx.ALIGN_BOTTOM)
        sizer_header.Add(tb, flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        sizer_header.Add(button_export, border=15, flag=wx.LEFT |
                         wx.ALIGN_CENTER_VERTICAL)

        stc = self.stc_history = ChatContentSTC(
            parent=panel_stc1, style=wx.BORDER_STATIC, name="chat_history")
        stc.SetDatabasePage(self)
        html_stats = self.html_stats = wx.html.HtmlWindow(parent=panel_stc1)
        html_stats.Bind(wx.html.EVT_HTML_LINK_CLICKED,
                        self.on_click_html_stats)
        html_stats.Bind(wx.EVT_SCROLLWIN, self.on_scroll_html_stats)
        html_stats.Bind(wx.EVT_SIZE, self.on_size_html_stats)
        html_stats.Hide()

        sizer_stc1.Add(sizer_header, border=5, flag=wx.GROW | wx.RIGHT |
                       wx.BOTTOM)
        sizer_stc1.Add(stc, proportion=1, border=5, flag=wx.GROW)
        sizer_stc1.Add(html_stats, proportion=1, flag=wx.GROW)

        label_filter = \
            wx.StaticText(parent=panel_stc2, label="Find messages with &text:")
        edit_filter = self.edit_filtertext = wx.TextCtrl(
            parent=panel_stc2, size=(100, -1), style=wx.TE_PROCESS_ENTER)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_filter_chat, edit_filter)
        edit_filter.SetToolTipString("Find messages containing the exact text")
        label_range = wx.StaticText(
            parent=panel_stc2, label="Show messages from time perio&d:")
        date1 = self.edit_filterdate1 = wx.TextCtrl(panel_stc2, size=(80, -1))
        date2 = self.edit_filterdate2 = wx.TextCtrl(panel_stc2, size=(80, -1),
                                                    style=wx.TE_RIGHT)
        date1.SetToolTipString("Date in the form YYYY-MM-DD")
        date2.SetToolTipString("Date in the form YYYY-MM-DD")
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
        list_participants.InsertColumn(0, "")
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_select_participant,
                  list_participants)
        list_participants.EnableSelectionGradient()
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
        button_filter_apply.SetToolTipString(
            "Filters the conversation by the specified text, "
            "date range and participants.")
        button_filter_export.SetToolTipString(
            "Exports filtered messages straight to file, "
            "without showing them (showing thousands of messages gets slow).")
        button_filter_reset.SetToolTipString(
            "Restores filter controls to initial values.")
        sizer_filter_buttons.Add(button_filter_apply)
        sizer_filter_buttons.AddSpacer(5)
        sizer_filter_buttons.Add(button_filter_export)
        sizer_filter_buttons.AddSpacer(5)
        sizer_filter_buttons.Add(button_filter_reset)
        sizer_filter_buttons.AddSpacer(5)
        sizer_dates.Add(date1)
        sizer_dates.AddStretchSpacer()
        sizer_dates.Add(date2, flag=wx.ALIGN_RIGHT)
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
        splitter.SplitHorizontally(panel1, panel2, sashPosition=self.Size[1]/3)
        panel2.Enabled = False


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
        tb.AddRadioTool(wx.ID_INDEX, bitmap=images.ToolbarMessage.Bitmap,
            shortHelp="Search in message body")
        tb.AddRadioTool(wx.ID_PREVIEW, bitmap=images.ToolbarContact.Bitmap,
            shortHelp="Search in contact information")
        tb.AddRadioTool(wx.ID_ABOUT, bitmap=images.ToolbarTitle.Bitmap,
            shortHelp="Search in chat title and participants")
        tb.AddRadioTool(wx.ID_STATIC, bitmap=images.ToolbarTables.Bitmap,
            shortHelp="Search in all columns of all database tables")
        tb.AddSeparator()
        tb.AddCheckTool(wx.ID_NEW, bitmap=images.ToolbarTabs.Bitmap,
            shortHelp="New tab for each search  (Alt-N)", longHelp="")
        tb.AddSimpleTool(wx.ID_STOP, bitmap=images.ToolbarStopped.Bitmap,
            shortHelpString="Stop current search, if any")
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
        html.SetTabAreaColour(tb.BackgroundColour)
        html.Font.PixelSize = (0, 8)

        label_html.BackgroundColour = tb.BackgroundColour
        
        sizer_top.Add(label_html, proportion=1, flag=wx.GROW)
        sizer_top.Add(tb, border=5, flag=wx.TOP | wx.RIGHT |
                      wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        sizer.Add(sizer_top, border=5, flag=wx.TOP | wx.RIGHT | wx.GROW)
        sizer.Add(html, border=5, proportion=1,
                  flag=wx.GROW | wx.LEFT | wx.RIGHT | wx.BOTTOM)
        wx.CallAfter(label_html.Show)


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
        tree = self.tree_tables = wx.gizmos.TreeListCtrl(
            parent=panel1,
            style=wx.TR_DEFAULT_STYLE
            #| wx.TR_HAS_BUTTONS
            #| wx.TR_TWIST_BUTTONS
            #| wx.TR_ROW_LINES
            #| wx.TR_COLUMN_LINES
            #| wx.TR_NO_LINES
            | wx.TR_FULL_ROW_HIGHLIGHT
        )
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
        tb.AddLabelTool(id=wx.ID_ADD, label="Insert new row.",
                        bitmap=bmp_tb, shortHelp="Add new row.")
        tb.AddLabelTool(id=wx.ID_DELETE, label="Delete current row.",
            bitmap=images.ToolbarDelete.Bitmap, shortHelp="Delete row.")
        tb.AddSeparator()
        tb.AddLabelTool(id=wx.ID_SAVE, label="Commit",
                        bitmap=images.ToolbarCommit.Bitmap,
                        shortHelp="Commit changes to database.")
        tb.AddLabelTool(id=wx.ID_UNDO, label="Rollback",
            bitmap=images.ToolbarRollback.Bitmap,
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
        button_reset.SetToolTipString("Resets all applied sorting "
                                      "and filtering.")
        button_reset.Bind(wx.EVT_BUTTON, self.on_button_reset_grid)
        button_reset.Enabled = False
        button_export = self.button_export_table = \
            wx.Button(parent=panel2, label="&Export to file")
        button_export.MinSize = (100, -1)
        button_export.SetToolTipString("Export rows to a file.")
        button_export.Bind(wx.EVT_BUTTON, self.on_button_export_grid)
        button_export.Enabled = False
        sizer_tb.Add(label_table, flag=wx.ALIGN_CENTER_VERTICAL)
        sizer_tb.AddStretchSpacer()
        sizer_tb.Add(button_reset, border=5, flag=wx.BOTTOM | wx.RIGHT |
                     wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        sizer_tb.Add(button_export, border=5, flag=wx.BOTTOM | wx.RIGHT |
                     wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        sizer_tb.Add(tb, flag=wx.ALIGN_RIGHT)
        grid = self.grid_table = wx.grid.Grid(parent=panel2)
        grid.SetToolTipString("Double click on column header to sort, "
                              "right click to filter.")
        grid.Bind(wx.grid.EVT_GRID_LABEL_LEFT_DCLICK, self.on_sort_grid_column)
        grid.GridWindow.Bind(wx.EVT_MOTION, self.on_mouse_over_grid)
        grid.Bind(wx.grid.EVT_GRID_LABEL_RIGHT_CLICK,
                  self.on_filter_grid_column)
        grid.Bind(wx.grid.EVT_GRID_CELL_CHANGE, self.on_change_table)
        label_help = wx.StaticText(panel2, wx.NewId(),
            "Double-click on column header to sort, right click to filter.")
        label_help.ForegroundColour = "grey"
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
        label_help.ForegroundColour = "grey"
        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        button_sql = self.button_sql = wx.Button(panel2, label="Execute S&QL")
        button_script = self.button_script = wx.Button(panel2, 
                                                       label="Execute scrip&t")
        button_sql.SetToolTipString("Execute a single statement "
                                    "from the SQL window")
        button_script.SetToolTipString("Execute multiple SQL statements, "
                                       "separated by semicolons")
        self.Bind(wx.EVT_BUTTON, self.on_button_sql, button_sql)
        self.Bind(wx.EVT_BUTTON, self.on_button_script, button_script)
        button_reset = self.button_reset_grid_sql = \
            wx.Button(parent=panel2, label="&Reset filter/sort")
        button_reset.SetToolTipString("Resets all applied sorting "
                                      "and filtering.")
        button_reset.Bind(wx.EVT_BUTTON, self.on_button_reset_grid)
        button_reset.Enabled = False
        button_export = self.button_export_sql = \
            wx.Button(parent=panel2, label="&Export to file")
        button_export.SetToolTipString("Export result to a file.")
        button_export.Bind(wx.EVT_BUTTON, self.on_button_export_grid)
        button_export.Enabled = False
        sizer_buttons.Add(button_sql, flag=wx.ALIGN_LEFT)
        sizer_buttons.Add(button_script, border=5, flag=wx.LEFT | wx.ALIGN_LEFT)
        sizer_buttons.AddStretchSpacer()
        sizer_buttons.Add(button_reset, border=5,
                          flag=wx.ALIGN_RIGHT | wx.RIGHT)
        sizer_buttons.Add(button_export, flag=wx.ALIGN_RIGHT)
        grid = self.grid_sql = wx.grid.Grid(parent=panel2)
        grid.Bind(wx.grid.EVT_GRID_LABEL_LEFT_DCLICK,
                  self.on_sort_grid_column)
        grid.Bind(wx.grid.EVT_GRID_LABEL_RIGHT_CLICK,
                  self.on_filter_grid_column)
        grid.Bind(wx.EVT_SCROLLWIN, self.on_scroll_grid_sql)
        grid.Bind(wx.EVT_SCROLL_THUMBRELEASE, self.on_scroll_grid_sql)
        grid.Bind(wx.EVT_SCROLL_CHANGED, self.on_scroll_grid_sql)
        grid.Bind(wx.EVT_KEY_DOWN, self.on_scroll_grid_sql)
        grid.GridWindow.Bind(wx.EVT_MOTION, self.on_mouse_over_grid)
        label_help_grid = wx.StaticText(panel2, wx.NewId(),
            "Double-click on column header to sort, right click to filter.")
        label_help_grid.ForegroundColour = "grey"

        sizer2.Add(label_help, border=5, flag=wx.GROW | wx.LEFT | wx.BOTTOM)
        sizer2.Add(sizer_buttons, border=5, flag=wx.GROW | wx.ALL)
        sizer2.Add(grid, border=5, proportion=2,
                   flag=wx.GROW | wx.LEFT | wx.RIGHT)
        sizer2.Add(label_help_grid, border=5, flag=wx.GROW | wx.LEFT | wx.TOP)

        sizer.Add(splitter, proportion=1, flag=wx.GROW)
        sash_pos = self.Size[1] / 3
        splitter.SplitHorizontally(panel1, panel2, sashPosition=sash_pos)


    def create_page_contacts(self, notebook):
        """Creates a page for importing contacts from file."""
        page = self.page_contacts = wx.Panel(parent=notebook)
        self.pageorder[page] = len(self.pageorder)
        notebook.AddPage(page, "Contacts+")
        sizer = page.Sizer = wx.BoxSizer(wx.VERTICAL)
        splitter = self.splitter_import = wx.SplitterWindow(
            parent=page, style=wx.BORDER_NONE)
        splitter.SetMinimumPaneSize(100)

        panel1 = wx.Panel(parent=splitter)
        sizer1 = panel1.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_header = wx.BoxSizer(wx.HORIZONTAL)
        sizer_top1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_selectbuttons = wx.BoxSizer(wx.VERTICAL)

        label_header = wx.StaticText(parent=panel1, 
            label="Import people to your Skype contacts from a CSV file, "
                  "like ones exported from MSN or GMail.\n"
                  "Skype needs to be running and logged in.\n\n"
                  "For exporting your MSN contacts, log in to live.com "
                  "with your MSN account and find \"Export contacts\" under "
                  "People.\n"
                  "For exporting your GMail contacts, log in to gmail.com and "
                  "find \"Download data\" under \"Account\".\n"
                  "For other CSV sources: header row should have fields "
                  "\"Name\", \"Phone\", \"E-mail\", or \"Skypename\"."
                  )
        label_header.ForegroundColour = "grey"
        button_import = self.button_import_file = \
            wx.Button(panel1, label="Se&lect contacts file")
        button_import_db = self.button_import_db = \
            wx.Button(panel1, label="Use &database contacts")
        button_import.Bind(wx.EVT_BUTTON, self.on_choose_import_file)
        button_import_db.Bind(wx.EVT_BUTTON, self.on_choose_import_db)
        sizer_selectbuttons.Add(button_import, flag=wx.ALIGN_CENTER_HORIZONTAL | wx.GROW)
        sizer_selectbuttons.AddStretchSpacer()
        sizer_selectbuttons.Add(button_import_db, flag=wx.ALIGN_CENTER_HORIZONTAL)
        sizer_header.Add(sizer_selectbuttons, border=10, flag=wx.RIGHT | wx.GROW)
        sizer_header.Add(label_header, border=60, flag=wx.LEFT)

        label_source = self.label_import_source = \
            wx.StaticText(parent=panel1, label="C&ontacts in source file:")
        sizer_top1.Add(label_source, flag=wx.ALIGN_BOTTOM)
        sizer_top1.AddStretchSpacer()
        label_filter = wx.StaticText(panel1, label="Filter c&ontacts:")
        sizer_top1.Add(label_filter, flag=wx.ALIGN_CENTER | wx.ALIGN_RIGHT | 
                       wx.RIGHT, border=5)
        edit_contactfilter = self.edit_contactfilter = wx.TextCtrl(
            parent=panel1, size=(75, -1))
        filter_tooltip = "Filter items in contact list"
        label_filter.SetToolTipString(filter_tooltip)
        edit_contactfilter.SetToolTipString(filter_tooltip)
        self.Bind(wx.EVT_TEXT, self.on_change_import_sourcefilter,
                  edit_contactfilter)
        sizer_top1.Add(edit_contactfilter, flag=wx.ALIGN_RIGHT)

        sourcelist = self.list_import_source = \
            controls.SortableListView(parent=panel1, style=wx.LC_REPORT)
        cols = [("name", "Name"), ("e-mail", "E-mail"), ("phone", "Phone")]
        sourcelist.SetColumns(cols)
        sourcelist.Bind(wx.EVT_LIST_ITEM_SELECTED,
                        self.on_select_import_sourcelist)
        sourcelist.Bind(wx.EVT_LIST_ITEM_DESELECTED,
                        self.on_select_import_sourcelist)
        sourcelist.Bind(wx.EVT_LIST_ITEM_ACTIVATED,
                        self.on_import_search)

        sizer1.Add(sizer_header, border=5, flag=wx.ALL)
        sizer1.Add(sizer_top1, border=5, flag=wx.ALL | wx.GROW)
        sizer1.Add(sourcelist, border=5, proportion=1,
                   flag=wx.GROW | wx.LEFT | wx.RIGHT)

        panel2 = wx.Panel(parent=splitter)
        sizer2 = panel2.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        button_search_selected = self.button_import_search_selected = \
            wx.Button(panel2, label="Search for selected contacts in Skype")
        button_select_all = self.button_import_select_all = \
            wx.Button(panel2, label="Select all")
        self.Bind(wx.EVT_BUTTON, self.on_import_search, button_search_selected)
        self.Bind(wx.EVT_BUTTON, self.on_import_select_all, button_select_all)
        button_search_selected.SetToolTipString("Search for the selected "
            "contacts through the running Skype application.")
        button_search_selected.Enabled = button_select_all.Enabled = False
        label_search = wx.StaticText(parent=panel2,
                                     label="Skype use&rbase search:")
        edit_search = self.edit_import_search_free = wx.TextCtrl(
            parent=panel2, size=(100, -1), style=wx.TE_PROCESS_ENTER)
        button_search_free = self.button_import_search_free = \
            wx.Button(panel2, label="Search in Skype")
        self.Bind(wx.EVT_TEXT_ENTER, self.on_import_search, edit_search)
        self.Bind(wx.EVT_BUTTON, self.on_import_search, button_search_free)
        for control in [label_search, edit_search, button_search_free]:
            control.SetToolTipString("Search for the entered value in "
                                     "Skype userbase.")

        sizer_buttons.Add(button_search_selected, flag=wx.ALIGN_LEFT)
        sizer_buttons.Add(button_select_all, border=5, flag=wx.LEFT)
        sizer_buttons.AddStretchSpacer()
        sizer_buttons.Add(label_search, flag=wx.ALIGN_CENTER_VERTICAL)
        sizer_buttons.Add(edit_search, border=5, flag=wx.LEFT)
        sizer_buttons.Add(button_search_free, border=5, flag=wx.LEFT)

        label_searchinfo = wx.StaticText(parent=panel2,
            label="Skype will be launched if not already running. Might bring "
                  "up a notification screen in Skype to allow access for "
                  "%s.\nSearching for many contacts at once can "
                  "take a long time." % conf.Title)
        label_searchinfo.ForegroundColour = "grey"

        sizer_resultlabel = wx.BoxSizer(wx.HORIZONTAL)
        label_result = self.label_import_result = \
            wx.StaticText(parent=panel2, label="Contacts found in Sk&ype:")
        resultlist = self.list_import_result = \
            controls.SortableListView(parent=panel2, style=wx.LC_REPORT)
        result_columns = [("#", "#"), ("FullName", "Name"),
            ("Handle", "Skype handle"), ("IsAuthorized", "Already added"),
            ("PhoneMobile", "Phone"), ("City", "City"), ("Country", "Country"),
            ("Sex", "Gender"), ("Birthday", "Birthday"),
            ("Language", "Language")]
        resultlist.SetColumns(result_columns)

        resultlist.Bind(
            wx.EVT_LIST_ITEM_SELECTED,   self.on_select_import_resultlist)
        resultlist.Bind(
            wx.EVT_LIST_ITEM_DESELECTED, self.on_select_import_resultlist)
        resultlist.Bind(wx.EVT_LIST_ITEM_ACTIVATED,self.on_import_add_contacts)

        sizer_footer = wx.BoxSizer(wx.HORIZONTAL)
        button_add = self.button_import_add = \
            wx.Button(panel2, label="Add the selected to your Skype contacts")

        label_filter = wx.StaticText(panel2, label="Filter res&ults:")
        edit_resultfilter = wx.TextCtrl(parent=panel2, size=(75, -1))
        filter_tooltip = "Filter items in Skype results list"
        label_filter.SetToolTipString(filter_tooltip)
        edit_resultfilter.SetToolTipString(filter_tooltip)
        self.Bind(wx.EVT_TEXT, self.on_change_import_resultfilter,
                  edit_resultfilter)
        button_clear = self.button_import_clear = \
            wx.Button(panel2, label="Clear selected from list")
        self.Bind(wx.EVT_BUTTON, self.on_import_add_contacts, button_add)
        self.Bind(wx.EVT_BUTTON, self.on_import_clear_contacts, button_clear)
        button_add.SetToolTipString("Opens an authorization request in Skype")
        button_add.Enabled = button_clear.Enabled = False
        sizer_footer.Add(button_add, flag=wx.ALIGN_LEFT)
        sizer_footer.AddStretchSpacer()
        sizer_footer.Add(label_filter, flag=wx.ALIGN_CENTER | wx.RIGHT, border=5)
        sizer_footer.Add(edit_resultfilter, flag=wx.wx.ALIGN_TOP)
        sizer_footer.Add(button_clear, flag=wx.ALIGN_RIGHT | wx.LEFT, border=20)

        sizer2.Add(sizer_buttons, border=5, flag=wx.GROW | wx.ALL)
        sizer_resultlabel.Add(label_result, flag=wx.ALIGN_BOTTOM)
        sizer_resultlabel.Add(label_searchinfo, border=60, flag=wx.LEFT)
        sizer2.Add(sizer_resultlabel, border=5, flag=wx.ALL)
        sizer2.Add(resultlist, border=5, proportion=1,
                   flag=wx.GROW | wx.LEFT | wx.RIGHT)
        sizer2.Add(sizer_footer, border=5, flag=wx.GROW | wx.ALL)

        sizer.Add(splitter, proportion=1, flag=wx.GROW)
        splitter.SplitHorizontally(panel1, panel2,
                                   sashPosition=self.Size[1]*2/5)


    def create_page_info(self, notebook):
        """Creates a page for seeing general database information."""
        page = self.page_info = wx.lib.scrolledpanel.ScrolledPanel(notebook)
        self.pageorder[page] = len(self.pageorder)
        notebook.AddPage(page, "Information")
        sizer = page.Sizer = wx.BoxSizer(wx.HORIZONTAL)

        panel1 = self.panel_accountinfo = wx.Panel(parent=page)
        panel2 = wx.Panel(parent=page)
        panel1.BackgroundColour = panel2.BackgroundColour = conf.BgColour
        sizer1 = panel1.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_account = wx.BoxSizer(wx.HORIZONTAL)
        label_account = wx.StaticText(parent=panel1,
                                      label="Main account information")
        label_account.Font = wx.Font(10, wx.FONTFAMILY_SWISS,
            wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, face=self.Font.FaceName)
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
                                  wx.FONTWEIGHT_BOLD, face=self.Font.FaceName)
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
                continue # continue for i, (name, label) in enumerate(..
            labeltext = wx.StaticText(parent=panel2, label="%s:" % label)
            labeltext.ForegroundColour = wx.Colour(102, 102, 102)
            valuetext = wx.TextCtrl(parent=panel2, value="Analyzing..",
                style=wx.NO_BORDER | wx.TE_MULTILINE | wx.TE_RICH)
            valuetext.MinSize = (-1, 35)
            valuetext.BackgroundColour = panel2.BackgroundColour
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
        button_check.SetToolTipString("Check database integrity for "
                                      "corruption and recovery.")
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


    def on_check_integrity(self, event):
        """
        Handler for checking database integrity, offers to save a fixed
        database if corruption detected.
        """
        msg = "Checking integrity of %s." % self.db.filename
        main.logstatus_flash(msg)
        busy = controls.BusyPanel(self, msg)
        wx.YieldIfNeeded()
        try:
            errors = self.db.check_integrity()
        except Exception as e:
            errors = e.args[:]
        busy.Close()
        main.status_flash("")
        if not errors:
            wx.MessageBox("No database errors detected.",
                          conf.Title, wx.ICON_INFORMATION)
        else:
            err = "\n- ".join(errors)
            main.log("Errors found in %s: %s", self.db, err)
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
                self.dialog_savefile.Wildcard = "SQLite database (*.db)|*.db"
                self.dialog_savefile.WindowStyle |= wx.FD_OVERWRITE_PROMPT
                if wx.ID_OK == self.dialog_savefile.ShowModal():
                    newfile = self.dialog_savefile.GetPath()
                    if not newfile.lower().endswith(".db"): newfile += ".db"
                    if newfile != self.db.filename:
                        main.status_flash("Recovering data from %s to %s.",
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
                        main.status_flash("Recovery to %s complete." % newfile)
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
        bmp = skypedata.get_avatar(account) or images.AvatarDefaultLarge.Bitmap
        self.bmp_account.SetBitmap(bmp)
        [sizer.Remove(0) for i in sizer.Children]

        fields = ["fullname", "skypename", "mood_text", "phone_mobile",
                  "phone_home", "phone_office", "emails", "country",
                  "province", "city", "homepage", "gender", "birthday",
                  "languages", "nrof_authed_buddies", "about",
                  "skypeout_balance", ]

        for field in fields:
            if not account.get(field): continue # for field
            value = account[field]
            if "emails" == field:
                value = ", ".join(value.split(" "))
            elif "gender" == field:
                value = {1: "male", 2: "female"}.get(value, "")
            elif "birthday" == field:
                try:
                    value = str(value)
                    value = "-".join([value[:4], value[4:6], value[6:]])
                except Exception: pass
            if value:
                if "skypeout_balance" == field:
                    precision = account.get("skypeout_precision") or 2
                    value = "%s %s" % (value / (10.0 ** precision),
                            (account.get("skypeout_balance_currency") or ""))
                if not isinstance(value, basestring):
                    value = str(value) 
                title = skypedata.ACCOUNT_FIELD_TITLES.get(field, field)
                lbltext = wx.StaticText(parent=panel, label="%s:" % title)
                valtext = wx.TextCtrl(parent=panel, value=value,
                    style=wx.NO_BORDER | wx.TE_MULTILINE | wx.TE_RICH)
                valtext.BackgroundColour = panel.BackgroundColour
                valtext.MinSize = (-1, 35)
                valtext.SetEditable(False)
                lbltext.ForegroundColour = wx.Colour(102, 102, 102)
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


    def split_panels(self):
        """
        Splits all SplitterWindow panels. To be called after layout in
        Linux wx 2.8, as otherwise panels do not get sized properly.
        """
        if not self:
            return
        sash_pos = self.Size[1] / 3
        panel1, panel2 = self.splitter_chats.Children
        self.splitter_chats.Unsplit()
        self.splitter_chats.SplitHorizontally(panel1, panel2, sash_pos)
        panel1, panel2 = self.splitter_tables.Children
        self.splitter_tables.Unsplit()
        self.splitter_tables.SplitVertically(panel1, panel2, 270)
        panel1, panel2 = self.splitter_sql.Children
        self.splitter_sql.Unsplit()
        self.splitter_sql.SplitHorizontally(panel1, panel2, sash_pos)
        panel1, panel2 = self.splitter_import.Children
        self.splitter_import.Unsplit()
        self.splitter_import.SplitHorizontally(panel1, panel2, sash_pos)
        wx.CallLater(1000, lambda: self and 
                     (self.tree_tables.SetColumnWidth(0, -1),
                      self.tree_tables.SetColumnWidth(1, -1)))


    def update_info_page(self, reload=True):
        """Updates the Information page with current data."""
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
            self.edit_info_chats.Value = "%(chats)s" % stats
            self.edit_info_contacts.Value = "%(contacts)s" % stats
            self.edit_info_messages.Value = "%(messages)s" % stats
            self.edit_info_transfers.Value = "%(transfers)s" % stats
        if "messages_from" in stats:
            self.edit_info_messages.Value += " (%s sent and %s received)" % \
                (stats.get("messages_from"), stats.get("messages_to"))
        text = ""
        if "lastmessage_dt" in stats:
            text = "%(lastmessage_dt)s %(lastmessage_from)s" % stats
        if stats and (stats.get("lastmessage_skypename") == self.db.id
        or skypedata.CHATS_TYPE_SINGLE != stats.get("lastmessage_chattype")):
            text += " in %(lastmessage_chat)s" % stats
        self.edit_info_lastmessage.Value = text
        text = ""
        if "firstmessage_dt" in stats:
            text = "%(firstmessage_dt)s %(firstmessage_from)s" % stats
        if stats and (stats.get("firstmessage_skypename") == self.db.id
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


    def on_refresh_tables(self, event):
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
        if do_refresh:
            self.db.clear_cache()
            self.db_grids.clear()
            self.load_tables_data()
            if self.grid_table.Table:
                grid, table_name = self.grid_table, self.grid_table.Table.table
                scrollpos = map(grid.GetScrollPos, [wx.HORIZONTAL, wx.VERTICAL])
                cursorpos = grid.GridCursorCol, grid.GridCursorRow
                self.on_change_table(None)
                grid.Table = wx.grid.PyGridTableBase() # Clear grid visually
                grid.Freeze()
                grid.Table = None # Reset grid data to empty

                tableitem = None
                table_name = table_name.lower()
                table = next((t for t in self.db.get_tables()
                              if t["name"].lower() == table_name), None)
                item = self.tree_tables.GetNext(self.tree_tables.RootItem)
                while table and item and item.IsOk():
                    table2 = self.tree_tables.GetItemPyData(item)
                    if table2 and table2.lower() == table["name"].lower():
                        tableitem = item
                        break # break while table and item and itek.IsOk()
                    item = self.tree_tables.GetNextSibling(item)
                if tableitem:
                    # Only way to create state change in wx.gizmos.TreeListCtrl
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
                sel = e.Selection
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


    def on_change_import_resultfilter(self, event):
        """
        Handler for changing text in contacts import result filter box,
        filters Skype userbase results list.
        """
        self.list_import_result.SetFilter(event.String.strip())


    def on_change_chatfilter(self, event):
        """Handler for changing text in chat filter box, filters chat list."""
        self.list_chats.SetFilter(event.String.strip())


    def on_change_import_sourcefilter(self, event):
        """
        Handler for changing text in contacts import source filter box,
        filters contacts source list.
        """
        self.list_import_source.SetFilter(event.String.strip())


    def on_choose_import_file(self, event):
        """Handler for clicking to choose a CSV file for contact import."""
        contacts = None
        if wx.ID_OK == self.dialog_importfile.ShowModal():
            filename = self.dialog_importfile.GetPath()
            try:
                contacts = skypedata.import_contacts_file(filename)
            except Exception as e:
                errormsg = "Error reading \"%s\".\n\n%s" % (filename, util.format_exc(e))
                main.logstatus_flash(errormsg)
                wx.MessageBox(errormsg, conf.Title, wx.OK | wx.ICON_WARNING)
                wx.CallAfter(support.report_error, errormsg)
        if contacts is not None:
            self.list_import_result.DeleteAllItems()
            cols = [("name", "Name"), ("e-mail", "E-mail"), ("phone", "Phone")]
            self.list_import_source.SetColumns(cols)
            self.list_import_source.Populate(contacts)
            self.button_import_add.Enabled = False
            self.button_import_clear.Enabled = False
            self.button_import_search_selected.Enabled = False
            self.label_import_source.Label = \
                "C&ontacts in source file %s [%s]:" % (filename, len(contacts))
            self.label_import_result.Label = "Contacts found in Sk&ype:"
            self.button_import_select_all.Enabled = len(contacts)
            main.logstatus_flash("Found %s in file %s.",
                                 util.plural("contact", contacts), filename)


    def on_choose_import_db(self, event):
        """Handler for clicking to choose to import contacts from current DB."""
        contacts = [{"e-mail": x["emails"] if "@" in (x["emails"] or "") else "", 
                     "name": x["name"], "skypename": x["skypename"], 
                     "phone": x["phone_mobile_normalized"]}
                    for x in self.db.get_contacts()]
        contacts = [x for x in contacts if any(x.values())]
        self.list_import_result.DeleteAllItems()
        cols = [("skypename", "Skypename"), ("name", "Name"), 
                ("e-mail", "E-mail"), ("phone", "Phone")]
        self.list_import_source.SetColumns(cols)
        self.list_import_source.Populate(contacts)
        self.button_import_add.Enabled = False
        self.button_import_clear.Enabled = False
        self.button_import_search_selected.Enabled = False
        self.label_import_source.Label = \
            "C&ontacts in database %s [%s]:" % (self.db, len(contacts))
        self.label_import_result.Label = "Contacts found in Sk&ype:"
        self.button_import_select_all.Enabled = len(contacts)


    def on_select_import_sourcelist(self, event):
        """
        Handler when a row is selected in the import contacts source list,
        enables UI buttons.
        """
        count = self.list_import_source.GetSelectedItemCount()
        self.button_import_search_selected.Enabled = (count > 0)


    def on_select_import_resultlist(self, event):
        """
        Handler when a row is selected in the import contacts result list,
        enables UI buttons.
        """
        count = self.list_import_result.GetSelectedItemCount()
        self.button_import_add.Enabled = (count > 0)
        self.button_import_clear.Enabled = (count > 0)


    def on_import_select_all(self, event):
        """Handler for clicking to select all imported contacts."""
        [self.list_import_source.Select(i)
         for i in range(self.list_import_source.ItemCount)]
        self.list_import_source.SetFocus()


    def on_import_search(self, event):
        """
        Handler for choosing to search Skype for contacts in the import source
        list.
        """
        if not self.skype_handler:
            msg = "Skype4Py not installed, cannot search."
            return wx.MessageBox(msg, conf.Title, wx.OK | wx.ICON_WARNING)
        search_values = []
        lst, lst2 = self.list_import_source, self.list_import_result
        if event.EventObject in [self.button_import_search_free,
                                 self.edit_import_search_free]:
            value = self.edit_import_search_free.Value.strip()
            if value:
                search_values.append(value)
                infotext = "Searching Skype userbase for \"%s\"." % value
        else:
            values_unique, contacts_unique = set(), set()
            selected = lst.GetFirstSelected()
            while selected >= 0:
                contact = lst.GetItemMappedData(selected)
                for key in ["skypename", "name", "phone", "e-mail"]:
                    if contact.get(key) and contact[key] not in values_unique:
                        search_values.append(contact[key])
                        values_unique.add(contact[key])
                        contacts_unique.add(id(contact))
                selected = lst.GetNextSelected(selected)
            info = "\"%s\"" % "\", \"".join(search_values)
            if len(info) > 60:
                info = info[:60] + ".."
            infotext = "Searching Skype userbase for %s (%s)." \
                        % (util.plural("contact", contacts_unique), info)
        if search_values:
            main.logstatus_flash(infotext)
            lst2.DeleteAllItems()
            self.button_import_add.Enabled = False
            self.button_import_clear.Enabled = False

            data = {"id": wx.NewId(), "handler": self.skype_handler,
                    "values": search_values}
            self.search_data_contact.update(data)
            self.worker_search_contacts.work(data)
            self.label_import_result.Label = "Contacts found in Sk&ype:"


    def on_search_contacts_result(self, event):
        """
        Handler for getting results from contact search thread, adds the
        results to the import list.
        """
        result = event.result
        # If search ID is different, results are from the previous search still
        lst2 = self.list_import_result
        if result["search"]["id"] == self.search_data_contact["id"]:
            lst2.Freeze()
            scrollpos = lst2.GetScrollPos(wx.VERTICAL)

            for user in result["results"]:
                data = {"user": user, "#": lst2.GetItemCountFull() + 1, }
                for k in ["FullName", "Handle", "IsAuthorized", "PhoneMobile",
                          "City", "Country", "Sex", "Birthday", "Language"]:
                    val = getattr(user, k)
                    if "IsAuthorized" == k:
                        val = "Yes" if val else "No"
                    elif "Sex" == k:
                        val = "" if ("UNKNOWN" == val) else val.lower()
                    data[k] = val
                lst2.AppendRow(data)
                if user.IsAuthorized:
                    lst2.SetItemTextColour(lst2.ItemCount - 1, "gray")

            lst2.SetScrollPos(wx.VERTICAL, scrollpos)
            lst2.Thaw()
            self.label_import_result.Label = \
                "Contacts found in Sk&ype [%s]:" % lst2.ItemCount
            if "done" in result:
                wx.Bell()
                main.logstatus_flash("Found %s in Skype userbase.",
                                     util.plural("contact", lst2.ItemCount))
            lst2.Update()


    def on_import_add_contacts(self, event):
        """
        Handler for adding an imported contact in Skype, opens an authorization
        request window in Skype.
        """
        lst = self.list_import_result
        selected, contacts = lst.GetFirstSelected(), []
        while selected >= 0:
            contacts.append(lst.GetItemMappedData(selected))
            selected = lst.GetNextSelected(selected)
        info = ", ".join([c["Handle"] for c in contacts])
        if len(info) > 60:
            info = info[:60] + ".."
        msg = "Add %s to your Skype contacts (%s)?" % (
              util.plural("person", contacts), info)
        if self.skype_handler and wx.OK == wx.MessageBox(msg,
            conf.Title, wx.OK | wx.CANCEL | wx.ICON_QUESTION
        ):
            busy = controls.BusyPanel(self,
                "Adding %s to your Skype contacts."
                % util.plural("person", contacts)
            )
            try:
                self.skype_handler.add_to_contacts(c["user"] for c in contacts)
                main.logstatus_flash("Added %s to your Skype contacts (%s).",
                                     util.plural("person", contacts), info)
            except Exception:
                msg = "Error adding contacts:\n\n%s" % traceback.format_exc()
                main.logstatus_flash(msg)
                wx.MessageBox(msg, conf.Title, wx.OK | wx.ICON_WARNING)
                wx.CallAfter(support.report_error, msg)
            finally:
                busy.Close()


    def on_import_clear_contacts(self, event):
        """
        Handler for clicking to remove selected items from contact import
        result list.
        """
        selected, selecteds = self.list_import_result.GetFirstSelected(), []
        while selected >= 0:
            selecteds.append(selected)
            selected = self.list_import_result.GetNextSelected(selected)
        for i in range(len(selecteds)):
            # - i, as item count is getting smaller one by one
            selected = selecteds[i] - i
            data = self.list_import_result.GetItemMappedData(selected)
            self.list_import_result.DeleteItem(selected)
        self.label_import_result.Label = "Contacts found in Sk&ype [%s]:" \
                                         % self.list_import_result.ItemCount
        self.button_import_add.Enabled = False
        self.button_import_clear.Enabled = False


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
        self.dialog_savefile.WindowStyle |= wx.FD_OVERWRITE_PROMPT
        if wx.ID_OK == self.dialog_savefile.ShowModal():
            filepath = self.dialog_savefile.GetPath()
            dirname = os.path.dirname(filepath)
            filename = os.path.basename(filepath)
            extname = export.CHAT_EXTS[self.dialog_savefile.FilterIndex]
            if not filename.lower().endswith(".%s" % extname):
                filename += ".%s" % extname
                filepath = os.path.join(dirname, filename)
            busy = controls.BusyPanel(
                self, "Exporting \"%s\"." % self.chat["title"]
            )
            main.status_flash("Exporting to %s.", filepath)
            try:
                messages = self.stc_history.GetMessages()
                progressfunc = lambda *args: wx.SafeYield()
                export.export_chats([self.chat], dirname, filename, self.db,
                    messages=messages, skip=False, progress=progressfunc)
                main.status_flash("Exported %s.", filepath)
                try: util.start_file(filepath)
                except Exception:
                    main.log("Error starting %s:\n\n%s.", filepath,
                             traceback.format_exc())
            except Exception:
                errormsg = "Error saving %s:\n\n%s" % \
                           (filepath, traceback.format_exc())
                main.logstatus_flash(errormsg)
                wx.MessageBox(errormsg, conf.Title, wx.OK | wx.ICON_WARNING)
                wx.CallAfter(support.report_error, errormsg)
                wx.CallAfter(util.try_until, lambda: os.unlink(filepath))
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

        menu = wx.lib.agw.flatmenu.FlatMenu()
        item_sel = wx.lib.agw.flatmenu.FlatMenuItem(menu, wx.NewId(),
               "Export selected chats into individual files")
        item_sel.Enable(len(selecteds))
        menu.AppendItem(item_sel)
        if export.xlsxwriter:
            item_sel2 = wx.lib.agw.flatmenu.FlatMenuItem(menu, wx.NewId(),
                "Export selected into a single Excel workbook, "
                "with separate sheets")
            item_sel2.Enable(len(selecteds))
            menu.AppendItem(item_sel2)
        menu.AppendSeparator()
        item_all = wx.lib.agw.flatmenu.FlatMenuItem(menu, wx.NewId(),
               "Export all chats into individual files")
        item_all.Enable(len(self.chats))
        menu.AppendItem(item_all)
        if export.xlsxwriter:
            item_all2 = wx.lib.agw.flatmenu.FlatMenuItem(menu, wx.NewId(),
                "Export all into a single Excel workbook, "
                "with separate sheets")
            item_all2.Enable(len(self.chats))
            menu.AppendItem(item_all2)
        for item in menu.GetMenuItems():
            self.Bind(wx.EVT_MENU, self.on_export_chats, item)

        sz_btn, pt_btn = event.EventObject.Size, event.EventObject.Position
        pt_btn = event.EventObject.Parent.ClientToScreen(pt_btn)
        menu.SetOwnerHeight(sz_btn.y)
        if menu.Size.width < sz_btn.width:
            menu.Size = sz_btn.width, menu.Size.height
        menu.Popup(pt_btn, self)


    def on_export_chats(self, event):
        """
        Handler for clicking to export selected or all chats, displays a select
        folder dialog and exports chats to individual files under the folder.
        """
        chats = [self.list_chats.GetItemMappedData(i)
                 for i in range(self.list_chats.ItemCount)]

        # Find menuitem index and label from original menu by event ID
        nitems = enumerate(event.EventObject.GetMenuItems())
        index = next((i for i, m in nitems if m.GetId() == event.Id), None)
        do_all = index > 1
        do_singlefile = index in [1, 4]

        if not do_all:
            selected, chats = self.list_chats.GetFirstSelected(), []
            while selected >= 0:
                chats.append(self.list_chats.GetItemMappedData(selected))
                selected = self.list_chats.GetNextSelected(selected)
        self.dialog_savefile.Message = "Choose folder where to save chat files"
        self.dialog_savefile.Filename = "Filename will be ignored"
        self.dialog_savefile.Wildcard = export.CHAT_WILDCARD
        self.dialog_savefile.WindowStyle ^= wx.FD_OVERWRITE_PROMPT
        if chats and do_singlefile:
            formatargs = collections.defaultdict(str)
            formatargs["skypename"] = os.path.basename(self.db.filename)
            formatargs.update(self.db.account or {})
            default = util.safe_filename(conf.ExportDbTemplate % formatargs)
            self.dialog_savefile.Filename = default
            self.dialog_savefile.Message = "Save chats file"
            self.dialog_savefile.Wildcard = export.CHAT_WILDCARD_SINGLEFILE
            self.dialog_savefile.WindowStyle |= wx.FD_OVERWRITE_PROMPT
        if chats and wx.ID_OK == self.dialog_savefile.ShowModal():
            dirname = os.path.dirname(self.dialog_savefile.GetPath())
            if do_singlefile:
                index = self.dialog_savefile.FilterIndex
                extname = export.CHAT_EXTS_SINGLEFILE[index]
                format = os.path.basename(self.dialog_savefile.GetPath())
            else:
                extname = export.CHAT_EXTS[self.dialog_savefile.FilterIndex]
                format = extname

            msg = "Exporting %s from \"%s\"\nas %s under %s." % \
                (util.plural("chat", chats), self.db.filename,
                 extname.upper(), dirname)
            busy = controls.BusyPanel(self, msg)
            main.logstatus(msg)
            files, count, errormsg = [], 0, None
            try:
                progressfunc = lambda *args: wx.SafeYield()
                files, count = export.export_chats(chats, dirname, format,
                    self.db, skip=do_all, progress=progressfunc)
            except Exception:
                errormsg = "Error exporting chats:\n\n%s" % \
                           traceback.format_exc()
            busy.Close()
            if not errormsg:
                main.logstatus_flash("Exported %s from %s as %s under %s.",
                                     util.plural("chat", count), self.db,
                                     extname.upper(), dirname)
                util.start_file(dirname if len(files) > 1 else files[0])
            else:
                main.logstatus_flash(errormsg)
                wx.MessageBox(errormsg, conf.Title, wx.OK | wx.ICON_WARNING)
                wx.CallAfter(support.report_error, errormsg)


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
        self.dialog_savefile.WindowStyle |= wx.FD_OVERWRITE_PROMPT
        if wx.ID_OK == self.dialog_savefile.ShowModal():
            filepath = self.dialog_savefile.GetPath()
            filename = os.path.basename(filepath)
            dirname = os.path.dirname(filepath)
            extname = export.CHAT_EXTS[self.dialog_savefile.FilterIndex]
            if not filename.lower().endswith(".%s" % extname):
                filename += ".%s" % extname
                filepath = os.path.join(dirname, extname)

            busy = controls.BusyPanel(self,
                   "Filtering and exporting \"%s\"." % self.chat["title"])
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
                    main.logstatus("Filtering and exporting to %s.", filepath)
                    progressfunc = lambda *args: wx.SafeYield()
                    export.export_chats([self.chat], dirname, filename, self.db,
                        messages=messages, progress=progressfunc)
                    main.logstatus_flash("Exported %s.", filepath)
                    util.start_file(filepath)
                else:
                    wx.MessageBox("Current filter leaves no data to export.",
                                  conf.Title, wx.OK | wx.ICON_INFORMATION)
            except Exception:
                errormsg = "Error saving %s:\n\n%s" % \
                           (filepath, traceback.format_exc())
                main.logstatus_flash(errormsg)
                wx.MessageBox(errormsg, conf.Title, wx.OK | wx.ICON_WARNING)
                wx.CallAfter(support.report_error, errormsg)
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
        if href.startswith("#") and self.html_stats.HasAnchor(href[1:]):
            self.html_stats.ScrollToAnchor(href[1:])
            wx.CallAfter(self.store_html_stats_scroll)
        elif href.startswith("file://"):
            filepath = urllib.url2pathname(href[5:])
            if filepath and os.path.exists(filepath):
                util.start_file(filepath)
            else:
                messageBox(
                    "The file \"%s\" cannot be found on this computer."
                    % (filepath),
                    conf.Title, wx.OK | wx.ICON_INFORMATION
                )
        elif href.startswith("sort://"):
            self.stats_sort_field = href[7:]
            self.populate_chat_statistics()
        elif href.startswith("clouds://"):
            self.stats_expand_clouds = ast.literal_eval(href[9:])
            self.populate_chat_statistics()
        elif href.startswith("message:"):
            self.show_stats(False)
            self.stc_history.FocusMessage(int(href[8:]))
        else:
            self.stc_history.SearchBarVisible = True
            self.show_stats(False)
            self.stc_history.Search(href, flags=wx.stc.STC_FIND_WHOLEWORD)
            self.stc_history.SetFocusSearch()


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
                menu.AppendItem(item_selection)
                menu.AppendSeparator()
                menu.AppendItem(item_selectall)
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
                    href = urllib.url2pathname(href[5:])
                    if any(href.startswith(x) for x in ["\\\\\\", "///"]):
                        href = href[3:] # Strip redundant filelink slashes
                    if isinstance(href, unicode):
                        # Workaround for wx.html.HtmlWindow double encoding
                        href = href.encode('latin1', errors="xmlcharrefreplace"
                               ).decode("utf-8")
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
                menu.AppendItem(item_selection)
                menu.AppendItem(item_copy)
                menu.AppendItem(item_selectall)
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
                filename = path = urllib.url2pathname(href[5:])
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
                item = self.tree_tables.GetNext(self.tree_tables.RootItem)
                while table and item and item.IsOk():
                    table2 = self.tree_tables.GetItemPyData(item)
                    if table2 and table2.lower() == table["name"].lower():
                        tableitem = item
                        break # break while table and item and itek.IsOk()
                    item = self.tree_tables.GetNextSibling(item)
                if tableitem:
                    self.notebook.SetSelection(self.pageorder[self.page_tables])
                    wx.YieldIfNeeded()
                    # Only way to create state change in wx.gizmos.TreeListCtrl
                    class HackEvent(object):
                        def __init__(self, item): self._item = item
                        def GetItem(self):        return self._item
                    self.on_change_tree_tables(HackEvent(tableitem))
                    if self.tree_tables.Selection != tableitem:
                        self.tree_tables.SelectItem(tableitem)
                        wx.YieldIfNeeded()
                    grid = self.grid_table
                    if grid.Table.filters:
                        grid.Table.ClearSort(refresh=False)
                        grid.Table.ClearFilter()
                    # Search for matching row and scroll to it.
                    table["columns"] = self.db.get_table_columns(table_name)
                    id_fields = [c["name"] for c in table["columns"]
                                 if c.get("pk_id")]
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
                            y = cell_coords.y / (pxls[1] or 15)
                            x, y = 0, y - pagesize / 2
                            grid.Scroll(x, y)
                            break # break for i in range(self.grid_table..
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
            main.status_flash("Finished searching for \"%s\" in %s.",
                result["search"]["text"], self.db.filename
            )
            self.tb_search_settings.SetToolNormalBitmap(
                wx.ID_STOP, images.ToolbarStopped.Bitmap)
            if search_id in self.workers_search:
                self.workers_search[search_id].stop()
                del self.workers_search[search_id]
        if "error" in result:
            main.log("Error searching %s:\n\n%s", self.db, result["error"])
            errormsg = "Error searching %s:\n\n%s" % \
                       (self.db, result.get("error_short", result["error"]))
            wx.MessageBox(errormsg, conf.Title, wx.OK | wx.ICON_WARNING)
            wx.CallAfter(support.report_error, errormsg)


    def on_searchall_callback(self, result):
        """Callback function for SearchThread, posts the data to self."""
        if self: # Check if instance is still valid (i.e. not destroyed by wx)
            wx.PostEvent(self, WorkerEvent(result=result))


    def on_search_contacts_callback(self, result):
        """Callback function for ContactSearchThread, posts result to self."""
        if self: # Check if instance is still valid (i.e. not destroyed by wx)
            wx.PostEvent(self, ContactWorkerEvent(result=result))


    def on_searchall(self, event):
        """
        Handler for clicking to global search the database.
        """
        text = self.edit_searchall.Value
        if text.strip():
            main.status_flash("Searching for \"%s\" in %s.",
                              text, self.db.filename)
            html = self.html_searchall
            data = {"id": wx.NewId(), "db": self.db, "text": text, "map": {},
                    "width": html.Size.width * 5/9, "table": "",
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
            conf.save()


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
                    tip = unicode(value)
            else:
                tip = unicode(value)
            tip = tip if len(tip) < 1000 else tip[:1000] + ".."
        if (row, col) != prev_cell or not (event.EventObject.ToolTip) \
        or event.EventObject.ToolTip.Tip != tip:
            event.EventObject.SetToolTipString(tip)
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
        initial values to filter controls.
        """
        for i in range(self.list_participants.GetItemCount()):
            c = self.list_participants.GetItem(i)
            c.Check(True)
            self.list_participants.SetItem(c)
        self.edit_filtertext.Value = ""
        self.range_date.SetValues(*self.chat_filter["startdaterange"])
        self.list_participants.Refresh()


    def on_filter_chat(self, event):
        """
        Handler for clicking to filter current chat history, applies the
        current filter to the chat messages.
        """
        new_filter, old_filter = self.build_filter(), self.stc_history.Filter
        current_filter = dict((t, old_filter) for t in new_filter)
        self.current_filter = current_filter
        self.new_filter = new_filter
        if new_filter != current_filter:
            self.chat_filter.update(new_filter)
            busy = controls.BusyPanel(self, "Filtering messages.")
            try:
                self.stc_history.SetFilter(self.chat_filter)
                self.stc_history.RefreshMessages()
                self.populate_chat_statistics()
            finally:
                busy.Close()
            has_messages = self.chat["message_count"] > 0
            self.tb_chat.EnableTool(wx.ID_MORE, has_messages)


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
                    self.list_participants.SetItem(i, c)
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
            pos = getattr(splitter, "_sashPosition", self.Size[1] / 3)
            splitter.SplitHorizontally(self.panel_chats1, self.panel_chats2,
                                       sashPosition=pos)
            shorthelp = "Maximize chat panel  (Alt-M)"
        self.tb_chat.SetToolShortHelp(wx.ID_ZOOM_100, shorthelp)


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


    def show_stats(self, show=True):
        """Shows or hides the statistics window."""
        html, stc = self.html_stats, self.stc_history
        changed = False
        focus = False
        for i in [html, stc]:
            focus = focus or (i.Shown and i.FindFocus() == i)
        if not stc.Shown != show:
            stc.Show(not show)
            changed = True
        if html.Shown != show:
            html.Show(show)
            changed = True
        if changed:
            stc.ContainingSizer.Layout()
        if focus: # Switch focus to the other control if previous had focus
            (html if show else stc).SetFocus()
        if show:
            if hasattr(html, "_last_scroll_pos"):
                html.Scroll(*html._last_scroll_pos)
            elif html.HasAnchor(html.OpenedAnchor):
                html.ScrollToAnchor(html.OpenedAnchor)
        self.tb_chat.ToggleTool(wx.ID_PROPERTIES, show)


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
            self.dialog_savefile.WindowStyle |= wx.FD_OVERWRITE_PROMPT
            if wx.ID_OK == self.dialog_savefile.ShowModal():
                filename = self.dialog_savefile.GetPath()
                exts = export.TABLE_EXTS if grid_source is self.grid_table \
                       else export.QUERY_EXTS
                extname = exts[self.dialog_savefile.FilterIndex]
                if not filename.lower().endswith(".%s" % extname):
                    filename += ".%s" % extname
                busy = controls.BusyPanel(self, "Exporting \"%s\"." % filename)
                main.status("Exporting \"%s\".", filename)
                try:
                    export.export_grid(grid_source, filename, title,
                                       self.db, sql, table)
                    main.logstatus_flash("Exported %s.", filename)
                    util.start_file(filename)
                except Exception:
                    msg = "Error saving %s:\n\n%s" % \
                          (filename, traceback.format_exc())
                    main.logstatus_flash(msg)
                    wx.MessageBox(msg, conf.Title, wx.OK | wx.ICON_WARNING)
                    wx.CallAfter(support.report_error, msg)
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
                main.log("Executing SQL script \"%s\".", sql)
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
            main.logstatus_flash(msg)
            wx.MessageBox(msg, conf.Title, wx.OK | wx.ICON_WARNING)


    def execute_sql(self, sql):
        """Executes the SQL query and populates the SQL grid with results."""
        try:
            grid_data = None
            if sql.lower().startswith(("select", "pragma", "explain")):
                # SELECT statement: populate grid with rows
                grid_data = SqliteGridBase.from_query(self.db, sql)
                self.grid_sql.SetTable(grid_data)
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
            main.logstatus_flash("Executed SQL \"%s\" (%s).", sql, self.db)
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
            main.logstatus_flash(msg)
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
                template = "Error saving table %s in \"%s\".\n\n%%r" % (
                           grid.table, self.db)
                msg, msgfull = template % e, template % traceback.format_exc()
                main.status_flash(msg), main.log(msgfull)
                wx.MessageBox(msg, conf.Title, wx.OK | wx.ICON_WARNING)
                wx.CallAfter(support.report_error, msgfull)
                break # break for grid
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
        item = self.tree_tables.GetNext(self.tree_tables.RootItem)
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
                break # break for i in range(self.parent_notebook..


    def on_commit_table(self, event):
        """Handler for clicking to commit the changed database table."""
        info = self.grid_table.Table.GetChangedInfo()
        if wx.OK == wx.MessageBox(
            "Are you sure you want to commit these changes (%s)?" %
            info, conf.Title, wx.OK | wx.CANCEL | wx.ICON_QUESTION
        ):
            main.log("Committing %s in table %s (%s).", info,
                     self.grid_table.Table.table, self.db)
            self.grid_table.Table.SaveChanges()
            self.on_change_table(None)
            # Refresh tables list with updated row counts
            tablemap = dict((t["name"], t) for t in self.db.get_tables(True))
            item = self.tree_tables.GetNext(self.tree_tables.RootItem)
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
            # Refresh cell colours; without CallAfter wx 2.8 can crash
            wx.CallLater(0, self.grid_table.ForceRefresh)


    def on_rollback_table(self, event):
        """Handler for clicking to rollback the changed database table."""
        self.grid_table.Table.UndoChanges()
        self.on_change_table(None)
        # Refresh scrollbars and colours; without CallAfter wx 2.8 can crash
        wx.CallLater(0, lambda: (self.grid_table.ContainingSizer.Layout(),
                                 self.grid_table.ForceRefresh()))


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
        # Refresh scrollbars; without CallAfter wx 2.8 can crash
        wx.CallAfter(self.grid_table.ContainingSizer.Layout)


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
            i = self.tree_tables.GetNext(self.tree_tables.RootItem)
            while i:
                text = self.tree_tables.GetItemText(i).lower()
                self.tree_tables.SetItemBold(i, text == lower)
                i = self.tree_tables.GetNextSibling(i)
            main.log("Loading table %s (%s).", table, self.db)
            busy = controls.BusyPanel(self, "Loading table \"%s\"." % table)
            try:
                grid_data = self.db_grids.get(lower)
                if not grid_data:
                    grid_data = SqliteGridBase.from_table(self.db, table)
                    self.db_grids[lower] = grid_data
                self.label_table.Label = "Table \"%s\":" % table
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
            except Exception:
                busy.Close()
                errormsg = "Could not load table %s.\n\n%s" % \
                           (table, traceback.format_exc())
                main.logstatus_flash(errormsg)
                wx.MessageBox(errormsg, conf.Title, wx.OK | wx.ICON_WARNING)
                wx.CallAfter(support.report_error, errormsg)


    def on_change_list_chats(self, event):
        """
        Handler for selecting an item in the chats list, loads the
        messages into the message log.
        """
        self.load_chat(self.list_chats.GetItemMappedData(event.Index))


    def load_chat(self, chat, center_message_id=None):
        """Loads history of the specified chat (as returned from db)."""
        if chat and (chat != self.chat or center_message_id):
            busy = None
            if chat != self.chat:
                # Update chat list colours and scroll to the opened chat
                main.log("Opening %s.", chat["title_long_lc"])
                self.list_chats.Freeze()
                scrollpos = self.list_chats.GetScrollPos(wx.VERTICAL)
                index_selected = -1
                for i in range(self.list_chats.ItemCount):
                    if self.list_chats.GetItemMappedData(i) == self.chat:
                        self.list_chats.SetItemFont(i, self.list_chats.Font)
                    elif self.list_chats.GetItemMappedData(i) == chat:
                        index_selected = i
                        f = self.list_chats.Font; f.SetWeight(wx.FONTWEIGHT_BOLD)
                        self.list_chats.SetItemFont(i, f)
                if index_selected >= 0:
                    delta = index_selected - scrollpos
                    if delta < 0 or abs(delta) >= self.list_chats.CountPerPage:
                        nudge = -self.list_chats.CountPerPage / 2
                        self.list_chats.ScrollLines(delta + nudge)
                self.list_chats.Thaw()
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
                    main.logstatus_flash("Notice: failed to refresh %s.\n\n%s",
                        chat["title_long_lc"], traceback.format_exc())
                self.edit_filtertext.Value = self.chat_filter["text"] = ""
                dts = "first_message_datetime", "last_message_datetime"
                date_range = [chat[n].date() if chat[n] else None for n in dts]
                self.chat_filter["daterange"] = date_range
                self.chat_filter["startdaterange"] = date_range
                dates_range = dates_values = date_range
                avatar_default = images.AvatarDefault.Bitmap
                if chat != self.chat:
                    # If chat has changed, load avatar images for the contacts
                    self.list_participants.ClearAll()
                    self.list_participants.InsertColumn(0, "")
                    sz_avatar = conf.AvatarImageSize
                    il = wx.ImageList(*sz_avatar)
                    il.Add(avatar_default)
                    self.list_participants.AssignImageList(
                        il, wx.IMAGE_LIST_SMALL)
                    index = 0
                    # wx will otherwise open a warning dialog on image error
                    nolog = wx.LogNull()
                    for p in chat["participants"]:
                        b = 0
                        if not p["contact"].get("avatar_bitmap"):
                            bmp = skypedata.get_avatar(p["contact"], sz_avatar)
                            if bmp:
                                p["contact"]["avatar_bitmap"] = bmp
                        if "avatar_bitmap" in p["contact"]:
                            b = il.Add(p["contact"]["avatar_bitmap"])
                        self.list_participants.InsertImageStringItem(index,
                            "%s (%s)" % (p["contact"]["name"], p["identity"]),
                            b, it_kind=1)
                        c = self.list_participants.GetItem(index)
                        c.Check(True)
                        self.list_participants.SetItem(c)
                        self.list_participants.SetItemData(index, p)
                        index += 1
                    del nolog # Restore default wx message logger
                    self.list_participants.SetColumnWidth(0, wx.LIST_AUTOSIZE)
                self.chat_filter["participants"] = [
                    p["identity"] for p in chat["participants"]]

            if center_message_id and self.chat == chat:
                if not self.stc_history.IsMessageShown(center_message_id):
                    self.stc_history.SetFilter(self.chat_filter)
                    self.stc_history.RefreshMessages(center_message_id)
                else:
                    self.stc_history.FocusMessage(center_message_id)
            else:
                self.stc_history.SetFilter(self.chat_filter)
                try:
                    self.stc_history.Populate(chat, self.db,
                        center_message_id=center_message_id)
                except Exception:
                    errormsg = "Error loading %s:\n\n%s" % \
                               (chat["title_long_lc"], traceback.format_exc())
                    main.logstatus_flash(errormsg)
                    wx.MessageBox(errormsg, conf.Title, wx.OK | wx.ICON_WARNING)

            if self.stc_history.GetMessage(0):
                values = [self.stc_history.GetMessage(0)["datetime"],
                    self.stc_history.GetMessage(-1)["datetime"]
                ]
                dates_values = tuple(i.date() for i in values)
                if not any(filter(None, dates_range)):
                    dts = "first_message_datetime", "last_message_datetime"
                    dates_range = [chat[n].date() if chat[n] else None for n in dts]
                if not any(filter(None, dates_range)):
                    dates_range = dates_values
                self.chat_filter["daterange"] = dates_range
                self.chat_filter["startdaterange"] = dates_values
            self.range_date.SetRange(*dates_range)
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
            self.populate_chat_statistics()
            if self.html_stats.Shown:
                self.show_stats(True) # To restore scroll position


    def populate_chat_statistics(self):
        """Populates html_stats with chat statistics and word cloud."""
        stats, html = self.stc_history.GetStatisticsData(), ""
        if stats:
            data = {"db": self.db, "participants": [],
                    "chat": self.chat, "sort_by": self.stats_sort_field,
                    "stats": stats, "images": {}, "authorimages": {},
                    "imagemaps": {}, "authorimagemaps": {},
                    "expand_clouds": self.stats_expand_clouds}
            # Fill avatar images
            fs, defaultavatar = self.memoryfs, "avatar__default.jpg"
            if defaultavatar not in fs["files"]:
                bmp = images.AvatarDefault.Bitmap
                fs["handler"].AddFile(defaultavatar, bmp, wx.BITMAP_TYPE_BMP)
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
                    fn = "%s_%s.jpg" % tuple(map(urllib.quote, vals))
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
                fn = "%s_%s_%s.png" % tuple(map(urllib.quote, vals))
                if fn in fs["files"]:
                    fs["handler"].RemoveFile(fn)
                bardata = sorted(histdata.items())
                bmp, rects = controls.BuildHistogram(bardata, *PLOTCONF[histtype])
                fs["handler"].AddFile(fn, bmp, wx.BITMAP_TYPE_PNG)
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
                    fn = "%s_%s_%s_%s.png" % tuple(map(urllib.quote, vals))
                    if fn in fs["files"]:
                        fs["handler"].RemoveFile(fn)
                    bardata = sorted(histdata.items())
                    bmp, rects = controls.BuildHistogram(bardata, *PLOTCONF[histtype])
                    fs["handler"].AddFile(fn, bmp, wx.BITMAP_TYPE_PNG)
                    fs["files"][fn] = 1
                    data["authorimages"][author][histtype] = fn
                    areas, msgs = [], hists["%s-firsts" % histtype]
                    for i, (interval, val) in enumerate(bardata):
                        if interval in msgs:
                            areas.append((rects[i], "message:%s" % msgs[interval]))
                    if author not in data["authorimagemaps"]:
                        data["authorimagemaps"][author] = {}
                    data["authorimagemaps"][author][histtype] = areas

            html = step.Template(templates.STATS_HTML, escape=True).expand(data)

        previous_anchor = self.html_stats.OpenedAnchor
        previous_scrollpos = getattr(self.html_stats, "_last_scroll_pos", None)
        self.html_stats.Freeze()
        self.html_stats.SetPage(html)
        self.html_stats.BackgroundColour = conf.BgColour
        if previous_scrollpos:
            self.html_stats.Scroll(*previous_scrollpos)
        elif previous_anchor and self.html_stats.HasAnchor(previous_anchor):
            self.html_stats.ScrollToAnchor(previous_anchor)
        self.html_stats.Thaw()


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
                current_filter = unicode(grid_data.filters[col]) \
                                 if col in grid_data.filters else ""
                dialog = wx.TextEntryDialog(self,
                    "Filter column \"%s\" by:" % grid_data.columns[col]["name"],
                    "Filter", defaultValue=current_filter,
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
                tabid = wx.NewId() if 0 != last_search.get("id") else 0
                self.html_searchall.InsertTab(0, title, tabid, html, info)

            # Populate the chats list
            self.chats = self.db.get_conversations()
            for c in self.chats:
                c["people"] = "" # Set empty data, stats will come later
            self.list_chats.Populate(self.chats)

            wx.CallLater(100, self.load_later_data)
        except Exception:
            wx.CallAfter(self.update_tabheader)
            errormsg = "Could not load chat list from %s.\n\n%s" % \
                       (self.db, traceback.format_exc())
            main.logstatus_flash(errormsg)
            wx.CallAfter(support.report_error, errormsg)
        wx.CallLater(500, self.update_info_page, False)
        wx.CallLater(200, self.load_tables_data)


    def load_later_data(self):
        """
        Loads later data from the database, like table metainformation and
        statistics for all chats, used as a background callback to speed
        up page opening.
        """
        try:
            # Load chat statistics and update the chat list
            self.db.get_conversations_stats(self.chats)
            for c in self.chats:
                people = sorted([p["identity"] for p in c["participants"]])
                if skypedata.CHATS_TYPE_SINGLE != c["type"]:
                    c["people"] = "%s (%s)" % (len(people), ", ".join(people))
                else:
                    people = [p for p in people if p != self.db.id]
                    c["people"] = ", ".join(people)

            if self.chat:
                # If the user already opened a chat while later data
                # was loading, update the date range control values.
                date_range = [self.chat["first_message_datetime"].date()
                              if self.chat["first_message_datetime"] else None,
                              self.chat["last_message_datetime"].date()
                              if self.chat["last_message_datetime"] else None ]
                self.range_date.SetRange(*date_range)
            main.status_flash("Opened Skype database %s.", self.db)
        except Exception:
            if self:
                errormsg = "Error loading additional data from %s.\n\n%s" % \
                           (self.db, traceback.format_exc())
                main.logstatus_flash(errormsg)
                wx.CallAfter(support.report_error, errormsg)
        if self:
            # Refresh list from loaded data, sort by last message datetime
            sortfunc = lambda l: l and (l.ResetColumnWidths(),
                                        l.SortListItems(4, 0))
            wx.CallLater(0, sortfunc, self.list_chats)
            wx.CallAfter(self.update_tabheader)


    def load_tables_data(self):
        """Loads table data into table tree and SQL editor."""
        try:
            tables = self.db.get_tables()
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

                for col in self.db.get_table_columns(table["name"]):
                    subchild = self.tree_tables.AppendItem(child, col["name"])
                    self.tree_tables.SetItemText(subchild, col["type"], 1)
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
                errormsg = "Error loading table data from %s.\n\n%s" % \
                           (self.db, traceback.format_exc())
                main.log(errormsg)
                wx.CallAfter(support.report_error, errormsg)


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
        main.status("Opening databases %s and %s.", self.db1, self.db2)
        self.db1.register_consumer(self), self.db2.register_consumer(self)
        self.title = title
        parent_notebook.InsertPage(1, self, title)
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
        button_swap.SetToolTipString("Swaps left and right database, "
                                     "changing merge direction.")
        self.Bind(wx.EVT_BUTTON, self.on_swap, button_swap)
        sizer_header.Add(label, border=5, proportion=1,
                         flag=wx.GROW | wx.TOP | wx.BOTTOM)
        sizer_header.Add(button_swap, border=5, flag=wx.LEFT | wx.RIGHT | 
                         wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(sizer_header, flag=wx.GROW)
        sizer.Layout() # To avoid header moving around during page creation

        bookstyle = wx.lib.agw.fmresources.INB_LEFT
        if (wx.version().startswith("2.8") and sys.version_info[0:] == [2]
        and sys.version_info < (2,7,3)):
            # wx 2.8 + Python below 2.7.3: labelbook can partly cover tab area
            bookstyle |= wx.lib.agw.fmresources.INB_FIT_LABELTEXT
        notebook = self.notebook = wx.lib.agw.labelbook.FlatImageBook(
            parent=self, agwStyle=bookstyle,
            style=wx.BORDER_STATIC)
        sizer.Add(notebook, proportion=10, border=5,
                  flag=wx.GROW | wx.LEFT | wx.RIGHT | wx.BOTTOM)

        il = wx.ImageList(32, 32)
        idx1 = il.Add(images.PageMergeAll.Bitmap)
        idx2 = il.Add(images.PageMergeChats.Bitmap)
        idx3 = il.Add(images.PageContacts.Bitmap)
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
        busy.Close()


    def create_page_merge_all(self, notebook):
        """Creates a page for merging all chats at once."""
        page = self.page_merge_all = wx.lib.scrolledpanel.ScrolledPanel(notebook)
        self.pageorder[page] = len(self.pageorder)
        notebook.AddPage(page, "Merge all")

        panel = wx.Panel(page, style=wx.BORDER_STATIC)
        label1 = self.label_all1 = wx.StaticText(panel, style=wx.ALIGN_RIGHT,
            label="%s\n\nAnalyzing..%s" % (self.db1.filename, "\n" * 7))
        bmp_arrow = wx.StaticBitmap(panel, bitmap=images.MergeToRight.Bitmap)
        label2 = self.label_all2 = wx.StaticText(panel,
            label="%s\n\nAnalyzing..%s" % (self.db2.filename, "\n" * 7))
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
            c.BackgroundColour = conf.BgColour
        gauge.ForegroundColour = conf.GaugeColour
        button_scan.Enabled = button_merge.Enabled = False
        button_scan.MinSize = button_merge.MinSize = (400, -1)
        html.SetFonts(normal_face=self.Font.FaceName,
                      fixed_face=self.Font.FaceName, sizes=[8] * 7)
        html.BackgroundColour = conf.MergeHtmlBackgroundColour
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
                      name="chats_label"), flag=wx.ALIGN_CENTER)
        sizer_top.AddStretchSpacer()
        label_filter = wx.StaticText(panel1, label="Filter ch&ats:")
        sizer_top.Add(label_filter, flag=wx.ALL, border=5)
        edit_chatfilter = self.edit_chatfilter = wx.TextCtrl(
            parent=panel1, size=(75, -1))
        filter_tooltip = "Filter items in chat list"
        label_filter.SetToolTipString(filter_tooltip)
        edit_chatfilter.SetToolTipString(filter_tooltip)
        self.Bind(wx.EVT_TEXT, self.on_change_chatfilter, edit_chatfilter)
        sizer_top.Add(edit_chatfilter, flag=wx.BOTTOM | wx.ALIGN_TOP, border=5)
        sizer_top.AddSpacer(20)
        self.button_merge_chats = wx.Button(panel1, label="Merge &selected")
        chats_tooltip = "Merge differences in selected chats to the right"
        self.button_merge_chats.SetToolTipString(chats_tooltip)
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
        panel_stc2.BackgroundColour = conf.BgColour
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
        button_merge.BackgroundColour = conf.BgColour
        button_export.BackgroundColour = conf.BgColour
        button_merge.Enabled = button_export.Enabled = False

        sizer_stc1.Add(stc1, proportion=1, flag=wx.GROW)
        sizer_stc2.AddStretchSpacer()
        sizer_stc2.Add(button_merge, border=5, flag=wx.ALIGN_CENTER_VERTICAL | 
                       wx.ALL | wx.GROW)
        sizer_stc2.Add(button_export, border=5, flag=wx.ALIGN_CENTER_VERTICAL | 
                       wx.ALL | wx.GROW)
        sizer_stc2.AddStretchSpacer()
        sizer2.Add(label_chat, border=5, flag=wx.ALL)
        sizer2.Add(splitter_diff, proportion=1, flag=wx.GROW)

        sizer.AddSpacer(5)
        sizer.Add(splitter, border=5, proportion=1, flag=wx.GROW | wx.ALL)
        splitter_diff.SetSashGravity(0.5)
        splitter_diff.SplitVertically(panel_stc1, panel_stc2,
                                      sashPosition=self.Size.width)
        splitter.SplitHorizontally(panel1, panel2,
                                   sashPosition=self.Size.height / 3)
        panel_stc2.SetupScrolling()


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
        panel2.BackgroundColour = conf.BgColour
        sizer1 = panel1.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer2 = panel2.Sizer = wx.BoxSizer(wx.VERTICAL)

        sizer_top = wx.BoxSizer(wx.HORIZONTAL)
        lbl = wx.StaticText(parent=panel1, label="New &contacts on the left:",
                            name="contact_list_label")
        sizer_top.Add(lbl, flag=wx.ALIGN_BOTTOM)
        sizer_top.AddStretchSpacer()
        label_filter = wx.StaticText(panel1, label="Filter c&ontacts:")
        sizer_top.Add(label_filter, flag=wx.ALIGN_CENTER | wx.ALIGN_RIGHT | 
                      wx.RIGHT, border=5)
        edit_contactfilter = self.edit_contactfilter = wx.TextCtrl(
            parent=panel1, size=(75, -1))
        filter_tooltip = "Filter items in contact lists"
        label_filter.SetToolTipString(filter_tooltip)
        edit_contactfilter.SetToolTipString(filter_tooltip)
        self.Bind(wx.EVT_TEXT, self.on_change_contactfilter,
                  edit_contactfilter)
        sizer_top.Add(edit_contactfilter)

        list1 = self.list_contacts = controls.SortableListView(
            parent=panel1,  style=wx.LC_REPORT, name="contact_list")
        list1.SetColumns(self.contacts_list_columns)
        list1.SetColumnsMaxWidth(300)
        self.Bind(
            wx.EVT_LIST_ITEM_SELECTED, self.on_select_list_contacts, list1)
        self.Bind(
            wx.EVT_LIST_ITEM_DESELECTED, self.on_select_list_contacts, list1)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_merge_contacts, list1)

        button1 = self.button_merge_contacts = controls.NoteButton(
            panel2, label="&Merge selected to the right",
            note="Copy selected contacts to the database on the right.",
            bmp=images.ButtonMergeLeft.Bitmap)
        button_all1 = self.button_merge_allcontacts = controls.NoteButton(
            panel2, label="Merge &all to the right",
            note="Copy all contacts to the database on the right.",
            bmp=images.ButtonMergeLeftMulti.Bitmap)
        button1.BackgroundColour = button_all1.BackgroundColour = conf.BgColour
        button1.Bind(wx.EVT_BUTTON, self.on_merge_contacts)
        button_all1.Bind(wx.EVT_BUTTON, self.on_merge_contacts)
        button1.Enabled = button_all1.Enabled = False
        sizer1.Add(sizer_top, flag=wx.GROW | wx.BOTTOM | wx.RIGHT, border=5)
        sizer1.Add(list1, proportion=1, flag=wx.GROW | wx.BOTTOM | wx.RIGHT,
                   border=5)
        sizer2.AddStretchSpacer()
        sizer2.Add(button1, flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL | wx.GROW,
                   border=5)
        sizer2.Add(button_all1, flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL | 
                   wx.GROW, border=5)
        sizer2.AddStretchSpacer()

        splitter.SplitVertically(panel1, panel2, sashPosition=self.Size.width)

        sizer.AddSpacer(10)
        sizer.Add(splitter, proportion=1, border=5,
                  flag=wx.GROW | wx.LEFT | wx.RIGHT)
        panel2.SetupScrolling()


    def split_panels(self):
        """
        Splits all SplitterWindow panels. To be called after layout in
        Linux wx 2.8, as otherwise panels do not get sized properly.
        """
        if not self:
            return
        sash_pos = self.Size[1] / 3
        panel1, panel2 = self.splitter_merge.Children
        self.splitter_merge.Unsplit()
        self.splitter_merge.SplitHorizontally(panel1, panel2, sash_pos)
        sash_pos = self.page_merge_contacts.Size[0] / 2
        panel1, panel2 = self.splitter_contacts.Children
        self.splitter_contacts.Unsplit()
        self.splitter_contacts.SplitVertically(panel1, panel2, sash_pos)


    def on_export_chat(self, event):
        """
        Handler for clicking to export a chat diff, displays a save file dialog
        and saves the current messages to file.
        """
        formatargs = collections.defaultdict(str); formatargs.update(self.chat)
        default = "Diff of %s" % conf.ExportChatTemplate % formatargs
        dialog = wx.FileDialog(parent=self, message="Save new messages",
            defaultDir=os.getcwd(), defaultFile=util.safe_filename(default),
            style=wx.FD_OVERWRITE_PROMPT | wx.FD_SAVE | wx.RESIZE_BORDER
        )
        dialog.Wildcard = export.CHAT_WILDCARD
        if wx.ID_OK == dialog.ShowModal():
            filepath = dialog.GetPath()
            dirname = os.path.dirname(filepath)
            filename = os.path.basename(filepath)
            extname = export.CHAT_EXTS[dialog.FilterIndex]
            if not filename.lower().endswith(".%s" % extname):
                filename += ".%s" % extname
                filepath = os.path.join(dirname, filename)
            busy = controls.BusyPanel(
                self, "Exporting \"%s\"." % self.chat["title"]
            )
            main.logstatus("Exporting to %s.", filepath)
            try:
                messages = self.db1.message_iterator(self.chat_diff["messages"])
                progressfunc = lambda *args: wx.SafeYield()
                export.export_chats([self.chat], dirname, filename,
                    self.db1, messages=messages, progress=progressfunc)
                main.logstatus_flash("Exported %s.", filepath)
                util.start_file(filepath)
            except Exception:
                errormsg = "Error saving %s:\n\n%s" % \
                           (filepath, traceback.format_exc())
                main.logstatus_flash(errormsg)
                wx.MessageBox(errormsg, conf.Title, wx.OK | wx.ICON_WARNING)
                wx.CallAfter(support.report_error, errormsg)
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
                break # break for c in self.compared
        if chat and self.page_merge_chats.Enabled:
            self.on_change_list_chats(chat=chat)
            self.notebook.SetSelection(self.pageorder[self.page_merge_chats])


    def on_worker_merge_result(self, event):
        """Handler for worker_merge result callback, updates UI and texts."""
        if event.result.get("type") in ["merge_left", "diff_merge_left"]:
            self.on_merge_all_result(event)
        elif "diff_left" == event.result.get("type"):
            self.on_scan_all_result(event)


    def on_worker_merge_callback(self, result):
        """Callback function for MergeThread, posts the data to self."""
        if self: # Check if instance is still valid (i.e. not destroyed by wx)
            wx.PostEvent(self, WorkerEvent(result=result))


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
            info = util.plural("selected chat", selecteds)
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
                self.html_report.SetPage("<body bgcolor='%s'><b>%s progress:"
                    "</b><br />" % (conf.MergeHtmlBackgroundColour, action))
                db1, db2 = self.db1, self.db2
                chats = list(filter(None, selecteds))
                if self.is_scanned:
                    type = "merge_left"
                    cc = [self.chats_diffdata.get(c["identity"]) for c in chats]
                    chats = list(filter(None, cc))
                else:
                    type = "diff_merge_left"
                params = locals()
                self.worker_merge.work(params)
                self.is_merging = True
                main.logstatus("Merging %s from %s to %s.", info, db1, db2)
                self.notebook.SetSelection(0)


    def on_link_db(self, event):
        """Handler on clicking a database link, opens the database tab."""
        self.TopLevelParent.load_database_page(event.GetLinkInfo().Href)


    def on_select_list_contacts(self, event):
        """
        Handler for changing selection in contacts list, updates button states.
        """
        lst = self.list_contacts
        self.button_merge_contacts.Enabled = lst.SelectedItemCount


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
        lst = self.list_contacts
        lst.SetFilter(event.String.strip())
        self.button_merge_contacts.Enabled = lst.SelectedItemCount
        self.button_merge_allcontacts.Enabled = lst.ItemCount


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
            main.log("Comparing %s (%s vs %s).", c["title_long_lc"],
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
                    nudge = -self.list_chats.CountPerPage / 2
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
                        util.plural("chat message", messages))
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
        button = event.EventObject
        db_target, db_source = self.db2, self.db1
        list_source = self.list_contacts
        source = 0
        contacts, contactgroups, indices = [], [], []
        if button is self.button_merge_allcontacts:
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
            text_add += util.plural("contact", contacts)
        if contactgroups:
            text_add += (" and " if contacts else "") \
                       + util.plural("contact group", contactgroups)
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
            main.log("Copied %s from %s into %s.", text_add, self.db1, self.db2)
            wx.MessageBox("Copied %s\n\nfrom %s\n\ninto %s." % (text_add,
                self.db1, self.db2), conf.Title, wx.OK | wx.ICON_INFORMATION)


    def on_scan_all(self, event):
        """
        Handler for clicking to scan for differences with the left database,
        starts scanning process.
        """
        main.logstatus("Scanning differences between %s and %s.",
                       self.db1, self.db2)
        self.chats_diffdata.clear()
        self.button_merge_all.Enabled = False
        self.button_scan_all.Enabled = False
        self.button_swap.Enabled = False
        self.button_merge_chats.Enabled = False
        if not self.html_report.Shown:
            self.html_report.Show()
            self.html_report.ContainingSizer.Layout()
        html = ("<body bgcolor='%s'><font color='%s'<b>Scan results:</b>"
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
            self.html_report.Freeze()
            scrollpos = self.html_report.GetScrollPos(wx.VERTICAL)
            self.html_report.AppendToPage(result["output"])
            self.html_report.Scroll(0, scrollpos)
            self.html_report.Thaw()
        if "status" in result:
            main.status_flash(result["status"])
        if "index" in result:
            mindex, mcount = result["index"], result["count"]
            cindex, ccount = result["chatindex"], result["chatcount"]
            percent = min(100, math.ceil(100 * util.safedivf(mindex, mcount)))
            msg = "Scan %d%% complete (%s of %s)." % \
                  (percent, cindex + 1, util.plural("conversation", ccount))
            self.update_gauge(self.gauge_progress, percent, msg)
        if "done" in result:
            self.is_scanning = False
            self.is_scanned = True
            s1 = util.plural("differing chat", self.chats_diffdata)
            main.logstatus_flash("Found %s in %s.", s1, self.db1)
            self.button_swap.Enabled = True
            self.button_merge_chats.Enabled = True
            if self.chats_diffdata:
                count_msgs = util.plural(
                    "message", sum(len(d["diff"]["messages"])
                                   for d in self.chats_diffdata.values()))
                count_chats = util.plural("chat", self.chats_diffdata)
                noteinfo = "%s from %s" % (count_msgs, count_chats)
                self.button_merge_all.Note = (
                    "Copy %s to the database on the right." % noteinfo)
                self.button_merge_all.Enabled = True
                self.html_report.AppendToPage(
                    "<br /><br />New in %s: %s in %s." % 
                    (self.db1, count_msgs, count_chats))
                scrollpos = (0, self.html_report.GetScrollRange(wx.VERTICAL))
                self.html_report.Scroll(*scrollpos)
            else:
                self.html_report.SetPage("<body bgcolor='%s'>No new messages."
                    "</body>" % conf.MergeHtmlBackgroundColour)
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
                               for d in self.chats_diffdata.values()))
            count_chats = util.plural("chat", self.chats_diffdata)
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
            self.html_report.SetPage("<body bgcolor='%s'><b>Merge progress:"
                "</b><br />" % conf.MergeHtmlBackgroundColour)
            self.page_merge_chats.Enabled = False
            self.page_merge_contacts.Enabled = False
            main.logstatus("Merging %s from %s to %s.", info, db1, db2)
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
            msg = "%s %d%% complete (%s of %s)." % (action, percent,
                  cindex+1, util.plural("conversation", ccount))
            self.update_gauge(self.gauge_progress, percent, msg)
            for chat in result.get("chats", []):
                if chat["identity"] in self.chats_diffdata:
                    del self.chats_diffdata[chat["identity"]]
        if "error" in result:
            self.is_merging = False
            self.update_gauge(self.gauge_progress, 0, "%s error." % action)
            main.log("%s error.\n\n%s", action, result["error"])
            msg = "%s error.\n\n%s" % (action, 
                  result.get("error_short", result["error"]))
            scrollpos = (0, self.html_report.GetScrollPos(wx.VERTICAL))
            self.html_report.AppendToPage("<br /> <b>Error merging chats:</b>"
                                          + result["error"])
            self.html_report.Scroll(*scrollpos)
            wx.MessageBox(msg, conf.Title, wx.OK | wx.ICON_WARNING)
            wx.CallAfter(support.report_error, result["error"])
        if "status" in result:
            main.status_flash(result["status"])
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
                main.logstatus_flash(info)
                self.update_gauge(self.gauge_progress, 100, "Merge complete.")
                text = "<br /><br /> %s" % result["output"]
                self.html_report.Freeze()
                self.html_report.AppendToPage(text)
                scrollpos = (0, self.html_report.GetScrollRange(wx.VERTICAL))
                self.html_report.Scroll(*scrollpos)
                self.html_report.Thaw()
                wx.MessageBox(info, conf.Title, wx.OK | wx.ICON_INFORMATION)
            self.button_merge_all.Note = self.MERGE_BUTTON_NOTE
            self.button_swap.Enabled = True
            self.button_merge_chats.Enabled = True
            wx.CallLater(20, self.load_later_data)
            if self.is_scanned and self.chats_diffdata:
                count_msgs = util.plural(
                    "message", sum(len(d["diff"]["messages"])
                                   for d in self.chats_diffdata.values()))
                count_chats = util.plural("chat", self.chats_diffdata)
                noteinfo = "%s from %s" % (count_msgs, count_chats)
                self.button_merge_all.Note = (
                    "Copy %s to the database on the right." % noteinfo)
                self.button_merge_all.Enabled = True
        elif "output" in result and result["output"]:
            scrollpos = (0, self.html_report.GetScrollPos(wx.VERTICAL))
            self.html_report.Freeze()
            self.html_report.AppendToPage("<br /> %s" % result["output"])
            self.html_report.Scroll(*scrollpos)
            self.html_report.Thaw()


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
                    break # break for c in gauge..
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
                parts.append(util.plural("%smessage" % newstr, messages))
            if participants:
                # Add to contacts those that are new
                cc2 = [db1.id, db2.id] + \
                    [i["identity"] for i in db2.get_contacts()]
                contacts2 = [i["contact"] for i in participants
                    if "id" in i["contact"] and i["identity"] not in cc2]
                if contacts2:
                    parts.append(util.plural("new contact", contacts2))
                parts.append(util.plural("%sparticipant" % newstr,
                                         participants))
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
                        chat2["id"] = db2.insert_chat(chat2, db1)
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
                main.logstatus_flash("Merged %s of chat \"%s\" from %s to %s.",
                                     info, chat2["title"], db1, db2)
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

        try:
            # Populate the chat comparison list
            chats1 = self.db1.get_conversations()
            chats2 = self.db2.get_conversations()
            c1map = dict((c["identity"], c) for c in chats1)
            c2map = dict((c["identity"], c) for c in chats2)
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

            self.list_chats.Populate(compared)
            self.list_chats.SortListItems(3, 0) # Sort by last message in left
            self.compared = compared
            self.chats1 = chats1
            self.chats2 = chats2
            wx.CallLater(200, self.load_later_data)
        except Exception:
            wx.CallAfter(self.update_tabheader)
            errormsg = "Could not load chat lists from %s and %s.\n\n%s" % \
                       (self.db1, self.db2, traceback.format_exc())
            main.logstatus_flash(errormsg)
            wx.MessageBox(errormsg, conf.Title, wx.OK | wx.ICON_WARNING)
            wx.CallAfter(support.report_error, errormsg)


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
            for c in self.compared:
                for i in range(2):
                    cmap = c2map if i else c1map
                    if c["c%s" % (i + 1)] and c["identity"] in cmap:
                        c["messages%s" % (i + 1)] = \
                            cmap[c["identity"]]["message_count"]
                        c["last_message_datetime%s" % (i + 1)] = \
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
                    t1 = list(filter(
                         None, [c["message_count"] for c in chats]))
                    count_messages = sum(t1) if t1 else 0
                    t2 = list(filter(
                         None, [c["first_message_datetime"] for c in chats]))
                    datetime_first = min(t2) if t2 else None
                    t3 = list(filter(
                         None, [c["last_message_datetime"] for c in chats]))
                    datetime_last = max(t3) if t3 else None
                    datetext_first = "" if not datetime_first \
                        else datetime_first.strftime("%Y-%m-%d %H:%M:%S")
                    datetext_last = "" if not datetime_last \
                        else datetime_last.strftime("%Y-%m-%d %H:%M:%S")
                    contacttext = util.plural("contact", contacts)
                    if condiff:
                        contacttext += " (%d not present on the %s)" % (
                                       len(condiff), ["right", "left"][i])
                    label.Label += "%s.\n%s.\n%s.\nFirst message at %s.\n" \
                                   "Last message at %s." % (
                                   util.plural("conversation", chats),
                                   util.plural("message", count_messages), 
                                   contacttext, datetext_first, datetext_last)
        except Exception as e:
            # Database access can easily fail if the user closes the tab before
            # the later data has been loaded.
            if self:
                main.log("Error loading additional data from %s or %s.\n\n%s",
                         self.db1, self.db2, traceback.format_exc())
                wx.MessageBox("Error loading additional data from %s or %s."
                              "\n\nError: %r." % (self.db1, self.db2, e),
                              conf.Title, wx.OK | wx.ICON_WARNING)

        if self:
            self.button_swap.Enabled = True
            self.button_merge_chats.Enabled = True
            if not self.is_scanned:
                self.button_scan_all.Enabled = True
                self.button_merge_all.Enabled = True
            main.status_flash("Opened databases %s and %s.",
                              self.db1, self.db2)
            self.page_merge_all.Layout()
            self.Refresh()
            if "linux2" == sys.platform and wx.version().startswith("2.8"):
                wx.CallAfter(self.split_panels)
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
        self._messages = None   # All retrieved messages (collections.deque)
        self._messages_current = None  # Currently shown (collections.deque)
        self._message_positions = {} # {msg id: (start index, end index)}
        # If set, range is centered around the message with the specified ID
        self._center_message_id =    -1
        # Index of the centered message in _messages
        self._center_message_index = -1
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
        self.SetWrapMode(True)
        self.SetMarginLeft(10)
        self.SetReadOnly(True)
        self._stc.Bind(wx.stc.EVT_STC_HOTSPOT_CLICK, self.OnUrl)
        self._stc.Bind(wx.EVT_RIGHT_UP, self.OnMenu)
        self._stc.Bind(wx.EVT_CONTEXT_MENU, lambda e: None)
        # Hide caret
        self.SetCaretForeground(conf.BgColour), self.SetCaretWidth(0)


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


    def OnMenu(self, event):
        """
        Handler for right-clicking (or pressing menu key), opens a custom context
        menu.
        """
        def clipboardize(text):
            if wx.TheClipboard.Open():
                d = wx.TextDataObject(text)
                wx.TheClipboard.SetData(d), wx.TheClipboard.Close()

        pos = self._stc.PositionFromPoint(event.Position)
        msg_id = msg = None
        pos_msgs = sorted((v, k) for k, v in self._message_positions.items())
        for i, (m_pos, m_id) in enumerate(pos_msgs):
            if m_pos[0] <= pos <= m_pos[1]:
                msg_id = m_id
                break
            elif i and pos_msgs[i-1][0][1] < pos and m_pos[0] > pos:
                msg_id = pos_msgs[i-1][1]
                break
            elif m_pos[0] > pos:
                break
        if not msg_id and pos_msgs and pos_msgs[-1][0][-1] < pos:
            msg_id = pos_msgs[-1][1]
        if msg_id:
            msg = next((m for m in self._messages_current 
                        if msg_id == m["id"]), None)
        menu = wx.Menu()
        item_selection = wx.MenuItem(menu, -1, "&Copy selection")
        menu.AppendItem(item_selection)
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
                if not isinstance(url, unicode):
                    url = unicode(url, "utf-8", errors="replace")
            item_link = wx.MenuItem(menu, -1, "C&opy %s location" % urltype)
            menu.AppendItem(item_link)
            menu.Bind(wx.EVT_MENU, on_copyurl, id=item_link.GetId())
        else:
            def on_copymsg(event):
                t = step.Template(templates.MESSAGE_CLIPBOARD)
                clipboardize(t.expand({"m": msg, "parser": self._parser}))
            def on_selectall(event): self._stc.SelectAll()
                
            item_msg = wx.MenuItem(menu, -1, "C&opy message")
            item_select = wx.MenuItem(menu, -1, "&Select all")
            menu.AppendItem(item_msg), menu.AppendItem(item_select)
            item_msg.Enable(bool(msg))
            menu.Bind(wx.EVT_MENU, on_copymsg, id=item_msg.GetId())
            menu.Bind(wx.EVT_MENU, on_selectall, id=item_select.GetId())
        self.PopupMenu(menu)


    def OnUrl(self, event):
        """
        Handler for clicking a link in chat history, opens the link in system
        browser.
        """
        stc = event.EventObject
        styles_link = [self._styles["link"], self._styles["boldlink"]]
        if stc.GetStyleAt(event.Position) in styles_link:
            # Go back and forth from position and get URL range.
            url, url_range = self.GetUrlAtPosition(event.Position)
            function, params = None, []
            if url_range[0] in self._filelinks:
                def start_file(url):
                    if os.path.exists(url):
                        util.start_file(url)
                    else:
                        messageBox("The file \"%s\" cannot be found "
                                   "on this computer." % url,
                                   conf.Title, wx.OK | wx.ICON_INFORMATION)
                function, params = start_file, [self._filelinks[url_range[0]]]
            elif url_range[0] in self._datelinks:
                def filter_range(label, daterange):
                    busy = controls.BusyPanel(self._page or self.Parent,
                                              "Filtering messages.")
                    try:
                        self._datelink_last = label
                        if self._page:
                            self._page.chat_filter["daterange"] = daterange
                            self._page.range_date.SetValues(*daterange)
                        newfilter = self.Filter
                        newfilter["daterange"] = daterange
                        self.Filter = newfilter
                        self.RefreshMessages(), self.ScrollToLine(0)
                        if self._page:
                            self._page.populate_chat_statistics()
                    finally:
                        busy.Close()
                function = filter_range
                params = [url, self._datelinks[url_range[0]]]
            elif url:
                function, params = webbrowser.open, [url]
            if function:
                # Calling function here immediately will cause STC to lose
                # MouseUp, resulting in autoselect mode from click position.
                wx.CallLater(100, function, *params)
        event.StopPropagation()


    def SetAutoRetrieve(self, retrieve):
        """Sets whether to auto-retrieve more messages."""
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
            or self._messages[0]["datetime"].date() \
            >= self._filter["daterange"][0]:
                m_iter = self._db.get_messages(self._chat,
                    ascending=False,
                    timestamp_from=self._messages[0]["timestamp"]
                )
                while m_iter:
                    try:
                        m = m_iter.next()
                        self._messages.appendleft(m)
                        if m["datetime"].date() < self._filter["daterange"][0]:
                            m_iter = None
                    except StopIteration:
                        m_iter = None
        last_dt = self._chat.get("last_message_datetime")
        if self._messages and last_dt \
        and self._messages[-1]["datetime"] < last_dt:
            # Last message timestamp is earlier than chat's last message
            # timestamp: new messages have arrived
            m_iter = self._db.get_messages(self._chat,
                ascending=True, use_cache=False,
                timestamp_from=self._messages[-1]["timestamp"]
            )
            while m_iter:
                try:
                    m = m_iter.next()
                    self._messages.append(m)
                except StopIteration:
                    m_iter = None


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
            previous_day = None
            count = 0
            focus_message_id = None
            self._filelinks.clear()
            self._datelinks.clear()
            # For accumulating various statistics
            rgx_highlight = re.compile(
                "(%s)" % re.escape(self._filter["text"]), re.I
            ) if ("text" in self._filter and self._filter["text"]) else None
            self._messages_current = collections.deque()

            # Assemble messages to show
            for m in self._messages:
                count += 1
                if self.IsMessageFilteredOut(m):
                    continue
                if self._center_message_index >= 0 \
                and count < self._center_message_index \
                - conf.MaxHistoryInitialMessages / 2:
                    # Skip messages before the range centered around a message
                    continue
                if self._center_message_index >= 0 \
                and count > self._center_message_index \
                + conf.MaxHistoryInitialMessages / 2:
                    # Skip messages after the range centered around a message
                    break # break for m in self._messages

                self._messages_current.append(m)

            # Add date and count information, links like "6 months"
            self._append_text("\n")
            if self._messages_current:
                m1, m2 = self._messages_current[0], self._messages_current[-1]
                self._append_text("History of  ")
                self._append_text(m1["datetime"].strftime("%d.%m.%Y"), "bold")
                if m1["datetime"].date() != m2["datetime"].date():
                    self._append_text(" to ")
                    self._append_text(
                        m2["datetime"].strftime("%d.%m.%Y"), "bold")
                self._append_text("  (%s).  " % util.plural(
                                  "message", self._messages_current))
            if self._chat["message_count"]:
                self._append_text("\nShow from:  ")
                date_first = self._chat["first_message_datetime"].date()
                date_last = self._chat["last_message_datetime"].date()
                date_until = datetime.date.today()
                dates_filter = self._filter.get("daterange")
                from_items = [] # [(title, [date_first, date_last])]
                if relativedelta:
                    for unit, count in [("day", 7), ("week", 2), ("day", 30),
                    ("month", 3), ("month", 6), ("year", 1), ("year", 2)]:
                        date_from = date_until - relativedelta(
                            **{util.plural(unit, with_items=False): count})
                        if date_from >= date_first and date_from <= date_last:
                            title = util.plural(unit, count)
                            from_items.append((title, [date_from, date_last]))
                    if date_until - relativedelta(years=2) > date_first:
                        # Warning: possible mis-showing here if chat < 4 years.
                        title = "2 to 4 years"
                        daterange = [date_until - relativedelta(years=4),
                                     date_until - relativedelta(years=2)]
                        from_items.append((title, daterange))
                    if date_until - relativedelta(years=4) > date_first:
                        title = "4 years and older"
                        daterange = [date_first,
                                     date_until - relativedelta(years=4)]
                        from_items.append((title, daterange))
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
                displayname = m["from_dispname"]
                special_text = "" # Special text after name, e.g. " SMS"
                body = m["body_xml"] or ""
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

                # Store message position for FocusMessage()
                messagepos = (length_before, self.STC.Length - 2)
                self._message_positions[m["id"]] = messagepos
                if self._center_message_id == m["id"]:
                    focus_message_id = m["id"]
                if i and not i % conf.MaxHistoryInitialMessages:
                    wx.YieldIfNeeded() # To have responsive GUI

            # Reset the centered message data, as filtering should override it
            self._center_message_index = -1
            self._center_message_id = -1
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
                        "a": "link", "ss": "default"}
        other_tags = ["blink", "font", "bodystatus", "i", "span", "flag"]
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
            if type(text) is str:
                text = text.decode("utf-8")
            if type(tail) is str:
                tail = tail.decode("utf-8")
            href = None
            if "a" == e.tag:
                href = e.get("href")
                if href.startswith("file:"):
                    pathname = urllib.url2pathname(e.get("href")[5:])
                    self._filelinks[self.STC.Length] = pathname
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
        if isinstance(text, unicode):
            text = text.encode("utf-8")
        text_parts = rgx_highlight.split(text) if rgx_highlight else [text]
        bold = "bold%s" % style if "bold%s" % style in self._styles else style
        len_self = self.GetTextLength()
        self.STC.AppendTextUTF8(text)
        self.STC.StartStyling(pos=len_self, mask=0xFF)
        self.STC.SetStyling(length=len(text), style=self._styles[style])
        for i, t in enumerate(text_parts):
            if i % 2:
                self.STC.StartStyling(pos=len_self, mask=0xFF)
                self.STC.SetStyling(length=len(t), style=self._styles[bold])
            len_self += len(t)


    def _append_multiline(self, text, indent):
        """
        Appends text with new lines indented at the specified level.
        """
        if "\n" in text:
            for line in text.split("\n"):
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
        self._center_message_index = -1
        self._center_message_id = -1

        if messages is not None:
            messages_current = collections.deque(messages)
            message_range = list(messages)
            if from_index is not None:
                messages_current = collections.deque(messages[from_index:])
        else:
            m_iter = db.get_messages(chat, ascending=False)

            i = 0
            message_show_limit = conf.MaxHistoryInitialMessages
            messages_current = collections.deque()
            try:
                iterate = (i < message_show_limit)
                while iterate:
                    m = m_iter.next()
                    if m:
                        i += 1
                        messages_current.appendleft(m)
                        if m["id"] == center_message_id:
                            self._center_message_index = len(messages_current)
                            self._center_message_id = center_message_id
                    else:
                        break # break while iterate
                    if center_message_id:
                        c = self._center_message_index + message_show_limit / 2
                        iterate = ((self._center_message_index < 0) or
                                   (len(messages_current) < c))
                    else:
                        iterate = (i < message_show_limit)
            except StopIteration:
                m_iter = None
            message_range = copy.copy(messages_current)
            if self._center_message_index >= 0:
                self._center_message_index = \
                    len(messages_current) - self._center_message_index

        self._chat = chat
        self._db = db
        self._messages_current = messages_current
        self._messages = message_range
        self._filter["daterange"] = [
            messages_current[0]["datetime"].date() if messages_current else None,
            messages_current[-1]["datetime"].date() if messages_current else None
        ]
        self.RefreshMessages(center_message_id)


    def FocusMessage(self, message_id):
        """Selects and scrolls the specified message into view."""
        if message_id in self._message_positions:
            padding = -50 # So that selection does not finish at visible edge
            for p in self._message_positions[message_id]:
                # Ensure that both ends of the selection are visible
                self.STC.CurrentPos = p + padding
                self.EnsureCaretVisible()
                padding = abs(padding)
            self.STC.SetSelection(*self._message_positions[message_id])


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
        elif ("daterange" in self._filter
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
        if self._messages_current and index < 0:
            index += len(self._messages_current)
        in_len = self._messages_current and index < len(self._messages_current)
        m = self._messages_current[index] if in_len else None
        return m


    def GetMessages(self):
        """Returns a list of all the currently shown messages."""
        result = []
        if self._messages_current:
            result = list(self._messages_current)
        return result


    def GetRetrievedMessages(self):
        """Returns a list of all retrieved messages."""
        result = []
        if self._messages:
            result = list(self._messages)
        return result


    def SetFilter(self, filter_data):
        """
        Sets the filter to use for the current chat. Does not refresh messages.

        @param   filter_data  None or {"daterange":
                              (datetime, datetime), "text": text in message,
                              "participants": [skypename1, ]}
        """
        filter_data = filter_data or {}
        if not util.cmp_dicts(self._filter, filter_data):
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


    def GetStatisticsData(self):
        """
        Returns the statistics collected during last Populate(), or {}.
        """
        return self._parser.get_collected_stats() if self._parser else {}


    def ClearAll(self):
        """Delete all text in the document."""
        readonly_state = self.GetReadOnly()
        self.SetReadOnly(False)
        wx.stc.StyledTextCtrl.ClearAll(self.STC)
        self.SetReadOnly(readonly_state)



class SqliteGridBase(wx.grid.PyGridTableBase):
    """
    Table base for wx.grid.Grid, can take its data from a single table, or from
    the results of any SELECT query.
    """

    """How many rows to seek ahead for query grids."""
    SEEK_CHUNK_LENGTH = 100

    @classmethod
    def from_query(cls, db, sql):
        """
        Constructs a SqliteGridBase instance from a full SQL query.

        @param   db   SkypeDatabase instance
        @param   sql  the SQL query to execute
        """
        self = cls()
        self.is_query = True
        self.db = db
        self.sql = sql
        self.row_iterator = self.db.execute(sql)
        # Fill column information
        self.columns = []
        for col in self.row_iterator.description or []:
            coldata = {"name": col[0], "type": "TEXT"}
            self.columns.append(coldata)

        # Doing some trickery here: we can only know the row count when we have
        # retrieved all the rows, which is preferrable not to do at first,
        # since there is no telling how much time it can take. Instead, we
        # update the row count chunk by chunk.
        self.row_count = self.SEEK_CHUNK_LENGTH
        # ID here is a unique value identifying rows in this object,
        # no relation to table data
        self.idx_all = [] # An ordered list of row identifiers in rows_all
        self.rows_all = {} # Unfiltered, unsorted rows {id: row, }
        self.rows_current = [] # Currently shown (filtered/sorted) rows
        self.rowids = {} # SQLite table rowids, not applicable for query
        self.iterator_index = -1
        self.sort_ascending = False
        self.sort_column = None # Index of column currently sorted by
        self.filters = {} # {col: value, }
        self.attrs = {} # {"new": wx.grid.GridCellAttr, }
        try:
            self.SeekToRow(self.SEEK_CHUNK_LENGTH - 1)
        except Exception:
            pass
        # Seek ahead on rows and get column information from there
        if self.rows_current:
            for coldata in self.columns:
                name = coldata["name"]
                if type(self.rows_current[0][name]) in [int, long, bool]:
                    coldata["type"] = "INTEGER"
                elif type(self.rows_current[0][name]) in [float]:
                    coldata["type"] = "REAL"
        return self


    @classmethod
    def from_table(cls, db, table, where="", order=""):
        """
        Constructs a SqliteGridBase instance from a single table.

        @param   db     SkypeDatabase instance
        @param   table  name of table
        @param   where  SQL WHERE clause, without "where" (e.g. "a=b AND c<3")
        @param   order  full SQL ORDER clause (e.g. "ORDER BY a DESC, b ASC")
        """
        self = cls()
        self.is_query = False
        self.db = db
        self.table = table
        self.where = where
        self.order = order
        self.columns = db.get_table_columns(table)
        self.row_count = list(db.execute(
            "SELECT COUNT(*) AS rows FROM %s %s %s" % (table, where, order)
        ))[0]["rows"]
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
        self.row_iterator = db.execute(
            "SELECT rowid AS %s, * FROM %s %s %s" % (self.rowid_name, table, 
            "WHERE %s" % where if where else "", order))
        self.iterator_index = -1
        self.sort_ascending = False
        self.sort_column = None # Index of column currently sorted by
        self.filters = {} # {col: value, }
        self.attrs = {} # {"new": wx.grid.GridCellAttr, }
        return self


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
                rowdata = self.row_iterator.next()
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
                if type(value) is buffer:
                    value = str(value).decode("latin1")
        if value and "BLOB" == self.columns[col]["type"]:
            # Blobs need special handling, as the text editor does not
            # support control characters or null bytes.
            value = value.encode("unicode-escape")
        return value if value is not None else ""


    def GetRow(self, row):
        """Returns the data dictionary of the specified row."""
        value = None
        if row < self.row_count:
            self.SeekToRow(row)
            if row < len(self.rows_current):
                value = self.rows_current[row]
        return value


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
            pass#if self.View: self.View.Fit()
        else:
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
        compare = cmp
        if 0 <= col < len(self.columns):
            col_name = self.columns[col]["name"]
            def compare(a, b):
                aval, bval = a[col_name], b[col_name]
                aval = aval.lower() if hasattr(aval, "lower") else aval
                bval = bval.lower() if hasattr(bval, "lower") else bval
                return cmp(aval, bval)
        self.rows_current.sort(cmp=compare, reverse=self.sort_ascending)
        if self.View:
            self.View.ForceRefresh()


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
            main.logstatus("Error saving changes in %s.\n\n%s",
                           self.table, traceback.format_exc())
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
            flag=wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        hbox1.Add(self.text_days, border=5, flag=wx.LEFT | wx.ALIGN_RIGHT)

        self.text_hours = wx.SpinCtrl(parent=self, style=wx.ALIGN_LEFT,
           size=(200, -1), value=str(hours), min=-sys.maxsize, max=sys.maxsize)
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        hbox2.AddStretchSpacer()
        hbox2.Add(wx.StaticText(parent=self, label="Hours:"),
                  flag=wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        hbox2.Add(self.text_hours, border=5, flag=wx.LEFT | wx.ALIGN_RIGHT)

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



class SkypeHandler(Skype4Py.Skype if Skype4Py else object):
    """A convenience wrapper around Skype4Py functionality."""

    def __init__(self):
        if Skype4Py:
            # Hack Skype4Py to avoid uncatchable error on refusing Skype access.
            # The original attachment_changed raises an exception on refusal,
            # and it cannot be caught as it rises in a callback thread.
            def attach_override(self, status):
                try:
                    self.skype._CallEventHandler("AttachmentStatus", status)
                    if status == Skype4Py.apiAttachRefused:
                        wx.CallAfter(wx.MessageBox, "Skype API access failed.", 
                                     conf.Title, wx.ICON_WARNING)
                except Exception: pass
            try:
                Skype4Py.skype.APINotifier.attachment_changed = attach_override
            except Exception: pass
            Skype4Py.Skype.__init__(self)


    def shutdown(self):
        """Posts a message to the running Skype application to close itself."""
        self.Client.Shutdown()


    def is_running(self):
        """Returns whether Skype is currently running."""
        return self.Client.IsRunning


    def launch(self):
        """Tries to launch Skype."""
        self.Client.Start()


    def search_users(self, value):
        """
        Searches for users with the specified value (either name, phone or
        e-mail) in the currently running Skype application.
        """
        if not self.is_running():
            self.launch()
        self.FriendlyName = conf.Title
        self.Attach() # Should open a confirmation dialog in Skype

        result = list(self.SearchForUsers(value))
        return result


    def add_to_contacts(self, users):
        """
        Adds the specified Skype4Py.User instances to Skype contacts in the
        currently running Skype application.
        """
        if not self.is_running():
            self.launch()
        self.FriendlyName = conf.Title
        self.Attach() # Should open a confirmation dialog in Skype
        for user in users:
            user.BuddyStatus = Skype4Py.enums.budPendingAuthorization
        self.Client.Focus()



class AboutDialog(wx.Dialog):
 
    def __init__(self, parent, content):
        wx.Dialog.__init__(self, parent, title="About %s" % conf.Title,
                           style=wx.CAPTION | wx.CLOSE_BOX)
        html = self.html = wx.html.HtmlWindow(self)
        button_update = wx.Button(self, label="Check for &updates")

        html.SetPage(content)
        html.BackgroundColour = conf.BgColour
        html.Bind(wx.html.EVT_HTML_LINK_CLICKED,
                  lambda e: webbrowser.open(e.GetLinkInfo().Href))
        button_update.Bind(wx.EVT_BUTTON, parent.on_check_update)

        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.Sizer.Add(html, proportion=1, flag=wx.GROW)
        sizer_buttons = self.CreateButtonSizer(wx.OK)
        sizer_buttons.Insert(0, button_update, border=150, flag=wx.RIGHT)
        self.Sizer.Add(sizer_buttons, border=8, flag=wx.ALIGN_CENTER | wx.ALL)
        self.Layout()
        self.Size = (self.Size[0], html.VirtualSize[1] + 60)
        self.CenterOnParent()



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
