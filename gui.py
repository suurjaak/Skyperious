#-*- coding: utf-8 -*-
"""
GUI for Skyperious, contains most application and user interface logic.

@author      Erki Suurjaak
@created     26.11.2011
@modified    30.04.2012
"""
import BeautifulSoup
import collections
import copy
import cStringIO
import ctypes
import datetime
import locale
import htmlentitydefs
import os
import re
import shutil
import sys
import textwrap
import threading
import time
import traceback
import unicodedata
import urllib
import webbrowser
import wx
import wx.gizmos
import wx.grid
import wx.lib
import wx.lib.agw.fmresources
import wx.lib.agw.genericmessagedialog
import wx.lib.agw.gradientbutton
import wx.lib.agw.labelbook
import wx.lib.agw.shapedbutton
import wx.lib.agw.ultimatelistctrl
import wx.lib.buttons
import wx.lib.inspection
import wx.lib.newevent
import wx.lib.wordwrap
import wx.py
import wx.stc

import conf
import controls
import export
import images
import main
import os_handler
import skypedata
import util
import wordcloud
import workers
import wx_accel


"""Custom application event for adding to log window."""
LogEvent,    EVT_LOG =    wx.lib.newevent.NewEvent()
"""Custom application event for worker results."""
WorkerEvent, EVT_WORKER = wx.lib.newevent.NewEvent()
"""Custom application event for setting main window status."""
StatusEvent, EVT_STATUS = wx.lib.newevent.NewEvent()


class MainWindow(wx_accel.AutoAcceleratorFrame):
    """Application main window."""

    def __init__(self):
        wx_accel.AutoAcceleratorFrame.__init__(
            self, parent=None, title=conf.Title, size=conf.WindowSize
        )

        self.db_filenames = {} # added DBs {filename: {size, last_modified}, }
        self.dbs = {}          # Open databases {filename: SkypeDatabase, }
        self.db_pages = {}     # {DatabasePage: SkypeDatabase, }
        self.merger_pages = {} # {MergerPage: (SkypeDatabase, SkypeDatabase), }
        self.page_merge_latest = None # Last opened merger page
        self.page_db_latest = None    # Last opened database page
        # List of Notebook pages user has visited, used for choosing page to
        # show when closing one.
        self.pages_visited = []
        self.Bind(EVT_LOG,    self.on_log_message)
        self.Bind(EVT_STATUS, self.on_set_status)

        conf.load()
        icons = images.get_appicons()
        self.SetIcons(icons)

        panel = self.panel_main = wx.Panel(self)
        sizer = panel.Sizer = wx.BoxSizer(wx.VERTICAL)

        self.frame_console = wx.py.shell.ShellFrame(parent=self,
            title="%s Console" % conf.Title, size=conf.ConsoleSize
        )
        self.frame_console.SetIcons(icons)
        self.frame_console.Bind(
            wx.EVT_CLOSE, lambda evt: self.frame_console.Hide()
        )
        self.frame_console_shown = False # Init flag
        console = self.console = self.frame_console.shell

        notebook = self.notebook = wx.Notebook(
            parent=panel, style=wx.NB_TOP | wx.NB_MULTILINE
        )

        self.create_page_databases(notebook)
        self.create_page_log(notebook)

        sizer.Add(
            notebook, proportion=1, flag=wx.GROW | wx.RIGHT | wx.BOTTOM
        )

        self.create_menu()
        self.CreateStatusBar()

        self.dialog_selectfolder = wx.DirDialog(
            parent=self,
            message="Choose a directory where to search for Skype databases",
            defaultPath=os.getcwd(),
            style=wx.DD_DIR_MUST_EXIST | wx.RESIZE_BORDER
        )
        self.widget_inspector = wx.lib.inspection.InspectionTool()

        # Memory file system for feeding avatar images to HtmlWindow
        self.memoryfs = {"files": {}, "handler": wx.MemoryFSHandler()}
        wx.FileSystem_AddHandler(self.memoryfs["handler"])

        self.Bind(wx.EVT_CLOSE, self.on_exit)
        self.Bind(wx.EVT_SIZE, self.on_size)
        notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_change_page)
        self.Center(wx.HORIZONTAL)
        self.Position.top = 50
        self.list_db.SetFocus()
        self.Show(True)


    def on_change_page(self, event):
        """
        Handler for changing a page in the main Notebook, remembers the visit.
        """
        p = self.notebook.GetPage(self.notebook.Selection)
        if not self.pages_visited or self.pages_visited[-1] != p:
            self.pages_visited.append(p)
        event.Skip() # Pass event along to next handler


    def on_size(self, event):
        wx.CallAfter(self.reposition_ui)
        event.Skip()


    def reposition_ui(self):
        """Called after resize and after creation, to finalize UI."""
        nb_size = self.notebook.ClientRect[2:]
        # Multiline notebooks tend to have problems after adding-removing
        # pages, need to force wx to redraw it fully: jiggle size by 1 pixel.
        self.notebook.Size = nb_size[0], nb_size[1]-1
        self.notebook.Size = nb_size[0], nb_size[1]
        self.notebook.Refresh()


    def create_page_databases(self, notebook):
        """
        Creates a page where databases are listed, and can be selected for
        merging.
        """
        page = self.page_databases = wx.Panel(notebook)
        notebook.AddPage(page, "Databases")
        sizer = page.Sizer = wx.BoxSizer(wx.VERTICAL)

        sizer_left = wx.BoxSizer(wx.VERTICAL)
        label_list = wx.StaticText(parent=page, label="Data&base list:")


        #dblist = self.list_db = wx.ListView(
        dblist = self.list_db = controls.SortableListView(
            parent=page, style=wx.LC_REPORT
        )
        sizer_left.Add(dblist, proportion=1, flag=wx.GROW)

        class FileDrop(wx.FileDropTarget):
            """A simple file drag-and-drop handler for database list."""
            def __init__(self, window):
                wx.FileDropTarget.__init__(self)
                self.window = window

            def OnDropFiles(self, x, y, filenames):
                for filename in filenames:
                    self.window.update_database_list(filename)

        dblist.SetColumnCount(3)
        dblist.InsertColumn(1, "Filename")
        dblist.InsertColumn(2, "Size")
        dblist.InsertColumn(3, "Date modified")
        dblist.Bind(wx.EVT_LIST_ITEM_SELECTED,   self.on_select_dblist)
        dblist.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.on_select_dblist)
        dblist.Bind(wx.EVT_LIST_ITEM_ACTIVATED,  self.on_open_from_dblist)
        dblist.Bind(wx.EVT_LIST_COL_CLICK,       self.on_sort_dblist)
        dblist.DropTarget = FileDrop(self)

        sizer_buttons = wx.BoxSizer(wx.VERTICAL)
        button_open = self.button_open = wx.Button(
            parent=page, label="&Open selected", size=(150, -1)
        )
        button_open.SetToolTipString("Opens first selected database.")
        button_open.Bind(wx.EVT_BUTTON, self.on_open_from_dblist)

        button_compare = self.button_compare = wx.Button(
            parent=page, label="Compare &two databases", size=(150, -1)
        )
        button_compare.SetToolTipString(
            "Opens the two selected databases and compares their content."
        )
        button_compare.Bind(wx.EVT_BUTTON, self.on_compare_databases)
        button_compare.Enabled = False
        button_open.Enabled = False
        button_detect = self.button_detect = wx.Button(
            parent=page, label="Detect databases", size=(150, -1)
        )
        button_detect.Bind(wx.EVT_BUTTON, self.on_detect_databases)
        button_detect.SetToolTipString(
            "Tries to auto-detect Skype databases from user folders."
        )
        button_find = self.button_find = wx.Button(
            parent=page, label="&Search folder", size=(150, -1)
        )
        button_find.SetToolTipString(
            "Selects a folder where to search for Skype databases (*.db)."
        )
        button_find.Bind(wx.EVT_BUTTON, self.on_add_from_folder)
        button_remove = self.button_remove = wx.Button(
            parent=page, label="Remove selected", size=(150, -1)
        )
        button_remove.SetToolTipString(
            "Removes the selected items from the database list."
        )
        button_remove.Bind(wx.EVT_BUTTON, self.on_remove_database)
        button_remove.Enabled = False
        button_copy = self.button_copy = wx.Button(
            parent=page, label="Save &a copy..", size=(150, -1)
        )
        button_copy.SetToolTipString(
            "Saves a copy of the selected database under a chosen name."
        )
        button_copy.Bind(wx.EVT_BUTTON, self.on_copy_database)
        button_copy.Enabled = False
        button_clear = self.button_clear = wx.Button(
            parent=page, label="Clear list", size=(150, -1)
        )
        button_clear.SetToolTipString("Empties the database list.")
        button_clear.Bind(wx.EVT_BUTTON, self.on_clear_databases)
        button_clear.Enabled = False
        button_exit = self.button_find = wx.Button(
            parent=page, label="Exit", size=(150, -1)
        )
        button_exit.SetToolTipString("Exits the application.")
        button_exit.Bind(wx.EVT_BUTTON, self.on_exit)
        sizer_buttons.Add(
            button_open, border=5, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM
        )
        sizer_buttons.Add(button_compare, border=5, flag=wx.ALL)
        sizer_buttons.AddStretchSpacer()
        sizer_buttons.Add(button_detect, border=5, flag=wx.ALL)
        sizer_buttons.Add(button_find, border=5, flag=wx.ALL)
        sizer_buttons.Add(button_copy, border=5, flag=wx.ALL)
        sizer_buttons.Add(button_remove, border=5, flag=wx.ALL)
        sizer_buttons.Add(button_clear, border=5, flag=wx.ALL)
        sizer_buttons.AddSpacer(15)
        sizer_buttons.Add(
            button_exit, border=5, flag=wx.wx.LEFT | wx.RIGHT | wx.TOP
        )

        sizer_sides = wx.BoxSizer(wx.HORIZONTAL)
        sizer_sides.Add(sizer_left, proportion=1, flag=wx.GROW)
        sizer_sides.Add(sizer_buttons, flag=wx.GROW)

        infotext = self.infotext = wx.StaticText(
            parent=page,
            label=conf.InfoText,
            style=wx.ALIGN_CENTER
        )
        sizer.Add(label_list, border=5, flag=wx.TOP | wx.LEFT)
        sizer.Add(sizer_sides,
            border=5, proportion=1, flag=wx.LEFT | wx.RIGHT | wx.GROW
        )
        sizer.Add(
            infotext, border=5, flag=wx.ALL | wx.GROW | wx.ALIGN_CENTER
        )

        for filename in conf.DBFiles:
            self.update_database_list(filename)


    def create_page_log(self, notebook):
        """Creates a page with log box."""
        page = self.page_log = wx.Panel(notebook)
        notebook.AddPage(page, "Log")
        sizer = page.Sizer = wx.BoxSizer(wx.VERTICAL)

        button_clear = self.button_clear_log = wx.Button(
            parent=page, label="Clear log", size=(100, -1)
        )
        button_clear.Bind(wx.EVT_BUTTON, lambda event: self.log.Clear())
        edit_log = self.log = wx.TextCtrl(page, -1, style=wx.TE_MULTILINE)
        edit_log.SetEditable(False)
        # Read-only controls tend to be made grey by default
        edit_log.BackgroundColour = "white"

        sizer.Add(
            button_clear, border=5, flag=wx.ALIGN_RIGHT | wx.TOP | wx.RIGHT
        )
        sizer.Add(edit_log, border=5, proportion=1, flag=wx.GROW | wx.ALL)


    def create_menu(self):
        """Creates the program menu."""
        menu = wx.MenuBar()

        menu_file = wx.Menu()
        self.SetMenuBar(menu)

        menu.Append(menu_file, "&File")
        menu_open_database = self.menu_open_database = menu_file.Append(
            id=wx.NewId(), text="&Open database...\tCtrl-O",
            help="Chooses a Skype database file to open."
        )
        self.Bind(wx.EVT_MENU, self.on_menu_open_database, menu_open_database)
        menu_recent = self.menu_recent = wx.Menu()
        menu_file.AppendMenu(id=wx.NewId(), text="&Recent databases",
            submenu=menu_recent, help="Recently opened databases."
        )
        menu_file.AppendSeparator()
        menu_launch_skype = self.menu_launch_skype = menu_file.Append(
            id=wx.NewId(), text="&Launch Skype",
            help="Launches Skype if possible."
        )
        self.Bind(wx.EVT_MENU, self.on_launch_skype, menu_launch_skype)
        menu_shutdown_skype = self.on_launch_skype = menu_file.Append(
            id=wx.NewId(), text="&Shut down Skype",
            help="Shuts down Skype if running."
        )
        self.Bind(wx.EVT_MENU, self.on_shutdown_skype, menu_shutdown_skype)
        menu_file.AppendSeparator()
        menu_console = self.menu_console = menu_file.Append(id=wx.NewId(),
            text="Show Python &console\tCtrl-W", help="Shows/hides the console window"
        )
        self.Bind(wx.EVT_MENU, self.on_showhide_console, menu_console)
        menu_inspect = self.menu_inspect = menu_file.Append(id=wx.NewId(),
            text="Show &widget inspector",
            help="Shows/hides the widget inspector"
        )
        self.Bind(wx.EVT_MENU, self.on_open_widget_inspector, menu_inspect)

        self.file_history = wx.FileHistory(conf.MaxRecentFiles)
        self.file_history.UseMenu(menu_recent)
        # Reverse filelist, as FileHistory works like a stack
        map(self.file_history.AddFileToHistory, conf.RecentFiles[::-1])
        wx.EVT_MENU_RANGE(self, wx.ID_FILE1, wx.ID_FILE9, self.on_recent_file)
        menu_file.AppendSeparator()
        m_exit = menu_file.Append(-1, "E&xit\tAlt-X", "Exit")
        self.Bind(wx.EVT_MENU, self.on_exit, m_exit)


    def detect_databases(self):
        """Fills the databases list with autodetected Skype databases."""
        main.logstatus("Searching local computer for Skype databases..")
        count = 0
        for filename in skypedata.detect_databases():
            if self.update_database_list(filename):
                main.log("Detected Skype database %s." % filename)
                count += 1
        main.logstatus("Detected %d%s Skype database%s.",
            count,
            " additional" if not (count) else "",
            "" if count == 1 else "s"
        )
        self.button_detect.Enabled = True


    def update_database_list(self, filename=""):
        """
        Inserts the database into the list, if not there already, and
        highlights opened databases in the list.

        @param   filename  possibly new filename, if any
        @return            True if was file was new, False otherwise
        """
        result = False
        # Insert into database lists, if not already there
        if filename:
            if filename not in conf.DBFiles:
                conf.DBFiles.append(filename)
                conf.save()
            if filename not in self.db_filenames:
                data = {"name": filename, "size": None, "last_modified": None}
                if os.path.exists(filename):
                    data["size"] = os.path.getsize(filename)
                    data["last_modified"] = datetime.datetime.fromtimestamp(
                        os.path.getmtime(filename)
                    )
                self.list_db.InsertStringItem(
                    self.list_db.GetItemCount(), filename
                )
                self.list_db.SetItemData(
                    self.list_db.GetItemCount() - 1, id(filename)
                )
                self.list_db.itemDataMap[id(filename)] = \
                    [filename, data["size"], data["last_modified"]]
                if data["last_modified"] is not None:
                    self.list_db.SetStringItem(self.list_db.GetItemCount() - 1,
                        1, util.format_bytes(data["size"])
                    )
                if data["last_modified"] is not None:
                    self.list_db.SetStringItem(self.list_db.GetItemCount() - 1,
                        2, data["last_modified"].strftime("%Y-%m-%d %H:%M:%S")
                    )
                for i in range(3):
                    self.list_db.SetColumnWidth(i, wx.LIST_AUTOSIZE)
                self.db_filenames[filename] = data
                result = True
        # Highlight filenames currently open
        for i in range(self.list_db.GetItemCount()):
            f = self.list_db.GetItemText(i)
            self.list_db.SetItemBackgroundColour(i,
                conf.ListOpenedBgColour \
                if f in self.dbs \
                else wx.WHITE
            )
            #self.list_db.SetItemTextColour(i,
            #    conf.DBFileOpenedColour \
            #    if f in self.dbs \
            #    else wx.BLACK
            #)
            # Select file as one last selected file if we are in form creation
            if not self.Shown and f == filename \
            and f in conf.LastSelectedFiles:
                self.list_db.Select(i)

        self.button_clear.Enabled = (self.list_db.ItemCount > 0)
        return result


    def on_clear_databases(self, event):
        """Handler for clicking to clear the database list."""
        while self.list_db.ItemCount:
            self.list_db.DeleteItem(0)
        del conf.DBFiles[:]
        del conf.LastSelectedFiles[:]
        self.db_filenames.clear()


    def on_copy_database(self, event):
        """Handler for clicking to save a copy of a database in the list."""
        original = self.list_db.GetItemText(self.list_db.GetFirstSelected())
        if not os.path.exists(original):
            wx.MessageBox(
                "The file \"%s\" does not exist on this computer." % original,
                conf.Title, wx.OK | wx.ICON_INFORMATION
            )
            return

        dialog = wx.FileDialog(parent=self, message="Save a copy..",
            defaultDir=os.getcwd(), defaultFile=os.path.basename(original),
            style=wx.FD_OVERWRITE_PROMPT | wx.FD_SAVE | wx.RESIZE_BORDER
        )
        if wx.ID_OK == dialog.ShowModal():
            newpath = dialog.GetPath()
            success = False
            try:
                shutil.copyfile(original, newpath)
                success = True
            except Exception, e:
                main.log("%s when trying to copy %s to %s.",
                    e, original, newpath
                )
                if os_handler.is_skype_running():
                    response = wx.MessageBox(
                        "Could not save a copy of \"%s\" as \"%s\".\n\n" \
                        "Probably because Skype is running. "
                        "Close Skype and try again?" % (original, newpath),
                        conf.Title, wx.OK | wx.CANCEL | wx.ICON_QUESTION
                    )
                    if wx.OK == response:
                        os_handler.shutdown_skype()
                        success, _ = self.try_until(
                            lambda: shutil.copyfile(original, newpath)
                        )
                        if not success:
                            wx.MessageBox(
                                "Still could not copy \"%s\" to \"%s\"." % (
                                    original, newpath
                                ), conf.Title,
                                wx.OK | wx.ICON_WARNING
                            )
                else:
                    wx.MessageBox(
                        "Failed to copy \"%s\" to \"%s\"." % (original, newpath),
                        conf.Title, wx.OK | wx.ICON_WARNING
                    )
            if success:
                main.logstatus(
                    "Saved a copy of %s as %s.", original, newpath
                )
                self.update_database_list(newpath)


    def on_remove_database(self, event):
        """Handler for clicking to remove an item from the database list."""
        selected, selecteds = self.list_db.GetFirstSelected(), []
        while selected >= 0:
            selecteds.append(selected)
            selected = self.list_db.GetNextSelected(selected)
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
        self.button_copy.Enabled = False
        self.button_remove.Enabled = False
        self.button_clear.Enabled = (self.list_db.ItemCount > 0)


    def on_launch_skype(self, event):
        """
        Handler on clicking to launch Skype, tries to determine Skype path and
        set the application running.
        """
        if os_handler.handler:
            if not os_handler.launch_skype():
                wx.MessageBox(
                    "Did not manage to launch Skype from inside %s, sorry." \
                    % conf.Title,
                    conf.Title, wx.OK | wx.ICON_INFORMATION
                )
        else:
            wx.MessageBox(
                "Launching only works in Windows, sorry.",
                conf.Title, wx.OK | wx.ICON_INFORMATION
            )


    def on_shutdown_skype(self, event):
        """
        Handler on clicking to shut down Skype, posts a message to the running
        Skype application to close itself.
        """
        os_handler.shutdown_skype()


    def on_detect_databases(self, event):
        """
        Handler for clicking to auto-detect Skype databases, starts the
        detection in a background thread.
        """
        self.button_detect.Enabled = False
        threading.Thread(target=self.detect_databases).start()


    def on_compare_databases(self, event):
        """
        Handler for clicking to compare two selected databases in the database
        list, creates the comparison page if not already open, and focuses it.
        """
        filename1 = self.list_db.GetItemText(self.list_db.GetFirstSelected())
        filename2 = self.list_db.GetItemText(
            self.list_db.GetNextSelected(self.list_db.GetFirstSelected())
        )
        db1 = db2 = None
        if filename1:
            if filename1 == filename2:
                wx.MessageBox(
                    "Left and right side are the same file.",
                    conf.Title, wx.OK | wx.ICON_INFORMATION
                )
            else:
                db1 = self.load_database(filename1)
        if db1 and filename2:
            db2 = self.load_database(filename2)
        page = None
        if db1 and db2:
            ds = set((db1, db2))
            pp = filter(lambda i: set((i.db1, i.db2)) == ds, self.merger_pages)
            page = pp[0] if pp else None
            if not page:
                page = MergerPage(self.notebook, db1, db2,
                    self.get_unique_tab_title("Database comparison")
                )
                page.Bind(wx.EVT_CLOSE, self.on_close_page)
                self.merger_pages[page] = (db1, db2)
                self.UpdateAccelerators()
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


    def on_menu_open_database(self, event):
        """
        Handler for open database menu, displays a file dialog and loads the
        chosen database.
        """
        dialog = wx.FileDialog(
            parent=self,
            message="Open",
            defaultDir=os.getcwd(),
            defaultFile="",
            wildcard="Skype database (*.db)|*.db|All files|*.*",
            style=wx.FD_FILE_MUST_EXIST | wx.FD_OPEN | wx.RESIZE_BORDER
        )
        dialog.ShowModal()
        filename = dialog.GetPath()
        if filename:
            self.load_database_page(filename)


    def on_recent_file(self, event):
        """Handler for clicking an entry in Recent Files menu."""
        filename = self.file_history.GetHistoryFile(event.GetId() - wx.ID_FILE1)
        self.load_database_page(filename)


    def on_add_from_folder(self, event):
        """
        Handler for clicking to select folder where to search Skype databases,
        adds found databases to database lists.
        """
        if self.dialog_selectfolder.ShowModal() == wx.ID_OK:
            folder = self.dialog_selectfolder.GetPath()
            main.logstatus("Detecting Skype databases under %s.", folder)
            count = 0
            for filename in skypedata.find_databases(folder):
                if filename not in self.db_filenames:
                    main.log("Detected Skype database %s.", filename)
                    self.update_database_list(filename)
                    count += 1
            main.logstatus("Detected %s under %s.",
                util.plural("new Skype database", count), folder
            )


    def on_showhide_console(self, event):
        """Toggles the console shown/hidden."""
        show = not self.frame_console.IsShown()
        if show:
            if not self.frame_console_shown:
                # First showing of console, set height to a fraction of main
                # form, and position it immediately under the main form, or
                # covering its bottom if no room.
                self.frame_console_shown = True
                size = wx.Size(self.Size.width, self.Size.height / 3)
                self.frame_console.Size = size
                display = wx.GetDisplaySize()
                y = 0
                min_bottom_space = 130 # Leave space for autocomplete dropdown
                if size.height > display.height - self.Size.height \
                - self.Position.y - min_bottom_space:
                    y = display.height - self.Size.height - self.Position.y \
                        - size.height - min_bottom_space
                self.frame_console.Position = (
                    self.Position.x, self.Position.y + self.Size.height + y
                )
            # Scroll to the last line
            self.console.ScrollToLine(self.console.LineCount + 3 - (
                self.console.Size.height / self.console.GetTextExtent(" ")[1]
            ))
        self.frame_console.Show(show)
        self.menu_console.Text = "%s &console\tCtrl-W" % (
            "Hide" if show else "Show"
        )


    def on_open_widget_inspector(self, event):
        """Toggles the widget inspection tool shown/hidden."""
        visible = not (self.widget_inspector.initialized \
                       and isinstance(self.widget_inspector._frame, wx.Frame))
        if visible:
            self.widget_inspector.Init()
            self.widget_inspector.Show(selectObj=self, refreshTree=True)
            self.widget_inspector._frame.Bind(
                wx.EVT_CLOSE,
                lambda e: (
                    e.Skip(),
                    self.menu_inspect.SetText("Show &widget inspector")
                )
            )
        else:
            self.widget_inspector._frame.Close()
        self.menu_inspect.Text = "%s &widget inspector" % (
            "Hide" if visible else "Show"
        )


    def on_recent_file(self, event):
        """ Handler for clicking an entry in Recent Files. """
        filename = self.file_history.GetHistoryFile(event.Id - wx.ID_FILE1)
        self.load_database_page(filename)


    def on_sort_dblist(self, event):
        """Handler for clicking to sort the database list, saves new o"""
        event.Skip()
        wx.CallAfter(self.save_dblist)


    def on_open_from_dblist(self, event):
        """Handler for clicking to open a database from a database list."""
        selected = self.list_db.GetFirstSelected()
        if selected >= 0:
            self.load_database_page(self.list_db.GetItemText(selected))


    def on_select_dblist(self, event):
        """
        Handler when a row is selected in a database list, enables UI buttons.
        """
        count = self.list_db.GetSelectedItemCount()
        self.button_open.Enabled = (count > 0)
        self.button_copy.Enabled = (count == 1)
        self.button_remove.Enabled = (count > 0)
        self.button_compare.Enabled = (count == 2)


    def on_exit(self, event):
        """
        Handler on application exit, asks about unsaved changes, if any.
        """
        do_exit = True
        unsaved_dbs = {} # {SkypeDatabase: filename, }
        for db in self.db_pages.values():
            if db.get_unsaved_grids():
                unsaved_dbs[db] = db.filename
        if unsaved_dbs:
            response = wx.MessageBox(
                "There are unsaved changes in data grids\n(%s). "
                "Save changes before closing?" % (
                    "\n".join(textwrap.wrap(", ".join(unsaved_dbs.values())))
                 ),
                 conf.Title, wx.YES | wx.NO | wx.CANCEL | wx.ICON_QUESTION
            )
            if wx.YES == response:
                for db in unsaved_dbs:
                    db.save_unsaved_grids()
            do_exit = (wx.CANCEL != response)
        if do_exit:
            # Save last selected files in db lists, to reselect them on rerun
            del conf.LastSelectedFiles[:]
            selected = self.list_db.GetFirstSelected()
            while selected >= 0:
                filename = self.list_db.GetItemText(selected)
                conf.LastSelectedFiles.append(filename)
                selected = self.list_db.GetNextSelected(selected)
            conf.save()
            self.Destroy()


    def on_close_page(self, event):
        """
        Handler for closing a page, removes page main notebook and updates
        accelerators.
        """
        page = event.EventObject
        page.Show(False)
        # Remove page from MainWindow data structures
        if isinstance(page, DatabasePage):
            del self.db_pages[page]
            page_dbs = [page.db]
            main.log("Closed database tab for %s." % page.db)
        else:
            del self.merger_pages[page]
            page_dbs = [page.db1, page.db2]
            main.log("Closed comparison tab for %s and %s." % (
                page.db1, page.db2
            ))
        # Close databases, if not used in any other page
        for db in page_dbs:
            if not db.has_consumers():
                del self.dbs[db.filename]
                db.close()
                main.log("Closed database %s." % db)
        # Remove any dangling references
        if self.page_merge_latest == page:
            self.page_merge_latest = None
        if self.page_db_latest == page:
            self.page_db_latest = None
        self.pages_visited = filter(lambda x: x != page, self.pages_visited)
        index_new = 0
        if self.pages_visited:
            for i in range(self.notebook.GetPageCount()):
                if self.notebook.GetPage(i) == self.pages_visited[-1]:
                    index_new = i
                    break
        self.notebook.SetSelection(index_new)
        # Remove page from among notebook pages
        for i in range(self.notebook.PageCount):
            if self.notebook.GetPage(i) == page:
                # Using DeletePage freezes app for some reason
                self.notebook.RemovePage(i)
                break
        self.update_database_list()
        self.SendSizeEvent() # Multiline wx.Notebooks need redrawing
        self.notebook.RemoveChild(page)
        page.Destroy()
        self.UpdateAccelerators() # Remove page accelerators


    def get_unique_tab_title(self, title):
        """
        Returns a title that is unique for the current notebook - if the
        specified title already exists, appends a counter to the end,
        e.g. "Database comparison (1)". Title is shortened from the left
        if longer than allowed.
        """
        unique = title_base = title
        if len(title_base) > conf.MaxTabTitleLength:
            title_base = "..%s" % title_base[-conf.MaxTabTitleLength:]
        all_titles = [self.notebook.GetPageText(i) \
            for i in range(self.notebook.PageCount)
        ]
        i = 1 # Start counter from 1
        while unique in all_titles:
            unique = "%s (%d)" % (title_base, i)
            i += 1
        return unique



    def save_dblist(self):
        """Saves the current database list into configuration file."""
        l = [self.list_db.GetItemText(i) for i in range(self.list_db.ItemCount)]
        conf.DBFiles[:] = l
        conf.save()


    def load_database(self, filename):
        """
        Tries to load the specified database, if not already open, and returns
        it.
        """
        db = self.dbs.get(filename, None)
        if not db:
            db = None
            if os.path.exists(filename):
                try:
                    db = skypedata.SkypeDatabase(filename)
                except:
                    is_accessible = False
                    try:
                        with open(filename, "rb") as f:
                            is_accessible = True
                    except Exception, e:
                        pass
                    if not is_accessible and os_handler.is_skype_running():
                        #wx.GetApp().Yield(True) # Allow UI to refresh
                        response = wx.MessageBox(
                            "Could not open %s.\n\n"
                            "Probably because Skype is running. "
                            "Close Skype and try again?" % filename,
                            conf.Title, wx.OK | wx.CANCEL | wx.ICON_WARNING
                        )
                        if wx.OK == response:
                            os_handler.shutdown_skype()
                            try_result, db = self.try_until(lambda:
                                skypedata.SkypeDatabase(filename, False)
                            )
                            if not try_result:
                                wx.MessageBox(
                                    "Still could not open %s." % filename,
                                    conf.Title, wx.OK | wx.ICON_WARNING
                                )
                    elif not is_accessible:
                        wx.MessageBox(
                            "Could not open %s.\n\n"
                            "Some other process may be using the file." \
                            % filename, conf.Title, wx.OK | wx.ICON_WARNING
                        )
                    else:
                        wx.MessageBox(
                            "Could not open %s.\n\n"
                            "Not a valid SQLITE database?" % filename,
                            conf.Title, wx.OK | wx.ICON_WARNING
                        )
                if db:
                    main.log("Opened %s (%s).", db, util.format_bytes(
                        db.filesize
                    ))
                    main.logstatus("Reading Skype database file %s.", db)
                    self.dbs[filename] = db
                    self.update_database_list(filename)
                    # Add filename to Recent Files menu and conf, if needed
                    if filename not in conf.RecentFiles:
                        conf.RecentFiles.insert(0, filename)
                        self.file_history.AddFileToHistory(filename)
                        del conf.RecentFiles[conf.MaxRecentFiles:]
                        conf.save()
                    self.check_future_dates(db)
            else:
                wx.MessageBox(
                    "Nonexistent file: %s." % filename,
                    conf.Title, wx.OK | wx.ICON_WARNING
                )
        return db


    def try_until(self, func, tries=10, sleep=0.5):
        """
        Tries to execute the specified function a number of times.

        @param    func   callable to execute
        @param    tries  number of times to try (default 10)
        @param    sleep  seconds to sleep after failed attempts (default 0.5)
        @return          (True if success else False, func_result)
        """
        count = 0
        result = False
        func_result = None
        while count < tries:
            count += 1
            try:
                func_result = func()
                result = True
            except Exception, e:
                if count < tries:
                    time.sleep(sleep)
        return result, func_result


    def load_database_page(self, filename):
        """
        Tries to load the specified database, if not already open, create a
        subpage for it, if not already created, and focuses the subpage.
        """
        db = None
        page = None
        if filename in self.dbs:
            db = self.dbs[filename]
        if db and db in self.db_pages.values():
            pp = filter(lambda i: i.db == db, self.db_pages)
            page = pp[0] if pp else None
        if not page:
            if not db:
                db = self.load_database(filename)
            if db:
                main.status("Opening Skype database file %s." % db)
                tab_title = self.get_unique_tab_title(db.filename)
                page = DatabasePage(self.notebook, db, self.memoryfs,tab_title)
                page.Bind(wx.EVT_CLOSE, self.on_close_page)
                self.db_pages[page] = db
                self.UpdateAccelerators()
        if page:
            for i in range(self.notebook.GetPageCount()):
                if self.notebook.GetPage(i) == page:
                    self.notebook.SetSelection(i)


    def on_set_status(self, event):
        """Event handler for adding a message to the log window."""
        self.SetStatusText(event.text)


    def on_log_message(self, event):
        """Event handler for adding a message to the log window."""
        try:
            self.log.AppendText(event.text + "\n")
        except Exception, e:
            print "Exception %s in on_log_message" % e


    def check_future_dates(self, db):
        """
        Checks the database for messages with a future date and asks the user
        about fixing them.
        """
        future_count, max_datetime = db.check_future_dates()
        if future_count:
            delta = datetime.datetime.now() - max_datetime
            dialog = DayHourDialog(parent=self, message=
                "The database has %s with a "
                "future timestamp (last being %s).\nThis can "
                "happen if the computer\"s clock has been set "
                "to a future date when the messages were "
                "received.\n\n"
                "If you want to fix these messages, "
                "enter how many days/hours to move them:" % \
                  (util.plural("message", future_count), max_datetime),
                caption=conf.Title, days=delta.days,
                hours=0
            )
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
                    conf.Title, wx.OK
                )



class DatabasePage(wx.Panel):
    """
    A wx.Notebook page for managing a single database file, has its own
    Notebook with a page for browsing chat history, and a page for
    viewing-changing tables.
    """

    def __init__(self, parent_notebook, db, memoryfs, title):
        wx.Panel.__init__(self, parent=parent_notebook)
        self.parent_notebook = parent_notebook
        self.db = db
        self.db.register_consumer(self)
        self.memoryfs = memoryfs
        self.Label = title
        parent_notebook.InsertPage(1, self, title)
        for i in range(parent_notebook.GetPageCount()):
            if parent_notebook.GetPage(i) == self:
                parent_notebook.SetSelection(i)
        # Multiline wx.Notebooks need redrawing
        self.TopLevelParent.SendSizeEvent()
        #wx.GetApp().Yield(True) # Allow notebook tabs and selection to refresh
        busy = controls.ProgressPanel(self, "Loading \"%s\"." % db.filename)

        self.chat = None  # Currently viewed chat
        self.chats = None # All chats in database
        self.chat_filter = { # Filter for currently shown chat history
            "daterange": None,      # Current date range
            "startdaterange": None, # Initial date range
            "text": "",             # Text in message content
            "participants": None    # Messages from [skype name, ]
        }

        # Create search thread and structures
        self.search_data = {"id": None} # Current search data {"text", "db", }
        self.results_html = "" # Partially assembled HTML for current results
        self.Bind(EVT_WORKER, self.on_searchall_result)
        self.worker_search = workers.SearchThread(self.on_searchall_callback)
        self.searchall_map = {} # {Link ID: search data} for html_searchall

        self.Bind(wx.EVT_CLOSE, self.on_close, self)

        sizer = self.Sizer = wx.BoxSizer(wx.VERTICAL)

        sizer_header = wx.BoxSizer(wx.HORIZONTAL)
        label_title = self.label_title = wx.StaticText(parent=self, label="")
        button_close = self.button_close = wx.Button(
            parent=self, label="&Close tab", size=(100, -1)
        )
        button_close.Enabled = False
        self.Bind(wx.EVT_BUTTON, self.on_close, button_close)
        sizer_header.Add(
            label_title, border=5, flag=wx.ALIGN_CENTER_VERTICAL | wx.TOP
        )
        sizer_header.AddStretchSpacer()
        sizer_header.Add(button_close, flag=wx.ALIGN_RIGHT)

        bookstyle = wx.lib.agw.fmresources.INB_LEFT
        if wx.version().startswith("2.8") and sys.version.startswith("2.6"):
            # In Python 2.6, wx 2.8 the FlatImageBook display is a tad buggy
            bookstyle |= wx.lib.agw.fmresources.INB_FIT_LABELTEXT
        notebook = self.notebook = wx.lib.agw.labelbook.FlatImageBook(
            parent=self, agwStyle=bookstyle,
            style=wx.BORDER_STATIC
        )

        il = wx.ImageList(32, 32)
        idx1 = il.Add(images.IconChats.GetBitmap())
        idx2 = il.Add(images.IconSearch.GetBitmap())
        idx3 = il.Add(images.IconDatabase.GetBitmap())
        idx4 = il.Add(images.IconSQL.GetBitmap())
        notebook.AssignImageList(il)

        self.create_page_chats(notebook)
        self.create_page_search(notebook)
        self.create_page_tables(notebook)
        self.create_page_sql(notebook)

        notebook.SetPageImage(0, idx1)
        notebook.SetPageImage(1, idx2)
        notebook.SetPageImage(2, idx3)
        notebook.SetPageImage(3, idx4)

        sizer.Add(sizer_header,
            border=5, flag=wx.LEFT | wx.RIGHT | wx.TOP | wx.GROW
        )
        sizer.Add(notebook,proportion=1, border=5, flag=wx.GROW | wx.ALL)

        self.dialog_savefile = wx.FileDialog(
            parent=self,
            defaultDir=os.getcwd(),
            defaultFile="",
            style=wx.FD_OVERWRITE_PROMPT | wx.FD_SAVE | wx.RESIZE_BORDER
        )

        self.TopLevelParent.page_db_latest = self
        self.TopLevelParent.console.run(
            "page = self.page_db_latest # Database tab"
        )
        self.TopLevelParent.console.run("db = page.db # Skype database")

        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_change_page)
        # Layout() required, otherwise sizers do not start working
        # automatically as it's late creation
        self.Layout()
        #wx.GetApp().Yield(True) # Allow UI to refresh before loading data
        self.load_data()
        # 2nd Layout() seems also required
        self.Layout()
        busy.Close()


    def create_page_chats(self, notebook):
        """Creates a page for listing and reading chats."""
        page = self.page_chats = wx.Panel(parent=notebook)
        notebook.AddPage(page, "Chats")
        sizer = page.Sizer = wx.BoxSizer(wx.VERTICAL)
        splitter = self.splitter_chats = wx.SplitterWindow(
            parent=page, style=wx.BORDER_NONE
        )
        splitter.SetMinimumPaneSize(50)

        panel1 = wx.Panel(parent=splitter)
        sizer1 = panel1.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_top = wx.BoxSizer(wx.HORIZONTAL)
        sizer_top.Add(
            wx.StaticText(panel1, label="A&ll chat entries in database:"),
            proportion=1, border=5, flag=wx.ALIGN_BOTTOM
        )
        list_chats = self.list_chats = controls.SortableListView(
            parent=panel1, style=wx.LC_REPORT | wx.LC_SINGLE_SEL
        )
        edit_search = self.edit_searchall_chats = wx.TextCtrl(parent=panel1,
            value=conf.HistorySearchDescription, size=(100, -1),
            style=wx.TE_PROCESS_ENTER
        )
        edit_search.SetForegroundColour("gray")
        self.Bind(wx.EVT_TEXT_ENTER, self.on_searchall_chats, edit_search)
        edit_search.Bind(wx.EVT_SET_FOCUS, self.on_focus_searchall)
        edit_search.Bind(wx.EVT_KILL_FOCUS, self.on_focus_searchall)
        button_search = self.button_searchall_chats = wx.Button(
            parent=panel1, label="Search &all", size=(100, -1)
        )
        self.Bind(wx.EVT_BUTTON, self.on_searchall_chats, button_search)
        self.Bind(wx.EVT_BUTTON, self.on_searchall_chats, button_search)
        sizer_top.Add(edit_search, border=5, flag=wx.RIGHT | wx.ALIGN_RIGHT)
        sizer_top.Add(button_search, flag=wx.ALIGN_RIGHT)
        sizer1.Add(sizer_top,
            border=5, flag=wx.RIGHT | wx.LEFT | wx.BOTTOM | wx.GROW
        )
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED,
            self.on_change_list_chats, list_chats
        )
        sizer1.Add(list_chats,
            proportion=1, border=5, flag=wx.GROW | wx.BOTTOM | wx.LEFT
        )

        panel2 = wx.Panel(parent=splitter)
        sizer2 = panel2.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_header = wx.BoxSizer(wx.HORIZONTAL)
        label_chat = self.label_chat = wx.StaticText(
            parent=panel2, label="C&hat:", name="chat_history_label"
        )
        button_stats = self.button_stats = wx.Button(
            parent=panel2, size=(100, -1), label="Toggle &stats"
        )
        button_stats.Enabled = False
        self.Bind(wx.EVT_BUTTON, self.on_toggle_stats, button_stats)
        button_filter = self.button_filter_chat = wx.Button(
            parent=panel2, label="To&ggle filter", size=(100, -1)
        )
        button_filter.Enabled = False
        self.Bind(wx.EVT_BUTTON, self.on_toggle_filter, button_filter)
        button_export = self.button_export_chat = wx.Button(
            parent=panel2, size=(100, -1), label="&Export to file"
        )
        button_export.Enabled = False
        self.Bind(wx.EVT_BUTTON, self.on_export_chat, button_export)
        sizer_header.Add(label_chat,
            proportion=1, border=5, flag=wx.ALIGN_BOTTOM | wx.LEFT
        )
        for b in [button_stats, button_filter, button_export]:
            sizer_header.Add(b, border=5, flag=wx.ALIGN_RIGHT | wx.LEFT)
        sizer2.Add(sizer_header, border=5, flag=wx.GROW | wx.RIGHT | wx.TOP)

        splitter_stc = self.splitter_stc = wx.SplitterWindow(
            parent=panel2, style=wx.BORDER_NONE
        )
        splitter_stc.SetMinimumPaneSize(50)
        panel_stc1 = self.panel_stc1 = wx.Panel(parent=splitter_stc)
        panel_stc2 = self.panel_stc2 = wx.Panel(parent=splitter_stc)
        sizer_stc1 = panel_stc1.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_stc2 = panel_stc2.Sizer = wx.BoxSizer(wx.VERTICAL)
        stc = self.stc_history = ChatContentSTC(
            parent=panel_stc1, style=wx.BORDER_STATIC, name="chat_history"
        )
        html_stats = self.html_stats = wx.html.HtmlWindow(parent=panel_stc1)
        html_stats.Bind(
            wx.html.EVT_HTML_LINK_CLICKED, self.on_click_html_stats
        )
        html_stats.Bind(wx.EVT_SCROLLWIN, self.on_scroll_html_stats)
        html_stats.Bind(wx.EVT_SIZE, self.on_size_html_stats)
        html_stats.Hide()

        sizer_stc1.Add(stc, proportion=1, flag=wx.GROW)
        sizer_stc1.Add(html_stats, proportion=1, flag=wx.GROW)

        label_filter = wx.StaticText(
            parent=panel_stc2, label="Find messages with &text:"
        )
        edit_filter = self.edit_filtertext = wx.TextCtrl(
            parent=panel_stc2, size=(100, -1), style=wx.TE_PROCESS_ENTER
        )
        self.Bind(wx.EVT_TEXT_ENTER, self.on_filter_chat, edit_filter)
        label_range = wx.StaticText(
            parent=panel_stc2, label="Show messages from time period:"
        )
        range_date = self.range_date = controls.RangeSlider(
            parent=panel_stc2, fmt="%Y-%m-%d"
        )
        label_list = wx.StaticText(
            parent=panel_stc2, label="Sho&w messages from:"
        )
        agw_style = wx.LC_REPORT | wx.LC_NO_HEADER | wx.LC_SINGLE_SEL | \
                    wx.lib.agw.ultimatelistctrl.ULC_NO_HIGHLIGHT | \
                    wx.lib.agw.ultimatelistctrl.ULC_HRULES | \
                    wx.lib.agw.ultimatelistctrl.ULC_SHOW_TOOLTIPS
        if hasattr(wx.lib.agw.ultimatelistctrl, "ULC_USER_ROW_HEIGHT"):
            agw_style |= wx.lib.agw.ultimatelistctrl.ULC_USER_ROW_HEIGHT
        list_participants = self.list_participants = \
            wx.lib.agw.ultimatelistctrl.UltimateListCtrl(
                parent=panel_stc2, agwStyle=agw_style
            )
        self.Bind(wx.EVT_LIST_ITEM_SELECTED,
            self.on_select_participant, list_participants
        )
        list_participants.EnableSelectionGradient()
        if hasattr(list_participants, "SetUserLineHeight"):
            list_participants.SetUserLineHeight(conf.AvatarImageSize[1] + 2)
        sizer_filter_buttons = wx.BoxSizer(wx.HORIZONTAL)
        button_filter_apply = self.button_chat_applyfilter = wx.Button(
            parent=panel_stc2, label="A&pply filter"
        )
        button_filter_export = self.button_chat_exportfilter = wx.Button(
            parent=panel_stc2, label="Expo&rt filter"
        )
        button_filter_reset = self.button_chat_unfilter = wx.Button(
            parent=panel_stc2, label="&Restore initial"
        )
        self.Bind(wx.EVT_BUTTON, self.on_filter_chat, button_filter_apply)
        self.Bind(
            wx.EVT_BUTTON, self.on_filterexport_chat, button_filter_export
        )
        self.Bind(wx.EVT_BUTTON, self.on_filterreset_chat, button_filter_reset)
        button_filter_apply.SetToolTipString(
            "Filters the conversation by the specified text, "
            "date range and participants."
        )
        button_filter_export.SetToolTipString(
            "Exports filtered messages straight to file, "
            "without showing them (showing thousands of messages gets slow)."
        )
        button_filter_reset.SetToolTipString(
            "Restores filter controls to initial values."
        )
        sizer_filter_buttons.Add(button_filter_apply)
        sizer_filter_buttons.AddSpacer(5)
        sizer_filter_buttons.Add(button_filter_export)
        sizer_filter_buttons.AddSpacer(5)
        sizer_filter_buttons.Add(button_filter_reset)
        sizer_filter_buttons.AddSpacer(5)
        sizer_stc2.Add(label_filter, border=5, flag=wx.LEFT)
        sizer_stc2.Add(edit_filter, border=5, flag=wx.GROW | wx.LEFT)
        sizer_stc2.AddSpacer(5)
        sizer_stc2.Add(label_range, border=5, flag=wx.LEFT)
        sizer_stc2.Add(range_date, border=5, flag=wx.GROW | wx.LEFT)
        sizer_stc2.AddSpacer(5)
        sizer_stc2.Add(label_list, border=5, flag=wx.LEFT)
        sizer_stc2.Add(list_participants,
            proportion=1, border=5, flag=wx.GROW | wx.LEFT
        )
        sizer_stc2.AddSpacer(5)
        sizer_stc2.Add(sizer_filter_buttons,
            proportion=0, border=5, flag=wx.GROW | wx.LEFT | wx.RIGHT
        )

        splitter_stc.SplitVertically(panel_stc1, panel_stc2, sashPosition=0)
        splitter_stc.Unsplit(panel_stc2) # Hide filter panel
        sizer2.Add(
            splitter_stc, proportion=1, border=5, flag=wx.GROW | wx.ALL
        )

        sizer.AddSpacer(10)
        sizer.Add(splitter, proportion=1, flag=wx.GROW)
        splitter.SplitHorizontally(
            panel1, panel2, sashPosition=self.Size[1] / 3
        )


    def create_page_search(self, notebook):
        """Creates a page for searching chats."""
        page = self.page_search = wx.Panel(parent=notebook)
        notebook.AddPage(page, "Search")
        sizer = page.Sizer = wx.BoxSizer(wx.VERTICAL)

        sizer_search = wx.BoxSizer(wx.HORIZONTAL)
        search = self.edit_searchall = wx.TextCtrl(parent=page,
            value=conf.HistorySearchDescription, style=wx.TE_PROCESS_ENTER,
            size=(200, -1)
        )
        search.SetForegroundColour("gray")
        search.Bind(wx.EVT_TEXT_ENTER, self.on_searchall)
        search.Bind(wx.EVT_SET_FOCUS, self.on_focus_searchall)
        search.Bind(wx.EVT_KILL_FOCUS, self.on_focus_searchall)
        button_search = self.button_searchall = wx.Button(
            parent=page, label="&Search", size=(100, -1)
        )
        self.Bind(wx.EVT_BUTTON, self.on_searchall, button_search)
        button_stop = self.button_searchall_stop = wx.Button(
            parent=page, label="Sto&p", size=(100, -1)
        )
        self.Bind(wx.EVT_BUTTON, self.on_searchall_stop, button_stop)
        cb_messages = self.cb_search_messages = wx.CheckBox(
            parent=page, label="Search message &body"
        )
        cb_chats = self.cb_search_chats = wx.CheckBox(
            parent=page, label="Search chat &title and participants"
        )
        cb_contacts = self.cb_search_contacts = wx.CheckBox(
            parent=page, label="Search contact &information"
        )
        cb_messages.Value = cb_chats.Value = cb_contacts.Value = True
        sizer_search.Add(search)
        sizer_search.Add(button_search, border=5, flag=wx.LEFT)
        sizer_search.Add(button_stop, border=5, flag=wx.LEFT)
        sizer_search.Add(cb_messages,
            border=15, flag=wx.LEFT | wx.ALIGN_CENTER_VERTICAL
        )
        sizer_search.Add(cb_chats,
            border=5, flag=wx.LEFT | wx.ALIGN_CENTER_VERTICAL
        )
        sizer_search.Add(cb_contacts,
            border=5, flag=wx.LEFT | wx.ALIGN_CENTER_VERTICAL
        )

        label_help = wx.StaticText(parent=page, label=\
            "Searches raw message body, so for example \"<sms\" finds SMS "
            "messages, \"<file\" finds transfers and \"<quote\" finds quoted "
            "messages."
        )
        label_help.ForegroundColour = "grey"
        html = self.html_searchall = wx.html.HtmlWindow(parent=page)
        html.Bind(
            wx.html.EVT_HTML_LINK_CLICKED, self.on_click_searchall_result
        )
        html.Font.PixelSize = (0, 8)

        sizer.Add(sizer_search, border=5, flag=wx.ALL)
        sizer.Add(label_help, border=5, flag=wx.LEFT | wx.TOP)
        sizer.Add(html, border=5, proportion=1, flag=wx.GROW | wx.ALL)


    def create_page_tables(self, notebook):
        """Creates a page for listing and browsing tables."""
        page = self.page_tables = wx.Panel(parent=notebook)
        notebook.AddPage(page, "Data tables")
        sizer = page.Sizer = wx.BoxSizer(wx.HORIZONTAL)
        splitter = self.splitter_tables = wx.SplitterWindow(
            parent=page, style=wx.BORDER_NONE
        )
        splitter.SetMinimumPaneSize(50)

        panel1 = wx.Panel(parent=splitter)
        sizer1 = panel1.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer1.Add(wx.StaticText(parent=panel1,
            label="&Tables:"), border=5, flag=wx.LEFT | wx.TOP | wx.BOTTOM
        )
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
        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.on_change_list_tables, tree)

        sizer1.Add(tree, proportion=1,
            border=5, flag=wx.GROW | wx.LEFT | wx.TOP | wx.BOTTOM
        )

        panel2 = wx.Panel(parent=splitter)
        sizer2 = panel2.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_tb = wx.BoxSizer(wx.HORIZONTAL)
        tb = self.tb_grid = wx.ToolBar(
            parent=panel2, style=wx.TB_FLAT | wx.TB_NODIVIDER
        )
        bmp_tb = images.ToolbarInsert.GetBitmap()
        tb.SetToolBitmapSize(bmp_tb.Size)
        tb.AddLabelTool(id=wx.ID_ADD, label="Insert new row.",
            bitmap=bmp_tb, shortHelp="Add new row."
        )
        tb.AddLabelTool(id=wx.ID_DELETE, label="Delete current row.",
            bitmap=images.ToolbarDelete.GetBitmap(), shortHelp="Delete row."
        )
        tb.AddSeparator()
        tb.AddLabelTool(id=wx.ID_SAVE, label="Commit",
            bitmap=images.ToolbarCommit.GetBitmap(),
            shortHelp="Commit changes to database."
        )
        tb.AddLabelTool(id=wx.ID_UNDO, label="Rollback",
            bitmap=images.ToolbarRollback.GetBitmap(),
            shortHelp="Rollback changes and restore original values."
        )
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
        button_reset = self.button_reset_grid_table = wx.Button(
            parent=panel2, label="&Reset filter/sort", size=(100, -1)
        )
        button_reset.SetToolTipString(
            "Resets all applied sorting and filtering."
        )
        button_reset.Bind(wx.EVT_BUTTON, self.on_button_reset_grid)
        button_export = self.button_export_table = wx.Button(
            parent=panel2, label="&Export to file", size=(100, -1)
        )
        button_export.SetToolTipString("Export rows to a file.")
        button_export.Bind(wx.EVT_BUTTON, self.on_button_export_grid)
        button_export.Enabled = False
        sizer_tb.Add(label_table, flag=wx.ALIGN_CENTER_VERTICAL)
        sizer_tb.AddStretchSpacer()
        sizer_tb.Add(button_reset, border=5, flag=wx.ALIGN_CENTER_VERTICAL \
            | wx.RIGHT | wx.BOTTOM | wx.ALIGN_RIGHT
        )
        sizer_tb.Add(button_export, border=5, flag=wx.ALIGN_CENTER_VERTICAL \
            | wx.RIGHT | wx.BOTTOM | wx.ALIGN_RIGHT
        )
        sizer_tb.Add(tb, flag=wx.ALIGN_RIGHT)
        grid = self.grid_table = wx.grid.Grid(parent=panel2)
        grid.SetToolTipString(
            "Double click on column header to sort, right click to filter."
        )
        grid.Bind(wx.grid.EVT_GRID_LABEL_LEFT_DCLICK,
            self.on_sort_grid_column
        )
        grid.GridWindow.Bind(wx.EVT_MOTION, self.on_mouse_over_grid)
        grid.Bind(wx.grid.EVT_GRID_LABEL_RIGHT_CLICK,
            self.on_filter_grid_column
        )
        grid.Bind(wx.grid.EVT_GRID_CELL_CHANGE,
            self.on_change_table
        )
        label_help = wx.StaticText(panel2, wx.NewId(),
            "Double-click on column header to sort, right click to filter."
        )
        label_help.ForegroundColour = "grey"
        sizer2.Add(sizer_tb, border=5, flag=wx.GROW | wx.LEFT)
        sizer2.Add(grid,
            border=5, proportion=2, flag=wx.GROW | wx.LEFT | wx.RIGHT
        )
        sizer2.Add(label_help, border=5, flag=wx.LEFT | wx.TOP)

        sizer.Add(splitter, proportion=1, flag=wx.GROW)
        splitter.SplitVertically(panel1, panel2, 270)


    def create_page_sql(self, notebook):
        """Creates a page for executing arbitrary SQL."""
        page = self.page_sql = wx.Panel(parent=notebook)
        notebook.AddPage(page, "SQL window")
        sizer = page.Sizer = wx.BoxSizer(wx.VERTICAL)
        splitter = self.splitter_sql = wx.SplitterWindow(
            parent=page, style=wx.BORDER_NONE
        )
        splitter.SetMinimumPaneSize(50)

        panel1 = wx.Panel(parent=splitter)
        sizer1 = panel1.Sizer = wx.BoxSizer(wx.VERTICAL)
        label_stc = wx.StaticText(parent=panel1, label="&SQL:")
        stc = self.stc_sql = controls.SQLiteTextCtrl(parent=panel1,
            style=wx.BORDER_STATIC | wx.TE_PROCESS_TAB | wx.TE_PROCESS_ENTER
        )
        stc.Bind(wx.EVT_KEY_DOWN, self.on_keydown_sql)
        stc.SetToolTipString(
            "Ctrl-Space shows autocompletion list. Alt-Enter runs the query "
            "contained in currently selected text or on the current line."
        )
        sizer1.Add(label_stc, border=5, flag=wx.ALL)
        sizer1.Add(stc, border=5, proportion=1, flag=wx.GROW | wx.LEFT)

        panel2 = wx.Panel(parent=splitter)
        sizer2 = panel2.Sizer = wx.BoxSizer(wx.VERTICAL)
        label_help = wx.StaticText(panel2, label=stc.GetToolTip().GetTip())
        label_help.ForegroundColour = "grey"
        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        button_sql = self.button_sql = wx.Button(panel2, label="Execute &SQL")
        self.Bind(wx.EVT_BUTTON, self.on_button_sql, button_sql)
        button_reset = self.button_reset_grid_sql = wx.Button(
            parent=panel2, label="&Reset filter/sort", size=(100, -1)
        )
        button_reset.SetToolTipString(
            "Resets all applied sorting and filtering."
        )
        button_reset.Bind(wx.EVT_BUTTON, self.on_button_reset_grid)
        button_export = self.button_export_sql = wx.Button(
            parent=panel2, label="&Export to file"
        )
        button_export.SetToolTipString("Export result to a file.")
        button_export.Bind(wx.EVT_BUTTON, self.on_button_export_grid)
        button_export.Enabled = False
        sizer_buttons.Add(button_sql, flag=wx.ALIGN_LEFT)
        sizer_buttons.AddStretchSpacer()
        sizer_buttons.Add(
            button_reset, border=5, flag=wx.ALIGN_RIGHT | wx.RIGHT
        )
        sizer_buttons.Add(button_export, flag=wx.ALIGN_RIGHT)
        grid = self.grid_sql = wx.grid.Grid(parent=panel2)
        #grid.EnableEditing(False)
        grid.Bind(wx.grid.EVT_GRID_LABEL_LEFT_DCLICK,
            self.on_sort_grid_column
        )
        grid.Bind(wx.grid.EVT_GRID_LABEL_RIGHT_CLICK,
            self.on_filter_grid_column
        )
        grid.Bind(wx.EVT_SCROLLWIN, self.on_scroll_grid_sql)
        grid.Bind(wx.EVT_SCROLL_THUMBRELEASE, self.on_scroll_grid_sql)
        grid.Bind(wx.EVT_SCROLL_CHANGED, self.on_scroll_grid_sql)
        grid.Bind(wx.EVT_KEY_DOWN, self.on_scroll_grid_sql)
        grid.GridWindow.Bind(wx.EVT_MOTION, self.on_mouse_over_grid)
        label_help_grid = wx.StaticText(panel2, wx.NewId(),
            "Double-click on column header to sort, right click to filter."
        )
        label_help_grid.ForegroundColour = "grey"

        sizer2.Add(label_help, border=5, flag=wx.GROW | wx.LEFT | wx.BOTTOM)
        sizer2.Add(sizer_buttons, border=5, flag=wx.GROW | wx.ALL)
        sizer2.Add(
            grid, border=5, proportion=2, flag=wx.GROW | wx.LEFT | wx.RIGHT
        )
        sizer2.Add(label_help_grid, border=5, flag=wx.GROW | wx.LEFT | wx.TOP)

        sizer.Add(splitter, proportion=1, flag=wx.GROW)
        splitter.SplitHorizontally(
            panel1, panel2, sashPosition=self.Size[1] / 3
        )


    def on_change_page(self, event):
        """
        Handler on changing notebook page, saves/restores the search
        HtmlWindow scroll position (HtmlWindow loses it on page change).
        """
        h = self.html_searchall
        is_search_page = False
        # Inconsistencies between wx 2.8 and 2.9.
        if hasattr(self.notebook, "GetPage"):
            p = self.notebook.GetPage(self.notebook.Selection)
            is_search_page = (p == self.page_search)
        elif hasattr(self.notebook, "_pages"):
            t = self.notebook._pages.GetPageText(self.notebook.GetSelection())
            is_search_page = (t == "Search")
        if is_search_page and hasattr(h, "_last_scroll_pos"):
            h.Scroll(*h._last_scroll_pos)
        else:
            h._last_scroll_pos = [
                h.GetScrollPos(wx.HORIZONTAL), h.GetScrollPos(wx.VERTICAL)
            ]
        event.Skip() # Pass event along to next handler


    def on_export_chat(self, event):
        """
        Handler for clicking to export a chat, displays a save file dialog and
        saves the current messages to file.
        """
        default = "Skype %s" % self.chat["title_long_lc"]
        self.dialog_savefile.Filename = util.safe_filename(default)
        self.dialog_savefile.Message = "Save chat"
        self.dialog_savefile.Wildcard = \
            "HTML document (*.html)|*.html|" \
            "Text document (*.txt)|*.txt|" \
            "CSV spreadsheet (*.csv)|*.csv"
        if wx.ID_OK == self.dialog_savefile.ShowModal():
            filename = self.dialog_savefile.GetPath()
            #wx.GetApp().Yield(True) # Allow dialog to close, status to refresh
            busy = controls.ProgressPanel(
                self, "Exporting \"%s\"." % self.chat["title"]
            )
            main.logstatus("Exporting to %s.", filename)
            export_result = export.export_chat(
                self.chat, self.stc_history.GetMessages(), filename, self.db
            )
            busy.Close()
            if export_result:
                main.logstatus("Exported %s.", filename)
                os_handler.start_file(filename)
            else:
                wx.MessageBox(
                    "Cannot access \"%s\"." % filename,
                    conf.Title, wx.OK | wx.ICON_WARNING
                )
                main.logstatus("Cannot access %s.", filename)


    def on_filterexport_chat(self, event):
        """
        Handler for clicking to export a chat filtering straight to file,
        displays a save file dialog and saves all filtered messages to file.
        """
        default = "Skype %s" % self.chat["title_long_lc"]
        self.dialog_savefile.Filename = util.safe_filename(default)
        self.dialog_savefile.Message = "Save chat"
        self.dialog_savefile.Wildcard = \
            "HTML document (*.html)|*.html|" \
            "Text document (*.txt)|*.txt|" \
            "CSV spreadsheet (*.csv)|*.csv"
        if wx.ID_OK == self.dialog_savefile.ShowModal():
            filename = self.dialog_savefile.GetPath()
            #wx.GetApp().Yield(True) # Allow dialog to close, status to refresh
            busy = controls.ProgressPanel(
                self, "Filtering and exporting \"%s\"." % self.chat["title"]
            )

            filter_new = self.build_filter()
            filter_backup = self.stc_history.GetFilter()
            self.stc_history.SetFilter(filter_new)
            self.stc_history.RetrieveMessagesIfNeeded()
            messages_all = self.stc_history.GetRetrievedMessages()
            messages = [m for m in messages_all \
                if not self.stc_history.IsMessageFilteredOut(m)
            ]
            self.stc_history.SetFilter(filter_backup)
            if messages:
                main.logstatus("Filtering and exporting to %s.", filename)
                export_result = export.export_chat(
                    self.chat, messages, filename, self.db
                )
                busy.Close()
                if export_result:
                    main.logstatus("Exported %s.", filename)
                    os_handler.start_file(filename)
                else:
                    wx.MessageBox(
                        "Cannot access \"%s\"." % filename,
                        conf.Title, wx.OK | wx.ICON_WARNING
                    )
                    main.logstatus("Cannot access %s.", filename)
            else:
                wx.MessageBox(
                    "Current filter leaves no data to export.",
                    conf.Title, wx.OK | wx.ICON_INFORMATION
                )


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
            wx.CallLater(50, lambda: html.Scroll(*html._last_scroll_pos))
        event.Skip() # Allow event to propagate wx handler


    def on_select_participant(self, event):
        """
        Handler for selecting an item the in the participants list, toggles
        its checked state.
        """
        c = self.list_participants.GetItem(event.GetIndex())
        c.Check(not c.IsChecked())
        self.list_participants.SetItem(c)
        self.list_participants.Refresh() # Need to notify list of data change


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
        self.html_stats._last_scroll_pos = [
            self.html_stats.GetScrollPos(wx.HORIZONTAL),
            self.html_stats.GetScrollPos(wx.VERTICAL)
        ]
        self.html_stats._last_scroll_range = [
            self.html_stats.GetScrollRange(wx.HORIZONTAL),
            self.html_stats.GetScrollRange(wx.VERTICAL)
        ]
        event.Skip() # Allow event to propagate wx handler


    def on_searchall_chats(self, event):
        """
        Handler for searching chats in page_chats, focuses the search tab
        and launches search.
        """
        value = self.edit_searchall_chats.Value
        if value and value != conf.HistorySearchDescription:
            self.edit_searchall.SetFocus() # Clears description text
            self.edit_searchall.Value = value
            self.edit_searchall.SelectAll()
            self.on_searchall(None)
            self.notebook.SetSelection(1)


    def on_click_html_stats(self, event):
        """
        Handler for clicking a link in chat history statistics, scrolls to
        anchor if anchor link, otherwise shows the history and finds the word
        clicked in the word cloud.
        """
        href = event.GetLinkInfo().Href
        if href.startswith("#") and self.html_stats.HasAnchor(href[1:]):
            self.html_stats.ScrollToAnchor(href[1:])
        elif href.startswith("file://"):
            filepath = urllib.url2pathname(href[5:])
            if filepath and os.path.exists(filepath):
                #webbrowser.open("file://%s" % file["filepath"])
                os_handler.start_file(filepath)
            else:
                messageBox(
                    "The file \"%s\" cannot be found on this computer." \
                    % (filepath),
                    conf.Title, wx.OK | wx.ICON_INFORMATION
                )
        else:
            self.stc_history.SearchBarVisible = True
            self.show_stats(False)
            self.stc_history.Search(href, flags=wx.stc.STC_FIND_WHOLEWORD)
            self.stc_history.SetFocusSearch()


    def on_click_searchall_result(self, event):
        """
        Handler for clicking a link in HtmlWindow, opens the link in default
        browser.
        """
        href = event.GetLinkInfo().Href
        link_data = self.searchall_map.get(href, None)
        if link_data:
            chat = link_data.get("chat", None)
            message = link_data.get("message", None)
            file = link_data.get("file", None)
            if file:
                if file["filepath"] and os.path.exists(file["filepath"]):
                    #webbrowser.open("file://%s" % file["filepath"])
                    os_handler.start_file(file["filepath"])
                else:
                    messageBox(
                        "The file \"%s\" cannot be found on this computer." \
                        % (file["filepath"] or file["filename"]),
                        conf.Title, wx.OK | wx.ICON_INFORMATION
                    )
            elif chat:
                self.notebook.SetSelection(0)
                self.load_chat(chat, center_message_id=(
                    message["id"] if message else None
                ))
                self.show_stats(False)
        elif not (href.startswith("chat:") or href.startswith("message:") \
        or href.startswith("file:")):
            webbrowser.open(href)


    def on_searchall_stop(self, event):
        """
        Handler for clicking to stop a search, signals the search thread to
        close.
        """
        self.worker_search.stop_work()


    def on_searchall_result(self, event):
        """
        Handler for getting results from search thread, adds the results to
        the search window.
        """
        result = event.result
        # If search ID is different, results are from the previous search still
        if result["search"]["id"] == self.search_data["id"]:
            self.searchall_map.update(result["map"])
            self.results_html += result["html"]
            html = self.results_html
            if "done" in result:
                main.status("Finished searching for \"%s\" in %s.",
                    result["search"]["text"], self.db.filename
                )
            else:
                html += "</table></font>"
            self.html_searchall.Freeze()
            scrollpos = self.html_searchall.GetScrollPos(wx.VERTICAL)
            self.html_searchall.SetPage(html)
            self.html_searchall.Scroll(0, scrollpos)
            self.html_searchall.Thaw()


    def on_searchall_callback(self, result):
        """Callback function for SearchThread, posts the data to self."""
        wx.PostEvent(self, WorkerEvent(result=result))


    def on_searchall(self, event):
        """
        Handler for clicking to search all chats.
        """
        text = self.edit_searchall.Value
        if text and text != conf.HistorySearchDescription:
            main.status("Searching for \"%s\" in %s.", text, self.db.filename)
            self.results_html = \
                "<font size='2' face='%s'>Results for \"%s\":<br /><br />" \
                "<table width='600' cellpadding='2' cellspacing='0'>" \
                % (conf.HistoryFontName,
                       text.replace("&", "&amp;").replace("<", "&lt;")
                  )
            self.worker_search.stop_work(True)
            html = self.html_searchall
            data = {"text": text, "db": self.db, "tables": [],
                "window": html, "id": wx.NewId()
            }
            if self.cb_search_messages.Value:
                data["tables"].append("messages")
            if self.cb_search_chats.Value:
                data["tables"].append("conversations")
            if self.cb_search_contacts.Value:
                data["tables"].append("contacts")
            self.searchall_map.clear()
            self.search_data.update(data)
            self.worker_search.work(data)
            html.SetPage(self.results_html + "</table></font>")


    def on_focus_searchall(self, event):
        """
        Handler for focusing/unfocusing the search control, shows/hides
        description.
        """
        if self.FindFocus() == event.EventObject:
            if event.EventObject.Value == conf.HistorySearchDescription:
                event.EventObject.SetForegroundColour("black")
                event.EventObject.Value = ""
            event.EventObject.SelectAll()
        else:
            if not event.EventObject.Value:
                event.EventObject.SetForegroundColour("gray")
                event.EventObject.Value = conf.HistorySearchDescription
        event.Skip() # Allow to propagate to parent, to show having focus


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
                    tip = datetime.datetime.fromtimestamp(value).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                except:
                    tip = unicode(value)
            else:
                tip = unicode(value)
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
        new_filter = self.build_filter()
        current_filter = dict((t, self.chat_filter[t]) for t in new_filter)
        self.current_filter = current_filter
        self.new_filter = new_filter
        if new_filter != current_filter:
            self.chat_filter.update(new_filter)
            busy = controls.ProgressPanel(self, "Filtering messages.")
            self.stc_history.SetFilter(self.chat_filter)
            self.stc_history.RefreshMessages()
            self.button_stats.Enabled = (self.chat["message_count"] > 0)
            self.button_export_chat.Enabled = (self.chat["message_count"] > 0)
            self.button_filter_chat.Enabled = (self.chat["message_count"] > 0)
            self.populate_chat_statistics()
            busy.Close()


    def build_filter(self):
        """Builds chat filter data from current control state."""
        # At least one participant must be selected: reset to previously
        # selected participants instead if nothing selected
        reselecteds = []
        #for i in range(self.list_participants.Count): # for checklistctr
        for i in range(self.list_participants.GetItemCount()):
            # Item text can be "Full Name (skypename)" or "skypename"
            #t = self.list_participants.Items[i]
            #match = re.findall("\(([^)]+)\)", t)
            #id = re.findall("\(([^)]+)\)", t)[0] if t.endswith(")") else t
            #id = self.list_participants.GetItemData(i)["identity"]
            # UltimateListCtrl does not expose checked state, have to
            # query it from each individual row
            if not self.list_participants.GetItem(i).IsChecked():
                id = self.list_participants.GetItemData(i)["identity"]
                if id in self.chat_filter["participants"]:
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
            # Participant list items are "Display name (skypename)"
            "participants": participants
        }
        return filterdata


    def on_toggle_filter(self, event):
        """Handler for clicking to show/hide chat filter."""
        if self.splitter_stc.IsSplit():
            self.splitter_stc.Unsplit(self.panel_stc2)
        else:
            p = self.splitter_stc.Size.width - self.panel_stc2.BestSize.width
            self.splitter_stc.SplitVertically(
                self.panel_stc1, self.panel_stc2, sashPosition=p
            )
            self.list_participants.SetColumnWidth(
                0, self.list_participants.Size.width
            )


    def on_toggle_stats(self, event):
        """
        Handler for clicking to show/hide statistics for chat, toggles display
        between chat history window and statistics window.
        """
        self.show_stats(not self.html_stats.Shown)


    def show_stats(self, show=True):
        """Shows or hides the statistics window."""
        html, stc = self.html_stats, self.stc_history
        changed = False
        focus = False
        for i in [html, stc]:
            focus = focus or (i.Shown and i.FindFocus() == i)
        if not stc.Shown != show:
            #print "reversing stc to %s" % (not show)
            stc.Show(not show)
            changed = True
        if html.Shown != show:
            #print "reversing html to %s" % show
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


    def on_button_reset_grid(self, event):
        """
        Handler for clicking to remove sorting and filtering on a grid,
        resets the grid and its view.
        """
        grid = self.grid_table \
            if event.EventObject == self.button_reset_grid_table \
            else self.grid_sql
        if grid.Table:
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
                table = grid_source.Table.table.capitalize()
                namebase = "table \"%s\"" % table
                self.dialog_savefile.Wildcard = \
                    "HTML document (*.html)|*.html|" \
                    "SQL INSERT statements (*.sql)|*.sql|" \
                    "CSV spreadsheet (*.csv)|*.csv"
            else:
                namebase = "SQL query"
                self.dialog_savefile.Wildcard = \
                    "HTML document (*.html)|*.html|" \
                    "CSV spreadsheet (*.csv)|*.csv"
                grid_source.Table.SeekAhead(True)
            default = "Skype - %s" % namebase
            self.dialog_savefile.Filename = util.safe_filename(default)
            self.dialog_savefile.Message = "Save table as"
            if wx.ID_OK == self.dialog_savefile.ShowModal():
                filename = self.dialog_savefile.GetPath()
                #wx.GetApp().Yield(True) # Allow file dialog to close
                busy = controls.ProgressPanel(
                    self, "Exporting \"%s\"." % filename
                )
                main.status("Exporting \"%s\".", filename)
                export_result = export.export_grid(grid_source,
                    filename, default, self.db, sql=sql, table=table
                )
                busy.Close()
                if export_result:
                    main.logstatus("Exported %s.", filename)
                    os_handler.start_file(filename)
                else:
                    wx.MessageBox(
                        "Cannot access \"%s\"." % filename,
                        conf.Title, wx.OK | wx.ICON_WARNING
                    )
                    main.logstatus("Cannot access %s.", filename)


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
        Handler for clicking to run an SQL query, runs the query, displays its
        results, if any, and commits changes done, if any.
        """
        sql = self.stc_sql.Text.strip()
        if sql:
            self.execute_sql(sql)


    def execute_sql(self, sql):
        """Executes the SQL query and populates the SQL grid with results."""
        try:
            grid_data = None
            if sql.lower().startswith("select"):
                # SELECT statement: populate grid with rows
                grid_data = self.db.execute_select(sql)
                self.grid_sql.SetTable(grid_data)
                self.button_export_sql.Enabled = True
            else:
                # Assume action query
                affected_rows = self.db.execute_action(sql)
                self.grid_sql.SetTable(None)
                self.grid_sql.CreateGrid(1, 1)
                self.grid_sql.SetColLabelValue(0, "Affected rows")
                self.grid_sql.SetCellValue(0, 0, str(affected_rows))
                self.button_export_sql.Enabled = False
            main.logstatus("Executed SQL \"%s\".", sql)
            size = self.grid_sql.Size
            self.grid_sql.Fit()
            # Jiggle size by 1 pixel to refresh scrollbars
            self.grid_sql.Size = size[0], size[1]-1
            self.grid_sql.Size = size[0], size[1]
            self.last_sql = sql
            self.grid_sql.SetColMinimalAcceptableWidth(100)
            if grid_data:
                [self.grid_sql.AutoSizeColLabelSize(i) \
                    for i in range(grid_data.GetNumberCols())
                ]
        except Exception, e:
            wx.MessageBox(
                unicode(e).capitalize(), conf.Title, wx.OK | wx.ICON_WARNING
            )


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
        item = self.tree_tables.GetNextVisible(self.tree_tables.RootItem)
        while item and item.IsOk():
            list_table = self.tree_tables.GetItemPyData(item)
            if list_table:
                list_table = list_table.lower()
                if list_table == grid_data.table:
                    self.tree_tables.SetItemTextColour(
                        item,
                        conf.DBTableChangedColour if grid_data.IsChanged() \
                           else "black"
                    )
                    break # break while
            item = self.tree_tables.GetNextVisible(item)

        # Mark database as changed/pristine in the parent notebook tabs
        for i in range(self.parent_notebook.PageCount):
            if self.parent_notebook.GetPage(i) == self:
                title = self.Label + ("*" if grid_data.IsChanged() else "")
                if self.parent_notebook.GetPageText(i) != title:
                    self.parent_notebook.SetPageText(i, title)
                break


    def on_commit_table(self, event):
        """Handler for clicking to commit the changed database table."""
        if wx.OK == wx.MessageBox(
            "Are you sure you want to commit these changes (%s)?" % (
                self.grid_table.Table.GetChangedInfo()
            ),
            conf.Title, wx.OK | wx.CANCEL
        ):
            self.grid_table.Table.SaveChanges()
            self.on_change_table(None)
            # Refresh tables list with updated row counts
            tablemap = dict((t["name"], t) for t in self.db.get_tables(True))
            item = self.tree_tables.GetNextVisible(self.tree_tables.RootItem)
            while item and item.IsOk():
                table = self.tree_tables.GetItemPyData(item)
                if table:
                    self.tree_tables.SetItemText(item, "%d row%s" % (
                        tablemap[table]["rows"],
                        "s" if tablemap[table]["rows"] != 1 else " "
                    ), 1)
                    if table == self.grid_table.Table.table:
                        self.tree_tables.SetItemTextColour(
                            item,
                            conf.DBTableChangedColour \
                                if self.grid_table.Table.IsChanged() \
                                else "black"
                        )
                item = self.tree_tables.GetNextVisible(item)


    def on_rollback_table(self, event):
        """Handler for clicking to rollback the changed database table."""
        self.grid_table.Table.UndoChanges()
        self.grid_table.ContainingSizer.Layout() # Refresh scrollbars
        self.on_change_table(None)


    def on_insert_row(self, event):
        """
        Handler for clicking to insert a table row, lets the user edit a new
        grid line.
        """
        self.grid_table.InsertRows(0)
        self.grid_table.SetGridCursor(0, 0)
        self.grid_table.ScrollLineY = 0 # Scroll to top to the new row
        self.grid_table.Refresh()
        self.grid_table.ContainingSizer.Layout() # Refresh scrollbars
        self.on_change_table(None)


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


    def on_change_list_tables(self, event):
        """
        Handler for selecting an item in the tables list, loads the table data
        into the table grid.
        """
        table = None
        item = event.GetItem()
        if item and item.IsOk():
            table = self.tree_tables.GetItemPyData(item)
        if table and \
        (not self.grid_table.Table or self.grid_table.Table.table != table):
            i = self.tree_tables.GetNextVisible(self.tree_tables.RootItem)
            while i:
                text = self.tree_tables.GetItemText(i)
                bgcolour = conf.ListOpenedBgColour if (text == table) \
                           else "white"
                self.tree_tables.SetItemBackgroundColour(i, bgcolour)
                i = self.tree_tables.GetNextSibling(i)
            busy = controls.ProgressPanel(self, "Loading table \"%s\"." % table)
            grid_data = self.db.get_table_data(table)
            self.label_table.Label = "Table \"%s\":" % table
            self.grid_table.SetTable(grid_data)
            self.page_tables.Layout() # React to grid size change
            self.grid_table.Scroll(0, 0)
            self.grid_table.SetColMinimalAcceptableWidth(100)
            [self.grid_table.AutoSizeColLabelSize(i) \
                for i in range(grid_data.GetNumberCols())
            ]
            self.on_change_table(None)
            self.tb_grid.EnableTool(wx.ID_ADD, True)
            self.tb_grid.EnableTool(wx.ID_DELETE, True)
            self.button_export_table.Enabled = True
            busy.Close()


    def on_change_list_chats(self, event,):
        """
        Handler for selecting an item in the chats list, loads the
        messages into the message log.
        """
        self.load_chat(self.list_chats._data_map.get(event.Data))


    def load_chat(self, chat, center_message_id=None):
        """Loads history of the specified chat (as returned from db)."""
        if chat and (chat != self.chat or center_message_id):
            if chat != self.chat:
                self.list_chats.Freeze()
                scrollpos = self.list_chats.GetScrollPos(wx.VERTICAL)
                index_selected = -1
                for i in range(self.list_chats.ItemCount):
                    if self.list_chats.GetItemMappedData(i) == self.chat:
                        self.list_chats.SetItemBackgroundColour(
                            i, self.list_chats.BackgroundColour
                        )
                    elif self.list_chats.GetItemMappedData(i) == chat:
                        index_selected = i
                        self.list_chats.SetItemBackgroundColour(
                            i, conf.ListOpenedBgColour
                        )
                if index_selected >= 0:
                    delta = index_selected - scrollpos
                    if delta < 0 or abs(delta) >= self.list_chats.CountPerPage:
                        nudge = -self.list_chats.CountPerPage / 2
                        self.list_chats.ScrollLines(delta + nudge)
                self.list_chats.Thaw()
                wx.GetApp().Yield(True) # Allow display to refresh
                # Add shortcut key flag to chat label
                self.label_chat.Label = chat["title_long"].replace(
                    "chat", "c&hat"
                ).replace("Chat", "C&hat") + ":"
                busy = controls.ProgressPanel(self, "Loading history for %s." \
                    % chat["title_long_lc"]
                )
            dates_range  = [None, None]
            dates_values = [None, None]
            if chat != self.chat or (center_message_id
            and not self.stc_history.IsMessageShown(center_message_id)):
                self.edit_filtertext.Value = self.chat_filter["text"] = ""
                date_range = [
                    chat["first_message_datetime"].date() \
                    if chat["first_message_datetime"] else None,
                    chat["last_message_datetime"].date() \
                    if chat["last_message_datetime"] else None
                ]
                self.chat_filter["daterange"] = date_range
                self.chat_filter["startdaterange"] = date_range
                dates_range = dates_values = date_range
                avatar_default = images.AvatarDefault.GetBitmap()
                if chat != self.chat:
                    # If chat has changed, load avatar images for the contacts
                    self.list_participants.ClearAll()
                    self.list_participants.InsertColumn(0, "")
                    il = wx.ImageList(*conf.AvatarImageSize)
                    il.Add(avatar_default)
                    index = 0
                    for p in chat["participants"]:
                        b = 0
                        if "avatar_image" in p["contact"] \
                        and "avatar_bitmap" not in p["contact"] \
                        and p["contact"]["avatar_image"]:
                            raw = p["contact"]["avatar_image"].encode(
                                "latin1"
                            )
                            if raw.startswith("\0"):
                                # For some reason, Skype avatar image blobs
                                # start with a null byte, unsupported by wx.
                                raw = raw[1:]
                            img = wx.ImageFromStream(cStringIO.StringIO(raw))
                            size = list(conf.AvatarImageSize)
                            pos = None
                            if img.Width != img.Height:
                                ratio = util.safedivf(img.Width, img.Height)
                                i = 0 if ratio < 1 else 1
                                size[i] = size[i] / ratio if i \
                                          else size[i] * ratio
                                pos = ((conf.AvatarImageSize[0] - size[0]) / 2,
                                    (conf.AvatarImageSize[1] - size[1]) / 2
                                )
                            img = img.ResampleBox(*size)
                            if pos:
                                bgcolor = (255, 255, 255)
                                img.Resize(conf.AvatarImageSize, pos, *bgcolor)
                            p["contact"]["avatar_bitmap"] = wx.BitmapFromImage(
                                img
                            )
                        if "avatar_bitmap" in p["contact"]:
                            b = il.Add(p["contact"]["avatar_bitmap"])
                        self.list_participants.InsertImageStringItem(index,
                            p["contact"]["name"], b, it_kind=1
                        )
                        c = self.list_participants.GetItem(index)
                        c.Check(True)
                        self.list_participants.SetItem(c)
                        self.list_participants.SetItemData(index, p)
                        index += 1
                    self.list_participants.AssignImageList(
                        il, wx.IMAGE_LIST_SMALL
                    )
                    self.list_participants.SetColumnWidth(0, wx.LIST_AUTOSIZE)
                self.chat_filter["participants"] = [
                    p["identity"] for p in chat["participants"]
                ]
            if center_message_id and self.chat == chat:
                if not self.stc_history.IsMessageShown(center_message_id):
                    self.stc_history.SetFilter(self.chat_filter)
                    self.stc_history.RefreshMessages(center_message_id)
                else:
                    self.stc_history.FocusMessage(center_message_id)
            else:
                self.stc_history.SetFilter(self.chat_filter)
                self.stc_history.Populate(chat, self.db,
                    center_message_id=center_message_id
                )
            if self.stc_history.GetMessage(0):
                values = [self.stc_history.GetMessage(0)["datetime"],
                    self.stc_history.GetMessage(-1)["datetime"]
                ]
                dates_values = tuple(i.date() for i in values)
                if not filter(None, dates_range):
                    dates_range = dates_values
                self.chat_filter["daterange"] = dates_range
                self.chat_filter["startdaterange"] = dates_range
            self.range_date.SetRange(*dates_range)
            self.range_date.SetValues(*dates_values)
            has_messages = bool(self.stc_history.GetMessage(0))
            self.button_stats.Enabled = has_messages
            self.button_export_chat.Enabled = has_messages
            self.button_filter_chat.Enabled = has_messages
            if self.chat != chat:
                self.chat = chat
                busy.Close()
            self.populate_chat_statistics()
            if self.html_stats.Shown:
                self.show_stats(True) # To restore scroll position


    def populate_chat_statistics(self):
        """Populates html_stats with chat statistics and word cloud."""

        previous_anchor = self.html_stats.OpenedAnchor
        previous_scrollpos = getattr(self.html_stats, "_last_scroll_pos", None)
        h = BeautifulSoup.MinimalSoup("")
        stats = self.stc_history.GetStatistics()
        if stats:
            t = BeautifulSoup.Tag(h, "table")

            if "avatar__default.jpg" not in self.memoryfs["files"]:
                self.memoryfs["handler"].AddFile("avatar__default.jpg",
                    images.AvatarDefault.GetBitmap(), wx.BITMAP_TYPE_BMP
                )
                self.memoryfs["files"]["avatar__default.jpg"] = 1

            def add_row(cell1, cell2):
                r = BeautifulSoup.Tag(h, "tr")
                c1 = BeautifulSoup.Tag(
                    h, "td", {"valign": "top", "width": "200"}
                )
                c2 = BeautifulSoup.Tag(h, "td", {"valign": "top"})
                c1.append(cell1 + ":"), c2.append(str(cell2))
                r.append(c1), r.append(c2), t.append(r)

            def add_contact_row(contact, values):
                name = contact["name"]
                r = BeautifulSoup.Tag(h, "tr")
                c1 = BeautifulSoup.Tag(h, "td", {"valign": "top"})
                c2 = BeautifulSoup.Tag(h, "td", {"valign": "top"})
                avatar_filename = "avatar__default.jpg"
                if "avatar_bitmap" in contact:
                    avatar_filename = "%s_%s.jpg" % tuple(map(
                        urllib.quote, (self.db.filename, contact["identity"])
                     ))
                    if avatar_filename not in self.memoryfs["files"]:
                        self.memoryfs["handler"].AddFile(avatar_filename,
                            contact["avatar_bitmap"], wx.BITMAP_TYPE_BMP
                        )
                        self.memoryfs["files"][avatar_filename] = 1
                c1.append("<table cellpadding='0' cellspacing='0'><tr>" \
                          "<td valign='top'><img src='memory:%s'/>" \
                          "&nbsp;&nbsp;</td><td valign='center'>%s</td></tr>" \
                          "</table>" % (
                              avatar_filename, export.escape(name, False)
                ))
                if isinstance(values, basestring):
                    c2.append(values)
                else:
                    for label, value, total, color in values:
                        width = util.safedivf(value, total) * conf.PlotWidth
                        # Set at least a width of 1 pixel for very small values
                        width = int(width) if (width > 1 or not value) else 1
                        tbl = BeautifulSoup.Tag(h, "table",
                            {"cellpadding": "0", "cellspacing": "0"}
                        )
                        tr = BeautifulSoup.Tag(h, "tr")
                        if width:
                            tr.append(BeautifulSoup.Tag(h, "td", {
                                "bgcolor": color, "width": str(width)
                            }))
                        if width < conf.PlotWidth:
                            tr.append(BeautifulSoup.Tag(h, "td", {
                                "bgcolor": conf.PlotBgColour,
                                "width": str(conf.PlotWidth - width)
                            }))
                        dl = BeautifulSoup.Tag(h, "td")
                        if "bytes" == label:
                            dl.append("&nbsp;%s" % util.format_bytes(value))
                        else:
                            dl.append("&nbsp;%s %s" % (value, label))
                        tr.append(dl); tbl.append(tr); c2.append(tbl)
                r.append(c1); r.append(c2); t.append(r)


            delta_date = stats["enddate"] - stats["startdate"]
            period_value = ""
            if delta_date.days:
                period_value = "%s - %s (%s)" % (
                    stats["startdate"].strftime("%d.%m.%Y"),
                    stats["enddate"].strftime("%d.%m.%Y"),
                    util.plural("day", delta_date.days)
                )
            else:
                period_value = stats["startdate"].strftime("%d.%m.%Y")
            chars_total = sum([i["chars"] for i in stats["counts"].values()])
            smschars_total = sum(
                [i["smschars"] for i in stats["counts"].values()]
            )
            files_total = sum([i["files"] for i in stats["counts"].values()])
            bytes_total = sum([i["bytes"] for i in stats["counts"].values()])
            msgs_value  = "%d (%s)" % (
                stats["messages"], util.plural("character", chars_total)
            ) if stats["messages"] else 0
            smses_value  = "%d (%s)" % (
                stats["smses"], util.plural("character", smschars_total)
            ) if stats["smses"] else 0
            files_value  = "%d (%s)" % (
                len(stats["transfers"]), util.format_bytes(bytes_total)
            ) if stats["transfers"] else 0
            add_row("Time period", period_value)
            if msgs_value:
                add_row("Messages", msgs_value)
            if smses_value:
                add_row("SMSes", smses_value)
            if files_value:
                add_row("Files", files_value)
            msgs_per_day = util.safedivf(stats["messages"], delta_date.days+1)
            # Drop trailing zeroes
            msgs_per_day = "%d" % msgs_per_day \
                if msgs_per_day == int(msgs_per_day) \
                else ("%.1f" % msgs_per_day)
            add_row("Messages per day", msgs_per_day)
            for p in self.chat["participants"]:
                id, name = p["identity"], p["contact"]["name"]
                plotvals = [] # [(label, value, total), ]
                if id in stats["counts"]:
                    msgs = stats["counts"][id]["messages"]
                    chars = stats["counts"][id]["chars"]
                    smses = stats["counts"][id]["smses"]
                    smschars = stats["counts"][id]["smschars"]
                    files = stats["counts"][id]["files"]
                    bytes = stats["counts"][id]["bytes"]
                    if msgs:
                        plotvals.append(("messages", msgs,
                            stats["messages"], conf.PlotMessagesColour
                        ))
                        plotvals.append(("characters", chars,
                            chars_total, conf.PlotMessagesColour
                        ))
                    if smses:
                        plotvals.append(("SMSes", smses,
                            stats["smses"], conf.PlotSMSesColour
                        ))
                        plotvals.append(("SMS characters", smschars,
                            smschars_total, conf.PlotSMSesColour
                        ))
                    if files:
                        plotvals.append(("files", files,
                            files_total, conf.PlotFilesColour
                        ))
                        plotvals.append(("bytes", bytes,
                            bytes_total, conf.PlotFilesColour
                        ))
                if plotvals:
                    add_contact_row(p["contact"], plotvals)
            h.append(t)
        cloud = self.stc_history.GetWordCloud()
        if cloud:
            if t.first():
                h.insert(0, "<table cellpadding='0' cellspacing='0' " \
                            "width='100%'><tr><td><a name='top'>" \
                            "<b>Statistics for currently shown messages:</b>" \
                            "</a></td><td align='right'><a href='#cloud'>" \
                            "Jump to word cloud</a></td></tr></table><br />"
                )
                h.append("<br /><hr />")
            h.append("<table cellpadding='0' cellspacing='0' width='100%'>" \
                     "<tr><td><a name='cloud'>" \
                     "<b>Word cloud for currently shown messages:</b>" \
                     "</a></td><td align='right'><a href='#top'>" \
                     "Back to top</a></td></tr></table><br />"
            )
        for word, count, fontsize in cloud:
            e = BeautifulSoup.Tag(h, "font", {
                "size": str(fontsize), "color": "blue"
            })
            a = BeautifulSoup.Tag(h, "a", {"href": word})
            a.append(word)
            e.append(a), e.append(" (%s) " % count), h.append(e)
        if stats and stats["transfers"]:
            h.append("<br /><hr />" \
                     "<table cellpadding='0' cellspacing='0' width='100%'>" \
                     "<tr><td><a name='transfers'>" \
                     "<b>Sent and received files:</b>" \
                     "</a></td><td align='right'><a href='#top'>" \
                     "Back to top</a></td></tr></table><br /><br />"
            )
            t = BeautifulSoup.Tag(h, "table", {"width": "100%%"})
            attr_font = {"face": conf.HistoryFontName, "size": "2"}
            colour_sender = {True: conf.HistoryRemoteAuthorColour,
                False: conf.HistoryLocalAuthorColour
            }

            for f in stats["transfers"]:
                r = BeautifulSoup.Tag(h, "tr")
                c1 = BeautifulSoup.Tag(h, "td", {"align": "right",
                    "valign": "top", "nowrap": ""
                })
                c2 = BeautifulSoup.Tag(h, "td", {"valign": "top", "nowrap": ""})
                c3 = BeautifulSoup.Tag(h, "td", {
                    "align": "right", "valign": "top"
                })
                c4 = BeautifulSoup.Tag(h, "td", {"valign": "top", "nowrap": ""})
                a = BeautifulSoup.Tag(h, "a", {
                    "href": skypedata.MessageParser.path_to_url(
                        f["filepath"] or f["filename"]
                     )
                })
                a.append(f["filepath"] or f["filename"])
                f1 = BeautifulSoup.Tag(h, "font", attr_font)
                f2 = BeautifulSoup.Tag(h, "font", attr_font)
                f3 = BeautifulSoup.Tag(h, "font", attr_font)
                f4 = BeautifulSoup.Tag(h, "font", attr_font)
                c1.append(f1), c2.append(f2), c3.append(f3), c4.append(f4)

                inbound = (skypedata.TRANSFER_TYPE_OUTBOUND == f["type"])
                partner = self.db.get_contact_name(f["partner_handle"])
                datetime_file = datetime.datetime.fromtimestamp(f["starttime"])
                f1["color"] = colour_sender[inbound]
                f1.append(partner if inbound else self.db.account["name"])
                f2.append(a), f3.append(util.format_bytes(int(f["filesize"])))
                f4.append(datetime_file.strftime("%Y-%m-%d %H:%M"))
                r.append(c1), r.append(c2), r.append(c3), r.append(c4)
                t.append(r)
            h.append(t)

        self.html_stats.Freeze()
        html = unicode(h)
        self.html_stats.SetPage(html)
        if previous_scrollpos:
            self.html_stats.Scroll(*previous_scrollpos)
        elif previous_anchor and self.html_stats.HasAnchor(previous_anchor):
            self.html_stats.ScrollToAnchor(previous_anchor)
        self.html_stats.Thaw()


    def on_sort_grid_column(self, event):
        """
        Handler for clicking a table grid column, sorts the table by the column.
        """
        grid = event.GetEventObject()
        if grid.Table:
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
        if grid.Table:
            row, col = event.GetRow(), event.GetCol()
            # Remember scroll positions, as grid update loses them
            scroll_hor = grid.GetScrollPos(wx.HORIZONTAL)
            scroll_ver = grid.GetScrollPos(wx.VERTICAL)
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
                        busy = controls.ProgressPanel(self.page_tables,
                            "Filtering column \"%s\" by \"%s\"." % (
                                grid_data.columns[col]["name"], new_filter
                        ))
                        grid_data.AddFilter(col, new_filter)
                        busy.Close()
                    else:
                        grid_data.RemoveFilter(col)
            grid.ContainingSizer.Layout() # React to grid size change


    def load_data(self):
        """Loads data from our SkypeDatabase."""
        # Populate the tables list
        self.label_title.Label = "Database \"%s\":" % self.db

        # Populate the chats list
        self.chats = self.db.get_conversations()
        for c in self.chats:
            c["people"] = "" # Set empty data, stats will come later

        column_map = [
            ("title", "Chat"), ("message_count", "Messages"),
            ("created_datetime", "Created"),
            ("first_message_datetime", "First message"),
            ("last_activity_datetime", "Last activity"),
            ("type_name", "Type"), ("people", "People")
        ]
        self.list_chats.Populate(column_map, self.chats)
        self.list_chats.SortListItems(4, 0) # Sort by last activity timestamp
        self.list_chats.OnSortOrderChanged()

        threading.Thread(target=self.load_later_data).start()


    def load_later_data(self):
        """
        Loads later data from the database, like table metainformation and
        statistics for all chats, used as a background callback to speed
        up page opening.
        """
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
                    grandchld = self.tree_tables.AppendItem(child, col["name"])
                    self.tree_tables.SetItemText(grandchld, col["type"], 1)
            self.tree_tables.Expand(root)
            if child:
                self.tree_tables.Expand(child)
                self.tree_tables.SetColumnWidth(0, -1)
                self.tree_tables.SetColumnWidth(1, -1)
                self.tree_tables.Collapse(child)

            # Add table and column names to SQL editor autocomplete
            self.stc_sql.AutoCompAddWords([t["name"] for t in tables])
            for t in tables:
                coldata = self.db.get_table_columns(t["name"])
                fields = [c["name"] for c in coldata]
                self.stc_sql.AutoCompAddSubWords(t["name"], fields)

            # Load chat statistics and update the chat list
            self.db.get_conversations_stats(self.chats)
            for c in self.chats:
                people = []
                if skypedata.CHATS_TYPE_SINGLE != c["type"]:
                    for p in c["participants"]:
                        people.append(p["contact"]["name"])
                c["people"] = ", ".join(people)
            self.list_chats.RefreshItems()
            if self.chat:
                # If the user already opened a chat while later data
                # was loading, update the date range control values.
                date_range = [
                    self.chat["first_message_datetime"].date() \
                    if self.chat["first_message_datetime"] else None,
                    self.chat["last_message_datetime"].date() \
                    if self.chat["last_message_datetime"] else None
                ]
                self.range_date.SetRange(*date_range)
        except Exception, e:
            # Database access can easily fail if the user closes the tab before
            # the later data has been loaded.
            if self:
                main.log("Error accessing database %s.\n%s",
                    self.db, traceback.format_exc()
                )
        if self:
            self.button_close.Enabled = True
            main.status("Opened Skype database %s.", self.db)


    def on_close(self, event):
        """
        Handler for clicking to close the page, stops search thread. If there
        is any uncommitted data, asks the user about saving.
        """
        do_close = True
        unsaved = self.db.get_unsaved_grids()
        if unsaved:
            response = wx.MessageBox(
                "Some tables in %s have unsaved data (%s).\n\n"
                "Save changes before closing?" % (
                    self.db, ", ".join(unsaved)
                ),
                conf.Title, wx.YES | wx.NO | wx.CANCEL | wx.ICON_QUESTION
            )
            if wx.YES == response:
                self.db.save_unsaved_grids()
            elif wx.CANCEL == response:
                do_close = False
        if do_close:
            self.worker_search.stop()
            self.db.unregister_consumer(self)
            self.Close()



class MergerPage(wx.Panel):
    """
    A wx.Notebook page for comparing two Skype databases, has its own Notebook
    with one page for diffing/merging chats, and another for contacts.
    """


    """Labels for chat diff result in chat list."""
    DIFFSTATUS_IDENTICAL = "In sync"
    DIFFSTATUS_DIFFERENT = "Out of sync"

    def __init__(self, parent_notebook, db1, db2, title):
        wx.Panel.__init__(self, parent=parent_notebook)
        self.parent_notebook = parent_notebook
        self.db1 = db1
        self.db2 = db2
        main.status("Opening Skype databases %s and %s.",
            self.db1, self.db2
        )
        self.db1.register_consumer(self)
        self.db2.register_consumer(self)
        self.Label = title
        parent_notebook.InsertPage(1, self, title)
        # Multiline wx.Notebooks need redrawing
        self.TopLevelParent.SendSizeEvent()
        for i in range(parent_notebook.GetPageCount()):
            if parent_notebook.GetPage(i) == self:
                parent_notebook.SetSelection(i)
        #wx.GetApp().Yield(True) # Allow notebook tab and selection to refresh
        busy = controls.ProgressPanel(
            self, "Comparing \"%s\"\n and \"%s\"." % (db1, db2)
        )

        self.chat_diff = None      # Chat currently being diffed
        self.chat_diff_data = None # {"messages": [,], "participants": [,]}
        self.compared = None       # List of all chats
        self.con1difflist = None   # Contact and contact group differences
        self.con2difflist = None   # Contact and contact group differences
        self.con1diff = None       # Contact differences for left
        self.con2diff = None       # Contact differences for right
        self.congroup1diff = None  # Contact group differences for left
        self.congroup2diff = None  # Contact group differences for right
        self.chats_differing = None  # [chats differing in db1, in db2]
        self.diffresults_html = None # Diff results HTML for db1, db2
        self.contacts_column_map = [
            ("identity", "Account"), ("name", "Name"),
            ("phone_mobile_normalized", "Mobile phone"),
            ("country", "Country"), ("city", "City"), ("about", "About"),
            ("__type", "Type")
        ]
        self.chats_column_map = [
            ("title", "Chat"), ("messages1", "Messages in left"),
            ("messages2", "Messages in right"),
            ("last_message_datetime1", "Last message in left"),
            ("last_message_datetime2", "Last message in right"),
            ("type_name", "Type"), ("diff_status", "First glance")
        ]
        self.diffresult_htmls = ["", ""] # Partially assembled HTML bits
        self.Bind(EVT_WORKER, self.on_scan_all_result)
        self.worker_diff = workers.DiffThread(self.on_scan_all_callback)

        sizer = self.Sizer = wx.BoxSizer(wx.VERTICAL)

        sizer_header = wx.BoxSizer(wx.HORIZONTAL)
        label = self.html_dblabel = wx.html.HtmlWindow(parent=self,
            size=(-1, 36), style=wx.html.HW_SCROLLBAR_NEVER
        )
        label.BackgroundColour = self.BackgroundColour
        label.SetFonts(normal_face=self.Font.FaceName,
            fixed_face=self.Font.FaceName, sizes=[8] * 7
        )
        self.Bind(wx.html.EVT_HTML_LINK_CLICKED, self.on_link_db, label)
        button_swap  = self.button_swap  = wx.Button(
            parent=self, label="&Swap left-right", size=(100, -1)
        )
        button_swap.Enabled = False
        button_swap.SetToolTipString("Swaps left and right database.")
        button_close = self.button_close = wx.Button(
            parent=self, label="&Close tab", size=(100, -1)
        )
        button_close.Enabled = False
        self.Bind(wx.EVT_BUTTON, self.on_swap, button_swap)
        self.Bind(wx.EVT_BUTTON, self.on_close, button_close)
        sizer_header.Add(label, border=5, proportion=1,
            flag=wx.GROW | wx.TOP | wx.BOTTOM
        )
        sizer_header.Add(button_swap, border=5,
            flag=wx.LEFT | wx.ALIGN_CENTER_VERTICAL
        )
        sizer_header.Add(button_close, border=5,
            flag=wx.LEFT | wx.ALIGN_CENTER_VERTICAL
        )

        bookstyle = wx.lib.agw.fmresources.INB_LEFT
        if wx.version().startswith("2.8") and sys.version.startswith("2.6"):
            # In Python 2.6, wx 2.8 the FlatImageBook display is a tad buggy
            bookstyle |= wx.lib.agw.fmresources.INB_FIT_LABELTEXT
        notebook = self.notebook = wx.lib.agw.labelbook.FlatImageBook(
            parent=self, agwStyle=bookstyle,
            style=wx.BORDER_STATIC
        )

        il = wx.ImageList(32, 32)
        idx1 = il.Add(images.IconMergeChats.GetBitmap())
        idx2 = il.Add(images.IconMergeContacts.GetBitmap())
        idx3 = il.Add(images.IconMergeAll.GetBitmap())
        notebook.AssignImageList(il)

        self.create_page_merge_chats(notebook)
        self.create_page_merge_contacts(notebook)
        self.create_page_merge_all(notebook)

        notebook.SetPageImage(0, idx1)
        notebook.SetPageImage(1, idx2)
        notebook.SetPageImage(2, idx3)


        sizer.Add(sizer_header, flag=wx.GROW)
        sizer.Add(notebook, proportion=10, border=5,
            flag=wx.GROW | wx.LEFT | wx.RIGHT | wx.BOTTOM
        )

        self.TopLevelParent.page_merge_latest = self
        self.TopLevelParent.console.run(
            "page12 = self.page_merge_latest # Merger tab"
        )
        self.TopLevelParent.console.run(
            "db1, db2 = page12.db1, page12.db2 # Chosen Skype databases"
        )

        # Layout() required, otherwise sizers do not start working
        # automatically as it's late creation
        self.Layout()
        self.Refresh()
        self.load_data()
        # 2nd Layout() seems also required
        self.Refresh()
        self.Layout()
        busy.Close()


    def create_page_merge_all(self, notebook):
        """Creates a page for merging everything at once."""
        page = self.page_merge_all = wx.Panel(parent=notebook)
        notebook.AddPage(page, "Merge all")
        sizer = page.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_data = wx.BoxSizer(wx.HORIZONTAL)
        sizer_html = wx.BoxSizer(wx.HORIZONTAL)
        sizer_html1 = wx.BoxSizer(wx.VERTICAL)
        sizer_html2 = wx.BoxSizer(wx.VERTICAL)
        label1 = self.label_all1 = wx.StaticText(page, style=wx.ALIGN_RIGHT,
            label="%s\n\nAnalyzing..%s" % (self.db1.filename, "\n" * 7)
        )
        label2 = self.label_all2 = wx.StaticText(page,
            label="%s\n\nAnalyzing..%s" % (self.db2.filename, "\n" * 7)
        )
        button_scan = self.button_scan_all = wx.Button(
            page, label="Scan differences between left and right"
        )
        html1 = self.html_results1 = controls.ScrollingHtmlWindow(
            page, style=wx.BORDER_STATIC
        )
        html2 = self.html_results2 = controls.ScrollingHtmlWindow(
            page, style=wx.BORDER_STATIC
        )
        for h in [html1, html2]:
            h.SetFonts(normal_face=self.Font.FaceName,
                fixed_face=self.Font.FaceName, sizes=[8] * 7
            )
            h.Bind(
                wx.html.EVT_HTML_LINK_CLICKED, self.on_click_htmldiff
            )

        buttonall1 = self.button_mergeall1 = wx.Button(
            page, label="Merge differences to the right >>>"
        )
        buttonall2 = self.button_mergeall2 = wx.Button(
            page, label="<<< Merge differences to the left"
        )
        button_scan.Enabled = False
        buttonall1.Enabled = buttonall2.Enabled = False
        button_scan.Bind(wx.EVT_BUTTON, self.on_scan_all)
        buttonall1.Bind(wx.EVT_BUTTON, self.on_merge_all)
        buttonall2.Bind(wx.EVT_BUTTON, self.on_merge_all)
        sizer_data.Add(label1, proportion=1, border=5, flag=wx.ALL)
        sizer_data.AddSpacer(20)
        sizer_data.Add(label2, proportion=1, border=5, flag=wx.ALL)
        sizer.AddSpacer(20)
        sizer.Add(sizer_data, flag=wx.ALIGN_CENTER)
        sizer.AddSpacer(10)
        sizer.Add(button_scan, flag=wx.ALIGN_CENTER_HORIZONTAL)
        sizer.AddSpacer(20)
        sizer.Add(wx.StaticText(page, label=\
            "Scanning will go through all chat messages in either database\n"
            "and find the ones not present in the other one.\n\n"
            "This can take several minutes.", style=wx.ALIGN_CENTER
        ), border=10, flag=wx.ALIGN_CENTER | wx.ALL)
        sizer_html1.Add(html1, proportion=1, flag=wx.GROW)
        sizer_html1.Add(buttonall1, border=15, flag=wx.TOP | wx.ALIGN_RIGHT)
        sizer_html2.Add(html2, proportion=1, flag=wx.GROW)
        sizer_html2.Add(buttonall2, border=15, flag=wx.TOP)
        sizer_html.Add(
            sizer_html1, proportion=1, border=5, flag=wx.ALL | wx.GROW
        )
        sizer_html.Add(
            sizer_html2, proportion=1, border=5, flag=wx.ALL | wx.GROW
        )
        sizer.Add(sizer_html, proportion=1, border=10, flag=wx.ALL | wx.GROW)


    def create_page_merge_chats(self, notebook):
        """Creates a page for seeing and merging differing chats."""
        page = self.page_merge_chats = wx.Panel(parent=notebook)
        notebook.AddPage(page, "Chats")
        sizer = page.Sizer = wx.BoxSizer(wx.VERTICAL)
        splitter = self.splitter_merge = wx.SplitterWindow(
            parent=page, style=wx.BORDER_NONE
        )
        splitter.SetMinimumPaneSize(50)
        panel1 = wx.Panel(parent=splitter)
        panel2 = wx.Panel(parent=splitter)
        sizer1 = panel1.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer2 = panel2.Sizer = wx.BoxSizer(wx.VERTICAL)

        sizer1.Add(wx.StaticText(
            parent=panel1, label="C&hat comparison:")
        )
        list_chats = self.list_chats = controls.SortableListView(
            parent=panel1, style=wx.LC_REPORT | wx.LC_SINGLE_SEL
        )
        list_chats.Enabled = False
        self.Bind(
            wx.EVT_LIST_ITEM_ACTIVATED, self.on_change_list_chats, list_chats
        )
        sizer1.Add(list_chats, proportion=1, flag=wx.GROW)

        label_chat = self.label_merge_chat = \
            wx.StaticText(parent=panel2, label="")
        splitter_diff = self.splitter_diff = wx.SplitterWindow(
            parent=panel2, style=wx.BORDER_SIMPLE
        )
        splitter_diff.SetMinimumPaneSize(1)
        panel_stc1 = self.panel_stc1 = wx.Panel(parent=splitter_diff)
        panel_stc2 = self.panel_stc2 = wx.Panel(parent=splitter_diff)
        sizer_stc1 = panel_stc1.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_stc2 = panel_stc2.Sizer = wx.BoxSizer(wx.VERTICAL)

        label_db1 = self.label_chat_db1 = wx.StaticText(
            parent=panel_stc1, label=""
        )
        stc1 = self.stc_diff1 = ChatContentSTC(
            parent=panel_stc1, style=wx.BORDER_STATIC
        )
        label_db2 = self.label_chat_db2 = wx.StaticText(
            parent=panel_stc2, label=""
        )
        stc2 = self.stc_diff2 = ChatContentSTC(
            parent=panel_stc2, style=wx.BORDER_STATIC
        )

        button1 = self.button_merge_chat_1 = wx.Button(parent=panel_stc1,
            label="Merge messages to database on the right >>>"
        )
        button2 = self.button_merge_chat_2 = wx.Button(parent=panel_stc2,
            label="<<< Merge messages to database on the left"
        )
        button1.Bind(wx.EVT_BUTTON, self.on_merge_chat)
        button2.Bind(wx.EVT_BUTTON, self.on_merge_chat)
        button1.Enabled = button2.Enabled = False

        sizer_stc1.Add(label_db1, border=5, flag=wx.ALL)
        sizer_stc1.Add(stc1, proportion=1, flag=wx.GROW)
        sizer_stc1.Add(button1, border=5, flag=wx.ALIGN_CENTER | wx.ALL)
        sizer_stc2.Add(label_db2, border=5, flag=wx.ALL)
        sizer_stc2.Add(stc2, proportion=1, flag=wx.GROW)
        sizer_stc2.Add(button2, border=5, flag=wx.ALIGN_CENTER | wx.ALL)
        sizer2.Add(label_chat, border=5, flag=wx.TOP | wx.LEFT)
        sizer2.Add(splitter_diff, proportion=1, flag=wx.GROW)

        sizer.AddSpacer(10)
        sizer.Add(splitter, border=5, proportion=1, flag=wx.GROW | wx.ALL)
        splitter_diff.SetSashGravity(0.5)
        splitter_diff.SplitVertically(panel_stc1, panel_stc2)
        splitter.SplitHorizontally(
            panel1, panel2, sashPosition=self.Size[1] / 3
        )


    def create_page_merge_contacts(self, notebook):
        """Creates a page for seeing and merging differing contacts."""
        page = self.page_merge_contacts = wx.Panel(parent=notebook)
        notebook.AddPage(page, "Contacts")
        sizer = page.Sizer = wx.BoxSizer(wx.VERTICAL)

        splitter = self.splitter = wx.SplitterWindow(
            parent=page, style=wx.BORDER_NONE
        )
        splitter.SetMinimumPaneSize(1)
        panel1 = wx.Panel(parent=splitter)
        panel2 = wx.Panel(parent=splitter)
        sizer1 = panel1.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer2 = panel2.Sizer = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(parent=page, label="&Differing contacts:")
        list1 = self.list_contacts1 = controls.SortableListView(
            parent=panel1, size=(700, 300), style=wx.LC_REPORT
        )
        self.Bind(
            wx.EVT_LIST_ITEM_SELECTED, self.on_select_list_contacts, list1
        )
        self.Bind(
            wx.EVT_LIST_ITEM_DESELECTED, self.on_select_list_contacts, list1
        )
        list2 = self.list_contacts2 = controls.SortableListView(
            parent=panel2, size=(700, 300), style=wx.LC_REPORT
        )
        self.Bind(
            wx.EVT_LIST_ITEM_SELECTED, self.on_select_list_contacts, list2
        )
        self.Bind(
            wx.EVT_LIST_ITEM_DESELECTED, self.on_select_list_contacts, list2
        )

        button1 = self.button_merge_contacts1 = wx.Button(parent=panel1,
            label="Merge selected contact(s) to database on the right >>>"
        )
        button2 = self.button_merge_contacts2 = wx.Button(parent=panel2,
            label="<<< Merge selected contact(s) to database on the left"
        )
        button_all1 = self.button_merge_allcontacts1 = wx.Button(parent=panel1,
            label="Merge all contacts to database on the right >>>"
        )
        button_all2 = self.button_merge_allcontacts2 = wx.Button(parent=panel2,
            label="<<< Merge all contacts to database on the left"
        )
        button1.Bind(wx.EVT_BUTTON, self.on_merge_contacts)
        button2.Bind(wx.EVT_BUTTON, self.on_merge_contacts)
        button_all1.Bind(wx.EVT_BUTTON, self.on_merge_contacts)
        button_all2.Bind(wx.EVT_BUTTON, self.on_merge_contacts)
        button1.Enabled = button2.Enabled = False
        button_all1.Enabled = button_all2.Enabled = False
        sizer1.Add(list1, proportion=1, flag=wx.GROW)
        sizer1.Add(button1, border=5, flag=wx.ALIGN_CENTER | wx.ALL)
        sizer1.Add(button_all1, border=5, flag=wx.ALIGN_CENTER | wx.ALL)
        sizer2.Add(list2, proportion=1, flag=wx.GROW)
        sizer2.Add(button2, border=5, flag=wx.ALIGN_CENTER | wx.ALL)
        sizer2.Add(button_all2, border=5, flag=wx.ALIGN_CENTER | wx.ALL)

        splitter.SplitVertically(
            panel1, panel2, sashPosition=self.Size.width / 2
        )

        sizer.AddSpacer(10)
        sizer.Add(label, border=5, flag=wx.BOTTOM | wx.LEFT)
        sizer.Add(splitter,
            proportion=1, border=5, flag=wx.GROW | wx.LEFT | wx.RIGHT
        )


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
        if chat:
            self.on_change_list_chats(chat=chat)
            self.notebook.SetSelection(0)


    def on_scan_all_result(self, event):
        """
        Handler for getting results from diff thread, adds the results to
        the diff windows.
        """
        result = event.result
        for i in range(2):
            self.diffresults_html[i] += result["htmls"][i]
            self.chats_differing[i].extend(result["chats"][i])
            html = [self.html_results1, self.html_results2][i]
            html.Freeze()
            scrollpos = html.GetScrollPos(wx.VERTICAL)
            html.SetPage(self.diffresults_html[i])
            html.Scroll(0, scrollpos)
            html.Thaw()
        if "done" in result:
            main.logstatus("Found %s in %s and %s in %s.",
                util.plural("differing chat", len(self.chats_differing[0])),
                self.db1,
                util.plural("differing chat", len(self.chats_differing[1])),
                self.db2
            )
            self.button_mergeall1.Enabled = \
                len(self.chats_differing[0]) or len(self.con1diff) \
                or len(self.congroup1diff)
            self.button_mergeall2.Enabled = \
                len(self.chats_differing[1]) or len(self.con2diff) \
                or len(self.congroup2diff)
            self.button_swap.Enabled = True


    def on_scan_all_callback(self, result):
        """Callback function for DiffThread, posts the data to self."""
        wx.PostEvent(self, WorkerEvent(result=result))


    def on_swap(self, event):
        """
        Handler for clicking to swap left and right databases, changes data
        structures and UI content.
        """
        self.db1, self.db2 = self.db2, self.db1
        self.html_dblabel.SetPage(
            "Database %s"
            " vs %s:" % (export.htmltag("a",
                            {"href": self.db1.filename}, self.db1.filename),
                         export.htmltag("a",
                            {"href": self.db2.filename}, self.db2.filename)
            )
        )
        self.html_dblabel.BackgroundColour = self.BackgroundColour
        self.con1diff, self.con2diff = self.con2diff, self.con1diff
        self.con1difflist, self.con2difflist = \
            self.con2difflist, self.con1difflist
        self.congroup1diff, self.congroup2diff = \
            self.congroup1diff, self.congroup2diff
        # Swap search-related objects and data

        for name in ["stc_diff", "html_results", "label_chat_db", "label_all"]:
            # Move controls from the left to the right and vice versa.
            o1, o2 = getattr(self, name + "1"), getattr(self, name + "2")
            if isinstance(o1, wx.StaticText):
                o1.Label, o2.Label = o2.Label, o1.Label
            else:
                sizer1, sizer2 = o1.ContainingSizer, o2.ContainingSizer
                parent1, parent2 = o1.Parent, o2.Parent
                o1index = sizer1.GetItemIndex(o1)
                o2index = sizer2.GetItemIndex(o2)
                sizer1.Remove(o1index)
                if sizer1 == sizer2:
                    o2index -= 1
                sizer2.Remove(o2index)
                if parent1 != parent2:
                    o1.Reparent(parent2)
                    o2.Reparent(parent1)
                if sizer1 == sizer2:
                    o2index += 1
                sizer1.Insert(o1index, o2, proportion=1, flag=wx.GROW)
                sizer2.Insert(o2index, o1, proportion=1, flag=wx.GROW)
                setattr(self, name + "1", o2)
                setattr(self, name + "2", o1)

        for lst in filter(None, [self.compared, self.con1diff, self.con2diff,
        self.congroup1diff, self.congroup2diff]):
            for item in lst:
                for t in ["c", "messages", "g"]:
                    # Swap left and right in data structures.
                    # @todo make a better structure, allowing a single change.
                    if "%s1" % t in item and "%s2" % t in item:
                        item["%s1" % t], item["%s2" % t] = \
                            item["%s2" % t], item["%s1" % t]
        if self.chats_differing:
            self.chats_differing = self.chats_differing[::-1]
        if self.diffresults_html:
            self.diffresults_html = self.diffresults_html[::-1]

        if self.con1difflist is not None:
            self.list_contacts1.Populate(
                self.contacts_column_map, self.con1difflist
            )
        if self.con2difflist is not None:
            self.list_contacts2.Populate(
                self.contacts_column_map, self.con2difflist
            )
        if self.compared is not None:
            self.list_chats.Populate(self.chats_column_map, self.compared)
            for i, c in enumerate(self.compared):
                if self.DIFFSTATUS_IDENTICAL == c["diff_status"]:
                    self.list_chats.SetItemTextColour(
                        i, conf.DiffIdenticalColour
                    )
            self.list_chats.SortListItems(3, 0) # Sort by last message in left
            self.list_chats.OnSortOrderChanged()
        # Swap button states
        for i in ["all", "_chat_", "_contacts", "_allcontacts"]:
            n = "button_merge%s" % i
            b1, b2 = getattr(self, "%s1" % n), getattr(self, "%s2" % n)
            b1.Enabled, b2.Enabled = b2.Enabled, b1.Enabled
        self.Refresh()
        self.page_merge_all.Layout()
        self.Layout()


    def on_link_db(self, event):
        """Handler on clicking a database link, opens the database tab."""
        self.TopLevelParent.load_database_page(event.GetLinkInfo().Href)


    def on_select_list_contacts(self, event):
        list_source = event.EventObject
        button_target = self.button_merge_contacts1
        if list_source is self.list_contacts2:
            button_target = self.button_merge_contacts2
        button_target.Enabled = list_source.SelectedItemCount > 0


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
            #print url, url_range
            webbrowser.open(url)


    def on_change_list_chats(self, event=None, chat=None):
        """
        Handler for activating an item in the differing chats list,
        goes through all messages of the chat in both databases and shows
        those messages that are missing or different, for both left and
        right.
        """
        c = chat if event is None \
            else self.list_chats._data_map.get(event.Data, None)
        if not self.chat_diff or c["identity"] != self.chat_diff["identity"]:
            self.label_merge_chat.Label = "Messages different in %s:" \
                % c["title_long_lc"]
            self.label_chat_db1.Label = self.db1.filename
            self.label_chat_db2.Label = self.db2.filename
            scrollpos = self.list_chats.GetScrollPos(wx.VERTICAL)
            index_selected = -1
            for i in range(self.list_chats.ItemCount):
                if self.list_chats.GetItemMappedData(i) == self.chat_diff:
                    self.list_chats.SetItemBackgroundColour(
                        i, self.list_chats.BackgroundColour
                    )
                elif self.list_chats.GetItemMappedData(i) == c:
                    index_selected = i
                    self.list_chats.SetItemBackgroundColour(
                        i, conf.ListOpenedBgColour
                    )
            if index_selected >= 0:
                delta = index_selected - scrollpos
                if delta < 0 or abs(delta) >= self.list_chats.CountPerPage:
                    nudge = -self.list_chats.CountPerPage / 2
                    self.list_chats.ScrollLines(delta + nudge)
            busy = controls.ProgressPanel(self,
                "Diffing messages for %s." % c["title_long_lc"]
            )

            diff = self.worker_diff.get_chat_diff(c, self.db1, self.db2)
            self.chat_diff = c
            self.chat_diff_data = diff
            self.button_merge_chat_1.Enabled = len(diff["messages"][0])
            self.button_merge_chat_2.Enabled = len(diff["messages"][1])
            busy.Close()

            self.stc_diff1.Populate(c, self.db1, diff["messages"][0])
            self.stc_diff2.Populate(c, self.db2, diff["messages"][1])


    def on_merge_contacts(self, event):
        """
        Handler for clicking to merge contacts from one database to the other,
        either selected or all contacts, depending on button clicked.
        """
        button = event.EventObject
        db_target, db_source = self.db2, self.db1
        list_source = self.list_contacts1
        source = 0
        if button in \
        [self.button_merge_allcontacts2, self.button_merge_contacts2]:
            db_target, db_source = self.db1, self.db2
            list_source = self.list_contacts2
            source = 1
        button_all = [
            self.button_merge_allcontacts1, self.button_merge_allcontacts2
        ][source]
        contacts, contactgroups, indices = [], [], []
        if button is button_all:
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
        contacts_target_final.update(
            dict([(c["identity"], c) for c in db_target.get_contacts()])
        )
        contacts_source = dict([(c['identity'], c)
            for c in db_source.get_contacts()
        ])
        for group in contactgroups:
            members = set(group["members"].split(" "))
            for new in members.difference(contacts_target_final):
                contacts.append(contacts_source[new])
        text_add = ""
        if contacts:
            text_add += util.plural("contact", len(contacts))
        if contactgroups:
            text_add += (" and " if contacts else "") \
                       + util.plural("contact group", len(contactgroups))
        if (contacts or contactgroups) and wx.OK == wx.MessageBox(
                "Copy %s\nfrom %s\ninto %s?" % (text_add, self.db1, self.db2),
                conf.Title, wx.OK | wx.CANCEL | wx.ICON_QUESTION):
            if contacts:
                db_target.insert_contacts(contacts)
            if contactgroups:
                db_target.replace_contactgroups(contactgroups)
            #for i in range(len(indices)):
            for i in sorted(indices)[::-1]:
                # - i, as item count is getting smaller one by one
                #item = indices[i] - i
                #list_source.DeleteItem(item)
                list_source.DeleteItem(i)
            condiff = [self.con1diff, self.con2diff][source]
            cgdiff = [self.congroup1diff, self.congroup1diff][source]
            difflist = [self.con1difflist, self.con1difflist][source]
            for c in [contacts, contactgroups]:
                [l.remove(c) for l in [condiff, cgdiff, difflist] if c in l]
            button_all.Enabled = list_source.ItemCount > 0
            db_target.clear_cache()
            wx.MessageBox("Copied %s\nfrom %s\ninto %s?" % (text_add,
                self.db1, self.db2), conf.Title, wx.OK | wx.ICON_INFORMATION
            )


    def on_scan_all(self, event):
        """
        Handler for clicking to scan all differences to copy to the other
        database, collects the data and loads it to screen.
        """
        main.logstatus("Scanning differences between %s and %s.",
            self.db1, self.db2
        )
        self.chats_differing = [[], []]
        self.diffresults_html = ["", ""]
        self.button_scan_all.Enabled = False
        self.button_swap.Enabled = False
        for i in range(2):
            contacts = [self.con1diff, self.con2diff][i]
            if contacts:
                text = "%s: %s.<br />" % (
                    util.plural("new contact", len(contacts)),
                    ", ".join(sorted([c["name"] for c in contacts]))
                )
                self.diffresults_html[i] += text
                h = [self.html_results1, self.html_results2][i]
                h.SetPage(text)
        self.worker_diff.work({"db1": self.db1, "db2": self.db2})


    def on_merge_all(self, event):
        """
        Handler for clicking to copy all the differences to the other
        database, asks for final confirmation and executes.
        """
        source = 0 if event.EventObject == self.button_mergeall1 else 1
        db1 = [self.db1, self.db2][source]
        db2 = [self.db1, self.db2][1 - source]
        chats  = self.chats_differing[source]
        contacts = [self.con1diff, self.con2diff][source]
        contactgroups = [self.congroup1diff, self.congroup2diff][source]
        # Contacts and contact groups are shown in the same list. If a contact
        # group is chosen, it can include contacts not yet in target database.
        contacts_target_final = dict([(c["identity"], c) for c in contacts])
        contacts_target_final.update(
            dict([(c["identity"], c) for c in db2.get_contacts()])
        )
        contacts_source = dict([(c['identity'], c)
            for c in db1.get_contacts()
        ])
        for group in contactgroups:
            members = set(group["members"].split(" "))
            for new in members.difference(contacts_target_final):
                contacts.append(contacts_source[new])
        info = ""
        if chats:
            info += util.plural("chat", len(chats))
        if contacts:
            info += (" and " if info else "") \
                 + util.plural("contact", len(contacts))
        if contactgroups:
            info += (" and " if info else "") \
                 + util.plural("contact group", len(contactgroups))
        proceed = wx.MessageBox(
            "Copy data of %s\nfrom %s\ninto %s?" % (info, db1, db2),
            conf.Title, wx.OK | wx.CANCEL | wx.ICON_QUESTION
        ) == wx.OK
        if proceed:
            busy = controls.ProgressPanel(
                self, "Merging %s\nfrom %s\nto %s." % (info, db1, db2)
            )
            wx.GetApp().Yield(True) # Allow UI to refresh
            main.logstatus("Merging %s from %s to %s.", info, db1, db2)
            event.EventObject.Enabled = False
            self.Refresh()
            count_messages = 0
            count_participants = 0
            if contacts:
                db2.insert_contacts(contacts)
            if contactgroups:
                db2.replace_contactgroups(contactgroups)
            for chat_data in chats:
                chat  = chat_data["chat"]["c2" if source else "c1"]
                chat2 = chat_data["chat"]["c1" if source else "c2"]
                messages, messages2 = \
                    chat_data["diff"]["messages"][::[1, -1][source]]
                participants, participants2 = \
                    chat_data["diff"]["participants"][::[1, -1][source]]
                if not chat2:
                    chat2 = chat.copy()
                    chat_data["chat"]["c1" if source else "c2"] = chat2
                    chat2["id"] = db2.insert_chat(chat2, db1)
                if (participants):
                    db2.insert_participants(chat2, participants)
                    count_participants += len(participants)
                if (messages):
                    db2.insert_messages(chat2, messages, db1, chat)
                    count_messages += len(messages)
            if chats:
                if count_participants:
                    info += (" and " if info else "") + \
                            util.plural("participant", count_participants)
                if count_messages:
                    info += (" and " if info else "") \
                        + util.plural("message", count_messages)
            db2.clear_cache()
            main.logstatus("Merged %s from %s to %s.", info, db1, db2)
            [self.html_results1, self.html_results2][source].SetPage("")
            busy.Close()
            wx.MessageBox("Copied %s\nfrom %s\ninto %s." % (
                    info, db1, db2
                ), conf.Title, wx.OK | wx.ICON_INFORMATION
            )
            self.list_chats.ClearAll()
            self.list_contacts1.ClearAll()
            self.list_contacts2.ClearAll()
            self.label_merge_chat.Label = ""
            self.label_chat_db1.Label = ""
            self.label_chat_db2.Label = ""
            self.chat_diff = None
            for s in [self.stc_diff1, self.stc_diff2]:
                s.SetReadOnly(False)
                s.ClearAll()
                s.SetReadOnly(True)
            later = threading.Thread(target=self.load_later_data)
            wx.CallLater(20, later.start)



    def on_merge_chat(self, event):
        """
        Handler for clicking to merge a chat from either side db to the other
        side db.
        """
        source = 0 if (self.button_merge_chat_1 == event.EventObject) else 1
        db1 = [self.db1, self.db2][source]
        db2 = [self.db1, self.db2][1 - source]
        chats_differing = self.chats_differing[source] \
                          if self.chats_differing else []
        chat  = [self.chat_diff["c1"], self.chat_diff["c2"]][source]
        chat2 = [self.chat_diff["c1"], self.chat_diff["c2"]][1 - source]
        messages, messages2 = \
            self.chat_diff_data["messages"][::[1, -1][source]]
        participants, participants2 = \
            self.chat_diff_data["participants"][::[1, -1][source]]
        condiff = [self.con1diff, self.con2diff][source]
        stc = [self.stc_diff1, self.stc_diff2][source]
        contacts2 = []

        if messages or participants:
            info = ""
            parts = []
            new_chat = not chat2
            newstr = "" if new_chat else "new "
            if new_chat:
                info += "new chat with "
            if messages:
                parts.append(util.plural("%smessage" % newstr, len(messages)))
            if participants:
                # Add to contacts those that are new
                cc2 = [db1.id, db2.id] + \
                    [i["identity"] for i in db2.get_contacts()]
                contacts2 = [i["contact"] for i in participants
                    if "id" in i["contact"] and i["identity"] not in cc2]
                if contacts2:
                    parts.append(util.plural("new contact", len(contacts2)))
                parts.append(util.plural("%sparticipant" % newstr,
                    len(participants)
                ))
            for i in parts:
                info += ("" if i == parts[0] else (
                    " and " if i == parts[-1] else ", "
                )) + i

            proceed = wx.OK == wx.MessageBox(
                "Copy %s\nfrom %s\ninto %s?" % (info, db1, db2),
                conf.Title, wx.OK | wx.CANCEL | wx.ICON_QUESTION
            )
            if proceed:
                if not chat2:
                    chat2 = chat.copy()
                    self.chat_diff["c1" if source else "c2"] = chat2
                    chat2["id"] = db2.insert_chat(chat2, db1)
                if (participants):
                    if contacts2:
                        db2.insert_contacts(contacts2)
                    for p in participants:
                        if p in condiff:
                            condiff.remove(p)
                    db2.insert_participants(chat2, participants)
                    del participants[:]
                if (messages):
                    db2.insert_messages(chat2, messages, db1, chat)
                    del messages[:]
                for c in chats_differing:
                    if c["chat"]["c2"]["id"] == chat["id"]:
                        chats_differing.remove(c)
                db2.clear_cache()
                stc.ReadOnly = False
                stc.ClearAll()
                stc.ReadOnly = True
                event.EventObject.Enabled = False
                main.logstatus("Merged %s of chat \"%s\" from %s to %s." % (
                    info, chat2["title"], db1, db2
                ))
                # Update chat list
                db2.get_conversations_stats([chat2])
                self.chat_diff["messages%s" % (1 - source + 1)] = \
                    chat2["message_count"]
                self.chat_diff["last_message_datetime%s" % (source + 1)] = \
                    chat2["last_message_datetime"]
                if not (messages2 or participants2):
                    for i in range(self.list_chats.ItemCount):
                        if self.list_chats.GetItemMappedData(i) \
                        == self.chat_diff:
                            self.list_chats.SetItemBackgroundColour(
                                i, self.list_chats.BackgroundColour
                            )
                self.list_chats.RefreshItems()
                stc.SetReadOnly(False), stc.ClearAll(), stc.SetReadOnly(True)
                infomsg = "Merged %s of chat \"%s\"\nfrom %s\nto %s." % (
                    info, chat2["title"], db1, db2
                )
                wx.MessageBox(infomsg, conf.Title, wx.OK | wx.ICON_INFORMATION)


    def load_data(self):
        """Loads data from our SkypeDatabases."""
        self.html_dblabel.SetPage(
            "Database %s"
            " vs %s:" % (export.htmltag("a",
                            {"href": self.db1.filename}, self.db1.filename),
                         export.htmltag("a",
                            {"href": self.db2.filename}, self.db2.filename)
            )
        )
        self.html_dblabel.BackgroundColour = self.BackgroundColour

        # Populate the chat comparison list
        chats1 = self.db1.get_conversations()
        chats2 = self.db2.get_conversations()
        c1map = dict((c["identity"], c) for c in chats1)
        c2map = dict((c["identity"], c) for c in chats2)
        compared = []
        for c1 in chats1:
            c1["c1"], c1["c2"] = c1.copy(), c2map.get(c1["identity"], None)
            compared.append(c1)
        for c2 in chats2:
            if c2["identity"] not in c1map:
                c2["c1"], c2["c2"] = None, c2.copy()
                compared.append(c2)
        for c in compared:
            c["last_message_datetime1"] = c["last_message_datetime2"] = None
            c["messages1"] = c["messages2"] = None
            c["diff_status"] = None

        self.list_chats.Populate(self.chats_column_map, compared)
        self.list_chats.SortListItems(3, 0) # Sort by last message in left
        self.list_chats.OnSortOrderChanged()
        self.compared = compared
        wx.CallLater(50, threading.Thread(target=self.load_later_data).start)


    def load_later_data(self):
        """
        Loads later data from the databases, like message counts and compared
        contacts, used as a background callback to speed up page opening.
        """
        try:
            chats1 = self.db1.get_conversations()
            chats2 = self.db2.get_conversations()
            self.db1.get_conversations_stats(chats1)
            self.db2.get_conversations_stats(chats2)
            c1map = dict((c["identity"], c) for c in chats1)
            c2map = dict((c["identity"], c) for c in chats2)
            for c in self.compared:
                for i in range(2):
                    cmap = c2map if i else c1map
                    if c["c%s" % (i + 1)] and c["identity"] in cmap:
                        c["messages%s" % (i + 1)] = \
                            cmap[c["identity"]]["message_count"]
                        c["last_message_datetime%s" % (i + 1)] = \
                            cmap[c["identity"]]["last_message_datetime"]
                c["diff_status"] = self.DIFFSTATUS_DIFFERENT
                identical = False
                if c["c1"] and c["c2"]:
                    identical = (c["messages1"] == c["messages2"])
                    identical &= (c["last_message_datetime1"] \
                        == c["last_message_datetime2"]
                    )
                if identical:
                    c["diff_status"] = self.DIFFSTATUS_IDENTICAL

            self.list_chats.Enabled = True
            self.list_chats.Populate(self.chats_column_map, self.compared)
            for i, c in enumerate(self.compared):
                if self.DIFFSTATUS_IDENTICAL == c["diff_status"]:
                    self.list_chats.SetItemTextColour(
                        i, conf.DiffIdenticalColour
                    )
            self.list_chats.SortListItems(3, 0) # Sort by last message in left
            self.list_chats.OnSortOrderChanged()

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
                c2 = con2map.get(c1["identity"], None)
                if not c2 and c1["identity"] not in con1new:
                    c = c1.copy()
                    c["c1"] = c1
                    c["c2"] = c2
                    con1diff.append(c)
                    con1new[c1["identity"]] = True
            for c2 in contacts2:
                c1 = con1map.get(c2["identity"], None)
                if not c1 and c2["identity"] not in con2new:
                    c = c2.copy()
                    c["c1"] = c1
                    c["c2"] = c2
                    con2diff.append(c)
                    con2new[c2["identity"]] = True
            for g1 in contactgroups1:
                g2 = cg2map.get(g1["name"], None)
                if not g2 or g2["members"] != g1["members"]:
                    g = g1.copy()
                    g["g1"] = g1
                    g["g2"] = g2
                    cg1diff.append(g)
            for g2 in contactgroups2:
                g1 = cg1map.get(g2["name"], None)
                if not g1 or g1["members"] != g2["members"]:
                    g = g2.copy()
                    g["g1"] = g1
                    g["g2"] = g2
                    cg2diff.append(g)
            dummy = {"__type": "Group", "phone_mobile_normalized": "",
                "country": "", "city": "", "about": "About"}
            con1difflist = [c.copy() for c in con1diff]
            [c.update({"__type": "Contact","__data": c}) for c in con1difflist]
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
            self.list_contacts1.Populate(self.contacts_column_map,con1difflist)
            self.list_contacts2.Populate(self.contacts_column_map,con2difflist)
            self.button_merge_allcontacts1.Enabled = len(con1difflist) > 0
            self.button_merge_allcontacts2.Enabled = len(con2difflist) > 0
            self.con1diff = con1diff
            self.con2diff = con2diff
            self.con1difflist = con1difflist
            self.con2difflist = con2difflist
            self.congroup1diff = cg1diff
            self.congroup2diff = cg2diff

            for i in range(2):
                db = self.db2 if i else self.db1
                tables = db.get_tables()
                transfers = 0
                if tables:
                    for t in tables:
                        if "transfers" == t["name"].lower():
                            transfers = t["rows"]
                            break
                condiff = self.con2diff if i else self.con1diff
                contacts = contacts2 if i else contacts1
                label = self.label_all2 if i else self.label_all1
                label.Label = \
                    "%s.\n\nSize %s.\nLast modified %s.\n" % (
                        db, util.format_bytes(db.filesize),
                        db.last_modified.strftime("%Y-%m-%d %H:%M:%S"),
                    )
                chats = chats2 if i else chats1
                if chats:
                    t1 = filter(None, [c["message_count"] for c in chats])
                    count_messages = sum(t1) if t1 else 0
                    t2 = filter(
                         None, [c["first_message_datetime"] for c in chats])
                    datetime_first = min(t2) if t2 else None
                    t3 = filter(
                         None, [c["last_message_datetime"] for c in chats])
                    datetime_last = max(t3) if t3 else None
                    datetext_first = "" if not datetime_first \
                        else datetime_first.strftime("%Y-%m-%d %H:%M:%S")
                    datetext_last = "" if not datetime_last \
                        else datetime_last.strftime("%Y-%m-%d %H:%M:%S")
                    label.Label += "%s.\n%s.\nFirst message at %s.\n" \
                        "Last message at %s.\n%s" % (
                            util.plural("conversation", len(chats)),
                            util.plural("message", count_messages), 
                            datetext_first, datetext_last,
                            util.plural("contact", len(contacts)), 
                        )
                    if condiff:
                        label.Label += " (%d not present on the %s)" % (
                            len(condiff), ["right", "left"][i]
                        )
                    label.Label += ".\n%s." % (
                        util.plural("file transfer", transfers),
                    )
        except Exception, e:
            # Database access can easily fail if the user closes the tab before
            # the later data has been loaded.
            if self:
                main.log("Error accessing database %s or %s.\n%s",
                    self.db1, self.db2, traceback.format_exc()
                )
        if self:
            self.page_merge_all.Layout()
            self.button_swap.Enabled = True
            self.button_close.Enabled = True
            if self.chats_differing is None:
                self.button_scan_all.Enabled = True
            main.status("Opened Skype databases %s and %s.",
                self.db1, self.db2
            )
            self.Refresh()


    def on_close(self, event):
        """
        Handler for clicking to close the page, closes the database and removes
        the page.
        """
        self.db1.unregister_consumer(self)
        self.db2.unregister_consumer(self)
        self.worker_diff.stop()
        self.worker_diff.join()
        self.Close()



class ChatContentSTC(controls.SearchableStyledTextCtrl):
    """A StyledTextCtrl for showing and filtering chat messages."""

    def __init__(self, *args, **kwargs):
        controls.SearchableStyledTextCtrl.__init__(self, *args, **kwargs)
        self.SetUndoCollection(False)

        self._chat = None       # Currently shown chat
        self._db = None         # Database for currently shown messages
        self._messages = None   # All retrieved messages (collections.deque)
        self._messages_current = None  # Currently shown (collections.deque)
        self._message_positions = {} # {msg id: (start index, end index)}
        # If set, range is centered around the message with the specified ID
        self._center_message_id =    -1
        # Index of the centered message in _messages
        self._center_message_index = -1
        # Word cloud from message texts [("word", count, fontsize), ]
        self._wordcloud = []
        self._stats = {}     # Statistics assembled for current content
        self._filelinks = {} # {link end position: file path}
        # Currently set message filter {"daterange": (datetime, datetime),
        # "text": text in message, "participants": [skypename1, ],
        # "message_id": message ID to show, range shown will be centered
        # around it}
        self._filter = {}
        self._filtertext_rgx = None # Cached regex for filter["text"]

        self._styles = {"default": 10, "bold": 11, "timestamp": 12,
            "remote": 13, "local": 14, "link": 15, "tiny": 16,
            "special": 17, "bolddefault": 18, "boldlink": 19, "boldspecial": 20
        }
        stylespecs = {
            "default":      "face:%s,size:%d,fore:%s" % (
                conf.HistoryFontName, conf.HistoryFontSize,
                conf.HistoryDefaultColour
             ),
             "bolddefault": "face:%s,size:%d,fore:%s,bold" % (
                conf.HistoryFontName, conf.HistoryFontSize,
                conf.HistoryDefaultColour
             ),
             "bold":        "face:%s,bold" % conf.HistoryFontName,
             "timestamp":   "fore:%s" % conf.HistoryTimestampColour,
             "remote":      "face:%s,bold,fore:%s" % (conf.HistoryFontName,
                conf.HistoryRemoteAuthorColour
             ),
            "local":        "face:%s,bold,fore:%s" % (conf.HistoryFontName,
                conf.HistoryLocalAuthorColour
            ),
            "link":         "fore:%s" % conf.HistoryLinkColour,
            "boldlink":     "face:%s,bold,fore:%s" % (conf.HistoryFontName,
                conf.HistoryLinkColour
            ),
            "tiny":         "size:1",
            "special":      "fore:%s" % conf.HistoryGreyColour,
            "boldspecial":  "face:%s,bold,fore:%s" % (conf.HistoryFontName,
                conf.HistoryGreyColour
            )
        }
        self.StyleSetSpec(wx.stc.STC_STYLE_DEFAULT, stylespecs["default"])
        for style, spec in stylespecs.items():
            self.StyleSetSpec(self._styles[style], spec)
        self.StyleSetHotSpot(self._styles["link"], True)
        self.StyleSetHotSpot(self._styles["boldlink"], True)
        self.SetWrapMode(True)
        self.SetMarginLeft(10)
        self.SetReadOnly(True)
        self.Bind(wx.stc.EVT_STC_HOTSPOT_CLICK, self.OnUrl)
        # Hide caret
        self.SetCaretForeground("white")
        self.SetCaretWidth(0)


    def OnUrl(self, event):
        """
        Handler for clicking a link in chat history, opens the link in system
        browser.
        """
        stc = event.EventObject
        styles_link = [self._styles["link"], self._styles["boldlink"]]
        if stc.GetStyleAt(event.Position) in styles_link:
            # Go back and forth from position and get URL range.
            url_range = {-1: -1, 1: -1} # { start and end positions }
            for step in url_range:
                pos = event.Position
                while stc.GetStyleAt(pos + step) in styles_link:
                    pos += step
                url_range[step] = pos
            url_range[1] += 1
            url = stc.GetTextRange(url_range[-1], url_range[1])
            if url_range[-1] in self._filelinks:
                def start_file(url):
                    if os.path.exists(url):
                        os_handler.start_file(url)
                    else:
                        messageBox(
                            "The file \"%s\" cannot be found " \
                            "on this computer." % url,
                            conf.Title, wx.OK | wx.ICON_INFORMATION
                        )
                url = self._filelinks[url_range[-1]]
                # Launching an external program here will cause STC to lose
                # MouseUp, resulting in autoselect mode from click position.
                wx.CallAfter(start_file, url)
            elif url:
                # Launching an external program here will cause STC to lose
                # MouseUp, resulting in autoselect mode from click position.
                wx.CallAfter(webbrowser.open, url)
        event.StopPropagation()


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
            m_iter = None
            if not self._messages[0]["datetime"] \
            or self._messages[0]["datetime"].date() \
            >= self._filter["daterange"][0]:
                m_iter = self._db.get_messages(self._chat,
                    ascending=False,
                    timestamp_from=self._messages[0]["timestamp"]
                )
            m = None
            notice_added = False
            while m_iter:
                try:
                    if m and not notice_added:
                        self.SetReadOnly(False) # Can't modify while read-only
                        self.AppendTextUTF8("Retrieving more messages..\n")
                        self.SetReadOnly(True)
                        #main.log(
                        #    "Conversation \"%s\": retrieving more messages.",
                        #    self._chat["title_long"]
                        #)
                        #wx.GetApp().Yield(True) # Allow UI to refresh
                        notice_added = True
                    m = m_iter.next()
                    self._messages.appendleft(m)
                    if m["datetime"].date() < self._filter["daterange"][0]:
                        m_iter = None
                except StopIteration, e:
                    m_iter = None


    def RefreshMessages(self, center_message_id=None):
        """
        Clears content and redisplays messages of current chat.

        @param   center_message_id  if specified, message with the ID is
                                    focused and message range will center
                                    around it, staying withing max number
        """
        self.SetReadOnly(False) # Can't modify while read-only
        self.ClearAll()
        self.SetReadOnly(True)
        del self._wordcloud[:]
        self._stats.clear()
        if self._messages:
            self.RetrieveMessagesIfNeeded()
            self.SetReadOnly(False) # Can't modify while read-only
            self.AppendText("Formatting messages..\n")
            self.SetReadOnly(True)
            #wx.GetApp().Yield(True) # Allow UI to refresh
            self.Refresh()
            self.Freeze()
            self.SetReadOnly(False) # Can't modify while read-only
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
            previous_day = datetime.date.fromtimestamp(0)
            count = 0
            focus_message_id = None
            transfers = self._db.get_transfers()
            self._filelinks.clear()
            # For accumulating various statistics
            texts = {"cloud": "", "links": [], "message": ""}
            stats = {"smses": 0, "transfers": [], "calls": 0, "messages": 0,
                "counts": {}, "total": 0, "startdate": None, "enddate": None
            }
            rgx_highlight = re.compile(
                "(%s)" % re.escape(self._filter["text"]), re.I
            ) if ("text" in self._filter and self._filter["text"]) else None
            self._messages_current = collections.deque()
            parser = skypedata.MessageParser(self._db)

            def write_element(dom, data, tails_new=None):
                """
                Appends the message body to the StyledTextCtrl.

                @param   dom        xml.etree.cElementTree.Element instance
                @param   data       {"links": [], "cloud": str, "message": str}
                @param   tails_new  internal use, {element: modified tail str}

                """
                tagstyle_map = {
                    "a": "link", "b": "bold", "quotefrom": "special"
                }
                to_skip = {} # {element to skip: True, }
                parent_map = dict(
                    (c, p) for p in dom.getiterator() for c in p
                )
                tails_new = {} if tails_new is None else tails_new
                linefeed_final = "\n\n" # Decreased if quotefrom is last
                for e in dom.getiterator():
                    # Possible tags: a|b|quote|quotefrom|msgstatus|special|xml
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
                        data["links"].append(text)
                        data["message"] += text + " "
                        href = e.get("href")
                        if href.startswith("file:"):
                            self._filelinks[self._stc.Length] = \
                                urllib.url2pathname(e.get("href")[5:])
                        linefeed_final = "\n\n"
                    elif "quote" == e.tag:
                        text = "\"" + text
                        data["cloud"] += text + " "
                        data["message"] += text + " "
                        children = e.getchildren()
                        if len(children) > 1:
                            # Last element is always quotefrom
                            tails_new[children[-2]] = (children[-2].tail \
                                if children[-2].tail else "" \
                            ) + "\""
                        else:
                            text += "\""
                        linefeed_final = "\n"
                    elif "quotefrom" == e.tag:
                        text = "\n%s\n" % text
                        data["message"] += text + " "
                    elif e.tag in ["xml", "b"]:
                        data["cloud"] += text + " "
                        data["message"] += text + " "
                        linefeed_final = "\n\n"
                    else:
                        text = ""
                    if text:
                        self._append_text(text, style, rgx_highlight)
                    for i in children:
                        write_element(i, data, tails_new)
                        to_skip[i] = True
                    if tail:
                        self._append_text(tail, "default", rgx_highlight)
                        data["cloud"] += tail + " "
                        data["message"] += tail + " "
                        linefeed_final = "\n\n"
                if "xml" == dom.tag:
                    self._append_text(linefeed_final)

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
                #if not stats["total"] % 100:
                #    main.log("Conversation "%s": display at %s.",
                #        self._chat["title_long"], stats["total"]
                #    )

                if m["datetime"].date() != previous_day:
                    # Day has changed: insert a date header
                    previous_day = m["datetime"].date()
                    weekday = previous_day.strftime("%A").capitalize()
                    date_formatted = previous_day.strftime("%d. %B %Y")
                    if locale.getpreferredencoding():
                        weekday = weekday.decode(locale.getpreferredencoding())
                        date_formatted = date_formatted.decode(
                            locale.getpreferredencoding()
                        )
                    self._append_text("\n%s" % weekday, "bold")
                    self._append_text(", %s\n\n" % date_formatted)

                dom = parser.parse(m)
                length_before = self._stc.Length
                time_value = m["datetime"].strftime("%H:%M")
                displayname = m["from_dispname"]
                special_text = "" # Special text after name, e.g. " SMS"
                body = m["body_xml"] or ""
                special_tag = dom.find("msgstatus")
                if special_tag is None:
                    self._append_text("%s %s\n" % (time_value, displayname),
                        colourmap[m["author"]]
                    )
                else:
                    self._append_text("%s %s" % (time_value, displayname),
                        colourmap[m["author"]]
                    )
                    self._append_text("%s\n" % special_tag.text, "special")

                texts["message"] = ""
                write_element(dom, texts)

                # Store message position for FocusMessage()
                length_after = self._stc.Length
                self._message_positions[m["id"]] = (
                    length_before, length_after - 2
                )
                if self._center_message_id == m["id"]:
                    focus_message_id = m["id"]

                # Collect statistics
                if m["author"] not in stats["counts"]:
                    stats["counts"][m["author"]] = {"files": 0, "bytes": 0,
                        "messages": 0, "chars": 0, "smses": 0, "smschars": 0,
                        "calls": 0, "calldurations": 0
                    }
                if skypedata.MESSAGES_TYPE_SMS == m["type"]:
                    stats["smses"] += 1
                    stats["counts"][m["author"]]["smses"] += 1
                    stats["counts"][m["author"]]["smschars"] += \
                        len(texts["message"])
                if skypedata.MESSAGES_TYPE_CALL == m["type"]:
                    stats["calls"] += 1
                    stats["counts"][m["author"]]["calls"] += 1
                    #if m["id"] :
                    #    
                    #stats["counts"][m["author"]]["calldurations"] += \
                    #    call["duration"] or 0
                elif skypedata.MESSAGES_TYPE_FILE == m["type"]:
                    files = [i for i in transfers \
                             if i["chatmsg_guid"] == m["guid"]
                    ]
                    if not files and "__files" in m:
                        files = m["__files"]
                    stats["transfers"].extend(files)
                    stats["counts"][m["author"]]["files"] += len(files)
                    stats["counts"][m["author"]]["bytes"] += \
                        sum([int(i["filesize"]) for i in files])
                elif skypedata.MESSAGES_TYPE_MESSAGE == m["type"]:
                    stats["messages"] += 1
                    stats["counts"][m["author"]]["messages"] += 1
                    stats["counts"][m["author"]]["chars"] += \
                        len(texts["message"])
                if not stats["startdate"]:
                    stats["startdate"] = m["datetime"]
                stats["enddate"] = m["datetime"]
                stats["total"] += 1

            if stats["total"]:
                self._stats = stats
            # Assemble word cloud data
            #main.log("Conversation \"%s\", analyzing word cloud.",
            #    self._chat["title_long"]
            #)
            self._wordcloud = wordcloud.get_cloud(
                texts["cloud"], texts["links"]
            )

            # Reset the centered message data, as filtering should override it
            self._center_message_index = -1
            self._center_message_id = -1
            self.SetReadOnly(True)
            if focus_message_id:
                self.FocusMessage(focus_message_id)
            else:
                self.ScrollToLine(self.LineCount)
            #main.log("Conversation \"%s\", showed %s" + (
            #        ", filtered out %s." % (count - stats["total"]) \
            #        if (count != stats["total"]) else "."
            #    ),
            #    self._chat["title_long"],
            #    util.plural("message", stats["total"])
            #)
            self.Thaw()


    def _append_text(self, text, style="default", rgx_highlight=None):
        """
        Appends text to the StyledTextCtrl in the specified style.

        @param   rgx_highlight  if set, substrings matching the regex are added
                                in highlighted style
        """
        text = text or ""
        if type(text) is unicode:
            text = text.encode("utf-8")
        text_parts = rgx_highlight.split(text) if rgx_highlight else [text]
        stc = self._stc
        bold = "bold%s" % style if "bold%s" % style in self._styles else style
        len_self = self.GetTextLength()
        stc.AppendTextUTF8(text)
        stc.StartStyling(pos=len_self, mask=0xFF)
        stc.SetStyling(length=len(text), style=self._styles[style])
        for i, t in enumerate(text_parts):
            if i % 2:
                stc.StartStyling(pos=len_self, mask=0xFF)
                stc.SetStyling(length=len(t), style=self._styles[bold])
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


    def Populate(self, chat, db, messages=None, center_message_id=None):
        """
        Populates the chat history with messages from the specified chat.

        @param   chat           chat data, as returned from SkypeDatabase
        @param   db             SkypeDatabase to use
        @param   messages       messages to show (if set, messages are not
                                retrieved from database)
        @param   center_msg_id  if set, specifies the message around which to
                                center other messages in the shown range
        """
        message_show_limit = conf.MaxHistoryInitialMessages
        if messages:
            message_show_limit = len(messages)

        self.ClearAll()
        self.AppendTextUTF8("Loading messages..\n")
        self.Refresh()
        #wx.GetApp().Yield(True) # Allow UI to refresh
        self._center_message_index = -1
        self._center_message_id = -1

        if messages is not None:
            message_range = collections.deque(messages)
        else:
            #main.log("Conversation \"%s\": retrieving messages.",
            #    chat["title_long"]
            #)
            m_iter = db.get_messages(chat, ascending=False)

            i = 0
            message_range = collections.deque()
            try:
                iterate = (i < message_show_limit)
                while iterate:
                    m = m_iter.next()
                    if m:
                        i += 1
                        # @todo have message_range only contain indices
                        message_range.appendleft(m)
                        if m["id"] == center_message_id:
                            self._center_message_index = len(message_range)
                            self._center_message_id = center_message_id
                    else:
                        break
                    if center_message_id:
                        iterate = (self._center_message_index < 0) or (
                            len(message_range) < self._center_message_index \
                                + message_show_limit / 2
                        )
                    else:
                        iterate = (i < message_show_limit)
            except StopIteration:
                m_iter = None
            if self._center_message_index >= 0:
                self._center_message_index = \
                    len(message_range) - self._center_message_index
            #main.log("Conversation \"%s\": retrieved %s.",
            #    chat["title_long"], util.plural("message", len(message_range))
            #)

        self._chat = chat
        self._db = db
        self._messages_current = message_range
        self._messages = copy.copy(message_range)
        self._calls = db.get_calls(chat)
        self._filter["daterange"] = [
            message_range[0]["datetime"].date() if message_range else None,
            message_range[-1]["datetime"].date() if message_range else None
        ]
        self.RefreshMessages()


    def FocusMessage(self, message_id):
        """Selects and scrolls the specified message into view."""
        if message_id in self._message_positions:
            padding = -50 # So that selection does not finish at visible edge
            for p in self._message_positions[message_id]:
                # Ensure that both ends of the selection are visible
                self._stc.CurrentPos = p + padding
                self.EnsureCaretVisible()
                padding = abs(padding)
            self._stc.SetSelection(*self._message_positions[message_id])


    def IsMessageFilteredOut(self, message):
        """
        Returns whether the specified message does not pass the current filter.
        """
        result = False
        if "participants" in self._filter \
        and self._filter["participants"] \
        and message["author"] not in self._filter["participants"]:
            result = True
        elif "daterange" in self._filter \
        and not (self._filter["daterange"][0] <= message["datetime"].date() \
        <= self._filter["daterange"][1]):
            result = True
        elif "text" in self._filter and self._filter["text"]:
            if not self._filtertext_rgx:
                self._filtertext_rgx = re.compile(re.escape(
                    self._filter["text"]
                ), re.IGNORECASE)
            if not message["body_xml"] \
            or not self._filtertext_rgx.search(message["body_xml"]):
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
        m = self._messages_current[index] if self._messages_current \
                and 0 <= index < len(self._messages_current) \
            else None
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


    def GetStatistics(self):
        """
        Returns statistics for the currently loaded content, as
        [("item", "value"), ].
        """
        return copy.deepcopy(self._stats)


    def GetWordCloud(self):
        """
        Returns the word cloud for currently loaded content,
        in descending order of relevance ["word": fontsize, ].
        """
        return copy.copy(self._wordcloud)



class DayHourDialog(wx.Dialog):
    """Popup dialog for entering two values, days and hours."""

    def __init__(self, parent, message, caption, days, hours):
        wx.Dialog.__init__(self, parent=parent, title=caption, size=(250, 200))

        vbox = self.Sizer = wx.BoxSizer(wx.VERTICAL)

        self.text_days = wx.SpinCtrl(parent=self, style=wx.ALIGN_LEFT,
            size=(200, -1), value=str(days), min=-sys.maxint, max=sys.maxint
        )
        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        hbox1.AddStretchSpacer()
        hbox1.Add(wx.StaticText(parent=self, label="Days:"),
            flag=wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL
        )
        hbox1.Add(self.text_days, border=5, flag=wx.LEFT | wx.ALIGN_RIGHT)

        self.text_hours = wx.SpinCtrl(parent=self, style=wx.ALIGN_LEFT,
            size=(200, -1), value=str(hours), min=-sys.maxint, max=sys.maxint
        )
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        hbox2.AddStretchSpacer()
        hbox2.Add(wx.StaticText(parent=self, label="Hours:"),
            flag=wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL
        )
        hbox2.Add(self.text_hours, border=5, flag=wx.LEFT | wx.ALIGN_RIGHT)

        button_ok = wx.Button(self, label="OK")
        button_cancel = wx.Button(self, label="Cancel", id=wx.ID_CANCEL)
        hbox3 = wx.BoxSizer(wx.HORIZONTAL)
        hbox3.AddStretchSpacer()
        hbox3.Add(button_ok, border=5, flag=wx.RIGHT)
        hbox3.Add(button_cancel, border=5, flag=wx.RIGHT)

        vbox.Add(
            wx.StaticText(parent=self, label=message), border=10, flag=wx.ALL
        )
        vbox.AddSpacer(5)
        vbox.Add(
            hbox1, border=5, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND
        )
        vbox.Add(
            hbox2, border=5, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND
        )
        vbox.Add(wx.StaticLine(self), border=5, proportion=1,
            flag=wx.LEFT | wx.RIGHT | wx.EXPAND
        )
        vbox.Add(hbox3, border=5, flag=wx.ALL | wx.EXPAND)

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


def messageBox(message, title, style):
    """Shows a non-native message box, with no bell sound for any style."""
    dlg = wx.lib.agw.genericmessagedialog.GenericMessageDialog(
        None, message, title, style
    )
    dlg.ShowModal()
    dlg.Destroy()
