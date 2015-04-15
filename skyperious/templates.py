# -*- coding: utf-8 -*-
"""
HTML and TXT templates for exports and statistics.

------------------------------------------------------------------------------
This file is part of Skyperious - a Skype database viewer and merger.
Released under the MIT License.

@author      Erki Suurjaak
@created     09.05.2013
@modified    14.04.2015
------------------------------------------------------------------------------
"""
import re

# Modules imported inside templates:
#import base64, datetime, os, pyparsing, re, string, sys, urllib, wx
#import conf, emoticons, images, skypedata, step, templates, util

"""Regex for replacing low bytes unusable in wx.HtmlWindow (\x00 etc)."""
SAFEBYTE_RGX = re.compile("[\x00-\x08,\x0B-\x0C,\x0E-x1F,\x7F]")

"""Replacer callback for low bytes unusable in wx.HtmlWindow (\x00 etc)."""
SAFEBYTE_REPL = lambda m: m.group(0).encode("unicode-escape")

"""HTML chat history export template."""
CHAT_HTML = """<%
import base64, datetime
import conf, emoticons, images, skypedata, templates, util
from third_party import step
%>
<!DOCTYPE HTML><html>
<head>
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
  <meta name="Author" content="{{conf.Title}}">
  <title>Skype {{chat["title_long_lc"]}}</title>
  <link rel="shortcut icon" type="image/png" href="data:image/ico;base64,{{!images.Icon16x16_8bit.data}}"/>
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
    a, a.visited { color: {{conf.ExportLinkColour}}; text-decoration: none; cursor: pointer; }
    a:hover, a.visited:hover { text-decoration: underline; }
    #footer {
      text-align: center;
      padding-bottom: 10px;
      color: #666;
    }
    #header { font-size: 1.1em; font-weight: bold; color: {{conf.ExportLinkColour}}; }
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
      background: url("data:image/png;base64,{{!images.ExportEdited.data}}")
                  center center no-repeat;
    }
    #content_table .timestamp span.removed {
      background: url("data:image/png;base64,{{!images.ExportRemoved.data}}")
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
      background: url("data:image/png;base64,{{!images.ExportClock.data}}")
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
      color: {{conf.PlotHoursColour}};
      vertical-align: top;
    }
    #stats_data > tbody > tr > td:nth-child(4) {
      color: {{conf.PlotDaysColour}};
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
    #wordclouds {
      display: none;
      padding-top: 15px;
    }
    #wordclouds > table {
      border-collapse: collapse;
      width: 100%;
    }
    #wordclouds > table > tbody > tr > td {
      vertical-align: top;
      padding-top: 5px;
      padding-bottom: 10px;
    }
    #wordclouds > table > tbody > tr {
      border-top: 1px solid #99BBFF;
    }
    #wordclouds > table > tbody > tr > td:first-child {
      vertical-align: top;
      width: 150px;
    }
    #toggle_wordclouds {
      font-size: 1.5em;
      color: blue;
      position: relative;
      top: 2px;
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
    #transfers table td:first-child a {
      color: inherit;
    }
    #transfers table td:first-child a:hover {
      text-decoration: underline;
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
    #chat_picture {
%if skypedata.CHATS_TYPE_SINGLE == chat["type"]:
      display: none;
%elif chat_picture_raw:
      margin: 0 10px 0 10px;
%endif
%if chat_picture_size:
      width: {{chat_picture_size[0]}}px;
      height: {{chat_picture_size[1]}}px;
%endif
    }
    span.gray {
      color: #999;
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
      background: url("data:image/gif;base64,{{!getattr(emoticons, e).data}}")
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

    var toggle_wordclouds = function(link) {
      link.innerHTML = "+-"["+" == link.innerHTML ? 1 : 0];
      toggle_element('wordclouds');
      return false;
    };

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
<%
alt = "%s%s" % (p["name"], (" (%s)" % p["identity"]) if p["name"] != p["identity"] else "")
%>
      <div><span class="avatar_large"><img title="{{alt}}" alt="{{alt}}" src="data:image/png;base64,{{!base64.b64encode(p.get("avatar_raw_large", "")) or images.AvatarDefaultLarge.data}}" /></span><br />{{p["name"]}}
%if p["name"] != p["identity"]:
      <br /><span class="identity">{{p["identity"]}}</span>
%endif
      </div>
%endfor
%elif chat_picture_raw:
      <img id="chat_picture" title="{{chat["title"]}}" alt="{{chat["title"]}}" src="data:image/png;base64,{{!base64.b64encode(chat_picture_raw)}}" />
%endif
    </td>
    <td id="header_center">
      <div id="header">{{chat["title_long"]}}.</div><br />
      Showing {{util.plural("message", message_count)}}
%if date1 and date2:
      from <b>{{date1}}</b> to <b>{{date2}}</b>.<br />
%else:
.<br />
%endif
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
<%
alt = "%s%s" % (p["name"], (" (%s)" % p["identity"]) if p["name"] != p["identity"] else "")
%>
      <div><span class="avatar_large"><img title="{{alt}}" alt="{{alt}}" src="data:image/png;base64,{{!base64.b64encode(p.get("avatar_raw_large", "")) or images.AvatarDefaultLarge.data}}" /></span><br />{{p["name"]}}
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
%for p in filter(lambda p: p["identity"] in stats["counts"], sorted(participants, key=lambda p: p["name"].lower())):
<%
alt = "%s (%s)" % (p["name"], p["identity"])
%>
    <span><span class="avatar_large"><img title="{{alt}}" alt="{{alt}}" src="data:image/png;base64,{{!base64.b64encode(p.get("avatar_raw_large", "")) or images.AvatarDefaultLarge.data}}" /></span>{{p["name"]}}<br />
    <span class="identity">
        {{p["identity"]}}
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
      <div>{{label}}</div>
%endfor
      </td><td colspan="2">
%for label, value in stats["info_items"]:
      <div>{{value}}</div>
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
        peak {{util.plural("message", maxval)}}<br />
{{!step.Template(templates.HISTOGRAM_SVG, strip=False, escape=True).expand(svgdata)}}
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
        peak {{util.plural("message", maxval)}}<br />
{{!step.Template(templates.HISTOGRAM_SVG, strip=False, escape=True).expand(svgdata)}}
        <br />{{interval.days}}-day intervals
%endif
      </td></tr>

%if len(stats["counts"]) > 1:
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
      </div></td>
      </tr>
%endif
%for p in filter(lambda p: p["identity"] in stats["counts"], sorted(participants, key=lambda p: p["name"].lower())):
      <tr class="stats_row">
        <td><table><tr><td class="avatar"><img title="{{p["name"]}}" alt="{{p["name"]}}" src="data:image/png;base64,{{!base64.b64encode(p.get("avatar_raw_small", "")) or images.AvatarDefault.data}}" /></td><td><span>{{p["name"]}}<br /><span class="identity">{{p["identity"]}}</span></span></td></tr></table></td>
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
text_cell1 = "%d%%" % round(percent) if (round(percent) > 25) else ""
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
  text, title = util.format_bytes(count), util.plural(label, count)
elif "callduration" == label:
  text, title = util.format_seconds(count, "call"), util.plural("second", count)
else:
  text = title = util.plural(label, count)
%>
          <div class="{{label}}" title="{{count}}">{{text}}</div>
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
{{!step.Template(templates.HISTOGRAM_SVG, strip=False, escape=True).expand(svgdata)}}
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
{{!step.Template(templates.HISTOGRAM_SVG, strip=False, escape=True).expand(svgdata)}}
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
      <span style="font-size: {{sizes[size]}}"><a title="Highlight '{{word}}' and go to first occurrence" href="#" onClick="return hilite(this);">{{word}}</a> <span title="{{countstring}}">({{count}})</span></span> 
%endfor
    </div>

%if stats.get("wordclouds"):
<%
sizes = {7: "2.5em;", 6: "2.1em;", 5: "1.75em;", 4: "1.5em;", 3: "1.3em;", 2: "1.1em;", 1: "0.85em", 0: "0.8em;"}
globalcounts = dict((w, sum(vv.values())) for w, vv in stats["wordcounts"].items())
%>
    <br /><br />
    <b>Word cloud for individuals</b>&nbsp;&nbsp;[<a title="Click to show/hide word clouds for individuals" href="#" onClick="return toggle_wordclouds(this);" id="toggle_wordclouds">+</a>]
    <div id="wordclouds">
      <table>
%for p in filter(lambda p: p["identity"] in stats["counts"], sorted(participants, key=lambda p: p["name"].lower())):
      <tr><td>
        <table><tr><td class="avatar"><img title="{{p["name"]}}" alt="{{p["name"]}}" src="data:image/png;base64,{{!base64.b64encode(p.get("avatar_raw_small", "")) or images.AvatarDefault.data}}" /></td><td><span>{{p["name"]}}<br /><span class="identity">{{p["identity"]}}</span></span></td></tr></table>
      </td><td>
        <div class="wordcloud">
%if stats["wordclouds"].get(p["identity"]):
%for word, count, size in stats["wordclouds"][p["identity"]]:
          <span style="font-size: {{sizes[size]}}"><a title="Highlight '{{word}}' and go to first occurrence" href="#" onClick="return hilite(this);">{{word}}</a> <span title="{{"%d%% of total usage" % round(100. * count / globalcounts.get(word, count))}}">({{count}})</span></span> 
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



%if stats["transfers"]:
    <div id="transfers">
      <span>Sent and received files:</span>
      <table style="width: 100%">
%for f in stats["transfers"]:
<%
from_remote = (f["partner_handle"] == db.id and skypedata.TRANSFER_TYPE_INBOUND == f["type"]) or \
              (f["partner_handle"] != db.id and skypedata.TRANSFER_TYPE_OUTBOUND == f["type"])
partner = f["partner_dispname"] or db.get_contact_name(f["partner_handle"])
dt = db.stamp_to_date(f["starttime"]) if f.get("starttime") else None
f_datetime = dt.strftime("%Y-%m-%d %H:%M") if dt else ""
f_datetime_title = dt.strftime("%Y-%m-%d %H:%M:%S") if dt else ""
%>
        <tr><td{{!" class='remote'" if from_remote else ""}} title="{{f["partner_handle"] if from_remote else db.account["skypename"]}}"><a href="#message:{{f["__message_id"]}}">{{partner if from_remote else db.account["name"]}}</a></td><td>
          <a href="{{util.path_to_url(f["filepath"] or f["filename"])}}" target="_blank">{{f["filepath"] or f["filename"]}}</a>
        </td><td title="{{util.plural("byte", int(f["filesize"]))}}">
          {{util.format_bytes(int(f["filesize"]))}}
        </td><td title="{{f_datetime_title}}">
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
<%
for chunk in message_buffer:
    echo(chunk)
%>
  </table>
</td></tr></table>
<div id="footer">Exported with {{conf.Title}} on {{datetime.datetime.now().strftime("%d.%m.%Y %H:%M")}}.</div>
</body>
</html>
"""


"""HTML chat history export template for the messages part."""
CHAT_MESSAGES_HTML = """<%
import skypedata, util

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
    <td class="day t3" title="{{day.strftime("%Y-%m-%d")}}"></td>
    <td class="day" colspan="2" title="{{day.strftime("%Y-%m-%d")}}"><span class="weekday">{{weekday}}</span>, {{weekdate}}</td>
  </tr>
%endif
<%
text = parser.parse(m, output={"format": "html", "export": True})
from_name = m["from_dispname"] if previous_author != m["author"] else ""
# Info messages like "/me is thirsty" -> author on same line.
is_info = (skypedata.MESSAGE_TYPE_INFO == m["type"])
# Kludge to get single-line messages with an emoticon to line up correctly
# with the author, as emoticons have an upper margin pushing the row higher
text_plain = m.get("body_txt", text)
emot_start = '<span class="emoticon '
shift_row = emot_start in text and (("<br />" not in text and len(text_plain) < 140) or text.index(emot_start) < 140)
author_class = "remote" if m["author"] != db.id else "local"
%>
  <tr{{' class="shifted"' if shift_row else ""}}>
    <td class="author {{author_class}}" colspan="2" title="{{m["author"]}}" id="message:{{m["id"]}}">{{from_name if not is_info else ""}}</td>
    <td class="t3"></td>
    <td class="message_content"><div>
%if is_info:
    <span class="{{author_class}}">{{m["from_dispname"]}}</span>
%endif
    {{!text}}
    </div></td>
    <td class="timestamp" title="{{m["datetime"].strftime("%Y-%m-%d %H:%M:%S")}}">
%if m["edited_timestamp"]:
    {{m["datetime"].strftime("%H:%M")}}<span class="{{"edited" if m["body_xml"] else "removed"}}" title="{{"Edited" if m["body_xml"] else "Removed"}} {{db.stamp_to_date(m["edited_timestamp"]).strftime("%H:%M:%S")}}">&nbsp;&nbsp;&nbsp;</span>
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

<%
for chunk in message_buffer:
    echo(chunk)
%>
"""


"""TXT chat history export template for the messages part."""
CHAT_MESSAGES_TXT = """<%
import skypedata, util

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

{{weekday}}, {{weekdate}}
----------------------------------------

%endif
%if skypedata.MESSAGE_TYPE_INFO == m["type"]:
{{m["datetime"].strftime("%H:%M")}}
{{m["from_dispname"]}} {{parser.parse(m, output={"format": "text", "wrap": True})}}
%else:
{{m["datetime"].strftime("%H:%M")}} {{m["from_dispname"]}}:
{{parser.parse(m, output={"format": "text", "wrap": True})}}
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
    <link rel="shortcut icon" type="image/png" href="data:image/ico;base64,{{!images.Icon16x16_8bit.data}}"/>
    <style>
        * { font-family: {{conf.HistoryFontName}}; font-size: 11px; }
        body {
            background: {{conf.HistoryBackgroundColour}};
            margin: 0px 10px 0px 10px;
        }
        .header { font-size: 1.1em; font-weight: bold; color: {{conf.ExportLinkColour}}; }
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
        a, a.visited { color: conf.ExportLinkColour; text-decoration: none; }
        a:hover, a.visited:hover { text-decoration: underline; }
        .footer {
          text-align: center;
          padding-bottom: 10px;
          color: #666;
        }
        .header { font-size: 1.1em; font-weight: bold; color: conf.ExportLinkColour; }
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
            <b>SQL:</b> {{sql}}
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
<td>{{"" if row[col] is None else row[col]}}</td>
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
            except UnicodeError:
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
import urllib
import conf, skypedata, util
%>
<font color="{{conf.FgColour}}" face="{{conf.HistoryFontName}}" size="3">
<table cellpadding="0" cellspacing="0" width="100%"><tr>
  <td><a name="top"><b>Statistics for currently shown messages in {{chat["title_long_lc"]}}:</b></a></td>
%if stats.get("wordcloud"):
  <td align="right" valign="top" nowrap=""><a href="#cloud"><font color="{{conf.LinkColour}}">Jump to word cloud</font></a></td>
%endif
</tr></table>
<font size="0">&nbsp;</font><br />
<font size="2">
<table cellpadding="2" cellspacing="2" width="100%">
%for i, (label, value) in enumerate(stats["info_items"]):
  <tr>
    <td width="150" valign="top">{{label}}:</td><td valign="top">{{value}}</td>
%if not i:
    <td rowspan="{{len(stats["info_items"])}}" valign="bottom">
%if "hours" in images:
<%
items = sorted(stats["totalhist"]["hours"].items())
maxkey, maxval = max(items, key=lambda x: x[1])
%>
      <font color="{{conf.PlotHoursColour}}">
      peak {{util.plural("message", maxval)}}<br />
      <img src="memory:{{images["hours"]}}" usemap="#hours-histogram"/><br />
      24h actitity</font>
      <map name="hours-histogram">
%for (x1, y1, x2, y2), link in imagemaps["hours"]:
        <area shape="rect" coords="{{x1}},{{y1}},{{x2}},{{y2}}" href="{{link}}">
%endfor
      </map>
%endif
    </td>
    <td rowspan="{{len(stats["info_items"])}}" valign="bottom">
%if "days" in images:
<%
items = sorted(stats["totalhist"]["days"].items())
maxkey, maxval = max(items, key=lambda x: x[1])
interval = items[1][0] - items[0][0]
%>
      <font color="{{conf.PlotDaysColour}}">
      peak {{util.plural("message", maxval)}}<br />
      <img src="memory:{{images["days"]}}" usemap="#days-histogram" /><br />
      {{interval.days}}-day intervals</font>
      <map name="days-histogram">
%for (x1, y1, x2, y2), link in imagemaps["days"]:
        <area shape="rect" coords="{{x1}},{{y1}},{{x2}},{{y2}}" href="{{link}}">
%endfor
      </map>
%endif
    </td>
%endif
  </tr>
%endfor

%if len(stats["counts"]) > 1:
  <tr><td><br /><br /></td><td colspan="3" valign="bottom">
    <b>Sort by:&nbsp;&nbsp;&nbsp;</b>
%for name, label in [("name", "Name"), ("messages", "Messages"), ("chars", "Characters"), ("smses", "SMS messages"), ("smschars", "SMS characters"), ("calls", "Calls"), ("calldurations", "Call duration"), ("files", "Files")]:
%if "name" == name or stats[name]:
%if sort_by == name:
      <span><font color="gray">{{label}}</font>&nbsp;&nbsp;&nbsp;&nbsp;</span>
%else:
      <span><a href="sort://{{name}}"><font color="{{conf.LinkColour}}">{{label}}</font></a>&nbsp;&nbsp;&nbsp;&nbsp;</span>
%endif
%endif
%endfor
  </td></tr>
%endif

<%
colormap = {"messages": conf.PlotMessagesColour, "smses": conf.PlotSMSesColour, "calls": conf.PlotCallsColour, "files": conf.PlotFilesColour}
sort_key = lambda p: -stats["counts"][p["identity"]].get(sort_by, 0) if "name" != sort_by else p["name"].lower()
participants_sorted = sorted(filter(lambda p: p["identity"] in stats["counts"], participants), key=sort_key)
%>

%for p in participants_sorted:
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
  <tr>
    <td valign="top">
      <table cellpadding="0" cellspacing="0"><tr>
        <td valign="top"><img src="memory:{{authorimages[p["identity"]]["avatar"]}}"/>&nbsp;&nbsp;</td>
        <td valign="center">{{p["name"]}}<br /><font size="2" color="gray">{{p["identity"]}}</font></td>
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
  text_cell3 = util.plural(label, count)
%>
      <table cellpadding="0" cellspacing="0" width="100%"><tr>
        <td bgcolor="{{colormap[type]}}" width="{{int(round(ratio * conf.StatisticsPlotWidth))}}" align="center">
%if text_cell1:
          <font color="#FFFFFF" size="2"><b>{{!text_cell1}}</b></font>
%endif
        </td>
        <td bgcolor="{{conf.PlotBgColour}}" width="{{int(round((1 - ratio) * conf.StatisticsPlotWidth))}}" align="center">
%if text_cell2:
          <font color="{{conf.PlotMessagesColour}}" size="2"><b>{{!text_cell2}}</b></font>
%endif
        </td>
        <td nowrap="">&nbsp;{{!text_cell3}}</td>
      </tr></table>
%endfor
    </td>
    <td valign="top">
<%
safe_id = urllib.quote(p["identity"])
%>
%if "hours" in authorimages.get(p["identity"] , {}):
      <img src="memory:{{authorimages[p["identity"]]["hours"]}}" usemap="#{{safe_id}}-hours" />
      <map name="{{safe_id}}-hours">
%for (x1, y1, x2, y2), link in authorimagemaps[p["identity"]]["hours"]:
        <area shape="rect" coords="{{x1}},{{y1}},{{x2}},{{y2}}" href="{{link}}">
%endfor
      </map>
%endif
    </td>
    <td valign="top">
%if "days" in authorimages.get(p["identity"] , {}):
      <img src="memory:{{authorimages[p["identity"]]["days"]}}" usemap="#{{safe_id}}-days" />
      <map name="{{safe_id}}-days">
%for (x1, y1, x2, y2), link in authorimagemaps[p["identity"]]["days"]:
        <area shape="rect" coords="{{x1}},{{y1}},{{x2}},{{y2}}" href="{{link}}">
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
  <td align="right"><a href="#top"><font color="{{conf.LinkColour}}">Back to top</font></a></td>
</tr></table>
<br /><br />
%for word, count, size in stats["wordcloud"]:
<font color="{{conf.LinkColour}}" size="{{size}}"><a href="{{word}}"><font color="{{conf.LinkColour}}">{{word}}</font></a> ({{count}}) </font>
%endfor
%endif

%if stats.get("wordclouds"):
<br /><br />
<b>Word cloud for individuals</b> [<a href="clouds://{{not expand_clouds}}"><font color="{{conf.LinkColour}}" size="4">{{"+-"[expand_clouds]}}</font></a>]
%if expand_clouds:
<table cellpadding="0" cellspacing="0" width="100%">
%for p in participants_sorted:
  <tr><td colspan="2"><hr /></td></tr>
  <tr><td valign="top" width="150">
    <table cellpadding="0" cellspacing="0"><tr>
      <td valign="top"><img src="memory:{{authorimages[p["identity"]]["avatar"]}}"/>&nbsp;&nbsp;</td>
      <td valign="center"><font size="2">{{p["name"]}}<br /><font color="gray">{{p["identity"]}}</font></font></td>
      <td width="10"></td>
    </tr></table>
  </td><td valign="top">
%if stats["wordclouds"].get(p["identity"]):
%for word, count, size in stats["wordclouds"][p["identity"]]:
    <font color="{{conf.LinkColour}}" size="{{size}}"><a href="{{word}}"><font color="{{conf.LinkColour}}">{{word}}</font></a> ({{count}}) </font>
%endfor
%else:
    <font color="gray" size="2">Not enough words.</font>
%endif
  </td></tr>
%endfor
</table>
%endif
%endif

%if stats.get("transfers"):
<br /><hr /><table cellpadding="0" cellspacing="0" width="100%"><tr><td><a name="transfers"><b>Sent and received files:</b></a></td><td align="right"><a href="#top"><font color="{{conf.LinkColour}}">Back to top</font></a></td></tr></table><br /><br />
<table width="100%">
%for f in stats["transfers"]:
<%
from_remote = (f["partner_handle"] == db.id and skypedata.TRANSFER_TYPE_INBOUND == f["type"]) or \
              (f["partner_handle"] != db.id and skypedata.TRANSFER_TYPE_OUTBOUND == f["type"])
partner = f["partner_dispname"] or db.get_contact_name(f["partner_handle"])
f_datetime = db.stamp_to_date(f["starttime"]).strftime("%Y-%m-%d %H:%M") if f.get("starttime") else ""
%>
  <tr>
    <td align="right" nowrap="" valign="top"><a href="message:{{f["__message_id"]}}"><font size="2" face="{{conf.HistoryFontName}}" color="{{conf.HistoryRemoteAuthorColour if from_remote else conf.HistoryLocalAuthorColour}}">{{partner if from_remote else db.account["name"]}}</font></a></td>
    <td valign="top"><font size="2" face="{{conf.HistoryFontName}}"><a href="{{util.path_to_url(f["filepath"] or f["filename"])}}"><font color="{{conf.LinkColour}}">{{f["filepath"] or f["filename"]}}</font></a></font></td>
    <td nowrap="" align="right" valign="top"><font size="2" face="{{conf.HistoryFontName}}">{{util.format_bytes(int(f["filesize"]))}}</font></td>
    <td nowrap="" valign="top"><font size="2" face="{{conf.HistoryFontName}}">{{f_datetime}}</font></td>
  </tr>
%endfor
</table>
%endif
</font>
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
    <font color="{{conf.SkypeLinkColour}}">{{title}}</font></a><br />
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
{{", " if i else ""}}{{!name_replaced}}{{!identity_replaced}}{{"." if i == len(matching_authors) - 1 else ""}}
%endfor
<br />
%endif
</td></tr>
"""


"""TXT template for search result row for a matched chat."""
SEARCH_ROW_CHAT_TXT = """<%
import re
import conf

title = chat["title"]
if title_matches:
    title = pattern_replace.sub(lambda x: "**%s**" % x.group(0), title)
%>
{{"%3d" % result_count}}. {{title}}
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
{{", " if i else ""}}{{!name_replaced}}{{!identity_replaced}}{{"." if i == len(matching_authors) - 1 else ""}}
%endfor
%endif
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
    <font color="{{conf.DisabledColour}}">{{result_count}}</font>
  </td><td colspan="2">
    <font color="{{conf.DisabledColour}}">{{!pattern_replace.sub(wrap_b, contact["name"])}}</font>
    <br /><table>
%for field in filter(lambda x: x in fields_filled, match_fields):
      <tr>
        <td nowrap valign="top"><font color="{{conf.DisabledColour}}">{{skypedata.CONTACT_FIELD_TITLES[field]}}</font></td>
        <td>&nbsp;</td><td>{{!fields_filled[field]}}</td>
      </tr>
%endfor
</table><br /></td></tr>
"""


"""TXT template for search result row of a matched contact."""
SEARCH_ROW_CONTACT_TXT = """<%
import conf, skypedata
%>
%if count <= 1 and result_count > 1:
-------------------------------------------------------------------------------
%endif
{{"%3d" % result_count}}. {{title}}
{{pattern_replace.sub(wrap_b, contact["name"])}}
%for field in filter(lambda x: x in fields_filled, match_fields):
  {{"15%s" % skypedata.CONTACT_FIELD_TITLES[field]}}: {{fields_filled[field]}}
%endfor
"""


"""HTML template for search result of chat messages, HTML table row."""
SEARCH_ROW_MESSAGE_HTML = """<%
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
if (skypedata.CHATS_TYPE_SINGLE != chat["type"]):
  after = " in %s" % chat["title_long_lc"]
elif m["author"] == search["db"].id:
  after = " to %s" % chat["title"]
%>
    <a href="message:{{m["id"]}}"><font color="{{conf.SkypeLinkColour}}">{{m["from_dispname"]}}{{after}}</font></a>
  </td><td align="right" nowrap>
    &nbsp;&nbsp;<font color="{{conf.HistoryTimestampColour}}">{{search["db"].stamp_to_date(m["timestamp"]).strftime("%d.%m.%Y %H:%M")}}</font>
  </td>
</tr>
<tr><td></td>
  <td width="100%" valign="top" colspan="2">
%if skypedata.MESSAGE_TYPE_INFO == m["type"]:
    <font color="{{conf.HistoryRemoteAuthorColour if m["author"] == search["db"].id else conf.HistoryLocalAuthorColour}}">{{m["from_dispname"]}}</font>
%endif
  {{!body}}<br /></td>
</tr>
"""


"""TXT template for search result item for chat messages."""
SEARCH_ROW_MESSAGE_TXT = """<%
import conf, skypedata

after = ""
if skypedata.CHATS_TYPE_SINGLE != chat["type"]:
  after = " in %s" % chat["title_long_lc"]
elif m["author"] == search["db"].id:
  after = " to %s" % chat["title"]
%>
{{search["db"].stamp_to_date(m["timestamp"]).strftime("%d.%m.%Y %H:%M")}} {{m["from_dispname"]}}{{after}}: {{body}}
"""


"""HTML template for search results header, start of HTML table."""
SEARCH_HEADER_HTML = """<%
import conf
%>
<font size="2" face="{{conf.HistoryFontName}}" color="{{conf.FgColour}}">
Results for "{{text}}" from {{fromtext}}:
%if "all tables" != fromtext:
<br /><br />
<table width="600" cellpadding="2" cellspacing="0">
%endif
"""


"""HTML template for table search results header, start of HTML table."""
SEARCH_ROW_TABLE_HEADER_HTML = """
<br /><br /><b><a name="{{table["name"]}}">Table {{table["name"]}}:</b></b><br />
<table border="1" cellpadding="4" cellspacing="0" width="1000">
<tr>
<th>#</th>
%for col in table["columns"]:
<th>{{col["name"]}}</th>
%endfor
</tr>
"""


"""TXT template for table search results header."""
SEARCH_ROW_TABLE_HEADER_TXT = """
Table {{table["name"]}}:
%for col in ["#"] + table["columns"]:
{{col["name"]}}    
%endfor
"""


"""HTML template for search result of DB table row, HTML table row."""
SEARCH_ROW_TABLE_HTML = """<%
import re
import conf, templates
%>
<tr>
<td align="right" valign="top"><a href="table:{{table["name"]}}:{{count}}">{{count}}</a></td>
%for col in table["columns"]:
<%
value = row[col["name"]]
value = value if value is not None else ""
value = templates.SAFEBYTE_RGX.sub(templates.SAFEBYTE_REPL, unicode(value))
%>
<td valign="top">{{!pattern_replace.sub(wrap_b, escape(value))}}</td>
%endfor
</tr>
"""


"""TXT template for search result of DB table row."""
SEARCH_ROW_TABLE_TXT = """<%
import re
import conf, templates
%>
{{count}}
%for col in table["columns"]:
<%
value = row[col["name"]]
value = value if value is not None else ""
value = templates.SAFEBYTE_RGX.sub(templates.SAFEBYTE_REPL, unicode(value))
%>
{{pattern_replace.sub(wrap_b, value)}}
%endfor
"""


"""Text shown in Help -> About dialog (HTML content)."""
ABOUT_TEXT = """<%
import sys
import conf
%>
<font size="2" face="{{conf.HistoryFontName}}" color="{{conf.FgColour}}">
<table cellpadding="0" cellspacing="0"><tr><td valign="top">
<img src="memory:skyperious.png" /></td><td width="10"></td><td valign="center">
<b>{{conf.Title}} version {{conf.Version}}</b>, {{conf.VersionDate}}.<br /><br />

{{conf.Title}} is written in Python, released as free open source software
under the MIT License.
</td></tr></table><br /><br />


&copy; 2011, Erki Suurjaak.
<a href="{{conf.HomeUrl}}"><font color="{{conf.LinkColour}}">suurjaak.github.com/Skyperious</font></a><br /><br /><br />



{{conf.Title}} has been built using the following open source software:
<ul>
  <li>wxPython{{" 3.0.2.0" if getattr(sys, 'frozen', False) else ""}},
      <a href="http://wxpython.org"><font color="{{conf.LinkColour}}">wxpython.org</font></a></li>
  <li>Pillow{{" 2.8.0" if getattr(sys, 'frozen', False) else ""}},
      <a href="https://pypi.python.org/pypi/Pillow/"><font color="{{conf.LinkColour}}">pypi.python.org/pypi/Pillow</font></a></li>
  <li>step, Simple Template Engine for Python,
      <a href="https://github.com/dotpy/step"><font color="{{conf.LinkColour}}">github.com/dotpy/step</font></a></li>
      <li>pyparsing{{" 2.0.3" if getattr(sys, 'frozen', False) else ""}}, 
      <a href="http://pyparsing.wikispaces.com/"><font color="{{conf.LinkColour}}">pyparsing.wikispaces.com</font></a></li>
  <li>XlsxWriter{{" 0.6.7" if getattr(sys, 'frozen', False) else ""}},
      <a href="https://github.com/jmcnamara/XlsxWriter"><font color="{{conf.LinkColour}}">
          github.com/jmcnamara/XlsxWriter</font></a></li>
  <li>dateutil{{" 2.4.1" if getattr(sys, 'frozen', False) else ""}}, <a href="https://pypi.python.org/pypi/python-dateutil">
      <font color="{{conf.LinkColour}}">pypi.python.org/pypi/python-dateutil</font></a></li>
  <li>Skype4Py, <a href="https://github.com/awahlig/skype4py">
      <font color="{{conf.LinkColour}}">github.com/awahlig/skype4py</font></a></li>
%if getattr(sys, 'frozen', False):
  <li>Python 2.7.9, <a href="http://www.python.org"><font color="{{conf.LinkColour}}">www.python.org</font></a></li>
  <li>PyInstaller 2.1, <a href="http://www.pyinstaller.org">
      <font color="{{conf.LinkColour}}">www.pyinstaller.org</font></a></li>
%endif
</ul><br /><br /><br />



Emoticons in HTML export are property of Skype Limited, &copy; 2004-2006,
released under the Skype Component License 1.0.<br /><br />


Default avatar icon from Fancy Avatars, &copy; 2009 Brandon Mathis<br />
<a href="http://brandonmathis.com/projects/fancy-avatars/">
<font color="{{conf.LinkColour}}">brandonmathis.com/projects/fancy-avatars</font></a><br /><br />


Several icons from Fugue Icons, &copy; 2010 Yusuke Kamiyamane<br />
<a href="http://p.yusukekamiyamane.com/"><font color="{{conf.LinkColour}}">p.yusukekamiyamane.com</font></a>
<br /><br />
Includes fonts Carlito Regular and Carlito bold,
<a href="https://fedoraproject.org/wiki/Google_Crosextra_Carlito_fonts"><font color="{{conf.LinkColour}}">fedoraproject.org/wiki/Google_Crosextra_Carlito_fonts</font></a>
%if getattr(sys, 'frozen', False):
<br /><br />
Installer created with Nullsoft Scriptable Install System 3.0a2,
<a href="http://nsis.sourceforge.net/"><font color="{{conf.LinkColour}}">nsis.sourceforge.net</font></a>
%endif

</font>
"""



"""Contents of the default page on search page."""
SEARCH_WELCOME_HTML = """<%
import conf
%>
<font face="{{conf.HistoryFontName}}" size="2" color="{{conf.FgColour}}">
<center>
<h5><font color="{{conf.SkypeLinkColour}}">Explore the database</font></h5>
<table cellpadding="10" cellspacing="0">
<tr>
  <td>
    <table cellpadding="0" cellspacing="2"><tr><td>
        <a href="page:#search"><img src="memory:HelpSearch.png" /></a>
      </td><td width="10"></td><td valign="center">
        Search over all Skype messages using a simple Google-like <a href="page:#help"><font color="{{conf.LinkColour}}">syntax</font></a>.<br />
        <br />
        Or choose other search targets from the toolbar: <br />
        search in contact information, or in chat information, <br />
        or across all database tables.
      </td></tr><tr><td nowrap align="center">
        <a href="page:#search"><b><font color="{{conf.FgColour}}">Search</font></b></a><br />
    </td></tr></table>
  </td>
  <td>
    <table cellpadding="0" cellspacing="2"><tr><td>
        <a href="page:tables"><img src="memory:HelpTables.png" /></a>
      </td><td width="10"></td><td valign="center">
        Browse, filter and change database tables,<br />
        export as HTML, SQL INSERT-statements or spreadsheet.
      </td></tr><tr><td nowrap align="center">
        <a href="page:tables"><b><font color="{{conf.FgColour}}">Data tables</font></b></a><br />
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
        export as HTML, TXT or spreadsheet.
      </td></tr><tr><td nowrap align="center">
        <a href="page:chats"><b><font color="{{conf.FgColour}}">Chats</font></b></a><br />
    </td></tr></table>
  </td>
  <td>
    <table cellpadding="0" cellspacing="2"><tr><td>
        <a href="page:sql"><img src="memory:HelpSQL.png" /></a>
      </td><td width="10"></td><td valign="center">
        Make direct SQL queries in the database,<br />
        export results as HTML or spreadsheet.
      </td></tr><tr><td nowrap align="center">
        <a href="page:sql"><b><font color="{{conf.FgColour}}">SQL window</font></b></a><br />
    </td></tr></table>
  </td>
</tr>
<tr>
  <td>
    <table cellpadding="0" cellspacing="2"><tr><td>
        <a href="page:info"><img src="memory:HelpInfo.png" /></a>
      </td><td width="10"></td><td valign="center">
        See information about the Skype account in this file,<br />
        view general database statistics,<br />
        check database integrity for corruption and recovery.
      </td></tr><tr><td nowrap align="center">
        <a href="page:info"><b><font color="{{conf.FgColour}}">Information</font></b></a>
    </td></tr></table>
  </td>
  <td>
    <table cellpadding="0" cellspacing="2"><tr><td>
        <a href="page:contacts"><img src="memory:HelpContacts.png" /></a>
      </td><td width="10"></td><td valign="center">
        Import contacts to Skype from a CSV file,<br />
        like ones exported from MSN or GMail.
      </td></tr><tr><td nowrap align="center">
        <a href="page:contacts"><b><font color="{{conf.FgColour}}">Contacts+</font></b></a>
    </td></tr></table>
  </td>
</tr>
</table>
</center>
</font>
"""


"""Long help text shown in a separate tab on search page."""
SEARCH_HELP_LONG = """<%
import conf
try:
    import pyparsing
except ImportError:
    pyparsing = None
%>
<font size="2" face="{{conf.HistoryFontName}}" color="{{conf.FgColour}}">
%if not pyparsing:
<b><font color="red">Search syntax currently limited:</font></b>&nbsp;&nbsp;pyparsing not installed.<br /><br /><br />
%endif
{{conf.Title}} supports a Google-like syntax for searching messages:<br /><br />
<table><tr><td width="500">
  <table border="0" cellpadding="5" cellspacing="1" bgcolor="{{conf.HelpBorderColour}}"
   valign="top" width="500">
  <tr>
    <td bgcolor="{{conf.BgColour}}" width="150">
      <b>Search for exact word or phrase</b><br /><br />
      <font color="{{conf.HelpCodeColour}}"><code>"do re mi"</code></font>
      <br />
    </td>
    <td bgcolor="{{conf.BgColour}}">
      <br /><br />
      Use quotes (<font color="{{conf.HelpCodeColour}}"><code>"</code></font>) to search for
      an exact phrase or word. Quoted text is searched exactly as entered,
      leaving whitespace as-is and ignoring any wildcard characters.
      <br />
    </td>
  </tr>
  <tr>
    <td bgcolor="{{conf.BgColour}}" width="150">
      <b>Search for either word</b><br /><br />
      <font color="{{conf.HelpCodeColour}}"><code>this OR that</code></font>
      <br />
    </td>
    <td bgcolor="{{conf.BgColour}}">
      <br /><br />
      To find messages containing at least one of several words,
      include <font color="{{conf.HelpCodeColour}}"><code>OR</code></font> between the words.
      <font color="{{conf.HelpCodeColour}}"><code>OR</code></font> works also
      for phrases and grouped words (but not keywords).
      <br />
    </td>
  </tr>
  <tr>
    <td bgcolor="{{conf.BgColour}}" width="150">
      <b>Group words together</b><br /><br />
      <font color="{{conf.HelpCodeColour}}"><code>(these two) OR this<br/>
      -(none of these)</code></font>
      <br />
    </td>
    <td bgcolor="{{conf.BgColour}}">
      <br /><br />
      Surround words with round brackets to group them for <code>OR</code>
      queries or for excluding from results.
      <br />
    </td>
  </tr>
  <tr>
    <td bgcolor="{{conf.BgColour}}" width="150">
      <b>Search for partially matching text</b><br /><br />
      <font color="{{conf.HelpCodeColour}}"><code>bas*ball</code></font>
      <br />
    </td>
    <td bgcolor="{{conf.BgColour}}">
      <br /><br />
      Use an asterisk (<font color="{{conf.HelpCodeColour}}"><code>*</code></font>) to make a
      wildcard query: the wildcard will match any text between its front and
      rear characters (including other words).
      <br />
    </td>
  </tr>
  <tr>
    <td bgcolor="{{conf.BgColour}}" width="150">
      <b>Search within specific chats</b><br /><br />
      <font color="{{conf.HelpCodeColour}}"><code>chat:office<br />
      chat:"coffee &amp; cig"</code></font>
      <br />
    </td>
    <td bgcolor="{{conf.BgColour}}">
      <br /><br />
      To find messages from specific chats only, use the keyword
      <font color="{{conf.HelpCodeColour}}"><code>chat:name</code></font>.<br /><br />
      Search from more than one chat by adding more 
      <font color="{{conf.HelpCodeColour}}"><code>chat:</code></font> keywords.
      <br />
    </td>
  </tr>
  <tr>
    <td bgcolor="{{conf.BgColour}}" width="150">
      <b>Search from specific authors</b><br /><br />
      <font color="{{conf.HelpCodeColour}}"><code>from:maria<br />
      from:"john smith"</code></font>
      <br />
    </td>
    <td bgcolor="{{conf.BgColour}}">
      <br /><br />
      To find messages from specific authors only, use the keyword
      <font color="{{conf.HelpCodeColour}}"><code>from:name</code></font>.<br /><br />
      Search from more than one author by adding more
      <font color="{{conf.HelpCodeColour}}"><code>from:</code></font> keywords.
      <br />
    </td>
  </tr>
  <tr>
    <td bgcolor="{{conf.BgColour}}" width="150">
      <b>Search from specific time periods</b><br /><br />
      <font color="{{conf.HelpCodeColour}}"><code>date:2008<br />date:2009-01<br />
      date:2005-12-24..2007</code></font>
      <br />
    </td>
    <td bgcolor="{{conf.BgColour}}">
      <br /><br />
      To find messages from specific time periods, use the keyword
      <font color="{{conf.HelpCodeColour}}"><code>date:period</code></font> or
      <font color="{{conf.HelpCodeColour}}"><code>date:periodstart..periodend</code></font>.
      For the latter, either start or end can be omitted.<br /><br />
      A date period can be year, year-month, or year-month-day. Additionally,
      <font color="{{conf.HelpCodeColour}}"><code>date:period</code></font> can use a wildcard
      in place of any part, so
      <font color="{{conf.HelpCodeColour}}"><code>date:*-12-24</code></font> would search for
      all messages from the 24th of December.<br /><br />
      Search from a more narrowly defined period by adding more
      <font color="{{conf.HelpCodeColour}}"><code>date:</code></font> keywords.
      <br />
    </td>
  </tr>
  <tr>
    <td bgcolor="{{conf.BgColour}}" width="150">
      <b>Exclude words or keywords</b><br /><br />
      <font color="{{conf.HelpCodeColour}}"><code>-notthisword<br />-"not this phrase"<br />
      -(none of these)<br/>-chat:notthischat<br/>-from:notthisauthor<br />
      -date:2013</code></font>
      <br />
    </td>
    <td bgcolor="{{conf.BgColour}}">
      <br /><br />
      To exclude certain messages, add a dash
      (<font color="{{conf.HelpCodeColour}}"><code>-</code></font>) in front of words,
      phrases, grouped words or keywords.
    </td>
  </tr>
  <tr>
    <td bgcolor="{{conf.BgColour}}" width="150">
      <b>SPECIAL: search specific tables</b><br /><br />
      <font color="{{conf.HelpCodeColour}}"><code>table:fromthistable<br />
      -table:notfromthistable</code></font>
      <br />
    </td>
    <td bgcolor="{{conf.BgColour}}">
      <br /><br />
      When performing search on all columns of all database tables
      (the fourth option on the search toolbar),
      use the keyword <font color="{{conf.HelpCodeColour}}"><code>table:name</code></font>
      to constrain results to specific tables only.<br /><br />
      Search from more than one table by adding more
      <font color="{{conf.HelpCodeColour}}"><code>table:</code></font> keywords, or exclude certain
      tables by adding a <font color="{{conf.HelpCodeColour}}"><code>-table:</code></font> keyword.
      <br />
    </td>
  </tr>
  </table>

</td><td valign="top" align="left">

  <b><font size="3">Examples</font></b><br /><br />

  <ul>
    <li>search for "flickr.com" from John or Jane in chats named "links":
        <br /><br />
        <font color="{{conf.HelpCodeColour}}">
        <code>flickr.com from:john from:jane chat:links</code></font><br />
    </li>
    <li>search from John Smith up to 2011:<br /><br />
        <font color="{{conf.HelpCodeColour}}"><code>from:"john smith" date:..2011</code></font>
        <br />
    </li>
    <li>search for either "John" and "my side" or "Stark" and "your side":
        <br /><br />
        <font color="{{conf.HelpCodeColour}}">
        <code>(john "my side") OR (stark "your side")</code></font><br />
    </li>
    <li>search for either "barbecue" or "grill" in 2012,
        except from June to August:<br /><br />
        <font color="{{conf.HelpCodeColour}}">
        <code>barbecue OR grill date:2012 -date:2012-06..2012-08</code>
        </font><br />
    </li>
    <li>search for "TPS report" in chats named "office"
        (but not named "backoffice") on the first day of the month in 2012:
        <br /><br />
        <font color="{{conf.HelpCodeColour}}">
        <code>"tps report" chat:office -chat:backoffice date:2012-*-1</code>
        </font><br />
    </li>
  </ul>

  <br /><br /><br />
  Search is made on raw Skype message body, so there can be results which do not
  seem to match the query - Skype messages contain more than plain text.<br />
  For example, searching for <font color="{{conf.HelpCodeColour}}"><code>href</code></font> will match a message with body
  <code><font color="{{conf.HelpCodeColour}}">&lt;a href="http://lmgtfy.com/"&gt;lmgtfy.com&lt;/a&gt;</font></code>,<br />
  displayed as <a href="http://lmgtfy.com/"><font color="{{conf.LinkColour}}">lmgtfy.com</font></a>.<br /><br />
  This can be used for finding specific type of messages, for example
  <font color="{{conf.HelpCodeColour}}"><code>&lt;sms</code></font> finds SMS messages, 
  <font color="{{conf.HelpCodeColour}}"><code>&lt;file</code></font> finds transfers, 
  <font color="{{conf.HelpCodeColour}}"><code>&lt;quote</code></font> finds quoted messages,
  and <font color="{{conf.HelpCodeColour}}"><code>&lt;ss</code></font> finds messages with emoticons.

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
<font size="2" face="{{conf.HistoryFontName}}" color="{{conf.DisabledColour}}">
For searching messages from specific chats, add "chat:name", and from specific contacts, add "from:name".
&nbsp;&nbsp;<a href=\"page:#help\"><font color="{{conf.LinkColour}}">{{helplink}}</font></a>.
</font>
"""


"""Database links on merge page."""
MERGE_DB_LINKS = """<%
import conf
%>
<font color="{{conf.FgColour}}">From <a href="{{db1.filename}}"><font color="{{conf.LinkColour}}">{{db1.filename}}</font></a> into <a href="{{db2.filename}}"><font color="{{conf.LinkColour}}">{{db2.filename}}</font></a>:</font>
"""


"""HTML template for quote elements in message body."""
MESSAGE_QUOTE = """
%if export:
<table class="quote"><tr>
    <td><span>&#8223;</span></td>
    <td><br /><span class="gray">{EMDASH} </span></td>
</tr></table>
%else:
<%
import conf
%>
<table cellpadding="0" cellspacing="0"><tr>
    <td valign="top"><font color="{{conf.DisabledColour}}" size="7">&quot;|</font></td>
    <td><br /><font color="{{conf.DisabledColour}}">{EMDASH} </font></td>
</tr></table>
%endif
"""


"""Chat row in database diff results list."""
DIFF_RESULT_ITEM = """<%
import conf
%>
<a href="{{chat["identity"]}}"><font color="{{conf.LinkColour}}">{{chat["title_long"]}}</font></a>
"""


"""Message template for copying to clipboard."""
MESSAGE_CLIPBOARD = """
[{{m["datetime"].strftime("%Y-%m-%d %H:%M:%S")}}] {{m["from_dispname"]}}: {{parser.parse(m, output={"format": "text"})}}
"""


"""Histogram SVG from [(interval, value), ] data."""
HISTOGRAM_SVG = """<%
#Expects parameters: data, links, rectsize, colour, maxval.
import datetime
import util

border = 1
rectstep = rectsize[0] + (1 if rectsize[0] < 10 else 2)
interval = data[1][0] - data[0][0]
%>
<svg width="{{len(data) * rectstep + 2 * border}}" height="{{rectsize[1] + 2 * border}}">
  <rect width="100%" height="100%" style="stroke-width: {{border}}; stroke: {{colour}}; fill: none;" />
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
    title = "%s: %s" % (datetitle, util.plural("message", val))
else:
    title = "%02d. hour: %s" % (start, util.plural("message", val))
%>
  <g class="svg_hover_group">
%if start in links:
    <a xlink:title="{{title}}" xlink:href="{{links[start]}}">
%endif
      <rect width="{{rectsize[0]}}" fill="{{colour}}" height="{{util.round_float(height, 2)}}" x="{{i * rectstep + border + 1}}" y="{{util.round_float(rectsize[1] - height + border, 2)}}"><title>{{title}}</title></rect>
      <rect width="{{rectsize[0]}}" fill="white" height="{{util.round_float(rectsize[1] - height, 2)}}" x="{{i * rectstep + border + 1}}" y="{{border}}"><title>{{title}}</title></rect>
%if start in links:
    </a>
%endif
  </g>
%endfor
</svg>
"""
