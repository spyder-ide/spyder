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
from PyQt4.QtCore import Qt

# For debugging purpose:
STDOUT = sys.stdout


#===============================================================================
# Syntax highlighting color schemes
#===============================================================================
COLOR_SCHEME_KEYS = ("background", "currentline", "occurence",
                     "ctrlclick", "sideareas",
                     "normal", "keyword", "builtin", "definition",
                     "comment", "string", "number", "instance")
COLORS = {
          'IDLE':
          {#  Name          Color    Bold   Italic
           "background":  "#ffffff",
           "currentline": "#eeffdd",
           "occurence":   "#e8f2fe",
           "ctrlclick":   "#0000ff",
           "sideareas":   "#efefef",
           "normal":     ("#000000", False, False),
           "keyword":    ("#ff7700", True,  False),
           "builtin":    ("#900090", False, False),
           "definition": ("#0000ff", False, False),
           "comment":    ("#dd0000", False, True),
           "string":     ("#00aa00", False, False),
           "number":     ("#924900", False, False),
           "instance":   ("#777777", True,  True),
           },
          'Pydev':
          {#  Name          Color    Bold   Italic
           "background":  "#ffffff",
           "currentline": "#e8f2fe",
           "occurence":   "#ffff99",
           "ctrlclick":   "#0000ff",
           "sideareas":   "#efefef",
           "normal":     ("#000000", False, False),
           "keyword":    ("#0000ff", False, False),
           "builtin":    ("#900090", False, False),
           "definition": ("#000000", True,  False),
           "comment":    ("#c0c0c0", False, False),
           "string":     ("#00aa00", False, True),
           "number":     ("#800000", False, False),
           "instance":   ("#000000", False, True),
           },
          'Emacs':
          {#  Name          Color    Bold   Italic
           "background":  "#000000",
           "currentline": "#2b2b43",
           "occurence":   "#abab67",
           "ctrlclick":   "#0000ff",
           "sideareas":   "#555555",
           "normal":     ("#ffffff", False, False),
           "keyword":    ("#3c51e8", False, False),
           "builtin":    ("#900090", False, False),
           "definition": ("#ff8040", True,  False),
           "comment":    ("#005100", False, False),
           "string":     ("#00aa00", False, True),
           "number":     ("#800000", False, False),
           "instance":   ("#ffffff", False, True),
           },
          'Scintilla':
          {#  Name          Color    Bold   Italic
           "background":  "#ffffff",
           "currentline": "#eeffdd",
           "occurence":   "#ffff99",
           "ctrlclick":   "#0000ff",
           "sideareas":   "#efefef",
           "normal":     ("#000000", False, False),
           "keyword":    ("#00007f", True,  False),
           "builtin":    ("#000000", False, False),
           "definition": ("#007f7f", True,  False),
           "comment":    ("#007f00", False, False),
           "string":     ("#7f007f", False, False),
           "number":     ("#007f7f", False, False),
           "instance":   ("#000000", False, True),
           },
          'Spyder':
          {#  Name          Color    Bold   Italic
           "background":  "#ffffff",
           "currentline": "#feefff",
           "occurence":   "#ffff99",
           "ctrlclick":   "#0000ff",
           "sideareas":   "#efefef",
           "normal":     ("#000000", False, False),
           "keyword":    ("#0000ff", False, False),
           "builtin":    ("#900090", False, False),
           "definition": ("#000000", True,  False),
           "comment":    ("#adadad", False, False),
           "string":     ("#00aa00", False, True),
           "number":     ("#800000", False, False),
           "instance":   ("#000000", False, True),
           },
          }
COLOR_SCHEME_NAMES = COLORS.keys()

class BaseSH(QSyntaxHighlighter):
    """Base Syntax Highlighter Class"""
    # Syntax highlighting rules:
    PROG = None
    # Syntax highlighting states (from one text block to another):
    NORMAL = 0
    def __init__(self, parent, font=None, color_scheme=None):
        super(BaseSH, self).__init__(parent)
        
        self.outlineexplorer_data = {}
        
        self.font = font
        self._check_color_scheme(color_scheme)
        if isinstance(color_scheme, basestring):
            self.color_scheme = COLORS[color_scheme]
        else:
            self.color_scheme = color_scheme
        
        self.background_color = None
        self.currentline_color = None
        self.occurence_color = None
        self.ctrlclick_color = None
        self.sideareas_color = None

        self.formats = None
        self.setup_formats(font)
        
    def get_background_color(self):
        return QColor(self.background_color)
        
    def get_currentline_color(self):
        return QColor(self.currentline_color)
        
    def get_occurence_color(self):
        return QColor(self.occurence_color)
    
    def get_ctrlclick_color(self):
        return QColor(self.ctrlclick_color)
    
    def get_sideareas_color(self):
        return QColor(self.sideareas_color)

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
        self.occurence_color = colors.pop("occurence")
        self.ctrlclick_color = colors.pop("ctrlclick")
        self.sideareas_color = colors.pop("sideareas")
        for name, (color, bold, italic) in colors.iteritems():
            format = QTextCharFormat(base_format)
            format.setForeground(QColor(color))
            format.setBackground(QColor(self.background_color))
            if bold:
                format.setFontWeight(QFont.Bold)
            format.setFontItalic(italic)
            self.formats[name] = format

    def _check_color_scheme(self, color_scheme):
        if isinstance(color_scheme, basestring):
            assert color_scheme in COLOR_SCHEME_NAMES
        else:
            assert all([key in color_scheme for key in COLOR_SCHEME_KEYS])

    def set_color_scheme(self, color_scheme):
        self._check_color_scheme(color_scheme)
        if isinstance(color_scheme, basestring):
            self.color_scheme = COLORS[color_scheme]
        else:
            self.color_scheme = color_scheme
        self.setup_formats()
        self.rehighlight()

    def highlightBlock(self, text):
        raise NotImplementedError
            
    def get_outlineexplorer_data(self):
        return self.outlineexplorer_data

    def rehighlight(self):
        self.outlineexplorer_data = {}
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        QSyntaxHighlighter.rehighlight(self)
        QApplication.restoreOverrideCursor()


#===============================================================================
# Python syntax highlighter
#===============================================================================
def any(name, alternates):
    "Return a named group pattern matching list of alternates."
    return "(?P<%s>" % name + "|".join(alternates) + ")"

def make_python_patterns(additional_keywords=[], additional_builtins=[]):
    "Strongly inspired from idlelib.ColorDelegator.make_pat"
    kw = r"\b" + any("keyword", keyword.kwlist+additional_keywords) + r"\b"
    builtinlist = [str(name) for name in dir(__builtin__)
                   if not name.startswith('_')]+additional_builtins
    builtin = r"([^.'\"\\#]\b|^)" + any("builtin", builtinlist) + r"\b"
    comment = any("comment", [r"#[^\n]*"])
    instance = any("instance", [r"\bself\b"])
    number = any("number",
                 [r"\b[+-]?[0-9]+[lL]?\b",
                  r"\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b",
                  r"\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b"])
    sqstring =     r"(\b[rRuU])?'[^'\\\n]*(\\.[^'\\\n]*)*'?"
    dqstring =     r'(\b[rRuU])?"[^"\\\n]*(\\.[^"\\\n]*)*"?'
    uf_sqstring =  r"(\b[rRuU])?'[^'\\\n]*(\\.[^'\\\n]*)*(\\)$(?!')$"
    uf_dqstring =  r'(\b[rRuU])?"[^"\\\n]*(\\.[^"\\\n]*)*(\\)$(?!")$'
    sq3string =    r"(\b[rRuU])?'''[^'\\]*((\\.|'(?!''))[^'\\]*)*(''')?"
    dq3string =    r'(\b[rRuU])?"""[^"\\]*((\\.|"(?!""))[^"\\]*)*(""")?'
    uf_sq3string = r"(\b[rRuU])?'''[^'\\]*((\\.|'(?!''))[^'\\]*)*(\\)?(?!''')$"
    uf_dq3string = r'(\b[rRuU])?"""[^"\\]*((\\.|"(?!""))[^"\\]*)*(\\)?(?!""")$'
    string = any("string", [sqstring, dqstring, sq3string, dq3string])
    ufstring1 = any("uf_sqstring", [uf_sqstring])
    ufstring2 = any("uf_dqstring", [uf_dqstring])
    ufstring3 = any("uf_sq3string", [uf_sq3string])
    ufstring4 = any("uf_dq3string", [uf_dq3string])
    return instance + "|" + kw + "|" + builtin + "|" + comment + "|" + \
           ufstring1 + "|" + ufstring2 + "|" + ufstring3 + "|" + ufstring4 + \
           "|" + string + "|" + number + "|" + any("SYNC", [r"\n"])

class OutlineExplorerData(object):
    CLASS = 0
    FUNCTION = 1
    def __init__(self):
        self.text = None
        self.fold_level = None
        self.def_type = None
        self.def_name = None
        
    def is_not_class_nor_function(self):
        return self.def_type not in (self.CLASS, self.FUNCTION)
        
    def get_class_name(self):
        if self.def_type == self.CLASS:
            return self.def_name
        
    def get_function_name(self):
        if self.def_type == self.FUNCTION:
            return self.def_name
    
class PythonSH(BaseSH):
    """Python Syntax Highlighter"""
    # Syntax highlighting rules:
    PROG = re.compile(make_python_patterns(), re.S)
    IDPROG = re.compile(r"\s+(\w+)", re.S)
    ASPROG = re.compile(r".*?\b(as)\b")
    # Syntax highlighting states (from one text block to another):
    (NORMAL, INSIDE_SQ3STRING, INSIDE_DQ3STRING,
     INSIDE_SQSTRING, INSIDE_DQSTRING) = range(5)
    DEF_TYPES = {"def": OutlineExplorerData.FUNCTION,
                 "class": OutlineExplorerData.CLASS}
    def __init__(self, parent, font=None, color_scheme=None):
        super(PythonSH, self).__init__(parent, font, color_scheme)
        self.import_statements = {}

    def highlightBlock(self, text):
        text = unicode(text)
        prev_state = self.previousBlockState()
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

        self.setFormat(0, len(text), self.formats["normal"])
        
        state = self.NORMAL
        match = self.PROG.search(text)
        while match:
            for key, value in match.groupdict().items():
                if value:
                    start, end = match.span(key)
                    start = max([0, start+offset])
                    end = max([0, end+offset])
                    if key == "uf_sq3string":
                        self.setFormat(start, end-start, self.formats["string"])
                        state = self.INSIDE_SQ3STRING
                    elif key == "uf_dq3string":
                        self.setFormat(start, end-start, self.formats["string"])
                        state = self.INSIDE_DQ3STRING
                    elif key == "uf_sqstring":
                        self.setFormat(start, end-start, self.formats["string"])
                        state = self.INSIDE_SQSTRING
                    elif key == "uf_dqstring":
                        self.setFormat(start, end-start, self.formats["string"])
                        state = self.INSIDE_DQSTRING
                    else:
                        self.setFormat(start, end-start, self.formats[key])
                        if key == "keyword":
                            if value in ("def", "class"):
                                match1 = self.IDPROG.match(text, end)
                                if match1:
                                    start1, end1 = match1.span(1)
                                    self.setFormat(start1, end1-start1,
                                                   self.formats["definition"])
                                    oedata = OutlineExplorerData()
                                    oedata.text = unicode(text)
                                    oedata.fold_level = start
                                    oedata.def_type = self.DEF_TYPES[
                                                                unicode(value)]
                                    oedata.def_name = text[start1:end1]
                            elif value in ("elif", "else", "except", "finally",
                                           "for", "if", "try", "while", "with"):
                                if text.lstrip().startswith(value):
                                    oedata = OutlineExplorerData()
                                    oedata.text = unicode(text).strip()
                                    oedata.fold_level = start
                                    oedata.def_type = None
                                    oedata.def_name = text.strip()
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
                                    match1 = self.ASPROG.match(text, end,
                                                               endpos)
                                    if not match1:
                                        break
                                    start, end = match1.span(1)
                                    self.setFormat(start, end-start,
                                                   self.formats["keyword"])
                    
            match = self.PROG.search(text, match.end())

        self.setCurrentBlockState(state)
        
        if oedata is not None:
            block_nb = self.currentBlock().blockNumber()
            self.outlineexplorer_data[block_nb] = oedata
        if import_stmt is not None:
            block_nb = self.currentBlock().blockNumber()
            self.import_statements[block_nb] = import_stmt
            
    def get_import_statements(self):
        return self.import_statements.values()
            
    def rehighlight(self):
        self.import_statements = {}
        super(PythonSH, self).rehighlight()


#===============================================================================
# Cython syntax highlighter
#===============================================================================
C_TYPES = 'bool char double enum float int long mutable short signed struct unsigned void'

class CythonSH(PythonSH):
    """Cython Syntax Highlighter"""
    ADDITIONAL_KEYWORDS = ["cdef", "ctypedef"]
    ADDITIONAL_BUILTINS = C_TYPES.split()
    PROG = re.compile(make_python_patterns(ADDITIONAL_KEYWORDS,
                                           ADDITIONAL_BUILTINS), re.S)
    IDPROG = re.compile(r"\s+([\w\.]+)", re.S)


#===============================================================================
# C/C++ syntax highlighter
#===============================================================================
def make_cpp_patterns():
    "Strongly inspired from idlelib.ColorDelegator.make_pat"
    kwstr1 = 'and and_eq bitand bitor break case catch const const_cast continue default delete do dynamic_cast else explicit export extern for friend goto if inline namespace new not not_eq operator or or_eq private protected public register reinterpret_cast return sizeof static static_cast switch template throw try typedef typeid typename union using virtual while xor xor_eq'
    kwstr1b = 'a addindex addtogroup anchor arg attention author b brief bug c class code date def defgroup deprecated dontinclude e em endcode endhtmlonly ifdef endif endlatexonly endlink endverbatim enum example exception f$ f[ f] file fn hideinitializer htmlinclude htmlonly if image include ingroup internal invariant interface latexonly li line link mainpage name namespace nosubgrouping note overload p page par param post pre ref relates remarks return retval sa section see showinitializer since skip skipline subsection test throw todo typedef union until var verbatim verbinclude version warning weakgroup'
    kwstr2 = 'asm auto class compl false true volatile wchar_t'
    kw = r"\b" + any("builtin", kwstr1.split()+kwstr1b.split()) + r"\b"
    builtin = r"\b" + any("keyword", kwstr2.split()+C_TYPES.split()) + r"\b"
    comment = any("comment", [r"//[^\n]*"])
    comment_start = any("comment_start", [r"\/\*"])
    comment_end = any("comment_end", [r"\*\/"])
    instance = any("instance", [r"\bthis\b"])
    number = any("number",
                 [r"\b[+-]?[0-9]+[lL]?\b",
                  r"\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b",
                  r"\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b"])
    sqstring = r"(\b[rRuU])?'[^'\\\n]*(\\.[^'\\\n]*)*'?"
    dqstring = r'(\b[rRuU])?"[^"\\\n]*(\\.[^"\\\n]*)*"?'
    string = any("string", [sqstring, dqstring])
    define = any("define", [r"#[^\n]*"])
    return instance + "|" + kw + "|" + comment + "|" + string + "|" + \
           number + "|" + comment_start + "|" + comment_end + "|" + \
           builtin + "|" + define + "|" + any("SYNC", [r"\n"])

class CppSH(BaseSH):
    """C/C++ Syntax Highlighter"""
    # Syntax highlighting rules:
    PROG = re.compile(make_cpp_patterns(), re.S)
    # Syntax highlighting states (from one text block to another):
    NORMAL = 0
    INSIDE_COMMENT = 1
    def __init__(self, parent, font=None, color_scheme=None):
        super(CppSH, self).__init__(parent, font, color_scheme)

    def highlightBlock(self, text):
        inside_comment = self.previousBlockState() == self.INSIDE_COMMENT
        self.setFormat(0, text.length(),
                       self.formats["comment" if inside_comment else "normal"])
        
        match = self.PROG.search(text)
        index = 0
        while match:
            for key, value in match.groupdict().items():
                if value:
                    start, end = match.span(key)
                    index += end-start
                    if key == "comment_start":
                        inside_comment = True
                        self.setFormat(start, text.length()-start,
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

        last_state = self.INSIDE_COMMENT if inside_comment else self.NORMAL
        self.setCurrentBlockState(last_state)


#===============================================================================
# Fortran Syntax Highlighter
#===============================================================================

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
    return kw + "|" + comment + "|" + string + "|" + \
           number + "|" + builtin + "|" + any("SYNC", [r"\n"])

class FortranSH(BaseSH):
    """Fortran Syntax Highlighter"""
    # Syntax highlighting rules:
    PROG = re.compile(make_fortran_patterns(), re.S)
    IDPROG = re.compile(r"\s+(\w+)", re.S)
    # Syntax highlighting states (from one text block to another):
    NORMAL = 0
    def __init__(self, parent, font=None, color_scheme=None):
        super(FortranSH, self).__init__(parent, font, color_scheme)

    def highlightBlock(self, text):
        self.setFormat(0, text.length(), self.formats["normal"])
        
        match = self.PROG.search(text)
        index = 0
        while match:
            for key, value in match.groupdict().items():
                if value:
                    start, end = match.span(key)
                    index += end-start
                    self.setFormat(start, end-start, self.formats[key])
                    if value in ("subroutine", "module", "function"):
                        match1 = self.IDPROG.match(text, end)
                        if match1:
                            start1, end1 = match1.span(1)
                            self.setFormat(start1, end1-start1,
                                           self.formats["definition"])
                    
            match = self.PROG.search(text, match.end())

class Fortran77SH(FortranSH):
    """Fortran 77 Syntax Highlighter"""
    def highlightBlock(self, text):
        if text.startsWith("c"):
            self.setFormat(0, text.length(), self.formats["comment"])
        else:
            FortranSH.highlightBlock(self, text)
            self.setFormat(0, 5, self.formats["comment"])
            self.setFormat(73, max([73, text.length()]),
                           self.formats["comment"])
