# -*- coding: utf-8 -*-
"""
Background workers for potentially long-running tasks like searching and
diffing.

------------------------------------------------------------------------------
This file is part of Skyperious - a Skype database viewer and merger.
Released under the MIT License.

@author      Erki Suurjaak
@created     10.01.2012
@modified    02.11.2013
------------------------------------------------------------------------------
"""
import datetime
import Queue
import re
import threading
import time
import traceback
import wx

from third_party import step

import conf
import main
import searchparser
import skypedata
import templates
import util


class WorkerThread(threading.Thread):
    """Base class for worker threads."""

    def __init__(self, callback):
        """
        @param   callback  function to call with result chunks
        """
        threading.Thread.__init__(self)
        self.daemon = True # Daemon threads do not keep application running
        self._callback = callback
        self._is_running = False
        self._stop_work = False   # Flag to stop the current work
        self._drop_results = False # Flag to not post back obtained results
        self._queue = Queue.Queue()
        self.start()


    def work(self, data):
        """
        Registers new work to process. Stops current work, if any.

        @param   data  a dict with work data
        """
        self._stop_work = True
        self._queue.put(data)


    def stop(self):
        """Stops the worker thread."""
        self._is_running = False
        self._drop_results = True
        self._stop_work = True
        self._queue.put(None) # To wake up thread waiting on queue


    def stop_work(self, drop_results=False):
        """
        Signals to stop the currently ongoing work, if any. Obtained results
        will be posted back, unless drop_results is True.
        """
        self._stop_work = True
        self._drop_results = drop_results


    def postback(self, data):
        # Check whether callback is still bound to a valid object instance
        if getattr(self._callback, "__self__", True):
            time.sleep(0.5) # Feeding results too fast makes GUI unresponsive
            self._callback(data)


    def yield_ui(self):
        """Allows UI to respond to user input."""
        try: wx.YieldIfNeeded()
        except: pass


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
        template_chat = step.Template(templates.SEARCH_ROW_CHAT_HTML)
        template_contact = step.Template(templates.SEARCH_ROW_CONTACT_HTML)
        template_message = step.Template(templates.SEARCH_ROW_MESSAGE_HTML)
        template_row = step.Template(templates.SEARCH_ROW_TABLE_HTML)
        template_table = step.Template(templates.SEARCH_ROW_TABLE_HEADER_HTML)
        query_parser = searchparser.SearchQueryParser()
        wrap_b = lambda x: "<b>%s</b>" % x.group(0)
        result = None
        while self._is_running:
            try:
                search = self._queue.get()
                if not search:
                    continue # continue while self._is_running
                self._stop_work = False
                self._drop_results = False
                parser = skypedata.MessageParser(search["db"])
                # {"html": html with results, "map": link data map}
                # map data: {"contact:666": {"contact": {contact data}}, }
                result_type, result_count, count = None, 0, 0
                result = {"html": "", "map": {},
                          "search": search, "count": 0}
                sql, params, match_words = query_parser.Parse(search["text"])

                # Turn wildcard characters * into regex-compatible .*
                match_words_re = [".*".join(map(re.escape, w.split("*")))
                                  for w in match_words]
                patt = "(%s)" % "|".join(match_words_re)
                # For replacing matching words with <b>words</b>
                pattern_replace = re.compile(patt, re.IGNORECASE)

                # Find chats with a matching title or matching participants
                chats = search["db"].get_conversations()
                chats.sort(key=lambda x: x["title"])
                chat_map = {} # {chat id: {chat data}}
                for chat in chats:
                    chat_map[chat["id"]] = chat
                    if "conversations" == search["table"] and match_words:
                        title_matches = False
                        matching_authors = []
                        if self.match_all(chat["title"], match_words):
                            title_matches = True
                        for participant in chat["participants"]:
                            contact = participant["contact"]
                            if contact:
                                for n in filter(None, [contact["fullname"],
                                contact["displayname"], contact["identity"]]):
                                    if self.match_all(n, match_words) \
                                    and contact not in matching_authors:
                                        matching_authors.append(contact)

                        if title_matches or matching_authors:
                            count += 1
                            result_count += 1
                            result["html"] += template_chat.expand(locals())
                            key = "chat:%s" % chat["id"]
                            result["map"][key] = {"chat": chat["id"]}
                            if not count % conf.SearchResultsChunk \
                            and not self._drop_results:
                                result["count"] = result_count
                                self.postback(result)
                                result = {"html": "", "map": {},
                                          "search": search, "count": 0}
                    if self._stop_work:
                        break # break for chat in chats
                if result["html"] and not self._drop_results:
                    result["count"] = result_count
                    self.postback(result)
                    result = {"html": "", "map": {}, "search": search,
                              "count": 0}

                # Find contacts with a matching name
                if not self._stop_work and "contacts" == search["table"] \
                and match_words:
                    count = 0
                    contacts = search["db"].get_contacts()
                    # Possibly more: country (ISO code, need map), birthday
                    # (base has YYYYMMDD in integer field).
                    match_fields = [
                        "displayname", "skypename", "province", "city",
                        "pstnnumber", "phone_home", "phone_office",
                        "phone_mobile", "homepage", "emails", "about",
                        "mood_text",
                    ]
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
                            result["html"] += template_contact.expand(locals())
                            if not (self._drop_results
                            or count % conf.SearchResultsChunk):
                                result["count"] = result_count
                                self.postback(result)
                                result = {"html": "", "map": {},
                                          "search": search, "count": 0}
                        if self._stop_work:
                            break # break for contact in contacts
                if result["html"] and not self._drop_results:
                    result["count"] = result_count
                    self.postback(result)
                    result = {"html": "", "map": {},
                              "search": search, "count": 0}

                # Find messages with a matching body
                if not self._stop_work and "messages" == search["table"]:
                    count, result_type = 0, "messages"
                    chat_messages = {} # {chat id: [message, ]}
                    chat_order = []    # [chat id, ]
                    messages = search["db"].get_messages(
                        additional_sql=sql, additional_params=params,
                        ascending=False, use_cache=False)
                    for m in messages:
                        chat = chat_map.get(m["convo_id"])
                        chat_title = chat["title_long"]
                        body = parser.parse(m,
                            pattern_replace if match_words else None,
                            html={"w": search["window"].Size.width * 5/9})
                        count += 1
                        result_count += 1
                        result["html"] += template_message.expand(locals())
                        key = "message:%s" % m["id"]
                        result["map"][key] = {"chat": chat["id"],
                                              "message": m["id"]}
                        if not count % conf.SearchResultsChunk \
                        and not self._drop_results:
                            result["count"] = result_count
                            self.postback(result)
                            result = {"html": "", "map": {},
                                      "search": search, "count": 0}
                        if self._stop_work or count >= conf.SearchMessagesMax:
                            break # break for m in messages

                infotext = search["table"]
                if not self._stop_work and "all tables" == search["table"]:
                    infotext, result_type = "", "table row"
                    # Search over all fields of all tables.
                    for table in search["db"].tables_list:
                        sql, params, words = \
                            query_parser.Parse(search["text"], table)
                        if not sql:
                            continue # continue for table in search["db"]..
                        infotext += (", " if infotext else "") + table["name"]
                        rows = search["db"].execute(sql, params)
                        row = rows.fetchone()
                        if not row:
                            continue # continue for table in search["db"]..
                        result["html"] = template_table.expand(locals())
                        count = 0
                        while row:
                            count += 1
                            result_count += 1
                            result["html"] += template_row.expand(locals())
                            key = "table:%s:%s" % (table["name"], count)
                            result["map"][key] = {"table": table["name"],
                                                  "row": row}
                            if not count % conf.SearchResultsChunk \
                            and not self._drop_results:
                                result["count"] = result_count
                                self.postback(result)
                                result = {"html": "", "map": {},
                                          "search": search, "count": 0}
                            if self._stop_work \
                            or result_count >= conf.SearchTableRowsMax:
                                break # break while row
                            row = rows.fetchone()
                        if not self._drop_results:
                            result["html"] += "</table>"
                            result["count"] = result_count
                            self.postback(result)
                            result = {"html": "", "map": {},
                                      "search": search, "count": 0}
                        infotext += " (%s)" % util.plural("result", count)
                        if self._stop_work \
                        or result_count >= conf.SearchTableRowsMax:
                            break # break for table in search["db"]..
                    single_table = ("," not in infotext)
                    infotext = "table%s: %s" % \
                               ("" if single_table else "s", infotext)
                    if not single_table:
                        infotext += "; %s in total" % \
                                    util.plural("result", result_count)
                final_text = "No matches found."
                if self._drop_results:
                    result["html"] = ""
                if result_count:
                    final_text = "Finished searching %s." % infotext

                if self._stop_work:
                    final_text += " Stopped by user."
                elif "messages" == result_type \
                and count >= conf.SearchMessagesMax:
                    final_text += " Stopped at %s limit %s." % \
                                  (result_type, conf.SearchMessagesMax)
                elif "table row" == result_type \
                and count >= conf.SearchTableRowsMax:
                    final_text += " Stopped at %s limit %s." % \
                                  (result_type, conf.SearchTableRowsMax)

                result["html"] += "</table><br /><br />%s</font>" % final_text
                result["done"] = True
                result["count"] = result_count
                self.postback(result)
            except Exception, e:
                if not result:
                    result = {}
                result["done"], result["error"] = True, traceback.format_exc()
                result["error_short"] = "%s: %s" % (type(e).__name__, e.message)
                self.postback(result)


class MergeThread(WorkerThread):
    """
    Merge background thread, compares conversations in two databases, yielding
    results back to main thread in chunks, or merges compared differences.
    """

    # Difftext to compare will be assembled from other fields for these types.
    MESSAGE_TYPES_IGNORE_BODY = [
        skypedata.MESSAGES_TYPE_GROUP, skypedata.MESSAGES_TYPE_PARTICIPANTS,
        skypedata.MESSAGES_TYPE_REMOVE, skypedata.MESSAGES_TYPE_LEAVE,
        skypedata.MESSAGES_TYPE_SHARE_DETAIL
    ]
    # Number of iterations between allowing a UI refresh
    REFRESH_COUNT = 20000


    def run(self):
        self._is_running = True
        while self._is_running:
            params = self._queue.get()
            self._stop_work = False
            self._drop_results = False
            if params and "diff" == params.get("type"):
                self.work_diff(params)
            elif params and "merge" == params.get("type"):
                self.work_merge(params)


    def work_diff(self, params):
        """
        Worker branch that compares all chats for differences, posting results
        back to application.
        """
        # {"htmls": [html result for db1, db2],
        #  "chats": [differing chats in db1, db2]}
        result = {"htmls": ["", ""], "chats": [[], []],
                  "params": params, "index": 0, "type": "diff"}
        db1, db2 = params["db1"], params["db2"]
        chats1 = db1.get_conversations()
        chats2 = db2.get_conversations()
        skypenames1 = [i["identity"] for i in db1.get_contacts()]
        skypenames2 = [i["identity"] for i in db2.get_contacts()]
        skypenames1.append(db1.id)
        skypenames2.append(db2.id)
        c1map = dict((c["identity"], c) for c in chats1)
        c2map = dict((c["identity"], c) for c in chats2)
        compared = []
        for c1 in chats1:
            c2 = c2map.get(c1["identity"])
            c = c1.copy()
            c["messages1"] = c1["message_count"] or 0
            c["messages2"] = c2["message_count"] or 0 if c2 else 0
            c["c1"], c["c2"] = c1, c2
            compared.append(c)
        for c2 in chats2:
            c1 = c1map.get(c2["identity"])
            if not c1:
                c = c2.copy()
                c["messages1"], c["messages2"] = 0, c["message_count"] or 0
                c["c1"], c["c2"] = c1, c2
                compared.append(c)
        compared.sort(key=lambda x: x["title"].lower())
        for index, chat in enumerate(compared):
            diff = self.get_chat_diff(chat, db1, db2)
            if self._stop_work:
                break # break for index, chat in enumerate(compared)
            for i in range(2):
                new_chat = not chat["c1" if i else "c2"]
                newstr = "" if new_chat else "new "
                info = util.htmltag("a", {"href": chat["identity"]},
                                    chat["title_long"], utf=False)
                if new_chat:
                    info += " - new chat"
                if diff["messages"][i]:
                   info += ", %s" % util.plural("%smessage" % newstr,
                                                diff["messages"][i])
                if diff["participants"][i] and newstr:
                        info += ", %s" % (
                            util.plural("%sparticipant" % newstr,
                                        diff["participants"][i]))
                if diff["messages"][i] or diff["participants"][i]:
                    info += ".<br />"
                    result["htmls"][i] += info
                    result["chats"][i].append({"chat": chat, "diff": diff})
            if not self._drop_results:
                self.postback(result)
                result = {"htmls": ["", ""], "chats": [[], []],
                          "params": params, "index": index, "type": "diff"}
        if not self._drop_results:
            result["done"] = True
            self.postback(result)



    def work_merge(self, params):
        """
        Worker branch that merges differences given in params, posting progress
        back to application.
        """
        error, e = None, None
        db1, db2, info = params["db1"], params["db2"], params["info"]
        chats, contacts = params["chats"], params["contacts"]
        source, contactgroups = params["source"], params["contactgroups"]
        count_messages = 0
        count_participants = 0
        try:
            if contacts:
                content = util.plural("contact", contacts)
                self.postback({"type": "merge", "gauge": 0,
                                "message": "Merging %s." % content})
                db2.insert_contacts(contacts, db1)
                self.postback({"type": "merge", "gauge": 100,
                                "message": "Merged %s." % content})
            if contactgroups:
                content = util.plural("contact group", contactgroups)
                self.postback({"type": "merge", "gauge": 0,
                                "message": "Merging %s." % content})
                db2.replace_contactgroups(contactgroups, db1)
                self.postback({"type": "merge", "gauge": 100,
                                "message": "Merged %s." % content})
            for index, chat_data in enumerate(chats):
                if self._stop_work:
                    break # break for i, chat_data in enumerate(chats)
                chat1 = chat_data["chat"]["c2" if source else "c1"]
                chat2 = chat_data["chat"]["c1" if source else "c2"]
                step = -1 if source else 1
                messages1, messages2 = chat_data["diff"]["messages"][::step]
                participants, participants2 = \
                    chat_data["diff"]["participants"][::step]
                if not chat2:
                    chat2 = chat1.copy()
                    chat_data["chat"]["c1" if source else "c2"] = chat2
                    chat2["id"] = db2.insert_chat(chat2, db1)
                if participants:
                    db2.insert_participants(chat2, participants, db1)
                    count_participants += len(participants)
                if messages1:
                    db2.insert_messages(chat2, messages1, db1, chat1,
                                        self.yield_ui, self.REFRESH_COUNT)
                    count_messages += len(messages1)
                self.postback({"type": "merge", "index": index,
                                "params": params})
        except Exception, e:
            error = traceback.format_exc()
        finally:
            if chats:
                if count_participants:
                    info += (" and " if info else "") + \
                            util.plural("participant", count_participants)
                if count_messages:
                    info += (" and " if info else "") \
                        + util.plural("message", count_messages)
            if not self._drop_results:
                result = {"type": "merge", "done": True, "info": info,
                          "source": source, "params": params}
                if error:
                    result["error"] = error
                    if e:
                        result["error_short"] = "%s: %s" % (
                                                type(e).__name__, e.message)
                self.postback(result)


    def get_chat_diff(self, chat, db1, db2):
        """
        Compares the chat in the two databases and returns the differences as
          {"messages": [[IDs of messages different in db1], [..db2]],
           "participants": [[participants different in db1], [..db2]]}.
        """
        c = chat
        messages1 = db1.get_messages(c["c1"], use_cache=False) \
                    if c["c1"] else []
        messages2 = db2.get_messages(c["c2"], use_cache=False) \
                    if c["c2"] else []
        c1m_diff = [] # Messages different in chat 1
        c2m_diff = [] # Messages different in chat 2
        participants1 = c["c1"]["participants"] if c["c1"] else []
        participants2 = c["c2"]["participants"] if c["c2"] else []
        c1p_diff = [] # Participants different in chat 1
        c2p_diff = [] # Participants different in chat 2
        c1p_map = dict((p["identity"], p) for p in participants1)
        c2p_map = dict((p["identity"], p) for p in participants2)

        m1map = {} # {remote_id: [(id, datetime), ], }
        m2map = {} # {remote_id: [(id, datetime), ], }
        m1_no_remote_ids = [] # [(id, datetime), ] with a NULL remote_id
        m2_no_remote_ids = [] # [(id, datetime), ] with a NULL remote_id
        m1bodymap = {} # {author+type+body: [(id, datetime), ], }
        m2bodymap = {} # {author+type+body: [(id, datetime), ], }
        difftexts = {} # {(id, datetime): text, }

        # Skip comparing messages if one side is completely empty
        parser1, parser2 = None, None
        if not messages1:
            c2m_diff = [(m["id"], m.get("datetime")) for m in messages2]
            messages1, messages2 = [], []
        elif not messages2:
            c1m_diff = [(m["id"], m.get("datetime")) for m in messages1]
            messages1, messages2 = [], []
        else:
            parser1 = skypedata.MessageParser(db1)
            parser2 = skypedata.MessageParser(db2)

        # Assemble maps by remote_id and create diff texts. remote_id is
        # not unique and can easily have duplicates.
        things = [(messages1, m1map, m1_no_remote_ids, m1bodymap, parser1),
                  (messages2, m2map, m2_no_remote_ids, m2bodymap, parser2)]
        for messages, idmap, noidmap, bodymap, parser in things:
            for i, m in enumerate(messages):
                # Avoid keeping whole messages in memory, can easily run out.
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
                    t = m["identities"]
                    if skypedata.MESSAGES_TYPE_LEAVE == m["type"]:
                        t = m["author"]
                else:
                    t = parser.parse(m, text={"wrap": False})
                t = t if isinstance(t, str) else t.encode("utf-8")
                author = (m["author"] or "").encode("utf-8")
                difftext = "%s-%s-%s" % (author, m["type"], t)
                difftexts[m_cache]  = difftext
                if difftext not in bodymap: bodymap[difftext] = []
                bodymap[difftext].append(m_cache)
                if i and not i % self.REFRESH_COUNT:
                    self.yield_ui()

        # Compare assembled remote_id maps between databases and see if there
        # are no messages with matching body in the other database.
        remote_id_maps = [(m1map, m2map, c1m_diff), (m2map, m1map, c2m_diff)]
        for map1, map2, output in remote_id_maps:
            remote_id_messages = [(r, j) for r, i in map1.items() for j in i]
            for i, (remote_id, m) in enumerate(remote_id_messages):
                if remote_id in map2:
                    is_match = lambda x: difftexts[m] == difftexts[x]
                    if not filter(is_match, map2[remote_id]):
                        output.append(m) # Nothing with same remote_id and body
                else:
                    output.append(m)
                if i and not i % self.REFRESH_COUNT:
                    self.yield_ui()
            

        # For messages with no remote_id-s, compare by author-type-body key
        # and see if there are no matching messages sufficiently close in time.
        no_remote_ids =  [(m1_no_remote_ids, c1m_diff, m2bodymap),
                          (m2_no_remote_ids, c2m_diff, m1bodymap)]
        for m_no_remote_ids, output, mbodymap in no_remote_ids:
            for i, m in enumerate(m_no_remote_ids):
                potential_matches = mbodymap.get(difftexts[m], [])
                if not [m2 for m2 in potential_matches
                        if self.match_time(m[1], m2[1], 180)]:
                    output.append(m)
                if i and not i % self.REFRESH_COUNT:
                    self.yield_ui()
        for p in participants1:
            if p["identity"] not in c2p_map:
                c1p_diff.append(p)
        for p in participants2:
            if p["identity"] not in c1p_map:
                c2p_diff.append(p)

        c1m_diff.sort(lambda a, b: cmp(a[1], b[1]))
        c2m_diff.sort(lambda a, b: cmp(a[1], b[1]))
        message_ids1 = [m[0] for m in c1m_diff]
        message_ids2 = [m[0] for m in c2m_diff]

        result = { "messages": [message_ids1, message_ids2],
                   "participants": [c1p_diff, c2p_diff] }
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



class ContactSearchThread(WorkerThread):
    """
    Contact search background thread, uses a running Skype application to
    search Skype userbase for contacts, yielding results back to main thread
    in chunks.
    """

    def run(self):
        self._is_running = True
        while self._is_running:
            search = self._queue.get()
            self._stop_work = False
            self._drop_results = False
            found = {} # { Skype handle: 1, }
            result = {"search": search, "results": []}
            if search and search["handler"]:
                for i, value in enumerate(search["values"]):
                    main.log("Searching Skype contact directory for '%s'.",
                             value)

                    for user in search["handler"].search_users(value):
                        if user.Handle not in found:
                            result["results"].append(user)
                            found[user.Handle] = 1

                        if not (self._drop_results 
                        or len(result["results"]) % conf.ContactResultsChunk):
                            self.postback(result)
                            result = {"search": search, "results": []}

                        if self._stop_work:
                            break # break for user in search["handler"].searc..

                    if result["results"] and not self._drop_results:
                        self.postback(result)
                        result = {"search": search, "results": []}

                    if self._stop_work:
                        break # break for i, value in enumerate(search_values)


                if not self._drop_results:
                    result["done"] = True
                    self.postback(result)



class DetectDatabaseThread(WorkerThread):
    """
    Skype database detection background thread, goes through potential
    directories and yields database filenames back to main thread one by one.
    """

    def run(self):
        self._is_running = True
        while self._is_running:
            search = self._queue.get()
            self._stop_work = self._drop_results = False
            if search:
                all_filenames = set() # To handle potential duplicates
                for filenames in skypedata.detect_databases():
                    filenames = all_filenames.symmetric_difference(filenames)
                    if not self._drop_results:
                        result = {"filenames": filenames}
                        self.postback(result)
                    all_filenames.update(filenames)
                    if self._stop_work:
                        break # break for filename in skypedata.detect_data...

                result = {"done": True, "count": len(all_filenames)}
                self.postback(result)
