"""
A light and fast template engine.

Copyright (c) 2012 Daniele Mazzocchio (danix@kernel-panic.it)

Redistribution and use in source and binary forms, with or without 
modification, are permitted provided that the following conditions are met:
- Redistributions of source code must retain the above copyright notice, this 
  list of conditions and the following disclaimer.
- Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.
- Neither the name of the developer nor the names of its contributors may be
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

@modified  11.06.2013 Erki Suurjaak: enclose expressions in {{}} instead of {},
                                     better Unicode support,
                                     option for strip in constructor,
                                     HTML escape function in namespace,
                                     template caching,
                                     Python 2.6 compatibility.
"""
import re


class Template(object):

    COMPILED_TEMPLATES = {} # {template string: code object, }

    def __init__(self, template, strip=True):
        """Initialize class"""
        super(Template, self).__init__()
        self.template = template
        self.options = {"strip": strip}
        self.builtins = {"setopt": lambda k, v: self.options.update({k: v}),
                         "escape": lambda s: escape_html(s)}
        if template in Template.COMPILED_TEMPLATES:
            self.code = Template.COMPILED_TEMPLATES[template]
        else:
            self.code = self._process(self._preprocess(self.template))
            Template.COMPILED_TEMPLATES[template] = self.code


    def expand(self, namespace={}, **kw):
        """Return the expanded template string"""
        output = []
        namespace.update(kw)
        namespace.update(self.builtins)
        namespace["echo"]  = lambda s: output.append(s)
        namespace["isdef"] = lambda v: v in namespace

        eval(compile(self.code, "<string>", "exec"), namespace)
        return self._postprocess("".join(map(to_uni, output)))


    def _strify(self, x):
        if not isinstance(x, unicode):
            if isinstance(x, str):
                x = unicode(x, "utf-8")
            else:
                x = str(x)
        return x


    def _preprocess(self, template):
        """Modify template string before code conversion"""
        # Replace inline ('%') blocks for easier parsing
        o = re.compile("(?m)^[ \t]*%((if|for|while|try).+:)")
        c = re.compile("(?m)^[ \t]*%(((else|elif|except|finally).*:)|(end\w+))")
        template = c.sub(r"<%:\g<1>%>", o.sub(r"<%\g<1>%>", template))

        # Replace ({{x}}) variables with '<%echo(x)%>'
        v = re.compile("\{\{(.*?)\}\}")
        template = v.sub(r"<%echo(\g<1>)%>\n", template)

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
            blk = re.sub(r"\\(%|{|})", "\g<1>", blk)

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
            output = re.sub("(?m)(^[ \t]+|[ \t]+$|(?<=[ \t])[ \t]+|^\n)", "",
                            output)
        return output


def escape_html(x):
    """Escape HTML special characters <> and quotes '"."""
    string = x if isinstance(x, basestring) else str(x)
    return string.replace("<",    "&lt;").replace(">", "&gt;") \
                 .replace("\"", "&quot;").replace("'", "&#39;")


def to_uni(x):
    if not isinstance(x, unicode):
        if isinstance(x, str):
            x = unicode(x, "utf-8")
        else:
            x = str(x)
    return x
