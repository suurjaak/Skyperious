# -*- coding: utf-8 -*-
"""
Functionality for exporting Skype data to external files.

------------------------------------------------------------------------------
This file is part of Skyperious - Skype chat history tool.
Released under the MIT License.

@author      Erki Suurjaak
@created     13.01.2012
@modified    01.08.2020
------------------------------------------------------------------------------
"""
import collections
import csv
import datetime
import itertools
import logging
import os
import re

try: # ImageFont for calculating column widths in Excel export, not required.
    from PIL import ImageFont
except ImportError:
    ImageFont = None
try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None

from . lib import util
from . lib.vendor import step

from . import conf
from . import emoticons
from . import guibase
from . import skypedata
from . import templates

try: # Used in measuring text extent for Excel column auto-width
    FONT_XLSX = ImageFont.truetype(conf.FontXlsxFile, 15)
    FONT_XLSX_BOLD = ImageFont.truetype(conf.FontXlsxBoldFile, 15)
except IOError: # Fall back to PIL default font if font files not on disk
    FONT_XLSX = FONT_XLSX_BOLD = ImageFont.load_default()
except Exception: # Fall back to a simple mono-spaced calculation if no PIL
    FONT_MONO = type('', (), {"getsize": lambda self, s: (8*len(s), 12)})()
    FONT_XLSX = FONT_XLSX_BOLD = FONT_MONO

"""FileDialog wildcard strings, matching extensions lists and default names."""
XLSX_WILDCARD = "Excel workbook (*.xlsx)|*.xlsx|" if xlsxwriter else ""
CHAT_WILDCARD = ("HTML document (*.html)|*.html|Text document (*.txt)|*.txt|"
                 "%sCSV spreadsheet (*.csv)|*.csv" % XLSX_WILDCARD)
CHAT_EXTS = ["html", "txt", "xlsx", "csv"] if xlsxwriter \
            else ["html", "txt", "csv"]
CHAT_WILDCARD_SINGLEFILE = "Excel workbook (*.xlsx)|*.xlsx" # Cannot end with |
CHAT_EXTS_SINGLEFILE = ["xlsx"]

TABLE_WILDCARD = ("HTML document (*.html)|*.html|"
                  "SQL INSERT statements (*.sql)|*.sql|"
                  "%sCSV spreadsheet (*.csv)|*.csv" % XLSX_WILDCARD)
TABLE_EXTS = ["html", "sql", "xlsx", "csv"] if xlsxwriter \
             else ["html", "sql", "csv"]

QUERY_WILDCARD = ("HTML document (*.html)|*.html|"
                  "%sCSV spreadsheet (*.csv)|*.csv" % XLSX_WILDCARD)
QUERY_EXTS = ["html", "xlsx", "csv"] if xlsxwriter else ["html", "csv"]


logger = logging.getLogger(__name__)


def export_chats(chats, path, format, db, messages=None, timerange=None, skip=True, progress=None):
    """
    Exports the specified chats from the database under path.

    @param   chats      list of chat dicts, as returned from SkypeDatabase
    @param   path       full path of directory where to save
    @param   format     export format (html|txt|xlsx|csv|filename.ext).
                        If format is filename.ext, a single file is created:
                        for single chat exports and multi chat XLSX exports
                        (for multi-file exports, filenames are named by chats).
    @param   db         SkypeDatabase instance
    @param   messages   list messages to export if not querying all
    @param   timerange  additional arguments for filtering messages, as
                        (from_timestamp or None, to_timestamp or None)
    @param   skip       whether to skip chats with no messages
    @param   progress   function called before exporting each chat, with the
                        number of messages exported so far
    @return             (list of exported filenames, number of chats exported,
                         number of messages exported)
    """
    files, count, message_count = [], 0, 0
    def make_filename(chat):
        if len(format) > 4: # Filename already given in format
            filename = os.path.join(path, format)
        else:
            args = collections.defaultdict(str); args.update(chat)
            filename = "%s.%s" % (conf.ExportChatTemplate % args, format)
            filename = os.path.join(path, util.safe_filename(filename))
            filename = util.unique_path(filename)
        return filename
    guibase.status("Exporting %s from %s %sto %s.",
                   util.plural("chat", chats), db.filename,
                   "" if len(format) > 4 else "as %s " % format.upper(),
                   format if len(format) > 4 else path, log=True)

    if format.lower().endswith(".xlsx"):
        filename = make_filename(chats[0])
        count, message_count = export_chats_xlsx(chats, filename, db, messages,
                                                 timerange, skip, progress)
        files.append(filename)
    else:
        if not os.path.exists(path):
            os.makedirs(path)
        export_func = (export_chats_xlsx if format.lower().endswith("xlsx")
                       else export_chat_csv if format.lower().endswith("csv")
                       else export_chat_template)

        if format.lower().endswith("html") and conf.SharedImageAutoDownload \
        and not db.live.is_logged_in() \
        and conf.Login.get(db.filename, {}).get("password"):
            # Log in to Skype online service to download shared images
            try: db.live.login(db.id, conf.Login[db.filename]["password"])
            except Exception: pass

        for chat in chats:
            do_skip = False
            timestamp_from, timestamp_to = timerange or (None, None)

            if skip and not messages and any(x is not None for x in timerange or ()) \
            and chat["message_count"]:
                messages = db.get_messages(chat, use_cache=False,
                    timestamp_from=timestamp_from, timestamp_to=timestamp_to
                )
                msg = next(messages, None)
                if not msg: do_skip, messages = True, None
                else: messages = itertools.chain([msg], messages)

            if do_skip or skip and not messages and not chat["message_count"]:
                logger.info("Skipping exporting %s: no messages.",
                            chat["title_long_lc"])
                if progress: progress(message_count)
                continue # continue for chat in chats

            guibase.status("Exporting %s.", chat["title_long_lc"], log=True)
            if progress: progress(message_count)
            filename = make_filename(chat)
            msgs = messages or db.get_messages(chat, use_cache=False,
                timestamp_from=timestamp_from, timestamp_to=timestamp_to
            )
            chatarg = [chat] if "xlsx" == format.lower() else chat
            chat_count, chat_message_count = export_func(chatarg, filename, db, msgs)
            count += chat_count
            message_count += chat_message_count
            files.append(filename)
    return files, count, message_count


def export_chats_xlsx(chats, filename, db, messages=None, timerange=None, skip=True, progress=None):
    """
    Exports the chats to a single XLSX file with chats on separate worksheets.

    @param   chats      list of chat data dicts, as returned from SkypeDatabase
    @param   filename   full path and filename of resulting file
    @param   db         SkypeDatabase instance
    @param   messages   list of messages to export if a single chat
    @param   timerange  additional arguments for filtering messages, as
                        (timestamp_from or None, timestamp_to or None)
    @param   skip       whether to skip chats with no messages
    @param   progress   function called before exporting each chat, with the
                        number of messages exported so far
    @return             (number of chats exported, number of messages exported)
    """
    count, message_count, style = 0, 0, {0: "timestamp", 2: "wrap", 3: "hidden"}

    writer = xlsx_writer(filename, autowrap=[2])
    for chat in chats:
        chat_message_count, do_skip = 0, False
        timestamp_from, timestamp_to = timerange or (None, None)

        if skip and not messages and any(x is not None for x in timerange or ()) \
        and chat["message_count"]:
            messages = db.get_messages(chat, use_cache=False,
                timestamp_from=timestamp_from, timestamp_to=timestamp_to
            )
            msg = next(messages, None)
            if not msg: do_skip, messages = True, None
            else: messages = itertools.chain([msg], messages)

        if do_skip or skip and not messages and not chat["message_count"]:
            logger.info("Skipping exporting %s: no messages.",
                        chat["title_long_lc"])
            continue # for chat

        guibase.status("Exporting %s.", chat["title_long_lc"], log=True)
        if progress: progress(message_count)
        parser = skypedata.MessageParser(db, chat=chat, stats=False)
        writer.add_sheet(chat["title"])
        writer.set_header(True)
        writer.writerow(["Time", "Author", "Message", "Skype Name"],
                        {3: "boldhidden"})
        writer.set_header(False)
        msgs = messages or db.get_messages(chat, use_cache=False,
            timestamp_from=timestamp_from, timestamp_to=timestamp_to
        )
        for m in msgs:
            text = parser.parse(m, output={"format": "text"})
            try:
                text = text.decode("utf-8")
            except UnicodeError: pass
            values = [m["datetime"], db.get_author_name(m), text, m["author"]]
            style[1] = "local" if db.id == m["author"] else "remote"
            writer.writerow(values, style)
            chat_message_count += 1
        count += bool(chat_message_count)
        message_count += chat_message_count
    writer.close()
    return count, message_count


def export_chat_template(chat, filename, db, messages):
    """
    Exports the chat messages to file using templates.

    @param   chat      chat data dict, as returned from SkypeDatabase
    @param   filename  full path and filename of resulting file, file extension
                       .html|.txt determines file format
    @param   db        SkypeDatabase instance
    @param   messages  list of message data dicts
    @return            (number of chats exported, number of messages exported)
    """
    count, message_count = 0, 0
    tmpfile, tmpname = None, None # Temporary file for exported messages
    try:
        is_html = filename.lower().endswith(".html")
        parser = skypedata.MessageParser(db, chat=chat, stats=True)
        namespace = {"db": db, "chat": chat, "messages": messages,
                     "parser": parser}
        # As HTML and TXT contain statistics in their headers before
        # messages, write out all messages to a temporary file first,
        # statistics will be available for the main file after parsing.
        # Cannot keep all messages in memory at once - very large chats
        # (500,000+ messages) can take gigabytes.
        tmpname = util.unique_path("%s.messages" % filename)
        tmpfile = open(tmpname, "w+")
        template = step.Template(templates.CHAT_MESSAGES_HTML if is_html else
                   templates.CHAT_MESSAGES_TXT, strip=False, escape=is_html)
        template.stream(tmpfile, namespace)

        namespace["stats"] = stats = parser.get_collected_stats()
        namespace.update({
            "date1": stats["startdate"].strftime("%d.%m.%Y")
                     if stats.get("startdate") else "",
            "date2": stats["enddate"].strftime("%d.%m.%Y")
                     if stats.get("enddate") else "",
            "emoticons_used": [x for x in stats["emoticons"]
                               if hasattr(emoticons, x)],
            "message_count":  stats.get("messages", 0),
        })

        if is_html:
            # Collect chat and participant images.
            namespace.update({"participants": [], "chat_picture_size": None,
                              "chat_picture_raw": None, })
            pic = chat["meta_picture"] or chat.get("__link", {}).get("meta_picture")
            if pic:
                raw = skypedata.fix_image_raw(pic)
                namespace["chat_picture_raw"] = raw
                namespace["chat_picture_size"] = util.img_size(raw)
                

            contacts = dict((c["skypename"], c) for c in db.get_contacts())
            partics = dict((p["identity"], p) for p in chat["participants"])
            # There can be authors not among participants, and vice versa
            for author in stats["authors"].union(partics):
                contact = partics.get(author, {}).get("contact")
                contact = contact or contacts.get(author, {})
                contact = contact or {"identity": author, "name": author}
                bmp = contact.get("avatar_bitmap")
                raw = contact.get("avatar_raw_small") or ""
                raw_large = contact.get("avatar_raw_large") or ""
                if not raw and not bmp:
                    raw = skypedata.get_avatar_raw(contact, conf.AvatarImageSize)
                raw = bmp and util.img_wx_to_raw(bmp) or raw
                if raw:
                    raw_large = raw_large or skypedata.get_avatar_raw(
                                    contact, conf.AvatarImageLargeSize)
                    contact["avatar_raw_small"] = raw
                    contact["avatar_raw_large"] = raw_large
                contact["rank"] = partics.get(author, {}).get("rank")
                namespace["participants"].append(contact)

        tmpfile.flush(), tmpfile.seek(0)
        namespace["message_buffer"] = iter(lambda: tmpfile.read(65536), "")
        with open(filename, "w") as f:
            t = templates.CHAT_HTML if is_html else templates.CHAT_TXT
            step.Template(t, strip=False, escape=is_html).stream(f, namespace)
        count = bool(namespace["message_count"])
        message_count = namespace["message_count"]
    finally:
        if tmpfile: util.try_until(tmpfile.close)
        if tmpname: util.try_until(lambda: os.unlink(tmpname))
    return count, message_count


def export_chat_csv(chat, filename, db, messages):
    """
    Exports the chat messages to a CSV data file.

    @param   chat      chat data dict, as returned from SkypeDatabase
    @param   filename  full path and filename of resulting file
    @param   db        SkypeDatabase instance
    @param   messages  list of message data dicts
    @return            (number of chats exported, number of messages exported)
    """
    count, message_count = 0, 0
    parser = skypedata.MessageParser(db, chat=chat, stats=False)
    dialect = csv.excel
    # csv.excel.delimiter default "," is not actually used by Excel.
    # Default linefeed "\r\n" would cause another "\r" to be written.
    dialect.delimiter, dialect.lineterminator = ";", "\r"
    with open(filename, "wb") as f:
        writer = csv.writer(f, dialect)
        writer.writerow(["Time", "Author", "Message"])
        for m in messages:
            text = parser.parse(m, output={"format": "text"})
            try:
                text = text.decode("utf-8")
            except UnicodeError: pass
            values = [m["datetime"].strftime("%Y-%m-%d %H:%M:%S"),
                      db.get_author_name(m), text ]
            values = [v.encode("latin1", "replace") for v in values]
            writer.writerow(values)
            message_count += 1
    count = bool(message_count)
    return count, message_count


def export_grid(grid, filename, title, db, sql_query="", table=""):
    """
    Exports the current contents of the specified wx.Grid to file.

    @param   grid       a wx.Grid object
    @param   filename   full path and filename of resulting file, file extension
                        .html|.csv|.sql|.xslx determines file format
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
    is_xlsx = filename.lower().endswith(".xlsx")
    try:
        with open(filename, "w") as f:
            columns = [c["name"] for c in grid.Table.columns]

            if is_csv or is_xlsx:
                if is_csv:
                    dialect = csv.excel
                    dialect.delimiter, dialect.lineterminator = ";", "\r"
                    writer = csv.writer(f, dialect)
                    if sql_query:
                        flat = sql_query.replace("\r", " ").replace("\n", " ")
                        sql_query = flat.encode("latin1", "replace")
                    header = [c.encode("latin1", "replace") for c in columns]
                else:
                    writer = xlsx_writer(filename, table or "SQL Query")
                    writer.set_header(True)
                    header = columns
                if sql_query:
                    a = [[sql_query]] + (["bold", 0, False] if is_xlsx else [])
                    writer.writerow(*a)
                writer.writerow(*([header, "bold"] if is_xlsx else [header]))
                writer.set_header(False) if is_xlsx else 0
                for row in grid.Table.GetRowIterator():
                    values = []
                    for col in columns:
                        val = "" if row[col] is None else row[col]
                        if is_csv:
                            val = val if isinstance(val, unicode) else str(val)
                            val = val.encode("latin1", "replace")
                        values.append(val)
                    writer.writerow(values)
                writer.close() if is_xlsx else 0
            else:
                namespace = {
                    "db_filename": db.filename,
                    "title":       title,
                    "columns":     columns,
                    "row_count":   grid.NumberRows,
                    "rows":        grid.Table.GetRowIterator(),
                    "sql":         sql_query,
                    "table":       table,
                    "app":         conf.Title,
                }
                if is_sql and table:
                    # Add CREATE TABLE statement.
                    create_sql = db.tables[table.lower()]["sql"] + ";"
                    re_sql = re.compile("^(CREATE\\s+TABLE\\s+)", re.IGNORECASE)
                    replacer = lambda m: ("%sIF NOT EXISTS " % m.group(1))
                    namespace["create_sql"] = re_sql.sub(replacer, create_sql)

                template = step.Template(templates.GRID_HTML if is_html else 
                           templates.SQL_TXT, strip=False, escape=is_html)
                template.stream(f, namespace)

            result = True
    finally:
        if f: util.try_until(f.close)
    return result



class xlsx_writer(object):
    """Convenience wrapper for xslxwriter, with csv.Writer-like interface."""
    COL_MAXWIDTH   = 100 # In Excel units, 1 == width of "0" in standard font
    ROW_MAXNUM     = 1048576 # Maximum per worksheet
    FMT_DEFAULT    = {"bg_color": "white", "valign": "top"}
    FMT_BOLD       = dict(FMT_DEFAULT, **{"bold": True})
    FMT_WRAP       = dict(FMT_DEFAULT, **{"text_wrap": True})
    FMT_LOCAL      = dict(FMT_DEFAULT, **{"font_color": "#999999"})
    FMT_REMOTE     = dict(FMT_DEFAULT, **{"font_color": "#3399FF"})
    FMT_HIDDEN     = dict(FMT_DEFAULT, **{"font_color": "#C0C0C0"})
    FMT_BOLDHIDDEN = dict(FMT_DEFAULT, **{"font_color": "#C0C0C0", "bold": True})
    FMT_TIMESTAMP  = dict(FMT_DEFAULT, **{"font_color": "#999999",
                                          "align": "left",
                                          "num_format": "yyyy-mm-dd HH:MM", })

    def __init__(self, filename, sheetname=None, autowrap=[]):
        """
        @param   sheetname  title of the first sheet to create, if any
        @param   autowrap   a list of column indices that will get their width
                            set to COL_MAXWIDTH and their contents wrapped
        """
        self._workbook = xlsxwriter.Workbook(filename,
            {"constant_memory": True, "strings_to_formulas": False})
        self._sheet      = None # Current xlsxwriter.Worksheet, if any
        self._sheets     = {} # {lowercase sheet name: xlsxwriter.Worksheet, }
        self._sheetnames = {} # {xlsxwriter.Worksheet: original given name, }
        self._headers    = {} # {sheet name: [[values, style, merge_cols], ], }
        self._col_widths = {} # {sheet name: {col index: width in Excel units}}
        self._autowrap   = [c for c in autowrap] # [column index to autowrap, ]
        self._format     = None

        # Worksheet style formats
        format_default = self._workbook.add_format(self.FMT_DEFAULT)
        self._formats  = collections.defaultdict(lambda: format_default)
        for t in ["bold", "wrap", "local", "remote",
                  "hidden", "boldhidden", "timestamp"]:
            f = getattr(self, "FMT_%s" % t.upper(), self.FMT_DEFAULT)
            self._formats[t] = self._workbook.add_format(f)

        # For calculating column widths
        self._fonts = collections.defaultdict(lambda: FONT_XLSX)
        self._fonts["bold"] = FONT_XLSX_BOLD
        unit_width_default = self._fonts[None].getsize("0")[0]
        self._unit_widths = collections.defaultdict(lambda: unit_width_default)
        self._unit_widths["bold"] = self._fonts["bold"].getsize("0")[0]

        if sheetname: # Create default sheet
            self.add_sheet(sheetname)


    def add_sheet(self, name=None):
        """Adds a new worksheet. Name will be changed if invalid/existing."""
        if self._sheet and hasattr(self._sheet, "_opt_close"):
            self._sheet._opt_close() # Close file handle to not hit ulimit
        safename = None
        if name:
            # Max length 31, no []:\\?/*\x00\x03, cannot start/end with '.
            stripped = name.strip("'")
            safename = re.sub(r"[\[\]\:\\\?\/\*\x00\x03]", " ", stripped)
            safename = safename[:29] + ".." if len(safename) > 31 else safename
            # Ensure unique name, appending (counter) if necessary
            base, counter = safename, 2
            while safename.lower() in self._sheets:
                suffix = " (%s)" % (counter)
                safename = base + suffix
                if len(safename) > 31:
                    safename = "%s..%s" % (base[:31 - len(suffix) - 2], suffix)
                counter += 1
        sheet = self._workbook.add_worksheet(safename)
        self._sheets[sheet.name.lower()] = self._sheet = sheet
        self._sheetnames[sheet] = name or sheet.name
        self._col_widths[sheet.name] = collections.defaultdict(lambda: 0)
        for c in self._autowrap:
            sheet.set_column(c, c, self.COL_MAXWIDTH, self._formats[None])
        self._row = 0

        # Worksheet write functions for different data types
        self._writers = collections.defaultdict(lambda: sheet.write)
        self._writers[datetime.datetime] = sheet.write_datetime
        # Avoid using write_url: URLs are very limited in Excel (max len 256)
        self._writers[str] = self._writers[unicode] = sheet.write_string


    def set_header(self, start):
        """Starts or stops header section: bold lines split from the rest."""
        self._format = "bold" if start else None
        if start:
            self._headers[self._sheet.name] = []
        else:
            self._sheet.freeze_panes(self._row, 0)


    def writerow(self, values, style={}, merge_cols=0, autowidth=True):
        """
        Writes to the current row from first column, steps to next row.
        If current sheet is full, starts a new one.

        @param   style       format name to apply for all columns, or a dict
                             mapping column indices to format names
        @param   merge_cols  how many columns to merge (0 for none)
        @param   autowidth   are the values used to auto-size column max width
        """
        if self._row >= self.ROW_MAXNUM: # Sheet full: start a new one
            name_former = self._sheet.name
            self.add_sheet(self._sheetnames[self._sheet])
            if name_former in self._headers: # Write same header
                self.set_header(True)
                [self.writerow(*x) for x in self._headers[name_former]]
                self.set_header(False)
        if "bold" == self._format:
            self._headers[self._sheet.name] += [(values, style, merge_cols)]
        if merge_cols:
            f = self._formats[self._format]
            self._sheet.merge_range(self._row, 0, self._row, merge_cols, "", f)
            values = values[0] if values else []
        for c, v in enumerate(values):
            writefunc = self._writers[type(v)]
            fmt_name = style if isinstance(style, basestring) \
                       else style.get(c, self._format)
            writefunc(self._row, c, v, self._formats[fmt_name])
            if (merge_cols or not autowidth or "wrap" == fmt_name
            or c in self._autowrap):
                continue # continue for c, v in enumerate(Values)

            # Calculate and update maximum written column width
            strval = (v.encode("latin1", "replace") if isinstance(v, unicode) 
                      else v.strftime("%Y-%m-%d %H:%M") \
                      if isinstance(v, datetime.datetime) else 
                      v if isinstance(v, basestring) else str(v))
            pixels = max(self._fonts[fmt_name].getsize(x)[0]
                         for x in strval.split("\n"))
            width = float(pixels) / self._unit_widths[fmt_name] + 1
            if not merge_cols and width > self._col_widths[self._sheet.name][c]:
                self._col_widths[self._sheet.name][c] = width
        self._row += 1


    def close(self):
        """Finalizes formatting and saves file content."""

        # Auto-size columns with calculated widths
        for sheet in self._workbook.worksheets():
            c = -1
            for c, w in sorted(self._col_widths[sheet.name].items()):
                w = min(w, self.COL_MAXWIDTH)
                sheet.set_column(c, c, w, self._formats[None])
            sheet.set_column(c + 1, 50, cell_format=self._formats[None])
        self._workbook.set_properties({"comments": "Exported with %s on %s." %
            (conf.Title, datetime.datetime.now().strftime("%d.%m.%Y %H:%M"))})
        self._workbook.close()
