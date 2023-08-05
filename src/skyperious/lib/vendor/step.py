"""
A light and fast template engine.

Copyright (c) 2012, Daniele Mazzocchio
All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.
* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.
* Neither the name of the developer nor the names of its contributors may be
  used to endorse or promote products derived from this software without
  specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

------------------------------------------------------------------------------

Supplemented with escape and postprocess and buffer size options, 
code object caching, get(), fixes and other tweaks, by Erki Suurjaak.
"""

import re


try: text_type, string_types = unicode, (bytes, unicode)  # Py2
except Exception: text_type, string_types = str, (str, )  # Py3


class Template(object):

    TRANSPILED_TEMPLATES = {} # {(template string, compile options): compilable code string}
    COMPILED_TEMPLATES   = {} # {compilable code string: code object}
    # Regexes for stripping all leading and interleaving, and all or rest of trailing whitespace.
    RE_STRIP = re.compile("(^[ \t]+|[ \t]+$|(?<=[ \t])[ \t]+|\\A[\r\n]+|[ \t\r\n]+\\Z)", re.M)
    RE_STRIP_STREAM = re.compile("(^[ \t]+|[ \t]+$|(?<=[ \t])[ \t]+|\\A[\r\n]+|"
                                 "((?<=(\r\n))|(?<=[ \t\r\n]))[ \t\r\n]+\\Z)", re.M)

    def __init__(self, template, strip=True, escape=False, postprocess=None):
        """Initialize class"""
        super(Template, self).__init__()
        pp = list([postprocess] if callable(postprocess) else postprocess or [])
        self.template = template
        self.options  = {"strip": strip, "escape": escape, "postprocess": pp}
        self.builtins = {"escape": escape_html, "setopt": self.options.__setitem__}
        key = (template, bool(escape))
        TPLS, CODES = Template.TRANSPILED_TEMPLATES, Template.COMPILED_TEMPLATES
        src = TPLS.setdefault(key, TPLS.get(key) or self._process(self._preprocess(self.template)))
        self.code = CODES.setdefault(src, CODES.get(src) or compile(src, "<string>", "exec"))

    def expand(self, namespace=None, **kw):
        """Return the expanded template string"""
        output = []
        eval(self.code, self._make_namespace(namespace, output.append, **kw))
        return self._postprocess("".join(map(to_unicode, output)))

    def stream(self, buffer, namespace=None, encoding="utf-8", buffer_size=65536, **kw):
        """Expand the template and stream it to a file-like buffer."""

        def write_buffer(s, flush=False, cache=[""]):
            # Cache output as a single string and write to buffer.
            cache[0] += to_unicode(s)
            if cache[0] and (flush or buffer_size < 1 or len(cache[0]) > buffer_size):
                v = self._postprocess(cache[0], stream=not flush)
                v and buffer.write(v.encode(encoding) if encoding else v)
                cache[0] = ""

        eval(self.code, self._make_namespace(namespace, write_buffer, **kw))
        write_buffer("", flush=True) # Flush any last cached bytes

    def _make_namespace(self, namespace, echo, **kw):
        """Return template namespace dictionary, containing given values and template functions."""
        namespace = dict(namespace or {}, **dict(kw, **self.builtins))
        namespace.update(echo=echo, get=namespace.get, isdef=namespace.__contains__)
        return namespace

    def _preprocess(self, template):
        """Modify template string before code conversion"""
        # Replace inline ('%') blocks for easier parsing
        o = re.compile("(?m)^[ \t]*%((if|for|while|try).+:)")
        c = re.compile("(?m)^[ \t]*%(((else|elif|except|finally).*:)|(end\\w+))")
        template = c.sub(r"<%:\g<1>%>", o.sub(r"<%\g<1>%>", template))

        # Replace {{!x}} and {{x}} variables with '<%echo(x)%>'.
        # If auto-escaping is enabled, use echo(escape(x)) for the second.
        vars = r"\{\{\s*\!(.*?)\}\}", r"\{\{(.*?)\}\}"
        subs = [r"<%echo(\g<1>)%>\n"] * 2
        if self.options["escape"]: subs[1] = r"<%echo(escape(\g<1>))%>\n"
        for v, s in zip(vars, subs): template = re.sub(v, s, template)

        return template

    def _process(self, template):
        """Return the code generated from the template string"""
        code_blk = re.compile(r"<%(.*?)%>\n?", re.DOTALL)
        indent, n = 0, 0
        code = []
        for n, blk in enumerate(code_blk.split(template)):
            # Replace '<\%' and '%\>' escapes
            blk = re.sub(r"<\\%", "<%", re.sub(r"%\\>", "%>", blk))
            # Unescape '%{}' characters
            blk = re.sub(r"\\(%|{|})", r"\g<1>", blk)

            if not (n % 2):
                if not blk: continue
                # Escape backslash characters
                blk = re.sub(r'\\', r'\\\\', blk)
                # Escape double-quote characters
                blk = re.sub(r'"', r'\\"', blk)
                blk = (" " * (indent*4)) + 'echo("""{0}""")'.format(blk)
            else:
                blk = blk.rstrip()
                if blk.lstrip().startswith(":"):
                    if not indent:
                        err = "unexpected block ending"
                        raise SyntaxError("Line {0}: {1}".format(n, err))
                    indent -= 1
                    if blk.startswith(":end"):
                        continue
                    blk = blk.lstrip()[1:]

                blk = re.sub("(?m)^", " " * (indent * 4), blk)
                if blk.endswith(":"):
                    indent += 1

            code.append(blk)

        if indent:
            err = "Reached EOF before closing block"
            raise EOFError("Line {0}: {1}".format(n, err))

        return "\n".join(code)

    def _postprocess(self, output, stream=False):
        """Modify output string after variables and code evaluation"""
        if self.options["strip"]:
            output = (Template.RE_STRIP_STREAM if stream else Template.RE_STRIP).sub("", output)
        for process in self.options["postprocess"]:
            output = process(output)
        return output


def escape_html(x):
    """Escape HTML special characters &<> and quotes "'."""
    CHARS, ENTITIES = "&<>\"'", ["&amp;", "&lt;", "&gt;", "&quot;", "&#39;"]
    string = x if isinstance(x, string_types) else str(x)
    for c, e in zip(CHARS, ENTITIES): string = string.replace(c, e)
    return string


def to_unicode(x, encoding="utf-8"):
    """Convert anything to Unicode."""
    if isinstance(x, (bytes, bytearray)):
        x = text_type(x, encoding, errors="replace")
    elif not isinstance(x, string_types):
        x = text_type(str(x))
    return x
