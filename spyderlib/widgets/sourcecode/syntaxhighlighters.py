# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Editor widget syntax highlighters based on QtGui.QSyntaxHighlighter
(Python syntax highlighting rules are inspired from idlelib)
"""

import sys, re, keyword, __builtin__

from spyderlib.qt.QtGui import (QColor, QApplication, QFont,
                                QSyntaxHighlighter, QCursor, QTextCharFormat)
from spyderlib.qt.QtCore import Qt

# For debugging purpose:
STDOUT = sys.stdout


#==============================================================================
# Syntax highlighting color schemes
#==============================================================================
COLOR_SCHEME_KEYS = ("background", "currentline", "occurence",
                     "ctrlclick", "sideareas", "matched_p", "unmatched_p",
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
           "matched_p":   "#99ff99",
           "unmatched_p": "#ff9999",
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
           "matched_p":   "#99ff99",
           "unmatched_p": "#ff9999",
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
           "matched_p":   "#009800",
           "unmatched_p": "#c80000",
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
           "matched_p":   "#99ff99",
           "unmatched_p": "#ff9999",
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
           "matched_p":   "#99ff99",
           "unmatched_p": "#ff9999",
           "normal":     ("#000000", False, False),
           "keyword":    ("#0000ff", False, False),
           "builtin":    ("#900090", False, False),
           "definition": ("#000000", True,  False),
           "comment":    ("#adadad", False, True),
           "string":     ("#00aa00", False, False),
           "number":     ("#800000", False, False),
           "instance":   ("#924900", False, True),
           },
          }
COLOR_SCHEME_NAMES = COLORS.keys()

class BaseSH(QSyntaxHighlighter):
    """Base Syntax Highlighter Class"""
    # Syntax highlighting rules:
    PROG = None
    # Syntax highlighting states (from one text block to another):
    NORMAL = 0
    def __init__(self, parent, font=None, color_scheme='Spyder'):
        QSyntaxHighlighter.__init__(self, parent)
        
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
        self.matched_p_color = None
        self.unmatched_p_color = None

        self.formats = None
        self.setup_formats(font)
        
    def get_background_color(self):
        return QColor(self.background_color)
        
    def get_foreground_color(self):
        """Return foreground ('normal' text) color"""
        return self.formats["normal"].foreground().color()
        
    def get_currentline_color(self):
        return QColor(self.currentline_color)
        
    def get_occurence_color(self):
        return QColor(self.occurence_color)
    
    def get_ctrlclick_color(self):
        return QColor(self.ctrlclick_color)
    
    def get_sideareas_color(self):
        return QColor(self.sideareas_color)
    
    def get_matched_p_color(self):
        return QColor(self.matched_p_color)
    
    def get_unmatched_p_color(self):
        return QColor(self.unmatched_p_color)

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
        self.matched_p_color = colors.pop("matched_p")
        self.unmatched_p_color = colors.pop("unmatched_p")
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


class TextSH(BaseSH):
    """Simple Text Syntax Highlighter Class (do nothing)"""
    def highlightBlock(self, text):
        pass


#==============================================================================
# Python syntax highlighter
#==============================================================================
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
                 [r"\b[+-]?[0-9]+[lLjJ]?\b",
                  r"\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b",
                  r"\b[+-]?0[oO][0-7]+[lL]?\b",
                  r"\b[+-]?0[bB][01]+[lL]?\b",
                  r"\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?[jJ]?\b"])
    sqstring =     r"(\b[rRuU])?'[^'\\\n]*(\\.[^'\\\n]*)*'?"
    dqstring =     r'(\b[rRuU])?"[^"\\\n]*(\\.[^"\\\n]*)*"?'
    uf_sqstring =  r"(\b[rRuU])?'[^'\\\n]*(\\.[^'\\\n]*)*(\\)$(?!')$"
    uf_dqstring =  r'(\b[rRuU])?"[^"\\\n]*(\\.[^"\\\n]*)*(\\)$(?!")$'
    sq3string =    r"(\b[rRuU])?'''[^'\\]*((\\.|'(?!''))[^'\\]*)*(''')?"
    dq3string =    r'(\b[rRuU])?"""[^"\\]*((\\.|"(?!""))[^"\\]*)*(""")?'
    uf_sq3string = r"(\b[rRuU])?'''[^'\\]*((\\.|'(?!''))[^'\\]*)*(\\)?(?!''')$"
    uf_dq3string = r'(\b[rRuU])?"""[^"\\]*((\\.|"(?!""))[^"\\]*)*(\\)?(?!""")$'
    string = any("string", [sq3string, dq3string, sqstring, dqstring])
    ufstring1 = any("uf_sqstring", [uf_sqstring])
    ufstring2 = any("uf_dqstring", [uf_dqstring])
    ufstring3 = any("uf_sq3string", [uf_sq3string])
    ufstring4 = any("uf_dq3string", [uf_dq3string])
    return "|".join([instance, kw, builtin, comment,
                     ufstring1, ufstring2, ufstring3, ufstring4, string,
                     number, any("SYNC", [r"\n"])])

class OutlineExplorerData(object):
    CLASS, FUNCTION, STATEMENT, COMMENT = range(4)
    def __init__(self):
        self.text = None
        self.fold_level = None
        self.def_type = None
        self.def_name = None
        
    def is_not_class_nor_function(self):
        return self.def_type not in (self.CLASS, self.FUNCTION)
    
    def is_comment(self):
        return self.def_type == self.COMMENT
        
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
    def __init__(self, parent, font=None, color_scheme='Spyder'):
        BaseSH.__init__(self, parent, font, color_scheme)
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
                        self.setFormat(start, end-start,
                                       self.formats["string"])
                        state = self.INSIDE_SQ3STRING
                    elif key == "uf_dq3string":
                        self.setFormat(start, end-start,
                                       self.formats["string"])
                        state = self.INSIDE_DQ3STRING
                    elif key == "uf_sqstring":
                        self.setFormat(start, end-start,
                                       self.formats["string"])
                        state = self.INSIDE_SQSTRING
                    elif key == "uf_dqstring":
                        self.setFormat(start, end-start,
                                       self.formats["string"])
                        state = self.INSIDE_DQSTRING
                    else:
                        self.setFormat(start, end-start, self.formats[key])
                        if key == "comment":
                            if text.lstrip().startswith('#---'):
                                oedata = OutlineExplorerData()
                                oedata.text = unicode(text).strip()
                                oedata.fold_level = start
                                oedata.def_type = OutlineExplorerData.COMMENT
                                oedata.def_name = text.strip()
                        elif key == "keyword":
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
                                           "for", "if", "try", "while",
                                           "with"):
                                if text.lstrip().startswith(value):
                                    oedata = OutlineExplorerData()
                                    oedata.text = unicode(text).strip()
                                    oedata.fold_level = start
                                    oedata.def_type = \
                                        OutlineExplorerData.STATEMENT
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
        BaseSH.rehighlight(self)


#==============================================================================
# Cython syntax highlighter
#==============================================================================
C_TYPES = 'bool char double enum float int long mutable short signed struct unsigned void'

class CythonSH(PythonSH):
    """Cython Syntax Highlighter"""
    ADDITIONAL_KEYWORDS = ["cdef", "ctypedef", "cpdef", "inline", "cimport",
                           "DEF"]
    ADDITIONAL_BUILTINS = C_TYPES.split()
    PROG = re.compile(make_python_patterns(ADDITIONAL_KEYWORDS,
                                           ADDITIONAL_BUILTINS), re.S)
    IDPROG = re.compile(r"\s+([\w\.]+)", re.S)


#==============================================================================
# C/C++ syntax highlighter
#==============================================================================
C_KEYWORDS1 = 'and and_eq bitand bitor break case catch const const_cast continue default delete do dynamic_cast else explicit export extern for friend goto if inline namespace new not not_eq operator or or_eq private protected public register reinterpret_cast return sizeof static static_cast switch template throw try typedef typeid typename union using virtual while xor xor_eq'
C_KEYWORDS2 = 'a addindex addtogroup anchor arg attention author b brief bug c class code date def defgroup deprecated dontinclude e em endcode endhtmlonly ifdef endif endlatexonly endlink endverbatim enum example exception f$ file fn hideinitializer htmlinclude htmlonly if image include ingroup internal invariant interface latexonly li line link mainpage name namespace nosubgrouping note overload p page par param post pre ref relates remarks return retval sa section see showinitializer since skip skipline subsection test throw todo typedef union until var verbatim verbinclude version warning weakgroup'
C_KEYWORDS3 = 'asm auto class compl false true volatile wchar_t'

def make_generic_c_patterns(keywords, builtins):
    "Strongly inspired from idlelib.ColorDelegator.make_pat"
    kw = r"\b" + any("keyword", keywords.split()) + r"\b"
    builtin = r"\b" + any("builtin", builtins.split()+C_TYPES.split()) + r"\b"
    comment = any("comment", [r"//[^\n]*",r"\/\*(.*?)\*\/"])
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

    def highlightBlock(self, text):
        text = unicode(text)
        inside_comment = self.previousBlockState() == self.INSIDE_COMMENT
        self.setFormat(0, len(text),
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
                        self.setFormat(start, len(text)-start,
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

    def highlightBlock(self, text):
        text = unicode(text)
        self.setFormat(0, len(text), self.formats["normal"])
        
        match = self.PROG.search(text)
        index = 0
        while match:
            for key, value in match.groupdict().items():
                if value:
                    start, end = match.span(key)
                    index += end-start
                    self.setFormat(start, end-start, self.formats[key])
                    if value.lower() in ("subroutine", "module", "function"):
                        match1 = self.IDPROG.match(text, end)
                        if match1:
                            start1, end1 = match1.span(1)
                            self.setFormat(start1, end1-start1,
                                           self.formats["definition"])
                    
            match = self.PROG.search(text, match.end())

class Fortran77SH(FortranSH):
    """Fortran 77 Syntax Highlighter"""
    def highlightBlock(self, text):
        text = unicode(text)
        if text.startswith(("c", "C")):
            self.setFormat(0, len(text), self.formats["comment"])
        else:
            FortranSH.highlightBlock(self, text)
            self.setFormat(0, 5, self.formats["comment"])
            self.setFormat(73, max([73, len(text)]),
                           self.formats["comment"])


#==============================================================================
# Diff/Patch highlighter
#==============================================================================

class DiffSH(BaseSH):
    """Simple Diff/Patch Syntax Highlighter Class"""
    def highlightBlock(self, text):
        text = unicode(text)
        if text.startswith("+++"):
            self.setFormat(0, len(text), self.formats["keyword"])
        elif text.startswith("---"):
            self.setFormat(0, len(text), self.formats["keyword"])
        elif text.startswith("+"):
            self.setFormat(0, len(text), self.formats["string"])
        elif text.startswith("-"):
            self.setFormat(0, len(text), self.formats["number"])
        elif text.startswith("@"):
            self.setFormat(0, len(text), self.formats["builtin"])


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

class GetTextSH(BaseSH):
    """gettext Syntax Highlighter"""
    # Syntax highlighting rules:
    PROG = re.compile(make_gettext_patterns(), re.S)
    def __init__(self, parent, font=None, color_scheme=None):
        BaseSH.__init__(self, parent, font, color_scheme)

    def highlightBlock(self, text):
        text = unicode(text)
        self.setFormat(0, len(text), self.formats["normal"])
        
        match = self.PROG.search(text)
        index = 0
        while match:
            for key, value in match.groupdict().items():
                if value:
                    start, end = match.span(key)
                    index += end-start
                    self.setFormat(start, end-start, self.formats[key])
                    
            match = self.PROG.search(text, match.end())

#==============================================================================
# HTML highlighter
#==============================================================================

class BaseWebSH(BaseSH):
    """Base class for CSS and HTML syntax highlighters"""
    NORMAL  = 0
    COMMENT = 1
    
    def __init__(self, parent, font=None, color_scheme=None):
        BaseSH.__init__(self, parent, font, color_scheme)
    
    def highlightBlock(self, text):
        text = unicode(text)
        previous_state = self.previousBlockState()
        
        if previous_state == self.COMMENT:
            self.setFormat(0, len(text), self.formats["comment"])
        else:
            previous_state = self.NORMAL
            self.setFormat(0, len(text), self.formats["normal"])
        
        self.setCurrentBlockState(previous_state)
        match = self.PROG.search(text)        

        match_count = 0
        n_characters = len(text)
        # There should never be more matches than characters in the text.
        while match and match_count < n_characters:
            match_dict = match.groupdict()
            for key, value in match_dict.items():
                if value:
                    start, end = match.span(key)
                    if previous_state == self.COMMENT:
                        if key == "multiline_comment_end":
                            self.setCurrentBlockState(self.NORMAL)
                            self.setFormat(end, len(text),
                                           self.formats["normal"])
                        else:
                            self.setCurrentBlockState(self.COMMENT)
                            self.setFormat(0, len(text),
                                           self.formats["comment"])
                    else:
                        if key == "multiline_comment_start":
                            self.setCurrentBlockState(self.COMMENT)
                            self.setFormat(start, len(text),
                                           self.formats["comment"])
                        else:
                            self.setCurrentBlockState(self.NORMAL)
                            self.setFormat(start, end-start,
                                           self.formats[key])
            
            match = self.PROG.search(text, match.end())
            match_count += 1

def make_html_patterns():
    """Strongly inspired from idlelib.ColorDelegator.make_pat """
    tags = any("builtin", [r"<",r"[\?/]?>", r"(?<=<).*?(?=[ >])"])
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

#==============================================================================
# CSS highlighter
#==============================================================================

def make_css_patterns():
    """Strongly inspired from idlelib.ColorDelegator.make_pat """
    tags = any("builtin", [r"^[^{}/*:;]+$",
                           r"(?<=}\/).*?(?={)",
                           r"[^}]+?(?={)"])
    keywords = any("keyword", [r"[\w-]+?(?=:)"])
    string = any("string", [r"(?<=:).+?(?=;)"])
    comment = any("comment", [r"/\*(.*?)\*/"])
    multiline_comment_start = any("multiline_comment_start", [r"\/\*"])
    multiline_comment_end = any("multiline_comment_end", [r"\*\/"])
    return "|".join([tags, keywords, string, comment,
                     multiline_comment_start, multiline_comment_end]) 
    
class CssSH(BaseWebSH):
    """CSS Syntax Highlighter"""
    PROG = re.compile(make_css_patterns(), re.S)

