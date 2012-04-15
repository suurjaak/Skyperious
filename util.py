#-*- coding: utf-8 -*-
"""
Miscellaneous utility functions.

@author      Erki Suurjaak
@created     16.02.2012
@modified    16.02.2012
"""
import math
import re
import string


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



def plural(word, count):
    """Returns the word as 'count words', or '1 word' if count is 1."""
    return "%s %s%s" % (count, word, "" if 1 == count else "s")



def cmp_dicts(dict1, dict2):
    """Returns True if dict2 has all the keys and matching values as dict1."""
    result = True
    index = 0
    for key, val in dict1.items():
        if key not in dict2:
            result = False
            #print 'Key ''%s'' is not in dict2.' % key
        elif dict2[key] != val:
            result = False
            #print 'Key ''%s'' value is ''%s'' in dict1, but ''%s'' in dict2.' % (key, val, dict2[key])
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
