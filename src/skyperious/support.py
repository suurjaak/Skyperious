# -*- coding: utf-8 -*-
"""
Updates and error reporting.

------------------------------------------------------------------------------
This file is part of Skyperious - Skype chat history tool.
Released under the MIT License.

@author      Erki Suurjaak
@created     16.04.2013
@modified    27.03.2022
------------------------------------------------------------------------------
"""
import datetime
import logging
import os
import platform
import re
import ssl
import sys
import tempfile

from six.moves import html_parser, urllib
import wx
import wx.adv

from . lib import controls
from . lib.controls import ColourManager
from . lib import util
from . lib import wx_accel

from . import conf
from . import guibase

"""Current update dialog window, if any, for avoiding concurrent updates."""
update_window = None

"""Feedback window reusable instance."""
feedback_window = None

"""URL-opener given Skyperious user-agent."""
url_opener = urllib.request.build_opener(
    urllib.request.HTTPSHandler(context=ssl._create_unverified_context())
)

logger = logging.getLogger(__name__)


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
        logger.info("Checking for new version at %s.", conf.DownloadURL)
        html = util.to_unicode(url_opener.open(conf.DownloadURL).read())
        links = re.findall("<a[^>]*\\shref=['\"](.+)['\"][^>]*>", html, re.I)
        if links:
            # Determine release types
            linkmap = {} # {"src": link, "x86": link, "x64": link}
            for link in links[:3]:
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
            version = (re.findall("(\\d[\\da-z.]+)", link) + [None])[0]
            logger.info("Newest %s version is %s.", install_type, version)
            try:
                if (version != conf.Version
                and canonic_version(conf.Version) >= canonic_version(version)):
                    version = None
            except Exception: pass
            if version and version != conf.Version:
                changes = ""
                try:
                    logger.info("Reading changelog from %s.", conf.ChangelogURL)
                    html = util.to_unicode(url_opener.open(conf.ChangelogURL).read())
                    match = re.search("<h4[^>]*>(v%s,.*)</h4\\s*>" % version,
                                      html, re.I)
                    if match:
                        ul = html[match.end(0):html.find("</ul", match.end(0))]
                        lis = re.findall("(<li[^>]*>(.+)</li\\s*>)+", ul, re.I)
                        items = [re.sub("<[^>]+>", "", x[1]) for x in lis]
                        items = list(map(html_parser.HTMLParser().unescape, items))
                        changes = "\n".join("- " + i.strip() for i in items)
                        if changes:
                            title = match.group(1)
                            changes = "Changes in %s\n\n%s" % (title, changes)
                except Exception:
                    logger.exception("Failed to read changelog.")
                url = urllib.parse.urljoin(conf.DownloadURL, link)
                result = (version, url, changes)
    except Exception:
        logger.exception("Failed to retrieve new version from %s.",
                         conf.DownloadURL)
        result = None
    update_window = None
    if callback:
        callback(result)
    return result


def download_and_install(url):
    """Downloads and launches the specified file."""
    global update_window, url_opener
    try:
        is_cancelled = False
        parent = wx.GetApp().TopWindow
        filename, tmp_dir = os.path.basename(url), tempfile.mkdtemp()
        dlg_progress = \
            controls.ProgressWindow(parent, "Downloading %s" % filename)
        dlg_progress.SetGaugeForegroundColour(conf.GaugeColour)
        dlg_progress.Position = (
            parent.Position.x + parent.Size.width  - dlg_progress.Size.width,
            parent.Position.y + parent.Size.height - dlg_progress.Size.height)
        update_window = dlg_progress
        urlfile = url_opener.open(url)
        filepath = os.path.join(tmp_dir, filename)
        logger.info("Downloading %s to %s.", url, filepath)
        filesize = int(urlfile.headers.get("content-length", sys.maxsize))
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
            logger.info("Upgrade cancelled, erasing temporary file %s.", filepath)
            util.try_ignore(os.unlink, filepath)
            util.try_ignore(os.rmdir,  tmp_dir)
        else:
            logger.info("Successfully downloaded %s of %s.",
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
    except Exception:
        logger.exception("Failed to download new version from %s.", url)


def take_screenshot(fullscreen=True):
    """Returns a wx.Bitmap screenshot taken of fullscreen or program window."""
    wx.YieldIfNeeded()
    if fullscreen:
        rect = wx.Rect(0, 0, *wx.DisplaySize())
    else:
        window = wx.GetApp().TopWindow
        rect   = window.GetRect()

        # adjust widths for Linux (figured out by John Torres 
        # http://article.gmane.org/gmane.comp.python.wxpython/67327)
        if "linux" in sys.platform:
            client_x, client_y = window.ClientToScreen((0, 0))
            border_width       = client_x - rect.x
            title_bar_height   = client_y - rect.y
            rect.width        += (border_width * 2)
            rect.height       += title_bar_height + border_width

    dc = wx.ScreenDC()
    dc.Clear()
    bmp = wx.Bitmap(rect.width, rect.height)
    dc_bmp = wx.MemoryDC()
    dc_bmp.SelectObject(bmp)
    dc_bmp.Blit(0, 0, rect.width, rect.height, dc, rect.x, rect.y)
    dc_bmp.SelectObject(wx.NullBitmap)
    del dc, dc_bmp
    if bmp.Depth > 24:
        try: # Drop alpha channel
            img = bmp.ConvertToImage()
            img.ClearAlpha()
            bmp = img.ConvertToBitmap()
        except Exception: pass
    return bmp


def send_report(content, type, screenshot=""):
    """
    Posts feedback or error data to the report web service.

    @return    True on success, False on failure
    """
    global url_opener
    result = False
    try:
        data = {"content": content.encode("utf-8"), "type": type,
                "screenshot": util.b64encode(screenshot),
                "version": "%s-%s" % (conf.Version, get_install_type())}
        url_opener.open(conf.ReportURL, urllib.parse.urlencode(data).encode("utf-8"))
        logger.info("Sent %s report to %s (%s).", type, conf.ReportURL, content)
        result = True
    except Exception:
        logger.exception("Failed to send %s to %s.", type, conf.ReportURL)
    return result


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
    nums = [int(re.sub("[^\\d]", "", x)) for x in v.split(".")][::-1]
    nums[0:0] = [0] * (3 - len(nums)) # Zero-pad if version like 1.4 or just 2
    # Like 1.4a: subtract 1 and add fractions to last number to make < 1.4
    if re.findall("\\d+([\\D]+)$", v):
        ords = [ord(x) for x in re.findall("\\d+([\\D]+)$", v)[0]]
        nums[0] += sum(x / (65536. ** (i + 1)) for i, x in enumerate(ords)) - 1
    return sum((x * 100 ** i) for i, x in enumerate(nums))



class FeedbackDialog(wx_accel.AutoAcceleratorMixIn, wx.Dialog):
    """
    A non-modal dialog for sending feedback with an optional screenshot,
    stays on top of parent.
    """
    THUMB_SIZE = (250, 150)

    """
    Dialog for entering a message to send to author, can include a screenshot.
    """
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent=parent, title="Send feedback",
                          style=wx.CAPTION | wx.CLOSE_BOX |
                                wx.FRAME_FLOAT_ON_PARENT | wx.RESIZE_BORDER)
        wx_accel.AutoAcceleratorMixIn.__init__(self)
        self.MinSize = (460, 460)

        panel = self.panel = wx.Panel(self)

        label = self.label_message = wx.StaticText(panel,
            label="Opinions, ideas for improvement, problems?")
        label_info = self.label_info = wx.StaticText(panel,
            label="For reply, include a contact e-mail.")
        ColourManager.Manage(label_info, "ForegroundColour", wx.SYS_COLOUR_HIGHLIGHT)

        edit = self.edit_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE)

        bmp = self.bmp = wx.StaticBitmap(panel, size=self.THUMB_SIZE)
        bmp.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        bmp.ToolTip = "Click to show full size preview"
        self.button_ok = wx.Button(panel, label="&Confirm")
        self.button_ok.ToolTip = "Confirm message before sending"
        self.button_cancel = wx.Button(panel, label="Cancel", id=wx.ID_CANCEL)
        self.cb_fullscreen = wx.CheckBox(panel, label="&Full screen")
        self.button_saveimage = wx.Button(panel, label="Save &image")
        self.button_saveimage.ToolTip = "Save screenshot to file."
        self.cb_bmp = wx.CheckBox(panel, label="Include &screenshot")

        self.Sizer       = wx.BoxSizer(wx.VERTICAL)
        sizer            = self.panel.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_upper      = wx.BoxSizer(wx.HORIZONTAL)
        sizer_lower      = wx.BoxSizer(wx.HORIZONTAL)
        sizer_controls   = wx.BoxSizer(wx.VERTICAL)
        sizer_buttons    = wx.BoxSizer(wx.HORIZONTAL)
        sizer_imagectrls = wx.BoxSizer(wx.VERTICAL)

        sizer_buttons.Add(self.button_ok, border=5, flag=wx.RIGHT)
        sizer_buttons.Add(self.button_cancel)

        sizer_imagectrls.Add(self.button_saveimage, border=8,  flag=wx.BOTTOM)
        sizer_imagectrls.Add(self.cb_fullscreen,    border=20, flag=wx.BOTTOM)

        sizer_controls.Add(sizer_buttons)
        sizer_controls.AddStretchSpacer()
        sizer_controls.Add(sizer_imagectrls)
        sizer_controls.Add(self.cb_bmp, border=5, flag=wx.TOP)

        sizer_upper.Add(label, flag=wx.GROW)
        sizer_upper.AddStretchSpacer()
        sizer_upper.Add(label_info)
        sizer_lower.Add(bmp, border=10, flag=wx.RIGHT)
        sizer_lower.AddStretchSpacer()
        sizer_lower.Add(sizer_controls, flag=wx.GROW)

        sizer.Add(sizer_upper, border=8, flag=wx.GROW | wx.ALL)
        sizer.Add(edit, proportion=2, border=8,
                  flag=wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.GROW)
        sizer.Add(sizer_lower, border=8, flag=wx.LEFT | wx.RIGHT |
                  wx.BOTTOM | wx.GROW)
        self.Sizer.Add(panel, proportion=1, flag=wx.GROW)

        self.Bind(wx.EVT_CHECKBOX,  self.OnToggleFullScreen, self.cb_fullscreen)
        self.Bind(wx.EVT_CHECKBOX,  self.OnToggleScreenshot, self.cb_bmp)
        self.Bind(wx.EVT_BUTTON,    self.OnSend,             self.button_ok)
        self.Bind(wx.EVT_BUTTON,    self.OnCancel,           self.button_cancel)
        self.Bind(wx.EVT_BUTTON,    self.OnSaveImage,        self.button_saveimage)
        bmp.Bind (wx.EVT_LEFT_DOWN, self.OnClickScreenshot)
        self.Bind(wx.EVT_CLOSE,     self.OnCancel)

        self.SetScreenshot(None)
        self.Fit()
        self.Show()


    def _SendReport(self, report_kwargs):
        """Tries to send report in the background, shows result message."""
        try_count = 0
        while try_count < 3 and not send_report(**report_kwargs):
            try_count += 1
        if try_count < 3:
            self.edit_text.Value = ""
            self.edit_text.SetFocus()
            self.SetScreenshot(None)
            text, style = "Feedback sent", wx.OK
        else:
            text = "Could not post feedback. Connection problems?"
            style = wx.OK | wx.ICON_WARNING
        guibase.status()
        wx.CallLater(500, wx.MessageBox, text, self.Title, style)


    def SetScreenshot(self, bitmap=None):
        """Sets the screenshot bitmap, if any."""
        self.screenshot = bitmap
        thumb = wx.NullBitmap
        if bitmap:
            img = bitmap.ConvertToImage()
            img = img.Rescale(*self.THUMB_SIZE)
            # wx.BitmapFromImage/img.ConvertToBitmap can yield buggy bitmaps
            thumb = wx.Bitmap.FromBuffer(img.Width, img.Height, img.GetData())
        self.cb_bmp.Value = bool(bitmap)
        self.bmp.SetBitmap(thumb)
        self.bmp.Show(self.cb_bmp.Value)
        self.button_saveimage.Show(self.cb_bmp.Value)
        self.cb_fullscreen.Show(self.cb_bmp.Value)


    def OnToggleScreenshot(self, event):
        """Handler for toggling screenshot on/off."""
        if self.cb_bmp.Value:
            self.SetScreenshot(take_screenshot(self.cb_fullscreen.Value))
        self.bmp.Show(self.cb_bmp.Value)
        self.button_saveimage.Show(self.cb_bmp.Value)
        self.cb_fullscreen.Show(self.cb_bmp.Value)
        self.Layout()


    def OnToggleFullScreen(self, event):
        """Handler for toggling screenshot size from fullscreen to window."""
        self.SetScreenshot(take_screenshot(self.cb_fullscreen.Value))


    def OnClickScreenshot(self, event):
        """Handler for clicking the screenshot, shows the image in a splash screen."""
        a = wx.GetApp()
        wx.adv.SplashScreen(self.screenshot, wx.adv.SPLASH_CENTRE_ON_SCREEN,
                            milliseconds=0, parent=a.TopWindow, style=wx.BORDER_NONE)


    def OnSend(self, event):
        """
        Handler for clicking to send feedback, hides the dialog and posts data
        to feedback web service.
        """
        text = self.edit_text.Value.strip()
        text_short = text[:500] + ".." if len(text) > 500 else text
        bmp = self.cb_bmp.Value and self.screenshot
        if text:
            ok = wx.MessageBox("Send the entered text%s? For reply, include "
                               "a contact e-mail in the text.\n\n\"%s\"" % (
                               " and screenshot" if bmp else "", text_short),
                               self.Title, wx.OK | wx.CANCEL | 
                               wx.ICON_INFORMATION)
            text = (text if wx.OK == ok else "")
        if text:
            self.Hide()
            kwargs = {"type": "feedback", "content": text}
            if bmp: kwargs["screenshot"] = util.img_wx_to_raw(bmp)
            guibase.status("Submitting feedback..")
            wx.CallAfter(self._SendReport, kwargs)


    def OnSaveImage(self, event):
        """
        Handler for clicking to save screenshot, opens a file dialog and
        saves the image file.
        """
        now = datetime.datetime.now().strftime("%Y-%m-%d %H%M")
        wildcard = "Portable Network Graphics (*.png)" \
                   "|*.png|Windows bitmap (*.bmp)|*.bmp"
        dialog = wx.FileDialog(parent=self, message="Save screenshot",
            defaultFile="%s screenshot %s" % (conf.Title, now),
            wildcard=wildcard,
            style=wx.FD_OVERWRITE_PROMPT | wx.FD_SAVE | wx.RESIZE_BORDER)
        if wx.ID_OK == dialog.ShowModal() and dialog.GetPath():
            format = (wx.BITMAP_TYPE_PNG, wx.BITMAP_TYPE_BMP)[dialog.FilterIndex]
            filename = controls.get_dialog_path(dialog)
            def callback():
                try:
                    self.screenshot.SaveFile(filename, format)
                    guibase.status("Saved screenshot %s.", filename, log=True)
                    util.start_file(filename)
                except Exception:
                    base = "Error saving screenshot file"
                    guibase.status("%s %s.", base, filename)
                    logger.exception("%s %s", base, filename)
                    msg = base + "\n\n%s" % filename
                    wx.MessageBox(msg, self.Title, wx.OK | wx.ICON_WARNING)
            wx.CallLater(10, callback)


    def OnCancel(self, event):
        """Handler for cancelling sending feedback, hides the dialog."""
        self.Hide()


url_opener.addheaders = [("User-agent", "%s %s (%s) (Python %s; wx %s; %s)" % (
    conf.Title, conf.Version, get_install_type(),
    ".".join(map(str, sys.version_info[:3])),
    ".".join(map(str, wx.VERSION[:4])),
    platform.platform() + ("-x64" if platform.machine().endswith("64") else "")
))]
