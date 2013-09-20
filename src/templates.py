# -*- coding: utf-8 -*-
"""
HTML and TXT templates for exports and statistics.

------------------------------------------------------------------------------
This file is part of Skyperious - a Skype database viewer and merger.
Released under the MIT License.

@author      Erki Suurjaak
@created     09.05.2013
@modified    19.09.2013
------------------------------------------------------------------------------
"""
import re

# Modules imported inside templates:
import base64, datetime, os, re, string, sys, urllib
import conf, emoticons, images, skypedata, util


"""Regex for replacing low bytes unusable in wx.HtmlWindow (\x00 etc)."""
SAFEBYTE_RGX = re.compile("[\x00-\x08,\x0B-\x0C,\x0E-x1F,\x7F]")

"""Replacer callback for low bytes unusable in wx.HtmlWindow (\x00 etc)."""
SAFEBYTE_REPL = lambda m: m.group(0).encode("unicode-escape")

"""HTML chat history export template."""
CHAT_HTML = """
<%
import base64, datetime, urllib
import conf, emoticons, images, skypedata, util
%>
<!DOCTYPE HTML><html>
<head>
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
  <meta name="Author" content="{{conf.Title}}">
  <title>Skype {{chat["title_long_lc"]}}</title>
  <link rel="shortcut icon" type="image/png" href="data:image/ico;base64,{{images.Icon16x16_8bit.data}}"/>
  <style>
    .highlight1  { background-color: #FFFF66; }
    .highlight2  { background-color: #A0FFFF; }
    .highlight3  { background-color: #99FF99; }
    .highlight4  { background-color: #FF9999; }
    .highlight5  { background-color: #FF66FF; }
    .highlight6  { background-color: #DE8C00; }
    .highlight7  { background-color: #00AA00; }
    .highlight8  { background-color: #BDC75A; }
    .highlight9  { background-color: #82C0FF; }
    .highlight10 { background-color: #9F8CFF; }
    body {
      font-family: {{conf.HistoryFontName}};
      font-size: 11px;
      background: {{conf.HistoryBackgroundColour}};
      margin: 0 10px 0 10px;
    }
    #body_table {
      margin-left: auto;
      margin-right: auto;
      border-spacing: 0 10px;
    }
    #body_table > tbody > tr > td {
      background: white;
      width: 800px;
      font-family: {{conf.HistoryFontName}};
      font-size: 11px;
      border-radius: 10px;
      padding: 10px;
    }
    #content_table {
      empty-cells: show;
      border-spacing: 0;
      width: 100%;
    }
    #content_table td {
      text-align: left;
      vertical-align: top;
      line-height: 1.5em;
      padding-bottom: 4px;
      padding-top: 3px;
    }
    #content_table table.quote td {
      padding-bottom: 0px;
    }
    table.quote {
      padding-bottom: 5px;
    }
    table.quote td:first-child {
      vertical-align: top;
      border-right: 1px solid #C0C0C0;
      padding: 0 3px 0 0;
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
      padding: 0 0 0 5px;
    }
    span.grey {
      color: #999;
    }
    a, a.visited { color: {{conf.HistoryLinkColour}}; text-decoration: none; cursor: pointer; }
    a:hover, a.visited:hover { text-decoration: underline; }
    #footer {
      text-align: center;
      padding-bottom: 10px;
      color: #666;
    }
    #header { font-size: 1.1em; font-weight: bold; color: {{conf.HistoryLinkColour}}; }
    #header_table {
      width: 100%;
    }
    #header_table td {
      vertical-align: top;
    }
    #header_left {
      width: 145px;
      text-align: left;
    }
    #header_center a {
      text-decoration: underline;
      font-weight: bold;
    }
    #header_center a.statistics {
      float: right;
      margin-right: 10px;
    }
    #header_right {
      width: 100%;
    }
    #header_left div, #header_right div {
      width: 100px;
      text-align: center;
    }
    #header_right {
      width: 100px;
      text-align: right;
    }
    #participants {
      padding: 5px;
      display: none;
    }
    #participants > span {
      float: left;
      margin: 2px;
      width: 200px;
      border: 1px solid #99BBFF;
      border-radius: 5px;
      padding: 5px;
    }
    #participants span.avatar_large {
      margin-right: 5px;
    }
    #statistics {
      padding: 5px;
      margin: 7px;
      display: none;
      border: 1px solid #99BBFF;
      border-radius: 5px;
    }
    #sort_header {
      margin-top: 10px;
      margin-bottom: 5px;
    }
    #sort_header a {
      text-decoration: underline;
      margin-left: 10px;
    }
    #sort_header a.selected {
      text-decoration: none;
      color: gray;
      cursor: default;
    }
    span.avatar_large {
      height: 96px;
      width: 96px;
      display: block;
      float: left;
      border: 1px solid lightgray;
    }
    span.avatar {
      height: 32px;
      width: 32px;
      display: block;
      margin-right: 10px;
    }
    .participants span.avatar_large {
      margin-right: 4px;
      display: inline;
    }
    #content_table td.day {
      border-top: 1px solid {{conf.HistoryLineColour}};
      border-bottom: 1px solid {{conf.HistoryLineColour}};
      padding-top: 3px; padding-bottom: 4px;
    }
    #content_table .weekday { font-weight: bold; }
    #content_table .timestamp {
      color: {{conf.HistoryTimestampColour}};
      text-align: left;
      width: 30px;
    }
    #content_table .timestamp span {
      position: relative;
      left: 5px;
      top: -1px;
      width: 11px;
      height: 11px;
    }
    #content_table .timestamp span.edited {
      background: url("data:image/png;base64,{{images.ExportEdited.data}}")
                  center center no-repeat;
    }
    #content_table .timestamp span.removed {
      background: url("data:image/png;base64,{{images.ExportRemoved.data}}")
                  center center no-repeat;
    }
    #content_table tr.shifted td.author, #content_table tr.shifted td.timestamp { 
      padding-top: 10px;
    }
    #content_table .author { min-width: 90px; text-align: right; }
    #content_table .remote { color: {{conf.HistoryRemoteAuthorColour}}; }
    #content_table .local { color: {{conf.HistoryLocalAuthorColour}}; }
    #content_table .t1 { width: 50px; }
    #content_table .t2 { width: 40px; }
    #content_table .t3 { width: 15px; min-width: 15px; }
    #content_table .day.t3 {
      padding: 5px;
      background: url("data:image/png;base64,{{images.ExportClock.data}}")
                  center center no-repeat;
    }
    #content_table .message_content {
      min-width: 500px;
      max-width: 635px;
      word-wrap: break-word;
    }
    #stats_data {
      width: 100%;
    }
    #stats_data > tbody > tr > td {
      padding: 0;
    }
    #stats_data > tbody > tr > td:first-child {
      vertical-align: top;
      width: 150px;
    }
    #stats_data > tbody > tr.stats_row > td:last-child {
      padding-left: 5px;
      line-height: 16px;
      white-space: nowrap;
    }
    .identity {
      color: gray;
    }
    #stats_data .name {
      vertical-align: middle;
    }
    #stats_data .avatar {
      float: left;
      padding: 0 5px 5px 0;
    }
    table.plot_table {
      white-space: nowrap;
      border-collapse: collapse;
      width: 100%;
    }
    table.plot_table > tbody > tr > td:first-child {
      width: 100%;
    }
    table.plot_table > tbody > tr > td {
      padding: 0;
    }
    table.plot_row {
      border-collapse: collapse;
      min-width: 100px;
      width: 100%;
      font-size: 0.9em;
      text-align: center;
      font-weight: bold;
    }
    table.plot_row td {
      padding: 0;
      height: 16px;
    }
    table.plot_row td:first-child {
      color: white;
    }
    table.plot_row.messages td:first-child {
      background-color: {{conf.PlotMessagesColour}};
    }
    table.plot_row.smses td:first-child {
      background-color: {{conf.PlotSMSesColour}};
    }
    table.plot_row.calls td:first-child {
      background-color: {{conf.PlotCallsColour}};
    }
    table.plot_row.files td:first-child {
      background-color: {{conf.PlotFilesColour}};
    }
    table.plot_row td:nth-child(2) {
      background-color: {{conf.PlotBgColour}};
      color: {{conf.PlotMessagesColour}};
    }
    #wordcloud {
      border-top: 1px solid #99BBFF;
      margin-top: 10px;
      padding-top: 5px;
      font-family: Arial, Helvetica, sans-serif;
    }
    #wordcloud span {
      color: blue;
      padding-right: 5px;
    }
    #wordcloud span a {
      font-size: 1em;
      color: blue;
    }
    #transfers {
      margin-top: 10px;
      padding-top: 5px;
      border-top: 1px solid #99BBFF;
    }
    #transfers table td {
      vertical-align: top;
      white-space: nowrap;
    }
    #transfers table a {
      color: blue;
    }
    #transfers table td:first-child {
      text-align: right;
      color: {{conf.HistoryLocalAuthorColour}};
      white-space: normal;
    }
    #transfers table td.remote:first-child {
      color: {{conf.HistoryRemoteAuthorColour}};
    }
    #transfers table td:last-child {
      text-align: right;
    }
    #transfers span {
      font-weight: bold;
      padding: 5px 0 10px 0;
      display: block;
      font-size: 1.1em;
    }
    span.avatar_large__default {
      background: url("data:image/png;base64,{{images.AvatarDefaultLarge.data}}")
                  center center no-repeat;
    }
    span.avatar__default {
      background: url("data:image/png;base64,{{images.AvatarDefault.data}}")
                  center center no-repeat;
    }
%for p in participants:
<%
p["avatar_class"] = "avatar__default"
p["avatar_class_large"] = "avatar_large__default"
%>
%if p["avatar_image_large_raw"]:
<%
id_csssafe = urllib.quote(p["identity"]).replace("%", "___").replace(".", "___").replace("/", "___")
p["avatar_class_large"] = "avatar_large__" + id_csssafe
%>
    span.{{p["avatar_class_large"]}} {
      background: url("data:image/jpg;base64,{{base64.b64encode(p["avatar_image_large_raw"])}}")
                  center center no-repeat;
    }
%endif
%if p["avatar_image_raw"]:
<%
p["avatar_class"] = "avatar__" + id_csssafe
%>
    span.{{p["avatar_class"]}} {
      background: url("data:image/jpg;base64,{{base64.b64encode(p["avatar_image_raw"])}}")
                  center center no-repeat;
    }
%endif
%endfor
    #chat_picture {
%if skypedata.CHATS_TYPE_SINGLE == chat["type"]:
      display: none;
%elif chat_picture:
      background: url("data:image/jpg;base64,{{base64.b64encode(chat_picture_raw)}}") center center no-repeat;
      margin: 0 10px 0 10px;
      display: block;
      width: {{chat_picture.Width}}px;
      height: {{chat_picture.Height}}px;
%endif
    }
%if emoticons_used:
    span.emoticon {
      margin-top: 1px;
      display: inline-block;
      height: 19px;
      width: 19px;
      color: rgba(255, 255, 255, 0);
      text-align: center;
      word-wrap: normal;
      line-height: 30px;
    }
%endif
%for e in emoticons_used:
    span.emoticon.{{e}} {
      background: url("data:image/gif;base64,{{getattr(emoticons, e).data}}")
                  center center no-repeat;
    }
%endfor
  </style>
  <script>
    var HIGHLIGHT_STYLES = 10;
    var style_counter = 0;
    var hilite_counter = 0;

    function toggle_element(id, id_hide) {
      var el = document.getElementById(id);
      el.style.visibility = "visible";
      el.style.display = el.style.display != "block" ? "block" : "none";
      if (el.style.display == "block") {
        var el_hide = document.getElementById(id_hide);
        if (el_hide) {
          el_hide.style.display = "none";
        }
      }
      return false;
    }

    function highlight(keyword, elements, style) {
      var last = elements.length;
      for (var i = 0; i < last; i++) {
        var cn = elements[i];
        if ("undefined" != typeof(cn)) {
          if (3 == cn.nodeType) {
            addHighlight(keyword, cn, style);
          } else if (0 < cn.childNodes.length && "a" != cn.tagName.toLowerCase()) {
            highlight(keyword, cn.childNodes, style);
          }
        }
      }
    }

    function addHighlight(keyword, container, style) {
      var val = container.nodeValue;
      if (-1 == val.toLowerCase().indexOf(keyword)) return;
      // As JavaScript regex character classes are not Unicode aware,
      // match word boundaries on non-word and non-Unicode characters.
      pattern = new RegExp("(^|[^\\\\\\\\w\\\\\\\\u0081-\\\\\\\\uFFFF])(" + keyword + ")([^\\\\\\\\w\\\\\\\\u0081-\\\\\\\\uFFFF]|$)", "ig");
      replaceWith = '$1<span class="' + style + '">$2</span>$3';
      html = val.replace(pattern, replaceWith);
      found = (html != val);
      if (found) {
        var textnode = document.createElement("text");
        textnode.innerHTML = html;
        try {
          var p = container.parentNode;
          p.replaceChild(textnode, container);
        } catch (e) {}
      }
    }

    function unhighlight(container, style) {
      if (container) {
        var content = container.innerHTML; 
        var re = new RegExp("<span class=['\\"]" + style + "['\\"]>(.*?)<\/span>", "ig");
        content = content.replace(re, "$1"); 
        container.innerHTML = content;
      }
    }

    function hilite(link) {
      if (link.className.indexOf("highlight") < 0) {
        var base_style = "highlight" + (style_counter % HIGHLIGHT_STYLES + 1);
        var style = "highlight_id" + hilite_counter + " " + base_style;
        link.title = "Unhighlight '" + link.textContent + "'";
        link.className = style;
        var elements = document.getElementsByClassName("message_content");
        highlight(link.textContent, elements, style);
        var highlights = document.getElementsByClassName(style);
        if (highlights.length > 1) {
          highlights[1].scrollIntoView(); // 0-th element is link
        }
        hilite_counter++;
        style_counter++;
      } else {
        link.title = "Highlight '" + link.textContent + "' and go to first occurrence";
        unhighlight(document.getElementById("content_table"), link.className);
        link.className = "";
        style_counter--;
      }
      return false;
    }

    function getInnerText(el) {
      if (typeof el == "string") return el;
      if (typeof el == "undefined") { return el };
      if (el.innerText) return el.innerText;
      var str = "";
      
      var cs = el.childNodes;
      var l = cs.length;
      for (var i = 0; i < l; i++) {
        switch (cs[i].nodeType) {
          case 1: //ELEMENT_NODE
            str += getInnerText(cs[i]);
            break;
          case 3:	//TEXT_NODE
            str += cs[i].nodeValue;
            break;
        }
      }
      return str;
    }

    function sort_stats(link, type) {
      if (link.className.indexOf("selected") >= 0) {
        return false;
      }
      var rowlist = document.getElementsByClassName("stats_row");
      var rows = [];
      for (var i = 0, ll = rowlist.length; i != ll; rows.push(rowlist[i++]));
      var sortfn = function(a, b) {
        var aa = "", bb = "";
        var name1 = getInnerText(a.children[0]).toLowerCase();
        var name2 = getInnerText(b.children[0]).toLowerCase();
        switch (type) {
          case "name":
            aa = name1;
            bb = name2;
            break;
          case "callduration":
            var a_rows = a.children[1].children[0].children[0];
            for (var i = 0; i < a_rows.children.length; i++) {
              if (a_rows.children[i].className.indexOf("callduration") != -1) {
                aa = -parseFloat(a_rows.children[i].title);
                break;
              }
            }
            var b_rows = b.children[1].children[0].children[0];
            for (var i = 0; i < b_rows.children.length; i++) {
              if (b_rows.children[i].className.indexOf("callduration") != -1) {
                bb = -parseFloat(b_rows.children[i].title);
                break;
              }
            }
            break;
          default: // messages characters sms smschars calls files
            for (var i = 0; i < a.children[2].children.length; i++) {
              if (type == a.children[2].children[i].className) {
                aa = -parseInt(getInnerText(a.children[2].children[i]), 10);
              }
            }
            for (var i = 0; i < b.children[2].children.length; i++) {
              if (type == b.children[2].children[i].className) {
                bb = -parseInt(getInnerText(b.children[2].children[i]), 10);
              }
            }
            break;
        }
        if (("" == aa) && ("" == bb)) {
          aa = name1;
          bb = name2;
        }
        if (aa == bb) return 0;
        if (aa <  bb) return -1;
        return 1;
      }
      rows.sort(sortfn);
      var table = document.getElementById("stats_data");
      for (var i = 0; i < rows.length; i++) {
        table.tBodies[0].appendChild(rows[i]);
      }
      var linklist = document.getElementsByClassName("selected");
      for (var i = 0; i < linklist.length; i++) {
        linklist[i].className = "";
      }
      link.className = "selected";
      return false;
    }
  </script>
</head>
<body>
<table id="body_table">
<tr><td>
  <table id="header_table">
  <tr>
    <td id="header_left">
%if skypedata.CHATS_TYPE_SINGLE == chat["type"]:
%for p in filter(lambda p: p["identity"] != db.id, participants):
      <div><span class="avatar_large header {{p["avatar_class_large"]}}" title="{{p["name"]}}{{(" (%s)" % p["identity"]) if p["name"] != p["identity"] else ""}}"></span><br />{{p["name"]}}
%if p["name"] != p["identity"]:
      <br /><span class="identity">{{p["identity"]}}</span>
%endif
      </div>
%endfor
%elif chat_picture:
      <span id="chat_picture" title="{{chat["title"]}}"></span>
%endif
    </td>
    <td id="header_center">
      <div id="header">{{chat["title_long"]}}.</div><br />
      Showing {{util.plural("message", message_count)}}
%if date1 and date2:
      from <b>{{date1}}</b> to <b>{{date2}}</b>
%endif
      .<br />
%if chat["created_datetime"]:
      Chat created on <b>{{chat["created_datetime"].strftime("%d.%m.%Y")}}</b>,
%else:
      Chat has
%endif
      <b>{{util.plural("message", chat["message_count"] or 0)}}</b> in total.<br />
      Source: <b>{{db.filename}}</b>.<br /><br />
%if skypedata.CHATS_TYPE_SINGLE != chat["type"]:
        <a title="Click to show/hide participants" href="javascript:;" onclick="return toggle_element('participants', 'statistics')">Participants</a>
%endif
%if stats and (stats["counts"] or stats["info_items"]):
        <a title="Click to show/hide statistics and wordcloud" class="statistics" href="javascript:;" onclick="return toggle_element('statistics', 'participants')">Statistics</a>
%endif
    </td>
    <td id="header_right">
%if skypedata.CHATS_TYPE_SINGLE == chat["type"]:
%for p in filter(lambda p: p["identity"] == db.id, participants):
      <div><span class="avatar_large header {{p["avatar_class_large"]}}" title="{{p["name"]}}{{(" (%s)" % p["identity"]) if p["name"] != p["identity"] else ""}}"></span><br />{{p["name"]}}
%if p["name"] != p["identity"]:
      <br /><span class="identity">{{p["identity"]}}</span>
%endif
      </div>
%endfor
%endif
    </td>
  </tr></table>

%if skypedata.CHATS_TYPE_SINGLE != chat["type"]:
  <div id="participants">
%for p in sorted(participants, key=lambda p: p["name"]):
    <span><span class="avatar_large {{p["avatar_class_large"]}}" title="{{p["name"]}} ({{p["identity"]}})"></span>{{p["name"]}}<br /><span class="identity">{{p["identity"]}}</span></span>
%endfor
  </div>
%endif

  <div id="statistics">
    <table id="stats_data">
%for label, value in stats["info_items"]:
      <tr><td>{{label}}:</td><td colspan="2">{{value}}</td></tr>
%endfor
%if len(stats["counts"]) > 1:
      <tr><td></td><td><div id="sort_header"><b>Sort by:</b>
        <a title="Sort statistics by name" href="#" onClick="return sort_stats(this, 'name');" class="selected">Name</a>
%if stats["messages"]:
        <a title="Sort statistics by messages" href="#" onClick="return sort_stats(this, 'message');">Messages</a>
        <a title="Sort statistics by characters" href="#" onClick="return sort_stats(this, 'character');">Characters</a>
%endif
%if stats["smses"]:
        <a title="Sort statistics by SMS messages" href="#" onClick="return sort_stats(this, 'SMS message');">SMSes</a>
        <a title="Sort statistics by SMS characters" href="#" onClick="return sort_stats(this, 'SMS character');">SMS characters</a>
%endif
%if stats["calls"]:
        <a title="Sort statistics by calls" href="#" onClick="return sort_stats(this, 'call');">Calls</a>
        <a title="Sort statistics by call duration" href="#" onClick="return sort_stats(this, 'callduration');">Call duration</a>
%endif
%if stats["transfers"]:
        <a title="Sort statistics by files sent" href="#" onClick="return sort_stats(this, 'file');">Files</a>
%endif
      </div></td><td></td></tr>
%endif
%for p in filter(lambda p: p["identity"] in stats["counts"], participants):
      <tr class="stats_row">
        <td><table><tr><td><span class="avatar header {{p["avatar_class"]}}" title="{{p["name"]}}"></span></td><td><span>{{p["name"]}}<br /><span class="identity">{{p["identity"]}}</span></span></td></tr></table></td>
        <td><table class="plot_table">
<%
stat_rows = [] # [(type, label, count, total)]
if stats["counts"][p["identity"]]["messages"]:
  stat_rows.append(("messages", "message", stats["counts"][p["identity"]]["messages"], stats["messages"]))
  stat_rows.append(("messages", "character", stats["counts"][p["identity"]]["chars"], stats["chars"]))
if stats["counts"][p["identity"]]["smses"]:
  stat_rows.append(("smses", "SMS message", stats["counts"][p["identity"]]["smses"], stats["smses"]))
  stat_rows.append(("smses", "SMS character", stats["counts"][p["identity"]]["smschars"], stats["smschars"]))
if stats["counts"][p["identity"]]["calls"]:
  stat_rows.append(("calls", "call", stats["counts"][p["identity"]]["calls"], stats["calls"]))
if stats["counts"][p["identity"]]["calldurations"]:
  stat_rows.append(("calls", "callduration", stats["counts"][p["identity"]]["calldurations"], stats["calldurations"]))
if stats["counts"][p["identity"]]["files"]:
  stat_rows.append(("files", "file", stats["counts"][p["identity"]]["files"], stats["files"]))
  stat_rows.append(("files", "byte", stats["counts"][p["identity"]]["bytes"], stats["bytes"]))
%>
%for type, label, count, total in stat_rows:
<%
percent = util.safedivf(count * 100, total)
text_cell1 = "%d%%" % round(percent) if (round(percent) > 9) else ""
text_cell2 = "" if text_cell1 else "%d%%" % round(percent)
if "byte" == label:
  text_total = util.format_bytes(total)
elif "callduration" == label:
  text_total = util.format_seconds(total)
else:
  text_total = util.plural(label, total)
%>
          <tr title="{{util.round_float(percent)}}% of {{text_total}} in total" class="{{label}}"><td>
            <table class="plot_row {{type}}"><tr><td style="width: {{"%.2f" % percent}}%;">{{text_cell1}}</td><td style="width: {{"%.2f" % (100 - percent)}}%;">{{text_cell2}}</td></tr></table>
          </td></tr>
%endfor
        </table></td><td>
%for type, label, count, total in stat_rows:
<%
if "byte" == label:
  text = util.format_bytes(count)
elif "callduration" == label:
  text = util.format_seconds(count, "call")
else:
  text = util.plural(label, count)
%>
          <div class="{{label}}">{{text}}</div>
%endfor
        </td>
      </tr>
%endfor
    </table>

%if stats["wordcloud"]:
    <div id="wordcloud">
<%
sizes = {7: "2.5em;", 6: "2.1em;", 5: "1.75em;", 4: "1.5em;", 3: "1.3em;", 2: "1.1em;", 1: "0.85em", 0: "0.8em;"}
%>
%for word, count, size in stats["wordcloud"]:
      <span style="font-size: {{sizes[size]}}"><a title="Highlight '{{word}}' and go to first occurrence" href="#" onClick="return hilite(this);">{{word}}</a> ({{count}})</span> 
%endfor
    </div>
%endif

%if stats["transfers"]:
    <div id="transfers">
      <span>Sent and received files:</span>
      <table style="width: 100%">
%for f in stats["transfers"]:
<%
from_remote = (f["partner_handle"] == db.id and skypedata.TRANSFER_TYPE_INBOUND == f["type"]) or \
              (f["partner_handle"] != db.id and skypedata.TRANSFER_TYPE_OUTBOUND == f["type"])
partner = f["partner_dispname"] or db.get_contact_name(f["partner_handle"])
f_datetime = datetime.datetime.fromtimestamp(f["starttime"]).strftime("%Y-%m-%d %H:%M") if f.get("starttime") else ""
%>
        <tr><td{{" class='remote'" if from_remote else ""}}>{{partner if from_remote else db.account["name"]}}</td><td>
          <a href="{{util.path_to_url(f["filepath"] or f["filename"])}}" target="_blank">{{f["filepath"] or f["filename"]}}</a>
        </td><td>
          {{util.format_bytes(int(f["filesize"]))}}
        </td><td>
          {{f_datetime}}
        </td></tr>
%endfor
      </table>
    </div>
%endif
  </div>
</td></tr>
<tr><td>
  <table id="content_table">
%for chunk in message_buffer:
{{chunk}}
%endfor
  </table>
</td></tr></table>
<div id="footer">Exported with {{conf.Title}} on {{datetime.datetime.now().strftime("%d.%m.%Y %H:%M")}}.</div>
</body>
</html>
"""


"""HTML chat history export template for the messages part."""
CHAT_MESSAGES_HTML = """<%
import datetime
import skypedata, util

previous_day = datetime.date.fromtimestamp(0)
previous_author = None
%>
%for m in messages:
%if m["datetime"].date() != previous_day:
<%
# Day has changed: insert a date header
day = m["datetime"].date()
weekday, weekdate = util.get_locale_day_date(day)
previous_author = None
%>
  <tr>
    <td class="t1"></td>
    <td class="day t2"></td>
    <td class="day t3"></td>
    <td class="day" colspan="2"><span class="weekday">{{weekday}}</span>, {{weekdate}}</td>
  </tr>
%endif
<%
text = parser.parse(m, html={"export": True})
from_name = m["from_dispname"] if previous_author != m["author"] else ""
# Info messages like "/me is thirsty" -> author on same line.
is_info = (skypedata.MESSAGES_TYPE_INFO == m["type"])
# Kludge to get single-line messages with an emoticon to line up correctly
# with the author, as emoticons have an upper margin pushing the row higher
text_plain = m.get("body_txt", text)
emot_start = '<span class="emoticon '
shift_row = emot_start in text and (("<br />" not in text and len(text_plain) < 140) or text.index(emot_start) < 140)
author_class = "remote" if m["author"] != db.id else "local"
%>
  <tr{{' class="shifted"' if shift_row else ""}}>
    <td class="author {{author_class}}" colspan="2">{{from_name if not is_info else ""}}</td>
    <td class="t3"></td>
    <td class="message_content"><div>
%if is_info:
    <span class="{{author_class}}">{{m["from_dispname"]}}</span>
%endif
    {{text}}
    </div></td>
    <td class="timestamp" title="{{m["datetime"].strftime("%Y-%m-%d %H:%M:%S")}}">
%if m["edited_timestamp"]:
    {{m["datetime"].strftime("%H:%M")}}<span class="{{"edited" if m["body_xml"] else "removed"}}" title="{{"Edited" if m["body_xml"] else "Removed"}} {{datetime.datetime.fromtimestamp(m["edited_timestamp"]).strftime("%H:%M:%S")}}">&nbsp;&nbsp;&nbsp;</span>
%else:
    {{m["datetime"].strftime("%H:%M")}}
%endif
    </td>
  </tr>
<%
previous_day = m["datetime"].date()
previous_author = m["author"]
%>
%endfor
"""



"""TXT chat history export template."""
CHAT_TXT = """<%
import datetime
import conf, skypedata, util
%>History of Skype {{chat["title_long_lc"]}}.
Showing {{util.plural("message", message_count)}}{{" from %s to %s" % (date1, date2) if (date1 and date2) else ""}}.
Chat {{"created on %s, " % chat["created_datetime"].strftime("%d.%m.%Y") if chat["created_datetime"] else ""}}{{util.plural("message", chat["message_count"] or 0)}} in total.
Source: {{db.filename}}.
Exported with {{conf.Title}} on {{datetime.datetime.now().strftime("%d.%m.%Y %H:%M")}}.
-------------------------------------------------------------------------------

%for chunk in message_buffer:
{{chunk}}
%endfor
"""


"""TXT chat history export template for the messages part."""
CHAT_MESSAGES_TXT = """<%
import datetime
import skypedata, util

previous_day = datetime.date.fromtimestamp(0)
%>
%for m in messages:
%if m["datetime"].date() != previous_day:
<%
# Day has changed: insert a date header
day = m["datetime"].date()
weekday, weekdate = util.get_locale_day_date(day)
previous_day = m["datetime"].date()
%>

{{weekday}}, {{weekdate}}
----------------------------------------

%endif
%if skypedata.MESSAGES_TYPE_INFO == m["type"]:
{{m["datetime"].strftime("%H:%M")}}
{{m["from_dispname"]}} {{parser.parse(m, text=True)}}
%else:
{{m["datetime"].strftime("%H:%M")}} {{m["from_dispname"]}}:
{{parser.parse(m, text=True)}}
%endif

%endfor
"""


"""HTML data grid export template."""
GRID_HTML = """<%
import datetime
import conf, images, util
%><!DOCTYPE HTML><html>
<head>
    <meta http-equiv='Content-Type' content='text/html;charset=utf-8' />
    <meta name="Author" content="{{conf.Title}}">
    <title>{{title}}</title>
    <link rel="shortcut icon" type="image/png" href="data:image/ico;base64,{{images.Icon16x16_8bit.data}}"/>
    <style>
        * { font-family: {{conf.HistoryFontName}}; font-size: 11px; }
        body {
            background: {{conf.HistoryBackgroundColour}};
            margin: 0px 10px 0px 10px;
        }
        .header { font-size: 1.1em; font-weight: bold; color: {{conf.HistoryLinkColour}}; }
        .header_table {
            width: 100%;
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
            font-family: {{conf.HistoryFontName}};
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
        a, a.visited { color: conf.HistoryLinkColour; text-decoration: none; }
        a:hover, a.visited:hover { text-decoration: underline; }
        .footer {
          text-align: center;
          padding-bottom: 10px;
          color: #666;
        }
        .header { font-size: 1.1em; font-weight: bold; color: conf.HistoryLinkColour; }
        td { text-align: left; vertical-align: top; }
    </style>
</head>
<body>
<table class="body_table">
<tr><td><table class="header_table">
    <tr>
        <td class="header_left"></td>
        <td>
            <div class="header">{{title}}</div><br />
            Source: <b>{{db_filename}}</b>.<br />
            <b>{{row_count}}</b> {{util.plural("row", row_count, with_items=False)}} in results.<br />
%if sql:
            <b>SQL:</b> {{escape(sql)}}
%endif
        </td>
    </tr></table>
</td></tr><tr><td><table class='content_table'>
<tr><th>#</th>
%for col in columns:
<th>{{col}}</th>
%endfor
</tr>
%for i, row in enumerate(rows):
<tr>
<td>{{i + 1}}</td>
%for col in columns:
<td>{{escape("" if row[col] is None else row[col])}}</td>
%endfor
</tr>
%endfor
</table>
</td></tr></table>
<div class='footer'>Exported with {{conf.Title}} on {{datetime.datetime.now().strftime("%d.%m.%Y %H:%M")}}.</div>
</body>
</html>
"""


"""TXT SQL insert statements export template."""
SQL_TXT = """<%
import datetime, re, string
import conf

UNPRINTABLES = "".join(set(unichr(i) for i in range(128)).difference(string.printable))
RE_UNPRINTABLE = re.compile("[%s]" % "".join(map(re.escape, UNPRINTABLES)))
str_cols = ", ".join(columns)
%>-- {{title}}.
-- Source: {{db_filename}}.
-- Exported with {{conf.Title}} on {{datetime.datetime.now().strftime("%d.%m.%Y %H:%M")}}.
%if sql:
-- SQL: {{sql}}
%endif
%if table:
{{create_sql}}
%endif

%for row in rows:
<%
values = []
%>
%for col in columns:
<%
value = row[col]
if isinstance(value, basestring):
    if RE_UNPRINTABLE.search(value):
        if isinstance(value, unicode):
            try:
                value = value.encode("latin1")
            except:
                value = value.encode("utf-8", errors="replace")
        value = "X'%s'" % value.encode("hex").upper()
    else:
        if isinstance(value, unicode):
            value = value.encode("utf-8")
        value = '"%s"' % (value.encode("string-escape").replace('\"', '""'))
elif value is None:
    value = "NULL"
else:
    value = str(value)
values.append(value)
%>
%endfor
INSERT INTO {{table}} ({{str_cols}}) VALUES ({{", ".join(values)}});
%endfor
"""



"""HTML statistics template, for use with HtmlWindow."""
STATS_HTML = """<%
import datetime, urllib
import conf, skypedata, util

%>
<table cellpadding="0" cellspacing="0" width="100%"><tr>
  <td><a name="top"><b>Statistics for currently shown messages in {{chat["title_long_lc"]}}:</b></a></td>
%if stats.get("wordcloud"):
  <td align="right"><a href="#cloud">Jump to word cloud</a></td>
%endif
</tr><tr><td><font size="0">&nbsp;</font></td></tr></table>
<br />
<table>
%for label, value in stats["info_items"]:
  <tr><td width="200" valign="top">{{label}}:</td><td valign="top">{{value}}</td></tr>
%endfor

%if len(stats["counts"]) > 1:
  <tr><td><br /><br /></td><td valign="bottom"><font size="2">
    <table cellpadding="0" cellspacing="0"><tr>
      <td nowrap="nowrap"><b>Sort by:&nbsp;&nbsp;&nbsp;</b></td>
%for name, label in [("name", "Name"), ("messages", "Messages"), ("chars", "Characters"), ("smses", "SMS messages"), ("smschars", "SMS characters"), ("calls", "Calls"), ("calldurations", "Call duration"), ("files", "Files")]:
%if "name" == name or stats[name]:
%if sort_by == name:
      <td><font color="gray">{{label}}</font>&nbsp;&nbsp;&nbsp;&nbsp;</td>
%else:
      <td><a href="sort://{{name}}">{{label}}</a>&nbsp;&nbsp;&nbsp;&nbsp;</td>
%endif
%endif
%endfor
    </tr></table>
  </font></td></tr>
%endif

<%
colormap = {"messages": conf.PlotMessagesColour, "smses": conf.PlotSMSesColour, "calls": conf.PlotCallsColour, "files": conf.PlotFilesColour}
sort_key = lambda p: -stats["counts"][p["identity"]].get(sort_by, 0) if "name" != sort_by else p["name"]
participants_sorted = sorted(filter(lambda p: p["identity"] in stats["counts"], participants), key=sort_key)
%>

%for p in participants_sorted:
<%
avatar_filename = "avatar__default.jpg"
if "avatar_bitmap" in p:
    avatar_filename = "%s_%s.jpg" % tuple(map(urllib.quote, (db.filename.encode("utf-8"), p["identity"])))
stat_rows = [] # [(type, label, count, total)]
if stats["counts"][p["identity"]]["messages"]:
  stat_rows.append(("messages", "message", stats["counts"][p["identity"]]["messages"], stats["messages"]))
  stat_rows.append(("messages", "character", stats["counts"][p["identity"]]["chars"], stats["chars"]))
if stats["counts"][p["identity"]]["smses"]:
  stat_rows.append(("smses", "SMS message", stats["counts"][p["identity"]]["smses"], stats["smses"]))
  stat_rows.append(("smses", "SMS character", stats["counts"][p["identity"]]["smschars"], stats["smschars"]))
if stats["counts"][p["identity"]]["calls"]:
  stat_rows.append(("calls", "call", stats["counts"][p["identity"]]["calls"], stats["calls"]))
if stats["counts"][p["identity"]]["calldurations"]:
  stat_rows.append(("calls", "callduration", stats["counts"][p["identity"]]["calldurations"], stats["calldurations"]))
if stats["counts"][p["identity"]]["files"]:
  stat_rows.append(("files", "file", stats["counts"][p["identity"]]["files"], stats["files"]))
  stat_rows.append(("files", "byte", stats["counts"][p["identity"]]["bytes"], stats["bytes"]))
%>
  <tr>
    <td valign="top">
      <table cellpadding="0" cellspacing="0"><tr>
        <td valign="top"><img src="memory:{{avatar_filename}}"/>&nbsp;&nbsp;</td>
        <td valign="center">{{p["name"]}}<br /><font size="2" color="gray">{{p["identity"]}}</font></td>
      </tr></table>
    </td><td valign="top">
%for type, label, count, total in stat_rows:
<%
percent = int(round(util.safedivf(count * 100, total)))
text_cell1 = "&nbsp;%d%%&nbsp;" % round(percent) if (round(percent) > 9) else ""
text_cell2 = "" if text_cell1 else "&nbsp;%d%%&nbsp;" % percent
if "byte" == label:
  text_cell3 = util.format_bytes(count)
elif "callduration" == label:
  text_cell3 = util.format_seconds(count, "call")
else:
  text_cell3 = util.plural(label, count)
%>
      <table cellpadding="0" width="100%" cellspacing="0"><tr>
        <td bgcolor="{{colormap[type]}}" width="{{percent * conf.PlotWidth / 100}}" align="center"><font color="#FFFFFF" size="2"><b>{{text_cell1}}</b></font></td>
        <td bgcolor="{{conf.PlotBgColour}}" width="{{(100 - percent) * conf.PlotWidth / 100}}" align="center"><font color="{{conf.PlotMessagesColour}}" size="2"><b>{{text_cell2}}</b></font></td>
        <td nowrap="nowrap">&nbsp;{{text_cell3}}</td>
      </tr></table>
%endfor
    </td>
  </tr>
%endfor
  
</table>

%if stats.get("wordcloud"):
<br /><hr />
<table cellpadding="0" cellspacing="0" width="100%"><tr>
  <td><a name="cloud"><b>Word cloud for currently shown messages:</b></a></td>
  <td align="right"><a href="#top">Back to top</a></td>
</tr></table>
<br /><br />
%for word, count, size in stats["wordcloud"]:
<font color="blue" size="{{size}}"><a href="{{word}}">{{word}}</a> ({{count}}) </font>
%endfor
%endif

%if stats.get("transfers"):
<br /><hr /><table cellpadding="0" cellspacing="0" width="100%"><tr><td><a name="transfers"><b>Sent and received files:</b></a></td><td align="right"><a href="#top">Back to top</a></td></tr></table><br /><br />
<table width="100%">
%for f in stats["transfers"]:
<%
from_remote = (f["partner_handle"] == db.id and skypedata.TRANSFER_TYPE_INBOUND == f["type"]) or \
              (f["partner_handle"] != db.id and skypedata.TRANSFER_TYPE_OUTBOUND == f["type"])
partner = f["partner_dispname"] or db.get_contact_name(f["partner_handle"])
f_datetime = datetime.datetime.fromtimestamp(f["starttime"]).strftime("%Y-%m-%d %H:%M") if f.get("starttime") else ""
%>
  <tr>
    <td align="right" nowrap="" valign="top"><font size="2" face="{{conf.HistoryFontName}}" color="{{conf.HistoryRemoteAuthorColour if from_remote else conf.HistoryLocalAuthorColour}}">{{partner if from_remote else db.account["name"]}}</font></td>
    <td nowrap="" valign="top"><font size="2" face="{{conf.HistoryFontName}}"><a href="{{util.path_to_url(f["filepath"] or f["filename"])}}">{{f["filepath"] or f["filename"]}}</a></font></td>
    <td align="right" valign="top"><font size="2" face="{{conf.HistoryFontName}}">{{util.format_bytes(int(f["filesize"]))}}</font></td>
    <td nowrap="" valign="top"><font size="2" face="{{conf.HistoryFontName}}">{{f_datetime}}</font></td>
  </tr>
%endfor
</table>
%endif
"""


"""HTML template for search result row for a matched chat, HTML table row."""
SEARCH_ROW_CHAT_HTML = """<%
import re
import conf

title = chat["title"]
if title_matches:
    title = pattern_replace.sub(lambda x: "<b>%s</b>" % x.group(0), title)
%>
<tr>
  <td align="right" valign="top">
    <font color="{{conf.HistoryGreyColour}}">{{result_count}}</font>
  </td><td colspan="2">
    <a href="chat:{{chat["id"]}}">
    <font color="{{conf.HistoryLinkColour}}">{{title}}</font></a><br />
%if title_matches:
    Title matches.<br />
%endif
%if matching_authors:
    Participant matches: 
%for i, c in enumerate(matching_authors):
<%
name = c["fullname"] or c["displayname"]
name_replaced = pattern_replace.sub(wrap_b, name)
identity_replaced = "" if (c["identity"] == name) else " (%s)" % pattern_replace.sub(wrap_b, c["identity"])
%>
{{", " if i else ""}}{{name_replaced}}{{identity_replaced}}{{"." if i == len(matching_authors) - 1 else ""}}
%endfor
<br />
%endif
</td></tr>
"""


"""HTML template for search result row of a matched contact, HTML table row."""
SEARCH_ROW_CONTACT_HTML = """<%
import conf, skypedata
%>
%if count <= 1 and result_count > 1:
<tr><td colspan='3'><hr /></td></tr>
%endif
<tr>
  <td align="right" valign="top">
    <font color="{{conf.HistoryGreyColour}}">{{result_count}}</font>
  </td><td colspan="2">
    <font color="{{conf.ResultContactFieldColour}}">{{pattern_replace.sub(wrap_b, contact["name"])}}</font>
    <br /><table>
%for field in filter(lambda x: x in fields_filled, match_fields):
      <tr>
        <td nowrap valign="top"><font color="{{conf.ResultContactFieldColour}}">{{skypedata.CONTACT_FIELD_TITLES[field]}}</font></td>
        <td>&nbsp;</td><td>{{fields_filled[field]}}</td>
      </tr>
%endfor
</table><br /></td></tr>
"""


"""HTML template for search result of chat messages, HTML table row."""
SEARCH_ROW_MESSAGE_HTML = """<%
import datetime
import conf, skypedata
%>
%if count <= 1 and result_count > 1:
<tr><td colspan='3'><hr /></td></tr>
%endif
<tr>
  <td align="right" valign="top">
    <font color="{{conf.HistoryGreyColour}}">{{result_count}}</font>
  </td><td valign="top">
<%
after = ""
if (skypedata.CHATS_TYPE_SINGLE != chat["type"]) or (m["author"] == search["db"].id):
  after = " in %s" % chat_title
%>
    <a href="message:{{m["id"]}}"><font color="{{conf.HistoryLinkColour}}">{{m["from_dispname"]}}{{after}}</font></a>
  </td><td align="right" nowrap>
    &nbsp;&nbsp;<font color="{{conf.HistoryTimestampColour}}">{{datetime.datetime.fromtimestamp(m["timestamp"]).strftime("%d.%m.%Y %H:%M")}}</font>
  </td>
</tr>
<tr><td></td>
  <td width="100%" valign="top" colspan="2">
%if skypedata.MESSAGES_TYPE_INFO == m["type"]:
    <font color="{{conf.HistoryRemoteAuthorColour if m["author"] == search["db"].id else conf.HistoryLocalAuthorColour}}">{{m["from_dispname"]}}</font>
%endif
  {{body}}<br /></td>
</tr>
"""



"""HTML template for search results header, start of HTML table."""
SEARCH_HEADER_HTML = """<%
import conf
%>
<font size="2" face="{{conf.HistoryFontName}}">
Results for "{{escape(text)}}" from {{fromtext}}:
%if "all tables" != fromtext:
<br /><br />
<table width="600" cellpadding="2" cellspacing="0">
%endif
"""


"""HTML template for table search results header, start of HTML table."""
SEARCH_ROW_TABLE_HEADER_HTML = """
<br /><br /><b>Table {{table["name"]}}:</b><br />
<table border="1" cellpadding="4" cellspacing="0" width="1000">
<tr>
<th>#</th>
%for col in table["columns"]:
<th>{{escape(col["name"])}}</th>
%endfor
</tr>
"""


"""HTML template for search result of DB table row, HTML table row."""
SEARCH_ROW_TABLE_HTML = """<%
import re
import conf, templates
%>
<tr>
<td align="right" valign="top"><a href="table:{{escape(table["name"])}}:{{count}}">{{count}}</a></td>
%for col in table["columns"]:
<%
value = row[col["name"]]
value = value if value is not None else ""
value = templates.SAFEBYTE_RGX.sub(templates.SAFEBYTE_REPL, unicode(value))
%>
<td valign="top">{{pattern_replace.sub(wrap_b, escape(value))}}</td>
%endfor
</tr>
"""


"""Text shown in Help -> About dialog (HTML content)."""
ABOUT_TEXT = """
<%
import sys
import conf
%>
<font size="2" face="Tahoma">
<table cellpadding="0" cellspacing="0"><tr><td valign="top">
<img src="memory:skyperious.png" /></td><td width="10"></td><td valign="center">
<b>{{conf.Title}} version {{conf.Version}}</b>, released {{conf.VersionDate}}.<br /><br />

{{conf.Title}} is written in Python, released as free open source software
under the MIT License.
</td></tr></table><br /><br />


&copy; 2011-2013, Erki Suurjaak.
<a href="{{conf.HomeUrl}}">suurjaak.github.com/Skyperious</a><br /><br /><br />



{{conf.Title}} has been built using the following open source software:
<ul>
  <li>wxPython 2.9.4, <a href="http://wxpython.org">wxpython.org</a></li>
  <li>BeautifulSoup 3.2.1, <a href="http://crummy.com/software/BeautifulSoup">
      crummy.com/software/BeautifulSoup</a></li>
  <li>step, Simple Template Engine for Python,
      <a href="https://github.com/dotpy/step">github.com/dotpy/step</a></li>
  <li>pyparsing 2.0.1,
      <a href="http://pyparsing.wikispaces.com/">pyparsing.wikispaces.com</a></li>
  <li>dateutil, <a href="https://pypi.python.org/pypi/python-dateutil">
      pypi.python.org/pypi/python-dateutil</a></li>
  <li>Skype4Py, <a href="https://github.com/awahlig/skype4py">
      github.com/awahlig/skype4py</a></li>
%if getattr(sys, 'frozen', False):
  <li>Python 2.7.5, <a href="http://www.python.org">www.python.org</a></li>
  <li>PyInstaller 2.0, <a href="http://www.pyinstaller.org">
      www.pyinstaller.org</a></li>
%endif
</ul><br /><br /><br />



Emoticons in HTML export are property of Skype Limited, &copy; 2004-2006,
released under the Skype Component License 1.0.<br /><br />


Default avatar icon from Fancy Avatars, &copy; 2009 Brandon Mathis<br />
<a href="http://brandonmathis.com/projects/fancy-avatars/">
brandonmathis.com/projects/fancy-avatars</a><br /><br />


Several icons from Fugue Icons, &copy; 2010 Yusuke Kamiyamane<br />
<a href="http://p.yusukekamiyamane.com/">p.yusukekamiyamane.com/</a>
</font>
"""



"""Contents of the default page on search page."""
SEARCH_WELCOME_HTML = """
<%
import conf
%>
<font face="{{conf.HistoryFontName}}" size="2">
<center>
<h5><font color="{{conf.HistoryLinkColour}}">Explore the database</font></h5>
<table cellpadding="10" cellspacing="0">
<tr>
  <td>
    <table cellpadding="0" cellspacing="2"><tr><td>
        <img src="memory:HelpSearch.png" />
      </td><td width="10"></td><td valign="center">
        Search over all Skype messages using a simple Google-like <a href="page:#help">syntax</a>.<br />
        <br />
        Or choose other search targets from the toolbar: <br />
        search in contact information, or in chat information, <br />
        or across all database tables.
      </td></tr><tr><td nowrap align="center">
        <b><font color="black">Search</font></b><br />
    </td></tr></table>
  </td>
  <td>
    <table cellpadding="0" cellspacing="2"><tr><td>
        <a href="page:tables"><img src="memory:HelpTables.png" /></a>
      </td><td width="10"></td><td valign="center">
        Browse, filter and change database tables,<br />
        export as HTML, SQL INSERT-statements or CSV.
      </td></tr><tr><td nowrap align="center">
        <a href="page:tables"><b><font color="black">Data tables</font></b></a><br />
    </td></tr></table>
  </td>
</tr>
<tr>
  <td>
    <table cellpadding="0" cellspacing="2"><tr><td>
        <a href="page:chats"><img src="memory:HelpChats.png" /></a>
      </td><td width="10"></td><td valign="center">
        Read Skype chats,
        view statistics and word clouds, <br />
        filter by content, date or author,<br />
        export as HTML, TXT or CSV.
      </td></tr><tr><td nowrap align="center">
        <a href="page:chats"><b><font color="black">Chats</font></b></a><br />
    </td></tr></table>
  </td>
  <td>
    <table cellpadding="0" cellspacing="2"><tr><td>
        <a href="page:sql"><img src="memory:HelpSQL.png" /></a>
      </td><td width="10"></td><td valign="center">
        Make direct SQL queries in the database,<br />
        export results as HTML or CSV.
      </td></tr><tr><td nowrap align="center">
        <a href="page:sql"><b><font color="black">SQL window</font></b></a><br />
    </td></tr></table>
  </td>
</tr>
<tr>
  <td>
    <table cellpadding="0" cellspacing="2"><tr><td>
        <a href="page:info"><img src="memory:HelpInfo.png" /></a>
      </td><td width="10"></td><td valign="center">
        See information about the Skype account in this file.
      </td></tr><tr><td nowrap align="center">
        <a href="page:info"><b><font color="black">Information</font></b></a>
    </td></tr></table>
  </td>
  <td>
    <table cellpadding="0" cellspacing="2"><tr><td>
        <a href="page:contacts"><img src="memory:HelpContacts.png" /></a>
      </td><td width="10"></td><td valign="center">
        Import contacts to Skype from a CSV file,<br />
        like ones exported from MSN or GMail.
      </td></tr><tr><td nowrap align="center">
        <a href="page:contacts"><b><font color="black">Contacts+</font></b></a>
    </td></tr></table>
  </td>
</tr>
</table>
</center>
</font>
"""


"""Long help text shown in a separate tab on search page."""
SEARCH_HELP_LONG = """
<%
import conf
%>
<font size="2" face="{{conf.HistoryFontName}}">

{{conf.Title}} supports a Google-like syntax for searching messages:<br /><br />
<table><tr><td width="500">

  <table border="0" cellpadding="5" cellspacing="1" bgcolor="#E5E5E5"
   valign="top" width="500">
  <tr>
    <td bgcolor="white" width="150">
      <b>Search for exact word or phrase<br /><br />
      <font color="#006600"><code>"do re mi"</code></font>
      <br />
    </td>
    <td bgcolor="white">
      <br /><br />
      Use quotes (<font color="#006600"><code>"</code></font>) to search for
      an exact phrase or word. Quoted text is searched exactly as entered,
      leaving whitespace as-is and ignoring any wildcard characters.
      <br />
    </td>
  </tr>
  <tr>
    <td bgcolor="white" width="150">
      <b>Search for either word<br /><br />
      <font color="#006600"><code>this OR that</code></font>
      <br />
    </td>
    <td bgcolor="white">
      <br /><br />
      To find messages containing at least one of several words,
      include <font color="#006600"><code>OR</code></font> between the words.
      <font color="#006600"><code>OR</code></font> works also
      for phrases and grouped words (but not keywords).
      <br />
    </td>
  </tr>
  <tr>
    <td bgcolor="white" width="150">
      <b>Group words together<br /><br />
      <font color="#006600"><code>(these two) OR this<br/>
      -(none of these)</code></font>
      <br />
    </td>
    <td bgcolor="white">
      <br /><br />
      Surround words with round brackets to group them for <code>OR</code>
      queries or for excluding from results.
      <br />
    </td>
  </tr>
  <tr>
    <td bgcolor="white" width="150">
      <b>Search for partially matching text<br /><br />
      <font color="#006600"><code>bas*ball</code></font>
      <br />
    </td>
    <td bgcolor="white">
      <br /><br />
      Use an asterisk (<font color="#006600"><code>*</code></font>) to make a
      wildcard query: the wildcard will match any text between its front and
      rear characters (including other words).
      <br />
    </td>
  </tr>
  <tr>
    <td bgcolor="white" width="150">
      <b>Search within specific chats<br /><br />
      <font color="#006600"><code>chat:office<br />
      chat:"coffee &amp cig"</code></font>
      <br />
    </td>
    <td bgcolor="white">
      <br /><br />
      To find messages from specific chats only, use the keyword
      <font color="#006600"><code>chat:name</code></font>.<br /><br />
      Search from more than one chat by adding more 
      <font color="#006600"><code>chat:</code></font> keywords.
      <br />
    </td>
  </tr>
  <tr>
    <td bgcolor="white" width="150">
      <b>Search from specific authors<br /><br />
      <font color="#006600"><code>from:maria<br />
      from:"john smith"</code></font>
      <br />
    </td>
    <td bgcolor="white">
      <br /><br />
      To find messages from specific authors only, use the keyword
      <font color="#006600"><code>from:name</code></font>.<br /><br />
      Search from more than one author by adding more
      <font color="#006600"><code>from:</code></font> keywords.
      <br />
    </td>
  </tr>
  <tr>
    <td bgcolor="white" width="150">
      <b>Search from specific time periods<br /><br />
      <font color="#006600"><code>date:2008<br />date:2009-01<br />
      date:2005-12-24..2007</code></font>
      <br />
    </td>
    <td bgcolor="white">
      <br /><br />
      To find messages from specific time periods, use the keyword
      <font color="#006600"><code>date:period</code></font> or
      <font color="#006600"><code>date:periodstart..periodend</code></font>.
      For the latter, either start or end can be omitted.<br /><br />
      A date period can be year, year-month, or year-month-day. Additionally,
      <font color="#006600"><code>date:period</code></font> can use a wildcard
      in place of any part, so
      <font color="#006600"><code>date:*-12-24</code></font> would search for
      all messages from the 24th of December.<br /><br />
      Search from a more narrowly defined period by adding more
      <font color="#006600"><code>date:</code></font> keywords.
      <br />
    </td>
  </tr>
  <tr>
    <td bgcolor="white" width="150">
      <b>Exclude words or keywords<br /><br />
      <font color="#006600"><code>-notthisword<br />-"not this phrase"<br />
      -(none of these)<br/>-chat:notthischat<br/>-from:notthisauthor<br />
      -date:2013</code></font>
      <br />
    </td>
    <td bgcolor="white">
      <br /><br />
      To exclude certain messages, add a dash
      (<font color="#006600"><code>-</code></font>) in front of words,
      phrases, grouped words or keywords.
    </td>
  </tr>
  <tr>
    <td bgcolor="white" width="150">
      <b>SPECIAL: search specific tables<br /><br />
      <font color="#006600"><code>table:fromthistable<br />
      -table:notfromthistable</code></font>
      <br />
    </td>
    <td bgcolor="white">
      <br /><br />
      When performing search on all columns of all database tables, use the keyword
      <font color="#006600"><code>table:name</code></font> to constrain results
      to specific tables only.<br /><br />
      Search from more than one table by adding more
      <font color="#006600"><code>table:</code></font> keywords, or exclude certain
      tables by adding a <font color="#006600"><code>-table:</code></font> keyword.
      <br />
    </td>
  </tr>
  </table>

</td><td valign="top" align="left">

  <b><font size="3">Examples</font></b><br /><br />

  <ul>
    <li>search for "flickr.com" from John or Jane in chats named "links":
        <br /><br />
        <font color="#006600">
        <code>flickr.com from:john from:jane chat:links</code></font><br />
    </li>
    <li>search from John Smith up to 2011:<br /><br />
        <font color="#006600"><code>from:"john smith" date:..2011</code></font>
        <br />
    </li>
    <li>search for either "John" and "my side" or "Stark" and "your side":
        <br /><br />
        <font color="#006600">
        <code>(john "my side") OR (stark "your side")</code></font><br />
    </li>
    <li>search for either "barbecue" or "grill" in 2012,
        except from June to August:<br /><br />
        <font color="#006600">
        <code>barbecue OR grill date:2012 -date:2012-06..2012-08</code>
        </font><br />
    </li>
    <li>search for "TPS report" in chats named "office"
        (but not named "backoffice") on the first day of the month in 2012:
        <br /><br />
        <font color="#006600">
        <code>"tps report" chat:office -chat:backoffice date:2012-*-1</code>
        </font><br />
    </li>
  </ul>

  <br /><br /><br />
  Search is made on raw Skype message body, so there can be results which do not
  seem to match the query - Skype messages contain more than plain text.<br />
  For example, searching for <font color="#006600"><code>href</code></font> will match a message with body
  <code><font color="blue">&lt;a <font color="red">href</font>=<font
  color="#FF00FF">"http://lmgtfy.com/"</font>&gt;</font>lmgtfy.com<font
  color="blue">&lt;/a&gt;</font></code>,<br />
  displayed as <a href="http://lmgtfy.com/">lmgtfy.com</a>.<br /><br />
  This can be used for finding specific type of messages, for example
  <font color="#006600"><code>&lt;sms</code></font> finds SMS messages, <font color="#006600"><code>&lt;file</code></font> finds transfers and <font color="#006600"><code>&lt;quote</code></font>
  finds quoted messages.


</td></tr></table>
</font>
"""


"""Short help text shown on search page."""
SEARCH_HELP_SHORT = """<%
import os
import conf
helplink = "Search help"
if "nt" == os.name: # In Windows, wx.HtmlWindow shows link whitespace quirkily
    helplink = helplink.replace(" ", "_")
%>
<font size="2" face="{{conf.HistoryFontName}}" color="gray">
For searching messages from specific chats, add "chat:name", and from specific contacts, add "from:name".
&nbsp;&nbsp;<a href=\"page:#help\">{{helplink}}</a>.
</font>
"""
