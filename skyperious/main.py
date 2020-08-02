# -*- coding: utf-8 -*-
"""
Skyperious main program entrance: launches GUI application or executes command
line interface, handles logging and status calls.

------------------------------------------------------------------------------
This file is part of Skyperious - Skype chat history tool.
Released under the MIT License.

@author      Erki Suurjaak
@created     26.11.2011
@modified    02.08.2020
------------------------------------------------------------------------------
"""
from __future__ import print_function
import argparse
import atexit
import codecs
import collections
import datetime
import errno
import getpass
import glob
import locale
import logging
import io
import itertools
import Queue
import os
import shutil
import sys
import threading
import time
import traceback
import warnings

try:
    import wx
    is_gui_possible = True
except ImportError:
    is_gui_possible = False
try: # For printing to a console from a packaged Windows binary
    import win32console
except ImportError:
    win32console = None

from . lib import util

from . import conf
from . import export
from . import guibase
from . import skypedata
from . import workers
if is_gui_possible:
    from . import gui


def date(s): return datetime.datetime.strptime(s, "%Y-%m-%d").date()


ARGUMENTS = {
    "description": "%s - Skype chat history tool." % conf.Title,
    "arguments": [
        {"args": ["--verbose"], "action": "store_true",
         "help": "print detailed progress messages to stderr"},
        {"args": ["-v", "--version"], "action": "version",
         "version": "%s %s, %s." % (conf.Title, conf.Version, conf.VersionDate)}],
    "commands": [
        {"name": "export",
         "help": "export Skype databases as HTML, text or spreadsheet",
         "description": "Export all message history from a Skype database "
                        "into files under a new folder" + (", or a single Excel "
                        "workbook with chats on separate sheets." 
                        if export.xlsxwriter else ""),
         "arguments": [
             {"args": ["-t", "--type"], "dest": "type",
              "choices": ["html", "xlsx", "csv", "txt", "xlsx_single"]
                         if export.xlsxwriter else ["html", "csv", "txt"],
              "default": "html", "required": False,
              "help": "export type: HTML files (default), Excel workbooks, "
                      "CSV spreadsheets, text files, or a single Excel "
                      "workbook with separate sheets" if export.xlsxwriter
                      else
                      "export type: HTML files (default), CSV spreadsheets, "
                      "text files", },
             {"args": ["FILE"], "nargs": "+",
              "help": "one or more Skype databases to export", }, 
             {"args": ["-c", "--chat"], "dest": "chat", "required": False,
              "help": "names of specific chats to export", "nargs": "+"},
             {"args": ["-a", "--author"], "dest": "author", "required": False,
              "help": "names of specific authors whose chats to export",
              "nargs": "+"},
             {"args": ["-s", "--start"], "dest": "start_date", "required": False,
              "help": "date to export messages from, as YYYY-MM-DD", "type": date},
             {"args": ["-e", "--end"], "dest": "end_date", "required": False,
              "help": "date to export messages until, as YYYY-MM-DD", "type": date},
             {"args": ["--ask-password"], "dest": "ask_password",
              "action": "store_true", "required": False,
              "help": "prompt for Skype password on HTML export "
                      "to download shared images"},
             {"args": ["--store-password"], "dest": "store_password",
              "action": "store_true", "required": False,
              "help": "store entered password in configuration"},
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
        {"name": "sync",
         "help": "download new messages from Skype online service",
         "description": "Synchronize Skype database via login to Skype online service.",
         "arguments": [
             {"args": ["-u", "--username"], "dest": "username",
              "help": "username for Skype account, used only if the Skype database "
                      "does not contain account information yet"},
             {"args": ["-p", "--password"], "dest": "password",
              "help": "password for Skype account, if not using stored or prompted"},
             {"args": ["--store-password"], "dest": "store_password",
              "action": "store_true", "required": False,
              "help": "store given password in configuration"},
             {"args": ["--ask-password"], "dest": "ask_password",
              "action": "store_true", "required": False,
              "help": "prompt for Skype account password"},
             {"args": ["-c", "--chat"], "dest": "chat", "required": False,
              "help": "names of specific chats to sync", "nargs": "+"},
             {"args": ["-a", "--author"], "dest": "author", "required": False,
              "help": "names of specific authors whose chats to sync",
              "nargs": "+"},
             {"args": ["FILE"], "nargs": "+",
              "help": "Skype database file to sync", },
             {"args": ["--verbose"], "action": "store_true",
              "help": "print detailed progress messages to stderr"}, ],
        }, 
        {"name": "merge", "help": "merge two or more Skype databases "
                                  "into a new database",
         "description": "Merge two or more Skype database files into a new "
                        "database in current directory, with a full combined "
                        "message history. New filename will be generated "
                        "automatically. Last database in the list will "
                        "be used as base for comparison.",
         "arguments": [
             {"args": ["FILE1"], "metavar": "FILE1", "nargs": 1,
              "help": "first Skype database"},
             {"args": ["FILE2"], "metavar": "FILE2", "nargs": "+",
              "help": "more Skype databases"},
             {"args": ["--verbose"], "action": "store_true",
              "help": "print detailed progress messages to stderr"},
             {"args": ["-o", "--output"], "dest": "output", "required": False,
              "help": "Final database filename, auto-generated by default"},
              ]
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


logger = logging.getLogger(__package__)
window = None # Application main window instance


def except_hook(etype, evalue, etrace):
    """Handler for all unhandled exceptions."""
    mqueue = getattr(except_hook, "queue", [])
    setattr(except_hook, "queue", mqueue)

    text = "".join(traceback.format_exception(etype, evalue, etrace)).strip()
    log = "An unexpected error has occurred:\n\n%s"
    logger.error(log, text)
    if not conf.PopupUnexpectedErrors: return
    conf.UnexpectedErrorCount += 1
    msg = "An unexpected error has occurred:\n\n%s\n\n" \
          "See log for full details." % util.format_exc(evalue)
    mqueue.append(msg)

    def after():
        if not mqueue: return
        msg = mqueue[0]
        dlg = wx.RichMessageDialog(None, msg, conf.Title, wx.OK | wx.ICON_ERROR)
        if conf.UnexpectedErrorCount > 2:
            dlg.ShowCheckBox("&Do not pop up further errors")
        dlg.ShowModal()
        if dlg.IsCheckBoxChecked():
            conf.PopupUnexpectedErrors = False
            del mqueue[:]
            conf.save()
        if mqueue: mqueue.pop(0)
        if mqueue and conf.PopupUnexpectedErrors: wx.CallAfter(after)

    if len(mqueue) < 2: wx.CallAfter(after)


def install_thread_excepthook():
    """
    Workaround for sys.excepthook not catching threading exceptions.

    @from   https://bugs.python.org/issue1230540
    """
    init_old = threading.Thread.__init__
    def init(self, *args, **kwargs):
        init_old(self, *args, **kwargs)
        run_old = self.run
        def run_with_except_hook(*a, **b):
            try: run_old(*a, **b)
            except Exception: sys.excepthook(*sys.exc_info())
        self.run = run_with_except_hook
    threading.Thread.__init__ = init


def run_merge(filenames, output_filename=None):
    """Merges all Skype databases to a new database."""
    dbs = [skypedata.SkypeDatabase(f) for f in filenames]
    db_base = dbs.pop()
    counts = collections.defaultdict(lambda: collections.defaultdict(int))
    postbacks = Queue.Queue()

    name, ext = os.path.splitext(os.path.split(db_base.filename)[-1])
    now = datetime.datetime.now().strftime("%Y%m%d")
    if not output_filename:
        output_filename = util.unique_path("%s.merged.%s%s" %  (name, now, ext))
    output("Creating %s, using %s as base." % (output_filename, db_base))
    bar = ProgressBar()
    bar.start()
    shutil.copyfile(db_base.filename, output_filename)
    db2 = skypedata.SkypeDatabase(output_filename)
    chats2 = db2.get_conversations()
    db2.get_conversations_stats(chats2)

    args = {"db2": db2, "type": "diff_merge_left"}
    worker = workers.MergeThread(postbacks.put)
    try:
        for db1 in dbs:
            chats = db1.get_conversations()
            db1.get_conversations_stats(chats)
            bar.afterword = " Processing %.*s.." % (30, db1)
            worker.work(dict(args, db1=db1, chats=chats))
            while True:
                result = postbacks.get()
                if "error" in result:
                    output("Error merging %s:\n\n%s" % (db1, result["error"]))
                    db1 = None # Signal for global break
                    break # break while True
                if "done" in result:
                    break # break while True
                if "diff" in result:
                    counts[db1]["chats"] += 1
                    counts[db1]["msgs"] += len(result["diff"]["messages"])
                if "index" in result:
                    bar.max = result["count"]
                    bar.update(result["index"])
                if result.get("output"):
                    logger.info(result["output"])
            if not db1:
                break # break for db1 in dbs
            bar.stop()
            bar.afterword = " Processed %s." % db1
            bar.update(bar.max)
            output()
    finally:
        worker and (worker.stop(), worker.join())

    if not counts:
        output("Nothing new to merge.")
        db2.close()
        os.unlink(output_filename)
    else:
        for db1 in dbs:
            output("Merged %s in %s from %s." %
                  (util.plural("message", counts[db1]["msgs"]),
                   util.plural("chat", counts[db1]["chats"]), db1))
        output("Merge into %s complete." % db2)
        db2.close()


def run_search(filenames, query):
    """Searches the specified databases for specified query."""
    dbs = [skypedata.SkypeDatabase(f) for f in filenames]
    postbacks = Queue.Queue()
    args = {"text": query, "table": "messages", "output": "text"}
    worker = workers.SearchThread(postbacks.put)
    try:
        for db in dbs:
            logger.info('Searching "%s" in %s.', query, db)
            worker.work(dict(args, db=db))
            while True:
                result = postbacks.get()
                if "error" in result:
                    output("Error searching %s:\n\n%s" %
                          (db, result.get("error_short", result["error"])))
                    break # break while True
                if "done" in result:
                    logger.info("Finished searching for \"%s\" in %s.", query, db)
                    break # break while True
                if result.get("count", 0) or conf.IsCLIVerbose:
                    if len(dbs) > 1:
                        output("%s:" % db, end=" ")
                    output(result["output"])
    finally:
        worker and (worker.stop(), worker.join())


def run_sync(filenames, username=None, password=None, ask_password=False,
             store_password=False, chatnames=(), authornames=()):
    """Synchronizes history in specified database from Skype online service."""

    ns = {"bar": None, "chat_title": None, "filename": None}
    enc = sys.stdout.encoding or locale.getpreferredencoding() or "utf-8"
    def progress(result=None, **kwargs):
        result = result or kwargs

        if "error" in result:
            if ns["bar"]: ns["bar"] = ns["bar"].stop()
            output("\nError syncing chat history: %(error)s" % result)

        elif "contacts" == result.get("table"):
            if result.get("start"):
                ns["bar"] = ProgressBar(afterword=" Synchronizing contacts..")
                ns["bar"].start()
            elif result.get("end"):
                t = ", ".join("%s %s" % (result[k], k) for k in ("new", "updated") if result[k])
                ns["bar"].afterword = " Synchronized contacts%s." % (": %s" % t if t else "")
                ns["bar"].update(result["total"])
                ns["bar"] = ns["bar"].stop()
            else:
                ns["bar"].max = result["total"]
                if "count" in result:
                    t = (", %s new" % result["new"]) if result["new"] else ""
                    ns["bar"].afterword = " Synchronizing contacts, %s processed%s." % (result["count"], t)
                    ns["bar"].update(result["count"])

        elif "chats" == result.get("table"):
            if result.get("start"):
                output("\nSynchronizing chats..")
            elif result.get("end"):
                ns["bar"] = ns["bar"].stop()
                output("\n\nSynchronized %s%s in %s: %s in total%s." % (
                    util.plural("chat", result["count"]) if result["count"] else "chats",
                    " (%s new)" % result["new"] if result["new"] else "",
                    ns["filename"],
                    util.plural("new message", result["message_count_new"]),
                    ", %s updated" % result["message_count_updated"] if result["message_count_updated"] else ""
                ))

        elif "messages" == result.get("table"):
            if result.get("start"):
                cc = db.get_conversations(chatidentities=[result["chat"]], reload=True, log=False)
                chat = cc[0] if cc else None

                title = chat["title_long_lc"] if chat else result["chat"]
                if isinstance(title, unicode):
                    # Use encoded title for length constraint to work,
                    # if output would introduce escape sequences.
                    title2 = title.encode(enc, errors="backslashreplace")
                    if len(title2) != len(title): title = title2
                if len(title) > 25:
                    title = title[:25] + ".."
                    if chat and skypedata.CHATS_TYPE_GROUP == chat["type"]: title += '"'
                ns["chat_title"] = title
                if ns["bar"]:
                    ns["bar"].pulse_pos = 0
                    ns["bar"].pause = False
                    ns["bar"].afterword = " Synchronizing %s" % title
                else:
                    ns["bar"] = ProgressBar(pulse=True, interval=0.05,
                                            afterword=" Synchronizing %s" % title)
                    ns["bar"].start()

            elif result.get("end"):
                t = ""
                if any(result[k] for k in ("new", "updated")):
                    t += ": %s new" % result["new"]
                    if result["updated"]: t += ", %s updated" % result["updated"]

                ns["bar"].afterword = " Synchronized %s%s." % (ns["chat_title"], t)
                ns["bar"].pulse_pos = None
                ns["bar"].pause = True
                ns["bar"].update()
                if t: output() # Force new line if chat got updated

            else:
                t = ""
                for k in "new", "updated":
                    if result.get(k): t += ", %s %s" % (result[k], k)
                if t: t += "."
                ns["bar"].afterword = " Synchronizing %s%s" % (ns["chat_title"], t)

        return True


    username0, password0, passwords = username, password, {}
    for filename in filenames:
        filepath = os.path.realpath(filename)
        file_existed = os.path.exists(filepath)

        output("\nSynchronizing %s from live." % filename)

        username = username0
        prompt = "%s does not exist, enter Skype username: " % filename
        while not file_existed and not username:
            output(prompt, end="")
            username = raw_input().strip()

        if not file_existed:
            with open(filepath, "w"): pass
        db = skypedata.SkypeDatabase(filepath)
        username = db.id or username
        password = password0 or passwords.get(username)

        prompt = "%s does not contain account information, enter Skype username: " % filename
        while not username:
            output(prompt, end="")
            username = raw_input().strip()
            if username: break # while not db.id

        if not password and not ask_password \
        and conf.Login.get(filepath, {}).get("password"):
            password = util.deobfuscate(conf.Login[filepath]["password"])

        prompt = "Enter Skype password for '%s': " % username
        while not db.live.is_logged_in():
            if ask_password or not password:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore") # possible GetPassWarning
                    while not password:
                        output(prompt, end="") # getpass output can raise errors
                        password = getpass.getpass("", io.BytesIO()).strip()
                        prompt = "Enter Skype password for '%s': " % username

            passwords[username] = password
            output("Logging in to Skype as '%s'.." % username, end="")
            try: db.live.login(username, password)
            except Exception as e:
                prompt = "\n%s\n%s" % (util.format_exc(e), prompt)
            else: output(" success!")

        if store_password:
            conf.Login.setdefault(filename, {})
            conf.Login[filename].update(store=True, password=util.obfuscate(password0))
            conf.save()

        chats = []
        if chatnames or authornames:
            cc = db.get_conversations(chatnames, authornames)
            chats = [c["identity"] for c in cc]

        output()
        db.live.progress = progress
        ns["filename"] = filename
        try: db.live.populate(chats)
        except Exception as e: progress(error=util.format_exc(e))
        db.close()
    

def run_export(filenames, format, chatnames, authornames, start_date, end_date, ask_password, store_password):
    """Exports the specified databases in specified format."""
    dbs = [skypedata.SkypeDatabase(f) for f in filenames]
    is_xlsx_single = ("xlsx_single" == format)
    timerange = map(util.datetime_to_epoch, (start_date, end_date))

    for db in dbs:

        if (ask_password and db.id and conf.SharedImageAutoDownload
        and format.lower().endswith("html")):
            password, prompt = "", "Enter Skype password for '%s': " % db.id
            while not db.live.is_logged_in():
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore") # possible GetPassWarning
                    while not password:
                        output(prompt, end="") # getpass output can raise errors
                        password = getpass.getpass("", io.BytesIO()).strip()
                        prompt = "Enter Skype password for '%s': " % db.id

                try: db.live.login(db.id, password)
                except Exception as e:
                    prompt = "\n%s\n%s" % (util.format_exc(e), prompt)

            if store_password:
                conf.Login.setdefault(db.filename, {})
                conf.Login[db.filename].update(store=True, password=util.obfuscate(password))
                conf.save()

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
            extras = [("", chatnames)] if chatnames else []
            extras += [(" with authors", authornames)] if authornames else []
            output("Exporting%s%s as %s %sto %s." % 
                  (" chats" if extras else "",
                   ",".join("%s like %s" % (x, y) for x, y in extras),
                   format[:4].upper(), dbstr, target))
            chats = sorted(db.get_conversations(chatnames, authornames),
                           key=lambda x: x["title"].lower())
            db.get_conversations_stats(chats)
            bar_total = sum(c["message_count"] for c in chats)
            bartext = " Exporting %.*s.." % (30, db.filename) # Enforce width
            pulse = any(x is not None for x in timerange)
            bar = ProgressBar(max=bar_total, afterword=bartext, pulse=pulse)
            bar.start()
            result = export.export_chats(chats, export_dir, filename, db,
                                         timerange=timerange, progress=bar.update)
            files, count, message_count = result
            bar.stop()
            if count:
                bar.afterword = " Exported %s from %s to %s. " % (
                    util.plural("message", message_count), db, target)
                bar.update(bar_total)
                output()
                logger.info("Exported %s and %s %sto %s as %s.",
                            util.plural("chat", count),
                            util.plural("message", message_count),
                            dbstr, target, format)
            else:
                output("\nNo messages to export%s." %
                      ("" if len(dbs) == 1 else " from %s" % db))
                os.unlink(filename) if is_xlsx_single else os.rmdir(export_dir)
        except Exception as e:
            output("Error exporting chats: %s\n\n%s" % 
                  (e, traceback.format_exc()))


def run_diff(filename1, filename2):
    """Compares the first database for changes with the second."""
    if os.path.realpath(filename1) == os.path.realpath(filename2):
        output("Error: cannot compare %s with itself." % filename1)
        return
    db1, db2 = map(skypedata.SkypeDatabase, [filename1, filename2])
    counts = collections.defaultdict(lambda: collections.defaultdict(int))
    postbacks = Queue.Queue()

    bar_text = "%.*s.." % (50, " Scanning %s vs %s" % (db1, db2))
    bar = ProgressBar(afterword=bar_text)
    bar.start()
    chats1, chats2 = db1.get_conversations(), db2.get_conversations()
    db1.get_conversations_stats(chats1), db2.get_conversations_stats(chats2)

    args = {"db1": db1, "db2": db2, "chats": chats1, "type": "diff_left"}
    worker = workers.MergeThread(postbacks.put)
    try:
        worker.work(args)
        while True:
            result = postbacks.get()
            if "error" in result:
                output("Error scanning %s and %s:\n\n%s" %
                      (db1, db2, result["error"]))
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
                bar.afterword = (" %s, %s." % (result["chats"][0]["chat"]["title"],
                                    text))
                counts[db1]["msgs"] += msgs
            if "index" in result:
                bar.max = result["count"]
                bar.update(result["index"])
            if result.get("output"):
                logger.info(result["output"])
    finally:
        worker and (worker.stop(), worker.join())

    bar.stop()
    bar.afterword = " Scanned %s and %s." % (db1, db2)
    bar.update(bar.max)
    output()


def run_gui(filenames):
    """Main GUI program entrance."""
    global logger, window

    # Set up logging to GUI log window
    logger.addHandler(guibase.GUILogHandler())
    logger.setLevel(logging.DEBUG)

    install_thread_excepthook()
    sys.excepthook = except_hook

    # Create application main window
    app = wx.App(redirect=True) # stdout and stderr redirected to wx popup
    # Avoid dialog buttons in native language
    mylocale = wx.Locale(wx.LANGUAGE_ENGLISH_US, wx.LOCALE_LOAD_DEFAULT)
    mylocale.AddCatalog("wxstd")
    window = gui.MainWindow()
    app.SetTopWindow(window) # stdout/stderr popup closes with MainWindow

    # Some debugging support
    window.run_console("import datetime, os, re, time, sys, wx")
    window.run_console("# All %s modules:" % conf.Title)
    window.run_console("from skyperious import conf, emoticons, export, "
                       "gui, guibase, images, live, main, searchparser, "
                       "skypedata, support, templates, workers")
    window.run_console("from skyperious.lib import controls, util, wordcloud, wx_accel")

    window.run_console("self = wx.GetApp().TopWindow # Application main window instance")
    logger.info("Started application.")
    for f in filter(os.path.isfile, filenames):
        wx.CallAfter(wx.PostEvent, window, gui.OpenDatabaseEvent(file=f))
    app.MainLoop()


def run(nogui=False):
    """Parses command-line arguments and either runs GUI, or a CLI action."""
    global is_gui_possible, logger

    if (getattr(sys, 'frozen', False) # Binary application
    or sys.executable.lower().endswith("pythonw.exe")):
        sys.stdout = ConsoleWriter(sys.stdout) # Hooks for attaching to 
        sys.stderr = ConsoleWriter(sys.stderr) # a text console
    if "main" not in sys.modules: # E.g. setuptools install, calling main.run
        srcdir = os.path.abspath(os.path.dirname(__file__))
        if srcdir not in sys.path: sys.path.append(srcdir)
        #sys.modules["main"] = __import__("main")

    argparser = argparse.ArgumentParser(description=ARGUMENTS["description"])
    for arg in ARGUMENTS["arguments"]:
        argparser.add_argument(*arg.pop("args"), **arg)
    subparsers = argparser.add_subparsers(dest="command")
    for cmd in ARGUMENTS["commands"]:
        kwargs = dict((k, cmd[k]) for k in cmd if k in ["help", "description"])
        subparser = subparsers.add_parser(cmd["name"], **kwargs)
        for arg in cmd["arguments"]:
            kwargs = dict((k, arg[k]) for k in arg if k != "args")
            subparser.add_argument(*arg["args"], **kwargs)

    if "nt" == os.name: # Fix Unicode arguments, otherwise converted to ?
        sys.argv[:] = win32_unicode_argv()
    argv = sys.argv[1:]
    if not argv or (argv[0] not in subparsers.choices
    and argv[0].endswith(".db")):
        argv[:0] = ["gui"] # argparse hack: force default argument
    if argv[0] in ("-h", "--help") and len(argv) > 1:
        argv[:2] = argv[:2][::-1] # Swap "-h option" to "option -h"

    arguments, _ = argparser.parse_known_args(argv)

    if hasattr(arguments, "FILE1") and hasattr(arguments, "FILE2"):
        arguments.FILE1 = [util.to_unicode(f) for f in arguments.FILE1]
        arguments.FILE2 = [util.to_unicode(f) for f in arguments.FILE2]
        arguments.FILE = arguments.FILE1 + arguments.FILE2
    if arguments.FILE: # Expand wildcards to actual filenames
        arguments.FILE = sum([glob.glob(f) if "*" in f else [f]
                              for f in arguments.FILE], [])
        arguments.FILE = sorted(set(util.to_unicode(f) for f in arguments.FILE))

    conf.load()
    if "gui" == arguments.command and (nogui or not is_gui_possible):
        argparser.print_help()
        status = None
        if not nogui: status = ("\n\nwxPython not found. %s graphical program "
                                "will not run." % conf.Title)
        sys.exit(status)
    elif "gui" != arguments.command:
        conf.IsCLI = True
        conf.IsCLIVerbose = arguments.verbose
        # Avoid Unicode errors when printing to console.
        enc = sys.stdout.encoding or locale.getpreferredencoding() or "utf-8"
        sys.stdout = codecs.getwriter(enc)(sys.stdout, "backslashreplace")
        sys.stderr = codecs.getwriter(enc)(sys.stderr, "backslashreplace")

        if conf.IsCLIVerbose:
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(logging.Formatter("%(asctime)s\t%(message)s"))
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)
        else:
            logger.addHandler(logging.NullHandler())

    if "diff" == arguments.command:
        run_diff(*arguments.FILE)
    elif "merge" == arguments.command:
        run_merge(arguments.FILE, arguments.output)
    elif "export" == arguments.command:
        run_export(arguments.FILE, arguments.type, arguments.chat, arguments.author,
                   arguments.start_date, arguments.end_date,
                   arguments.ask_password, arguments.store_password)
    elif "search" == arguments.command:
        run_search(arguments.FILE, arguments.QUERY)
    elif "sync" == arguments.command:
        run_sync(arguments.FILE, arguments.username, arguments.password,
                 arguments.ask_password, arguments.store_password,
                 arguments.chat, arguments.author)
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
                self.init_console()

            try: self.realwrite(text), self.flush()
            except Exception: self.stream.write(text)
        else:
            self.stream.write(text)


    def init_console(self):
        """Sets up connection to console."""
        try:
            win32console.AttachConsole(-1) # pythonw.exe from console
            atexit.register(lambda: ConsoleWriter.realwrite("\n"))
        except Exception:
            pass # Okay if fails: can be python.exe from console
        try:
            handle = win32console.GetStdHandle(
                                  win32console.STD_OUTPUT_HANDLE)
            handle.WriteConsole("\n")
            ConsoleWriter.handle = handle
            ConsoleWriter.realwrite = handle.WriteConsole
        except Exception: # Fails if GUI program: make new console
            try: win32console.FreeConsole()
            except Exception: pass
            try:
                win32console.AllocConsole()
                handle = open("CONOUT$", "w")
                argv = [util.longpath(sys.argv[0])] + sys.argv[1:]
                handle.write(" ".join(argv) + "\n\n")
                handle.flush()
                ConsoleWriter.handle = handle
                ConsoleWriter.realwrite = handle.write
                sys.stdin = open("CONIN$", "r")
                atexit.register(self.on_exe_exit)
            except Exception:
                try: win32console.FreeConsole()
                except Exception: pass
                ConsoleWriter.realwrite = self.stream.write
        ConsoleWriter.is_loaded = True


    def on_exe_exit(self):
        """atexit handler for compiled binary, keeps window open for a minute."""
        countdown = 60
        try:
            self.write("\n")
            while countdown:
                output("\rClosing window in %s.." % countdown, end=" ")
                time.sleep(1)
                countdown -= 1
        except Exception: pass



class ProgressBar(threading.Thread):
    """
    A simple ASCII progress bar with a ticker thread, drawn like
    '[---------\   36%            ] Progressing text..'.
    or for pulse mode
    '[    ----                    ] Progressing text..'.
    """

    def __init__(self, max=100, value=0, min=0, width=30, forechar="-",
                 backchar=" ", foreword="", afterword="", interval=1, pulse=False):
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
        @param   pulse      ignore value-min-max, use constant pulse instead
        """
        threading.Thread.__init__(self)
        for k, v in locals().items(): setattr(self, k, v) if "self" != k else 0
        self.daemon = True # Daemon threads do not keep application running
        self.percent = None        # Current progress ratio in per cent
        self.value = None          # Current progress bar value
        self.pause = False         # Whether drawing is currently paused
        self.pulse_pos = 0         # Current pulse position
        self.bar = "%s[%s%s]%s" % (foreword,
                                   backchar if pulse else forechar,
                                   backchar * (width - 3),
                                   afterword)
        self.printbar = self.bar   # Printable text, with padding to clear previous
        self.progresschar = itertools.cycle("-\\|/")
        self.is_running = False
        if not pulse: self.update(value, draw=False)


    def update(self, value=None, draw=True):
        """Updates the progress bar value, and refreshes by default."""
        if value is not None: self.value = min(self.max, max(self.min, value))
        w_full = self.width - 2
        if self.pulse:
            if self.pulse_pos is None:
                bartext = "%s[%s]%s" % (self.foreword,
                                        self.forechar * (self.width - 2),
                                        self.afterword)
            else:
                dash = self.forechar * max(1, (self.width - 2) / 7)
                pos = self.pulse_pos
                if pos < len(dash):
                    dash = dash[:pos]
                elif pos >= self.width - 1:
                    dash = dash[:-(pos - self.width - 2)]

                bar = "[%s]" % (self.backchar * w_full)
                # Write pulse dash into the middle of the bar
                pos1 = min(self.width - 1, pos + 1)
                bar = bar[:pos1 - len(dash)] + dash + bar[pos1:]
                bartext = "%s%s%s" % (self.foreword, bar, self.afterword)
                self.pulse_pos = (self.pulse_pos + 1) % (self.width + 2)
        else:
            new_percent = int(round(100.0 * self.value / (self.max or 1)))
            w_done = max(1, int(round((new_percent / 100.0) * w_full)))
            # Build bar outline, animate by cycling last char from progress chars
            char_last = self.forechar
            if draw and w_done < w_full: char_last = next(self.progresschar)
            bartext = "%s[%s%s%s]%s" % (
                       self.foreword, self.forechar * (w_done - 1), char_last,
                       self.backchar * (w_full - w_done), self.afterword)
            # Write percentage into the middle of the bar
            centertxt = " %2d%% " % new_percent
            pos = len(self.foreword) + self.width / 2 - len(centertxt) / 2
            bartext = bartext[:pos] + centertxt + bartext[pos + len(centertxt):]
            self.percent = new_percent
        self.printbar = bartext + " " * max(0, len(self.bar) - len(bartext))
        self.bar = bartext
        if draw: self.draw()


    def draw(self):
        """Prints the progress bar, from the beginning of the current line."""
        output("\r" + self.printbar, end=" ")


    def run(self):
        self.is_running = True
        while self.is_running:
            if not self.pause: self.update(self.value)
            time.sleep(self.interval)


    def stop(self):
        self.is_running = False


def win32_unicode_argv():
    # @from http://stackoverflow.com/a/846931/145400
    result = sys.argv
    from ctypes import POINTER, byref, cdll, c_int, windll
    from ctypes.wintypes import LPCWSTR, LPWSTR
 
    GetCommandLineW = cdll.kernel32.GetCommandLineW
    GetCommandLineW.argtypes = []
    GetCommandLineW.restype = LPCWSTR
 
    CommandLineToArgvW = windll.shell32.CommandLineToArgvW
    CommandLineToArgvW.argtypes = [LPCWSTR, POINTER(c_int)]
    CommandLineToArgvW.restype = POINTER(LPWSTR)
 
    argc = c_int(0)
    argv = CommandLineToArgvW(GetCommandLineW(), byref(argc))
    if argc.value:
        # Remove Python executable and commands if present
        start = argc.value - len(sys.argv)
        result = [argv[i].encode("utf-8") for i in range(start, argc.value)]
    return result


def output(s="", **kwargs):
    """Print wrapper, avoids "Broken pipe" errors if piping is interrupted."""
    try: print(s, **kwargs)
    except UnicodeError:
        try:
            if isinstance(s, str): print(s.decode(errors="replace"), **kwargs)
        except Exception: pass
    try:
        sys.stdout.flush() # Uncatchable error otherwise if interrupted
    except IOError as e:
        if e.errno in (errno.EINVAL, errno.EPIPE):
            sys.exit() # Stop work in progress if sys.stdout or pipe closed
        raise # Propagate any other errors


if "__main__" == __name__:
    try: run()
    except KeyboardInterrupt: sys.exit()
