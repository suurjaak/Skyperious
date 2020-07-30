# -*- coding: utf-8 -*-
"""
GUI frame template:
- auto-accelerated control shortcuts, "&OK" will turn Alt-O into shortcut
- Python console window, initially hidden,
  with auto-saved command history kept in conf.ConsoleHistoryCommands
- wx widget inspector window, initially hidden
- option for log panel, handles logging messages via wx events

------------------------------------------------------------------------------
This file is part of Skyperious - Skype chat history tool.
Released under the MIT License.

@author      Erki Suurjaak
@created     03.04.2012
@modified    30.07.2020
"""
import datetime
import logging
import os
import re
import traceback

try:
    import wx
    import wx.lib.inspection
    import wx.py
    import wx.stc
except ImportError: wx = None

from . lib.controls import ColourManager, KEYS
from . lib import util
from . lib import wx_accel

from . import conf

logger = logging.getLogger(__name__)



def status(text="", *args, **kwargs):
    """
    Sets main window status text, optionally logs the message.

    @param   args   string format arguments, if any, to substitute in text
    @param   flash  whether to clear the status after timeout,
                    by default after conf.StatusFlashLength if not given seconds
    @param   log    whether to log the message to main window
    """
    log, flash = (kwargs.get(x) for x in ("log", "flash"))
    window = wx and wx.GetApp() and wx.GetApp().GetTopWindow()
    if not window and not log: return

    try: msg = text % args if args else text
    except Exception:
        try:
            args = tuple(map(util.to_unicode, args))
            msg = text % args if args else text
        except Exception: msg = text
    msg = re.sub("[\n\r\t]+", " ", msg)
    if log: logger.info(msg)
    try: window and window.set_status(msg, timeout=flash)
    except Exception: pass



class GUILogHandler(logging.Handler):
    """Logging handler that forwards logging messages to GUI log window."""

    def __init__(self):
        self.deferred = [] # Messages logged before main window available
        super(self.__class__, self).__init__()


    def emit(self, record):
        """Adds message to GUI log window, or postpones if window unavailable."""
        try:
            now = datetime.datetime.now()
            try: text = record.msg % record.args if record.args else record.msg
            except Exception:
                try:
                    args = tuple(map(util.to_unicode, record.args or ()))
                    text = record.msg % args if args else record.msg
                except Exception: text = record.msg
            if record.exc_info:
                text += "\n\n" + "".join(traceback.format_exception(*record.exc_info))
            if "\n" in text:
                text = text.replace("\n", "\n\t\t\t") # Indent linebreaks
                text = re.sub(r"^\s+$", "", text, flags=re.M) # Unindent whitespaced lines
            msg = "%s.%03d\t%s" % (now.strftime("%Y-%m-%d %H:%M:%S"),
                                   now.microsecond / 1000, text)

            window = wx.GetApp() and wx.GetApp().GetTopWindow()
            if window:
                msgs = self.deferred + [msg]
                for m in msgs: wx.CallAfter(window.log_message, m)
                del self.deferred[:]
            else: self.deferred.append(msg)
        except Exception: pass
        


class TemplateFrameMixIn(wx_accel.AutoAcceleratorMixIn if wx else object):
    """Application main window."""

    def __init__(self):
        wx_accel.AutoAcceleratorMixIn.__init__(self)

        self.Bind(wx.EVT_CLOSE, self.on_exit)

        self.console_commands = set() # Commands from run_console()
        self.frame_console = wx.py.shell.ShellFrame(parent=self,
            title=u"%s Console" % conf.Title, size=conf.ConsoleSize)
        self.frame_console.Bind(wx.EVT_CLOSE, self.on_showhide_console)
        self.frame_console_shown = False # Init flag
        console = self.console = self.frame_console.shell
        if not isinstance(conf.ConsoleHistoryCommands, list):
            conf.ConsoleHistoryCommands = [] 
        for cmd in conf.ConsoleHistoryCommands:
            console.addHistory(cmd)
        console.Bind(wx.EVT_KEY_DOWN, self.on_keydown_console)
        self.widget_inspector = wx.lib.inspection.InspectionTool()

        self.CreateStatusBar()


    def create_log_panel(self, parent):
        """Creates and returns the log output panel."""
        panel = wx.Panel(parent)
        sizer = panel.Sizer = wx.BoxSizer(wx.VERTICAL)
        ColourManager.Manage(panel, "BackgroundColour", wx.SYS_COLOUR_BTNFACE)

        button_clear = wx.Button(parent=panel, label="C&lear log", size=(100, -1))
        edit_log = self.log = wx.stc.StyledTextCtrl(panel)
        edit_log.SetMarginCount(0)
        edit_log.SetReadOnly(True)
        edit_log.SetTabWidth(edit_log.TabWidth * 2)
        edit_log.SetWrapMode(wx.stc.STC_WRAP_WORD)

        def on_clear(event=None):
            edit_log.SetReadOnly(False)
            edit_log.ClearAll()
            edit_log.SetReadOnly(True)
        def on_colour(event=None):
            if event: event.Skip()
            fgcolour, crcolour, bgcolour = (
                wx.SystemSettings.GetColour(x).GetAsString(wx.C2S_HTML_SYNTAX)
                for x in (wx.SYS_COLOUR_GRAYTEXT, wx.SYS_COLOUR_BTNTEXT,
                          wx.SYS_COLOUR_WINDOW)
            )
            edit_log.SetCaretForeground(crcolour)
            edit_log.StyleSetSpec(wx.stc.STC_STYLE_DEFAULT,
                                  "back:%s,fore:%s" % (bgcolour, fgcolour))
            edit_log.StyleClearAll() # Apply the new default style to all styles

        button_clear.Bind(wx.EVT_BUTTON,     on_clear)
        self.Bind(wx.EVT_SYS_COLOUR_CHANGED, on_colour)
        on_colour()

        sizer.Add(button_clear, border=5, flag=wx.ALIGN_RIGHT | wx.TOP |
                  wx.RIGHT)
        sizer.Add(edit_log, border=5, proportion=1, flag=wx.GROW | wx.ALL)
        return panel


    def create_menu(self):
        """Creates the program menu."""
        menu = wx.MenuBar()
        menu_file = wx.Menu()
        menu.Insert(0, menu_file, "&File")
        menu_recent = self.menu_recent = wx.Menu()
        menu_file.AppendMenu(id=wx.NewIdRef().Id, text="&Recent files",
            submenu=menu_recent, help="Recently opened files.")
        menu_file.AppendSeparator()
        menu_console = self.menu_console = menu_file.Append(
            id=wx.NewIdRef().Id, kind=wx.ITEM_CHECK, text="Show &console\tCtrl-E",
            help="Show/hide a Python shell environment window")
        menu_inspect = self.menu_inspect = menu_file.Append(
            id=wx.NewIdRef().Id, kind=wx.ITEM_CHECK, text="Show &widget inspector",
            help="Show/hide the widget inspector")

        self.file_history = wx.FileHistory(conf.MaxRecentFiles)
        self.file_history.UseMenu(menu_recent)
        for f in conf.RecentFiles[::-1]: # Backwards - FileHistory is a stack
            os.path.exists(f) and self.file_history.AddFileToHistory(f)
        wx.EVT_MENU_RANGE(self, wx.ID_FILE1, wx.ID_FILE9, self.on_recent_file)
        menu_file.AppendSeparator()
        m_exit = menu_file.Append(-1, "E&xit\tAlt-X", "Exit")

        self.Bind(wx.EVT_MENU, self.on_showhide_console, menu_console)
        self.Bind(wx.EVT_MENU, self.on_open_widget_inspector, menu_inspect)
        self.Bind(wx.EVT_MENU, self.on_exit, m_exit)
        self.SetMenuBar(menu)


    def on_exit(self, event):
        """Handler on application exit, saves configuration."""
        conf.save()
        self.Destroy()


    def on_keydown_console(self, event):
        """Handler for keydown in console, saves entered command in history."""
        event.Skip()
        if (event.KeyCode in KEYS.ENTER and not event.ShiftDown()
        and self.console.history):
            # Defer saving until command is inserted into console history
            wx.CallAfter(self.save_last_command)


    def run_console(self, command):
        """
        Runs the command in the Python console. Will not be saved to console
        commands history.
        """
        self.console.run(command)
        self.console_commands.add(command)


    def save_last_command(self):
        """
        Saves the last console command in conf, minus the commands given via
        run_console().
        """
        h = [x for x in self.console.history if x not in self.console_commands]
        history = h[:conf.MaxConsoleHistory][::-1]
        if history != conf.ConsoleHistoryCommands:
            conf.ConsoleHistoryCommands[:] = history
            conf.save()


    def set_status(self, text, timeout=False):
        """Sets main window status bar text, optionally clears after timeout."""
        self.SetStatusText(text)
        if not timeout or not text: return

        if timeout is True: timeout = conf.StatusFlashLength
        clear = lambda sb: sb and sb.StatusText == text and self.SetStatusText("")
        wx.CallLater(timeout, clear, self.StatusBar)


    def log_message(self, text):
        """Adds a message to the log control."""
        if not hasattr(self, "log") \
        or hasattr(conf, "LogEnabled") and not conf.LogEnabled: return

        self.log.SetReadOnly(False)
        try: self.log.AppendText(text + "\n")
        except Exception:
            try: self.log.AppendText(text.decode("utf-8", "replace") + "\n")
            except Exception as e: print("Exception %s: %s in log_message" %
                                         (e.__class__.__name__, e))
        self.log.SetReadOnly(True)


    def on_showhide_console(self, event=None):
        """Toggles the console shown/hidden."""
        show = not self.frame_console.IsShown()
        if show and not self.frame_console_shown:
            # First showing of console, set height to a fraction of main
            # form, and position it immediately under the main form, or
            # covering its bottom if no room.
            self.frame_console_shown = True
            size = wx.Size(self.Size.width, max(200, self.Size.height / 3))
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
        if show: self.console.ScrollToLine(self.console.LineCount + 3 - (
            self.console.Size.height / self.console.GetTextExtent(" ")[1]
        )) # Scroll to the last line
        self.frame_console.Show(show)
        self.frame_console.Iconize(False)
        if hasattr(self, "menu_console"): self.menu_console.Check(show)


    def on_open_widget_inspector(self, event=None):
        """Toggles the widget inspection tool shown/hidden."""
        visible = not (self.widget_inspector.initialized
                       and self.widget_inspector._frame)
        if visible:
            self.widget_inspector.Init()
            self.widget_inspector.Show(selectObj=self, refreshTree=True)
            self.widget_inspector._frame.Bind(wx.EVT_CLOSE, lambda e: e.Skip())
        else:
            self.widget_inspector._frame.Close()
        if hasattr(self, "menu_inspect"):
            self.menu_inspect.Check(visible)


    def on_recent_file(self, event):
        """Handler for clicking an entry in Recent Files menu."""
        filename = self.file_history.GetHistoryFile(event.GetId() - wx.ID_FILE1)
        self.open_file(filename)
