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

Supplemented with escape and newline options, by Erki Suurjaak.
"""

import re


try:              text_type, string_types = unicode, (basestring, )  # Py2
except NameError: text_type, string_types = str,     (str, )         # Py3


class Template(object):

    COMPILED_TEMPLATES = {} # {(template string, compile options): code object}
    # Regex for stripping all leading, trailing and interleaving whitespace.
    RE_STRIP = re.compile("(^[ \t]+|[ \t]+$|(?<=[ \t])[ \t]+|\A[\r\n]+|[ \t\r\n]+\Z)", re.M)

    def __init__(self, template, strip=True, escape=False):
        """Initialize class"""
        super(Template, self).__init__()
        self.template = template
        self.options  = {"strip": strip, "escape": escape}
        self.builtins = {"escape": escape_html,
                         "setopt": lambda k, v: self.options.update({k: v}), }
        cache_key = (template, bool(escape))
        if cache_key in Template.COMPILED_TEMPLATES:
            self.code = Template.COMPILED_TEMPLATES[cache_key]
        else:
            self.code = self._process(self._preprocess(self.template))
            Template.COMPILED_TEMPLATES[cache_key] = self.code

    def expand(self, namespace={}, **kw):
        """Return the expanded template string"""
        output = []
        namespace.update(kw, **self.builtins)
        namespace["echo"]  = output.append
        namespace["isdef"] = lambda v: v in namespace

        eval(compile(self.code, "<string>", "exec"), namespace)
        return self._postprocess("".join(map(to_unicode, output)))

    def stream(self, buffer, namespace={}, encoding="utf-8", newline=None, **kw):
        """
        Expand the template and stream it to a file-like buffer.

        @param   newline     if specified, converts \r \n \r\n linefeeds to given
        """
        lfrgx, blfrgx = "(\r(?!\n))|((?<!\r)\n)|(\r\n)", b"(\r(?!\n))|((?<!\r)\n)|(\r\n)"
        bnewline = None if newline is None else newline.encode("latin1")
        def write_buffer(s, flush=False, cache=[""]):
            # Cache output as a single string and write to buffer.
            cache[0] += to_unicode(s)
            if flush and cache[0] or len(cache[0]) > 65536:
                s, cache[0] = postprocess(cache[0]), ""
                if newline is not None:
                    rgx, lf = (blfrgx, bnewline) if isinstance(s, bytes) else (lfrgx, newline)
                    s = re.sub(rgx, lf, s)
                buffer.write(s)

        namespace.update(kw, **self.builtins)
        namespace["echo"]  = write_buffer
        namespace["isdef"] = lambda v: v in namespace
        postprocess = lambda s: s.encode(encoding)
        if self.options["strip"]:
            postprocess = lambda s: Template.RE_STRIP.sub("", s).encode(encoding)

        eval(compile(self.code, "<string>", "exec"), namespace)
        write_buffer("", flush=True) # Flush any last cached bytes

    def _preprocess(self, template):
        """Modify template string before code conversion"""
        # Replace inline '%' blocks for easier parsing
        o = re.compile(r"(?m)^[ \t]*%((if|for|while|try).+:)")
        c = re.compile(r"(?m)^[ \t]*%(((else|elif|except|finally).*:)|(end\w+))")
        template = c.sub(r"<%:\g<1>%>", o.sub(r"<%\g<1>%>", template))

        # Replace {{!x}} and {{x}} variables with '<%echo(x)%>'.
        # If auto-escaping is enabled, uses echo(escape(x)) for the second.
        vars = r"\{\{\s*\!(.*?)\}\}", r"\{\{(.*?)\}\}"
        subs = [r"<%echo(\g<1>)%>\n"] * 2
        if self.options["escape"]: subs[1] = r"<%echo(escape(\g<1>))%>\n"
        for v, s in zip(vars, subs): template = re.sub(v, s, template)

        return template

    def _process(self, template):
        """Return the code generated from the template string"""
        code_blk = re.compile(r"<%(.*?)%>\n?", re.DOTALL)
        indent = 0
        code = []
        for n, blk in enumerate(code_blk.split(template)):
            # Replace '<\%' and '%\>' escapes
            blk = re.sub(r"<\\%", "<%", re.sub(r"%\\>", "%>", blk))
            # Unescape '%{}' characters
            blk = re.sub(r"\\(%|{|})", r"\g<1>", blk)

            if not (n % 2):
                # Escape double-quote characters
                blk = re.sub(r"\"", "\\\"", blk)
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

    def _postprocess(self, output):
        """Modify output string after variables and code evaluation"""
        if self.options["strip"]:
            output = Template.RE_STRIP.sub("", output)
        return output


def escape_html(x):
    """Escape HTML special characters &<> and quotes "'."""
    CHARS, ENTITIES = "&<>\"'", ["&amp;", "&lt;", "&gt;", "&quot;", "&#39;"]
    string = x if isinstance(x, text_type) else str(x)
    for c, e in zip(CHARS, ENTITIES): string = string.replace(c, e)
    return string


def to_unicode(x, encoding="utf-8"):
    """Convert anything to Unicode."""
    if isinstance(x, bytes):
        x = text_type(x, encoding, errors="replace")
    elif not isinstance(x, string_types):
        x = text_type(str(x))
    return x
