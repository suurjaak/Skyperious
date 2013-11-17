# -*- coding: utf-8 -*-
"""
Updates and error reporting.

------------------------------------------------------------------------------
This file is part of Skyperious - a Skype database viewer and merger.
Released under the MIT License.

@author      Erki Suurjaak
@created     16.04.2013
@modified    16.11.2013
------------------------------------------------------------------------------
"""
import base64
import datetime
import hashlib
import HTMLParser
import os
import re
import sys
import tempfile
import time
import traceback
import urllib
import urllib2
import wx

import conf
import controls
import main
import util

"""Current update dialog window, if any, for avoiding concurrent updates."""
update_window = None

"""Feedback window reusable instance."""
feedback_window = None

"""URL-opener with Skyperious useragent."""
url_opener = urllib2.build_opener()
url_opener.addheaders = [("User-agent", "%s %s" % (conf.Title, conf.Version))]


def check_newest_version(callback=None):
    """
    Queries the Skyperious download page for available newer releases.

    @param   callback  function to call with check result, if any
             @result   (version, url, changes) if new version up,
                       () if up-to-date, None if query failed
    """
    global update_window, url_opener
    result = ()
    update_window = True
    try:
        main.log("Checking for new version at %s.", conf.DownloadURL)
        html = url_opener.open(conf.DownloadURL).read()
        links = re.findall("<a[^>]*\shref=['\"](.+)['\"][^>]*>", html, re.I)
        links = [urllib.basejoin(conf.DownloadURL, x) for x in links[:3]]
        if links:
            # Determine release types
            linkmap = {} # {"src": link, "x86": link, "x64": link}
            for link in links:
                link_text = link.lower()
                if link_text.endswith(".zip"):
                    linkmap["src"] = link
                elif link_text.endswith(".exe") and "_x64" in link_text:
                    linkmap["x64"] = link
                elif link_text.endswith(".exe"):
                    linkmap["x86"] = link

            install_type = get_install_type()
            link = linkmap[install_type]
            # Extract version number like 1.3.2a from skyperious_1.3.2a_x64.exe
            version = (re.findall("(\d[\da-z.]+)", link) + [None])[0]
            try:
                if version != conf.Version \
                and canonic_version(conf.Version) >= canonic_version(version):
                    version = None
            except: pass
            if version and version != conf.Version:
                main.log("Newest %s version is %s.", install_type, version)
                changes = ""
                try:
                    main.log("Reading changelog from %s.", conf.ChangelogURL)
                    html = url_opener.open(conf.ChangelogURL).read()
                    match = re.search("<h4[^>]*>(v%s,.*)</h4\s*>" % version,
                                      html, re.I)
                    if match:
                        ul = html[match.end(0):html.find("</ul", match.end(0))]
                        lis = re.findall("(<li[^>]*>(.+)</li\s*>)+", ul, re.I)
                        items = [re.sub("<[^>]+>", "", x[1]) for x in lis]
                        items = map(HTMLParser.HTMLParser().unescape, items)
                        changes = "\n".join("- " + i.strip() for i in items)
                        if changes:
                            title = match.group(1)
                            changes = "Changes in %s\n\n%s" % (title, changes)
                except:
                    main.log("Failed to read changelog.\n\n%s.",
                             traceback.format_exc())
                url = urllib.basejoin(conf.DownloadURL, link)
                result = (version, url, changes)
    except:
        main.log("Failed to retrieve new version from %s.\n\n%s",
                 conf.DownloadURL, traceback.format_exc())
        result = None
    update_window = None
    if callback:
        callback(result)
    return result



def download_and_install(url):
    """
    Downloads and launches the specified file.
    """
    global update_window, url_opener
    try:
        is_cancelled = False
        parent = wx.GetApp().TopWindow
        filename, tmp_dir = os.path.split(url)[-1], tempfile.mkdtemp()
        dlg_progress = \
            controls.ProgressWindow(parent, "Downloading %s" % filename)
        dlg_progress.SetGaugeForegroundColour(conf.GaugeColour)
        dlg_progress.Position = (
            parent.Position.x + parent.Size.width  - dlg_progress.Size.width,
            parent.Position.y + parent.Size.height - dlg_progress.Size.height)
        update_window = dlg_progress
        urlfile = url_opener.open(url)
        filepath = os.path.join(tmp_dir, filename)
        main.log("Downloading %s to %s.", url, filepath)
        filesize = int(urlfile.headers.get("content-length", sys.maxint))
        with open(filepath, "wb") as f:
            BLOCKSIZE = 65536
            bytes_downloaded = 0
            buf = urlfile.read(BLOCKSIZE)
            while len(buf):
                f.write(buf)
                bytes_downloaded += len(buf)
                percent = 100 * bytes_downloaded / filesize
                msg = "%d%% of %s" % (percent, util.format_bytes(filesize))
                is_cancelled = not dlg_progress.Update(percent, msg)
                if is_cancelled:
                    break # break while len(buf)
                wx.YieldIfNeeded()
                buf = urlfile.read(BLOCKSIZE)
        dlg_progress.Destroy()
        update_window = None
        if is_cancelled:
            main.log("Removing temporary file %s.", filepath)
            util.try_until(lambda: os.unlink(filepath), count=1)
            util.try_until(lambda: os.rmdir(tmp_dir), count=1)
        else:
            main.log("Successfully downloaded %s of %s.",
                     util.format_bytes(filesize), filename)
            dlg_proceed = controls.NonModalOKDialog(parent,
                "Update information",
                "Ready to open %s. You should close %s before upgrading."
                % (filename, conf.Title))
            def proceed_handler(event):
                global update_window
                update_window = None
                dlg_proceed.Destroy()
                util.start_file(filepath)
            update_window = dlg_proceed
            dlg_proceed.Bind(wx.EVT_CLOSE, proceed_handler)
    except:
        main.log("Failed to download new version from %s.\n\n%s", url,
                 traceback.format_exc())



def reporting_write(write):
    """
    Decorates a write(str) method with a handler that collects written text
    and queues reporting errors in the background.
    """
    cached = []
    def handle_error():
        text = "".join(cached)[:100000]
        if text:
            main.log(text)
            report_error(text)
        cached[:] = []
    def cache_text(string):
        if not cached:
            # CallLater fails if not called from main thread
            wx.CallAfter(wx.CallLater, 500, handle_error)
        cached.append(string)
        return write(string)
    return cache_text



def take_screenshot():
    """Returns a wx.Bitmap screenshot taken of the main window."""
    window = wx.GetApp().TopWindow
    rect   = window.GetRect()

    # adjust widths for Linux (figured out by John Torres 
    # http://article.gmane.org/gmane.comp.python.wxpython/67327)
    if "linux2" == sys.platform:
        client_x, client_y = window.ClientToScreen((0, 0))
        border_width       = client_x - rect.x
        title_bar_height   = client_y - rect.y
        rect.width        += (border_width * 2)
        rect.height       += title_bar_height + border_width

    window.Raise()
    wx.YieldIfNeeded()
    dc = wx.ScreenDC()
    bmp = wx.EmptyBitmap(rect.width, rect.height)
    dc_bmp = wx.MemoryDC()
    dc_bmp.SelectObject(bmp)
    dc_bmp.Blit(0, 0, rect.width, rect.height, dc, rect.x, rect.y)
    dc_bmp.SelectObject(wx.NullBitmap)
    return bmp


def report_error(text):
    """Reports the error, if error reporting is enabled and below limit."""
    if conf.ErrorReportsAutomatic:
        # Set severe constraints on error sending to avoid creating
        # a busy idiot.
        today = datetime.date.today().strftime("%Y%m%d")
        conf.ErrorsReportedOnDay = conf.ErrorsReportedOnDay or {}
        reports_today = conf.ErrorsReportedOnDay.get(today, 0)
        text_hashed = "%s\n\n%s" % (conf.Version, text)
        hash = hashlib.sha1(text_hashed).hexdigest()
        if hash not in conf.ErrorReportHashes \
        and reports_today < conf.ErrorReportsPerDay:
            reports_today += 1
            conf.ErrorReportHashes.append(hash)
            conf.ErrorsReportedOnDay[today] = reports_today
            # Keep configuration in reasonable size
            if len(conf.ErrorReportHashes) > conf.ErrorsStoredMax:
                conf.ErrorReportHashes = \
                    conf.ErrorReportHashes[-conf.ErrorHashesMax:]
            if len(conf.ErrorsReportedOnDay) > conf.ErrorsStoredMax:
                days = sorted(conf.ErrorsReportedOnDay.keys())
                # Prune older days from dictionary
                for day in days[:len(days) - conf.ErrorsStoredMax]:
                    del conf.ErrorsReportedOnDay[day]
            conf.save()
            send_report(text, "error")


def send_report(content, type, screenshot=""):
    """Posts feedback or error data to the report web service."""
    global url_opener
    try:
        data = {"content": content.encode("utf-8"), "type": type,
                "screenshot": base64.b64encode(screenshot),
                "version": "%s-%s" % (conf.Version, get_install_type())}
        url_opener.open(conf.ReportURL, urllib.urlencode(data))
        main.log("Sent %s report to %s (%s).", type, conf.ReportURL, content)
    except:
        main.log("Failed to send %s to %s.\n\n%s", type, conf.ReportURL,
                 traceback.format_exc())


def get_install_type():
    """Returns the current Skyperious installation type (src|x64|x86)."""
    prog_text = sys.argv[0].lower()
    if not prog_text.endswith(".exe"):
        result = "src"
    elif util.is_os_64bit() and "program files\\" in prog_text:
        result = "x64"
    else:
        result = "x86"
    return result


def canonic_version(v):
    """Returns a numeric version representation: "1.3.2a" to 10301,99885."""
    nums = [int(re.sub("[^\d]", "", x)) for x in v.split(".")][::-1]
    nums[0:0] = [0] * (3 - len(nums)) # Zero-pad if version like 1.4 or just 2
    # Like 1.4a: subtract 1 and add fractions to last number to make < 1.4
    if re.findall("\d+([\D]+)$", v):
        ords = map(ord, re.findall("\d+([\D]+)$", v)[0])
        nums[0] += sum(x / (65536. ** (i + 1)) for i, x in enumerate(ords)) - 1
    return sum((x * 100 ** i) for i, x in enumerate(nums))


class FeedbackDialog(wx.Dialog):
    """
    A non-modal dialog for sending feedback with an optional screenshot,
    stays on top of parent.
    """
    THUMB_SIZE = (150, 90)

    """
    Dialog for entering a message to send to author, can include a screenshot.
    """
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent=parent, title="Send feedback",
                          style=wx.CAPTION | wx.CLOSE_BOX |
                                wx.FRAME_FLOAT_ON_PARENT | wx.RESIZE_BORDER)
        self.MinSize = (460, 460)
        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        panel = self.panel = wx.Panel(self)
        sizer = self.panel.Sizer = wx.BoxSizer(wx.VERTICAL)

        sizer_upper = wx.BoxSizer(wx.HORIZONTAL)
        label = self.label_message = wx.StaticText(panel,
            label="Opinions, ideas for improvement, problems?")
        label_info = self.label_info = wx.StaticText(panel,
            label="For reply, include a contact e-mail.")
        label_info.ForegroundColour = "grey"
        sizer_upper.Add(label, flag=wx.GROW)
        sizer_upper.AddStretchSpacer()
        sizer_upper.Add(label_info, flag=wx.ALIGN_RIGHT)
        sizer.Add(sizer_upper, border=8, flag=wx.GROW | wx.ALL)

        edit = self.edit_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE)
        sizer.Add(edit, proportion=2, border=8,
                  flag=wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.GROW)

        sizer_lower = wx.BoxSizer(wx.HORIZONTAL)
        cb = self.cb_bmp = wx.CheckBox(panel, label="Include\nscreenshot")
        bmp = self.bmp = wx.StaticBitmap(panel, size=self.THUMB_SIZE)
        sizer_lower.Add(cb, flag=wx.ALIGN_BOTTOM)
        sizer_lower.Add(bmp, border=8, flag=wx.LEFT | wx.ALIGN_CENTER_VERTICAL)

        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.button_ok = wx.Button(panel, label="Send")
        self.button_cancel = wx.Button(panel, label="Cancel", id=wx.ID_CANCEL)
        sizer_buttons.Add(self.button_ok, border=8, flag=wx.LEFT | wx.RIGHT)
        sizer_buttons.Add(self.button_cancel)
        sizer_lower.AddStretchSpacer()
        sizer_lower.Add(sizer_buttons, flag=wx.ALIGN_RIGHT | wx.ALIGN_BOTTOM)
        sizer.Add(sizer_lower, border=8,
                  flag=wx.ALL | wx.ALIGN_BOTTOM | wx.GROW)

        self.Sizer.Add(panel, proportion=1, flag=wx.GROW)
        self.Bind(wx.EVT_CHECKBOX, self.OnToggleScreenshot, self.cb_bmp)
        self.Bind(wx.EVT_BUTTON, self.OnSend, self.button_ok)
        self.Bind(wx.EVT_BUTTON, self.OnCancel, self.button_cancel)
        self.Bind(wx.EVT_CLOSE, self.OnCancel)

        self.SetScreenshot(None)
        self.Layout()
        self.Refresh()
        self.Size = self.Size # Touch to force correct size
        self.Show()


    def SetScreenshot(self, bitmap=None):
        """Sets the screenshot bitmap, if any."""
        self.screenshot = bitmap
        thumb = wx.NullBitmap
        if bitmap:
            img = wx.ImageFromBitmap(bitmap)
            img = img.ResampleBox(*self.THUMB_SIZE)
            # wx.BitmapFromImage/img.ConvertToBitmap can yield buggy bitmaps
            thumb = wx.BitmapFromBuffer(img.Width, img.Height, img.Data)
        self.cb_bmp.Value = bool(bitmap)
        self.bmp.SetBitmap(thumb)
        self.bmp.Show(self.cb_bmp.Value)


    def OnToggleScreenshot(self, event):
        """Handler for toggling screenshot on/off."""
        if self.cb_bmp.Value:
            pos = self.Position
            self.Hide() # Dialog window can interfere with screen copy
            screenshot = take_screenshot()
            self.Show()
            self.Position = pos # Can lose position on hide in Linux
            self.SetScreenshot(screenshot)
        self.bmp.Show(self.cb_bmp.Value)
        self.Layout()


    def OnSend(self, event):
        """
        Handler for clicking to send feedback, hides the dialog and posts data
        to feedback web service.
        """
        text = self.edit_text.Value.strip()
        text_short = text[:500] + ".." if len(text) > 500 else text
        bmp = self.cb_bmp.Value and self.screenshot
        if text:
            ok = wx.MessageBox("Send the entered text%s?\n\n\"%s\"" % (
                               " and screenshot" if bmp else "", text_short),
                               self.Title, wx.OK | wx.CANCEL | 
                               wx.ICON_INFORMATION)
            text = (text if wx.OK == ok else "")
        if text:
            self.Hide()
            time.sleep(0.1)
            kwargs = {"type": "feedback"}
            kwargs["content"] = text
            if bmp:
                kwargs["screenshot"] = util.bitmap_to_raw(bmp)
            wx.CallAfter(lambda: send_report(**kwargs))
            wx.MessageBox("Feedback sent, thank you!", self.Title, wx.OK)
            self.edit_text.Value = ""
            self.edit_text.SetFocus()
            self.SetScreenshot(None)


    def OnCancel(self, event):
        """Handler for cancelling sending feedback, hides the dialog."""
        self.Hide()
