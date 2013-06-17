# -*- coding: utf-8 -*-
"""
Skyperious main program entrance.

Skyperious is a simple tool for accessing Skype database files, with the
primary aim of merging chat history from another Skype database file.

In addition, Skyperious allows to:
- read, search, filter and export chats
- see chat statistics
- import contacts from a CSV file to your Skype contacts
- browse and modify all database tables
- execute arbitrary queries on the database
- fix chat history messages that have been saved with a future timestamp
  (can happen if the computer's clock has been in the future when receiving
  messages)

@author      Erki Suurjaak
@created     26.11.2011
@modified    15.06.2013
"""
import datetime
import multiprocessing.connection
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
instance_check = None  # wx.SingleInstanceChecker

def run():
    """Main program entrance."""
    global deferred_logs, deferred_status, instance_check, window
    conf.load()

    instance_check = wx.SingleInstanceChecker(conf.IPCName)
    if not conf.AllowMultipleInstances and instance_check.IsAnotherRunning():
        data = os.path.realpath(sys.argv[1]) if len(sys.argv) > 1 else ""
        if ipc_send(conf.IPCName, conf.IPCPort, data):
            return

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
                       " images, main, skypedata, skyperious, step, support,"
                       " templates, util, wordcloud, workers, wx_accel")

    window.console.run("self = main.window # Application main window instance")
    log("Started application.")
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
    msg = "%s,%03d\t%s" % (timestamp.strftime("%H:%M:%S"),
                           timestamp.microsecond / 1000,
                           text % args if args else text)
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
            if window.StatusBar.StatusText == msg:
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


def ipc_send(authkey, port, data):
    """
    Sends data to another Skyperious instance via multiprocessing.

    @return  True if operation successful, False otherwise
    """
    result = False
    client = None
    limit = 10000
    while not client and limit:
        kwargs = {"address": ("localhost", port), "authkey": authkey}
        try:
            client = multiprocessing.connection.Client(**kwargs)
            client.send(data)
            result = True
        except Exception, e:
            port = port + 1
            limit -= 1
    return result


if "__main__" == __name__:
    run()
