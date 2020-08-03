# -*- coding: utf-8 -*-
"""
Background workers for potentially long-running tasks like searching and
diffing.

------------------------------------------------------------------------------
This file is part of Skyperious - Skype chat history tool.
Released under the MIT License.

@author      Erki Suurjaak
@created     10.01.2012
@modified    02.08.2020
------------------------------------------------------------------------------
"""
import datetime
import logging
import Queue
import re
import threading
import traceback

try:
    import wx
except ImportError:
    pass # Most functionality works without wx

from . lib import util
from . lib.vendor import step

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
        self._queue = Queue.Queue()


    def work(self, data):
        """
        Registers new work to process. Stops current work, if any. Starts 
        thread if not running.

        @param   data  a dict with work data
        """
        self._queue.put(data)
        if not self._is_running: self.start()


    def stop(self):
        """Stops the worker thread."""
        self._is_running   = False
        self._is_working   = False
        self._drop_results = True
        self._queue.put(None) # To wake up thread waiting on queue


    def stop_work(self, drop_results=False):
        """
        Signals to stop the currently ongoing work, if any. Obtained results
        will be posted back, unless drop_results is True.
        """
        self._is_working = False
        self._drop_results = drop_results


    def is_working(self):
        """Returns whether the thread is currently doing work."""
        return self._is_working


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
                        wrap_html = lambda x: wx.lib.wordwrap.wordwrap(x, width, dc)
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
                FACTORY = lambda x: step.Template(TEMPLATES[x], escape=is_html)
                logger.info('Searching "%s" in %s (%s).',
                            search["text"], search["table"], search["db"])

                parser = skypedata.MessageParser(search["db"],
                                                 wrapper=wrap_html)
                # {"output": text with results, "map": link data map}
                # map data: {"contact:666": {"contact": {contact data}}, }
                result_type, result_count, count = None, 0, 0
                result = {"output": "", "map": {},
                          "search": search, "count": 0}
                sql, params, match_words = query_parser.Parse(search["text"])

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
                    chats.sort(key=lambda x: x["title"])
                    chat_map = {} # {chat id: {chat data}}
                    template_chat = FACTORY("chat")
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
                            count += 1
                            result_count += 1
                            try: result["output"] += template_chat.expand(locals())
                            except Exception:
                                logger.exception("Error formatting search result for chat %s in %s.",
                                                 chat, search["db"])
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
                    if not self._is_working:
                        break # break for chat in chats
                if result["output"] and not self._drop_results:
                    result["count"] = result_count
                    self.postback(result)
                    result = {"output": "", "map": {}, "search": search,
                              "count": 0}

                # Find contacts with a matching name
                if self._is_working and "contacts" == search["table"] \
                and match_words:
                    count = 0
                    contacts = search["db"].get_contacts()
                    # Possibly more: country (ISO code, need map), birthday
                    # (base has YYYYMMDD in integer field).
                    match_fields = [
                        "given_displayname", "displayname", "skypename",
                        "province", "city", "pstnnumber", "phone_home",
                        "phone_office", "phone_mobile", "homepage", "emails",
                        "about", "mood_text",
                    ]
                    template_contact = FACTORY("contact")
                    for contact in contacts:
                        match = False
                        fields_filled = {}
                        for field in match_fields:
                            if contact[field]:
                                val = contact[field]
                                if self.match_all(val, match_words):
                                    match = True
                                    val = pattern_replace.sub(wrap_b, val)
                                fields_filled[field] = val
                        if match:
                            count += 1
                            result_count += 1
                            try: result["output"] += template_contact.expand(locals())
                            except Exception:
                                logger.exception("Error formatting search result for contact %s in %s.",
                                                 contact, search["db"])
                                count -= 1
                                result_count -= 1
                                continue # for contact
                            if not (self._drop_results
                            or count % conf.SearchResultsChunk):
                                result["count"] = result_count
                                self.postback(result)
                                result = {"output": "", "map": {},
                                          "search": search, "count": 0}
                        if not self._is_working:
                            break # break for contact in contacts
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
                        ascending=False, use_cache=False)
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
                            break # break for m in messages

                infotext = search["table"]
                if self._is_working and "all tables" == search["table"]:
                    infotext, result_type = "", "table row"
                    # Search over all fields of all tables.
                    template_table = FACTORY("table")
                    template_row = FACTORY("row")
                    for table in search["db"].get_tables():
                        table["columns"] = search["db"].get_table_columns(
                            table["name"])
                        sql, params, words = query_parser.Parse(search["text"],
                                                                table)
                        if not sql:
                            continue # continue for table in search["db"]..
                        rows = search["db"].execute(sql, params)
                        row = rows.fetchone()
                        namepre, namesuf = ("<b>", "</b>") if row else ("", "")
                        countpre, countsuf = (("<a href='#%s'>" % 
                            step.escape_html(table["name"]), "</a>") if row
                            else ("", ""))
                        infotext += (", " if infotext else "") \
                                    + namepre + table["name"] + namesuf
                        if not row:
                            continue # continue for table in search["db"]..
                        result["output"] = template_table.expand(locals())
                        count = 0
                        while row:
                            count += 1
                            result_count += 1
                            try: result["output"] += template_row.expand(locals())
                            except Exception:
                                logger.exception("Error formatting search result for row %s in %s.",
                                                 row, search["db"])
                                count -= 1
                                result_count -= 1
                                continue # for contact
                            key = "table:%s:%s" % (table["name"], count)
                            result["map"][key] = {"table": table["name"],
                                                  "row": row}
                            if not count % conf.SearchResultsChunk \
                            and not self._drop_results:
                                result["count"] = result_count
                                self.postback(result)
                                result = {"output": "", "map": {},
                                          "search": search, "count": 0}
                            if not self._is_working or (is_html
                            and result_count >= conf.MaxSearchTableRows):
                                break # break while row
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
                        if not self._is_working or (is_html
                        and result_count >= conf.MaxSearchTableRows):
                            break # break for table in search["db"]..
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
            diff = self.get_chat_diff_left(chat, db1, db2, postback)
            if not self._is_working:
                break # break for index, chat in enumerate(compared)
            if diff["messages"] \
            or (chat["message_count"] and diff["participants"]):
                new_chat = not chat["c2"]
                newstr = "" if new_chat else "new "
                info = info_template.expand(chat=chat)
                if new_chat:
                    info += " - new chat"
                if diff["messages"]:
                    info += ", %s" % util.plural("%smessage" % newstr,
                                                 diff["messages"])
                else:
                    info += ", no messages"
                if diff["participants"] and not new_chat:
                    info += ", %s" % (util.plural("%sparticipant" % newstr,
                                                  diff["participants"]))
                info += ".<br />"
                result["output"] += info
                result["chats"].append({"chat": chat, "diff": diff})
            result["index"] = postback["index"]
            if not self._drop_results:
                if index < len(compared) - 1:
                    result["status"] = ("Scanning %s." % 
                                        compared[index + 1]["title_long_lc"])
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
        error, e = None, None
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
            count_messages = 0
            count_participants = 0

            for index, chat in enumerate(compared):
                result["chatindex"] = index
                postback = dict((k, v) for k, v in result.items()
                                if k not in ["output", "chats", "params"])
                diff = self.get_chat_diff_left(chat, db1, db2, postback)
                if not self._is_working:
                    break # break for index, chat in enumerate(compared)
                if diff["messages"] \
                or (chat["message_count"] and diff["participants"]):
                    chat1 = chat["c1"]
                    chat2 = chat["c2"]
                    new_chat = not chat2
                    if new_chat:
                        chat2 = chat1.copy()
                        chat["c2"] = chat2
                        chat2["id"] = db2.insert_conversation(chat2, db1)
                    if diff["participants"]:
                        db2.insert_participants(chat2, diff["participants"],
                                                db1)
                        count_participants += len(diff["participants"])
                    if diff["messages"]:
                        db2.insert_messages(chat2, diff["messages"], db1, chat1,
                                            self.yield_ui, self.REFRESH_COUNT)
                        count_messages += len(diff["messages"])

                    newstr = "" if new_chat else "new "
                    info = "Merged %s" % chat["title_long_lc"]
                    if new_chat:
                        info += " - new chat"
                    if diff["messages"]:
                        info += ", %s" % util.plural("%smessage" % newstr,
                                                     diff["messages"])
                    else:
                        info += ", no messages"
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
        finally:
            if not self._drop_results:
                if compared:
                    info = "Merged %s" % util.plural("new message",
                                                     count_messages)
                    if count_participants:
                        info += " and %s" % util.plural("new participant",
                                                        count_participants)
                    info += " \n\nto %s." % db2
                else:
                    info = "Nothing new to merge from %s to %s." % (db1, db2)
                result = {"type": "diff_merge_left", "done": True,
                          "output": info, "params": params, "chats": [] }
                if error:
                    result["error"] = error
                    if e: result["error_short"] = repr(e)
                self.postback(result)


    def work_merge_left(self, params):
        """
        Worker branch that merges differences given in params, posting progress
        back to application.
        """
        error, e = None, None
        db1, db2 = params["db1"], params["db2"]
        chats = params["chats"]
        count_messages = 0
        count_participants = 0
        result = {"count": sum(len(x["diff"]["messages"]) for x in chats),
                  "index": 0, "chatindex": 0, "chatcount": len(chats),
                  "type": "merge_left", "output": "", "chats": [],
                  "params": params}
        try:
            for index, chat_data in enumerate(chats):
                if not self._is_working:
                    break # break for i, chat_data in enumerate(chats)
                chat1 = chat_data["chat"]["c1"]
                chat2 = chat_data["chat"]["c2"]
                messages = chat_data["diff"]["messages"]
                participants = chat_data["diff"]["participants"]
                html = "Merged %s" % chat1["title_long_lc"]
                if not chat2:
                    html += " - new chat"
                if messages:
                    newstr = "" if not chat2 else "new "
                    html += ", %s" % util.plural("%smessage" % newstr, messages)
                else:
                    html += ", no messages"
                html += "."
                if not chat2:
                    chat2 = chat1.copy()
                    chat_data["chat"]["c2"] = chat2
                    chat2["id"] = db2.insert_conversation(chat2, db1)
                if participants:
                    db2.insert_participants(chat2, participants, db1)
                    count_participants += len(participants)
                if messages:
                    db2.insert_messages(chat2, messages, db1, chat1,
                                        self.yield_ui, self.REFRESH_COUNT)
                    count_messages += len(messages)
                if not self._drop_results:
                    result.update(output=html, chatindex=index,
                                  chats=[chat_data["chat"]])
                    result["index"] += len(messages)
                    if index < len(chats) - 1:
                        result["status"] = ("Merging %s."
                            % chats[index + 1]["chat"]["title_long_lc"])
                    self.postback(result)
                    result = dict(result, output="", chats=[])
        except Exception as e:
            error = traceback.format_exc()
        finally:
            html = "Nothing to merge."
            if chats:
                html = "Merged %s" % util.plural("new message",
                                                 count_messages)
                if count_participants:
                    html += " and %s" % util.plural("new participant",
                                                    count_participants)
                html += " \n\nto %s." % db2
            if not self._drop_results:
                result = {"type": "merge_left", "done": True, "output": html,
                          "params": params}
                if error:
                    result["error"] = error
                    if e: result["error_short"] = repr(e)
                self.postback(result)


    def get_chat_diff_left(self, chat, db1, db2, postback=None):
        """
        Compares the chat in the two databases and returns the differences from
        the left as {"messages": [message IDs different in db1],
                     "participants": [participants different in db1] }.

        @param   postback  if {"count": .., "index": ..}, updates index
                           and posts the result at POSTBACK_COUNT intervals
        """
        c = chat
        participants1 = c["c1"]["participants"] if c["c1"] else []
        participants2 = c["c2"]["participants"] if c["c2"] else []
        c2p_map = dict((p["identity"], p) for p in participants2)
        c1p_diff = [p for p in participants1 if p["identity"] not in c2p_map]
        c1m_diff = [] # [(id, datetime), ] messages different in chat 1

        if not c["messages1"]:
            messages1, messages2 = [], [] # Left side empty, skip all messages
        elif not c["messages2"]:
            messages1, messages2 = [], [] # Right side empty, take whole left
            messages_all = db1.get_messages(c["c1"], use_cache=False)
            c1m_diff = [(m["id"], m["datetime"]) for m in messages_all]
        else:
            messages1 = db1.get_messages(c["c1"], use_cache=False)
            messages2 = db2.get_messages(c["c2"], use_cache=False)
            parser1 = skypedata.MessageParser(db1)
            parser2 = skypedata.MessageParser(db2)
            parse_options = {"format": "text", "merge": True}

            m1map = {} # {remote_id: [(id, datetime), ], }
            m2map = {} # {remote_id: [(id, datetime), ], }
            m1_no_remote_ids = [] # [(id, datetime), ] with a NULL remote_id
            m2_no_remote_ids = [] # [(id, datetime), ] with a NULL remote_id
            m1bodymap = {} # {author+type+body: [(id, datetime), ], }
            m2bodymap = {} # {author+type+body: [(id, datetime), ], }
            difftexts = {} # {(id, datetime): text, }

            # Assemble maps by remote_id and create diff texts. remote_id is
            # not unique and can easily have duplicates.
            things = [(messages1, m1map, m1_no_remote_ids, m1bodymap, parser1),
                      (messages2, m2map, m2_no_remote_ids, m2bodymap, parser2)]
            for messages, idmap, noidmap, bodymap, parser in things:
                for i, m in enumerate(messages):
                    # Avoid keeping whole messages in memory, can run out.
                    m_cache = (m["id"], m.get("datetime"))
                    if m["remote_id"]:
                        if m["remote_id"] not in idmap:
                            idmap[m["remote_id"]] = []
                        idmap[m["remote_id"]].append(m_cache)
                    else:
                        noidmap.append(m_cache)
                    # In these messages, parsed body can differ even though
                    # message is the same: contact names are taken from current
                    # database values. Using raw values instead.
                    if m["type"] in self.MESSAGE_TYPES_IGNORE_BODY:
                        t = m["identities"] or ""
                        if skypedata.MESSAGE_TYPE_LEAVE == m["type"]:
                            t = m["author"]
                    else:
                        t = parser.parse(m, output=parse_options)
                    t = t if isinstance(t, str) else t.encode("utf-8")
                    author = (m["author"] or "").encode("utf-8")
                    difftext = "%s-%s-%s" % (author, m["type"], t)
                    difftexts[m_cache]  = difftext
                    if difftext not in bodymap: bodymap[difftext] = []
                    bodymap[difftext].append(m_cache)
                    if i and not i % self.REFRESH_COUNT:
                        self.yield_ui()
                    if postback: postback["index"] += 1
                    if postback and i and not i % self.POSTBACK_COUNT:
                        self.postback(postback)

            # Compare assembled remote_id maps between databases and see if
            # there are no messages with matching body in the other database.
            remote_id_messages = [(r, j) for r, i in m1map.items() for j in i]
            for i, (remote_id, m) in enumerate(remote_id_messages):
                if remote_id in m2map:
                    is_match = lambda x: (difftexts[m] == difftexts[x])
                    if not any(filter(is_match, m2map[remote_id])):
                        c1m_diff.append(m) # Nothing with same remote_id+body
                else:
                    c1m_diff.append(m)
                if i and not i % self.REFRESH_COUNT:
                    self.yield_ui()

            # For messages with no remote_id-s, compare by author-type-body key
            # and see if there are no matching messages close in time.
            for i, m in enumerate(m1_no_remote_ids):
                potential_matches = m2bodymap.get(difftexts[m], [])
                if not [m2 for m2 in potential_matches
                        if self.match_time(m[1], m2[1], 180)]:
                    c1m_diff.append(m)
                if i and not i % self.REFRESH_COUNT:
                    self.yield_ui()

        message_ids1 = [m[0] for m in sorted(c1m_diff, key=lambda x: x[1])]
        result = { "messages": message_ids1, "participants": c1p_diff }
        return result


    def match_time(self, d1, d2, leeway_seconds=0):
        """Whether datetimes might be same but from different timezones."""
        result = False
        d1, d2 = (d1, d2) if d1 and d2 and (d1 < d2) else (d2, d1)
        delta = d2 - d1 if d1 and d2 else datetime.timedelta()
        if util.timedelta_seconds(delta) > 24 * 3600:
            delta = datetime.timedelta() # Skip if not even within same day
        for hour in range(int(util.timedelta_seconds(delta) / 3600) + 1):
            d1plus = d1 + datetime.timedelta(hours=hour)
            result = util.timedelta_seconds(d2 - d1plus) < leeway_seconds
            if result:
                break # break for hour in range(..
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
                    break # break for filename in skypedata.detect_data...

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
            result = {"action": action["action"], "opts": action, "done": True}
            try:
                if "login" == action["action"]:
                    self._skype.login(password=action["password"])
                elif "populate" == action["action"]:
                    self._skype.populate(action.get("chats"))
            except Exception as e:
                result["error"] = traceback.format_exc()
                result["error_short"] = util.format_exc(e)
            if not self._is_working: result["stop"] = True

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
            return self.is_working 

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
            if not self._is_working: result["stop"] = True

            if not self._drop_results: self.postback(result)
            self._is_working = False
