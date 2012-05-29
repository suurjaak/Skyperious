#-*- coding: utf-8 -*-
"""
GUI frame templates.

@author      Erki Suurjaak
@created     03.04.2012
@modified    16.05.2012
"""
import os
import wx
import wx.lib.inspection
import wx.lib.newevent
import wx.py

import conf
import wx_accel


"""Custom application event for adding to log page."""
LogEvent,    EVT_LOG =    wx.lib.newevent.NewEvent()
"""Custom application event for setting main window status."""
StatusEvent, EVT_STATUS = wx.lib.newevent.NewEvent()


class TemplateFrameMixIn(wx_accel.AutoAcceleratorMixIn):
    """Application main window."""

    def __init__(self):
        wx_accel.AutoAcceleratorMixIn.__init__(self)

        conf.load()

        self.Bind(EVT_LOG,      self.on_log_message)
        self.Bind(EVT_STATUS,   self.on_set_status)
        self.Bind(wx.EVT_CLOSE, self.on_exit)

        self.frame_console = wx.py.shell.ShellFrame(parent=self,
            title=u"%s Console" % conf.Title, size=conf.ConsoleSize
        )
        self.frame_console.Bind(
            wx.EVT_CLOSE, lambda evt: self.frame_console.Hide()
        )
        self.frame_console_shown = False # Init flag
        console = self.console = self.frame_console.shell
        for cmd in conf.ConsoleHistoryCommands:
            console.addHistory(cmd)
        console.Bind(wx.EVT_KEY_DOWN, self.on_keydown_console)
        self.widget_inspector = wx.lib.inspection.InspectionTool()

        self.CreateStatusBar()


    def create_page_log(self, notebook):
        """Creates the log page."""
        page = self.page_log = wx.Panel(notebook)
        notebook.AddPage(page, "Log")
        sizer = page.Sizer = wx.BoxSizer(wx.VERTICAL)

        button_clear = self.button_clear_log = wx.Button(
            parent=page, label="C&lear log", size=(100, -1)
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
        menu.Insert(0, menu_file, "&File")
        menu_recent = self.menu_recent = wx.Menu()
        menu_file.AppendMenu(id=wx.NewId(), text="&Recent files",
            submenu=menu_recent, help="Recently opened files."
        )
        menu_file.AppendSeparator()
        menu_console = self.menu_console = menu_file.Append(id=wx.NewId(),
            text="Show &console\tCtrl-W", help="Shows/hides the console window."
        )
        self.Bind(wx.EVT_MENU, self.on_showhide_console, menu_console)
        menu_inspect = self.menu_inspect = menu_file.Append(id=wx.NewId(),
            text="Show &widget inspector",
            help="Shows/hides the widget inspector."
        )
        self.Bind(wx.EVT_MENU, self.on_open_widget_inspector, menu_inspect)

        self.file_history = wx.FileHistory(conf.MaxRecentFiles)
        self.file_history.UseMenu(menu_recent)
        for filename in conf.RecentFiles[::-1]:
            # Iterate backwards, as FileHistory works like a stack
            if os.path.exists(filename):
                self.file_history.AddFileToHistory(filename)
        wx.EVT_MENU_RANGE(self, wx.ID_FILE1, wx.ID_FILE9, self.on_recent_file)
        menu_file.AppendSeparator()
        m_exit = menu_file.Append(-1, "E&xit\tAlt-X", "Exit")
        self.Bind(wx.EVT_MENU, self.on_exit, m_exit)
        self.SetMenuBar(menu)


    def on_exit(self, event):
        """
        Handler on application exit, asks about unsaved changes, if any.
        """
        do_exit = True
        if do_exit:
            conf.save()
            self.Destroy()


    def on_keydown_console(self, event):
        """Handler for keydown in console, saves entered command in history."""
        event.Skip()
        if (wx.WXK_RETURN == event.KeyCode and not event.ShiftDown()
        and self.console.history):
            # Defer saving until command is inserted into console history
            wx.CallAfter(self.save_last_command)


    def save_last_command(self):
        """Saves the last console command in conf."""
        history = self.console.history[-conf.ConsoleHistoryMax:][::-1]
        if history != conf.ConsoleHistoryCommands:
            conf.ConsoleHistoryCommands[:] = history
            conf.save()


    def on_set_status(self, event):
        """Event handler for adding a message to the log page."""
        self.SetStatusText(event.text)


    def on_log_message(self, event):
        """Event handler for adding a message to the log page."""
        try:
            if not (hasattr(conf, "LogEnabled")) or conf.LogEnabled:
                self.log.AppendText(event.text + "\n")
        except Exception, e:
            print "Exception %s in on_log_message" % e


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
        """Handler for clicking an entry in Recent Files menu."""
        filename = self.file_history.GetHistoryFile(event.GetId() - wx.ID_FILE1)
        self.open_file(filename)
