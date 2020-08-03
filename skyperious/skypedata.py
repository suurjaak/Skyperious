# -*- coding: utf-8 -*-
"""
Skype database access and message parsing functionality.

------------------------------------------------------------------------------
This file is part of Skyperious - Skype chat history tool.
Released under the MIT License.

@author      Erki Suurjaak
@created     26.11.2011
@modified    02.08.2020
------------------------------------------------------------------------------
"""
import cgi
import collections
import copy
import cStringIO
import datetime
import logging
import math
import os
import re
import sqlite3
import shutil
import sys
import textwrap
import time
import urllib
from xml.etree import cElementTree as ElementTree

try: import wx # For avatar bitmaps in GUI program
except ImportError: pass

from . lib import util
from . lib import wordcloud
from . lib.vendor import step

from . import conf
from . import emoticons
from . import templates


CHATS_TYPE_SINGLE          =   1 # 1:1 chat
CHATS_TYPE_GROUP           =   2 # 1:n chat
CHATS_TYPE_CONFERENCE      =   4 # video conference
CHATS_TYPENAMES = {
    CHATS_TYPE_SINGLE    : "Single",
    CHATS_TYPE_GROUP     : "Group",
    CHATS_TYPE_CONFERENCE: "Conference"
}
MESSAGE_REMOVED_TEXT = "This message has been removed."
MESSAGE_TYPE_TOPIC        =   2 # Changed chat topic or picture
MESSAGE_TYPE_GROUP        =   4 # Created group conversation
MESSAGE_TYPE_UPDATE_DONE  =   8 # Updated, can now participate in this chat
MESSAGE_TYPE_UPDATE_NEED  =   9 # Needs update to participate in this chat
MESSAGE_TYPE_PARTICIPANTS =  10 # Added participants to chat
MESSAGE_TYPE_REMOVE       =  12 # Removed participants from chat
MESSAGE_TYPE_LEAVE        =  13 # Contact left the chat
MESSAGE_TYPE_CALL         =  30 # Started Skype call
MESSAGE_TYPE_CALL_END     =  39 # Skype call ended
MESSAGE_TYPE_INTRO        =  50 # Intro message, "wish to add to my contacts"
MESSAGE_TYPE_SHARE_DETAIL =  51 # Sharing contact details
MESSAGE_TYPE_BLOCK        =  53 # Blocking contacts
MESSAGE_TYPE_INFO         =  60 # Info message like "/me is planting corn"
MESSAGE_TYPE_MESSAGE      =  61 # Ordinary message
MESSAGE_TYPE_CONTACTS     =  63 # Sent contacts
MESSAGE_TYPE_SMS          =  64 # SMS message
MESSAGE_TYPE_FILE         =  68 # File transfer
MESSAGE_TYPE_SHARE_VIDEO  =  70 # Video sharing
MESSAGE_TYPE_BIRTHDAY     = 110 # Birthday notification
MESSAGE_TYPE_SHARE_PHOTO  = 201 # Photo sharing
MESSAGE_TYPE_SHARE_VIDEO2 = 253 # Video sharing
MESSAGE_TYPES_BASE = (2, 4, 10, 12, 13, 30, 39, 50, 51, 53, 60, 61, 63, 64, 68, 70, 201)
MESSAGE_TYPES_MESSAGE = (2, 4, 8, 9, 10, 12, 13, 30, 39, 50, 51, 53, 60, 61, 63, 64, 68, 70, 201)
MESSAGE_TYPES_STATS = (2, 4, 10, 12, 13, 50, 51, 53, 60, 61, 63, 64, 68, 70, 201)
CHATMSG_TYPE_PARTICIPANTS  =  1 # Added participants to chat (type 10)
CHATMSG_TYPE_PARTICIPANTS2 =  2 # Added participants to chat; or file transfer notice (type 10, 100)
CHATMSG_TYPE_MESSAGE       =  3 # Ordinary message (type 61)
CHATMSG_TYPE_LEAVE         =  4 # Contact left the chat (type 13)
CHATMSG_TYPE_TOPIC         =  5 # Changed chat topic (type 2)
CHATMSG_TYPE_ACCEPT        =  6 # Accepted file transfer (type 100)
CHATMSG_TYPE_SPECIAL       =  7 # File transfer, SMS, "/me laughs" or others (type 60, 64, 68, 201)
CHATMSG_TYPE_CONTACTS      =  8 # Sent contacts (type 63)
CHATMSG_TYPE_REMOVE        = 11 # Removed participants from chat (type 12)
CHATMSG_TYPE_PICTURE       = 15 # Changed chat picture (type 2)
CHATMSG_TYPE_SPECIAL2      = 18 # Calls/contacts/transfers (type 30, 39, 51, 68)
TRANSFER_TYPE_OUTBOUND     =  1 # Transfer sent by partner_handle
TRANSFER_TYPE_INBOUND      =  2 # Transfer sent to partner_handle
CONTACT_FIELD_TITLES = {
    "displayname" : "Display name",
    "skypename"   : "Skype Name",
    "province"    : "State/Province",
    "city"        : "City",
    "pstnnumber"  : "Phone",
    "phone_home"  : "Home phone",
    "phone_office": "Office phone",
    "phone_mobile": "Mobile phone",
    "homepage"    : "Website",
    "emails"      : "Emails",
    "about"       : "About me",
    "mood_text"   : "Mood",
    "country"     : "Country/Region",
}
ACCOUNT_FIELD_TITLES = {
    "fullname"           : "Full name",
    "given_displayname"  : "Given display name",
    "skypename"          : "Skype name",
    "mood_text"          : "Mood",
    "phone_mobile"       : "Mobile phone",
    "phone_home"         : "Home phone",
    "phone_office"       : "Office phone",
    "emails"             : "E-mails",
    "country"            : "Country",
    "province"           : "Province",
    "city"               : "City",
    "homepage"           : "Website",
    "gender"             : "Gender",
    "birthday"           : "Birth date",
    "languages"          : "Languages",
    "nrof_authed_buddies": "Contacts",
    "about"              : "About me",
    "skypeout_balance"   : "SkypeOut balance",
}
AUTHORS_SPECIAL = ["sys"] # Used by Skype for system messages

logger = logging.getLogger(__name__)


class SkypeDatabase(object):
    """Access to a Skype database file."""

    """SQL CREATE statements for Skype tables."""
    CREATE_STATEMENTS = {
        "accounts":            "CREATE TABLE Accounts (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, status INTEGER, pwdchangestatus INTEGER, logoutreason INTEGER, commitstatus INTEGER, suggested_skypename TEXT, skypeout_balance_currency TEXT, skypeout_balance INTEGER, skypeout_precision INTEGER, skypein_numbers TEXT, subscriptions TEXT, cblsyncstatus INTEGER, contactssyncstatus INTEGER, offline_callforward TEXT, chat_policy INTEGER, skype_call_policy INTEGER, pstn_call_policy INTEGER, avatar_policy INTEGER, buddycount_policy INTEGER, timezone_policy INTEGER, webpresence_policy INTEGER, phonenumbers_policy INTEGER, voicemail_policy INTEGER, authrequest_policy INTEGER, ad_policy INTEGER, partner_optedout TEXT, service_provider_info TEXT, registration_timestamp INTEGER, nr_of_other_instances INTEGER, partner_channel_status TEXT, flamingo_xmpp_status INTEGER, federated_presence_policy INTEGER, liveid_membername TEXT, roaming_history_enabled INTEGER, cobrand_id INTEGER, shortcircuit_sync INTEGER, signin_name TEXT, read_receipt_optout INTEGER, hidden_expression_tabs TEXT, owner_under_legal_age INTEGER, type INTEGER, skypename TEXT, pstnnumber TEXT, fullname TEXT, birthday INTEGER, gender INTEGER, languages TEXT, country TEXT, province TEXT, city TEXT, phone_home TEXT, phone_office TEXT, phone_mobile TEXT, emails TEXT, homepage TEXT, about TEXT, profile_timestamp INTEGER, received_authrequest TEXT, displayname TEXT, refreshing INTEGER, given_authlevel INTEGER, aliases TEXT, authreq_timestamp INTEGER, mood_text TEXT, timezone INTEGER, nrof_authed_buddies INTEGER, ipcountry TEXT, given_displayname TEXT, availability INTEGER, lastonline_timestamp INTEGER, capabilities BLOB, avatar_image BLOB, assigned_speeddial TEXT, lastused_timestamp INTEGER, authrequest_count INTEGER, assigned_comment TEXT, alertstring TEXT, avatar_timestamp INTEGER, mood_timestamp INTEGER, rich_mood_text TEXT, synced_email BLOB, set_availability INTEGER, options_change_future BLOB, msa_pmn TEXT, authorized_time INTEGER, sent_authrequest TEXT, sent_authrequest_time INTEGER, sent_authrequest_serial INTEGER, buddyblob BLOB, cbl_future BLOB, node_capabilities INTEGER, node_capabilities_and INTEGER, revoked_auth INTEGER, added_in_shared_group INTEGER, in_shared_group INTEGER, authreq_history BLOB, profile_attachments BLOB, stack_version INTEGER, offline_authreq_id INTEGER, verified_email BLOB, verified_company BLOB, uses_jcs INTEGER, forward_starttime INTEGER)",
        "alerts":              "CREATE TABLE Alerts (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, timestamp INTEGER, partner_name TEXT, is_unseen INTEGER, partner_id INTEGER, partner_event TEXT, partner_history TEXT, partner_header TEXT, partner_logo TEXT, message_content TEXT, message_footer TEXT, meta_expiry INTEGER, message_header_caption TEXT, message_header_title TEXT, message_header_subject TEXT, message_header_cancel TEXT, message_header_later TEXT, message_button_caption TEXT, message_button_uri TEXT, message_type INTEGER, window_size INTEGER, notification_id INTEGER, extprop_hide_from_history INTEGER, chatmsg_guid BLOB, event_flags INTEGER)",
        "appschemaversion":    "CREATE TABLE AppSchemaVersion (ClientVersion TEXT NOT NULL, SQLiteSchemaVersion INTEGER NOT NULL, SchemaUpdateType INTEGER NOT NULL)",
        "callhandlers":        "CREATE TABLE CallHandlers (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER)",
        "callmembers":         "CREATE TABLE CallMembers (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, identity TEXT, dispname TEXT, languages TEXT, call_duration INTEGER, price_per_minute INTEGER, price_precision INTEGER, price_currency TEXT, payment_category TEXT, type INTEGER, status INTEGER, failurereason INTEGER, sounderror_code INTEGER, soundlevel INTEGER, pstn_statustext TEXT, pstn_feedback TEXT, forward_targets TEXT, forwarded_by TEXT, debuginfo TEXT, videostatus INTEGER, target_identity TEXT, mike_status INTEGER, is_read_only INTEGER, quality_status INTEGER, call_name TEXT, transfer_status INTEGER, transfer_active INTEGER, transferred_by TEXT, transferred_to TEXT, guid TEXT, next_redial_time INTEGER, nrof_redials_done INTEGER, nrof_redials_left INTEGER, transfer_topic TEXT, real_identity TEXT, start_timestamp INTEGER, is_conference INTEGER, quality_problems TEXT, identity_type INTEGER, country TEXT, creation_timestamp INTEGER, stats_xml TEXT, is_premium_video_sponsor INTEGER, is_multiparty_video_capable INTEGER, recovery_in_progress INTEGER, fallback_in_progress INTEGER, nonse_word TEXT, nr_of_delivered_push_notifications INTEGER, call_session_guid TEXT, version_string TEXT, ip_address TEXT, is_video_codec_compatible INTEGER, group_calling_capabilities INTEGER, mri_identity TEXT, is_seamlessly_upgraded_call INTEGER, voicechannel INTEGER, video_count_changed INTEGER, is_active_speaker INTEGER, dominant_speaker_rank INTEGER, participant_sponsor TEXT, content_sharing_role INTEGER, endpoint_details TEXT, pk_status INTEGER, call_db_id INTEGER, prime_status INTEGER, light_weight_meeting_role INTEGER, capabilities INTEGER, endpoint_type INTEGER, accepted_by TEXT, is_server_muted INTEGER, admit_failure_reason INTEGER)",
        "calls":               "CREATE TABLE Calls (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, begin_timestamp INTEGER, topic TEXT, is_muted INTEGER, is_unseen_missed INTEGER, host_identity TEXT, is_hostless INTEGER, mike_status INTEGER, duration INTEGER, soundlevel INTEGER, access_token TEXT, active_members INTEGER, is_active INTEGER, name TEXT, video_disabled INTEGER, joined_existing INTEGER, server_identity TEXT, vaa_input_status INTEGER, is_incoming INTEGER, is_conference INTEGER, is_on_hold INTEGER, start_timestamp INTEGER, quality_problems TEXT, current_video_audience TEXT, premium_video_status INTEGER, premium_video_is_grace_period INTEGER, is_premium_video_sponsor INTEGER, premium_video_sponsor_list TEXT, technology INTEGER, max_videoconfcall_participants INTEGER, optimal_remote_videos_in_conference INTEGER, message_id TEXT, status INTEGER, thread_id TEXT, leg_id TEXT, conversation_type TEXT, datachannel_object_id INTEGER, endpoint_details TEXT, caller_mri_identity TEXT, member_count_changed INTEGER, transfer_status INTEGER, transfer_failure_reason INTEGER, old_members BLOB, partner_handle TEXT, partner_dispname TEXT, type INTEGER, failurereason INTEGER, failurecode INTEGER, pstn_number TEXT, old_duration INTEGER, conf_participants BLOB, pstn_status TEXT, members BLOB, conv_dbid INTEGER, is_server_muted INTEGER, forwarding_destination_type TEXT, incoming_type TEXT, onbehalfof_mri TEXT, transferor_mri TEXT, light_weight_meeting_count_changed INTEGER)",
        "chatmembers":         "CREATE TABLE ChatMembers (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, chatname TEXT, identity TEXT, role INTEGER, is_active INTEGER, cur_activities INTEGER, adder TEXT)",
        "chats":               "CREATE TABLE Chats (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, name TEXT, timestamp INTEGER, adder TEXT, type INTEGER, posters TEXT, participants TEXT, topic TEXT, activemembers TEXT, friendlyname TEXT, alertstring TEXT, is_bookmarked INTEGER, activity_timestamp INTEGER, mystatus INTEGER, passwordhint TEXT, description TEXT, options INTEGER, picture BLOB, guidelines TEXT, dialog_partner TEXT, myrole INTEGER, applicants TEXT, banned_users TEXT, topic_xml TEXT, name_text TEXT, unconsumed_suppressed_msg INTEGER, unconsumed_normal_msg INTEGER, unconsumed_elevated_msg INTEGER, unconsumed_msg_voice INTEGER, state_data BLOB, lifesigns INTEGER, last_change INTEGER, first_unread_message INTEGER, pk_type INTEGER, dbpath TEXT, split_friendlyname TEXT, conv_dbid INTEGER)",
        "contactgroups":       "CREATE TABLE ContactGroups (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, type_old INTEGER, given_displayname TEXT, nrofcontacts INTEGER, nrofcontacts_online INTEGER, custom_group_id INTEGER, type INTEGER, associated_chat TEXT, proposer TEXT, description TEXT, members TEXT, cbl_id INTEGER, cbl_blob BLOB, fixed INTEGER, keep_sharedgroup_contacts INTEGER, chats TEXT, extprop_is_hidden INTEGER, extprop_sortorder_value INTEGER, extprop_is_expanded INTEGER, given_sortorder INTEGER, abch_guid TEXT)",
        "contacts":            "CREATE TABLE Contacts (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, type INTEGER, skypename TEXT, pstnnumber TEXT, aliases TEXT, fullname TEXT, birthday INTEGER, gender INTEGER, languages TEXT, country TEXT, province TEXT, city TEXT, phone_home TEXT, phone_office TEXT, phone_mobile TEXT, emails TEXT, hashed_emails TEXT, homepage TEXT, about TEXT, avatar_image BLOB, mood_text TEXT, rich_mood_text TEXT, timezone INTEGER, capabilities BLOB, profile_timestamp INTEGER, nrof_authed_buddies INTEGER, ipcountry TEXT, avatar_timestamp INTEGER, mood_timestamp INTEGER, received_authrequest TEXT, authreq_timestamp INTEGER, lastonline_timestamp INTEGER, availability INTEGER, displayname TEXT, refreshing INTEGER, given_authlevel INTEGER, given_displayname TEXT, assigned_speeddial TEXT, assigned_comment TEXT, alertstring TEXT, lastused_timestamp INTEGER, authrequest_count INTEGER, assigned_phone1 TEXT, assigned_phone1_label TEXT, assigned_phone2 TEXT, assigned_phone2_label TEXT, assigned_phone3 TEXT, assigned_phone3_label TEXT, buddystatus INTEGER, isauthorized INTEGER, popularity_ord INTEGER, external_id TEXT, external_system_id TEXT, isblocked INTEGER, authorization_certificate BLOB, certificate_send_count INTEGER, account_modification_serial_nr INTEGER, saved_directory_blob BLOB, nr_of_buddies INTEGER, server_synced INTEGER, contactlist_track INTEGER, last_used_networktime INTEGER, authorized_time INTEGER, sent_authrequest TEXT, sent_authrequest_time INTEGER, sent_authrequest_serial INTEGER, buddyblob BLOB, cbl_future BLOB, node_capabilities INTEGER, revoked_auth INTEGER, added_in_shared_group INTEGER, in_shared_group INTEGER, authreq_history BLOB, profile_attachments BLOB, stack_version INTEGER, offline_authreq_id INTEGER, node_capabilities_and INTEGER, authreq_crc INTEGER, authreq_src INTEGER, pop_score INTEGER, authreq_nodeinfo BLOB, main_phone TEXT, unified_servants TEXT, phone_home_normalized TEXT, phone_office_normalized TEXT, phone_mobile_normalized TEXT, sent_authrequest_initmethod INTEGER, authreq_initmethod INTEGER, verified_email BLOB, verified_company BLOB, sent_authrequest_extrasbitmask INTEGER, liveid_cid TEXT, extprop_seen_birthday INTEGER, extprop_sms_target INTEGER, extprop_external_data TEXT, is_auto_buddy INTEGER, group_membership INTEGER, is_mobile INTEGER, is_trusted INTEGER, avatar_url TEXT, firstname TEXT, lastname TEXT, network_availability INTEGER, avatar_url_new TEXT, avatar_hiresurl TEXT, avatar_hiresurl_new TEXT, profile_json TEXT, profile_etag TEXT, dirblob_last_search_time INTEGER, mutual_friend_count INTEGER)",
        "contentsharings":     "CREATE TABLE ContentSharings (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, call_id INTEGER, identity TEXT, status INTEGER, sharing_id TEXT, state TEXT, failurereason INTEGER, failurecode INTEGER, failuresubcode INTEGER)",
        "conversationviews":   "CREATE TABLE ConversationViews (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, view_id INTEGER)",
        "conversations":       "CREATE TABLE Conversations (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, identity TEXT, type INTEGER, live_host TEXT, live_is_hostless INTEGER, live_call_technology INTEGER, optimal_remote_videos_in_conference INTEGER, live_start_timestamp INTEGER, live_is_muted INTEGER, max_videoconfcall_participants INTEGER, alert_string TEXT, is_bookmarked INTEGER, is_blocked INTEGER, given_displayname TEXT, displayname TEXT, local_livestatus INTEGER, inbox_timestamp INTEGER, inbox_message_id INTEGER, last_message_id INTEGER, unconsumed_suppressed_messages INTEGER, unconsumed_normal_messages INTEGER, unconsumed_elevated_messages INTEGER, unconsumed_messages_voice INTEGER, active_vm_id INTEGER, context_horizon INTEGER, consumption_horizon INTEGER, consumption_horizon__ms INTEGER, last_activity_timestamp INTEGER, active_invoice_message INTEGER, spawned_from_convo_id INTEGER, pinned_order INTEGER, creator TEXT, creation_timestamp INTEGER, my_status INTEGER, opt_joining_enabled INTEGER, opt_moderated INTEGER, opt_access_token TEXT, opt_entry_level_rank INTEGER, opt_disclose_history INTEGER, opt_history_limit_in_days INTEGER, opt_admin_only_activities INTEGER, passwordhint TEXT, meta_name TEXT, meta_topic TEXT, meta_guidelines TEXT, meta_picture BLOB, picture TEXT, is_p2p_migrated INTEGER, migration_instructions_posted INTEGER, premium_video_status INTEGER, premium_video_is_grace_period INTEGER, guid TEXT, dialog_partner TEXT, meta_description TEXT, premium_video_sponsor_list TEXT, mcr_caller TEXT, chat_dbid INTEGER, history_horizon INTEGER, history_sync_state TEXT, thread_version TEXT, consumption_horizon_set_at INTEGER, alt_identity TEXT, in_migrated_thread_since INTEGER, awareness_liveState TEXT, join_url TEXT, reaction_thread TEXT, parent_thread TEXT, consumption_horizon_rid INTEGER, consumption_horizon_crc INTEGER, consumption_horizon_bookmark INTEGER, client_id TEXT, last_synced_message_id INTEGER, last_synced_message_version INTEGER, last_synced_days INTEGER, version INTEGER, endpoint_details TEXT, extprop_profile_height INTEGER, extprop_chat_width INTEGER, extprop_chat_left_margin INTEGER, extprop_chat_right_margin INTEGER, extprop_entry_height INTEGER, extprop_windowpos_x INTEGER, extprop_windowpos_y INTEGER, extprop_windowpos_w INTEGER, extprop_windowpos_h INTEGER, extprop_window_maximized INTEGER, extprop_window_detached INTEGER, extprop_pinned_order INTEGER, extprop_new_in_inbox INTEGER, extprop_tab_order INTEGER, extprop_video_layout INTEGER, extprop_video_chat_height INTEGER, extprop_chat_avatar INTEGER, extprop_consumption_timestamp INTEGER, extprop_form_visible INTEGER, extprop_recovery_mode INTEGER, extprop_translator_enabled INTEGER, extprop_translator_call_my_lang TEXT, extprop_translator_call_other_lang TEXT, extprop_translator_chat_my_lang TEXT, extprop_translator_chat_other_lang TEXT, extprop_conversation_first_unread_emote INTEGER, datachannel_object_id INTEGER, invite_status INTEGER, highlights_follow_pending TEXT, highlights_follow_waiting TEXT, highlights_add_pending TEXT, highlights_add_waiting TEXT)",
        "datachannels":        "CREATE TABLE DataChannels (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, status INTEGER)",
        "dbmeta":              "CREATE TABLE DbMeta (key TEXT NOT NULL PRIMARY KEY, value TEXT)",
        "legacymessages":      "CREATE TABLE LegacyMessages (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER)",
        "lightweightmeetings": "CREATE TABLE LightWeightMeetings (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, call_id INTEGER, status INTEGER, state TEXT, failurereason INTEGER, failurecode INTEGER, failuresubcode INTEGER)",
        "mediadocuments":      "CREATE TABLE MediaDocuments (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, storage_document_id INTEGER, status INTEGER, doc_type INTEGER, uri TEXT, original_name TEXT, title TEXT, description TEXT, thumbnail_url TEXT, web_url TEXT, mime_type TEXT, type TEXT, service TEXT, consumption_status INTEGER, convo_id INTEGER, message_id INTEGER, sending_status INTEGER, ams_id TEXT)",
        "messageannotations":  "CREATE TABLE MessageAnnotations (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, message_id INTEGER, type INTEGER, key TEXT, value TEXT, author TEXT, timestamp INTEGER, status INTEGER)",
        "messages":            "CREATE TABLE Messages (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, chatname TEXT, timestamp INTEGER, author TEXT, from_dispname TEXT, chatmsg_type INTEGER, identities TEXT, leavereason INTEGER, body_xml TEXT, chatmsg_status INTEGER, body_is_rawxml INTEGER, edited_by TEXT, edited_timestamp INTEGER, newoptions INTEGER, newrole INTEGER, dialog_partner TEXT, oldoptions INTEGER, guid BLOB, convo_id INTEGER, type INTEGER, sending_status INTEGER, param_key INTEGER, param_value INTEGER, reason TEXT, error_code INTEGER, consumption_status INTEGER, author_was_live INTEGER, participant_count INTEGER, pk_id INTEGER, crc INTEGER, remote_id INTEGER, call_guid TEXT, extprop_contact_review_date TEXT, extprop_contact_received_stamp INTEGER, extprop_contact_reviewed INTEGER, option_bits INTEGER, server_id INTEGER, annotation_version INTEGER, timestamp__ms INTEGER, language TEXT, bots_settings TEXT, reaction_thread TEXT, content_flags INTEGER)",
        "participants":        "CREATE TABLE Participants (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, convo_id INTEGER, identity TEXT, rank INTEGER, requested_rank INTEGER, text_status INTEGER, voice_status INTEGER, live_identity TEXT, live_price_for_me TEXT, live_fwd_identities TEXT, live_start_timestamp INTEGER, sound_level INTEGER, debuginfo TEXT, next_redial_time INTEGER, nrof_redials_left INTEGER, last_voice_error TEXT, quality_problems TEXT, live_type INTEGER, live_country TEXT, transferred_by TEXT, transferred_to TEXT, adder TEXT, sponsor TEXT, last_leavereason INTEGER, is_premium_video_sponsor INTEGER, is_multiparty_video_capable INTEGER, live_identity_to_use TEXT, livesession_recovery_in_progress INTEGER, livesession_fallback_in_progress INTEGER, is_multiparty_video_updatable INTEGER, live_ip_address TEXT, is_video_codec_compatible INTEGER, group_calling_capabilities INTEGER, is_seamlessly_upgraded_call INTEGER, live_voicechannel INTEGER, read_horizon INTEGER, is_active_speaker INTEGER, dominant_speaker_rank INTEGER, endpoint_details TEXT, messaging_mode INTEGER, real_identity TEXT, adding_in_progress_since INTEGER)",
        "smses":               "CREATE TABLE SMSes (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, is_failed_unseen INTEGER, price_precision INTEGER, type INTEGER, status INTEGER, failurereason INTEGER, price INTEGER, price_currency TEXT, target_numbers TEXT, target_statuses BLOB, body TEXT, timestamp INTEGER, reply_to_number TEXT, chatmsg_id INTEGER, extprop_hide_from_history INTEGER, extprop_extended INTEGER, identity TEXT, notification_id INTEGER, event_flags INTEGER, reply_id_number TEXT, convo_name TEXT, outgoing_reply_type INTEGER, error_category INTEGER)",
        "transfers":           "CREATE TABLE Transfers (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, type INTEGER, partner_handle TEXT, partner_dispname TEXT, status INTEGER, failurereason INTEGER, starttime INTEGER, finishtime INTEGER, filepath TEXT, filename TEXT, filesize TEXT, bytestransferred TEXT, bytespersecond INTEGER, chatmsg_guid BLOB, chatmsg_index INTEGER, convo_id INTEGER, pk_id INTEGER, nodeid BLOB, last_activity INTEGER, flags INTEGER, old_status INTEGER, old_filepath INTEGER, extprop_localfilename TEXT, extprop_hide_from_history INTEGER, extprop_window_visible INTEGER, extprop_handled_by_chat INTEGER, accepttime INTEGER, parent_id INTEGER, offer_send_list TEXT)",
        "translators":         "CREATE TABLE Translators (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER)",
        "videomessages":       "CREATE TABLE VideoMessages (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, qik_id BLOB, attached_msg_ids TEXT, sharing_id TEXT, status INTEGER, vod_status INTEGER, vod_path TEXT, local_path TEXT, public_link TEXT, progress INTEGER, title TEXT, description TEXT, author TEXT, creation_timestamp INTEGER, type TEXT)",
        "videos":              "CREATE TABLE Videos (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, status INTEGER, dimensions TEXT, error TEXT, debuginfo TEXT, duration_1080 INTEGER, duration_720 INTEGER, duration_hqv INTEGER, duration_vgad2 INTEGER, duration_ltvgad2 INTEGER, timestamp INTEGER, hq_present INTEGER, duration_ss INTEGER, ss_timestamp INTEGER, media_type INTEGER, convo_id INTEGER, device_path TEXT, device_name TEXT, participant_id INTEGER, rank INTEGER)",
        "voicemails":          "CREATE TABLE Voicemails (id INTEGER NOT NULL PRIMARY KEY, is_permanent INTEGER, type INTEGER, partner_handle TEXT, partner_dispname TEXT, status INTEGER, failurereason INTEGER, subject TEXT, timestamp INTEGER, duration INTEGER, allowed_duration INTEGER, playback_progress INTEGER, convo_id INTEGER, chatmsg_guid BLOB, notification_id INTEGER, flags INTEGER, size INTEGER, path TEXT, failures INTEGER, vflags INTEGER, xmsg TEXT, extprop_hide_from_history INTEGER)",
    }


    def __init__(self, filename, log_error=True):
        """
        Initializes a new Skype database object from the file.

        @param   log_error  if False, exceptions on opening the database
                            are not written to log (written by default)
        """
        self.filename = os.path.realpath(filename)
        self.basefilename = os.path.basename(self.filename)
        self.filesize = None
        self.last_modified = None
        self.backup_created = False
        self.consumers = set() # Registered objects using this database
        self.account = None    # Row from table Accounts
        self.id = None   # Accounts.skypename
        self.tables = {} # {"name": {"Name":str, "rows": 0, "columns": []}, }
        self.tables_list = None # Ordered list of table items
        self.table_rows = {}    # {"tablename1": [..], }
        self.table_objects = {} # {"tablename1": {id1: {rowdata1}, }, }
        self.update_fileinfo()
        try:
            self.connection = sqlite3.connect(self.filename,
                                              check_same_thread=False)
            self.connection.row_factory = self.row_factory
            self.connection.text_factory = str
            rows = self.execute("SELECT name, sql FROM sqlite_master "
                                "WHERE type = 'table'").fetchall()
            for row in rows:
                self.tables[row["name"].lower()] = row
        except Exception:
            if log_error: logger.exception("Error opening database %s.", filename)
            self.close()
            raise
        from . import live # Avoid circular import
        self.update_accountinfo(log_error)
        self.live = live.SkypeLogin(self)


    def __str__(self):
        if self and hasattr(self, "filename"):
            return self.filename


    def make_title_col(self, table="conversations", alias=None):
        """Returns SQL expression for selecting chat/contact/account title."""
        PREFS = ["given_displayname", "fullname", "displayname", "meta_topic",
                 "skypename", "pstnnumber", "identity"]
        DEFS = {"chats": "identity", "accounts": "skypename", "contacts": "skypename"}
        cols = self.get_table_columns(table)
        colnames = [x["name"].lower() for x in cols]
        mycols = [x for x in PREFS if x in colnames]
        if not cols: mycols = DEFS.get(table, [])

        result = ""
        for n in mycols:
            result += " WHEN COALESCE(TRIM(%s), '') != '' THEN %s" % (n, n)
        return "CASE %s ELSE '#' || %s.id END" % (result.strip(), alias or table)


    def check_integrity(self):
        """Checks SQLite database integrity, returning a list of errors."""
        result = []
        rows = self.execute("PRAGMA integrity_check").fetchall()
        if len(rows) != 1 or "ok" != rows[0]["integrity_check"].lower():
            result = [r["integrity_check"] for r in rows]
        return result


    def recover_data(self, filename):
        """
        Recovers as much data from this database to a new database as possible.
        
        @return  a list of encountered errors, if any
        """
        result = []
        with open(filename, "w") as _: pass # Truncate file
        self.execute("ATTACH DATABASE ? AS new", (filename, ))
        # Create structure for all tables
        for t in (x for x in self.tables_list or [] if x.get("sql")):
            if t["name"].lower().startswith("sqlite_"): continue # Internal use
            sql  = t["sql"].replace("CREATE TABLE ", "CREATE TABLE new.")
            self.execute(sql)
        # Copy data from all tables
        for t in (x for x in self.tables_list or [] if x.get("sql")):
            if t["name"].lower().startswith("sqlite_"): continue # Internal use
            sql = "INSERT INTO new.%(name)s SELECT * FROM main.%(name)s" % t
            try:
                self.execute(sql)
            except Exception as e:
                result.append(repr(e))
                logger.exception("Error copying table %s from %s to %s.",
                                 t["name"], self.filename, filename)
        # Create indexes
        indexes = []
        try:
            sql = "SELECT * FROM sqlite_master WHERE TYPE = ?"
            indexes = self.execute(sql, ("index", )).fetchall()
        except Exception as e:
            result.append(repr(e))
            logger.exception("Error getting indexes from %s.", self.filename)
        for i in (x for x in indexes if x.get("sql")):
            sql  = i["sql"].replace("CREATE INDEX ", "CREATE INDEX new.")
            try:
                self.execute(sql)
            except Exception as e:
                result.append(repr(e))
                logger.exception("Error creating index %s for %s.",
                                 i["name"], filename)
        self.execute("DETACH DATABASE new")
        return result


    def clear_cache(self):
        """Clears all the currently cached rows."""
        self.table_rows.clear()
        self.table_objects.clear()
        self.get_tables(True)


    def update_accountinfo(self, log_error=True):
        """Refreshes Skype account information."""
        try:
            titlecol = self.make_title_col("accounts")
            self.account = self.execute("SELECT *, %s AS name, "
                "skypename AS identity FROM accounts LIMIT 1" % titlecol).fetchone()
            self.id = self.account["skypename"]
        except Exception:
            if log_error:
                logger.exception("Error getting account information from %s.", self)


    def stamp_to_date(self, timestamp):
        """Converts the UNIX timestamp to datetime using localtime."""
        return datetime.datetime.fromtimestamp(timestamp)


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
            except Exception:
                pass
            del self.connection
            self.connection = None
        for attr in ["tables", "tables_list", "table_rows", "table_objects"]:
            if hasattr(self, attr):
                delattr(self, attr)
                setattr(self, attr, None if ("tables_list" == attr) else {})

        # Remove live login tokenfile if not storing password
        if not conf.Login.get(self.filename, {}).get("store"):
            try: os.unlink(self.live.tokenpath)
            except Exception: pass


    def execute(self, sql, params=(), log=True):
        """Shorthand for self.connection.execute()."""
        result = None
        if self.connection:
            if log and conf.LogSQL:
                logger.info("SQL: %s%s", sql,
                            ("\nParameters: %s" % params) if params else "")
            result = self.connection.execute(sql, params)
        return result


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


    def is_open(self):
        """Returns whether the database is currently open."""
        return (self.connection is not None)


    def get_tables(self, refresh=False, this_table=None):
        """
        Returns the names and rowcounts of all tables in the database, as
        [{"name": "tablename", "rows": 0, "sql": CREATE SQL}, ].
        Uses already retrieved cached values if possible, unless refreshing.

        @param   refresh     if True, information including rowcounts is
                             refreshed
        @param   this_table  if set, only information for this table is
                             refreshed
        """
        if self.is_open() and (refresh or self.tables_list is None):
            sql = "SELECT name, sql FROM sqlite_master WHERE type = 'table' " \
                  "%sORDER BY name COLLATE NOCASE" % \
                  ("AND name = ? " if this_table else "")
            params = [this_table] if this_table else []
            rows = self.execute(sql, params).fetchall()
            tables = {}
            tables_list = []
            for row in rows:
                table = row
                try:
                    res = self.execute("SELECT COUNT(*) AS count FROM %s" %
                                       table["name"], log=False)
                    table["rows"] = res.fetchone()["count"]
                except sqlite3.DatabaseError:
                    table["rows"] = 0
                    logger.exception("Error getting %s row count for %s.",
                                     table, self.filename)
                # Here and elsewhere in this module - table names are turned to
                # lowercase when used as keys.
                tables[table["name"].lower()] = table
                tables_list.append(table)
            if this_table:
                self.tables.update(tables)
                for t in self.tables_list or []:
                    if t["name"] == this_table:
                        self.tables_list.remove(t)
                if self.tables_list is None:
                    self.tables_list = []
                self.tables_list += tables_list
                self.tables_list.sort(key=lambda x: x["name"])
            else:
                self.tables = tables
                self.tables_list = tables_list

        return self.tables_list


    def get_general_statistics(self, full=True):
        """
        Get up-to-date general statistics raw from the database.

        @param   full  whether to return full statistics, or only tables
                       and last chat
        """
        result = collections.defaultdict(str)
        if self.account:
            result.update({"name": self.account.get("name"),
                           "skypename": self.account.get("skypename")})
        COUNTS = ["Conversations", "Messages", "Contacts"]
        if full: COUNTS += ["Transfers"]
        for table in COUNTS:
            res = self.execute("SELECT COUNT(*) AS count FROM %s" % table)
            label = "chats" if "Conversations" == table else table.lower()
            result[label] = next(res, {}).get("count")

        for k, table in [("chats", "Conversations"), ("messages", "Messages"),
                       ("contacts", "Contacts"), ("transfers", "Transfers")]:
            res = self.execute("SELECT COUNT(*) AS count FROM %s" % table)
            result[k] = next(res, {}).get("count")

        titlecol = self.make_title_col()
        typestr = ", ".join(map(str, MESSAGE_TYPES_BASE))

        for i, label in enumerate(["last", "first"]):
            direction = "ASC" if i else "DESC"
            res = self.execute("SELECT author, from_dispname, convo_id, timestamp "
                               "FROM Messages WHERE type IN (%s) "
                               "ORDER BY timestamp %s LIMIT 1" % (typestr, direction))
            msg = next(res, None)
            if msg:
                chat = next((x for x in self.table_rows.get("conversations", [])
                             if x["id"] == msg["convo_id"]), None)
                chat = chat or self.execute(
                    "SELECT *, %s AS title FROM conversations "
                    "WHERE id = ?" % titlecol, [msg["convo_id"]]
                ).fetchone()
                if msg.get("timestamp"):
                    dt = self.stamp_to_date(msg["timestamp"])
                    result["%smessage_dt" % label] = dt.strftime("%Y-%m-%d %H:%M")
                contact = self.account if msg["author"] == self.id else None
                contact = contact or self.table_objects.get("contacts", {}).get(msg["author"])
                if not contact:
                    cntitlecol = self.make_title_col("contacts")
                    contact = self.execute(
                        "SELECT *, COALESCE(skypename, pstnnumber, '') AS identity, "
                        "%s AS name FROM contacts WHERE identity = ?"
                    % cntitlecol, [msg["author"]]).fetchone()
                result["%smessage_from" % label] = self.get_author_name(msg, contact)
                result["%smessage_skypename" % label] = msg["author"]
                if chat:
                    title = ('"%s"' if CHATS_TYPE_SINGLE != chat["type"]
                             else "chat with %s") % chat["title"]
                    result["%smessage_chat" % label] = title
                    result["%smessage_chattype" % label] = chat["type"]
            if not full: break # for i, label

        for i in range(2) if full else ():
            row = self.execute("SELECT COUNT(*) AS count FROM Messages "
                "WHERE author %s= :skypename AND type IN (%s)"
                % ("!="[i], typestr), result).fetchone()
            result["messages_" + ("to", "from")[i]] = row["count"]

        return result


    def get_messages(self, chat=None, ascending=True,
                     additional_sql=None, additional_params=None,
                     timestamp_from=None, timestamp_to=None, use_cache=True):
        """
        Yields all the messages (or messages for the specified chat), as
        {"datetime": datetime, ..}, ordered from earliest to latest.
        Uses already retrieved cached values if possible, unless additional
        query parameters are used.

        @param   chat               as returned by get_conversations(), if any
        @param   ascending          specify message order, earliest to latest
                                    or latest to earliest
        @param   additional_sql     additional SQL string added to the end
        @param   additional_params  SQL parameter dict for additional_sql
        @param   timestamp_from     timestamp beyond which messages will start
        @param   timestamp_to       timestamp beyond which messages will end
        @param   use_cache          whether to use cached values if available.
                                    The LIKE keywords will be ignored if True.
        """
        if self.is_open() and "messages" in self.tables:
            if "messages" not in self.table_rows:
                self.table_rows["messages"] = {} # {convo_id: [{msg1},]}
            if not use_cache \
            or not (chat and chat["id"] in self.table_rows["messages"]):
                sql, params = "SELECT m.* FROM messages m ", {}
                if additional_sql and " c." in additional_sql:
                    sql += "LEFT JOIN conversations c ON m.convo_id = c.id "
                if additional_sql and " cn." in additional_sql:
                    sql += "LEFT JOIN contacts cn ON m.author = cn.skypename "
                # Take only known and supported types of messages.
                sql += "WHERE m.type IN (%s)" % ", ".join(
                       map(str, MESSAGE_TYPES_MESSAGE))
                if chat:
                    cc = [x for x in (chat, chat.get("__link")) if x]
                    ff = [":convo_id%s" % i for i in range(len(cc))]
                    sql += " AND m.convo_id IN (%s)" % ", ".join(ff)
                    for i, c in enumerate(cc):
                        params["convo_id%s" % i] = c["id"]
                if timestamp_from:
                    sql += " AND m.timestamp %s :timestamp_from" % "<>"[ascending]
                    params["timestamp_from"] = timestamp_from
                if timestamp_to:
                    sql += " AND m.timestamp %s :timestamp_to" % "><"[ascending]
                    params["timestamp_to"] = timestamp_to
                if additional_sql:
                    sql += " AND (%s)" % additional_sql
                    params.update(additional_params or {})
                sql += " ORDER BY m.timestamp %s" \
                    % ("ASC" if ascending else "DESC")
                res = self.execute(sql, params)
                messages = []
                message = res.fetchone()
                while message:
                    message["datetime"] = None
                    if message["timestamp"]:
                        message["datetime"] = self.stamp_to_date(
                                              message["timestamp"])
                    if chat and use_cache and len(params) == 1:
                        messages.append(message)
                    yield message
                    message = res.fetchone()
                if chat and use_cache and len(params) == 1:
                    # Only cache queries getting full range
                    self.table_rows["messages"][chat["id"]] = messages
            else:
                messages_sorted = sorted(
                    self.table_rows["messages"][chat["id"]],
                    key=lambda m: m["timestamp"], reverse=not ascending
                )
                if timestamp_from:
                    messages_sorted = (x for x in messages_sorted
                        if (x["timestamp"] > timestamp_from if ascending 
                            else x["timestamp"] < timestamp_from))
                for message in messages_sorted:
                    yield message


    def row_factory(self, cursor, row):
        """
        Creates dicts from resultset rows, with BLOB fields converted to
        strings.
        """
        result = {}
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
                except Exception:
                    result[name] = str(result[name]).decode("latin1")
        return result


    def get_conversations(self, chatnames=None, authornames=None, chatidentities=None,
                          reload=False, log=True):
        """
        Returns chats as
        [{"id": integer, "title": "chat title", "created_datetime": datetime,
          "title_long": "Group chat "chat_title"", "title_long_lc": "group..",
          "last_activity_datetime": datetime, "type_name": chat type name}, ..]
        Combines migrated chats into a single one under {"__link": {oldchat}}.
        Uses already retrieved cached values if possible.

        @param   chatnames       return chats with names containing given values
        @param   authornames     return chats with authors containing given values
        @param   chatidentities  return chats with given identities
        @param   reload          ignore cache, retrieve everything again
        """
        result = []
        if not self.is_open() or "conversations" not in self.tables:
            return result

        if reload or "conversations" not in self.table_rows:
            participants = {}
            sortkey_participants = lambda x: (x["contact"].get("name") or "").lower()
            if "contacts" in self.tables and "participants" in self.tables:
                if log: logger.info("Conversations and participants: "
                                    "retrieving all (%s).", self.filename)
                self.get_contacts(reload=reload)
                self.get_table_rows("participants", reload=reload)
                for p in self.table_objects["participants"].values():
                    if p["convo_id"] not in participants:
                        participants[p["convo_id"]] = []
                    if p["identity"] == self.id:
                        p["contact"] = self.account
                    else:
                        # Fake a dummy contact object if no contact row
                        p["contact"] = self.table_objects["contacts"].get(
                            p["identity"], {"skypename":   p["identity"],
                                            "identity":    p["identity"],
                                            "name":        p["identity"],
                                            "fullname":    p["identity"],
                                            "displayname": p["identity"]}
                        )
                    participants[p["convo_id"]].append(p)
            [p.sort(key=sortkey_participants) for p in participants.values()]
            where, args = "WHERE displayname IS NOT NULL ", {}
            for i, item in enumerate(chatnames or []):
                safe = item.replace("%", "\\%").replace("_", "\\_")
                where += (" OR " if i else "AND (") + (
                         "title LIKE :name%s" % i +
                         (" ESCAPE '\\'" if safe != item else "") +
                         (")" if i == len(chatnames) - 1 else ""))
                args["name%s" % i] = "%" + safe + "%"
            for i, identity in enumerate(chatidentities or []):
                where += (" OR " if i else "AND (") + (
                          "identity = :identity%s" % i + 
                         (")" if i == len(chatidentities) - 1 else ""))
                args["identity%s" % i] = identity
            titlecol = self.make_title_col()
            rows = self.execute(
                "SELECT *, %s AS title, "
                "NULL AS created_datetime, NULL AS last_activity_datetime "
                "FROM conversations %s"
                "ORDER BY last_activity_timestamp DESC" % (titlecol, where), args
            ).fetchall()

            # Chats can refer to older entries, prior to system from Skype 7.
            # Collate such chats automatically, with merged statistics.
            idmap = dict((x["identity"], x) for x in rows)
            for c in rows:
                if c.get("alt_identity") in idmap: # Pointing to new ID
                    idmap[c["alt_identity"]]["__link"] = c
                if "thread.skype" not in c["identity"]: continue
                # Can contain old chat ID base64-encoded into new identity:
                # 19:I3Vuby8kZG9zOzUxNzAyYzg3NmU0ZmVjNmU=@p2p.thread.skype
                pattern = r"(\d+:)([^@]+)(.*)"
                repl = lambda x: x.group(2).decode("base64")
                try:
                    oldid = re.sub(pattern, repl, str(c["identity"]))
                    if oldid in idmap:
                        c["__link"] = idmap[oldid]
                except Exception: pass
            oldset = set(x["__link"]["identity"] for x in rows
                         if x.get("__link"))
            for chat in rows:
                chat["participants"] = participants.get(chat["id"], [])
                if authornames:
                    fs = "given_displayname fullname displayname skypename pstnnumber".split()
                    vals = [p["contact"].get(field, None) for field in fs
                            for p in chat["participants"]]
                    match = any(re.search(name, value, re.I | re.U)
                                for name in map(re.escape, authornames)
                                for value in vals if value)
                    if not vals or not match: continue # for chat

                chat["title_long"] = ("Chat with %s"
                    if CHATS_TYPE_SINGLE == chat["type"]
                    else "Group chat \"%s\"") % chat["title"]
                chat["title_long_lc"] = \
                    chat["title_long"][0].lower() + chat["title_long"][1:]
                for k, v in [("creation_timestamp", "created_datetime"),
                ("last_activity_timestamp", "last_activity_datetime")]:
                    if chat[k]:
                        chat[v] = self.stamp_to_date(chat[k])

                chat["type_name"] = CHATS_TYPENAMES.get(chat["type"],
                    "Unknown (%d)" % chat["type"])
                # Set stats attributes presence
                chat["message_count"] = None
                chat["first_message_datetime"] = None
                chat["last_message_datetime"] = None
                if chat["identity"] not in oldset: # Available in link
                    result.append(chat)

            for chat in result:
                # Second pass: combine participants from linked chats, populate people
                if chat.get("__link") and chat["__link"].get("participants"):
                    pmap = dict((p["identity"], p) for c in (chat, chat["__link"])
                                for p in c["participants"])
                    chat["participants"] = sorted(pmap.values(), key=sortkey_participants)

                people = sorted([p["identity"] for p in chat["participants"]])
                if CHATS_TYPE_SINGLE != chat["type"]:
                    chat["people"] = "%s (%s)" % (len(people), ", ".join(people))
                else:
                    chat["people"] = ", ".join(p for p in people if p != self.id)

            if log: logger.info("Conversations and participants retrieved "
                "(%s chats, %s contacts, %s).",
                len(result), len(self.table_rows["contacts"]),
                self.filename
            )
            self.table_rows["conversations"] = result
        else:
            result = self.table_rows["conversations"]

        return result


    def get_conversations_stats(self, chats, log=True):
        """
        Collects statistics for all conversations and fills in the values:
        {"first_message_timestamp": int, "first_message_datetime": datetime,
         "last_message_timestamp": int, "last_message_datetime": datetime,
         "message_count": message count, }.
        Combines linked chat statistics into parent chat statistics.

        @param   chats  list of chats, as returned from get_conversations()
        """
        if log and chats:
            logger.info("Statistics collection starting (%s).", self.filename)
        stats = {}
        if self.is_open() and "messages" in self.tables:
            and_str, and_val = "", []
            if 1 == len(chats):
                cc = [x for x in (chats[0], chats[0].get("__link")) if x]
                and_str = " AND convo_id IN (%s)" % ", ".join("?" * len(cc))
                and_val = [c["id"] for c in cc]
            sql = ("SELECT convo_id AS id, COUNT(*) AS message_count, "
                   "MIN(timestamp) AS first_message_timestamp, "
                   "MAX(timestamp) AS last_message_timestamp, "
                   "NULL AS first_message_datetime, "
                   "NULL AS last_message_datetime "
                   "FROM messages WHERE type IN (%s)%s GROUP BY convo_id" 
                   % (", ".join(map(str, MESSAGE_TYPES_STATS)), and_str))
            rows_stat = self.execute(sql, and_val).fetchall()
            stats = dict((i["id"], i) for i in rows_stat)
        for chat in chats:
            chat["message_count"] = 0
            cc = [x for x in (chat, chat.get("__link")) if x]
            datas = [stats[x["id"]] for x in cc if x["id"] in stats]
            if not datas: continue
            for data in datas: # Initialize datetime objects
                for n in ["first_message", "last_message"]:
                    if data[n + "_timestamp"]:
                        dt = self.stamp_to_date(data[n + "_timestamp"])
                        data[n + "_datetime"] = dt

            for n, f in zip(["first_message_datetime", "last_message_datetime",
                "created_datetime", "creation_timestamp", "message_count",
                "last_activity_datetime", "last_activity_timestamp"],
                [min, max, min, min, sum, max, max]
            ): # Combine 
                values = [d.get(n, c.get(n)) for c, d in zip(cc, datas)]
                values = [x for x in values if x is not None]
                chat[n] = f(values) if values else None

        if log and chats:
            logger.info("Statistics collected (%s).", self.filename)


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


    def get_contacts(self, reload=False):
        """
        Returns all the contacts in the database, as
        [{"identity": skypename or pstnnumber,
          "name": displayname or fullname, },]
        Uses already retrieved cached values if possible.

        @param   reload  ignore cache, retrieve everything again
        """
        result = []
        if not self.is_open() or "contacts" not in self.tables:
            return result

        if reload or "contacts" not in self.table_rows:
            titlecol = self.make_title_col("contacts")
            rows = self.execute(
                "SELECT *, COALESCE(skypename, pstnnumber, '') "
                    "AS identity, "
                "%s AS name FROM contacts ORDER BY name COLLATE NOCASE"
            % titlecol).fetchall()
            self.table_objects["contacts"] = {}
            for c in rows:
                result.append(c)
                self.table_objects["contacts"][c["identity"]] = c
            self.table_rows["contacts"] = result
        else:
            result = self.table_rows["contacts"]

        return result


    def get_contact_name(self, identity, contact=None):
        """
        Returns the full name for the specified contact, or given identity if
        not set.

        @param   identity  skypename or pstnnumber
        @param   contact   cached Contacts-row, if any
        """
        name = ""
        if identity == self.id:
            name = self.account["name"]
        else:
            if not contact:
                self.get_contacts()
                contact = self.table_objects["contacts"].get(identity)
            if contact: name = contact["name"]
        name = name or identity
        return name


    def get_author_name(self, message, contact=None):
        """
        Returns the display name of the message author,
        contact name if contact available else message from_dispname or author.

        @param   contact   cached Contacts-row, if any
        """
        result = self.get_contact_name(message["author"], contact)
        if result == message["author"] and message.get("from_dispname"):
            result = message["from_dispname"]
        return result


    def get_table_rows(self, table, reload=False):
        """
        Returns all the rows of the specified table.
        Uses already retrieved cached values if possible.

        @param   reload  ignore cache, retrieve everything again
        """
        result = []
        table = table.lower()
        if table in self.tables:
            if reload or table not in self.table_rows:
                col_data = self.get_table_columns(table)
                pks = [c["name"] for c in col_data if c["pk"]]
                pk = pks[0] if len(pks) == 1 else None
                result = self.execute("SELECT * FROM %s" % table).fetchall()
                self.table_rows[table] = result
                self.table_objects[table] = {}
                if pk:
                    for row in result:
                        self.table_objects[table][row[pk]] = row
            else:
                result = self.table_rows[table]
        return result


    def get_smses(self):
        """
        Returns all the SMSes in the database.
        Uses already retrieved cached values if possible.
        """
        if self.is_open() and "smses" in self.tables:
            if "smses" not in self.table_rows:
                rows = self.execute(
                    "SELECT * FROM smses ORDER BY id").fetchall()
                smses = []
                for sms in rows:
                    smses.append(sms)
                self.table_rows["smses"] = smses
            else:
                smses = self.table_rows["smses"]

        return smses


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
            ids = [chat["id"], chat.get("__link", {}).get("id", chat["id"])]
            videos = [v for v in videos if v["convo_id"] in ids]
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
            ids = [chat["id"], chat.get("__link", {}).get("id", chat["id"])]
            calls = [c for c in calls if c["conv_dbid"] in ids]
        return calls


    def get_contact(self, identity):
        """
        Returns the contact specified by the identity
        (skypename or pstnnumber), using cache if possible.
        """
        contact = None
        if self.is_open() and "contacts" in self.tables:
            if "contacts" not in self.table_objects:
                self.table_objects["contacts"] = {}
            contact = self.table_objects["contacts"].get(identity)
            if not contact:
                titlecol = self.make_title_col("contacts")
                contact = self.execute(
                    "SELECT *, %s AS name, "
                    "COALESCE(skypename, pstnnumber, '') AS identity "
                    "FROM contacts WHERE skypename = :identity "
                    "OR pstnnumber = :identity" % titlecol,
                    {"identity": identity}
                ).fetchone()
                self.table_objects["contacts"][identity] = contact

        return contact


    def get_table_columns(self, table):
        """
        Returns the columns of the specified table, as
        [{"name": "col1", "type": "INTEGER", }, ], or [] if not retrievable.
        """
        table = table.lower()
        table_columns = []
        if self.is_open() and self.tables_list is None:
            self.get_tables()
        if self.is_open() and table in self.tables:
            if "columns" in self.tables[table]:
                table_columns = self.tables[table]["columns"]
            else:
                table_columns = []
                try:
                    res = self.execute("PRAGMA table_info(%s)" % table, log=False)
                    for row in res.fetchall():
                        table_columns.append(row)
                except sqlite3.DatabaseError:
                    logger.exception("Error getting %s column data for %s.",
                                     table, self.filename)
                self.tables[table]["columns"] = table_columns
        return table_columns


    def update_fileinfo(self):
        """Updates database file size and modification information."""
        self.filesize = os.path.getsize(self.filename)
        self.last_modified = datetime.datetime.fromtimestamp(
                             os.path.getmtime(self.filename))


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
                    try:
                        val = val.encode("latin1")
                    except Exception:
                        val = val.encode("utf-8")
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
        if create_sql or (table in self.CREATE_STATEMENTS):
            self.execute(create_sql or self.CREATE_STATEMENTS[table])
            self.connection.commit()
            row = self.execute("SELECT name, sql FROM sqlite_master "
                                "WHERE type = 'table' "
                                "AND LOWER(name) = ?", [table]).fetchone()
            self.tables[table] = row


    def insert_conversation(self, chat, source_db):
        """Inserts the specified conversation into the database and returns its ID."""
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

            cursor = self.execute("INSERT INTO conversations (%s) VALUES (%s)"
                                  % (str_cols, str_vals), chat_filled)
            self.connection.commit()
            self.last_modified = datetime.datetime.now()
            return cursor.lastrowid


    def insert_messages(self, chat, messages, source_db, source_chat,
                        heartbeat=None, beatcount=None):
        """
        Inserts the specified messages under the specified chat in this
        database, includes related rows in Calls, Videos, Transfers and
        SMSes.

        @param    messages   list of messages, or message IDs from source_db
        @param    heartbeat  function called after every @beatcount message
        @param    beatcount  number of messages after which to call heartbeat
        @return              a list of inserted message IDs
        """
        result = []
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
            logger.info("Merging %s (%s) into %s.",
                        util.plural("chat message", messages),
                        chat["title_long_lc"], self.filename)
            self.ensure_backup()
            # Messages.chatname corresponds to Chats.name, and Chats entries
            # must exist for Skype application to be able to find the messages.
            cc = [x for x in (source_chat, source_chat.get("__link")) if x]
            chatrows_source = dict((i["name"], i) for i in 
                source_db.execute("SELECT * FROM chats WHERE conv_dbid IN (%s)"
                    % ", ".join("?" * len(cc)), [x["id"] for x in cc]))
            chatrows_present = dict([(i["name"], 1)
                for i in self.execute("SELECT name FROM chats")])
            col_data = self.get_table_columns("messages")
            fields = [col["name"] for col in col_data if col["name"] != "id"]
            str_cols = ", ".join(fields)
            str_vals = ":" + ", :".join(fields)
            transfer_col_data = self.get_table_columns("transfers")
            transfer_fields = [col["name"] for col in transfer_col_data
                               if col["name"] != "id"]
            transfer_cols = ", ".join(transfer_fields)
            transfer_vals = ", ".join("?" * len(transfer_fields))
            sms_col_data = self.get_table_columns("smses")
            sms_fields = [col["name"] for col in sms_col_data
                          if col["name"] != "id"]
            sms_cols = ", ".join(sms_fields)
            sms_vals = ", ".join("?" * len(sms_fields))
            chat_col_data = self.get_table_columns("chats")
            chat_fields = [col["name"] for col in chat_col_data
                           if col["name"] not in ("id", "conv_dbid")]
            chat_cols = ", ".join(chat_fields + ["conv_dbid"])
            chat_vals = ", ".join("?" * (len(chat_fields) + 1))

            timestamp_earliest = source_chat["creation_timestamp"] \
                                 or sys.maxsize

            for i, m in enumerate(source_db.message_iterator(messages)):
                # Insert corresponding Chats entry, if not present
                if (m["chatname"] not in chatrows_present
                and m["chatname"] in chatrows_source):
                    chatrowdata = chatrows_source[m["chatname"]]
                    chatrow = [chatrowdata.get(col, "") for col in chat_fields]
                    chatrow = self.blobs_to_binary(
                        chatrow, chat_fields, chat_col_data)
                    chatrow.append(chat["id"]) # For conv_dbid
                    sql = "INSERT INTO chats (%s) VALUES (%s)" % \
                          (chat_cols, chat_vals)
                    self.execute(sql, chatrow)
                    chatrows_present[m["chatname"]] = 1
                m_filled = self.fill_missing_fields(m, fields)
                m_filled["convo_id"] = chat["id"]
                if m["author"] == source_db.id:  # Ensure correct author
                    m_filled["author"] = self.id # if merge from other account
                m_filled = self.blobs_to_binary(m_filled, fields, col_data)
                cursor = self.execute("INSERT INTO messages (%s) VALUES (%s)"
                                      % (str_cols, str_vals), m_filled)
                m_id = cursor.lastrowid
                if (MESSAGE_TYPE_FILE == m["type"]
                and "transfers" in source_db.tables):
                    transfers = [t for t in source_db.get_transfers()
                                 if t.get("chatmsg_guid") == m["guid"]]
                    if transfers:
                        sql = "INSERT INTO transfers (%s) VALUES (%s)" % \
                              (transfer_cols, transfer_vals)
                        transfers.sort(key=lambda x: x.get("chatmsg_index"))
                        for t in map(dict.copy, transfers):
                            # pk_id and nodeid are troublesome, ditto in SMSes,
                            # because their meaning is unknown - will
                            # something go out of sync if their values differ?
                            if t["partner_handle"] == source_db.id:
                                t["partner_handle"] = self.id
                            row = [t.get(col, "") if col != "convo_id" else chat["id"]
                                   for col in transfer_fields]
                            row = self.blobs_to_binary(row, transfer_fields,
                                                       transfer_col_data)
                            self.execute(sql, row)
                if (MESSAGE_TYPE_SMS == m["type"]
                and "smses" in source_db.tables):
                    smses = [s for s in source_db.get_smses()
                             if s.get("chatmsg_id") == m["id"]]
                    if smses:
                        sql = "INSERT INTO smses (%s) VALUES (%s)" % \
                              (sms_cols, sms_vals)
                        for sms in smses:
                            t = [sms.get(col, "") if col != "chatmsg_id" else m_id
                                 for col in sms_fields]
                            t = self.blobs_to_binary(t, sms_fields, sms_col_data)
                            self.execute(sql, t)
                timestamp_earliest = min(timestamp_earliest, m["timestamp"])
                result.append(m_id)
                if heartbeat and beatcount and i and not i % beatcount:
                    heartbeat()
            if (timestamp_earliest
            and chat["creation_timestamp"] > timestamp_earliest):
                # Conversations.creation_timestamp must not be later than the
                # oldest message, Skype will not show messages older than that.
                chat["creation_timestamp"] = timestamp_earliest
                chat["created_datetime"] = self.stamp_to_date(timestamp_earliest)
                self.execute("UPDATE conversations SET creation_timestamp = "
                             ":creation_timestamp WHERE id = :id", chat)
            self.connection.commit()
            self.last_modified = datetime.datetime.now()
        return result


    def insert_participants(self, chat, participants, source_db):
        """
        Inserts the specified participants under the specified chat in this
        database.
        """
        if self.is_open() and not self.account and source_db.account:
            self.insert_account(source_db.account)
        if self.is_open() and "participants" not in self.tables:
            self.create_table("participants")
        if self.is_open() and "contacts" not in self.tables:
            self.create_table("contacts")
        if self.is_open() and "participants" in self.tables:
            logger.info("Merging %d chat participants (%s) into %s.",
                        len(participants), chat["title_long_lc"], self.filename)
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
            logger.info("Inserting account \"%s\" into %s.",
                        account["skypename"], self.filename)
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


    def insert_contacts(self, contacts, source_db):
        """
        Inserts the specified contacts into this database.
        """
        if self.is_open() and not self.account and source_db.account:
            self.insert_account(source_db.account)
        if self.is_open() and "contacts" not in self.tables:
            self.create_table("contacts")
        if self.is_open() and "contacts" in self.tables:
            logger.info("Merging %d contacts into %s.", len(contacts), self.filename)
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


    def replace_contactgroups(self, groups, source_db):
        """
        Inserts or updates the specified contact groups in this database.
        """
        if self.is_open() and not self.account and source_db.account:
            self.insert_account(source_db.account)
        if self.is_open() and "contactgroups" not in self.tables:
            self.create_table("contactgroups")
        if self.is_open() and "contactgroups" in self.tables:
            logger.info("Merging %d contact groups into %s.",
                        len(groups), self.filename)
            self.ensure_backup()

            col_data = self.get_table_columns("contactgroups")
            pk = [c["name"] for c in col_data if c["pk"]][0]
            pk_key = "PK%s" % int(time.time())
            fields = [col["name"] for col in col_data if not col["pk"]]
            str_fields = ", ".join(["%s = :%s" % (col, col) for col in fields])
            existing = dict([(c["name"], c) for c in self.get_contactgroups()])
            for c in (x for x in groups if x["name"] in existing):
                c_filled = self.fill_missing_fields(c, fields)
                c_filled[pk_key] = existing[c["name"]][pk]
                self.execute("UPDATE contactgroups SET %s WHERE %s = :%s" %
                             (str_fields, pk, pk_key ), c_filled)

            str_cols = ", ".join(fields)
            str_vals = ":" + ", :".join(fields)
            for c in (x for x in groups if x["name"] not in existing):
                c_filled = self.fill_missing_fields(c, fields)
                c_filled = self.blobs_to_binary(c_filled, fields, col_data)
                self.execute("INSERT INTO contactgroups (%s) VALUES (%s)" %
                             (str_cols, str_vals), c_filled)
            self.connection.commit()
            self.last_modified = datetime.datetime.now()


    def message_iterator(self, lst):
        """
        Yields message rows from the list. If the list consists of message IDs,
        executes queries on the Messages table and yields result rows.
        """
        if not lst:
            return
        if isinstance(lst[0], dict):
            for m in lst:
                yield m
        else:
            for ids in [lst[i:i+999] for i in range(0, len(lst), 999)]:
                # Divide into chunks: SQLite can take up to 999 parameters.
                idstr = ", ".join(":id%s" % (j+1) for j in range(len(ids)))
                s = "id IN (%s)" % idstr
                p = dict(("id%s" % (j+1), x) for j, x in enumerate(ids))
                res = self.get_messages(additional_sql=s, additional_params=p)
                for m in res:
                    yield m


    def update_row(self, table, row, original_row, rowid=None, log=True):
        """
        Updates the table row in the database, identified by its primary key
        in its original values, or the given rowid if table has no primary key.
        """
        if not self.is_open():
            return
        table, where = table.lower(), ""
        if log: logger.info("Updating 1 row in table %s, %s.",
                            self.tables[table]["name"], self.filename)
        self.ensure_backup()
        colmap = {x["name"]: x for x in self.get_table_columns(table)}
        col_data = [colmap[x] for x in row if x in colmap]
        values, where = row.copy(), ""
        setsql = ", ".join("%(name)s = :%(name)s" % x for x in col_data)
        if rowid is not None:
            pk_key = "PK%s" % int(time.time()) # Avoid existing field collision
            where, values[pk_key] = "ROWID = :%s" % pk_key, rowid
        else:
            for pk in [n for n, c in colmap.items() if c["pk"]]:
                pk_key = "PK%s" % int(time.time())
                values[pk_key] = original_row[pk]
                where += (" AND " if where else "") + "%s IS :%s" % (pk, pk_key)
        if not where:
            return False # Sanity check: no primary key and no rowid
        self.execute("UPDATE %s SET %s WHERE %s" % (table, setsql, where),
                     values, log=log)
        self.connection.commit()
        self.last_modified = datetime.datetime.now()


    def insert_row(self, table, row, log=True):
        """
        Inserts the new table row in the database.

        @return  ID of the inserted row
        """
        if not self.is_open():
            return
        table = table.lower()
        if log: logger.info("Inserting 1 row into table %s, %s.",
                            self.tables[table]["name"], self.filename)
        self.ensure_backup()
        col_data = self.get_table_columns(table)
        fields = [col["name"] for col in col_data if col["name"] in row]
        str_cols = ", ".join(fields)
        str_vals = ":" + ", :".join(fields)
        row = self.blobs_to_binary(row, fields, col_data)
        cursor = self.execute("INSERT INTO %s (%s) VALUES (%s)" %
                              (table, str_cols, str_vals), row, log=log)
        self.connection.commit()
        self.last_modified = datetime.datetime.now()
        return cursor.lastrowid


    def delete_row(self, table, row, rowid=None, log=True):
        """
        Deletes the table row from the database. Row is identified by its
        primary key, or by rowid if no primary key.

        @return   success as boolean
        """
        if not self.is_open():
            return
        table, where = table.lower(), ""
        if log: logger.info("Deleting 1 row from table %s, %s.",
                            self.tables[table]["name"], self.filename)
        self.ensure_backup()
        col_data = self.get_table_columns(table)
        values, where = row.copy(), ""
        if rowid is not None:
            pk_key = "PK%s" % int(time.time()) # Avoid existing field collision
            where, values[pk_key] = "ROWID = :%s" % pk_key, rowid
        else:
            for pk in [c["name"] for c in col_data if c["pk"]]:
                pk_key = "PK%s" % int(time.time())
                values[pk_key] = row[pk]
                where += (" AND " if where else "") + "%s IS :%s" % (pk, pk_key)
        if not where:
            return False # Sanity check: no primary key and no rowid
        self.execute("DELETE FROM %s WHERE %s" % (table, where), values, log=log)
        self.connection.commit()
        self.last_modified = datetime.datetime.now()
        return True



class MessageParser(object):
    """A Skype message parser, able to collect statistics from its input."""

    """Maximum line width in characters for text output."""
    TEXT_MAXWIDTH = 79

    """HTML entities in the body to be replaced before feeding to xml.etree."""
    REPLACE_ENTITIES = {"&apos;": "'"}

    """Regex for replacing raw emoticon texts with emoticon tags."""
    EMOTICON_RGX = re.compile("(%s)" % "|".join(
                              s for i in emoticons.EmoticonData.values()
                              for s in map(re.escape, i["strings"])))

    """
    Replacer callback for raw emoticon text, with verification look-ahead.
    Emoticon can be preceded by anything, followed by possible punctuation,
    and must end with whitespace, or string ending, or another emoticon.
    """
    EMOTICON_REPL = lambda self, m: ("<ss type=\"%s\">%s</ss>" % 
        (emoticons.EmoticonStrings[m.group(1)], m.group(1))
        if m.group(1) in emoticons.EmoticonStrings
        and re.match(r"^%s*[%s]*(\s|$)" % (self.EMOTICON_RGX.pattern,
                                           re.escape(".,;:?!'\"")),
                     m.string[m.start(1) + len(m.group(1)):])
        else m.group(1)
    )

    """Regex for checking the existence of any character all emoticons have."""
    EMOTICON_CHARS_RGX = re.compile("[:|()/]")

    """Regex for replacing low bytes unparseable in XML (\x00 etc)."""
    SAFEBYTE_RGX = re.compile("[\x00-\x08,\x0B-\x0C,\x0E-x1F,\x7F]")

    """Replacer callback for low bytes unusable in XML (\x00 etc)."""
    SAFEBYTE_REPL = lambda self, m: m.group(0).encode("unicode-escape")

    """Mapping known failure reason codes to """
    FAILURE_REASONS = {"1": "Failed", "4": "Not enough Skype Credit."}

    """Number of bins in statistics days histogram."""
    HISTOGRAM_DAY_BINS = 10

    """Convenience class for earliest messages in histogram bins."""
    MessageStamp = collections.namedtuple("MessageStamp", "date id")


    def __init__(self, db, chat=None, stats=False, wrapper=None):
        """
        @param   db       SkypeDatabase instance for additional queries
        @param   chat     chat being parsed
        @param   stats    whether to collect message statistics, assumes chat
        @param   wrapper  multi-line text wrap function, if any
        """
        self.db = db
        self.chat = chat
        self.stats = {}
        self.wrapfunc = wrapper
        self.textwrapfunc = textwrap.TextWrapper(width=self.TEXT_MAXWIDTH,
            expand_tabs=False, replace_whitespace=False,
            break_long_words=False, break_on_hyphens=False
        ).wrap # Text format output is wrapped with a fixed-width font
        if stats:
            self.stats = {
                "smses": 0, "transfers": [], "calls": 0, "messages": 0,
                "counts": {}, "total": 0, "startdate": None, "enddate": None,
                "wordclouds": {}, # Per-author
                "wordcloud": [], # [(word, count, size), ]
                "wordcounts": {}, # {word: {author: count, }, }
                "links": {}, # {author: [link, ], }
                "last_cloudtext": "",
                "last_message": "", "chars": 0, "smschars": 0, "files": 0,
                "bytes": 0, "calldurations": 0, "info_items": [],
                "authors": set(), # Authors encountered in parsed messages
                "cloudcounter": wordcloud.GroupCounter(conf.WordCloudLengthMin),
                "totalhist": {}, # Histogram data {"hours", "hours-firsts", "days", ..}}
                "hists": {}, # Author histogram data {author: {"hours", ..} }
                "workhist": {}, # {"hours": {0: {author: count}}, "days": ..}}
                "emoticons": collections.defaultdict(lambda: collections.defaultdict(int)),
                "shared_images": {}} # {message_id: {url, datetime, author, author_name}, }


    def parse(self, message, rgx_highlight=None, output=None):
        """
        Parses the specified Skype message and returns the message body as
        DOM, HTML or TXT.

        @param   message        message data dict
        @param   rgx_highlight  regex for finding text to highlight, if any
        @param   output         dict with output options:
                                "format": "html" returns an HTML string 
                                                 including author and timestamp
                                          "text" returns message body plaintext
                                "wrap": False    whether to wrap long lines
                                "export": False  whether output is for export,
                                                 using another content template
                                "merge": False   for merge comparison, inserts
                                                 skypename instead of fullname
        @return                 a string if html or text specified, 
                                or ElementTree.Element containing message body,
                                with "xml" as the root tag
                                and any number of subtags:
                                (a|b|quote|quotefrom|msgstatus|bodystatus),
        """
        result = dom = None
        output = output or {}
        is_html = "html" == output.get("format")

        if "dom" in message:
            dom = message["dom"] # Cached DOM already exists
        if dom is None:
            dom = self.parse_message_dom(message, output)
            if not (output.get("merge")
            or message["id"] in self.stats.get("shared_images", {})):
                message["dom"] = dom # Cache DOM if it was not mutated

        if dom is not None:
            self.stats and self.collect_message_stats(message, dom)
            if is_html: # Create a copy, HTML will mutate dom
                dom = copy.deepcopy(dom)
                rgx_highlight and self.highlight_text(dom, rgx_highlight)

        if dom is not None and is_html:
            result = self.dom_to_html(dom, output, message)
        elif dom is not None and "text" == output.get("format"):
            result = self.dom_to_text(dom)
            if output.get("wrap"):
                linelists = map(self.textwrapfunc, result.split("\n"))
                ll = "\n".join(j if j else "" for i in linelists for j in i)
                # Force DOS linefeeds
                result = re.sub("([^\r])\n", lambda m: m.group(1) + "\r\n", ll)
        else:
            result = dom

        return result


    def parse_message_dom(self, message, options):
        """
        Parses the body of the Skype message according to message type.

        @param   message  message data dict
        @param   output   output options, {merge: True} has different content
        @return           ElementTree instance
        """
        body = message["body_xml"] or ""
        get_contact_name = self.db.get_contact_name
        get_author_name = self.db.get_author_name
        get_quote_name = lambda x: x.get("authorname") or ""
        if options.get("merge"):           # Use skypename in merge: full name
            get_contact_name = lambda x: x # can be different across databases
            get_author_name = get_quote_name = lambda m: m.get("author") or ""

        for entity, value in self.REPLACE_ENTITIES.items():
            body = body.replace(entity, value)
        body = body.encode("utf-8")
        if (message["type"] == MESSAGE_TYPE_MESSAGE and "<" not in body
        and self.EMOTICON_CHARS_RGX.search(body)):
            # Replace emoticons with <ss> tags if message appears to
            # have no XML (probably in older format).
            body = self.EMOTICON_RGX.sub(self.EMOTICON_REPL, body)
        dom = self.make_xml(body, message)

        if MESSAGE_TYPE_SMS == message["type"] \
        or (MESSAGE_TYPE_INFO == message["type"]
        and "<sms" in message["body_xml"]):
            # SMS body can be plaintext, or can be XML. Relevant tags:
            # <sms alt="It's hammer time."><status>6</status>
            # <failurereason>0</failurereason><targets>
            # <target status="6">+555011235</target></targets><body>
            # <chunk id="0">te</chunk><chunk id="1">xt</chunk></body>
            # <encoded_body>text</encoded_body></sms>
            if dom.find("sms") is not None: # Body is XML data
                if dom.find("*/encoded_body") is not None:
                    # Message has all content in a single element
                    elem = dom.find("*/encoded_body")
                    encoded_body = ElementTree.tostring(elem)
                    body = encoded_body[14:-15] # Drop <encoded_body> tags
                elif dom.find("*/body/chunk") is not None:
                    # Message content is in <body>/<chunk> elements
                    chunks = {}
                    for c in dom.findall("*/body/chunk"):
                        chunks[int(c.get("id"))] = c.text
                    body = "".join([v for k, v in sorted(chunks.items())])
                else:
                    # Fallback, message content is in <sms alt="content"
                    body = dom.find("sms").get("alt")
                body = body.encode("utf-8")
            # Replace text emoticons with <ss>-tags if body not XML.
            if "<" not in body and self.EMOTICON_CHARS_RGX.search(body):
                body = self.EMOTICON_RGX.sub(self.EMOTICON_REPL, body)
            status_text = " SMS"
            status = dom.find("*/failurereason")
            if status is not None and status.text in self.FAILURE_REASONS:
                status_text += ": %s" % self.FAILURE_REASONS[status.text]
            dom = self.make_xml("<msgstatus>%s</msgstatus>%s" %
                                (status_text, body), message)
        elif MESSAGE_TYPE_FILE == message["type"] \
        or (MESSAGE_TYPE_INFO == message["type"]
        and "<files" in message["body_xml"]):
            transfers = self.db.get_transfers()
            files = dict((f["chatmsg_index"], f) for f in transfers
                         if f["chatmsg_guid"] == message["guid"])
            if not files:
                # No rows in Transfers, try to find data from message body
                # and create replacements for Transfers fields
                for f in dom.findall("*/file"):
                    files[int(f.get("index"))] = {
                        "filename": f.text, "filepath": "",
                        "filesize": f.get("size", 0),
                        "partner_handle": message["author"],
                        "partner_dispname": get_author_name(message),
                        "starttime": message["timestamp"],
                        "type": TRANSFER_TYPE_OUTBOUND}
            message["__files"] = [f for i, f in sorted(files.items())]
            dom.clear()
            dom.text = "sent " if MESSAGE_TYPE_INFO == message["type"] \
                       else "Sent "
            dom.text += util.plural("file", files, False) + " "
            for i, f in enumerate(files[i] for i in sorted(files)):
                if len(dom) > 0:
                    a.tail = ", "
                h = util.path_to_url(f["filepath"] or f["filename"])
                a = ElementTree.SubElement(dom, "a", {"href": h})
                a.text = f["filename"]
                a.tail = "" if i < len(files) - 1 else "."
        elif MESSAGE_TYPE_INFO == message["type"] \
        and "<location" in message["body_xml"]:
            href, text = None, None
            for link in dom.getiterator("a"):
                href, text = link.get("href"), link.text
                break # for link
            if href and text:
                dom.clear()
                dom.text = "has shared a location: "
                a = ElementTree.SubElement(dom, "a", {"href": href})
                a.text = text
        elif MESSAGE_TYPE_CONTACTS == message["type"]:
            self.db.get_contacts()
            contacts = sorted(get_contact_name(i.get("f") or i.get("s"))
                              for i in dom.findall("*/c"))
            dom.clear()
            dom.text = "Sent %s " % util.plural("contact", contacts, False)
            for i, c in enumerate(contacts):
                if len(dom) > 0:
                    b.tail = ", "
                b = ElementTree.SubElement(dom, "b")
                b.text = c["name"] if isinstance(c, dict) else c
                b.tail = "" if i < len(contacts) - 1 else "."
        elif MESSAGE_TYPE_TOPIC == message["type"]:
            if dom.text:
                dom.text = "Changed the conversation topic to \"%s\"." \
                           % dom.text
                if not dom.text.endswith("."):
                    dom.text += "."
            else:
                dom.text = "Changed the conversation picture."
        elif message["type"] in (MESSAGE_TYPE_CALL, MESSAGE_TYPE_CALL_END):
            # Durations can either be in both start and end message,
            # or only in end message if it's like '<partlist type="ended" ..'
            do_durations = MESSAGE_TYPE_CALL == message["type"] or \
                           "ended" == (dom.find("partlist") or {}).get("type")
            for elem in dom.getiterator("part") if do_durations else ():
                identity = elem.get("identity")
                duration = elem.findtext("duration")
                if identity and duration:
                    identity = re.sub(r"^\d+\:", "", identity)
                    calldurations = message.get("__calldurations", {})
                    try:
                        calldurations[identity] = float(duration)
                        message["__calldurations"] = calldurations
                    except (TypeError, ValueError):
                        pass
            text = " Call" if MESSAGE_TYPE_CALL == message["type"] else " Call ended"
            if "missed" == (dom.find("partlist") or {}).get("type"):
                text = " Call missed" # <partlist type="missed" ..
            dom.clear()
            ElementTree.SubElement(dom, "msgstatus").text = text
        elif MESSAGE_TYPE_LEAVE == message["type"]:
            dom.clear()
            b = ElementTree.SubElement(dom, "b")
            b.text = get_author_name(message)
            b.tail = " has left the conversation."
        elif MESSAGE_TYPE_INTRO == message["type"]:
            orig = "\n\n" + dom.text if dom.text else ""
            dom.clear()
            b = ElementTree.SubElement(dom, "b")
            b.text = get_author_name(message)
            b.tail = " would like to add you on Skype%s" % orig
        elif message["type"] in [MESSAGE_TYPE_PARTICIPANTS,
        MESSAGE_TYPE_GROUP, MESSAGE_TYPE_BLOCK, MESSAGE_TYPE_REMOVE,
        MESSAGE_TYPE_SHARE_DETAIL]:
            names = sorted(get_contact_name(x) for x in filter(None,
                           (message["identities"] or "").split(" ")))
            dom.clear()
            dom.text = "Added "
            if MESSAGE_TYPE_SHARE_DETAIL == message["type"]:
                dom.text = "Has shared contact details"
                if names: dom.text += " with "
            elif MESSAGE_TYPE_BLOCK == message["type"]:
                dom.text = "Blocked "
            elif MESSAGE_TYPE_GROUP == message["type"]:
                dom.text = "Created a group conversation"
                if names: dom.text += " with "
            for i in names:
                if len(dom) > 0:
                    b.tail = ", "
                b = ElementTree.SubElement(dom, "b")
                b.text = i["name"] if type(i) is dict else i
            if names:
                b.tail = "."
            else:
                dom.text += "."
            if MESSAGE_TYPE_REMOVE == message["type"]:
                if names:
                    dom.text = "Removed "
                    b.tail = " from this conversation."
                else:
                    dom.text = "Removed  from this conversation."
        elif message["type"] in [MESSAGE_TYPE_INFO, MESSAGE_TYPE_MESSAGE,
        MESSAGE_TYPE_SHARE_PHOTO, MESSAGE_TYPE_SHARE_VIDEO, MESSAGE_TYPE_SHARE_VIDEO2] \
        and message["edited_timestamp"] and not message["body_xml"]:
            elm_sub = ElementTree.SubElement(dom, "bodystatus")
            elm_sub.text = MESSAGE_REMOVED_TEXT
        elif MESSAGE_TYPE_SHARE_VIDEO == message["type"]:
            for elm in dom.findall("videomessage"):
                elm.tag = "span"
                sid, link = elm.get("sid"), elm.get("publiclink")
                elm.text = ("%s has shared a video with you" %
                            get_author_name(message))
                if link:
                    elm.text += " - "
                    ElementTree.SubElement(elm, "a", href=link).text = link
                elif sid:
                    elm.text += " - code %s" % sid
        elif message["type"] in [MESSAGE_TYPE_UPDATE_NEED,
        MESSAGE_TYPE_UPDATE_DONE]:
            names = sorted(get_contact_name(x)
                           for x in (message["identities"] or "").split(" "))
            dom.clear()
            b = None
            for n in names:
                if len(dom) > 0:
                    b.tail = ", "
                b = ElementTree.SubElement(dom, "b")
                b.text = n["name"] if type(n) is dict else n
            if b is not None:
                b.tail = " needs to update Skype to participate in this chat."
                if MESSAGE_TYPE_UPDATE_DONE == message["type"]:
                    b.tail = " can now participate in this chat."

        # Photo/video sharing: take image link, if any
        if any(dom.getiterator("URIObject")):
            url = dom.find("URIObject").get("uri")
            link = next(dom.getiterator("a"), None)
            if not url and link:
                url = link.get("href")
            elif not url: # Parse link from message contents
                text = ElementTree.tostring(dom, "utf-8", "text")
                match = re.search(r"(https?://[^\s<]+)", text)
                if match: # Make link clickable
                    url = match.group(0)
                    a = step.Template('<a href="{{u}}">{{u}}</a>').expand(u=url)
                    text2 = text.replace(url, a.encode("utf-8"))
                    dom = self.make_xml(text2, message) or dom
            if url and self.stats:
                self.stats["shared_images"][message["id"]] = dict(url=url,
                    author_name=get_author_name(message), author=message["author"],
                    success=False, datetime=message["datetime"])
            # Sanitize XML tags like Title|Text|Description|..
            dom = self.sanitize(dom, ["a", "b", "i", "s", "ss", "quote", "span"])

        # Process Skype message quotation tags, assembling a simple
        # <quote>text<special>footer</special></quote> element.
        # element
        for quote in dom.findall("quote"):
            quote.text = quote.text or ""
            for i in quote.findall("legacyquote"):
                # <legacyquote> contains preformatted timestamp and author
                if i.tail:
                    quote.text += i.tail
                quote.remove(i)
            footer = get_quote_name(quote)
            if quote.get("timestamp") and quote.get("timestamp").isdigit():
                footer += (", %s" if footer else "%s") % \
                    self.db.stamp_to_date(int(quote.get("timestamp"))
                    ).strftime("%d.%m.%Y %H:%M")
            if footer:
                ElementTree.SubElement(quote, "quotefrom").text = footer
            quote.attrib.clear() # Drop the numerous data attributes
        return dom


    def make_xml(self, text, message):
        """Returns a new xml.etree.cElementTree node from the text."""
        result = None
        TAG = "<xml>%s</xml>"
        try:
            result = ElementTree.fromstring(TAG % text)
        except Exception:
            text = self.SAFEBYTE_RGX.sub(self.SAFEBYTE_REPL, text)
            try:
                result = ElementTree.fromstring(TAG % text)
            except Exception:
                try:
                    text = text.replace("&", "&amp;")
                    result = ElementTree.fromstring(TAG % text)
                except Exception as e:
                    result = ElementTree.fromstring(TAG % "")
                    result.text = text
                    logger.error("Error parsing message %s, body \"%s\" (%s).", 
                                 message["id"], text, e)
        return result


    def highlight_text(self, dom, rgx_highlight):
        """Wraps text matching regex in any dom element in <b> nodes."""
        parent_map = dict((c, p) for p in dom.getiterator() for c in p)
        rgx_highlight_split = re.compile("<b>")
        repl_highlight = lambda x: "<b>%s<b>" % x.group(0) 
        # Highlight substrings in <b>-tags
        for i in dom.getiterator():
            if "b" == i.tag:
                continue # continue for i in dom.getiterator()
            for j, t in enumerate([i.text, i.tail]):
                if not t:
                    continue # continue for j, t in enumerate(..)
                highlighted = rgx_highlight.sub(repl_highlight, t)
                parts = rgx_highlight_split.split(highlighted)
                if len(parts) < 2:
                    continue # continue for j, t in enumerate(..)
                index_insert = (list(parent_map[i]).index(i) + 1) if j else 0
                setattr(i, "tail" if j else "text", "")
                b = None
                for k, part in enumerate(parts):
                    if k % 2: # Text to highlight, wrap in <b>
                        b = ElementTree.Element("b")
                        b.text = part
                        if j: # Processing i.tail
                            parent_map[i].insert(index_insert, b)
                        else: # Processing i.text
                            i.insert(index_insert, b)
                        index_insert += 1
                    else: # Other text, append to tail/text
                        if j: # Processing i.tail
                            if b is not None: #
                                b.tail = part
                            else:
                                i.tail = (i.tail or "") + part
                        else: # Processing i.text
                            if b is not None:
                                b.tail = part
                            else:
                                i.text = part


    def dom_to_html(self, dom, output, message):
        """Returns an HTML representation of the message body."""
        shared_image = self.stats.get("shared_images", {}).get(message["id"])
        if shared_image and output.get("export") \
        and conf.SharedImageAutoDownload and self.db.live.is_logged_in():
            raw = self.db.live.get_api_image(shared_image["url"])
            if raw:
                shared_image["success"] = True
                ns = dict(shared_image, image=raw, message_id=message["id"])
                return step.Template(templates.CHAT_MESSAGE_IMAGE).expand(ns)

        other_tags = ["blink", "font", "span", "table", "tr", "td", "br"]
        greytag, greyattr, greyval = "font", "color", conf.HistoryGreyColour
        if output.get("export"):
            greytag, greyattr, greyval = "span", "class", "gray"
        for elem in dom.getiterator():
            index = 0
            for subelem in elem:
                if "quote" == subelem.tag:
                    # Replace quote tags with a formatted subtable
                    templ = step.Template(templates.MESSAGE_QUOTE)
                    template = templ.expand(export=output.get("export"))
                    template = template.replace("\n", " ").strip()
                    table = ElementTree.fromstring(template)
                    # Select last, content cell
                    cell = table.findall("*/td")[-1]
                    elem_quotefrom = subelem.find("quotefrom")
                    if elem_quotefrom is not None:
                        cell.find(greytag).text += elem_quotefrom.text
                        subelem.remove(elem_quotefrom)
                    cell.text = subelem.text
                    # Insert all children before the last font element
                    len_orig = len(cell)
                    [cell.insert(len(cell) - len_orig, i) for i in subelem]
                    table.tail = subelem.tail
                    elem[index] = table # Replace <quote> element in parent
                elif "ss" == subelem.tag: # Emoticon
                    if output.get("export"):
                        emot, emot_type = subelem.text, subelem.get("type")
                        template, vals = "<span>%s</span>", [emot]
                        if hasattr(emoticons, emot_type):
                            data = emoticons.EmoticonData[emot_type]
                            title = data["title"]
                            if data["strings"][0] != data["title"]:
                                title += " " + data["strings"][0]
                            template = "<span class=\"emoticon %s\" " \
                                       "title=\"%s\">%s</span>"
                            vals = [emot_type, title, emot]
                        span_str = template % tuple(map(cgi.escape, vals))
                        span = ElementTree.fromstring(span_str)
                        span.tail = subelem.tail
                        elem[index] = span # Replace <ss> element in parent
                elif subelem.tag in ["msgstatus", "bodystatus"]:
                    subelem.tag = greytag
                    subelem.set(greyattr, greyval)
                    # Add whitespace before next content
                    subelem.tail = " " + (subelem.tail or "")
                elif subelem.tag in ["b", "i", "s"]:
                    subelem.attrib.clear() # Clear raw_pre and raw_post
                elif "a" == subelem.tag:
                    subelem.set("target", "_blank")
                    if output.get("export"):
                        href = subelem.get("href").encode("utf-8")
                        subelem.set("href", urllib.quote(href, ":/=?&#"))
                    else: # Wrap content in system link colour
                        t = "<font color='%s'></font>" % conf.SkypeLinkColour
                        span = ElementTree.fromstring(t)
                        span.text = subelem.text
                        for i in list(subelem):
                            span.append(i), subelem.remove(i)
                        subelem.text = ""
                        subelem.append(span)
                elif subelem.tag not in other_tags:
                    # Unknown tag: drop if empty, otherwise convert to span
                    if not (subelem.text or subelem.tail):
                        elem.remove(subelem)
                        index -= 1
                    else:
                        subelem.tag = "span"
                        subelem.attrib.clear()
                index += 1
            if not self.wrapfunc:
                continue # continue for elem in dom.getiterator()
            for i, v in enumerate([elem.text, elem.tail]):
                v and setattr(elem, "tail" if i else "text", self.wrapfunc(v))
        try:
            # Discard <?xml ..?><xml> tags from start, </xml> from end
            result = ElementTree.tostring(dom, "UTF-8")[44:-6]
        except Exception as e:
            # If ElementTree.tostring fails, try converting all text
            # content from UTF-8 to Unicode.
            logger.exception("Exception for '%s'.", message["body_xml"])
            for elem in [dom] + dom.findall("*"):
                for attr in ["text", "tail"]:
                    val = getattr(elem, attr)
                    if val and isinstance(val, str):
                        try:
                            setattr(elem, attr, val.decode("utf-8"))
                        except Exception as e:
                            logger.error("Error decoding %s value \"%s\" (type %s)"
                                         " of %s for \"%s\": %s", attr, val,
                                         type(val), elem, message["body_xml"], e)
            try:
                result = ElementTree.tostring(dom, "UTF-8")[44:-6]
            except Exception:
                logger.error("Failed to parse the message \"%s\" from %s.",
                             message["body_xml"], message["author"])
                result = message["body_xml"] or ""
                result = result.replace("<", "&lt;").replace(">", "&gt;")
        # emdash workaround, cElementTree won't handle unknown entities
        result = result.replace("{EMDASH}", "&mdash;") \
                       .replace("\n", "<br />")
        return result


    def dom_to_text(self, dom):
        """Returns a plaintext representation of the message DOM."""
        text, tail = dom.text or "", dom.tail or ""
        if "quote" == dom.tag:
            text = "\"" + text
        elif "quotefrom" == dom.tag:
            text = "\"\r\n%s\r\n" % text
        elif "msgstatus" == dom.tag:
            text = "[%s]\r\n" % text.strip()
        elif dom.tag in ["i", "b", "s"]: # italic bold strikethrough
            pre = post = dict(i="_", b="*", s="~")[dom.tag]
            if dom.get("raw_pre"): pre = dom.get("raw_pre")
            if dom.get("raw_post"): post = dom.get("raw_post")
            text, tail = pre + text, post + tail
        return text + "".join(self.dom_to_text(x) for x in dom) + tail


    def sanitize(self, dom, known_tags):
        """Turns unknown tags to span, drops empties and unnests single root."""
        parent_map = dict((c, p) for p in dom.getiterator() for c in p)
        blank = lambda x: not (x.text or x.tail or x.getchildren())
        drop = lambda p, c: (p.remove(c), blank(p) and drop(parent_map[p], p))

        def process_node(node, last=None):
            for child in node.getchildren():
                if child.tag not in known_tags:
                    child.attrib, child.tag = {}, "span"
                process_node(child)
                if child.text or child.getchildren(): last = child
                else:
                    if child.tail: # Not totally empty: hang tail onto previous
                        if last: last.tail = (last.tail or "") + child.tail
                        else:    node.text = (node.text or "") + child.tail
                    try: drop(node, child) # Recursively drop empty node from parent
                    except Exception: pass

        process_node(dom)
        while len(dom) == 1 and "span" == dom[0].tag and not dom[0].tail:
            dom, dom.tag = dom[0], dom.tag # Collapse single spans to root
        return dom


    def add_dict_text(self, dictionary, key, text, inter=" "):
        """Adds text to an entry in the dictionary."""
        dictionary[key] += (inter if dictionary[key] else "") + text


    def collect_message_stats(self, message, dom):
        """Adds message statistics to accumulating data."""
        author_stats = collections.defaultdict(lambda: 0)
        self.stats["startdate"] = self.stats["startdate"] or message["datetime"]
        self.stats["enddate"] = message["datetime"]
        author = message["author"]
        if author in AUTHORS_SPECIAL:
            return
        self.stats["authors"].add(author)
        self.stats["total"] += 1
        self.stats["last_message"] = ""
        if message["type"] in [MESSAGE_TYPE_SMS, MESSAGE_TYPE_MESSAGE]:
            self.collect_dom_stats(dom, message)
            self.stats["cloudcounter"].add_text(self.stats["last_cloudtext"],
                                                author)
            self.stats["last_cloudtext"] = ""
            message["body_txt"] = self.stats["last_message"] # Export kludge
        if (message["type"] in [MESSAGE_TYPE_SMS, MESSAGE_TYPE_CALL,
        MESSAGE_TYPE_CALL_END, MESSAGE_TYPE_FILE, MESSAGE_TYPE_MESSAGE]
        and author not in self.stats["counts"]):
            self.stats["counts"][author] = author_stats.copy()
        hourkey, daykey = message["datetime"].hour, message["datetime"].date()
        if not self.stats["workhist"]:
            MAXSTAMP = MessageParser.MessageStamp(
                datetime.datetime(9999, 12, 31, 23, 59, 59), sys.maxint)
            intdict = lambda: collections.defaultdict(int)
            stampdict = lambda: collections.defaultdict(lambda: MAXSTAMP)
            self.stats["workhist"] = {
                "hours": collections.defaultdict(intdict),
                "days": collections.defaultdict(intdict),
                "hours-firsts": collections.defaultdict(stampdict),
                "days-firsts": collections.defaultdict(stampdict), }
        stamp = MessageParser.MessageStamp(message["datetime"], message["id"])
        for name, key in [("hours", hourkey), ("days", daykey)]:
            self.stats["workhist"][name][key][author] += 1
            histobin = self.stats["workhist"][name + "-firsts"][author]
            if histobin[key] > stamp: histobin[key] = stamp
            
        len_msg = len(self.stats["last_message"])
        if MESSAGE_TYPE_SMS == message["type"]:
            self.stats["smses"] += 1
            self.stats["counts"][author]["smses"] += 1
            self.stats["counts"][author]["smschars"] += len_msg
        elif message["type"] in (MESSAGE_TYPE_CALL, MESSAGE_TYPE_CALL_END):
            if MESSAGE_TYPE_CALL == message["type"]:
                self.stats["calls"] += 1
                self.stats["counts"][author]["calls"] += 1
            calldurations = message.get("__calldurations", {})
            for identity, duration in calldurations.items():
                if identity not in self.stats["counts"]:
                    self.stats["counts"][identity] = author_stats.copy()
                self.stats["counts"][identity]["calldurations"] += duration
            if calldurations:
                self.stats["calldurations"] += max(calldurations.values())
        elif MESSAGE_TYPE_FILE == message["type"]:
            files = message.get("__files")
            if files is None:
                transfers = self.db.get_transfers()
                filedict = dict((f["chatmsg_index"], f) for f in transfers
                                if f["chatmsg_guid"] == message["guid"])
                files = [f for i, f in sorted(filedict.items())]
                message["__files"] = files
            for f in files: f["__message_id"] = message["id"]
            self.stats["transfers"].extend(files)
            self.stats["counts"][author]["files"] += len(files)
            size_files = sum([util.try_until(lambda: int(i["filesize"]))[1] or 0
                              for i in files])
            self.stats["counts"][author]["bytes"] += size_files
        elif MESSAGE_TYPE_MESSAGE == message["type"]:
            self.stats["messages"] += 1
            self.stats["counts"][author]["messages"] += 1
            self.stats["counts"][author]["chars"] += len_msg


    def collect_dom_stats(self, dom, message, tails_new=None):
        """Updates current statistics with data from the message DOM."""
        to_skip = {} # {element to skip: True, }
        tails_new = {} if tails_new is None else tails_new
        for elem in dom.getiterator():
            if elem in to_skip:
                continue
            text = elem.text or ""
            tail = tails_new[elem] if elem in tails_new else (elem.tail or "")
            if type(text) is str:
                text = text.decode("utf-8")
            if type(tail) is str:
                tail = tail.decode("utf-8")
            subitems = []
            if "quote" == elem.tag:
                self.add_dict_text(self.stats, "last_cloudtext", text)
                self.add_dict_text(self.stats, "last_message", text)
                subitems = elem.getchildren()
            elif "a" == elem.tag:
                self.stats["links"].setdefault(message["author"], []).append(text)
                self.add_dict_text(self.stats, "last_message", text)
            elif "ss" == elem.tag:
                self.stats["emoticons"][elem.get("type")][message["author"]] += 1
            elif "quotefrom" == elem.tag:
                self.add_dict_text(self.stats, "last_message", text)
            elif elem.tag in ["xml", "i", "b", "s"]:
                self.add_dict_text(self.stats, "last_cloudtext", text)
                self.add_dict_text(self.stats, "last_message", text)
            for i in subitems:
                self.collect_dom_stats(i, message, tails_new)
                to_skip[i] = True
            if tail:
                self.add_dict_text(self.stats, "last_cloudtext", tail)
                self.add_dict_text(self.stats, "last_message", tail)


    def get_collected_stats(self):
        """
        Returns the statistics collected during message parsing.

        @return  dict with statistics entries, or empty dict if not collecting
        """
        if not self.stats or self.stats["wordclouds"]:
            return self.stats
        stats = self.stats
        for k in ["chars", "smschars", "files", "bytes", "calls"]:
            stats[k] = sum(i[k] for i in stats["counts"].values())

        del stats["info_items"][:]
        delta_date = None
        if stats["enddate"] and stats["startdate"]:
            delta_date = stats["enddate"] - stats["startdate"]
            if delta_date.days:
                period_value = "%s - %s (%s)" % \
                               (stats["startdate"].strftime("%d.%m.%Y"),
                                stats["enddate"].strftime("%d.%m.%Y"),
                                util.plural("day", delta_date.days))
            else:
                period_value = stats["startdate"].strftime("%d.%m.%Y")
            stats["info_items"].append(("Time period", period_value))
        if stats["messages"]:
            msgs_value  = "%d (%s)" % (stats["messages"],
                          util.plural("character", stats["chars"]))
            stats["info_items"].append(("Messages", msgs_value))
        if stats["smses"]:
            smses_value  = "%d (%s)" % (stats["smses"],
                           util.plural("character", stats["smschars"]))
            stats["info_items"].append(("SMSes", smses_value))
        if stats["calls"]:
            calls_value  = "%d (%s)" % (stats["calls"],
                           util.format_seconds(stats["calldurations"]))
            stats["info_items"].append(("Calls", calls_value))
        if stats["transfers"]:
            files_value  = "%d (%s)" % (len(stats["transfers"]),
                           util.format_bytes(stats["bytes"]))
            stats["info_items"].append(("Files", files_value))

        if delta_date is not None:
            per_day = util.safedivf(stats["messages"], delta_date.days + 1)
            if stats["messages"] and not round(per_day, 1):
                per_day = "<1"
            else:
                per_day = util.round_float(per_day)
            stats["info_items"].append(("Messages per day", per_day))

            # Fill author and chat hourly histogram
            histbase = {"hours": dict((x, 0) for x in range(24)), "days": {},
                        "hours-firsts": {}, "days-firsts": {}}
            stats["totalhist"] = copy.deepcopy(histbase)
            stats["hists"] = {}
            # Fill total histogram hours and initialize author hour structures
            for hour, counts in stats["workhist"]["hours"].items():
                for author in stats["authors"]:
                    if author not in stats["hists"]:
                        stats["hists"][author] = copy.deepcopy(histbase)
                    if author in counts:
                        stats["hists"][author]["hours"][hour] += counts[author]
                        stats["totalhist"]["hours"][hour] += counts[author]
            # Assemble total hourly histogram earliest messages
            hourstamps = stats["workhist"]["hours-firsts"]
            for hour in range(24):
                stamps = [x[hour] for x in hourstamps.values() if hour in x]
                if stamps:
                    stats["totalhist"]["hours-firsts"][hour] = min(stamps).id
            # Assemble author hourly histograms earliest messages
            for author, stamps in hourstamps.items():
                authorstamps = dict((k, v.id) for k, v in stamps.items())
                stats["hists"][author]["hours-firsts"] = authorstamps

            days_per_bin = float(delta_date.days) / self.HISTOGRAM_DAY_BINS
            step = datetime.timedelta(max(1, int(math.ceil(days_per_bin))))
            # Initialize total histogram day and author day structures
            for i in range(self.HISTOGRAM_DAY_BINS):
                bindate = (stats["startdate"] + step * i).date()
                stats["totalhist"]["days"][bindate] = 0
                for author in stats["hists"]:
                    stats["hists"][author]["days"][bindate] = 0
            max_bindate = max(stats["totalhist"]["days"])
            # Fill total histogram and author days
            MAXSTAMP = MessageParser.MessageStamp(
                datetime.datetime(9999, 12, 31, 23, 59, 59), sys.maxint)
            stampfactory = lambda: collections.defaultdict(lambda: MAXSTAMP)
            daystamps = collections.defaultdict(stampfactory)
            for date, counts in sorted(stats["workhist"]["days"].items()):
                bindate = stats["startdate"].date()
                while bindate + step <= date: bindate += step
                bindate = min(bindate, max_bindate)
                for author, count in counts.items():
                    if author not in stats["hists"]:
                        stats["hists"][author] = copy.deepcopy(histbase)
                    if bindate not in stats["hists"][author]["days"]:
                        stats["hists"][author]["days"][bindate] = 0
                    stats["hists"][author]["days"][bindate] += count
                    stats["totalhist"]["days"][bindate] += count
                    stamp = stats["workhist"]["days-firsts"][author].get(date)
                    if stamp:
                        daystamps[author][bindate] = \
                            min(stamp, daystamps[author][bindate])
            # Assemble total hourly histogram earliest messages
            for i in range(self.HISTOGRAM_DAY_BINS):
                date = (stats["startdate"] + step * i).date()
                stamps = [x[date] for x in daystamps.values() if date in x]
                if stamps:
                    stats["totalhist"]["days-firsts"][date] = min(stamps).id
            # Assemble author hourly histograms earliest messages
            for author, stamps in daystamps.items():
                authorstamps = dict((k, v.id) for k, v in stamps.items())
                stats["hists"][author]["days-firsts"] = authorstamps

        # Create main cloudtext
        options = {"COUNT_MIN": conf.WordCloudCountMin, 
                   "WORDS_MAX": conf.WordCloudWordsMax}
        for author, links in stats["links"].items():
            stats["cloudcounter"].add_words(links, author)
        stats["wordcloud"] = stats["cloudcounter"].cloud(options=options)

        # Create author cloudtexts, scaled to max word count in main cloud
        options.update(SCALE=max([x[1] for x in stats["wordcloud"]] or [0]),
                       WORDS_MAX=conf.WordCloudWordsAuthorMax,
                       FONTSIZE_MAX=wordcloud.FONTSIZE_MAX - 1) # 1 step smaller
        for author in stats["authors"]:
            cloud = stats["cloudcounter"].cloud(author, options)
            stats["wordclouds"][author] = cloud

        # Accumulate word counts for main cloud hovertexts
        stats["wordcounts"] = collections.defaultdict(dict)
        words = set(x[0] for x in stats["wordcloud"])
        [words.update(y[0] for y in x) for x in stats["wordclouds"].values()]
        for author in stats["authors"]:
            for w, c in stats["cloudcounter"].counts(author, words).items():
                stats["wordcounts"][w][author] = c

        return stats



def is_skype_database(filename, path=None):
    """Returns whether the file looks to be a Skype database file."""
    result, conn = False, None
    try:
        filename = os.path.join(path, filename) if path else filename
        conn = sqlite3.connect(filename)
        [conn.execute("SELECT id FROM %s LIMIT 1" % x)
         for x in "Accounts", "Conversations", "Messages"]
        result = True
    except Exception:
        logger.exception("Error checking database %s.", filename)
    finally:
        conn and conn.close()

    return result


def is_sqlite_file(filename, path=None):
    """Returns whether the file looks to be an SQLite database file."""
    result = ".db" == filename[-3:].lower()
    if result:
        try:
            fullpath = os.path.join(path, filename) if path else filename
            result = bool(os.path.getsize(fullpath))
            if result:
                result = False
                SQLITE_HEADER = "SQLite format 3\00"
                with open(fullpath, "rb") as f:
                    result = (f.read(len(SQLITE_HEADER)) == SQLITE_HEADER)
        except Exception: pass
    return result


def detect_databases(progress):
    """
    Tries to detect Skype database files on the current computer, looking
    under "Documents and Settings", and other potential locations.

    @param   progress  callback function returning whether task should continue
    @yield             each value is a list of detected database paths
    """
    # First, search system directories for main.db files.
    if "nt" == os.name:
        search_paths = [os.path.join(os.getenv("APPDATA"), "Skype")]
        c = os.getenv("SystemDrive") or "C:"
        for path in ["%s\\Users" % c, "%s\\Documents and Settings" % c]:
            if os.path.exists(path):
                search_paths.append(path)
                break # break for path in [..]
    else:
        search_paths = [os.getenv("HOME"),
                        "/Users" if "mac" == os.name else "/home"]
    search_paths = map(util.to_unicode, search_paths)

    WINDOWS_APPDIRS = ["application data", "roaming"]
    for search_path in filter(os.path.exists, search_paths):
        logger.info("Looking for Skype databases under %s.", search_path)
        for root, dirs, files in os.walk(search_path):
            if progress and not progress(): return
            if os.path.basename(root).lower() in WINDOWS_APPDIRS:
                # Skip all else under "Application Data" or "AppData\Roaming".
                dirs[:] = [x for x in dirs if "skype" == x.lower()]
            results = []
            for f in files:
                if progress and not progress(): break # for f
                if "main.db" == f.lower() and is_skype_database(f, root):
                    results.append(os.path.realpath(os.path.join(root, f)))
            if results: yield results
    if progress and not progress(): return

    # Then search current working directory for *.db files.
    search_path = util.to_unicode(os.getcwd())
    logger.info("Looking for Skype databases under %s.", search_path)
    for root, dirs, files in os.walk(search_path):
        if progress and not progress(): return
        results = []
        for f in files:
            if progress and not progress(): break # for f
            if is_skype_database(f, root):
                results.append(os.path.realpath(os.path.join(root, f)))
        if results: yield results


def find_databases(folder):
    """Yields a list of all SQLite databases under the specified folder."""
    for root, dirs, files in os.walk(folder):
        for f in (x for x in files if is_sqlite_file(x, root)):
            yield os.path.join(root, f)


def get_avatar(datadict, size=None, aspect_ratio=True):
    """
    Returns a wx.Bitmap for the contact/account avatar, if any.

    @param   datadict      row from Contacts or Accounts
    @param   size          (width, height) to resize image to, if any
    @param   aspect_ratio  if True, keeps image aspect ratio is on resizing,
                           filling the outside in white
    """
    result = None
    raw = fix_image_raw(datadict.get("avatar_image") or 
                        datadict.get("profile_attachments") or "")
    if raw:
        try:
            img = wx.Image(cStringIO.StringIO(raw))
            if size and list(size) != list(img.GetSize()):
                img = util.img_wx_resize(img, size, aspect_ratio)
            result = img.ConvertToBitmap()
        except Exception:
            logger.exception("Error loading avatar image for %s.",
                             datadict["skypename"])
    return result


def get_avatar_raw(datadict, size=None, aspect_ratio=True, format="PNG"):
    """
    Returns the contact/account avatar image, if any, as raw encoded image.

    @param   datadict      row from Contacts or Accounts
    @param   size          (width, height) to resize larger image down to,
                           if any
    @param   aspect_ratio  if True, keeps image aspect ratio is on resizing,
                            filling the outside in white
    @param   format        image format type as supported by PIL or wx
    """
    result = fix_image_raw(datadict.get("avatar_image") or
                           datadict.get("profile_attachments") or "")
    if result and (size or format):
        try:
            result = util.img_recode(result, format, size, aspect_ratio)
        except Exception:
            logger.exception("Error creating avatar for %s.", datadict["skypename"])
    return result


def fix_image_raw(raw):
    """Returns the raw image bytestream with garbage removed from front."""
    JPG_HEADER = "\xFF\xD8\xFF\xE0\x00\x10JFIF"
    PNG_HEADER = "\x89PNG\r\n\x1A\n"
    if isinstance(raw, unicode):
        raw = raw.encode("latin1")
    if JPG_HEADER in raw:
        raw = raw[raw.index(JPG_HEADER):]
    elif PNG_HEADER in raw:
        raw = raw[raw.index(PNG_HEADER):]
    elif raw.startswith("\0"):
        raw = raw[1:]
        if raw.startswith("\0"):
            raw = "\xFF" + raw[1:]
    return raw



"""
Information on Skype database tables (unreliable, mostly empirical):

Accounts       - one row with user profile information
Alerts         - alerts from Skype payments, Facebook etc
CallMembers    - participants in Skype calls
Calls          - Skype phone calls
ChatMembers    - may be unused, migration from old *.dbb files on Skype upgrade
Chats          - some sort of a bridge between Conversations and Messages
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
  chatmsg_type    NULL: any type also can be NULL (NB!),
                  1:    add participant (type 10),
                        identities has space-separated list)
                  2:    type 10: add participant (identities has
                        space-separated list)
                        type 100: notice that a file transfer was offered
                  3:    ordinary message (type 61)
                  4:    "%name has left" (type 13)
                  5:    set conversation topic (type 2)
                  6:    file accepting (type 100)
                  7:    file transfer, SMS, or "/me laughs", or others
                        (type 60, 64, 68, 201)
                        if transfer, Messages.guid == Transfers.chatmsg_guid
                  8:    sent contacts (body_xml has contacts XML) (type 63)
                  11:   "%name removed %name from this conversation." (type 12)
                  15:   "%name has changed the conversation picture" (type 2)
                  18:   different call/contact things (type 30, 39, 51, 68)

  type            2:    set topic or picture (chatmsg_type 5, 15)
                  4:    "#author created a group conversation with #identities.
                        Show group conversation" (chatmsg_type NULL)
                  8:    "%name can now participate in this chat."
                        (chatmsg_type NULL)
                  9:    "%name needs to update Skype to participate in this chat."
                        (chatmsg_type NULL)
                  10:   added participant (chatmsg_type 1, 2)
                  12:   sent contacts (chatmsg_type 11)
                  13:   "%name has left" (chatmsg_type 4)
                  30:   call (chatmsg_type 18). body_xml can have
                        participants XML.
                  39:   call ended (chatmsg_type 18)
                  50:   intro message, "wish to add you to my contacts"
                        (chatmsg_type NULL). body_xml can have display message.
                        Seems received when one or other adds on request?
                  51:   "%name has shared contact details with %myname."
                        (chatmsg_type 18)
                  53:   blocking contacts in #identities
                  60:   various info messages (chatmsg_type 7),
                        e.g. "has sent a file to x, y, ..", or "/me laughs"
                  61:   ordinary message (chatmsg_type 7)
                  63:   sent contacts (chatmsg_type 8)
                  64:   SMS (chatmsg_type 7)
                  68:   file transfer (chatmsg_type 7)
                  70:   video sharing (chatmsg_type NULL)
                  100:  file sending and accepting (chatmsg_type 2, 6)
                  110:  birthday alert (chatmsg_type NULL)
                  201:  photo sharing (chatmsg_type 7)
  edited_timestamp      if set, message has been edited; if body_xml is empty,
                        message has been deleted

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
  type            1:    partner_handle is sending
                  2:    partner_handle is receiving


Videos:
  convo_id        foreign key on Calls.id
"""
