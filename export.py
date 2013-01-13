# -*- coding: utf-8 -*-
"""
Functionality for exporting Skype data to external files.

@author      Erki Suurjaak
@created     13.01.2012
@modified    05.01.2013
"""

import base64
import codecs
import collections
import cStringIO
import csv
import datetime
import locale
import re
import traceback
import wx
import xml.etree.cElementTree

import conf
import images
import main
import skypedata
import util


"""HTML database grid header template."""
GRID_HTML_HEADER = """<!DOCTYPE HTML><html>
<head>
    <meta http-equiv='Content-Type' content='text/html;charset=utf-8' />
    <meta name="Author" content="%(app)s">
    <title>%%(title)s</title>
    <link rel="shortcut icon" type="image/png" href="data:image/ico;base64,%(favicon)s"/>
    <style>
        * { font-family: %(font)s; font-size: 11px; }
        body {
            background: %(bgcolour)s;
            margin: 0px 10px 0px 10px;
        }
        .header { font-size: 1.1em; font-weight: bold; color: %(linkcolour)s; }
        .header_table {
            width: 100%%%%;
        }
        .header_left {
            width: 145px;
            text-align: left;
        }
        table.body_table {
            margin-left: auto;
            margin-right: auto;
            border-spacing: 0px 10px;
        }
        table.body_table > tbody > tr > td {
            background: white;
            width: 800px;
            font-family: %(font)s;
            font-size: 11px;
            border-radius: 10px;
            padding: 10px;
        }
        table.content_table {
            empty-cells: show;
            border-spacing: 2px;
        }
        table.content_table td {
            line-height: 1.5em;
            padding: 5px;
            border: 1px solid #C0C0C0;
        }
        a, a.visited { color: %(linkcolour)s; text-decoration: none; }
        a:hover, a.visited:hover { text-decoration: underline; }
        .footer {
          text-align: center;
          padding-bottom: 10px;
          color: #666;
        }
        .header { font-size: 1.1em; font-weight: bold; color: %(linkcolour)s; }
        td { text-align: left; vertical-align: top; }
    </style>
</head>
<body>
<table class="body_table">
<tr><td><table class="header_table">
    <tr>
        <td class="header_left"></td>
        <td>
            <div class="header">%%(title)s</div><br />
            Source: <b>%%(db)s</b>.<br />
            <b>%%(count)s</b> rows in results.<br />%%(info)s
        </td>
    </tr></table>
</td></tr><tr><td><table class='content_table'>
""" % {
    "bgcolour"    : conf.HistoryBackgroundColour,
    "linkcolour"  : conf.HistoryLinkColour,
    "app"         : conf.Title,
    "font"        : conf.HistoryFontName,
    "favicon"     : images.Icon8bit16x16.data,
}

"""HTML chat history header template."""
CHAT_HTML_HEADER = """<!DOCTYPE HTML><html>
<head>
    <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
    <meta name="Author" content="%(app)s">
    <title>%%(title)s</title>
    <link rel="shortcut icon" type="image/png" href="data:image/ico;base64,%(favicon)s"/>
    <style>
        * { font-family: %(font)s; font-size: 11px; }
        body {
            background: %(bgcolour)s;
            margin: 0px 10px 0px 10px;
        }
        table.body_table {
            margin-left: auto;
            margin-right: auto;
            border-spacing: 0px 10px;
        }
        table.body_table > tbody > tr > td {
            background: white;
            width: 800px;
            font-family: %(font)s;
            font-size: 11px;
            border-radius: 10px;
            padding: 10px;
        }
        table.content_table {
            empty-cells: show;
            border-spacing: 0px;
            width: 100%%%%;
        }
        table.content_table td {
            text-align: left;
            vertical-align: top;
            line-height: 1.5em;
            padding-bottom: 5px;
        }
        table.quote {
          padding-bottom: 5px;
        }
        table.quote td:first-child {
          vertical-align: top;
          border-right: 1px solid #C0C0C0;
          padding: 0px 3px 0px 0px;
        }
        table.quote td:first-child span {
          position: relative;
          top: 15px;
          left: -2px;
          font-size: 4em;
          color: #999;
          font-family: Courier;
        }
        table.quote td:last-child {
          padding: 0px 0px 0px 5px;
        }
        span.grey {
          color: #999;
        }
        a, a.visited { color: %(linkcolour)s; text-decoration: none; }
        a:hover, a.visited:hover { text-decoration: underline; }
        .footer {
          text-align: center;
          padding-bottom: 10px;
          color: #666;
        }
        .header { font-size: 1.1em; font-weight: bold; color: %(linkcolour)s; }
        .header a {
            text-decoration: underline;
        }
        .header_table td {
            vertical-align: top;
        }
        .header_table {
            width: 100%%%%;
        }
        .header_left {
            width: 145px;
            text-align: left;
        }
        .header_left div, .header_right div {
            width: 100px;
            text-align: center;
        }
        .header_right {
            width: 100px;
            text-align: right;
        }
        .participants {
            padding: 5px;
            float: left;
            display: none;
        }
        .participants span {
            float: left;
            margin: 2px;
            width: 200px;
            border: 1px solid #99BBFF;
            border-radius: 5px;
            padding: 5px;
        }
        .participants img {
            margin-right: 5px;
        }
        span.avatar {
            height: 96px;
            width: 96px;
            display: block;
            float: left;
            border: 1px solid lightgray;
        }
        .participants span.avatar {
            margin-right: 4px;
            display: inline;
        }
        span.avatar__default {
            background: url(data:image/png;base64,%(imageavatar)s)
                        center center no-repeat;
        }%%(css_avatars)s
        span.chat_picture {
            display: none;
        }%%(css_chat_picture)s
        table.content_table td.day {
            border-top: 1px solid %(linecolour)s;
            border-bottom: 1px solid %(linecolour)s;
            padding-top: 7px; padding-bottom: 7px;
        }
        table.content_table .weekday { font-weight: bold; }
        table.content_table .timestamp {
            color: %(timecolour)s;
            text-align: right;
            width: 40px;
        }
        table.content_table .author { min-width: 90px; text-align: right; }
        table.content_table .remote { color: %(remotecolour)s; }
        table.content_table .local { color: %(localcolour)s; }
        table.content_table .t1 { width: 50px; }
        table.content_table .t2 { width: 40px; }
        table.content_table .t3 { width: 15px; min-width: 15px; }
        table.content_table .day.t3 {
            padding: 5px;
            background: url(data:image/png;base64,%(imageclock)s)
                        center center no-repeat;
        }
    </style>
    <script>
        function toggle_participants() {
            var el = document.getElementById('participants');
            el.style.visibility = 'visible';
            el.style.display = el.style.display != 'block' ? 'block' : 'none';
            return false;
        }
    </script>
</head>
<body>
<table class="body_table">
<tr><td><table class="header_table">
    <tr>
        <td class="header_left">%%(header_left)s</td>
        <td>
            <div class="header">%%(title)s.</div><br />
            %%(chat_info)s
            Source: <b>%%(db)s</b>.<br /><br />%%(header_link)s
        </td>
        <td class="header_right">%%(header_right)s</td>
    </tr><tr>
        <td colspan="3"><div id="participants" class="participants">
""" % {
    "bgcolour"    : conf.HistoryBackgroundColour,
    "linecolour"  : conf.HistoryLineColour,
    "timecolour"  : conf.HistoryTimestampColour,
    "localcolour" : conf.HistoryLocalAuthorColour,
    "remotecolour": conf.HistoryRemoteAuthorColour,
    "linkcolour"  : conf.HistoryLinkColour,
    "app"         : conf.Title,
    "font"        : conf.HistoryFontName,
    "imageavatar" : images.AvatarDefaultLarge.data,
    "imageclock"  : images.ExportClock.data,
    "favicon"     : images.Icon8bit16x16.data,
}
"""Toggle show/hide link for the participants section."""
PARTICIPANTS_LINK = \
    "<div class='header'><a title='Click to show/hide participants' href='#'" \
    " onclick='return toggle_participants()'>Participants</a></div>"


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
        if is_txt:
            f = codecs.open(filename, "w", "utf-8")
        else:
            f = open(filename, "w")

        # @todo add stats?
        parser = skypedata.MessageParser(db)
        chat_title = chat["title_long_lc"]
        main_data = {
            "title":          chat_title,
            "date1":          messages[0]["datetime"].strftime("%d.%m.%Y") \
                              if len(messages) else "",
            "date2":          messages[-1]["datetime"].strftime("%d.%m.%Y") \
                              if len(messages) else "",
            "messages_total": util.plural("message", chat["message_count"]),
            "chat_created":   chat["created_datetime"].strftime("%d.%m.%Y") \
                              if chat["created_datetime"] else "",
            "app":            conf.Title,
            "now":            datetime.datetime.now() \
                              .strftime("%d.%m.%Y %H:%M"),
            "db":             db.filename,
            "count":          str(len(messages)),
            "chat_info":      "Showing %s" \
                              % util.plural("message", len(messages)),
        }
        if is_html:
            # Write HTML header and table header
            header_data = dict([
                (k, escape(v)) for k, v in main_data.items()
            ])
            if header_data["date1"] and header_data["date2"]:
                header_data["chat_info"] += \
                    " from <b>%(date1)s</b> to <b>%(date2)s</b>" % header_data
            header_data["chat_info"] += ".<br />"
            if header_data["chat_created"]:
                header_data["chat_info"] += \
                    "Chat created on <b>%(chat_created)s</b>" % header_data
            if header_data["messages_total"]:
                header_data["chat_info"] += \
                    ("," if header_data["chat_created"] else "Chat has") +\
                    " <b>%(messages_total)s</b> in total" % header_data
            if header_data["chat_created"] or header_data["messages_total"]:
                header_data["chat_info"] += ".<br />"
            header_data.update({
                "title": "History of Skype " + header_data["title"],
                "css_avatars": "", "css_chat_picture": "",
                "header_left": "",
                "header_right": "",
                "header_link": ""
            })
            if chat["meta_picture"]:
                raw = chat["meta_picture"].encode("latin1")
                if raw.startswith("\0"):
                    # For some reason, Skype image blobs
                    # can start with a null byte.
                    raw = raw[1:]
                if raw.startswith("\0"):
                    raw = "\xFF" + raw[1:]
                header_data["header_left"] = htmltag("span", {
                    "class": "chat_picture", "title": chat["title"]
                })
                img = wx.ImageFromStream(cStringIO.StringIO(raw))
                header_data["css_chat_picture"] = cssrule("span.chat_picture",{
                    "background": 
                        "url(data:image/jpg;base64,%s) " \
                        "center center no-repeat" % base64.b64encode(raw),
                    "margin": "0px 10px 0px 10px",
                    "display": "block",
                    "width": "%spx" % img.Width,
                    "height": "%spx" % img.Height,
                })
            if chat["participants"]:    
                for p in chat["participants"]:
                    avatar_class = "avatar__default"
                    if "avatar_image" in p["contact"] \
                    and p["contact"]["avatar_image"]:
                        raw = p["contact"]["avatar_image"].encode("latin1")
                        if raw.startswith("\0"):
                            # For some reason, Skype avatar image blobs
                            # can start with a null byte.
                            raw = raw[1:]
                        if raw.startswith("\0"):
                            #raw = raw[1:]
                            raw = "\xFF" + raw[1:]
                        # Replace dots and commas, as they are
                        # not valid CSS identifier characters
                        avatar_class = "avatar_" \
                            + p["identity"].replace(".", "___") \
                              .replace(",", "---")
                        header_data["css_avatars"] += cssrule(
                            "span.%s" % avatar_class, {
                                "background":
                                    "url(data:image/jpg;base64,%s) center " \
                                    "center no-repeat" % base64.b64encode(raw)
                        })
                    if skypedata.CHATS_TYPE_SINGLE == chat["type"]:
                        title = p["contact"]["name"]
                        name = escape(p["contact"]["name"])
                        if p["contact"]["name"] != p["identity"]:
                            title += " (%s)" % p["identity"]
                            name += "<br />(%s)" % escape(p["identity"])
                        side = "right" if (p["identity"] == db.id) else "left"
                        header_data["header_%s" % side] = "<div>%s" \
                            "<br />%s</div>" % (
                                htmltag("span", {"title": title,
                                    "class": "avatar header %s" % avatar_class}
                                ), name
                            )
            if skypedata.CHATS_TYPE_SINGLE != chat["type"]:
                header_data["header_link"] = PARTICIPANTS_LINK
            for k, v in header_data.items():
                header_data[k] = str(v)
            f.write(CHAT_HTML_HEADER % header_data)
            if skypedata.CHATS_TYPE_SINGLE != chat["type"]:
                for p in sorted(chat["participants"],
                    key=lambda a: a["contact"]["name"].lower()
                ):
                    img_attr = {"class": "avatar avatar__default"}
                    img_attr["title"] = p["contact"]["name"]
                    if p["contact"]["name"] != p["identity"]:
                        img_attr["title"] += " (%s)" % p["identity"]
                    if "avatar_image" in p["contact"] \
                    and p["contact"]["avatar_image"]:
                        # Replace dots and commas, as they are not valid
                        # CSS identifier characters
                        img_attr["class"] = "avatar avatar_%s" \
                            % p["identity"].replace(".", "___") \
                              .replace(",", "---")
                    name = escape(p["contact"]["name"])
                    if p["contact"]["name"] != p["identity"]:
                        name += "<br />(%s)" % escape(p["identity"])
                    f.write("            <span>%(img)s%(name)s</span>\n" % {
                        "name": name,
                        "img": htmltag("span", img_attr),
                    })
            f.write("        </div>\r\n    </td>\r\n</tr>\r\n</table>\r\n" \
              "</td></tr><tr><td><table class='content_table'>\r\n")
        elif is_txt:
            main_data["hr"] = "-" * 79
            f.write("History of Skype %(title)s.\r\n" \
                    "Showing %(count)s messages" % main_data)
            if main_data["date1"] and main_data["date2"]:
                f.write(" from %(date1)s to %(date2)s" % main_data)
            f.write(".\r\n")
            if main_data["chat_created"]:
                f.write("Chat created on %(chat_created)s" % main_data)
            else:
                f.write("Chat has")
            if main_data["messages_total"]:
                f.write(("," if main_data["chat_created"] else "") + 
                        " %(messages_total)s in total" % main_data)
            f.write(".\r\n")
            f.write(
                    "Source: %(db)s.\r\n" \
                    "Exported with %(app)s on %(now)s." \
                    "\r\n%(hr)s\r\n" % main_data
            )
        elif is_csv:
            # Initialize CSV writer and write header row
            dialect = csv.excel
            # Default is "," which is actually not Excel
            dialect.delimiter = ";"
            # Default is "\r\n", which causes another "\r" to be written
            dialect.lineterminator = "\r"
            csv_writer = csv.writer(f, dialect)
            csv_writer.writerow(["Time", "Author", "Message"])

        colourmap = collections.defaultdict(lambda: "remote")
        colourmap[db.id] = "local"
        previous_day = datetime.date.fromtimestamp(0)
        for m in messages:
            if m["datetime"].date() != previous_day:
                # Day has changed: insert a date header
                previous_day = m["datetime"].date()
                weekday = previous_day.strftime("%A").capitalize()
                date = previous_day.strftime("%d. %B %Y")
                if locale.getpreferredencoding():
                    weekday = weekday.decode(locale.getpreferredencoding())
                    date = date.decode(
                        locale.getpreferredencoding()
                    )
                if is_html:
                    f.write(
                        "<tr>\r\n\t<td class='t1'></td>\r\n\t" \
                        "<td class='day t2'></td>\r\n\t" \
                        "<td class='day t3'></td>\r\n\t" \
                        "<td class='day' colspan='2'><span class='weekday'>" \
                        "%(weekday)s</span>, %(date)s</td>\r\n</tr>\r\n" % {
                            "weekday": escape(weekday),
                            "date": escape(date)
                    })
                elif is_txt:
                    f.write("\r\n%(weekday)s, %(date)s\r\n%(hr)s\r\n\r\n" % {
                        "weekday": weekday, "date": date, "hr": "-" * 40
                    })

            if is_html:
                body = parser.parse(m, html={"w": -1, "export": True})
                f.write("<tr>\r\n\t" \
                    "<td class='author %(authorclass)s' colspan='2'>" \
                    "%(name)s</td>\r\n\t" \
                    "<td class='t3'></td>\r\n\t<td>%(text)s</td>\r\n\t" \
                    "<td class='timestamp' title='%(stamp)s'>" \
                    "%(time)s</td>\r\n</tr>\r\n" % {
                        "authorclass": colourmap[m["author"]],
                        "time": m["datetime"].strftime("%H:%S"),
                        "stamp": m["datetime"].strftime("%Y-%m-%d %H:%M:%S"),
                        "name": escape(m["from_dispname"]),
                        "text": body
                })
            else:
                parsed_text = parser.parse(m, text=True)
                try:
                    parsed_text = parsed_text.decode("utf-8")
                except Exception, e:
                    pass
            if is_txt:
                f.write("%(datetime)s %(name)s:\r\n%(text)s\r\n\r\n" % {
                    "datetime": m["datetime"].strftime("%H:%S"),
                    "name": m["from_dispname"],
                    "text": parsed_text
                })
            elif is_csv:
                try:
                    parsed_text = parser.parse(m, text=True)
                    parsed_text = parsed_text.decode("utf-8")
                except Exception, e:
                    pass
                values = [m["datetime"].strftime("%Y-%m-%d %H:%M:%S"),
                    m["from_dispname"].encode("utf-8"),
                    parsed_text.encode("utf-8")
                ]
                csv_writer.writerow(values)
        if is_html:
            f.write("</table>\r\n</td></tr></table>\r\n<div class='footer'>" \
                "Exported with %(app)s on %(now)s.</div>\r\n" \
                "</body>\r\n</html>" % header_data
            )
        f.close()
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
    # @todo do with BeautifulSoup?
    try:
        if sql: # not related to is_sql
            sql = sql.encode("utf-8")
        with open(filename, "w") as f:
            is_html = filename.lower().endswith(".html")
            is_csv  = filename.lower().endswith(".csv")
            is_sql  = filename.lower().endswith(".sql")
            columns = \
                [col["name"].encode("utf-8") for col in grid.Table.columns]
            main_data = {
                "title": title,
                "db": db.filename,
                "app": conf.Title,
                "now": datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
            }
            if is_html:
                main_data = dict([(k, escape(v)) for k,v in main_data.items()])
                # Write HTML header and table header
                info = "<b>SQL:</b> %s" % escape(sql) if sql \
                       else ""
                f.write(GRID_HTML_HEADER % {"info": info,
                    "title": escape(title), "db": escape(db.filename),
                    "count": grid.NumberRows
                })
                f.write("<tr><th>#</th><th>%s</th></tr>" \
                    % "</th><th>".join(columns)
                )
            elif is_csv:
                # Initialize CSV writer and write header row
                dialect = csv.excel
                # Default is "," which is actually not Excel
                dialect.delimiter = ";"
                # Default is "\r\n", which causes another "\r" to be written
                dialect.lineterminator = "\r"
                csv_writer = csv.writer(f, dialect)
                csv_writer.writerow(["%(title)s, source: %(db)s. " \
                    "Exported with %(app)s on %(now)s." % main_data
                ])
                if sql:
                    csv_writer.writerow(["SQL: %s" \
                        % sql.replace("\r", " ").replace("\n", " ")
                    ])
                csv_writer.writerow(columns)
            elif is_sql:
                f.write("-- %(title)s.\n-- Source: %(db)s.\n" \
                    "-- Exported with %(app)s on %(now)s.\n" % main_data
                )
                if sql:
                    f.write("# SQL: %s\n" % sql)
                str_cols = ", ".join(columns)
                str_vals = "%(" + ")s, %(".join(columns) + ")s"
                if table:
                    # Add CREATE TABLE statement.
                    create_sql = db.tables[table.lower()]["sql"]
                    re_sql = re.compile(
                        "^(CREATE\s+TABLE\s+)", re.IGNORECASE | re.MULTILINE
                    )
                    create_sql = re_sql.sub(
                        lambda m: "%sIF NOT EXISTS " % m.group(1), create_sql
                    )
                    f.write("%s;\n\n" % create_sql)

            for i in range(grid.NumberRows):
                data = grid.Table.GetRow(i)
                values = []
                if is_sql:
                    for col_name in columns:
                        value = data[col_name]
                        if isinstance(value, unicode):
                            value = value.encode("utf-8")
                        if isinstance(value, basestring):
                            value = "\"%s\"" % value.encode("string-escape") \
                                                    .replace("\"", "\"\"")
                        elif value is None:
                            value = "NULL"
                        else:
                            value = str(value)
                        values.append(value)
                    stmt =  u"INSERT INTO %s (%s) VALUES (" % (table, str_cols)
                    stmt += ", ".join(values) + ");\n"
                    f.write(stmt)
                else:
                    for col_name in columns:
                        if isinstance(data[col_name], unicode):
                            values.append(data[col_name].encode("utf-8"))
                        elif data[col_name] is None:
                            values.append("")
                        else:
                            values.append(str(data[col_name]))
                if is_html:
                    # Some values can contain HTML, need to make it safe
                    values = map(lambda x: escape(x, utf=False), values)
                    values.insert(0, str(i + 1))
                    f.write("<tr><td>%s</td></tr>" % "</td><td>".join(values))
                elif is_csv:
                    csv_writer.writerow(values)

            if is_html:
                # Write HTML footer
                f.write("</table>\r\n</td></tr></table>\r\n" \
                    "<div class='footer'>Exported with %(app)s on %(now)s." \
                    "</div>\r\n</body>\r\n</html>" % main_data
                )
            f.close()
            result = True
    except Exception, e:
        if f:
            f.close()
        main.log("Export cannot access %s.\n%s", filename,
            traceback.format_exc()
        )
    return result



def htmltag(name, attrs=None, content=None, utf=True):
    """
    Returns an HTML tag string for the specified name, attributes and content.

    @param   name     HTML tag name, like 'a'
    @param   attrs    tag attributes dict
    @param   content  tag content string
    @param   utf      whether to convert all values to UTF-8
    """
    SELF_CLOSING_TAGS = ["img", "br", "meta", "hr", "base", "basefont",
                         "input", "area", "link"]
    tag = "<%s" % name
    if attrs:
        tag += " " + " ".join([
            "%s='%s'" % (k, escape(v, utf=utf))
            for k, v in attrs.items()
        ])
    if name not in SELF_CLOSING_TAGS:
    #or (content is not None and str(content)):
        tag += ">%s</%s>" % (escape(content, utf=utf), name)
    else:
        tag += " />"
    return tag


def cssrule(name, attrs):
    """Returns a CSS rule string with the specified name and attributes."""
    INDENT = "    "
    START = 2
    css = "\n%s%s {\n%s" % (INDENT * START, name, INDENT * (START + 1))
    css += ("\n%s" % (INDENT * (START + 1))).join(
        ["%s: %s;" % (k, v) for k, v in attrs.items()]
    )
    css += "\n%s}" % (INDENT * START)
    return css



def escape(value, utf=True, attr=False):
    """
    Escapes the value for HTML (converts " and < to &quot; and &lt;).

    @param   value  string or unicode value
    @param   utf    whether to encode result into UTF-8 (True by default)
    """
    strval = value if isinstance(value, basestring) \
             else (str(value) if value is not None else "")
    result = strval.replace("\"", "&quot;").replace("'", "&#39;") \
                   .replace("<", "&lt;")
    if utf:
        result = result.encode("utf-8")
    return result
