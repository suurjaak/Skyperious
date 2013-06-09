# -*- coding: utf-8 -*-
"""
Functionality for exporting Skype data to external files.

@author      Erki Suurjaak
@created     13.01.2012
@modified    31.05.2013
"""
import cStringIO
import csv
import datetime
import os
import re
import tempfile
import traceback
import wx

import conf
import main
import skypedata
import step
import templates


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

        parser = skypedata.MessageParser(db, stats=is_html, chat=chat)
        chat_title = chat["title_long_lc"]
        namespace = {
            "db":               db,
            "chat":             chat,
            "messages":         messages,
            "parser":           parser,
            "date1":            messages[0]["datetime"].strftime("%d.%m.%Y") \
                                if len(messages) else "",
            "date2":            messages[-1]["datetime"].strftime("%d.%m.%Y") \
                                if len(messages) else "",
            "chat_picture":     None,
            "chat_picture_raw": None,
            "stats":            None,
        }
        if is_html:
            namespace["participants"] = []
            # Write HTML header and table header
            if chat["meta_picture"]:
                raw = skypedata.fix_raw(chat["meta_picture"])
                img = wx.ImageFromStream(cStringIO.StringIO(raw))
                namespace["chat_picture"] = img
                namespace["chat_picture_raw"] = raw
            if chat["participants"]:    
                for p in chat["participants"]:
                    c = p["contact"].copy()
                    namespace["participants"].append(c)
                    c["avatar_image_raw"], c["avatar_image_small_raw"] = "", ""
                    if c.get("avatar_image", None):
                        if "avatar_bitmap" not in c:
                            bmp = skypedata.bitmap_from_raw(
                                  c["avatar_image"], conf.AvatarImageSize)
                            c["avatar_bitmap"] = bmp
                            p["contact"]["avatar_bitmap"] = bmp # Cache resized

                        raw = skypedata.fix_raw(c["avatar_image"])
                        c["avatar_image_raw"] = raw

                        # Create small avatar image for statistics
                        try:
                            fd, fn_bmp = tempfile.mkstemp()
                            os.close(fd)
                            bmp = c["avatar_bitmap"]
                            bmp.SaveFile(fn_bmp, wx.BITMAP_TYPE_JPEG)
                            raw_small = open(fn_bmp, "rb").read()
                            c["avatar_image_small_raw"] = raw_small
                            os.unlink(fn_bmp)
                        except:
                            main.log("Failed to write temporary avatar file "
                                     "for contact %s.\n%s",
                                     c["identity"], traceback.format_exc())

            for m in messages:
                parser.parse(m)
            namespace["stats"] = parser.get_collected_stats()
            parser.stats = False # Statistics retrieved, disable collecting
        elif is_csv:
            # Initialize CSV writer and write header row
            dialect = csv.excel
            # Default is "," which is actually not Excel
            dialect.delimiter = ";"
            # Default is "\r\n", which causes another "\r" to be written
            dialect.lineterminator = "\r"
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
                    m["from_dispname"].encode("utf-8"),
                    parsed_text.encode("utf-8")
                ]
                csv_writer.writerow(values)
            f.close()

        if is_txt or is_html:
            template = templates.CHAT_HTML if is_html else templates.CHAT_TXT
            s = step.Template(template, strip=is_html).expand(namespace)
            with open(filename, "w") as f:
                f.write(s.encode("utf-8"))
        result = True
    except Exception, e:
        if f:
            f.close()
        main.log("Export cannot access %s.\n%s", filename,
            traceback.format_exc()
        )
    return result


def export_grid(grid, filename, title, db, sql="", table=""):
    """
    Exports the current contents of the specified wx.Grid to file.

    @param   grid      a wx.Grid object
    @param   filename  full path and filename of resulting file, file extension
                       .html|.csv|.sql determines file format
    @param   title     title used in HTML
    @param   db        SkypeDatabase instance
    @param   sql       the SQL query producing the grid contents, if any
    @param   table     name of the table producing the grid contents, if any
    """
    result = False
    f = None
    try:
        if sql: # not related to is_sql
            sql = sql.encode("utf-8")
        with open(filename, "w") as f:
            is_html = filename.lower().endswith(".html")
            is_csv  = filename.lower().endswith(".csv")
            is_sql  = filename.lower().endswith(".sql")
            columns = [c["name"].encode("utf-8") for c in grid.Table.columns]
            namespace = {
                "db_filename": db.filename,
                "title":       title,
                "columns":     columns,
                "rows":        [],
                "sql":         sql,
                "table":       table,
                "app":         conf.Title,
            }

            if is_csv:
                dialect = csv.excel
                dialect.delimiter = ";" # Default is "," which is actually not Excel
                # Default is "\r\n", which causes another "\r" to be written
                dialect.lineterminator = "\r"
                csv_writer = csv.writer(f, dialect)
                if sql:
                    csv_writer.writerow(["SQL: %s" \
                        % sql.replace("\r", " ").replace("\n", " ")])
                csv_writer.writerow(columns)
            elif is_sql and table:
                # Add CREATE TABLE statement.
                create_sql = db.tables[table.lower()]["sql"] + ";"
                re_sql = re.compile(
                    "^(CREATE\s+TABLE\s+)", re.IGNORECASE | re.MULTILINE)
                create_sql = re_sql.sub(
                    lambda m: "%sIF NOT EXISTS " % m.group(1), create_sql)
                namespace["create_sql"] = create_sql

            for i in range(grid.NumberRows):
                data = grid.Table.GetRow(i)
                values = []
                if is_csv:
                    for col_name in columns:
                        if isinstance(data[col_name], unicode):
                            values.append(data[col_name].encode("utf-8"))
                        elif data[col_name] is None:
                            values.append("")
                        else:
                            values.append(str(data[col_name]))
                    csv_writer.writerow(values)
                else:
                    values = [data[c] for c in columns]
                    namespace["rows"].append(values)

            if not is_csv:
                template = templates.GRID_HTML if is_html else templates.SQL_TXT
                s = step.Template(template, strip=is_html).expand(namespace)
                f.write(s.encode("utf-8"))

            f.close()
            result = True
    except Exception, e:
        if f:
            f.close()
        main.log("Export cannot access %s.\n%s", filename,
            traceback.format_exc()
        )
    return result
