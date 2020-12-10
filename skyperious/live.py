# -*- coding: utf-8 -*-
"""
Functionality for communicating with Skype online service.

------------------------------------------------------------------------------
This file is part of Skyperious - Skype chat history tool.
Released under the MIT License.

@author      Erki Suurjaak
@created     08.07.2020
@modified    10.12.2020
------------------------------------------------------------------------------
"""
import base64
import collections
import datetime
import json
import logging
import os
import re
import struct
import sys
import tarfile
import tempfile
import time
import urllib
import warnings

BeautifulSoup = skpy = ijson = None
try: from bs4 import BeautifulSoup
except ImportError: pass
try: import skpy
except ImportError: pass
try: import ijson
except ImportError: pass

from . lib import util

from . import conf
from . import skypedata


logger = logging.getLogger(__name__)


class SkypeLogin(object):
    """
    Class for logging into Skype web account and retrieving chat history.
    """

    RATE_LIMIT  =  30 # Max number of requests in rate window
    RATE_WINDOW =   2 # Length of rate window, in seconds
    RETRY_LIMIT =   3 # Number of attempts to overcome transient I/O errors
    RETRY_DELAY = 0.5 # Sleep interval between retries, in seconds

    # Enum for save() results
    SAVE = type('', (), dict(SKIP=0, INSERT=1, UPDATE=2, NOCHANGE=3))


    def __init__(self, db=None, progress=None):
        """
        @param   db        existing SkypeDatabase instance if not creating new
        @param   progress  callback function invoked with (action, ?error, ?table, ?count, ?total, ?new, ?updated),
                           returning false if work should stop
        """
        self.db           = db   # SQLite database populated with live data
        self.progress     = progress
        self.username     = db.username if db else None
        self.skype        = None # skpy.Skype instance
        self.tokenpath    = None # Path to login tokenfile
        self.cache        = collections.defaultdict(dict) # {table: {identity: {item}}}
        self.populated    = False
        self.query_stamps = [] # [datetime.datetime, ] for rate limiting
        self.msg_stamps   = {} # {remote_id: last timestamp__ms}


    def is_logged_in(self):
        """Returns whether there is active login."""
        return bool(self.skype and self.skype.conn.connected)


    def login(self, username=None, password=None, token=True, init_db=True):
        """
        Logs in to Skype with given username or raises error on failure.
        Can try to use existing tokenfile if available (tokenfiles expire in 24h).
        Creates database if not already created.

        @param   token    whether to use existing tokenfile instead of password
        @param   init_db  whether to create and open Skype database after login
        """
        if self.db and self.db.username: self.username = self.db.username
        if username and not self.username: self.username = username
        path = util.safe_filename(self.username)
        if path != self.username: path += "_%x" % hash(self.username)
        path = self.tokenpath = os.path.join(conf.VarDirectory, "%s.token" % path)

        logger.info("Logging in to Skype online service as '%s'.", self.username)
        kwargslist = []
        if password: kwargslist += [{"user": self.username, "pwd": password, "tokenFile": path}]
        if token and os.path.isfile(path) and os.path.getsize(path):
            kwargslist.insert(0, {"tokenFile": path}) # Try with existing token
        else:
            util.create_file(path)
        for kwargs in kwargslist:
            try: self.skype = skpy.Skype(**kwargs)
            except Exception:
                _, e, tb = sys.exc_info()
                if kwargs is not kwargslist[-1]: continue # for kwargs
                logger.exception("Error logging in to Skype as '%s'.", self.username)
                try: os.unlink(path)
                except Exception: pass
                raise e, None, tb
            else: break # for kwargs
        if init_db: self.init_db()


    def init_db(self, filename=None, truncate=False):
        """Creates SQLite database if not already created."""
        if not self.db:
            path = filename or make_db_path(self.username)
            truncate = truncate or not os.path.exists(path)
            self.db = skypedata.SkypeDatabase(path, truncate=truncate)
            self.db.live = self
        for table in self.db.CREATE_STATEMENTS:
            if table not in self.db.tables: self.db.create_table(table)


    def build_cache(self):
        """Fills in local cache."""
        BINARIES = "avatar_image", "guid", "meta_picture"
        for table in "accounts", "chats", "contacts", "messages":
            key = "identity" if "chats" == table else \
                  "pk_id" if "messages" == table else "skypename"
            cols  = "id, guid, pk_id, remote_id, convo_id, timestamp" if "messages" == table else "*"
            where = " WHERE pk_id IS NOT NULL" if "messages" == table else ""
            dbtable = "conversations" if "chats" == table else table
            for row in self.db.execute("SELECT %s FROM %s%s" % (cols, dbtable, where), log=False):
                for k in BINARIES: # Convert binary fields back from Unicode
                    if isinstance(row.get(k), unicode):
                        try:
                            row[k] = row[k].encode("latin1")
                        except Exception:
                            row[k] = row[k].encode("utf-8")
                self.cache[table][row[key]] = dict(row)
        self.cache["contacts"].update(self.cache["accounts"]) # For name lookup


    def request(self, func, *args, **kwargs):
        """
        Invokes Skype request function with positional and keyword arguments,
        handles request rate limiting and transient communication errors.

        @param   __retry  special keyword argument, does not retry if falsy
        @param   __raise  special keyword argument, does not raise if falsy
        """
        self.query_stamps.append(datetime.datetime.utcnow())
        while len(self.query_stamps) > self.RATE_LIMIT:
            self.query_stamps.pop(0)

        dts = self.query_stamps
        delta = (dts[-1] - dts[0]) if len(dts) == self.RATE_LIMIT else 0
        if delta and delta.total_seconds() < self.RATE_WINDOW:
            time.sleep(self.RATE_WINDOW)
        doretry, doraise = kwargs.pop("__retry", True), kwargs.pop("__raise", True)
        tries = 0
        while True:
            try: return func(*args, **kwargs)
            except Exception:
                tries += 1
                if tries > self.RETRY_LIMIT or not doretry:
                    logger.exception("Error calling %r.", func)
                    if doraise: raise
                    else: return
                time.sleep(self.RETRY_DELAY)
            finally: # Replace with final
                self.query_stamps[-1] = datetime.datetime.utcnow()


    def save(self, table, item, parent=None):
        """
        Saves the item to SQLite table. Returns true if item with the same 
        content already existed.

        @param    parent  chat for messages
        @return           one of SkypeLogin.SAVE
        """
        dbitem = self.convert(table, item, parent=parent)
        if dbitem is None: return self.SAVE.SKIP
        result, dbitem1, table = None, dict(dbitem), table.lower()

        identity = dbitem["skypename"] if table in ("accounts", "contacts") else \
                   dbitem["identity"]  if "chats" == table else dbitem.get("pk_id")
        dbitem0 = self.cache[table].get(identity)
        if "messages" == table and dbitem.get("remote_id") \
        and not isinstance(item, (skpy.SkypeCallMsg, skpy.SkypeMemberMsg, skpy.msg.SkypePropertyMsg)):
            # Look up message by remote_id instead, to detect edited messages
            dbitem0 = next((v for v in self.cache[table].values()
                            if v.get("remote_id") == dbitem["remote_id"]
                            and v["convo_id"] == dbitem["convo_id"]), dbitem0)
        if "chats" == table and isinstance(item, skpy.SkypeGroupChat) \
        and not dbitem.get("displayname"):
            if dbitem0 and dbitem0["displayname"]:
                dbitem["displayname"] = dbitem0["displayname"]
            else: # Assemble name from participants
                for x in item.userIds[:4]: # Use up to 4 names
                    if x not in self.cache["contacts"]:
                        contact = self.request(self.skype.contacts.contact, x, __raise=False)
                        try:
                            if contact: self.save("contacts", contact)
                        except Exception:
                            logger.exception("Error saving contact %r.", contact)
                cc = map(self.get_contact_name, item.userIds)
                dbitem["displayname"] = ", ".join(cc[:4])
                if len(cc) > 4: dbitem["displayname"] += ", ..."
            dbitem1 = dict(dbitem)


        dbtable = "conversations" if "chats" == table else table
        if dbitem0:
            dbitem["id"] = dbitem1["id"] = dbitem0["id"]
            if "messages" == table and dbitem0["pk_id"] != dbitem["pk_id"] \
            and dbitem0.get("remote_id") == dbitem.get("remote_id"):
                # Different messages with same remote_id -> edited or deleted message
                dbitem["edited_by"] = dbitem["author"]
                dbitem["edited_timestamp"] = max(dbitem["timestamp"], dbitem0["timestamp"])
                if dbitem["timestamp__ms"] <= self.msg_stamps[dbitem["remote_id"]]:
                    dbitem.pop("body_xml") # We have a later more valid content
                self.msg_stamps[dbitem["remote_id"]] = max(dbitem["timestamp__ms"], self.msg_stamps[dbitem["remote_id"]])
                if dbitem["timestamp__ms"] > dbitem0["timestamp__ms"]:
                    dbitem.update({k: dbitem0[k] for k in ("pk_id", "guid", "timestamp")})
                result, dbitem1 = self.SAVE.SKIP, dict(dbitem)

            self.db.update_row(dbtable, dbitem, dbitem0, log=False)
            for k, v in dbitem0.items() if result is None else ():
                if k not in dbitem: dbitem[k] = v
        else:
            dbitem["id"] = self.db.insert_row(dbtable, dbitem, log=False)
            dbitem["__inserted__"] = True
            result = self.SAVE.INSERT

        if "messages" == table and "remote_id" in dbitem1 \
        and dbitem1["remote_id"] not in self.msg_stamps:
            self.msg_stamps[dbitem1["remote_id"]] = dbitem1["timestamp__ms"]

        if identity is not None:
            cacheitem = dict(dbitem)
            if "messages" == table: # Retain certain fields only, sparing memory
                cacheitem = dict((k, dbitem[k]) for k in (
                    "id", "guid", "pk_id", "remote_id", "convo_id",
                    "timestamp", "timestamp__ms"
                ) if k in dbitem)
            self.cache[table][identity] = cacheitem
            if "accounts" == table:
                self.cache["contacts"][identity] = cacheitem # For name lookup

        if "chats" == table:
            self.insert_participants(item, dbitem, dbitem0)
            self.insert_chats(item, dbitem, dbitem0)
        if "chats" == table and isinstance(item, skpy.SkypeGroupChat):
            # See if older-style chat entry is present
            identity0 = id_to_identity(item.id)
            chat0 = self.cache["chats"].get(identity0) if identity0 != item.id else None
            if chat0:
                result = self.SAVE.NOCHANGE

        if "messages" == table and isinstance(item, skpy.SkypeFileMsg) and item.file:
            self.insert_transfers(item, dbitem, dbitem0)

        if "messages" == table and isinstance(item, skpy.SkypeCallMsg):
            self.insert_calls(item, dbitem, dbitem0)

        if result is None and dbitem0 and dbitem0.get("__inserted__"):
            result = self.SAVE.SKIP # Primary was inserted during this run, no need to count
        if result is None and dbitem0:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore") # Swallow Unicode equality warnings
                same = all(v == dbitem0[k] for k, v in dbitem1.items() if k in dbitem0)
                result = self.SAVE.NOCHANGE if same else self.SAVE.UPDATE
        return result


    def insert_transfers(self, msg, row, row0):
        """Inserts Transfers-row for SkypeFileMsg, if not already present."""
        try:
            t = dict(is_permanent=1, filename=msg.file.name, convo_id=row["convo_id"],
                     filesize=msg.file.size, starttime=row["timestamp"],
                     chatmsg_guid=row["guid"], chatmsg_index=0,
                     type=skypedata.TRANSFER_TYPE_OUTBOUND, partner_handle=msg.userId,
                     partner_dispname=self.get_contact_name(msg.userId))
            existing = None
            if row0:
                cursor = self.db.execute("SELECT 1 FROM transfers WHERE "
                                         "convo_id = :convo_id AND chatmsg_guid = :guid", row0, log=False)
                existing = cursor.fetchone()
            if not existing: self.db.insert_row("transfers", t, log=False)
        except Exception:
            logger.exception("Error inserting Transfers-row for message %r.", msg)


    def insert_participants(self, chat, row, row0):
        """Inserts Participants-rows for SkypeChat, if not already present."""
        try:
            participants, newcontacts = [], []
            usernames = chat.userIds if isinstance(chat, skpy.SkypeGroupChat) \
                        else set([self.skype.user.id, chat.userId])
            for username in usernames:
                p = dict(is_permanent=1, convo_id=row["id"], identity=username)
                if isinstance(chat, skpy.SkypeGroupChat) and username == chat.creatorId:
                    p.update(rank=1)
                participants.append(p)
            existing = set()
            if row0:
                cursor = self.db.execute("SELECT identity FROM participants "
                                         "WHERE convo_id = :id", row0, log=False)
                existing.update(x["identity"] for x in cursor)
            for p in participants:
                if p["identity"] not in existing:
                    self.db.insert_row("participants", p, log=False)
                if p["identity"] not in self.cache["contacts"]:
                    contact = self.request(self.skype.contacts.contact,
                                           p["identity"], __raise=False)
                    if contact: newcontacts.append(contact)
            for c in newcontacts: self.save("contacts", c)
        except Exception:
            logger.exception("Error inserting Participants-rows for chat %r.", chat)


    def insert_chats(self, chat, row, row0):
        """Inserts Chats-row for SkypeChat, if not already present."""
        try:
            if self.db.execute("SELECT 1 FROM chats "
                               "WHERE conv_dbid = :id", row, log=False).fetchone():
                return

            cursor = self.db.execute("SELECT identity FROM participants "
                                     "WHERE convo_id = :id", row, log=False)
            memberstr = " ".join(sorted(x["identity"] for x in cursor))
            c = dict(is_permanent=1, name=row["identity"], conv_dbid=row["id"],
                     posters=memberstr, participants=memberstr,
                     activemembers=memberstr, friendlyname=row["displayname"])
            self.db.insert_row("chats", c, log=False)
        except Exception:
            logger.exception("Error inserting Chats-row for chat %r.", chat)


    def insert_calls(self, msg, row, row0):
        """Inserts Calls-row for SkypeCallMsg."""
        try:
            if row0 or skpy.SkypeCallMsg.State.Started == msg.state: return

            duration = 0
            bs = BeautifulSoup(msg.content, "html.parser") if BeautifulSoup else None
            for tag in bs.find_all("duration") if bs else ():
                try: duration = max(duration, int(float(tag.text)))
                except Exception: pass

            ts = row["timestamp"] - duration
            c = dict(conv_dbid=row["convo_id"], begin_timestamp=ts,
                     name="1-%s" % ts, duration=duration)
            self.db.insert_row("calls", c, log=False)
        except Exception:
            logger.exception("Error inserting Calls-row for message %r.", msg)


    def convert(self, table, item, parent=None):
        """
        Converts item from SkPy object to Skype database dict.
        """
        result, table = {}, table.lower()

        if table in ("accounts", "contacts"):
            # SkypeContact(id='username', name=Name(first='first', last='last'), location=Location(country='EE'), language='ET', avatar='https://avatar.skype.com/v1/avatars/username/public', birthday=datetime.date(1984, 5, 9))

            result.update(is_permanent=1, skypename=item.id, languages=item.language)
            if item.name:
                name = unicode(item.name)
                result.update(displayname=name, fullname=name)
            if item.birthday:
                result.update(birthday=date_to_integer(item.birthday))
            if item.location and item.location.country:
                result.update(country=item.location.country)
            if item.location and item.location.region:
                result.update(province=item.location.region)
            if item.location and item.location.city:
                result.update(city=item.location.city)
            for phone in item.phones or ():
                if skpy.SkypeContact.Phone.Type.Mobile == phone.type:
                    result.update(phone_mobile=phone.number)
                elif skpy.SkypeContact.Phone.Type.Work == phone.type:
                    result.update(phone_office=phone.number)
                elif skpy.SkypeContact.Phone.Type.Home == phone.type:
                    result.update(phone_home=phone.number)
            if item.raw.get("homepage"):
                result.update(homepage=item.raw["homepage"])
            if item.raw.get("gender"):
                try: result.update(gender=int(item.raw["gender"]))
                except Exception: pass
            if item.raw.get("emails"):
                result.update(emails=" ".join(item.raw["emails"]))

            if item.avatar: # https://avatar.skype.com/v1/avatars/username/public
                raw = self.download_media(item.avatar)
                # main.db has NULL-byte in front of image binary
                if raw: result.update(avatar_image="\0" + raw)

        if "accounts" == table:
            if item.mood:
                result.update(mood_text=unicode(item.mood))
            if re.match(".+@.+", self.username or ""):
                result.update(liveid_membername=self.username)

        elif "chats" == table:

            result.update(identity=item.id)
            if isinstance(item, skpy.SkypeSingleChat):
                # SkypeSingleChat(id='8:username', alerts=True, userId='username')

                result.update(identity=item.userId, type=skypedata.CHATS_TYPE_SINGLE)
                if item.userId not in self.cache["contacts"]:
                    citem = self.request(self.skype.contacts.contact, item.userId, __raise=False)
                    if citem: self.save("contacts", citem)
                result.update(displayname=self.get_contact_name(item.userId))

            elif isinstance(item, skpy.SkypeGroupChat):
                # SkypeGroupChat(id='19:xyz==@p2p.thread.skype', alerts=True, topic='chat topic', creatorId='username;epid={87e22f7c-d816-ea21-6cb3-05b477922f95}', userIds=['username1', 'username2'], adminIds=['username'], open=False, history=True, picture='https://experimental-api.asm.skype.com/..')

                result.update(type=skypedata.CHATS_TYPE_GROUP, meta_topic=item.topic)
                if item.topic:
                    result.update(displayname=item.topic)
                if item.creatorId:
                    creator = re.sub(";.+$", "", item.creatorId)
                    if creator: result.update(creator=creator)
                if item.picture:
                    # https://api.asm.skype.com/v1/objects/0-weu-d14-abcdef..
                    raw = self.get_api_media(item.picture, category="avatar")
                    # main.db has NULL-byte in front of image binary
                    if raw: result.update(meta_picture="\0" + raw)
            else: result = None

        elif "contacts" == table:
            result.update(type=1, isblocked=item.blocked, # type 1: normal contact, 10: bot
                          isauthorized=item.authorised)
            if item.name and item.name.first:
                result.update(firstname=item.name.first)
            if item.name and item.name.last:
                result.update(lastname=item.name.last)
            if item.mood:
                result.update(mood_text=item.mood.plain, rich_mood_text=item.mood.rich)
            if item.avatar:
                result.update(avatar_url=item.avatar)

        elif "messages" == table:

            ts = util.datetime_to_epoch(item.time)
            pk_id, guid = make_message_ids(item.id)
            result.update(is_permanent=1, timestamp=int(ts), author=item.userId,
                          pk_id=pk_id, guid=guid,
                          from_dispname=self.get_contact_name(item.userId),
                          body_xml=item.content, timestamp__ms=ts*1000)

            if parent:
                identity = parent.id if isinstance(parent, skpy.SkypeGroupChat) else parent.userId
                chat = self.cache["chats"].get(identity)
                if not chat:
                    self.save("chats", parent)
                    chat = self.cache["chats"].get(identity)
                result.update(convo_id=chat["id"])
            remote_id = item.raw.get("skypeeditedid") or item.clientId
            if remote_id: result.update(remote_id=hash(remote_id))

            if isinstance(parent, skpy.SkypeSingleChat):
                result.update(dialog_partner=item.userId)

            if isinstance(item, skpy.SkypeTextMsg):
                # SkypeTextMsg(id='1594466183791', type='RichText', time=datetime.datetime(2020, 7, 11, 11, 16, 16, 392000), clientId='16811922854185209745', userId='username', chatId='8:username', content='<ss type="hi">(wave)</ss>')

                result.update(chatmsg_type=skypedata.CHATMSG_TYPE_MESSAGE,
                              type=skypedata.MESSAGE_TYPE_MESSAGE)
                process_message_edit(result)

            elif isinstance(item, skpy.SkypeCallMsg):
                # SkypeCallMsg(id='1593784617947', type='Event/Call', time=datetime.datetime(2020, 7, 3, 13, 56, 57, 949000), clientId='3666747505059875266', userId='username', chatId='8:username', content='<partlist type="ended" alt="" callId="1593784540478"><part identity="8:username"><name>Display Name</name><duration>84.82</duration></part><part identity="8:username2"><name>Display Name 2</name><duration>84.82</duration></part></partlist>', state=SkypeCallMsg.State.Ended, userIds=['username', '8:username2'], userNames=['Display Name', 'Display Name 2'])

                result.update(chatmsg_type=skypedata.CHATMSG_TYPE_SPECIAL2)
                if skpy.SkypeCallMsg.State.Ended == item.state:
                    result.update(type=skypedata.MESSAGE_TYPE_CALL_END)
                else:
                    result.update(type=skypedata.MESSAGE_TYPE_CALL)

            elif isinstance(item, skpy.SkypeContactMsg):
                # SkypeContactMsg(id='1594466296388', type='RichText/Contacts', time=datetime.datetime(2020, 7, 11, 11, 18, 9, 509000), clientId='3846577445969002747', userId='username', chatId='8:username', content='<contacts><c t="s" s="username2" f="Display Name"></c></contacts>', contactIds=['username2'], contactNames=['Display Name'])

                result.update(chatmsg_type=skypedata.CHATMSG_TYPE_SPECIAL,
                              type=skypedata.MESSAGE_TYPE_CONTACTS)

            elif isinstance(item, skpy.SkypeImageMsg):
                # SkypeImageMsg(id='1594466401638', type='RichText/UriObject', time=datetime.datetime(2020, 7, 11, 11, 19, 13, 899000), clientId='566957100626477146', userId='username', chatId='8:username', content='<URIObject uri="https://api.asm.skype.com/v1/objects/0-weu-d3-abcdef.." url_thumbnail="https://api.asm.skype.com/v1/objects/0-weu-d3-abcdef../views/imgt1_anim" type="Picture.1" doc_id="0-weu-d3-abcdef.." width="1191" height="619">To view this shared photo, go to: <a href="https://login.skype.com/login/sso?go=xmmfallback?pic=0-weu-d3-abcdef..">https://login.skype.com/login/sso?go=xmmfallback?pic=0-weu-d3-abcdef..</a><OriginalName v="f.png"></OriginalName><FileSize v="108188"></FileSize><meta type="photo" originalName="f.png"></meta></URIObject>', file=File(name='f.png', size='108188', urlFull='https://api.asm.skype.com/v1/objects/0-weu-d3-abcdef..', urlThumb='https://api.asm.skype.com/v1/objects/0-weu-d3-abcdef../views/imgt1_anim', urlView='https://login.skype.com/login/sso?go=xmmfallback?pic=0-weu-d3-abcdef..'))

                result.update(chatmsg_type=skypedata.CHATMSG_TYPE_SPECIAL,
                              type=skypedata.MESSAGE_TYPE_SHARE_PHOTO)

            elif isinstance(item, skpy.SkypeFileMsg):
                # SkypeFileMsg(id='1594466346559', type='RichText/Media_GenericFile', time=datetime.datetime(2020, 7, 11, 11, 18, 19, 39000), clientId='8167024171841589273', userId='username', chatId='8:username', content='<URIObject uri="https://api.asm.skype.com/v1/objects/0-weu-d3-abcdef.." url_thumbnail="https://api.asm.skype.com/v1/objects/0-weu-d3-abcdef../views/original" type="File.1" doc_id="0-weu-d3-abcdef..">To view this file, go to: <a href="https://login.skype.com/login/sso?go=webclient.xmm&amp;docid=0-weu-d3-abcdef..">https://login.skype.com/login/sso?go=webclient.xmm&amp;docid=0-weu-d3-abcdef..</a><OriginalName v="f.txt"></OriginalName><FileSize v="447"></FileSize></URIObject>', file=File(name='f.txt', size='447', urlFull='https://api.asm.skype.com/v1/objects/0-weu-d3-abcdef..', urlThumb='https://api.asm.skype.com/v1/objects/0-weu-d3-abcdef../views/original', urlView='https://login.skype.com/login/sso?go=webclient.xmm&docid=0-weu-d3-abcdef..'))

                result.update(chatmsg_type=skypedata.CHATMSG_TYPE_SPECIAL, type=skypedata.MESSAGE_TYPE_FILE,
                              body_xml='<files><file index="0" size="%s">%s</file></files>' % 
                                       (urllib.quote(util.to_unicode(item.file.size or 0)),
                                        util.to_unicode(item.file.name or "file").replace("<", "&lt;").replace(">", "&gt;")))

            elif isinstance(item, skpy.msg.SkypeTopicPropertyMsg):
                # SkypeTopicPropertyMsg(id='1594466832242', type='ThreadActivity/TopicUpdate', time=datetime.datetime(2020, 7, 11, 11, 27, 12, 242000), userId='username', chatId='19:abcdef..@thread.skype', content='<topicupdate><eventtime>1594466832367</eventtime><initiator>8:username</initiator><value>The Topic</value></topicupdate>', topic='The Topic')

                result.update(chatmsg_type=skypedata.CHATMSG_TYPE_TOPIC,
                              type=skypedata.MESSAGE_TYPE_TOPIC,
                              body_xml=item.topic)

            elif isinstance(item, skpy.SkypeAddMemberMsg):
                # SkypeAddMemberMsg(id='1594467205492', type='ThreadActivity/AddMember', time=datetime.datetime(2020, 7, 11, 11, 33, 25, 492000), userId='username', chatId='19:abcdef..@thread.skype', content='<addmember><eventtime>1594467205492</eventtime><initiator>8:username</initiator><target>8:username2</target></addmember>', memberId='username2')

                result.update(chatmsg_type=skypedata.CHATMSG_TYPE_CONTACTS,
                              type=skypedata.MESSAGE_TYPE_PARTICIPANTS,
                              identities=item.memberId)

            elif isinstance(item, skpy.SkypeRemoveMemberMsg):
                # SkypeRemoveMemberMsg(id='1594467133414', type='ThreadActivity/DeleteMember', time=datetime.datetime(2020, 7, 11, 11, 32, 13, 414000), userId='username', chatId='19:abcdef..@thread.skype', content='<deletemember><eventtime>1594467133727</eventtime><initiator>8:username</initiator><target>8:username2</target></deletemember>', memberId='username2')

                if item.userId == item.memberId:
                    result.update(chatmsg_type=skypedata.CHATMSG_TYPE_LEAVE,
                                  type=skypedata.MESSAGE_TYPE_LEAVE)
                else:
                    result.update(chatmsg_type=skypedata.CHATMSG_TYPE_REMOVE,
                                  type=skypedata.MESSAGE_TYPE_REMOVE,
                                  identities=item.memberId)

            elif isinstance(item, skpy.SkypeLocationMsg):
                # SkypeLocationMsg(id='1594466687344', type='RichText/Location', time=datetime.datetime(2020, 7, 11, 11, 24, 0, 305000), clientId='12438271979076057148', userId='username', chatId='8:username', content='<location isUserLocation="0" latitude="59436810" longitude="24740695" timeStamp="1594466640235" timezone="Europe/Tallinn" locale="en-US" language="en" address="Kesklinn, Tallinn, 10146 Harju Maakond, Estonia" addressFriendlyName="Kesklinn, Tallinn, 10146 Harju Maakond, Estonia" shortAddress="Kesklinn, Tallinn, 10146 Harju Maakond, Estonia" userMri="8:username"><a href="https://www.bing.com/maps/default.aspx?cp=9.43681~24.740695&amp;dir=0&amp;lvl=15&amp;where1=Kesklinn,%20Tallinn,%2010137%20Harju%20Maakond,%20Estonia">Kesklinn, Tallinn, 10146 Harju Maakond, Estonia</a></location>', latitude=59.43681, longitude=24.740695, address='Kesklinn, Tallinn, 10146 Harju Maakond, Estonia', mapUrl='https://www.bing.com/maps/default.aspx?cp=59.43681~24.740695&dir=0&lvl=15&where1=Kesklinn,%20Tallinn,%2010146 %20Harju%20Maakond,%20Estonia')

                result.update(chatmsg_type=skypedata.CHATMSG_TYPE_SPECIAL,
                              type=skypedata.MESSAGE_TYPE_INFO)

            elif "ThreadActivity/PictureUpdate" == item.type:
                # SkypeMsg(id='1594466869805', type='ThreadActivity/PictureUpdate', time=datetime.datetime(2020, 7, 11, 11, 27, 49, 805000), userId='abcdef..@thread.skype', chatId='19:abcdef..@thread.skype', content='<pictureupdate><eventtime>1594466869930</eventtime><initiator>8:username</initiator><value>URL@https://api.asm.skype.com/v1/objects/0-weu-d15-abcdef..</value></pictureupdate>')

                result.update(chatmsg_type=skypedata.CHATMSG_TYPE_PICTURE,
                              type=skypedata.MESSAGE_TYPE_TOPIC)
                try:
                    tag = BeautifulSoup and BeautifulSoup(item.content, "html.parser").find("initiator")
                    if tag and tag.text:
                        author = id_to_identity(tag.text)
                        result.update(author=author)
                        result.update(from_dispname=self.get_contact_name(author))
                except Exception:
                    logger.warn("Error parsing author from message %r.", item, exc_info=True)

            elif "RichText/Media_Video"    == item.type \
            or   "RichText/Media_AudioMsg" == item.type:
                # SkypeMsg(id='1594466637922', type='RichText/Media_Video', time=datetime.datetime(2020, 7, 11, 11, 23, 10, 45000), clientId='7459423203289210001', userId='username', chatId='8:username', content='<URIObject uri="https://api.asm.skype.com/v1/objects/0-weu-d8-abcdef.." url_thumbnail="https://api.asm.skype.com/v1/objects/0-weu-d8-abcdef../views/thumbnail" type="Video.1/Message.1" doc_id="0-weu-d8-abcdef.." width="640" height="480">To view this video message, go to: <a href="https://login.skype.com/login/sso?go=xmmfallback?vim=0-weu-d8-abcdef..">https://login.skype.com/login/sso?go=xmmfallback?vim=0-weu-d8-abcdef..</a><OriginalName v="937029c3-6a12-4202-bdaf-aac9e341c63d.mp4"></OriginalName><FileSize v="103470"></FileSize></URIObject>')
                # For audio: type="Audio.1/Message.1", "To hear this voice message, go to: ", ../views/audio

                result.update(type=skypedata.MESSAGE_TYPE_SHARE_VIDEO2)

            else: # SkypeCardMsg, SkypeChangeMemberMsg, ..
                result = None

        return result


    def populate(self, chats=()):
        """
        Retrieves all chats and messages, or selected chats only.
        
        @param   chats  list of chat identities to populate if not everything
        """
        if self.populated:
            self.skype = None
            self.login() # Re-login to reset query cache
        self.build_cache()
        if not chats:
            try: self.save("accounts", self.skype.user)
            except Exception:
                logger.exception("Error saving account %r.", self.skype.user)
        cstr = "%s " % util.plural("chat", chats, numbers=False) if chats else ""
        logger.info("Starting to sync %s'%s' from Skype online service as '%s'.",
                    cstr, self.db, self.username)
        self.populate_history(chats)
        self.cache.clear()
        self.populated = True
        logger.info("Finished syncing %s'%s'.", cstr, self.db)


    def populate_history(self, chats=()):
        """
        Retrieves all conversations and their messages.

        @param   chats  list of chat identities to populate if not all
        """
        if self.progress and not self.progress(action="populate", table="chats", start=True):
            return
        if not self.cache: self.build_cache()

        identities = map(identity_to_id, chats or ())
        getter = lambda c: self.request(self.skype.chats.chat, c, __raise=False)
        selchats = {k: v for (k, v) in ((x, getter(x)) for x in identities) if v}

        new, mtotalnew, mtotalupdated, run = 0, 0, 0, True
        updateds, completeds, msgids = set(), set(), set()
        while run:
            mychats = selchats if chats else self.request(self.skype.chats.recent, __raise=False)
            if not mychats: break # while run
            for chat in mychats.values():
                if chat.id.startswith("48:") or chat.id.startswith("28:"):
                    # Skip specials like "48:calllogs" or "28:concierge"
                    continue # for chat
                if isinstance(chat, skpy.SkypeGroupChat) and not chat.userIds:
                    # Weird empty conversation, getMsgs raises 404
                    continue # for chat
                if isinstance(chat, skpy.SkypeSingleChat) and chat.userId == self.skype.user.id:
                    # Conversation with self?
                    continue # for chat
                cidentity = chat.id if isinstance(chat, skpy.SkypeGroupChat) else chat.userId

                if cidentity in updateds: continue # for chat

                mcount, mnew, mupdated, mrun = 0, 0, 0, True
                mfirst, mlast = datetime.datetime.max, datetime.datetime.min
                while mrun:
                    msgs = self.request(chat.getMsgs, __raise=False) or []

                    if msgs and cidentity not in self.cache["chats"]:
                        # Save chat only if there are any messages
                        try: action = self.save("chats", chat)
                        except Exception:
                            logger.exception("Error saving chat %r.", chat)
                            if self.progress and not self.progress(): run = False
                            mrun = False
                            break # while mrun
                        if self.SAVE.INSERT == action: new += 1
                        if action in (self.SAVE.INSERT, self.SAVE.UPDATE):
                            updateds.add(cidentity)
                        if self.progress and not self.progress(
                            action="populate", table="messages", chat=cidentity, start=True
                        ):
                            run = mrun = False
                            break # while mrun

                    for msg in msgs:
                        try: action = self.save("messages", msg, parent=chat)
                        except Exception:
                            logger.exception("Error saving message %r.", msg)
                            if self.progress and not self.progress():
                                msgs, mrun = [], False
                                break # for msg
                            continue # for msg
                        if self.SAVE.SKIP != action:   mcount += 1
                        if self.SAVE.INSERT == action: mnew += 1
                        if self.SAVE.UPDATE == action: mupdated += 1
                        if action in (self.SAVE.INSERT, self.SAVE.UPDATE):
                            mfirst, mlast = min(mfirst, msg.time), max(mlast, msg.time)
                        if self.progress and not self.progress(
                            action="populate", table="messages", chat=cidentity,
                            count=mcount, new=mnew, updated=mupdated
                        ):
                            msgs, mrun = [], False
                            break # for msg
                        if self.SAVE.NOCHANGE == action and msg.id not in msgids:
                            msgs = [] # Stop on reaching already retrieved messages
                            break # for msg
                        msgids.add(msg.id)
                    if not msgs:
                        break # while mrun
                mtotalnew, mtotalupdated = mtotalnew + mnew, mtotalupdated + mupdated
                if (mnew or mupdated):
                    updateds.add(cidentity)
                    if cidentity in self.cache["chats"]:
                        row = self.db.execute("SELECT id, convo_id, MIN(timestamp) AS first, "
                                              "MAX(timestamp) AS last "
                                              "FROM messages WHERE convo_id = :id", self.cache["chats"][cidentity]
                        ).fetchone()
                        self.db.execute("UPDATE conversations SET last_message_id = :id, "
                                        "last_activity_timestamp = :last, "
                                        "creation_timestamp = COALESCE(creation_timestamp, :first) "
                                        "WHERE id = :convo_id", row)
                        completeds.add(cidentity)

                if self.progress and not self.progress(action="populate", table="messages",
                    chat=cidentity, end=True, count=mcount,
                    new=mnew, updated=mupdated, first=mfirst, last=mlast
                ):
                    run = False
                    break # for chat
                if not mrun: break # for chat
            if chats: break # while run

        ids = [self.cache["chats"][x]["id"] for x in updateds
               if x in self.cache["chats"] and x not in completeds]
        for myids in [ids[i:i+999] for i in range(0, len(ids), 999)]:
            # Divide into chunks: SQLite can take up to 999 parameters.
            idstr = ", ".join(":id%s" % (j+1) for j in range(len(myids)))
            where = " WHERE convo_id IN (%s)" % idstr
            args = dict(("id%s" % (j+1), x) for j, x in enumerate(myids))

            stats = self.db.execute("SELECT id, convo_id, MIN(timestamp) AS first, "
                                    "MAX(timestamp) AS last "
                                    "FROM messages%s GROUP BY convo_id" % where, args)
            for row in stats:
                self.db.execute("UPDATE conversations SET last_message_id = :id, "
                                "last_activity_timestamp = :last, "
                                "creation_timestamp = COALESCE(creation_timestamp, :first) "
                                "WHERE id = :convo_id", row)

        if self.progress: self.progress(
            action="populate", table="chats", end=True, count=len(updateds), new=new,
            message_count_new=mtotalnew, message_count_updated=mtotalupdated
        )


    def get_api_media(self, url, category=None):
        """
        Returns media raw binary from Skype API URL via login, or None.

        @param   category  type of media, e.g. "avatar" for avatar image
        """
        url = make_media_url(url, category)
        urls = [url]
        # Some images appear to be available on one domain, some on another
        if not url.startswith("https://experimental-api.asm"):
            url0 = re.sub(r"https\:\/\/.+\.asm", "https://experimental-api.asm", url)
            urls.insert(0, url0)
        for url in urls:
            raw = self.download_media(url)
            if raw: return raw


    def download_media(self, url):
        """Downloads and returns media raw binary from Skype URL via login, or None."""
        try:
            r = self.request(self.skype.conn, "GET", url,
                             auth=skpy.SkypeConnection.Auth.Authorize,
                             __retry=False)
            hdr = lambda r: r.headers.get("content-type", "")
            if r.ok and r.content and any(x in hdr(r) for x in ("image", "audio", "video")):
                return r.content
        except Exception: pass


    def get_contact_name(self, identity):
        """Returns contact displayname or fullname or identity."""
        result = None
        contact = self.cache["contacts"].get(identity)
        if contact:
            result = contact.get("displayname") or contact.get("fullname")
        result = result or identity
        return result



class SkypeExport(skypedata.SkypeDatabase):
    """
    Class for parsing a Skype export file and populating the database.
    File is a JSON file, or a TAR file containing "messages.json".

    The JSON file has the following structure: {
      'exportDate':    '2020-07-06T20:55',
      'userId':        '8:accountname',
      'conversations': [{

        'displayName':     'chat name',
        'version':         1594056032575.0,
        'id':              'chat ID',
        'properties':      {
            'conversationblocked': False,
            'conversationstatus':  None,
            'lastimreceivedtime':  '2020-07-01T11:16:16.634Z',
            'consumptionhorizon':  '1594056032374;1594056031232;2130221778977763996'
        },
        'threadProperties': {
          'membercount': 15,
          'topic':       'chat topic',
          'members':     '["accountname",..]', # Note that the list is a JSON string
        },
        'MessageList':   [{
          'conversationid': 'chat ID', 
          'displayName':    None,
          'messagetype':    'RichText',
          'properties':     None,
          'content':        'message content',
          'version':        1594056032374.0,
          'amsreferences':  None,
          'from':           'accountname',
          'id':             '1594056032374'
          'originalarrivaltime': '2020-07-06T17:20:30.609Z',
        }, ..],
      }, ..],
    }.

    Account names can have prefix like '8:accountname'.

    Message type can be one of the following (not complete list): [
     'Event/Call', 'InviteFreeRelationshipChanged/Initialized', 'Notice', 
     'PopCard', 'RichText', 'RichText/Media_Album', 'RichText/Media_Card',
     'RichText/Media_GenericFile', 'RichText/Media_Video', 'RichText/UriObject',
     'Text', 'ThreadActivity/AddMember', 'ThreadActivity/DeleteMember',
     'ThreadActivity/HistoryDisclosedUpdate', 'ThreadActivity/JoiningEnabledUpdate',
     'ThreadActivity/PictureUpdate', 'ThreadActivity/TopicUpdate'
    ].

    Message properties can be (not complete list):
    - {"edittime": "1592494326832", "isserversidegenerated": True}
    - {"deletetime": "1592494326832"}
    """


    def __init__(self, filename, dbfilename=None):
        self.export_path = filename
        self.export_filesize = os.path.getsize(filename)
        ts = os.path.getmtime(filename)
        self.export_last_modified = datetime.datetime.fromtimestamp(ts)
        self.export_parsed = False
        self.is_temporary = not dbfilename

        if self.is_temporary:
            fh, dbfilename = tempfile.mkstemp(".db")
            os.close(fh)
        super(SkypeExport, self).__init__(dbfilename, truncate=not self.is_temporary)
        for table in self.CREATE_STATEMENTS: self.create_table(table)


    def __str__(self):
        return self.export_path


    def get_filesize(self): return self.export_filesize
    filesize = property(get_filesize, lambda *a: None)

    def get_last_modified(self): return self.export_last_modified
    last_modified = property(get_last_modified, lambda *a: None)


    def close(self):
        """Closes the database, clears memory, and deletes temporary database."""
        super(SkypeExport, self).close()
        try: self.is_temporary and os.unlink(self.filename)
        except Exception: pass


    def export_read(self, progress=None):
        """Reads in export file and populates database."""
        f, tf = None, None
        try:
            f, tf = self.export_open(self.export_path)
        except Exception: raise
        else: self.export_parse(f, progress)
        finally:
            util.try_ignore(f and f.close)
            util.try_ignore(tf and tf.close)
            util.try_ignore(self.clear_cache)
            self.export_parsed = True


    def export_parse(self, f, progress=None):
        """Parses JSON data from file pointer and inserts to database."""
        parser = ijson.parse(f)

        self.get_tables()
        self.table_objects.setdefault("contacts", {})
        self.table_rows.setdefault("participants", [])
        chat, msg, edited_msgs, skip_chat = {}, {}, {}, False
        counts = {"chats": 0, "messages": 0}
        lastcounts = dict(counts)
        logger.info("Parsing Skype export file %s.", self.export_path)
        while True:
            # Prefix is a dot-separated path of nesting, composed of
            # dictionary keys and "item" for list elements,
            # e.g. "conversations.item.MessageList.item.content"
            prefix, evt, value = next(parser, (None, None, None))
            if not prefix and not evt:
                if progress: progress(counts=counts)
                break # while True

            # Dictionary start: ("nested path", "start_map", None)
            if "start_map" == evt:
                if "conversations.item" == prefix:
                    chat = {"is_permanent": 1}
                    chat["id"] = self.insert_row("conversations", chat)
                    counts["chats"] += 1
                elif "conversations.item.MessageList.item" == prefix:
                    msg = {"is_permanent": 1, "convo_id": chat["id"], "__type": None}

            # Dictionary end: ("nested path", "end_map", None)
            elif "end_map" == evt:
                if "conversations.item" == prefix:
                    if skip_chat:
                        skip_chat = False
                        self.delete_row("conversations", chat, log=False)
                        counts["messages"] -= self.execute("DELETE FROM messages WHERE convo_id = ?",
                                                           [chat["id"]], log=False).rowcount
                        counts["chats"] -= 1
                    else:
                        chat = self.export_finalize_chat(chat)
                        self.update_row("conversations", chat, chat, log=False)
                    edited_msgs.clear()
                elif "conversations.item.MessageList.item" == prefix:
                    if not skip_chat: 
                        msg = self.export_finalize_message(msg, chat, edited_msgs)
                        if msg:
                            msg["id"] = self.insert_row("messages", msg, log=False)
                            counts["messages"] += 1

            # List start: ("nested path", "start_array", None)
            elif "start_array" == evt: pass

            # List end: ("nested path", "end_array", None)
            elif "end_array" == evt: pass

            # List element start: ("nested path.item", "data type", element value)
            elif (prefix or "").endswith(".item"): pass

            # Dictionary key: ("nested path", "map_key", "key name")
            elif "map_key" == evt: pass

            # Dictionary value: ("nested path.key name", "data type", value)
            else:
                if "userId" == prefix:
                    account = dict(skypename=id_to_identity(value), is_permanent=1)
                    self.insert_row("accounts", account)
                    self.update_accountinfo()

                elif "conversations.item.id" == prefix:
                    # Skip specials like "48:calllogs" or "28:concierge"
                    skip_chat = value.startswith("48:") or value.startswith("28:")
                    chat["identity"] = value
                    chat["type"] = skypedata.CHATS_TYPE_GROUP
                    if value.startswith("8:"):
                        chat["identity"] = value[2:]
                        chat["type"] = skypedata.CHATS_TYPE_SINGLE 

                elif "conversations.item.displayName" == prefix:
                    chat["displayname"] = value

                elif "conversations.item.threadProperties.topic" == prefix:
                    chat["meta_topic"] = value

                elif "conversations.item.threadProperties.members" == prefix:
                    if skip_chat: continue # while True
                    for identity in map(id_to_identity, json.loads(value)):
                        if identity not in self.table_objects["contacts"] and identity != self.id:
                            contact = dict(skypename=identity, is_permanent=1)
                            contact["id"] = self.insert_row("contacts", contact)
                            self.table_objects["contacts"][identity] = contact
                        p = dict(is_permanent=1, convo_id=chat["id"], identity=identity)
                        p["id"] = self.insert_row("participants", p, log=False)
                        self.table_rows["participants"].append(p)

                elif "conversations.item.MessageList.item.id" == prefix:
                    if skip_chat: continue # while True
                    pk_id, guid = make_message_ids(value)
                    msg.update(pk_id=pk_id, guid=guid)

                elif "conversations.item.MessageList.item.from" == prefix:
                    if skip_chat: continue # while True
                    msg["author"] = id_to_identity(value)

                elif "conversations.item.MessageList.item.displayName" == prefix:
                    if value: msg["from_dispname"] = value

                elif "conversations.item.MessageList.item.content" == prefix:
                    msg["body_xml"] = value

                elif "conversations.item.MessageList.item.originalarrivaltime" == prefix:
                    if skip_chat: continue # while True
                    ts = self.export_parse_timestamp(value)
                    msg["timestamp"] = int(ts)
                    msg["timestamp__ms"] = ts * 1000

                elif "conversations.item.MessageList.item.properties.edittime" == prefix:
                    msg["edited_timestamp"] = int(value) / 1000

                elif "conversations.item.MessageList.item.properties.deletetime" == prefix:
                    if skip_chat: continue # while True
                    msg["edited_timestamp"] = int(value) / 1000
                    msg["body_xml"] = ""

                elif "conversations.item.MessageList.item.properties.isserversidegenerated" == prefix:
                    if skip_chat: continue # while True
                    if value: msg["__generated"] = True

                elif "conversations.item.MessageList.item.messagetype" == prefix:
                    msg["__type"] = value # For post-processing

            if progress and lastcounts != counts and (counts["chats"] != lastcounts["chats"]
            or counts["messages"] and not counts["messages"] % 100) \
            and not progress(counts=counts):
                break # while True

            lastcounts = dict(counts)


    def export_finalize_chat(self, chat):
        """
        Populates last fields, inserts account participant if lacking.
        """
        if "meta_topic" in chat and "displayname" not in chat:
            chat["displayname"] = chat["meta_topic"]

        # Insert account participant if not inserted
        if not any(self.id == x["identity"] and chat["id"] == x["convo_id"]
                   for x in self.table_rows["participants"]):
            p = dict(is_permanent=1, convo_id=chat["id"], identity=self.id)
            p["id"] = self.insert_row("participants", p, log=False)
            self.table_rows["participants"].append(p)

        return chat


    def export_finalize_message(self, msg, chat, edited_msgs):
        """
        Populates last fields, inserts contacts and participants where lacking,
        updates contact/account displayname. Returns None to skip message insert.
        """
        if "edited_timestamp" in msg: msg["edited_by"] = msg["author"]

        if skypedata.CHATS_TYPE_SINGLE == chat["type"]:
            msg["dialog_partner"] = msg["author"]

        msg.update(chatmsg_type=skypedata.CHATMSG_TYPE_MESSAGE,
                   type=skypedata.MESSAGE_TYPE_MESSAGE)

        if 'Event/Call' == msg["__type"]:
            # <partlist type="ended" alt="" callId="1593784540478"><part identity="8:username"><name>Display Name</name><duration>84.82</duration></part><part identity="8:username2"><name>Display Name 2</name><duration>84.82</duration></part></partlist>

            msg.update(chatmsg_type=skypedata.CHATMSG_TYPE_SPECIAL2,
                       type=skypedata.MESSAGE_TYPE_CALL)
            if 'type="ended"' in msg.get("body_xml", ""):
                msg.update(type=skypedata.MESSAGE_TYPE_CALL_END)

        elif "RichText/Contacts" == msg["__type"]:
            msg.update(chatmsg_type=skypedata.CHATMSG_TYPE_SPECIAL,
                       type=skypedata.MESSAGE_TYPE_CONTACTS)

        elif "RichText/UriObject" == msg["__type"]:
            msg.update(chatmsg_type=skypedata.CHATMSG_TYPE_SPECIAL,
                       type=skypedata.MESSAGE_TYPE_SHARE_PHOTO)

        elif "RichText/Media_GenericFile" == msg["__type"]:
            # <URIObject uri="https://api.asm.skype.com/v1/objects/0-weu-d3-abcdef.." url_thumbnail="https://api.asm.skype.com/v1/objects/0-weu-d3-abcdef../views/original" type="File.1" doc_id="0-weu-d3-abcdef..">To view this file, go to: <a href="https://login.skype.com/login/sso?go=webclient.xmm&amp;docid=0-weu-d3-abcdef..">https://login.skype.com/login/sso?go=webclient.xmm&amp;docid=0-weu-d3-abcdef..</a><OriginalName v="f.txt"></OriginalName><FileSize v="447"></FileSize></URIObject>

            msg.update(chatmsg_type=skypedata.CHATMSG_TYPE_SPECIAL,
                       type=skypedata.MESSAGE_TYPE_FILE)
            try:
                bs = BeautifulSoup(msg["body_xml"], "html.parser")
                name = bs.find("originalname").get("v")
                size = bs.find("filesize").get("v")
                msg["body_xml"] = '<files><file index="0" size="%s">%s</file></files>' % (
                                  urllib.quote(util.to_unicode(size or 0)),
                                  util.to_unicode(name or "file").replace("<", "&lt;").replace(">", "&gt;"))
            except Exception:
                if BeautifulSoup: logger.warn("Error parsing file from %s.", msg, exc_info=True)

        elif "ThreadActivity/TopicUpdate" == msg["__type"]:
            # <topicupdate><eventtime>1594466832367</eventtime><initiator>8:username</initiator><value>The Topic</value></topicupdate>

            msg.update(chatmsg_type=skypedata.CHATMSG_TYPE_TOPIC,
                       type=skypedata.MESSAGE_TYPE_TOPIC)
            try:
                bs = BeautifulSoup(msg["body_xml"], "html.parser")
                initiator = id_to_identity(bs.find("initiator").text)
                if initiator: msg["author"] = initiator
                msg["body_xml"] = bs.find("value").text
            except Exception:
                if BeautifulSoup: logger.warn("Error parsing topic from %s.", msg, exc_info=True)

        elif "ThreadActivity/AddMember" == msg["__type"]:
            # <addmember><eventtime>1594467205492</eventtime><initiator>8:username</initiator><target>8:username2</target></addmember>

            msg.update(chatmsg_type=skypedata.CHATMSG_TYPE_CONTACTS,
                       type=skypedata.MESSAGE_TYPE_PARTICIPANTS)
            try:
                bs = BeautifulSoup(msg["body_xml"], "html.parser")
                initiator = id_to_identity(bs.find("initiator").text)
                if initiator: msg["author"] = initiator
                msg["identities"] = id_to_identity(bs.find("target").text)
            except Exception:
                if BeautifulSoup: logger.warn("Error parsing identities from %s.", msg, exc_info=True)

        elif "ThreadActivity/DeleteMember" == msg["__type"]:
            # <deletemember><eventtime>1594467133727</eventtime><initiator>8:username</initiator><target>8:username2</target></deletemember>

            try:
                bs = BeautifulSoup(msg["body_xml"], "html.parser")
                initiator = id_to_identity(bs.find("initiator").text)
                target = id_to_identity(bs.find("target").text)
                if initiator: msg["author"] = initiator
                if msg["author"] == target:
                    msg.update(chatmsg_type=skypedata.CHATMSG_TYPE_LEAVE,
                               type=skypedata.MESSAGE_TYPE_LEAVE)
                else:
                    msg.update(chatmsg_type=skypedata.CHATMSG_TYPE_REMOVE,
                               type=skypedata.MESSAGE_TYPE_REMOVE,
                               identities=target)
            except Exception:
                if BeautifulSoup: logger.warn("Error parsing identities from %s.", msg, exc_info=True)

        elif "RichText/Location" == msg["__type"]:
            msg.update(chatmsg_type=skypedata.CHATMSG_TYPE_SPECIAL,
                       type=skypedata.MESSAGE_TYPE_INFO)

        elif "ThreadActivity/PictureUpdate" == msg["__type"]:
            # <pictureupdate><eventtime>1594466869930</eventtime><initiator>8:username</initiator><value>URL@https://api.asm.skype.com/v1/objects/0-weu-d15-abcdef..</value></pictureupdate>

            msg.update(chatmsg_type=skypedata.CHATMSG_TYPE_PICTURE,
                       type=skypedata.MESSAGE_TYPE_TOPIC)
            try:
                bs = BeautifulSoup(msg["body_xml"], "html.parser")
                initiator = id_to_identity(bs.find("initiator").text)
                if initiator: msg["author"] = initiator
            except Exception:
                if BeautifulSoup: logger.warn("Error parsing author from %s.", msg, exc_info=True)

        elif "RichText/Media_Video"    == msg["__type"] \
        or   "RichText/Media_AudioMsg" == msg["__type"]:
            # <URIObject uri="https://api.asm.skype.com/v1/objects/0-weu-d8-abcdef.." url_thumbnail="https://api.asm.skype.com/v1/objects/0-weu-d8-abcdef../views/thumbnail" type="Video.1/Message.1" doc_id="0-weu-d8-abcdef.." width="640" height="480">To view this video message, go to: <a href="https://login.skype.com/login/sso?go=xmmfallback?vim=0-weu-d8-abcdef..">https://login.skype.com/login/sso?go=xmmfallback?vim=0-weu-d8-abcdef..</a><OriginalName v="937029c3-6a12-4202-bdaf-aac9e341c63d.mp4"></OriginalName><FileSize v="103470"></FileSize></URIObject>

            msg.update(type=skypedata.MESSAGE_TYPE_SHARE_VIDEO2)

        elif msg["__type"] not in ("Text", "RichText", "InviteFreeRelationshipChanged/Initialized", "RichText/Media_Card"):
            # One of 'Notice', 'PopCard', 'RichText/Media_Album',
            # 'ThreadActivity/HistoryDisclosedUpdate', 'ThreadActivity/JoiningEnabledUpdate', ..
            return None

        if "author" not in msg or "timestamp" not in msg \
        or msg.get("__generated") and not msg.get("body_xml") \
        and "edited_timestamp" not in msg:
            return None # Can be blank messages, especially from serverside

        process_message_edit(msg)

        if (msg["author"], msg["timestamp__ms"]) in edited_msgs:
            # Take pk_id and guid from earlier message
            msg0 = edited_msgs[(msg["author"], msg["timestamp__ms"])]
            msg0.update(pk_id=msg["pk_id"], guid=msg["guid"])
            self.update_row("messages", msg0, msg0, log=False)
            return None # Edited message, final version already parsed

        if "edited_timestamp" in msg:
            edited_msgs[(msg["author"], msg["timestamp__ms"])] = msg

        # Insert contact if not inserted
        if msg["author"] != self.id \
        and msg["author"] not in self.table_objects["contacts"]:
            contact = dict(skypename=msg["author"], is_permanent=1)
            contact["id"] = self.insert_row("contacts", contact)
            self.table_objects["contacts"][msg["author"]] = contact

        # Insert participant if not inserted
        if not any(msg["author"] == x["identity"] and msg["convo_id"] == x["convo_id"]
                   for x in self.table_rows["participants"]):
            p = dict(is_permanent=1, convo_id=msg["convo_id"], identity=msg["author"])
            p["id"] = self.insert_row("participants", p, log=False)
            self.table_rows["participants"].append(p)

        # Take contact/account displayname from message if not populated
        ptable, pitem = None, {}
        if msg["author"] == self.id:
            ptable, pitem = "accounts", self.account
        if msg["author"] in self.table_objects["contacts"]:
            ptable, pitem = "contacts", self.table_objects["contacts"][msg["author"]]
        if msg.get("from_dispname") and "displayname" not in pitem:
            pitem["displayname"] = msg["from_dispname"]
            self.update_row(ptable, pitem, pitem, log=False)

        return msg


    @staticmethod
    def export_parse_timestamp(value):
        """
        Returns UNIX timestamp from datetime string like "2020-07-06T17:20:30.609Z".
        """
        v, suf = value.replace("T", " ").rstrip("Z"), ""
        if "." in v: v, suf = v.split(".")
        dt = datetime.datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
        if suf:
            try:
                suf = re.sub(r"[\D]", "", suf).ljust(6, "0")
                dt = dt.replace(microsecond=int(suf))
            except Exception: pass
        return util.datetime_to_epoch(dt)


    @staticmethod
    def export_open(filename):
        """Returns (opened JSON file pointer, opened TAR file pointer if any)."""
        f, tf = None, None
        try:
            try:
                tf = tarfile.open(filename)
                f = tf.extractfile("messages.json")
            except Exception: f = open(filename, "rb")
        except Exception: raise
        else: return f, tf


    @staticmethod
    def export_get_account(filename):
        """Returns the Skype account name from export file."""
        result, f, tf = None, None, None
        try:
            f, tf = SkypeExport.export_open(filename)
        except Exception: raise
        else:
            parser = ijson.parse(f)
            while True:
                prefix, evt, value = next(parser, (None, None, None))
                if not prefix and not evt: break # while True
                if "userId" == prefix:
                    result = id_to_identity(value)
                    break # while True
        finally:
            util.try_ignore(f and f.close)
            util.try_ignore(tf and tf.close)
        return result



def date_to_integer(date):
    """Returns datetime.date as integer YYYYMMDD, or None if date is None."""
    result = None
    if isinstance(date, datetime.date):
        result = 10000 * date.year + 100 * date.month + date.day
    return result


def id_to_identity(chatid):
    """
    Returns conversation or contact identity in Skype database;
    "username" from "8:username" for single chats,
    or "#username1/$username2;123456abcdef"
    from "19:I3VzZXJuYW1lMS8kdXNlcm5hbWUyOzEyMzQ1NmFiY2RlZg==@p2p.thread.skype"
    for older peer-to-peer group chats,
    or "19:xyz@thread.skype" for newer group chats.
    """
    result = chatid
    if result and not result.endswith("@thread.skype"):
        result = re.sub(r"^\d+\:", "", result) # Strip numeric prefix
        if result.endswith("@p2p.thread.skype"):
            result = result[:-len("@p2p.thread.skype")]
            try: result = base64.b64decode(result)
            except Exception: pass
    return result


def identity_to_id(identity):
    """
    Returns conversation or contact ID in Skype live;
    "8:username" from "username" for single chats,
    or "19:I3VzZXJuYW1lMS8kdXNlcm5hbWUyOzEyMzQ1NmFiY2RlZg==@p2p.thread.skype"
    from "#username1/$username2;123456abcdef"
    for older peer-to-peer group chats,
    or "19:xyz@thread.skype" as-is for newer group chats.
    """
    result = identity
    if result and not result.endswith("@thread.skype"):
        if result.startswith("#"):
            result = "19:%s@p2p.thread.skype" % base64.b64encode(result)
        elif not result.endswith("thread.skype"):
            result = "8:%s" % result
    return result


def make_db_path(username):
    """Returns the default database path for username."""
    base = util.safe_filename(username)
    if base != username: base += "_%x" % hash(username)
    return os.path.join(conf.VarDirectory, "%s.main.db" % base)


def make_message_ids(msg_id):
    """Returns (pk_id, guid) for message ID."""
    try: pk_id = int(msg_id) if int(msg_id).bit_length() < 64 else hash(msg_id)
    except Exception: pk_id = hash(msg_id) # Ensure fit into INTEGER-column
    guid = struct.pack("<i" if pk_id.bit_length() < 32 else "<q", pk_id)
    guid *= 32 / len(guid)
    return (pk_id, guid)


def process_message_edit(msg):
    """Strips edited-tag from body and updates fields if edit in content."""
    if not msg or "<e_m" not in (msg.get("body_xml") or ""): return

    # <e_m ts="1526383416" ts_ms="1526383417250" a="skypename" t="61"/>
    try:
        # Edited messages can be in form "new content<e_m ..>",
        # where ts_ms is the timestamp of the original message.
        # Message may also start with "Edited previous message: <e_m ..".
        STRIP_PREFIX = "Edited previous message: "
        if msg["body_xml"].startswith(STRIP_PREFIX):
            msg["body_xml"] = msg["body_xml"][len(STRIP_PREFIX):]
        bs = BeautifulSoup(msg["body_xml"], "html.parser")
        tag = bs.find("e_m")
        ts_ms = int(tag.get("ts_ms"))
        msg["edited_timestamp"] = msg["timestamp"]
        msg["edited_by"] = msg["author"]
        msg["timestamp"] = ts_ms / 1000
        msg["timestamp__ms"] = ts_ms
        tag.unwrap() # Remove tag from soup
        if not bs.encode().strip():
            msg["body_xml"] = "" # Only had <e_m>-tag: deleted message
    except Exception:
        if BeautifulSoup: logger.warn("Error parsing edited timestamp from %s.", msg, exc_info=True)


def make_media_url(url, category=None):
    """
    Returns URL with appropriate path appended if Skype shared media URL,
    e.g. "https://api.asm.skype.com/v1/objects/0-weu-d11-../views/imgpsh_fullsize"
    for  "https://api.asm.skype.com/v1/objects/0-weu-d11-..".

    @param   category  type of media, e.g. "avatar" for avatar image
    """
    if not url or "api.asm.skype.com/" not in url: return url

    if   "avatar"  == category and not url.endswith("/views/avatar_fullsize"):
        url += "/views/avatar_fullsize"
    elif "audio"   == category and not url.endswith("/views/audio"):
        url += "/views/audio"
    elif "video"   == category and not url.endswith("/views/video"):
        url += "/views/video"
    elif "sticker" == category and not url.endswith("/views/thumbnail"):
        url += "/views/thumbnail"
    elif "/views/" not in url:
        url += "/views/imgpsh_fullsize"

    return url
