# -*- coding: utf-8 -*-
"""
Background workers for potentially long-running tasks like searching and
diffing.

------------------------------------------------------------------------------
This file is part of Skyperious - Skype chat history tool.
Released under the MIT License.

@author      Erki Suurjaak
@created     10.01.2012
@modified    10.05.2025
------------------------------------------------------------------------------
"""
import collections
import datetime
import logging
import os
import re
import threading
import traceback

from six.moves import queue
import step
try:
    import wx
except ImportError:
    pass # Most functionality works without wx

from . lib import controls
from . lib import util

from . import conf
from . import searchparser
from . import skypedata
from . import templates

logger = logging.getLogger(__name__)


class WorkerThread(threading.Thread):
    """Base class for worker threads."""

    def __init__(self, callback):
        """
        @param   callback  function to call with result chunks
        """
        threading.Thread.__init__(self)
        self._callback = callback
        self._is_running   = False # Flag whether thread is running
        self._is_working   = False # Flag whether thread is currently working
        self._drop_results = False # Flag to not post back obtained results
        self._queue = queue.Queue()


    def work(self, data):
        """
        Registers new work to process. Stops current work, if any. Starts
        thread if not running.

        @param   data  a dict with work data
        """
        self._queue.put(data)
        if not self._is_running: self.start()


    def stop(self, drop_results=True):
        """Stops the worker thread."""
        self._is_running   = False
        self._is_working   = False
        self._drop_results = drop_results
        while not self._queue.empty(): self._queue.get_nowait()
        self._queue.put(None) # To wake up thread waiting on queue


    def stop_work(self, drop_results=False):
        """
        Signals to stop the currently ongoing work, if any. Obtained results
        will be posted back, unless drop_results is True.
        """
        self._is_working = False
        self._drop_results = drop_results
        while not self._queue.empty(): self._queue.get_nowait()


    def is_working(self):
        """Returns whether the thread is currently doing work."""
        return self._is_working or self._is_running and not self._queue.empty()


    def postback(self, data):
        # Check whether callback is still bound to a valid object instance
        if callable(self._callback) and getattr(self._callback, "__self__", True):
            self._callback(data)


    def yield_ui(self):
        """Allows UI to respond to user input."""
        try: wx.YieldIfNeeded()
        except Exception: pass



class SearchThread(WorkerThread):
    """
    Search background thread, searches the database on demand, yielding
    results back to main thread in chunks.
    """


    def match_all(self, text, words):
        """Returns whether the text contains all the specified words."""
        text_lower = text.lower()
        result = all(w in text_lower for w in words)
        return result


    def run(self):
        self._is_running = True
        # For identifying "chat:xxx" and "from:xxx" keywords
        query_parser = searchparser.SearchQueryParser()
        result = None
        while self._is_running:
            try:
                search = self._queue.get()
                if not search:
                    continue # continue while self._is_running

                self._is_working, self._drop_results = True, False
                is_html = ("text" != search.get("output"))
                reverse, offset, limit = (search.get(k, 0) for k in ("reverse", "offset", "limit"))
                wrap_html = None # MessageParser wrap function, for HTML output
                if is_html:
                    TEMPLATES = {
                        "chat":    templates.SEARCH_ROW_CHAT_HTML,
                        "contact": templates.SEARCH_ROW_CONTACT_HTML,
                        "message": templates.SEARCH_ROW_MESSAGE_HTML,
                        "table":   templates.SEARCH_ROW_TABLE_HEADER_HTML,
                        "row":     templates.SEARCH_ROW_TABLE_HTML, }
                    wrap_b = lambda x: "<b>%s</b>" % x.group(0)
                    output = {"format": "html"}
                    width = search.get("width", -1)
                    if width > 0:
                        dc = wx.MemoryDC()
                        dc.SetFont(wx.Font(8, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL,
                            wx.FONTWEIGHT_NORMAL, faceName=conf.HistoryFontName))
                        wrap_html = lambda x: controls.wordwrap(x, width, dc)
                        output["wrap"] = True
                else:
                    TEMPLATES = {
                        "chat":    templates.SEARCH_ROW_CHAT_TXT,
                        "contact": templates.SEARCH_ROW_CONTACT_TXT,
                        "message": templates.SEARCH_ROW_MESSAGE_TXT,
                        "table":   templates.SEARCH_ROW_TABLE_HEADER_TXT,
                        "row":     templates.SEARCH_ROW_TABLE_TXT, }
                    wrap_b = lambda x: "**%s**" % x.group(0)
                    output = {"format": "text"}
                FACTORY = lambda x, s=True: step.Template(TEMPLATES[x], escape=is_html, strip=s)
                logger.info('Searching "%s" in %s (%s).',
                            search["text"], search["table"], search["db"])

                parser = skypedata.MessageParser(search["db"],
                                                 wrapper=wrap_html)
                result_type, result_count, match_count, count = None, 0, 0, 0
                # {"output": text with results, "map": link data map}
                # map data: {"contact:666": {"contact": {contact data}}, }
                result = {"output": "", "map": {},
                          "search": search, "count": 0}
                sql, params, match_words = query_parser.Parse(search["text"])
                match_words = [x.lower() for x in match_words]

                # Turn wildcard characters * into regex-compatible .*
                match_words_re = [".*".join(map(re.escape, w.split("*")))
                                  for w in match_words]
                patt = "(%s)" % "|".join(match_words_re)
                # For replacing matching words with <b>words</b>
                pattern_replace = re.compile(patt, re.IGNORECASE)

                # Find chats with a matching title or matching participants
                chats = []
                if search["table"] in ["conversations", "messages"]:
                    chats = search["db"].get_conversations()
                    chats.sort(key=lambda x: x["title"], reverse=reverse)
                    chat_map = {} # {chat id: {chat data}}
                    template_chat = FACTORY("chat", is_html)
                for chat in chats:
                    chat_map[chat["id"]] = chat
                    if chat.get("__link"): chat_map[chat["__link"]["id"]] = chat
                    if "conversations" == search["table"] and match_words:
                        title_matches = False
                        matching_authors = []
                        if self.match_all(chat["title"], match_words):
                            title_matches = True
                        for participant in chat["participants"]:
                            contact = participant["contact"]
                            if contact:
                                for n in filter(bool, [contact["name"], contact["fullname"],
                                contact["displayname"], contact["identity"]]):
                                    if self.match_all(n, match_words) \
                                    and contact not in matching_authors:
                                        matching_authors.append(contact)
                        if title_matches or matching_authors:
                            match_count += 1
                            if offset and match_count < offset:
                                continue # for chat
                            count += 1
                            result_count += 1
                            try: result["output"] += template_chat.expand(locals())
                            except Exception:
                                logger.exception("Error formatting search result for chat %s in %s.",
                                                 chat, search["db"])
                                match_count -= 1
                                count -= 1
                                result_count -= 1
                                continue # for chat
                            key = "chat:%s" % chat["id"]
                            result["map"][key] = {"chat": chat["id"]}
                            if not count % conf.SearchResultsChunk \
                            and not self._drop_results:
                                result["count"] = result_count
                                self.postback(result)
                                result = {"output": "", "map": {},
                                          "search": search, "count": 0}
                    if limit and result_count >= limit:
                        break # for chat
                    if not self._is_working:
                        break # for chat
                if result["output"] and not self._drop_results:
                    result["count"] = result_count
                    self.postback(result)
                    result = {"output": "", "map": {}, "search": search,
                              "count": 0}

                # Find contacts with a matching name
                if self._is_working and "contacts" == search["table"] \
                and match_words:
                    count = 0
                    contacts = search["db"].get_contacts()[::-1 if reverse else 1]
                    template_contact = FACTORY("contact", is_html)
                    for contact in contacts:
                        match = False
                        fields_filled = {}
                        for field, _ in skypedata.CONTACT_FIELD_TITLES.items():
                            val = skypedata.format_contact_field(contact, field)
                            if val:
                                if self.match_all(val, match_words):
                                    match = True
                                    val = pattern_replace.sub(wrap_b, val)
                                fields_filled[field] = val
                        if match:
                            match_count += 1
                            if offset and match_count < offset:
                                continue # for contact
                            count += 1
                            result_count += 1
                            try: result["output"] += template_contact.expand(locals())
                            except Exception:
                                logger.exception("Error formatting search result for contact %s in %s.",
                                                 contact, search["db"])
                                match_count -= 1
                                count -= 1
                                result_count -= 1
                                continue # for contact
                            if not (self._drop_results
                            or count % conf.SearchResultsChunk):
                                result["count"] = result_count
                                self.postback(result)
                                result = {"output": "", "map": {},
                                          "search": search, "count": 0}
                        if limit and result_count >= limit:
                            break # for contact
                        if not self._is_working:
                            break # for contact
                if result["output"] and not self._drop_results:
                    result["count"] = result_count
                    self.postback(result)
                    result = {"output": "", "map": {},
                              "search": search, "count": 0}

                # Find messages with a matching body
                if self._is_working and "messages" == search["table"]:
                    template_message = FACTORY("message")
                    count, result_type = 0, "messages"
                    chat_messages = {} # {chat id: [message, ]}
                    chat_order = []    # [chat id, ]
                    messages = search["db"].get_messages(
                        additional_sql=sql, additional_params=params,
                        limit=(limit, offset) if limit or offset else (),
                        ascending=reverse, use_cache=False)
                    for m in messages:
                        chat = chat_map.get(m["convo_id"])
                        body = parser.parse(m, pattern_replace if match_words
                                            else None, output)
                        count += 1
                        result_count += 1
                        try: result["output"] += template_message.expand(locals())
                        except Exception:
                            logger.exception("Error formatting search result for message %s in %s.",
                                             m, search["db"])
                            count -= 1
                            result_count -= 1
                            continue # for m
                        key = "message:%s" % m["id"]
                        result["map"][key] = {"chat": chat["id"],
                                              "message": m["id"]}
                        if not is_html or (not self._drop_results
                        and not count % conf.SearchResultsChunk):
                            result["count"] = result_count
                            self.postback(result)
                            result = {"output": "", "map": {},
                                      "search": search, "count": 0}
                        if not self._is_working or (is_html
                        and count >= conf.MaxSearchMessages):
                            break # for m

                infotext = search["table"]
                if self._is_working and "all tables" == search["table"]:
                    infotext, result_type = "", "table row"
                    # Search over all fields of all tables.
                    template_table = FACTORY("table", is_html)
                    template_row = FACTORY("row", is_html)
                    for table in search["db"].get_tables()[::-1 if reverse else 1]:
                        table["columns"] = search["db"].get_table_columns(
                            table["name"])
                        sql, params, words = query_parser.Parse(search["text"],
                                                                table)
                        if not sql:
                            continue # continue for table in search["db"]..
                        if reverse and re.search(r" ORDER BY \S+$", sql):
                            sql += " DESC"
                        rows = search["db"].execute(sql, params)
                        row = rows.fetchone()
                        namepre, namesuf = ("<b>", "</b>") if row else ("", "")
                        countpre, countsuf = (("<a href='#%s'>" %
                            step.step.escape_html(table["name"]), "</a>") if row
                            else ("", ""))
                        infotext += (", " if infotext else "") \
                                    + namepre + table["name"] + namesuf
                        if not row:
                            continue # continue for table in search["db"]..
                        result["output"] = template_table.expand(locals())
                        count = 0
                        while row:
                            match_count += 1
                            if offset and match_count < offset:
                                continue # while row
                            count += 1
                            result_count += 1
                            try: result["output"] += template_row.expand(locals())
                            except Exception:
                                logger.exception("Error formatting search result for row %s in %s.",
                                                 row, search["db"])
                                match_count -= 1
                                count -= 1
                                result_count -= 1
                                continue # while row
                            key = "table:%s:%s" % (table["name"], count)
                            result["map"][key] = {"table": table["name"],
                                                  "row": row}
                            if not count % conf.SearchResultsChunk \
                            and not self._drop_results:
                                result["count"] = result_count
                                self.postback(result)
                                result = {"output": "", "map": {},
                                          "search": search, "count": 0}
                            if limit and result_count >= limit:
                                break # while row
                            if not self._is_working or (is_html
                            and result_count >= conf.MaxSearchTableRows):
                                break # while row
                            row = rows.fetchone()
                        if not self._drop_results:
                            if is_html:
                                result["output"] += "</table>"
                            result["count"] = result_count
                            self.postback(result)
                            result = {"output": "", "map": {},
                                      "search": search, "count": 0}
                        infotext += " (%s%s%s)" % (countpre,
                                    util.plural("result", count), countsuf)
                        if limit and result_count >= limit:
                            break # for table
                        if not self._is_working or (is_html
                        and result_count >= conf.MaxSearchTableRows):
                            break # for table
                    single_table = ("," not in infotext)
                    infotext = "table%s: %s" % \
                               ("" if single_table else "s", infotext)
                    if not single_table:
                        infotext += "; %s in total" % \
                                    util.plural("result", result_count)
                final_text = "No matches found."
                if self._drop_results:
                    result["output"] = ""
                if result_count:
                    final_text = "Finished searching %s." % infotext

                if not self._is_working:
                    final_text += " Stopped by user."
                elif "messages" == result_type and is_html \
                and count >= conf.MaxSearchMessages:
                    final_text += " Stopped at %s limit %s." % \
                                  (result_type, conf.MaxSearchMessages)
                elif "table row" == result_type and is_html \
                and count >= conf.MaxSearchTableRows:
                    final_text += " Stopped at %s limit %s." % \
                                  (result_type, conf.MaxSearchTableRows)

                result["output"] += "</table><br /><br />%s</font>" % final_text
                if not is_html: result["output"] = ""
                result["done"] = True
                result["count"] = result_count
                self.postback(result)
                logger.info("Search found %s results.", result["count"])
            except Exception as e:
                if not result:
                    result = {}
                result["done"], result["error"] = True, traceback.format_exc()
                result["error_short"] = repr(e)
                self.postback(result)
            finally:
                self._is_working = False


class MergeThread(WorkerThread):
    """
    Merge background thread, compares conversations in two databases, yielding
    results back to main thread in chunks, or merges compared differences.
    """

    # Difftext to compare will be assembled from other fields for these types.
    MESSAGE_TYPES_IGNORE_BODY = [
        skypedata.MESSAGE_TYPE_GROUP, skypedata.MESSAGE_TYPE_PARTICIPANTS,
        skypedata.MESSAGE_TYPE_REMOVE, skypedata.MESSAGE_TYPE_LEAVE,
        skypedata.MESSAGE_TYPE_SHARE_DETAIL
    ]
    # Number of iterations between allowing a UI refresh
    REFRESH_COUNT = 20000
    # Number of iterations between performing an intermediary postback
    POSTBACK_COUNT = 5000


    def run(self):
        self._is_running = True
        while self._is_running:
            params = self._queue.get()
            if not params: continue # while self._is_running

            self._is_working, self._drop_results = True, False
            try:
                if "diff_left" == params.get("type"):
                    self.work_diff_left(params)
                elif "diff_merge_left" == params.get("type"):
                    self.work_diff_merge_left(params)
                elif "merge_left" == params.get("type"):
                    self.work_merge_left(params)
            finally:
                self._is_working = False


    def work_diff_left(self, params):
        """
        Worker branch that compares all chats on the left side for differences,
        posting results back to application.
        """
        # {"output": "html result for db1, db2",
        #  "index": currently processed chat index,
        #  "chats": [differing chats in db1]}
        result = {"output": "", "chats": [], "count": 0,
                  "chatindex": 0, "chatcount": 0,
                  "params": params, "index": 0, "type": "diff_left"}
        db1, db2 = params["db1"], params["db2"]
        chats1 = params.get("chats") or db1.get_conversations()
        chats2 = db2.get_conversations()
        c2map = dict((c["identity"], c) for c in chats2)
        for c in (c for c in chats2 if c.get("__link")):
            c2map[c["__link"]["identity"]] = c
        compared = []
        for c1 in chats1:
            c2 = c2map.get(c1["identity"])
            if not c2 and c1.get("__link"):
                c2 = c2map.get(c1["__link"]["identity"])
            c = c1.copy()
            c["messages1"] = c1["message_count"] or 0
            c["messages2"] = c2["message_count"] or 0 if c2 else 0
            c["c1"], c["c2"] = c1, c2
            compared.append(c)
            result["count"] += c["messages1"] + c["messages2"]
        result["chatcount"] = len(chats1)
        compared.sort(key=lambda x: x["title"].lower())
        info_template = step.Template(templates.DIFF_RESULT_ITEM, escape=True)

        for index, chat in enumerate(compared):
            result["chatindex"] = index
            postback = dict((k, v) for k, v in result.items()
                            if k not in ["output", "chats", "params"])
            diff = self.get_chat_diff_left(chat, db1, db2, postback, runcheck=True)
            if not self._is_working:
                break # for index, chat
            if not conf.ShareDirectoryEnabled: diff["shared_files"] = []
            if diff["messages"] or diff["shared_files"] \
            or (chat["message_count"] and diff["participants"]):
                new_chat = not chat["c2"]
                newstr = "" if new_chat else "new "
                info = info_template.expand(chat=chat)
                if new_chat:
                    info += " - new chat"
                if diff["messages"]:
                    info += ", %s" % util.plural("%smessage" % newstr, diff["messages"])
                elif not diff["shared_files"]:
                    info += ", no messages"
                if diff["shared_files"]:
                    info += ", %s" % util.plural("%sshared file" % newstr, diff["shared_files"])
                if diff["participants"] and not new_chat:
                    info += ", %s" % (util.plural("%sparticipant" % newstr, diff["participants"]))
                info += ".<br />"
                result["output"] += info
                result["chats"].append({"chat": chat, "diff": diff})
            result["index"] = postback["index"]
            if not self._drop_results:
                if index < len(compared) - 1:
                    result["status"] = ("Scanning %s." % compared[index + 1]["title_long_lc"])
                self.postback(result)
                result = dict(result, output="", chats=[])
        if not self._drop_results:
            result["done"] = True
            self.postback(result)



    def work_diff_merge_left(self, params):
        """
        Worker branch that compares all chats on the left side for differences,
        copies them over to the right, posting progress back to application.
        """
        result = {"output": "", "index": 0, "count": 0, "chatindex": 0,
                  "chatcount": 0, "params": params, "chats": [],
                  "type": "diff_merge_left"}
        error, exc = None, None
        compared = []
        db1, db2 = params["db1"], params["db2"]
        try:
            chats1 = params.get("chats") or db1.get_conversations()
            chats2 = db2.get_conversations()
            c2map = dict((c["identity"], c) for c in chats2)
            for c in (c for c in chats2 if c.get("__link")):
                c2map[c["__link"]["identity"]] = c
            for c1 in chats1:
                c2 = c2map.get(c1["identity"])
                if not c2 and c1.get("__link"):
                    c2 = c2map.get(c1["__link"]["identity"])
                c = c1.copy()
                c["messages1"] = c1["message_count"] or 0
                c["messages2"] = c2["message_count"] or 0 if c2 else 0
                c["c1"], c["c2"] = c1, c2
                compared.append(c)
                result["count"] += c["messages1"] + c["messages2"]
            result["chatcount"] = len(chats1)
            compared.sort(key=lambda x: x["title"].lower())
            counts = collections.defaultdict(int)

            for index, chat in enumerate(compared):
                result["chatindex"] = index
                postback = dict((k, v) for k, v in result.items()
                                if k not in ["output", "chats", "params"])
                diff = self.get_chat_diff_left(chat, db1, db2, postback, runcheck=True)
                if not self._is_working:
                    break # for index, chat
                if not conf.ShareDirectoryEnabled: diff["shared_files"] = []
                if diff["messages"] or diff["shared_files"] \
                or (chat["message_count"] and diff["participants"]):
                    chat1 = chat["c1"]
                    chat2 = chat["c2"]
                    new_chat = not chat2
                    if new_chat:
                        chat2 = chat1.copy()
                        chat["c2"] = chat2
                        chat2["id"] = db2.insert_conversation(chat2, db1)
                    if diff["participants"]:
                        db2.insert_participants(chat2, diff["participants"], db1)
                        counts["participants"] += len(diff["participants"])
                    if diff["messages"]:
                        db2.insert_messages(chat2, diff["messages"], db1, chat1, diff["shared_files"],
                                            self.yield_ui, self.REFRESH_COUNT)
                        counts["messages"] += len(diff["messages"])
                    if diff["shared_files"]:
                        files_missing = [f for f in diff["shared_files"] if f.get("msg_id2")]
                        if files_missing:
                            db2.insert_shared_files(chat2, files_missing, db1,
                                                    self.yield_ui, self.REFRESH_COUNT)
                        counts["shared_files"] += len(diff["shared_files"])

                    newstr = "" if new_chat else "new "
                    info = "Merged %s" % chat["title_long_lc"]
                    if new_chat:
                        info += " - new chat"
                    if diff["messages"]:
                        info += ", %s" % util.plural("%smessage" % newstr, diff["messages"])
                    elif not diff["shared_files"]:
                        info += ", no messages"
                    if diff["shared_files"]:
                        info += ", %s" % util.plural("%sshared file" % newstr, diff["shared_files"])
                    if diff["participants"]:
                        info += ", %s" % util.plural("%sparticipant" % newstr, diff["participants"])
                    result["output"] = info + "."
                    result["diff"] = diff
                result["index"] = postback["index"]
                result["chats"].append(chat)
                if not self._drop_results:
                    if index < len(compared) - 1:
                        result["status"] = ("Scanning %s." %
                                            compared[index+1]["title_long_lc"])
                    self.postback(result)
                    result = dict(result, output="", chats=[])
        except Exception as e:
            error = traceback.format_exc()
            exc = e
        finally:
            if not self._drop_results:
                if compared:
                    count_texts = []
                    for category in ("messages", "shared_files", "participants"):
                        if counts.get(category):
                            word = category[:-1].replace("_", " ")
                            count_texts.append(util.plural("new %s" % word, counts[category],
                                                           sep=","))
                    info = "Merged %s\n\nto %s." % (" and ".join(count_texts), db2)
                else:
                    info = "Nothing new to merge from %s to %s." % (db1, db2)
                result = {"type": "diff_merge_left", "done": True,
                          "output": info, "params": params, "chats": [] }
                if error:
                    result["error"] = error
                    if exc: result["error_short"] = repr(exc)
                self.postback(result)


    def work_merge_left(self, params):
        """
        Worker branch that merges differences given in params, posting progress
        back to application.
        """
        error, e = None, None
        db1, db2 = params["db1"], params["db2"]
        chats = params["chats"]
        counts = collections.defaultdict(int)
        result = {"count": sum(len(x["diff"]["messages"]) for x in chats),
                  "index": 0, "chatindex": 0, "chatcount": len(chats),
                  "type": "merge_left", "output": "", "chats": [],
                  "params": params}
        exc = None
        try:
            for index, chat_data in enumerate(chats):
                if not self._is_working:
                    break # for index, chat_data
                chat1 = chat_data["chat"]["c1"]
                chat2 = chat_data["chat"]["c2"]
                messages = chat_data["diff"]["messages"]
                participants = chat_data["diff"]["participants"]
                shared_files = chat_data["diff"]["shared_files"]
                if not conf.ShareDirectoryEnabled: conf.ShareDirectoryEnabled = []
                newstr = "" if not chat2 else "new "
                html = "Merged %s" % chat1["title_long_lc"]
                if not chat2:
                    html += " - new chat"
                if messages:
                    html += ", %s" % util.plural("%smessage" % newstr, messages)
                elif not shared_files:
                    html += ", no messages"
                if shared_files:
                    html += ", %s" % util.plural("%sshared file" % newstr, shared_files)
                html += "."
                if not chat2:
                    chat2 = chat1.copy()
                    chat_data["chat"]["c2"] = chat2
                    chat2["id"] = db2.insert_conversation(chat2, db1)
                if participants:
                    db2.insert_participants(chat2, participants, db1)
                    counts["participants"] += len(participants)
                if messages:
                    db2.insert_messages(chat2, messages, db1, chat1, shared_files,
                                        self.yield_ui, self.REFRESH_COUNT)
                    counts["messages"] += len(messages)
                if shared_files:
                    files_missing = [f for f in shared_files if f.get("msg_id2")]
                    if files_missing:
                        db2.insert_shared_files(chat2, files_missing, db1,
                                                self.yield_ui, self.REFRESH_COUNT)
                    counts["shared_files"] += len(shared_files)

                if not self._drop_results:
                    result.update(output=html, chatindex=index, chats=[chat_data["chat"]])
                    result["index"] += len(messages)
                    if index < len(chats) - 1:
                        result["status"] = ("Merging %s." %
                                            chats[index + 1]["chat"]["title_long_lc"])
                    self.postback(result)
                    result = dict(result, output="", chats=[])
        except Exception as e:
            error = traceback.format_exc()
            exc = e
        finally:
            html = "Nothing to merge."
            if chats:
                count_texts = []
                for category in ("messages", "shared_files", "participants"):
                    if counts.get(category):
                        word = category[:-1].replace("_", " ")
                        count_texts.append(util.plural("new %s" % word, counts[category], sep=","))
                html = "Merged %s\n\n to %s." % (" and ".join(count_texts), db2)
            if not self._drop_results:
                result = {"type": "merge_left", "done": True, "output": html, "params": params}
                if error:
                    result["error"] = error
                    if exc: result["error_short"] = repr(exc)
                self.postback(result)


    def get_chat_diff_left(self, chat, db1, db2, postback=None, runcheck=False):
        """
        Compares the chat in the two databases and returns the differences from
        the left as {"messages": [message IDs different in db1],
                     "participants": [participants different in db1],
                     "shared_Files": [shared files missing in db2, with optional msg_id2]}.

        @param   postback  if {"count": .., "index": ..}, updates index
                           and posts the result at POSTBACK_COUNT intervals
        @param   runcheck  if true, breaks when thread is no longer marked working
        """
        c = chat
        participants1 = c["c1"]["participants"] if c["c1"] else []
        participants2 = c["c2"]["participants"] if c["c2"] else []
        c2p_map = {p["identity"]: p for p in participants2}
        c1p_diff = [p for p in participants1 if p["identity"] not in c2p_map
                    or (p["contact"].get("id") and not c2p_map[p["identity"]]["contact"].get("id"))]

        c1f_map, c2f_map = {}, {} # {message ID: {.._shared_files_ row..}} for both sides
        if conf.ShareDirectoryEnabled:
            for db, convo, fmap in [(db1, c["c1"], c1f_map), (db2, c["c2"], c2f_map)]:
                if convo and "_shared_files_" in db.tables:
                    for f in db.execute("SELECT * FROM _shared_files_ WHERE convo_id = :id", convo):
                        path = db.get_shared_file_path(f["msg_id"])
                        if path and os.path.isfile(path): fmap[f["msg_id"]] = f

        c1m_diff = [] # [(id, datetime), ] messages different in chat 1
        c1f_diff = [] # [{..shared file dict, ?msg_id2..}, ] files from chat 1 missing in chat 2
        db_account_ids = set(filter(bool, [db1.id, db1.username, db2.id, db2.username]))

        if not c["messages1"]:   # Left side empty, skip all messages
            if postback: postback["index"] += c["messages2"]
        elif not c["messages2"]: # Right side empty, take entire left
            messages1 = db1.get_messages(c["c1"], use_cache=False)
            c1m_diff = [(m["id"], m["datetime"]) for m in messages1]
            if postback: postback["index"] += len(c1m_diff)
        else:
            messages1 = db1.get_messages(c["c1"], use_cache=False)
            messages2 = db2.get_messages(c["c2"], use_cache=False)
            parser1 = skypedata.MessageParser(db1)
            parser2 = skypedata.MessageParser(db2)
            parse_options = {"format": "text", "merge": True}

            m2buckets = {} # {datetime.date: {(author, body): [(id, datetime), ]}}

            # Assemble all chat message contents from db2
            for i, m in enumerate(messages2):
                if not m.get("datetime"): continue # for i, m

                mkey, akey = (m["id"], m["datetime"]), None
                t = util.to_unicode(parser2.parse(m, output=parse_options), "utf-8")
                if m["author"] not in db_account_ids:
                    akey = util.to_unicode(m["author"] or "", "utf-8")
                bucket = m2buckets.setdefault(m["datetime"].date(), {})
                bucket.setdefault((akey, t), []).append(mkey)

                if runcheck and not self._is_working:
                    break # for i, m
                if i and not i % self.REFRESH_COUNT:
                    self.yield_ui()
                if postback: postback["index"] += 1
                if postback and i and not i % self.POSTBACK_COUNT:
                    self.postback(postback)

            # For every chat message in db1, see if there is a match in db2
            DELTAS = [datetime.timedelta(days=x) for x in range(-1, 2)]
            for i, m in enumerate(messages1):
                if not m.get("datetime"): continue # for i, m

                t = util.to_unicode(parser1.parse(m, output=parse_options), "utf-8")
                if m["author"] in db_account_ids: ckey = (None, t)
                else: ckey = (util.to_unicode(m["author"] or "", "utf-8"), t)

                potentials, mdate = [], m["datetime"].date()
                for delta in DELTAS:
                    # Look for matching messages within -1/+1 day interval
                    potentials += m2buckets.get(mdate+delta, {}).get(ckey, [])
                m2key = next((x for x in potentials
                              if self.match_time(m["datetime"], x[1], 180)), None)
                if not m2key:
                    c1m_diff.append((m["id"], m["datetime"]))
                if m["id"] in c1f_map and (not m2key or m2key[0] not in c2f_map):
                    filedata = c1f_map[m["id"]]
                    if m2key: filedata = dict(filedata, msg_id2=m2key[0])
                    c1f_diff.append(filedata)
                if runcheck and not self._is_working:
                    break # for i, m
                if i and not i % self.REFRESH_COUNT:
                    self.yield_ui()
                if postback: postback["index"] += 1
                if postback and i and not i % self.POSTBACK_COUNT:
                    self.postback(postback)

        message_ids1 = [x[0] for x in sorted(c1m_diff, key=lambda x: x[1])]
        result = {"messages": message_ids1, "participants": c1p_diff, "shared_files": c1f_diff}

        return result


    def match_time(self, d1, d2, slack=0):
        """
        Returns whether datetimes might be same but from different timezones:
        comparison ignores hours within a single-day interval.

        @param   slack  seconds of slack between timestamp minutes
        """
        if not d1 or not d2: return False
        d1, d2 = (d1, d2) if d1 < d2 else (d2, d1)
        delta = d2 - d1
        if util.timedelta_seconds(delta) > 24 * 3600:
            return False # Skip if not even within same day

        result = False
        for hour in range(int(util.timedelta_seconds(delta) / 3600) + 1):
            d1plus = d1 + datetime.timedelta(hours=hour)
            result = util.timedelta_seconds(d2 - d1plus) < slack
            if result: break # for hour
        return result



class DetectDatabaseThread(WorkerThread):
    """
    Skype database detection background thread, goes through potential
    directories and yields database filenames back to main thread one by one.
    """

    def run(self):
        self._is_running = True
        while self._is_running:
            search = self._queue.get()
            if not search: continue # while self._is_running

            self._is_working, self._drop_results = True, False
            all_filenames = set() # To handle potential duplicates
            for filenames in skypedata.detect_databases(lambda: self._is_working):
                filenames = all_filenames.symmetric_difference(filenames)
                if not self._drop_results:
                    result = {"filenames": filenames}
                    self.postback(result)
                all_filenames.update(filenames)
                if not self._is_working:
                    break # for filenames

            result = {"done": True, "count": len(all_filenames)}
            self.postback(result)
            self._is_working = False


class LiveThread(WorkerThread):
    """
    Skype online service background thread, carries out login and retrieval.
    """


    def __init__(self, callback, skype):
        """
        @param   callback  function to call with request progress
        @param   skype     live.SkypeLogin instance
        """
        super(LiveThread, self).__init__(callback)
        self._skype = skype


    def run(self):
        self._is_running = True
        while self._is_running:
            action = self._queue.get()
            if not action: continue # while self._is_running

            self._is_working, self._drop_results = True, False
            result = {"action": action["action"], "opts": action, "end": True}
            try:
                if "login" == action["action"]:
                    self._skype.login(password=action["password"])
                elif "populate" == action["action"]:
                    self._skype.populate(action.get("chats"))
                elif "account" == action["action"]:
                    self._skype.populate_account()
                elif "contacts" == action["action"]:
                    self._skype.populate_contacts(action.get("contacts"))
                elif "history" == action["action"]:
                    self._skype.populate_chats(action.get("chats"), messages=True)
                elif "chats" == action["action"]:
                    self._skype.populate_chats(action.get("chats"), messages=False)
                elif "shared_files" == action["action"]:
                    self._skype.populate_files(action.get("chats"))
            except Exception as e:
                logger.exception("Error working with Skype online service.")
                result["error"] = traceback.format_exc()
                result["error_short"] = util.format_exc(e)
            if self._queue.empty():   result["done"] = True
            if not self.is_working(): result["stop"] = True

            if not self._drop_results: self.postback(result)
            self._is_working = False


class SkypeArchiveThread(WorkerThread):
    """
    Skype export file parser thread, carries out importing to temporary database.
    """


    def __init__(self, callback):
        """
        @param   callback  function to call with parse progress
        """
        super(SkypeArchiveThread, self).__init__(callback)


    def run(self):
        self._is_running = True

        def progress(**kwargs):
            if kwargs and not self._drop_results: self.postback(kwargs)
            return self._is_working

        while self._is_running:
            action = self._queue.get()
            if not action: continue # while self._is_running

            self._is_working, self._drop_results = True, False
            result = {"action": action["action"], "opts": action, "done": True}
            try:
                if "parse" == action["action"]:
                    action["db"].export_read(progress)
            except Exception as e:
                logger.exception("Error parsing Skype export %s.", action["db"].export_path)
                result["error"] = traceback.format_exc()
                result["error_short"] = util.format_exc(e)
            if not self.is_working(): result["stop"] = True

            if not self._drop_results: self.postback(result)
            self._is_working = False
