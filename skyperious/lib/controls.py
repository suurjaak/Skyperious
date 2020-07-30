# -*- coding: utf-8 -*-
"""
Stand-alone GUI components for wx:

- BusyPanel(wx.Window):
  Primitive hover panel with a message that stays in the center of parent
  window.

- ColourManager(object):
  Updates managed component colours on Windows system colour change.

- EntryDialog(wx.Dialog):
  Non-modal text entry dialog with auto-complete dropdown, appears in lower
  right corner.

- HintedTextCtrl(wx.TextCtrl):
  A text control with a hint text shown when no value, hidden when focused.

- NonModalOKDialog(wx.Dialog):
  A simple non-modal dialog with an OK button, stays on top of parent.

- NoteButton(wx.Panel, wx.Button):
  A large button with a custom icon, main label, and additional note.
  Inspired by wx.CommandLinkButton, which does not support custom icons
  (at least not of wx 2.9.4).

- PropertyDialog(wx.Dialog):
  Dialog for displaying an editable property grid. Supports strings,
  integers, booleans, and tuples interpreted as wx.Size.

- ProgressWindow(wx.Dialog):
  A simple non-modal ProgressDialog, stays on top of parent frame.

- RangeSlider(wx.Panel):
  A horizontal slider with two markers for selecting a value range. Supports
  numeric and date/time values.

- ScrollingHtmlWindow(wx.html.HtmlWindow):
  HtmlWindow that remembers its scroll position on resize and append.
    
- SearchableStyledTextCtrl(wx.Panel):
  A wx.stc.StyledTextCtrl with a search bar that appears on demand, top or
  bottom of the control.
  Search bar has a text box, next-previous buttons, search options and a
  close button. Next/previous buttons set search direction: after clicking
  "Previous", pressing Enter in search box searches upwards.

- SortableListView(wx.ListView, wx.lib.mixins.listctrl.ColumnSorterMixin):
  A sortable list view that can be batch-populated, autosizes its columns,
  supports clipboard copy.

- SortableUltimateListCtrl(wx.lib.agw.ultimatelistctrl.UltimateListCtrl,
                           wx.lib.mixins.listctrl.ColumnSorterMixin):
  A sortable list view that can be batch-populated, autosizes its columns,
  supports clipboard copy.

- SQLiteTextCtrl(wx.stc.StyledTextCtrl):
  A StyledTextCtrl configured for SQLite syntax highlighting.

- TabbedHtmlWindow(wx.Panel):
  wx.html.HtmlWindow with tabs for different content pages.
    
- TextCtrlAutoComplete(wx.TextCtrl):
  A text control with autocomplete using a dropdown list of choices. During
  typing, the first matching choice is appended to textbox value, with the
  appended text auto-selected.
  If wx.PopupWindow is not available (Mac), behaves like a common TextCtrl.
  Based on TextCtrlAutoComplete by Michele Petrazzo, from a post
  on 09.02.2006 in wxPython-users thread "TextCtrlAutoComplete",
  http://wxpython-users.1045709.n5.nabble.com/TextCtrlAutoComplete-td2348906.html

- def BuildHistogram(data, barsize=(3, 30), colour="#2d8b57", maxval=None):
  Paints and returns (wx.Bitmap, rects) with histogram plot from data.

------------------------------------------------------------------------------
This file is part of Skyperious - Skype chat history tool.
Released under the MIT License.

@author      Erki Suurjaak
@created     13.01.2012
@modified    26.07.2020
------------------------------------------------------------------------------
"""
import ast
import collections
import copy
import datetime
import functools
import locale
import operator
import os
import re
import sys
import wx
import wx.html
import wx.lib.agw.flatnotebook
import wx.lib.agw.gradientbutton
import wx.lib.agw.labelbook
import wx.lib.agw.ultimatelistctrl
try: # ShapedButton requires PIL, might not be installed
    import wx.lib.agw.shapedbutton
except Exception: pass 
import wx.lib.embeddedimage
import wx.lib.gizmos
import wx.lib.mixins.listctrl
import wx.lib.newevent
import wx.lib.wordwrap
import wx.stc


# Convenience methods for creating a wx.Brush and wx.Pen or returning cached.
BRUSH = lambda c,      s=wx.BRUSHSTYLE_SOLID: wx.TheBrushList.FindOrCreateBrush(c,    s)
PEN   = lambda c, w=1, s=wx.PENSTYLE_SOLID:   wx.ThePenList  .FindOrCreatePen  (c, w, s)



class KEYS(object):
    """Keycode groupings, includes numpad keys."""
    UP         = wx.WXK_UP,       wx.WXK_NUMPAD_UP
    DOWN       = wx.WXK_DOWN,     wx.WXK_NUMPAD_DOWN
    LEFT       = wx.WXK_LEFT,     wx.WXK_NUMPAD_LEFT
    RIGHT      = wx.WXK_RIGHT,    wx.WXK_NUMPAD_RIGHT
    PAGEUP     = wx.WXK_PAGEUP,   wx.WXK_NUMPAD_PAGEUP
    PAGEDOWN   = wx.WXK_PAGEDOWN, wx.WXK_NUMPAD_PAGEDOWN
    ENTER      = wx.WXK_RETURN,   wx.WXK_NUMPAD_ENTER
    INSERT     = wx.WXK_INSERT,   wx.WXK_NUMPAD_INSERT
    DELETE     = wx.WXK_DELETE,   wx.WXK_NUMPAD_DELETE
    HOME       = wx.WXK_HOME,     wx.WXK_NUMPAD_HOME
    END        = wx.WXK_END,      wx.WXK_NUMPAD_END
    SPACE      = wx.WXK_SPACE,    wx.WXK_NUMPAD_SPACE
    BACKSPACE  = wx.WXK_BACK,
    TAB        = wx.WXK_TAB,      wx.WXK_NUMPAD_TAB
    ESCAPE     = wx.WXK_ESCAPE,

    ARROW      = UP + DOWN + LEFT + RIGHT
    PAGING     = PAGEUP + PAGEDOWN
    NAVIGATION = ARROW + PAGING + HOME + END + TAB
    COMMAND    = ENTER + INSERT + DELETE + SPACE + BACKSPACE + ESCAPE

    NAME_CTRL  = "Cmd" if "darwin" == sys.platform else "Ctrl"



class BusyPanel(wx.Window):
    """
    Primitive hover panel with a message that stays in the center of parent
    window.
    """
    FOREGROUND_COLOUR = wx.WHITE
    BACKGROUND_COLOUR = wx.Colour(110, 110, 110, 255)
    REFRESH_INTERVAL  = 500

    def __init__(self, parent, label):
        wx.Window.__init__(self, parent)
        self.Hide() # Avoid initial flicker

        timer = self._timer = wx.Timer(self)

        label = wx.StaticText(self, label=label, style=wx.ST_ELLIPSIZE_END)

        self.BackgroundColour  = self.BACKGROUND_COLOUR
        label.ForegroundColour = self.FOREGROUND_COLOUR

        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.Sizer.Add(label, border=15, flag=wx.ALL | wx.ALIGN_CENTER_HORIZONTAL)
        self.Fit()

        maxsize = [self.Parent.Size.width / 2, self.Parent.Size.height * 2 / 3]
        self.Size = tuple(min(a, b) for a, b in zip(self.Size, maxsize))

        self.Bind(wx.EVT_PAINT, lambda e: (e.Skip(), self.Refresh()))
        self.Bind(wx.EVT_TIMER, lambda e: (e.Skip(), self.Refresh()))
        self.Bind(wx.EVT_WINDOW_DESTROY, self._OnDestroy)

        self.Layout()
        self.CenterOnParent()
        self.Show()
        parent.Refresh()
        wx.Yield()
        timer.Start(self.REFRESH_INTERVAL)


    def _OnDestroy(self, event):
        event.Skip()
        try: self._timer.Stop()
        except Exception: pass


    def Close(self):
        try: self.Destroy(); self.Parent.Refresh()
        except Exception: pass



class ColourManager(object):
    """
    Updates managed component colours on Windows system colour change.
    """
    colourcontainer   = None
    colourmap         = {} # {colour name in container: wx.SYS_COLOUR_XYZ}
    darkcolourmap     = {} # {colour name in container: wx.SYS_COLOUR_XYZ}
    darkoriginals     = {} # {colour name in container: original value}
    # {ctrl: (prop name: colour name in container)}
    ctrls             = collections.defaultdict(dict)


    @classmethod
    def Init(cls, window, colourcontainer, colourmap, darkcolourmap):
        """
        Hooks WM_SYSCOLORCHANGE on Windows, updates colours in container
        according to map.

        @param   window           application main window
        @param   colourcontainer  object with colour attributes
        @param   colourmap        {"attribute": wx.SYS_COLOUR_XYZ}
        @param   darkcolourmap    colours changed if dark background,
                                  {"attribute": wx.SYS_COLOUR_XYZ or wx.Colour}
        """
        cls.colourcontainer = colourcontainer
        cls.colourmap.update(colourmap)
        cls.darkcolourmap.update(darkcolourmap)
        for name in darkcolourmap:
            if not hasattr(colourcontainer, name): continue # for name
            cls.darkoriginals[name] = getattr(colourcontainer, name)

        cls.UpdateContainer()

        # Hack: monkey-patch FlatImageBook with non-hardcoded background
        class HackContainer(wx.lib.agw.labelbook.ImageContainer):
            WHITE_BRUSH = wx.WHITE_BRUSH
            def OnPaint(self, event):
                bgcolour = cls.ColourHex(wx.SYS_COLOUR_WINDOW)
                if "#FFFFFF" != bgcolour: wx.WHITE_BRUSH = BRUSH(bgcolour)
                try: result = HackContainer.__base__.OnPaint(self, event)
                finally: wx.WHITE_BRUSH = HackContainer.WHITE_BRUSH
                return result
        wx.lib.agw.labelbook.ImageContainer = HackContainer

        # Hack: monkey-patch TreeListCtrl with working Colour properties
        wx.lib.gizmos.TreeListCtrl.BackgroundColour = property(
            wx.lib.gizmos.TreeListCtrl.GetBackgroundColour,
            wx.lib.gizmos.TreeListCtrl.SetBackgroundColour
        )
        wx.lib.gizmos.TreeListCtrl.ForegroundColour = property(
            wx.lib.gizmos.TreeListCtrl.GetForegroundColour,
            wx.lib.gizmos.TreeListCtrl.SetForegroundColour
        )

        window.Bind(wx.EVT_SYS_COLOUR_CHANGED, cls.OnSysColourChange)


    @classmethod
    def Manage(cls, ctrl, prop, colour):
        """
        Starts managing a control colour property.

        @param   ctrl    wx component
        @param   prop    property name like "BackgroundColour",
                         tries using ("Set" + prop)() if no such property
        @param   colour  colour name in colour container like "BgColour",
                         or system colour ID like wx.SYS_COLOUR_WINDOW
        """
        if not ctrl: return
        cls.ctrls[ctrl][prop] = colour
        cls.UpdateControlColour(ctrl, prop, colour)


    @classmethod
    def OnSysColourChange(cls, event):
        """
        Handler for system colour change, refreshes configured colours
        and updates managed controls.
        """
        event.Skip()
        cls.UpdateContainer()
        cls.UpdateControls()


    @classmethod
    def ColourHex(cls, idx):
        """Returns wx.Colour or system colour as HTML colour hex string."""
        colour = idx if isinstance(idx, wx.Colour) \
                 else wx.SystemSettings.GetColour(idx)
        return colour.GetAsString(wx.C2S_HTML_SYNTAX)


    @classmethod
    def GetColour(cls, colour):
        if isinstance(colour, wx.Colour): return colour
        return wx.Colour(getattr(cls.colourcontainer, colour)) \
               if isinstance(colour, basestring) \
               else wx.SystemSettings.GetColour(colour)


    @classmethod
    def Adjust(cls, colour1, colour2, ratio=0.5):
        """
        Returns first colour adjusted towards second.
        Arguments can be wx.Colour, RGB tuple, colour hex string,
        or wx.SystemSettings colour index.

        @param   ratio    RGB channel adjustment ratio towards second colour
        """
        colour1 = wx.SystemSettings.GetColour(colour1) \
                  if isinstance(colour1, (int, long)) else wx.Colour(colour1)
        colour2 = wx.SystemSettings.GetColour(colour2) \
                  if isinstance(colour2, (int, long)) else wx.Colour(colour2)
        rgb1, rgb2 = tuple(colour1)[:3], tuple(colour2)[:3]
        delta  = tuple(a - b for a, b in zip(rgb1, rgb2))
        result = tuple(a - (d * ratio) for a, d in zip(rgb1, delta))
        result = tuple(min(255, max(0, x)) for x in result)
        return wx.Colour(result)


    @classmethod
    def UpdateContainer(cls):
        """Updates configuration colours with current system theme values."""
        for name, colourid in cls.colourmap.items():
            setattr(cls.colourcontainer, name, cls.ColourHex(colourid))

        if "#FFFFFF" != cls.ColourHex(wx.SYS_COLOUR_WINDOW):
            for name, colourid in cls.darkcolourmap.items():
                setattr(cls.colourcontainer, name, cls.ColourHex(colourid))
        else:
            for name, value in cls.darkoriginals.items():
                setattr(cls.colourcontainer, name, value)


    @classmethod
    def UpdateControls(cls):
        """Updates all managed controls."""
        for ctrl, props in cls.ctrls.items():
            if not ctrl: # Component destroyed
                cls.ctrls.pop(ctrl)
                continue # for ctrl, props

            for prop, colour in props.items():
                cls.UpdateControlColour(ctrl, prop, colour)


    @classmethod
    def UpdateControlColour(cls, ctrl, prop, colour):
        """Sets control property or invokes "Set" + prop."""
        mycolour = cls.GetColour(colour)
        if hasattr(ctrl, prop):
            setattr(ctrl, prop, mycolour)
        elif hasattr(ctrl, "Set" + prop):
            getattr(ctrl, "Set" + prop)(mycolour)



class HintedTextCtrl(wx.TextCtrl):
    """
    A text control with a hint text shown when no value, hidden when focused.
    Fires EVT_TEXT_ENTER event on text change.
    Clears entered value on pressing Escape.
    """


    def __init__(self, parent, hint="", escape=True, adjust=False, **kwargs):
        """
        @param   hint    hint text shown when no value and no focus
        @param   escape  whether to clear entered value on pressing Escape
        @param   adjust  whether to adjust hint colour more towards background
        """
        super(HintedTextCtrl, self).__init__(parent, **kwargs)
        self._text_colour = ColourManager.GetColour(wx.SYS_COLOUR_BTNTEXT)
        self._hint_colour = ColourManager.GetColour(wx.SYS_COLOUR_GRAYTEXT) if not adjust else \
                            ColourManager.Adjust(wx.SYS_COLOUR_GRAYTEXT, wx.SYS_COLOUR_WINDOW)
        self.SetForegroundColour(self._text_colour)

        self._hint = hint
        self._adjust = adjust
        self._hint_on = False # Whether textbox is filled with hint value
        self._ignore_change = False # Ignore value change
        if not self.Value:
            self.Value = self._hint
            self.SetForegroundColour(self._hint_colour)
            self._hint_on = True

        self.Bind(wx.EVT_SYS_COLOUR_CHANGED,  self.OnSysColourChange)
        self.Bind(wx.EVT_SET_FOCUS,           self.OnFocus)
        self.Bind(wx.EVT_KILL_FOCUS,          self.OnFocus)
        self.Bind(wx.EVT_TEXT,                self.OnText)
        if escape: self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)


    def OnFocus(self, event):
        """
        Handler for focusing/unfocusing the control, shows/hides hint.
        """
        event.Skip() # Allow to propagate to parent, to show having focus
        self._ignore_change = True
        if self and self.FindFocus() is self:
            if self._hint_on:
                self.SetForegroundColour(self._text_colour)
                wx.TextCtrl.ChangeValue(self, "")
                self._hint_on = False
            self.SelectAll()
        elif self:
            if self._hint and not self.Value:
                # Control has been unfocused, set and colour hint
                wx.TextCtrl.ChangeValue(self, self._hint)
                self.SetForegroundColour(self._hint_colour)
                self._hint_on = True
        wx.CallAfter(setattr, self, "_ignore_change", False)


    def OnKeyDown(self, event):
        """Handler for keypress, empties text on escape."""
        event.Skip()
        if event.KeyCode in [wx.WXK_ESCAPE] and self.Value:
            self.Value = ""
            evt = wx.CommandEvent(wx.wxEVT_COMMAND_TEXT_ENTER, self.Id)
            evt.EventObject = self
            evt.String = self.Value
            wx.PostEvent(self, evt)


    def OnText(self, event):
        """Handler for text change, fires TEXT_ENTER event."""
        event.Skip()
        if self._ignore_change: return
        evt = wx.CommandEvent(wx.wxEVT_COMMAND_TEXT_ENTER, self.Id)
        evt.SetEventObject(self)
        evt.SetString(self.Value)
        wx.PostEvent(self, evt)


    def OnSysColourChange(self, event):
        """Handler for system colour change, updates text colour."""
        event.Skip()
        self._text_colour = ColourManager.GetColour(wx.SYS_COLOUR_BTNTEXT)
        self._hint_colour = ColourManager.GetColour(wx.SYS_COLOUR_GRAYTEXT) if not self._adjust else \
                            ColourManager.Adjust(wx.SYS_COLOUR_GRAYTEXT, wx.SYS_COLOUR_WINDOW)
        def after():
            if not self: return
            colour = self._hint_colour if self._hint_on else self._text_colour
            self.SetForegroundColour(colour)
        wx.CallAfter(after)


    def GetHint(self):
        """Returns the current hint."""
        return self._hint
    def SetHint(self, hint):
        """Sets the hint value."""
        self._hint = hint
        if self._hint_on or not self.Value and not self.HasFocus():
            self._ignore_change = True
            wx.TextCtrl.ChangeValue(self, self._hint)
            self.SetForegroundColour(self._hint_colour)
            self._hint_on = True
            wx.CallAfter(setattr, self, "_ignore_change", False)
    Hint = property(GetHint, SetHint)


    def GetValue(self):
        """
        Returns the current value in the text field, or empty string if filled
        with hint.
        """
        return "" if self._hint_on else wx.TextCtrl.GetValue(self)
    def SetValue(self, value):
        """Sets the value in the text entry field."""
        self._ignore_change = True
        wx.TextCtrl.SetValue(self, value)
        if value or self.FindFocus() is self:
            self.SetForegroundColour(self._text_colour)
            self._hint_on = False
        elif not value and self.FindFocus() is not self:
            wx.TextCtrl.SetValue(self, self._hint)
            self.SetForegroundColour(self._hint_colour)
            self._hint_on = True
        wx.CallAfter(setattr, self, "_ignore_change", False)
    Value = property(GetValue, SetValue)


    def ChangeValue(self, value):
        """Sets the new text control value."""
        self._ignore_change = True
        wx.TextCtrl.ChangeValue(self, value)
        if value or self.FindFocus() is self:
            self.SetForegroundColour(self._text_colour)
            self._hint_on = False
        elif not value and self.FindFocus() is not self:
            wx.TextCtrl.SetValue(self, self._hint)
            self.SetForegroundColour(self._hint_colour)
            self._hint_on = True
        wx.CallAfter(setattr, self, "_ignore_change", False)



class NonModalOKDialog(wx.Dialog):
    """A simple non-modal dialog with an OK button, stays on top of parent."""

    def __init__(self, parent, title, message):
        wx.Dialog.__init__(self, parent=parent, title=title,
                           style=wx.CAPTION | wx.CLOSE_BOX | 
                                 wx.FRAME_FLOAT_ON_PARENT)

        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.label_message = wx.StaticText(self, label=message)
        self.Sizer.Add(self.label_message, proportion=1,
                       border=2*8, flag=wx.ALL)
        sizer_buttons = self.CreateButtonSizer(wx.OK)
        self.Sizer.Add(sizer_buttons, proportion=0, border=8,
                       flag=wx.ALIGN_CENTER_HORIZONTAL | wx.BOTTOM)
        self.Bind(wx.EVT_BUTTON, self.OnClose, id=wx.ID_OK)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Fit()
        self.Layout()
        self.CenterOnParent()
        self.Show()


    def OnClose(self, event):
        self.Close()
        event.Skip()



class EntryDialog(wx.Dialog):
    """
    Non-modal text entry dialog with auto-complete dropdown, appears in lower
    right corner.
    Fires a wx.EVT_COMMAND_ENTER event on pressing Enter or button.
    """
    HIDE_TIMEOUT = 1500 # Milliseconds to wait for hiding after losing focus

    def __init__(self, parent, title, label="", value="", emptyvalue="", tooltip="", choices=[]):
        """
        @param   title       dialog window title
        @param   label       label before text entry, if any
        @param   value       default value of text entry
        @param   emptyvalue  gray text shown in text box if empty and unfocused
        @param   tooltip     tooltip shown for enter button
        """
        style = wx.CAPTION | wx.CLOSE_BOX | wx.STAY_ON_TOP
        wx.Dialog.__init__(self, parent=parent, title=title, style=style)
        self._hider = None # Hider callback wx.Timer

        if label:
            label_text = self._label = wx.StaticText(self, label=label)
        text = self._text = TextCtrlAutoComplete(
            self, description=emptyvalue, size=(200, -1),
            style=wx.TE_PROCESS_ENTER)
        tb = wx.ToolBar(parent=self, style=wx.TB_FLAT | wx.TB_NODIVIDER)

        text.Value = value
        text.SetChoices(choices)
        bmp = wx.ArtProvider.GetBitmap(wx.ART_GO_FORWARD, wx.ART_TOOLBAR,
                                       (16, 16))
        tb.SetToolBitmapSize(bmp.Size)
        tb.AddTool(wx.ID_FIND, "", bitmap=bmp, shortHelp=tooltip)
        tb.Realize()

        self.Bind(wx.EVT_ACTIVATE, self._OnActivate, self)
        text.Bind(wx.EVT_KEY_DOWN, self._OnKeyDown)
        self.Bind(wx.EVT_TEXT_ENTER, self._OnSearch, text)
        self.Bind(wx.EVT_TOOL, self._OnSearch, id=wx.ID_FIND)
        self.Bind(wx.EVT_LIST_DELETE_ALL_ITEMS, self._OnClearChoices, text)

        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_top = wx.BoxSizer(wx.HORIZONTAL)
        if label:
            sizer_top.Add(label_text, flag=wx.ALIGN_CENTER_VERTICAL |
                          wx.LEFT, border=5)
        sizer_top.Add(text, flag=wx.ALIGN_CENTER_VERTICAL | wx.LEFT, border=5)
        sizer_top.Add(tb, flag=wx.LEFT | wx.RIGHT |
                      wx.ALIGN_CENTER_VERTICAL, border=5)
        self.Sizer.Add(sizer_top, flag=wx.GROW | wx.TOP | wx.BOTTOM, border=5)
        self.Fit()
        x, y, w, h = wx.GetClientDisplayRect()
        self.Position = (x + w - self.Size.width, y + h - self.Size.height)
        self._pos_last = self.Position
        self._displayrect_last = (x, y, w, h)



    def Show(self, show=True):
        """Shows or hides the window, and raises it if shown."""
        if show:
            x, y, w, h = wx.GetClientDisplayRect()
            if (x, y, w, h) != self._displayrect_last:     # Display size has
                self.Position = (x + w - self.Size.width,  # changed, move to
                                 y + h - self.Size.height) # screen corner.
                self._displayrect_last = (x, y, w, h)
            self.Raise()
            self._text.SetFocus()
        wx.Dialog.Show(self, show)


    def GetValue(self):
        """Returns the text box value."""
        return self._text.Value
    def SetValue(self, value):
        """Sets the text box value."""
        self._text.Value = value
    Value = property(GetValue, SetValue)


    def SetChoices(self, choices):
        """Sets the auto-complete choices for text box."""
        self._text.SetChoices(choices)


    def _OnActivate(self, event):
        if not (event.Active or self._hider):
            self._hider = wx.CallLater(self.HIDE_TIMEOUT, self.Hide)
        elif event.Active and self._hider: # Kill the hiding timeout, if any
            self._hider.Stop()
            self._hider = None


    def _OnKeyDown(self, event):
        if wx.WXK_ESCAPE == event.KeyCode and not self._text.IsDropDownShown():
            self.Hide()
        event.Skip()


    def _OnSearch(self, event):
        findevent = wx.CommandEvent(wx.wxEVT_COMMAND_ENTER, self.GetId())
        wx.PostEvent(self, findevent)


    def _OnClearChoices(self, event):
        choice = wx.MessageBox("Clear search history?", self.Title,
                               wx.OK | wx.CANCEL | wx.ICON_QUESTION)
        if wx.OK == choice:
            self._text.SetChoices([])



class NoteButton(wx.Panel, wx.Button):
    """
    A large button with a custom icon, main label, and additional note.
    Inspired by wx.CommandLinkButton, which does not support custom icons
    (at least not of wx 2.9.4).
    """

    """Stipple bitmap for focus marquee line."""
    BMP_MARQUEE = None

    def __init__(self, parent, label=wx.EmptyString, note=wx.EmptyString,
                 bmp=wx.NullBitmap, id=-1, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0, name=wx.PanelNameStr):
        wx.Panel.__init__(self, parent, id, pos, size,
                          style | wx.FULL_REPAINT_ON_RESIZE, name)
        self._label = label
        self._note = note
        self._bmp = bmp
        self._bmp_disabled = bmp
        if bmp is not None and bmp.IsOk():
            img = bmp.ConvertToImage().ConvertToGreyscale()
            self._bmp_disabled = wx.Bitmap(img) if img.IsOk() else bmp
        self._hover = False # Whether button is being mouse hovered
        self._press = False # Whether button is being mouse pressed
        self._align = style & (wx.ALIGN_RIGHT | wx.ALIGN_CENTER)
        self._enabled = True
        self._size = self.Size

        # Wrapped texts for both label and note
        self._text_label = None
        self._text_note = None
        # (width, height, lineheight) for wrapped texts in current DC
        self._extent_label = None
        self._extent_note = None

        self._cursor_hover   = wx.Cursor(wx.CURSOR_HAND)
        self._cursor_default = wx.Cursor(wx.CURSOR_DEFAULT)

        self.Bind(wx.EVT_MOUSE_EVENTS,       self.OnMouseEvent)
        self.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.OnMouseCaptureLostEvent)
        self.Bind(wx.EVT_PAINT,              self.OnPaint)
        self.Bind(wx.EVT_SIZE,               self.OnSize)
        self.Bind(wx.EVT_SET_FOCUS,          self.OnFocus)
        self.Bind(wx.EVT_KILL_FOCUS,         self.OnFocus)
        self.Bind(wx.EVT_ERASE_BACKGROUND,   self.OnEraseBackground)
        self.Bind(wx.EVT_KEY_DOWN,           self.OnKeyDown)
        self.Bind(wx.EVT_CHAR_HOOK,          self.OnChar)

        self.SetCursor(self._cursor_hover)
        ColourManager.Manage(self, "ForegroundColour", wx.SYS_COLOUR_BTNTEXT)
        ColourManager.Manage(self, "BackgroundColour", wx.SYS_COLOUR_BTNFACE)
        self.WrapTexts()


    def GetMinSize(self):
        return self.DoGetBestSize()


    def DoGetBestSize(self):
        w = 40 if self.Size.width  < 40 else self.Size.width
        h = 40 if self.Size.height < 40 else self.Size.height
        if self._bmp:
            w = max(w, self._bmp.Size.width  + 20)
            h = max(h, self._bmp.Size.height + 20)
        if self._extent_label:
            h1 = 10 + self._bmp.Size.height + 10
            h2 = 10 + self._extent_label[1] + 10 + self._extent_note[1] + 10
            h  = max(h1, h2)
        return wx.Size(w, h)


    def Draw(self, dc):
        """Draws the control on the given device context."""
        global BRUSH, PEN
        width, height = self.GetClientSize()
        if not self.Shown or not (width > 20 and height > 20):
            return
        if not self._extent_label:
            self.WrapTexts()

        x, y = 10, 10
        if (self._align & wx.ALIGN_RIGHT):
            x = width - 10 - self._bmp.Size.width
        elif (self._align & wx.ALIGN_CENTER):
            x = 10 + (width - self.DoGetBestSize().width) / 2

        dc.Font = self.Font
        dc.Brush = BRUSH(self.BackgroundColour)
        if self.IsThisEnabled():
            dc.TextForeground = self.ForegroundColour
        else:
            graycolour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)
            dc.TextForeground = graycolour
        dc.Pen = PEN(dc.TextForeground)
        dc.Clear()

        is_focused = (self.FindFocus() is self)

        if is_focused:
            # Draw simple border around button
            dc.Brush = wx.TRANSPARENT_BRUSH
            dc.DrawRectangle(0, 0, width, height)

            # Create cached focus marquee
            if not NoteButton.BMP_MARQUEE:
                NoteButton.BMP_MARQUEE = wx.Bitmap(2, 2)
                dc_bmp = wx.MemoryDC()
                dc_bmp.SelectObject(NoteButton.BMP_MARQUEE)
                dc_bmp.Background = wx.Brush(self.BackgroundColour)
                dc_bmp.Clear()
                dc_bmp.Pen = wx.Pen(self.ForegroundColour)
                dc_bmp.DrawPointList([(0, 1), (1, 0)])
                dc_bmp.SelectObject(wx.NullBitmap)

            # Draw focus marquee
            try:
                pen = PEN(dc.TextForeground, 1, wx.PENSTYLE_STIPPLE)
                pen.Stipple, dc.Pen = NoteButton.BMP_MARQUEE, pen
                dc.DrawRectangle(4, 4, width - 8, height - 8)
            except wx.wxAssertionError: # Gtk does not support stippled pens
                brush = BRUSH(dc.TextForeground)
                brush.SetStipple(NoteButton.BMP_MARQUEE)
                dc.Brush = brush
                dc.Pen = wx.TRANSPARENT_PEN
                dc.DrawRectangle(4, 4, width - 8, height - 8)
                dc.Brush = BRUSH(self.BackgroundColour)
                dc.DrawRectangle(5, 5, width - 10, height - 10)
            dc.Pen = PEN(dc.TextForeground)

        if self._press or (is_focused and any(wx.GetKeyState(x) for x in KEYS.SPACE)):
            # Button is being clicked with mouse: create sunken effect
            colours = [(128, 128, 128)] * 2
            lines   = [(1, 1, width - 2, 1), (1, 1, 1, height - 2)]
            dc.DrawLineList(lines, [PEN(wx.Colour(*c)) for c in colours])
            x += 1; y += 1
        elif self._hover and self.IsThisEnabled():
            # Button is being hovered with mouse: create raised effect
            colours  = [(255, 255, 255)] * 2
            if wx.WHITE == self.BackgroundColour:
                colours =  [(158, 158, 158)] * 2
            lines    = [(0, 0, 0, height - 1), (0, 0, width - 1, 0)]
            colours += [(128, 128, 128)] * 2
            lines   += [(1, height - 2, width - 1, height - 2),
                        (width - 2, 1, width - 2, height - 2)]
            colours += [(64, 64, 64)] * 2
            lines   += [(0, height - 1, width, height - 1),
                        (width - 1, 0, width - 1, height - 1)]
            dc.DrawLineList(lines, [PEN(wx.Colour(*c)) for c in colours])

        if self._bmp:
            bmp = self._bmp if self.IsThisEnabled() else self._bmp_disabled
            dc.DrawBitmap(bmp, x, y)

        if self._align & wx.ALIGN_RIGHT:
            x -= 10 + max(self._extent_label[0], self._extent_note[0])
        else:
            x += self._bmp.Size.width + 10

        # Draw label and accelerator key underlines
        dc.Font = wx.Font(dc.Font.PointSize, dc.Font.Family, dc.Font.Style,
                          wx.FONTWEIGHT_BOLD, faceName=dc.Font.FaceName)
        text_label = self._text_label
        if "&" in self._label:
            text_label, h = "", y - 1
            dc.Pen = wx.Pen(dc.TextForeground)
            for line in self._text_label.split("\n"):
                i, chars = 0, ""
                while i < len(line):
                    if "&" == line[i]:
                        i += 1
                        if i < len(line) and "&" != line[i]:
                            extent = dc.GetTextExtent(line[i])
                            extent_all = dc.GetTextExtent(chars)
                            x1, y1 = x + extent_all[0], h + extent[1]
                            dc.DrawLine(x1, y1, x1 + extent[0], y1)
                        elif i < len(line):
                            chars += line[i] # Double ampersand: add as one
                    if i < len(line):
                        chars += line[i]
                    i += 1
                h += self._extent_label[1]
                text_label += chars + "\n"
        dc.DrawText(text_label, x, y)

        # Draw note
        _, label_h = dc.GetMultiLineTextExtent(self._text_label)
        y += label_h + 10
        dc.Font = self.Font
        dc.DrawText(self._text_note, x, y)


    def WrapTexts(self):
        """Wraps button texts to current control size."""
        self._text_label, self._text_note = self._label, self._note

        if not self._label and not self._note:
            self._extent_label = self._extent_note = (0, 0)
            return

        WORDWRAP = wx.lib.wordwrap.wordwrap
        width, height = self.Size
        if width > 20 and height > 20:
            dc = wx.ClientDC(self)
        else: # Not properly sized yet: assume a reasonably fitting size
            dc, width, height = wx.MemoryDC(), 500, 100
            dc.SelectObject(wx.Bitmap(500, 100))
        dc.Font = self.Font
        x = 10 + self._bmp.Size.width + 10
        self._text_note = WORDWRAP(self._text_note, width - 10 - x, dc)
        dc.Font = wx.Font(dc.Font.PointSize, dc.Font.Family, dc.Font.Style,
                          wx.FONTWEIGHT_BOLD, faceName=dc.Font.FaceName)
        self._text_label = WORDWRAP(self._text_label, width - 10 - x, dc)
        self._extent_label = dc.GetMultiLineTextExtent(self._text_label)
        self._extent_note = dc.GetMultiLineTextExtent(self._text_note)


    def OnPaint(self, event):
        """Handler for paint event, calls Draw()."""
        dc = wx.BufferedPaintDC(self)
        self.Draw(dc)


    def OnSize(self, event):
        """Handler for size event, resizes texts and repaints control."""
        event.Skip()
        if event.Size != self._size:
            self._size = event.Size
            wx.CallAfter(lambda: self and (self.WrapTexts(), self.Refresh(),
                         self.InvalidateBestSize(), self.Parent.Layout()))


    def OnFocus(self, event):
        """Handler for receiving/losing focus, repaints control."""
        if self: # Might get called when control already destroyed
            self.Refresh()


    def OnEraseBackground(self, event):
        """Handles the wx.EVT_ERASE_BACKGROUND event."""
        pass # Intentionally empty to reduce flicker.


    def OnKeyDown(self, event):
        """Refreshes display if pressing space (showing sunken state)."""
        if not event.AltDown() and event.UnicodeKey in KEYS.SPACE:
            self.Refresh()
        else: event.Skip()


    def OnChar(self, event):
        """Queues firing button event on pressing space or enter."""
        skip = True
        if not event.AltDown() \
        and event.UnicodeKey in KEYS.SPACE + KEYS.ENTER:
            button_event = wx.PyCommandEvent(wx.EVT_BUTTON.typeId, self.Id)
            button_event.EventObject = self
            wx.CallLater(1, wx.PostEvent, self, button_event)
            skip = False
            self.Refresh()
        if skip: event.Skip()


    def OnMouseEvent(self, event):
        """
        Mouse handler, creates hover/press border effects and fires button
        event on click.
        """
        event.Skip()
        refresh = False
        if event.Entering():
            refresh = True
            self._hover = True
            if self.HasCapture():
                self._press = True
        elif event.Leaving():
            refresh = True
            self._hover = self._press = False
        elif event.LeftDown():
            refresh = True
            self._press = True
            self.CaptureMouse()
        elif event.LeftUp():
            refresh = True
            self._press = False
            if self.HasCapture():
                self.ReleaseMouse()
                if self._hover:
                    btnevent = wx.PyCommandEvent(wx.EVT_BUTTON.typeId, self.Id)
                    btnevent.EventObject = self
                    wx.PostEvent(self, btnevent)
        if refresh:
            self.Refresh()


    def OnMouseCaptureLostEvent(self, event):
        """Handles MouseCaptureLostEvent, updating control UI if needed."""
        self._hover = self._press = False


    def ShouldInheritColours(self):
        return True


    def InheritsBackgroundColour(self):
        return True


    def Disable(self):
        return self.Enable(False)


    def Enable(self, enable=True):
        """
        Enable or disable this control for user input, returns True if the
        control state was changed.
        """
        result = (self._enabled != enable)
        if not result: return result

        self._enabled = enable
        wx.Panel.Enable(self, enable)
        self.Refresh()
        return result
    def IsEnabled(self): return wx.Panel.IsEnabled(self)
    Enabled = property(IsEnabled, Enable)


    def IsThisEnabled(self):
        """Returns the internal enabled state, independent of parent state."""
        if hasattr(wx.Panel, "IsThisEnabled"):
            result = wx.Panel.IsThisEnabled(self)
        else:
            result = self._enabled
        return result


    def GetLabel(self):
        return self._label
    def SetLabel(self, label):
        if label != self._label:
            self._label = label
            self.WrapTexts()
            self.InvalidateBestSize()
            self.Refresh()
    Label = property(GetLabel, SetLabel)


    def SetNote(self, note):
        if note != self._note:
            self._note = note
            self.WrapTexts()
            self.InvalidateBestSize()
            self.Refresh()
    def GetNote(self):
        return self._note
    Note = property(GetNote, SetNote)



class PropertyDialog(wx.Dialog):
    """
    Dialog for displaying an editable property grid. Supports strings,
    integers, booleans, and wx classes like wx.Size interpreted as tuples.
    """


    COLOUR_ERROR = wx.RED

    def __init__(self, parent, title):
        wx.Dialog.__init__(self, parent, title=title,
                          style=wx.CAPTION | wx.CLOSE_BOX | wx.RESIZE_BORDER)
        self.properties = [] # [(name, type, orig_val, default, label, ctrl), ]

        panelwrap = wx.Panel(self)
        panel = self.panel = wx.ScrolledWindow(panelwrap)

        self.Sizer      = wx.BoxSizer(wx.VERTICAL)
        panelwrap.Sizer = wx.BoxSizer(wx.VERTICAL)
        panel.Sizer     = wx.BoxSizer(wx.VERTICAL)
        sizer_items = self.sizer_items = wx.GridBagSizer(hgap=5, vgap=1)

        sizer_buttons = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        button_ok     = next((x.Window for x in sizer_buttons.Children
                              if x.Window and wx.ID_OK == x.Window.Id), None)
        button_reset  = wx.Button(self, label="Restore defaults")
        if button_ok:
            button_ok.Label = "Save"
            button_reset.MoveAfterInTabOrder(button_ok)

        panel.Sizer.Add(sizer_items, proportion=1, border=5, flag=wx.GROW | wx.RIGHT)
        panelwrap.Sizer.Add(panel, proportion=1, border=10, flag=wx.GROW | wx.ALL)
        self.Sizer.Add(panelwrap, proportion=1, flag=wx.GROW)
        sizer_buttons.Insert(min(2, sizer_buttons.ItemCount), button_reset)
        self.Sizer.Add(sizer_buttons, border=10, flag=wx.ALL | wx.ALIGN_RIGHT)

        self.Bind(wx.EVT_BUTTON, self._OnSave,   id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self._OnReset,  button_reset)
        self.Bind(wx.EVT_BUTTON, self._OnReset,  id=wx.ID_APPLY)

        self.MinSize, self.Size = (320, 180), (420, 420)
        ColourManager.Manage(self, "BackgroundColour", wx.SYS_COLOUR_WINDOW)


    def AddProperty(self, name, value, help="", default=None, typeclass=unicode):
        """Adds a property to the frame."""
        row = len(self.properties) * 2
        label = wx.StaticText(self.panel, label=name)
        if bool == typeclass:
            ctrl = wx.CheckBox(self.panel)
            ctrl_flag = wx.ALIGN_CENTER_VERTICAL
            label_handler = lambda e: ctrl.SetValue(not ctrl.IsChecked())
        else:
            ctrl = wx.TextCtrl(self.panel, style=wx.BORDER_SIMPLE)
            ctrl_flag = wx.GROW | wx.ALIGN_CENTER_VERTICAL
            label_handler = lambda e: (ctrl.SetFocus(), ctrl.SelectAll())
        tip = wx.StaticText(self.panel, label=help)

        ctrl.Value = self._GetValueForCtrl(value, typeclass)
        ctrl.ToolTip = label.ToolTip = "Value of type %s%s." % (
            typeclass.__name__,
            "" if default is None else ", default %s" % repr(default))
        ColourManager.Manage(tip, "ForegroundColour", wx.SYS_COLOUR_GRAYTEXT)
        tipfont, tipfont.PixelSize = tip.Font, (0, 9)
        tip.Font = tipfont
        tip.Wrap(self.panel.Size[0] - 30)
        for x in (label, tip): x.Bind(wx.EVT_LEFT_UP, label_handler)

        self.sizer_items.Add(label, pos=(row, 0), flag=wx.ALIGN_CENTER_VERTICAL)
        self.sizer_items.Add(ctrl, pos=(row, 1), flag=ctrl_flag)
        self.sizer_items.Add(tip, pos=(row + 1, 0), span=(1, 2),
                             flag=wx.BOTTOM, border=3)
        self.properties.append((name, typeclass, value, default, label, ctrl))


    def Realize(self):
        """Lays out the properties, to be called when adding is completed."""
        self.panel.SetScrollRate(0, 20)
        self.sizer_items.AddGrowableCol(1) # Grow ctrl column


    def GetProperties(self):
        """
        Returns the current legal property values, as [(name, value), ].
        Illegal values are replaced with initial values.
        """
        result = []
        for name, typeclass, orig, default, label, ctrl in self.properties:
            value = self._GetValueForType(ctrl.Value, typeclass)
            result.append((name, orig if value is None else value))
        return result


    def _OnSave(self, event):
        """
        Handler for clicking save, checks values and hides the dialog if all
        ok, highlights errors otherwise.
        """
        all_ok = True
        for name, typeclass, orig, default, label, ctrl in self.properties:
            if self._GetValueForType(ctrl.Value, typeclass) is None:
                all_ok = False
                label.ForegroundColour = ctrl.ForegroundColour = self.COLOUR_ERROR
            else:
                label.ForegroundColour = ctrl.ForegroundColour = self.ForegroundColour
        event.Skip() if all_ok else self.Refresh()


    def _OnReset(self, event):
        """Handler for clicking reset, restores default values if available."""
        for name, typeclass, orig, default, label, ctrl in self.properties:
            if default is not None:
                ctrl.Value = self._GetValueForCtrl(default, typeclass)
            if self.COLOUR_ERROR == ctrl.ForegroundColour:
                label.ForegroundColour = ctrl.ForegroundColour = self.ForegroundColour
        self.Refresh()


    def _GetValueForType(self, value, typeclass):
        """Returns value in type expected, or None on failure."""
        try:
            result = typeclass(value)
            if isinstance(result, (int, long)) and result < 0:
                raise ValueError() # Reject negative numbers
            isinstance(result, basestring) and result.strip()[0] # Reject empty
            return result
        except Exception:
            return None


    def _GetValueForCtrl(self, value, typeclass):
        """Returns the value in type suitable for appropriate wx control."""
        value = tuple(value) if isinstance(value, list) else value
        if isinstance(value, tuple):
            value = tuple(str(x) if isinstance(x, unicode) else x for x in value)
        return "" if value is None else value \
               if isinstance(value, (basestring, bool)) else unicode(value)



class ProgressWindow(wx.Dialog):
    """
    A simple non-modal ProgressDialog, stays on top of parent frame.
    """

    def __init__(self, parent, title, message="", maximum=100, cancel=True,
                 style=wx.CAPTION | wx.CLOSE_BOX | wx.FRAME_FLOAT_ON_PARENT):
        wx.Dialog.__init__(self, parent=parent, title=title, style=style)
        self._is_cancelled = False

        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        panel = self._panel = wx.Panel(self)
        sizer = self._panel.Sizer = wx.BoxSizer(wx.VERTICAL)

        label = self._label_message = wx.StaticText(panel, label=message)
        sizer.Add(label, border=2*8, flag=wx.LEFT | wx.TOP)
        gauge = self._gauge = wx.Gauge(panel, range=maximum, size=(300,-1),
                              style=wx.GA_HORIZONTAL | wx.PD_SMOOTH)
        sizer.Add(gauge, border=2*8,
                  flag=wx.LEFT | wx.RIGHT | wx.TOP | wx.GROW)
        gauge.Value = 0
        if cancel:
            self._button_cancel = wx.Button(self._panel, id=wx.ID_CANCEL)
            sizer.Add(self._button_cancel, border=8,
                      flag=wx.TOP | wx.BOTTOM | wx.ALIGN_CENTER_HORIZONTAL)
            self.Bind(wx.EVT_BUTTON, self.OnCancel, self._button_cancel)
            self.Bind(wx.EVT_CLOSE, self.OnCancel)
        else:
            sizer.Add((8, 8))

        self.Sizer.Add(panel, flag=wx.GROW)
        self.Fit()
        self.Layout()
        self.Refresh()
        self.Show()


    def Update(self, value, message=None):
        """
        Updates the progressbar value, and message if given.

        @return  False if dialog was cancelled by user, True otherwise
        """
        if message is not None:
            self._label_message.Label = message
        self._gauge.Value = value
        self.Refresh()
        return not self._is_cancelled


    def OnCancel(self, event):
        """
        Handler for cancelling the dialog, hides the window.
        """
        self._is_cancelled = True
        self.Hide()


    def SetGaugeForegroundColour(self, colour):
        self._gauge.ForegroundColour = colour



class RangeSlider(wx.Panel):
    """
    A horizontal slider with two markers for selecting a value range. Supports
    numeric and date/time values. Fires a wx.EVT_SLIDER event on value change.
    Disabling MARKER_LABEL_SHOW will skip drawing marker label area.
    """
    BAR_ARROW_BG_COLOUR     = wx.Colour(212, 208, 200)
    BAR_ARROW_FG_COLOUR     = wx.Colour(0,     0,   0)
    BAR_COLOUR1             = wx.Colour(255, 255, 255) # Scrollbar buttons background
    BAR_COLOUR2             = wx.Colour(162, 162, 162) # gradient start and end
    BAR_HL_COLOUR           = wx.Colour(230, 229, 255) # Scrollbar hilite gradient start
    BOX_COLOUR              = wx.Colour(205, 205, 205) # Drawn around range values
    LABEL_COLOUR            = wx.Colour(136, 136, 136)
    SELECTION_LINE_COLOUR   = wx.Colour(68,   68,  68) # Line surrounding selection
    LINE_COLOUR             = wx.Colour(97,   97,  97)
    MARKER_BUTTON_COLOUR    = wx.Colour(102, 102, 102) # Drag button border
    MARKER_BUTTON_BG_COLOUR = wx.Colour(227, 227, 227) # Drag button background
    RANGE_COLOUR            = wx.Colour(185, 185, 255, 128)
    RANGE_DISABLED_COLOUR   = wx.Colour(185, 185, 185, 128)
    TICK_COLOUR             = wx.Colour(190, 190, 190)
    BAR_BUTTON_WIDTH        = 11 # Width of scrollbar arrow buttons
    BAR_HEIGHT              = 11 # Height of scrollbar
    MARKER_BUTTON_WIDTH     = 9  # Width of drag button that appears on hover
    MARKER_BUTTON_HEIGHT    = 16 # Width of drag button that appears on hover
    MARKER_CAPTURE_PADX     = 3  # x-distance from marker where highlight starts
    MARKER_WIDTH            = 5
    RANGE_TOP               = 5  # Vertical start of range area
    RANGE_BOTTOM            = 15 # Vertical end of range area
    RANGE_LABEL_TOP_GAP     = 3  # Upper padding of range label in range area
    RANGE_LABEL_BOTTOM_GAP  = 6  # Lower padding of range label in range area
    SCROLL_STEP             = 5  # Scroll step in pixels
    TICK_HEIGHT             = 5
    TICK_STEP               = 5  # Tick after every xth pixel
    MARKER_LABEL_SHOW       = True # Whether to show marker labels and area


    def __init__(self, parent, id=-1, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0, name=wx.PanelNameStr,
                 rng=None, vals=None, fmt="%Y-%m-%d"):
        """
        Creates a new RangeSlider.

        @param   rng   the value range this control uses, as (min, max). If
                       range and values are left blank, default to a date range
                       of 3 years until now; if only range is blank, it is
                       assigned the values also
        @param   vals  the initial range positions, as (left, right). If values
                       and range are left blank, default to date values 2 and 1
                       years past; if only values are blank, they are assigned
                       the range values
        @param   fmt   format string or function used for formatting label
                       values, see LabelFormat
        """
        wx.Panel.__init__(self, parent, id, pos, size,
                            style | wx.FULL_REPAINT_ON_RESIZE, name)
        ColourManager.Manage(self, "BackgroundColour", wx.SYS_COLOUR_WINDOW)

        # Fill unassigned range and values with other givens, or assign
        # a default date range.
        if not rng and vals:
            rng = vals
        elif not rng:
            now = datetime.datetime.now().date()
            rng = (now - datetime.timedelta(days=3*365), now)
            vals = (now - datetime.timedelta(days=2*365),
                    now - datetime.timedelta(days=1*365), )
        elif not vals:
            vals = rng

        self._rng = list(rng)
        self._vals = list(vals)
        self._vals_prev = [None, None]
        self._fmt = fmt
        if self._vals[0] < self._rng[0]:
            self._vals[0] = self._rng[0]
        if self._vals[1] > self._rng[1]:
            self._vals[1] = self._rng[1]
        # (x,y,w,h) tuples for left and right marker mouse capture areas
        self._capture_areas = [None, None]
        self._mousepos = None # Current mouse position, or None if mouse not in
        self._mousepos_special = False # If last mousepos needed redrawing
        self._dragging_markers = [False, False] # Whether marker is under drag
        self._dragging_scrollbar = False # Whether scrollbar is under drag
        self._marker_xs = [None, None] # [left x, right x]
        self._active_marker = None # Index of the currently hovered marker
        self._cursor_marker_hover    = wx.Cursor(wx.CURSOR_SIZEWE)
        self._cursor_default         = wx.Cursor(wx.CURSOR_DEFAULT)
        self._grip_area = None # Current scrollbar grip area
        self._bar_arrow_areas = None # Scrollbar arrow areas
        self._box_area = None # Current range area
        self._box_gap_areas = [] # [rect padding box_area on a side, ]
        self._bar_area = None # Scrollbar area
        self.SetInitialSize(self.GetMinSize())
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
        self.Bind(wx.EVT_MOUSE_EVENTS, self.OnMouseEvent)
        self.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.OnMouseCaptureLostEvent)


    def GetLabelFormat(self):
        return self._fmt
    def SetLabelFormat(self, label_format):
        self._fmt = label_format
    LabelFormat = property(GetLabelFormat, SetLabelFormat, doc=
        """
        Format string or function used for formatting values. Format strings
        are used as common Python format strings, except for date or time
        values they are given to strftime. Format functions are given a single
        value parameter and are expected to return a string value.
        """
    )


    def GetLeftValue(self):
        return self._vals[0]
    def SetLeftValue(self, value):
        return self.SetValue(wx.LEFT, value)
    LeftValue = property(GetLeftValue, SetLeftValue, doc=
        "The left position value. Cannot get greater than the right value."
    )
    def GetRightValue(self):
        return self._vals[1]
    def SetRightValue(self, value, refresh=True):
        return self.SetValue(wx.RIGHT, value, refresh)
    RightValue = property(GetRightValue, SetRightValue, doc=
        "The right position value. Cannot get smaller than the left value."
    )


    def GetValues(self):
        """
        Returns the chosen left and right values, as a tuple.
        """
        return tuple(self._vals)
    def SetValues(self, left, right, refresh=True):
        """
        Sets both position values. Values will be confined to available
        range, not going beyond the same edge or the other marker. Control
        will be redrawn if value has changed (and `refresh` is not False).
        """
        new_vals = [left, right]
        for i, value in enumerate(new_vals):
            if value is not None and value != self._vals[i]:
                confiners = [(min, max), (max, min)][i]
                limits = (new_vals[1 - i], self._rng[i])
                for confine, limit in zip(confiners, limits):
                    try:    # Confine value between range edge and other marker
                        value = confine(value, limit)
                    except Exception: # Fails if value of new type is being set
                        self._vals[i] = None
                if self._rng[0] is not None \
                and not (self._rng[0] <= value <= self._rng[1]):
                    value = self._rng[0] if value < self._rng[0] \
                            else self._rng[1]
            self._vals_prev[i] = self._vals[i]
            self._vals[i] = value
        if self._vals != self._vals_prev:
            if refresh: self.Refresh()
            wx.PostEvent(self, wx.CommandEvent(wx.EVT_SLIDER.typeId))
    Values = property(GetValues, SetValues, doc=
                      "See `GetValues` and `SetValues`.")


    def GetValue(self, side):
        """
        Returns the position value on the specified side.
        Side is 0 for left, non-0 for right (wx.LEFT and wx.RIGHT fit).
        """
        return self._vals[1 if side else 0]


    def SetValue(self, side, value, refresh=True):
        """
        Sets the position value on the specified side. Value will be confined
        to available range, not going beyond the same edge or the other marker.
        Side is 0 for left, non-0 for right (wx.LEFT and wx.RIGHT fit). Control
        will be redrawn if value has changed (and `refresh` is not False).
        """
        i = 1 if side else 0
        if value is not None and value != self._vals[i]:
            confiners = [(min, max), (max, min)][i]
            limits = (self._vals[1 - i], self._rng[i])
            for confine, limit in zip(confiners, limits):
                try:    # Confine value between range edge and other marker
                    value = confine(value, limit)
                except Exception: # Fails if value of new type is being set
                    self._vals[i] = None
            if self._rng[0] is not None \
            and not (self._rng[0] <= value <= self._rng[1]):
                value = self._rng[0] if value < self._rng[0] else self._rng[1]
        self._vals_prev[i] = self._vals[i]
        self._vals[i] = value
        if self._vals[i] != self._vals_prev[i]:
            if refresh: self.Refresh()
            wx.PostEvent(self, wx.CommandEvent(wx.EVT_SLIDER.typeId))


    def GetRange(self):
        return tuple(self._rng)
    def SetRange(self, left, right, refresh=True):
        #assert value_range, len(value_range) == 2,
        #       type(value_range[0]) == type(value_range[1])
        former_rng = self._rng
        self._rng = list((left, right))
        for i in range(2):
            # Set the value again to confine it inside the new range. If it
            # fails (probably a type change), reset it to range edge.
            self.SetValue(i, self._vals[i])
            if self._vals[i] is None:
                self.SetValue(i, self._rng[i])
        if refresh and former_rng != self._rng:
            self.Refresh()
    Range = property(GetRange, SetRange, doc=
        """
        The current value range of the control. Setting the range as outside of
        current selection causes selection to be reset to range edges.
        """
    )


    def GetMinSize(self):
        best = wx.Size(-1, -1)
        # GetFullTextExtent returns (width, height, descent, leading)
        extent = self.GetFullTextExtent(self.FormatLabel(self._rng[1]))
        # 2.3 provides a bit of space between 2 labels
        best.width  = 2.3 * extent[0]
        # +1 for upper gap plus label height plus optional marker label height,
        # plus all set positions 
        best.height = (1 + (1 + self.MARKER_LABEL_SHOW) * sum(extent[1:3])
                       + self.RANGE_TOP + self.RANGE_LABEL_TOP_GAP
                       + self.RANGE_LABEL_BOTTOM_GAP + self.TICK_HEIGHT
                       + self.BAR_HEIGHT)
        return best


    def OnPaint(self, event):
        dc = wx.BufferedPaintDC(self)
        self.Draw(dc)


    def OnEraseBackground(self, event):
        """Handles the wx.EVT_ERASE_BACKGROUND event."""
        pass # Intentionally empty to reduce flicker.


    def FormatLabel(self, value):
        """Returns the value as given by the current format."""
        formatted = None
        formatter = self._fmt or "%s"
        if callable(formatter):
            formatted = formatter(value)
        elif isinstance(value, (datetime.date, datetime.time)):
            formatted = value.strftime(formatter)
        else:
            if type(self._rng[0]) == int and type(value) == float:
                value = int(value)
            formatted = formatter % value
        return formatted



    def Draw(self, dc):
        global BRUSH, PEN
        width, height = self.GetClientSize()
        if not width or not height:
            return

        dc.Clear()
        if self.Enabled:
            dc.SetTextForeground(self.LABEL_COLOUR)
        else:
            graycolour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)
            dc.SetTextForeground(graycolour)
        if not any(filter(None, self._rng)):
            return

        timedelta_micros = lambda delta: delta.days * 86400 * 1000000 \
                               + delta.seconds * 1000000 + delta.microseconds

        # Clear area and init data
        left_label, right_label = map(self.FormatLabel, self._rng)
        # GetFullTextExtent returns (width, height, descent, leading)
        left_extent  = self.GetFullTextExtent(left_label)
        right_extent = self.GetFullTextExtent(right_label)
        max_extent = right_extent if (right_extent > left_extent) \
                     else left_extent
        range_delta = self._rng[1] - self._rng[0]
        box_top = 2 # 2 for border and gap
        if self.MARKER_LABEL_SHOW:
            box_top += sum(max_extent[1:3])
        selection_top = box_top + self.RANGE_TOP
        selection_height = height - selection_top - self.RANGE_BOTTOM
        self._box_area = wx.Rect(self.BAR_BUTTON_WIDTH, box_top,
                                 width - 2 * self.BAR_BUTTON_WIDTH,
                                 height - box_top - self.BAR_HEIGHT)
        self._box_gap_areas = [
            wx.Rect(0, box_top, self.BAR_BUTTON_WIDTH,
                    height - box_top - self.BAR_HEIGHT), 
            wx.Rect(width - self.BAR_BUTTON_WIDTH, box_top,
                    width, height - box_top - self.BAR_HEIGHT)]
        dc.SetFont(self.GetFont())
        range_colour = self.RANGE_COLOUR if self.Enabled \
                       else self.RANGE_DISABLED_COLOUR

        # Fill background
        dc.SetBrush(BRUSH(self.BackgroundColour))
        dc.SetPen(PEN(self.BackgroundColour))
        dc.DrawRectangle(0, 0, width, height)
        dc.SetPen(PEN(self.BOX_COLOUR))
        dc.DrawLine(0, box_top, width, box_top) # Top line
        #dc.DrawRectangle(-1, box_top, width + 2, height - box_top)

        # Draw current selection background, edge and scrollbar
        self._bar_arrow_areas = None
        if any(filter(None, self._vals)):
            value_rect = wx.Rect(-1, selection_top, -1, selection_height)
            for i in range(2):
                marker_delta = self._vals[i] - self._rng[0]
                range_delta_local = range_delta
                if i and not range_delta \
                and isinstance(self._rng[0], datetime.date):
                    # If date selection and only single day, fill entire area
                    marker_delta = range_delta_local = 1
                elif isinstance(self._vals[i], (datetime.date, datetime.time)):
                    # Cannot divide by timedeltas: convert to microseconds
                    marker_delta = timedelta_micros(marker_delta)
                    range_delta_local = timedelta_micros(range_delta) or 1
                x = self._box_area.x \
                    + self._box_area.width * marker_delta / range_delta_local
                value_rect[2 if i else 0] = (x - value_rect[0]) if i else x
            dc.SetBrush(BRUSH(range_colour))
            dc.SetPen(PEN(range_colour))
            dc.DrawRectangle(*value_rect)
            # Draw scrollbar arrow buttons
            self._bar_area = wx.Rect(
                0, height - self.BAR_HEIGHT, width, self.BAR_HEIGHT
            )
            dc.SetPen(PEN(self.TICK_COLOUR))
            self._bar_arrow_areas = [None, None]
            for i in range(2):
                self._bar_arrow_areas[i] = wx.Rect(
                    self._bar_area.width - self.BAR_BUTTON_WIDTH if i else 0,
                    self._bar_area.y, self.BAR_BUTTON_WIDTH, self.BAR_HEIGHT
                )
                #dc.GradientFillLinear(self._bar_arrow_areas[i],
                #   self.BAR_COLOUR1, self.BAR_COLOUR2, wx.WEST
                #)
                button_colour = self.BAR_ARROW_BG_COLOUR
                if self._mousepos and self._bar_arrow_areas[i].Contains(self._mousepos):
                    button_colour = self.BAR_HL_COLOUR
                dc.SetBrush(BRUSH(button_colour))
                dc.DrawRectangle(*self._bar_arrow_areas[i])
            dc.SetBrush(BRUSH(self.BAR_ARROW_FG_COLOUR))
            dc.SetPen(PEN(self.BAR_ARROW_FG_COLOUR))
            dc.DrawPolygon(((self.BAR_BUTTON_WIDTH / 2 + 1,
                height - self.BAR_HEIGHT / 2 - 3), (
                    self.BAR_BUTTON_WIDTH / 2 + 1, 
                    height - self.BAR_HEIGHT / 2 + 1
                ), (self.BAR_BUTTON_WIDTH / 2 - 1,
                    height - self.BAR_HEIGHT / 2 - 1
                )
            ))
            dc.DrawPolygon(((width - self.BAR_BUTTON_WIDTH / 2 - 2,
                height - self.BAR_HEIGHT / 2 - 3), (
                    width - self.BAR_BUTTON_WIDTH / 2 - 2,
                    height - self.BAR_HEIGHT / 2 + 1
                ), (width - self.BAR_BUTTON_WIDTH / 2,
                    height - self.BAR_HEIGHT / 2 - 1
                )
            ))
            # Draw scrollbar
            bar_rect = self._grip_area = wx.Rect(
                value_rect.x,
                height - self.BAR_HEIGHT,
                value_rect.width,
                self.BAR_HEIGHT - 1 # -1 for box border
            )
            dc.GradientFillLinear(bar_rect, self.BAR_COLOUR1,
                self.BAR_HL_COLOUR if (
                    self._mousepos and self._grip_area.Contains(self._mousepos)
                ) else self.BAR_COLOUR2, wx.SOUTH
            )
            # Draw a few vertical dashes in the scrollbar center
            if bar_rect.width > 12:
                dashes = [(
                    bar_rect.x + bar_rect.width / 2 - 3 + i,
                    bar_rect.y + (3 if i % 2 else 2),
                    bar_rect.x + bar_rect.width / 2 - 3 + i,
                    bar_rect.y + bar_rect.height - (1 if i % 2 else 2)
                ) for i in range(8)]
                pens = [PEN(self.BAR_COLOUR2), PEN(self.BAR_COLOUR1)] * 4
                dc.DrawLineList(dashes, pens)
            # Draw range edges
            edges = [
                # Left edge to selection start
                (0, box_top, value_rect.x, box_top),
                # Selection end to right edge
                (value_rect.x + value_rect.width, box_top, width, box_top),
                # Selection bottom left-right
                (value_rect.x, height - 1, value_rect.x + value_rect.width,
                    height - 1
                ),
            ]
            dc.SetPen(PEN(self.SELECTION_LINE_COLOUR))
            dc.DrawLineList(edges)

        # Draw ticks and main ruler line
        tick_count = self._box_area.width / self.TICK_STEP + 1
        lines = [(
            self._box_area.x + i * self.TICK_STEP,
            height - self.BAR_HEIGHT - self.TICK_HEIGHT,
            self._box_area.x + i * self.TICK_STEP,
            height - self.BAR_HEIGHT
        ) for i in range(tick_count)
        ]
        lines.append(( # Ruler line
            0, height - self.BAR_HEIGHT,
            width - 1, height - self.BAR_HEIGHT
        ))
        dc.SetPen(PEN(self.TICK_COLOUR))
        dc.DrawLineList(lines)

        # Draw labels, determining how many labels can fit comfortably.
        left = (2 + self._box_area.left, selection_top + self.RANGE_LABEL_TOP_GAP)
        labels, label_coords = [left_label], [left]
        label_count = int(width / (max_extent[0] * 4 / 3.0)) # 4/3 is nice padding
        if isinstance(self._rng[0], (datetime.date, datetime.time)):
            value_step = range_delta / (label_count or sys.maxsize)
        else:
            # Should use floats for all numeric values, to get finer precision
            value_step = range_delta / float(label_count)
        # Skip first and last, as left and right are already known.
        for i in range(1, label_count - 1):
            labels.append(self.FormatLabel(self._rng[0] + i * value_step))
            label_coords += [(self._box_area.x + i * self._box_area.width 
                / label_count, selection_top + self.RANGE_LABEL_TOP_GAP)]
        labels.append(right_label)
        label_coords += [(self._box_area.right - right_extent[0],
                          selection_top + self.RANGE_LABEL_TOP_GAP)]
        dc.DrawTextList(labels, label_coords)

        # Draw left and right markers
        marker_labels = [None, None] # [(text, area) * 2]
        marker_draw_order = [0, 1] if self._active_marker == 1 else [1, 0]
        # Draw active marker last, leaving its content on top
        for i in marker_draw_order:
            marker_delta = self._vals[i] - self._rng[0]
            range_delta_local = range_delta
            if i and not range_delta \
            and isinstance(self._rng[0], datetime.date):
                # If date selection and only single day, fill entire area
                marker_delta = range_delta_local = 1
            elif isinstance(self._vals[i], (datetime.date, datetime.time)):
                # Cannot divide by timedeltas: convert to microseconds
                marker_delta = timedelta_micros(marker_delta)
                range_delta_local = timedelta_micros(range_delta) or 1
            x = (self._box_area.x +
                 self._box_area.width * marker_delta / range_delta_local)
            self._marker_xs[i] = x
            label = self.FormatLabel(self._vals[i])
            # GetFullTextExtent returns (width, height, descent, leading)
            label_extent = self.GetFullTextExtent(label)
            # Center label on top of marker. +2 for padding
            label_area = wx.Rect(x - label_extent[0] / 2, 0, 
                label_extent[0] + 2, sum(label_extent[1:2])
            )
            if not self.ClientRect.Contains(label_area):
                # Rest label against the edge if going out of control area
                label_area.x = 1 if (label_area.x < 1) \
                    else (width - label_area.width)
            marker_labels[i] = (label, label_area)

            area = wx.Rect(x - self.MARKER_WIDTH / 2, box_top,
                self.MARKER_WIDTH, height - box_top - self.BAR_HEIGHT)
            # Create a slightly larger highlight capture area for marker
            capture_area = self._capture_areas[i] = wx.Rect(*area)
            capture_area.x -= self.MARKER_CAPTURE_PADX
            capture_area.width += self.MARKER_CAPTURE_PADX

            dc.SetPen(PEN(self.SELECTION_LINE_COLOUR))
            dc.DrawLine(x, box_top, x, height)
            if self._mousepos is not None:
                # Draw drag buttons when mouse in control
                button_area = wx.Rect(-1, -1, self.MARKER_BUTTON_WIDTH,
                                      self.MARKER_BUTTON_HEIGHT).CenterIn(area)
                button_radius = 3
                if i == self._active_marker:
                    brush_colour = wx.WHITE # self.BAR_HL_COLOUR
                else:
                    brush_colour = self.MARKER_BUTTON_BG_COLOUR
                dc.SetBrush(BRUSH(brush_colour))
                dc.SetPen(PEN(self.MARKER_BUTTON_COLOUR))
                dc.DrawRoundedRectangle(*button_area, radius=button_radius)
                button_lines = [
                    (button_area.x + button_radius + i * 2, 
                        button_area.y + button_radius,
                        button_area.x + button_radius + i * 2, 
                         button_area.y + button_area.height - button_radius
                    ) for i in range(
                        (self.MARKER_BUTTON_WIDTH - 2 * button_radius + 1) / 2
                    )
                ]
                dc.SetPen(PEN(self.SELECTION_LINE_COLOUR))
                dc.DrawLineList(button_lines)
        if self.MARKER_LABEL_SHOW:
            # Move marker labels apart if overlapping each other
            rect1, rect2 = [x[1] for x in marker_labels]
            if rect1.Intersects(rect2):
                overlap = wx.Rect(*rect1).Intersect(rect2).width
                delta1 = (overlap / 2) + 1 # +1 for padding
                if (rect1.x - delta1 < 1):
                    delta1 = rect1.x - 1 # Left going over left edge: set to 1
                delta2 = overlap - delta1
                if (rect2.right + delta2 > width):
                    delta2 = width - rect2.right # Right going over right edge:
                    delta1 = overlap - delta2    # set to right edge
                rect1.x -= delta1
                rect2.x += delta2
            # Draw left and right marker labels
            for text, area in marker_labels:
                dc.DrawText(text, area.x, 0)


    def OnMouseEvent(self, event):
        if not self.Enabled or not any(filter(None, self._rng)):
            return

        if not self._box_area:
            # Must not have been drawn yet
            self.Refresh()
        last_pos = self._mousepos
        self._mousepos = event.Position
        refresh = False
        active_markers = [i for i, c in enumerate(self._capture_areas)
                          if c and c.Contains(event.Position)]
        active_marker = active_markers[0] if active_markers else None
        if len(active_markers) > 1 and last_pos \
        and last_pos.x > event.Position.x:
            # Switch marker to right if two are overlapping and approaching
            # from the right.
            active_marker = active_markers[-1]
        self.SetToolTip("")

        if event.Entering():
            refresh = True
        elif event.Moving():
            if active_marker is not None:
                if not self._mousepos_special:
                    # Moved into a special position: draw active areas
                    self._active_marker = active_marker
                    self._mousepos_special = True
                    self.TopLevelParent.SetCursor(self._cursor_marker_hover)
                    refresh = True
            elif self._mousepos_special:
                # Moved out from a special position: draw default
                self._active_marker = None
                self.TopLevelParent.SetCursor(self._cursor_default)
                self._mousepos_special = False
                refresh = True
            elif self._grip_area:
                if (self._grip_area.Contains(self._mousepos) \
                and not self._grip_area.Contains(last_pos)) \
                or (self._grip_area.Contains(last_pos) \
                and not self._grip_area.Contains(self._mousepos)):
                    refresh = True
                else:
                    for button_area in self._bar_arrow_areas:
                        if button_area.Contains(self._mousepos):
                            refresh = True
            if not self._mousepos_special \
            and self._box_area and self._box_area.Contains(event.Position):
                x_delta = abs(event.Position.x - self._box_area.x + 1)
                range_delta = self._rng[1] - self._rng[0]
                x_step = range_delta * x_delta / self._box_area.width
                self.SetToolTip(self.FormatLabel(self._rng[0] + x_step))
        elif event.LeftDClick():
            if active_marker is not None:
                # Maximize/restore marker value on double-clicking a marker
                i = active_marker
                if self._vals[i] == self._rng[i]:
                    # Currently is maximized: restore to previous value, or
                    # center of available space if nothing previous.
                    if self._vals_prev[i] is None \
                    or self._vals_prev[i] == self._rng[i]:
                        center = self._rng[i] \
                            + (self._rng[i] - self._vals[1 - i]) / 2
                        self.SetValue(i, center, False)
                    else:
                        self.SetValue(i, self._vals_prev[i], False)
                else:
                    # Currently is not maximized: set value to range edge
                    self.SetValue(i, self._rng[i], False)
                refresh = True
            elif self._grip_area and self._grip_area.Contains(event.Position):
                # Maximize/restore both markers on double-clicking scrollbar
                if self._vals == self._rng:
                    # Currently is maximized: restore to previous values, or
                    # spaced evenly in available space if nothing previous.
                    for i in range(2):
                        if self._vals_prev[i] is None \
                        or self._vals_prev[i] == self._rng[i]:
                            center = self._rng[i] \
                                + (self._rng[i] - self._vals[1 - i]) / 2
                            self.SetValue(i, center, False)
                        else:
                            self.SetValue(i, self._vals_prev[i], False)
                else:
                    # Currently is not maximized: set value to range edge
                    self.SetValues(*self._rng, refresh=False)
        elif event.LeftDown():
            if active_marker is not None:
                self.CaptureMouse()
                self._dragging_markers[active_marker] = True
            elif self._grip_area and self._grip_area.Contains(event.Position):
                self.CaptureMouse()
                self._dragging_scrollbar = True
            elif self._bar_area and self._bar_area.Contains(event.Position):
                arrow = [i for i, a in enumerate(self._bar_arrow_areas) \
                    if a.Contains(event.Position)
                ]
                arrow = arrow[0] if arrow else None
                if arrow is not None:
                    # Nudge scrollbar in arrow direction
                    direction = [-1, 1][arrow]
                    step = self.SCROLL_STEP * (
                        (self._rng[1] - self._rng[0]) / self.ClientSize.width
                    )
                else:
                    # Move scrollbar by its length
                    direction = -1 \
                        if (event.Position.x < self._grip_area.x) else 1
                    step = (self._vals[1] - self._vals[0])
                if isinstance(self._rng[0], datetime.date) and step.days < 1:
                    # Enforce a minimum step of 1 day for date values
                    step = datetime.timedelta(days=1)
                new_vals = [(x + step) if (direction > 0) else (x - step) \
                    for x in self._vals
                ]
                # If one value would go over the edge, pull both values
                # back equally
                for i in range(2):
                    # Test left with less-than, right with greater-than
                    if [operator.lt, operator.gt][i](new_vals[i], self._rng[i]):
                        new_vals[i] = self._rng[i]
                        if direction > 0:
                            new_vals[1 - i] -= step \
                                - (self._rng[i] - self._vals[i])
                        else:
                            new_vals[1 - i] += step \
                                - (self._vals[i] - self._rng[i])
                self.SetValues(*new_vals, refresh=False)
                refresh = True
            elif self._box_area and (self._box_area.Contains(event.Position)
            or any(x.Contains(event.Position) for x in self._box_gap_areas)):
                x_delta = abs(max(0, event.Position.x - self._box_area.x + 1))
                range_delta = self._rng[1] - self._rng[0]
                x_step = range_delta * x_delta / self._box_area.width
                x_val = min(max(self._rng[0] + x_step, self._rng[0]), self._rng[1])
                closest, _ = min(enumerate(abs(x - x_val) for x in self._vals),
                                 key=lambda x: x[1])
                self.SetValue(closest, x_val)
        elif event.LeftUp():
            if self.HasCapture():
                self.ReleaseMouse()
                if active_marker is None:
                    self.TopLevelParent.SetCursor(self._cursor_default)
                    self._mousepos_special = False
                    self._active_marker = None
                if not self.ClientRect.Contains(event.Position):
                    # Mouse was down inside self, dragged out and released
                    self._mousepos = None
            self._dragging_markers[:] = [False] * 2
            self._dragging_scrollbar = False
            refresh = True
        elif event.Dragging():
            if self._mousepos_special:
                i = self._active_marker
                do_step = True
                # Skip drag if marker is against an edge (either range edge or
                # the other marker) and cursor is beyond that edge.
                if self._vals[i] in [self._rng[i], self._vals[1 - i]]:
                    # if is_right_side XOR is_against_range
                    direction = -1 if (i ^ (self._vals[i] != self._rng[i])) \
                        else 1
                    do_step = 0 <= \
                        direction * cmp(event.Position.x, self._marker_xs[i])
                if do_step:
                    self._dragging_markers[i] = True
                    x_delta = abs(event.Position.x - last_pos.x)
                    x_direction = 1 if (event.Position.x > last_pos.x) else -1
                    range_delta = self._rng[1] - self._rng[0]
                    step = range_delta * x_delta / self.GetClientSize().width
                    if isinstance(self._rng[0], datetime.date) and step.days < 1:
                        # Enforce a minimum step of 1 day for date values
                        step = datetime.timedelta(days=1)
                    in_area = self._grip_area.Contains(
                        event.Position.x, self._grip_area.Top
                    )
                    enlarging = (x_direction > 0) if i else (x_direction < 0)
                    x_i_delta = abs(self._marker_xs[i] - event.Position.x)
                    if x_i_delta > 5 and not (in_area ^ enlarging):
                        # Skip if mouse is far from the border being moved and
                        # area is enlarged from inside or shrunk from outside
                        step = 0
                    if step:
                        new_val = (self._vals[i] + step) if x_direction > 0 \
                                  else (self._vals[i] - step)
                        self.SetValue(i, new_val, False)
                        refresh = True
            elif self._dragging_scrollbar:
                do_step = True
                # Skip drag if scrollbar is against the range edge and
                # cursor is moving toward that edge.
                if self._grip_area.x <= self._box_area.x \
                or self._grip_area.right >= self._box_area.right:
                    going_right = (event.Position.x > last_pos.x)
                    do_step = going_right \
                        and (self._grip_area.right < self._box_area.right) \
                        or not going_right \
                        and (self._grip_area.x > self._box_area.x)
                if do_step:
                    x_delta = abs(event.Position.x - last_pos.x)
                    x_direction = 1 if (event.Position.x > last_pos.x) else -1
                    going_right = (event.Position.x > last_pos.x)
                    range_delta = self._rng[1] - self._rng[0]
                    range_width = self.GetClientSize().width
                    step = range_delta * x_delta / range_width
                    in_area = self._grip_area.Contains(
                        event.Position.x, self._grip_area.Top
                    )
                    closest_i, x_i_delta = 0, sys.maxsize
                    for i in range(2):
                        dlt = abs(self._marker_xs[i] - event.Position.x)
                        if dlt < x_i_delta:
                            closest_i, x_i_delta = i, dlt
                    outwards = (x_direction > 0) if closest_i \
                               else (x_direction < 0)
                    if in_area or not outwards:
                        step = 0
                    if step:
                        if isinstance(self._rng[0], datetime.date) \
                        and step.days < 1:
                            # Enforce a minimum step of 1 day for date values
                            step = datetime.timedelta(days=1)
                        new_vals = [(x + step) if going_right else (x - step)
                            for x in self._vals
                        ]
                        # If one value would go over the edge, pull both values
                        # back equally
                        for i in range(2):
                            # Test left with less-than, right with greater-than
                            if [operator.lt,
                            operator.gt][i](new_vals[i], self._rng[i]):
                                new_vals[i] = self._rng[i]
                                if going_right:
                                    new_vals[1 - i] -= step \
                                        - (self._rng[i] - self._vals[i])
                                else:
                                    new_vals[1 - i] += step \
                                        - (self._vals[i] - self._rng[i])
                        self.SetValues(*new_vals, refresh=False)
                        refresh = True
        elif event.Leaving():
            i = self._active_marker
            if not self.HasCapture():
                self._mousepos = None
            if self._mousepos_special and not self.HasCapture():
                self.TopLevelParent.SetCursor(self._cursor_default)
                self._mousepos_special = False
                self._active_marker = None
            refresh = True
        if refresh:
            self.Refresh()
        # event.Y
        # event.X
        # event.WheelRotation
        # event.WheelDelta
        # event.Position
        # event.Moving
        # event.LogicalPosition
        # event.LeftUp
        # event.LeftIsDown
        # event.LeftDown
        # event.LeftDClick
        # event.Leaving
        # event.EventType
        # event.Event
        # event.Entering
        # event.Dragging


    def OnMouseCaptureLostEvent(self, event):
        """Handles MouseCaptureLostEvent, updating control UI if needed."""
        if self._mousepos_special:
            self._mousepos_special = False
            self.Refresh()


    def AcceptsFocusFromKeyboard(self):
        return True

    def AcceptsFocus(self):
        return True

    def ShouldInheritColours(self):
        return True

    def GetDefaultAttributes(self):
        return wx.Panel.GetClassDefaultAttributes()

    def DoGetBestSize(self):
        best = wx.Size(200, 40)
        self.CacheBestSize(best)
        return best



class ScrollingHtmlWindow(wx.html.HtmlWindow):
    """
    HtmlWindow that remembers its scroll position on resize and append.
    """

    def __init__(self, *args, **kwargs):
        wx.html.HtmlWindow.__init__(self, *args, **kwargs)
        self.Bind(wx.EVT_SCROLLWIN, self._OnScroll)
        self.Bind(wx.EVT_SIZE, self._OnSize)
        self._last_scroll_pos = [0, 0]
        self._last_scroll_range = [0, 1]


    def _OnSize(self, event):
        """
        Handler for sizing the HtmlWindow, sets new scroll position based
        previously stored one (HtmlWindow loses its scroll position on resize).
        """
        for i in range(2):
            orient = wx.VERTICAL if i else wx.HORIZONTAL
            # Division can be > 1 on first resizings, bound it to 1.
            pos, rng = self._last_scroll_pos[i], self._last_scroll_range[i]
            ratio = pos / float(rng) if rng else 0.0
            ratio = min(1, pos / float(rng) if rng else 0.0)
            self._last_scroll_pos[i] = ratio * self.GetScrollRange(orient)
        try:
            # Execute scroll later as something resets it after this handler
            wx.CallLater(50, lambda:
                self.Scroll(*self._last_scroll_pos) if self else None)
        except Exception:
            pass # CallLater fails if not called from the main thread
        event.Skip() # Allow event to propagate wx handler


    def _OnScroll(self, event=None):
        """
        Handler for scrolling the window, stores scroll position
        (HtmlWindow loses it on resize).
        """
        p, r = self.GetScrollPos, self.GetScrollRange
        self._last_scroll_pos   = [p(x) for x in (wx.HORIZONTAL, wx.VERTICAL)]
        self._last_scroll_range = [r(x) for x in (wx.HORIZONTAL, wx.VERTICAL)]
        if event: event.Skip() # Allow event to propagate wx handler


    def Scroll(self, x, y):
        """Scrolls the window so the view start is at the given point."""
        self._last_scroll_pos = [x, y]
        return super(ScrollingHtmlWindow, self).Scroll(x, y)


    def SetPage(self, source):
        """Sets the source of a page and displays it."""
        self._last_scroll_pos, self._last_scroll_range = [0, 0], [0, 1]
        return super(ScrollingHtmlWindow, self).SetPage(source)


    def AppendToPage(self, source):
        """
        Appends HTML fragment to currently displayed text, refreshes the window
        and restores scroll position.
        """
        self.Freeze()
        p, r, s = self.GetScrollPos, self.GetScrollRange, self.GetScrollPageSize
        pos, rng, size = (x(wx.VERTICAL) for x in [p, r, s])
        result = super(ScrollingHtmlWindow, self).AppendToPage(source)
        if size != s(wx.VERTICAL) or pos + size >= rng:
            pos = r(wx.VERTICAL) # Keep scroll at bottom edge
        self.Scroll(0, pos), self._OnScroll()
        self.Thaw()
        return result



class SortableListView(wx.ListView, wx.lib.mixins.listctrl.ColumnSorterMixin):
    """
    A sortable list view that can be batch-populated, autosizes its columns,
    can be filtered by string value matched on any row column,
    supports clipboard copy.
    """
    COL_PADDING = 30

    def __init__(self, *args, **kwargs):
        wx.ListView.__init__(self, *args, **kwargs)
        wx.lib.mixins.listctrl.ColumnSorterMixin.__init__(self, 0)
        self.itemDataMap = {} # {item_id: [values], } for ColumnSorterMixin
        self._data_map = {} # {item_id: row dict, } currently visible data
        self._id_rows = [] # [(item_id, {row dict}), ] all data items
        self._columns = [] # [(name, label), ]
        self._filter = "" # Filter string
        self._col_widths = {} # {col_index: width in pixels, }
        self._col_maxwidth = -1 # Maximum width for auto-sized columns
        # Remember row colour attributes { item_id: {SetItemTextColour: x,
        # SetItemBackgroundColour: y, }, }
        self._row_colours = collections.defaultdict(dict)
        # Default row column formatter function
        frmt = lambda: lambda r, c: "" if r.get(c) is None else unicode(r[c])
        self._formatters = collections.defaultdict(frmt)
        id_copy, id_selectall = wx.NewIdRef().Id, wx.NewIdRef().Id
        entries = [(wx.ACCEL_CTRL, x, id_copy)
                   for x in (ord("C"), wx.WXK_INSERT, wx.WXK_NUMPAD_INSERT)]
        entries += [(wx.ACCEL_CTRL, ord("A"), id_selectall)]
        self.SetAcceleratorTable(wx.AcceleratorTable(entries))
        self.Bind(wx.EVT_MENU, self.OnCopy, id=id_copy)
        self.Bind(wx.EVT_MENU, self.OnSelectAll, id=id_selectall)
        self.counter = lambda x={"c": 0}: x.update(c=1+x["c"]) or x["c"]


    def SetColumnFormatters(self, formatters):
        """
        Sets the functions used for formatting displayed column values.

        @param   formatters  {col_name: function(rowdict, col_name), }
        """
        self._formatters.clear()
        if formatters:
            self._formatters.update(formatters)


    def Populate(self, rows):
        """
        Populates the control with rows, clearing previous data, if any.
        Re-selects the previously selected row, if any.

        @param   rows        a list of data dicts
        """
        self._col_widths.clear()
        self._row_colours.clear()
        self._id_rows = [(self.counter(), r) for r in rows]
        self.RefreshRows()


    def AppendRow(self, data):
        """
        Appends the specified data to the control as a new row.

        @param   data     item data dictionary
        """
        item_id = self.counter()
        if self._RowMatchesFilter(data):
            columns = [c[0] for c in self._columns]
            index = self.ItemCount
            col_value = self._formatters[columns[0]](data, columns[0])
            self.InsertItem(index, col_value)
            for i, col_name in [(i, x) for i, x in enumerate(columns) if i]:
                col_value = self._formatters[col_name](data, col_name)
                self.SetItem(index, i, col_value)
                col_width = self.GetTextExtent(col_value)[0] + self.COL_PADDING
                if col_width > self._col_widths.get(i, 0):
                    self._col_widths[i] = col_width
                    self.SetColumnWidth(i, col_width)
            self.SetItemData(index, item_id)
            self.itemDataMap[item_id] = [data[c] for c in columns]
            self._data_map[item_id] = data
            self.SetItemImage(index, -1)
            self.SetItemColumnImage(index, 0, -1)
        self._id_rows.append((item_id, data))


    def GetFilter(self):
        return self._filter
    def SetFilter(self, value, force_refresh=False):
        """
        Sets the text to filter list by. Any row not containing the text in any
        column will be hidden.

        @param   force_refresh  if True, all content is refreshed even if
                                filter value did not change
        """
        if force_refresh or value != self._filter:
            if force_refresh:
                self._col_widths.clear()
            self._filter = value
            if self._id_rows:
                self.RefreshRows()


    def RefreshRows(self):
        """
        Clears the list and inserts all unfiltered rows, auto-sizing the 
        columns.
        """
        selected_ids, selected = [], self.GetFirstSelected()
        while selected >= 0:
            selected_ids.append(self.GetItemData(selected))
            selected = self.GetNextSelected(selected)

        # Store row colour attributes
        for i in range(self.ItemCount):
            t, b = self.GetItemTextColour(i), self.GetItemBackgroundColour(i)
            id = self.GetItemData(i)
            for func, value in [(self.SetItemTextColour, t),
                                (self.SetItemBackgroundColour, b)]:
                if wx.NullColour != value:
                    self._row_colours[id][func] = value
                elif func in self._row_colours[id]:
                    del self._row_colours[id][func]
            if id in self._row_colours and not self._row_colours[id]:
                del self._row_colours[id]

        self.Freeze()
        wx.ListView.DeleteAllItems(self)
        # To map list item data ID to row, ListView allows only integer per row
        row_data_map = {} # {item_id: {row dict}, }
        item_data_map = {} # {item_id: [row values], }
        # For measuring by which to set column width: header or value
        header_lengths = {} # {col_name: integer}
        col_lengths = {} # {col_name: integer}
        for col_name, col_label in self._columns:
            col_lengths[col_name] = 0
            # Keep space for sorting arrows.
            width = self.GetTextExtent(col_label + "  ")[0] + self.COL_PADDING
            header_lengths[col_name] = width
        index = 0
        for item_id, row in self._id_rows:
            if not self._RowMatchesFilter(row):
                continue # continue for index, (item_id, row) in enumerate(..)
            col_name = self._columns[0][0]
            col_value = self._formatters[col_name](row, col_name)
            col_lengths[col_name] = max(col_lengths[col_name],
                                        self.GetTextExtent(col_value)[0] + self.COL_PADDING)
            self.InsertItem(index, col_value)
            self.SetItemData(index, item_id)
            self.SetItemImage(index, -1)
            self.SetItemColumnImage(index, 0, -1)
            item_data_map[item_id] = {0: row[col_name]}
            row_data_map[item_id] = row
            col_index = 1 # First was already inserted
            for col_name, col_label in self._columns[col_index:]:
                col_value = self._formatters[col_name](row, col_name)
                col_width = self.GetTextExtent(col_value)[0] + self.COL_PADDING
                col_lengths[col_name] = max(col_lengths[col_name], col_width)
                self.SetItem(index, col_index, col_value)
                item_data_map[item_id][col_index] = row.get(col_name)
                col_index += 1
            index += 1
        self._data_map = row_data_map
        self.itemDataMap = item_data_map
        if self._id_rows and not self._col_widths:
            if self._col_maxwidth > 0:
                for col_name, width in col_lengths.items():
                    col_lengths[col_name] = min(width, self._col_maxwidth)
                for col_name, width in header_lengths.items():
                    header_lengths[col_name] = min(width, self._col_maxwidth)
            for i, (col_name, col_label) in enumerate(self._columns):
                col_width = max(col_lengths[col_name], header_lengths[col_name])
                self.SetColumnWidth(i, col_width)
                self._col_widths[i] = col_width
                #wx.LIST_AUTOSIZE, wx.LIST_AUTOSIZE_USEHEADER
        elif self._col_widths:
            for col, width in self._col_widths.items():
                self.SetColumnWidth(col, width)
        if self.GetSortState()[0] >= 0:
            self.SortListItems(*self.GetSortState())

        if selected_ids or self._row_colours:
            idindx = dict((self.GetItemData(i), i)
                          for i in range(self.ItemCount))
        for item_id, attrs in self._row_colours.items(): # Re-colour rows
            if item_id not in idindx: continue
            [func(idindx[item_id], value) for func, value in attrs.items()]
        if selected_ids: # Re-select the previously selected items
            [self.Select(idindx[i]) for i in selected_ids if i in idindx]

        self.Thaw()


    def ResetColumnWidths(self):
        """Resets the stored column widths, triggering a fresh autolayout."""
        self._col_widths.clear()
        self.RefreshRows()


    def DeleteItem(self, index):
        """Deletes the row at the specified index."""
        data_id = self.GetItemData(index)
        data = self._data_map.get(data_id)
        del self._data_map[data_id]
        self._id_rows.remove((data_id, data))
        return wx.ListView.DeleteItem(self, index)


    def DeleteAllItems(self):
        """Deletes all items data and clears the list."""
        self.itemDataMap = {}
        self._data_map = {}
        self._id_rows = []
        self._row_colours.clear()
        self.Freeze()
        result = wx.ListView.DeleteAllItems(self)
        self.Thaw()
        return result


    def GetItemCountFull(self):
        """Returns the full row count, including items hidden by filter."""
        return len(self._id_rows)


    def SetColumnsMaxWidth(self, width):
        """Sets the maximum width for all columns, used in auto-size."""
        self._col_maxwidth = width


    def SetColumns(self, columns):
        """
        Sets the list columns, clearing current columns if any.

        @param   columns  [(column name, column label), ]
        """
        self.ClearAll()
        self.SetColumnCount(len(columns))
        for i, (name, label) in enumerate(columns):
            col_label = label + "  " # Keep space for sorting arrows.
            self.InsertColumn(i + 1, col_label)
            self._col_widths[i] = max(self._col_widths.get(i, 0),
                self.GetTextExtent(col_label)[0] + self.COL_PADDING)
            self.SetColumnWidth(i, self._col_widths[i])
        self._columns = columns


    def GetItemMappedData(self, index):
        """Returns the data mapped to the specified row index."""
        data_id = self.GetItemData(index)
        data = self._data_map.get(data_id)
        return data


    def GetListCtrl(self):
        """Required by ColumnSorterMixin."""
        return self


    def SortListItems(self, col=-1, ascending=1):
        """Sorts the list items on demand."""
        wx.lib.mixins.listctrl.ColumnSorterMixin.SortListItems(
            self, col, ascending)
        self.OnSortOrderChanged()


    def GetColumnSorter(self):
        """
        Override ColumnSorterMixin.GetColumnSorter to specify our sorting,
        which accounts for None values.
        """
        sorter = self.__ColumnSorter if hasattr(self, "itemDataMap") \
            else wx.lib.mixins.listctrl.ColumnSorterMixin.GetColumnSorter(self)
        return sorter


    def OnSortOrderChanged(self):
        """
        Callback called by ColumnSorterMixin after sort order has changed
        (whenever user clicked column header), refreshes column header sort
        direction info.
        """
        ARROWS = {True: u" ↓", False: u" ↑"}
        col_sorted, ascending = self.GetSortState()
        for i in range(self.ColumnCount):
            col_item = self.GetColumn(i)
            if i == col_sorted:
                new_item = wx.ListItem()
                t = col_item.Text.replace(ARROWS[0], "").replace(ARROWS[1], "")
                new_item.Text = u"%s%s" % (t, ARROWS[ascending])
                self.SetColumn(i, new_item)
            elif any(i for i in ARROWS.values() if i in col_item.Text):
                # Remove the previous sort arrow, if any
                new_item = wx.ListItem()
                t = col_item.Text.replace(ARROWS[0], "").replace(ARROWS[1], "")
                new_item.Text = t
                self.SetColumn(i, new_item)


    def OnCopy(self, event):
        """Copies selected rows to clipboard."""
        rows, i = [], self.GetFirstSelected()
        while i >= 0:
            data = self.GetItemMappedData(i)
            rows.append("\t".join(self._formatters[n](data, n)
                                  for n, l in self._columns))
            i = self.GetNextSelected(i)
        if rows:
            clipdata = wx.TextDataObject()
            clipdata.SetText("\n".join(rows))
            wx.TheClipboard.Open()
            wx.TheClipboard.SetData(clipdata)
            wx.TheClipboard.Close()


    def OnSelectAll(self, event):
        """Selects all rows."""
        for i in range(self.ItemCount): self.Select(i)


    def _RowMatchesFilter(self, row):
        """Returns whether the row dict matches the current filter."""
        result = True
        if self._filter:
            result = False
            pattern = re.escape(self._filter)
            for col_name, col_label in self._columns:
                col_value = self._formatters[col_name](row, col_name)
                if re.search(pattern, col_value, re.I):
                    result = True
                    break
        return result


    def __ColumnSorter(self, key1, key2):
        """
        Sort function fed to ColumnSorterMixin, is given two integers which we
        have mapped on our own.
        """
        col = self._col
        ascending = self._colSortFlag[col]
        item1 = self.itemDataMap[key1][col]
        item2 = self.itemDataMap[key2][col]

        #--- Internationalization of string sorting with locale module
        if isinstance(item1, unicode) and isinstance(item2, unicode):
            cmpVal = locale.strcoll(item1.lower(), item2.lower())
        elif isinstance(item1, str) or isinstance(item2, str):
            items = item1.lower(), item2.lower()
            cmpVal = locale.strcoll(*map(unicode, items))
        else:
            if item1 is None:
                cmpVal = -1
            elif item2 is None:
                cmpVal = 1
            else:
                cmpVal = cmp(item1, item2)

        # If items are equal, pick something else to make the sort value unique
        if cmpVal == 0:
            cmpVal = apply(cmp, self.GetSecondarySortValues(col, key1, key2))

        result = cmpVal if ascending else -cmpVal
        return result



class SortableUltimateListCtrl(wx.lib.agw.ultimatelistctrl.UltimateListCtrl,
                               wx.lib.mixins.listctrl.ColumnSorterMixin):
    """
    A sortable list control that can be batch-populated, autosizes its columns,
    can be filtered by string value matched on any row column,
    supports clipboard copy.
    """
    COL_PADDING = 30

    SORT_ARROW_UP = wx.lib.embeddedimage.PyEmbeddedImage(
        "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAADxJ"
        "REFUOI1jZGRiZqAEMFGke2gY8P/f3/9kGwDTjM8QnAaga8JlCG3CAJdt2MQxDCAUaOjyjKMp"
        "cRAYAABS2CPsss3BWQAAAABJRU5ErkJggg==")

    #----------------------------------------------------------------------
    SORT_ARROW_DOWN = wx.lib.embeddedimage.PyEmbeddedImage(
        "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAEhJ"
        "REFUOI1jZGRiZqAEMFGke9QABgYGBgYWdIH///7+J6SJkYmZEacLkCUJacZqAD5DsInTLhDR"
        "bcPlKrwugGnCFy6Mo3mBAQChDgRlP4RC7wAAAABJRU5ErkJggg==")


    def __init__(self, *args, **kwargs):
        kwargs.setdefault("agwStyle", 0)
        if hasattr(wx.lib.agw.ultimatelistctrl, "ULC_USER_ROW_HEIGHT"):
            kwargs["agwStyle"] |= wx.lib.agw.ultimatelistctrl.ULC_USER_ROW_HEIGHT
        if hasattr(wx.lib.agw.ultimatelistctrl, "ULC_SHOW_TOOLTIPS"):
            kwargs["agwStyle"] |= wx.lib.agw.ultimatelistctrl.ULC_SHOW_TOOLTIPS

        wx.lib.agw.ultimatelistctrl.UltimateListCtrl.__init__(self, *args, **kwargs)
        wx.lib.mixins.listctrl.ColumnSorterMixin.__init__(self, 0)
        try:
            ColourManager.Manage(self._headerWin, "ForegroundColour", wx.SYS_COLOUR_BTNTEXT)
            ColourManager.Manage(self._mainWin,   "BackgroundColour", wx.SYS_COLOUR_WINDOW)
        except Exception: pass
        self.itemDataMap = {}   # {item_id: [values], } for ColumnSorterMixin
        self._data_map = {}     # {item_id: row dict, } currently visible data
        self._id_rows = []      # [(item_id, {row dict}), ] all data items
        self._id_images = {}    # {item_id: imageIds}
        self._columns = []      # [(name, label), ]
        self._filter = ""       # Filter string
        self._col_widths = {}   # {col_index: width in pixels, }
        self._col_maxwidth = -1 # Maximum width for auto-sized columns
        self._top_row = None    # List top row data dictionary, if any
        self._drag_start = None # Item index currently dragged
        self.counter = lambda x={"c": 0}: x.update(c=1+x["c"]) or x["c"]
        self.AssignImageList(self._CreateImageList(), wx.IMAGE_LIST_SMALL)

        # Default row column formatter function
        frmt = lambda: lambda r, c: "" if r.get(c) is None else unicode(r[c])
        self._formatters = collections.defaultdict(frmt)
        id_copy = wx.NewIdRef().Id
        entries = [(wx.ACCEL_CMD, x, id_copy) for x in KEYS.INSERT + (ord("C"), )]
        self.SetAcceleratorTable(wx.AcceleratorTable(entries))
        self.Bind(wx.EVT_MENU, self.OnCopy, id=id_copy)
        self.Bind(wx.EVT_LIST_COL_CLICK, self.OnSort)
        self.Bind(wx.lib.agw.ultimatelistctrl.EVT_LIST_BEGIN_DRAG,  self.OnDragStart)
        self.Bind(wx.lib.agw.ultimatelistctrl.EVT_LIST_END_DRAG,    self.OnDragStop)
        self.Bind(wx.lib.agw.ultimatelistctrl.EVT_LIST_BEGIN_RDRAG, self.OnDragCancel)
        self.Bind(wx.EVT_SYS_COLOUR_CHANGED, self.OnSysColourChange)


    def GetScrollThumb(self, orientation):
        """Returns the scrollbar size in pixels."""
        # Workaround for wxpython v4 bug of missing orientation parameter
        return self._mainWin.GetScrollThumb(orientation) if self._mainWin else 0


    def GetScrollRange(self, orientation):
        """Returns the scrollbar range in pixels."""
        # Workaround for wxpython v4 bug of missing orientation parameter
        return self._mainWin.GetScrollRange(orientation) if self._mainWin else 0


    def GetSortImages(self):
        """For ColumnSorterMixin."""
        return (0, 1)


    def AssignImages(self, images):
        """
        Assigns images associated with the control.
        SetTopRow/AppendRow/InsertRow/Populate use imageIds from this list.

        @param   images  list of wx.Bitmap objects
        """
        for x in images: self.GetImageList(wx.IMAGE_LIST_SMALL).Add(x)
        if hasattr(self, "SetUserLineHeight"):
            h = images[0].Size[1]
            self.SetUserLineHeight(int(h * 1.5))


    def SetTopRow(self, data, imageIds=()):
        """
        Adds special top row to list, not subject to sorting or filtering.

        @param   data      item data dictionary
        @param   imageIds  list of indexes for the images associated to top row
        """
        self._top_row = data
        if imageIds: self._id_images[-1] = self._ConvertImageIds(imageIds)
        else: self._id_images.pop(-1, None)
        self._PopulateTopRow()


    def SetColumnFormatters(self, formatters):
        """
        Sets the functions used for formatting displayed column values.

        @param   formatters  {col_name: function(rowdict, col_name), }
        """
        self._formatters.clear()
        if formatters: self._formatters.update(formatters)


    def Populate(self, rows, imageIds=()):
        """
        Populates the control with rows, clearing previous data, if any.
        Re-selects the previously selected row, if any.

        @param   rows      a list of data dicts
        @param   imageIds  list of indexes for the images associated to rows
        """
        if rows: self._col_widths.clear()
        self._id_rows[:] = []
        if imageIds: imageIds = self._ConvertImageIds(imageIds)
        for r in rows:
            item_id = self.counter()
            self._id_rows += [(item_id, r)]
            if imageIds: self._id_images[item_id] = imageIds
        self.RefreshRows()


    def AppendRow(self, data, imageIds=()):
        """
        Appends the specified data to the control as a new row.

        @param   data      item data dictionary
        @param   imageIds  list of indexes for the images associated to this row
        """
        self.InsertRow(self.GetItemCount(), data, imageIds)


    def InsertRow(self, index, data, imageIds=()):
        """
        Inserts the specified data to the control at specified index as a new row.

        @param   data      item data dictionary
        @param   imageIds  list of indexes for the images associated to this row
        """
        item_id = self.counter()
        if imageIds:
            imageIds = self._id_images[item_id] = self._ConvertImageIds(imageIds)

        index = min(index, self.GetItemCount())
        if self._RowMatchesFilter(data):
            columns = [c[0] for c in self._columns]
            for i, col_name in enumerate(columns):
                col_value = self._formatters[col_name](data, col_name)

                if imageIds and not i: self.InsertImageStringItem(index, col_value, imageIds)
                elif not i: self.InsertStringItem(index, col_value)
                else: self.SetStringItem(index, i, col_value)
            self.SetItemData(index, item_id)
            self.itemDataMap[item_id] = [data[c] for c in columns]
            self._data_map[item_id] = data
            self.SetItemTextColour(index, self.ForegroundColour)
            self.SetItemBackgroundColour(index, self.BackgroundColour)
        self._id_rows.insert(index - (1 if self._top_row else 0), (item_id, data))
        if self.GetSortState()[0] >= 0:
            self.SortListItems(*self.GetSortState())


    def GetFilter(self):
        return self._filter
    def SetFilter(self, value, force_refresh=False):
        """
        Sets the text to filter list by. Any row not containing the text in any
        column will be hidden.

        @param   force_refresh  if True, all content is refreshed even if
                                filter value did not change
        """
        if force_refresh or value != self._filter:
            self._filter = value
            if force_refresh: self._col_widths.clear()
            if self._id_rows: self.RefreshRows()


    def RefreshRows(self):
        """
        Clears the list and inserts all unfiltered rows, auto-sizing the
        columns.
        """
        selected_ids, selected_idxs, selected = [], [], self.GetFirstSelected()
        while selected >= 0:
            selected_ids.append(self.GetItemData(selected))
            selected_idxs.append(selected)
            selected = self.GetNextSelected(selected)

        self.Freeze()
        try:
            for i in selected_idxs:
                self._mainWin.SendNotify(i, wx.wxEVT_COMMAND_LIST_ITEM_DESELECTED)
            wx.lib.agw.ultimatelistctrl.UltimateListCtrl.DeleteAllItems(self)
            self._PopulateTopRow()
            self._PopulateRows(selected_ids)
        finally: self.Thaw()


    def ResetColumnWidths(self):
        """Resets the stored column widths, triggering a fresh autolayout."""
        self._col_widths.clear()
        self.RefreshRows()


    def DeleteItem(self, index):
        """Deletes the row at the specified index."""
        item_id = self.GetItemData(index)
        data = self._data_map.get(item_id)
        del self._data_map[item_id]
        self._id_rows.remove((item_id, data))
        self._id_images.pop(item_id, None)
        return wx.lib.agw.ultimatelistctrl.UltimateListCtrl.DeleteItem(self, index)


    def DeleteAllItems(self):
        """Deletes all items data and clears the list."""
        self.itemDataMap = {}
        self._data_map = {}
        self._id_rows = []
        for item_id in self._id_images:
            if item_id >= 0: self._id_images.pop(item_id)
        self.Freeze()
        try:
            result = wx.lib.agw.ultimatelistctrl.UltimateListCtrl.DeleteAllItems(self)
            self._PopulateTopRow()
        finally: self.Thaw()
        return result


    def GetItemCountFull(self):
        """Returns the full row count, including items hidden by filter."""
        return len(self._id_rows)


    def GetItemTextFull(self, idx):
        """Returns item text by index, including items hidden by filter."""
        data, col_name = self._id_rows[idx][-1], self._columns[0][0]
        return self._formatters[col_name](data, col_name)


    def SetColumnsMaxWidth(self, width):
        """Sets the maximum width for all columns, used in auto-size."""
        self._col_maxwidth = width


    def SetColumns(self, columns):
        """
        Sets the list columns, clearing current columns if any.

        @param   columns  [(column name, column label), ]
        """
        self.ClearAll()
        self.SetColumnCount(len(columns))
        for i, (name, label) in enumerate(columns):
            col_label = label + "  " # Keep space for sorting arrows.
            self.InsertColumn(i, col_label)
            self._col_widths[i] = max(self._col_widths.get(i, 0),
                self.GetTextExtent(col_label)[0] + self.COL_PADDING)
            self.SetColumnWidth(i, self._col_widths[i])
        self._columns = copy.deepcopy(columns)


    def SetColumnAlignment(self, column, align):
        """
        Sets alignment for column at specified index.

        @param   align  one of ULC_FORMAT_LEFT, ULC_FORMAT_RIGHT, ULC_FORMAT_CENTER
        """
        item = self.GetColumn(column)
        item.SetAlign(align)
        self.SetColumn(column, item)


    def GetItemMappedData(self, index):
        """Returns the data mapped to the specified row index."""
        data_id = self.GetItemData(index)
        data = self._data_map.get(data_id)
        return data


    def GetListCtrl(self):
        """Required by ColumnSorterMixin."""
        return self


    def SortListItems(self, col=-1, ascending=1):
        """Sorts the list items on demand."""
        selected_ids, selected = [], self.GetFirstSelected()
        while selected >= 0:
            selected_ids.append(self.GetItemData(selected))
            selected = self.GetNextSelected(selected)

        wx.lib.mixins.listctrl.ColumnSorterMixin.SortListItems(
            self, col, ascending)

        if selected_ids: # Re-select the previously selected items
            idindx = dict((self.GetItemData(i), i)
                          for i in range(self.GetItemCount()))
            [self.Select(idindx[i]) for i in selected_ids if i in idindx]


    def GetColumnSorter(self):
        """
        Override ColumnSorterMixin.GetColumnSorter to specify our sorting,
        which accounts for None values.
        """
        sorter = self.__ColumnSorter if hasattr(self, "itemDataMap") \
            else wx.lib.mixins.listctrl.ColumnSorterMixin.GetColumnSorter(self)
        return sorter


    def OnSysColourChange(self, event):
        """
        Handler for system colour change, updates sort arrow and item colours.
        """
        event.Skip()
        il, il2  = self.GetImageList(wx.IMAGE_LIST_SMALL), self._CreateImageList()
        for i in range(il2.GetImageCount()): il.Replace(i, il2.GetBitmap(i))
        self.RefreshRows()


    def OnCopy(self, event):
        """Copies selected rows to clipboard."""
        rows, i = [], self.GetFirstSelected()
        while i >= 0:
            data = self.GetItemMappedData(i)
            rows.append("\t".join(self._formatters[n](data, n)
                                  for n, l in self._columns))
            i = self.GetNextSelected(i)
        if rows:
            clipdata = wx.TextDataObject()
            clipdata.SetText("\n".join(rows))
            wx.TheClipboard.Open()
            wx.TheClipboard.SetData(clipdata)
            wx.TheClipboard.Close()


    def OnSort(self, event):
        """Handler on clicking column, sorts list."""
        col, ascending = self.GetSortState()
        if col == event.GetColumn() and not ascending: # Clear sort
            self._col = -1
            self._colSortFlag = [0] * self.GetColumnCount()
            self.ClearColumnImage(col)
            self.RefreshRows()
        else:
            ascending = 1 if col != event.GetColumn() else 1 - ascending
            self.SortListItems(event.GetColumn(), ascending)


    def OnDragStop(self, event):
        """Handler for stopping drag in the list, rearranges list."""
        start, stop = self._drag_start, max(1, event.GetIndex())
        if not start or start == stop: return

        selecteds, selected = [], self.GetFirstSelected()
        while selected > 0:
            selecteds.append(selected)
            selected = self.GetNextSelected(selected)

        idx = stop if start > stop else stop - len(selecteds)
        if not selecteds: # Dragged beyond last item
            idx, selecteds = self.GetItemCount() - 1, [start]

        datas     = map(self.GetItemMappedData, selecteds)
        image_ids = map(self._id_images.get, map(self.GetItemData, selecteds))

        self.Freeze()
        try:
            for x in selecteds[::-1]: self.DeleteItem(x)
            for i, (data, imageIds) in enumerate(zip(datas, image_ids)):
                imageIds0 = self._ConvertImageIds(imageIds, reverse=True)
                self.InsertRow(idx + i, data, imageIds0)
                self.Select(idx + i)
            self._drag_start = None
        finally: self.Thaw()


    def OnDragStart(self, event):
        """Handler for dragging items in the list, cancels dragging."""
        if self.GetSortState()[0] < 0 \
        and (not self._top_row or event.GetIndex()):
            self._drag_start = event.GetIndex()
        else:
            self._drag_start = None
            self.OnDragCancel(event)


    def OnDragCancel(self, event):
        """Handler for cancelling item drag in the list, cancels dragging."""
        class HackEvent(object): # UltimateListCtrl hack to cancel drag.
            def __init__(self, pos=wx.Point()): self._position = pos
            def GetPosition(self): return self._position
        wx.CallAfter(lambda: self and self.Children[0].DragFinish(HackEvent()))


    def _CreateImageList(self):
        """
        Creates image list for the control, populated with sort arrow images.
        Arrow colours are adjusted for system foreground colours if necessary.
        """
        il = wx.lib.agw.ultimatelistctrl.PyImageList(*self.SORT_ARROW_UP.Bitmap.Size)
        fgcolour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNTEXT)
        defrgb, myrgb = "\x00" * 3, "".join(map(chr, fgcolour.Get()))[:3]

        for embedded in self.SORT_ARROW_UP, self.SORT_ARROW_DOWN:
            if myrgb != defrgb:
                img = embedded.Image.Copy()
                if not img.HasAlpha(): img.InitAlpha()
                data = img.GetDataBuffer()
                for i in range(embedded.Image.Width * embedded.Image.Height):
                    rgb = data[i*3:i*3 + 3]
                    if rgb == defrgb: data[i*3:i*3 + 3] = myrgb
                il.Add(img.ConvertToBitmap())
            else:
                il.Add(embedded.Bitmap)
        return il


    def _ConvertImageIds(self, imageIds, reverse=False):
        """Returns user image indexes adjusted by internal image count."""
        if not imageIds: return imageIds
        shift = (-1 if reverse else 1) * len(self.GetSortImages() or [])
        return [x + shift for x in imageIds]


    def _PopulateTopRow(self):
        """Populates top row state, if any."""
        if not self._top_row: return

        columns = [c[0] for c in self._columns]
        col_value = self._formatters[columns[0]](self._top_row, columns[0])
        if -1 in self._id_images:
            self.InsertImageStringItem(0, col_value, self._id_images[-1])
        else: self.InsertStringItem(0, col_value)
        for i, col_name in enumerate(columns[1:], 1):
            col_value = self._formatters[col_name](self._top_row, col_name)
            self.SetStringItem(0, i, col_value)
        self.SetItemBackgroundColour(0, self.BackgroundColour)
        self.SetItemTextColour(0, self.ForegroundColour)

        def resize():
            if not self: return
            w = sum((self.GetColumnWidth(i) for i in range(1, len(self._columns))), 0)
            width = self.Size[0] - w - 5 # Space for padding
            if self.GetScrollRange(wx.VERTICAL) > 1:
                width -= self.GetScrollThumb(wx.VERTICAL) # Space for scrollbar
            self.SetColumnWidth(0, width)
        if self.GetItemCount() == 1: wx.CallAfter(resize)


    def _PopulateRows(self, selected_ids=()):
        """Populates all rows, restoring previous selecteds if any"""

        # To map list item data ID to row, ListCtrl allows only integer per row
        row_data_map = {} # {item_id: {row dict}, }
        item_data_map = {} # {item_id: [row values], }
        # For measuring by which to set column width: header or value
        header_lengths = {} # {col_name: integer}
        col_lengths = {} # {col_name: integer}
        for col_name, col_label in self._columns:
            col_lengths[col_name] = 0
            # Keep space for sorting arrows.
            width = self.GetTextExtent(col_label + "  ")[0] + self.COL_PADDING
            header_lengths[col_name] = width
        index = self.GetItemCount()
        for item_id, row in self._id_rows:
            if not self._RowMatchesFilter(row): continue # for item_id, row
            col_name = self._columns[0][0]
            col_value = self._formatters[col_name](row, col_name)
            col_lengths[col_name] = max(col_lengths[col_name],
                                        self.GetTextExtent(col_value)[0] + self.COL_PADDING)

            if item_id in self._id_images:
                self.InsertImageStringItem(index, col_value, self._id_images[item_id])
            else: self.InsertStringItem(index, col_value)

            self.SetItemData(index, item_id)
            item_data_map[item_id] = {0: row[col_name]}
            row_data_map[item_id] = row
            col_index = 1 # First was already inserted
            for col_name, col_label in self._columns[col_index:]:
                col_value = self._formatters[col_name](row, col_name)
                col_width = self.GetTextExtent(col_value)[0] + self.COL_PADDING
                col_lengths[col_name] = max(col_lengths[col_name], col_width)
                self.SetStringItem(index, col_index, col_value)
                item_data_map[item_id][col_index] = row.get(col_name)
                col_index += 1
            self.SetItemTextColour(index, self.ForegroundColour)
            self.SetItemBackgroundColour(index, self.BackgroundColour)
            index += 1
        self._data_map = row_data_map
        self.itemDataMap = item_data_map

        if self._id_rows and not self._col_widths:
            if self._col_maxwidth > 0:
                for col_name, width in col_lengths.items():
                    col_lengths[col_name] = min(width, self._col_maxwidth)
                for col_name, width in header_lengths.items():
                    header_lengths[col_name] = min(width, self._col_maxwidth)
            for i, (col_name, col_label) in enumerate(self._columns):
                col_width = max(col_lengths[col_name], header_lengths[col_name])
                self.SetColumnWidth(i, col_width)
                self._col_widths[i] = col_width
        elif self._col_widths:
            for col, width in self._col_widths.items():
                self.SetColumnWidth(col, width)
        if self.GetSortState()[0] >= 0:
            self.SortListItems(*self.GetSortState())

        if selected_ids: # Re-select the previously selected items
            idindx = dict((self.GetItemData(i), i)
                          for i in range(self.GetItemCount()))
            for item_id in selected_ids:
                if item_id not in idindx: continue # for item_id
                self.Select(idindx[item_id])
                if idindx[item_id] >= self.GetCountPerPage():
                    lh = self.GetUserLineHeight()
                    dy = (idindx[item_id] - self.GetCountPerPage() / 2) * lh
                    self.ScrollList(0, dy)


    def _RowMatchesFilter(self, row):
        """Returns whether the row dict matches the current filter."""
        result = True
        if self._filter:
            result = False
            patterns = map(re.escape, self._filter.split())
            for col_name, col_label in self._columns:
                col_value = self._formatters[col_name](row, col_name)
                if all(re.search(p, col_value, re.I | re.U) for p in patterns):
                    result = True
                    break
        return result


    def __ColumnSorter(self, key1, key2):
        """
        Sort function fed to ColumnSorterMixin, is given two integers which we
        have mapped on our own. Returns -1, 0 or 1.
        """
        if key1 not in self.itemDataMap or key2 not in self.itemDataMap:
            return 0

        col = self._col
        ascending = self._colSortFlag[col]
        item1 = self.itemDataMap[key1][col]
        item2 = self.itemDataMap[key2][col]

        #--- Internationalization of string sorting with locale module
        if isinstance(item1, unicode) and isinstance(item2, unicode):
            cmpVal = locale.strcoll(item1.lower(), item2.lower())
        elif isinstance(item1, str) or isinstance(item2, str):
            items = item1.lower(), item2.lower()
            cmpVal = locale.strcoll(*map(unicode, items))
        else:
            if item1 is None:
                cmpVal = -1
            elif item2 is None:
                cmpVal = 1
            else:
                cmpVal = cmp(item1, item2)

        # If items are equal, pick something else to make the sort value unique
        if cmpVal == 0:
            cmpVal = apply(cmp, self.GetSecondarySortValues(col, key1, key2))

        result = cmpVal if ascending else -cmpVal
        return result



class SQLiteTextCtrl(wx.stc.StyledTextCtrl):
    """A StyledTextCtrl configured for SQLite syntax highlighting."""

    """SQLite reserved keywords."""
    KEYWORDS = map(unicode, sorted([
        "ABORT", "ACTION", "ADD", "AFTER", "ALL", "ALTER", "ANALYZE",
        "AND", "AS", "ASC", "ATTACH", "AUTOINCREMENT", "BEFORE",
        "BEGIN", "BETWEEN", "BINARY", "BY", "CASCADE", "CASE", "CAST",
        "CHECK", "COLLATE", "COLUMN", "COMMIT", "CONFLICT", "CONSTRAINT",
        "CREATE", "CROSS", "CURRENT_DATE", "CURRENT_TIME",
        "CURRENT_TIMESTAMP", "DATABASE", "DEFAULT", "DEFERRABLE",
        "DEFERRED", "DELETE", "DESC", "DETACH", "DISTINCT", "DROP",
        "EACH", "ELSE", "END", "ESCAPE", "EXCEPT", "EXCLUSIVE",
        "EXISTS", "EXPLAIN", "FAIL", "FOR", "FOREIGN", "FROM", "FULL",
        "GLOB", "GROUP", "HAVING", "IF", "IGNORE", "IMMEDIATE", "IN",
        "INDEX", "INDEXED", "INITIALLY", "INNER", "INSERT", "INSTEAD",
        "INTERSECT", "INTO", "IS", "ISNULL", "JOIN", "KEY", "LEFT", "LIKE",
        "LIMIT", "MATCH", "NATURAL", "NO", "NOCASE", "NOT", "NOTNULL",
        "NULL", "OF", "OFFSET", "ON", "OR", "ORDER", "OUTER", "PLAN",
        "PRAGMA", "PRIMARY", "QUERY", "RAISE", "REFERENCES", "REGEXP",
        "REINDEX", "RELEASE", "RENAME", "REPLACE", "RESTRICT", "RIGHT",
        "ROLLBACK", "ROW", "ROWID", "RTRIM", "SAVEPOINT", "SELECT", "SET",
        "TABLE", "TEMP", "TEMPORARY", "THEN", "TO", "TRANSACTION", "TRIGGER",
        "UNION", "UNIQUE", "UPDATE", "USING", "VACUUM", "VALUES", "VIEW",
        "VIRTUAL", "WHEN", "WHERE", "WITHOUT",
    ]))
    """SQLite data types."""
    TYPEWORDS = map(unicode, sorted([
        "BLOB",
        "INTEGER", "BIGINT", "INT", "INT2", "INT8", "MEDIUMINT", "SMALLINT",
                   "TINYINT", "UNSIGNED",
        "NUMERIC", "BOOLEAN", "DATE", "DATETIME", "DECIMAL",
        "TEXT", "CHARACTER", "CLOB", "NCHAR", "NVARCHAR", "VARCHAR", "VARYING",
        "REAL", "DOUBLE", "FLOAT", "PRECISION",
    ]))
    AUTOCOMP_STOPS = " .,;:([)]}'\"\\<>%^&+-=*/|`"
    """String length from which autocomplete starts."""
    AUTOCOMP_LEN = 2
    FONT_FACE = "Courier New" if os.name == "nt" else "Courier"

    def __init__(self, *args, **kwargs):
        wx.stc.StyledTextCtrl.__init__(self, *args, **kwargs)
        self.autocomps_added = set(["sqlite_master"])
        # All autocomps: added + KEYWORDS
        self.autocomps_total = self.KEYWORDS
        # {word.upper(): set(words filled in after word+dot), }
        self.autocomps_subwords = {}

        self.SetLexer(wx.stc.STC_LEX_SQL)
        self.SetMarginWidth(1, 0) # Get rid of left margin
        self.SetTabWidth(4)
        # Keywords must be lowercase, required by StyledTextCtrl
        self.SetKeyWords(0, u" ".join(self.KEYWORDS + self.TYPEWORDS).lower())
        self.AutoCompStops(self.AUTOCOMP_STOPS)
        self.SetWrapMode(wx.stc.STC_WRAP_WORD)
        self.SetCaretLineBackAlpha(20)
        self.SetCaretLineVisible(True)
        self.AutoCompSetIgnoreCase(True)
        self.Bind(wx.EVT_KEY_DOWN,           self.OnKeyDown)
        self.Bind(wx.EVT_KILL_FOCUS,         self.OnKillFocus)
        self.Bind(wx.EVT_SYS_COLOUR_CHANGED, self.OnSysColourChange)
        self.Bind(wx.stc.EVT_STC_ZOOM,       self.OnZoom)

        self.SetStyleSpecs()

        """
        This is how a non-sorted case-insensitive list can be used.
        self.Bind(wx.stc.EVT_STC_USERLISTSELECTION, self.OnUserListSelected)
        # listType must be > 0, value is not important for STC.
        self.UserListShow(listType=1, itemList=u" ".join(self.autocomps_total))
        def OnUserListSelected(self, event):
            text = event.GetText()
            if text:
                pos = 1#self._posBeforeCompList
                self.SetTargetStart(pos)
                self.SetTargetEnd(self.GetCurrentPos())
                self.ReplaceTarget("")
                self.InsertText(pos, text)
                self.GotoPos(pos + len(text))
        """


    def SetStyleSpecs(self):
        """Sets STC style colours."""
        fgcolour, bgcolour, highcolour = (
            wx.SystemSettings.GetColour(x).GetAsString(wx.C2S_HTML_SYNTAX)
            for x in (wx.SYS_COLOUR_BTNTEXT, wx.SYS_COLOUR_WINDOW
                      if self.Enabled else wx.SYS_COLOUR_BTNFACE,
                      wx.SYS_COLOUR_HOTLIGHT)
        )


        self.SetCaretForeground(fgcolour)
        self.SetCaretLineBackground("#00FFFF")
        self.StyleSetSpec(wx.stc.STC_STYLE_DEFAULT,
                          "face:%s,back:%s,fore:%s" % (self.FONT_FACE, bgcolour, fgcolour))
        self.StyleClearAll() # Apply the new default style to all styles
        self.StyleSetSpec(wx.stc.STC_SQL_DEFAULT,   "face:%s" % self.FONT_FACE)
        self.StyleSetSpec(wx.stc.STC_SQL_STRING,    "fore:#FF007F") # "
        self.StyleSetSpec(wx.stc.STC_SQL_CHARACTER, "fore:#FF007F") # "
        self.StyleSetSpec(wx.stc.STC_SQL_QUOTEDIDENTIFIER, "fore:%s" % highcolour)
        self.StyleSetSpec(wx.stc.STC_SQL_WORD,  "fore:%s,bold" % highcolour)
        self.StyleSetSpec(wx.stc.STC_SQL_WORD2, "fore:%s,bold" % highcolour)
        self.StyleSetSpec(wx.stc.STC_SQL_USER1, "fore:%s,bold" % highcolour)
        self.StyleSetSpec(wx.stc.STC_SQL_USER2, "fore:%s,bold" % highcolour)
        self.StyleSetSpec(wx.stc.STC_SQL_USER3, "fore:%s,bold" % highcolour)
        self.StyleSetSpec(wx.stc.STC_SQL_USER4, "fore:%s,bold" % highcolour)
        self.StyleSetSpec(wx.stc.STC_SQL_SQLPLUS, "fore:#ff0000,bold")
        self.StyleSetSpec(wx.stc.STC_SQL_SQLPLUS_COMMENT, "back:#ffff00")
        self.StyleSetSpec(wx.stc.STC_SQL_SQLPLUS_PROMPT,  "back:#00ff00")
        # 01234567890.+-e
        self.StyleSetSpec(wx.stc.STC_SQL_NUMBER, "fore:#FF00FF")
        # + - * / % = ! ^ & . , ; <> () [] {}
        self.StyleSetSpec(wx.stc.STC_SQL_OPERATOR, "fore:%s" % highcolour)
        # --...
        self.StyleSetSpec(wx.stc.STC_SQL_COMMENTLINE, "fore:#008000")
        # #...
        self.StyleSetSpec(wx.stc.STC_SQL_COMMENTLINEDOC, "fore:#008000")
        # /*...*/
        self.StyleSetSpec(wx.stc.STC_SQL_COMMENT, "fore:#008000")
        self.StyleSetSpec(wx.stc.STC_SQL_COMMENTDOC, "fore:#008000")
        self.StyleSetSpec(wx.stc.STC_SQL_COMMENTDOCKEYWORD, "back:#AAFFAA")
        self.StyleSetSpec(wx.stc.STC_SQL_COMMENTDOCKEYWORDERROR, "back:#AAFFAA")

        self.StyleSetSpec(wx.stc.STC_STYLE_BRACELIGHT, "fore:%s" % highcolour)
        self.StyleSetSpec(wx.stc.STC_STYLE_BRACEBAD, "fore:#FF0000")


    def AutoCompAddWords(self, words):
        """Adds more words used in autocompletion."""
        self.autocomps_added.update(words)
        # A case-insensitive autocomp has to be sorted, will not work
        # properly otherwise. UserList would support arbitrarily sorting.
        self.autocomps_total = sorted(list(self.autocomps_added) +
                                      map(unicode, self.KEYWORDS),
                                      cmp=self.stricmp)


    def AutoCompAddSubWords(self, word, subwords):
        """
        Adds more subwords used in autocompletion, will be shown after the word
        and a dot.
        """
        word, subwords = unicode(word), map(unicode, subwords)
        if word not in self.autocomps_added:
            self.AutoCompAddWords([word])
        if subwords:
            word_key = word.upper()
            self.autocomps_subwords.setdefault(word_key, set())
            self.autocomps_subwords[word_key].update(subwords)


    def OnKillFocus(self, event):
        """Handler for control losing focus, hides autocomplete."""
        self.AutoCompCancel()


    def OnSysColourChange(self, event):
        """Handler for system colour change, updates STC styling."""
        event.Skip()
        self.SetStyleSpecs()


    def OnZoom(self, event):
        """Disables zoom."""
        if self.Zoom: self.Zoom = 0


    def OnKeyDown(self, event):
        """
        Shows autocomplete if user is entering a known word, or pressed
        Ctrl-Space. Added autocomplete words are listed first, SQL keywords
        second.
        """
        skip = True
        if self.CallTipActive():
            self.CallTipCancel()
        if not self.AutoCompActive() and not event.AltDown():
            do_autocomp = False
            words = self.autocomps_total
            autocomp_len = 0
            if wx.WXK_SPACE == event.UnicodeKey and event.CmdDown():
                # Start autocomp when user presses Ctrl+Space
                do_autocomp = True
            elif not event.CmdDown():
                # Check if we have enough valid text to start autocomplete
                char = None
                try: # Not all keycodes can be chars
                    char = chr(event.UnicodeKey).decode("latin1")
                except Exception:
                    pass
                if char not in [wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, 10, 13] \
                and char is not None:
                    # Get a slice of the text on the current text up to caret.
                    line_text = self.GetTextRange(
                        self.PositionFromLine(self.GetCurrentLine()),
                        self.GetCurrentPos()
                    )
                    text = u""
                    for last_word in re.findall("(\\w+)$", line_text):
                        text += last_word
                    text = text.upper()
                    if "." == char:
                        # User entered "word.", show subword autocompletion if
                        # defined for the text.
                        if text in self.autocomps_subwords:
                            words = sorted(
                                self.autocomps_subwords[text], cmp=self.stricmp
                            )
                            do_autocomp = True
                            skip = False
                            self.AddText(char)
                    else:
                        text += char
                        if len(text) >= self.AUTOCOMP_LEN and any(x for x in
                        self.autocomps_total if x.upper().startswith(text)):
                            do_autocomp = True
                            current_pos = self.GetCurrentPos() - 1
                            while chr(self.GetCharAt(current_pos)).isalnum():
                                current_pos -= 1
                            autocomp_len = self.GetCurrentPos() - current_pos - 1
            if do_autocomp:
                if skip: event.Skip()
                self.AutoCompShow(autocomp_len, u" ".join(words))
        elif self.AutoCompActive() and wx.WXK_DELETE == event.KeyCode:
            self.AutoCompCancel()
        if skip: event.Skip()


    def stricmp(self, a, b):
        return cmp(a.lower(), b.lower())



class SearchableStyledTextCtrl(wx.Panel):
    """
    A StyledTextCtrl with a search bar that appears on demand, top or bottom.
    Search bar has a text box, next-previous buttons, search options and a
    close button. Next/previous buttons set search direction: after clicking
    "Previous", pressing Enter in search box searches upwards.

    Bar appears on pressing Ctrl-F in the control, or clicking the search icon
    in the right corner (bottom by default).

    @author    Erki Suurjaak
    @created   07.01.2012
    @modified  08.02.2012
    """

    """Ctrl-hotkey for showing-focusing search bar."""
    SEARCH_HOTKEY_CODE = ord("F")

    """Label before the search box."""
    SEARCH_LABEL = "Find: "

    """Label for the Next button."""
    BUTTON_NEXT_LABEL = " Next"

    """Label for the Previous button."""
    BUTTON_PREV_LABEL = " Previous"

    """Label for the "Match case" checkbox."""
    CB_CASE_LABEL = "Match case"

    """Label for the "Match whole word" checkbox."""
    CB_WHOLEWORD_LABEL = "Whole word"

    """Label for the "Match regex" checkbox."""
    CB_REGEX_LABEL = "Regex"

    """Width of the search box, in pixels."""
    SEARCH_WIDTH = 150

    """Background colour for the search edit box if no match found."""
    SEARCH_NOMATCH_BGCOLOUR = wx.Colour(255, 102, 102) # "#FF6666"

    """Foreground colour for the search edit box if no match found."""
    SEARCH_NOMATCH_FGCOLOUR = wx.Colour(255, 255, 255) # "#FFFFFF"

    """Font colour of descriptive text in the search box."""
    SEARCH_DESCRIPTIVE_COLOUR = None # Postpone to after wx.App creation

    """Text to be displayed in the search box when it"s empty and unfocused."""
    SEARCH_DESCRIPTIVE_TEXT = "Search for.."

    """Background colour for selected matched text in the control."""
    MATCH_SELECTED_BGCOLOUR = wx.Colour(10, 36, 106) # "#0A246A"

    """Foreground colour for search buttons."""
    BUTTON_FGCOLOUR = wx.Colour(71, 83, 88) # "#475358"

    """Top background colour for search button gradient."""
    BUTTON_BGCOLOUR_TOP = wx.Colour(254, 254, 254) # "#FEFEFE"

    """Middle background colour for search button gradient."""
    BUTTON_BGCOLOUR_MIDDLE = wx.Colour(236, 236, 236) # "#ECECEC"

    """Bottom background colour for search button gradient."""
    BUTTON_BGCOLOUR_BOTTOM = wx.Colour(223, 223, 223) # "#DFDFDF"

    """Image for the close button."""
    IMG_CLOSE = wx.lib.embeddedimage.PyEmbeddedImage(
        "iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAYAAADED76LAAAAAXNSR0IArs4c6QAAAARnQ"
        "U1BAACxjwv8YQUAAAAgY0hSTQAAeiYAAICEAAD6AAAAgOgAAHUwAADqYAAAOpgAABdwnL"
        "pRPAAAABp0RVh0U29mdHdhcmUAUGFpbnQuTkVUIHYzLjUuMTAw9HKhAAAAUklEQVQoU2N"
        "Yu2nLf7eg8P9AwICMQWIgOQYQA4ZhCpDFwLpgAhWNLf9BGFkD3FhkCRAbZhpcQXlDM1wn"
        "iI2iAGYkSAJZIUgRYUcuX7MOpzdBcgBnRZ25rvtD2gAAAABJRU5ErkJggg==")

    """Image for the Previous button."""
    IMG_PREV = wx.lib.embeddedimage.PyEmbeddedImage(
        "iVBORw0KGgoAAAANSUhEUgAAAAYAAAAGCAYAAADgzO9IAAAAAXNSR0IArs4c6QAAAARnQ"
        "U1BAACxjwv8YQUAAAAgY0hSTQAAeiYAAICEAAD6AAAAgOgAAHUwAADqYAAAOpgAABdwnL"
        "pRPAAAABp0RVh0U29mdHdhcmUAUGFpbnQuTkVUIHYzLjUuMTAw9HKhAAAAQklEQVQYV2P"
        "4//8/Aww/efr0f3v/JCD3PwNccPmadf/9o+L/uwWFQySOnjj5PzWvCCwAw/glYOaDjPIO"
        "i0YYhctyAJvWYR0gpxhPAAAAAElFTkSuQmCC")

    """Image for the Next button."""
    IMG_NEXT = wx.lib.embeddedimage.PyEmbeddedImage(
        "iVBORw0KGgoAAAANSUhEUgAAAAYAAAAGCAYAAADgzO9IAAAAAXNSR0IArs4c6QAAAARnQ"
        "U1BAACxjwv8YQUAAAAgY0hSTQAAeiYAAICEAAD6AAAAgOgAAHUwAADqYAAAOpgAABdwnL"
        "pRPAAAABp0RVh0U29mdHdhcmUAUGFpbnQuTkVUIHYzLjUuMTAw9HKhAAAARElEQVQYV2P"
        "4//8/Q3v/pP9Pnj4FMv8zwDCY4RYU/t8/Kv7/8jXr4JJwCZAkCKfmFf0/euIkRCtMEKuE"
        "d1g0plHYLAcAYhZhHfMXUEMAAAAASUVORK5CYII=")

    """Image for toggle chat search bar button."""
    IMG_TOGGLE = wx.lib.embeddedimage.PyEmbeddedImage(
        "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAGXRFWHRTb2Z0d2FyZQBBZG9i"
        "ZSBJbWFnZVJlYWR5ccllPAAABBJJREFUeNq0Vm1oW1UYPveem3tvc7v0Nk269SOxJCVZqR3b"
        "0qyhbm5WaLvOUf/LNh2yDqQgFIqwKZsKxf7Zn03ETWHtLxGRqrNu1kLcxlyzgKmjwVl0I62a"
        "ffUjmqTN/dh7bm/LXdqbdYIHHs7lvOc878d53/dcSlVV9H8Oykzg9/s1UBSFMMbaDHAC6kC8"
        "EWDTt84DkmBoHHCPGCzLMiLz0NAQYsyI8wYH2GEvrww8u2O3z+Wtq6ze5Cy1F7Ncam52PhaL"
        "3b4aHpl4kJyOwr4xwMIqD0yIidUcoHX7rradjbs7tllYjhWtLFNRyluN++4kZ2dGh7+KRi9/"
        "dxmsvwRY0Dzw+XyorKwMORwOtNZ9wFqo8fn2XaEXOxspmqYxTSGnjePz91U5SkqaWzuDqqpQ"
        "kfAwCVuYrNNerxeJoogkSVoFiOXGUmdFMLhn31ZCTg5YOQYzmKLzFZA1gWeZppZ92yCUQXJW"
        "W1cUpVAS1G8JveBjeZ4D5zT3UpmcHJ/OzZsdwBbeEniupe7CZ5/Wk8tniKUFRpVnc0OFccEC"
        "MSrbwFkEDltYhsZG2UJOkX6/+0/as3lLJfBWaR48QUGJKNpt4OPK5bgcVojS48TGMJFZLLXb"
        "gLdkPQpojCmsKJRMrlvLVxNyLTz0kgKYMfBq30wulyukIJWafZAWxPIiSVbl9Vbvv3MP08Cb"
        "0ixcK3sM+DM+Hk1aWbySloqKTHsLkXEWzMZjkXvkrKaAlHUBjI9888UkkhdQEYtJNaOcpJh6"
        "IsmKIjAS/+3Q53FyVlMgCAIqgGzij8m5wXNnbopFTDHcLp/NyWvmNU1RNIvRhsGzH8biN8cj"
        "6XT6L229QCjtUCN7oNLrgg3+V0/1v/uLgBeLeRbbGExzhBBaCAUXyvAWLKhSprjv/RPR82dP"
        "h7PZ7Ggmk1nKLBNyB5C3VFe7Wg4ePHSkv/+DwRs3Ird+/OFi8pVDr/s693e43G6XAxoZNT01"
        "Pfv9pYt3Pjn3cfy3W7+GGYYZ5jgus9LLmpub88nLgbzV7X5m5+HDR7r6+t4biETGRhcXFy+A"
        "rIh0VUAN8VDf/xBwW++iCZZlkc1mQ6AIJRKJVR5sAvK9NTWepqNHu7tOnjxGyK8A+TDI7ut7"
        "Ek/z4BgVVAD5fo+ndnt3d2/X8eM9A9ev/zQG5F+D7C7ptOTRedqxrKAKyF+urfU39PS83dXb"
        "+8bAtWtXfwbyL4H4b9IQ1/u0kvqBDDK0y/p6FAqF3jxw4LWPJiam1La2jvNWq/UteCar/4vF"
        "eW/JUgsJBAK9k5P31fb2lwj5O0DsJY1TB2MA1kEbQBmwSgFZdLrd7iaovMaZmRkG8ncEBFNo"
        "qYOSopINsxkUHctnHlNA/g5Y3VpK32SEUgBq3vcyVhQ8EmAAk5L6w4z4Fw0AAAAASUVORK5C"
        "YII="
    )


    def __init__(self, parent, id=wx.ID_ANY, pos=wx.DefaultPosition,
                 size=(300, 40), style=0, name=wx.stc.STCNameStr,
                 searchBarPos=wx.BOTTOM, searchDirection=wx.DOWN):
        """
        Creates a new searchable StyledTextCtrl instance, with the search bar
        hidden.

        @param   searchPos        vertical position for search bar,
                                  wx.BOTTOM (default) or wx.TOP
        @param   searchDirection  initial search direction,
                                  wx.DOWN (default) or wx.UP
        """
        wx.Panel.__init__(self, parent=parent, pos=pos,
            size=size, style=style | wx.TAB_TRAVERSAL
        )
        if not SearchableStyledTextCtrl.SEARCH_DESCRIPTIVE_COLOUR:
            desccolour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_DESKTOP)
            SearchableStyledTextCtrl.SEARCH_DESCRIPTIVE_COLOUR = desccolour

        self._search_direction = wx.DOWN if (searchDirection == wx.DOWN) \
                                 else wx.UP
        self._search_pos = -1       # Current search caret position
        self._search_text = ""      # Current search text
        self._search_at_end = False # Is current search position last found?

        self._bar_pos = wx.BOTTOM if (searchBarPos == wx.BOTTOM) else wx.TOP
        self.Sizer = wx.BoxSizer(wx.VERTICAL)

        # Remove border bits from given style, as the border style will be set
        # to the wrapping panel.
        nobits = [wx.BORDER_DOUBLE, wx.BORDER_RAISED, wx.BORDER_SIMPLE,
            wx.BORDER_STATIC, wx.BORDER_SUNKEN, wx.BORDER_THEME, wx.BORDER
        ]
        style_sub = functools.reduce(lambda a, b: a & ~b, nobits,
                                     style | wx.BORDER_NONE)
        self._stc = wx.stc.StyledTextCtrl(self, id, style=style_sub, name=name)

        bmp = self.IMG_TOGGLE.GetBitmap()
        buttonsize = bmp.Width + 4, bmp.Height + 4
        try: # ShapedButton might be unavailable if PIL not installed
            self._button_toggle = wx.lib.agw.shapedbutton.SBitmapButton(
                parent=self._stc, id=wx.ID_ANY, size=buttonsize, bitmap=bmp)
            self._button_toggle.SetUseFocusIndicator(False) # Hide focus marquee
        except Exception:
            self._button_toggle = wx.BitmapButton(self._stc, wx.ID_ANY, bmp,
                buttonsize, style = wx.NO_BORDER)
            bgcolour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)
            self._button_toggle.BackgroundColour = bgcolour
        self._button_toggle.SetToolTip("Show search bar (Ctrl-F)")

        panel = self._panel_bar = wx.Panel(parent=self)
        sizer_bar = panel.Sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._label_search = wx.StaticText(panel, label=self.SEARCH_LABEL)
        self._edit = wx.TextCtrl(parent=panel, style=wx.TE_PROCESS_ENTER,
            value=self.SEARCH_DESCRIPTIVE_TEXT, size=(self.SEARCH_WIDTH, -1))
        self._edit.SetForegroundColour(self.SEARCH_DESCRIPTIVE_COLOUR)
        self._button_next = wx.lib.agw.gradientbutton.GradientButton(
            parent=panel, label=self.BUTTON_NEXT_LABEL, size=(-1, 26),
            bitmap=self.IMG_NEXT.GetBitmap())
        self._button_prev = wx.lib.agw.gradientbutton.GradientButton(
            parent=panel, label=self.BUTTON_PREV_LABEL, size=(-1, 26),
            bitmap=self.IMG_PREV.GetBitmap())
        for b in [self._button_next, self._button_prev]:
            b.SetForegroundColour(self.BUTTON_FGCOLOUR)
            b.SetTopStartColour(self.BUTTON_BGCOLOUR_TOP)
            b.SetTopEndColour(self.BUTTON_BGCOLOUR_MIDDLE)
            b.SetBottomStartColour(self.BUTTON_BGCOLOUR_MIDDLE)
            b.SetBottomEndColour(self.BUTTON_BGCOLOUR_BOTTOM)
            b.SetPressedTopColour(self.BUTTON_BGCOLOUR_MIDDLE)
            b.SetPressedBottomColour(self.BUTTON_BGCOLOUR_BOTTOM)
        # Linux tweak: as GradientButtons get their background from their
        # parent, and backgrounds might not propagate well through the window
        # hierarchy, set the parent background to a guaranteed proper one.
        panel.BackgroundColour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)

        self._cb_case = wx.CheckBox(parent=panel, label=self.CB_CASE_LABEL)
        self._cb_wholeword = wx.CheckBox(
            parent=panel, label=self.CB_WHOLEWORD_LABEL
        )
        self._cb_regex = wx.CheckBox(parent=panel, label=self.CB_REGEX_LABEL)
        try: # ShapedButton might be unavailable if PIL not installed
            self._button_close = wx.lib.agw.shapedbutton.SBitmapButton(
                parent=panel, id=wx.ID_ANY, size=(16, 16),
                bitmap=self.IMG_CLOSE.GetBitmap())
            self._button_close.SetUseFocusIndicator(False) # Hide focus marquee
        except Exception:
            self._button_close = wx.BitmapButton(panel, wx.ID_ANY,
                self.IMG_CLOSE.GetBitmap(), (20, 20), style = wx.NO_BORDER)
        self._button_close.SetToolTip("Hide search bar.")
        sizer_bar.Add(self._label_search, border=5,
            flag=wx.LEFT | wx.ALIGN_CENTER_VERTICAL)
        sizer_bar.Add(self._edit, border=5,
            flag=wx.LEFT | wx.ALIGN_CENTER_VERTICAL)
        sizer_bar.Add(self._button_next, border=5, flag=wx.LEFT)
        sizer_bar.Add(self._button_prev, border=5, flag=wx.LEFT)
        sizer_bar.AddStretchSpacer()
        for i in [self._cb_case, self._cb_wholeword, self._cb_regex]:
            sizer_bar.Add(i, border=5,
                flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        sizer_bar.Add(self._button_close, flag=wx.ALIGN_CENTER_VERTICAL)

        # AddMany item tuple structure: (item, proportion=0, flag=0, border=0).
        items = [(self._stc, 1, wx.EXPAND), (panel, 0, wx.EXPAND | wx.ALL, 5)]
        if self._bar_pos != wx.BOTTOM:
            item = (panel, 0, wx.EXPAND | wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
            items = [item, items[0]]
        self.Sizer.AddMany(items)
        self._panel_bar.Hide()

        self._stc.Bind(wx.EVT_KEY_UP, self.OnKeyUpCtrl)
        self._stc.Bind(wx.stc.EVT_STC_PAINTED,
                       lambda e: self.UpdateToggleButton())
        self._stc.Bind(wx.stc.EVT_STC_UPDATEUI,
                       lambda e: self.UpdateToggleButton())
        self._edit.Bind(wx.EVT_SET_FOCUS, self.OnFocusSearch)
        self._edit.Bind(wx.EVT_KILL_FOCUS, self.OnFocusSearch)
        self._edit.Bind(wx.EVT_TEXT_ENTER, lambda e: self.DoSearch())
        self._edit.Bind(wx.EVT_TEXT, self.OnTextSearch)
        self._edit.Bind(wx.EVT_KEY_DOWN, self.OnKeyDownSearch)
        self._button_next.Bind(wx.EVT_BUTTON, self.OnButtonSearchNext)
        self._button_prev.Bind(wx.EVT_BUTTON, self.OnButtonSearchPrev)
        self._button_close.Bind(wx.EVT_BUTTON, self.OnButtonClose)
        self._button_toggle.Bind(wx.EVT_BUTTON,
                                 lambda e: self.ToggleSearchBar())
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Layout()


    def SetFocusSearch(self, selectAll=True):
        """Sets focus to the search box."""
        self._edit.SetFocus()
        if selectAll:
            self._edit.SelectAll()


    def GetSearchBarPosition(self):
        """
        Returns the current vertical position of the search bar,
        wx.BOTTOM (default) or wx.TOP.
        """
        return self._bar_pos
    def SetSearchBarPosition(self, pos):
        """
        Sets the current vertical position of the search bar,
        wx.BOTTOM (default) or wx.TOP.
        """
        prev_pos = self._bar_pos
        self._bar_pos = wx.TOP if (pos == wx.TOP) else wx.BOTTOM
        if prev_pos != pos:
            item = (self._panel_bar, 0, wx.EXPAND | wx.ALL, 5)
            if pos == wx.BOTTOM:
                item = (self._panel_bar, 0, wx.EXPAND | wx.ALL, 5)
            self.Sizer.Remove(self.Sizer.GetItemIndex(self._panel_bar))
            self.Sizer.Insert(0, *item)
            self.UpdateToggleButton()
            #self.Layout()
    SearchBarPosition = property(GetSearchBarPosition, SetSearchBarPosition,
        doc=
        """
        Current vertical position of the search bar,
        wx.BOTTOM (default) or wx.TOP.
        """
    )


    def GetSearchDirection(self):
        """Returns the current search direction, wx.DOWN (default) or wx.UP."""
        return self._search_direction
    def SetSearchDirection(self, direction):
        """Sets the current search direction, wx.DOWN (default) or wx.UP."""
        self._search_direction = wx.DOWN if (direction == wx.DOWN) else wx.UP
    SearchDirection = property(GetSearchDirection, SetSearchDirection,
        doc="Current search direction, wx.DOWN (default) or wx.UP."
    )


    def GetSearchText(self):
        """Returns the currently set search text, if any."""
        return self._search_text


    def GetSearchPosition(self):
        """
        Returns the current search position, in characters. Next search
        will start from this position.
        """
        return self._search_pos
    def SetSearchPosition(self, position):
        """
        Sets the current search position, in characters. Next search
        will start from this position, or from start position if negative.
        """
        self._search_pos = int(position)
    SearchPosition = property(GetSearchPosition, SetSearchPosition, doc=\
        """
        Current search position, in characters. Next search will
        will start from this position, or from start position if negative.
        """
    )


    def IsSearchBarVisible(self):
        """Returns whether the search bar is currently visible."""
        return self._panel_bar.Shown
    def SetSearchBarVisible(self, visible=True):
        """Sets the search bar visible/hidden."""
        self._panel_bar.Shown = visible
        self._button_toggle.Shown = not visible
        self.Layout()
    SearchBarVisible = property(IsSearchBarVisible, SetSearchBarVisible, doc=\
        """Search bar visibility."""
    )


    def FindNext(self, text, flags=0, direction=wx.DOWN):
        """
        Finds and selects the next occurrence of the specified text from the
        current search position, in the current search direction.

        @param   text   text string to search
        @param   flags  search flags (wx.stc.STC_FIND_*)
        @return         position of found match, negative if no more found
        """
        pos_found = -1
        if text:
            down = (self._search_direction == wx.DOWN)
            pos = self._search_pos or (0 if down else self._stc.Length)
            if self._search_at_end and text == self._search_text:
                # Wrap search around to direction start if last search was
                # unsuccessful for the same text.
                pos = 0 if down else self._stc.Length
                self._search_at_end = False
            elif down and pos <= self.Length and text == self._search_text:
                # Increment position if searching downwards for same text, STC
                # remains stuck in last found position otherwise.
                pos += 1
            self.SetCurrentPos(pos)
            self.SetAnchor(pos)
            self.SearchAnchor()
            functions = {wx.DOWN: self.SearchNext, wx.UP: self.SearchPrev}
            final = text if type(text) is unicode else text.decode("utf-8")
            self._search_pos = functions[self._search_direction](flags, final)
            if (self._search_pos < 0):
                # There are no more matches: clear selection and reset position
                self.SetSelection(-1, 0)
                self._search_at_end = True
                self._search_pos = None
            else:
                # Match found
                pos_found = self._search_pos
                self.EnsureCaretVisible() # Scrolls to search anchor
                self._search_at_end = False
        else: # No search text at all: clear selection
            self.SetSelection(-1, 0)
        self._search_text = text
        return pos_found


    def Search(self, text, flags=0, direction=wx.DOWN, position=0):
        """
        Finds and selects the next occurrence of specified text with the
        specified settings, and sets the search parameters into the search bar.

        @param   text       text string to search
        @param   flags      search flags (wx.stc.STC_FIND_*)
        @param   direction  search direction, wx.DOWN (default) or wx.UP
        @param   position   search position, in characters
        @return             position of found match, negative if not found
        """
        self._edit.Value = text
        self._cb_case.Value = (flags & wx.stc.STC_FIND_MATCHCASE)
        self._cb_wholeword.Value = (flags & wx.stc.STC_FIND_WHOLEWORD)
        self._cb_regex.Value = (flags & wx.stc.STC_FIND_REGEXP)
        self.SearchDirection = direction
        self.SearchPosition = position
        self.DoSearch()


    def DoSearch(self):
        """
        Searches for currently entered search text from the current search
        position, in the current search direction. Search is wrapped around
        to direction start.
        """
        text = self._edit.Value
        nomatch = False
        if text and text != self.SEARCH_DESCRIPTIVE_TEXT:
            flags = 0
            if self._cb_case.Value:
                flags |= wx.stc.STC_FIND_MATCHCASE
            if self._cb_wholeword.Value:
                flags |= wx.stc.STC_FIND_WHOLEWORD
            if self._cb_regex.Value:
                flags |= wx.stc.STC_FIND_REGEXP
            nomatch = self.FindNext(text, flags, self._search_direction) < 0
        if text != self.SEARCH_DESCRIPTIVE_TEXT:
            bgcolour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)
            self._edit.SetBackgroundColour(self.SEARCH_NOMATCH_BGCOLOUR
                if nomatch else bgcolour)
            self._edit.SetForegroundColour(self.SEARCH_NOMATCH_FGCOLOUR
                if nomatch else self.ForegroundColour)
            self._edit.Refresh() # Repaint text box colours


    def ToggleSearchBar(self):
        """
        Toggles the search bar visible/hidden.
        """
        self._panel_bar.Show(not self._panel_bar.Shown)
        self._button_toggle.Show(not self._panel_bar.Shown)
        if self._panel_bar.Shown:
            self._edit.SetFocus()
            self._edit.SelectAll()
        else:
            self._stc.SetFocus()
        self.SendSizeEvent()


    def OnSize(self, event):
        """Repositions toggle search button."""
        self.Layout() # Force size update
        self.UpdateToggleButton()
        event.Skip()


    def UpdateToggleButton(self):
        """Updates the toggle button position."""
        size_btn = self._button_toggle.Size
        size_stc = self._stc.ClientRect
        newpos = wx.Point(
            size_stc.width - size_btn.width, size_stc.height - size_btn.height
        )
        if self._bar_pos != wx.BOTTOM:
            newpos.y = 0
        if self._button_toggle.Position != newpos:
            self._button_toggle.Position = newpos


    def OnButtonClose(self, event):
        """Handler for clicking the Close button, hides the search bar."""
        self.ToggleSearchBar()
        self._stc.SetFocus()


    def OnFocusSearch(self, event):
        """
        Handler for focusing/unfocusing the search control, shows/hides
        description.
        """
        if self.FindFocus() == self._edit:
            if self._edit.Value == self.SEARCH_DESCRIPTIVE_TEXT:
                self._edit.SetForegroundColour(self.ForegroundColour)
                self._edit.Value = ""
        else:
            if not self._edit.Value:
                self._edit.SetForegroundColour(self.SEARCH_DESCRIPTIVE_COLOUR)
                self._edit.Value = self.SEARCH_DESCRIPTIVE_TEXT
        event.Skip() # Allow to propagate to parent, to show having focus


    def OnKeyUpCtrl(self, event):
        """Shows and focuses search on Ctrl-F."""
        if self.SEARCH_HOTKEY_CODE == event.KeyCode and event.CmdDown():
            if not self._panel_bar.Shown:
                self.SetSearchBarVisible(True)
            self._edit.SetFocus()
            self._edit.SelectAll()
        event.Skip() # Allow event to propagate


    def OnKeyDownSearch(self, event):
        """Handler for key down in search box, hides search bar on escape."""
        if (wx.WXK_ESCAPE == event.KeyCode):
            self.SetSearchBarVisible(False)
            self._stc.SetFocus()
        else:
            event.Skip() # Allow event to propagate


    def OnTextSearch(self, event):
        """
        Handler for entering text in search box, calls search if not
        entering a regular expression.
        """
        if not self._cb_regex.Value:
            self.DoSearch()


    def OnButtonSearchNext(self, event):
        """
        Handler for the Next button, searches downwards from the current
        search position.
        """
        self._search_direction = wx.DOWN
        self.DoSearch()


    def OnButtonSearchPrev(self, event):
        """
        Handler for the Previous button, searches downwards from the current
        search position.
        """
        self._search_direction = wx.UP
        self.DoSearch()


    def __getattr__(self, name):
        """Wraps all access to StyledTextCtrl transparently."""
        attr = None
        if hasattr(SearchableStyledTextCtrl, name):
            attr = getattr(self, name)
        elif hasattr(self._stc, name):
            attr = getattr(self._stc, name)
        else:
            raise AttributeError("\"%s\" object has no attribute \"%s\"" % (
                self.__class__.__name__, name
            ))
        return attr


    STC = property(lambda s: s._stc)



TabLeftDClickEvent, EVT_TAB_LEFT_DCLICK = wx.lib.newevent.NewEvent()

class TabbedHtmlWindow(wx.Panel):
    """
    HtmlWindow with tabs for different content pages.
    """

    def __init__(self, parent, id=wx.ID_ANY, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=wx.html.HW_DEFAULT_STYLE,
                 name=""):
        wx.Panel.__init__(self, parent, pos=pos, size=size, style=style)
        # [{"title", "content", "id", "info", "scrollpos", "scrollrange"}]
        self._tabs = []
        self._default_page = ""      # Content shown on the blank page
        self._delete_callback = None # Function called after deleting a tab
        ColourManager.Manage(self, "BackgroundColour", wx.SYS_COLOUR_WINDOW)

        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        notebook = self._notebook = wx.lib.agw.flatnotebook.FlatNotebook(
            parent=self, size=(-1, 27),
            agwStyle=wx.lib.agw.flatnotebook.FNB_NO_X_BUTTON |
                     wx.lib.agw.flatnotebook.FNB_MOUSE_MIDDLE_CLOSES_TABS |
                     wx.lib.agw.flatnotebook.FNB_NO_TAB_FOCUS |
                     wx.lib.agw.flatnotebook.FNB_VC8)
        self._html = wx.html.HtmlWindow(parent=self, style=style, name=name)

        self.Sizer.Add(notebook, flag=wx.GROW)
        self.Sizer.Add(self._html, proportion=1, flag=wx.GROW)

        self._html.Bind(wx.EVT_SIZE, self._OnSize)
        notebook.GetTabArea().Bind(wx.EVT_LEFT_DCLICK, self._OnLeftDClickTabArea)
        notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self._OnChangeTab)
        notebook.Bind(wx.lib.agw.flatnotebook.EVT_FLATNOTEBOOK_PAGE_CLOSING,
                      self._OnDeleteTab)
        notebook.Bind(wx.lib.agw.flatnotebook.EVT_FLATNOTEBOOK_PAGE_DROPPED,
                      self._OnDropTab)
        self._html.Bind(wx.EVT_SCROLLWIN, self._OnScroll)

        ColourManager.Manage(notebook, "ActiveTabColour", wx.SYS_COLOUR_WINDOW)
        ColourManager.Manage(notebook, "TabAreaColour",   wx.SYS_COLOUR_BTNFACE)
        try: notebook._pages.GetSingleLineBorderColour = notebook.GetActiveTabColour
        except Exception: pass # Hack to get uniform background colour

        # Monkey-patch object with HtmlWindow and FlatNotebook attributes
        for name in ["Scroll", "GetScrollRange", "GetScrollPos",
                     "SelectAll", "SelectionToText",
                     "GetBackgroundColour", "SetBackgroundColour"]:
            setattr(self, name, getattr(self._html, name))
        for name in ["GetTabAreaColour", "SetTabAreaColour"]:
            setattr(self, name, getattr(self._notebook, name))

        self._CreateTab(0, "") # Make default empty tab in notebook with no text
        self.Layout()


    def _OnLeftDClickTabArea(self, event):
        """Fires a TabLeftDClickEvent if a tab header was double-clicked."""
        area = self._notebook.GetTabArea()
        where, tab = area.HitTest(event.GetPosition())
        if wx.lib.agw.flatnotebook.FNB_TAB == where and tab < len(self._tabs):
            wx.PostEvent(self, TabLeftDClickEvent(Data=self._tabs[tab]))


    def _OnSize(self, event):
        """
        Handler for sizing the HtmlWindow, sets new scroll position based
        previously stored one (HtmlWindow loses its scroll position on resize).
        """
        if self._tabs:
            tab = self._tabs[self._notebook.GetSelection()]
            for i in range(2):
                orient = wx.VERTICAL if i else wx.HORIZONTAL
                # Division can be > 1 on first resizings, bound it to 1.
                pos, rng = tab["scrollpos"][i], tab["scrollrange"][i]
                ratio = pos / float(rng) if rng else 0.0
                ratio = min(1, pos / float(rng) if rng else 0.0)
                tab["scrollpos"][i] = ratio * self.GetScrollRange(orient)
            # Execute scroll later as something resets it after this handler
            try:
                wx.CallLater(50, lambda:
                             self.Scroll(*tab["scrollpos"]) if self else None)
            except Exception:
                pass # CallLater fails if not called from the main thread
        event.Skip() # Allow event to propagate to wx handler



    def _OnScroll(self, event):
        """
        Handler for scrolling the window, stores scroll position
        (HtmlWindow loses it on resize).
        """
        event.Skip() # Propagate to wx handler and get updated results later
        wx.CallAfter(self._StoreScrollPos)


    def _StoreScrollPos(self):
        """Stores the current scroll position for the current tab, if any."""
        if self and self._tabs:
            tab = self._tabs[self._notebook.GetSelection()]
            tab["scrollpos"]   = [self.GetScrollPos(wx.HORIZONTAL),
                                  self.GetScrollPos(wx.VERTICAL)]
            tab["scrollrange"] = [self.GetScrollRange(wx.HORIZONTAL),
                                  self.GetScrollRange(wx.VERTICAL)]
        

    def _OnChangeTab(self, event):
        """Handler for selecting another tab in notebook, loads tab content."""
        if self._tabs:
            self.SetActiveTab(self._notebook.GetSelection())
            # Forward event to TabbedHtmlWindow listeners
            wx.PostEvent(self.GetEventHandler(), event)


    def _OnDropTab(self, event):
        """Handler for dropping a dragged tab."""
        new, old = event.GetSelection(), event.GetOldSelection()
        new = min(new, len(self._tabs) - 1) # Can go over the edge
        if self._tabs and new != old and new >= 0:
            self._tabs[old], self._tabs[new] = self._tabs[new], self._tabs[old]


    def _OnDeleteTab(self, event):
        """Handler for clicking in notebook to close a tab."""
        if not self._tabs:
            event.Veto() # User clicked to delete the default page, cancel
        else:
            nb = self._notebook
            tab = self._tabs[event.GetSelection()]
            self._tabs.remove(tab)
            if 1 == nb.GetPageCount(): # Was the only page,
                nb.SetPageText(0, "")  # reuse as default empty tab
                event.Veto()
                self._SetPage(self._default_page)
                # Default empty tab has no closing X: remove X from tab style
                style = nb.GetAGWWindowStyleFlag()
                style ^= wx.lib.agw.flatnotebook.FNB_X_ON_TAB
                nb.SetAGWWindowStyleFlag(style)
            else:
                index = min(nb.GetSelection(), nb.GetPageCount() - 2)
                self.SetActiveTab(index)
            if self._delete_callback:
                self._delete_callback(tab)


    def _CreateTab(self, index, title):
        """Creates a new tab in the tab container at specified index."""
        p = wx.Panel(parent=self, size=(0,0)) 
        p.Hide() # Dummy empty window as notebook needs something to hold
        self._notebook.InsertPage(index, page=p, text=title, select=True)


    def _SetPage(self, content):
        """Sets current HTML page content."""
        self._html.SetPage(content)
        ColourManager.Manage(self._html, "BackgroundColour", wx.SYS_COLOUR_WINDOW)


    def SetDeleteCallback(self, callback):
        """Sets the function called after deleting a tab, with tab data."""
        self._delete_callback = callback


    def SetDefaultPage(self, content):
        self._default_page = content
        if not self._tabs:
            self._SetPage(self._default_page)


    def InsertTab(self, index, title, id, content, info):
        """
        Inserts a new tab with the specified title and content at the specified
        index, and activates the new tab.
        """
        tab = {"title": title, "content": content, "id": id,
               "scrollpos": [0, 0], "scrollrange": [0, 0], "info": info}
        is_empty = bool(self._tabs)
        self._tabs.insert(index, tab)
        if is_empty:
            self._CreateTab(index, tab["title"])
        else: # First real tab: fill the default empty one
            self._notebook.SetPageText(0, tab["title"])
            # Default empty tab had no closing X: add X to tab style
            style = self._notebook.GetAGWWindowStyleFlag()
            style |= wx.lib.agw.flatnotebook.FNB_X_ON_TAB
            self._notebook.SetAGWWindowStyleFlag(style)

        self._html.Freeze()
        self._SetPage(tab["content"])
        self._html.Thaw()


    def GetTabDataByID(self, id):
        """Returns the data of the tab with the specified ID, or None."""
        result = next((x for x in self._tabs if x["id"] == id), None)
        return result


    def SetTabDataByID(self, id, title, content, info, new_id=None):
        """
        Sets the title, content and info of the tab with the specified ID.

        @param   info    additional info associated with the tab
        @param   new_id  if set, tab ID is updated to this
        """
        tab = next((x for x in self._tabs if x["id"] == id), None)
        if tab:
            tab["title"], tab["content"], tab["info"] = title, content, info
            if new_id is not None:
                tab["id"] = new_id
            self._notebook.SetPageText(self._tabs.index(tab), tab["title"])
            self._notebook.Refresh()
            if self._tabs[self._notebook.GetSelection()] == tab:
                self._html.Freeze()
                self._SetPage(tab["content"])
                self._html.Scroll(*tab["scrollpos"])
                self._html.Thaw()


    def SetActiveTab(self, index):
        """Sets active the tab at the specified index."""
        tab = self._tabs[index]
        self._notebook.SetSelection(index)
        self._html.Freeze()
        self._SetPage(tab["content"])
        self._html.Scroll(*tab["scrollpos"])
        self._html.Thaw()


    def SetActiveTabByID(self, id):
        """Sets active the tab with the specified ID."""
        tab = next((x for x in self._tabs if x["id"] == id), None)
        index = self._tabs.index(tab)
        self._notebook.SetSelection(index)
        self._html.Freeze()
        self._SetPage(tab["content"])
        self._html.Scroll(*tab["scrollpos"])
        self._html.Thaw()


    def GetActiveTabData(self):
        """Returns all the data for the active tab."""
        if self._tabs:
            return self._tabs[self._notebook.GetSelection()]


    def GetTabCount(self):
        """Returns the number of tabs (default empty tab is not counted)."""
        return len(self._tabs)



class TextCtrlAutoComplete(wx.TextCtrl):
    """
    A text control with autocomplete using a dropdown list of choices. During
    typing, the first matching choice is appended to textbox value, with the
    appended text auto-selected.
    Fires a wx.EVT_LIST_DELETE_ALL_ITEMS event if user clicked to clear all
    choices.

    If wx.PopupWindow is not available (Mac), behaves like a common TextCtrl.
    Based on TextCtrlAutoComplete by Michele Petrazzo, from a post
    on 09.02.2006 in wxPython-users thread "TextCtrlAutoComplete",
    http://wxpython-users.1045709.n5.nabble.com/TextCtrlAutoComplete-td2348906.html
    """
    DROPDOWN_COUNT_PER_PAGE = 8
    DROPDOWN_CLEAR_TEXT = "Clear search history"


    def __init__(self, parent, choices=None, description="",
                 **kwargs):
        """
        @param   choices      list of auto-complete choices, if any
        @param   description  description text shown if nothing entered yet
        """
        if "style" in kwargs:
            kwargs["style"] = wx.TE_PROCESS_ENTER | kwargs["style"]
        else:
            kwargs["style"] = wx.TE_PROCESS_ENTER
        wx.TextCtrl.__init__(self, parent, **kwargs)
        self._text_colour = self._desc_colour = self._clear_colour = None
        ColourManager.Manage(self, "_text_colour",  wx.SYS_COLOUR_BTNTEXT)
        ColourManager.Manage(self, "_desc_colour",  wx.SYS_COLOUR_GRAYTEXT)
        ColourManager.Manage(self, "_clear_colour", wx.SYS_COLOUR_HOTLIGHT)

        self._choices = [] # Ordered case-insensitively
        self._choices_lower = [] # Cached lower-case choices
        self._ignore_textchange = False # ignore next OnText
        self._skip_autocomplete = False # skip setting textbox value in OnText
        self._lastinsertionpoint = None # For whether to show dropdown on click
        self._value_last = "" # For resetting to last value on Esc
        self._description = description
        self._description_on = False # Is textbox filled with description?
        if not self.Value:
            self.Value = self._description
            self.SetForegroundColour(self._desc_colour)
            self._description_on = True
        try:
            self._listwindow = wx.PopupWindow(self)
            self._listbox = wx.ListCtrl(self._listwindow, pos=(0, 0),
                                        style=wx.BORDER_SIMPLE | wx.LC_REPORT
                                        | wx.LC_SINGLE_SEL | wx.LC_NO_HEADER)
        except AttributeError:
            # Probably Mac, where wx.PopupWindow does not exist yet as of 2013.
            self._listbox = self._listwindow = None

        if self._listbox:
            ColourManager.Manage(self._listbox, "TextColour", wx.SYS_COLOUR_GRAYTEXT)
            self.SetChoices(choices or [])
            self._cursor = None
            # For changing cursor when hovering over final "Clear" item.
            self._cursor_action_hover = wx.Cursor(wx.CURSOR_HAND)
            self._cursor_default      = wx.Cursor(wx.CURSOR_DEFAULT)

            gp = self
            while gp is not None:
                # Dropdown has absolute position, must be moved when parent is.
                gp.Bind(wx.EVT_MOVE,                self.OnSizedOrMoved, gp)
                gp.Bind(wx.EVT_SIZE,                self.OnSizedOrMoved, gp)
                gp = gp.GetParent()
            self.Bind(wx.EVT_TEXT,                  self.OnText, self)
            self.Bind(wx.EVT_KEY_DOWN,              self.OnKeyDown, self)
            self.Bind(wx.EVT_LEFT_DOWN,             self.OnClickDown, self)
            self.Bind(wx.EVT_LEFT_UP,               self.OnClickUp, self)
            self._listbox.Bind(wx.EVT_LEFT_DOWN,    self.OnListClick)
            self._listbox.Bind(wx.EVT_LEFT_DCLICK,  self.OnListDClick)
            self._listbox.Bind(wx.EVT_MOUSE_EVENTS, self.OnMouse)
            self._listwindow.Bind(wx.EVT_LISTBOX,   self.OnListItemSelected,
                                  self._listbox)
        self.Bind(wx.EVT_SET_FOCUS,                 self.OnFocus, self)
        self.Bind(wx.EVT_KILL_FOCUS,                self.OnFocus, self)
        self.Bind(wx.EVT_SYS_COLOUR_CHANGED,        self.OnSysColourChange)


    def OnSysColourChange(self, event):
        """
        Handler for system colour change, updates text colours.
        """
        event.Skip()
        colour = self._desc_colour if self._description_on else self._text_colour
        self.SetForegroundColour(colour)
        self.SetChoices(self._choices)


    def OnListClick(self, event):
        """Handler for clicking the dropdown list, selects the clicked item."""
        index, flag = self._listbox.HitTest(event.GetPosition())
        if len(self._choices) > index >= 0:
            self._listbox.Select(index)
        elif index == len(self._choices) + 1: # Clicked "Clear choices" item
            event = wx.CommandEvent(wx.wxEVT_COMMAND_LIST_DELETE_ALL_ITEMS,
                                    self.GetId())
            wx.PostEvent(self, event)


    def OnListDClick(self, event):
        """
        Handler for double-clicking the dropdown list, sets textbox value to
        selected item and fires TEXT_ENTER.
        """
        self.SetValueFromSelected()
        enterevent = wx.CommandEvent(wx.wxEVT_COMMAND_TEXT_ENTER, self.GetId())
        wx.PostEvent(self, enterevent)


    def OnSizedOrMoved(self, event):
        """
        Handler for moving or sizing the control or any parent, hides dropdown.
        """
        event.Skip()
        if self: self.ShowDropDown(False)


    def OnClickDown(self, event):
        """
        Handler for clicking and holding left mouse button, remembers click
        position.
        """
        event.Skip()
        self._lastinsertionpoint = self.GetInsertionPoint()


    def OnClickUp(self, event):
        """
        Handler for releasing left mouse button, toggles dropdown list
        visibility on/off if clicking same spot in textbox.
        """
        event.Skip()
        if (self.GetInsertionPoint() == self._lastinsertionpoint):
            self.ShowDropDown(not self._listwindow.Shown)


    def OnListItemSelected(self, event):
        """
        Handler for selecting an item in the dropdown list, sets its value to
        textbox.
        """
        event.Skip()
        self.SetValueFromSelected()


    def OnFocus(self, event):
        """
        Handler for focusing/unfocusing the control, shows/hides description.
        """
        event.Skip() # Allow to propagate to parent, to show having focus
        if self and self.FindFocus() is self:
            if self._description_on:
                self.Value = ""
            self._value_last = self.Value
            self.SelectAll()
        elif self:
            if self._description and not self.Value:
                # Control has been unfocused, set and colour description
                self.Value = self._description
                self.SetForegroundColour(self._desc_colour)
                self._description_on = True
            if self._listbox:
                self.ShowDropDown(False)


    def OnMouse(self, event):
        """
        Handler for mouse events, changes cursor to pointer if hovering over
        action item like "Clear history".
        """
        event.Skip()
        index, flag = self._listbox.HitTest(event.GetPosition())
        if index == self._listbox.ItemCount - 1:
            if self._cursor != self._cursor_action_hover:
                self._cursor = self._cursor_action_hover
                self._listbox.SetCursor(self._cursor_action_hover)
        elif self._cursor == self._cursor_action_hover:
            self._cursor = self._cursor_default
            self._listbox.SetCursor(self._cursor_default)


    def OnKeyDown(self, event):
        """Handler for any keypress, changes dropdown items."""
        if not self._choices: return event.Skip()

        skip = True
        visible = self._listwindow.Shown
        selected = self._listbox.GetFirstSelected()
        selected_new = None
        if event.KeyCode in KEYS.UP + KEYS.DOWN:
            if visible:
                step = 1 if event.KeyCode in KEYS.DOWN else -1
                itemcount = len(self._choices)
                selected_new = min(itemcount - 1, max(0, selected + step))
                self._listbox.Select(selected_new)
                ensured = selected_new + (0
                          if selected_new != len(self._choices) - 1 else 2)
                self._listbox.EnsureVisible(ensured)
            self.ShowDropDown()
            skip = False
        elif event.KeyCode in KEYS.PAGING:
            if visible:
                step = 1 if event.KeyCode in KEYS.PAGEDOWN else -1
                self._listbox.ScrollPages(step)
                itemcount = len(self._choices)
                countperpage = self._listbox.CountPerPage
                next_pos = selected + countperpage * step
                selected_new = min(itemcount - 1, max(0, next_pos))
                ensured = selected_new + (0
                          if selected_new != len(self._choices) - 1 else 2)
                self._listbox.EnsureVisible(ensured)
                self._listbox.Select(selected_new)
            self.ShowDropDown()
            skip = False
        elif event.KeyCode in KEYS.DELETE + (wx.WXK_BACK, ):
            self._skip_autocomplete = True
            self.ShowDropDown()

        if visible:
            if selected_new is not None: # Replace textbox value with new text
                self._ignore_textchange = True
                self.Value = self._listbox.GetItemText(selected_new)
                self.SetInsertionPointEnd()
            if event.KeyCode in KEYS.ENTER:
                self.ShowDropDown(False)
            if wx.WXK_ESCAPE == event.KeyCode:
                self.ShowDropDown(False)
                skip = False
        else:
            if wx.WXK_ESCAPE == event.KeyCode:
                if self._value_last != self.Value:
                    self.Value = self._value_last
                    self.SelectAll()
            elif event.CmdDown() and event.KeyCode in map(ord, "AH"):
                # Avoid opening dropdown on Ctrl-A (select all) or Ctrl-H (backspace)
                self._ignore_textchange = True
        if skip: event.Skip()


    def OnText(self, event):
        """
        Handler for changing textbox value, auto-completes the text and selects
        matching item in dropdown list, if any.
        """
        event.Skip()
        if self._ignore_textchange:
            self._ignore_textchange = self._skip_autocomplete = False
            return
        text = self.Value
        if text and not self._description_on:
            found = False
            text_lower = text.lower()
            for i, choice in enumerate(self._choices):
                if self._choices_lower[i].startswith(text_lower):
                    choice = text + choice[len(text):]
                    found = True
                    self.ShowDropDown(True)
                    self._listbox.Select(i)
                    self._listbox.EnsureVisible(i)
                    if not self._skip_autocomplete:
                        # Use a callback function to change value - changing
                        # value inside handler causes multiple events in Linux.
                        def autocomplete_callback(choice):
                            if self and self.Value == text: # Can have changed
                                self._ignore_textchange = True # To skip OnText
                                self.Value = choice # Auto-complete text
                                self.SetSelection(len(text), -1) # Select added
                        wx.CallAfter(autocomplete_callback, choice)
                    break
            if not found: # Deselect currently selected item
                self._listbox.Select(self._listbox.GetFirstSelected(), False)
        else:
            self.ShowDropDown(False)
        self._skip_autocomplete = False


    def SetChoices(self, choices):
        """Sets the choices available in the dropdown list."""
        if choices:
            lower = [i.lower() for i in choices]
            sorted_all = sorted(zip(lower, choices)) # [("a", "A"), ("b", "b")]
            self._choices_lower, self._choices = map(list, zip(*sorted_all))
        else:
            self._choices_lower, self._choices = [], []

        if self._listbox:
            self._listbox.ClearAll()
            self._listbox.InsertColumn(0, "Select")
            choices = self._choices[:]
            choices += ["", self.DROPDOWN_CLEAR_TEXT] if choices else []
            for i, text in enumerate(choices):
                self._listbox.InsertItem(i, text)
            if choices: # Colour "Clear" item
                self._listbox.SetItemTextColour(i, self._clear_colour)

            itemheight = self._listbox.GetItemRect(0)[-1] if choices else 0
            itemcount = min(len(choices), self.DROPDOWN_COUNT_PER_PAGE)
            # Leave room vertically for border and padding.
            size = wx.Size(self.Size.width - 3, itemheight * itemcount + 5)
            self._listbox.Size = self._listwindow.Size = size
            # Leave room for vertical scrollbar
            self._listbox.SetColumnWidth(0, size.width - 16)
            self._listbox.SetScrollbar(wx.HORIZONTAL, 0, 0, 0)


    def SetValueFromSelected(self):
        """Sets the textbox value from the selected dropdown item, if any."""
        selected = self._listbox.GetFirstSelected()
        if len(self._choices) > selected >= 0:
            self.SetValue(self._listbox.GetItemText(selected))
            self.SetInsertionPointEnd()
            self.SetSelection(-1, -1)
            self.ShowDropDown(False)


    def ShowDropDown(self, show=True):
        """Toggles the dropdown list visibility on/off."""
        if show and self.IsShownOnScreen() and self._choices and self._listwindow:
            size = self._listwindow.GetSize()
            width, height = self.Size.width - 3, self.Size.height
            x, y = self.ClientToScreen(0, height - 2)
            if size.GetWidth() <> width:
                size.SetWidth(width)
                self._listwindow.SetSize(size)
                self._listbox.SetSize(self._listwindow.GetClientSize())
                # Leave room for vertical scrollbar
                self._listbox.SetColumnWidth(0, width - 16)
                self._listbox.SetScrollbar(wx.HORIZONTAL, 0, 0, 0)
            if y + size.GetHeight() < wx.GetDisplaySize().height:
                self._listwindow.SetPosition((x, y))
            else: # No room at the bottom: show dropdown on top of textbox
                self._listwindow.SetPosition((x, y - height - size.height))
            self._listwindow.Show()
        elif self._listwindow:
            self._listwindow.Hide()


    def IsDropDownShown(self):
        """Returns whether the dropdown window is currently shown."""
        return self._listwindow.Shown


    def GetValue(self):
        """
        Returns the current value in the text field, or empty string if filled
        with description.
        """
        value = wx.TextCtrl.GetValue(self)
        if self._description_on:
            value = ""
        return value
    def SetValue(self, value):
        """Sets the value in the text entry field."""
        self.SetForegroundColour(self._text_colour)
        self._description_on = False
        self._ignore_textchange = True
        return wx.TextCtrl.SetValue(self, value)
    Value = property(GetValue, SetValue)



def BuildHistogram(data, barsize=(3, 30), colour="#2d8b57", maxval=None):
    """
    Paints and returns (wx.Bitmap, rects) with histogram bar plot from data.

    @return   (wx.Bitmap, [(x1, y1, x2, y2), ])
    """
    global BRUSH, PEN
    bgcolour, border = "white", 1
    rect_step = barsize[0] + (1 if barsize[0] < 10 else 2)
    w, h = len(data) * rect_step + border + 1, barsize[1] + 2 * border
    bmp = wx.Bitmap(w, h)
    dc = wx.MemoryDC()
    dc.SelectObject(bmp)
    dc.Brush = BRUSH(bgcolour)
    dc.Pen = PEN(colour)
    dc.Clear()
    dc.DrawRectangle(0, 0, w, h)

    bars = []
    safediv = lambda a, b: a / float(b) if b else 0.0
    maxval = maxval if maxval is not None else max(zip(*data)[1])
    for i, (interval, val) in enumerate(data):
        h = barsize[1] * safediv(val, maxval) + 1
        if val and h < 1.5: h = 1.5 # Very low values produce no visual bar
        x = i * rect_step + border + 1
        y = bmp.Height - h
        bars.append((x, y, barsize[0], h))
    dc.Brush = BRUSH(colour)
    dc.DrawRectangleList(bars)

    dc.SelectObject(wx.NullBitmap)
    rects = [(x, border, x+w, bmp.Height - 2*border) for x, y, w, h in bars]
    return bmp, rects



def get_controls(window):
    """Returns a list of all nested controls of given window."""
    result, cc = [], list(window.Children)
    while cc:
        c = cc.pop(0)
        if isinstance(c, wx.Control): result.append(c)
        cc.extend(c.Children)
    return result
