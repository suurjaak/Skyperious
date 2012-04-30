# -*- coding: utf-8 -*-
"""
Skype database access functionality.

@author      Erki Suurjaak
@created     26.11.2011
@modified    30.04.2012
"""
import copy
import datetime
import os
import Queue
import re
import sqlite3
import shutil
import sys
import threading
import textwrap
import time
import traceback
import urllib
import wx
import wx.lib.wordwrap
import wx.grid
import xml.etree.cElementTree
import xml.parsers.expat

import conf
import gui
import main


CHATS_TYPE_SINGLE          =   1 # 1:1 chat
CHATS_TYPE_GROUP           =   2 # 1:n chat
CHATS_TYPE_CONFERENCE      =   4 # video conference
CHATS_TYPENAMES = {
    CHATS_TYPE_SINGLE    : "Single",
    CHATS_TYPE_GROUP     : "Group",
    CHATS_TYPE_CONFERENCE: "Conference"
}
MESSAGES_TYPE_TOPIC        =   2 # Changed chat topic or picture
MESSAGES_TYPE_GROUP        =   4 # Created group conversation
MESSAGES_TYPE_PARTICIPANTS =  10 # Added participants to chat
MESSAGES_TYPE_REMOVE       =  12 # Removed participants from chat
MESSAGES_TYPE_LEAVE        =  13 # Contact left the chat
MESSAGES_TYPE_CALL         =  30 # Started Skype call
MESSAGES_TYPE_CALL_END     =  39 # Skype call ended
MESSAGES_TYPE_SHARE_DETAIL =  51 # Sharing contact details
MESSAGES_TYPE_MESSAGE      =  61 # Ordinary message
MESSAGES_TYPE_CONTACTS     =  63 # Sent contacts
MESSAGES_TYPE_SMS          =  64 # SMS message
MESSAGES_TYPE_FILE         =  68 # File transfer
MESSAGES_TYPE_BIRTHDAY     = 110 # Birthday notification
TRANSFER_TYPE_OUTBOUND     =   1 # An outbound transfer, sent by this account
TRANSFER_TYPE_INBOUND      =   2 # An inbound transfer, sent to this account


class SkypeDatabase(object):
    """Access to a Skype database file."""

    """Insert SQL statements for Skype tables."""
    INSERT_STATEMENTS = {
      "accounts": "CREATE TABLE Accounts (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, skypename TEXT, fullname TEXT, pstnnumber TEXT, birthday INTEGER, gender INTEGER, languages TEXT, country TEXT, province TEXT, city TEXT, phone_home TEXT, phone_office TEXT, phone_mobile TEXT, emails TEXT, homepage TEXT, about TEXT, profile_timestamp INTEGER, received_authrequest TEXT, displayname TEXT, refreshing INTEGER, given_authlevel INTEGER, aliases TEXT, authreq_timestamp INTEGER, mood_text TEXT, timezone INTEGER, nrof_authed_buddies INTEGER, ipcountry TEXT, given_displayname TEXT, availability INTEGER, lastonline_timestamp INTEGER, capabilities BLOB, avatar_image BLOB, assigned_speeddial TEXT, lastused_timestamp INTEGER, authrequest_count INTEGER, status INTEGER, pwdchangestatus INTEGER, suggested_skypename TEXT, logoutreason INTEGER, skypeout_balance_currency TEXT, skypeout_balance INTEGER, skypeout_precision INTEGER, skypein_numbers TEXT, offline_callforward TEXT, commitstatus INTEGER, cblsyncstatus INTEGER, chat_policy INTEGER, skype_call_policy INTEGER, pstn_call_policy INTEGER, avatar_policy INTEGER, buddycount_policy INTEGER, timezone_policy INTEGER, webpresence_policy INTEGER, owner_under_legal_age INTEGER, phonenumbers_policy INTEGER, voicemail_policy INTEGER, assigned_comment TEXT, alertstring TEXT, avatar_timestamp INTEGER, mood_timestamp INTEGER, type INTEGER, rich_mood_text TEXT, partner_optedout TEXT, service_provider_info TEXT, registration_timestamp INTEGER, nr_of_other_instances INTEGER, synced_email BLOB, set_availability INTEGER, authorized_time INTEGER, sent_authrequest TEXT, sent_authrequest_time INTEGER, sent_authrequest_serial INTEGER, buddyblob BLOB, cbl_future BLOB, node_capabilities INTEGER, node_capabilities_and INTEGER, revoked_auth INTEGER, added_in_shared_group INTEGER, in_shared_group INTEGER, authreq_history BLOB, profile_attachments BLOB, stack_version INTEGER, offline_authreq_id INTEGER, subscriptions TEXT, authrequest_policy INTEGER, ad_policy INTEGER, options_change_future BLOB, verified_email BLOB, verified_company BLOB, partner_channel_status TEXT, cbl_profile_blob BLOB, flamingo_xmpp_status INTEGER)",
      "alerts": "CREATE TABLE Alerts (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, timestamp INTEGER, partner_name TEXT, is_unseen INTEGER, partner_id INTEGER, partner_event TEXT, partner_history TEXT, partner_header TEXT, partner_logo TEXT, message_content TEXT, message_footer TEXT, meta_expiry INTEGER, message_header_caption TEXT, message_header_title TEXT, message_header_subject TEXT, message_header_cancel TEXT, message_header_later TEXT, message_button_caption TEXT, message_button_uri TEXT, message_type INTEGER, window_size INTEGER, notification_id INTEGER, extprop_hide_from_history INTEGER, chatmsg_guid BLOB, event_flags INTEGER)",
      "callmembers": "CREATE TABLE CallMembers (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, quality_status INTEGER, call_name TEXT, price_precision INTEGER, transfer_status INTEGER, transfer_active INTEGER, transferred_by TEXT, transferred_to TEXT, guid TEXT, identity TEXT, dispname TEXT, languages TEXT, call_duration INTEGER, price_per_minute INTEGER, price_currency TEXT, type INTEGER, status INTEGER, failurereason INTEGER, sounderror_code INTEGER, soundlevel INTEGER, pstn_statustext TEXT, pstn_feedback TEXT, forward_targets TEXT, forwarded_by TEXT, debuginfo TEXT, videostatus INTEGER, target_identity TEXT, mike_status INTEGER, is_read_only INTEGER, next_redial_time INTEGER, nrof_redials_left INTEGER, nrof_redials_done INTEGER, transfer_topic TEXT, real_identity TEXT, start_timestamp INTEGER, pk_status INTEGER, call_db_id INTEGER, prime_status INTEGER, is_conference INTEGER, quality_problems TEXT, identity_type INTEGER, country TEXT, creation_timestamp INTEGER, payment_category TEXT, stats_xml TEXT, is_premium_video_sponsor INTEGER, is_multiparty_video_capable INTEGER, recovery_in_progress INTEGER, nonse_word TEXT)",
      "calls": "CREATE TABLE Calls (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, begin_timestamp INTEGER, partner_handle TEXT, partner_dispname TEXT, server_identity TEXT, type INTEGER, old_members BLOB, status INTEGER, failurereason INTEGER, topic TEXT, pstn_number TEXT, old_duration INTEGER, conf_participants BLOB, pstn_status TEXT, failurecode INTEGER, is_muted INTEGER, vaa_input_status INTEGER, is_incoming INTEGER, is_conference INTEGER, host_identity TEXT, mike_status INTEGER, duration INTEGER, soundlevel INTEGER, access_token TEXT, active_members INTEGER, is_active INTEGER, name TEXT, video_disabled INTEGER, joined_existing INTEGER, is_unseen_missed INTEGER, is_on_hold INTEGER, members BLOB, conv_dbid INTEGER, start_timestamp INTEGER, quality_problems TEXT, current_video_audience TEXT, premium_video_status INTEGER, premium_video_is_grace_period INTEGER, is_premium_video_sponsor INTEGER, premium_video_sponsor_list TEXT)",
      "chatmembers": "CREATE TABLE ChatMembers (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, chatname TEXT, identity TEXT, role INTEGER, is_active INTEGER, cur_activities INTEGER, adder TEXT)",
      "chats": "CREATE TABLE Chats (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, name TEXT, timestamp INTEGER, adder TEXT, type INTEGER, posters TEXT, participants TEXT, topic TEXT, activemembers TEXT, friendlyname TEXT, alertstring TEXT, is_bookmarked INTEGER, activity_timestamp INTEGER, mystatus INTEGER, passwordhint TEXT, description TEXT, options INTEGER, picture BLOB, guidelines TEXT, dialog_partner TEXT, myrole INTEGER, applicants TEXT, banned_users TEXT, topic_xml TEXT, name_text TEXT, unconsumed_suppressed_msg INTEGER, unconsumed_normal_msg INTEGER, unconsumed_elevated_msg INTEGER, unconsumed_msg_voice INTEGER, state_data BLOB, lifesigns INTEGER, last_change INTEGER, first_unread_message INTEGER, pk_type INTEGER, dbpath TEXT, split_friendlyname TEXT, conv_dbid INTEGER)",
      "contactgroups": "CREATE TABLE ContactGroups (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, type_old INTEGER, given_displayname TEXT, nrofcontacts INTEGER, nrofcontacts_online INTEGER, custom_group_id INTEGER, type INTEGER, associated_chat TEXT, proposer TEXT, description TEXT, members TEXT, cbl_id INTEGER, cbl_blob BLOB, fixed INTEGER, keep_sharedgroup_contacts INTEGER, chats TEXT, extprop_is_hidden INTEGER, extprop_sortorder_value INTEGER, extprop_is_expanded INTEGER, given_sortorder INTEGER)",
      "contacts": "CREATE TABLE Contacts (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, skypename TEXT, fullname TEXT, pstnnumber TEXT, birthday INTEGER, gender INTEGER, languages TEXT, country TEXT, province TEXT, city TEXT, phone_home TEXT, phone_office TEXT, phone_mobile TEXT, emails TEXT, homepage TEXT, about TEXT, profile_timestamp INTEGER, received_authrequest TEXT, displayname TEXT, refreshing INTEGER, given_authlevel INTEGER, aliases TEXT, authreq_timestamp INTEGER, mood_text TEXT, timezone INTEGER, nrof_authed_buddies INTEGER, ipcountry TEXT, buddystatus INTEGER, isauthorized INTEGER, isblocked INTEGER, given_displayname TEXT, availability INTEGER, lastonline_timestamp INTEGER, capabilities BLOB, avatar_image BLOB, assigned_speeddial TEXT, lastused_timestamp INTEGER, authrequest_count INTEGER, assigned_comment TEXT, alertstring TEXT, avatar_timestamp INTEGER, mood_timestamp INTEGER, type INTEGER, rich_mood_text TEXT, authorization_certificate BLOB, certificate_send_count INTEGER, account_modification_serial_nr INTEGER, saved_directory_blob BLOB, nr_of_buddies INTEGER, server_synced INTEGER, contactlist_track INTEGER, last_used_networktime INTEGER, assigned_phone1 TEXT, assigned_phone1_label TEXT, assigned_phone2 TEXT, assigned_phone2_label TEXT, assigned_phone3 TEXT, assigned_phone3_label TEXT, authorized_time INTEGER, sent_authrequest TEXT, sent_authrequest_time INTEGER, sent_authrequest_serial INTEGER, buddyblob BLOB, cbl_future BLOB, node_capabilities INTEGER, node_capabilities_and INTEGER, revoked_auth INTEGER, added_in_shared_group INTEGER, in_shared_group INTEGER, authreq_history BLOB, profile_attachments BLOB, stack_version INTEGER, offline_authreq_id INTEGER, authreq_crc INTEGER, authreq_src INTEGER, pop_score INTEGER, authreq_nodeinfo BLOB, main_phone TEXT, unified_servants TEXT, phone_home_normalized TEXT, phone_office_normalized TEXT, phone_mobile_normalized TEXT, sent_authrequest_initmethod INTEGER, authreq_initmethod INTEGER, extprop_seen_birthday INTEGER, extprop_sms_target INTEGER, extprop_can_show_avatar INTEGER, popularity_ord INTEGER, verified_email BLOB, verified_company BLOB, sent_authrequest_extrasbitmask INTEGER, extprop_external_data TEXT)",
      "conversations": "CREATE TABLE Conversations (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, identity TEXT, type INTEGER, live_host TEXT, live_start_timestamp INTEGER, live_is_muted INTEGER, alert_string TEXT, is_bookmarked INTEGER, given_displayname TEXT, displayname TEXT, local_livestatus INTEGER, inbox_timestamp INTEGER, inbox_message_id INTEGER, unconsumed_suppressed_messages INTEGER, unconsumed_normal_messages INTEGER, unconsumed_elevated_messages INTEGER, unconsumed_messages_voice INTEGER, active_vm_id INTEGER, context_horizon INTEGER, consumption_horizon INTEGER, last_activity_timestamp INTEGER, active_invoice_message INTEGER, spawned_from_convo_id INTEGER, pinned_order INTEGER, creator TEXT, creation_timestamp INTEGER, my_status INTEGER, opt_joining_enabled INTEGER, opt_access_token TEXT, opt_entry_level_rank INTEGER, opt_disclose_history INTEGER, opt_history_limit_in_days INTEGER, opt_admin_only_activities INTEGER, passwordhint TEXT, meta_name TEXT, meta_topic TEXT, meta_guidelines TEXT, meta_picture BLOB, premium_video_status INTEGER, premium_video_is_grace_period INTEGER, guid TEXT, dialog_partner TEXT, meta_description TEXT, premium_video_sponsor_list TEXT, chat_dbid INTEGER, history_horizon INTEGER, extprop_profile_height INTEGER, extprop_chat_width INTEGER, extprop_chat_left_margin INTEGER, extprop_chat_right_margin INTEGER, extprop_entry_height INTEGER, extprop_windowpos_x INTEGER, extprop_windowpos_y INTEGER, extprop_windowpos_w INTEGER, extprop_windowpos_h INTEGER, extprop_window_maximized INTEGER, extprop_window_detached INTEGER, extprop_pinned_order INTEGER, extprop_new_in_inbox INTEGER, extprop_tab_order INTEGER, extprop_video_layout INTEGER, extprop_video_chat_height INTEGER, extprop_chat_avatar INTEGER, extprop_consumption_timestamp INTEGER, extprop_form_visible INTEGER, extprop_recovery_mode INTEGER)",
      "dbmeta": "CREATE TABLE DbMeta (key TEXT NOT NULL PRIMARY KEY, value TEXT)",
      "legacymessages": "CREATE TABLE LegacyMessages (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER)",
      "messages": "CREATE TABLE Messages (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, chatname TEXT, timestamp INTEGER, author TEXT, from_dispname TEXT, chatmsg_type INTEGER, identities TEXT, leavereason INTEGER, body_xml TEXT, chatmsg_status INTEGER, body_is_rawxml INTEGER, edited_by TEXT, edited_timestamp INTEGER, newoptions INTEGER, newrole INTEGER, dialog_partner TEXT, oldoptions INTEGER, guid BLOB, convo_id INTEGER, type INTEGER, sending_status INTEGER, param_key INTEGER, param_value INTEGER, reason TEXT, error_code INTEGER, consumption_status INTEGER, author_was_live INTEGER, participant_count INTEGER, pk_id INTEGER, crc INTEGER, remote_id INTEGER, call_guid TEXT, extprop_contact_review_date TEXT, extprop_contact_received_stamp INTEGER, extprop_contact_reviewed INTEGER)",
      "participants": "CREATE TABLE Participants (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, convo_id INTEGER, identity TEXT, rank INTEGER, requested_rank INTEGER, text_status INTEGER, voice_status INTEGER, video_status INTEGER, live_identity TEXT, live_price_for_me TEXT, live_fwd_identities TEXT, live_start_timestamp INTEGER, sound_level INTEGER, debuginfo TEXT, next_redial_time INTEGER, nrof_redials_left INTEGER, last_voice_error TEXT, quality_problems TEXT, live_type INTEGER, live_country TEXT, transferred_by TEXT, transferred_to TEXT, adder TEXT, is_premium_video_sponsor INTEGER, is_multiparty_video_capable INTEGER, live_identity_to_use TEXT, livesession_recovery_in_progress INTEGER, extprop_default_identity INTEGER, last_leavereason INTEGER)",
      "smses": "CREATE TABLE SMSes (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, is_failed_unseen INTEGER, price_precision INTEGER, type INTEGER, status INTEGER, failurereason INTEGER, price INTEGER, price_currency TEXT, target_numbers TEXT, target_statuses BLOB, body TEXT, timestamp INTEGER, reply_to_number TEXT, chatmsg_id INTEGER, extprop_hide_from_history INTEGER, extprop_extended INTEGER, identity TEXT, notification_id INTEGER, event_flags INTEGER)",
      "transfers": "CREATE TABLE Transfers (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, type INTEGER, partner_handle TEXT, partner_dispname TEXT, status INTEGER, failurereason INTEGER, starttime INTEGER, finishtime INTEGER, filepath TEXT, filename TEXT, filesize TEXT, bytestransferred TEXT, bytespersecond INTEGER, chatmsg_guid BLOB, chatmsg_index INTEGER, convo_id INTEGER, pk_id INTEGER, nodeid BLOB, last_activity INTEGER, flags INTEGER, old_status INTEGER, old_filepath INTEGER, extprop_localfilename TEXT, extprop_hide_from_history INTEGER, extprop_window_visible INTEGER, extprop_handled_by_chat INTEGER, accepttime INTEGER)",
      "videos": "CREATE TABLE Videos (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, status INTEGER, dimensions TEXT, error TEXT, debuginfo TEXT, duration_1080 INTEGER, duration_720 INTEGER, duration_hqv INTEGER, duration_vgad2 INTEGER, duration_ltvgad2 INTEGER, timestamp INTEGER, hq_present INTEGER, duration_ss INTEGER, ss_timestamp INTEGER, media_type INTEGER, convo_id INTEGER, device_path TEXT)",
      "voicemails": "CREATE TABLE Voicemails (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, type INTEGER, partner_handle TEXT, partner_dispname TEXT, status INTEGER, failurereason INTEGER, subject TEXT, timestamp INTEGER, duration INTEGER, allowed_duration INTEGER, playback_progress INTEGER, convo_id INTEGER, chatmsg_guid BLOB, notification_id INTEGER, flags INTEGER, size INTEGER, path TEXT, failures INTEGER, vflags INTEGER, xmsg TEXT, extprop_hide_from_history INTEGER)",
    }



    def __init__(self, filename, log_error=True):
        """
        Initializes a new Skype database object from the file.

        @param   log_error  if False, exceptions on opening the database
                            are not written to log (written by default)
        """
        self.filename = filename
        self.basefilename = os.path.basename(self.filename)
        self.backup_created = False
        self.consumers = set() # Registered objects, notified on clearing cache
        self.account = None    # Row from table Accounts
        self.id = None   # Accounts.skypename
        self.tables = {} # {"name": {"Name":str, "rows": 0, "columns": []}, }
        self.tables_list = None # Ordered list of table items
        self.table_rows = {}    # {"tablename1": [..], }
        self.table_objects = {} # {"tablename1": {id1: {rowdata1}, }, }
        self.table_grids = {}   # {"tablename1": TableBase, }
        self.update_fileinfo()
        try:
            self.connection = sqlite3.connect(self.filename,
                check_same_thread = False)
            self.connection.row_factory = self.row_factory
            self.connection.text_factory = str
            rows = self.execute(
                "SELECT name, sql FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
            for row in rows:
                self.tables[row["name"].lower()] = row
        except Exception, e:
            if log_error:
                main.log("Error opening database %s (%s).", filename,
                    traceback.format_exc()
                )
            self.close()
            raise

        try:
            self.account = self.execute("SELECT *, "
                "COALESCE(fullname, displayname, skypename) AS name, "
                "skypename AS identity FROM accounts LIMIT 1"
            ).fetchone()
            self.id = self.account["skypename"]
        except Exception, e:
            if log_error:
                main.log("Error getting account information from %s (%s).",
                    filename, e
                )


    def __str__(self):
        if self and hasattr(self, "filename"):
            return self.filename


    def clear_cache(self):
        """Clears all the currently cached rows."""
        self.table_rows.clear()
        self.table_objects.clear()
        self.get_tables(True)


    def register_consumer(self, consumer):
        """
        Registers a consumer with the database, notified on clearing cache by
        consumer.on_database_changed().
        """
        self.consumers.add(consumer)


    def unregister_consumer(self, consumer):
        """Removes a registered consumer from the database."""
        if consumer in self.consumers:
            self.consumers.remove(consumer)


    def has_consumers(self):
        """Returns whether the database has currently registered consumers."""
        return len(self.consumers) > 0


    def close(self):
        """Closes the database and frees all allocated data."""
        if hasattr(self, "connection"):
            try:
                self.connection.close()
            finally:
                del self.connection
                self.connection = None
        for attr in ["tables", "tables_list", "table_rows",
        "table_grids", "table_objects"]:
            if hasattr(self, attr):
                delattr(self, attr)
                setattr(self, attr, None)


    def execute(self, *args, **kwargs):
        """Shorthand for self.execute()."""
        result = None
        if self.connection:
            result = self.connection.execute(*args, **kwargs)
        return result


    def execute_select(self, sql):
        """
        Returns a TableBase instance initialized with the results of the query.
        """
        grid = TableBase.from_query(self, sql)
        return grid


    def execute_action(self, sql):
        """
        Executes the specified SQL INSERT/UPDATE/DELETE statement and returns
        the number of affected rows.
        """
        self.ensure_backup()
        res = self.execute(sql)
        affected_rows = res.rowcount
        self.connection.commit()
        return affected_rows


    def check_future_dates(self):
        """
        Checks whether any messages in the database have a timestamp in the
        future (this can happen if the computer clock has been erraneously
        set to a future date when receing messages).

        @return  (future message count, max future datetime)
        """
        result = (None, None)
        if self.is_open() and "messages" in self.tables:
            now = self.future_check_timestamp = int(time.time())
            timestamp_max = self.execute(
                "SELECT MAX(Timestamp) AS max FROM messages"
            ).fetchone()["max"] # UNIX timestamp
            count = self.execute(
                "SELECT COUNT(*) AS count FROM messages WHERE timestamp > ?",
                [now]
            ).fetchone()["count"]
            result = (count, datetime.datetime.fromtimestamp(timestamp_max))

        return result


    def move_future_dates(self, days, hours):
        """
        Updates the timestamp of future messages.

        @param   days   days to move, positive or negative number
        @param   hours  hours to move, positive or negative number
        """
        if self.is_open() and "messages" in self.tables:
            self.ensure_backup()
            seconds = (days * 24 + hours) * 3600
            self.execute(
                "UPDATE messages SET timestamp = timestamp + ? "
                "WHERE timestamp > ?", [seconds, self.future_check_timestamp]
            )
            self.connection.commit()
            self.last_modified = datetime.datetime.now()


    def is_open(self):
        """Returns whether the database is currently open."""
        return (self.connection is not None)


    def get_tables(self, refresh=False, this_table=None):
        """
        Returns the names and rowcounts of all tables in the database, as
        [{"name": "tablename", "rows": 0, "sql": CREATE SQL}, ].
        Uses already retrieved cached values if possible, unless refreshing.

        @param   refresh        if True, information including rowcounts is
                                refreshed
        @param   this_table  if set, only information for this table is
                                refreshed
        """
        if self.is_open() and (refresh or self.tables_list is None):
            sql = "SELECT name, sql FROM sqlite_master WHERE type = 'table' " \
                  "%sORDER BY name" % ("AND name = ? " if this_table else "")
            params = [this_table] if this_table else []
            rows = self.execute(sql, params).fetchall()
            tables = {}
            tables_list = []
            for row in rows:
                table = row
                table["rows"] = self.execute(
                    "SELECT COUNT(*) AS count FROM %s" % table["name"]
                ).fetchone()["count"]
                # Here and elsewhere in this module - table names are turned to
                # lowercase when used as keys.
                tables[table["name"].lower()] = table
                tables_list.append(table)
            if this_table:
                self.tables.update(tables)
                for t in self.tables_list:
                    if t["name"] == this_table:
                        self.tables_list.remove(t)
                self.tables_list += tables_list
                self.tables_list.sort(key=lambda x: x["name"])
            else:
                self.tables = tables
                self.tables_list = tables_list

        return self.tables_list


    def get_messages(self, chat=None, ascending=True,
                     timestamp_from=None, body_like=None):
        """
        Yields all the messages (or messages for the specified chat), as
        {"datetime": datetime, ..}, ordered from earliest to latest.
        Uses already retrieved cached values if possible.

        @param   chat            as returned from get_conversations(), if any
        @param   ascending       can specify message order, earliest to latest
                                 or latest to earliest
        @param   body_like       text to match in body with LIKE
        @param   timestamp_from  timestamp beyond which messages will start
        """
        if self.is_open() and "messages" in self.tables:
            if "messages" not in self.table_rows:
                self.table_rows["messages"] = {} # {convo_id: [{msg1},]}
            if not (chat and chat["id"] in self.table_rows["messages"]):
                # Cache messages
                params = {}
                # Take only message types we can handle
                sql = "SELECT * FROM messages WHERE " \
                      "type IN (2, 10, 12, 13, 30, 39, 51, 61, 63, 64, 68)"
                if chat:
                    sql += " AND convo_id = :convo_id"
                    params["convo_id"] = chat["id"]
                if timestamp_from:
                    sql += " AND timestamp %s :timestamp" % \
                           (">" if ascending else "<")
                    params["timestamp"] = timestamp_from
                if body_like:
                    sql += " AND body_xml LIKE :body_like"
                    params["body_like"] = "%%%s%%" % body_like
                sql += " ORDER BY timestamp %s" \
                    % ("ASC" if ascending else "DESC")
                res = self.execute(sql, params)
                messages = []
                message = res.fetchone()
                while message:
                    message["datetime"] = None
                    if message["timestamp"]:
                        message["datetime"] = datetime.datetime.fromtimestamp(
                            message["timestamp"]
                        )
                    messages.append(message)
                    yield message
                    message = res.fetchone()
                if chat:
                    self.table_rows["messages"][chat["id"]] = messages
            else:
                messages_sorted = sorted(
                    self.table_rows["messages"][chat["id"]],
                    key=lambda m: m["timestamp"], reverse=not ascending
                )
                if timestamp_from:
                    messages_sorted = filter(
                        lambda x: (x["timestamp"] > timestamp_from)
                        if ascending else
                        (x["timestamp"] < timestamp_from), messages_sorted
                    )
                for message in messages_sorted:
                    yield message


    def row_factory(self, cursor, row):
        """
        Creates dicts from resultset rows, with BLOB fields converted to
        strings.
        """
        result = {}
        #print cursor.description
        for idx, col in enumerate(cursor.description):
            name = col[0]
            result[name] = row[idx]
        for name in result.keys():
            datatype = type(result[name])
            if datatype is buffer:
                result[name] = str(result[name]).decode("latin1")
            elif datatype is str or datatype is unicode:
                try:
                    result[name] = str(result[name]).decode("utf-8")
                except:
                    result[name] = str(result[name]).decode("latin1")
        return result


    def get_conversations(self):
        """
        Returns all the chats and message rowcounts in the database, as
        [{"id": integer, "title": "chat title", "created_datetime": datetime,
          "title_long": "Group chat "chat_title"", "title_long_lc": "group..",
          "last_activity_datetime": datetime, "type_name": chat type name}, ..]
        Uses already retrieved cached values if possible.
        """
        conversations = []
        if self.is_open() and "conversations" in self.tables:
            if "conversations" not in self.table_rows:
                participants = {}
                if "contacts" in self.tables and "participants" in self.tables:
                    main.log("Conversations and participants: "
                             "retrieving all (%s).", self.filename)
                    self.get_contacts()
                    self.get_table_rows("participants")
                    for i in self.table_objects["participants"].values():
                        if i["convo_id"] not in participants:
                            participants[i["convo_id"]] = []
                        if i["identity"] == self.id:
                            i["contact"] = self.account
                        else:
                            # Fake a dummy contact object if no contact row
                            i["contact"] = self.table_objects["contacts"].get(
                                i["identity"], {"skypename":   i["identity"],
                                                "identity":    i["identity"],
                                                "name":        i["identity"],
                                                "fullname":    i["identity"],
                                                "displayname": i["identity"]}
                            )
                        participants[i["convo_id"]].append(i)
                [i.sort(key=lambda x: (x["contact"]["name"] or "").lower())
                 for i in participants.values()]
                rows = self.execute(
                    "SELECT *, COALESCE(displayname, meta_topic) AS title, "
                    "NULL AS created_datetime, "
                    "NULL AS last_activity_datetime "
                    "FROM conversations WHERE displayname IS NOT NULL "
                    "ORDER BY last_activity_timestamp DESC"
                ).fetchall()
                conversations = []
                for chat in rows:
                    chat["title_long"] = ("Chat with %s"
                        if CHATS_TYPE_SINGLE == chat["type"]
                        else "Group chat \"%s\"") % chat["title"]
                    chat["title_long_lc"] = \
                        chat["title_long"][0].lower() + chat["title_long"][1:]
                    for k, v in [("creation_timestamp", "created_datetime"),
                    ("last_activity_timestamp", "last_activity_datetime")]:
                        if chat[k]:
                            chat[v] = datetime.datetime.fromtimestamp(chat[k])
                        
                    chat["type_name"] = CHATS_TYPENAMES.get(chat["type"],
                        "Unknown (%d)" % chat["type"])
                    # Set stats attributes presence
                    chat["message_count"] = None
                    chat["first_message_timestamp"] = None
                    chat["last_message_timestamp"] = None
                    chat["first_message_datetime"] = None
                    chat["last_message_datetime"] = None
                    #chat["participants"] = []
                    chat["participants"] = participants.get(chat["id"], [])
                    conversations.append(chat)
                main.log("Conversations and participants retrieved "
                    "(%s chats, %s contacts, %s).",
                    len(conversations), len(self.table_rows["contacts"]),
                    self.filename
                )
                self.table_rows["conversations"] = conversations
            else:
                conversations = self.table_rows["conversations"]

        return conversations


    def get_conversations_stats(self, chats):
        """
        Collects statistics for all conversations and fills in the values:
        {"first_message_timestamp": int, "first_message_datetime": datetime,
         "last_message_timestamp": int, "last_message_datetime": datetime,
         "participants": [{row from Participants,
                           "contact": {row from Contacts}}, ],
         "message_count": message count, }.

        @param   chats  list of chats, as returned from get_conversations()
        """
        main.log("Statistics collection starting (%s).", self.filename)
        stats = []
        participants = {}
        if self.is_open() and "messages" in self.tables:
            and_str = " AND convo_id in (%s)" % ", ".join(["?"] * len(chats)) \
                      if chats else ""
            and_val = [c["id"] for c in chats] if chats else []
            rows_stat = self.execute(
                "SELECT convo_id AS id, COUNT(*) AS message_count, "
                "MIN(timestamp) AS first_message_timestamp, "
                "MAX(timestamp) AS last_message_timestamp, "
                "NULL AS first_message_datetime, "
                "NULL AS last_message_datetime "
                "FROM messages "
                "WHERE type IN (2, 10, 13, 51, 61, 63, 64, 68) "
                + and_str +
                "GROUP BY convo_id", and_val).fetchall()
            stats = dict((i["id"], i) for i in rows_stat)
        for chat in chats:
            if chat["id"] in stats:
                data = stats[chat["id"]]
                for n in ["first_message", "last_message"]:
                    if data["%s_timestamp" % n]:
                        data["%s_datetime" % n] = \
                            datetime.datetime.fromtimestamp(
                                data["%s_timestamp" % n]
                            )
                chat.update(data)
        main.log("Statistics collected (%s).", self.filename)


    def get_contactgroups(self):
        """
        Returns the non-empty contact groups in the database.
        Uses already retrieved cached values if possible.
        """
        groups = []
        if self.is_open() and "contactgroups" in self.tables:
            if "contactgroups" not in self.table_rows:
                rows = self.execute(
                    "SELECT *, given_displayname AS name FROM contactgroups "
                    "WHERE members IS NOT NULL ORDER BY id").fetchall()
                self.table_objects["contactgroups"] = {}
                for group in rows:
                    groups.append(group)
                    self.table_objects["contactgroups"][group["id"]] = group
                self.table_rows["contactgroups"] = groups
            else:
                groups = self.table_rows["contactgroups"]

        return groups


    def get_contacts(self):
        """
        Returns all the contacts in the database, as
        [{"identity": skypename or pstnnumber,
          "name": displayname or fullname, },]
        Uses already retrieved cached values if possible.
        """
        contacts = []
        if self.is_open() and "contacts" in self.tables:
            if "contacts" not in self.table_rows:
                rows = self.execute(
                    "SELECT *, COALESCE(skypename, pstnnumber) AS identity, "
                    "COALESCE(fullname, displayname, skypename, pstnnumber) "
                    "AS name FROM contacts ORDER BY name").fetchall()
                self.table_objects["contacts"] = {}
                for c in rows:
                    contacts.append(c)
                    self.table_objects["contacts"][c["identity"]] = c
                self.table_rows["contacts"] = contacts
            else:
                contacts = self.table_rows["contacts"]

        return contacts


    def get_contact_name(self, identity):
        """
        Returns the full name for the specified contact, or given identity if
        not set.

        @param   identity  skypename or pstnnumber
        """
        name = identity
        self.get_contacts()
        if identity == self.id:
            name = self.account["name"]
        elif identity in self.table_objects["contacts"]:
            name = self.table_objects["contacts"][identity]["name"]
        return name



    def get_table_rows(self, table):
        """
        Returns all the rows of the specified table.
        Uses already retrieved cached values if possible.
        """
        rows = []
        table = table.lower()
        if table in self.tables:
            if table not in self.table_rows:
                col_data = self.get_table_columns(table)
                pks = [c["name"] for c in col_data if c["pk"]]
                pk = pks[0] if len(pks) == 1 else None
                rows = self.execute("SELECT * FROM %s" % table).fetchall()
                self.table_rows[table] = rows
                self.table_objects[table] = {}
                if pk:
                    for row in rows:
                        self.table_objects[table][row[pk]] = row
            else:
                rows = self.table_rows[table]
        return rows


    def get_transfers(self):
        """
        Returns all the transfers in the database.
        Uses already retrieved cached values if possible.
        """
        transfers = []
        if self.is_open() and "transfers" in self.tables:
            if "transfers" not in self.table_rows:
                rows = self.execute(
                    "SELECT * FROM transfers ORDER BY id").fetchall()
                transfers = []
                for transfer in rows:
                    transfers.append(transfer)
                self.table_rows["transfers"] = transfers
            else:
                transfers = self.table_rows["transfers"]

        return transfers


    def get_videos(self, chat=None):
        """
        Returns all valid video rows in the database (with a matching row in
        Calls). Uses already retrieved cached values if possible.

        @param   chat  if a row from get_conversations, returns only videos
                       under this chat
        """
        videos = []
        if self.is_open() and "videos" in self.tables:
            if "videos" not in self.table_rows:
                rows = self.execute(
                    "SELECT videos.* FROM videos "
                    "INNER JOIN calls ON videos.convo_id = calls.id "
                    "ORDER BY videos.id"
                ).fetchall()
                videos = []
                self.table_objects["videos"] = {}
                for video in rows:
                    videos.append(video)
                    self.table_objects["videos"][video["id"]] = video
                self.table_rows["videos"] = videos
            else:
                videos = self.table_rows["videos"]

        if chat:
            videos = [v for v in videos if v["convo_id"] == chat["id"]]
        return videos


    def get_calls(self, chat=None):
        """
        Returns all calls in the database.
        Uses already retrieved cached values if possible.

        @param   chat  if a row from get_conversations, returns only calls
                       under this chat
        """
        calls = []
        if self.is_open() and "calls" in self.tables:
            if "calls" not in self.table_rows:
                rows = self.execute(
                    "SELECT * FROM calls ORDER BY calls.id"
                ).fetchall()
                calls = []
                self.table_objects["calls"] = {}
                for call in rows:
                    calls.append(call)
                    self.table_objects["calls"][call["id"]] = call
                self.table_rows["calls"] = calls
            else:
                calls = self.table_rows["calls"]

        if chat:
            calls = [c for c in calls if c["conv_dbid"] == chat["id"]]
        return calls


    def get_conversation_participants(self, chat):
        """
        Returns the participants of the chat, as
        [{name, all Participant columns, "contact": {all Contact columns}}]
        (excluding database account owner).
        """
        participants = []
        if self.is_open() and "contacts" in self.tables:
            if "contacts" not in self.table_objects:
                # Retrieve and cache all contacts
                self.table_objects["contacts"] = {}
                rows = self.execute(
                    "SELECT *, COALESCE(skypename, pstnnumber) AS identity "
                    "FROM contacts").fetchall()
                for row in rows:
                    self.table_objects["contacts"][row["identity"]] = row
            rows = self.execute(
                "SELECT COALESCE(c.fullname, c.displayname, c.skypename, "
                "c.pstnnumber) AS name, c.skypename, p.* "
                "FROM contacts AS c INNER JOIN participants AS p "
                "ON p.identity = c.skypename "
                "WHERE p.convo_id = :id AND c.skypename != :skypename "
                "ORDER BY name ASC",
                {"id": chat["id"], "skypename": self.account["skypename"]}
            ).fetchall()
            for p in rows:
                p["contact"] = self.table_objects["contacts"].get(
                    p["identity"], None
                )
                if not p["contact"]:
                    p["contact"] = self.get_contact(p["identity"])
                participants.append(p)

        return participants


    def get_contact(self, identity):
        """
        Returns the contact specified by the identity
        (skypename or pstnnumber).
        """
        contact = None
        if self.is_open() and "contacts" in self.tables:
            """Returns the specified contact row, using cache if possible."""
            if "contacts" not in self.table_objects:
                self.table_objects["contacts"] = {}
            contact = self.table_objects["contacts"].get(identity, None)
            if not contact:
                contact = self.execute(
                    "SELECT *, COALESCE(fullname, displayname, skypename, "
                    "pstnnumber) AS name, COALESCE(skypename, pstnnumber) "
                    "AS identity FROM contacts WHERE skypename = :identity "
                    "OR pstnnumber = :identity",
                    {"identity": identity}
                ).fetchone()
                self.table_objects["contacts"][identity] = contact

        return contact


    def get_table_columns(self, table):
        """
        Returns the columns of the specified table, as
        [{"name": "col1", "type": "INTEGER", }, ] or None if not found.
        """
        table = table.lower()
        table_columns = None
        if self.is_open() and self.tables_list is None:
            self.get_tables()
        if self.is_open() and table in self.tables:
            if "columns" in self.tables[table]:
                table_columns = self.tables[table]["columns"]
            else:
                res = self.execute("PRAGMA table_info(%s)" % table)
                table_columns = []
                for row in res.fetchall():
                    table_columns.append(row)
                self.tables[table]["columns"] = table_columns
        return table_columns


    def get_table_data(self, table):
        """
        Returns a TableBase instance initialized with the contents of the
        specified table.
        Uses already retrieved cached values if possible.
        """
        table = table.lower()
        if table not in self.table_grids:
            self.table_grids[table] = TableBase.from_table(self, table)

        return self.table_grids[table]


    def get_unsaved_grids(self):
        """
        Returns a list of table names that have a grid where changes have not
        been saved after changing.
        """
        tables = []
        for table, grid_data in self.table_grids.items():
            if grid_data.IsChanged():
                tables.append(table)
        return tables


    def save_unsaved_grids(self):
        """Saves all data in unsaved grids."""
        for table, grid_data in self.table_grids.items():
            if grid_data.IsChanged():
                grid_data.SaveChanges()


    def update_fileinfo(self):
        """Updates database file size and modification information."""
        self.filesize = os.path.getsize(self.filename)
        self.last_modified = datetime.datetime.fromtimestamp(
            os.path.getmtime(self.filename)
        )


    def ensure_backup(self):
        """Creates a backup file if configured so, and not already created."""
        if conf.DBDoBackup:
            if (not self.backup_created
            or not os.path.exists("%s.bak" % self.filename)):
                shutil.copyfile(self.filename, "%s.bak" % self.filename)
                self.backup_created = True


    def blobs_to_binary(self, values, list_columns, col_data):
        """
        Converts blob columns in the list to sqlite3.Binary, suitable
        for using as a query parameter.
        """
        result = []
        is_dict = isinstance(values, dict)
        list_values = [values[i] for i in list_columns] if is_dict else values
        map_columns = dict([(i["name"], i) for i in col_data])
        for i, val in enumerate(list_values):
            if "blob" == map_columns[list_columns[i]]["type"].lower() and val:
                if isinstance(val, unicode):
                    val = val.encode("latin1")
                val = sqlite3.Binary(val)
            result.append(val)
        if is_dict:
            result = dict([(list_columns[i], x) for i, x in enumerate(result)])
        return result


    def fill_missing_fields(self, data, fields):
        """Creates a copy of the data and adds any missing fields."""
        filled = data.copy()
        for field in fields:
            if field not in filled:
                filled[field] = None
        return filled


    def create_table(self, table, create_sql=None):
        """Creates the specified table and updates our column data."""
        table = table.lower()
        if create_sql or (table in self.INSERT_STATEMENTS):
            self.execute(create_sql or self.INSERT_STATEMENTS[table])
            row = self.execute("SELECT name, sql FROM sqlite_master "
                                "WHERE type = 'table' "
                                "AND LOWER(name) = ?", [table]).fetchone()
            self.tables[table] = row


    def insert_chat(self, chat, source_db):
        """Inserts the specified chat into the database and returns its ID."""
        if self.is_open() and not self.account and source_db.account:
            self.insert_account(source_db.account)
        if self.is_open() and "conversations" not in self.tables:
            self.create_table("conversations")
        if self.is_open() and "conversations" in self.tables:
            self.ensure_backup()
            col_data = self.get_table_columns("conversations")
            fields = [col["name"] for col in col_data if col["name"] != "id"]
            str_cols = ", ".join(fields)
            str_vals = ":" + ", :".join(fields)
            chat_filled = self.fill_missing_fields(chat, fields)
            chat_filled = self.blobs_to_binary(chat_filled, fields, col_data)

            cursor = self.execute(
                "INSERT INTO conversations (%s) VALUES (%s)" % (
                    str_cols, str_vals
                )
            , chat_filled)
            self.connection.commit()
            self.last_modified = datetime.datetime.now()
            return cursor.lastrowid


    def insert_messages(self, chat, messages, source_db, source_chat):
        """
        Inserts the specified messages under the specified chat in this
        database, includes related rows in Calls, Videos, Transfers and
        SMSes.
        """
        if self.is_open() and not self.account and source_db.account:
            self.insert_account(source_db.account)
        if self.is_open() and "messages" not in self.tables:
            self.create_table("messages")
        if self.is_open() and "transfers" not in self.tables:
            self.create_table("transfers")
        if self.is_open() and "smses" not in self.tables:
            self.create_table("smses")
        if self.is_open() and "chats" not in self.tables:
            self.create_table("chats")
        if self.is_open() and "messages" in self.tables:
            main.log("Merging %d chat messages (%s) into %s.", len(messages),
                chat["title_long_lc"], self.filename
            )
            self.ensure_backup()
            # Messages.chatname corresponds to Chats.name, and Chats entries
            # must exist for Skype application to be able to find the messages.
            chatrows_source = dict([(i["name"], i) for i in 
                source_db.execute(
                    "SELECT * FROM chats WHERE conv_dbid = ?",
                    [source_chat["id"]]
                )
            ])
            chatrows_present = dict([(i["name"], 1)
                for i in self.execute("SELECT name FROM chats")]
            )
            col_data = self.get_table_columns("messages")
            fields = [col["name"] for col in col_data if col["name"] != "id"]
            str_cols = ", ".join(fields)
            str_vals = ":" + ", :".join(fields)
            transfer_col_data = self.get_table_columns("transfers")
            transfer_fields = [col["name"] for col in transfer_col_data
                if col["name"] != "id"
            ]
            transfer_cols = ", ".join(transfer_fields)
            transfer_vals = ", ".join(["?"] * len(transfer_fields))
            sms_col_data = self.get_table_columns("smses")
            sms_fields = [col["name"] for col in sms_col_data
                if col["name"] != "id"
            ]
            sms_cols = ", ".join(sms_fields)
            sms_vals = ", ".join(["?"] * len(sms_fields))
            chat_col_data = self.get_table_columns("chats")
            chat_fields = [col["name"] for col in chat_col_data
                if col["name"] != "id"
            ]
            chat_cols = ", ".join(chat_fields)
            chat_vals = ", ".join(["?"] * len(chat_fields))
            timestamp_earliest = source_chat["creation_timestamp"] \
                                 or sys.maxint
            for m in messages:
                # Insert corresponding Chats entry, if not present
                if (m["chatname"] not in chatrows_present
                and m["chatname"] in chatrows_source):
                    chatrow = chatrows_source[m["chatname"]]
                    chatrow = [(chatrow[col] if col in chatrow else "")
                        for col in chat_fields
                    ]
                    chatrow = self.blobs_to_binary(
                        chatrow, chat_fields, chat_col_data
                    )
                    self.execute(
                        "INSERT INTO chats (%s) VALUES (%s)" % (
                            chat_cols, chat_vals
                        )
                    , chatrow)
                    chatrows_present[m["chatname"]] = 1
                m_filled = self.fill_missing_fields(m, fields)
                m_filled["convo_id"] = chat["id"]
                m_filled = self.blobs_to_binary(m_filled, fields, col_data)
                self.execute("INSERT INTO messages (%s) VALUES (%s)" % (
                    str_cols, str_vals
                ), m_filled)
                if (m["chatmsg_type"] == 7 and m["type"] == 68
                and "transfers" in source_db.tables):
                    transfer = source_db.execute(
                        "SELECT * FROM Transfers WHERE chatmsg_guid = :guid", m
                    ).fetchone()
                    if transfer:
                        t = []
                        for col in transfer_fields:
                            if col == "convo_id":
                                t.append(chat["id"])
                            else:
                                t.append(transfer[col])
                        # pk_id and nodeid are troublesome, because their
                        # meaning is unknown, maybe something will go out of
                        # sync if their values can differ?
                        t = self.blobs_to_binary(
                            t, transfer_fields, transfer_col_data
                        )
                        self.execute(
                            "INSERT INTO transfers (%s) VALUES (%s)" % (
                                transfer_cols, transfer_vals
                            )
                        , t)
                if (m["chatmsg_type"] == 7 and m["type"] == 64
                and "smses" in source_db.tables):
                    sms = source_db.execute(
                        "SELECT * FROM smses WHERE chatmsg_id = :id", m
                    ).fetchone()
                    if sms:
                        t = [(sms[col] if col in sms else "")
                            for col in sms_fields
                        ]
                        # pk_id and nodeid are troublesome, because their
                        # meaning is unknown, maybe something will go out of
                        # sync if their values can differ?
                        t = self.blobs_to_binary(t, sms_fields, sms_col_data)
                        self.execute(
                            "INSERT INTO smses (%s) VALUES (%s)" % (
                                sms_cols, sms_vals
                            )
                        , t)
                timestamp_earliest = min(timestamp_earliest, m["timestamp"])
            if (timestamp_earliest
            and chat["creation_timestamp"] > timestamp_earliest):
                # Conversations.creation_timestamp must not be later than the
                # oldest message, Skype will not show messages older than that.
                chat["creation_timestamp"] = timestamp_earliest
                chat["created_datetime"] = \
                    datetime.datetime.fromtimestamp(timestamp_earliest)
                self.execute("UPDATE conversations SET creation_timestamp = "
                    ":creation_timestamp WHERE id = :id", chat
                )
            self.connection.commit()
            self.last_modified = datetime.datetime.now()


    def insert_participants(self, chat, participants):
        """
        Inserts the specified messages under the specified chat in this
        database.
        """
        if self.is_open() and not self.account and source_db.account:
            self.insert_account(source_db.account)
        if self.is_open() and "participants" not in self.tables:
            self.create_table("participants")
        if self.is_open() and "contacts" not in self.tables:
            self.create_table("contacts")
        if self.is_open() and "participants" in self.tables:
            main.log("Merging %d chat participants (%s) into %s.",
                len(participants), chat["title_long_lc"], self.filename
            )
            self.ensure_backup()
            col_data = self.get_table_columns("participants")
            fields = [col["name"] for col in col_data if col["name"] != "id"]
            str_cols = ", ".join(fields)
            str_vals = ":" + ", :".join(fields)

            for p in participants:
                p_filled = self.fill_missing_fields(p, fields)
                p_filled = self.blobs_to_binary(p_filled, fields, col_data)
                p_filled["convo_id"] = chat["id"]
                self.execute("INSERT INTO participants (%s) VALUES (%s)" % (
                    str_cols, str_vals
                ), p_filled)

            self.connection.commit()
            self.last_modified = datetime.datetime.now()


    def insert_account(self, account):
        """
        Inserts the specified account into this database and sets it as the
        current account.
        """
        if self.is_open() and "accounts" not in self.tables:
            self.create_table("accounts")
            self.get_tables(True, "accounts")
        if self.is_open() and "accounts" in self.tables:
            main.log("Inserting account \"%s\" into %s.",
                account["skypename"], self.filename
            )
            self.ensure_backup()
            col_data = self.get_table_columns("accounts")
            fields = [col["name"] for col in col_data if col["name"] != "id"]
            str_cols = ", ".join(fields)
            str_vals = ":" + ", :".join(fields)

            a_filled = self.fill_missing_fields(account, fields)
            del a_filled["id"]
            a_filled = self.blobs_to_binary(a_filled, fields, col_data)
            self.execute("INSERT INTO accounts (%s) VALUES (%s)" % (
                str_cols, str_vals
            ), a_filled)
            self.connection.commit()
            self.last_modified = datetime.datetime.now()
            self.account = a_filled
            self.id = a_filled["skypename"]


    def insert_contacts(self, contacts):
        """
        Inserts the specified contacts into this database.
        """
        if self.is_open() and not self.account and source_db.account:
            self.insert_account(source_db.account)
        if self.is_open() and "contacts" not in self.tables:
            self.create_table("contacts")
        if self.is_open() and "contacts" in self.tables:
            main.log(
                "Merging %d contacts into %s.", len(contacts), self.filename
            )
            self.ensure_backup()
            col_data = self.get_table_columns("contacts")
            fields = [col["name"] for col in col_data if col["name"] != "id"]
            str_cols = ", ".join(fields)
            str_vals = ":" + ", :".join(fields)
            for c in contacts:
                c_filled = self.fill_missing_fields(c, fields)
                c_filled = self.blobs_to_binary(c_filled, fields, col_data)
                self.execute("INSERT INTO contacts (%s) VALUES (%s)" % (
                    str_cols, str_vals
                ), c_filled)
            self.connection.commit()
            self.last_modified = datetime.datetime.now()


    def replace_contactgroups(self, groups):
        """
        Inserts or updates the specified contact groups in this database.
        """
        if self.is_open() and not self.account and source_db.account:
            self.insert_account(source_db.account)
        if self.is_open() and "contactgroups" not in self.tables:
            self.create_table("contactgroups")
        if self.is_open() and "contactgroups" in self.tables:
            main.log("Merging %d contact groups into %s.",
                len(groups), self.filename
            )
            self.ensure_backup()

            col_data = self.get_table_columns("contactgroups")
            pk = [c["name"] for c in col_data if c["pk"]][0]
            pk_key = "PK%s" % int(time.time())
            fields = [col["name"] for col in col_data if not col["pk"]]
            str_fields = ", ".join(["%s = :%s" % (col, col) for col in fields])
            existing = dict([(c["name"], c) for c in self.get_contactgroups()])
            for c in filter(lambda x: x["name"] in existing, groups):
                c_filled = self.fill_missing_fields(c, fields)
                c_filled[pk_key] = existing[c["name"]][pk]
                self.execute("UPDATE contactgroups SET %s WHERE %s = :%s" % (
                    str_fields, pk, pk_key
                ), c_filled)

            str_cols = ", ".join(fields)
            str_vals = ":" + ", :".join(fields)
            for c in filter(lambda x: x["name"] not in existing, groups):
                c_filled = self.fill_missing_fields(c, fields)
                c_filled = self.blobs_to_binary(c_filled, fields, col_data)
                self.execute("INSERT INTO contactgroups (%s) VALUES (%s)" % (
                    str_cols, str_vals
                ), c_filled)
            self.connection.commit()
            self.last_modified = datetime.datetime.now()


    def save_row(self, table, row):
        """
        Updates the row in the database or inserts it if not existing.

        @return  ID of the inserted row
        """
        if self.is_open():
            self.ensure_backup()
            table = table.lower()
            col_data = self.get_table_columns(table)
            pk = [c["name"] for c in col_data if c["pk"]][0]
            exists = self.execute(
                "SELECT * FROM %s WHERE %s = :%s" % (table, pk, pk), row
            ).fetchone()
            if exists:
                return self.update_row(table, row)
            else:
                return self.insert_row(table, row)


    def update_row(self, table, row, original_row):
        """
        Updates the table row in the database, identified by its primary key
        in its original values.
        """
        if self.is_open():
            table = table.lower()
            main.log("Updating 1 row in table %s, %s.",
                self.tables[table]["name"], self.filename
            )
            self.ensure_backup()
            col_data = self.get_table_columns(table)
            pk = [c["name"] for c in col_data if c["pk"]][0]
            fields = ", ".join([
                "%(name)s = :%(name)s" % col
                    for col in col_data
            ])
            pk_key = "PK%s" % int(time.time())
            values = row.copy()
            values[pk_key] = original_row[pk]
            self.execute("UPDATE %s SET %s WHERE %s = :%s" % (
                table, fields, pk, pk_key
            ), values)
            self.connection.commit()
            self.last_modified = datetime.datetime.now()
            return row[pk]


    def insert_row(self, table, row):
        """
        Inserts the new table row in the database.

        @return  ID of the inserted row
        """
        if self.is_open():
            table = table.lower()
            main.log("Inserting 1 row into table %s, %s.",
                self.tables[table]["name"], self.filename
            )
            self.ensure_backup()
            col_data = self.get_table_columns(table)
            fields = [col["name"] for col in col_data]
            str_cols = ", ".join(fields)
            str_vals = ":" + ", :".join(fields)
            row = self.blobs_to_binary(row, fields, col_data)
            cursor = self.execute("INSERT INTO %s (%s) VALUES (%s)" % (
                table, str_cols, str_vals
            ), row)
            self.connection.commit()
            self.last_modified = datetime.datetime.now()
            return cursor.lastrowid


    def delete_row(self, table, row):
        """
        Deletes the table row from the database. Row is identified by its
        primary key.
        """
        if self.is_open():
            table = table.lower()
            main.log("Deleting 1 row from table %s, %s.",
                self.tables[table]["name"], self.filename
            )
            self.ensure_backup()
            col_data = self.get_table_columns(table)
            pk = [c["name"] for c in col_data if c["pk"]][0]
            self.execute("DELETE FROM %s WHERE %s = :%s" % (table, pk, pk), row)
            self.connection.commit()
            self.last_modified = datetime.datetime.now()


    def query_table(self, table, order=None, params=None):
        """
        Queries the table and yields results as dicts.

        @param   table     a simple table name, or a more complex join
        @param   order     [(column name to order by, is_ascending), ]
        @param   params    list of AND criteria {name: (operator, value)}
        """
        if self.is_open():
            table = table.lower()
            if table in self.tables:
                paramstr = ""
                orderstr = ""
                values = {}
                if order:
                    for name, ascending in order:
                        orderstr += ", " if orderstr else " ORDER BY "
                        orderstr += name + (" ASC" if ascending else " DESC")
                if params:
                    for name in params:
                        paramstr += " AND " if paramstr else " WHERE "
                        paramstr += "%s %s :%s" % (name, params[name][0], name)
                        values[name] = params[name][1]

                res = self.execute("SELECT * FROM %s%s%s" % (
                    table, paramstr, orderstr
                ), values)
                row = res.fetchone()
                while row:
                    yield row
                    row = res.fetchone()



class TableBase(wx.grid.PyGridTableBase):
    """
    Table base for wx.grid.Grid, can take its data from a single table, or from
    the results of any SELECT query.
    """

    """How many rows to seek ahead for query grids."""
    SEEK_CHUNK_LENGTH = 100

    @classmethod
    def from_query(cls, db, sql):
        """
        Constructs a TableBase instance from a full SQL query.

        @param   db   SkypeDatabase instance
        @param   sql  the SQL query to execute
        """
        self = cls()
        self.is_query = True
        self.db = db
        self.sql = sql
        self.row_iterator = self.db.execute(sql)
        # Fill column information
        self.columns = []
        for idx, col in enumerate(self.row_iterator.description):
            coldata = {"name": col[0], "type": "TEXT"}
            self.columns.append(coldata)

        # Doing some trickery here: we can only know the row count when we have
        # retrieved all the rows, which is preferrable not to do at first,
        # since there is no telling how much time it can take. Instead, we
        # update the row count chunk by chunk.
        self.row_count = self.SEEK_CHUNK_LENGTH
        # ID here is a unique value identifying rows in this object,
        # no relation to table data
        self.idx_all = [] # An ordered list of row identifiers in rows_all
        self.rows_all = {} # Unfiltered, unsorted rows {id: row, }
        self.rows_current = [] # Currently shown (filtered/sorted) rows
        self.iterator_index = -1
        self.sort_ascending = False
        self.sort_column = None # Index of column currently sorted by
        self.filters = {} # {col: value, }
        self.attrs = {} # {"new": wx.grid.GridCellAttr, }
        try:
            self.SeekToRow(self.SEEK_CHUNK_LENGTH - 1)
        except Exception, e:
            pass
        # Seek ahead on rows and get column information from there
        if self.rows_current:
            for coldata in self.columns:
                name = coldata["name"]
                if type(self.rows_current[0][name]) in [int, long, bool]:
                    coldata["type"] = "INTEGER"
                elif type(self.rows_current[0][name]) in [float]:
                    coldata["type"] = "REAL"
        return self


    @classmethod
    def from_table(cls, db, table, where="", order=""):
        """
        Constructs a TableBase instance from a single table.

        @param   db     SkypeDatabase instance
        @param   table  name of table
        @param   where  SQL WHERE clause, without "where" (e.g. "a=b AND c<3")
        @param   order  full SQL ORDER clause (e.g. "ORDER BY a DESC, b ASC")
        """
        self = cls()
        self.is_query = False
        self.db = db
        self.table = table
        self.where = where
        self.order = order
        self.columns = db.get_table_columns(table)
        self.row_count = list(db.execute(
            "SELECT COUNT(*) AS rows FROM %s %s %s" % (table, where, order)
        ))[0]["rows"]
        # ID here is a unique value identifying rows in this object,
        # no relation to table data
        self.idx_all = [] # An ordered list of row identifiers in rows_all
        self.rows_all = {} # Unfiltered, unsorted rows {id: row, }
        self.rows_current = [] # Currently shown (filtered/sorted) rows
        self.idx_changed = set() # set of indices for changed rows in rows_all
        self.rows_backup = {} # For changed rows {id: original_row, }
        self.idx_new = [] # Unsaved added row indices
        self.rows_deleted = {} # Uncommitted deleted rows {id: deleted_row, }
        self.row_iterator = db.execute(
            "SELECT * FROM %s %s %s"
            % (table, "WHERE %s" % where if where else "", order)
        )
        self.iterator_index = -1
        self.sort_ascending = False
        self.sort_column = None # Index of column currently sorted by
        self.filters = {} # {col: value, }
        self.attrs = {} # {"new": wx.grid.GridCellAttr, }
        return self


    def GetColLabelValue(self, col):
        label = self.columns[col]["name"]
        if col == self.sort_column:
            label += u" ↑" if self.sort_ascending else u" ↓"
        if col in self.filters:
            if "TEXT" == self.columns[col]["type"]:
                label += "\nlike \"%s\"" % self.filters[col]
            else:
                label += "\n= %s" % self.filters[col]
        return label


    def GetNumberRows(self):
        result = self.row_count
        if self.filters:
            result = len(self.rows_current)
        return result


    def GetNumberCols(self):
        return len(self.columns)


    def SeekAhead(self, to_end=False):
        """
        Seeks ahead on the query cursor, by the chunk length or until the end.

        @param   to_end  if True, retrieves all rows
        """
        seek_count = self.row_count + self.SEEK_CHUNK_LENGTH - 1
        if to_end:
            seek_count = sys.maxint
        self.SeekToRow(seek_count)


    def SeekToRow(self, row):
        """Seeks ahead on the row iterator to the specified row."""
        rows_before = len(self.rows_all)
        row_initial = row
        while self.row_iterator and (self.iterator_index < row):
            rowdata = None
            try:
                rowdata = self.row_iterator.next()
            except Exception, e:
                pass
            if rowdata:
                idx = id(rowdata)
                rowdata["__id__"] = idx
                rowdata["__changed__"] = False
                rowdata["__new__"] = False
                rowdata["__deleted__"] = False
                self.rows_all[idx] = rowdata
                self.rows_current.append(rowdata)
                self.idx_all.append(idx)
                self.iterator_index += 1
            else:
                self.row_iterator = None
        if self.is_query:
            if (self.row_count != self.iterator_index + 1):
                self.row_count = self.iterator_index + 1
                self.NotifyViewChange(rows_before)


    def GetValue(self, row, col):
        value = None
        if row < self.row_count:
            self.SeekToRow(row)
            if row < len(self.rows_current):
                value = self.rows_current[row][self.columns[col]["name"]]
                if type(value) is buffer:
                    value = str(value).decode("latin1")
        if value and "BLOB" == self.columns[col]["type"]:
            # Blobs need special handling, as the text editor does not
            # support control characters or null bytes.
            value = value.encode("unicode-escape")
        return value if value is not None else ""


    def GetRow(self, row):
        """Returns the data dictionary of the specified row."""
        value = None
        if row < self.row_count:
            self.SeekToRow(row)
            if row < len(self.rows_current):
                value = self.rows_current[row]
        return value


    def SetValue(self, row, col, val):
        if not (self.is_query) and (row < self.row_count):
            accepted = False
            col_value = None
            if "INTEGER" == self.columns[col]["type"]:
                if not val: # Set column to NULL
                    accepted = True
                else:
                    try:
                        # Allow user to enter a comma for decimal separator.
                        valc = val.replace(",", ".")
                        col_value = float(valc) if ("." in valc) else int(val)
                        accepted = True
                    except:
                        pass
            elif "BLOB" == self.columns[col]["type"]:
                # Blobs need special handling, as the text editor does not
                # support control characters or null bytes.
                try:
                    col_value = val.decode("unicode-escape")
                    accepted = True
                except: # Entered text is not valid escaped Unicode, discard
                    pass
            else:
                col_value = val
                accepted = True
            if accepted:
                self.SeekToRow(row)
                data = self.rows_current[row]
                idx = data["__id__"]
                if not data["__new__"]:
                    if idx not in self.rows_backup:
                        # Backup only existing rows, new rows will be dropped
                        # on rollback anyway.
                        self.rows_backup[idx] = data.copy()
                    data["__changed__"] = True
                    self.idx_changed.add(idx)
                data[self.columns[col]["name"]] = col_value
                if self.View: self.View.Refresh()


    def IsChanged(self):
        """Returns whether there is uncommitted changed data in this grid."""
        result = (
            0 < len(self.idx_changed) + len(self.idx_new)
            + len(self.rows_deleted.items())
        )
        return result


    def GetChangedInfo(self):
        """Returns an info string about the uncommited changes in this grid."""
        infolist = []
        values = {
            "new": len(self.idx_new), "changed": len(self.idx_changed),
            "deleted": len(self.rows_deleted.items()),
        }
        for label, count in values.items():
            if count:
                infolist.append("%s %s row%s"
                    % (count, label, "s" if count != 1 else ""))
        return ", ".join(infolist)


    def GetAttr(self, row, col, kind):
        if not self.attrs:
            for n in ["new", "default", "row_changed", "cell_changed",
            "newblob", "defaultblob", "row_changedblob", "cell_changedblob"]:
                self.attrs[n] = wx.grid.GridCellAttr()
            for n in ["new", "newblob"]:
                self.attrs[n].SetBackgroundColour(conf.GridRowInsertedColour)
            for n in ["row_changed", "row_changedblob"]:
                self.attrs[n].SetBackgroundColour(conf.GridRowChangedColour)
            for n in ["cell_changed", "cell_changedblob"]:
                self.attrs[n].SetBackgroundColour(conf.GridCellChangedColour)
            for n in ["newblob", "defaultblob",
            "row_changedblob", "cell_changedblob"]:
                self.attrs[n].SetEditor(wx.grid.GridCellAutoWrapStringEditor())

        blob = "blob" if (self.columns[col]["type"].lower() == "blob") else ""

        attr = self.attrs["default%s" % blob]
        if row < len(self.rows_current):
            if self.rows_current[row]["__changed__"]:
                idx = self.rows_current[row]["__id__"]
                value = self.rows_current[row][self.columns[col]["name"]]
                backup = self.rows_backup[idx][self.columns[col]["name"]]
                if backup != value:
                    attr = self.attrs["cell_changed%s" % blob]
                else:
                    attr = self.attrs["row_changed%s" % blob]
            elif self.rows_current[row]["__new__"]:
                attr = self.attrs["new%s" % blob]
        attr.IncRef()
        return attr


    def InsertRows(self, row, numRows):
        """Inserts new, unsaved rows at position 0 (row is ignored)."""
        rows_before = len(self.rows_current)
        for i in range(numRows):
            # Construct empty dict from column names
            rowdata = dict((col["name"], None) for col in self.columns)
            idx = id(rowdata)
            rowdata["__id__"] = idx
            rowdata["__changed__"] = False
            rowdata["__new__"] = True
            rowdata["__deleted__"] = False
            # Insert rows at the beginning, so that they can be edited
            # immediately, otherwise would need to retrieve all rows first.
            self.idx_all.insert(0, idx)
            self.rows_current.insert(0, rowdata)
            self.rows_all[idx] = rowdata
            self.idx_new.append(idx)
        self.row_count += numRows
        self.NotifyViewChange(rows_before)


    def DeleteRows(self, row, numRows):
        """Deletes rows from a specified position."""
        if row + numRows - 1 < self.row_count:
            self.SeekToRow(row + numRows - 1)
            rows_before = len(self.rows_current)
            for i in range(numRows):
                data = self.rows_current[row]
                idx = data["__id__"]
                del self.rows_current[row]
                if idx in self.rows_backup:
                    # If row was changed, switch to its backup data
                    data = self.rows_backup[idx]
                    del self.rows_backup[idx]
                    self.idx_changed.remove(idx)
                if not data["__new__"]:
                    # Drop new rows on delete, rollback can't restore them.
                    data["__changed__"] = False
                    data["__deleted__"] = True
                    self.rows_deleted[idx] = data
                else:
                    self.idx_new.remove(idx)
                    self.idx_all.remove(idx)
                    del self.rows_all[idx]
                self.row_count -= numRows
            self.NotifyViewChange(rows_before)


    def NotifyViewChange(self, rows_before):
        """
        Notifies the grid view of a change in the underlying grid table if
        current row count is different.
        """
        if self.View:
            args = None
            rows_now = len(self.rows_current)
            if rows_now < rows_before:
                args = [
                    self,
                    wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED,
                    rows_now,
                    rows_before - rows_now
                ]
            elif rows_now > rows_before:
                args = [
                    self,
                    wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED,
                    rows_now - rows_before
                ]
            if args:
                self.View.ProcessTableMessage(wx.grid.GridTableMessage(*args))



    def AddFilter(self, col, val):
        """
        Adds a filter to the grid data on the specified column. Ignores the
        value if invalid for the column (e.g. a string for an integer column).

        @param   col   column index
        @param   val   a simple value for filtering. For numeric columns, the
                       value is matched exactly, and for text columns,
                       matched by substring.
        """
        accepted_value = None
        if "INTEGER" == self.columns[col]["type"]:
            try:
                # Allow user to enter a comma for decimal separator.
                accepted_value = float(val.replace(",", ".")) \
                                 if ("." in val or "," in val) \
                                 else int(val)
            except ValueError:
                pass
        else:
            accepted_value = val
        if accepted_value is not None:
            self.filters[col] = accepted_value
            self.Filter()


    def RemoveFilter(self, col):
        """Removes filter on the specified column, if any."""
        if col in self.filters:
            del self.filters[col]
        self.Filter()


    def ClearFilter(self, refresh=True):
        """Clears all added filters."""
        self.filters.clear()
        if refresh:
            self.Filter()


    def ClearSort(self, refresh=True):
        """Clears current sort."""
        self.sort_column = None
        if refresh:
            self.rows_current[:].sort(
                key=lambda x: self.idx_all.index(x["__id__"])
            )
            if self.View:
                self.View.ForceRefresh()


    def Filter(self):
        """
        Filters the grid table with the currently added filters.
        """
        self.SeekToRow(self.row_count - 1)
        rows_before = len(self.rows_current)
        del self.rows_current[:]
        for idx in self.idx_all:
            row = self.rows_all[idx]
            if not row["__deleted__"] and self._is_row_unfiltered(row):
                self.rows_current.append(row)
        if self.sort_column is not None:
            pass#if self.View: self.View.Fit()
        else:
            self.sort_ascending = not self.sort_ascending
            self.SortColumn(self.sort_column)
        self.NotifyViewChange(rows_before)


    def SortColumn(self, col):
        """
        Sorts the grid data by the specified column, reversing the previous
        sort order, if any.
        """
        self.SeekToRow(self.row_count - 1)
        self.sort_ascending = not self.sort_ascending
        self.sort_column = col
        compare = cmp
        if 0 <= col < len(self.columns):
            col_name = self.columns[col]["name"]
            compare = lambda a, b: cmp(a[col_name], b[col_name])
        self.rows_current.sort(cmp=compare, reverse=self.sort_ascending)
        if self.View:
            self.View.ForceRefresh()


    def SaveChanges(self):
        """
        Saves the rows that have been changed in this table. Undo information
        is destroyed.
        """
        # Save all existing changed rows
        for idx in self.idx_changed.copy():
            row = self.rows_all[idx]
            self.db.update_row(self.table, row, self.rows_backup[idx])
            row["__changed__"] = False
            self.idx_changed.remove(idx)
            del self.rows_backup[idx]
        # Save all newly inserted rows
        pk = [c["name"] for c in self.columns if c["pk"]][0]
        for idx in self.idx_new[:]:
            row = self.rows_all[idx]
            row[pk] = self.db.insert_row(self.table, row)
            row["__new__"] = False
            self.idx_new.remove(idx)
        # Deleted all newly deleted rows
        for idx, row in self.rows_deleted.copy().items():
            self.db.delete_row(self.table, row)
            del self.rows_deleted[idx]
            del self.rows_all[idx]
            self.idx_all.remove(idx)
        if self.View: self.View.Refresh()


    def UndoChanges(self):
        """Undoes the changes made to the rows in this table."""
        rows_before = len(self.rows_current)
        # Restore all changed row data from backup
        for idx in self.idx_changed.copy():
            row = self.rows_backup[idx]
            row["__changed__"] = False
            self.rows_all[idx].update(row)
            self.idx_changed.remove(idx)
            del self.rows_backup[idx]
        # Discard all newly inserted rows
        for idx in self.idx_new[:]:
            row = self.rows_all[idx]
            del self.rows_all[idx]
            if row in self.rows_current: self.rows_current.remove(row)
            self.idx_new.remove(idx)
            self.idx_all.remove(idx)
        # Undelete all newly deleted items
        for idx, row in self.rows_deleted.items():
            row["__deleted__"] = False
            del self.rows_deleted[idx]
            if self._is_row_unfiltered(row):
                self.rows_current.append(row)
            self.row_count += 1
        self.NotifyViewChange(rows_before)
        if self.View: self.View.Refresh()


    def _is_row_unfiltered(self, rowdata):
        """
        Returns whether the row is not filtered out by the current filtering
        criteria, if any.
        """
        is_unfiltered = True
        for col, filter_value in self.filters.items():
            column_data = self.columns[col]
            if "INTEGER" == column_data["type"]:
                is_unfiltered &= (filter_value == rowdata[column_data["name"]])
            elif "TEXT" == column_data["type"]:
                str_value = (rowdata[column_data["name"]] or "").lower()
                is_unfiltered &= str_value.find(filter_value.lower()) >= 0
        return is_unfiltered



class ExecuteThread(threading.Thread):
    """
    A thread for executing a database query and yielding its results. Can
    be used as an iterator.
    """

    """Number of rows retrieved in one cycle."""
    CHUNK_SIZE = 50

    def __init__(self, db, sql, params=None):
        """
        Creates and starts a new execution thread.

        @param   db      SkypeDatabase instance
        @param   sql     SQL query to execute
        @param   params  execution parameters, if any
        """
        threading.Thread.__init__(self)
        self.daemon = True # Daemon threads do not keep application running
        self._db = db
        self._cursor = None
        self._sql = sql
        self._params = params
        self._event_next = threading.Event()
        self._rows = Queue.Queue()
        self._running = False
        self.start()


    def run(self):
        """Runs the execution thread, retrieving in chunks until all done."""
        self._running = True
        self._cursor = self._db.execute(self._sql, self._params or [])
        while self._running:
            self._event_next.wait()
            self._event_next.clear()
            count = 0
            while self._cursor and count < self.CHUNK_SIZE:
                try:
                    row = self._cursor.next()
                    self._rows.put(row)
                    count += 1
                except StopIteration:
                    self._cursor = None
                    self._rows.put(None)
                    self._running = False


    def __iter__(self):
        return self


    def next(self):
        """
        Returns the next row from the query, waking the execution thread and
        waiting until more has been retrieved if necessary, or raises
        StopIteration if no more rows.
        """
        if not self._rows.qsize():
            self._event_next.set()
        row = self._rows.get()
        if row == None:
            raise StopIteration()
        return row



class MessageParser(object):
    """A simple Skype message parser."""

    """
    Maximum line width in characters for text output.
    """
    TEXT_MAXWIDTH = 79

    """HTML entities in the body that will be replaced."""
    ENTITIES = {
        "&apos;": "'" # "&amp;": "&",
    }

    """Regex for replacing emoticon tags with text emoticons."""
    EMOTICON_RGX = re.compile(
        "<ss[^>]*>([^>]+)<\/ss>", re.IGNORECASE
    )

    """Regex replacement for emoticon tags."""
    EMOTICON_REPL = lambda self, m: m.group(1)

    """Regex for replacing low bytes unparseable in XML (\x00 etc)."""
    SAFEBYTE_RGX = re.compile("[\x00-\x08,\x0B-\x0C,\x0E-x1F,\x7F]")

    """Regex for finding long words to break."""
    BREAKLONG_RGX = re.compile("([^\s-]{%d})" % 120)

    """Regex replacement for low bytes unparseable in XML (\x00 etc)."""
    SAFEBYTE_REPL = lambda self, m: m.group(0).encode("unicode-escape")

    """Mapping known failure reason codes to """
    FAILURE_REASONS = {"1": "Failed", "4": "Not enough Skype Credit."}

    """HTML template for quote elements in body."""
    HTML_QUOTE_TEMPLATE = "<table cellpadding='0' cellspacing='0'><tr>" \
                            "<td valign='top'>" \
                              "<font color='%(grey)s' size='7'>&quot;|</font>" \
                            "</td><td><br />" \
                              "<font color='%(grey)s'>{EMDASH} </font></td>" \
                          "</tr></table>" % {"grey": conf.HistoryGreyColour}

    """Export HTML template for quote elements in body."""
    HTML_QUOTE_TEMPLATE_EXPORT = "<table class='quote'><tr>" \
                                    "<td><span>&#8223;</span></td>" \
                                    "<td><br /><span class='grey'>" \
                                        "{EMDASH} </span></td>" \
                                 "</tr></table>"


    def __init__(self, db):
        """
        @param   db             SkypeDatabase instance for additional queries
        """
        self.db = db
        self.dc = wx.MemoryDC()
        self.dc.SetFont(wx.Font(8, wx.SWISS, wx.NORMAL, wx.NORMAL,
            face=conf.HistoryFontName)
        )
        self.textwrapper = textwrap.TextWrapper(width=self.TEXT_MAXWIDTH,
            expand_tabs=False, replace_whitespace=False,
            break_long_words=False, break_on_hyphens=False
        )


    def parse(self, message, rgx_highlight=None, html=None, text=None):
        """
        Parses the specified Skype message and returns the message body as DOM
        or HTML.

        @param   message        message data dict
        @param   rgx_highlight  regex for finding text to highlight, if any
        @param   html           if set, returned value is an assembled HTML
                                string instead of a DOM element, argument
                                contains data for wrapping long words, as:
                                {"w": pixel width}. Negative or zero width
                                will skip wrapping.
        @param   text           if set, returned value is a plaintext
                                representation of the message body, argument
                                can specify to not wrap lines, as:
                                {"wrap": False}. By default lines are wrapped.
        @return                 xml.etree.cElementTree.Element containing
                                message body, with "xml" as the root tag and
                                any number of subtags:
                                (a|b|quote|quotefrom|msgstatus)
                                , or an HTML string if html specified
        """
        result = None
        dom = None
        if "dom" in message:
            dom = message["dom"] # Cached DOM already exists
        if not dom:
            body = message["body_xml"] or ""

            for entity, value in self.ENTITIES.items():
                body = body.replace(entity, value)
            # Stripping out emoticon tags with regex works 100% reliably and is
            # easier than replacing them in the DOM.
            body = self.EMOTICON_RGX.sub(
                (self.EMOTICON_REPL), (body.encode("utf-8"))
            )
            #print message["body_xml"], body
            try:
                dom = xml.etree.cElementTree.fromstring(
                    "<xml>%s</xml>" % body
                )
            except Exception, e:
                body = self.SAFEBYTE_RGX.sub(self.SAFEBYTE_REPL, body)
                try:
                    dom = xml.etree.cElementTree.fromstring(
                        "<xml>%s</xml>" % body
                    )
                except Exception, e:
                    dom = xml.etree.cElementTree.fromstring("<xml></xml>")
                    main.log("Error parsing message %s, body \"%s\" (%s).", 
                        message["id"], body, e
                    )

            if MESSAGES_TYPE_SMS == message["type"]:
                # SMS body can be plaintext, or can be XML. Relevant tags:
                # <sms alt="It's hammer time."><status>6</status>
                # <failurereason>0</failurereason><targets>
                # <target status="6">+555011235</target></targets></sms>
                status_text = " SMS"
                if dom.find("sms"):
                    # Body is XML data
                    body = dom.find("sms").get("alt")
                else:
                    # Body is plaintext message
                    body = body
                status = dom.find("*/failurereason")
                if status is not None and status.text in self.FAILURE_REASONS:
                    status_text += ": %s" % self.FAILURE_REASONS[status.text]
                dom.clear()
                elm_stat = xml.etree.cElementTree.SubElement(dom, "msgstatus")
                elm_stat.text = status_text
                elm_stat.tail = body
            elif MESSAGES_TYPE_FILE == message["type"]:
                transfers = self.db.get_transfers()
                files = dict([(i["chatmsg_index"], i) for i in transfers
                    if i["chatmsg_guid"] == message["guid"]
                ])
                if not files:
                    # No rows in Transfers, try to find data from message body
                    # and create replacements for Transfers fields
                    for f in dom.findall("*/file"):
                        files[int(f.get("index"))] = {"filename": f.text,
                            "filepath": "", "filesize": f.get("size"),
                            "partner_handle": message["author"],
                            "starttime": message["timestamp"],
                            "type": (TRANSFER_TYPE_OUTBOUND 
                                     if message["author"] == self.db.id
                                     else TRANSFER_TYPE_INBOUND)
                        }
                message["__files"] = files.values()
                dom.clear()
                dom.text = "Sent file" + (len(files) > 1 and "s " or " ")
                a = None
                for i in sorted(files.keys()):
                    f = files[i]
                    if len(dom) > 0:
                        a.tail = ", "
                    a = xml.etree.cElementTree.SubElement(dom, "a", {
                        "href": self.path_to_url(f["filepath"] or f["filename"])
                    })
                    a.text = f["filename"]
                if a is not None:
                    a.tail = "."
            elif MESSAGES_TYPE_CONTACTS == message["type"]:
                self.db.get_contacts()
                contacts = sorted([self.db.get_contact_name(i.get("f"))
                    for i in dom.findall("*/c")
                ])
                dom.clear()
                dom.text = "Sent contact" + (len(contacts) > 1 and "s " or " ")
                for i in contacts:
                    if len(dom) > 0:
                        b.tail = ", "
                    b = xml.etree.cElementTree.SubElement(dom, "b")
                    b.text = i["name"] if type(i) is dict else i
                b.tail = "."
            elif MESSAGES_TYPE_PARTICIPANTS == message["type"]:
                participants = sorted([self.db.get_contact_name(i)
                    for i in message["identities"].split(" ")
                ])
                dom.clear()
                dom.text = "Added "
                for i in participants:
                    if len(dom) > 0:
                        b.tail = ", "
                    b = xml.etree.cElementTree.SubElement(dom, "b")
                    b.text = i["name"] if type(i) is dict else i
                b.tail = "."
            elif MESSAGES_TYPE_TOPIC == message["type"]:
                if dom.text:
                    dom.text = \
                        "Changed the conversation topic to \"%s\"." % dom.text
                    if not dom.text.endswith("."):
                        dom.text += "."
                else:
                    dom.text = "Changed the conversation picture."
            elif MESSAGES_TYPE_CALL == message["type"]:
                dom.clear()
                elm_stat = xml.etree.cElementTree.SubElement(dom, "msgstatus")
                elm_stat.text = " Call"
            elif MESSAGES_TYPE_CALL_END == message["type"]:
                dom.clear()
                elm_stat = xml.etree.cElementTree.SubElement(dom, "msgstatus")
                elm_stat.text = " Call ended"
            elif MESSAGES_TYPE_LEAVE == message["type"]:
                dom.text = "%s has left the conversation." \
                            % message["from_dispname"]
            elif MESSAGES_TYPE_SHARE_DETAIL == message["type"]:
                names_to = [self.db.get_contact_name(i)
                    for i in message["identities"].split(" ")
                ]
                dom.text = "Has shared contact details with "
                for i in names_to:
                    if len(dom) > 0:
                        b.tail = ", "
                    b = xml.etree.cElementTree.SubElement(dom, "b")
                    b.text = i
                b.tail = "."
            elif MESSAGES_TYPE_MESSAGE == message["type"]:
                pass

            # Process Skype message quotation tags, assembling a simple
            # <quote>text<special>footer</special></quote> element.
            # element
            #print "b4 quotez"
            for quote in dom.findall("quote"):
                #print "DOING QUOTE"
                quote.text = quote.text or ""
                for i in quote.findall("legacyquote"):
                    # <legacyquote> contains preformatted timestamp and author
                    if i.tail:
                        quote.text += i.tail
                    quote.remove(i)
                footer = quote.get("authorname") or ""
                if quote.get("timestamp"):
                    footer += (", %s" if footer else "%s") % \
                        datetime.datetime.fromtimestamp(
                            int(quote.get("timestamp"))
                        ).strftime("%d.%m.%Y %H:%M")
                if footer:
                    elm_sub = xml.etree.cElementTree.SubElement(quote, "quotefrom")
                    elm_sub.text = footer
                quote.attrib.clear() # Drop the numerous data attributes
            message["dom"] = dom # Cache DOM
        if dom is not None and (rgx_highlight or html):
            # Create a copy, as we will modify the contents
            dom = copy.deepcopy(dom)
        if dom is not None and rgx_highlight:

            def highlight(match):
                b = xml.etree.cElementTree.Element("b")
                b.text = match.group(0)
                return xml.etree.cElementTree.tostring(b)

            parent_map = dict(
                (c, p) for p in dom.getiterator() for c in p
            )
            rgx_highlight_split = re.compile("<b>")
            # Highlight substrings in <b>-tags
            for i in dom.getiterator():
                if "b" == i.tag:
                    continue
                for j, t in [(0, i.text), (1, i.tail)]:
                    if t:
                        highlighted = rgx_highlight.sub(
                            lambda x: "<b>%s<b>" % x.group(0), t)
                        parts = rgx_highlight_split.split(highlighted)
                        if len(parts) > 1:
                            if j:
                                i.tail = ""
                                index_insert = list(parent_map[i]).index(i) + 1
                            else:
                                i.text = ""
                                index_insert = 0
                            b = None
                            for i_part, part in enumerate(parts):
                                if i_part % 2:
                                    # Highlighted text, wrap in <b>
                                    b = xml.etree.cElementTree.Element("b")
                                    b.text = part
                                    if j: # Processing i.tail
                                        parent_map[i].insert(index_insert, b)
                                    else: # Processing i.text
                                        i.insert(index_insert, b)
                                    index_insert += 1
                                else:
                                    # Non-highlighted text, append to tail/text
                                    if j: # Processing i.tail
                                        if b is not None: #
                                            b.tail = part
                                        else:
                                            i.tail = (i.tail or "") + part
                                    else: # Processing i.text
                                        if b is not None: #
                                            b.tail = part
                                        else:
                                            i.text = part

        if dom is not None and html is not None:
            greytag, greyattr, greyval = "font", "color", conf.HistoryGreyColour
            if html.get("export", False):
                greytag, greyattr, greyval = "span", "class", "grey"
            for elem in dom.getiterator():
                index = 0
                for subelem in elem:
                    if "quote" == subelem.tag:
                        elem_quotefrom = subelem.find("quotefrom")
                        # Replace quote tags with a formatted subtable
                        template = self.HTML_QUOTE_TEMPLATE
                        if html.get("export", False):
                            template = self.HTML_QUOTE_TEMPLATE_EXPORT
                        table = xml.etree.cElementTree.fromstring(template)
                        # Select last, content cell
                        cell = table.findall("*/td")[-1]
                        cell.find(greytag).text += elem_quotefrom.text
                        subelem.remove(elem_quotefrom)
                        cell.text = subelem.text
                        # Insert all children before the last font element
                        len_orig = len(cell)
                        [cell.insert(len(cell) - len_orig, i) for i in subelem]
                        table.tail = subelem.tail
                        elem[index] = table # Replace quote element in parent
                    elif "msgstatus" == subelem.tag:
                        subelem.tag = greytag
                        subelem.set(greyattr, greyval)
                        # Add whitespace before next content
                        subelem.tail = " " + (subelem.tail or "")
                    elif "a" == subelem.tag:
                        subelem.set("target", "_blank")
                    index += 1
                for name, value in [("text", elem.text), ("tail", elem.tail)]:
                    if value:
                        value_new = wx.lib.wordwrap.wordwrap(
                            value, html["w"], self.dc
                        ) if (html.get("w", 0) > 0) \
                          else self.BREAKLONG_RGX.sub("\\1 ", value)
                        setattr(elem, name, value_new)
            try:
                # Discard <?xml ..?><xml> tags from start and </xml> from end
                result = xml.etree.cElementTree.tostring(dom, "UTF-8")[44:-6]
                # emdash workaround, cElementTree won't handle unknown entities
                result = result.replace("{EMDASH}", "&mdash;") \
                               .replace("\n", "<br />")
            except Exception, e:
                self.db.sota = dom
                raise e
        elif dom is not None and text is not None:
            result = self.dom_to_text(dom)
            if not isinstance(text, dict) or text.get("wrap", True):
                linelists = map(self.textwrapper.wrap, result.split("\n"))
                ll = "\n".join(i[0] if i else "" for i in linelists)
                # Force DOS linefeeds
                result = re.sub("([^\r])\n", lambda m: m.group(1) + "\r\n", ll)
        else:
            result = dom

        return result


    def dom_to_text(self, dom):
        fulltext = ""
        to_skip = {} # {element to skip: True, }
        for elem in dom.getiterator():
            text = elem.text or ""
            tail = elem.tail or ""
            subitems = []
            if "quote" == elem.tag:
                text = "\"" + text
                subitems = elem.getchildren()
            elif "quotefrom" == elem.tag:
                text = "\"\r\n%s\r\n" % text
            elif "msgstatus" == elem.tag:
                text = "[%s]\r\n" % text.strip()
            if text:
                fulltext += text
            for i in subitems:
                fulltext += self.dom_to_text(i)
                to_skip[i] = True
            if tail:
                fulltext += tail
        return fulltext


    @classmethod
    def path_to_url(cls, path, encoding="utf-8"):
        """Returns the local file path as a URL."""
        if type(path) is unicode:
            path = path.encode(encoding)
        url = urllib.pathname2url(path)
        url = "file:%s%s" % ("" if url.startswith("///") else "///" , url)
        return url



def detect_databases():
    """
    Tries to detect Skype database files on the current computer, looking
    under "Documents and Settings", and other potential locations.

    @yield   a list of detected database paths
    """

    # First, search local directory.
    search_paths = [os.getcwd()]
    for search_path in search_paths:
        main.log("Looking for Skype databases under %s.", search_path)
        for root, dirs, files in os.walk(search_path):
            for f in files:
                if f.lower().endswith(".db"):
                    yield os.path.join(root, f)

    # Then search user home directories, starting from current user's home.
    c = os.getenv("SystemDrive") or "C:"
    home_folder = os.getenv("USERPROFILE") or os.getenv("HOME") or ""
    search_paths = [
        home_folder,
        "%s\\Documents and Settings" % c, # Windows 2000, XP, 2003
        "%s\\Users" % c,                  # Windows Vista, 7
        "/Users",                         # MacOSX
        "/home"                           # Linux
    ]
    for search_path in filter(os.path.exists, search_paths):
        main.log("Looking for Skype databases under %s.", search_path)
        for root, dirs, files in os.walk(search_path):
            if "application data" == os.path.basename(root).lower():
                # Prune other applications from dirlist if we're under
                # "Application Data" in Windows, to lessen time overhead.
                filtered = filter(lambda x: "skype" == x.lower(), dirs)
                del dirs[:]
                dirs.extend(filtered)
            for f in files:
                if "main.db" == f.lower():
                    yield os.path.join(root, f)



def find_databases(folder):
    """
    Yields a list of all Skype databases under the specified folder.
    """
    for root, dirs, files in os.walk(folder):
        db_files = filter(lambda x: x.lower().endswith(".db"), files)
        for filename in db_files:
            yield os.path.join(root, filename)



"""
Information on Skype database tables (unreliable, mostly empirical):

Accounts       - one row with user profile information
Alerts         - alerts from Skype payments, Facebook etc
CallMembers    - participants in Skype calls
Calls          - Skype phone calls
ChatMembers    - may be unused, migration from old *.dbb files on Skype upgrade
Chats          - may be unused, migration from old *.dbb files on Skype upgrade
ContactGroups  - user-defined contact groups
Contacts       - all Skype contacts, also including plain phone numbers
Conversations  - all conversations, both single and group chats
DbMeta         - Skype internal metainformation
LegacyMessages - seems unused
Messages       - all conversation messages, including Skype internals
Participants   - conversation participants
SMSes          - SMSes sent from Skype, connected to Messages. Can have
                 several rows per one message
Transfers      - file transfers, connected to Messages
Videos         - video calls, connected to Calls
Voicemails     - voicemail information


Information collected on some table fields (an incomplete list):

Contacts:
  about                  "About" field in profile
  assigned_phone1        1st of 3 self-assigned phone numbers per contact
  assigned_phone2        2nd of 3 self-assigned phone numbers per contact
  assigned_phone3        3rd of 3 self-assigned phone numbers per contact
  assigned_phone1_label  0: Home, 1: Office, 2: Mobile, 3: Other
  assigned_phone2_label  0: Home, 1: Office, 2: Mobile, 3: Other
  assigned_phone3_label  0: Home, 1: Office, 2: Mobile, 3: Other
  birthday               birth date as YYYYMMDD in integer field
  city                   City field in profile
  country                "Country/Region" in profile, contains 2-char code
  fullname               exists for most if not all active Skype contacts
  gender                 1: male, 2: female, NULL: undefined
  displayname            contact display name, is set also for single phone numbers
  emails                 "Email" field in profile, contains space-separated list
  homepage               "Website" field in profile
  languages              "Language" field in profile, contains 2-char code
  mood_text              plaintext of the "Mood" field in profile
  phone_home             "Home phone" field in profile
  phone_office           "Office phone" field in profile
  phone_mobile           "Mobile phone" field in profile
  province               "State/Province" field in profile
  pstnnumber             contains the number for single phone number contacts
  rich_mood_text         "Mood" field in profile, can contain XML
                         (e.g. flag/video tags)
  skypename              skype account name, blank for added pstnnumbers

Conversations:
  type            1: single, 2: group
  identity        unique global identifier, skypename of other correspondent
                  for single chats and a complex value for multichats
  displayname     name of other correspondent for single chats, and
                  given/assigned name for multichats
  meta_topic      topic set to the conversation


Messages:
  chatmsg_type    NULL: (type 4, 30, 39, 50, 53, 68, 110)
                  1:    add participant (type 10),
                        identities has space-separated list)
                  2:    type 10: add participant (identities has
                        space-separated list)
                        type 100: notice that a file transfer was offered
                  3:    ordinary message (type 61)
                  4:    "%name has left" (type 13)
                  5:    set conversation topic (type 2)
                  6:    file accepting (type 100)
                  7:    file transfer, SMS, or "/me laughs" (type 60, 64, 68)
                        if transfer, Messages.guid == Transfers.chatmsg_guid
                  8:    sent contacts (body_xml has contacts XML) (type 63)
                  11:   "%name removed %name from this conversation." (type 12)
                  15:   "%name% has changed the conversation picture" (type 2)
                  18:   different call/contact things (type 30, 39, 51)

  type            2:    set topic or picture (chatmsg_type 5, 15)
                  4:    "#author created a group conversation with #identities.
                        Show group conversation" (chatmsg_type NULL)
                  10:   added participant (chatmsg_type 1, 2)
                  12:   sent contacts (chatmsg_type 11)
                  13:   "%name has left" (chatmsg_type 4)
                  30:   call (chatmsg_type 18, NULL). body_xml can have
                        participants XML.
                  39:   call ended (chatmsg_type 18, NULL)
                  50:   intro message, "wish to add you to my contacts"
                        (chatmsg_type NULL). body_xml can have display message.
                        Seems received when one or other adds on request?
                  51:   "%name has shared contact details with %myname."
                        (chatmsg_type 18)
                  53:   unknown and undetectable (just 1 in encountered
                        databases, with NULL chatmsg_type and pretty NULL
                        altogether). Might be related to a contact changing
                        their account.
                  60:   various info messages (chatmsg_type 7),
                        e.g. "has sent a file to x, y, ..", or "/me laughs"
                  61:   ordinary message (chatmsg_type 7)
                  63:   sent contacts (chatmsg_type 8)
                  64:   SMS (chatmsg_type 7)
                  68:   file transfer (chatmsg_type 7)
                  100:  file sending and accepting (chatmsg_type 2, 6)
                  110:  birthday alert (chatmsg_type NULL)

SMSes:
  chatmsg_id      if set, refers to the Messages.id entry showing this SMS
  failurereason   0:    no failure
                  1:    general
                  4:    not enough Skype credit
  status          3:    unknown
                  5:    unknown
                  6:    delivered
                  7:    unknown
                  8:    failed

Transfers:
  chatmsg_guid    if set, refers to Messages.guid WHERE chatmsg_type = 7
  chatmsg_index   index of the file in the chat message (for batch transfers)
  convo_id        if set, refers to the Conversations entry
  failurereason   0:    cancelled
                  2:    delivered
                  5:    sending failed
                  8:    sending failed
                  10:   file isn't available
  status          7:    cancelled
                  8:    delivered
                  9:    failed
                  10:   file isn't available
                  11:   file isn't available on this computer
                  12:   delivered
  type            1:    outbound
                  2:    inbound


Videos:
  convo_id        foreign key on Calls.id

"""
