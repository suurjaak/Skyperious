# -*- coding: utf-8 -*-
"""
Skyperious main program entrance: launches application and handles logging
and status calls.

------------------------------------------------------------------------------
This file is part of Skyperious - a Skype database viewer and merger.
Released under the MIT License.

@author      Erki Suurjaak
@created     26.11.2011
@modified    29.08.2013
------------------------------------------------------------------------------
"""
import datetime
import os
import sys
import wx

import conf
import guibase
import skyperious
import support

window = None          # Application main window instance
deferred_logs = []     # Log messages cached before main window is available
deferred_status = []   # Last status cached before main window is available


def run():
    """Main program entrance."""
    global deferred_logs, deferred_status, window
    conf.load()

    # Values in some threads would otherwise not be the same
    sys.modules["main"].deferred_logs = deferred_logs
    sys.modules["main"].deferred_status = deferred_status

    # Create application main window
    app = wx.App(redirect=True) # stdout and stderr redirected to wx popup
    window = skyperious.MainWindow()
    app.SetTopWindow(window)    # stdout/stderr popup closes with MainWindow
    sys.modules["main"].window = window
    # Decorate write to catch printed errors
    sys.stdout.write = support.reporting_write(sys.stdout.write)

    # Some debugging support
    window.console.run("import datetime, os, re, time, sys, wx")
    window.console.run("# All %s modules:" % conf.Title)
    window.console.run("import conf, controls, emoticons, export, guibase,"
                       "images, main, searchparser, skypedata, skyperious, "
                       "support, templates, util, wordcloud, workers, "
                       "wx_accel")

    window.console.run("self = main.window # Application main window instance")
    log("Started application on %s.", datetime.date.today())
    if len(sys.argv) > 1:
        event = skyperious.OpenDatabaseEvent(file=sys.argv[1])
        wx.CallAfter(wx.PostEvent, window, event)
    app.MainLoop()


def log(text, *args):
    """
    Logs a timestamped message to main window.

    @param   args  string format arguments, if any, to substitute in text
    """
    global deferred_logs, window
    timestamp = datetime.datetime.now()
    finaltext = text % args if args else text
    if "\n" in finaltext: # Indent all linebreaks
        finaltext = finaltext.replace("\n", "\n\t\t")
    msg = "%s,%03d\t%s" % (timestamp.strftime("%H:%M:%S"),
                           timestamp.microsecond / 1000,
                           finaltext)
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
    msg = text % args if args else text
    if window:
        process_deferreds()
        wx.PostEvent(window, guibase.StatusEvent(text=msg))
    else:
        deferred_status[:] = [msg]



def status_flash(text, *args):
    """
    Sets main window status text that will be cleared after a timeout.

    @param   args  string format arguments, if any, to substitute in text
    """
    global deferred_status, window
    msg = text % args if args else text
    if window:
        process_deferreds()
        wx.PostEvent(window, guibase.StatusEvent(text=msg))
        def clear_status():
            if window.StatusBar and window.StatusBar.StatusText == msg:
                window.SetStatusText("")
        wx.CallLater(conf.StatusFlashLength, clear_status)
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


def logstatus_flash(text, *args):
    """
    Logs a timestamped message to main window and sets main window
    status text that will be cleared after a timeout.

    @param   args  string format arguments, if any, to substitute in text
    """
    log(text, *args)
    status_flash(text, *args)


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
