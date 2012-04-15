# -*- coding: utf-8 -*-
"""
Skyperious main program entrance.

Skyperious is a simple tool for accessing Skype database files, with the
primary aim of merging chat history from another Skype database file.

In addition, Skyperious allows to:
- read, search, filter and export chats
- see chat statistics
- browse and modify all database tables
- execute arbitrary queries on the database
- fix chat history messages that have been saved with a future timestamp
  (can happen if the computer's clock has been in the future when receiving
  messages)

@author      Erki Suurjaak
@created     26.11.2011
@modified    29.03.2012
"""
import datetime
import sys
import traceback
import wx

import gui

window = None # gui.MainWindow instance


def run():
    """Main program entrance."""
    global window
    app = wx.App()
    window = gui.MainWindow()
    # "global window" does not quite do the trick for all threads
    sys.modules["main"].window = window
    # Some debugging support
    window.console.run("import datetime, os, re, time, sys, wx")
    window.console.run("# Skyperious modules:")
    window.console.run("import conf, controls, export, images, main")
    window.console.run("import os_handler, skypedata, wordcloud, workers, "
        "wx_accel, util"
    )
    window.console.run("self = main.window # gui.MainWindow instance")
    log("Started application.")
    app.MainLoop()


def log(text, *args):
    """
    Logs a timestamped message to main log window.

    @param   args  string format arguments, if any, to substitute in text
    """
    global window
    timestamp = datetime.datetime.now()
    msg = "%s,%03d\t%s" % (timestamp.strftime("%H:%M:%S"),
                timestamp.microsecond / 1000, text % args
            )
    if window:
        wx.PostEvent(window, gui.LogEvent(text=msg))


def status(text, *args):
    """
    Sets main window status text.

    @param   args  string format arguments, if any, to substitute in text
    """
    global window
    if window:
        wx.PostEvent(window, gui.StatusEvent(text=text % args))


def logstatus(text, *args):
    """
    Logs a timestamped message to main log window and sets main window
    status text.

    @param   args  string format arguments, if any, to substitute in text
    """
    global window
    if window:
        timestamp = datetime.datetime.now()
        status = text % args
        wx.PostEvent(window, gui.StatusEvent(text=status))
        msg = "%s,%03d\t%s" % (timestamp.strftime("%H:%M:%S"),
                    timestamp.microsecond / 1000, status
                )
        wx.PostEvent(window, gui.LogEvent(text=msg))
    


if "__main__" == __name__:
    try:
        run()
    except Exception, e:
        #with open("errors.log", "a") as f:
        #    f.write("\n%s %s %s\n" % ("-" * 30, datetime.datetime.now(), "-" * 30))
        #    traceback.print_exc(file=f)
        raise
