# -*- coding: utf-8 -*-
"""
Miscellaneous utility functions.

------------------------------------------------------------------------------
This file is part of Skyperious - a Skype database viewer and merger.
Released under the MIT License.

@author      Erki Suurjaak
@created     16.02.2012
@modified    02.03.2014
------------------------------------------------------------------------------
"""
import cStringIO
import ctypes
import locale
import math
import os
import re
import string
import subprocess
import sys
import tempfile
import time
import urllib

from PIL import Image
try:
    import wx
except ImportError:
    pass # Most functionality works without wx


def m(o, name, case_insensitive=True):
    """Returns the members of the object or dict, filtered by name."""
    members = o.keys() if isinstance(o, dict) else dir(o)
    if case_insensitive:
        return [i for i in members if name.lower() in i.lower()]
    else:
        return [i for i in members if name in i]


def safedivf(a, b):
    """A zero-safe division, returns 0.0 if b is 0, a / float(b) otherwise."""
    return a / float(b) if b else 0.0


def safe_filename(filename):
    return re.sub(r"[\/\\\:\*\?\"\<\>\|]", "", filename)


def format_bytes(size, precision=2, max_units=True):
    """
    Returns a formatted byte size (e.g. "421.45 MB" or "421,451,273 bytes").

    @param   precision  number of decimals to leave after converting to
                        maximum units
    @param   max_units  whether to convert value to corresponding maximum
                        unit, or leave as bytes and add thousand separators
    """
    formatted = "0 bytes"
    size = int(size)
    if size:
        byteunit = "byte" if 1 == size else "bytes"
        if max_units:
            UNITS = [byteunit, "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
            log = min(len(UNITS) - 1, math.floor(math.log(size, 1024)))
            formatted = "%.*f" % (precision, size / math.pow(1024, log))
            while formatted.endswith("0"): formatted = formatted[:-1]
            if formatted.endswith("."): formatted = formatted[:-1]
            formatted += " " + UNITS[int(log)]
        else:
            formatted = "".join([x + ("," if i and not i % 3 else "")
                                 for i, x in enumerate(str(size)[::-1])][::-1])
            formatted += " " + byteunit
    return formatted


def format_seconds(seconds, insert=""):
    """
    Returns nicely formatted seconds, e.g. "25 hours, 12 seconds".

    @param   insert  text inserted between count and unit, e.g. "4 call hours"
    """
    insert = insert + " " if insert else ""
    formatted = "0 %sseconds" % insert
    seconds = int(seconds)
    if seconds:
        formatted, inter = "", ""
        for unit, count in zip(["hour", "minute", "second"], [3600, 60, 1]):
            if seconds >= count:
                label = "%s%s" % (insert if not formatted else "", unit)
                formatted += inter + plural(label, seconds / count)
                seconds %= count
                inter = ", "
    return formatted


def plural(word, items=None, with_items=True):
    """
    Returns the word as 'count words', or '1 word' if count is 1,
    or 'words' if count omitted, or .

    @param   word
    @param   items       item collection or count,
                         or None to get just the plural of the word
             with_items  if False, count is omitted from final result
    """
    count = items or 0
    if hasattr(items, "__len__"):
        count = len(items)
    result = word + ("" if 1 == count else "s")
    if with_items and items is not None:
        result = "%s %s" % (count, result)
    return result


def cmp_dicts(dict1, dict2):
    """Returns True if dict2 has all the keys and matching values as dict1."""
    result = True
    index = 0
    for key, val in dict1.items():
        if key not in dict2:
            result = False
        elif dict2[key] != val:
            result = False
        if not result:
            break # break for key, val
    return result


def cmp_dictlists(list1, list2):
    """Returns the two dictionary lists with matching dictionaries removed."""

    # Items different in list1, items different in list2
    result = ([], [])
    for d1 in list1:
        match = False
        for d2 in list2:
            if cmp_dicts(d1, d2):
                match = True
                break # break for d2 in list2
        if not match:
            result[0].append(d1)
    for d2 in list2:
        match = False
        for d1 in list1:
            if cmp_dicts(d2, d1):
                match = True
                break # break for d1 in list1
        if not match:
            result[1].append(d2)
    return result


def try_until(func, count=1, sleep=0.5):
    """
    Tries to execute the specified function a number of times.

    @param    func   callable to execute
    @param    count  number of times to try (default 1)
    @param    sleep  seconds to sleep after failed attempts, if any
                     (default 0.5)
    @return          (True, func_result) if success else (False, None)
    """
    tries = 0
    result = False
    func_result = None
    while tries < count:
        tries += 1
        try:
            func_result = func()
            result = True
        except Exception as e:
            if tries < count and sleep:
                time.sleep(sleep)
    return result, func_result


def to_int(value):
    """Returns the value as integer, or None if not integer."""
    try:
        result = int(value)
    except ValueError as e:
        result = None
    return result


def unique_path(pathname):
    """
    Returns a unique version of the path. If a file or directory with the
    same name already exists, returns a unique version
    (e.g. "C:\config (2).sys" if ""C:\config.sys" already exists).
    """
    result = pathname
    base, ext = os.path.splitext(result)
    counter = 2
    while os.path.exists(result):
        result = "%s (%s)%s" % (base, counter, ext)
        counter += 1
    return result


def start_file(filepath):
    """Tries to open the specified file."""
    if "nt" == os.name:
        try:
            os.startfile(filepath)
        except WindowsError as e:
            if 1155 == e.winerror: # ERROR_NO_ASSOCIATION
                cmd = "Rundll32.exe SHELL32.dll, OpenAs_RunDLL %s"
                os.popen(cmd % filepath)
            else:
                raise
    elif "mac" == os.name:
        subprocess.call(("open", filepath))
    elif "posix" == os.name:
        subprocess.call(("xdg-open", filepath))


def is_os_64bit():
    """Returns whether the operating system is 64-bit (Windows-only)."""
    if 'PROCESSOR_ARCHITEW6432' in os.environ:
        return True
    return os.environ['PROCESSOR_ARCHITECTURE'].endswith('64')


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
        tag += " " + " ".join(["%s='%s'" % (k, escape_html(v, utf=utf))
                               for k, v in attrs.items()])
    if name not in SELF_CLOSING_TAGS:
    #or (content is not None and str(content)):
        tag += ">%s</%s>" % (escape_html(content, utf=utf), name)
    else:
        tag += " />"
    return tag


def escape_html(value, utf=True):
    """
    Escapes the value for HTML content (converts "'< to &quot;&#39;&lt;).

    @param   value  string or unicode value
    @param   utf    whether to encode result into UTF-8 (True by default)
    """
    strval = value if isinstance(value, basestring) \
             else (str(value) if value is not None else "")
    result = strval.replace("<",    "&lt;").replace(">", "&gt;") \
                   .replace("\"", "&quot;").replace("'", "&#39;")
    if utf:
        result = result.encode("utf-8")
    return result


def round_float(value, precision=1):
    """
    Returns the float as a string, rounded to the specified precision and
    with trailing zeroes (and . if no decimals) removed.
    """
    result = str(round(value, precision)).rstrip("0").rstrip(".")
    return result


def divide_delta(td1, td2):
    """Divides two timedeltas and returns the integer result."""
    us1 = td1.microseconds + 1000000 * (td1.seconds + 86400 * td1.days)
    us2 = td2.microseconds + 1000000 * (td2.seconds + 86400 * td2.days)
    # Integer division, fractional division would be float(us1) / us2
    return us1 / us2


def pil_to_wx_image(pil_image, copy_alpha=True):
    """Converts a PIL.Image to wx.Image."""
    wx_image = wx.EmptyImage(*pil_image.size)
    wx_image.SetData(pil_image.convert("RGB").tostring())
    if copy_alpha and ("A" == pil_image.mode[-1]):
        wx_image.SetAlphaData(pil_image.tostring()[3::4])
    return wx_image


def wx_image_to_pil(wx_image, copy_alpha=True):
    """Converts a wx.Image to PIL.Image."""
    pil_image = Image.new("RGB", wx_image.GetSize())
    pil_image.fromstring(wx_image.Data)
    if wx_image.HasAlpha() and copy_alpha:
        pil_image = pil_image.convert("RGBA")
        alpha = Image.fromstring("L", wx_image.GetSize(), wx_image.AlphaData)
        pil_image.putalpha(alpha)
    return pil_image


def wx_bitmap_to_raw(wx_bitmap, format="PNG"):
    """Returns the wx.Bitmap or wx.Image as raw data of specified type."""
    stream = cStringIO.StringIO()
    img = wx_bitmap if isinstance(wx_bitmap, wx.Image) \
          else wx_bitmap.ConvertToImage()
    wx_image_to_pil(img).save(stream, format)
    result = stream.getvalue()
    return result


def timedelta_seconds(timedelta):
    """Returns the total timedelta duration in seconds."""
    if hasattr(timedelta, "total_seconds"):
        result = timedelta.total_seconds()
    else:
        result = timedelta.days * 24 * 3600 + timedelta.seconds + \
                 timedelta.microseconds / 1000000.
    return result


def add_unique(lst, item, direction=1, maxlen=sys.maxint):
    """
    Adds the item to the list from start or end. If item is already in list,
    removes it first. If list is longer than maxlen, shortens it.

    @param   direction  side from which item is added, -1/1 for start/end
    @param   maxlen     maximum length list is allowed to grow to before
                        shortened from the other direction
    """
    if item in lst:
        lst.remove(item)
    lst.insert(0, item) if (direction < 0) else lst.append(item)
    if len(lst) > maxlen:
        lst[:] = lst[:maxlen] if (direction < 0) else lst[-maxlen:]
    return lst


def get_locale_day_date(dt):
    """Returns a formatted (weekday, weekdate) in current locale language."""
    weekday = dt.strftime("%A")
    weekdate = dt.strftime("%d. %B %Y")
    if locale.getpreferredencoding():
        try:
            weekday = weekday.decode(locale.getpreferredencoding())
            weekdate = weekdate.decode(locale.getpreferredencoding())
        except Exception:
            try:
                weekday = weekday.decode("latin1")
                weekdate = weekdate.decode("latin1")
            except Exception:
                pass
    weekday = weekday.capitalize()
    return weekday, weekdate


def path_to_url(path, encoding="utf-8"):
    """
    Returns the local file path as a URL, e.g. "file:///C:/path/file.ext".
    """
    if isinstance(path, unicode):
        path = path.encode(encoding)

    if not ":" in path:
        # No drive specifier, just convert slashes and quote the name
        if path[:2] == "\\\\":
            path = "\\\\" + path
        url = urllib.quote("/".join(path.split("\\")))
    else:
        parts = path.split(":")
        url = ""

        if len(parts[0]) == 1: # Looks like a proper drive, e.g. C:\
            url = "///" + urllib.quote(parts[0].upper()) + ":"
            parts = parts[1:]
        components = ":".join(parts).split("\\")
        for part in filter(None, components):
            url += "/" + urllib.quote(part)

    url = "file:%s%s" % ("" if url.startswith("///") else "///" , url)
    return url


def to_unicode(value):
    """Returns the value as a Unicode string."""
    result = value
    if not isinstance(value, unicode):
        if isinstance(value, str):
            try:
                result = unicode(value, locale.getpreferredencoding())
            except Exception:
                result = unicode(value, "utf-8", errors="replace")
        else:
            result = unicode(str(value), errors="replace")
    return result


def longpath(path):
    """Returns the path in long Windows form (not shortened to PROGRA~1)."""
    result = path
    try:
        buf = ctypes.create_unicode_buffer(65536)
        GetLongPathNameW = ctypes.windll.kernel32.GetLongPathNameW
        if GetLongPathNameW(unicode(path), buf, 65536):
            result = buf.value
        else:
            head, tail = os.path.split(path)
            if GetLongPathNameW(unicode(head), buf, 65536):
                result = os.path.join(buf.value, tail)
    except Exception: pass
    return result
