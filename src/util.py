#-*- coding: utf-8 -*-
"""
Miscellaneous utility functions.

@author      Erki Suurjaak
@created     16.02.2012
@modified    27.05.2013
"""
import math
import os
import re
import string
import subprocess
import time


def m(o, name, case_insensitive=True):
    """Returns the members of the object, filtered by name."""
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
    CHARS_VALID = "-_.() %s%s" % (string.ascii_letters, string.digits)
    encoded = unicodedata.normalize("NFKD", filename).encode(
        "ASCII", "ignore"
    )
    safe = "".join(c for c in encoded if c in CHARS_VALID)
    return safe



def format_bytes(size, precision=2):
    """Returns a formatted byte size (e.g. 421.45 MB)."""
    formatted = "0 bytes"
    size = int(size)
    if size:
        log = math.floor(math.log(size, 1024))
        formatted = "%.*f" % (precision, size / math.pow(1024, log))
        if formatted.endswith("0"): formatted = formatted[:-1]
        if formatted.endswith("0"): formatted = formatted[:-1]
        if formatted.endswith("."): formatted = formatted[:-1]
        formatted += " " + ["byte" if 1 == size else "bytes",
            "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"
        ][int(log)]
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



def plural(word, count_or_items=None):
    """
    Returns the word as 'count words', or '1 word' if count is 1,
    or 'words' if count omitted.

    @param   word
    @param   count_or_items  count, or item collection, or None to omit the
                             count from result
    """
    count = count_or_items or 0
    if hasattr(count_or_items, "__len__"):
            count = len(count_or_items)
    result = word + ("" if 1 == count else "s")
    if count_or_items is not None:
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
                break
        if not match:
            result[0].append(d1)
    for d2 in list2:
        match = False
        for d1 in list1:
            if cmp_dicts(d2, d1):
                match = True
                break
        if not match:
            result[1].append(d2)
    return result


def try_until(func, count=10, sleep=0.5):
    """
    Tries to execute the specified function a number of times.

    @param    func   callable to execute
    @param    count  number of times to try (default 10)
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
        except Exception, e:
            if tries < count and sleep:
                time.sleep(sleep)
    return result, func_result


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
        except WindowsError, e:
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
    """Returns whether the operating system is 64-bit (only MSW for now)."""
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
        tag += " " + " ".join([
            "%s='%s'" % (k, escape_html(v, utf=utf))
            for k, v in attrs.items()
        ])
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
