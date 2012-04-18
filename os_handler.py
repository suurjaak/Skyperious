# -*- coding: utf-8 -*-
"""
OS-specific functionality. Skype access currently only under Windows.

@author      Erki Suurjaak
@created     08.11.2011
@modified    08.12.2011
"""

import os
import ctypes

"""Current handler instance, if any."""
handler = None


def shutdown_skype():
    """Posts a message to the running Skype application to close itself."""
    global handler
    if handler:
        return handler.shutdown_skype()


def is_skype_running():
    """Returns whether Skype is currently running."""
    global handler
    if handler:
        return handler.is_skype_running()


def start_file(filepath):
    """Tries to open the specified file."""
    if "nt" == os.name:
        os.startfile(filepath)
    elif "mac" == os.name:
        subprocess.call(("open", filepath))
    elif "posix" == os.name:
        subprocess.call(("xdg-open", filepath))


def launch_skype():
    """Tries to launch Skype, returns True on success."""
    global handler
    if handler:
        return handler.launch_skype()


class SkypeWindowsHandler(object):
    """Handler for a Windows OS."""

    """Name of the Skype main form in Windows window list."""
    SKYPE_MAINFORM_CLASS = "tSkMainForm"

    """Windows constant for signalling a program to close."""
    WM_CLOSE = 0x0010

    def launch_skype(self):
        """Tries to launch Skype, returns True on success."""

        # From Skype4Py.api.windows
        key = ctypes.c_long()
        # try to find Skype in HKEY_CURRENT_USER registry tree
        if 0 != ctypes.windll.advapi32.RegOpenKeyA(
        0x80000001, "Software\\Skype\\Phone", ctypes.byref(key)):
            # try to find Skype in HKEY_LOCAL_MACHINE registry tree
            if 0 != ctypes.windll.advapi32.RegOpenKeyA(
            0x80000002, "Software\\Skype\\Phone", ctypes.byref(key)):
                raise Exception("Skype not installed")
        pathlen = ctypes.c_long(512)
        path = ctypes.create_string_buffer(pathlen.value)
        if 0 != ctypes.windll.advapi32.RegQueryValueExA(
        key, "SkypePath", None, None, path, ctypes.byref(pathlen)):
            ctypes.windll.advapi32.RegCloseKey(key)
            raise SkypeAPIError("Cannot find Skype path")
        ctypes.windll.advapi32.RegCloseKey(key)
        exec_result = ctypes.windll.shell32.ShellExecuteA(
            None, "open", path.value, "", None, 0
        )
        return exec_result > 32


    def shutdown_skype(self):
        """
        Posts a message to the running Skype application to close itself.
        """
        import win32con
        import win32gui

        skype_handle = self.get_window_handle(self.SKYPE_MAINFORM_CLASS)
        if skype_handle:
            win32gui.PostMessage(skype_handle, self.WM_CLOSE, 0, 0)


    def is_skype_running(self):
        """Returns whether Skype is currently running."""
        return not (not self.get_window_handle(self.SKYPE_MAINFORM_CLASS))


    def get_window_handle(self, window_class_name):
        """
        Returns the handle of a Windows program window specified by the
        class_name, e.g. "tSKMainForm" for Skype, or None if window not found.
        """
        import win32gui

        result = None
        windows = []
        win32gui.EnumWindows(self.window_enumeration_handler, windows)
        # Title is like "Skype\x99 [1] - username", class_name is
        # "tSkMainForm".
        for hwnd, title, class_name in windows:
            if class_name == window_class_name:
                result = hwnd
                break
        return result


    def get_window_class_name(self, hwnd):
        """Returns the class name of the specified window handle."""
        class_name = ctypes.c_buffer("\000" * 32)
        ctypes.windll.user32.GetClassNameA(hwnd, class_name, len(class_name))
        return class_name.value


    def window_enumeration_handler(self, hwnd, resultList):
        """
        Pass to win32gui.EnumWindows() to generate list of window handle,
        window text, window class tuples.
        """
        import win32gui

        resultList.append((
            hwnd,
            win32gui.GetWindowText(hwnd),
            self.get_window_class_name(hwnd)
        ))



if "nt" == os.name:
    handler = SkypeWindowsHandler()
# @todo add Linux handler
