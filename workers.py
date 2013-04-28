#-*- coding: utf-8 -*-
"""
Background workers for searching and diffing.

@author      Erki Suurjaak
@created     10.01.2012
@modified    28.04.2013
"""
import cStringIO
import datetime
import Queue
import re
import threading
import time
import xml.etree.cElementTree

import conf
import export
import skypedata
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


    def _postback(self, data):
        time.sleep(0.5) # Feeding results too fast makes GUI unresponsive
        self._callback(data)




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
        pattern_chat    = re.compile("chat\:([^\s]+)")
        pattern_contact = re.compile("from\:([^\s]+)")
        while self._is_running:
            search = self._queue.get()
            self._stop_work = False
            self._drop_results = False
            if search:
                result_count = 0
                parser = skypedata.MessageParser(search["db"])
                # {"html": html with results, "map": link data map}
                # map data: {"contact:666": {"contact": {contact data}}, }
                counts = {"chats": 0, "contacts": 0, "messages": 0}
                result = {"html": "", "map": {},
                          "search": search, "counts": counts}
                # Lists of words to find in either message body, chat title and
                # participant name fields, or contact name fields.
                match_words = filter(None, search["text"].lower().split(" "))
                match_chats, match_contacts = [], []

                for word in match_words[:]:
                    if pattern_chat.match(word):
                        match_chats.append(pattern_chat.split(word)[1])
                        match_words.remove(word)
                    elif pattern_contact.match(word):
                        match_contacts.append(pattern_contact.split(word)[1])
                        match_words.remove(word)
                # For replacing matching words with <b>words</b>
                pattern_replace = re.compile(
                    "(%s)" % "|".join(map(re.escape, match_words)),
                    re.IGNORECASE
                )

                # Find chats with a matching title or matching participants
                chats = search["db"].get_conversations()
                chats.sort(key=lambda x: x["title"])
                chat_map = {} # {chat id: {chat data}}
                for chat in chats:
                    chat_map[chat["id"]] = chat
                    if "conversations" in search["tables"] and match_words:
                        title_matches = False
                        matching_authors = []
                        if self.match_all(chat["title"], match_words):
                            title_matches = True
                        for participant in chat["participants"]:
                            c = participant["contact"]
                            if c:
                                for n in filter(None, [c["fullname"],
                                c["displayname"], c["identity"]]):
                                    if self.match_all(n, match_words) \
                                    and c not in matching_authors:
                                        matching_authors.append(c)

                        if title_matches or matching_authors:
                            result_count += 1
                            counts["chats"] += 1
                            title = chat["title"]
                            if title_matches:
                                title = pattern_replace.sub(
                                    lambda x: "<b>%s</b>" % x.group(0), title
                                )

                            entry = "<tr><td align='right' valign='top'>" \
                                    "<font color='%s'>%s</font></td>" \
                                    "<td colspan='2'><a href='chat:%s'>" \
                                    "<font color='%s'>%s</font></a><br />" % (
                                        conf.HistoryGreyColour, result_count,
                                        chat["id"], conf.HistoryLinkColour,
                                        chat["title_long"]
                            )
                            if title_matches:
                                entry += u"Title matches.<br />"
                            if matching_authors:
                                entry += u"Participant matches: %s.<br />" % \
                                    ", ".join([u"%s (%s)" % (
                                        pattern_replace.sub(
                                            lambda x: "<b>%s</b>" % x.group(0),
                                            c["fullname"] or c["displayname"]
                                        ), pattern_replace.sub(
                                            lambda x: "<b>%s</b>" % x.group(0),
                                            c["identity"]
                                        )
                                    ) for c in matching_authors
                                ])
                            entry += "</td></tr>"
                            result["html"] += entry
                            result["map"]["chat:%s" % chat["id"]] = \
                                {"chat": chat}
                            if not counts["chats"] % conf.SearchResultsChunk \
                            and not self._drop_results:
                                self._postback(result)
                                result = {"html": "", "map": {},
                                          "search": search, "counts": counts}
                    if self._stop_work:
                        break # break for chat in chats
                if result["html"] and not self._drop_results:
                    self._postback(result)
                    result = {"html": "", "map": {}, "search": search,
                              "counts": counts}

                # Find contacts with a matching name
                if not self._stop_work and "contacts" in search["tables"] \
                and match_words:
                    contacts = search["db"].get_contacts()
                    # Possibly more: country (ISO code, need map), birthday
                    # (base has YYYYMMDD in integer field).
                    match_fields = [
                        "displayname", "skypename", "province", "city",
                        "pstnnumber", "phone_home", "phone_office",
                        "phone_mobile", "homepage", "emails", "about",
                        "mood_text"
                    ]
                    field_titles = {
                        "displayname": "Display name",
                        "skypename": "Skype Name",
                        "province": "State/Province",
                        "city": "City",
                        "pstnnumber": "Phone",
                        "phone_home": "Home phone",
                        "phone_office": "Office phone",
                        "phone_mobile": "Mobile phone",
                        "homepage": "Website",
                        "emails": "Emails",
                        "about": "About me",
                        "mood_text": "Mood",
                        "country": "Country/Region",
                        "province": "State/Province",
                    }
                    for contact in contacts:
                        match = False
                        fields_filled = {}
                        for field in match_fields:
                            if contact[field]:
                                value = contact[field]
                                if self.match_all(value, match_words):
                                    match = True
                                    value = pattern_replace.sub(
                                        lambda x: "<b>%s</b>" % x.group(0),
                                        value
                                    )
                                fields_filled[field] = value
                        if match:
                            entry = u""
                            if (not counts["contacts"]) and result_count:
                                entry += "<tr><td colspan='3'><hr /></td></tr>"
                            result_count += 1
                            counts["contacts"] += 1
                            entry += u"<tr><td align='right' valign='top'>" \
                                    "<font color='%s'>%s</font></td>" \
                                    "<td colspan='2'>" \
                                    "<font color='%s'>Contact %s</font>" \
                                    "<br /><table>" % (
                                        conf.HistoryGreyColour, result_count,
                                        conf.ResultContactFieldColour,
                                        pattern_replace.sub(
                                            lambda x: "<b>%s</b>" % x.group(0),
                                            contact["name"]
                                        )
                                    )
                            for field in match_fields:
                                if field in fields_filled:
                                    entry += u"<tr><td nowrap valign='top'>" \
                                            "<font color='%s'>%s</font></td>" \
                                            "<td>&nbsp;</td><td>%s</td></tr>" \
                                             % (conf.ResultContactFieldColour,
                                                field_titles[field],
                                                fields_filled[field]
                                             )
                            entry += "</table><br /></td></tr>"
                            result["html"] += entry
                            result["map"]["contact:%s" % contact["id"]] = \
                                {"contact": contact}
                            if not \
                                counts["contacts"] % conf.SearchResultsChunk \
                            and not self._drop_results:
                                self._postback(result)
                                result = {"html": "", "map": {},
                                          "search": search, "counts": counts}
                        if self._stop_work:
                            break # break for contact in contacts
                if result["html"] and not self._drop_results:
                    self._postback(result)
                    result = {"html": "", "map": {}, "search": search,
                              "counts": counts}

                # Find messages with a matching body
                if not self._stop_work and "messages" in search["tables"]:
                    chat_messages = {} # {chat id: [message, ]}
                    chat_order = []    # [chat id, ]
                    messages = search["db"].get_messages(
                        ascending=False, body_likes=match_words,
                        author_likes=match_contacts, chat_likes=match_chats,
                        use_cache=False
                    )
                    for m in messages:
                        chat = chat_map.get(m["convo_id"], None)
                        chat_title = chat["title_long"]
                        entry = u""
                        if (not counts["messages"]) and result_count:
                            entry += "<tr><td colspan='3'><hr /></td></tr>"
                        result["html"] += entry
                        result_count += 1
                        counts["messages"] += 1
                        time_value = datetime.datetime.fromtimestamp(
                            m["timestamp"]).strftime("%d.%m.%Y %H:%M"
                        )
                        displayname = m["from_dispname"]
                        body = parser.parse(m,
                            pattern_replace if match_words else None,
                            html={"w": search["window"].Size.width * 5 / 9})
                        if type(body) is str:
                            body = body.decode("utf-8")

                        entry = \
                            u"<tr><td align='right' valign='top'>" \
                            "<font color='%s'>%s</font></td>" \
                            "<td valign='top'><a href='message:%s'>" \
                            "<font color='%s'>%s%s</font></a></td>" \
                            "<td align='right' nowrap>&nbsp;&nbsp;" \
                            "<font color='%s'>%s</font></td></tr><tr>" \
                            "<td></td>" \
                            "<td width='100%%' valign='top' colspan='2'>" \
                            "%s<br/></td></tr>" \
                            % (conf.HistoryGreyColour,
                               result_count,
                               m["id"], conf.HistoryLinkColour,
                               displayname,
                               "" if (
                                   skypedata.CHATS_TYPE_SINGLE == chat["type"] \
                                   and m["author"] != search["db"].id
                               ) else " in %s" % chat_title,
                               conf.HistoryTimestampColour, time_value,
                               body
                        )
                        result["html"] += entry
                        result["map"]["message:%s" % m["id"]] = \
                            {"chat": chat, "message": m}
                        if self._stop_work:
                            break # break for m in messages
                        if not counts["messages"] % conf.SearchResultsChunk \
                        and not self._drop_results:
                            self._postback(result)
                            result = {"html": "", "map": {}, "search": search,
                                      "counts": counts}
                        if counts["messages"] >= conf.SearchMessagesMax:
                            break
                        if self._stop_work \
                        or counts["messages"] >= conf.SearchMessagesMax:
                            break # break for c in chat_order

                final_text = "No matches found."
                if self._drop_results:
                    result["html"] = ""
                elif result_count:
                    final_text = ""
                    for table, count in filter(lambda x: x[1], counts.items()):
                        text = util.plural(table[:-1], count)
                        final_text += (", " if final_text else "") + text
                    final_text = "Found %s." % final_text

                if self._stop_work:
                    final_text += " Search stopped by user."
                elif counts["messages"] >= conf.SearchMessagesMax:
                    final_text += " Search stopped at message limit %s." \
                                  % conf.SearchMessagesMax

                result["html"] += "</table><br />%s</font>" % final_text
                result["done"] = True
                self._postback(result)



class DiffThread(WorkerThread):
    """
    Diff background thread, compares conversations in two databases, yielding
    results back to main thread in chunks.
    """

    # Difftext to compare will be assembled from other fields for these types.
    MESSAGE_TYPES_IGNORE_BODY = [
        skypedata.MESSAGES_TYPE_GROUP, skypedata.MESSAGES_TYPE_PARTICIPANTS,
        skypedata.MESSAGES_TYPE_REMOVE, skypedata.MESSAGES_TYPE_LEAVE,
        skypedata.MESSAGES_TYPE_SHARE_DETAIL
    ]


    def run(self):
        self._is_running = True
        while self._is_running:
            params = self._queue.get()
            self._stop_work = False
            self._drop_results = False
            if params:
                # {"htmls": [html result for db1, db2],
                #  "chats": [differing chats in db1, db2]}
                result = {
                    "htmls": ["", ""], "chats": [[], []], "params": params
                }
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
                    c2 = c2map.get(c1["identity"], None)
                    c = c1.copy()
                    c["messages1"] = c1["message_count"] or 0
                    c["messages2"] = c2["message_count"] or 0 if c2 else 0
                    c["c1"] = c1
                    c["c2"] = c2
                    compared.append(c)
                for c2 in chats2:
                    c1 = c1map.get(c2["identity"], None)
                    if not c1:
                        c = c2.copy()
                        c["messages2"] = c["message_count"] or 0
                        c["messages1"] = 0
                        c["c1"] = c1
                        c["c2"] = c2
                        compared.append(c)
                compared.sort(key=lambda x: x["title"])
                for chat in compared:
                    diff = self.get_chat_diff(chat, db1, db2)
                    if self._stop_work:
                        break # break for chat in compared
                    for i in range(2):
                        new_chat = not chat["c1" if i else "c2"]
                        newstr = "" if new_chat else "new "
                        info = export.htmltag("a", {"href": chat["identity"]},
                            chat["title_long"], utf=False
                        )
                        if new_chat:
                            info += " - new chat"
                        skypenames_other = [skypenames1, skypenames2][1 - i]
                        if diff["messages"][i]:
                           info += ", %s" % (
                                util.plural("%smessage" % newstr,
                                    len(diff["messages"][i])
                                )
                           )
                        if diff["participants"][i] and newstr:
                                info += ", %s" % (
                                    util.plural("%sparticipant" % newstr,
                                        len(diff["participants"][i])
                                    )
                                )
                        if diff["messages"][i] or diff["participants"][i]:
                            info += ".<br />"
                            result["htmls"][i] += info
                            result["chats"][i].append(
                                {"chat": chat, "diff": diff}
                            )
                            if not self._drop_results \
                            and not len(result["chats"][i]) \
                            % conf.DiffResultsChunk:
                                self._postback(result)
                                result = {
                                    "htmls": ["", ""], "chats": [[], []],
                                    "params": params
                                }
                if not self._drop_results:
                    result["done"] = True
                    self._postback(result)


    def get_chat_diff(self, chat, db1, db2):
        """
        Compares the chat in the two databases and returns the differences as {
          "messages": [[messages different in db1], [..db2]],
          "participants": [[participants different in db1], [..db2]]
        }.
        """
        c = chat
        messages1 = list(db1.get_messages(c["c1"])) if c["c1"] else []
        messages2 = list(db2.get_messages(c["c2"])) if c["c2"] else []
        c1m_diff = [] # Messages different in chat 1
        c2m_diff = [] # Messages different in chat 2
        participants1 = c["c1"]["participants"] if c["c1"] else []
        participants2 = c["c2"]["participants"] if c["c2"] else []
        c1p_diff = [] # Participants different in chat 1
        c2p_diff = [] # Participants different in chat 2
        c1p_map = dict((p["identity"], p) for p in participants1)
        c2p_map = dict((p["identity"], p) for p in participants2)

        m1map = {} # {remote_id: [message, ], }
        m2map = {} # {remote_id: [message, ], }
        m1_no_remote_ids = [] # [message, ] with a NULL remote_id
        m2_no_remote_ids = [] # [message, ] with a NULL remote_id
        m1bodymap = {} # {author+type+body: [message, ], }
        m2bodymap = {} # {author+type+body: [message, ], }
        difftexts = {} # {id(message): text, }

        # Skip comparing messages if one side is completely empty
        parser1, parser2 = None, None
        if not messages1:
            c2m_diff, messages1, messages2 = messages2, [], []
        elif not messages2:
            c1m_diff, messages1, messages2 = messages1, [], []
        else:
            parser1 = skypedata.MessageParser(db1)
            parser2 = skypedata.MessageParser(db2)

        # Assemble maps by remote_id and create diff texts. remote_id is not
        # unique and can easily have duplicates.
        for messages, idmap, noidmap, bodymap, parser, mdiff in [
        (messages1, m1map, m1_no_remote_ids, m1bodymap, parser1, c1m_diff),
        (messages2, m2map, m2_no_remote_ids, m2bodymap, parser2, c2m_diff)]:
            for m in messages:
                if m["remote_id"]:
                    if m["remote_id"] not in idmap:
                        idmap[m["remote_id"]] = []
                    idmap[m["remote_id"]].append(m)
                else:
                    noidmap.append(m)
                # In these messages, parsed body can differ even though
                # message is the same: contact names are taken from current
                # database values. Using raw values instead.
                if m["type"] in self.MESSAGE_TYPES_IGNORE_BODY:
                    t = m["author"] if skypedata.MESSAGES_TYPE_LEAVE \
                                       == m["type"] else m["identities"]
                else:
                    t = parser.parse(m, text={"wrap": False})
                t = t if type(t) is str else t.encode("utf-8")
                difftext = difftexts[id(m)] = "%s-%s-%s" % (
                    (m["author"] or "").encode("utf-8"), m["type"], t
                )
                if difftext not in bodymap: bodymap[difftext] = []
                bodymap[difftext].append(m)

        # Compare assembled remote_id maps between databases and see if there
        # are no messages with matching body in the other database.
        for remote_id, m in [(r, j) for r, i in m1map.items() for j in i]:
            if remote_id in m2map:
                if not filter(lambda x: difftexts[id(m)] == difftexts[id(x)],
                    m2map[remote_id]
                ):
                    # No message with same remote_id has same body
                    c1m_diff.append(m)
            else:
                c1m_diff.append(m)
        for remote_id, m in [(r, j) for r, i in m2map.items() for j in i]:
            if remote_id in m1map:
                if not filter(lambda x: difftexts[id(m)] == difftexts[id(x)],
                    m1map[remote_id]
                ):
                    # No message with same remote_id has same body
                    c2m_diff.append(m)
            else:
                c2m_diff.append(m)

        # For messages with no remote_id-s, compare by author-type-body key
        # and see if there are no matching messages sufficiently close in time.
        for m in m1_no_remote_ids:
            potential_matches = m2bodymap.get(difftexts[id(m)], [])
            # Allow a 3-minute leeway between timestamps of duplicated messages
            if not [i for i in potential_matches if 
            (abs(i["timestamp"] - m["timestamp"]) < 3 * 60)]:
                c1m_diff.append(m)
        for m in m2_no_remote_ids:
            potential_matches = m1bodymap.get(difftexts[id(m)], [])
            # Allow a 3-minute leeway between timestamps of duplicated messages
            if not [i for i in potential_matches if 
            (abs(i["timestamp"] - m["timestamp"]) < 180)]:
                c2m_diff.append(m)
        for p in participants1:
            if p["identity"] not in c2p_map:
                c1p_diff.append(p)
        for p in participants2:
            if p["identity"] not in c1p_map:
                c2p_diff.append(p)

        c1m_diff.sort(lambda a, b: cmp(a["datetime"], b["datetime"]))
        c2m_diff.sort(lambda a, b: cmp(a["datetime"], b["datetime"]))

        result = {
            "messages": [c1m_diff, c2m_diff],
            "participants": [c1p_diff, c2p_diff]
        }
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
            if search:
                for i, value in enumerate(search["values"]):
                    for user in search["handler"].search_users(value):
                        if user.Handle not in found:
                            result["results"].append(user)
                            found[user.Handle] = 1

                        if not (self._drop_results 
                        or len(result["results"]) % conf.ContactResultsChunk):
                            self._postback(result)
                            result = {"search": search, "results": []}

                        if self._stop_work:
                            break # break for user in search["handler"].searc..

                    if result["results"] and not self._drop_results:
                        self._postback(result)
                        result = {"search": search, "results": []}

                    if self._stop_work:
                        break # break for i, value in enumerate(search_values)

                if not self._drop_results:
                    result["done"] = True
                    self._postback(result)
