# -*- coding: utf-8 -*-
"""
Miscellaneous utility functions.

------------------------------------------------------------------------------
This file is part of Skyperious - Skype chat history tool.
Released under the MIT License.

@author      Erki Suurjaak
@created     16.02.2012
@modified    30.07.2020
------------------------------------------------------------------------------
"""
import calendar
import ctypes
import datetime
import io
import locale
import math
import os
import re
import string
import subprocess
import sys
import time
import urllib
import warnings

Image = ImageFile = wx = None # For image resize, most functions work without
try: from PIL import Image, ImageFile
except ImportError: pass
try: import wx
except ImportError: pass


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
    """Returns the filename with characters like \:*?"<>| removed."""
    return re.sub(r"[\/\\\:\*\?\"\<\>\|\x00-\x1f]", "", filename)


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
            formatted = formatted.rstrip("0").rstrip(".")
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


def format_exc(e):
    """Formats an exception as Class: message, or Class: (arg1, arg2, ..)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore") # DeprecationWarning on e.message
        msg = to_unicode(e.message) if getattr(e, "message", None) \
              else "(%s)" % ", ".join(map(to_unicode, e.args)) if e.args else ""
    result = u"%s%s" % (type(e).__name__, ": " + msg if msg else "")
    return result


def plural(word, items=None, with_items=True):
    """
    Returns the word as 'count words', or '1 word' if count is 1,
    or 'words' if count omitted.

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


def xor(text, key):
    """Returns the given string XORed with given key."""
    while len(key) < len(text): key += key
    key = key[:len(text)]
    return "".join(chr(ord(a) ^ ord(b)) for (a, b) in zip(text, key))


def obfuscate(text, key=string.punctuation):
    """Returns text obfuscated with key."""
    if not isinstance(key, basestring): key = str(key)
    return xor(text, key).encode("base64").strip()


def deobfuscate(text, key=string.punctuation):
    """Returns deobfuscated text obfuscated with key ."""
    if not isinstance(key, basestring): key = str(key)
    try: return xor(text.decode("base64"), key)
    except Exception: return ""


def datetime_to_epoch(dt):
    """Returns datetime.datetime or .date as UNIX timestamp, or None if dt is None."""
    result = None
    if isinstance(dt, datetime.date):
        x = calendar.timegm(dt.timetuple())
        if isinstance(dt, datetime.datetime):
            x += dt.microsecond / 1e6
        if x >= 0: result = x if x % 1 else int(x)
    return result


def cmp_dicts(dict1, dict2):
    """
    Returns True if dict2 has all the keys and matching values as dict1.
    List values are converted to tuples before comparing.
    """
    result = True
    for key, v1 in dict1.items():
        result, v2 = key in dict2, dict2.get(key)
        if result:
            v1, v2 = (tuple(x) if isinstance(x, list) else x for x in [v1, v2])
            result = (v1 == v2)
        if not result:
            break # break for key, v1
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
    result, func_result, tries = False, None, 0
    while tries < count:
        tries += 1
        try: result, func_result = True, func()
        except Exception:
            time.sleep(sleep) if tries < count and sleep else None
    return result, func_result


def to_int(value):
    """Returns the value as integer, or None if not integer."""
    try: return int(value)
    except ValueError: return None


def unique_path(pathname):
    """
    Returns a unique version of the path. If a file or directory with the
    same name already exists, returns a unique version
    (e.g. "C:\config (2).sys" if ""C:\config.sys" already exists).
    """
    result = pathname
    if "linux2" == sys.platform and isinstance(result, unicode) \
    and "utf-8" != sys.getfilesystemencoding():
        result = result.encode("utf-8") # Linux has trouble if locale not UTF-8
    path, name = os.path.split(result)
    base, ext = os.path.splitext(name)
    if len(name) > 255: # Filesystem limitation
        name = base[:255 - len(ext) - 2] + ".." + ext
        result = os.path.join(path, name)
    counter = 2
    while os.path.exists(result):
        suffix = " (%s)%s" % (counter, ext)
        name = base + suffix
        if len(name) > 255:
            name = base[:255 - len(suffix) - 2] + ".." + suffix
        result = os.path.join(path, name)
        counter += 1
    return result


def start_file(filepath):
    """
    Tries to open the specified file in the operating system.

    @return  (success, error message)
    """
    success, error = True, ""
    try:
        if "nt" == os.name:
            try: os.startfile(filepath)
            except WindowsError as e:
                if 1155 == e.winerror: # ERROR_NO_ASSOCIATION
                    cmd = "Rundll32.exe SHELL32.dll, OpenAs_RunDLL %s"
                    os.popen(cmd % filepath)
                else: raise
        elif "mac" == os.name:
            subprocess.call(("open", filepath))
        elif "posix" == os.name:
            subprocess.call(("xdg-open", filepath))
    except Exception as e:
        success, error = False, repr(e)
    return success, error


def is_os_64bit():
    """Returns whether the operating system is 64-bit (Windows-only)."""
    return ('PROCESSOR_ARCHITEW6432' in os.environ 
            or os.environ['PROCESSOR_ARCHITECTURE'].endswith('64'))


def round_float(value, precision=1):
    """
    Returns the float as a string, rounded to the specified precision and
    with trailing zeroes (and . if no decimals) removed.
    """
    return str(round(value, precision)).rstrip("0").rstrip(".")


def divide_delta(td1, td2):
    """Divides two timedeltas and returns the integer result."""
    us1 = td1.microseconds + 1000000 * (td1.seconds + 86400 * td1.days)
    us2 = td2.microseconds + 1000000 * (td2.seconds + 86400 * td2.days)
    # Integer division, fractional division would be float(us1) / us2
    return us1 / us2


def img_recode(raw, format="PNG", size=None, aspect_ratio=True):
    """Recodes and/or resizes the raw image, using wx or PIL."""
    result = raw
    if wx:
        img = wx.Image(io.BytesIO(raw))
        if size: img = img_wx_resize(img, size, aspect_ratio)
        result = img_wx_to_raw(img, format)
    elif ImageFile:
        imgparser = ImageFile.Parser(); imgparser.feed(raw)
        img = imgparser.close()
        if size: img = img_pil_resize(img, size, aspect_ratio)
        stream = io.BytesIO()
        img.save(stream, format)
        result = stream.getvalue()
    return result


def img_size(raw):
    """Returns the size of the as (width, height), using wx or PIL."""
    result = None
    if wx:
        result = tuple(wx.Image(io.BytesIO(raw)).GetSize())
    elif ImageFile:
        imgparser = ImageFile.Parser(); imgparser.feed(raw)
        result = tuple(imgparser.close().size)
    return result


def img_wx_to_raw(img, format="PNG"):
    """Returns the wx.Image or wx.Bitmap as raw data of specified type."""
    stream = io.BytesIO()
    img = img if isinstance(img, wx.Image) else img.ConvertToImage()
    fmttype = getattr(wx, "BITMAP_TYPE_" + format.upper(), wx.BITMAP_TYPE_PNG)
    img.SaveFile(stream, fmttype)
    result = stream.getvalue()
    return result


def img_wx_resize(img, size, aspect_ratio=True, bg=(255, 255, 255)):
    """
    Returns a resized wx.Image or wx.Bitmap, centered if aspect ratio rescale
    resulted in free space on one axis.
    """
    result = img if isinstance(img, wx.Image) else img.ConvertToImage()
    if size:
        size1, size2 = list(result.GetSize()), list(size)
        if size2 != size1:
            align_pos = None
            if size1[0] < size[0] and size1[1] < size[1]:
                size2 = tuple(size1)
                align_pos = [(a - b) / 2 for a, b in zip(size, size2)]
            elif aspect_ratio:
                ratio = safedivf(*size1[:2])
                size2[ratio > 1] *= ratio if ratio < 1 else 1 / ratio
                align_pos = [(a - b) / 2 for a, b in zip(size, size2)]
            if size1[0] > size[0] or size1[1] > size[1]:
                if result is not img: result = result.Copy()
                result.Rescale(*size2)
            if align_pos:
                if result is not img: result = result.Copy()
                result.Resize(size, align_pos, *bg)
    return result


def img_pil_resize(img, size, aspect_ratio=True, bg=(255, 255, 255)):
    """
    Returns a resized PIL.Image, centered if aspect ratio rescale resulted in 
    free space on one axis.
    """
    result = img
    if size and list(size) != list(result.size):
        size2, align_pos = list(size), None
        if result.size[0] < size[0] and img.size[1] < size[1]:
            size2 = result.size
            align_pos = [(a - b) / 2 for a, b in zip(size, size2)]
        elif aspect_ratio:
            ratio = safedivf(*result.size[:2])
            size2[ratio > 1] *= ratio if ratio < 1 else 1 / ratio
            align_pos = [(a - b) / 2 for a, b in zip(size, size2)]
        if result.size[0] > size[0] or result.size[1] > size[1]:
            result.thumbnail(tuple(map(int, size2)), Image.ANTIALIAS)
        if align_pos:
            result, result0 = Image.new(img.mode, size, bg), result
            result.paste(result0, tuple(map(int, align_pos)))
    return result


def timedelta_seconds(timedelta):
    """Returns the total timedelta duration in seconds."""
    if hasattr(timedelta, "total_seconds"):
        result = timedelta.total_seconds()
    else: # Python 2.6 compatibility
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
    lst.insert(0, item) if direction < 0 else lst.append(item)
    if len(lst) > maxlen:
        lst[:] = lst[:maxlen] if direction < 0 else lst[-maxlen:]
    return lst


def get_locale_day_date(dt):
    """Returns a formatted (weekday, weekdate) in current locale language."""
    weekday, weekdate = dt.strftime("%A"), dt.strftime("%d. %B %Y")
    if locale.getpreferredencoding():
        for enc in (locale.getpreferredencoding(), "latin1"):
            try:
                weekday, weekdate = (x.decode(enc) for x in [weekday, weekdate])
                break
            except Exception: pass
    weekday = weekday.capitalize()
    return weekday, weekdate


def path_to_url(path, encoding="utf-8"):
    """
    Returns the local file path as a URL, e.g. "file:///C:/path/file.ext".
    """
    path = path.encode(encoding) if isinstance(path, unicode) else path
    if ":" not in path:
        # No drive specifier, just convert slashes and quote the name
        if path[:2] == "\\\\":
            path = "\\\\" + path
        url = urllib.quote("/".join(path.split("\\")))
    else:
        url, parts = "", path.split(":")
        if len(parts[0]) == 1: # Looks like a proper drive, e.g. C:\
            url = "///" + urllib.quote(parts[0].upper()) + ":"
            parts = parts[1:]
        components = ":".join(parts).split("\\")
        for part in filter(None, components):
            url += "/" + urllib.quote(part)
    url = "file:%s%s" % ("" if url.startswith("///") else "///" , url)
    return url


def to_unicode(value, encoding=None):
    """
    Returns the value as a Unicode string. Tries decoding as UTF-8 if 
    locale encoading fails.
    """
    result = value
    if not isinstance(value, unicode):
        encoding = encoding or locale.getpreferredencoding()
        if not isinstance(value, str):
            try: value = str(value)
            except Exception: value = repr(value)
        try: result = unicode(value, encoding)
        except Exception:
            result = unicode(value, "utf-8", errors="backslashreplace")
    return result


def longpath(path):
    """Returns the path in long Windows form ("Program Files" not PROGRA~1)."""
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
