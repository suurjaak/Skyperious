# -*- coding: utf-8 -*-
"""
HTML and TXT templates for exports and statistics.

------------------------------------------------------------------------------
This file is part of Skyperious - Skype chat history tool.
Released under the MIT License.

@author      Erki Suurjaak
@created     09.05.2013
@modified    02.04.2022
------------------------------------------------------------------------------
"""
import re

# Modules imported inside templates:
#import codecs, collections, datetime, functools, imghdr, json, logging, mimetypes, os, pyparsing, re, string, sys, six, wx
#from skyperious import conf, emoticons, images, skypedata, templates
#from skyperious.lib import util
#from skyperious.lib.vendor import step

"""Regex for replacing low bytes unusable in wx.HtmlWindow (\x00 etc)."""
SAFEBYTE_RGX = re.compile("[\x00-\x08,\x0B-\x0C,\x0E-x1F,\x7F]")

"""Replacer callback for low bytes unusable in wx.HtmlWindow (\x00 etc)."""
SAFEBYTE_REPL = lambda m: m.group(0).encode("unicode-escape").decode("latin1")


"""
HTML chat history export template.

@param   chat               chat data dictionary
@param   date1              first message datetime
@param   date2              last message datetime
@param   db                 SkypeDatabase instance
@param   chat_picture_size  (w, h) or None
@param   chat_picture_raw   image raw binary or None
@param   emoticons_used     {type: {author: count}}
@param   message_buffer     buffer-like object to yield messages content
@param   message_count      total message count
@param   parser             MessageParser instance
@param   participants       [{contact row.., rank, ?avatar_raw_small, ?avatar_raw_large}]
@param   stats              SkypeDatabase.get_collected_stats()
@param   timeline           [{dt, label, count, messages, ?label2}, ]
@param   timeline_units     (topunit, ?subunit)
"""
CHAT_HTML = """<%
import collections, datetime, functools, imghdr, json
import six
from six.moves import urllib
from skyperious import conf, emoticons, images, skypedata, templates
from skyperious.lib import util
from skyperious.lib.vendor import step

%>
<!DOCTYPE HTML><html lang="">
<head>
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
  <meta name="generator" content="{{ conf.Title }} {{ conf.Version }}" />
  <title>Skype {{ chat["title_long_lc"] }}</title>
  <link rel="shortcut icon" type="image/png" href="data:image/png;base64,{{! images.Icon16x16_8bit.data }}"/>
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
      font-family: {{ conf.HistoryFontName }};
      font-size: 11px;
      background: {{ conf.HistoryBackgroundColour }};
      color: black;
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
      font-family: {{ conf.HistoryFontName }};
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
    a, a.visited { color: {{ conf.ExportLinkColour }}; text-decoration: none; cursor: pointer; outline: 0; }
    a:hover, a.visited:hover { text-decoration: underline; }
    #footer {
      text-align: center;
      padding-bottom: 10px;
      color: #666;
    }
    #header { font-size: 1.1em; font-weight: bold; color: {{ conf.ExportLinkColour }}; }
    #header_table {
      width: 100%;
    }
    #header_table td {
      vertical-align: top;
    }
    #header_table #header_left {
      width: 145px;
      text-align: center;
      vertical-align: middle;
    }
    #header_center a {
      text-decoration: underline;
      font-weight: bold;
    }
    #header_center table.links {
      table-layout: fixed;
      width: 100%;
    }
    #header_center table.links td:nth-child(2) {
      text-align: center;
    }
    #header_center table.links td:last-child {
      text-align: right;
    }
    #header_right {
      width: 100%;
    }
    #header_left div, #header_right div {
      overflow: hidden;
      text-align: center;
      text-overflow: ellipsis;
      width: 100px;
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
    .avatar_large {
      float: left;
      position: relative;
      width: 96px;
      height: 96px;
      border: 1px solid lightgray;
    }
    .avatar {
      width: 32px;
      height: 32px;
      text-align: center;
      vertical-align: middle;
      padding: 0 5px 5px 0;
    }
    .avatar_large > img {
      position: absolute;
      top: 0;
      bottom: 0;
      left: 0;
      right: 0;
      margin: auto;
      max-height: 96px;
      max-width: 96px;
    }
    .avatar > img {
      max-height: 32px;
      max-width: 32px;
%if not (util.wx or util.Image):
      object-fit: scale-down;
%endif
    }
    #participants .avatar_large {
      margin-right: 5px;
    }
    #participants .avatar_item span {
      display: inline-block;
      max-width: 100%;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    #content_table td.day {
      border-top: 1px solid {{ conf.HistoryLineColour }};
      border-bottom: 1px solid {{ conf.HistoryLineColour }};
      padding-top: 3px; padding-bottom: 4px;
    }
    #content_table .weekday { font-weight: bold; }
    .timestamp {
      color: {{ conf.HistoryTimestampColour }};
    }
    #content_table .timestamp {
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
      background: url("data:image/png;base64,{{! images.ExportEdited.data }}")
                  center center no-repeat;
    }
    #content_table .timestamp span.removed {
      background: url("data:image/png;base64,{{! images.ExportRemoved.data }}")
                  center center no-repeat;
    }
    #content_table tr.shifted td.author, #content_table tr.shifted td.timestamp { 
      padding-top: 10px;
    }
    #content_table .author { min-width: 90px; text-align: right; }
    .remote, .remote a { color: {{ conf.HistoryRemoteAuthorColour }}; }
    .local, .local a { color: {{ conf.HistoryLocalAuthorColour }}; }
    #content_table .t1 { width: 50px; }
    #content_table .t2 { width: 40px; }
    #content_table .t3 { width: 15px; min-width: 15px; }
    #content_table .day.t3 {
      padding: 5px;
      background: url("data:image/png;base64,{{! images.ExportClock.data }}")
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
    #stats_data > tbody > tr:first-child > td:nth-child(2),
    #stats_data > tbody > tr > td:nth-child(4),
    #stats_data > tbody > tr > td:nth-child(5) {
      vertical-align: top;
    }
    #stats_data > tbody > tr.stats_row > td > table > tbody > tr td:nth-child(2) { /* participant name and identity */
      max-width: 200px;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    #stats_data > tbody > tr.stats_row > td:nth-child(3) {
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
    #stats_data > tbody > tr > td:nth-child(3) {
      color: {{ conf.PlotHoursColour }};
      vertical-align: top;
    }
    #stats_data > tbody > tr > td:nth-child(4) {
      color: {{ conf.PlotDaysColour }};
      vertical-align: top;
    }
    #stats_data > tbody > tr:first-child > td:nth-child(3),
    #stats_data > tbody > tr:first-child > td:nth-child(4) {
      vertical-align: bottom;
    }
    .svg_hover_group:hover {
      opacity: 0.7;
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
      background-color: {{ conf.PlotMessagesColour }};
    }
    table.plot_row.smses td:first-child {
      background-color: {{ conf.PlotSMSesColour }};
    }
    table.plot_row.calls td:first-child {
      background-color: {{ conf.PlotCallsColour }};
    }
    table.plot_row.files td:first-child {
      background-color: {{ conf.PlotFilesColour }};
    }
    table.plot_row.shares td:first-child {
      background-color: {{ conf.PlotSharesColour }};
    }
    table.plot_row td:nth-child(2) {
      background-color: {{ conf.PlotBgColour }};
      color: {{ conf.PlotMessagesColour }};
    }
    #wordcloud {
      border-top: 1px solid #99BBFF;
      margin-top: 10px;
      padding-top: 5px;
    }
    .wordcloud span {
      color: blue;
      padding-right: 5px;
      font-family: Arial, Helvetica, sans-serif;
    }
    .wordcloud span a {
      font-size: 1em;
      color: blue;
    }
    #wordclouds, #emoticons {
      display: none;
      padding-top: 15px;
    }
    #wordclouds > table, #emoticons  {
      border-collapse: collapse;
      width: 100%;
    }
    #wordclouds > table > tbody > tr > td, #emoticons > tbody > tr > td {
      vertical-align: top;
      padding-top: 5px;
      padding-bottom: 10px;
    }
    #wordclouds > table > tbody > tr, #emoticons > tbody > tr {
      border-top: 1px solid #99BBFF;
    }
    #wordclouds > table > tbody > tr > td:first-child, #emoticons > tbody > tr > td:first-child {
      vertical-align: top;
      width: 150px;
    }
    #emoticons td.total {
      text-align: right;
      padding: 13px;
    }
    #emoticons table.emoticon_rows td:nth-child(3) {
      color: {{ conf.PlotHoursColour }};
      text-align: right;
    }
    #emoticons table.emoticon_rows td:nth-child(4) {
      color: #999;
    }
    .toggle_plusminus {
      font-size: 1.5em;
      color: blue;
      position: relative;
      top: 2px;
    }
    #shared_media, #transfers {
      margin-top: 10px;
      padding-top: 5px;
      border-top: 1px solid #99BBFF;
    }
    #transfers table {
      display: none;
      margin-top: 10px;
      width: 100%;
    }
    #shared_media table {
      display: none;
      margin-top: 10px;
      width: 100%;
    }
    #shared_media table td, #transfers table td {
      vertical-align: top;
      white-space: nowrap;
    }
    #shared_media table a, #transfers table a {
      color: blue;
    }
    #shared_media table td:first-child, #transfers table td:first-child { /* author */
      padding-right: 15px;
      text-align: right;
      white-space: normal;
    }
    #shared_media table td:last-child, #transfers table td:last-child { /* timestamp */
      text-align: right;
    }
    #shared_media table td:last-child a, #transfers table td:last-child a { /* timestamp link */
      color: inherit;
    }
    #shared_media table td:last-child a:hover, #transfers table td:last-child a:hover {
      text-decoration: underline;
    }
    #shared_media td:nth-child(2) { /* filename and filesize */
      display: flex;
      justify-content: space-between;
    }
    #shared_media td:nth-child(3) { /* live-link */
      text-align: right;
    }
    #transfers td:nth-child(3) { /* filesize */
      text-align: right;
    }
    #shared_media .filename {
      color: {{ conf.HistoryBackgroundColour }};
    }
    #shared_media .filename, #transfers .filename {
      color: blue;
    }
    #timeline {
      background: white;
      display: none;
      position: fixed;
      top: 0px;
      bottom: 0px;
      left: 0px; /* Fallback if no support for max() */
      left: max(0px, 50% - 425px - 150px);
      width: 140px;
      padding: 5px;
      z-index: 1;
    }
    #timeline h3 {
      color: {{ conf.ExportLinkColour }};
      margin: 0;
      padding: 5px 0;
    }
    #timeline a.toggle {
      position: absolute;
      top: 5px;
      right: 5px;
    }
    #timeline ul {
      height: calc(100% - 28px);
      list-style-type: none;
      margin: 0;
      padding: 1px;
      position: relative;
      overflow-y: auto;
      overflow-x: hidden;
    }
    #timeline ul li {
      font-size: 15px;
      line-height: 25px;
    }
    #timeline ul li a {
      border: 1px solid transparent;
      border-radius: 5px;
      color: black;
      display: block;
      padding: 5px;
    }
    #timeline ul li a:hover {
      border-color: black;
      cursor: pointer;
      text-decoration: underline;
    }
    #timeline ul li .name {
      font-size: 12px;
    }
    #timeline ul li.highlight .name {
      font-weight: bold;
    }
    #timeline ul li.month a {
      padding-left: 10px;
    }
    #timeline ul li.week a {
      font-size:    10px;
      padding-left: 20px;
    }
    #timeline ul li.day,
    #timeline ul li.date a {
      padding-left: 15px;
    }
    #timeline ul li.hour a {
      padding-left: 25px;
    }
    #timeline ul li .count {
      font-size: 9px;
    }
    #timeline ul li.year .date {
      font-size: 18px;
    }
    #timeline ul li .count {
      float: right;
      font-size: 8px;
      opacity: 0.4;
    }
    #timeline ul li.hour .date {
      font-size: 10px;
    }
    #timeline ul li.day .date {
      font-size: 11px;
    }
    div.shared_media.image {
      border-radius: 5px;
      display: inline-block;
      max-width: 305px;
      max-height: 210px;
      position: relative;
      overflow: hidden;
    }
    div.shared_media.image img {
      border-radius: 5px;
      cursor: pointer;
      max-width: 305px;
      max-height: 210px;
    }
    div.shared_media.image .cover {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.1);
      border-radius: 5px;
      pointer-events: none;
    }
    #chat_picture {
%if skypedata.CHATS_TYPE_SINGLE == chat["type"]:
      display: none;
%elif chat_picture_raw:
      margin: 0 10px 0 10px;
      max-width: 125px;
      max-height: 125px;
%endif
%if chat_picture_size:
      width: {{ chat_picture_size[0] }}px;
      height: {{ chat_picture_size[1] }}px;
%endif
    }
    span.gray {
      color: #999;
    }
    .message_content .filename {
      color: {{ conf.ExportLinkColour }};
    }
    body.darkmode {
      background: black;
      color: white;
    }
    body.darkmode #timeline,
    body.darkmode #body_table > tbody > tr > td {
      background: #1E2224;
    }
    body.darkmode #timeline ul li a {
      color: white;
    }
    body.darkmode #header,
    body.darkmode #timeline h3,
    body.darkmode .wordcloud span,
    body.darkmode a, body.darkmode a.visited,
    body.darkmode #transfers .filename,
    body.darkmode .toggle_plusminus,
    body.darkmode #shared_media table td:not(:first-child) a {
      color: #80FF74;
    }
    body.darkmode #stats_data > tbody > tr > td:nth-child(3),
    body.darkmode #emoticons table.emoticon_rows td:nth-child(3) {
      color: #2D928B;
    }
    a#darkmode {
      color: black;
      display: inline-block;
      text-decoration: none;
    }
    body.darkmode a#darkmode {
      color: white;
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
    span.emoticon.{{ e }} {
      background: url("data:image/gif;base64,{{! getattr(emoticons, e).data }}")
                  center center no-repeat;
    }
%endfor
%if any(x["success"] for x in stats["shared_media"].values()):
    {{! templates.LIGHTBOX_CSS }}
%endif
  </style>
  <script>
<%
MESSAGE_TIMELINES = functools.reduce(lambda a, b: ([a.setdefault(m, []).append(timeline.index(b)) for m in b["messages"]], a)[-1], timeline, {})
%>
    var HIGHLIGHT_STYLES = 10;
    var TIMELINES = {{! json.dumps([x["datestr"] for x in timeline]) }};
    var MESSAGE_TIMELINES = {{! json.dumps(collections.OrderedDict(sorted(MESSAGE_TIMELINES.items()))) }}; // {message ID: [timeline index, ]}
    var style_counter = 0;
    var hilite_counter = 0;
    var scroll_highlights = {}; // {message ID: highlight}
    var scroll_timer = null;    // setTimeout ID
    var scroll_timeline = true; // Whether to scroll timeline on scrolling messages
    var scroll_history = [window.scrollY, window.scrollY]; // Last scroll positions

    function toggle_element(id, id_hide) {
      var el = document.getElementById(id);
      el.style.visibility = "visible";
      var displayType = "table" == el.tagName.toLowerCase() ? "table" : "block";
      el.style.display = el.style.display != displayType ? displayType : "none";
      if (el.style.display != "none") {
        var el_hide = document.getElementById(id_hide);
        if (el_hide) {
          el_hide.style.display = "none";
        }
      }
      return false;
    }

    function toggle_darkmode() {
      document.body.classList.toggle("darkmode");
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

    var toggle_plusminus = function(link, id) {
      link.innerHTML = "+–"["+" == link.innerHTML ? 1 : 0];
      toggle_element(id);
      return false;
    };

    /** Attaches scroll observer to message rows. */
    var init_timeline = function() {
      var items = Array.prototype.slice.call(document.querySelectorAll("#timeline ul li"));
      items.forEach(function(x) { x.addEventListener("click", on_click_timeline); });

      var rows = Array.prototype.slice.call(document.querySelectorAll("#content_table tr"));
      rows.forEach(scroll_observer.observe.bind(scroll_observer));
    };

    /** Highlights timeline for messages in view, scrolls to highlights. */
    var highlight_timeline = function() {
      scroll_timer = null;

      var on = {}, off = {}; // {"timeline:xyz": true}
      var msg_ids = Object.keys(scroll_highlights);
      for (var i = 0; i < msg_ids.length; i++) {
        var msg_id = msg_ids[i], into_view = scroll_highlights[msg_id];
        if (!into_view) delete scroll_highlights[msg_id];
        var timeline_idxs = MESSAGE_TIMELINES[msg_id];
        if (!timeline_idxs) continue; // for i
        for (var j = 0; j < timeline_idxs.length; j++) {
          (into_view ? on : off)["timeline:" + encodeURIComponent(TIMELINES[timeline_idxs[j]])] = true;
        };
      };
      Object.keys(on).forEach(function(x) { delete off[x]; });
      var elems_off = Object.keys(off).map(document.getElementById.bind(document)).filter(Boolean),
          elems_on  = Object.keys(on ).map(document.getElementById.bind(document)).filter(Boolean);
      elems_off.forEach(function(x) { x.classList.remove("highlight"); });
      elems_on. forEach(function(x) { x.classList.add   ("highlight"); });
      if (!scroll_timeline || !elems_on.length) return;

      var leafelems_on  = elems_on .filter(function(x) { return !x.classList.contains("root"); });
      var leafelems_off = elems_off.filter(function(x) { return !x.classList.contains("root"); });
      if (!leafelems_on.length) leafelems_on = elems_on;
      if (!leafelems_on.length) return;
      var container = elems_on[0].parentElement,
          viewport  = [container.scrollTop, container.scrollTop + container.clientHeight],
          downward  = scroll_history[1] > scroll_history[0],
          anchor    = leafelems_on[downward ? leafelems_on.length - 1 : 0];
      anchor = (downward ? anchor.nextElementSibling : anchor.previousElementSibling) || anchor;
      if (anchor.classList.contains("root")) {
        var anchor2 = downward ? anchor.nextElementSibling : anchor.previousElementSibling;
        if (anchor2 && !anchor2.classList.contains("root")) anchor = anchor2;
      };
      if (anchor.offsetTop >= viewport[0] && anchor.offsetTop + anchor.offsetHeight <= viewport[1]) return;
      container.scrollTop = Math.max(0, anchor.offsetTop - (downward ? container.clientHeight - anchor.offsetHeight : 0));
    };

    /** Cancels scrolling timeline on ensuring messages-viewport change. */
    var on_click_timeline = function() {
      scroll_timeline = false;
      window.setTimeout(function() { scroll_timeline = true; }, 500);
      return true;
    };

    /** Queues scrolled messages for highlighting timeline. */
    var on_scroll_messages = function(entries) {
      scroll_history = [scroll_history[1], window.scrollY];
      if (scroll_timeline !== false)
        scroll_timeline = ("none" != document.getElementById("timeline").style.display) ? true : null;
      if (scroll_timeline === null) return;

      entries.forEach(function(entry) {
        var msg_id = entry.target.id.replace("message:", "");
        if (msg_id) scroll_highlights[msg_id] = entry.isIntersecting;
      });
      scroll_timer = scroll_timer || window.setTimeout(highlight_timeline, 100);
    };

    if (window.IntersectionObserver) {
      var scroll_options = {"root": document.querySelector("#content_table"), "threshold": [0, 1]};
      var scroll_observer = new IntersectionObserver(on_scroll_messages, scroll_options);
      document.addEventListener("DOMContentLoaded", init_timeline);
    };

%if any(x["success"] for x in stats["shared_media"].values()):
    {{! templates.LIGHTBOX_JS }}
%endif
  </script>
</head>
<body>
<div id="timeline">
<h3>Timeline</h3>
<a title="Click to hide timeline" href="javascript:;" class="toggle" onclick="return toggle_element('timeline')">x</a>
<ul>
%for entry in timeline:
  <li class="{{ entry["unit"] + (" root" if entry["unit"] == timeline_units[0] else "") }}" id="timeline:{{ urllib.parse.quote(entry["datestr"]) }}">
    <a href="#message:{{ entry["messages"][0] }}" title="{{ entry["datestr"] }} : {{ util.plural("message", entry["messages"], sep=",") }}">
%if entry["unit"] in ("month", "day"):
      <span class="date">{{ entry["label"] }}</span> <span class="name">{{ entry["label2"] }}</span>
%elif "date" == entry["unit"]:
      <span class="date name">{{ entry["label"] }}<sup>{{ entry["label2"] }}</sup></span>
%else:
      <span class="date name">{{ entry["label"] }}</span>
%endif
      <span class="count">{{ (entry["count"]) }}</span>
    </a>
  </li>
%endfor
</ul>
</div>
<table id="body_table">
<tr><td>
  <table id="header_table">
  <tr>
    <td id="header_left">
%if skypedata.CHATS_TYPE_SINGLE == chat["type"]:
%for p in filter(lambda p: p["identity"] != db.id, participants):
<%
alt = "%s%s" % (p["name"], (" (%s)" % p["identity"]) if p["name"] != p["identity"] else "")
%>
      <div><span class="avatar_large"><img title="{{ alt }}" alt="{{ alt }}" src="data:image/png;base64,{{! util.b64encode(p.get("avatar_raw_large", "")) or images.AvatarDefaultLarge.data }}" /></span><br /><span class="name" title="{{ p["name"] }}">{{ p["name"] }}</span>
%if p["name"] != p["identity"]:
      <br /><span class="identity" title="{{ p["identity"] }}">{{ p["identity"] }}</span>
%endif
      </div>
%endfor
%elif chat_picture_raw:
<%
try: filetype = imghdr.what("", chat_picture_raw[:100].encode("latin1")) or "png"
except Exception: filetype = "png"
%>
      <img id="chat_picture" title="{{ chat["title"] }}" alt="{{ chat["title"] }}" src="data:image/{{ filetype }};base64,{{! util.b64encode(chat_picture_raw) }}" />
%endif
    </td>
    <td id="header_center">
      <div id="header">{{ chat["title_long"] }}.</div><br />
      Showing {{ util.plural("message", message_count, sep=",") }}
%if date1 and date2:
      from <b>{{ date1 }}</b> to <b>{{ date2 }}</b>.
%else:
.
%endif
<% 
# &#x1F313; first quarter moon symbol
# &#xFE0E;  Unicode variation selector, force preceding character to monochrome text glyph  
%>
<a href="javascript:;" onclick="return toggle_darkmode()" id="darkmode" title="Click to toggle dark/light mode">&#x1F313;&#xFE0E;</a> 
<br />
%if chat["created_datetime"]:
      Chat created on <b>{{ chat["created_datetime"].strftime("%d.%m.%Y") }}</b>,
%else:
      Chat has
%endif
      <b>{{ util.plural("message", chat["message_count"] or 0, sep=",") }}</b> in total.<br />
      Source: <b>{{ db.filename }}</b>.<br /><br />

      <table class="links"><tr>
        <td>
%if skypedata.CHATS_TYPE_SINGLE != chat["type"]:
          <a title="Click to show/hide participants" href="javascript:;" onclick="return toggle_element('participants', 'statistics')">Participants</a>
%endif
        </td><td>
%if timeline:
          <a title="Click to show/hide timeline" href="javascript:;" onclick="return toggle_element('timeline')">Timeline</a>
%endif
        </td><td>
%if stats and (stats["counts"] or stats["info_items"]):
        <a title="Click to show/hide statistics and wordcloud" class="statistics" href="javascript:;" onclick="return toggle_element('statistics', 'participants')">Statistics</a>
%endif
        </td>
      </tr></table>

    </td>
    <td id="header_right">
%if skypedata.CHATS_TYPE_SINGLE == chat["type"]:
%for p in filter(lambda p: p["identity"] == db.id, participants):
<%
alt = "%s%s" % (p["name"], (" (%s)" % p["identity"]) if p["name"] != p["identity"] else "")
%>
      <div><span class="avatar_large"><img title="{{ alt }}" alt="{{ alt }}" src="data:image/png;base64,{{! util.b64encode(p.get("avatar_raw_large", "")) or images.AvatarDefaultLarge.data }}" /></span><br /><span class="name" title="{{ p["name"] }}">{{ p["name"] }}</span>
%if p["name"] != p["identity"]:
      <br /><span class="identity" title="{{ p["identity"] }}">{{ p["identity"] }}</span>
%endif
      </div>
%endfor
%endif
    </td>
  </tr></table>

%if skypedata.CHATS_TYPE_SINGLE != chat["type"]:
  <div id="participants">
<%
filterer = lambda p: not stats["counts"] or p["identity"] == db.id or p["identity"] in stats["counts"]
%>
%for p in filter(filterer, sorted(participants, key=lambda p: p["name"].lower())):
<%
alt = "%s (%s)" % (p["name"], p["identity"])
%>
    <span class="avatar_item"><span class="avatar_large"><img title="{{ alt }}" alt="{{ alt }}" src="data:image/png;base64,{{! util.b64encode(p.get("avatar_raw_large", "")) or images.AvatarDefaultLarge.data }}" /></span><span class="name" title="{{ p["name"] }}">{{ p["name"] }}</span><br />
    <span class="identity" title="{{ p["identity"] }}">
        {{ p["identity"] }}
%if 1 == p.get("rank"):
        <br /><br />chat creator
%endif
    </span></span>
%endfor
  </div>
%endif

  <div id="statistics">
    <table id="stats_data">
      <tr><td>
%for label, value in stats["info_items"]:
      <div>{{ label }}</div>
%endfor
      </td><td colspan="2">
%for label, value in stats["info_items"]:
      <div>{{ value }}</div>
%endfor
      </td><td>
%if stats.get("totalhist", {}).get("hours"):
<%
items = sorted(stats["totalhist"]["hours"].items())
links = dict((i, "#message:%s" % x)
             for i, x in stats["totalhist"]["hours-firsts"].items())
maxkey, maxval = max(items, key=lambda x: x[1])
svgdata = {"data": items, "links": links, "maxval": maxval,
           "colour": conf.PlotHoursColour, "rectsize": conf.PlotHoursUnitSize}
%>
        peak {{ util.plural("message", maxval) }}<br />
{{! step.Template(templates.HISTOGRAM_SVG, strip=False, escape=True).expand(svgdata) }}
        <br />24h activity
%endif
      </td><td>
%if stats.get("totalhist", {}).get("days"):
<%
items = sorted(stats["totalhist"]["days"].items())
links = dict((i, "#message:%s" % x)
             for i, x in stats["totalhist"]["days-firsts"].items())
maxkey, maxval = max(items, key=lambda x: x[1])
interval = items[1][0] - items[0][0]
svgdata = {"data": items, "links": links, "maxval": maxval,
	         "colour": conf.PlotDaysColour, "rectsize": conf.PlotDaysUnitSize}
%>
        peak {{ util.plural("message", maxval) }}<br />
{{! step.Template(templates.HISTOGRAM_SVG, strip=False, escape=True).expand(svgdata) }}
        <br />{{ interval.days }}-day intervals
%endif
      </td></tr>

%if len(stats["counts"]) > 1 and len([x for x in ("messages", "smses", "calls", "transfers", "shares") if stats[x]]) > 1:
      <tr id="stats_header"><td></td><td colspan="4"><div id="sort_header"><b>Sort by:</b>
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
%if stats["shares"]:
        <a title="Sort statistics by media shared" href="#" onClick="return sort_stats(this, 'share');">Shares</a>
%endif
      </div></td>
      </tr>
%endif
%for p in filter(lambda p: p["identity"] in stats["counts"], sorted(participants, key=lambda p: p["name"].lower())):
      <tr class="stats_row">
        <td><table><tr><td class="avatar"><img title="{{ p["name"] }}" alt="{{ p["name"] }}" src="data:image/png;base64,{{! util.b64encode(p.get("avatar_raw_small", "")) or images.AvatarDefault.data }}" /></td><td><span class="name" title="{{ p["name"] }}">{{ p["name"] }}<br /><span class="identity" title="{{ p["identity"] }}">{{ p["identity"] }}</span></span></td></tr></table></td>
        <td><table class="plot_table">
<%
stat_rows = [] # [(type, label, count, total)]
if stats["counts"][p["identity"]]["messages"]:
  stat_rows.append(("messages", "message",   stats["counts"][p["identity"]]["messages"], stats["messages"]))
  stat_rows.append(("messages", "character", stats["counts"][p["identity"]]["chars"],    stats["chars"]))
if stats["counts"][p["identity"]]["smses"]:
  stat_rows.append(("smses", "SMS message",   stats["counts"][p["identity"]]["smses"],    stats["smses"]))
  stat_rows.append(("smses", "SMS character", stats["counts"][p["identity"]]["smschars"], stats["smschars"]))
if stats["counts"][p["identity"]]["calls"]:
  stat_rows.append(("calls", "call", stats["counts"][p["identity"]]["calls"], stats["calls"]))
if stats["counts"][p["identity"]]["calldurations"]:
  stat_rows.append(("calls", "callduration", stats["counts"][p["identity"]]["calldurations"], stats["calldurations"]))
if stats["counts"][p["identity"]]["files"]:
  stat_rows.append(("files", "file", stats["counts"][p["identity"]]["files"], stats["files"]))
  stat_rows.append(("files", "byte", stats["counts"][p["identity"]]["bytes"], stats["bytes"]))
if stats["counts"][p["identity"]]["shares"]:
  stat_rows.append(("shares", "share", stats["counts"][p["identity"]]["shares"],     stats["shares"]))
  stat_rows.append(("shares", "byte",  stats["counts"][p["identity"]]["sharebytes"], stats["sharebytes"]))
%>
%for type, label, count, total in stat_rows:
<%
percent = util.safedivf(count * 100, total)
text_cell1 = "%d%%" % round(percent) if (round(percent) > 25) else ""
text_cell2 = "" if text_cell1 else "%d%%" % round(percent)
if "byte" in label:
  text_total = util.format_bytes(total)
elif "callduration" == label:
  text_total = util.format_seconds(total)
else:
  text_total = util.plural(label, total, sep=",")
%>
          <tr title="{{ util.round_float(percent) }}% of {{ text_total }} in total" class="{{ label }}"><td>
            <table class="plot_row {{ type }}"><tr><td style="width: {{ "%.2f" % percent }}%;">{{ text_cell1 }}</td><td style="width: {{ "%.2f" % (100 - percent) }}%;">{{ text_cell2 }}</td></tr></table>
          </td></tr>
%endfor
        </table></td><td>
%for type, label, count, total in stat_rows:
<%
if "byte" in label:
  text = util.format_bytes(count)
elif "callduration" == label:
  text = util.format_seconds(count, "call")
else:
  text = util.plural(label, count, sep=",")
%>
          <div class="{{ label }}" title="{{ count }}">{{ text }}</div>
%endfor
        </td>
        <td>
%if stats.get("hists", {}).get(p["identity"], {}).get("hours"):
<%
svgdata = {
    "data":     sorted(stats["hists"][p["identity"]]["hours"].items()),
    "links":    dict((i, "#message:%s" % x) for i, x in stats["hists"][p["identity"]]["hours-firsts"].items()),
    "maxval":   max(stats["totalhist"]["hours"].values()),
    "colour":   conf.PlotHoursColour, "rectsize": conf.PlotHoursUnitSize }
%>
{{! step.Template(templates.HISTOGRAM_SVG, strip=False, escape=True).expand(svgdata) }}
%endif
        </td>
        <td>
%if stats.get("hists", {}).get(p["identity"], {}).get("days"):
<%
svgdata = {
    "data":     sorted(stats["hists"][p["identity"]]["days"].items()),
    "links":    dict((i, "#message:%s" % x) for i, x in stats["hists"][p["identity"]]["days-firsts"].items()),
    "maxval":   max(stats["totalhist"]["days"].values()),
    "colour":   conf.PlotDaysColour, "rectsize": conf.PlotDaysUnitSize }
%>
{{! step.Template(templates.HISTOGRAM_SVG, strip=False, escape=True).expand(svgdata) }}
%endif
        </td>
      </tr>
%endfor
    </table>


%if stats["wordcloud"]:
    <div id="wordcloud" class="wordcloud">
<%
sizes = {7: "2.5em;", 6: "2.1em;", 5: "1.75em;", 4: "1.5em;", 3: "1.3em;", 2: "1.1em;", 1: "0.85em", 0: "0.8em;"}
%>
%for word, count, size in stats["wordcloud"]:
<%
countstring = ";\\n".join("%s from %s" % (c, a) for a, c in sorted(stats["wordcounts"][word].items(), key=lambda x: -x[1]))
%>
      <span style="font-size: {{ sizes[size] }}"><a title="Highlight '{{ word }}' and go to first occurrence" href="#" onClick="return hilite(this);">{{ word }}</a> <span title="{{ countstring }}">({{ count }})</span></span> 
%endfor
    </div>

%if stats.get("wordclouds"):
<%
sizes = {7: "2.5em;", 6: "2.1em;", 5: "1.75em;", 4: "1.5em;", 3: "1.3em;", 2: "1.1em;", 1: "0.85em", 0: "0.8em;"}
globalcounts = dict((w, sum(vv.values())) for w, vv in stats["wordcounts"].items())
%>
    <br /><br />
    <b>Word cloud for individuals</b>&nbsp;&nbsp;[<a title="Click to show/hide word clouds for individuals" href="#" onClick="return toggle_plusminus(this, 'wordclouds');" class="toggle_plusminus">+</a>]
    <div id="wordclouds">
      <table>
%for p in filter(lambda p: p["identity"] in stats["counts"], sorted(participants, key=lambda p: p["name"].lower())):
      <tr><td>
        <table><tr><td class="avatar"><img title="{{ p["name"] }}" alt="{{ p["name"] }}" src="data:image/png;base64,{{! util.b64encode(p.get("avatar_raw_small", "")) or images.AvatarDefault.data }}" /></td><td><span>{{ p["name"] }}<br /><span class="identity">{{ p["identity"] }}</span></span></td></tr></table>
      </td><td>
        <div class="wordcloud">
%if stats["wordclouds"].get(p["identity"]):
%for word, count, size in stats["wordclouds"][p["identity"]]:
          <span style="font-size: {{ sizes[size] }}"><a title="Highlight '{{ word }}' and go to first occurrence" href="#" onClick="return hilite(this);">{{ word }}</a> <span title="{{ "%d%% of total usage" % round(100. * count / globalcounts.get(word, count)) }}">({{ count }})</span></span> 
%endfor
%else:
          <span class="gray">Not enough words.</span>
%endif
        </div>
      </td></tr>
%endfor
      </table>
    </div>
%endif
%endif


%if stats["emoticons"]:
    <br /><br />
    <b>Emoticon statistics</b>&nbsp;&nbsp;[<a title="Click to show/hide emoticon statistics" href="#" onClick="return toggle_plusminus(this, 'emoticons');" class="toggle_plusminus">+</a>]
    <table id="emoticons">
<%
emoticon_counts = {"": dict((x, sum(vv.values())) for x, vv in stats["emoticons"].items())}
for emoticon, counts in stats["emoticons"].items():
    for author, count in counts.items():
        emoticon_counts.setdefault(author, {})[emoticon] = count
total = sum(emoticon_counts[""].values())
authors = [("", {})] + sorted([(p["identity"], p) for p in participants if p["identity"] in stats["counts"]], key=lambda x: x[1]["name"].lower())
%>
%for identity, participant in authors:
<%
name = participant.get("name", "TOTAL")
smalltotal = sum(emoticon_counts.get(identity, {}).values())
%>
      <tr>
%if participant:
        <td><table><tr><td class="avatar">
        <img title="{{ name }}" alt="{{ name }}" src="data:image/png;base64,{{! util.b64encode(participant.get("avatar_raw_small", "")) or images.AvatarDefault.data }}" />
        </td><td><span>{{ name }}<br /><span class="identity">{{ identity }}</span></span></td></tr></table></td>
%else:
        <td style="padding: 13px;">{{ name }}</td>
%endif
        <td class="total" title="{{ "%s%% of %s in total" % (util.round_float(100. * smalltotal / total), total) if participant and smalltotal else "" }}">{{ smalltotal or "" }}</td><td>
%if identity in emoticon_counts:
        <td><table class="emoticon_rows">
%endif
%for emoticon, count in sorted(emoticon_counts.get(identity, {}).items(), key=lambda x: (-x[1], x[0])):
<%
if emoticon in emoticons.EmoticonData:
    title, text = emoticons.EmoticonData[emoticon]["title"], emoticons.EmoticonData[emoticon]["strings"][0]
    if text != title:
        title += " " + text
else:
    text, title = emoticon, "%s (%s)" % (emoticon.capitalize(), emoticon)
percent = 100. * count / total
text_cell1 = "%d%%" % round(percent) if (round(percent) > 14) else ""
text_cell2 = "" if text_cell1 else "%d%%" % round(percent)
subtitle = "%s%% of %s in personal total" % (util.round_float(100. * count / smalltotal), smalltotal) if participant else "%s%% of %s in total" % (util.round_float(percent), total)
%>
        <tr title="{{ util.round_float(percent) }}% of {{ total }} in total">
          <td><span class="emoticon {{ emoticon }}" title="{{ title }}">{{ text }}</span></td>
          <td><table class="plot_row messages" style="width: {{ conf.EmoticonsPlotWidth }}px;"><tr><td style="width: {{ "%.2f" % percent }}%;">{{ text_cell1 }}</td><td style="width: {{ "%.2f" % (100 - percent) }}%;">{{ text_cell2 }}</td></tr></table></td>
          <td title="{{ subtitle }}">{{ count }}</td><td title="{{ subtitle }}">{{ title }}</td>
        </tr>
%endfor
%if identity in emoticon_counts:
        </table>
%else:
        <td style="padding-top: 13px;"><span class="gray">No emoticons.</span>
%endif
      </td></tr>
%endfor
</table>
%endif


%if stats["shared_media"]:
    <div id="shared_media">

    <b>Shared media</b>&nbsp;&nbsp;[<a title="Click to show/hide shared media links" href="#" onClick="return toggle_plusminus(this, 'shared_media_table');" class="toggle_plusminus">+</a>]
    <table id="shared_media_table">
%for message_id, data in sorted(stats["shared_media"].items(), key=lambda x: x[1]["datetime"]):
      <tr>
        <td class="{{ "remote" if data["author"] != db.id else "local" }}" title="{{ data["author"] }}">{{ data["author_name"] }}</td>
        <td>
          <span class="filename">{{ data.get("filename") or "" }}</span>
%if data.get("filesize") is not None:
          <span class="filesize" title="{{ util.plural("byte", data["filesize"], sep=",") }}">{{ util.format_bytes(data["filesize"]) }}</span>
%endif
        </td>
        <td>
%if data.get("url"):
            <a href="{{ data["url"] }}" target="_blank">Online</a>
%endif
        </td>
        <td class="timestamp" title="{{ data["datetime"].strftime("%Y-%m-%d %H:%M:%S") }}"><a href="#message:{{ message_id }}">{{ data["datetime"].strftime("%Y-%m-%d %H:%M") }}</a></td>
      </tr>
%endfor
    </table>
    </div>
%endif


%if stats["transfers"]:
    <div id="transfers">
      <b>Sent and received files</b>&nbsp;&nbsp;[<a title="Click to show/hide file transfers" href="#" onClick="return toggle_plusminus(this, 'transfers_table');" class="toggle_plusminus">+</a>]
      <table id="transfers_table">
%for f in stats["transfers"]:
<%
from_remote = (f["partner_handle"] == db.id and skypedata.TRANSFER_TYPE_INBOUND == f["type"]) or \
              (f["partner_handle"] != db.id and skypedata.TRANSFER_TYPE_OUTBOUND == f["type"])
partner = f["partner_dispname"] or db.get_contact_name(f["partner_handle"])
dt = db.stamp_to_date(f["starttime"]) if f.get("starttime") else None
f_datetime = dt.strftime("%Y-%m-%d %H:%M") if dt else ""
f_datetime_title = dt.strftime("%Y-%m-%d %H:%M:%S") if dt else ""
%>
        <tr><td class="{{ "remote" if from_remote else "local" }}" title="{{ f["partner_handle"] if from_remote else db.username }}">{{ partner if from_remote else db.account["name"] }}</td><td>
%if f["filepath"]:
          <a href="{{ util.path_to_url(f["filepath"]) }}" target="_blank" class="filename">{{ f["filepath"] }}</a>
%else:
          <span class="filename">{{ f["filename"] }}</span>
%endif
        </td><td title="{{ util.plural("byte", int(f["filesize"]), sep=",") }}">
          {{ util.format_bytes(int(f["filesize"])) }}
        </td><td class="timestamp" title="{{ f_datetime_title }}">
          <a href="#message:{{ f["__message_id"] }}">{{ f_datetime }}</a>
        </td></tr>
%endfor
      </table>
    </div>
%endif


  </div>
</td></tr>
<tr><td>
  <table id="content_table">
<%
for chunk in message_buffer:
    echo(chunk)
%>
  </table>
</td></tr></table>
<div id="footer">Exported with {{ conf.Title }} on {{ datetime.datetime.now().strftime("%d.%m.%Y %H:%M") }}.</div>
%if any(x["success"] for x in stats["shared_media"].values()):
<script> new Lightbox().load({carousel: false}); </script>
%endif
</body>
</html>
"""


"""
HTML chat history export template for the messages part.

@param   db              SkypeDatabase instance
@param   chat            chat data dictionary
@param   messages        message iterator
@param   parser          MessageParser instance
@param   ?media_folder   path to save images under, if not embedding
"""
CHAT_MESSAGES_HTML = """<%
from skyperious import skypedata
from skyperious.lib import util

output = {"format": "html", "export": True}
if isdef("media_folder") and media_folder: output["media_folder"] = media_folder
previous_day, previous_author = None, None
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
    <td class="day t3" title="{{ day.strftime("%Y-%m-%d") }}"></td>
    <td class="day" colspan="2" title="{{ day.strftime("%Y-%m-%d") }}"><span class="weekday">{{ weekday }}</span>, {{ weekdate }}</td>
  </tr>
%endif
<%
content = parser.parse(m, output=output)
from_name = db.get_author_name(m) if previous_author != m["author"] else ""
# Info messages like "/me is thirsty" -> author on same line.
is_info = (skypedata.MESSAGE_TYPE_INFO == m["type"])
# Kludge to get single-line messages with an emoticon to line up correctly
# with the author, as emoticons have an upper margin pushing the row higher
text_plain = m.get("body_txt", content)
emot_start = ' class="emoticon '
shift_row = emot_start in content and (("<br />" not in content and len(text_plain) < 140) or content.index(emot_start) < 140)
author_class = "remote" if m["author"] != db.id else "local"
%>
  <tr id="message:{{ m["id"] }}"{{! ' class="shifted"' if shift_row else "" }}>
    <td class="author {{ author_class }}" colspan="2" title="{{ m["author"] }}">{{ from_name if not is_info else "" }}</td>
    <td class="t3"></td>
    <td class="message_content"><div>
%if is_info:
    <span class="{{ author_class }}">{{ db.get_author_name(m) }}</span>
%endif
      {{! content }}
    </div></td>
    <td class="timestamp" title="{{ m["datetime"].strftime("%Y-%m-%d %H:%M:%S") }}">
%if m["edited_timestamp"]:
      {{ m["datetime"].strftime("%H:%M") }}<span class="{{ "edited" if m["body_xml"] else "removed" }}" title="{{ "Edited" if m["body_xml"] else "Removed" }} {{ db.stamp_to_date(m["edited_timestamp"]).strftime("%H:%M:%S") }}">&nbsp;&nbsp;&nbsp;</span>
%else:
      {{ m["datetime"].strftime("%H:%M") }}
%endif
    </td>
  </tr>
<%
previous_day = m["datetime"].date()
previous_author = m["author"]
%>
%endfor
"""


"""
HTML chat history export template for shared media message body.

@param   content         raw file binary
@param   author          author skypename
@param   author_name     author display name
@param   datetime        message datetime
@param   url             file URL in Skype online
@param   message         message data dict
@param   ?category       media category like "video", defaults to "image"
@param   ?filename       media filename, if any
@param   ?media_folder   path to save files under, if not embedding
"""
CHAT_MESSAGE_MEDIA = """<%
import imghdr, logging, mimetypes, os
from six.moves import urllib
from skyperious import conf, skypedata
from skyperious.lib import util

category = category if isdef("category") else None
filename = filename if isdef("filename") else None
if category not in ("audio", "video"): category = "image"
src, mimetype, filetype = url, None, None
if filename:
    filetype = os.path.splitext(filename)[-1][1:]
if category in ("audio", "video"):
    mimetype = mimetypes.guess_type(filename or "")[0]
else:
    filetype = imghdr.what("", content) or filetype or "image"
if filename and filetype and not os.path.splitext(filename)[-1]:
    filename = "%s.%s" % (filename, filetype)
filetype = filetype or category
mimetype = mimetype or "%s/%s" % (category, escape(filetype))

caption = "From %s at <a href='#message:%s'>%s</a>." % tuple(map(escape, [author_name, message["id"], datetime.strftime("%Y-%m-%d %H:%M")]))
title = "Click to %s." % ("enlarge" if "image" == category else "play")
if filename:
    caption, title = ("%s: %s." % (x[:-1], filename) for x in (caption, title))
if isdef("media_folder") and media_folder:
    basename = filename or "%s.%s" % (message["id"], filetype)
    basename = util.safe_filename(basename)
    filepath = util.unique_path(os.path.join(media_folder, basename))
    src = "%s/%s" % tuple(urllib.parse.quote(os.path.basename(x)) for x in (media_folder, filepath))
    try:
        with util.create_file(filepath, "wb", handle=True) as f: f.write(content)
    except Exception:
        logger = logging.getLogger(conf.Title.lower())
        logger.exception("Error saving export image %s.", filepath)
else:
    src = "data:%s;base64,%s" % (mimetype, util.b64encode(content))
%>
%if skypedata.CHATMSG_TYPE_PICTURE == message["chatmsg_type"]:
  Changed the conversation picture:<br />
%endif
<div class="shared_media {{ category }}">
%if "audio" == category:
  <audio {{ 'data-name="%s" ' % filename if filename else '' }} title="{{ title }}" src="{{ src }}" controls>
    To hear this voice message, go to:
    <a href="{{ url }}" target="_blank">{{ url }}</a>.
  </audio>
%elif "video" == category:
  <video {{ 'data-name="%s" ' % filename if filename else '' }}width="240" title="{{ title }}" src="{{ src }}" controls>
    To view this video message, go to:
    <a href="{{ url }}" target="_blank">{{ url }}</a>.
  </video>
%else:
<%
size, MAXW, MAXH = None, 305, 210
try:
    w, h = size = util.img_size(content)
    if w > MAXW or h > MAXH:
        ratio = min(util.safedivf(min(MAXW, w), w), util.safedivf(min(MAXH, h), h))
        size = w * ratio, h * ratio
except Exception: pass
%>
    %if isdef("media_folder") and media_folder:
  <a href="{{ src }}" target="_blank" onclick="return false">
    %endif
  <img src="{{ src }}" title="{{ title }}" alt="{{ title }}" data-jslghtbx data-jslghtbx-group="shared_media" data-jslghtbx-caption="{{ caption }}" />
  <div class="cover"{{ ' style="width: %spx; height: %spx;"' % size if size else '' }}></div>
    %if isdef("media_folder") and media_folder:
  </a>
    %endif
%endif
</div>
"""



"""
HTML chat history export template for shared files message body.

@param   files         [{filename, filepath, fileurl, content}]
@param   media_folder  path to save files under
"""
CHAT_MESSAGE_FILE = """<%
import logging, os
from six.moves import urllib
from skyperious import conf
from skyperious.lib import util

punct = lambda i: "." if i == len(files) - 1 else ","
%>
Sent {{ util.plural("file", files, numbers=False) }}
%for i, file in enumerate(files):
<%
if file["content"]:
    basename = util.safe_filename(file["filename"])
    filepath = util.unique_path(os.path.join(media_folder, basename))
    src = "%s/%s" % tuple(urllib.parse.quote(os.path.basename(x)) for x in (media_folder, filepath))
    try:
        with util.create_file(filepath, "wb", handle=True) as f:
            f.write(file["content"])
    except Exception:
        src = None
        logger = logging.getLogger(conf.Title.lower())
        logger.exception("Error saving export file %s.", filepath)
else:
    src = util.path_to_url(file["filepath"]) if file["filepath"] else None
%>
%if src:
  <a href="{{ src }}" target="_blank">{{ file["filename"] }}</a>{{ punct(i) }}
%else:
  <span class="filename">{{ file["filename"] }}</span>{{ punct(i) }}
%endif
%endfor
"""



"""
TXT chat history export template.

@param   chat               chat data dictionary
@param   date1              first message datetime
@param   date2              last message datetime
@param   db                 SkypeDatabase instance
@param   message_buffer     buffer-like object to yield messages content
@param   message_count      total message count
"""
CHAT_TXT = """<%
import datetime
from skyperious import conf, skypedata
from skyperious.lib import util

%>History of Skype {{ chat["title_long_lc"] }}.
Showing {{ util.plural("message", message_count, sep=",") }}{{ " from %s to %s" % (date1, date2) if (date1 and date2) else "" }}.
Chat {{ "created on %s, " % chat["created_datetime"].strftime("%d.%m.%Y") if chat["created_datetime"] else "" }}{{ util.plural("message", chat["message_count"] or 0, sep=",") }} in total.
Source: {{ db.filename }}.
Exported with {{ conf.Title }} on {{ datetime.datetime.now().strftime("%d.%m.%Y %H:%M") }}.
-------------------------------------------------------------------------------

<%
for chunk in message_buffer:
    echo(chunk)
%>
"""


"""
TXT chat history export template for the messages part.

@param   db                 SkypeDatabase instance
@param   messages           iterator yielding messages
@param   parser             MessageParser instance
"""
CHAT_MESSAGES_TXT = """<%
from skyperious import skypedata
from skyperious.lib import util

previous_day = None
%>
%for m in messages:
%if m["datetime"].date() != previous_day:
<%
# Day has changed: insert a date header
day = m["datetime"].date()
weekday, weekdate = util.get_locale_day_date(day)
previous_day = m["datetime"].date()
%>

{{ weekday }}, {{ weekdate }}
----------------------------------------

%endif
%if skypedata.MESSAGE_TYPE_INFO == m["type"]:
{{ m["datetime"].strftime("%H:%M") }}
{{ db.get_author_name(m) }} {{ parser.parse(m, output={"format": "text", "wrap": True}) }}
%else:
{{ m["datetime"].strftime("%H:%M") }} {{ db.get_author_name(m) }}:
{{ parser.parse(m, output={"format": "text", "wrap": True}) }}
%endif

%endfor
"""


"""
HTML data grid export template.

@param   db            SkypeDatabase instance
@param   title         export title
@param   columns       [name, ]
@param   row_count     total number of rows
@param   rows          iterator yielding rows
@param   sql           SQL query, if any
"""
GRID_HTML = """<%
import datetime
from skyperious import conf, images
from skyperious.lib import util

%><!DOCTYPE HTML><html lang="">
<head>
    <meta http-equiv='Content-Type' content='text/html;charset=utf-8' />
    <meta name="generator" content="{{ conf.Title }} {{ conf.Version }}" />
    <title>{{ title }}</title>
    <link rel="shortcut icon" type="image/png" href="data:image/png;base64,{{! images.Icon16x16_8bit.data }}"/>
    <style>
        * { font-family: {{ conf.HistoryFontName }}; font-size: 11px; }
        body {
            background: {{ conf.HistoryBackgroundColour }};
            color: black;
            margin: 0px 10px 0px 10px;
        }
        .header { font-size: 1.1em; font-weight: bold; color: {{ conf.ExportLinkColour }}; }
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
            font-family: {{ conf.HistoryFontName }};
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
        a, a.visited { color: {{ conf.ExportLinkColour }}; text-decoration: none; }
        a:hover, a.visited:hover { text-decoration: underline; }
        .footer {
          text-align: center;
          padding-bottom: 10px;
          color: #666;
        }
        .header { font-size: 1.1em; font-weight: bold; color: {{ conf.ExportLinkColour }}; }
        td { text-align: left; vertical-align: top; }
        body.darkmode {
          background: black;
          color: white;
        }
        body.darkmode .header {
          color: #80FF74;
        }
        body.darkmode table.body_table > tbody > tr > td {
          background: #1E2224;
        }
        a#darkmode {
          color: black;
          display: inline-block;
          text-decoration: none;
        }
        body.darkmode a#darkmode {
          color: white;
        }
    </style>
    <script>
      function toggle_darkmode() {
        document.body.classList.toggle("darkmode");
        return false;
      };
    </script>
</head>
<body>
<table class="body_table">
<tr><td><table class="header_table">
    <tr>
        <td class="header_left"></td>
        <td>
            <div class="header">{{ title }}</div><br />
            Source: <b>{{ db.filename }}</b>.<br />
            <b>{{ row_count }}</b> {{ util.plural("row", row_count, numbers=False, sep=",") }} in results.
<% 
# &#x1F313; first quarter moon symbol
# &#xFE0E;  Unicode variation selector, force preceding character to monochrome text glyph  
%>
            <a href="javascript:;" onclick="return toggle_darkmode()" id="darkmode" title="Click to toggle dark/light mode">&#x1F313;&#xFE0E;</a> 
            <br />
%if sql:
            <b>SQL:</b> {{ sql }}
%endif
        </td>
    </tr></table>
</td></tr><tr><td><table class="content_table">
<tr><th>#</th>
%for col in columns:
<th>{{ col }}</th>
%endfor
</tr>
%for i, row in enumerate(rows):
<tr>
<td>{{ i + 1 }}</td>
%for col in columns:
<td>{{ "" if row[col] is None else row[col] }}</td>
%endfor
</tr>
%endfor
</table>
</td></tr></table>
<div class="footer">Exported with {{ conf.Title }} on {{ datetime.datetime.now().strftime("%d.%m.%Y %H:%M") }}.</div>
</body>
</html>
"""


"""
TXT SQL insert statements export template.

@param   db            SkypeDatabase instance
@param   title         export title
@param   columns       [name, ]
@param   rows          iterator yielding rows
@param   sql           SQL query, if any
@param   table         table name, if any
@param   ?create_sql   CREATE TABLE SQL, if any
"""
SQL_TXT = """<%
import datetime
from skyperious import conf
from skyperious.lib import util

str_cols = ", ".join(columns)
%>-- {{ title }}.
-- Source: {{ db.filename }}.
-- Exported with {{ conf.Title }} on {{ datetime.datetime.now().strftime("%d.%m.%Y %H:%M") }}.
%if sql:
-- SQL: {{ sql }}
%endif
%if table:
{{ create_sql }}
%endif

%for row in rows:
INSERT INTO {{ table }} ({{ str_cols }}) VALUES ({{ ", ".join(util.format_sql_value(row[col]) for col in columns) }});
%endfor
"""



"""
HTML statistics template, for use with HtmlWindow.

@param   db               SkypeDatabase instance
@param   participants     [{contact data}, ]
@param   chat             chat data dictionary
@param   sort_by          the field stats are currently sorted by
@param   stats            SkypeDatabase.get_collected_stats()
@param   images           {histogram type: memoryfs filename}
@param   authorimages     {identity: {image type: memoryfs filename}}
@param   imagemaps        {histogram type: [(rect, href)]}
@param   authorimagemaps  {identity: {histogram type: [(rect, href)]}}
@param   expand           {clouds: bool, emoticons, shared_media}
"""
STATS_HTML = """<%
from six.moves import urllib
from skyperious import conf, emoticons, skypedata
from skyperious.lib import util

%>
<font color="{{ conf.FgColour }}" face="{{ conf.HistoryFontName }}" size="3">
<table cellpadding="0" cellspacing="0" width="100%"><tr>
  <td><a name="top"><b>Statistics for currently shown messages in {{ chat["title_long_lc"] }}:</b></a></td>
%if stats.get("wordcloud"):
  <td align="right" valign="top" nowrap=""><a href="#cloud"><font color="{{ conf.LinkColour }}">Jump to word cloud</font></a></td>
%endif
</tr></table>
<font size="0">&nbsp;</font><br />
<font size="2">
<table cellpadding="2" cellspacing="2" width="100%">
%for i, (label, value) in enumerate(stats["info_items"]):
  <tr>
    <td width="150" valign="top">{{ label }}:</td><td valign="top">{{ value }}</td>
%if not i:
    <td rowspan="{{ len(stats["info_items"]) }}" valign="bottom">
%if "hours" in images:
<%
items = sorted(stats["totalhist"]["hours"].items())
maxkey, maxval = max(items, key=lambda x: x[1])
%>
      <font color="{{ conf.PlotHoursColour }}">
      peak {{ util.plural("message", maxval) }}<br />
      <img src="memory:{{ images["hours"] }}" usemap="#hours-histogram"/><br />
      24h actitity</font>
      <map name="hours-histogram">
%for (x1, y1, x2, y2), link in imagemaps["hours"]:
        <area shape="rect" coords="{{ x1 }},{{ y1 }},{{ x2 }},{{ y2 }}" href="{{ link }}">
%endfor
      </map>
%endif
    </td>
    <td rowspan="{{ len(stats["info_items"]) }}" valign="bottom">
%if "days" in images:
<%
items = sorted(stats["totalhist"]["days"].items())
maxkey, maxval = max(items, key=lambda x: x[1])
interval = items[1][0] - items[0][0]
%>
      <font color="{{ conf.PlotDaysColour }}">
      peak {{ util.plural("message", maxval) }}<br />
      <img src="memory:{{ images["days"] }}" usemap="#days-histogram" /><br />
      {{ interval.days }}-day intervals</font>
      <map name="days-histogram">
%for (x1, y1, x2, y2), link in imagemaps["days"]:
        <area shape="rect" coords="{{ x1 }},{{ y1 }},{{ x2 }},{{ y2 }}" href="{{ link }}">
%endfor
      </map>
%endif
    </td>
%endif
  </tr>
%endfor

%if len(stats["counts"]) > 1 and len([x for x in ("messages", "smses", "calls", "transfers", "shares") if stats[x]]) > 1:
  <tr><td><br /><br /></td><td colspan="3" valign="bottom">
    <b>Sort by:&nbsp;&nbsp;&nbsp;</b>
%for name, label in [("name", "Name"), ("messages", "Messages"), ("chars", "Characters"), ("smses", "SMS messages"), ("smschars", "SMS characters"), ("calls", "Calls"), ("calldurations", "Call duration"), ("files", "Files"), ("shares", "Shares")]:
%if "name" == name or stats[name]:
%if sort_by == name:
      <span><font color="gray">{{ label }}</font>&nbsp;&nbsp;&nbsp;&nbsp;</span>
%else:
      <span><a href="sort://{{ name }}"><font color="{{ conf.LinkColour }}">{{ label }}</font></a>&nbsp;&nbsp;&nbsp;&nbsp;</span>
%endif
%endif
%endfor
  </td></tr>
%endif

<%
colormap = {"messages": conf.PlotMessagesColour, "smses": conf.PlotSMSesColour, "calls": conf.PlotCallsColour, "files": conf.PlotFilesColour, "shares": conf.PlotSharesColour}
sort_key = lambda p: -stats["counts"][p["identity"]].get(sort_by, 0) if "name" != sort_by else p["name"].lower()
participants_sorted = sorted(filter(lambda p: p["identity"] in stats["counts"], participants), key=sort_key)
%>

%for p in participants_sorted:
<%
stat_rows = [] # [(type, label, count, total)]
if stats["counts"][p["identity"]]["messages"]:
  stat_rows.append(("messages", "message",   stats["counts"][p["identity"]]["messages"], stats["messages"]))
  stat_rows.append(("messages", "character", stats["counts"][p["identity"]]["chars"],    stats["chars"]))
if stats["counts"][p["identity"]]["smses"]:
  stat_rows.append(("smses", "SMS message",   stats["counts"][p["identity"]]["smses"],    stats["smses"]))
  stat_rows.append(("smses", "SMS character", stats["counts"][p["identity"]]["smschars"], stats["smschars"]))
if stats["counts"][p["identity"]]["calls"]:
  stat_rows.append(("calls", "call", stats["counts"][p["identity"]]["calls"], stats["calls"]))
if stats["counts"][p["identity"]]["calldurations"]:
  stat_rows.append(("calls", "callduration", stats["counts"][p["identity"]]["calldurations"], stats["calldurations"]))
if stats["counts"][p["identity"]]["files"]:
  stat_rows.append(("files", "file", stats["counts"][p["identity"]]["files"], stats["files"]))
  stat_rows.append(("files", "byte", stats["counts"][p["identity"]]["bytes"], stats["bytes"]))
if stats["counts"][p["identity"]]["shares"]:
  stat_rows.append(("shares", "share", stats["counts"][p["identity"]]["shares"],     stats["shares"]))
  stat_rows.append(("shares", "byte",  stats["counts"][p["identity"]]["sharebytes"], stats["sharebytes"]))
%>
  <tr>
    <td valign="top">
      <table cellpadding="0" cellspacing="0"><tr>
        <td valign="top"><img src="memory:{{ authorimages[p["identity"]]["avatar"] }}"/>&nbsp;&nbsp;</td>
        <td valign="center">{{ p["name"] }}<br /><font size="2" color="gray">{{ p["identity"] }}</font></td>
      </tr></table>
    </td><td valign="top">
%for type, label, count, total in stat_rows:
<%
ratio = util.safedivf(count, total)
percent = int(round(100 * ratio))
text_cell1 = "&nbsp;%d%%&nbsp;" % round(percent) if (round(percent) > 30) else ""
text_cell2 = "" if text_cell1 else "&nbsp;%d%%&nbsp;" % percent
if "byte" == label:
  text_cell3 = util.format_bytes(count)
elif "callduration" == label:
  text_cell3 = util.format_seconds(count, "call")
else:
  text_cell3 = util.plural(label, count, sep=",")
%>
      <table cellpadding="0" cellspacing="0" width="100%"><tr>
        <td bgcolor="{{ colormap[type] }}" width="{{ int(round(ratio * conf.StatisticsPlotWidth)) }}" align="center">
%if text_cell1:
          <font color="#FFFFFF" size="2"><b>{{! text_cell1 }}</b></font>
%endif
        </td>
        <td bgcolor="{{ conf.PlotBgColour }}" width="{{ int(round((1 - ratio) * conf.StatisticsPlotWidth)) }}" align="center">
%if text_cell2:
          <font color="{{ conf.PlotMessagesColour }}" size="2"><b>{{! text_cell2 }}</b></font>
%endif
        </td>
        <td nowrap="">&nbsp;{{! text_cell3 }}</td>
      </tr></table>
%endfor
    </td>
    <td valign="top">
<%
safe_id = urllib.parse.quote(p["identity"])
%>
%if "hours" in authorimages.get(p["identity"] , {}):
      <img src="memory:{{ authorimages[p["identity"]]["hours"] }}" usemap="#{{ safe_id }}-hours" />
      <map name="{{ safe_id }}-hours">
%for (x1, y1, x2, y2), link in authorimagemaps[p["identity"]]["hours"]:
        <area shape="rect" coords="{{ x1 }},{{ y1 }},{{ x2 }},{{ y2 }}" href="{{ link }}">
%endfor
      </map>
%endif
    </td>
    <td valign="top">
%if "days" in authorimages.get(p["identity"] , {}):
      <img src="memory:{{ authorimages[p["identity"]]["days"] }}" usemap="#{{ safe_id }}-days" />
      <map name="{{ safe_id }}-days">
%for (x1, y1, x2, y2), link in authorimagemaps[p["identity"]]["days"]:
        <area shape="rect" coords="{{ x1 }},{{ y1 }},{{ x2 }},{{ y2 }}" href="{{ link }}">
%endfor
      </map>
%endif
    </td>
  </tr>
%endfor
  
</table>
</font>

%if stats.get("wordcloud"):
<br /><hr />
<table cellpadding="0" cellspacing="0" width="100%"><tr>
  <td><a name="cloud"><b>Word cloud for currently shown messages:</b></a></td>
  <td align="right"><a href="#top"><font color="{{ conf.LinkColour }}">Back to top</font></a></td>
</tr></table>
<br /><br />
%for word, count, size in stats["wordcloud"]:
<font color="{{ conf.LinkColour }}" size="{{ size }}"><a href="{{ word }}"><font color="{{ conf.LinkColour }}">{{ word }}</font></a> ({{ count }}) </font>
%endfor
%endif

%if stats.get("wordclouds"):
<br /><br />
<b>Word cloud for individuals</b> [<a href="expand://clouds"><font color="{{ conf.LinkColour }}" size="4">{{! ("+", "&ndash;")[expand["clouds"]] }}</font></a>]
%if expand["clouds"]:
<br /><br />
<table cellpadding="0" cellspacing="0" width="100%">
%for p in participants_sorted:
  <tr><td valign="top" width="150">
    <table cellpadding="0" cellspacing="0"><tr>
      <td valign="top"><img src="memory:{{ authorimages[p["identity"]]["avatar"] }}"/>&nbsp;&nbsp;</td>
      <td valign="center"><font size="2">{{ p["name"] }}<br /><font color="gray">{{ p["identity"] }}</font></font></td>
      <td width="10"></td>
    </tr></table>
  </td><td valign="top">
%if stats["wordclouds"].get(p["identity"]):
%for word, count, size in stats["wordclouds"][p["identity"]]:
    <font color="{{ conf.LinkColour }}" size="{{ size }}"><a href="{{ word }}"><font color="{{ conf.LinkColour }}">{{ word }}</font></a> ({{ count }}) </font>
%endfor
%else:
    <font color="gray" size="2">Not enough words.</font>
%endif
  </td></tr>
  <tr><td colspan="2"><hr /></td></tr>
%endfor
</table>
%endif
%endif

%if stats.get("emoticons"):
<br /><br />
<b>Emoticons statistics</b> [<a href="expand://emoticons"><font color="{{ conf.LinkColour }}" size="4">{{! ("+", "&ndash;")[expand["emoticons"]] }}</font></a>]
%if expand["emoticons"]:
<%
emoticon_counts = {"": dict((x, sum(vv.values())) for x, vv in stats["emoticons"].items())}
for emoticon, counts in stats["emoticons"].items():
    for author, count in counts.items():
        emoticon_counts.setdefault(author, {})[emoticon] = count
total = sum(emoticon_counts[""].values())
authors = [("", {})] + [(p["identity"], p) for p in participants_sorted]
%>
<br /><br />
<table cellpadding="0" cellspacing="2" width="100%">
%for identity, participant in authors:
<%
name = participant.get("name", "TOTAL")
smalltotal = sum(emoticon_counts.get(identity, {}).values())
%>
%if participant:
  <tr><td valign="top" width="150">
    <table cellpadding="0" cellspacing="0"><tr>
      <td valign="top"><img src="memory:{{ authorimages[participant["identity"]]["avatar"] }}"/>&nbsp;&nbsp;</td>
      <td valign="center"><font size="2">{{ participant["name"] }}<br /><font color="gray">{{ participant["identity"] }}</font></font></td>
      <td width="10"></td>
    </tr></table>
  </td><td valign="top" align="right">
%else:
  <tr><td valign="top" width="150"><table cellpadding="3" cellspacing="0"><tr><td><font size="2">{{ name }}</font></td></tr></table></td><td valign="top" align="right">
%endif
    <table cellpadding="0" cellspacing="3"><tr><td align="right"><font size="2">{{ smalltotal or "" }}</font></td></tr></table></td><td valign="top">
%if identity in emoticon_counts:
    <table cellpadding="0" cellspacing="2">
%endif
%for emoticon, count in sorted(emoticon_counts.get(identity, {}).items(), key=lambda x: (-x[1], x[0])):
<%
if emoticon in emoticons.EmoticonData:
    title, text = emoticons.EmoticonData[emoticon]["title"], emoticons.EmoticonData[emoticon]["strings"][0]
    if text != title:
        title += " " + text
else:
    text, title = emoticon, "%s (%s)" % (emoticon.capitalize(), emoticon)
ratio = util.safedivf(count, total)
percent = 100. * ratio
text_cell1 = "&nbsp;%d%%&nbsp;" % round(percent) if (round(percent) > 18) else ""
text_cell2 = "" if text_cell1 else "&nbsp;%d%%&nbsp;" % percent
%>
        <tr>
          <td><img src="memory:emoticon_{{ emoticon if hasattr(emoticons, emoticon) else "transparent" }}.gif" width="19" height="19"/></td>
          <td><table cellpadding="0" cellspacing="0" width="{{ conf.EmoticonsPlotWidth }}">

            <td bgcolor="{{ conf.PlotMessagesColour }}" width="{{ int(round(ratio * conf.EmoticonsPlotWidth)) }}" align="center">
%if text_cell1:
              <font color="#FFFFFF" size="2"><b>{{! text_cell1 }}</b></font>
%endif
            </td>
            <td bgcolor="{{ conf.PlotBgColour }}" width="{{ int(round((1 - ratio) * conf.EmoticonsPlotWidth)) }}" align="center">
%if text_cell2:
              <font color="{{ conf.PlotMessagesColour }}" size="2"><b>{{! text_cell2 }}</b></font>
%endif
            </td>
	        </table></td>
          <td align="right"><font size="2" color="{{ conf.PlotHoursColour }}">&nbsp;{{ count }}</font></td><td><font size="2" color="gray">&nbsp;{{ title }}</font></td>
        </tr>
%endfor
%if identity in emoticon_counts:
    </table>
%else:
    <font color="gray" size="2">No emoticons.</font>
%endif
  </td></tr>
  <tr><td colspan="3"><hr /></td></tr>
%endfor
</table>
%endif
%endif


%if stats["shared_media"]:
<hr />
<b>Shared media</b> [<a href="expand://shared_media"><font color="{{ conf.LinkColour }}" size="4">{{! ("+", "&ndash;")[expand["shared_media"]] }}</font></a>]
%if expand["shared_media"]:
<br /><br />
<table width="100%">
%for message_id, data in sorted(stats["shared_media"].items(), key=lambda x: x[1]["datetime"]):
  <tr>
    <td align="right" valign="top" nowrap="">
      <font size="2" face="{{ conf.HistoryFontName }}" color="{{ conf.HistoryRemoteAuthorColour if data["author"] != db.id else conf.HistoryLocalAuthorColour }}">{{ data["author_name"] }}</font>
    </td>
    <td valign="top">
%if data.get("filename"):
      <font size="2" face="{{ conf.HistoryFontName }}" color="{{ conf.LinkColour }}">{{ data["filename"] }}</font>
%endif
    </td>
    <td align="right" valign="top" nowrap="">
%if data.get("filesize") is not None:
      <font size="2" face="{{ conf.HistoryFontName }}">{{ util.format_bytes(data["filesize"]) }}</font>
%endif
    </td>
    <td valign="top">
%if data.get("url"):
      <font size="2" face="{{ conf.HistoryFontName }}"><a href="{{ data["url"] }}"><font color="{{ conf.LinkColour }}">Online</font></a></font>
%endif
    </td>
    <td align="right" valign="top" nowrap=""><a href="message:{{ message_id }}"><font size="2" color="{{ conf.HistoryTimestampColour }}" face="{{ conf.HistoryFontName }}">{{ data["datetime"].strftime("%Y-%m-%d %H:%M") }}</font></a></td>
  </tr>
%endfor
</table>
%endif
%endif


%if stats.get("transfers"):
<hr /><table cellpadding="0" cellspacing="0" width="100%"><tr><td><a name="transfers"><b>Sent and received files:</b></a></td><td align="right"><a href="#top"><font color="{{ conf.LinkColour }}">Back to top</font></a></td></tr></table><br /><br />
<table width="100%">
%for f in stats["transfers"]:
<%
from_remote = (f["partner_handle"] == db.id and skypedata.TRANSFER_TYPE_INBOUND == f["type"]) or \
              (f["partner_handle"] != db.id and skypedata.TRANSFER_TYPE_OUTBOUND == f["type"])
partner = f["partner_dispname"] or db.get_contact_name(f["partner_handle"])
f_datetime = db.stamp_to_date(f["starttime"]).strftime("%Y-%m-%d %H:%M") if f.get("starttime") else ""
%>
  <tr>
    <td align="right" valign="top" nowrap=""><font size="2" face="{{ conf.HistoryFontName }}" color="{{ conf.HistoryRemoteAuthorColour if from_remote else conf.HistoryLocalAuthorColour }}">{{ partner if from_remote else db.account["name"] }}</font></td>
    <td valign="top"><font size="2" face="{{ conf.HistoryFontName }}">
%if f["filepath"]:
    <a href="{{ util.path_to_url(f["filepath"]) }}">
      <font color="{{ conf.LinkColour }}">{{ f["filepath"] }}</font>
    </a>
%else:
    <font color="{{ conf.LinkColour }}">{{ f["filename"] }}</font>
%endif
    </font></td>
    <td align="right" valign="top" nowrap=""><font size="2" face="{{ conf.HistoryFontName }}">{{ util.format_bytes(int(f["filesize"])) }}</font></td>
    <td align="right" valign="top" nowrap=""><a href="message:{{ f["__message_id"] }}"><font size="2" color="{{ conf.HistoryTimestampColour }}" face="{{ conf.HistoryFontName }}">{{ f_datetime }}</font></a></td>
  </tr>
%endfor
</table>
%endif
</font>
"""


"""
Contact information template, for use with HtmlWindow.

@param   db               SkypeDatabase instance
@param   contact          contact data dictionary, including "conversations": [}
@param   sort_by          the field that chats are currently sorted by
@param   avatar           memoryfs filename
"""
CONTACT_HTML = """<%
from skyperious import conf, skypedata
from skyperious.lib import util

CHAT_COLS = [("title_long", "Chat"), ("message_count", "Messages from contact"),
             ("ratio", "Message ratio"),
             ("first_message_datetime", "First message"),
             ("last_message_datetime", "Last message")]
datefmt = lambda x: x.strftime("%Y-%m-%d %H:%M") if x else ""
chats = {x["id"]: x for x in db.get_conversations()}
%>
<font color="{{ conf.FgColour }}" face="{{ conf.HistoryFontName }}" size="2">
<table cellpadding="0" cellspacing="0" width="100%"><tr>
  <td width="100" align="center" valign="top">
%if avatar:
<%
sz = None
if avatar_size[0] > 300:
    ratio = 300. / avatar_size[0]
    sz = tuple(int(x * ratio) for x in avatar_size)
%>
    <img src="memory:{{ avatar }}" {{! 'width="%s" height="%s" ' % sz if sz else "" }}/><br />
    <a href="avatar"><font color="{{ conf.LinkColour }}">Save image</font></a>
%else:
    <img src="memory:avatar__default__large.png" /><br />
%endif
  </td>
  <td>
    <img src="memory:blank.gif" width="1" height="100" />
  </td>
  <td valign="top">
    <table>
%for name, label in ((n, t) for n, t in skypedata.CONTACT_FIELD_TITLES.items() if skypedata.format_contact_field(contact, n)):
      <tr>
        <td nowrap valign="top"><b>{{ label }}:</b></td>
        <td>{{ skypedata.format_contact_field(contact, name) }}</td>
      </tr>
%endfor
    </table>
  </td>
</tr></table>

<br /><br />

%if contact.get("conversations"):
<table cellpadding="2" cellspacing="2"><tr>
%for i, (name, label) in enumerate(CHAT_COLS):
    <td nowrap width="{{ 100 if i else 400 }}" align="{{ "right" if i in (1, 2) else "left" }}" valign="top">
%if name == sort_by:
        <font color="gray">
%else:
        <a href="sort://{{ name }}"><font color="{{ conf.LinkColour }}">
%endif
            {{ label }}
%if name == sort_by:
        </font>
%else:
        </font></a>
%endif
    </td>
%endfor
%for data in contact["conversations"]:
  <tr>
    <td valign="top">{{ data["title_long"] }} <a href="chat://{{ data["id"] }}"><font color="{{ conf.LinkColour }}">&gt;</font></a></td>
    <td align="right" valign="top">{{ data["message_count"] }}</td>
    <td align="right" valign="top">{{ util.round_float(data["ratio"], 0) + "%" if data.get("ratio") is not None else "" }}</td>
    <td align="right" nowrap valign="top">{{ datefmt(data["first_message_datetime"]) }}
%if data["first_message_datetime"]:
        <a href="chat://{{ data["id"] }}/{{ data["first_message_id"] }}"><font color="{{ conf.LinkColour }}">&gt;</font></a>
%endif
    </td>
    <td align="right" nowrap valign="top">{{ datefmt(data["last_message_datetime"]) }}
%if data["last_message_datetime"]:
        <a href="chat://{{ data["id"] }}/{{ data["last_message_id"] }}"><font color="{{ conf.LinkColour }}">&gt;</font></a>
%endif
    </td>
    <td width="10"></td>
    <td><a href="export://{{ data["id"] }}"><font color="{{ conf.LinkColour }}">Export</font></a></td>
  </tr>
%endfor
</table>
%endif

</font>
"""


"""
HTML template for search result row for a matched chat, HTML table row.

@param   chat              chat data dictionary
@param   result_count      total number of results
@param   pattern_replace   re.RegexObject to find matching text
@param   matching_authors  [{contact data}, ]
@param   title_matches     whether chat was matched by title
@param   wrap_b            function(text) returning <b>text</b>
"""
SEARCH_ROW_CHAT_HTML = """<%
import re
from skyperious import conf
from skyperious.lib.vendor import step

title = step.escape_html(chat["title"])
if title_matches:
    title = pattern_replace.sub(lambda x: "<b>%s</b>" % x.group(0), title)
%>
<tr>
  <td align="right" valign="top">
    <font color="{{ conf.HistoryGreyColour }}">{{ result_count }}</font>
  </td><td colspan="2">
    <a href="chat:{{ chat["id"] }}">
    <font color="{{ conf.SkypeLinkColour }}">{{! title }}</font></a><br />
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
{{ ", " if i else "" }}{{! name_replaced }}{{! identity_replaced }}{{ "." if i == len(matching_authors) - 1 else "" }}
%endfor
<br />
%endif
</td></tr>
"""


"""
TXT template for search result row for a matched chat.

@param   chat              chat data dictionary
@param   result_count      total number of results so far
@param   pattern_replace   re.RegexObject to find matching text
@param   matching_authors  [{contact data}, ]
@param   title_matches     whether chat was matched by title
@param   wrap_b            function(text) returning **text**
"""
SEARCH_ROW_CHAT_TXT = """<%
import re
from skyperious import conf

title = chat["title"]
if title_matches:
    title = pattern_replace.sub(lambda x: "**%s**" % x.group(0), title)
%>
{{ "%3d" % result_count }}. {{ title }}
%if title_matches:
    Title matches.
%endif
%if matching_authors:
    Participant matches: 
%for i, c in enumerate(matching_authors):
<%
name = c["fullname"] or c["displayname"]
name_replaced = pattern_replace.sub(wrap_b, name)
identity_replaced = "" if (c["identity"] == name) else " (%s)" % pattern_replace.sub(wrap_b, c["identity"])
%>
{{ ", " if i else "" }}{{! name_replaced }}{{! identity_replaced }}{{ "." if i == len(matching_authors) - 1 else "" }}
%endfor
%endif
"""


"""
HTML template for search result row of a matched contact, HTML table row.

@param   count             index of current match
@param   result_count      total number of results so far
@param   fields_filled     {field: highlighted value}
@param   pattern_replace   re.RegexObject to find matching text
@param   wrap_b            function(text) returning <b>text</b>
"""
SEARCH_ROW_CONTACT_HTML = """<%
from skyperious import conf, skypedata

%>
%if count <= 1 and result_count > 1:
<tr><td colspan='3'><hr /></td></tr>
%endif
<tr>
  <td align="right" valign="top">
    <font color="{{ conf.DisabledColour }}">{{ result_count }}</font>
  </td><td colspan="2">
    <a href="contact:{{ contact["id"] }}"><font color="{{ conf.LinkColour }}">
      {{! pattern_replace.sub(wrap_b, contact["name"]) }}
    </font></a>
    <br /><table>
%for field in filter(lambda x: x in fields_filled, skypedata.CONTACT_FIELD_TITLES):
      <tr>
        <td nowrap valign="top"><font color="{{ conf.DisabledColour }}">{{ skypedata.CONTACT_FIELD_TITLES[field] }}</font></td>
        <td>&nbsp;</td><td>{{! fields_filled[field] }}</td>
      </tr>
%endfor
</table><br /></td></tr>
"""


"""
TXT template for search result row of a matched contact.

@param   count             index of current match
@param   result_count      total number of results so far
@param   fields_filled     {field: highlighted value}
@param   match_fields      [contact field, ]
@param   pattern_replace   re.RegexObject to find matching text
@param   wrap_b            function(text) returning **text**
"""
SEARCH_ROW_CONTACT_TXT = """<%
from skyperious import conf, skypedata

%>
%if count <= 1 and result_count > 1:
-------------------------------------------------------------------------------
%endif
{{ "%3d" % result_count }}. {{ title }}
{{ pattern_replace.sub(wrap_b, contact["name"]) }}
%for field in filter(lambda x: x in fields_filled, match_fields):
  {{ "15%s" % skypedata.CONTACT_FIELD_TITLES[field] }}: {{ fields_filled[field] }}
%endfor
"""


"""
HTML template for search result of chat messages, HTML table row.

@param   chat              chata data dictionary
@param   m                 message data dictionary
@param   count             index of current match
@param   result_count      total number of results so far
@param   search            {db}
"""
SEARCH_ROW_MESSAGE_HTML = """<%
from skyperious import conf, skypedata

%>
%if count <= 1 and result_count > 1:
<tr><td colspan='3'><hr /></td></tr>
%endif
<tr>
  <td align="right" valign="top">
    <font color="{{ conf.HistoryGreyColour }}">{{ result_count }}</font>
  </td><td valign="top">
<%
after = ""
if (skypedata.CHATS_TYPE_SINGLE != chat["type"]):
  after = " in %s" % chat["title_long_lc"]
elif m["author"] == search["db"].id:
  after = " to %s" % chat["title"]
%>
    <a href="message:{{ m["id"] }}"><font color="{{ conf.SkypeLinkColour }}">{{ search["db"].get_author_name(m) }}{{ after }}</font></a>
  </td><td align="right" nowrap>
    &nbsp;&nbsp;<font color="{{ conf.HistoryTimestampColour }}">{{ search["db"].stamp_to_date(m["timestamp"]).strftime("%d.%m.%Y %H:%M") }}</font>
  </td>
</tr>
<tr><td></td>
  <td width="100%" valign="top" colspan="2">
%if skypedata.MESSAGE_TYPE_INFO == m["type"]:
    <font color="{{ conf.HistoryRemoteAuthorColour if m["author"] == search["db"].id else conf.HistoryLocalAuthorColour }}">{{ search["db"].get_author_name(m) }}</font>
%endif
  {{! body }}<br /></td>
</tr>
"""


"""
TXT template for search result item for chat messages.

@param   chat              chata data dictionary
@param   m                 message data dictionary
@param   search            {db}
"""
SEARCH_ROW_MESSAGE_TXT = """<%
from skyperious import conf, skypedata

after = ""
if skypedata.CHATS_TYPE_SINGLE != chat["type"]:
  after = " in %s" % chat["title_long_lc"]
elif m["author"] == search["db"].id:
  after = " to %s" % chat["title"]
%>
{{ search["db"].stamp_to_date(m["timestamp"]).strftime("%d.%m.%Y %H:%M") }} {{ search["db"].get_author_name(m) }}{{ after }}: {{ body }}
"""


"""
HTML template for search results header, start of HTML table.

@param   text      search query
@param   fromtext  search domain label like "all tables"
"""
SEARCH_HEADER_HTML = """<%
from skyperious import conf

%>
<font size="2" face="{{ conf.HistoryFontName }}" color="{{ conf.FgColour }}">
Results for "{{ text }}" from {{ fromtext }}:
%if "all tables" != fromtext:
<br /><br />
<table width="600" cellpadding="2" cellspacing="0">
%endif
"""


"""
HTML template for table search results header, start of HTML table.

@param   table  table data dictionary {name, columns: [{name, }]}
"""
SEARCH_ROW_TABLE_HEADER_HTML = """
<br /><br /><b><a name="{{ table["name"] }}">Table {{ table["name"] }}:</b></b><br />
<table border="1" cellpadding="4" cellspacing="0" width="1000">
<tr>
<th>#</th>
%for col in table["columns"]:
<th>{{ col["name"] }}</th>
%endfor
</tr>
"""


"""
TXT template for table search results header.

@param   table  table data dictionary {name, columns: [{name, }]}
"""
SEARCH_ROW_TABLE_HEADER_TXT = """
Table {{ table["name"] }}:
%for col in ["#"] + table["columns"]:
{{ col["name"] }}    
%endfor
"""


"""
HTML template for search result of DB table row, HTML table row.

@param   count             number of results so far
@param   table             table data dictionary {name, columns: [{name, }]}
@param   pattern_replace   re.RegexObject to find matching text
@param   wrap_b            function(text) returning <b>text</b>
"""
SEARCH_ROW_TABLE_HTML = """<%
import re
from skyperious.lib import util
from skyperious import conf, templates

%>
<tr>
<td align="right" valign="top"><a href="table:{{ table["name"] }}:{{ count }}">{{ count }}</a></td>
%for col in table["columns"]:
<%
value = row[col["name"]]
value = value if value is not None else ""
value = templates.SAFEBYTE_RGX.sub(templates.SAFEBYTE_REPL, util.to_unicode(value))
%>
<td valign="top">{{! pattern_replace.sub(wrap_b, escape(value)) }}</td>
%endfor
</tr>
"""


"""
TXT template for search result of DB table row.

@param   count             number of results so far
@param   table             table data dictionary {name, columns: [{name, }]}
@param   pattern_replace   re.RegexObject to find matching text
@param   wrap_b            function(text) returning **text**
"""
SEARCH_ROW_TABLE_TXT = """<%
import re
from skyperious.lib import util
from skyperious import conf, templates

%>
{{ count }}
%for col in table["columns"]:
<%
value = row[col["name"]]
value = value if value is not None else ""
value = templates.SAFEBYTE_RGX.sub(templates.SAFEBYTE_REPL, util.to_unicode(value))
%>
{{ pattern_replace.sub(wrap_b, value) }}
%endfor
"""


"""Text shown in Help -> About dialog (HTML content)."""
ABOUT_TEXT = """<%
import sys
from skyperious import conf

%>
<font size="2" face="{{ conf.HistoryFontName }}" color="{{ conf.FgColour }}">
<table cellpadding="0" cellspacing="0"><tr><td valign="top">
<img src="memory:skyperious.png" /></td><td width="10"></td><td valign="center">
<b>{{ conf.Title }} version {{ conf.Version }}</b>, {{ conf.VersionDate }}.<br /><br />

{{ conf.Title }} is written in Python, released as free open source software
under the MIT License.
</td></tr></table><br /><br />


&copy; 2011, Erki Suurjaak.
<a href="{{ conf.HomeUrl }}"><font color="{{ conf.LinkColour }}">suurjaak.github.io/Skyperious</font></a><br /><br /><br />



{{ conf.Title }} has been built using the following open source software:
<ul>
  <li>wxPython,
      <a href="http://wxpython.org"><font color="{{ conf.LinkColour }}">wxpython.org</font></a></li>
  <li>appdirs,
      <a href="https://pypi.org/project/appdirs"><font color="{{ conf.LinkColour }}">pypi.org/project/appdirs</font></a></li>
  <li>beautifulsoup4,
      <a href="https://pypi.org/project/beautifulsoup4"><font color="{{ conf.LinkColour }}">pypi.org/project/beautifulsoup4</font></a></li>
  <li>ijson,
      <a href="https://pypi.org/project/ijson"><font color="{{ conf.LinkColour }}">pypi.org/project/ijson</font></a></li>
  <li>Pillow,
      <a href="https://pypi.org/project/Pillow"><font color="{{ conf.LinkColour }}">pypi.org/project/Pillow</font></a></li>
  <li>pyparsing,
      <a href="https://pypi.org/project/pyparsing"><font color="{{ conf.LinkColour }}">pypi.org/project/pyparsing</font></a></li>
  <li>six,
      <a href="https://pypi.org/project/six/"><font color="{{ conf.LinkColour }}">pypi.org/project/six</font></a></li>
  <li>SkPy,
      <a href="https://pypi.org/project/SkPy"><font color="{{ conf.LinkColour }}">pypi.org/project/SkPy</font></a></li>
  <li>step, Simple Template Engine for Python,
      <a href="https://pypi.org/project/step-template"><font color="{{ conf.LinkColour }}">pypi.org/project/step-template</font></a></li>
  <li>XlsxWriter,
      <a href="https://pypi.org/project/XlsxWriter"><font color="{{ conf.LinkColour }}">
          pypi.org/project/XlsxWriter</font></a></li>
  <li>jsOnlyLightbox,
      <a href="https://github.com/felixhagspiel/jsOnlyLightbox"><font color="{{ conf.LinkColour }}">github.com/felixhagspiel/jsOnlyLightbox</font></a></li>
%if getattr(sys, 'frozen', False):
  <li>Python,
      <a href="http://www.python.org"><font color="{{ conf.LinkColour }}">www.python.org</font></a></li>
  <li>PyInstaller,
      <a href="https://www.pyinstaller.org"><font color="{{ conf.LinkColour }}">www.pyinstaller.org</font></a></li>
%endif
</ul><br /><br />



Emoticons in HTML export are property of Skype Limited, &copy; 2004-2006,
released under the Skype Component License 1.0.<br /><br />


Default avatar icon from Fancy Avatars, &copy; 2009 Brandon Mathis<br />
<a href="https://github.com/imathis/fancy-avatars">
<font color="{{ conf.LinkColour }}">github.com/imathis/fancy-avatars</font></a><br /><br />


Several icons from Fugue Icons, &copy; 2010 Yusuke Kamiyamane<br />
<a href="https://p.yusukekamiyamane.com/"><font color="{{ conf.LinkColour }}">p.yusukekamiyamane.com</font></a>
<br /><br />
Includes fonts Carlito Regular and Carlito bold,
<a href="https://fedoraproject.org/wiki/Google_Crosextra_Carlito_fonts"><font color="{{ conf.LinkColour }}">fedoraproject.org/wiki/Google_Crosextra_Carlito_fonts</font></a>
%if getattr(sys, 'frozen', False):
<br /><br />
Installer created with Nullsoft Scriptable Install System,
<a href="https://nsis.sourceforge.io"><font color="{{ conf.LinkColour }}">nsis.sourceforge.io</font></a>
%endif

</font>
"""



"""Contents of the default page on search page."""
SEARCH_WELCOME_HTML = """<%
from skyperious import conf

%>
<font face="{{ conf.HistoryFontName }}" size="2" color="{{ conf.FgColour }}">
<center>
<h5><font color="{{ conf.SkypeLinkColour }}">Overview</font></h5>
<table cellpadding="0" cellspacing="0">
<tr>
  <td valign="top">
    <table cellpadding="0" cellspacing="2"><tr><td>
        <a href="page:#search"><img src="memory:HelpSearch.png" /></a>
      </td><td width="10"></td><td valign="center">
        Search over all Skype messages using a simple Google-like <a href="page:#help"><font color="{{ conf.LinkColour }}">syntax</font></a>.<br />
        <br />
        Or choose other search targets from the toolbar: <br />
        search in contact information, or in chat information, <br />
        or across all database tables.
      </td></tr><tr><td nowrap align="center">
        <a href="page:#search"><b><font color="{{ conf.FgColour }}">Search</font></b></a><br />
    </td></tr></table>
  </td>
  <td valign="top">
    <table cellpadding="0" cellspacing="2"><tr><td>
        <a href="page:tables"><img src="memory:HelpTables.png" /></a>
      </td><td width="10"></td><td valign="center">
        Browse, filter and change database tables,<br />
        export as HTML, SQL INSERT-statements or spreadsheet.
      </td></tr><tr><td nowrap align="center">
        <a href="page:tables"><b><font color="{{ conf.FgColour }}">Data tables</font></b></a><br />
    </td></tr></table>
  </td>
</tr>
<tr>
  <td valign="top">
    <table cellpadding="0" cellspacing="2"><tr><td>
        <a href="page:chats"><img src="memory:HelpChats.png" /></a>
      </td><td width="10"></td><td valign="center">
        Read Skype chats,
        view statistics and word clouds, <br />
        filter by content, date or author,<br />
        export as HTML, TXT or spreadsheet.
      </td></tr><tr><td nowrap align="center">
        <a href="page:chats"><b><font color="{{ conf.FgColour }}">Chats</font></b></a><br />
    </td></tr></table>
  </td>
  <td valign="top">
    <table cellpadding="0" cellspacing="2"><tr><td>
        <a href="page:sql"><img src="memory:HelpSQL.png" /></a>
      </td><td width="10"></td><td valign="center">
        Make direct SQL queries in the database,<br />
        export results as HTML or spreadsheet.
      </td></tr><tr><td nowrap align="center">
        <a href="page:sql"><b><font color="{{ conf.FgColour }}">SQL window</font></b></a><br />
    </td></tr></table>
  </td>
</tr>
<tr>
  <td valign="top">
    <table cellpadding="0" cellspacing="2"><tr><td>
        <a href="page:chats"><img src="memory:HelpContacts.png" /></a>
      </td><td width="10"></td><td valign="center">
        See Skype contacts, <br />
        statistics on chats they have participated in,<br />
        export contacts and chats.
      </td></tr><tr><td nowrap align="center">
        <a href="page:chats"><b><font color="{{ conf.FgColour }}">Contacts</font></b></a><br />
    </td></tr></table>
  </td>
  <td valign="top">
    <table cellpadding="0" cellspacing="2"><tr><td>
        <a href="page:live"><img src="memory:HelpOnline.png" /></a>
      </td><td width="10"></td><td valign="center">
        Log in to Skype online service<br />
        in order to synchronize chat history from live, <br />
        and download shared media in HTML export. 
      </td></tr><tr><td nowrap align="center">
        <a href="page:live"><b><font color="{{ conf.FgColour }}">Online</font></b></a>
    </td></tr></table>
  </td>
</tr>
<tr>
  <td valign="top">
    <table cellpadding="0" cellspacing="2"><tr><td>
        <a href="page:info"><img src="memory:HelpInfo.png" /></a>
      </td><td width="10"></td><td valign="center">
        See information about the Skype account in this file,<br />
        view general database statistics,<br />
        check database integrity for corruption and recovery.
      </td></tr><tr><td nowrap align="center">
        <a href="page:info"><b><font color="{{ conf.FgColour }}">Information</font></b></a>
    </td></tr></table>
  </td>
</tr>
</table>
</center>
</font>
"""


"""Long help text shown in a separate tab on search page."""
SEARCH_HELP_LONG = """<%
from skyperious import conf

try:
    import pyparsing
except ImportError:
    pyparsing = None
%>
<font size="2" face="{{ conf.HistoryFontName }}" color="{{ conf.FgColour }}">
%if not pyparsing:
<b><font color="red">Search syntax currently limited:</font></b>&nbsp;&nbsp;pyparsing not installed.<br /><br /><br />
%endif
{{ conf.Title }} supports a Google-like syntax for searching messages:<br /><br />
<table><tr><td width="500">
  <table border="0" cellpadding="5" cellspacing="1" bgcolor="{{ conf.HelpBorderColour }}"
   valign="top" width="500">
  <tr>
    <td bgcolor="{{ conf.BgColour }}" width="150">
      <b>Search for exact word or phrase</b><br /><br />
      <font color="{{ conf.HelpCodeColour }}"><code>"do re mi"</code></font>
      <br />
    </td>
    <td bgcolor="{{ conf.BgColour }}">
      <br /><br />
      Use quotes (<font color="{{ conf.HelpCodeColour }}"><code>"</code></font>) to search for
      an exact phrase or word. Quoted text is searched exactly as entered,
      leaving whitespace as-is and ignoring any wildcard characters.
      <br />
    </td>
  </tr>
  <tr>
    <td bgcolor="{{ conf.BgColour }}" width="150">
      <b>Search for either word</b><br /><br />
      <font color="{{ conf.HelpCodeColour }}"><code>this OR that</code></font>
      <br />
    </td>
    <td bgcolor="{{ conf.BgColour }}">
      <br /><br />
      To find messages containing at least one of several words,
      include <font color="{{ conf.HelpCodeColour }}"><code>OR</code></font> between the words.
      <font color="{{ conf.HelpCodeColour }}"><code>OR</code></font> works also
      for phrases and grouped words (but not keywords).
      <br />
    </td>
  </tr>
  <tr>
    <td bgcolor="{{ conf.BgColour }}" width="150">
      <b>Group words together</b><br /><br />
      <font color="{{ conf.HelpCodeColour }}"><code>(these two) OR this<br/>
      -(none of these)</code></font>
      <br />
    </td>
    <td bgcolor="{{ conf.BgColour }}">
      <br /><br />
      Surround words with round brackets to group them for <code>OR</code>
      queries or for excluding from results.
      <br />
    </td>
  </tr>
  <tr>
    <td bgcolor="{{ conf.BgColour }}" width="150">
      <b>Search for partially matching text</b><br /><br />
      <font color="{{ conf.HelpCodeColour }}"><code>bas*ball</code></font>
      <br />
    </td>
    <td bgcolor="{{ conf.BgColour }}">
      <br /><br />
      Use an asterisk (<font color="{{ conf.HelpCodeColour }}"><code>*</code></font>) to make a
      wildcard query: the wildcard will match any text between its front and
      rear characters (including other words).
      <br />
    </td>
  </tr>
  <tr>
    <td bgcolor="{{ conf.BgColour }}" width="150">
      <b>Search within specific chats</b><br /><br />
      <font color="{{ conf.HelpCodeColour }}"><code>chat:office<br />
      chat:"coffee &amp; cig"</code></font>
      <br />
    </td>
    <td bgcolor="{{ conf.BgColour }}">
      <br /><br />
      To find messages from specific chats only, use the keyword
      <font color="{{ conf.HelpCodeColour }}"><code>chat:name</code></font>.<br /><br />
      Search from more than one chat by adding more 
      <font color="{{ conf.HelpCodeColour }}"><code>chat:</code></font> keywords.
      <br />
    </td>
  </tr>
  <tr>
    <td bgcolor="{{ conf.BgColour }}" width="150">
      <b>Search from specific authors</b><br /><br />
      <font color="{{ conf.HelpCodeColour }}"><code>from:maria<br />
      from:"john smith"</code></font>
      <br />
    </td>
    <td bgcolor="{{ conf.BgColour }}">
      <br /><br />
      To find messages from specific authors only, use the keyword
      <font color="{{ conf.HelpCodeColour }}"><code>from:name</code></font>.<br /><br />
      Search from more than one author by adding more
      <font color="{{ conf.HelpCodeColour }}"><code>from:</code></font> keywords.
      <br />
    </td>
  </tr>
  <tr>
    <td bgcolor="{{ conf.BgColour }}" width="150">
      <b>Search from specific time periods</b><br /><br />
      <font color="{{ conf.HelpCodeColour }}"><code>date:2008<br />date:2009-01<br />
      date:2005-12-24..2007</code></font>
      <br />
    </td>
    <td bgcolor="{{ conf.BgColour }}">
      <br /><br />
      To find messages from specific time periods, use the keyword
      <font color="{{ conf.HelpCodeColour }}"><code>date:period</code></font> or
      <font color="{{ conf.HelpCodeColour }}"><code>date:periodstart..periodend</code></font>.
      For the latter, either start or end can be omitted.<br /><br />
      A date period can be year, year-month, or year-month-day. Additionally,
      <font color="{{ conf.HelpCodeColour }}"><code>date:period</code></font> can use a wildcard
      in place of any part, so
      <font color="{{ conf.HelpCodeColour }}"><code>date:*-12-24</code></font> would search for
      all messages from the 24th of December.<br /><br />
      Search from a more narrowly defined period by adding more
      <font color="{{ conf.HelpCodeColour }}"><code>date:</code></font> keywords.
      <br />
    </td>
  </tr>
  <tr>
    <td bgcolor="{{ conf.BgColour }}" width="150">
      <b>Exclude words or keywords</b><br /><br />
      <font color="{{ conf.HelpCodeColour }}"><code>-notthisword<br />-"not this phrase"<br />
      -(none of these)<br/>-chat:notthischat<br/>-from:notthisauthor<br />
      -date:2013</code></font>
      <br />
    </td>
    <td bgcolor="{{ conf.BgColour }}">
      <br /><br />
      To exclude certain messages, add a dash
      (<font color="{{ conf.HelpCodeColour }}"><code>-</code></font>) in front of words,
      phrases, grouped words or keywords.
    </td>
  </tr>
  <tr>
    <td bgcolor="{{ conf.BgColour }}" width="150">
      <b>SPECIAL: search specific tables</b><br /><br />
      <font color="{{ conf.HelpCodeColour }}"><code>table:fromthistable<br />
      -table:notfromthistable</code></font>
      <br />
    </td>
    <td bgcolor="{{ conf.BgColour }}">
      <br /><br />
      When performing search on all columns of all database tables
      (the fourth option on the search toolbar),
      use the keyword <font color="{{ conf.HelpCodeColour }}"><code>table:name</code></font>
      to constrain results to specific tables only.<br /><br />
      Search from more than one table by adding more
      <font color="{{ conf.HelpCodeColour }}"><code>table:</code></font> keywords, or exclude certain
      tables by adding a <font color="{{ conf.HelpCodeColour }}"><code>-table:</code></font> keyword.
      <br />
    </td>
  </tr>
  </table>

</td><td valign="top" align="left">

  <b><font size="3">Examples</font></b><br /><br />

  <ul>
    <li>search for "flickr.com" from John or Jane in chats named "links":
        <br /><br />
        <font color="{{ conf.HelpCodeColour }}">
        <code>flickr.com from:john from:jane chat:links</code></font><br />
    </li>
    <li>search from John Smith up to 2011:<br /><br />
        <font color="{{ conf.HelpCodeColour }}"><code>from:"john smith" date:..2011</code></font>
        <br />
    </li>
    <li>search for either "John" and "my side" or "Stark" and "your side":
        <br /><br />
        <font color="{{ conf.HelpCodeColour }}">
        <code>(john "my side") OR (stark "your side")</code></font><br />
    </li>
    <li>search for either "barbecue" or "grill" in 2012,
        except from June to August:<br /><br />
        <font color="{{ conf.HelpCodeColour }}">
        <code>barbecue OR grill date:2012 -date:2012-06..2012-08</code>
        </font><br />
    </li>
    <li>search for "TPS report" in chats named "office"
        (but not named "backoffice") on the first day of the month in 2012:
        <br /><br />
        <font color="{{ conf.HelpCodeColour }}">
        <code>"tps report" chat:office -chat:backoffice date:2012-*-1</code>
        </font><br />
    </li>
  </ul>

  <br /><br /><br />
  Search is made on raw Skype message body, so there can be results which do not
  seem to match the query - Skype messages contain more than plain text.<br />
  For example, searching for <font color="{{ conf.HelpCodeColour }}"><code>href</code></font> will match a message with body
  <code><font color="{{ conf.HelpCodeColour }}">&lt;a href="http://lmgtfy.com/"&gt;lmgtfy.com&lt;/a&gt;</font></code>,<br />
  displayed as <a href="http://lmgtfy.com/"><font color="{{ conf.LinkColour }}">lmgtfy.com</font></a>.<br /><br />
  This can be used for finding specific type of messages, for example
  <font color="{{ conf.HelpCodeColour }}"><code>&lt;sms</code></font> finds SMS messages, 
  <font color="{{ conf.HelpCodeColour }}"><code>&lt;file</code></font> finds transfers, 
  <font color="{{ conf.HelpCodeColour }}"><code>&lt;quote</code></font> finds quoted messages,
  and <font color="{{ conf.HelpCodeColour }}"><code>&lt;ss</code></font> finds messages with emoticons.

</td></tr></table>
</font>
"""


"""Short help text shown on search page."""
SEARCH_HELP_SHORT = """<%
import os
from skyperious import conf

helplink = "Search help"
if "nt" == os.name: # In Windows, wx.HtmlWindow shows link whitespace quirkily
    helplink = helplink.replace(" ", "_")
%>
<font size="2" face="{{ conf.HistoryFontName }}" color="{{ conf.DisabledColour }}">
For searching messages from specific chats, add "chat:name", and from specific contacts, add "from:name".
&nbsp;&nbsp;<a href=\"page:#help\"><font color="{{ conf.LinkColour }}">{{ helplink }}</font></a>.
</font>
"""


"""
Database links on merge page.

@param   db1  SkypeDatabase instance
@param   db2  SkypeDatabase instance
"""
MERGE_DB_LINKS = """<%
from skyperious import conf, live

%>
%if isinstance(db1, live.SkypeExport):
<font color="{{ conf.FgColour }}">From {{ db1 }} into <a href="{{ db2.filename }}"><font color="{{ conf.LinkColour }}">{{ db2.filename }}</font></a>:</font>
%else:
<font color="{{ conf.FgColour }}">From <a href="{{ db1.filename }}"><font color="{{ conf.LinkColour }}">{{ db1.filename }}</font></a> into <a href="{{ db2.filename }}"><font color="{{ conf.LinkColour }}">{{ db2.filename }}</font></a>:</font>
%endif
"""


"""Information text shown if Skype online login fails."""
LOGIN_FAIL_INFO = """<%
from skyperious import conf

%>
<body text="{{ conf.DisabledColour }}" bgcolor="{{ conf.BgColour }}" link="{{ conf.LinkColour }}">
Skype online login is not very reliable. It can experience temporary failures,
and might not work for all accounts.
<br /><br />
If you are getting a "Profile accrual is required" error,
setting an e-mail address as your primary Skype alias
at <a href="https://account.live.com">account.live.com</a> 
may solve the problem, under Security -> More security options -> Sign-in options.
</font>
"""


"""
HTML template for quote elements in message body.

@param   export  whether content is for HTML export
"""
MESSAGE_QUOTE = """
%if export:
<table class="quote"><tr>
    <td><span>&#8223;</span></td>
    <td><br /><span class="gray">{EMDASH} </span></td>
</tr></table>
%else:
<%
from skyperious import conf
%>
<table cellpadding="0" cellspacing="0"><tr>
    <td valign="top"><font color="{{ conf.DisabledColour }}" size="7">&quot;|</font></td>
    <td><br /><font color="{{ conf.DisabledColour }}">{EMDASH} </font></td>
</tr></table>
%endif
"""


"""
Chat row in database diff results list.

@param   chat  chat data dictionary
"""
DIFF_RESULT_ITEM = """<%
from skyperious import conf

%>
<a href="{{ chat["identity"] }}"><font color="{{ conf.LinkColour }}">{{ chat["title_long"] }}</font></a>
"""


"""
Message template for copying to clipboard.

@param   m       message data dictionary
@param   parser  MessageParser instance
"""
MESSAGE_CLIPBOARD = """
[{{ m["datetime"].strftime("%Y-%m-%d %H:%M:%S") }}] {{ parser.db.get_author_name(m) }}: {{ parser.parse(m, output={"format": "text"}) }}
"""


"""
Histogram SVG for message statistics.

@param   data      [(index or datetime, value), ]
@param   links     {index: href, }
@param   rectsize  histogram single bar size (w, h)
@param   colour    histogram colour
@param   maxval    histogram maximum value
"""
HISTOGRAM_SVG = """<%
import datetime
from skyperious.lib import util

border = 1
rectstep = rectsize[0] + (1 if rectsize[0] < 10 else 2)
interval = data[1][0] - data[0][0]
%>
<svg width="{{ len(data) * rectstep + 2 * border }}" height="{{ rectsize[1] + 2 * border }}">
  <rect width="100%" height="100%" style="stroke-width: {{ border }}; stroke: {{ colour }}; fill: white;" />
%for i, (start, val) in enumerate(data):
<%
height = rectsize[1] * util.safedivf(val, maxval)
if 0 < height < 0.8: height = 0.8 # Very low values produce no or poorly visible bar
if hasattr(start, "strftime"):
    if interval > datetime.timedelta(days=1):
        date2 = start + interval
        datetitle = "%s .. %s, %s days" % (start.strftime("%Y-%m-%d"), date2.strftime("%Y-%m-%d"), interval.days)
    else:
        datetitle = start.strftime("%Y-%m-%d")
    title = "%s: %s" % (datetitle, util.plural("message", val, sep=","))
else:
    title = "%02d. hour: %s" % (start, util.plural("message", val, sep=","))
%>
  <g class="svg_hover_group">
%if start in links:
    <a xlink:title="{{ title }}" xlink:href="{{ links[start] }}">
%endif
      <rect width="{{ rectsize[0] }}" fill="{{ colour }}" height="{{ util.round_float(height, 2) }}" x="{{ i * rectstep + border + 1 }}" y="{{ util.round_float(rectsize[1] - height + border, 2) }}"><title>{{ title }}</title></rect>
      <rect width="{{ rectsize[0] }}" fill="white" height="{{ util.round_float(rectsize[1] - height, 2) }}" x="{{ i * rectstep + border + 1 }}" y="{{ border }}"><title>{{ title }}</title></rect>
%if start in links:
    </a>
%endif
  </g>
%endfor
</svg>
"""


"""CSS rules for chat HTML export shared images lightbox."""
LIGHTBOX_CSS = """
    .jslghtbx-ie8.jslghtbx{background-image:url(../img/trans-bck.png);display:none}.jslghtbx-ie8.jslghtbx.jslghtbx-active{display:block}.jslghtbx-ie8.jslghtbx .jslghtbx-contentwrapper>img{-ms-filter:"progid:DXImageTransform.Microsoft.Alpha(Opacity=0)";display:block}.jslghtbx-ie8.jslghtbx .jslghtbx-contentwrapper.jslghtbx-wrapper-active>img{-ms-filter:"progid:DXImageTransform.Microsoft.Alpha(Opacity=100)"}.jslghtbx{font-family:sans-serif;overflow:auto;visibility:hidden;position:fixed;z-index:2;left:0;top:0;width:100%;height:100%;background-color:transparent}.jslghtbx.jslghtbx-active{visibility:visible;background-color:rgba(0,0,0,.85)}.jslghtbx-loading-animation{margin-top:-60px;margin-left:-60px;width:120px;height:120px;top:50%;left:50%;display:none;position:absolute;z-index:-1}.jslghtbx-loading-animation>span{display:inline-block;width:20px;height:20px;border-radius:20px;margin:5px;background-color:#fff;-webkit-transition:all .3s ease-in-out;-moz-transition:all .3s ease-in-out;-o-transition:all .3s ease-in-out;-ms-transition:all .3s ease-in-out}.jslghtbx-loading-animation>span.jslghtbx-active{margin-bottom:60px}.jslghtbx.jslghtbx-loading .jslghtbx-loading-animation{display:block}.jslghtbx-nooverflow{overflow:hidden!important}.jslghtbx-contentwrapper{margin:auto;visibility:hidden}.jslghtbx-contentwrapper>img{background:#fff;padding:.5em;display:none;height:auto;margin-left:auto;margin-right:auto;opacity:0}.jslghtbx-contentwrapper.jslghtbx-wrapper-active{visibility:visible}.jslghtbx-contentwrapper.jslghtbx-wrapper-active>img{display:block;opacity:1}.jslghtbx-caption{display:none;margin:5px auto;max-width:450px;color:#fff;text-align:center;font-size:.9em}.jslghtbx-active .jslghtbx-caption{display:block}.jslghtbx-contentwrapper.jslghtbx-animate>img{opacity:0}.jslghtbx-contentwrapper>img.jslghtbx-animate-transition{-webkit-transition:opacity .2s ease-in-out;-moz-transition:opacity .2s ease-in-out;-o-transition:opacity .2s ease-in-out;-ms-transition:opacity .2s ease-in-out}.jslghtbx-contentwrapper>img.jslghtbx-animate-init,.jslghtbx-contentwrapper>img.jslghtbx-animating-next,.jslghtbx-contentwrapper>img.jslghtbx-animating-prev{opacity:1;-ms-filter:"progid:DXImageTransform.Microsoft.Alpha(Opacity=100)"}.jslghtbx-contentwrapper>img.jslghtbx-animate-transition{cursor:pointer}.jslghtbx-close{position:fixed;right:23px;top:23px;margin-top:-4px;font-size:2em;color:#FFF;cursor:pointer;-webkit-transition:all .3s ease-in-out;-moz-transition:all .3s ease-in-out;-o-transition:all .3s ease-in-out;-ms-transition:all .3s ease-in-out}.jslghtbx-close:hover{text-shadow:0 0 10px #fff}@media screen and (max-width:1060px){.jslghtbx-close{font-size:1.5em}}.jslghtbx-next,.jslghtbx-prev{display:none;position:fixed;top:50%;max-width:6%;max-height:250px;cursor:pointer;-webkit-transition:all .2s ease-in-out;-moz-transition:all .2s ease-in-out;-o-transition:all .2s ease-in-out;-ms-transition:all .2s ease-in-out}.jslghtbx-next.jslghtbx-active,.jslghtbx-prev.jslghtbx-active{display:block}.jslghtbx-next>img,.jslghtbx-prev>img{width:100%}.jslghtbx-next{right:.6em}.jslghtbx-next.jslghtbx-no-img:hover{border-left-color:#787878}@media screen and (min-width:451px){.jslghtbx-next{right:.6em}.jslghtbx-next.jslghtbx-no-img{border-top:110px solid transparent;border-bottom:110px solid transparent;border-left:40px solid #FFF}}@media screen and (max-width:600px){.jslghtbx-next.jslghtbx-no-img{right:5px;padding-left:0;border-top:60px solid transparent;border-bottom:60px solid transparent;border-left:15px solid #FFF}}@media screen and (max-width:450px){.jslghtbx-next{right:.2em;padding-left:20px}}.jslghtbx-prev{left:.6em}.jslghtbx-prev.jslghtbx-no-img:hover{border-right-color:#787878}@media screen and (min-width:451px){.jslghtbx-prev{left:.6em}.jslghtbx-prev.jslghtbx-no-img{border-top:110px solid transparent;border-bottom:110px solid transparent;border-right:40px solid #FFF}}@media screen and (max-width:600px){.jslghtbx-prev.jslghtbx-no-img{left:5px;padding-right:0;border-top:60px solid transparent;border-bottom:60px solid transparent;border-right:15px solid #FFF}}@media screen and (max-width:450px){.jslghtbx-prev{left:.2em;padding-right:20px}}.jslghtbx-thmb{padding:2px;max-width:100%;max-height:140px;cursor:pointer;box-shadow:0 0 3px 0 #000;-webkit-transition:all .3s ease-in-out;-moz-transition:all .3s ease-in-out;-o-transition:all .3s ease-in-out;-ms-transition:all .3s ease-in-out}@media screen and (min-width:451px){.jslghtbx-thmb{margin:1em}}@media screen and (max-width:450px){.jslghtbx-thmb{margin:1em 0}}.jslghtbx-thmb:hover{box-shadow:0 0 14px 0 #000}
"""

"""JavaScript for chat HTML export shared images lightbox."""
LIGHTBOX_JS = """
    function Lightbox(){function z(){return window.innerHeight||document.documentElement.offsetHeight}function A(){return window.innerWidth||document.documentElement.offsetWidth}function B(a,b,c,d){a.addEventListener?a.addEventListener(b,c,d||!1):a.attachEvent&&a.attachEvent("on"+b,c)}function C(a,b){return a&&b?new RegExp("(^|\\\\s)"+b+"(\\\\s|$)").test(a.className):void 0}function D(a,b){return a&&b?(a.className=a.className.replace(new RegExp("(?:^|\\\\s)"+b+"(?!\\\\S)"),""),a):void 0}function E(a,b){return a&&b?(C(a,b)||(a.className+=" "+b),a):void 0}function F(a){return"undefined"!=typeof a?!0:!1}function G(a,b){if(!a||!F(a))return!1;var c;return a.getAttribute?c=a.getAttribute(b):a.getAttributeNode&&(c=a.getAttributeNode(b).value),F(c)&&""!=c?c:!1}function H(a,b){if(!a||!F(a))return!1;var c;return a.getAttribute?c=a.getAttribute(b):a.getAttributeNode&&(c=a.getAttributeNode(b).value),"string"==typeof c?!0:!1}function I(a){B(a,"click",function(){h=G(a,"data-jslghtbx-group")||!1,i=a,S(a,!1,!1,!1)},!1)}function J(a){a.stopPropagation?a.stopPropagation():a.returnValue=!1}function K(b){for(var c=[],d=0;d<a.thumbnails.length;d++)G(a.thumbnails[d],"data-jslghtbx-group")===b&&c.push(a.thumbnails[d]);return c}function L(a,b){for(var c=K(b),d=0;d<c.length;d++)if(G(a,"src")===G(c[d],"src")&&G(a,"data-jslghtbx")===G(c[d],"data-jslghtbx"))return d}function M(){if(h){var a=new Image,b=new Image,c=L(i,h);c===k.length-1?(a.src=k[k.length-1].src,b.src=k[0].src):0===c?(a.src=k[k.length-1].src,b.src=k[1].src):(a.src=k[c-1].src,b.src=k[c+1].src)}}function N(){if(!b){O();var d=function(){if(E(a.box,"jslghtbx-loading"),!c&&"number"==typeof a.opt.loadingAnimation){var b=0;o=setInterval(function(){E(p[b],"jslghtbx-active"),setTimeout(function(){D(p[b],"jslghtbx-active")},a.opt.loadingAnimation),b=b>=p.length?0:b+=1},a.opt.loadingAnimation)}};q=setTimeout(d,500)}}function O(){if(!b&&(D(a.box,"jslghtbx-loading"),!c&&"string"!=typeof a.opt.loadingAnimation&&a.opt.loadingAnimation)){clearInterval(o);for(var d=0;d<p.length;d++)D(p[d],"jslghtbx-active")}}function P(){if(!r){if(r=document.createElement("span"),E(r,"jslghtbx-next"),a.opt.nextImg){var b=document.createElement("img");b.setAttribute("src",a.opt.nextImg),r.appendChild(b)}else E(r,"jslghtbx-no-img");B(r,"click",function(b){J(b),a.next()},!1),a.box.appendChild(r)}if(E(r,"jslghtbx-active"),!s){if(s=document.createElement("span"),E(s,"jslghtbx-prev"),a.opt.prevImg){var c=document.createElement("img");c.setAttribute("src",a.opt.prevImg),s.appendChild(c)}else E(s,"jslghtbx-no-img");B(s,"click",function(b){J(b),a.prev()},!1),a.box.appendChild(s)}E(s,"jslghtbx-active")}function Q(){if(a.opt.responsive&&r&&s){var b=z()/2-r.offsetHeight/2;r.style.top=b+"px",s.style.top=b+"px"}}function R(c){function f(a){return"boolean"==typeof a?a:!0}if(c||(c={}),a.opt={boxId:c.boxId||!1,controls:f(c.controls),dimensions:f(c.dimensions),captions:f(c.captions),prevImg:"string"==typeof c.prevImg?c.prevImg:!1,nextImg:"string"==typeof c.nextImg?c.nextImg:!1,hideCloseBtn:c.hideCloseBtn||!1,closeOnClick:"boolean"==typeof c.closeOnClick?c.closeOnClick:!0,loadingAnimation:void 0===c.loadingAnimation?!0:c.loadingAnimation,animElCount:c.animElCount||4,preload:f(c.preload),carousel:f(c.carousel),animation:c.animation||400,nextOnClick:f(c.nextOnClick),responsive:f(c.responsive),maxImgSize:c.maxImgSize||.8,keyControls:f(c.keyControls),onopen:c.onopen||!1,onclose:c.onclose||!1,onload:c.onload||!1,onresize:c.onresize||!1,onloaderror:c.onloaderror||!1},a.opt.boxId)a.box=document.getElementById(a.opt.boxId);else if(!a.box&&!document.getElementById("jslghtbx")){var g=document.createElement("div");g.setAttribute("id","jslghtbx"),g.setAttribute("class","jslghtbx"),a.box=g,d.appendChild(a.box)}if(a.box.innerHTML=e,b&&E(a.box,"jslghtbx-ie8"),a.wrapper=document.getElementById("jslghtbx-contentwrapper"),!a.opt.hideCloseBtn){var h=document.createElement("span");h.setAttribute("id","jslghtbx-close"),h.setAttribute("class","jslghtbx-close"),h.innerHTML="X",a.box.appendChild(h),B(h,"click",function(b){J(b),a.close()},!1)}if(!b&&a.opt.closeOnClick&&B(a.box,"click",function(){a.close()},!1),"string"==typeof a.opt.loadingAnimation)n=document.createElement("img"),n.setAttribute("src",a.opt.loadingAnimation),E(n,"jslghtbx-loading-animation"),a.box.appendChild(n);else if(a.opt.loadingAnimation){a.opt.loadingAnimation="number"==typeof a.opt.loadingAnimation?a.opt.loadingAnimation:200,n=document.createElement("div"),E(n,"jslghtbx-loading-animation");for(var i=0;i<a.opt.animElCount;)p.push(n.appendChild(document.createElement("span"))),i++;a.box.appendChild(n)}a.opt.responsive?(B(window,"resize",function(){a.resize()},!1),E(a.box,"jslghtbx-nooverflow")):D(a.box,"jslghtbx-nooverflow"),a.opt.keyControls&&(B(document,"keydown",function(b){J(b),l&&39==b.keyCode&&a.next()},!1),B(document,"keydown",function(b){J(b),l&&37==b.keyCode&&a.prev()},!1),B(document,"keydown",function(b){J(b),l&&27==b.keyCode&&a.close()},!1))}function S(e,f,m,n){if(!e&&!f)return!1;h=f||h||G(e,"data-jslghtbx-group"),h&&(k=K(h),"boolean"!=typeof e||e||(e=k[0])),j.img=new Image,i=e;var o;o="string"==typeof e?e:G(e,"data-jslghtbx")?G(e,"data-jslghtbx"):G(e,"src"),g=!1,l||("number"==typeof a.opt.animation&&E(j.img,"jslghtbx-animate-transition jslghtbx-animate-init"),l=!0,a.opt.onopen&&a.opt.onopen()),a.opt&&F(a.opt.hideOverflow)&&!a.opt.hideOverflow||d.setAttribute("style","overflow: hidden"),a.box.setAttribute("style","padding-top: 0"),a.wrapper.innerHTML="",a.wrapper.appendChild(j.img),a.opt.animation&&E(a.wrapper,"jslghtbx-animate");var p=G(e,"data-jslghtbx-caption");if(p&&a.opt.captions){var r=document.createElement("p");r.setAttribute("class","jslghtbx-caption"),r.innerHTML=p,a.wrapper.appendChild(r)}E(a.box,"jslghtbx-active"),b&&E(a.wrapper,"jslghtbx-active"),a.opt.controls&&k.length>1&&(P(),Q()),j.img.onerror=function(){a.opt.onloaderror&&a.opt.onloaderror(n)},j.img.onload=function(){if(j.originalWidth=this.naturalWidth||this.width,j.originalHeight=this.naturalHeight||this.height,b||c){var d=new Image;d.setAttribute("src",o),j.originalWidth=d.width,j.originalHeight=d.height}var e=setInterval(function(){C(a.box,"jslghtbx-active")&&(E(a.wrapper,"jslghtbx-wrapper-active"),"number"==typeof a.opt.animation&&E(j.img,"jslghtbx-animate-transition"),m&&m(),O(),clearTimeout(q),a.opt.preload&&M(),a.opt.nextOnClick&&(E(j.img,"jslghtbx-next-on-click"),B(j.img,"click",function(b){J(b),a.next()},!1)),a.opt.onload&&a.opt.onload(n),clearInterval(e),a.resize())},10)},j.img.setAttribute("src",o),N()}var n,o,q,t,u,x,y,a=this,b=!1,c=!1,d=document.getElementsByTagName("body")[0],e='<div class="jslghtbx-contentwrapper" id="jslghtbx-contentwrapper" ></div>',g=!1,h=!1,i=!1,j={},k=[],l=!1,p=[],r=!1,s=!1;a.opt={},a.box=!1,a.wrapper=!1,a.thumbnails=[],a.load=function(d){navigator.appVersion.indexOf("MSIE 8")>0&&(b=!0),navigator.appVersion.indexOf("MSIE 9")>0&&(c=!0),R(d);for(var e=document.getElementsByTagName("img"),f=0;f<e.length;f++)H(e[f],"data-jslghtbx")&&(a.thumbnails.push(e[f]),I(e[f]))},a.open=function(a,b){a&&b&&(b=!1),S(a,b,!1,!1)},a.resize=function(){if(j.img){t=A(),u=z();var b=a.box.offsetWidth,c=a.box.offsetHeight;!g&&j.img&&j.img.offsetWidth&&j.img.offsetHeight&&(g=j.img.offsetWidth/j.img.offsetHeight),Math.floor(b/g)>c?(x=c*g,y=c):(x=b,y=b/g),x=Math.floor(x*a.opt.maxImgSize),y=Math.floor(y*a.opt.maxImgSize),(a.opt.dimensions&&y>j.originalHeight||a.opt.dimensions&&x>j.originalWidth)&&(y=j.originalHeight,x=j.originalWidth),j.img.setAttribute("width",x),j.img.setAttribute("height",y),j.img.setAttribute("style","margin-top:"+(z()-y)/2+"px"),setTimeout(Q,200),a.opt.onresize&&a.opt.onresize()}},a.next=function(){if(h){var b=L(i,h)+1;if(k[b])i=k[b];else{if(!a.opt.carousel)return;i=k[0]}"number"==typeof a.opt.animation?(D(j.img,"jslghtbx-animating-next"),setTimeout(function(){var b=function(){setTimeout(function(){E(j.img,"jslghtbx-animating-next")},a.opt.animation/2)};S(i,!1,b,"next")},a.opt.animation/2)):S(i,!1,!1,"next")}},a.prev=function(){if(h){var b=L(i,h)-1;if(k[b])i=k[b];else{if(!a.opt.carousel)return;i=k[k.length-1]}"number"==typeof a.opt.animation?(D(j.img,"jslghtbx-animating-prev"),setTimeout(function(){var b=function(){setTimeout(function(){E(j.img,"jslghtbx-animating-next")},a.opt.animation/2)};S(i,!1,b,"prev")},a.opt.animation/2)):S(i,!1,!1,"prev")}},a.close=function(){h=!1,i=!1,j={},k=[],l=!1,D(a.box,"jslghtbx-active"),D(a.wrapper,"jslghtbx-wrapper-active"),D(r,"jslghtbx-active"),D(s,"jslghtbx-active"),a.box.setAttribute("style","padding-top: 0px"),O(),b&&a.box.setAttribute("style","display: none"),a.opt&&F(a.opt.hideOverflow)&&!a.opt.hideOverflow||d.setAttribute("style","overflow: auto"),a.opt.onclose&&a.opt.onclose()}}
"""
