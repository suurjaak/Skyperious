# -*- coding: utf-8 -*-
"""
Main program entrance. Program-specific main window is loaded from
conf.MainWindowModule.

@author      Erki Suurjaak
@created     26.11.2011
@modified    29.05.2012
"""
import datetime
import sys
import traceback
import wx

import conf
import guibase

window = None          # Application main window instance
deferred_logs = []     # Log messages cached before main window is available
deferred_status = []   # Last status cached before main window is available

def run():
    """Main program entrance."""
    global deferred_logs, deferred_status, window
    window_module = __import__(conf.MainWindowModule)
    # Values in some threads would otherwise not be the same
    sys.modules["main"].deferred_logs = deferred_logs
    sys.modules["main"].deferred_status = deferred_status

    # Create application main window
    app = wx.App()
    window = window_module.MainWindow()
    sys.modules["main"].window = window

    # Some debugging support
    window.console.run("import datetime, os, re, time, sys, wx")
    window.console.run("# Application base modules:")
    window.console.run("import conf, guibase, main, util, wx_accel, "
        + conf.MainWindowModule
    )
    window.console.run("self = main.window # Application main window instance")
    log("Started application.")
    app.MainLoop()


def log(text, *args):
    """
    Logs a timestamped message to main window.

    @param   args  string format arguments, if any, to substitute in text
    """
    global deferred_logs, window
    timestamp = datetime.datetime.now()
    msg = "%s,%03d\t%s" % (timestamp.strftime("%H:%M:%S"),
                timestamp.microsecond / 1000, text % args
            )
    if window:
        process_deferreds()
        wx.PostEvent(window, guibase.LogEvent(text=msg))
    else:
        deferred_logs.append(msg)


def status(text, *args):
    """
    Sets main window status text.

    @param   args  string format arguments, if any, to substitute in text
    """
    global deferred_status, window
    msg = text % args
    if window:
        process_deferreds()
        wx.PostEvent(window, guibase.StatusEvent(text=msg))
    else:
        deferred_status[:] = [msg]


def logstatus(text, *args):
    """
    Logs a timestamped message to main window and sets main window
    status text.

    @param   args  string format arguments, if any, to substitute in text
    """
    log(text, *args)
    status(text, *args)


def process_deferreds():
    """
    Forwards log messages and status, cached before main window was available.
    """
    global deferred_logs, deferred_status, window
    if window:
        if deferred_logs:
            for deferred_msg in deferred_logs:
                wx.PostEvent(window, guibase.LogEvent(text=deferred_msg))
            del deferred_logs[:]
        if deferred_status:
            wx.PostEvent(window, guibase.StatusEvent(text=deferred_status[0]))
            del deferred_status[:]



if "__main__" == __name__:
    run()
