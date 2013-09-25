# -*- coding: utf-8 -*-
"""
Functionality for exporting Skype data to external files.

------------------------------------------------------------------------------
This file is part of Skyperious - a Skype database viewer and merger.
Released under the MIT License.

@author      Erki Suurjaak
@created     13.01.2012
@modified    16.09.2013
------------------------------------------------------------------------------
"""
import cStringIO
import csv
import datetime
import os
import re
import traceback
import wx

from third_party import step

import conf
import emoticons
import main
import skypedata
import templates
import util


def export_chat(chat, messages, filename, db):
    """
    Exports the chat messages to file.

    @param   chat      chat data dict, as returned from SkypeDatabase
    @param   messages  list of message data dicts
    @param   filename  full path and filename of resulting file, file extension
                       .html|.txt determines file format
    @param   db        SkypeDatabase instance
    """
    result = False
    f = None
    try:
        is_html = filename.lower().endswith(".html")
        is_csv  = filename.lower().endswith(".csv")
        is_txt  = filename.lower().endswith(".txt")
        parser = skypedata.MessageParser(db, chat=chat, stats=is_html)

        if is_html or is_txt:
            namespace = {"db": db, "chat": chat, "messages": messages,
                         "parser": parser}

        if is_html:
            # Collect chat and participant images.
            namespace.update({"chat_picture": None, "chat_picture_raw": None,
                              "participants": [], })
            if chat["meta_picture"]:
                raw = skypedata.fix_image_raw(chat["meta_picture"])
                img = wx.ImageFromStream(cStringIO.StringIO(raw))
                namespace["chat_picture"] = img
                namespace["chat_picture_raw"] = raw
            for p in chat["participants"]:
                contact = p["contact"].copy()
                namespace["participants"].append(contact)
                contact.update(avatar_image_raw="", avatar_image_large_raw="")
                bmp = contact.get("avatar_bitmap")
                if not bmp:
                    bmp = skypedata.get_avatar(contact, conf.AvatarImageSize)
                    if bmp:
                        p["contact"]["avatar_bitmap"] = bmp # Cache resized
                if bmp:
                    s = conf.AvatarImageLargeSize
                    raw_large = skypedata.get_avatar_jpg(contact, s)
                    contact["avatar_image_raw"] = util.bitmap_to_raw(bmp)
                    contact["avatar_image_large_raw"] = raw_large

        if is_csv:
            dialect = csv.excel
            # Delimiter for Excel dialect "," is actually not used by Excel.
            # Default linefeed "\r\n" would cause another "\r" to be written.
            dialect.delimiter, dialect.lineterminator = ";", "\r"
            f = open(filename, "w")
            csv_writer = csv.writer(f, dialect)
            csv_writer.writerow(["Time", "Author", "Message"])

            for m in messages:
                parsed_text = parser.parse(m, text=True)
                try:
                    parsed_text = parsed_text.decode("utf-8")
                except Exception, e:
                    pass
                values = [m["datetime"].strftime("%Y-%m-%d %H:%M:%S"),
                          m["from_dispname"], parsed_text, ]
                values = [v.encode("latin1", 'replace') for v in values]
                csv_writer.writerow(values)
            f.close()
        else:
            # Cannot keep all messages in memory at once - very large chats
            # (500,000+ messages) can take gigabytes.
            # As HTML and TXT contain statistics in their headers before
            # messages, write out all messages to a temporary file first,
            # statistics will be available for the main file after parsing.
            tmpname = util.unique_path("%s.messages" % filename)
            tmpfile = open(tmpname, "w+")
            mtemplate = templates.CHAT_MESSAGES_HTML if is_html \
                        else templates.CHAT_MESSAGES_TXT
            step.Template(mtemplate, strip=False).stream(tmpfile, namespace)

            namespace["stats"] = stats = parser.get_collected_stats()
            namespace.update({
                "date1": stats["startdate"].strftime("%d.%m.%Y")
                         if stats.get("startdate") else "",
                "date2": stats["enddate"].strftime("%d.%m.%Y")
                         if stats.get("enddate") else "",
                "message_count":  stats.get("messages", 0),
                "emoticons_used": filter(lambda e: hasattr(emoticons, e),
                                         parser.emoticons_unique),
            })

            tmpfile.flush(), tmpfile.seek(0)
            namespace["message_buffer"] = iter(lambda: tmpfile.read(65536), '')
            template = templates.CHAT_HTML if is_html else templates.CHAT_TXT
            with open(filename, "w") as f:
                step.Template(template, strip=False).stream(f, namespace)
            tmpfile.close()
            util.try_until(lambda: os.unlink(tmpname), count=1)

        result = True
    except Exception, e:
        main.log("Error exporting to %s.\n\n%s", filename,
                 traceback.format_exc())
        if f: util.try_until(lambda: f.close(), count=1)
        raise
    return result


def export_grid(grid, filename, title, db, sql_query="", table=""):
    """
    Exports the current contents of the specified wx.Grid to file.

    @param   grid       a wx.Grid object
    @param   filename   full path and filename of resulting file, file extension
                        .html|.csv|.sql determines file format
    @param   title      title used in HTML
    @param   db         SkypeDatabase instance
    @param   sql_query  the SQL query producing the grid contents, if any
    @param   table      name of the table producing the grid contents, if any
    """
    result = False
    f = None
    is_html = filename.lower().endswith(".html")
    is_csv  = filename.lower().endswith(".csv")
    is_sql  = filename.lower().endswith(".sql")
    try:
        with open(filename, "w") as f:
            columns = [c["name"] for c in grid.Table.columns]

            def iter_rows():
                """Iterating row generator."""
                row, index = grid.Table.GetRow(0), 0
                while row:
                    yield row
                    index += 1; row = grid.Table.GetRow(index)

            if is_csv:
                dialect = csv.excel
                # Delimiter for Excel dialect "," is actually not used by Excel.
                # Default linefeed "\r\n" would cause another "\r" to be written.
                dialect.delimiter, dialect.lineterminator = ";", "\r"
                csv_writer = csv.writer(f, dialect)
                if sql_query:
                    replaced = sql_query.replace("\r", " ").replace("\n", " ")
                    top = ["SQL: %s" % replaced.encode("latin1", 'replace')]
                    csv_writer.writerow(top)
                header = [c.encode("latin1", "replace") for c in columns]
                csv_writer.writerow(header)

                for row in iter_rows():
                    values = []
                    for col in columns:
                        val = "" if row[col] is None else row[col]
                        val = val if isinstance(val, unicode) else str(val)
                        values.append(val.encode("latin1", "replace"))
                    csv_writer.writerow(values)
            else:
                namespace = {
                    "db_filename": db.filename,
                    "title":       title,
                    "columns":     columns,
                    "row_count":   grid.NumberRows,
                    "rows":        iter_rows(),
                    "sql":         sql_query,
                    "table":       table,
                    "app":         conf.Title,
                }
                if is_sql and table:
                    # Add CREATE TABLE statement.
                    create_sql = db.tables[table.lower()]["sql"] + ";"
                    re_sql = re.compile("^(CREATE\s+TABLE\s+)", re.IGNORECASE)
                    replacer = lambda m: ("%sIF NOT EXISTS " % m.group(1))
                    namespace["create_sql"] = re_sql.sub(replacer, create_sql)

                template = templates.GRID_HTML if is_html else templates.SQL_TXT
                step.Template(template, strip=False).stream(f, namespace)

            f.close()
            result = True
    except Exception, e:
        main.log("Error exporting to %s.\n\n%s", filename,
                 traceback.format_exc())
        if f: util.try_until(lambda: f.close(), count=1)
        raise
    return result
