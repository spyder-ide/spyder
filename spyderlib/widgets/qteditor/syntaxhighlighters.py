# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Editor widget syntax highlighters based on PyQt4.QtGui.QSyntaxHighlighter
Syntax highlighting rules are inspired from idlelib
"""

import sys, re, keyword, __builtin__

from PyQt4.QtGui import (QColor, QApplication, QFont, QSyntaxHighlighter,
                         QCursor, QTextCharFormat)
from PyQt4.QtCore import Qt, SIGNAL

# For debugging purpose:
STDOUT = sys.stdout


#===============================================================================
# Python syntax highlighter
#===============================================================================
def any(name, alternates):
    "Return a named group pattern matching list of alternates."
    return "(?P<%s>" % name + "|".join(alternates) + ")"

def make_python_patterns():
    "Strongly inspired from idlelib.ColorDelegator.make_pat"
    kw = r"\b" + any("KEYWORD", keyword.kwlist) + r"\b"
    builtinlist = [str(name) for name in dir(__builtin__)
                                        if not name.startswith('_')]
    builtin = r"([^.'\"\\#]\b|^)" + any("BUILTIN", builtinlist) + r"\b"
    comment = any("COMMENT", [r"#[^\n]*"])
    instance = any("INSTANCE", [r"\bself\b"])
    number = any("NUMBER",
                 [r"\b[+-]?[0-9]+[lL]?\b",
                  r"\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b",
                  r"\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b"])
    ml_sq3string = r"(\b[rRuU])?'''[^'\\]*((\\.|'(?!''))[^'\\]*)*"
    ml_dq3string = r'(\b[rRuU])?"""[^"\\]*((\\.|"(?!""))[^"\\]*)*'
    multiline_string = any("ML_STRING", [ml_sq3string, ml_dq3string])
    sqstring = r"(\b[rRuU])?'[^'\\\n]*(\\.[^'\\\n]*)*'?"
    dqstring = r'(\b[rRuU])?"[^"\\\n]*(\\.[^"\\\n]*)*"?'
    sq3string = r"(\b[rRuU])?'''[^'\\]*((\\.|'(?!''))[^'\\]*)*(''')?"
    dq3string = r'(\b[rRuU])?"""[^"\\]*((\\.|"(?!""))[^"\\]*)*(""")?'
    string = any("STRING", [sq3string, dq3string, sqstring, dqstring])
    return instance + "|" + kw + "|" + builtin + "|" + comment + "|" + \
           multiline_string + "|" + string + "|" + number + "|" + \
           any("SYNC", [r"\n"])

#TODO: Use setCurrentBlockUserData for brace matching (see Qt documentation)
class ClassBrowserData(object):
    CLASS = 0
    FUNCTION = 1
    def __init__(self):
        self.text = None
        self.fold_level = None
        self.def_type = None
        self.def_name = None
        
    def get_class_name(self):
        if self.def_type == self.CLASS:
            return self.def_name
        
    def get_function_name(self):
        if self.def_type == self.FUNCTION:
            return self.def_name
    
class BaseSH(QSyntaxHighlighter):
    """Base Syntax Highlighter Class"""
    # Syntax highlighting rules:
    PROG = None
    # Syntax highlighting states (from one text block to another):
    NORMAL = 0
    # Syntax highlighting color schemes:
    COLORS = {
              'IDLE':
              (#  Name          Color    Bold   Italic
               ("NORMAL",     "#000000", False, False),
               ("KEYWORD",    "#ff7700", True,  False),
               ("BUILTIN",    "#900090", False, False),
               ("DEFINITION", "#0000ff", False, False),
               ("COMMENT",    "#dd0000", False, True),
               ("STRING",     "#00aa00", False, False),
               ("NUMBER",     "#924900", False, False),
               ("INSTANCE",   "#777777", True,  True),
               ),
              'Pydev':
              (#  Name          Color    Bold   Italic
               ("NORMAL",     "#000000", False, False),
               ("KEYWORD",    "#0000FF", False, False),
               ("BUILTIN",    "#900090", False, False),
               ("DEFINITION", "#000000", True,  False),
               ("COMMENT",    "#C0C0C0", False, False),
               ("STRING",     "#00AA00", False, True),
               ("NUMBER",     "#800000", False, False),
               ("INSTANCE",   "#000000", False, True),
               ),
              'Scintilla':
              (#  Name          Color    Bold   Italic
               ("NORMAL",     "#000000", False, False),
               ("KEYWORD",    "#00007F", True,  False),
               ("BUILTIN",    "#000000", False, False),
               ("DEFINITION", "#007F7F", True,  False),
               ("COMMENT",    "#007F00", False, False),
               ("STRING",     "#7F007F", False, False),
               ("NUMBER",     "#007F7F", False, False),
               ("INSTANCE",   "#000000", False, True),
               ),
              }
    def __init__(self, parent, font=None, color_scheme=None):
        super(BaseSH, self).__init__(parent)
        
        self.classbrowser_data = {}
        
        if color_scheme is None:
            color_scheme = 'Pydev'
        self.color_scheme = color_scheme

        self.formats = None
        self.setup_formats(font)

    def setup_formats(self, font=None):
        base_format = QTextCharFormat()
        if font is not None:
            base_format.setFont(font)
        self.formats = {}
        for name, color, bold, italic in self.COLORS[self.color_scheme]:
            format = QTextCharFormat(base_format)
            format.setForeground(QColor(color))
            if bold:
                format.setFontWeight(QFont.Bold)
            format.setFontItalic(italic)
            self.formats[name] = format

    def highlightBlock(self, text):
        raise NotImplementedError
            
    def get_classbrowser_data_iterator(self):
        """
        Return class browser data iterator
        The iterator yields block number and associated data
        """
        block_dict = {}
        for block, data in self.classbrowser_data.iteritems():
            block_dict[block.blockNumber()] = data
        def iterator():
            for block_nb in sorted(block_dict.keys()):
                yield block_nb, block_dict[block_nb]
        return iterator

    def rehighlight(self):
        self.classbrowser_data = {}
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        QSyntaxHighlighter.rehighlight(self)
        QApplication.restoreOverrideCursor()


class PythonSH(BaseSH):
    """Python Syntax Highlighter"""
    # Syntax highlighting rules:
    PROG = re.compile(make_python_patterns(), re.S)
    IDPROG = re.compile(r"\s+(\w+)", re.S)
    ASPROG = re.compile(r".*?\b(as)\b")
    # Syntax highlighting states (from one text block to another):
    NORMAL = 0
    INSIDE_STRING = 1
    DEF_TYPES = {"def": ClassBrowserData.FUNCTION, "class": ClassBrowserData.CLASS}
    def __init__(self, parent, font=None, color_scheme=None):
        super(PythonSH, self).__init__(parent)
        self.import_statements = {}

    def highlightBlock(self, text):
        inside_string = self.previousBlockState() == self.INSIDE_STRING
        self.setFormat(0, text.length(),
                       self.formats["STRING" if inside_string else "NORMAL"])
        
        cbdata = None
        import_stmt = None
        
        text = unicode(text)
        match = self.PROG.search(text)
        index = 0
        while match:
            for key, value in match.groupdict().items():
                if value:
                    start, end = match.span(key)
                    index += end-start
                    if key == "ML_STRING":
                        self.setFormat(start, end-start, self.formats["STRING"])
                        inside_string = not inside_string
                    elif inside_string:
                        self.setFormat(start, end-start, self.formats["STRING"])
                    else:
                        self.setFormat(start, end-start, self.formats[key])
                        if value in ("def", "class"):
                            match1 = self.IDPROG.match(text, end)
                            if match1:
                                start1, end1 = match1.span(1)
                                self.setFormat(start1, end1-start1,
                                               self.formats["DEFINITION"])
                                cbdata = ClassBrowserData()
                                cbdata.text = unicode(text)
                                cbdata.fold_level = start
                                cbdata.def_type = self.DEF_TYPES[unicode(value)]
                                cbdata.def_name = text[start1:end1]
                        elif value == "import":
                            import_stmt = text.strip()
                            # color all the "as" words on same line, except
                            # if in a comment; cheap approximation to the
                            # truth
                            if '#' in text:
                                endpos = text.index('#')
                            else:
                                endpos = len(text)
                            while True:
                                match1 = self.ASPROG.match(text, end, endpos)
                                if not match1:
                                    break
                                start, end = match1.span(1)
                                self.setFormat(start, end-start,
                                               self.formats["KEYWORD"])
                    
            match = self.PROG.search(text, match.end())

        last_state = self.INSIDE_STRING if inside_string else self.NORMAL
        self.setCurrentBlockState(last_state)
        
        if cbdata is not None:
            self.classbrowser_data[self.currentBlock()] = cbdata
        if import_stmt is not None:
            self.import_statements[self.currentBlock()] = import_stmt
            
    def get_import_statements(self):
        return self.import_statements.values()
            
    def rehighlight(self):
        self.import_statements = {}
        super(PythonSH, self).rehighlight()


#===============================================================================
# Cython syntax highlighter
#===============================================================================

class CythonSH(PythonSH):
    """Cython Syntax Highlighter"""
    pass


#===============================================================================
# C/C++ syntax highlighter
#===============================================================================

def make_cpp_patterns():
    "Strongly inspired from idlelib.ColorDelegator.make_pat"
    comment = any("COMMENT", [r"//[^\n]*"])
    comment_start = any("COMMENT_START", [r"\/\*"])
    comment_end = any("COMMENT_END", [r"\*\/"])
    instance = any("INSTANCE", [r"\bthis\b"])
    number = any("NUMBER",
                 [r"\b[+-]?[0-9]+[lL]?\b",
                  r"\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b",
                  r"\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b"])
    sqstring = r"(\b[rRuU])?'[^'\\\n]*(\\.[^'\\\n]*)*'?"
    dqstring = r'(\b[rRuU])?"[^"\\\n]*(\\.[^"\\\n]*)*"?'
    string = any("STRING", [sqstring, dqstring])
    return instance + "|" + comment + "|" + string + "|" + number + "|" + \
           comment_start + "|" + comment_end + "|" + any("SYNC", [r"\n"])

class CppSH(BaseSH):
    """C/C++ Syntax Highlighter"""
    # Syntax highlighting rules:
    PROG = re.compile(make_cpp_patterns(), re.S)
    # Syntax highlighting states (from one text block to another):
    NORMAL = 0
    INSIDE_COMMENT = 1
    def __init__(self, parent, font=None, color_scheme=None):
        super(CppSH, self).__init__(parent)

    def highlightBlock(self, text):
        inside_comment = self.previousBlockState() == self.INSIDE_COMMENT
        self.setFormat(0, text.length(),
                       self.formats["COMMENT" if inside_comment else "NORMAL"])
        
        match = self.PROG.search(text)
        index = 0
        while match:
            for key, value in match.groupdict().items():
                if value:
                    start, end = match.span(key)
                    index += end-start
                    if key == "COMMENT_START":
                        inside_comment = True
                        self.setFormat(start, text.length()-start,
                                       self.formats["COMMENT"])
                    elif key == "COMMENT_END":
                        inside_comment = False
                        self.setFormat(start, end-start,
                                       self.formats["COMMENT"])
                    elif inside_comment:
                        self.setFormat(start, end-start,
                                       self.formats["COMMENT"])
                    else:
                        self.setFormat(start, end-start, self.formats[key])
                    
            match = self.PROG.search(text, match.end())

        last_state = self.INSIDE_COMMENT if inside_comment else self.NORMAL
        self.setCurrentBlockState(last_state)

