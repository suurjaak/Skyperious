# -*- coding: utf-8 -*-
"""
Functionality for binding wx control label shortcut keys to events
automatically. In wx, a button with a label "E&xit" would be displayed as
having the label "Exit" with "x" underlined, indicating a keyboard shortcut,
but wx does not bind these shortcuts automatically, requiring constructing
the acceleration table piecemeal.

Supported controls:
- wx.Button       click handler called
- wx.CheckBox     value is reversed, control focused, change handler called
- wx.TextCtrl     control focused, all text selected
- wx.RadioButton  control focused, value selected
- wx.Control      control focused
- wx.ToolBar      tool event is called, if the tool shorthelp includes a
                  parseable shortcut key like (Alt-S)
- wx.ToggleButton ToggleButton handler called

Uses primitive heuristic analysis to detect connected label-control pairs:
- wx.StaticTexts whose next sibling is a focusable control
- wx.StaticTexts that have an Id one less from a focusable control (created
  immediately before creating the control)
- wx.StaticTexts that have the same Name as a control with "label" appended or
  prepended,
  e.g. "iptext" and "iptext_label"|"iptext.label"|"iptext label"|"labeliptext"

------------------------------------------------------------------------------
This file is part of Skyperious - a Skype database viewer and merger.
Released under the MIT License.

@author      Erki Suurjaak
@created     19.11.2011
@modified    09.03.2015
------------------------------------------------------------------------------
"""
import functools
import re
import wx

DEBUG = False


class AutoAcceleratorMixIn(object):
    """
    A windowed control that assigns global keyboard shortcuts to all its
    controls that have a shortcut key defined in their label (e.g. a button'
    labeled "E&xit" gets assigned the shortcut Alt-X).
    Accelerator table is autocreated on first showing; if changing controls
    afterwards, call UpdateAccelerators().

    @param   use_heuristics  whether to use heuristic analysis to detect
                             connected label-control pairs
    """
    def __init__(self, use_heuristics=True):
        """
        @param   use_heuristics  whether to use heuristic analysis to detect
                                 connected label-control pairs
        """
        self.__use_heuristics = use_heuristics
        self.__shortcuts = None # {shortcut char: target control, }


    def Show(self, *args, **kwargs):
        """
        Initializes the shortcut keys from child controls, if not already
        created, and calls parent.Show.
        """
        if not hasattr(self, "__shortcuts"):
            self.__shortcuts = None # {shortcut char: target control, }
        if self.__shortcuts is None:
            self.UpdateAccelerators()
        super(AutoAcceleratorMixIn, self).Show(*args, **kwargs)


    def UpdateAccelerators(self, use_heuristics=True):
        """
        Rebuilds the control shortcut keys in this frame.

        @param   use_heuristics  whether to use heuristic analysis to detect
                                 connected label-control pairs (sticky)
        """
        if not hasattr(self, "__shortcuts"):
            self.__shortcuts = None # {shortcut char: target control, }
        self.__use_heuristics = use_heuristics
        self.__shortcuts = accelerate(self, self.__use_heuristics)



def collect_shortcuts(control, use_heuristics=True):
    """
    Returns a map of detected shortcut keys and target controls under the
    specified control.

    @param   control         the control to start from
    @param   use_heuristics  whether to use heuristic analysis to detect
                             connected label-control pairs
    @return                  a map of detected shortcut chars and a list of
                             their target controls (there can be several
                             controls with one shortcut, e.g. controls on
                             different pages of a Notebook)
    """

    result  = {} # {char: control, }
    nameds  = {} # collected controls with Name {name: control, }
    statics = {} # collected StaticTexts with a shortcut {control: char, }

    def parse_shortcuts(ctrl):
        """
        Parses the shortcut keys from the control label, if any.

        @return    [keys]
        """
        result = []
        # wx.TextCtrl.Label is the same as its value, so must not use that
        if isinstance(ctrl, wx.ToolBar):
            toolsmap = dict()
            for i in range(ctrl.GetToolsCount() + 1):
                # wx 2.8 has no functionality for getting tools by index, so
                # need to gather them by layout position
                try:
                    tool = ctrl.FindToolForPosition(i * ctrl.ToolSize[0], 0)
                    toolsmap[repr(tool)] = tool
                except Exception: pass # FindTool not implemented in GTK
            for tool in filter(None, toolsmap.values()):
                text = ctrl.GetToolShortHelp(tool.GetId())
                parts = re.split("\\(Alt-(.)\\)", text, maxsplit=1)
                if len(parts) > 1:
                    result.append(parts[1].lower())
        elif hasattr(ctrl, "Label") and not isinstance(ctrl, wx.TextCtrl):
            for part in filter(len, ctrl.Label.split("&")[1:]):
                # Labels have potentially multiple ampersands - find one that
                # is usable (preceding a valid character. 32 and lower are
                # spaces, punctuation, control characters, etc).
                key = part[0].lower()
                if ord(key) > 32:
                    result.append(key)
                    if (DEBUG) and key:
                        print("Parsed '%s' in label '%s'." % (key, ctrl.Label))
                    break # break for part in filter
        return result


    def collect_recurse(ctrl, result, nameds, statics):
        """
        Goes through the control and all its children and collects accelerated
        controls.

        @return    {key: control, }
        """
        if hasattr(ctrl, "GetChildren"):
            children = ctrl.GetChildren()
            for i in range(len(children)):
                collect_recurse(children[i], result, nameds, statics)

        keys = parse_shortcuts(ctrl)
        for key in keys:
            if isinstance(ctrl, wx.StaticText):
                statics[ctrl] = key
            else:
                if key not in result:
                    result[key] = []
                if ctrl not in result[key]:
                    result[key].append(ctrl)
                    if (DEBUG): print("Selected '%s' for '%s' (%s.Id=%s)." %
                                      (key, ctrl.Label, ctrl.ClassName,
                                       ctrl.GetId()))
        if ctrl.Name:
            if DEBUG: print("Found named control %s %s." % (ctrl.Name, ctrl))
            nameds[ctrl.Name] = ctrl


    collect_recurse(control, result, nameds, statics)
    result_values = [j for i in result.values() for j in i]
    if use_heuristics:
        for ctrl, key in statics.items():
            # For wx.StaticTexts, see if the next sibling, or control with the
            # next ID, or control sitting next in the sizer  is focusable -
            # shortcut will set focus to the control.
            chosen = None
            next_sibling = hasattr(ctrl, "GetNextSibling") \
                           and ctrl.GetNextSibling()
            # Do not include buttons, as buttons have their own shortcut keys.
            if next_sibling and not isinstance(next_sibling, wx.Button) \
            and (not next_sibling.Enabled or next_sibling.AcceptsFocus()
            or getattr(next_sibling, "CanAcceptFocus", lambda: False)()):
                chosen = next_sibling
                if (DEBUG):
                    print("Selected '%s' by previous sibling wxStaticText "
                          "'%s' (%s.ID=%s)." %
                          (key, ctrl.Label, chosen.ClassName, chosen.Id))
            if not chosen:
                # Try to see if the item with the next ID is focusable.
                next_ctrl = wx.FindWindowById(ctrl.Id - 1)
                # Disabled controls might return False for AcceptsFocus).
                if next_ctrl and not isinstance(next_ctrl, wx.Button) \
                and (not next_ctrl.Enabled or next_ctrl.AcceptsFocus()
                or getattr(next_ctrl, "CanAcceptFocus", lambda: False)()):
                    chosen = next_ctrl
                    if (DEBUG):
                        print("Selected '%s' by previous ID wxStaticText "
                              "'%s' (%s.ID=%s)." %
                              (key, ctrl.Label, chosen.ClassName, chosen.Id))
            if not chosen and ctrl.ContainingSizer:
                # Try to see if the item next in the same sizer is focusable
                sizer_items = []
                while True:
                    try:
                        item = ctrl.ContainingSizer.GetItem(len(sizer_items))
                        sizer_items.append(item.Window)
                    except Exception:
                        break # Reached item limit
                index = sizer_items.index(ctrl)
                if index < len(sizer_items) - 1:
                    next_ctrl = sizer_items[index + 1]
                    if (next_ctrl and not isinstance(next_ctrl, wx.Button)
                    and (not next_ctrl.Enabled or next_ctrl.AcceptsFocus()
                    or getattr(next_ctrl, "CanAcceptFocus", lambda: False)())):
                        chosen = next_ctrl
                        if (DEBUG):
                            print("Selected '%s' by previous in sizer "
                                  "wxStaticText '%s' (%s.ID=%s)." %
                                  (key, ctrl.Label, chosen.ClassName, chosen.Id))
            if chosen and chosen not in result_values:
                if key not in result:
                    result[key] = []
                result[key].append(chosen)
                result_values.append(chosen)

        for name, ctrl in nameds.items():
            # For named controls, see if there is another control with the same
            # name, but "label" appended or prepended.
            if (DEBUG): print("Going through named %s '%s'." % (ctrl, name))
            match_found = False
            label_regex = re.compile("(^label[_ \\.]*%s$)|(^%s[_ \\.]*label$)"
                                     % tuple([name] * 2), re.IGNORECASE)
            for potential_name, potential in nameds.items():
                if label_regex.match(potential_name):
                    keys = parse_shortcuts(potential)
                    for key in keys:
                        if (DEBUG):
                            print("Name %s matches potential %s, key=%s." % (
                                  name, potential_name, key))
                        if key and (ctrl not in result_values):
                            match_found = True
                            if key not in result:
                                result[key] = []
                            if ctrl not in result[key]:
                                result[key].append(ctrl)
                            result_values.append(ctrl)
                            if (DEBUG):
                                print("Selected '%s' by named StaticText "
                                      "'%s' (%s.ID=%s, %s.Name=%s, "
                                      "wxStaticText.Name=%s)." %
                                      (key, potential.Label, ctrl.ClassName,
                                       ctrl.ClassName, ctrl.Id, ctrl.Name,
                                       potential.Name))
                            break # break for key in keys
                    if match_found:
                        break # break for potential_name, potential in nameds
    return result



def accelerate(window, use_heuristics=True):
    """
    Assigns global keyboard shortcuts to all controls under the specified
    wx.Window that have a shortcut key defined in their label (e.g. a button
    labeled "E&xit" gets assigned the shortcut Alt-X). Resets previously
    set accelerators, if any.

    @param   control         the wx.Window instance to process, gets its
                             accelerator table reset
    @param   use_heuristics  whether to use heuristic analysis to detect
                             connected label-control pairs
    @return                  a map of detected shortcut chars and their target
                             controls
    """

    def shortcut_handler(targets, key, shortcut_event):
        """
        Shortcut event handler, calls the appropriate event on the target.

        @param   targets         list of target controls. If there is more than
                                 one target control, the first non-disabled
                                 and visible is chosen.
        @param   key             the event shortcut key, like 's'
        @param   shortcut_event  menu event generated by the accelerator table
        """
        if (DEBUG):
            print("Handling target %s" %
                  [(type(t), t.Id, t.Label) for t in targets])
        event = None
        for target in targets:
            if (isinstance(target, wx.Control) # has not been destroyed
            and target.IsShownOnScreen()       # visible on current panel
            and target.Enabled):
                if isinstance(target, wx.Button):
                    # Buttons do not get focus on shortcuts by convention
                    event = wx.CommandEvent(wx.EVT_BUTTON.typeId, target.Id)
                    event.SetEventObject(target)
                elif isinstance(target, wx.ToggleButton):
                    # Buttons do not get focus on shortcuts by convention
                    event = wx.CommandEvent(wx.EVT_TOGGLEBUTTON.typeId,
                                            target.Id)
                    event.SetEventObject(target)
                    # Need to change value, as event goes directly to handler
                    target.Value = not target.Value
                elif isinstance(target, wx.CheckBox):
                    event = wx.CommandEvent(wx.EVT_CHECKBOX.typeId, target.Id)
                    # Need to change value, as event goes directly to handler
                    target.Value = not target.Value
                    target.SetFocus()
                elif isinstance(target, wx.ToolBar):
                    # Toolbar shortcuts are defined in their shorthelp texts
                    toolsmap, tb = dict(), target
                    for i in range(tb.GetToolsCount() + 1):
                        try:
                            tool = tb.FindToolForPosition(i * tb.ToolSize[0], 0)
                            toolsmap[repr(tool)] = tool
                        except Exception: pass # FindTool not implemented in GTK
                    for tool in filter(None, toolsmap.values()):
                        id = tool.GetId()
                        text = tb.GetToolShortHelp(id)
                        parts = re.split("\\(Alt-(%s)\\)" % key, text,
                                         maxsplit=1, flags=re.IGNORECASE)
                        if len(parts) > 1:
                            event = wx.CommandEvent(wx.EVT_TOOL.typeId, id)
                            event.SetEventObject(target)
                            target.ToggleTool(id, not target.GetToolState(id))
                            break # break for i in range(target.GetToolsCount)
                else:
                    target.SetFocus()
                    if isinstance(target, wx.TextCtrl):
                        target.SelectAll()
                break # break for target in targets
        if event:
            if (DEBUG): print("Chose target %s." % (target.Label or target))

            wx.PostEvent(target.GetEventHandler(), event)
        else:
            shortcut_event.Skip(True) # Not handled by us: propagate

    if hasattr(window, "__ampersand_shortcut_menu"):
        # Remove previously created menu, if any
        for menu_item in window.__ampersand_shortcut_menu.MenuItems:
            if (DEBUG): print("Removing dummy menu item '%s'" % menu_item.Label)
            window.Unbind(wx.EVT_MENU, menu_item)
        del window.__ampersand_shortcut_menu
    shortcuts = collect_shortcuts(window, use_heuristics)
    if shortcuts:
        accelerators = []
        dummy_menu = wx.Menu()
        for key, targets in shortcuts.items():
            if (DEBUG): print("Binding %s to targets %s." %
                              (key, [type(t) for t in targets]))
            menu_item = dummy_menu.Append(wx.ID_ANY, text="&%s" % key)
            window.Bind(wx.EVT_MENU,
                        functools.partial(shortcut_handler, targets, key),
                        menu_item)
            accelerators.append((wx.ACCEL_ALT, ord(key), menu_item.Id))
        window.SetAcceleratorTable(wx.AcceleratorTable(accelerators))
        window.__ampersand_shortcut_menu = dummy_menu
    return shortcuts
