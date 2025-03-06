# -*- coding: utf-8 -*-
"""
Skyperious main program entrance: launches GUI application or executes command
line interface, handles logging and status calls.

------------------------------------------------------------------------------
This file is part of Skyperious - Skype chat history tool.
Released under the MIT License.

@author      Erki Suurjaak
@created     26.11.2011
@modified    02.12.2024
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
import os
import re
import shutil
import sys
import textwrap
import threading
import time
import traceback
import warnings

import six
from six.moves import queue
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
from . import live
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
         "version": "%s %s, %s." % (conf.Title, conf.Version, conf.VersionDate)},
        {"args": ["--no-terminal"], "action": "store_true", "dest": "no_terminal",
         "help": "command-line output suitable for non-terminal display, "
                 "like piping to a file"},
        {"args": ["--config-file"], "dest": "config_file", "nargs": 1,
         "help": "path of configuration file to use"}
    ],
    "commands": [
        {"name": "export",
         "help": "export Skype databases as HTML, text or spreadsheet",
         "description": "Export all message history from a Skype database "
                        "into files under a new folder" + (", or a single Excel "
                        "workbook with chats on separate sheets."
                        if export.xlsxwriter else ""),
         "arguments": [
             {"args": ["-t", "--type"], "dest": "format",
              "choices": ["html", "xlsx", "csv", "txt", "xlsx_single"]
                         if export.xlsxwriter else ["html", "csv", "txt"],
              "default": "html", "required": False, "type": str.lower,
              "help": "export type: HTML files (default), Excel workbooks, "
                      "CSV spreadsheets, text files, or a single Excel "
                      "workbook with separate sheets" if export.xlsxwriter
                      else
                      "export type: HTML files (default), CSV spreadsheets, "
                      "text files"},
             {"args": ["FILE"], "nargs": "+",
              "help": "one or more Skype databases to export\n"
                      "(supports * wildcards)"},
             {"args": ["-o", "--output"], "dest": "output_dir",
              "metavar": "DIR", "required": False,
              "help": "output directory if not current directory"},
             {"args": ["-c", "--chat"], "dest": "chats", "metavar": "CHAT", "required": False,
              "help": "names of specific chats to export", "nargs": "+"},
             {"args": ["-a", "--author"], "dest": "authors", "metavar": "NAME", "required": False,
              "help": "names of specific authors whose chats to export",
              "nargs": "+"},
             {"args": ["-s", "--start"], "dest": "start_date", "required": False,
              "help": "date to export messages from, as YYYY-MM-DD", "type": date},
             {"args": ["-e", "--end"], "dest": "end_date", "required": False,
              "help": "date to export messages until, as YYYY-MM-DD", "type": date},
             {"args": ["--media-folder"], "dest": "media_folder",
              "action": "store_true", "required": False,
              "help": "save shared media into a subfolder in HTML export "
                      "instead of embedding into HTML"},
             {"args": ["--media-cache"], "dest": "media_cache",
              "action": "store_true", "required": False,
              "help": "cache downloaded media in user directory, "
                      "for faster repeated exports"},
             {"args": ["-p", "--password"], "dest": "password",
              "help": "password for Skype account to download shared media in HTML export,\n"
                      "if not using stored or prompted"},
             {"args": ["--ask-password"], "dest": "ask_password",
              "action": "store_true", "required": False,
              "help": "prompt for Skype password on HTML export "
                      "to download shared media"},
             {"args": ["--store-password"], "dest": "store_password",
              "action": "store_true", "required": False,
              "help": "store entered password in configuration"},
             {"args": ["--verbose"], "action": "store_true",
              "help": "print detailed progress messages to stderr"},
             {"args": ["--no-terminal"], "action": "store_true", "dest": "no_terminal",
              "help": "command-line output suitable for non-terminal display, "
                      "like piping to a file"},
             {"args": ["--config-file"], "dest": "config_file", "nargs": 1,
              "help": "path of configuration file to use"},
        ]},
        {"name": "search",
         "help": "search Skype databases for messages or data",
         "description": "Search Skype databases for messages, chat or contact "
                        "information, or table data.",
         "arguments": [
             {"args": ["-t", "--type"], "dest": "category", "required": False,
              "choices": ["message", "contact", "chat", "table"],
              "default": "message",
              "help": "search in message body (default), in contact "
                      "information, in chat title and participants, or in any "
                      "database table"},
             {"args": ["query"], "metavar": "QUERY",
              "help": "search query, with a simple query syntax, for example: "
                      "\"this OR that chat:links from:john\". More on syntax "
                      "at https://suurjaak.github.io/Skyperious/help.html. " },
             {"args": ["FILE"], "nargs": "+",
              "help": "Skype database file(s) to search\n"
                      "(supports * wildcards)"},
             {"args": ["--limit"], "type": int,
              "help": "maximum number of matches to find"},
             {"args": ["--offset"], "type": int,
              "help": "number of matches to skip from the beginning"},
             {"args": ["--reverse"], "action": "store_true",
              "help": "find matches in reverse order"},
             {"args": ["--verbose"], "action": "store_true",
              "help": "print detailed progress messages to stderr"},
             {"args": ["--config-file"], "dest": "config_file", "nargs": 1,
              "help": "path of configuration file to use"},
        ]},
        {"name": "sync",
         "help": "download new messages from Skype online service",
         "description": "Synchronize Skype database via login to Skype online service.",
         "arguments": [
             {"args": ["-u", "--username"], "dest": "username",
              "help": "username for Skype account, used only if the Skype database "
                      "does not contain account information yet"},
             {"args": ["-p", "--password"], "dest": "password",
              "help": "password for Skype account, if not using stored or prompted"},
             {"args": ["--ask-password"], "dest": "ask_password",
              "action": "store_true", "required": False,
              "help": "prompt for Skype account password"},
             {"args": ["--store-password"], "dest": "store_password",
              "action": "store_true", "required": False,
              "help": "store given password in configuration"},
             {"args": ["--contact-update"], "dest": "sync_contacts",
              "action": "store_true", "required": False, "default": None,
              "help": "update profile fields of existing contacts "
                      "from online data (default)"},
             {"args": ["--no-contact-update"], "dest": "sync_contacts",
              "action": "store_false", "required": False, "default": None,
              "help": "do not update profile fields of existing contacts "
                      "from online data"},
             {"args": ["--check-older"], "dest": "sync_older",
              "action": "store_true", "required": False, "default": None,
              "help": "check all older chats in database for messages to sync, "
                      "may take a long time (default)"},
             {"args": ["--no-check-older"], "dest": "sync_older",
              "action": "store_false", "required": False, "default": None,
              "help": "do not check all older chats in database for messages to sync"},
             {"args": ["-c", "--chat"], "dest": "chats", "metavar": "CHAT", "required": False,
              "help": "names of specific chats to sync", "nargs": "+"},
             {"args": ["-a", "--author"], "dest": "authors", "metavar": "NAME", "required": False,
              "help": "names of specific authors whose chats to sync",
              "nargs": "+"},
             {"args": ["FILE"], "nargs": "+",
              "help": "Skype database file(s) to sync (supports * wildcards), "
                      "will be created if it does not exist yet"},
             {"args": ["--verbose"], "action": "store_true",
              "help": "print detailed progress messages to stderr"},
             {"args": ["--no-terminal"], "action": "store_true", "dest": "no_terminal",
              "help": "command-line output suitable for non-terminal display, "
                      "like piping to a file; also skips all user interaction "
                      "like asking for Skype username or password"},
             {"args": ["--config-file"], "dest": "config_file", "nargs": 1,
              "help": "path of configuration file to use"},
        ]},
        {"name": "contacts",
         "help": "export Skype contacts as HTML, text or spreadsheet",
         "description": "Export contacts from a Skype database into file.",
         "arguments": [
             {"args": ["-t", "--type"], "dest": "format",
              "choices": ["html", "xlsx", "csv", "txt"]
                         if export.xlsxwriter else ["html", "csv", "txt"],
              "default": "html", "required": False, "type": str.lower,
              "help": "export type: HTML files (default), Excel workbooks, "
                      "CSV spreadsheets, text files" if export.xlsxwriter
                      else
                      "export type: HTML files (default), CSV spreadsheets, "
                      "text files"},
             {"args": ["FILE"], "nargs": "+",
              "help": "Skype databases to process (supports * wildcards)"},
             {"args": ["-o", "--output"], "dest": "output",
              "metavar": "FILE", "required": False,
              "help": "output filename if not using auto-generated"},
             {"args": ["-f", "--filter"], "dest": "fields", "metavar": "TEXT",
              "nargs": "+", "required": False,
              "help": "select contacts with given texts in any profile fields"},
             {"args": ["-n", "--name"], "dest": "names", "metavar": "NAME",
              "nargs": "+", "required": False,
              "help": "names of specific contacts to select"},
             {"args": ["-c", "--chat"], "dest": "chats", "metavar": "CHAT",
              "nargs": "+", "required": False,
              "help": "names of chats to select contacts by"},
             {"args": ["--verbose"], "action": "store_true",
              "help": "print detailed progress messages to stderr"},
             {"args": ["--no-terminal"], "action": "store_true", "dest": "no_terminal",
              "help": "command-line output suitable for non-terminal display, "
                      "like piping to a file; also skips all user interaction "
                      "like asking for Skype username or password"},
             {"args": ["--config-file"], "dest": "config_file", "nargs": 1,
              "help": "path of configuration file to use"},
        ]},
        {"name": "create",
         "help": "create a new database, blank or from a Skype source",
         "description": "Create a new blank database, or populated from "
                        "Skype online service, or from a Skype export archive.",
         "arguments": [
             {"args": ["-i", "--input"], "dest": "input",
              "help": "Skype export archive to populate from (*.json;*.tar)"},
             {"args": ["-u", "--username"], "dest": "username",
              "help": "Skype username, for a blank database if no password"},
             {"args": ["-p", "--password"], "dest": "password",
              "help": "password for populating database from Skype online service"},
             {"args": ["--ask-password"], "dest": "ask_password",
              "action": "store_true", "required": False,
              "help": "prompt for Skype account password"},
             {"args": ["--store-password"], "dest": "store_password",
              "action": "store_true", "required": False,
              "help": "store given password in configuration"},
             {"args": ["FILE"], "nargs": 1,
              "help": "Skype database file to create. Skipped if exists."},
             {"args": ["--verbose"], "action": "store_true",
              "help": "print detailed progress messages to stderr"},
             {"args": ["--no-terminal"], "action": "store_true", "dest": "no_terminal",
              "help": "command-line output suitable for non-terminal display, "
                      "like piping to a file; also skips all user interaction "
                      "like asking for Skype username or password"},
             {"args": ["--config-file"], "dest": "config_file", "nargs": 1,
              "help": "path of configuration file to use"},
        ]},
        {"name": "merge", "help": "merge two or more Skype databases "
                                  "into a new database",
         "description": "Merge two or more Skype database files into a new "
                        "database in current directory, with a full combined "
                        "message history. New filename will be generated "
                        "automatically. Last database in the list will "
                        "be used as base for comparison.",
         "arguments": [
             {"args": ["FILE"], "metavar": "FILE", "nargs": "+",
              "help": "two or more Skype databases to merge\n"
                      "(supports * wildcards)"},
             {"args": ["-o", "--output"], "dest": "output", "required": False,
              "help": "Final database filename, auto-generated by default"},
             {"args": ["--verbose"], "action": "store_true",
              "help": "print detailed progress messages to stderr"},
             {"args": ["--no-terminal"], "action": "store_true", "dest": "no_terminal",
              "help": "command-line output suitable for non-terminal display, "
                      "like piping to a file"},
             {"args": ["--config-file"], "dest": "config_file", "nargs": 1,
              "help": "path of configuration file to use"},
        ]},
        {"name": "diff", "help": "compare chat history in two Skype databases",
         "description": "Compare two Skype databases for differences "
                        "in chat history.",
         "arguments": [
             {"args": ["FILE1"], "help": "first Skype database", "nargs": 1},
             {"args": ["FILE2"], "help": "second Skype databases", "nargs": 1},
             {"args": ["--verbose"], "action": "store_true",
              "help": "print detailed progress messages to stderr"},
             {"args": ["--no-terminal"], "action": "store_true", "dest": "no_terminal",
              "help": "command-line output suitable for non-terminal display, "
                      "like piping to a file"},
             {"args": ["--config-file"], "dest": "config_file", "nargs": 1,
              "help": "path of configuration file to use"},
        ]},
        {"name": "gui",
         "help": "launch Skyperious graphical program (default option)",
         "description": "Launch Skyperious graphical program (default option)",
         "arguments": [
             {"args": ["FILE"], "nargs": "*",
              "help": "Skype database(s) to open on startup, if any\n"
                      "(supports * wildcards)"},
             {"args": ["--config-file"], "dest": "config_file", "nargs": 1,
              "help": "path of configuration file to use"},
        ]},
    ],
}


logger = logging.getLogger(__package__)
window = None # Application main window instance


class MainApp(wx.App if wx else object):

    def InitLocale(self):
        self.ResetLocale()
        if "win32" == sys.platform:  # Avoid dialog buttons in native language
            mylocale = wx.Locale(wx.LANGUAGE_ENGLISH_US, wx.LOCALE_LOAD_DEFAULT)
            mylocale.AddCatalog("wxstd")
            self._initial_locale = mylocale  # Override wx.App._initial_locale
            # Workaround for MSW giving locale as "en-US"; standard format is "en_US".
            # Py3 provides "en[-_]US" in wx.Locale names and accepts "en" in locale.setlocale();
            # Py2 provides "English_United States.1252" in wx.Locale.SysName and accepts only that.
            name = mylocale.SysName if sys.version_info < (3, ) else mylocale.Name.split("_", 1)[0]
            try: locale.setlocale(locale.LC_ALL, name)
            except Exception: logger.warning("Failed to set locale %r.", name, exc_info=True)


class LineSplitFormatter(argparse.HelpFormatter):
    """Formatter for argparse that retains newlines in help texts."""

    def _split_lines(self, text, width):
        return sum((textwrap.wrap(re.sub(r"\s+", " ", t).strip(), width)
                    for t in text.splitlines()), [])


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


def run_merge(filenames, args):
    """
    Merges all Skype databases to a new database.

    @param   args       argparse.Namespace
               output   name of output database, auto-generated if not given
    """
    dbs = [skypedata.SkypeDatabase(f) for f in filenames]
    db_base = dbs.pop()
    counts = collections.defaultdict(lambda: collections.defaultdict(int))
    postbacks = queue.Queue()

    name, ext = os.path.splitext(os.path.basename(db_base.filename))
    now = datetime.datetime.now().strftime("%Y%m%d")
    output_filename = args.output or util.unique_path("%s.merged.%s%s" %  (name, now, ext))
    output("Creating %s, using %s as base." % (output_filename, db_base))
    bar = ProgressBar(static=conf.IsCLINonTerminal)
    bar.start()
    shutil.copyfile(db_base.filename, output_filename)
    db2 = skypedata.SkypeDatabase(output_filename)

    args = {"db2": db2, "type": "diff_merge_left"}
    worker = workers.MergeThread(postbacks.put)
    bar.stop()
    try:
        for db1 in dbs:
            AFTER_MAX = sys.maxsize if conf.IsCLINonTerminal else 30
            bar = ProgressBar(static=conf.IsCLINonTerminal,
                              afterword=" Processing %s%s.." % (
                              "..." if len(db1.filename) > AFTER_MAX else "",
                              db1.filename[-AFTER_MAX:]))
            bar.start()
            chats = db1.get_conversations()
            db1.get_conversations_stats(chats)
            db2.get_conversations_stats(db2.get_conversations(reload=True))
            worker.work(dict(args, db1=db1, chats=chats))
            while True:
                result = postbacks.get()
                if "error" in result:
                    output("Error merging %s:\n\n%s" % (db1, result["error"]))
                    db1 = None # Signal for global break
                    break # while True
                if "done" in result:
                    bar.value, bar.max = 100, 100
                    break # while True
                if "diff" in result:
                    counts[db1]["chats"] += 1
                    counts[db1]["msgs"] += len(result["diff"]["messages"])
                if "index" in result:
                    bar.max = result["count"]
                    if not conf.IsCLINonTerminal: bar.update(result["index"])
                if result.get("output"):
                    logger.info(result["output"])
            bar.stop()
            if not db1:
                break # for db1
            bar.afterword = " Processed %s." % db1
            bar.update() # Lay out full filename, probably wraps to next line
            output() # Force linefeed for next progress bar
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


def run_search(filenames, args):
    """
    Searches the specified databases for specified query.

    @param   args         argparse.Namespace
               query      search query text
               category   search category like "message"
               reverse    find matches in reverse order
               offset     number of matches to skip from the beginning
               limit      maximum number of matches to find
    """
    TABLES = {"message": "messages", "contact": "contacts", "chat": "conversations",
              "table": "all tables"}
    dbs = [skypedata.SkypeDatabase(f) for f in filenames]
    postbacks = queue.Queue()
    wargs = {"text": args.query, "reverse": args.reverse, "offset": args.offset,
             "limit": args.limit, "table": TABLES.get(args.category, args.category),
             "output": "text"}
    worker = workers.SearchThread(postbacks.put)
    try:
        for db in dbs:
            logger.info('Searching "%s" in %s %s.', args.query, db, wargs["table"])
            worker.work(dict(wargs, db=db))
            while True:
                result = postbacks.get()
                if "error" in result:
                    output("Error searching %s:\n\n%s" %
                          (db, result.get("error_short", result["error"])))
                    break # while True
                if "done" in result:
                    logger.info("Finished searching for \"%s\" in %s %s.",
                                args.query, db, wargs["table"])
                    break # while True
                if result.get("count", 0) or conf.IsCLIVerbose:
                    if len(dbs) > 1:
                        output("%s:" % db, end=" ")
                    output(result["output"])
    finally:
        worker and (worker.stop(), worker.join())


def run_sync(filenames, args):
    """
    Synchronizes history in specified databases from Skype online service.

    @param   args               argparse.Namespace
               username         Skype username
               password         Skype password
               ask_password     whether to ask password on the command line interactively
               store_password   whether to store password in configuration file
               sync_contacts    whether to update profile fields of existing contacts
               sync_older       whether to check all older chats in database for messages to sync
               chats            names of specific chats to export
               authors          names of specific authors whose chats to export
    """
    ns = {"bar": None, "chat_title": None, "filename": None}
    enc = sys.stdout.encoding or locale.getpreferredencoding() or "utf-8"
    def progress(result=None, **kwargs):
        result = result or kwargs

        if "error" in result:
            if ns["bar"]: ns["bar"] = ns["bar"].stop()
            output("\nError syncing chat history: %(error)s" % result)

        elif "chats" == result.get("table"):
            if result.get("start"):
                output("\nSynchronizing chats..")
            elif result.get("end"):
                ns["bar"].pulse_pos = None
                ns["bar"].value = ns["bar"].max
                ns["bar"].afterword = " Complete."
                ns["bar"].update()
                ns["bar"] = ns["bar"].stop()
                output("\n\nSynchronized %s%s in %s: %s in total%s." % (
                    util.plural("chat", result["count"]) if result["count"] else "chats",
                    " (%s new)" % result["new"] if result["new"] else "",
                    ns["filename"],
                    util.plural("new message", result["message_count_new"]),
                    ", %s updated" % result["message_count_updated"] if result["message_count_updated"] else ""
                ))
                if result["contact_count_new"] or result["contact_count_updated"]:
                    output("%s." % ", ".join(filter(bool, [
                        util.plural("new contact", result["contact_count_new"], sep=",")
                        if result["contact_count_new"] else "",
                        util.plural("contact", result["contact_count_updated"], sep=",") + " updated"
                        if result["contact_count_updated"] else "",
                    ])))

        elif "messages" == result.get("table"):
            if result.get("start"):
                cc = db.get_conversations(chatidentities=[result["chat"]], reload=True, log=False)
                chat = cc[0] if cc else None

                title = chat["title_long_lc"] if chat else result["chat"]
                if isinstance(title, six.text_type):
                    # Use encoded title for length constraint to work,
                    # if output would introduce escape sequences.
                    title2 = title.encode(enc, errors="backslashreplace")
                    if len(title2) != len(title): title = title2
                AFTER_MAX = sys.maxsize if conf.IsCLINonTerminal else 25
                if len(title) > AFTER_MAX:
                    title = title[:AFTER_MAX] + ".."
                    if chat and skypedata.CHATS_TYPE_GROUP == chat["type"]: title += '"'
                suff = ".." if conf.IsCLINonTerminal else ""
                if ns["bar"]:
                    ns["bar"].pulse     = True
                    ns["bar"].pulse_pos = 0
                    ns["bar"].afterword = " Synchronizing %s%s" % (title, suff)
                    if title != ns["chat_title"]: ns["bar"].update()
                    ns["bar"].pause = False
                else:
                    ns["bar"] = ProgressBar(pulse=True, interval=0.05,
                                            static=conf.IsCLINonTerminal,
                                            afterword=" Synchronizing %s%s" %
                                            (title, suff))
                    ns["bar"].start()
                ns["chat_title"] = title

            elif result.get("end"):
                t = ""
                if any(result[k] for k in ("new", "updated")):
                    t += ": %s new" % result["new"]
                    if result["updated"]: t += ", %s updated" % result["updated"]

                ns["bar"].pause = True
                ns["bar"].afterword = " Synchronized %s%s." % (ns["chat_title"], t)
                ns["bar"].pulse_pos = None
                ns["bar"].update()
                if t and not conf.IsCLINonTerminal:
                    output() # Force new line if chat got updated

            else:
                t = ""
                for k in "new", "updated":
                    if result.get(k): t += ", %s %s" % (result[k], k)
                if t: t += "."
                ns["bar"].afterword = " Synchronizing %s%s" % (ns["chat_title"], t)

        elif "info" == result.get("action") and result.get("message"):
            if not ns["bar"]:
                ns["bar"] = ProgressBar(pulse=True, interval=0.05,
                                        static=conf.IsCLINonTerminal)
                ns["bar"].start()
            ns["bar"].afterword = " %s" % result["message"].strip()
            ns["bar"].pulse_pos = 0
            if "index" in result and "count" in result:
                ns["bar"].pulse = False
                ns["bar"].value = result["index"]
                ns["bar"].max   = result["count"]
            ns["bar"].update()
            ns["bar"].pause = False

        return True


    username0, password0, passwords = args.username, args.password, {}
    for filename in filenames:
        filepath = os.path.realpath(filename)
        file_existed = os.path.exists(filepath)

        output("\nSynchronizing %s from live." % filename)
        username = username0
        password = password0 or passwords.get(username)

        if not password and (not args.ask_password or conf.IsCLINonTerminal) \
        and conf.Login.get(filepath, {}).get("password"):
            password = util.deobfuscate(conf.Login[filepath]["password"])

        if not file_existed and conf.IsCLINonTerminal \
        and (not username or not password):
            output("Username or password not given, skip creating %s." % filename)
            continue # for filename

        prompt = "%s does not exist, enter Skype username: " % filename
        while not file_existed and not username:
            output(prompt, end="")
            username = six.moves.input().strip()

        db = skypedata.SkypeDatabase(filepath, truncate=not file_existed)
        username = db.username or username

        prompt = "%s does not contain account information, enter Skype username: " % filename
        while not username and not conf.IsCLINonTerminal:
            output(prompt, end="")
            username = six.moves.input().strip()
            if username: break # while not username

        if conf.IsCLINonTerminal and (not username or not password):
            output("Username or password not given, skip syncing %s." % filename)
            continue # for filename

        prompt, count = "Enter Skype password for '%s': " % username, 0
        while not db.live.is_logged_in() and count < 5:
            if (args.ask_password or not password) and not conf.IsCLINonTerminal:
                password = get_password(username, prompt=prompt)
            passwords[username] = password
            if not count or not conf.IsCLINonTerminal and (args.ask_password or not password):
                output("Logging in to Skype as '%s'.." % username, end="")
            try: db.live.login(username, password, init_db=True)
            except Exception as e:
                prompt = "\n%s\n%s" % (util.format_exc(e), prompt)
            else: output(" success!")
            count += 1
        save_conf = False

        sync_older = args.sync_older
        if not file_existed:
            conf.Login.setdefault(filepath, {})["sync_older"] = False
            save_conf, sync_older = True, None

        if password and args.store_password:
            conf.Login.setdefault(filepath, {})
            conf.Login[filepath].update(store=True, password=util.obfuscate(password))
            save_conf = True

        if args.sync_contacts is not None:
            if not args.sync_contacts:
                conf.Login.setdefault(filepath, {})["sync_contacts"] = False
            elif filepath in conf.Login:
                conf.Login[filepath].pop("sync_contacts", None)

        if sync_older is not None:
            if not sync_older:
                conf.Login.setdefault(filepath, {})["sync_older"] = False
            elif filepath in conf.Login:
                conf.Login[filepath].pop("sync_older", None)

        if save_conf: conf.save()

        if not db.live.is_logged_in():
            output("\nFailed to log in to Skype live.")
            continue # for filename

        chats = []
        if args.chats or args.authors:
            cc = db.get_conversations(args.chats, args.authors)
            chats = [c["identity"] for c in cc]

        output()
        db.live.progress = progress
        ns["filename"] = filename
        try: db.live.populate(chats)
        except Exception as e: progress(error=util.format_exc(e))
        db.close()


def run_create(filenames, args):
    """
    Creates a new database, blank or from a Skype source.

    @param   args               argparse.Namespace
               input            path of Skype export archive to populate from
               username         Skype username
               password         Skype password
               ask_password     whether to ask password on the command line interactively
               store_password   whether to store password in configuration file
    """
    if not args.input and not args.username:
        output("Not enough arguments.")
        sys.exit(1)

    filename = os.path.realpath(filenames[0])
    if os.path.exists(filename):
        output("%s already exists." % filename)
        sys.exit(1)

    if not args.input: # Create blank database, with just account username
        logger.info("Creating new blank database %s for user '%s'.", filename, args.username)
        db = skypedata.SkypeDatabase(filename, truncate=True)
        db.ensure_schema()
        db.insert_account({"skypename": args.username})
        output("Created blank database %s for user %s." % (filename, args.username))
        db.close()
        if args.username and (args.password or args.ask_password):
            run_sync(filenames, args)
        return

    counts = {}
    def progress(result=None, **kwargs):
        result = result or kwargs
        if "counts" in result:
            counts.update(result["counts"])
            t = ", ".join(util.plural(x[:-1], counts[x], sep=",")
                          for x in sorted(counts))
            bar.afterword = " Imported %s." % t
        return True

    username, password = live.SkypeExport.export_get_account(args.input), args.password
    db = live.SkypeExport(args.input, filename)

    if args.ask_password and args.store_password: password = get_password(username)
    logger.info("Creating new database %s from Skype export %s, user '%s'.",
                filename, args.input, username)
    output()
    bar = ProgressBar(pulse=True, interval=0.05, static=conf.IsCLINonTerminal)
    bar.afterword =" Importing %s" % filename
    bar.start()

    try: db.export_read(progress)
    except Exception:
        _, e, tb = sys.exc_info()
        logger.exception("Error importing Skype export archive %s.", filename)
        util.try_ignore(db.close)
        util.try_ignore(os.unlink, filename)
        six.reraise(type(e), e, tb)

    bar.stop()
    bar.pulse = False
    bar.update(100)
    db.close()
    if password and args.store_password:
        conf.Login.setdefault(filename, {})
        conf.Login[filename].update(store=True, password=util.obfuscate(password))
        conf.save()
    sz = util.format_bytes(os.path.getsize(filename))
    t = " and ".join(util.plural(x[:-1], counts[x], sep=",") for x in sorted(counts))
    output("\n\nCreated new database %s from Skype export archive %s." % (filename, args.input))
    output("Database size %s, username '%s', with %s." % (sz, db.username, t))


def run_export(filenames, args):
    """
    Exports the specified databases in specified format.

    @param   args               argparse.Namespace
               format           export type
               output_dir       output directory if not current directory
               chats            names of specific chats to export
               authors          names of specific authors whose chats to export
               start_date       date to export messages from, as YYYY-MM-DD
               end_date         date to export messages until, as YYYY-MM-DD
               media_folder     save shared media into a subfolder in HTML export
               media_cache      cache downloaded media in user directory
               password         Skype password
               ask_password     whether to ask password on the command line interactively
               store_password   whether to store password in configuration file
    """
    dbs = [skypedata.SkypeDatabase(f) for f in filenames]
    is_xlsx_single, format = ("xlsx_single" == args.format), args.format
    if is_xlsx_single: format = "xlsx"
    timerange = [util.datetime_to_epoch(x) for x in (args.start_date, args.end_date)]
    output_dir = args.output_dir or os.getcwd()

    for db in dbs:

        if (args.password or args.ask_password) and db.username \
        and (conf.SharedImageAutoDownload or conf.SharedAudioVideoAutoDownload
             or conf.SharedFileAutoDownload and args.media_folder) \
        and "html" == format:
            password = None
            while not db.live.is_logged_in():
                password = args.password or get_password(db.username)
                try: db.live.login(password=password)
                except Exception as e: output("\n" + util.format_exc(e))

            if password and args.store_password:
                conf.Login.setdefault(db.filename, {})
                conf.Login[db.filename].update(store=True, password=util.obfuscate(password))
                conf.save()

        formatargs = collections.defaultdict(str)
        formatargs["skypename"] = os.path.basename(db.filename)
        formatargs.update(db.account or {})
        basename = util.safe_filename(conf.ExportDbTemplate % formatargs)
        dbstr = "from %s " % db if len(dbs) != 1 else ""
        if is_xlsx_single:
            path = os.path.join(output_dir, "%s.xlsx" % basename)
        else:
            path = os.path.join(output_dir, basename)
        path = util.unique_path(path)
        util.try_ignore(os.makedirs, output_dir)
        try:
            extras = [("", args.chats)] if args.chats else []
            extras += [(" with authors", args.authors)] if args.authors else []
            output("Exporting%s%s as %s %sto %s." %
                  (" chats" if extras else "",
                   ",".join("%s like %s" % (x, y) for x, y in extras),
                   format.upper(), dbstr, path))
            chats = sorted(db.get_conversations(args.chats, args.authors),
                           key=lambda x: x["title"].lower())
            db.get_conversations_stats(chats)
            bar_total = sum(c["message_count"] for c in chats)
            AFTER_MAX = sys.maxsize if conf.IsCLINonTerminal else 30
            bartext = " Exporting %s%s.." % (
                      "..." if len(db.filename) > AFTER_MAX else "",
                      db.filename[-AFTER_MAX:])

            pulse = any(x is not None for x in timerange)
            bar = ProgressBar(max=bar_total, afterword=bartext, pulse=pulse,
                              static=conf.IsCLINonTerminal)
            bar.start()
            opts = dict(progress=not conf.IsCLINonTerminal and bar.update,
                        timerange=timerange)
            if not is_xlsx_single: opts["multi"] = True
            if args.media_folder: opts["media_folder"] = True
            if args.media_cache:  opts["media_cache"]  = True
            result = export.export_chats(chats, path, format, db, opts)
            files, count, message_count = result
            bar.stop()
            if count:
                bar.afterword = " Exported %s from %s to %s. " % (
                    util.plural("message", message_count), db, path)
                bar.update(bar_total)
                output()
                logger.info("Exported %s and %s %sto %s as %s.",
                            util.plural("chat", count),
                            util.plural("message", message_count),
                            dbstr, path, format.upper())
            else:
                output("\nNo messages to export%s." %
                      ("" if len(dbs) == 1 else " from %s" % db))
                util.try_ignore((os.unlink if is_xlsx_single else os.rmdir), path)
        except Exception as e:
            output("Error exporting chats: %s\n\n%s" %
                  (e, traceback.format_exc()))


def run_contacts(filenames, args):
    """
    Exports contacts from the specified databases in specified format.

    @param   args       argparse.Namespace
               format   export type
               output   output filename, auto-generated if not given
               fields   values in profile fields to select contacts by
               names    names to select contacts by
               chats    specific chats to select contacts by
    """
    AFTER_MAX = sys.maxsize if conf.IsCLINonTerminal else 30
    get_fields = lambda db, c: skypedata.CONTACT_FIELD_TITLES if db.id != c["identity"] \
                               else skypedata.ACCOUNT_FIELD_TITLES

    for filename in filenames:
        try: db = skypedata.SkypeDatabase(filename)
        except Exception as e:
            logger.exception("Error opening %s.", filename)
            output("Error opening %s: %s" % (filename, e))
            continue # for filename

        bartext = " Reading %s%s.." % (
                  "..." if len(db.filename) > AFTER_MAX else "",
                  db.filename[-AFTER_MAX:])
        bar = ProgressBar(afterword=bartext, interval=0.05, pulse=True,
                          static=conf.IsCLINonTerminal)
        bar.start()

        path = args.output
        if not path:
            formatargs = collections.defaultdict(str)
            formatargs["skypename"] = os.path.basename(db.filename)
            formatargs.update(db.account or {})
            path = "%s.%s" % (util.safe_filename(conf.ExportContactsTemplate % formatargs), args.format)
        path = util.unique_path(path)

        chats    = db.get_conversations()
        contacts = [db.account] + db.get_contacts()
        db.get_conversations_stats(chats)
        db.get_contacts_stats(contacts, chats)

        if args.fields:
            entries, texts = [], [x.lower() for x in args.fields]
            for c in contacts:
                ff = [(skypedata.format_contact_field(c, n) or "").lower()
                      for n in get_fields(db, c)]
                if ff and all(any(t in f for f in ff) for t in texts):
                    entries.append(c)
            contacts = entries
        if args.names:
            entries, texts = [], [x.lower() for x in args.names]
            for c in contacts:
                ff = [(c.get(n) or "").lower() for n in c if "name" in n]
                if ff and all(any(t in f for f in ff) for t in texts):
                    entries.append(c)
            contacts = entries
        if args.chats:
            entries, texts = [], [x.lower() for x in args.chats]
            chatmap = {x["id"]: x for x in chats}
            chatmap.update({x["__link"]["id"]: x["__link"] for x in chats if x.get("__link")})
            for c in contacts:
                ff = [(chatmap[x["id"]].get("title") or "").lower()
                      for x in c.get("conversations", [])]
                if ff and all(any(t in f for f in ff) for t in texts):
                    entries.append(c)
            contacts = entries

        util.try_ignore(os.makedirs, os.path.dirname(path))
        bar.afterword = " Exporting %s%s.." % (
                        "..." if len(db.filename) > AFTER_MAX else "",
                        db.filename[-AFTER_MAX:])
        bar.update()
        try:
            export.export_contacts(contacts, path, args.format, db)
            bar.stop()
            bar.afterword = " Exported %s from '%s' to '%s'. " % (
                util.plural("contact", contacts), db, path)
            bar.pulse = False
            bar.update(bar.max)
            output()
            logger.info("Exported %s %sto %s as %s.", util.plural("contact", contacts),
                        "from %s " % db if len(filenames) != 1 else "", path, args.format.upper())
        except Exception as e:
            output("Error exporting contacts: %s\n\n%s" %
                  (e, traceback.format_exc()))


def run_diff(filename1, filename2):
    """Compares the first database for changes with the second."""
    if os.path.realpath(filename1) == os.path.realpath(filename2):
        output("Error: cannot compare %s with itself." % filename1)
        return
    db1, db2 = map(skypedata.SkypeDatabase, [filename1, filename2])
    counts = collections.defaultdict(lambda: collections.defaultdict(int))
    postbacks = queue.Queue()

    AFTER_MAX = sys.maxsize if conf.IsCLINonTerminal else 20
    bar_text = " Scanning %s%s vs %s%s.." % ("..." if len(db1.filename) > AFTER_MAX else "",
                                             db1.filename[-AFTER_MAX:],
                                             "..." if len(db2.filename) > AFTER_MAX else "",
                                             db2.filename[-AFTER_MAX:])
    bar = ProgressBar(afterword=bar_text, static=conf.IsCLINonTerminal)
    bar.start()
    chats1, chats2 = db1.get_conversations(), db2.get_conversations()
    db1.get_conversations_stats(chats1), db2.get_conversations_stats(chats2)

    args = {"db1": db1, "db2": db2, "chats": chats1, "type": "diff_left"}
    worker = workers.MergeThread(postbacks.put)
    if conf.IsCLINonTerminal: output()
    try:
        worker.work(args)
        TITLE_MAX = sys.maxsize if conf.IsCLINonTerminal else 25
        while True:
            result = postbacks.get()
            if "error" in result:
                output("Error scanning %s and %s:\n\n%s" %
                      (db1, db2, result["error"]))
                break # while True
            if "done" in result:
                break # while True
            if "chats" in result and result["chats"]:
                counts[db1]["chats"] += 1
                new_chat = not result["chats"][0]["chat"]["c2"]
                newstr   = "" if new_chat else "new "
                msgs     = len(result["chats"][0]["diff"]["messages"])
                contacts = len(result["chats"][0]["diff"]["participants"])
                msgs_text = util.plural("%smessage" % newstr, msgs) if msgs else ""
                contacts_text = util.plural("%sparticipant" % newstr, contacts) \
                                if contacts else ""
                text = ", ".join(filter(bool, [msgs_text, contacts_text]))
                title = result["chats"][0]["chat"]["title"]
                if len(title) > TITLE_MAX: title = title[:TITLE_MAX] + ".."
                if new_chat: title += " - new chat"
                bar.afterword = " %s." % ", ".join(filter(bool, [title, text]))
                counts[db1]["msgs"] += msgs
            if "index" in result:
                bar.max = result["count"]
                if not conf.IsCLINonTerminal: bar.update(result["index"])
            if result.get("output"):
                if not conf.IsCLINonTerminal: output() # Push bar to next line
                elif result.get("chats"): bar.update()
                logger.info(result["output"])
                bar.afterword = ""
    finally:
        worker and (worker.stop(), worker.join())

    bar.stop()
    if conf.IsCLINonTerminal: output()
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
    app = MainApp(redirect=True) # stdout and stderr redirected to wx popup
    window = gui.MainWindow()
    app.SetTopWindow(window) # stdout/stderr popup closes with MainWindow
    wx.Log.SetLogLevel(wx.LOG_Error) # Swallow warning popups

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

    warnings.simplefilter("ignore", UnicodeWarning)

    if (conf.Frozen # Binary application
    or sys.executable.lower().endswith("pythonw.exe")):
        conf.IsCLINonTerminal = None # Flag for ConsoleWriter.init_console()
        sys.stdout = ConsoleWriter(sys.stdout) # Hooks for attaching to
        sys.stderr = ConsoleWriter(sys.stderr) # a text console
    if "main" not in sys.modules: # E.g. setuptools install, calling main.run
        srcdir = os.path.abspath(os.path.dirname(__file__))
        if srcdir not in sys.path: sys.path.append(srcdir)
        #sys.modules["main"] = __import__("main")

    argparser = argparse.ArgumentParser(description=ARGUMENTS["description"],
        prog=None if conf.Frozen or conf.Snapped else conf.Title.lower()
    )
    for arg in map(dict, ARGUMENTS["arguments"]):
        argparser.add_argument(*arg.pop("args"), **arg)
    subparsers = argparser.add_subparsers(dest="command")
    for cmd in ARGUMENTS["commands"]:
        kwargs = dict((k, cmd[k]) for k in cmd if k in ["help", "description"])
        subparser = subparsers.add_parser(cmd["name"],
                    formatter_class=LineSplitFormatter, **kwargs)
        for arg in map(dict, cmd["arguments"]):
            subparser.add_argument(*arg.pop("args"), **arg)

    argv = sys.argv[:]
    if "nt" == os.name and six.PY2: # Fix Unicode arguments, otherwise converted to ?
        argv = win32_unicode_argv(argv)
    argv = argv[1:]

    rootflags = tuple(subparsers.choices) + ("-h", "--help", "-v", "--version")
    if not argv or not any(x in argv for x in rootflags):
        argv[:0] = ["gui"] # argparse hack: force default argument
    if argv[0] in ("-h", "--help") and len(argv) > 1:
        argv[:2] = argv[:2][::-1] # Swap "-h option" to "option -h"

    arguments, _ = argparser.parse_known_args(argv)

    if hasattr(arguments, "FILE1") and hasattr(arguments, "FILE2"):
        arguments.FILE1 = [util.to_unicode(f) for f in arguments.FILE1]
        arguments.FILE2 = [util.to_unicode(f) for f in arguments.FILE2]
        arguments.FILE = arguments.FILE1 + arguments.FILE2
    if arguments.FILE: # Expand wildcards to actual filenames
        arguments.FILE = sum([sorted(glob.glob(f)) if "*" in f else [f]
                             for f in arguments.FILE], [])
        arguments.FILE = list(collections.OrderedDict(
            (util.to_unicode(f), 1) for f in arguments.FILE[::-1]
        ))[::-1] # Reverse and re-reverse to discard earlier duplicates

    conf.load(arguments.config_file)
    if "gui" == arguments.command and (nogui or not is_gui_possible):
        argparser.print_help()
        status = None
        if not nogui: status = ("\n\nwxPython not found. %s graphical program "
                                "will not run." % conf.Title)
        sys.exit(status)
    elif "gui" != arguments.command:
        conf.IsCLI = True
        conf.IsCLIVerbose     = arguments.verbose
        conf.IsCLINonTerminal = arguments.no_terminal
        if six.PY2:
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

    if "create" == arguments.command:
        run_create(arguments.FILE, arguments)
    elif "diff" == arguments.command:
        run_diff(*arguments.FILE)
    elif "merge" == arguments.command:
        if len(arguments.FILE) < 2:
            output("%s%s merge: error: too few FILE arguments" % (
                   subparsers.choices["merge"].format_usage(),
                   os.path.basename(sys.argv[0])))
            return
        run_merge(arguments.FILE, arguments)
    elif "export" == arguments.command:
        run_export(arguments.FILE, arguments)
    elif "contacts" == arguments.command:
        run_contacts(arguments.FILE, arguments)
    elif "search" == arguments.command:
        run_search(arguments.FILE, arguments)
    elif "sync" == arguments.command:
        run_sync(arguments.FILE, arguments)
    elif "gui" == arguments.command:
        try: run_gui(arguments.FILE)
        except Exception: traceback.print_exc()



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
                if not conf.IsCLINonTerminal: atexit.register(self.on_exe_exit)
            except Exception:
                try: win32console.FreeConsole()
                except Exception: pass
                ConsoleWriter.realwrite = self.stream.write
        ConsoleWriter.is_loaded = True


    def on_exe_exit(self):
        """atexit handler for compiled binary, keeps window open for a minute."""
        q = queue.Queue()

        def waiter():
            six.moves.input()
            q.put(None)

        def ticker():
            countdown = 60
            txt = "\rClosing window in %s.. Press ENTER to exit."
            while countdown > 0 and q.empty():
                output(txt % countdown, end=" ")
                countdown -= 1
                time.sleep(1)
            q.put(None)

        self.write("\n\n")
        for f in waiter, ticker:
            t = threading.Thread(target=f)
            t.daemon = True
            t.start()
        q.get()
        os._exit(0)



class ProgressBar(threading.Thread):
    """
    A simple ASCII progress bar with a ticker thread, drawn like
    '[---------\   36%            ] Progressing text..'.
    or for pulse mode
    '[    ----                    ] Progressing text..'.
    """

    def __init__(self, max=100, value=0, min=0, width=30, forechar="-",
                 backchar=" ", foreword="", afterword="", interval=1,
                 pulse=False, static=False):
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
        @param   static     print stripped afterword only, on explicit update()
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
        if static or not pulse: self.update(value, draw=static)


    def update(self, value=None, draw=True):
        """Updates the progress bar value, and refreshes by default."""
        if self.static:
            if self.afterword.strip(): output(self.afterword.strip())
            return

        if value is not None: self.value = min(self.max, max(self.min, value))
        w_full = self.width - 2
        if self.pulse:
            if self.pulse_pos is None:
                bartext = "%s[%s]%s" % (self.foreword,
                                        self.forechar * (self.width - 2),
                                        self.afterword)
            else:
                dash = self.forechar * max(1, (self.width - 2) // 7)
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
            percent = int(round(100.0 * self.value / (self.max or 1)))
            percent = 99 if percent == 100 and self.value < self.max else percent
            w_done = max(1, int(round((percent / 100.0) * w_full)))
            # Build bar outline, animate by cycling last char from progress chars
            char_last = self.forechar
            if draw and w_done < w_full: char_last = next(self.progresschar)
            bartext = "%s[%s%s%s]%s" % (
                       self.foreword, self.forechar * (w_done - 1), char_last,
                       self.backchar * (w_full - w_done), self.afterword)
            # Write percentage into the middle of the bar
            centertxt = " %2d%% " % percent
            pos = len(self.foreword) + self.width // 2 - len(centertxt) // 2
            bartext = bartext[:pos] + centertxt + bartext[pos + len(centertxt):]
            self.percent = percent
        self.printbar = bartext + " " * max(0, len(self.bar) - len(bartext))
        self.bar, prevbar = bartext, self.bar
        if draw and prevbar != self.bar: self.draw()


    def draw(self):
        """Prints the progress bar, from the beginning of the current line."""
        if self.static: return
        output("\r" + self.printbar, end=" ")
        if len(self.printbar) != len(self.bar):
            self.printbar = self.bar # Discard padding to clear previous
            output("\r" + self.printbar, end=" ")


    def run(self):
        if self.static: return # No running progress
        self.is_running = True
        while self.is_running:
            if not self.pause: self.update(self.value)
            time.sleep(self.interval)


    def stop(self):
        self.is_running = False


def win32_unicode_argv(argv):
    # @from http://stackoverflow.com/a/846931/145400
    result = argv
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


def get_password(username, prompt=None):
    """Asks user for password from keyboard input."""
    result, prompt = "", prompt or "Enter Skype password for '%s': " % username
    with warnings.catch_warnings():
        warnings.simplefilter("ignore") # possible GetPassWarning
        while not result:
            output(prompt, end="") # getpass output can raise errors
            result = getpass.getpass("", io.BytesIO()).strip()
    return result


def output(s="", **kwargs):
    """Print wrapper, avoids "Broken pipe" errors if piping is interrupted."""
    try: print(s, **kwargs)
    except UnicodeError:
        try:
            if isinstance(s, six.binary_type): print(s.decode(errors="replace"), **kwargs)
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
