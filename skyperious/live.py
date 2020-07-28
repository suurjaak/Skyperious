# -*- coding: utf-8 -*-
"""
Functionality for communicating with Skype online service.

------------------------------------------------------------------------------
This file is part of Skyperious - a Skype database viewer and merger.
Released under the MIT License.

@author      Erki Suurjaak
@created     08.07.2020
@modified    28.07.2020
------------------------------------------------------------------------------
"""
import base64
import collections
import datetime
import logging
import os
import re
import struct
import time
import urllib
import warnings

BeautifulSoup = skpy = None
try: from bs4 import BeautifulSoup
except ImportError: pass
try: import skpy
except ImportError: pass

from . lib import util

from . import conf
from . import guibase
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
        Logs in to Skype or raises error on failure.

        @param   db        existing SkypeDatabase instance if not creating new
        @param   progress  callback function invoked with (action, ?error, ?table, ?count, ?total, ?new, ?updated),
                           returning false if work should stop
        """
        self.db           = db   # SQLite database populated with live data
        self.progress     = progress
        self.username     = db.id if db else None
        self.skype        = None # skpy.Skype instance
        self.tokenpath    = None # Path to login tokenfile
        self.cache        = collections.defaultdict(dict) # {table: {identity: {item}}}
        self.populated    = False
        self.query_stamps = [] # [datetime.datetime, ] for rate limiting
        self.msg_stamps   = {} # {remote_id: last timestamp}


    def is_logged_in(self):
        """Returns whether there is active login."""
        return bool(self.skype and self.skype.conn.connected)


    def login(self, username=None, password=None, token=True):
        """
        Logs in to Skype with given username, can try to use existing tokenfile
        if available (tokenfiles expire in 24h).

        @param   token   whether to use existing tokenfile instead of password
        """
        if username and (not self.db or not self.db.id): self.username = username
        path = util.safe_filename(self.username)
        if path != self.username: path += "_%x" % hash(self.username)
        path = self.tokenpath = os.path.join(conf.VarDirectory, "%s.token" % path)

        logger.info("Logging in to Skype online service as '%s'.", self.username)
        kwargslist = []
        if password: kwargslist += [{"user": self.username, "pwd": password, "tokenFile": path}]
        if token and os.path.isfile(path) and os.path.getsize(path):
            kwargslist.insert(0, {"tokenFile": path}) # Try with existing token
        else:
            try: os.makedirs(conf.VarDirectory)
            except Exception: pass
            with open(path, "w"): pass
        for kwargs in kwargslist:
            try: self.skype = skpy.Skype(**kwargs)
            except Exception:
                if kwargs is not kwargslist[-1]: continue # for kwargs
                logger.exception("Error logging in to Skype as '%s'.", self.username)
                try: os.unlink(path)
                except Exception: pass
                raise
            else: break # for kwargs
        self.init_db()


    def init_db(self):
        """Creates SQLite database if not already created."""
        if not self.db:
            path = self.make_db_path(self.username)
            if not os.path.isfile(path):
                with open(path, "w") as f: pass
            self.db = skypedata.SkypeDatabase(path, log_error=False)
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
                    logger.exception("Error calling %s.", func)
                    if doraise: raise
                    else: return
                time.sleep(self.RETRY_DELAY)
            finally: # Replace with final
                self.query_stamps[-1] = datetime.datetime.utcnow()


    def save(self, table, item, parent=None):
        """
        Saves the item to SQLite table. Returns true if item with the same 
        content already existed.

        @return   one of SkypeLogin.SAVE
        """
        dbitem, table = self.convert(table, item, parent=parent), table.lower()
        if dbitem is None: return self.SAVE.SKIP
        result, dbitem1 = None, dict(dbitem)

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
                        contact = self.request(self.skype.contacts.contact, x)
                        if contact: self.save("contacts", contact)
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
                if dbitem["timestamp"] < self.msg_stamps[dbitem["remote_id"]]:
                    dbitem.pop("body_xml") # We have a later more valid content
                self.msg_stamps[dbitem["remote_id"]] = max(dbitem["timestamp"], self.msg_stamps[dbitem["remote_id"]])
                if dbitem["timestamp"] > dbitem0["timestamp"]:
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
            self.msg_stamps[dbitem1["remote_id"]] = dbitem1["timestamp"]

        if identity is not None:
            cacheitem = dict(dbitem)
            if "messages" == table: # Retain certain fields only, sparing memory
                cacheitem = dict((k, dbitem[k]) for k in 
                    ("id", "guid", "pk_id", "remote_id", "convo_id", "timestamp")
                if k in dbitem)
            self.cache[table][identity] = cacheitem
            if "accounts" == table:
                self.cache["contacts"][identity] = cacheitem # For name lookup

        if "chats" == table:
            self.insert_participants(item, dbitem, dbitem0)
            self.insert_chats(item, dbitem, dbitem0)
        if "chats" == table and isinstance(item, skpy.SkypeGroupChat):
            # See if older-style chat entry is present
            identity0 = self.id_to_identity(item.id)
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


    def insert_participants(self, chat, row, row0):
        """Inserts Participants-rows for SkypeChat, if not already present."""
        participants, newcontacts = [], []
        usernames = chat.userIds if isinstance(chat, skpy.SkypeGroupChat) \
                    else set([self.username, chat.userId])
        for username in usernames:
            p = dict(is_permanent=1, convo_id=row["id"], identity=username)
            if isinstance(chat, skpy.SkypeGroupChat) and username == chat.creatorId:
                p.update(rank=1)
            participants.append(p)
        existing = set()
        if row0:
            cursor = self.db.execute("SELECT identity FROM participants WHERE convo_id = :id", row0, log=False)
            existing.update(x["identity"] for x in cursor)
        for p in participants:
            if p["identity"] not in existing:
                self.db.insert_row("participants", p, log=False)
            if p["identity"] not in self.cache["contacts"]:
                contact = self.request(self.skype.contacts.contact, p["identity"], __raise=False)
                if contact: newcontacts.append(contact)
        for c in newcontacts: self.save("contacts", c)


    def insert_chats(self, chat, row, row0):
        """Inserts Chats-row for SkypeChat, if not already present."""
        if self.db.execute("SELECT 1 FROM chats WHERE conv_dbid = :id", row).fetchone():
            return

        cursor = self.db.execute("SELECT identity FROM participants WHERE convo_id = :id", row, log=False)
        memberstr = " ".join(sorted(x["identity"] for x in cursor))
        c = dict(is_permanent=1, name=row["identity"], conv_dbid=row["id"],
                 posters=memberstr, participants=memberstr, activemembers=memberstr,
                 friendlyname=row["displayname"])
        self.db.insert_row("chats", c, log=False)


    def insert_calls(self, msg, row, row0):
        """Inserts Calls-row for SkypeCallMsg."""
        if row0 or skpy.SkypeCallMsg.State.Started == msg.state: return

        duration = 0
        bs = BeautifulSoup(msg.content, "html.parser") if BeautifulSoup else None
        for tag in bs.find_all("duration") if bs else ():
            try: duration = max(duration, int(float(tag.text)))
            except Exception: pass

        ts = row["timestamp"] - duration
        c = dict(conv_dbid=row["convo_id"], begin_timestamp=ts, name="1-%s" % ts, duration=duration)
        self.db.insert_row("calls", c, log=False)


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
                result.update(birthday=self.date_to_integer(item.birthday))
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

            if item.avatar and "?" in item.avatar:
                # https://avatar.skype.com/v1/avatars/username/public?auth_key=1455825688
                raw = self.download_image(item.avatar)
                # main.db has NULL-byte in front of image binary
                if raw: result.update(avatar_image="\0" + raw)

        if "accounts" == table:
            if item.mood:
                result.update(mood_text=unicode(item.mood))

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
                    raw = self.get_api_image(item.picture, category="avatar")
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
            result.update(is_permanent=1, timestamp=int(ts), author=item.userId,
                          from_dispname=self.get_contact_name(item.userId),
                          body_xml=item.content, timestamp__ms=ts*1000)

            # Ensure that pk_id fits into INTEGER-column
            try: pk_id = int(item.id) if int(item.id).bit_length() < 64 else hash(item.id)
            except Exception: pk_id = hash(item.id)
            guid = struct.pack("<i" if pk_id.bit_length() < 32 else "<q", pk_id)
            guid *= 32 / len(guid)
            result.update(pk_id=pk_id, guid=guid)

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

            elif isinstance(item, skpy.SkypeCallMsg):
                # SkypeCallMsg(id='1593784617947', type='Event/Call', time=datetime.datetime(2020, 7, 3, 13, 56, 57, 949000), clientId='3666747505059875266', userId='username', chatId='8:username', content='<partlist type="ended" alt="" callId="1593784540478"><part identity="username"><name>Display Name</name><duration>84.82</duration></part><part identity="8:username2"><name>Display Name 2</name><duration>84.82</duration></part></partlist>', state=SkypeCallMsg.State.Ended, userIds=['username', '8:username2'], userNames=['Display Name', 'Display Name 2'])

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
                                       tuple(map(urllib.quote, [item.file.size, item.file.name])))

            elif isinstance(item, skpy.msg.SkypeTopicPropertyMsg):
                # SkypeTopicPropertyMsg(id='1594466832242', type='ThreadActivity/TopicUpdate', time=datetime.datetime(2020, 7, 11, 11, 27, 12, 242000), userId='live:.cid.c63ad15063a6dfca', chatId='19:e1a913fec4eb4be9b989379768d24229@thread.skype', content='<topicupdate><eventtime>1594466832367</eventtime><initiator>8:live:.cid.c63ad15063a6dfca</initiator><value>Groupie: topic</value></topicupdate>', topic='Groupie: topic')

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
                tag = BeautifulSoup and BeautifulSoup(item.content, "html.parser").find("initiator")
                if tag and tag.text:
                    author = self.id_to_identity(tag.text)
                    result.update(author=author)
                    result.update(from_dispname=self.get_contact_name(author))

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
        Retrieves all available contacts, chats and messages, or selected chats only.
        
        @param   chats  list of chat identities to populate if not everything
        """
        if self.populated:
            self.skype = None
            self.login() # Re-login to reset query cache
        self.build_cache()
        if not chats: self.save("accounts", self.skype.user)
        cstr = "%s " % util.plural("chat", chats, with_items=False) if chats else ""
        logger.info("Starting to sync %s'%s' from Skype online service as '%s'.",
                    cstr, self.db, self.username)
        if not chats: self.populate_contacts()
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

        identities = map(self.identity_to_id, chats or ())
        getter = lambda c: self.request(self.skype.chats.chat, c, __raise=False)
        selchats = {k: v for (k, v) in ((x, getter(x)) for x in identities) if v}

        updateds, new, mtotalnew, mtotalupdated, run = set(), 0, 0, 0, True
        msgids = set()
        while run:
            mychats = selchats if chats else self.request(self.skype.chats.recent, __raise=False)
            if not mychats: break # while run
            for chat in mychats.values():
                if chat.id.startswith("48:"): # Skip specials like "48:calllogs"
                    continue # for chat
                if isinstance(chat, skpy.SkypeGroupChat) and not chat.userIds:
                    # Weird empty conversation, getMsgs raises 404
                    continue # for chat
                if isinstance(chat, skpy.SkypeSingleChat) and chat.userId == self.username:
                    # Conversation with self?
                    continue # for chat
                cidentity = chat.id if isinstance(chat, skpy.SkypeGroupChat) else chat.userId

                if cidentity in updateds: continue # for chat
                action = self.save("chats", chat)
                if self.SAVE.INSERT == action: new += 1
                if action in (self.SAVE.INSERT, self.SAVE.UPDATE):
                    updateds.add(cidentity)
                if self.progress and not self.progress(
                    action="populate", table="messages", chat=cidentity, start=True
                ):
                    run = False
                    break # for chat

                mcount, mnew, mupdated, mrun = 0, 0, 0, True
                mfirst, mlast = datetime.datetime.max, datetime.datetime.min
                while mrun:
                    msgs = self.request(chat.getMsgs, __raise=False) or []
                    for msg in msgs:
                        action = self.save("messages", msg, parent=chat)
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
                if (mtotalnew or mtotalupdated): updateds.add(cidentity)
                if self.progress and not self.progress(action="populate", table="messages",
                    chat=cidentity, end=True, count=mcount,
                    new=mnew, updated=mupdated, first=mfirst, last=mlast
                ):
                    run = False
                    break # for chat
                if not mrun: break # for chat
            if chats: break # while run

        ids = [self.cache["chats"][x]["id"] for x in updateds if x in self.cache["chats"]]
        for myids in [ids[i:i+999] for i in range(0, len(ids), 999)]:
            # Divide into chunks: SQLite can take up to 999 parameters.
            idstr = ", ".join(":id%s" % (j+1) for j in range(len(myids)))
            where = " WHERE convo_id IN (%s)" % idstr
            args = dict(("id%s" % (j+1), x) for j, x in enumerate(myids))

            lasts = self.db.execute("SELECT id, convo_id, MAX(timestamp) AS ts "
                                    "FROM messages%s GROUP BY convo_id" % where, args)
            for row in lasts:
                self.db.execute("UPDATE conversations SET last_message_id = :id, "
                                "last_activity_timestamp = :ts WHERE id = :convo_id", row)

        if self.progress: self.progress(
            action="populate", table="chats", end=True, count=len(updateds), new=new,
            message_count_new=mtotalnew, message_count_updated=mtotalupdated
        )


    def populate_contacts(self):
        """Retrieves the list of contacts."""
        if self.progress and not self.progress(action="populate", table="contacts", start=True):
            return
        if not self.cache: self.build_cache()

        self.request(self.skype.contacts.sync)
        contacts = set(self.skype.contacts.contactIds)
        total = len(contacts)
        if self.progress and not self.progress(
            action="populate", table="contacts", total=total
        ):
            return
        count, new, updated, run = 0, 0, 0, True
        for username in contacts:
            contact = self.request(self.skype.contacts.contact, username, __raise=False)
            if not contact: continue # for username
            action = self.save("contacts", contact)
            if self.SAVE.INSERT == action: new     += 1
            if self.SAVE.UPDATE == action: updated += 1
            count += 1
            if self.progress and not self.progress(
                action="populate", table="contacts", count=count, total=total, new=new, updated=updated
            ): break # for username
        if self.progress: self.progress(
            action="populate", table="contacts", end=True, count=count, total=total, new=new, updated=updated
        )


    def get_api_image(self, url, category=None):
        """
        Returns image raw binary from Skype API URL via login, or None.

        @param   category  type of image, e.g. "avatar"
        """
        if "avatar" == category and not url.endswith("/views/avatar_fullsize"):
            url += "/views/avatar_fullsize"
        elif "/views/" not in url:
            url += "/views/imgpsh_fullsize"

        urls = [url]
        # Some images appear to be available on one domain, some on another
        if not url.startswith("https://experimental-api.asm"):
            url0 = re.sub("https\:\/\/.+\.asm", "https://experimental-api.asm", url)
            urls.insert(0, url0)
        for url in urls:
            raw = self.download_image(url)
            if raw: return raw


    def download_image(self, url):
        """Downloads and returns image raw binary from Skype URL via login, or None."""
        try:
            r = self.request(self.skype.conn, "GET", url,
                             auth=skpy.SkypeConnection.Auth.Authorize,
                             __retry=False)
            if r.ok and r.content and "image" in r.headers.get("content-type", ""):
                return r.content
        except Exception: pass


    @staticmethod
    def date_to_integer(date):
        """Returns datetime.date as integer YYYYMMDD, or None if date is None."""
        result = None
        if isinstance(date, datetime.date):
            result = 10000 * date.year + 100 * date.month + date.day
        return result


    def get_contact_name(self, identity):
        """Returns contact displayname or fullname or identity."""
        result = None
        contact = self.cache["contacts"].get(identity)
        if contact:
            result = contact.get("displayname") or contact.get("fullname")
        result = result or identity
        return result


    @staticmethod
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
        if not result.endswith("@thread.skype"):
            result = re.sub(r"^\d+\:", "", result) # Strip numeric prefix
            if result.endswith("@p2p.thread.skype"):
                result = result[:-len("@p2p.thread.skype")]
                try: result = base64.b64decode(result)
                except Exception: pass
        return result


    @staticmethod
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
        if not result.endswith("@thread.skype"):
            if result.startswith("#"):
                result = "19:%s@p2p.thread.skype" % base64.b64encode(result)
            elif not result.endswith("thread.skype"):
                result = "8:%s" % result
        return result


    @staticmethod
    def make_db_path(username):
        """Returns the default database path for username."""
        base = util.safe_filename(username)
        if base != username: base += "_%x" % hash(username)
        return os.path.join(conf.VarDirectory, "%s.main.db" % base)
