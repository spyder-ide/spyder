# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Editor widget syntax highlighters based on QtGui.QSyntaxHighlighter
(Python syntax highlighting rules are inspired from idlelib)
"""

# Standard library imports
from __future__ import print_function
import keyword
import os
import re
import weakref

# Third party imports
from pygments.lexer import RegexLexer, bygroups
from pygments.lexers import get_lexer_by_name
from pygments.token import (Text, Other, Keyword, Name, String, Number,
                            Comment, Generic, Token)
from qtpy.QtCore import Qt, QTimer, Signal
from qtpy.QtGui import (QColor, QCursor, QFont, QSyntaxHighlighter,
                        QTextCharFormat, QTextOption)
from qtpy.QtWidgets import QApplication

# Local imports
from spyder.config.base import _
from spyder.config.manager import CONF
from spyder.py3compat import (builtins, is_text_string, to_text_string, PY3,
                              PY36_OR_MORE)
from spyder.plugins.editor.utils.languages import CELL_LANGUAGES
from spyder.plugins.editor.utils.editor import TextBlockHelper as tbh
from spyder.plugins.editor.utils.editor import BlockUserData
from spyder.utils.workers import WorkerManager
from spyder.plugins.outlineexplorer.api import OutlineExplorerData
from spyder.utils.qstringhelpers import qstring_length



# =============================================================================
# Constants
# =============================================================================
DEFAULT_PATTERNS = {
    'file':
        r'file:///?(?:[\S]*)',
    'issue':
        (r'(?:(?:(?:gh:)|(?:gl:)|(?:bb:))?[\w\-_]*/[\w\-_]*#\d+)|'
         r'(?:(?:(?:gh-)|(?:gl-)|(?:bb-))\d+)'),
    'mail':
        r'(?:mailto:\s*)?([a-z0-9_\.-]+)@([\da-z\.-]+)\.([a-z\.]{2,6})',
    'url':
        r"https?://([\da-z\.-]+)\.([a-z\.]{2,6})([/\w\.-]*)[^ ^'^\"]+",
}

COLOR_SCHEME_KEYS = {
    "background":     _("Background:"),
    "currentline":    _("Current line:"),
    "currentcell":    _("Current cell:"),
    "occurrence":     _("Occurrence:"),
    "ctrlclick":      _("Link:"),
    "sideareas":      _("Side areas:"),
    "matched_p":      _("Matched <br>parens:"),
    "unmatched_p":    _("Unmatched <br>parens:"),
    "normal":         _("Normal text:"),
    "keyword":        _("Keyword:"),
    "builtin":        _("Builtin:"),
    "definition":     _("Definition:"),
    "comment":        _("Comment:"),
    "string":         _("String:"),
    "number":         _("Number:"),
    "instance":       _("Instance:"),
}

COLOR_SCHEME_NAMES = CONF.get('appearance', 'names')

# Mapping for file extensions that use Pygments highlighting but should use
# different lexers than Pygments' autodetection suggests.  Keys are file
# extensions or tuples of extensions, values are Pygments lexer names.
CUSTOM_EXTENSION_LEXER = {
    '.ipynb': 'json',
    '.nt': 'bat',
    '.m': 'matlab',
    ('.properties', '.session', '.inf', '.reg', '.url',
     '.cfg', '.cnf', '.aut', '.iss'): 'ini'
}

# Convert custom extensions into a one-to-one mapping for easier lookup.
custom_extension_lexer_mapping = {}
for key, value in CUSTOM_EXTENSION_LEXER.items():
    # Single key is mapped unchanged.
    if is_text_string(key):
        custom_extension_lexer_mapping[key] = value
    # Tuple of keys is iterated over and each is mapped to value.
    else:
        for k in key:
            custom_extension_lexer_mapping[k] = value


#==============================================================================
# Auxiliary functions
#==============================================================================
def get_span(match, key=None):
    if key is not None:
        start, end = match.span(key)
    else:
        start, end = match.span()
    start = qstring_length(match.string[:start])
    end = qstring_length(match.string[:end])
    return start, end


def get_color_scheme(name):
    """Get a color scheme from config using its name"""
    name = name.lower()
    scheme = {}
    for key in COLOR_SCHEME_KEYS:
        try:
            scheme[key] = CONF.get('appearance', name+'/'+key)
        except:
            scheme[key] = CONF.get('appearance', 'spyder/'+key)
    return scheme


def any(name, alternates):
    "Return a named group pattern matching list of alternates."
    return "(?P<%s>" % name + "|".join(alternates) + ")"


def create_patterns(patterns, compile=False):
    """
    Create patterns from pattern dictionary.

    The key correspond to the group name and the values a list of
    possible pattern alternatives.
    """
    all_patterns = []
    for key, value in patterns.items():
        all_patterns.append(any(key, [value]))

    regex = '|'.join(all_patterns)

    if compile:
        regex = re.compile(regex)

    return regex


DEFAULT_PATTERNS_TEXT = create_patterns(DEFAULT_PATTERNS, compile=False)
DEFAULT_COMPILED_PATTERNS = re.compile(create_patterns(DEFAULT_PATTERNS,
                                                       compile=True))


#==============================================================================
# Syntax highlighting color schemes
#==============================================================================
class BaseSH(QSyntaxHighlighter):
    """Base Syntax Highlighter Class"""
    # Syntax highlighting rules:
    PROG = None
    BLANKPROG = re.compile(r"\s+")
    # Syntax highlighting states (from one text block to another):
    NORMAL = 0
    # Syntax highlighting parameters.
    BLANK_ALPHA_FACTOR = 0.31

    sig_outline_explorer_data_changed = Signal()
    # Signal to advertise a new cell
    sig_new_cell = Signal(OutlineExplorerData)

    def __init__(self, parent, font=None, color_scheme='Spyder'):
        QSyntaxHighlighter.__init__(self, parent)

        self.font = font
        if is_text_string(color_scheme):
            self.color_scheme = get_color_scheme(color_scheme)
        else:
            self.color_scheme = color_scheme

        self.background_color = None
        self.currentline_color = None
        self.currentcell_color = None
        self.occurrence_color = None
        self.ctrlclick_color = None
        self.sideareas_color = None
        self.matched_p_color = None
        self.unmatched_p_color = None

        self.formats = None
        self.setup_formats(font)

        self.cell_separators = None
        self.editor = None
        self.patterns = DEFAULT_COMPILED_PATTERNS

    def get_background_color(self):
        return QColor(self.background_color)

    def get_foreground_color(self):
        """Return foreground ('normal' text) color"""
        return self.formats["normal"].foreground().color()

    def get_currentline_color(self):
        return QColor(self.currentline_color)

    def get_currentcell_color(self):
        return QColor(self.currentcell_color)

    def get_occurrence_color(self):
        return QColor(self.occurrence_color)

    def get_ctrlclick_color(self):
        return QColor(self.ctrlclick_color)

    def get_sideareas_color(self):
        return QColor(self.sideareas_color)

    def get_matched_p_color(self):
        return QColor(self.matched_p_color)

    def get_unmatched_p_color(self):
        return QColor(self.unmatched_p_color)

    def get_comment_color(self):
        """ Return color for the comments """
        return self.formats['comment'].foreground().color()

    def get_color_name(self, fmt):
        """Return color name assigned to a given format"""
        return self.formats[fmt].foreground().color().name()

    def setup_formats(self, font=None):
        base_format = QTextCharFormat()
        if font is not None:
            self.font = font
        if self.font is not None:
            base_format.setFont(self.font)
        self.formats = {}
        colors = self.color_scheme.copy()
        self.background_color = colors.pop("background")
        self.currentline_color = colors.pop("currentline")
        self.currentcell_color = colors.pop("currentcell")
        self.occurrence_color = colors.pop("occurrence")
        self.ctrlclick_color = colors.pop("ctrlclick")
        self.sideareas_color = colors.pop("sideareas")
        self.matched_p_color = colors.pop("matched_p")
        self.unmatched_p_color = colors.pop("unmatched_p")
        for name, (color, bold, italic) in list(colors.items()):
            format = QTextCharFormat(base_format)
            format.setForeground(QColor(color))
            if bold:
                format.setFontWeight(QFont.Bold)
            format.setFontItalic(italic)
            self.formats[name] = format

    def set_color_scheme(self, color_scheme):
        if is_text_string(color_scheme):
            self.color_scheme = get_color_scheme(color_scheme)
        else:
            self.color_scheme = color_scheme
        self.setup_formats()
        self.rehighlight()

    @staticmethod
    def _find_prev_non_blank_block(current_block):
        previous_block = (current_block.previous()
                          if current_block.blockNumber() else None)
        # find the previous non-blank block
        while (previous_block and previous_block.blockNumber() and
               previous_block.text().strip() == ''):
            previous_block = previous_block.previous()
        return previous_block

    def update_patterns(self, patterns):
        """Update patterns to underline."""
        all_patterns = DEFAULT_PATTERNS.copy()
        additional_patterns = patterns.copy()

        # Check that default keys are not overwritten
        for key in DEFAULT_PATTERNS.keys():
            if key in additional_patterns:
                # TODO: print warning or check this at the plugin level?
                additional_patterns.pop(key)
        all_patterns.update(additional_patterns)

        self.patterns = create_patterns(all_patterns, compile=True)

    def highlightBlock(self, text):
        """
        Highlights a block of text. Please do not override, this method.
        Instead you should implement
        :func:`spyder.utils.syntaxhighplighters.SyntaxHighlighter.highlight_block`.

        :param text: text to highlight.
        """
        self.highlight_block(text)

    def highlight_block(self, text):
        """
        Abstract method. Override this to apply syntax highlighting.

        :param text: Line of text to highlight.
        :param block: current block
        """
        raise NotImplementedError()

    def highlight_patterns(self, text, offset=0):
        """Highlight URI and mailto: patterns."""
        match = self.patterns.search(text, offset)
        while match:
            for __, value in list(match.groupdict().items()):
                if value:
                    start, end = get_span(match)
                    start = max([0, start + offset])
                    end = max([0, end + offset])
                    font = self.format(start)
                    font.setUnderlineStyle(True)
                    self.setFormat(start, end - start, font)

            match = self.patterns.search(text, match.end())

    def highlight_spaces(self, text, offset=0):
        """
        Make blank space less apparent by setting the foreground alpha.
        This only has an effect when 'Show blank space' is turned on.
        """
        flags_text = self.document().defaultTextOption().flags()
        show_blanks =  flags_text & QTextOption.ShowTabsAndSpaces
        if show_blanks:
            format_leading = self.formats.get("leading", None)
            format_trailing = self.formats.get("trailing", None)
            match = self.BLANKPROG.search(text, offset)
            while match:
                start, end = get_span(match)
                start = max([0, start+offset])
                end = max([0, end+offset])
                # Format trailing spaces at the end of the line.
                if end == qstring_length(text) and format_trailing is not None:
                    self.setFormat(start, end - start, format_trailing)
                # Format leading spaces, e.g. indentation.
                if start == 0 and format_leading is not None:
                    self.setFormat(start, end - start, format_leading)
                format = self.format(start)
                color_foreground = format.foreground().color()
                alpha_new = self.BLANK_ALPHA_FACTOR * color_foreground.alphaF()
                color_foreground.setAlphaF(alpha_new)
                self.setFormat(start, end - start, color_foreground)
                match = self.BLANKPROG.search(text, match.end())

    def highlight_extras(self, text, offset=0):
        """
        Perform additional global text highlight.

        Derived classes could call this function at the end of
        highlight_block().
        """
        self.highlight_spaces(text, offset=offset)
        self.highlight_patterns(text, offset=offset)

    def rehighlight(self):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        QSyntaxHighlighter.rehighlight(self)
        QApplication.restoreOverrideCursor()


class TextSH(BaseSH):
    """Simple Text Syntax Highlighter Class (only highlight spaces)."""

    def highlight_block(self, text):
        """Implement highlight, only highlight spaces."""
        text = to_text_string(text)
        self.setFormat(0, qstring_length(text), self.formats["normal"])
        self.highlight_extras(text)


class GenericSH(BaseSH):
    """Generic Syntax Highlighter"""
    # Syntax highlighting rules:
    PROG = None  # to be redefined in child classes

    def highlight_block(self, text):
        """Implement highlight using regex defined in children classes."""
        text = to_text_string(text)
        self.setFormat(0, qstring_length(text), self.formats["normal"])

        match = self.PROG.search(text)
        index = 0
        while match:
            for key, value in list(match.groupdict().items()):
                if value:
                    start, end = get_span(match, key)
                    index += end-start
                    self.setFormat(start, end-start, self.formats[key])

            match = self.PROG.search(text, match.end())

        self.highlight_extras(text)


#==============================================================================
# Python syntax highlighter
#==============================================================================
def make_python_patterns(additional_keywords=[], additional_builtins=[]):
    "Strongly inspired from idlelib.ColorDelegator.make_pat"
    kwlist = keyword.kwlist + additional_keywords
    builtinlist = [str(name) for name in dir(builtins)
                   if not name.startswith('_')] + additional_builtins
    repeated = set(kwlist) & set(builtinlist)
    for repeated_element in repeated:
        kwlist.remove(repeated_element)
    kw = r"\b" + any("keyword", kwlist) + r"\b"
    builtin = r"([^.'\"\\#]\b|^)" + any("builtin", builtinlist) + r"\b"
    comment = any("comment", [r"#[^\n]*"])
    instance = any("instance", [r"\bself\b",
                                r"\bcls\b",
                                (r"^\s*@([a-zA-Z_][a-zA-Z0-9_]*)"
                                     r"(\.[a-zA-Z_][a-zA-Z0-9_]*)*")])
    number_regex = [r"\b[+-]?[0-9]+[lLjJ]?\b",
                    r"\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b",
                    r"\b[+-]?0[oO][0-7]+[lL]?\b",
                    r"\b[+-]?0[bB][01]+[lL]?\b",
                    r"\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?[jJ]?\b"]
    if PY3:
        prefix = "r|u|R|U|f|F|fr|Fr|fR|FR|rf|rF|Rf|RF|b|B|br|Br|bR|BR|rb|rB|Rb|RB"
    else:
        prefix = "r|u|ur|R|U|UR|Ur|uR|b|B|br|Br|bR|BR"
    sqstring =     r"(\b(%s))?'[^'\\\n]*(\\.[^'\\\n]*)*'?" % prefix
    dqstring =     r'(\b(%s))?"[^"\\\n]*(\\.[^"\\\n]*)*"?' % prefix
    uf_sqstring =  r"(\b(%s))?'[^'\\\n]*(\\.[^'\\\n]*)*(\\)$(?!')$" % prefix
    uf_dqstring =  r'(\b(%s))?"[^"\\\n]*(\\.[^"\\\n]*)*(\\)$(?!")$' % prefix
    ufe_sqstring = r"(\b(%s))?'[^'\\\n]*(\\.[^'\\\n]*)*(?!\\)$(?!')$" % prefix
    ufe_dqstring = r'(\b(%s))?"[^"\\\n]*(\\.[^"\\\n]*)*(?!\\)$(?!")$' % prefix
    sq3string =    r"(\b(%s))?'''[^'\\]*((\\.|'(?!''))[^'\\]*)*(''')?" % prefix
    dq3string =    r'(\b(%s))?"""[^"\\]*((\\.|"(?!""))[^"\\]*)*(""")?' % prefix
    uf_sq3string = r"(\b(%s))?'''[^'\\]*((\\.|'(?!''))[^'\\]*)*(\\)?(?!''')$" \
                   % prefix
    uf_dq3string = r'(\b(%s))?"""[^"\\]*((\\.|"(?!""))[^"\\]*)*(\\)?(?!""")$' \
                   % prefix
    # Needed to achieve correct highlighting in Python 3.6+
    # See spyder-ide/spyder#7324.
    if PY36_OR_MORE:
        # Based on
        # https://github.com/python/cpython/blob/
        # 81950495ba2c36056e0ce48fd37d514816c26747/Lib/tokenize.py#L117
        # In order: Hexnumber, Binnumber, Octnumber, Decnumber,
        # Pointfloat + Exponent, Expfloat, Imagnumber
        number_regex = [
                r"\b[+-]?0[xX](?:_?[0-9A-Fa-f])+[lL]?\b",
                r"\b[+-]?0[bB](?:_?[01])+[lL]?\b",
                r"\b[+-]?0[oO](?:_?[0-7])+[lL]?\b",
                r"\b[+-]?(?:0(?:_?0)*|[1-9](?:_?[0-9])*)[lL]?\b",
                r"\b((\.[0-9](?:_?[0-9])*')|\.[0-9](?:_?[0-9])*)"
                "([eE][+-]?[0-9](?:_?[0-9])*)?[jJ]?\b",
                r"\b[0-9](?:_?[0-9])*([eE][+-]?[0-9](?:_?[0-9])*)?[jJ]?\b",
                r"\b[0-9](?:_?[0-9])*[jJ]\b"]
    number = any("number", number_regex)

    string = any("string", [sq3string, dq3string, sqstring, dqstring])
    ufstring1 = any("uf_sqstring", [uf_sqstring])
    ufstring2 = any("uf_dqstring", [uf_dqstring])
    ufstring3 = any("uf_sq3string", [uf_sq3string])
    ufstring4 = any("uf_dq3string", [uf_dq3string])
    ufstring5 = any("ufe_sqstring", [ufe_sqstring])
    ufstring6 = any("ufe_dqstring", [ufe_dqstring])
    return "|".join([instance, kw, builtin, comment,
                     ufstring1, ufstring2, ufstring3, ufstring4, ufstring5,
                     ufstring6, string, number, any("SYNC", [r"\n"])])


def get_code_cell_name(text):
    """Returns a code cell name from a code cell comment."""
    name = text.strip().lstrip("#% ")
    if name.startswith("<codecell>"):
        name = name[10:].lstrip()
    elif name.startswith("In["):
        name = name[2:]
        if name.endswith("]:"):
            name = name[:-1]
        name = name.strip()
    return name


class PythonSH(BaseSH):
    """Python Syntax Highlighter"""
    # Syntax highlighting rules:
    add_kw = ['async', 'await']
    PROG = re.compile(make_python_patterns(additional_keywords=add_kw), re.S)
    IDPROG = re.compile(r"\s+(\w+)", re.S)
    ASPROG = re.compile(r"\b(as)\b")
    # Syntax highlighting states (from one text block to another):
    (NORMAL, INSIDE_SQ3STRING, INSIDE_DQ3STRING,
     INSIDE_SQSTRING, INSIDE_DQSTRING,
     INSIDE_NON_MULTILINE_STRING) = list(range(6))
    DEF_TYPES = {"def": OutlineExplorerData.FUNCTION,
                 "class": OutlineExplorerData.CLASS}
    # Comments suitable for Outline Explorer
    OECOMMENT = re.compile(r'^(# ?--[-]+|##[#]+ )[ -]*[^- ]+')

    def __init__(self, parent, font=None, color_scheme='Spyder'):
        BaseSH.__init__(self, parent, font, color_scheme)
        self.cell_separators = CELL_LANGUAGES['Python']
        # Avoid updating the outline explorer with every single letter typed
        self.outline_explorer_data_update_timer = QTimer()
        self.outline_explorer_data_update_timer.setSingleShot(True)
        self.outline_explorer_data_update_timer.timeout.connect(
            self.sig_outline_explorer_data_changed)

    def highlight_match(self, text, match, key, value, offset,
                        state, import_stmt, oedata):
        """Highlight a single match."""
        start, end = get_span(match, key)
        start = max([0, start+offset])
        end = max([0, end+offset])
        length = end - start
        if key == "uf_sq3string":
            self.setFormat(start, length, self.formats["string"])
            state = self.INSIDE_SQ3STRING
        elif key == "uf_dq3string":
            self.setFormat(start, length, self.formats["string"])
            state = self.INSIDE_DQ3STRING
        elif key == "uf_sqstring":
            self.setFormat(start, length, self.formats["string"])
            state = self.INSIDE_SQSTRING
        elif key == "uf_dqstring":
            self.setFormat(start, length, self.formats["string"])
            state = self.INSIDE_DQSTRING
        elif key in ["ufe_sqstring", "ufe_dqstring"]:
            self.setFormat(start, length, self.formats["string"])
            state = self.INSIDE_NON_MULTILINE_STRING
        else:
            self.setFormat(start, length, self.formats[key])
            if key == "comment":
                if text.lstrip().startswith(self.cell_separators):
                    oedata = OutlineExplorerData(self.currentBlock())
                    oedata.text = to_text_string(text).strip()
                    # cell_head: string contaning the first group
                    # of '%'s in the cell header
                    cell_head = re.search(r"%+|$", text.lstrip()).group()
                    if cell_head == '':
                        oedata.cell_level = 0
                    else:
                        oedata.cell_level = qstring_length(cell_head) - 2
                    oedata.fold_level = start
                    oedata.def_type = OutlineExplorerData.CELL
                    def_name = get_code_cell_name(text)
                    oedata.def_name = def_name
                    # Let the editor know a new cell was added in the document
                    self.sig_new_cell.emit(oedata)
                elif self.OECOMMENT.match(text.lstrip()):
                    oedata = OutlineExplorerData(self.currentBlock())
                    oedata.text = to_text_string(text).strip()
                    oedata.fold_level = start
                    oedata.def_type = OutlineExplorerData.COMMENT
                    oedata.def_name = text.strip()
            elif key == "keyword":
                if value in ("def", "class"):
                    match1 = self.IDPROG.match(text, end)
                    if match1:
                        start1, end1 = get_span(match1, 1)
                        self.setFormat(start1, end1-start1,
                                       self.formats["definition"])
                        oedata = OutlineExplorerData(self.currentBlock())
                        oedata.text = to_text_string(text)
                        oedata.fold_level = (qstring_length(text)
                                             - qstring_length(text.lstrip()))
                        oedata.def_type = self.DEF_TYPES[to_text_string(value)]
                        oedata.def_name = text[start1:end1]
                        oedata.color = self.formats["definition"]
                elif value in ("elif", "else", "except", "finally",
                               "for", "if", "try", "while",
                               "with"):
                    if text.lstrip().startswith(value):
                        oedata = OutlineExplorerData(self.currentBlock())
                        oedata.text = to_text_string(text).strip()
                        oedata.fold_level = start
                        oedata.def_type = OutlineExplorerData.STATEMENT
                        oedata.def_name = text.strip()
                elif value == "import":
                    import_stmt = text.strip()
                    # color all the "as" words on same line, except
                    # if in a comment; cheap approximation to the
                    # truth
                    if '#' in text:
                        endpos = qstring_length(text[:text.index('#')])
                    else:
                        endpos = qstring_length(text)
                    while True:
                        match1 = self.ASPROG.match(text, end, endpos)
                        if not match1:
                            break
                        start, end = get_span(match1, 1)
                        self.setFormat(start, length, self.formats["keyword"])

        return state, import_stmt, oedata

    def highlight_block(self, text):
        """Implement specific highlight for Python."""
        text = to_text_string(text)
        prev_state = tbh.get_state(self.currentBlock().previous())
        if prev_state == self.INSIDE_DQ3STRING:
            offset = -4
            text = r'""" '+text
        elif prev_state == self.INSIDE_SQ3STRING:
            offset = -4
            text = r"''' "+text
        elif prev_state == self.INSIDE_DQSTRING:
            offset = -2
            text = r'" '+text
        elif prev_state == self.INSIDE_SQSTRING:
            offset = -2
            text = r"' "+text
        else:
            offset = 0
            prev_state = self.NORMAL

        oedata = None
        import_stmt = None

        self.setFormat(0, qstring_length(text), self.formats["normal"])

        state = self.NORMAL
        match = self.PROG.search(text)
        while match:
            for key, value in list(match.groupdict().items()):
                if value:
                    state, import_stmt, oedata = self.highlight_match(
                        text, match, key, value, offset,
                        state, import_stmt, oedata)

            match = self.PROG.search(text, match.end())

        tbh.set_state(self.currentBlock(), state)

        # Use normal format for indentation and trailing spaces
        # Unless we are in a string
        states_multiline_string = [
            self.INSIDE_DQ3STRING, self.INSIDE_SQ3STRING,
            self.INSIDE_DQSTRING, self.INSIDE_SQSTRING]
        states_string = states_multiline_string + [
            self.INSIDE_NON_MULTILINE_STRING]
        self.formats['leading'] = self.formats['normal']
        if prev_state in states_multiline_string:
            self.formats['leading'] = self.formats["string"]
        self.formats['trailing'] = self.formats['normal']
        if state in states_string:
            self.formats['trailing'] = self.formats['string']
        self.highlight_extras(text, offset)

        block = self.currentBlock()
        data = block.userData()

        need_data = (oedata or import_stmt)

        if need_data and not data:
            data = BlockUserData(self.editor)

        # Try updating
        update = False
        if oedata and data and data.oedata:
            update = data.oedata.update(oedata)

        if data and not update:
            data.oedata = oedata
            self.outline_explorer_data_update_timer.start(500)

        if (import_stmt) or (data and data.import_statement):
            data.import_statement = import_stmt

        block.setUserData(data)

    def get_import_statements(self):
        """Get import statment list."""
        block = self.document().firstBlock()
        statments = []
        while block.isValid():
            data = block.userData()
            if data and data.import_statement:
                statments.append(data.import_statement)
            block = block.next()
        return statments

    def rehighlight(self):
        BaseSH.rehighlight(self)


#==============================================================================
# Cython syntax highlighter
#==============================================================================
C_TYPES = 'bool char double enum float int long mutable short signed struct unsigned void NULL'

class CythonSH(PythonSH):
    """Cython Syntax Highlighter"""
    ADDITIONAL_KEYWORDS = [
        "cdef", "ctypedef", "cpdef", "inline", "cimport", "extern",
        "include", "begin", "end", "by", "gil", "nogil", "const", "public",
        "readonly", "fused", "static", "api", "DEF", "IF", "ELIF", "ELSE"]

    ADDITIONAL_BUILTINS = C_TYPES.split() + [
        "array", "bint", "Py_ssize_t", "intern", "reload", "sizeof", "NULL"]
    PROG = re.compile(make_python_patterns(ADDITIONAL_KEYWORDS,
                                           ADDITIONAL_BUILTINS), re.S)
    IDPROG = re.compile(r"\s+([\w\.]+)", re.S)


#==============================================================================
# Enaml syntax highlighter
#==============================================================================
class EnamlSH(PythonSH):
    """Enaml Syntax Highlighter"""
    ADDITIONAL_KEYWORDS = ["enamldef", "template", "attr", "event", "const", "alias",
                           "func"]
    ADDITIONAL_BUILTINS = []
    PROG = re.compile(make_python_patterns(ADDITIONAL_KEYWORDS,
                                           ADDITIONAL_BUILTINS), re.S)
    IDPROG = re.compile(r"\s+([\w\.]+)", re.S)


#==============================================================================
# C/C++ syntax highlighter
#==============================================================================
C_KEYWORDS1 = 'and and_eq bitand bitor break case catch const const_cast continue default delete do dynamic_cast else explicit export extern for friend goto if inline namespace new not not_eq operator or or_eq private protected public register reinterpret_cast return sizeof static static_cast switch template throw try typedef typeid typename union using virtual while xor xor_eq'
C_KEYWORDS2 = 'a addindex addtogroup anchor arg attention author b brief bug c class code date def defgroup deprecated dontinclude e em endcode endhtmlonly ifdef endif endlatexonly endlink endverbatim enum example exception f$ file fn hideinitializer htmlinclude htmlonly if image include ingroup internal invariant interface latexonly li line link mainpage name namespace nosubgrouping note overload p page par param post pre ref relates remarks return retval sa section see showinitializer since skip skipline subsection test throw todo typedef union until var verbatim verbinclude version warning weakgroup'
C_KEYWORDS3 = 'asm auto class compl false true volatile wchar_t'

def make_generic_c_patterns(keywords, builtins,
                            instance=None, define=None, comment=None):
    "Strongly inspired from idlelib.ColorDelegator.make_pat"
    kw = r"\b" + any("keyword", keywords.split()) + r"\b"
    builtin = r"\b" + any("builtin", builtins.split()+C_TYPES.split()) + r"\b"
    if comment is None:
        comment = any("comment", [r"//[^\n]*", r"\/\*(.*?)\*\/"])
    comment_start = any("comment_start", [r"\/\*"])
    comment_end = any("comment_end", [r"\*\/"])
    if instance is None:
        instance = any("instance", [r"\bthis\b"])
    number = any("number",
                 [r"\b[+-]?[0-9]+[lL]?\b",
                  r"\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b",
                  r"\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b"])
    sqstring = r"(\b[rRuU])?'[^'\\\n]*(\\.[^'\\\n]*)*'?"
    dqstring = r'(\b[rRuU])?"[^"\\\n]*(\\.[^"\\\n]*)*"?'
    string = any("string", [sqstring, dqstring])
    if define is None:
        define = any("define", [r"#[^\n]*"])
    return "|".join([instance, kw, comment, string, number,
                     comment_start, comment_end, builtin,
                     define, any("SYNC", [r"\n"])])

def make_cpp_patterns():
    return make_generic_c_patterns(C_KEYWORDS1+' '+C_KEYWORDS2, C_KEYWORDS3)

class CppSH(BaseSH):
    """C/C++ Syntax Highlighter"""
    # Syntax highlighting rules:
    PROG = re.compile(make_cpp_patterns(), re.S)
    # Syntax highlighting states (from one text block to another):
    NORMAL = 0
    INSIDE_COMMENT = 1
    def __init__(self, parent, font=None, color_scheme=None):
        BaseSH.__init__(self, parent, font, color_scheme)

    def highlight_block(self, text):
        """Implement highlight specific for C/C++."""
        text = to_text_string(text)
        inside_comment = tbh.get_state(self.currentBlock().previous()) == self.INSIDE_COMMENT
        self.setFormat(0, qstring_length(text),
                       self.formats["comment" if inside_comment else "normal"])

        match = self.PROG.search(text)
        index = 0
        while match:
            for key, value in list(match.groupdict().items()):
                if value:
                    start, end = get_span(match, key)
                    index += end-start
                    if key == "comment_start":
                        inside_comment = True
                        self.setFormat(start, qstring_length(text)-start,
                                       self.formats["comment"])
                    elif key == "comment_end":
                        inside_comment = False
                        self.setFormat(start, end-start,
                                       self.formats["comment"])
                    elif inside_comment:
                        self.setFormat(start, end-start,
                                       self.formats["comment"])
                    elif key == "define":
                        self.setFormat(start, end-start,
                                       self.formats["number"])
                    else:
                        self.setFormat(start, end-start, self.formats[key])

            match = self.PROG.search(text, match.end())

        self.highlight_extras(text)

        last_state = self.INSIDE_COMMENT if inside_comment else self.NORMAL
        tbh.set_state(self.currentBlock(), last_state)


def make_opencl_patterns():
    # Keywords:
    kwstr1 = 'cl_char cl_uchar cl_short cl_ushort cl_int cl_uint cl_long cl_ulong cl_half cl_float cl_double cl_platform_id cl_device_id cl_context cl_command_queue cl_mem cl_program cl_kernel cl_event cl_sampler cl_bool cl_bitfield cl_device_type cl_platform_info cl_device_info cl_device_address_info cl_device_fp_config cl_device_mem_cache_type cl_device_local_mem_type cl_device_exec_capabilities cl_command_queue_properties cl_context_properties cl_context_info cl_command_queue_info cl_channel_order cl_channel_type cl_mem_flags cl_mem_object_type cl_mem_info cl_image_info cl_addressing_mode cl_filter_mode cl_sampler_info cl_map_flags cl_program_info cl_program_build_info cl_build_status cl_kernel_info cl_kernel_work_group_info cl_event_info cl_command_type cl_profiling_info cl_image_format'
    # Constants:
    kwstr2 = 'CL_FALSE, CL_TRUE, CL_PLATFORM_PROFILE, CL_PLATFORM_VERSION, CL_PLATFORM_NAME, CL_PLATFORM_VENDOR, CL_PLATFORM_EXTENSIONS, CL_DEVICE_TYPE_DEFAULT , CL_DEVICE_TYPE_CPU, CL_DEVICE_TYPE_GPU, CL_DEVICE_TYPE_ACCELERATOR, CL_DEVICE_TYPE_ALL, CL_DEVICE_TYPE, CL_DEVICE_VENDOR_ID, CL_DEVICE_MAX_COMPUTE_UNITS, CL_DEVICE_MAX_WORK_ITEM_DIMENSIONS, CL_DEVICE_MAX_WORK_GROUP_SIZE, CL_DEVICE_MAX_WORK_ITEM_SIZES, CL_DEVICE_PREFERRED_VECTOR_WIDTH_CHAR, CL_DEVICE_PREFERRED_VECTOR_WIDTH_SHORT, CL_DEVICE_PREFERRED_VECTOR_WIDTH_INT, CL_DEVICE_PREFERRED_VECTOR_WIDTH_LONG, CL_DEVICE_PREFERRED_VECTOR_WIDTH_FLOAT, CL_DEVICE_PREFERRED_VECTOR_WIDTH_DOUBLE, CL_DEVICE_MAX_CLOCK_FREQUENCY, CL_DEVICE_ADDRESS_BITS, CL_DEVICE_MAX_READ_IMAGE_ARGS, CL_DEVICE_MAX_WRITE_IMAGE_ARGS, CL_DEVICE_MAX_MEM_ALLOC_SIZE, CL_DEVICE_IMAGE2D_MAX_WIDTH, CL_DEVICE_IMAGE2D_MAX_HEIGHT, CL_DEVICE_IMAGE3D_MAX_WIDTH, CL_DEVICE_IMAGE3D_MAX_HEIGHT, CL_DEVICE_IMAGE3D_MAX_DEPTH, CL_DEVICE_IMAGE_SUPPORT, CL_DEVICE_MAX_PARAMETER_SIZE, CL_DEVICE_MAX_SAMPLERS, CL_DEVICE_MEM_BASE_ADDR_ALIGN, CL_DEVICE_MIN_DATA_TYPE_ALIGN_SIZE, CL_DEVICE_SINGLE_FP_CONFIG, CL_DEVICE_GLOBAL_MEM_CACHE_TYPE, CL_DEVICE_GLOBAL_MEM_CACHELINE_SIZE, CL_DEVICE_GLOBAL_MEM_CACHE_SIZE, CL_DEVICE_GLOBAL_MEM_SIZE, CL_DEVICE_MAX_CONSTANT_BUFFER_SIZE, CL_DEVICE_MAX_CONSTANT_ARGS, CL_DEVICE_LOCAL_MEM_TYPE, CL_DEVICE_LOCAL_MEM_SIZE, CL_DEVICE_ERROR_CORRECTION_SUPPORT, CL_DEVICE_PROFILING_TIMER_RESOLUTION, CL_DEVICE_ENDIAN_LITTLE, CL_DEVICE_AVAILABLE, CL_DEVICE_COMPILER_AVAILABLE, CL_DEVICE_EXECUTION_CAPABILITIES, CL_DEVICE_QUEUE_PROPERTIES, CL_DEVICE_NAME, CL_DEVICE_VENDOR, CL_DRIVER_VERSION, CL_DEVICE_PROFILE, CL_DEVICE_VERSION, CL_DEVICE_EXTENSIONS, CL_DEVICE_PLATFORM, CL_FP_DENORM, CL_FP_INF_NAN, CL_FP_ROUND_TO_NEAREST, CL_FP_ROUND_TO_ZERO, CL_FP_ROUND_TO_INF, CL_FP_FMA, CL_NONE, CL_READ_ONLY_CACHE, CL_READ_WRITE_CACHE, CL_LOCAL, CL_GLOBAL, CL_EXEC_KERNEL, CL_EXEC_NATIVE_KERNEL, CL_QUEUE_OUT_OF_ORDER_EXEC_MODE_ENABLE, CL_QUEUE_PROFILING_ENABLE, CL_CONTEXT_REFERENCE_COUNT, CL_CONTEXT_DEVICES, CL_CONTEXT_PROPERTIES, CL_CONTEXT_PLATFORM, CL_QUEUE_CONTEXT, CL_QUEUE_DEVICE, CL_QUEUE_REFERENCE_COUNT, CL_QUEUE_PROPERTIES, CL_MEM_READ_WRITE, CL_MEM_WRITE_ONLY, CL_MEM_READ_ONLY, CL_MEM_USE_HOST_PTR, CL_MEM_ALLOC_HOST_PTR, CL_MEM_COPY_HOST_PTR, CL_R, CL_A, CL_RG, CL_RA, CL_RGB, CL_RGBA, CL_BGRA, CL_ARGB, CL_INTENSITY, CL_LUMINANCE, CL_SNORM_INT8, CL_SNORM_INT16, CL_UNORM_INT8, CL_UNORM_INT16, CL_UNORM_SHORT_565, CL_UNORM_SHORT_555, CL_UNORM_INT_101010, CL_SIGNED_INT8, CL_SIGNED_INT16, CL_SIGNED_INT32, CL_UNSIGNED_INT8, CL_UNSIGNED_INT16, CL_UNSIGNED_INT32, CL_HALF_FLOAT, CL_FLOAT, CL_MEM_OBJECT_BUFFER, CL_MEM_OBJECT_IMAGE2D, CL_MEM_OBJECT_IMAGE3D, CL_MEM_TYPE, CL_MEM_FLAGS, CL_MEM_SIZECL_MEM_HOST_PTR, CL_MEM_HOST_PTR, CL_MEM_MAP_COUNT, CL_MEM_REFERENCE_COUNT, CL_MEM_CONTEXT, CL_IMAGE_FORMAT, CL_IMAGE_ELEMENT_SIZE, CL_IMAGE_ROW_PITCH, CL_IMAGE_SLICE_PITCH, CL_IMAGE_WIDTH, CL_IMAGE_HEIGHT, CL_IMAGE_DEPTH, CL_ADDRESS_NONE, CL_ADDRESS_CLAMP_TO_EDGE, CL_ADDRESS_CLAMP, CL_ADDRESS_REPEAT, CL_FILTER_NEAREST, CL_FILTER_LINEAR, CL_SAMPLER_REFERENCE_COUNT, CL_SAMPLER_CONTEXT, CL_SAMPLER_NORMALIZED_COORDS, CL_SAMPLER_ADDRESSING_MODE, CL_SAMPLER_FILTER_MODE, CL_MAP_READ, CL_MAP_WRITE, CL_PROGRAM_REFERENCE_COUNT, CL_PROGRAM_CONTEXT, CL_PROGRAM_NUM_DEVICES, CL_PROGRAM_DEVICES, CL_PROGRAM_SOURCE, CL_PROGRAM_BINARY_SIZES, CL_PROGRAM_BINARIES, CL_PROGRAM_BUILD_STATUS, CL_PROGRAM_BUILD_OPTIONS, CL_PROGRAM_BUILD_LOG, CL_BUILD_SUCCESS, CL_BUILD_NONE, CL_BUILD_ERROR, CL_BUILD_IN_PROGRESS, CL_KERNEL_FUNCTION_NAME, CL_KERNEL_NUM_ARGS, CL_KERNEL_REFERENCE_COUNT, CL_KERNEL_CONTEXT, CL_KERNEL_PROGRAM, CL_KERNEL_WORK_GROUP_SIZE, CL_KERNEL_COMPILE_WORK_GROUP_SIZE, CL_KERNEL_LOCAL_MEM_SIZE, CL_EVENT_COMMAND_QUEUE, CL_EVENT_COMMAND_TYPE, CL_EVENT_REFERENCE_COUNT, CL_EVENT_COMMAND_EXECUTION_STATUS, CL_COMMAND_NDRANGE_KERNEL, CL_COMMAND_TASK, CL_COMMAND_NATIVE_KERNEL, CL_COMMAND_READ_BUFFER, CL_COMMAND_WRITE_BUFFER, CL_COMMAND_COPY_BUFFER, CL_COMMAND_READ_IMAGE, CL_COMMAND_WRITE_IMAGE, CL_COMMAND_COPY_IMAGE, CL_COMMAND_COPY_IMAGE_TO_BUFFER, CL_COMMAND_COPY_BUFFER_TO_IMAGE, CL_COMMAND_MAP_BUFFER, CL_COMMAND_MAP_IMAGE, CL_COMMAND_UNMAP_MEM_OBJECT, CL_COMMAND_MARKER, CL_COMMAND_ACQUIRE_GL_OBJECTS, CL_COMMAND_RELEASE_GL_OBJECTS, command execution status, CL_COMPLETE, CL_RUNNING, CL_SUBMITTED, CL_QUEUED, CL_PROFILING_COMMAND_QUEUED, CL_PROFILING_COMMAND_SUBMIT, CL_PROFILING_COMMAND_START, CL_PROFILING_COMMAND_END, CL_CHAR_BIT, CL_SCHAR_MAX, CL_SCHAR_MIN, CL_CHAR_MAX, CL_CHAR_MIN, CL_UCHAR_MAX, CL_SHRT_MAX, CL_SHRT_MIN, CL_USHRT_MAX, CL_INT_MAX, CL_INT_MIN, CL_UINT_MAX, CL_LONG_MAX, CL_LONG_MIN, CL_ULONG_MAX, CL_FLT_DIG, CL_FLT_MANT_DIG, CL_FLT_MAX_10_EXP, CL_FLT_MAX_EXP, CL_FLT_MIN_10_EXP, CL_FLT_MIN_EXP, CL_FLT_RADIX, CL_FLT_MAX, CL_FLT_MIN, CL_FLT_EPSILON, CL_DBL_DIG, CL_DBL_MANT_DIG, CL_DBL_MAX_10_EXP, CL_DBL_MAX_EXP, CL_DBL_MIN_10_EXP, CL_DBL_MIN_EXP, CL_DBL_RADIX, CL_DBL_MAX, CL_DBL_MIN, CL_DBL_EPSILON, CL_SUCCESS, CL_DEVICE_NOT_FOUND, CL_DEVICE_NOT_AVAILABLE, CL_COMPILER_NOT_AVAILABLE, CL_MEM_OBJECT_ALLOCATION_FAILURE, CL_OUT_OF_RESOURCES, CL_OUT_OF_HOST_MEMORY, CL_PROFILING_INFO_NOT_AVAILABLE, CL_MEM_COPY_OVERLAP, CL_IMAGE_FORMAT_MISMATCH, CL_IMAGE_FORMAT_NOT_SUPPORTED, CL_BUILD_PROGRAM_FAILURE, CL_MAP_FAILURE, CL_INVALID_VALUE, CL_INVALID_DEVICE_TYPE, CL_INVALID_PLATFORM, CL_INVALID_DEVICE, CL_INVALID_CONTEXT, CL_INVALID_QUEUE_PROPERTIES, CL_INVALID_COMMAND_QUEUE, CL_INVALID_HOST_PTR, CL_INVALID_MEM_OBJECT, CL_INVALID_IMAGE_FORMAT_DESCRIPTOR, CL_INVALID_IMAGE_SIZE, CL_INVALID_SAMPLER, CL_INVALID_BINARY, CL_INVALID_BUILD_OPTIONS, CL_INVALID_PROGRAM, CL_INVALID_PROGRAM_EXECUTABLE, CL_INVALID_KERNEL_NAME, CL_INVALID_KERNEL_DEFINITION, CL_INVALID_KERNEL, CL_INVALID_ARG_INDEX, CL_INVALID_ARG_VALUE, CL_INVALID_ARG_SIZE, CL_INVALID_KERNEL_ARGS, CL_INVALID_WORK_DIMENSION, CL_INVALID_WORK_GROUP_SIZE, CL_INVALID_WORK_ITEM_SIZE, CL_INVALID_GLOBAL_OFFSET, CL_INVALID_EVENT_WAIT_LIST, CL_INVALID_EVENT, CL_INVALID_OPERATION, CL_INVALID_GL_OBJECT, CL_INVALID_BUFFER_SIZE, CL_INVALID_MIP_LEVEL, CL_INVALID_GLOBAL_WORK_SIZE'
    # Functions:
    builtins = 'clGetPlatformIDs, clGetPlatformInfo, clGetDeviceIDs, clGetDeviceInfo, clCreateContext, clCreateContextFromType, clReleaseContext, clGetContextInfo, clCreateCommandQueue, clRetainCommandQueue, clReleaseCommandQueue, clGetCommandQueueInfo, clSetCommandQueueProperty, clCreateBuffer, clCreateImage2D, clCreateImage3D, clRetainMemObject, clReleaseMemObject, clGetSupportedImageFormats, clGetMemObjectInfo, clGetImageInfo, clCreateSampler, clRetainSampler, clReleaseSampler, clGetSamplerInfo, clCreateProgramWithSource, clCreateProgramWithBinary, clRetainProgram, clReleaseProgram, clBuildProgram, clUnloadCompiler, clGetProgramInfo, clGetProgramBuildInfo, clCreateKernel, clCreateKernelsInProgram, clRetainKernel, clReleaseKernel, clSetKernelArg, clGetKernelInfo, clGetKernelWorkGroupInfo, clWaitForEvents, clGetEventInfo, clRetainEvent, clReleaseEvent, clGetEventProfilingInfo, clFlush, clFinish, clEnqueueReadBuffer, clEnqueueWriteBuffer, clEnqueueCopyBuffer, clEnqueueReadImage, clEnqueueWriteImage, clEnqueueCopyImage, clEnqueueCopyImageToBuffer, clEnqueueCopyBufferToImage, clEnqueueMapBuffer, clEnqueueMapImage, clEnqueueUnmapMemObject, clEnqueueNDRangeKernel, clEnqueueTask, clEnqueueNativeKernel, clEnqueueMarker, clEnqueueWaitForEvents, clEnqueueBarrier'
    # Qualifiers:
    qualifiers = '__global __local __constant __private __kernel'
    keyword_list = C_KEYWORDS1+' '+C_KEYWORDS2+' '+kwstr1+' '+kwstr2
    builtin_list = C_KEYWORDS3+' '+builtins+' '+qualifiers
    return make_generic_c_patterns(keyword_list, builtin_list)

class OpenCLSH(CppSH):
    """OpenCL Syntax Highlighter"""
    PROG = re.compile(make_opencl_patterns(), re.S)


#==============================================================================
# Fortran Syntax Highlighter
#==============================================================================
def make_fortran_patterns():
    "Strongly inspired from idlelib.ColorDelegator.make_pat"
    kwstr = 'access action advance allocatable allocate apostrophe assign assignment associate asynchronous backspace bind blank blockdata call case character class close common complex contains continue cycle data deallocate decimal delim default dimension direct do dowhile double doubleprecision else elseif elsewhere encoding end endassociate endblockdata enddo endfile endforall endfunction endif endinterface endmodule endprogram endselect endsubroutine endtype endwhere entry eor equivalence err errmsg exist exit external file flush fmt forall form format formatted function go goto id if implicit in include inout integer inquire intent interface intrinsic iomsg iolength iostat kind len logical module name named namelist nextrec nml none nullify number only open opened operator optional out pad parameter pass pause pending pointer pos position precision print private program protected public quote read readwrite real rec recl recursive result return rewind save select selectcase selecttype sequential sign size stat status stop stream subroutine target then to type unformatted unit use value volatile wait where while write'
    bistr1 = 'abs achar acos acosd adjustl adjustr aimag aimax0 aimin0 aint ajmax0 ajmin0 akmax0 akmin0 all allocated alog alog10 amax0 amax1 amin0 amin1 amod anint any asin asind associated atan atan2 atan2d atand bitest bitl bitlr bitrl bjtest bit_size bktest break btest cabs ccos cdabs cdcos cdexp cdlog cdsin cdsqrt ceiling cexp char clog cmplx conjg cos cosd cosh count cpu_time cshift csin csqrt dabs dacos dacosd dasin dasind datan datan2 datan2d datand date date_and_time dble dcmplx dconjg dcos dcosd dcosh dcotan ddim dexp dfloat dflotk dfloti dflotj digits dim dimag dint dlog dlog10 dmax1 dmin1 dmod dnint dot_product dprod dreal dsign dsin dsind dsinh dsqrt dtan dtand dtanh eoshift epsilon errsns exp exponent float floati floatj floatk floor fraction free huge iabs iachar iand ibclr ibits ibset ichar idate idim idint idnint ieor ifix iiabs iiand iibclr iibits iibset iidim iidint iidnnt iieor iifix iint iior iiqint iiqnnt iishft iishftc iisign ilen imax0 imax1 imin0 imin1 imod index inint inot int int1 int2 int4 int8 iqint iqnint ior ishft ishftc isign isnan izext jiand jibclr jibits jibset jidim jidint jidnnt jieor jifix jint jior jiqint jiqnnt jishft jishftc jisign jmax0 jmax1 jmin0 jmin1 jmod jnint jnot jzext kiabs kiand kibclr kibits kibset kidim kidint kidnnt kieor kifix kind kint kior kishft kishftc kisign kmax0 kmax1 kmin0 kmin1 kmod knint knot kzext lbound leadz len len_trim lenlge lge lgt lle llt log log10 logical lshift malloc matmul max max0 max1 maxexponent maxloc maxval merge min min0 min1 minexponent minloc minval mod modulo mvbits nearest nint not nworkers number_of_processors pack popcnt poppar precision present product radix random random_number random_seed range real repeat reshape rrspacing rshift scale scan secnds selected_int_kind selected_real_kind set_exponent shape sign sin sind sinh size sizeof sngl snglq spacing spread sqrt sum system_clock tan tand tanh tiny transfer transpose trim ubound unpack verify'
    bistr2 = 'cdabs cdcos cdexp cdlog cdsin cdsqrt cotan cotand dcmplx dconjg dcotan dcotand decode dimag dll_export dll_import doublecomplex dreal dvchk encode find flen flush getarg getcharqq getcl getdat getenv gettim hfix ibchng identifier imag int1 int2 int4 intc intrup invalop iostat_msg isha ishc ishl jfix lacfar locking locnear map nargs nbreak ndperr ndpexc offset ovefl peekcharqq precfill prompt qabs qacos qacosd qasin qasind qatan qatand qatan2 qcmplx qconjg qcos qcosd qcosh qdim qexp qext qextd qfloat qimag qlog qlog10 qmax1 qmin1 qmod qreal qsign qsin qsind qsinh qsqrt qtan qtand qtanh ran rand randu rewrite segment setdat settim system timer undfl unlock union val virtual volatile zabs zcos zexp zlog zsin zsqrt'
    kw = r"\b" + any("keyword", kwstr.split()) + r"\b"
    builtin = r"\b" + any("builtin", bistr1.split()+bistr2.split()) + r"\b"
    comment = any("comment", [r"\![^\n]*"])
    number = any("number",
                 [r"\b[+-]?[0-9]+[lL]?\b",
                  r"\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b",
                  r"\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b"])
    sqstring = r"(\b[rRuU])?'[^'\\\n]*(\\.[^'\\\n]*)*'?"
    dqstring = r'(\b[rRuU])?"[^"\\\n]*(\\.[^"\\\n]*)*"?'
    string = any("string", [sqstring, dqstring])
    return "|".join([kw, comment, string, number, builtin,
                     any("SYNC", [r"\n"])])

class FortranSH(BaseSH):
    """Fortran Syntax Highlighter"""
    # Syntax highlighting rules:
    PROG = re.compile(make_fortran_patterns(), re.S|re.I)
    IDPROG = re.compile(r"\s+(\w+)", re.S)
    # Syntax highlighting states (from one text block to another):
    NORMAL = 0
    def __init__(self, parent, font=None, color_scheme=None):
        BaseSH.__init__(self, parent, font, color_scheme)

    def highlight_block(self, text):
        """Implement highlight specific for Fortran."""
        text = to_text_string(text)
        self.setFormat(0, qstring_length(text), self.formats["normal"])

        match = self.PROG.search(text)
        index = 0
        while match:
            for key, value in list(match.groupdict().items()):
                if value:
                    start, end = get_span(match, key)
                    index += end-start
                    self.setFormat(start, end-start, self.formats[key])
                    if value.lower() in ("subroutine", "module", "function"):
                        match1 = self.IDPROG.match(text, end)
                        if match1:
                            start1, end1 = get_span(match1, 1)
                            self.setFormat(start1, end1-start1,
                                           self.formats["definition"])

            match = self.PROG.search(text, match.end())

        self.highlight_extras(text)

class Fortran77SH(FortranSH):
    """Fortran 77 Syntax Highlighter"""
    def highlight_block(self, text):
        """Implement highlight specific for Fortran77."""
        text = to_text_string(text)
        if text.startswith(("c", "C")):
            self.setFormat(0, qstring_length(text), self.formats["comment"])
            self.highlight_extras(text)
        else:
            FortranSH.highlight_block(self, text)
            self.setFormat(0, 5, self.formats["comment"])
            self.setFormat(73, max([73, qstring_length(text)]),
                           self.formats["comment"])


#==============================================================================
# IDL highlighter
#
# Contribution from Stuart Mumford (Littlemumford) - 2012-02-02
# See spyder-ide/spyder#850.
#==============================================================================
def make_idl_patterns():
    """Strongly inspired by idlelib.ColorDelegator.make_pat."""
    kwstr = 'begin of pro function endfor endif endwhile endrep endcase endswitch end if then else for do while repeat until break case switch common continue exit return goto help message print read retall stop'
    bistr1 = 'a_correlate abs acos adapt_hist_equal alog alog10 amoeba arg_present arra_equal array_indices ascii_template asin assoc atan beseli beselj besel k besely beta bilinear bin_date binary_template dinfgen dinomial blk_con broyden bytarr byte bytscl c_correlate call_external call_function ceil chebyshev check_math chisqr_cvf chisqr_pdf choldc cholsol cindgen clust_wts cluster color_quan colormap_applicable comfit complex complexarr complexround compute_mesh_normals cond congrid conj convert_coord convol coord2to3 correlate cos cosh cramer create_struct crossp crvlength ct_luminance cti_test curvefit cv_coord cvttobm cw_animate cw_arcball cw_bgroup cw_clr_index cw_colorsel cw_defroi cw_field cw_filesel cw_form cw_fslider cw_light_editor cw_orient cw_palette_editor cw_pdmenu cw_rgbslider cw_tmpl cw_zoom dblarr dcindgen dcomplexarr defroi deriv derivsig determ diag_matrix dialog_message dialog_pickfile pialog_printersetup dialog_printjob dialog_read_image dialog_write_image digital_filter dilate dindgen dist double eigenql eigenvec elmhes eof erode erf erfc erfcx execute exp expand_path expint extrac extract_slice f_cvf f_pdf factorial fft file_basename file_dirname file_expand_path file_info file_same file_search file_test file_which filepath findfile findgen finite fix float floor fltarr format_axis_values fstat fulstr fv_test fx_root fz_roots gamma gauss_cvf gauss_pdf gauss2dfit gaussfit gaussint get_drive_list get_kbrd get_screen_size getenv grid_tps grid3 griddata gs_iter hanning hdf_browser hdf_read hilbert hist_2d hist_equal histogram hough hqr ibeta identity idl_validname idlitsys_createtool igamma imaginary indgen int_2d int_3d int_tabulated intarr interpol interpolate invert ioctl ishft julday keword_set krig2d kurtosis kw_test l64indgen label_date label_region ladfit laguerre la_cholmprove la_cholsol la_Determ la_eigenproblem la_eigenql la_eigenvec la_elmhes la_gm_linear_model la_hqr la_invert la_least_square_equality la_least_squares la_linear_equation la_lumprove la_lusol la_trimprove la_trisol leefit legendre linbcg lindgen linfit ll_arc_distance lmfit lmgr lngamma lnp_test locale_get logical_and logical_or logical_true lon64arr lonarr long long64 lsode lu_complex lumprove lusol m_correlate machar make_array map_2points map_image map_patch map_proj_forward map_proj_init map_proj_inverse matrix_multiply matrix_power max md_test mean meanabsdev median memory mesh_clip mesh_decimate mesh_issolid mesh_merge mesh_numtriangles mesh_smooth mesh_surfacearea mesh_validate mesh_volume min min_curve_surf moment morph_close morph_distance morph_gradient morph_histormiss morph_open morph_thin morph_tophat mpeg_open msg_cat_open n_elements n_params n_tags newton norm obj_class obj_isa obj_new obj_valid objarr p_correlate path_sep pcomp pnt_line polar_surface poly poly_2d poly_area poly_fit polyfillv ployshade primes product profile profiles project_vol ptr_new ptr_valid ptrarr qgrid3 qromb qromo qsimp query_bmp query_dicom query_image query_jpeg query_mrsid query_pict query_png query_ppm query_srf query_tiff query_wav r_correlate r_test radon randomn randomu ranks read_ascii read_binary read_bmp read_dicom read_image read_mrsid read_png read_spr read_sylk read_tiff read_wav read_xwd real_part rebin recall_commands recon3 reform region_grow regress replicate reverse rk4 roberts rot rotate round routine_info rs_test s_test savgol search2d search3d sfit shift shmdebug shmvar simplex sin sindgen sinh size skewness smooth sobel sort sph_scat spher_harm spl_init spl_interp spline spline_p sprsab sprsax sprsin sprstp sqrt standardize stddev strarr strcmp strcompress stregex string strjoin strlen strlowcase strmatch strmessage strmid strpos strsplit strtrim strupcase svdfit svsol swap_endian systime t_cvf t_pdf tag_names tan tanh temporary tetra_clip tetra_surface tetra_volume thin timegen tm_test total trace transpose tri_surf trigrid trisol ts_coef ts_diff ts_fcast ts_smooth tvrd uindgen unit uintarr ul64indgen ulindgen ulon64arr ulonarr ulong ulong64 uniq value_locate variance vert_t3d voigt voxel_proj warp_tri watershed where widget_actevix widget_base widget_button widget_combobox widget_draw widget_droplist widget_event widget_info widget_label widget_list widget_propertsheet widget_slider widget_tab widget_table widget_text widget_tree write_sylk wtn xfont xregistered xsq_test'
    bistr2 = 'annotate arrow axis bar_plot blas_axpy box_cursor breakpoint byteorder caldata calendar call_method call_procedure catch cd cir_3pnt close color_convert compile_opt constrained_min contour copy_lun cpu create_view cursor cw_animate_getp cw_animate_load cw_animate_run cw_light_editor_get cw_light_editor_set cw_palette_editor_get cw_palette_editor_set define_key define_msgblk define_msgblk_from_file defsysv delvar device dfpmin dissolve dlm_load doc_librar draw_roi efont empty enable_sysrtn erase errplot expand file_chmod file_copy file_delete file_lines file_link file_mkdir file_move file_readlink flick flow3 flush forward_function free_lun funct gamma_ct get_lun grid_input h_eq_ct h_eq_int heap_free heap_gc hls hsv icontour iimage image_cont image_statistics internal_volume iplot isocontour isosurface isurface itcurrent itdelete itgetcurrent itregister itreset ivolume journal la_choldc la_ludc la_svd la_tridc la_triql la_trired linkimage loadct ludc make_dll map_continents map_grid map_proj_info map_set mesh_obj mk_html_help modifyct mpeg_close mpeg_put mpeg_save msg_cat_close msg_cat_compile multi obj_destroy on_error on_ioerror online_help openr openw openu oplot oploterr particle_trace path_cache plot plot_3dbox plot_field ploterr plots point_lun polar_contour polyfill polywarp popd powell printf printd ps_show_fonts psafm pseudo ptr_free pushd qhull rdpix readf read_interfile read_jpeg read_pict read_ppm read_srf read_wave read_x11_bitmap reads readu reduce_colors register_cursor replicate_inplace resolve_all resolve_routine restore save scale3 scale3d set_plot set_shading setenv setup_keys shade_surf shade_surf_irr shade_volume shmmap show3 showfont skip_lun slicer3 slide_image socket spawn sph_4pnt streamline stretch strput struct_assign struct_hide surface surfr svdc swap_enian_inplace t3d tek_color threed time_test2 triangulate triql trired truncate_lun tv tvcrs tvlct tvscl usersym vector_field vel velovect voronoi wait wdelete wf_draw widget_control widget_displaycontextmenu window write_bmp write_image write_jpeg write_nrif write_pict write_png write_ppm write_spr write_srf write_tiff write_wav write_wave writeu wset wshow xbm_edit xdisplayfile xdxf xinteranimate xloadct xmanager xmng_tmpl xmtool xobjview xobjview_rotate xobjview_write_image xpalette xpcolo xplot3d xroi xsurface xvaredit xvolume xyouts zoom zoom_24'
    kw = r"\b" + any("keyword", kwstr.split()) + r"\b"
    builtin = r"\b" + any("builtin", bistr1.split()+bistr2.split()) + r"\b"
    comment = any("comment", [r"\;[^\n]*"])
    number = any("number",
                 [r"\b[+-]?[0-9]+[lL]?\b",
                  r"\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b",
		  r"\b\.[0-9]d0|\.d0+[lL]?\b",
                  r"\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b"])
    sqstring = r"(\b[rRuU])?'[^'\\\n]*(\\.[^'\\\n]*)*'?"
    dqstring = r'(\b[rRuU])?"[^"\\\n]*(\\.[^"\\\n]*)*"?'
    string = any("string", [sqstring, dqstring])
    return "|".join([kw, comment, string, number, builtin,
                     any("SYNC", [r"\n"])])

class IdlSH(GenericSH):
    """IDL Syntax Highlighter"""
    PROG = re.compile(make_idl_patterns(), re.S|re.I)


#==============================================================================
# Diff/Patch highlighter
#==============================================================================
class DiffSH(BaseSH):
    """Simple Diff/Patch Syntax Highlighter Class"""
    def highlight_block(self, text):
        """Implement highlight specific Diff/Patch files."""
        text = to_text_string(text)
        if text.startswith("+++"):
            self.setFormat(0, qstring_length(text), self.formats["keyword"])
        elif text.startswith("---"):
            self.setFormat(0, qstring_length(text), self.formats["keyword"])
        elif text.startswith("+"):
            self.setFormat(0, qstring_length(text), self.formats["string"])
        elif text.startswith("-"):
            self.setFormat(0, qstring_length(text), self.formats["number"])
        elif text.startswith("@"):
            self.setFormat(0, qstring_length(text), self.formats["builtin"])

        self.highlight_extras(text)

#==============================================================================
# NSIS highlighter
#==============================================================================
def make_nsis_patterns():
    "Strongly inspired from idlelib.ColorDelegator.make_pat"
    kwstr1 = 'Abort AddBrandingImage AddSize AllowRootDirInstall AllowSkipFiles AutoCloseWindow BGFont BGGradient BrandingText BringToFront Call CallInstDLL Caption ClearErrors CompletedText ComponentText CopyFiles CRCCheck CreateDirectory CreateFont CreateShortCut Delete DeleteINISec DeleteINIStr DeleteRegKey DeleteRegValue DetailPrint DetailsButtonText DirText DirVar DirVerify EnableWindow EnumRegKey EnumRegValue Exec ExecShell ExecWait Exch ExpandEnvStrings File FileBufSize FileClose FileErrorText FileOpen FileRead FileReadByte FileSeek FileWrite FileWriteByte FindClose FindFirst FindNext FindWindow FlushINI Function FunctionEnd GetCurInstType GetCurrentAddress GetDlgItem GetDLLVersion GetDLLVersionLocal GetErrorLevel GetFileTime GetFileTimeLocal GetFullPathName GetFunctionAddress GetInstDirError GetLabelAddress GetTempFileName Goto HideWindow ChangeUI CheckBitmap Icon IfAbort IfErrors IfFileExists IfRebootFlag IfSilent InitPluginsDir InstallButtonText InstallColors InstallDir InstallDirRegKey InstProgressFlags InstType InstTypeGetText InstTypeSetText IntCmp IntCmpU IntFmt IntOp IsWindow LangString LicenseBkColor LicenseData LicenseForceSelection LicenseLangString LicenseText LoadLanguageFile LogSet LogText MessageBox MiscButtonText Name OutFile Page PageCallbacks PageEx PageExEnd Pop Push Quit ReadEnvStr ReadINIStr ReadRegDWORD ReadRegStr Reboot RegDLL Rename ReserveFile Return RMDir SearchPath Section SectionEnd SectionGetFlags SectionGetInstTypes SectionGetSize SectionGetText SectionIn SectionSetFlags SectionSetInstTypes SectionSetSize SectionSetText SendMessage SetAutoClose SetBrandingImage SetCompress SetCompressor SetCompressorDictSize SetCtlColors SetCurInstType SetDatablockOptimize SetDateSave SetDetailsPrint SetDetailsView SetErrorLevel SetErrors SetFileAttributes SetFont SetOutPath SetOverwrite SetPluginUnload SetRebootFlag SetShellVarContext SetSilent ShowInstDetails ShowUninstDetails ShowWindow SilentInstall SilentUnInstall Sleep SpaceTexts StrCmp StrCpy StrLen SubCaption SubSection SubSectionEnd UninstallButtonText UninstallCaption UninstallIcon UninstallSubCaption UninstallText UninstPage UnRegDLL Var VIAddVersionKey VIProductVersion WindowIcon WriteINIStr WriteRegBin WriteRegDWORD WriteRegExpandStr WriteRegStr WriteUninstaller XPStyle'
    kwstr2 = 'all alwaysoff ARCHIVE auto both bzip2 components current custom details directory false FILE_ATTRIBUTE_ARCHIVE FILE_ATTRIBUTE_HIDDEN FILE_ATTRIBUTE_NORMAL FILE_ATTRIBUTE_OFFLINE FILE_ATTRIBUTE_READONLY FILE_ATTRIBUTE_SYSTEM FILE_ATTRIBUTE_TEMPORARY force grey HIDDEN hide IDABORT IDCANCEL IDIGNORE IDNO IDOK IDRETRY IDYES ifdiff ifnewer instfiles instfiles lastused leave left level license listonly lzma manual MB_ABORTRETRYIGNORE MB_DEFBUTTON1 MB_DEFBUTTON2 MB_DEFBUTTON3 MB_DEFBUTTON4 MB_ICONEXCLAMATION MB_ICONINFORMATION MB_ICONQUESTION MB_ICONSTOP MB_OK MB_OKCANCEL MB_RETRYCANCEL MB_RIGHT MB_SETFOREGROUND MB_TOPMOST MB_YESNO MB_YESNOCANCEL nevershow none NORMAL off OFFLINE on READONLY right RO show silent silentlog SYSTEM TEMPORARY text textonly true try uninstConfirm windows zlib'
    kwstr3 = 'MUI_ABORTWARNING MUI_ABORTWARNING_CANCEL_DEFAULT MUI_ABORTWARNING_TEXT MUI_BGCOLOR MUI_COMPONENTSPAGE_CHECKBITMAP MUI_COMPONENTSPAGE_NODESC MUI_COMPONENTSPAGE_SMALLDESC MUI_COMPONENTSPAGE_TEXT_COMPLIST MUI_COMPONENTSPAGE_TEXT_DESCRIPTION_INFO MUI_COMPONENTSPAGE_TEXT_DESCRIPTION_TITLE MUI_COMPONENTSPAGE_TEXT_INSTTYPE MUI_COMPONENTSPAGE_TEXT_TOP MUI_CUSTOMFUNCTION_ABORT MUI_CUSTOMFUNCTION_GUIINIT MUI_CUSTOMFUNCTION_UNABORT MUI_CUSTOMFUNCTION_UNGUIINIT MUI_DESCRIPTION_TEXT MUI_DIRECTORYPAGE_BGCOLOR MUI_DIRECTORYPAGE_TEXT_DESTINATION MUI_DIRECTORYPAGE_TEXT_TOP MUI_DIRECTORYPAGE_VARIABLE MUI_DIRECTORYPAGE_VERIFYONLEAVE MUI_FINISHPAGE_BUTTON MUI_FINISHPAGE_CANCEL_ENABLED MUI_FINISHPAGE_LINK MUI_FINISHPAGE_LINK_COLOR MUI_FINISHPAGE_LINK_LOCATION MUI_FINISHPAGE_NOAUTOCLOSE MUI_FINISHPAGE_NOREBOOTSUPPORT MUI_FINISHPAGE_REBOOTLATER_DEFAULT MUI_FINISHPAGE_RUN MUI_FINISHPAGE_RUN_FUNCTION MUI_FINISHPAGE_RUN_NOTCHECKED MUI_FINISHPAGE_RUN_PARAMETERS MUI_FINISHPAGE_RUN_TEXT MUI_FINISHPAGE_SHOWREADME MUI_FINISHPAGE_SHOWREADME_FUNCTION MUI_FINISHPAGE_SHOWREADME_NOTCHECKED MUI_FINISHPAGE_SHOWREADME_TEXT MUI_FINISHPAGE_TEXT MUI_FINISHPAGE_TEXT_LARGE MUI_FINISHPAGE_TEXT_REBOOT MUI_FINISHPAGE_TEXT_REBOOTLATER MUI_FINISHPAGE_TEXT_REBOOTNOW MUI_FINISHPAGE_TITLE MUI_FINISHPAGE_TITLE_3LINES MUI_FUNCTION_DESCRIPTION_BEGIN MUI_FUNCTION_DESCRIPTION_END MUI_HEADER_TEXT MUI_HEADER_TRANSPARENT_TEXT MUI_HEADERIMAGE MUI_HEADERIMAGE_BITMAP MUI_HEADERIMAGE_BITMAP_NOSTRETCH MUI_HEADERIMAGE_BITMAP_RTL MUI_HEADERIMAGE_BITMAP_RTL_NOSTRETCH MUI_HEADERIMAGE_RIGHT MUI_HEADERIMAGE_UNBITMAP MUI_HEADERIMAGE_UNBITMAP_NOSTRETCH MUI_HEADERIMAGE_UNBITMAP_RTL MUI_HEADERIMAGE_UNBITMAP_RTL_NOSTRETCH MUI_HWND MUI_ICON MUI_INSTALLCOLORS MUI_INSTALLOPTIONS_DISPLAY MUI_INSTALLOPTIONS_DISPLAY_RETURN MUI_INSTALLOPTIONS_EXTRACT MUI_INSTALLOPTIONS_EXTRACT_AS MUI_INSTALLOPTIONS_INITDIALOG MUI_INSTALLOPTIONS_READ MUI_INSTALLOPTIONS_SHOW MUI_INSTALLOPTIONS_SHOW_RETURN MUI_INSTALLOPTIONS_WRITE MUI_INSTFILESPAGE_ABORTHEADER_SUBTEXT MUI_INSTFILESPAGE_ABORTHEADER_TEXT MUI_INSTFILESPAGE_COLORS MUI_INSTFILESPAGE_FINISHHEADER_SUBTEXT MUI_INSTFILESPAGE_FINISHHEADER_TEXT MUI_INSTFILESPAGE_PROGRESSBAR MUI_LANGDLL_ALLLANGUAGES MUI_LANGDLL_ALWAYSSHOW MUI_LANGDLL_DISPLAY MUI_LANGDLL_INFO MUI_LANGDLL_REGISTRY_KEY MUI_LANGDLL_REGISTRY_ROOT MUI_LANGDLL_REGISTRY_VALUENAME MUI_LANGDLL_WINDOWTITLE MUI_LANGUAGE MUI_LICENSEPAGE_BGCOLOR MUI_LICENSEPAGE_BUTTON MUI_LICENSEPAGE_CHECKBOX MUI_LICENSEPAGE_CHECKBOX_TEXT MUI_LICENSEPAGE_RADIOBUTTONS MUI_LICENSEPAGE_RADIOBUTTONS_TEXT_ACCEPT MUI_LICENSEPAGE_RADIOBUTTONS_TEXT_DECLINE MUI_LICENSEPAGE_TEXT_BOTTOM MUI_LICENSEPAGE_TEXT_TOP MUI_PAGE_COMPONENTS MUI_PAGE_CUSTOMFUNCTION_LEAVE MUI_PAGE_CUSTOMFUNCTION_PRE MUI_PAGE_CUSTOMFUNCTION_SHOW MUI_PAGE_DIRECTORY MUI_PAGE_FINISH MUI_PAGE_HEADER_SUBTEXT MUI_PAGE_HEADER_TEXT MUI_PAGE_INSTFILES MUI_PAGE_LICENSE MUI_PAGE_STARTMENU MUI_PAGE_WELCOME MUI_RESERVEFILE_INSTALLOPTIONS MUI_RESERVEFILE_LANGDLL MUI_SPECIALINI MUI_STARTMENU_GETFOLDER MUI_STARTMENU_WRITE_BEGIN MUI_STARTMENU_WRITE_END MUI_STARTMENUPAGE_BGCOLOR MUI_STARTMENUPAGE_DEFAULTFOLDER MUI_STARTMENUPAGE_NODISABLE MUI_STARTMENUPAGE_REGISTRY_KEY MUI_STARTMENUPAGE_REGISTRY_ROOT MUI_STARTMENUPAGE_REGISTRY_VALUENAME MUI_STARTMENUPAGE_TEXT_CHECKBOX MUI_STARTMENUPAGE_TEXT_TOP MUI_UI MUI_UI_COMPONENTSPAGE_NODESC MUI_UI_COMPONENTSPAGE_SMALLDESC MUI_UI_HEADERIMAGE MUI_UI_HEADERIMAGE_RIGHT MUI_UNABORTWARNING MUI_UNABORTWARNING_CANCEL_DEFAULT MUI_UNABORTWARNING_TEXT MUI_UNCONFIRMPAGE_TEXT_LOCATION MUI_UNCONFIRMPAGE_TEXT_TOP MUI_UNFINISHPAGE_NOAUTOCLOSE MUI_UNFUNCTION_DESCRIPTION_BEGIN MUI_UNFUNCTION_DESCRIPTION_END MUI_UNGETLANGUAGE MUI_UNICON MUI_UNPAGE_COMPONENTS MUI_UNPAGE_CONFIRM MUI_UNPAGE_DIRECTORY MUI_UNPAGE_FINISH MUI_UNPAGE_INSTFILES MUI_UNPAGE_LICENSE MUI_UNPAGE_WELCOME MUI_UNWELCOMEFINISHPAGE_BITMAP MUI_UNWELCOMEFINISHPAGE_BITMAP_NOSTRETCH MUI_UNWELCOMEFINISHPAGE_INI MUI_WELCOMEFINISHPAGE_BITMAP MUI_WELCOMEFINISHPAGE_BITMAP_NOSTRETCH MUI_WELCOMEFINISHPAGE_CUSTOMFUNCTION_INIT MUI_WELCOMEFINISHPAGE_INI MUI_WELCOMEPAGE_TEXT MUI_WELCOMEPAGE_TITLE MUI_WELCOMEPAGE_TITLE_3LINES'
    bistr = 'addincludedir addplugindir AndIf cd define echo else endif error execute If ifdef ifmacrodef ifmacrondef ifndef include insertmacro macro macroend onGUIEnd onGUIInit onInit onInstFailed onInstSuccess onMouseOverSection onRebootFailed onSelChange onUserAbort onVerifyInstDir OrIf packhdr system undef verbose warning'
    instance = any("instance", [r'\$\{.*?\}', r'\$[A-Za-z0-9\_]*'])
    define = any("define", [r"\![^\n]*"])
    comment = any("comment", [r"\;[^\n]*", r"\#[^\n]*", r"\/\*(.*?)\*\/"])
    return make_generic_c_patterns(kwstr1+' '+kwstr2+' '+kwstr3, bistr,
                                   instance=instance, define=define,
                                   comment=comment)

class NsisSH(CppSH):
    """NSIS Syntax Highlighter"""
    # Syntax highlighting rules:
    PROG = re.compile(make_nsis_patterns(), re.S)


#==============================================================================
# gettext highlighter
#==============================================================================
def make_gettext_patterns():
    "Strongly inspired from idlelib.ColorDelegator.make_pat"
    kwstr = 'msgid msgstr'
    kw = r"\b" + any("keyword", kwstr.split()) + r"\b"
    fuzzy = any("builtin", [r"#,[^\n]*"])
    links = any("normal", [r"#:[^\n]*"])
    comment = any("comment", [r"#[^\n]*"])
    number = any("number",
                 [r"\b[+-]?[0-9]+[lL]?\b",
                  r"\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b",
                  r"\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b"])
    sqstring = r"(\b[rRuU])?'[^'\\\n]*(\\.[^'\\\n]*)*'?"
    dqstring = r'(\b[rRuU])?"[^"\\\n]*(\\.[^"\\\n]*)*"?'
    string = any("string", [sqstring, dqstring])
    return "|".join([kw, string, number, fuzzy, links, comment,
                     any("SYNC", [r"\n"])])

class GetTextSH(GenericSH):
    """gettext Syntax Highlighter"""
    # Syntax highlighting rules:
    PROG = re.compile(make_gettext_patterns(), re.S)

#==============================================================================
# yaml highlighter
#==============================================================================
def make_yaml_patterns():
    "Strongly inspired from sublime highlighter "
    kw = any("keyword", [r":|>|-|\||\[|\]|[A-Za-z][\w\s\-\_ ]+(?=:)"])
    links = any("normal", [r"#:[^\n]*"])
    comment = any("comment", [r"#[^\n]*"])
    number = any("number",
                 [r"\b[+-]?[0-9]+[lL]?\b",
                  r"\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b",
                  r"\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b"])
    sqstring = r"(\b[rRuU])?'[^'\\\n]*(\\.[^'\\\n]*)*'?"
    dqstring = r'(\b[rRuU])?"[^"\\\n]*(\\.[^"\\\n]*)*"?'
    string = any("string", [sqstring, dqstring])
    return "|".join([kw, string, number, links, comment,
                     any("SYNC", [r"\n"])])

class YamlSH(GenericSH):
    """yaml Syntax Highlighter"""
    # Syntax highlighting rules:
    PROG = re.compile(make_yaml_patterns(), re.S)


#==============================================================================
# HTML highlighter
#==============================================================================
class BaseWebSH(BaseSH):
    """Base class for CSS and HTML syntax highlighters"""
    NORMAL  = 0
    COMMENT = 1

    def __init__(self, parent, font=None, color_scheme=None):
        BaseSH.__init__(self, parent, font, color_scheme)

    def highlight_block(self, text):
        """Implement highlight specific for CSS and HTML."""
        text = to_text_string(text)
        previous_state = tbh.get_state(self.currentBlock().previous())

        if previous_state == self.COMMENT:
            self.setFormat(0, qstring_length(text), self.formats["comment"])
        else:
            previous_state = self.NORMAL
            self.setFormat(0, qstring_length(text), self.formats["normal"])

        tbh.set_state(self.currentBlock(), previous_state)
        match = self.PROG.search(text)

        match_count = 0
        n_characters = qstring_length(text)
        # There should never be more matches than characters in the text.
        while match and match_count < n_characters:
            match_dict = match.groupdict()
            for key, value in list(match_dict.items()):
                if value:
                    start, end = get_span(match, key)
                    if previous_state == self.COMMENT:
                        if key == "multiline_comment_end":
                            tbh.set_state(self.currentBlock(), self.NORMAL)
                            self.setFormat(end, qstring_length(text),
                                           self.formats["normal"])
                        else:
                            tbh.set_state(self.currentBlock(), self.COMMENT)
                            self.setFormat(0, qstring_length(text),
                                           self.formats["comment"])
                    else:
                        if key == "multiline_comment_start":
                            tbh.set_state(self.currentBlock(), self.COMMENT)
                            self.setFormat(start, qstring_length(text),
                                           self.formats["comment"])
                        else:
                            tbh.set_state(self.currentBlock(), self.NORMAL)
                            try:
                                self.setFormat(start, end-start,
                                               self.formats[key])
                            except KeyError:
                                # Happens with unmatched end-of-comment.
                                # See spyder-ide/spyder#1462.
                                pass

            match = self.PROG.search(text, match.end())
            match_count += 1

        self.highlight_extras(text)

def make_html_patterns():
    """Strongly inspired from idlelib.ColorDelegator.make_pat """
    tags = any("builtin", [r"<", r"[\?/]?>", r"(?<=<).*?(?=[ >])"])
    keywords = any("keyword", [r" [\w:-]*?(?==)"])
    string = any("string", [r'".*?"'])
    comment = any("comment", [r"<!--.*?-->"])
    multiline_comment_start = any("multiline_comment_start", [r"<!--"])
    multiline_comment_end = any("multiline_comment_end", [r"-->"])
    return "|".join([comment, multiline_comment_start,
                     multiline_comment_end, tags, keywords, string])

class HtmlSH(BaseWebSH):
    """HTML Syntax Highlighter"""
    PROG = re.compile(make_html_patterns(), re.S)


# =============================================================================
# Markdown highlighter
# =============================================================================
def make_md_patterns():
    h1 = '^#[^#]+'
    h2 = '^##[^#]+'
    h3 = '^###[^#]+'
    h4 = '^####[^#]+'
    h5 = '^#####[^#]+'
    h6 = '^######[^#]+'

    titles = any('title', [h1, h2, h3, h4, h5, h6])

    html_tags = any("builtin", [r"<", r"[\?/]?>", r"(?<=<).*?(?=[ >])"])
    html_symbols = '&[^; ].+;'
    html_comment = '<!--.+-->'

    strikethrough = any('strikethrough', [r'(~~)(.*?)~~'])
    strong = any('strong', [r'(\*\*)(.*?)\*\*'])

    italic = r'(__)(.*?)__'
    emphasis = r'(//)(.*?)//'
    italic = any('italic', [italic, emphasis])

    # links - (links) after [] or links after []:
    link_html = (r'(?<=(\]\())[^\(\)]*(?=\))|'
                 '(<https?://[^>]+>)|'
                 '(<[^ >]+@[^ >]+>)')
    # link/image references - [] or ![]
    link = r'!?\[[^\[\]]*\]'
    links = any('link', [link_html, link])

    # blockquotes and lists -  > or - or * or 0.
    blockquotes = (r'(^>+.*)'
                   r'|(^(?:    |\t)*[0-9]+\. )'
                   r'|(^(?:    |\t)*- )'
                   r'|(^(?:    |\t)*\* )')
    # code
    code = any('code', ['^`{3,}.*$'])
    inline_code = any('inline_code', ['`[^`]*`'])

    # math - $$
    math = any('number', [r'^(?:\${2}).*$', html_symbols])

    comment = any('comment', [blockquotes, html_comment])

    return '|'.join([titles, comment, html_tags, math, links, italic, strong,
                     strikethrough, code, inline_code])


class MarkdownSH(BaseSH):
    """Markdown Syntax Highlighter"""
    # Syntax highlighting rules:
    PROG = re.compile(make_md_patterns(), re.S)
    NORMAL = 0
    CODE = 1

    def highlightBlock(self, text):
        text = to_text_string(text)
        previous_state = self.previousBlockState()

        if previous_state == self.CODE:
            self.setFormat(0, qstring_length(text), self.formats["code"])
        else:
            previous_state = self.NORMAL
            self.setFormat(0, qstring_length(text), self.formats["normal"])

        self.setCurrentBlockState(previous_state)

        match = self.PROG.search(text)
        match_count = 0
        n_characters = qstring_length(text)

        while match and match_count< n_characters:
            for key, value in list(match.groupdict().items()):
                start, end = get_span(match, key)

                if value:
                    previous_state = self.previousBlockState()

                    if previous_state == self.CODE:
                        if key == "code":
                            # Change to normal
                            self.setFormat(0, qstring_length(text),
                                           self.formats["normal"])
                            self.setCurrentBlockState(self.NORMAL)
                        else:
                            continue
                    else:
                        if key == "code":
                            # Change to code
                            self.setFormat(0, qstring_length(text),
                                           self.formats["code"])
                            self.setCurrentBlockState(self.CODE)
                            continue

                    self.setFormat(start, end - start, self.formats[key])

            match = self.PROG.search(text, match.end())
            match_count += 1

        self.highlight_extras(text)

    def setup_formats(self, font=None):
        super(MarkdownSH, self).setup_formats(font)

        font = QTextCharFormat(self.formats['normal'])
        font.setFontItalic(True)
        self.formats['italic'] = font

        self.formats['strong'] = self.formats['definition']

        font = QTextCharFormat(self.formats['normal'])
        font.setFontStrikeOut(True)
        self.formats['strikethrough'] = font

        font = QTextCharFormat(self.formats['string'])
        font.setUnderlineStyle(True)
        self.formats['link'] = font

        self.formats['code'] = self.formats['string']
        self.formats['inline_code'] = self.formats['string']

        font = QTextCharFormat(self.formats['keyword'])
        font.setFontWeight(QFont.Bold)
        self.formats['title'] = font


#==============================================================================
# Pygments based omni-parser
#==============================================================================
# IMPORTANT NOTE:
# --------------
# Do not be tempted to generalize the use of PygmentsSH (that is tempting
# because it would lead to more generic and compact code, and not only in
# this very module) because this generic syntax highlighter is far slower
# than the native ones (all classes above). For example, a Python syntax
# highlighter based on PygmentsSH would be 2 to 3 times slower than the
# current native PythonSH syntax highlighter.

class PygmentsSH(BaseSH):
    """Generic Pygments syntax highlighter."""
    # Store the language name and a ref to the lexer
    _lang_name = None
    _lexer = None

    # Syntax highlighting states (from one text block to another):
    NORMAL = 0
    def __init__(self, parent, font=None, color_scheme=None):
        # Map Pygments tokens to Spyder tokens
        self._tokmap = {Text: "normal",
                        Generic: "normal",
                        Other: "normal",
                        Keyword: "keyword",
                        Token.Operator: "normal",
                        Name.Builtin: "builtin",
                        Name: "normal",
                        Comment: "comment",
                        String: "string",
                        Number: "number"}
        # Load Pygments' Lexer
        if self._lang_name is not None:
            self._lexer = get_lexer_by_name(self._lang_name)

        BaseSH.__init__(self, parent, font, color_scheme)

        # This worker runs in a thread to avoid blocking when doing full file
        # parsing
        self._worker_manager = WorkerManager()

        # Store the format for all the tokens after Pygments parsing
        self._charlist = []

        # Flag variable to avoid unnecessary highlights if the worker has not
        # yet finished processing
        self._allow_highlight = True

    def make_charlist(self):
        """Parses the complete text and stores format for each character."""

        def worker_output(worker, output, error):
            """Worker finished callback."""
            self._charlist = output
            if error is None and output:
                self._allow_highlight = True
                self.rehighlight()
            self._allow_highlight = False

        text = to_text_string(self.document().toPlainText())
        tokens = self._lexer.get_tokens(text)

        # Before starting a new worker process make sure to end previous
        # incarnations
        self._worker_manager.terminate_all()

        worker = self._worker_manager.create_python_worker(
            self._make_charlist,
            tokens,
            self._tokmap,
            self.formats,
        )
        worker.sig_finished.connect(worker_output)
        worker.start()

    def _make_charlist(self, tokens, tokmap, formats):
        """
        Parses the complete text and stores format for each character.

        Uses the attached lexer to parse into a list of tokens and Pygments
        token types.  Then breaks tokens into individual letters, each with a
        Spyder token type attached.  Stores this list as self._charlist.

        It's attached to the contentsChange signal of the parent QTextDocument
        so that the charlist is updated whenever the document changes.
        """

        def _get_fmt(typ):
            """Get the Spyder format code for the given Pygments token type."""
            # Exact matches first
            if typ in tokmap:
                return tokmap[typ]
            # Partial (parent-> child) matches
            for key, val in tokmap.items():
                if typ in key: # Checks if typ is a subtype of key.
                    return val

            return 'normal'

        charlist = []
        for typ, token in tokens:
            fmt = formats[_get_fmt(typ)]
            for letter in token:
                charlist.append((fmt, letter))

        return charlist

    def highlightBlock(self, text):
        """ Actually highlight the block"""
        # Note that an undefined blockstate is equal to -1, so the first block
        # will have the correct behaviour of starting at 0.
        if self._allow_highlight:
            start = self.previousBlockState() + 1
            end = start + qstring_length(text)
            for i, (fmt, letter) in enumerate(self._charlist[start:end]):
                self.setFormat(i, 1, fmt)
            self.setCurrentBlockState(end)
            self.highlight_extras(text)


class PythonLoggingLexer(RegexLexer):
    """
    A lexer for logs generated by the Python builtin 'logging' library.

    Taken from
    https://bitbucket.org/birkenfeld/pygments-main/pull-requests/451/add-python-logging-lexer
    """

    name = 'Python Logging'
    aliases = ['pylog', 'pythonlogging']
    filenames = ['*.log']
    tokens = {
        'root': [
            (r'^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\,?\d*)(\s\w+)',
             bygroups(Comment.Preproc, Number.Integer), 'message'),
            (r'"(.*?)"|\'(.*?)\'', String),
            (r'(\d)', Number.Integer),
            (r'(\s.+/n)', Text)
        ],

        'message': [
            (r'(\s-)(\sDEBUG)(\s-)(\s*[\d\w]+([.]?[\d\w]+)+\s*)',
             bygroups(Text, Number, Text, Name.Builtin), '#pop'),
            (r'(\s-)(\sINFO\w*)(\s-)(\s*[\d\w]+([.]?[\d\w]+)+\s*)',
             bygroups(Generic.Heading, Text, Text, Name.Builtin), '#pop'),
            (r'(\sWARN\w*)(\s.+)', bygroups(String, String), '#pop'),
            (r'(\sERROR)(\s.+)',
             bygroups(Generic.Error, Name.Constant), '#pop'),
            (r'(\sCRITICAL)(\s.+)',
             bygroups(Generic.Error, Name.Constant), '#pop'),
            (r'(\sTRACE)(\s.+)',
             bygroups(Generic.Error, Name.Constant), '#pop'),
            (r'(\s\w+)(\s.+)',
             bygroups(Comment, Generic.Output), '#pop'),
        ],

    }


def guess_pygments_highlighter(filename):
    """
    Factory to generate syntax highlighter for the given filename.

    If a syntax highlighter is not available for a particular file, this
    function will attempt to generate one based on the lexers in Pygments. If
    Pygments is not available or does not have an appropriate lexer, TextSH
    will be returned instead.
    """
    try:
        from pygments.lexers import get_lexer_for_filename, get_lexer_by_name
    except Exception:
        return TextSH

    root, ext = os.path.splitext(filename)
    if ext == '.txt':
        # Pygments assigns a lexer that doesn’t highlight anything to
        # txt files. So we avoid that here.
        return TextSH
    elif ext in custom_extension_lexer_mapping:
        try:
            lexer = get_lexer_by_name(custom_extension_lexer_mapping[ext])
        except Exception:
            return TextSH
    elif ext == '.log':
        lexer = PythonLoggingLexer()
    else:
        try:
            lexer = get_lexer_for_filename(filename)
        except Exception:
            return TextSH

    class GuessedPygmentsSH(PygmentsSH):
        _lexer = lexer

    return GuessedPygmentsSH
