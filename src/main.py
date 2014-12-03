# -*- coding: utf-8 -*-
"""
Skyperious main program entrance: launches GUI application or executes command
line interface, handles logging and status calls.

------------------------------------------------------------------------------
This file is part of Skyperious - a Skype database viewer and merger.
Released under the MIT License.

@author      Erki Suurjaak
@created     26.11.2011
@modified    04.12.2014
------------------------------------------------------------------------------
"""
import argparse
import atexit
import codecs
import collections
import datetime
import glob
import locale
import itertools
import Queue
import os
import shutil
import sys
import threading
import time
import traceback

try:
    import wx
    is_gui_possible = True
except ImportError:
    is_gui_possible = False
try: # For printing to a console from a packaged Windows binary
    import win32console
except ImportError:
    win32console = None

import conf
import export
import skypedata
import util
import workers
if is_gui_possible:
    import guibase
    import skyperious
    import support

ARGUMENTS = {
    "description": "%s - Skype SQLite database viewer and merger." % conf.Title,
    "arguments": [
        {"args": ["--verbose"], "action": "store_true",
         "help": "print detailed progress messages to stderr"}, ],
    "commands": [
        {"name": "export",
         "help": "export Skype databases as HTML, text or spreadsheet",
         "description": "Export all message history from a Skype database "
                        "into files under a new folder, or a single Excel "
                        "workbook with chats on separate sheets.",
         "arguments": [
             {"args": ["-t", "--type"], "dest": "type",
              "choices": ["html", "xlsx", "csv", "txt", "xlsx_single"],
              "default": "html", "required": False,
              "help": "export type: HTML files (default), Excel workbooks, "
                      "CSV spreadsheets, text files, or a single Excel "
                      "workbook with separate sheets", },
             {"args": ["FILE"], "nargs": "+",
              "help": "one or more Skype databases to export", }, 
             {"args": ["--verbose"], "action": "store_true",
              "help": "print detailed progress messages to stderr"}, ],
        }, 
        {"name": "search",
         "help": "search Skype databases for messages or data",
         "description": "Search Skype databases for messages, chat or contact "
                        "information, or table data.",
         "arguments": [
             {"args": ["-t", "--type"], "dest": "type", "required": False,
              "choices": ["message", "contact", "chat", "table"],
              "default": "message",
              "help": "search in message body (default), in contact "
                      "information, in chat title and participants, or in any "
                      "database table", },
             {"args": ["QUERY"],
              "help": "search query, with a Google-like syntax, for example: "
                      "\"this OR that chat:links from:john\". More on syntax "
                      "at https://suurjaak.github.io/Skyperious/help.html. " },
             {"args": ["FILE"], "nargs": "+",
              "help": "Skype database file(s) to search", },
             {"args": ["--verbose"], "action": "store_true",
              "help": "print detailed progress messages to stderr"}, ],
        }, 
        {"name": "merge", "help": "merge two or more Skype databases "
                                  "into a new database",
         "description": "Merge two or more Skype database files into a new "
                        "database in current directory, with a full combined "
                        "message history. New filename will be chosen "
                        "automatically. Last database in the list will "
                        "be used as base for comparison.",
         "arguments": [
             {"args": ["FILE1"], "metavar": "FILE1", "nargs": 1,
              "help": "first Skype database"},
             {"args": ["FILE2"], "metavar": "FILE2", "nargs": "+",
              "help": "more Skype databases"},
             {"args": ["--verbose"], "action": "store_true",
              "help": "print detailed progress messages to stderr"}, ],
        }, 
        {"name": "diff", "help": "compare chat history in two Skype databases",
         "description": "Compare two Skype databases for differences "
                        "in chat history.",
         "arguments": [
             {"args": ["FILE1"], "help": "first Skype database", "nargs": 1},
             {"args": ["FILE2"], "help": "second Skype databases", "nargs": 1},
             {"args": ["--verbose"], "action": "store_true",
              "help": "print detailed progress messages to stderr"}, ],
        }, 
        {"name": "gui",
         "help": "launch Skyperious graphical program (default option)",
         "description": "Launch Skyperious graphical program (default option)",
         "arguments": [
             {"args": ["FILE"], "nargs": "*",
              "help": "Skype database to open on startup, if any"}, ]
        },
    ],
}


window = None         # Application main window instance
deferred_logs = []    # Log messages cached before main window is available
deferred_status = []  # Last status cached before main window is available
is_cli = False        # Is program running in command-line interface mode
is_verbose = False    # Is command-line interface verbose


def log(text, *args):
    """
    Logs a timestamped message to main window.

    @param   args  string format arguments, if any, to substitute in text
    """
    global deferred_logs, is_cli, is_verbose, window
    now = datetime.datetime.now()
    try:
        finaltext = text % args if args else text
    except UnicodeError:
        args = tuple(map(util.to_unicode, args))
        finaltext = text % args if args else text
    if "\n" in finaltext: # Indent all linebreaks
        finaltext = finaltext.replace("\n", "\n\t\t")
    msg = "%s.%03d\t%s" % (now.strftime("%H:%M:%S"), now.microsecond / 1000,
                           finaltext)
    if window:
        process_deferreds()
        wx.PostEvent(window, guibase.LogEvent(text=msg))
    elif is_cli and is_verbose:
        sys.stderr.write(msg + "\n"), sys.stderr.flush()
    else:
        deferred_logs.append(msg)


def status(text, *args):
    """
    Sets main window status text.

    @param   args  string format arguments, if any, to substitute in text
    """
    global deferred_status, is_cli, is_verbose, window
    try:
        msg = text % args if args else text
    except UnicodeError:
        args = tuple(map(util.to_unicode, args))
        msg = text % args if args else text
    if window:
        process_deferreds()
        wx.PostEvent(window, guibase.StatusEvent(text=msg))
    elif is_cli and is_verbose:
        sys.stderr.write(msg + "\n")
    else:
        deferred_status[:] = [msg]



def status_flash(text, *args):
    """
    Sets main window status text that will be cleared after a timeout.

    @param   args  string format arguments, if any, to substitute in text
    """
    global deferred_status, window
    try:
        msg = text % args if args else text
    except UnicodeError:
        args = tuple(map(util.to_unicode, args))
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
    Logs a timestamped message to main window and sets main window status text.

    @param   args  string format arguments, if any, to substitute in text
    """
    log(text, *args)
    status(text, *args)


def logstatus_flash(text, *args):
    """
    Logs a timestamped message to main window and sets main window status text
    that will be cleared after a timeout.

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
            for msg in deferred_logs:
                wx.PostEvent(window, guibase.LogEvent(text=msg))
            del deferred_logs[:]
        if deferred_status:
            wx.PostEvent(window, guibase.StatusEvent(text=deferred_status[0]))
            del deferred_status[:]


def run_merge(filenames):
    """Merges all Skype databases to a new database."""
    dbs = [skypedata.SkypeDatabase(f) for f in filenames]
    db_base = dbs.pop()
    counts = collections.defaultdict(lambda: collections.defaultdict(int))
    postbacks = Queue.Queue()
    postfunc = lambda r: postbacks.put(r)
    worker = workers.MergeThread(postfunc)

    name, ext = os.path.splitext(os.path.split(db_base.filename)[-1])
    now = datetime.datetime.now().strftime("%Y%m%d")
    filename_final = util.unique_path("%s.merged.%s%s" %  (name, now, ext))
    print("Creating %s, using %s as base." % (filename_final, db_base))
    shutil.copyfile(db_base.filename, filename_final)
    db2 = skypedata.SkypeDatabase(filename_final)
    chats2 = db2.get_conversations()
    db2.get_conversations_stats(chats2)

    for db1 in dbs:
        chats = db1.get_conversations()
        db1.get_conversations_stats(chats)
        bar_total = sum(c["message_count"] for c in chats)
        bar_text = " Processing %.*s.." % (30, db1)
        bar = ProgressBar(max=bar_total, afterword=bar_text)
        bar.start()
        args = {"db1": db1, "db2": db2, "chats": chats,
                "type": "diff_merge_left"}
        worker.work(args)
        while True:
            result = postbacks.get()
            if "error" in result:
                print("Error merging %s:\n\n%s" % (db1, result["error"]))
                worker = None # Signal for global break
                break # break while True
            if "done" in result:
                break # break while True
            if "diff" in result:
                counts[db1]["chats"] += 1
                counts[db1]["msgs"] += len(result["diff"]["messages"])
                msgcounts = sum(c["message_count"] for c in result["chats"])
                bar.update(bar.value + msgcounts)
            if result["output"]:
                log(result["output"])
        if not worker:
            break # break for db1 in dbs
        bar.stop()
        bar.afterword = " Processed %s." % db1
        bar.update(bar_total)
        print

    if not counts:
        print("Nothing new to merge.")
        db2.close()
        os.unlink(filename_final)
    else:
        for db1 in dbs:
            print("Merged %s in %s from %s." %
                  (util.plural("message", counts[db1]["msgs"]),
                   util.plural("chat", counts[db1]["chats"]), db1))
        print("Merge into %s complete." % db2)


def run_search(filenames, query):
    """Searches the specified databases for specified query."""
    dbs = [skypedata.SkypeDatabase(f) for f in filenames]

    postbacks = Queue.Queue()
    postfunc = lambda r: postbacks.put(r)
    worker = workers.SearchThread(postfunc)

    for db in dbs:
        log("Searching \"%s\" in %s." % (query, db))
        args = {"db": db, "text": query, "table": "messages", "output": "text"}
        worker.work(args)
        while True:
            result = postbacks.get()
            if "error" in result:
                print("Error searching %s:\n\n%s" %
                      (db, result.get("error_short", result["error"])))
                break # break while True
            if "done" in result:
                log("Finished searching for \"%s\" in %s.", query, db)
                break # break while True
            if result.get("count", 0) or is_verbose:
                if len(dbs) > 1:
                    print "%s:" % db,
                print(result["output"])


def run_export(filenames, format):
    """Exports the specified databases in specified format."""
    dbs = [skypedata.SkypeDatabase(f) for f in filenames]
    is_xlsx_single = ("xlsx_single" == format)

    for db in dbs:
        formatargs = collections.defaultdict(str)
        formatargs["skypename"] = os.path.basename(db.filename)
        formatargs.update(db.account or {})
        basename = util.safe_filename(conf.ExportDbTemplate % formatargs)
        dbstr = "from %s " % db if len(dbs) != 1 else ""
        if is_xlsx_single:
            export_dir = os.getcwd()
            filename = util.unique_path("%s.xlsx" % basename)
        else:
            export_dir = util.unique_path(os.path.join(os.getcwd(), basename))
            filename = format
        target = filename if is_xlsx_single else export_dir
        try:
            print("Exporting as %s %sto %s." % 
                  (format[:4].upper(), dbstr, target))
            chats = sorted(db.get_conversations(),
                           key=lambda x: x["title"].lower())
            db.get_conversations_stats(chats)
            bar_total = sum(c["message_count"] for c in chats)
            bartext = " Exporting %.*s.." % (30, db.filename) # Enforce width
            bar = ProgressBar(max=bar_total, afterword=bartext)
            bar.start()
            result = export.export_chats(chats, export_dir, filename, db,
                                         progress=lambda x: bar.update(x))
            files, count = result
            bar.stop()
            if count:
                bar.afterword = " Exported %s to %s. " % (db, target)
                bar.update(bar_total)
                print
                log("Exported %s %sto %s as %s.", util.plural("chat", count),
                     dbstr, target, format)
            else:
                print("\nNo messages to export%s." %
                      ("" if len(dbs) == 1 else " from %s" % db))
                os.unlink(filename) if is_xlsx_single else os.rmdir(export_dir)
        except Exception as e:
            print("Error exporting chats: %s\n\n%s" % 
                  (e, traceback.format_exc()))


def run_diff(filename1, filename2):
    """Compares the first database for changes with the second."""
    if os.path.realpath(filename1) == os.path.realpath(filename2):
        print("Error: cannot compare %s with itself." % filename1)
        return
    db1, db2 = map(skypedata.SkypeDatabase, [filename1, filename2])
    counts = collections.defaultdict(lambda: collections.defaultdict(int))
    postbacks = Queue.Queue()
    postfunc = lambda r: postbacks.put(r)
    worker = workers.MergeThread(postfunc)

    chats1, chats2 = db1.get_conversations(), db2.get_conversations()
    db1.get_conversations_stats(chats1), db2.get_conversations_stats(chats2)
    bar_total = sum(c["message_count"] for c in chats1)
    bar_text = "%.*s.." % (50, " Scanning %s vs %s" % (db1, db2))
    bar = ProgressBar(max=bar_total, afterword=bar_text)
    bar.start()
    args = {"db1": db1, "db2": db2, "chats": chats1, "type": "diff_left"}
    worker.work(args)
    while True:
        result = postbacks.get()
        if "error" in result:
            print("Error scanning %s and %s:\n\n%s" %
                  (db1, db2, result["error"]))
            worker = None # Signal for global break
            break # break while True
        if "done" in result:
            break # break while True
        if "chats" in result and result["chats"]:
            counts[db1]["chats"] += 1
            msgs = len(result["chats"][0]["diff"]["messages"])
            msgs_text = util.plural("new message", msgs)
            contacts_text = util.plural("new participant", 
                            result["chats"][0]["diff"]["participants"])
            text = ", ".join(filter(None, [msgs_text, contacts_text]))
            print("%s, %s." % (result["chats"][0]["chat"]["title_long"], text))
            counts[db1]["msgs"] += msgs
            bar.update(bar.value + result["chats"][0]["chat"]["message_count"])
        if result["output"]:
            log(result["output"])
    bar.stop()
    bar.afterword = " Scanned %s and %s." % (db1, db2)
    bar.update(bar_total)
    print


def run_gui(filenames):
    """Main GUI program entrance."""
    global deferred_logs, deferred_status, window

    # Values in some threads would otherwise not be the same
    sys.modules["main"].deferred_logs = deferred_logs
    sys.modules["main"].deferred_status = deferred_status

    # Create application main window
    app = wx.App(redirect=True) # stdout and stderr redirected to wx popup
    window = sys.modules["main"].window = skyperious.MainWindow()
    app.SetTopWindow(window) # stdout/stderr popup closes with MainWindow
    # Decorate write to catch printed errors
    try: sys.stdout.write = support.reporting_write(sys.stdout.write)
    except: pass

    # Some debugging support
    window.run_console("import datetime, os, re, time, sys, wx")
    window.run_console("# All %s modules:" % conf.Title)
    window.run_console("import conf, controls, emoticons, export, guibase, "
                       "images, main, searchparser, skypedata, skyperious, "
                       "support, templates, util, wordcloud, workers, "
                       "wx_accel")

    window.run_console("self = main.window # Application main window instance")
    log("Started application on %s.", datetime.date.today())
    for f in filter(os.path.isfile, filenames):
        wx.CallAfter(wx.PostEvent, window, skyperious.OpenDatabaseEvent(file=f))
    app.MainLoop()


def run():
    """Parses command-line arguments and either runs GUI, or a CLI action."""
    global is_cli, is_gui_possible, is_verbose

    if (getattr(sys, 'frozen', False) # Binary application
    or sys.executable.lower().endswith("pythonw.exe")):
        sys.stdout = ConsoleWriter(sys.stdout) # Hooks for attaching to 
        sys.stderr = ConsoleWriter(sys.stderr) # a text console

    argparser = argparse.ArgumentParser(description=ARGUMENTS["description"])
    for arg in ARGUMENTS["arguments"]:
        names = arg["args"]; del arg["args"]
        argparser.add_argument(*names, **arg)
    subparsers = argparser.add_subparsers(dest="command")
    for cmd in ARGUMENTS["commands"]:
        kwargs = dict((k, cmd[k]) for k in cmd if k in ["help", "description"])
        subparser = subparsers.add_parser(cmd["name"], **kwargs)
        for arg in cmd["arguments"]:
            kwargs = dict((k, arg[k]) for k in arg if k != "args")
            subparser.add_argument(*arg["args"], **kwargs)

    argv = sys.argv[1:]
    if not argv or (argv[0] not in subparsers.choices 
    and argv[0].endswith(".db")):
        argv[:0] = ["gui"] # argparse hack: force default argument
    if argv[0] in ("-h", "--help") and len(argv) > 1:
        argv[:2] = argv[:2][::-1] # Swap "-h option" to "option -h"

    arguments = argparser.parse_args(argv)

    if hasattr(arguments, "FILE1") and hasattr(arguments, "FILE2"):
        arguments.FILE1 = [util.to_unicode(f) for f in arguments.FILE1]
        arguments.FILE2 = [util.to_unicode(f) for f in arguments.FILE2]
        arguments.FILE = arguments.FILE1 + arguments.FILE2
    if arguments.FILE: # Expand wildcards to actual filenames
        arguments.FILE = sum([(sorted(glob.glob(f)) if "*" in f else [f])
                             for f in arguments.FILE], [])
        arguments.FILE = [util.to_unicode(f) for f in arguments.FILE]

    if "gui" == arguments.command and not is_gui_possible:
        argparser.print_help()
        print("\n\nwxPython not found. %s graphical program will not run." %
              conf.Title)
        sys.exit()
    elif "gui" != arguments.command:
        conf.load()
        is_cli = sys.modules["main"].is_cli = True
        is_verbose = sys.modules["main"].is_verbose = arguments.verbose
        enc = sys.stdout.encoding or locale.getpreferredencoding() or "utf-8"
        if "nt" == os.name: # Avoid print encoding errors under windows
            sys.stdout = codecs.getwriter(enc)(sys.stdout, "xmlcharrefreplace")
            sys.stderr = codecs.getwriter(enc)(sys.stderr, "xmlcharrefreplace")

    if "diff" == arguments.command:
        run_diff(*arguments.FILE)
    elif "merge" == arguments.command:
        run_merge(arguments.FILE)
    elif "export" == arguments.command:
        run_export(arguments.FILE, arguments.type)
    elif "search" == arguments.command:
        run_search(arguments.FILE, arguments.QUERY)
    elif "gui" == arguments.command:
        run_gui(arguments.FILE)


class ConsoleWriter(object):
    """
    Wrapper for sys.stdout/stderr, attaches to the parent console or creates 
    a new command console, usable from python.exe, pythonw.exe or
    compiled binary. Hooks application exit to wait for final user input.
    """
    handle = None # note: class variables
    is_loaded = False
    realwrite = None

    def __init__(self, stream):
        """
        @param   stream  sys.stdout or sys.stderr
        """
        self.encoding = getattr(stream, "encoding", locale.getpreferredencoding())
        self.stream = stream


    def flush(self):
        if not ConsoleWriter.handle and ConsoleWriter.is_loaded:
            self.stream.flush()
        elif hasattr(ConsoleWriter.handle, "flush"):
            ConsoleWriter.handle.flush()


    def write(self, text):
        """
        Prints text to console window. GUI application will need to attach to
        the calling console, or launch a new console if not available.
        """
        global window
        if not window and win32console:
            if not ConsoleWriter.is_loaded and not ConsoleWriter.handle:
                try:
                    win32console.AttachConsole(-1) # pythonw.exe from console
                    atexit.register(lambda: ConsoleWriter.realwrite("\n"))
                except Exception:
                    pass # Okay if fails: can be python.exe from console
                try:
                    handle = win32console.GetStdHandle(
                                          win32console.STD_OUTPUT_HANDLE)
                    handle.WriteConsole("\n" + text)
                    ConsoleWriter.handle = handle
                    ConsoleWriter.realwrite = handle.WriteConsole
                except Exception: # Fails if GUI program: make new console
                    try: win32console.FreeConsole()
                    except Exception: pass
                    try:
                        win32console.AllocConsole()
                        handle = open("CONOUT$", "w")
                        argv = [util.longpath(sys.argv[0])] + sys.argv[1:]
                        handle.write(" ".join(argv) + "\n\n" + text)
                        handle.flush()
                        ConsoleWriter.handle = handle
                        ConsoleWriter.realwrite = handle.write
                        sys.stdin = open("CONIN$", "r")
                        exitfunc = lambda s: (handle.write(s), handle.flush(),
                                              raw_input())
                        atexit.register(exitfunc, "\nPress ENTER to exit.")
                    except Exception:
                        try: win32console.FreeConsole()
                        except Exception: pass
                        ConsoleWriter.realwrite = self.stream.write
                ConsoleWriter.is_loaded = True
            else:
                try:
                    self.realwrite(text)
                    self.flush()
                except Exception:
                    self.stream.write(text)
        else:
            self.stream.write(text)


class ProgressBar(threading.Thread):
    """
    A simple ASCII progress bar with a ticker thread, drawn like
    '[---------\   36%            ] Progressing text..'.
    """

    def __init__(self, max=100, value=0, min=0, width=30, forechar="-",
                 backchar=" ", foreword="", afterword="", interval=1):
        """
        Creates a new progress bar, without drawing it yet.

        @param   max        progress bar maximum value, 100%
        @param   value      progress bar initial value
        @param   min        progress bar minimum value, for 0%
        @param   width      progress bar width (in characters)
        @param   forechar   character used for filling the progress bar
        @param   backchar   character used for filling the background
        @param   foreword   text in front of progress bar
        @param   afterword  text after progress bar
        @param   interval   ticker thread interval, in seconds
        """
        threading.Thread.__init__(self)
        self.daemon = True # Daemon threads do not keep application running
        self.max = max
        self.min = min
        self.width = width
        self.forechar = forechar
        self.backchar = backchar
        self.foreword = foreword
        self.afterword = afterword
        self.interval = interval
        self.percent = None        # Current progress ratio in per cent
        self.value = None          # Current progress bar value
        self.bar = "%s[-%s]%s" % (foreword, " " * (self.width - 3), afterword)
        self.progresschar = itertools.cycle("-\\|/")
        self.is_running = False
        self.update(value, draw=False)


    def update(self, value, draw=True):
        """Updates the progress bar value, and refreshes by default."""
        self.value = min(self.max, max(self.min, value))
        new_percent = int(round(100.0 * self.value / (self.max or 1)))
        full_w = self.width - 2
        done_w = max(1, int(round((new_percent / 100.0) * full_w)))
        # Build bar outline, animate by cycling last char from progress chars
        char_last = self.forechar
        if draw and done_w < full_w: char_last = next(self.progresschar)
        self.bar = "%s[%s%s%s]%s" % (
                   self.foreword, self.forechar * (done_w - 1), char_last,
                   self.backchar * (full_w - done_w), self.afterword)
        # Write percentage into the middle of the bar
        centertxt = " %2d%% " % new_percent
        pos = len(self.foreword) + self.width / 2 - len(centertxt) / 2
        self.bar = self.bar[:pos] + centertxt + self.bar[pos + len(centertxt):]
        self.percent = new_percent
        if draw: self.draw()


    def draw(self):
        """Prints the progress bar, from the beginning of the current line."""
        print "\r" + self.bar,


    def run(self):
        self.is_running = True
        while self.is_running:
            self.update(self.value), time.sleep(self.interval)


    def stop(self):
        self.is_running = False


if "__main__" == __name__:
    run()
