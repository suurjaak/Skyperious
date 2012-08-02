#-*- coding: utf-8 -*-
"""
Stand-alone GUI components for wx.

@author      Erki Suurjaak
@created     13.01.2012
@modified    02.08.2012
"""
import datetime
import locale
import operator
import os
import re
import sys
import threading
import wx
import wx.html
import wx.lib.embeddedimage
import wx.lib.mixins.listctrl
import wx.stc


class SortableListView(wx.ListView, wx.lib.mixins.listctrl.ColumnSorterMixin):
    """
    A sortable list view that can be batch-populated, autosizes its columns.
    """

    def __init__(self, *args, **kwargs):
        wx.ListView.__init__(self, *args, **kwargs)
        wx.lib.mixins.listctrl.ColumnSorterMixin.__init__(self, 0)
        self.itemDataMap = {}


    def Populate(self, column_map, rows):
        """
        Populates the control with rows and columns. Re-selects the previously
        selected row, if any.

        @param   column_map     a list of (column name, column title) tuples
        @param   rows           a list of dicts, will be used in sorting.
        """
        selected_text = None
        selected_index = self.GetFirstSelected()
        if selected_index >= 0:
            selected_text = self.GetItemText(selected_index)
        selected_index = -1
        self.Freeze()
        self.ClearAll()

        col_index = 0
        # For measuring by which to set column width: header or value
        header_lengths = {} # {col_name: integer}
        col_lengths = {} # {col_name: integer}
        self.SetColumnCount(len(column_map))
        item_data_map = {}
        for col_name, col_label in column_map:
            # Keep space for sorting arrows, to decrease display changes.
            self.InsertColumn(col_index, col_label + "  ")
            col_lengths[col_name] = 0
            header_lengths[col_name] = len(col_label + "  ")
            col_index += 1
        # To map list item data ID to row, ListCtrl allows only integer per row
        row_data_map = {}
        row_index = 0
        for row in rows:
            col_name = column_map[0][0]
            col_value = "" if row[col_name] is None else unicode(row[col_name])
            # Keep space for the 0 (icon) column, to decrease display changes.
            col_lengths[col_name] = \
                max(col_lengths[col_name], len(col_value) + 3)
            self.InsertStringItem(row_index, col_value)
            row_id = id(row)
            self.SetItemData(row_index, row_id)
            item_data_map[row_id] = {0: row[col_name]}
            row_data_map[row_id] = row
            self.SetItemImage(row_index, -1)
            if selected_text == col_value:
                selected_index = row_index
            row_index += 1
        row_index = 0
        # @todo find out why doing it it one pass mixes up values between rows
        for row in rows:
            col_index = 1 # First was already inserted
            row_id = id(row)
            for col_name, col_label in column_map[col_index:]:
                col_value = "" if (col_name not in row
                                   or row[col_name] is None
                            ) else unicode(row[col_name])
                col_lengths[col_name] = \
                    max(col_lengths[col_name], len(col_value))
                self.SetStringItem(row_index, col_index, col_value)
                item_data_map[row_id][col_index] = row.get(col_name, None)
                col_index += 1
            self.SetItemColumnImage(row_index, 0, -1)
            row_index += 1
        col_index = 0
        for col_name, col_label in column_map:
            self.SetColumnWidth(col_index,
                wx.LIST_AUTOSIZE if (
                    not col_index \
                    or (col_lengths[col_name] > header_lengths[col_name])
                ) else header_lengths[col_name] * self.GetTextExtent("n")[0]
                #wx.LIST_AUTOSIZE_USEHEADER
            )
            col_index += 1
        self._data_map = row_data_map
        self.itemDataMap = item_data_map
        self._column_map = column_map
        if selected_index >= 0:
            self.Select(selected_index)
        self.Thaw()


    def RefreshItems(self):
        """
        Refreshes the content of all rows. Re-selects the previously selected
        row, if any.
        """
        selected_text = None
        selected_index = self.GetFirstSelected()
        if selected_index >= 0:
            selected_text = self.GetItemText(selected_index)
        selected_index = -1

        # For measuring by which to set column width: header or value
        header_lengths = {} # {col_name: integer}
        col_lengths = {} # {col_name: integer}
        for col_name, col_label in self._column_map:
            # Keep space for sorting arrows, to decrease display changes.
            col_lengths[col_name] = 0
            header_lengths[col_name] = len(col_label + "  ")
        self.Freeze()
        for row_index in range(self.ItemCount):
            row = self._data_map[self.GetItemData(row_index)]
            col_index = 0
            for col_name, col_label in self._column_map:
                col_value = "" if (col_name not in row
                                   or row[col_name] is None
                            ) else unicode(row[col_name])
                col_lengths[col_name] = \
                    max(col_lengths[col_name], len(col_value))
                self.SetStringItem(row_index, col_index, col_value)
                self.itemDataMap[self.GetItemData(row_index)][col_index] = \
                    row[col_name] if col_name in row else None
                if selected_text == col_value:
                    selected_index = row_index
                col_index += 1
        col_index = 0
        for col_name, col_label in self._column_map:
            self.SetColumnWidth(col_index,
                wx.LIST_AUTOSIZE if (
                    not col_index \
                    or (col_lengths[col_name] > header_lengths[col_name])
                ) else header_lengths[col_name] * self.GetTextExtent("w")[0]
                #wx.LIST_AUTOSIZE_USEHEADER
            )
            col_index += 1
        if selected_index >= 0:
            self.Select(selected_index)
        self.Thaw()


    def GetItemMappedData(self, row):
        """Returns the data mapped to the specified row."""
        data = None
        data_id = self.GetItemData(row)
        data = self._data_map.get(data_id, None)
        return data


    def OnSortOrderChanged(self):
        """
        Callback called after sort order has changed (whenever user
        clicked column header), refreshes column header sort direction info.
        """
        ARROWS = {True: u" ↓", False: u" ↑"}
        for i in range(self.ColumnCount):
            col_item = self.GetColumn(i)
            if i == self._col:
                new_item = wx.ListItem()
                new_item.Text = u"%s%s" % (
                    col_item.Text.replace(ARROWS[0], "").replace(
                        ARROWS[1], ""
                    ),
                    ARROWS[self._colSortFlag[i]]
                )
                self.SetColumn(i, new_item)
            elif filter(lambda i: i in col_item.Text, ARROWS.values()):
                # Remove the previous sort arrow
                new_item = wx.ListItem()
                new_item.Text = col_item.Text.replace(ARROWS[0], "").replace(
                    ARROWS[1], ""
                )
                self.SetColumn(i, new_item)


    def GetListCtrl(self):
        """Required by ColumnSorterMixin."""
        return self


    def GetColumnSorter(self):
        """
        Override ColumnSorterMixin.GetColumnSorter to specify our sorting,
        which accounts for None values.
        """
        sorter = self.__ColumnSorter if hasattr(self, "_data_map") \
            else wx.lib.mixins.listctrl.ColumnSorterMixin.GetColumnSorter(self)
        return sorter
            


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
        if type(item1) == unicode and type(item2) == unicode:
            cmpVal = locale.strcoll(item1, item2)
        elif type(item1) == str or type(item2) == str:
            cmpVal = locale.strcoll(unicode(item1), unicode(item2))
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
    KEYWORDS = [
        u"ABORT", u"ACTION", u"ADD", u"AFTER", u"ALL", u"ALTER", u"ANALYZE",
        u"AND", u"AS", u"ASC", u"ATTACH", u"AUTOINCREMENT", u"BEFORE",
        u"BEGIN", u"BETWEEN", u"BY", u"CASCADE", u"CASE", u"CAST", u"CHECK",
        u"COLLATE", u"COLUMN", u"COMMIT", u"CONFLICT", u"CONSTRAINT",
        u"CREATE", u"CROSS", u"CURRENT_DATE", u"CURRENT_TIME",
        u"CURRENT_TIMESTAMP", u"DATABASE", u"DEFAULT", u"DEFERRABLE",
        u"DEFERRED", u"DELETE", u"DESC", u"DETACH", u"DISTINCT", u"DROP",
        u"EACH", u"ELSE", u"END", u"ESCAPE", u"EXCEPT", u"EXCLUSIVE",
        u"EXISTS", u"EXPLAIN", u"FAIL", u"FOR", u"FOREIGN", u"FROM", u"FULL",
        u"GLOB", u"GROUP", u"HAVING", u"IF", u"IGNORE", u"IMMEDIATE", u"IN",
        u"INDEX", u"INDEXED", u"INITIALLY", u"INNER", u"INSERT", u"INSTEAD",
        u"INTERSECT", u"INTO", u"IS", u"ISNULL", u"JOIN", u"KEY", u"LEFT",
        u"LIKE", u"LIMIT", u"MATCH", u"NATURAL", u"NO", u"NOT", u"NOTNULL",
        u"NULL", u"OF", u"OFFSET", u"ON", u"OR", u"ORDER", u"OUTER", u"PLAN",
        u"PRAGMA", u"PRIMARY", u"QUERY", u"RAISE", u"REFERENCES", u"REGEXP",
        u"REINDEX", u"RELEASE", u"RENAME", u"REPLACE", u"RESTRICT", u"RIGHT",
        u"ROLLBACK", u"ROW", u"SAVEPOINT", u"SELECT", u"SET", u"TABLE",
        u"TEMP", u"TEMPORARY", u"THEN", u"TO", u"TRANSACTION", u"TRIGGER",
        u"UNION", u"UNIQUE", u"UPDATE", u"USING", u"VACUUM", u"VALUES", u"VIEW",
        u"VIRTUAL", u"WHEN", u"WHERE"
    ]
    AUTOCOMP_STOPS = " .,;:([)]}'\"\\<>%^&+-=*/|`"
    FONT_FACE = "Courier New" if os.name == "nt" else "Courier"
    """String length from which autocomplete starts."""
    AUTOCOMP_LEN = 2

    def __init__(self, *args, **kwargs):
        wx.stc.StyledTextCtrl.__init__(self, *args, **kwargs)
        self.autocomps_added = set()
        # All autocomps: added + KEYWORDS
        self.autocomps_total = self.KEYWORDS
        # {word.upper(): set(words filled in after word+dot), }
        self.autocomps_subwords = {}

        self.SetLexer(wx.stc.STC_LEX_SQL)
        self.SetMarginWidth(1, 0) # Get rid of left margin
        self.SetTabWidth(4)
        # Keywords must be lowercase, required by StyledTextCtrl
        self.SetKeyWords(0, u" ".join(self.KEYWORDS).lower())
        self.AutoCompStops(self.AUTOCOMP_STOPS)
        self.SetWrapMode(wx.stc.STC_WRAP_WORD)
        self.SetCaretLineBackground("#00FFFF")
        self.SetCaretLineBackAlpha(20)
        self.SetCaretLineVisible(True)
        self.AutoCompSetIgnoreCase(True)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)

        self.StyleSetSpec(wx.stc.STC_STYLE_DEFAULT, "face:%s" % self.FONT_FACE)
        self.StyleSetSpec(wx.stc.STC_SQL_DEFAULT, "face:%s" % self.FONT_FACE)
        self.StyleSetSpec(wx.stc.STC_SQL_STRING, "fore:#FF007F") # "
        self.StyleSetSpec(wx.stc.STC_SQL_CHARACTER, "fore:#FF007F") # "
        self.StyleSetSpec(wx.stc.STC_SQL_QUOTEDIDENTIFIER, "fore:#0000FF")
        self.StyleSetSpec(wx.stc.STC_SQL_WORD, "fore:#0000FF,bold")
        self.StyleSetSpec(wx.stc.STC_SQL_WORD2, "fore:#0000FF,bold")
        self.StyleSetSpec(wx.stc.STC_SQL_USER1, "fore:#0000FF,bold")
        self.StyleSetSpec(wx.stc.STC_SQL_USER2, "fore:#0000FF,bold")
        self.StyleSetSpec(wx.stc.STC_SQL_USER3, "fore:#0000FF,bold")
        self.StyleSetSpec(wx.stc.STC_SQL_USER4, "fore:#0000FF,bold")
        self.StyleSetSpec(wx.stc.STC_SQL_SQLPLUS, "fore:#ff0000,bold")
        self.StyleSetSpec(wx.stc.STC_SQL_SQLPLUS_COMMENT, "back:#ffff00")
        self.StyleSetSpec(wx.stc.STC_SQL_SQLPLUS_PROMPT, "back:#00ff00")
        # 01234567890.+-e
        self.StyleSetSpec(wx.stc.STC_SQL_NUMBER, "fore:#FF00FF")
        # + - * / % = ! ^ & . , ; <> () [] {}
        self.StyleSetSpec(wx.stc.STC_SQL_OPERATOR, "fore:#0000FF")
        # --...
        self.StyleSetSpec(wx.stc.STC_SQL_COMMENTLINE, "back:#AAFFAA")
        # #...
        self.StyleSetSpec(wx.stc.STC_SQL_COMMENTLINEDOC, "back:#FF0000")
        # /*...*/
        self.StyleSetSpec(wx.stc.STC_SQL_COMMENT, "back:#AAFFAA")
        self.StyleSetSpec(wx.stc.STC_SQL_COMMENTDOC, "back:#AAFFAA")
        self.StyleSetSpec(wx.stc.STC_SQL_COMMENTDOCKEYWORD, "back:#AAFFAA")
        self.StyleSetSpec(wx.stc.STC_SQL_COMMENTDOCKEYWORDERROR, "back:#AAFFAA")

        self.StyleSetSpec(wx.stc.STC_STYLE_BRACELIGHT, "fore:#0000FF")
        self.StyleSetSpec(wx.stc.STC_STYLE_BRACEBAD, "fore:#FF0000")

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


    def AutoCompAddWords(self, words):
        """Adds more words used in autocompletion."""
        self.autocomps_added.update(words)
        # A case-insensitive autocomp has to be sorted, will not work
        # properly otherwise. UserList would support arbitrarily sorting.
        self.autocomps_total = sorted(
            list(self.autocomps_added) + self.KEYWORDS, cmp=self.stricmp
        )


    def AutoCompAddSubWords(self, word, subwords):
        """
        Adds more subwords used in autocompletion, will be shown after the word
        and a dot.
        """
        if word not in self.autocomps_added:
            self.AutoCompAddWords([word])
        if subwords:
            word_key = word.upper()
            if word_key not in self.autocomps_subwords:
                self.autocomps_subwords[word_key] = set()
            self.autocomps_subwords[word_key].update(subwords)


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
            key_code = event.UnicodeKey
            if wx.WXK_SPACE == key_code and event.CmdDown():
                # Start autocomp when user presses Ctrl+Space
                do_autocomp = True
            elif not event.CmdDown():
                # Check if we have enough valid text to start autocomplete
                char = None
                try: # Not all keycodes can be chars
                    char = chr(key_code).decode("latin1")
                except:
                    pass
                if char not in [wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, 10, 13] \
                and char is not None:
                    # Get a slice of the text on the current text up to caret.
                    line_text = self.GetTextRange(
                        self.PositionFromLine(self.GetCurrentLine()),
                        self.GetCurrentPos()
                    )
                    text = u""
                    for last_word in re.findall("(\w+)$", line_text):
                        text += last_word
                    text = text.upper()
                    self.char=char
                    self.evt = event
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
                        if (len(text) >= self.AUTOCOMP_LEN) and filter(
                            lambda x: x.upper().startswith(text),
                            self.autocomps_total
                        ):
                            do_autocomp = True
                            current_pos = self.GetCurrentPos() - 1
                            while chr(self.GetCharAt(current_pos)).isalnum():
                                current_pos -= 1
                            autocomp_len = self.GetCurrentPos() - current_pos - 1
            if do_autocomp:
                if skip: event.Skip()
                self.AutoCompShow(autocomp_len, u" ".join(words))
        if skip: event.Skip()


    def stricmp(self, a, b):
        return cmp(a.lower(), b.lower())



class RangeSlider(wx.PyPanel):
    """
    A horizontal slider with two markers for selecting a value range. Supports
    numeric and date/time values.
    """
    BACKGROUND_COLOUR       = wx.Colour(255, 255, 255)
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
        wx.PyPanel.__init__(self, parent, id, pos, size,
            style | wx.FULL_REPAINT_ON_RESIZE, name
        )

        # Fill unassigned range and values with other givens, or assign
        # a default date range.
        if not rng and vals:
            rng = vals
        elif not rng:
            now = datetime.datetime.now().date()
            rng = (now - datetime.timedelta(days=3*365), now)
            vals = (now - datetime.timedelta(days=2*365),
                now - datetime.timedelta(days=1*365),
            )
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
        self._cursor_marker_hover    = wx.StockCursor(wx.CURSOR_SIZEWE)
        self._cursor_default         = wx.StockCursor(wx.CURSOR_DEFAULT)
        self._grip_area = None # Current scrollbar grip area
        self._bar_arrow_areas = None # Scrollbar arrow areas
        self._box_area = None # Current range area
        self._bar_area = None # Scrollbar area
        self.SetInitialSize(self.GetMinSize())
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
        self.Bind(wx.EVT_MOUSE_EVENTS, self.OnMouseEvent)
        self.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.OnMouseCaptureLostEvent)
        self.SetToolTipString(
            "Double-click on marker or scrollbar to maximize/restore values."
        )


    def GetLabelFormat(self):
        return self._fmt
    def SetLabelFormat(self, label_format):
        self._fmt = label_format
    LabelFormat = property(GetLabelFormat, SetLabelFormat, doc= \
        """
        Format string or function used for formatting values. Format strings
        are used as common Python format strings, except for date or time
        values they are given to strftime. Format functions are given a single
        value parameter and are expected to return a string value.
        """
    )


    def GetLeftValue(self):
        return self._vals(0)
    def SetLeftValue(self, value):
        return self.SetValue(wx.LEFT, value)
    LeftValue = property(GetLeftValue, SetLeftValue, doc= \
        "The left position value. Cannot get greater than the right value."
    )
    def GetRightValue(self):
        return self._vals(1)
    def SetRightValue(self, value, refresh=True):
        return self.SetValue(wx.RIGHT, value, refresh)
    RightValue = property(GetRightValue, SetRightValue, doc= \
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
            if value is not None:
                confiners = [(min, max), (max, min)][i]
                limits = (new_vals[1 - i], self._rng[i])
                for confine, limit in zip(confiners, limits):
                    try:    # Confine value between range edge and other marker
                        former_value = value
                        value = confine(value, limit)
                    except: # Fails if a value of new type is being set
                        self._vals[i] = None
            self._vals_prev[i] = self._vals[i]
            self._vals[i] = value
        if refresh and self._vals != self._vals_prev:
            self.Refresh()
    Values = property(GetValues, SetValues, doc= \
        "See `GetValues` and `SetValues`."
    )


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
        if value is not None:
            confiners = [(min, max), (max, min)][i]
            limits = (self._vals[1 - i], self._rng[i])
            for confine, limit in zip(confiners, limits):
                try:    # Confine value between range edge and other marker
                    former_value = value
                    value = confine(value, limit)
                except: # Comparison fails if a value of new type is being set
                    self._vals[i] = None
        self._vals_prev[i] = self._vals[i]
        self._vals[i] = value
        if refresh and self._vals[i] != self._vals_prev[i]:
            self.Refresh()


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
    Range = property(GetRange, SetRange, doc= \
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
        # 1 for upper gap, plus all set positions plus 2 * label height
        best.height = (1 + 2 * (extent[1] + extent[2]) + self.RANGE_TOP
                      + self.RANGE_LABEL_TOP_GAP + self.RANGE_LABEL_BOTTOM_GAP
                      + self.TICK_HEIGHT + self.BAR_HEIGHT)
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
        elif isinstance(self._rng[0], (datetime.date, datetime.time)):
            formatted = value.strftime(formatter)
        else:
            if type(self._rng[0]) == int and type(value) == float:
                value = int(value)
            formatted = formatter % value
        return formatted



    def Draw(self, dc):
        width, height = self.GetClientSize()
        if not width or not height:
            return

        dc.Clear()
        if self.IsEnabled():
            dc.SetTextForeground(self.LABEL_COLOUR)
        else:
            dc.SetTextForeground(
                wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)
            )
        if not filter(None, self._rng):
            return

        # Clear area and init data
        left_label, right_label = map(self.FormatLabel, self._rng)
        # GetFullTextExtent returns (width, height, descent, leading)
        left_extent  = self.GetFullTextExtent(left_label)
        right_extent = self.GetFullTextExtent(right_label)
        max_extent = right_extent if (right_extent > left_extent) \
                     else left_extent
        range_delta = self._rng[1] - self._rng[0]
        box_top = (max_extent[1] + max_extent[2]) + 2 # 1 for border, 1 for gap
        selection_top = box_top + self.RANGE_TOP
        selection_height = height - selection_top - self.RANGE_BOTTOM
        self._box_area = wx.Rect(self.BAR_BUTTON_WIDTH, box_top,
            width - 2 * self.BAR_BUTTON_WIDTH,
            height - box_top - self.BAR_HEIGHT
        )
        dc.SetFont(self.GetFont())

        # Fill background
        dc.SetBrush(wx.Brush(self.BACKGROUND_COLOUR, wx.SOLID))
        dc.SetPen(wx.Pen(self.BACKGROUND_COLOUR))
        dc.DrawRectangle(0, 0, width, height)
        dc.SetPen(wx.Pen(self.BOX_COLOUR))
        dc.DrawLine(0, box_top, width, box_top) # Top line
        #dc.DrawRectangle(-1, box_top, width + 2, height - box_top)

        # Draw current selection background, edge and scrollbar
        self._bar_arrow_areas = None
        if filter(None, self._vals):
            value_rect = wx.Rect(-1, selection_top, -1, selection_height)
            for i in range(2):
                marker_delta = self._vals[i] - self._rng[0]
                range_delta_local = range_delta
                if isinstance(self._vals[i], (datetime.date, datetime.time)):
                    # Cannot divide by timedeltas: convert to microseconds
                    marker_delta = marker_delta.days * 86400000000 \
                        + marker_delta.seconds * 1000000 \
                        + marker_delta.microseconds
                    range_delta_local = range_delta.days * 86400000000 \
                        + range_delta.seconds * 1000000 \
                        + range_delta.microseconds
                    if not range_delta_local:
                        range_delta_local = 1 # One-value range, set x at left
                x = self._box_area.x \
                    + self._box_area.width * marker_delta / range_delta_local
                value_rect[2 if i else 0] = (x - value_rect[0]) if i else x
            dc.SetBrush(wx.Brush(self.RANGE_COLOUR, wx.SOLID))
            dc.SetPen(wx.Pen(self.RANGE_COLOUR))
            dc.DrawRectangle(*value_rect)
            # Draw scrollbar arrow buttons
            self._bar_area = wx.Rect(
                0, height - self.BAR_HEIGHT, width, self.BAR_HEIGHT
            )
            dc.SetPen(wx.Pen(self.TICK_COLOUR))
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
                if self._bar_arrow_areas[i].Contains(self._mousepos):
                    button_colour = self.BAR_HL_COLOUR
                dc.SetBrush(wx.Brush(button_colour, wx.SOLID))
                dc.DrawRectangle(*self._bar_arrow_areas[i])
            dc.SetBrush(wx.Brush(self.BAR_ARROW_FG_COLOUR, wx.SOLID))
            dc.SetPen(wx.Pen(self.BAR_ARROW_FG_COLOUR))
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
                    self._grip_area.Contains(self._mousepos)
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
                pens = [wx.Pen(self.BAR_COLOUR2), wx.Pen(self.BAR_COLOUR1)] * 4
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
            dc.SetPen(wx.Pen(self.SELECTION_LINE_COLOUR))
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
        dc.SetPen(wx.Pen(self.TICK_COLOUR))
        dc.DrawLineList(lines)

        # Draw labels, determining how many labels can fit comfortably.
        # 4/3 leaves a nice padding between.
        label_count = int(width / (max_extent[0] * 4 / 3.0))
        labels = [left_label]
        label_coords = [(2, selection_top + self.RANGE_LABEL_TOP_GAP)]
        if isinstance(self._rng[0], (datetime.date, datetime.time)):
            # Cannot use floats to divide timedeltas
            value_step = range_delta / (label_count or sys.maxsize)
            # Tickid on major ja minor. Valime siin, kuhu me mida paneme.
            # variandid: aasta-kuu, aastakuu-päev, päev-tund, tund-minut jne
        else:
            # Should use floats for other values, to get finer precision
            value_step = range_delta / float(label_count)
        # Skip first and last, as left and right are already set.
        for i in range(1, label_count - 1):
            labels.append(self.FormatLabel(self._rng[0] + i * value_step))
            label_coords.append((self._box_area.x \
                + i * self._box_area.width / label_count,
                selection_top + self.RANGE_LABEL_TOP_GAP
            ))
        labels.append(right_label)
        label_coords.append((self._box_area.right - right_extent[0],
            selection_top + self.RANGE_LABEL_TOP_GAP
        ))
        dc.DrawTextList(labels, label_coords)

        # Draw left and right markers
        marker_labels = [None, None] # [(text, area) * 2]
        marker_draw_order = [0, 1] if self._active_marker == 1 else [1, 0]
        # Draw active marker last, leaving its content on top
        for i in marker_draw_order:
            marker_delta = self._vals[i] - self._rng[0]
            range_delta_local = range_delta
            if isinstance(self._vals[i], (datetime.date, datetime.time)):
                # Cannot divide by timedeltas: convert to microseconds
                marker_delta = marker_delta.days * 86400000000 \
                    + marker_delta.seconds * 1000000 \
                    + marker_delta.microseconds
                range_delta_local = range_delta.days * 86400000000 \
                    + range_delta.seconds * 1000000 \
                    + range_delta.microseconds
                if not range_delta_local:
                    range_delta_local = 1 # One-value range, set x at left
            x = self._box_area.x \
                + self._box_area.width * marker_delta / range_delta_local
            self._marker_xs[i] = x
            label = self.FormatLabel(self._vals[i])
            # GetFullTextExtent returns (width, height, descent, leading)
            label_extent = self.GetFullTextExtent(label)
            # Center label on top of marker. +2 for padding
            label_area = wx.Rect(x - label_extent[0] / 2, 0, 
                label_extent[0] + 2, sum(label_extent[1:2])
            )
            if not self.ClientRect.ContainsRect(label_area):
                # Rest label against the edge if going out of control area
                label_area.x = 1 if (label_area.x < 1) \
                    else (width - label_area.width)
            marker_labels[i] = (label, label_area)

            area = wx.Rect(
                x - self.MARKER_WIDTH / 2, box_top,
                self.MARKER_WIDTH, height - box_top - self.BAR_HEIGHT
            )
            # Create a slightly larger highlight capture area for marker
            capture_area = self._capture_areas[i] = wx.Rect(*area)
            capture_area.x     -= self.MARKER_CAPTURE_PADX
            capture_area.width += self.MARKER_CAPTURE_PADX

            dc.SetPen(wx.Pen(self.SELECTION_LINE_COLOUR))
            dc.DrawLine(x, box_top, x, height)
            if self._mousepos is not None:
                # Draw drag buttons when mouse in control
                button_area = wx.Rect(-1, -1, self.MARKER_BUTTON_WIDTH,
                    self.MARKER_BUTTON_HEIGHT
                ).CenterIn(area)
                button_radius = 3
                if i == self._active_marker:
                    brush_colour = wx.WHITE#self.BAR_HL_COLOUR
                else:
                    brush_colour = self.MARKER_BUTTON_BG_COLOUR
                dc.SetBrush(wx.Brush(brush_colour, wx.SOLID))
                dc.SetPen(wx.Pen(self.MARKER_BUTTON_COLOUR))
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
                dc.SetPen(wx.Pen(self.SELECTION_LINE_COLOUR))
                dc.DrawLineList(button_lines)
        # Move marker labels apart if overlapping each other
        if marker_labels[0][1].Intersects(marker_labels[1][1]):
            # +1 for padding
            overlap = wx.Rect(*marker_labels[0][1]) \
                .Intersect(marker_labels[1][1]).width
            delta1 = (overlap / 2) + 1
            if (marker_labels[0][1].x - delta1 < 1):
                # Left is going over left edge: set to 1
                delta1 = marker_labels[0][1].x - 1
            delta2 = overlap - delta1
            if (marker_labels[1][1].right + delta2 > width):
                # Right is going over right side: set to right edge
                delta2 = width - marker_labels[1][1].right
                delta1 = overlap - delta2

            marker_labels[0][1].x -= delta1
            marker_labels[1][1].x += delta2
        # Draw left and right marker labels
        for text, area in marker_labels:
            dc.DrawText(text, area.x, 0)


    def OnMouseEvent(self, event):
        if not self.Enabled:
            return

        if not self._box_area:
            # Must not have been drawn yet
            self.Refresh()
        last_pos = self._mousepos
        self._mousepos = event.Position
        refresh = False
        active_markers = [i for i, c in enumerate(self._capture_areas) \
            if c and c.Contains(event.Position)
        ]
        active_marker = active_markers[0] if active_markers else None
        if len(active_markers) > 1 and last_pos \
        and last_pos.x > event.Position.x:
            # Switch marker to right if two are overlapping and approaching
            # from the right.
            active_marker = active_markers[-1]
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
            self._dragging_markers[i] = False
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
                    range_width = self.GetClientSize().width
                    step = range_delta * x_delta / self.GetClientSize().width
                    if isinstance(self._rng[0], datetime.date) and step.days < 1:
                        # Enforce a minimum step of 1 day for date values
                        step = datetime.timedelta(days=1)
                    in_area = self._grip_area.ContainsXY(
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
                    edge_x = self._box_area.x \
                             if self._grip_area.x <= self._box_area.x \
                             else self._box_area.right + 1
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
                    in_area = self._grip_area.ContainsXY(
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
        return wx.PyPanel.GetClassDefaultAttributes()

    def DoGetBestSize(self):
        best = wx.Size(200, 40)
        self.CacheBestSize(best)
        return best




class SearchableStyledTextCtrl(wx.PyPanel):
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
    CB_WHOLEWORD_LABEL = "Match whole word"

    """Label for the "Match regex" checkbox."""
    CB_REGEX_LABEL = "Match regex"

    """Width of the search box, in pixels."""
    SEARCH_WIDTH = 150

    """Background colour for the search edit box if no match found."""
    SEARCH_NOMATCH_BGCOLOUR = wx.NamedColour("#FF6666")

    """Foreground colour for the search edit box if no match found."""
    SEARCH_NOMATCH_FGCOLOUR = wx.NamedColour("#FFFFFF")

    """Font colour of descriptive text in the search box."""
    SEARCH_DESCRIPTIVE_COLOUR = wx.NamedColour("#808080")

    """Text to be displayed in the search box when it"s empty and unfocused."""
    SEARCH_DESCRIPTIVE_TEXT = "Search for.."

    """Background colour for selected matched text in the control."""
    MATCH_SELECTED_BGCOLOUR = wx.NamedColour("#0A246A")

    """Foreground colour for search buttons."""
    BUTTON_FGCOLOUR = wx.NamedColour("#475358")

    """Top background colour for search button gradient."""
    BUTTON_BGCOLOUR_TOP = wx.NamedColour("#FEFEFE")

    """Middle background colour for search button gradient."""
    BUTTON_BGCOLOUR_MIDDLE = wx.NamedColour("#ECECEC")

    """Bottom background colour for search button gradient."""
    BUTTON_BGCOLOUR_BOTTOM = wx.NamedColour("#DFDFDF")

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
        wx.PyPanel.__init__(self, parent=parent, pos=pos,
            size=size, style=style | wx.TAB_TRAVERSAL
        )

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
        style_sub = reduce(lambda a, b: a & ~b, nobits, style | wx.BORDER_NONE)
        self._stc = wx.stc.StyledTextCtrl(id=id, parent=self,
            style=style_sub, name=name
        )

        self._button_toggle = wx.lib.agw.shapedbutton.SBitmapButton(
            parent=self._stc, id=wx.ID_ANY, size=(16, 16),
            bitmap=wx.ArtProvider_GetBitmap(wx.ART_FIND, size=(8, 8))
        )
        self._button_toggle.SetUseFocusIndicator(False) # Hide focus marquee

        panel = self._panel_bar = wx.Panel(parent=self)
        sizer_bar = panel.Sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._label_search = wx.StaticText(parent=panel,
            label=self.SEARCH_LABEL
        )
        self._edit = wx.TextCtrl(parent=panel, style=wx.TE_PROCESS_ENTER,
            value=self.SEARCH_DESCRIPTIVE_TEXT, size=(self.SEARCH_WIDTH, -1)
        )
        self._edit.SetForegroundColour(self.SEARCH_DESCRIPTIVE_COLOUR)
        self._button_next = wx.lib.agw.gradientbutton.GradientButton(
            parent=panel, label=self.BUTTON_NEXT_LABEL, size=(-1, 26),
            bitmap=self.IMG_NEXT.GetBitmap()
        )
        self._button_prev = wx.lib.agw.gradientbutton.GradientButton(
            parent=panel, label=self.BUTTON_PREV_LABEL, size=(-1, 26),
            bitmap=self.IMG_PREV.GetBitmap()
        )
        for b in [self._button_next, self._button_prev]:
            b.SetForegroundColour   (self.BUTTON_FGCOLOUR)
            b.SetTopStartColour     (self.BUTTON_BGCOLOUR_TOP)
            b.SetTopEndColour       (self.BUTTON_BGCOLOUR_MIDDLE)
            b.SetBottomStartColour  (self.BUTTON_BGCOLOUR_MIDDLE)
            b.SetBottomEndColour    (self.BUTTON_BGCOLOUR_BOTTOM)
            b.SetPressedTopColour   (self.BUTTON_BGCOLOUR_MIDDLE)
            b.SetPressedBottomColour(self.BUTTON_BGCOLOUR_BOTTOM)

        self._cb_case = wx.CheckBox(parent=panel, label=self.CB_CASE_LABEL)
        self._cb_wholeword = wx.CheckBox(
            parent=panel, label=self.CB_WHOLEWORD_LABEL
        )
        self._cb_regex = wx.CheckBox(parent=panel, label=self.CB_REGEX_LABEL)
        self._button_close = wx.lib.agw.shapedbutton.SBitmapButton(
            parent=panel, id=wx.ID_ANY, size=(16, 16),
            bitmap=self.IMG_CLOSE.GetBitmap()
        )
        self._button_close.SetToolTipString("Show or hide the search bar.")
        self._button_close.SetUseFocusIndicator(False) # Hide focus marquee
        self._button_close.SetToolTipString("Hide search bar.")
        sizer_bar.Add(self._label_search, border=5,
            flag=wx.LEFT | wx.ALIGN_CENTER_VERTICAL
        )
        sizer_bar.Add(self._edit, border=5,
            flag=wx.LEFT | wx.ALIGN_CENTER_VERTICAL
        )
        sizer_bar.Add(self._button_next, border=5, flag=wx.LEFT)
        sizer_bar.Add(self._button_prev, border=5, flag=wx.LEFT)
        sizer_bar.AddStretchSpacer()
        for i in [self._cb_case, self._cb_wholeword, self._cb_regex]:
            sizer_bar.Add(i, border=5,
                flag=wx.RIGHT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL
            )
        sizer_bar.Add(self._button_close,
            flag=wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL
        )

        # AddMany tuples: (item, proportion=0, flag=0, border=0).
        item_child = (self._stc, 1, wx.EXPAND)
        item_bar = (panel, 0, wx.EXPAND | wx.ALL, 5)
        items = [item_child, item_bar]
        if self._bar_pos != wx.BOTTOM:
            item_bar = (panel, 0,
                wx.EXPAND | wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5
            )
            items = [item_bar, item_chile]
        self.Sizer.AddMany(items)
        self._panel_bar.Hide()

        self._stc.Bind(wx.EVT_KEY_UP, self.OnKeyUpCtrl)
        self._stc.Bind(
            wx.stc.EVT_STC_PAINTED, lambda e: self.UpdateToggleButton()
        )
        self._stc.Bind(
            wx.stc.EVT_STC_UPDATEUI, lambda e: self.UpdateToggleButton()
        )
        self._edit.Bind(wx.EVT_SET_FOCUS, self.OnFocusSearch)
        self._edit.Bind(wx.EVT_KILL_FOCUS, self.OnFocusSearch)
        self._edit.Bind(wx.EVT_TEXT_ENTER, lambda e: self.DoSearch())
        self._edit.Bind(wx.EVT_TEXT, self.OnTextSearch)
        self._edit.Bind(wx.EVT_KEY_DOWN, self.OnKeyDownSearch)
        self._button_next.Bind(wx.EVT_BUTTON, self.OnButtonSearchNext)
        self._button_prev.Bind(wx.EVT_BUTTON, self.OnButtonSearchPrev)
        self._button_close.Bind(wx.EVT_BUTTON, self.OnButtonClose)
        self._button_toggle.Bind(
            wx.EVT_BUTTON, lambda e: self.ToggleSearchBar()
        )
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
            self._edit.SetBackgroundColour(self.SEARCH_NOMATCH_BGCOLOUR \
                if nomatch else wx.WHITE
            )
            self._edit.SetForegroundColour(self.SEARCH_NOMATCH_FGCOLOUR \
                if nomatch else self.ForegroundColour
            )
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



class ProgressPanel(wx.Window):
    FOREGROUND_COLOUR = wx.WHITE
    BACKGROUND_COLOUR = wx.Colour(110, 110, 110, 255)
    #GAUGE_FOREGROUND_COLOUR = wx.GREEN
    #GAUGE_BACKGROUND_COLOUR = wx.WHITE

    def __init__(self, parent, label):
        wx.Window.__init__(self, parent)
        sizer = self.Sizer = wx.BoxSizer(wx.VERTICAL)
        label = self._label = wx.StaticText(parent=self, label=label)
        #gauge = self._gauge = wx.Gauge(parent=self, range=1500)
        #gauge.MinSize = (parent.Size.width / 2, -1)
        #gauge.Value = 1000
        self.BackgroundColour = self.BACKGROUND_COLOUR
        label.ForegroundColour = self.FOREGROUND_COLOUR
        #gauge.ForegroundColour = self.GAUGE_FOREGROUND_COLOUR
        #gauge.BackgroundColour = self.GAUGE_BACKGROUND_COLOUR
        sizer.Add(label, border=15, flag=wx.ALL | wx.ALIGN_CENTER_HORIZONTAL)
        #self.Sizer.Add(gauge, proportion=1, border=15,
        #    flag=wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.ALIGN_CENTER_HORIZONTAL
        #)
        self.Fit()
        self.CenterOnParent()
        self.Bind(wx.EVT_PAINT, lambda e: self.Refresh())
        #wx.CallLater(300, lambda: self.Pulse() if self else None)
        #self._gauge.Pulse()
        self.Layout()
        self.Update()
        parent.Refresh()


    def Close(self):
        self.Hide()
        self.Parent.Refresh()
        #wx.GetApp().Yield(True) # Allow display to refresh
        self.Destroy()



class ScrollingHtmlWindow(wx.html.HtmlWindow):
    """
    HtmlWindow that remembers its scroll position on resize.
    """

    def __init__(self, *args, **kwargs):
        wx.html.HtmlWindow.__init__(self, *args, **kwargs)
        self.Bind(wx.EVT_SCROLLWIN, self._OnScroll)
        self.Bind(wx.EVT_SIZE, self._OnSize)
        self._last_scroll_pos = [0, 0]
        self._last_scroll_range = [0, 0]

    def _OnSize(self, event):
        """
        Handler for sizing the HtmlWindow, sets new scroll position based
        previously stored one (HtmlWindow loses its scroll position on resize).
        """
        if hasattr(self, "_last_scroll_pos"):
            for i in range(2):
                orient = wx.VERTICAL if i else wx.HORIZONTAL
                # Division can be > 1 on first resizings, bound it to 1.
                pos, rng = self._last_scroll_pos[i], self._last_scroll_range[i]
                ratio = pos / float(rng) if rng else 0.0
                ratio = min(1, pos / float(rng) if rng else 0.0)
                self._last_scroll_pos[i] = ratio * self.GetScrollRange(orient)
            # Execute scroll later as something resets it after this handler
            try:
                wx.CallLater(50, lambda:
                    self.Scroll(*self._last_scroll_pos) if self else None
                )
            except:
                pass # CallLater fails if not called from the main thread
        event.Skip() # Allow event to propagate wx handler


    def _OnScroll(self, event):
        """
        Handler for scrolling the window, stores scroll position
        (HtmlWindow loses it on resize).
        """
        self._last_scroll_pos = [
            self.GetScrollPos(wx.HORIZONTAL), self.GetScrollPos(wx.VERTICAL)
        ]
        self._last_scroll_range = [
            self.GetScrollRange(wx.HORIZONTAL), self.GetScrollRange(wx.VERTICAL)
        ]
        event.Skip() # Allow event to propagate wx handler
