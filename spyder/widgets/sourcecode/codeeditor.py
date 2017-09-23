# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Editor widget based on QtGui.QPlainTextEdit
"""

# TODO: Try to separate this module from spyder to create a self
#       consistent editor module (Qt source code and shell widgets library)

# %% This line is for cell execution testing
# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
from __future__ import division
from unicodedata import category
import os.path as osp
import re
import sre_constants
import sys
import time

# Third party imports
from qtpy import is_pyqt46
from qtpy.compat import to_qvariant
from qtpy.QtCore import QRegExp, Qt, QTimer, Signal, Slot
from qtpy.QtGui import (QColor, QCursor, QFont, QIntValidator,
                        QKeySequence, QPaintEvent, QPainter,
                        QTextBlockUserData, QTextCharFormat, QTextCursor,
                        QKeyEvent, QTextDocument, QTextFormat, QTextOption)
from qtpy.QtPrintSupport import QPrinter
from qtpy.QtWidgets import (QApplication, QDialog, QDialogButtonBox,
                            QGridLayout, QHBoxLayout, QInputDialog, QLabel,
                            QLineEdit, QMenu, QMessageBox, QSplitter,
                            QToolTip, QVBoxLayout)
from spyder.widgets.panels.classfunctiondropdown import ClassFunctionDropdown

# %% This line is for cell execution testing

# Local imports
from spyder.config.base import get_conf_path, _, DEBUG
from spyder.config.gui import config_shortcut, get_shortcut
from spyder.config.main import (CONF, RUN_CELL_SHORTCUT,
                                RUN_CELL_AND_ADVANCE_SHORTCUT)
from spyder.py3compat import to_text_string
from spyder.utils import icon_manager as ima
from spyder.utils import syntaxhighlighters as sh
from spyder.utils import encoding, sourcecode
from spyder.utils.dochelpers import getobj
from spyder.utils.qthelpers import add_actions, create_action, mimedata2url
from spyder.utils.sourcecode import ALL_LANGUAGES, CELL_LANGUAGES
from spyder.utils.editor import TextHelper
from spyder.widgets.editortools import PythonCFM
from spyder.widgets.sourcecode.base import TextEditBaseWidget
from spyder.widgets.sourcecode.kill_ring import QtKillRing
from spyder.widgets.panels.linenumber import LineNumberArea
from spyder.widgets.panels.edgeline import EdgeLine
from spyder.widgets.panels.indentationguides import IndentationGuide
from spyder.widgets.panels.scrollflag import ScrollFlagArea
from spyder.widgets.panels.manager import PanelsManager
from spyder.widgets.panels.codefolding import FoldingPanel
from spyder.widgets.sourcecode.folding import IndentFoldDetector
from spyder.widgets.sourcecode.extensions.manager import (
        EditorExtensionsManager)
from spyder.widgets.sourcecode.extensions.closequotes import (
        CloseQuotesExtension)
from spyder.widgets.sourcecode.api.decoration import TextDecoration
from spyder.api.panel import Panel

try:
    import nbformat as nbformat
    from nbconvert import PythonExporter as nbexporter
except:
    nbformat = None  # analysis:ignore

# %% This line is for cell execution testing
# For debugging purpose:
LOG_FILENAME = get_conf_path('codeeditor.log')
DEBUG_EDITOR = DEBUG >= 3


def is_letter_or_number(char):
    """ Returns whether the specified unicode character is a letter or a number.
    """
    cat = category(char)
    return cat.startswith('L') or cat.startswith('N')

# =============================================================================
# Go to line dialog box
# =============================================================================
class GoToLineDialog(QDialog):
    def __init__(self, editor):
        QDialog.__init__(self, editor, Qt.WindowTitleHint
                         | Qt.WindowCloseButtonHint)

        # Destroying the C++ object right after closing the dialog box,
        # otherwise it may be garbage-collected in another QThread
        # (e.g. the editor's analysis thread in Spyder), thus leading to
        # a segmentation fault on UNIX or an application crash on Windows
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.lineno = None
        self.editor = editor

        self.setWindowTitle(_("Editor"))
        self.setModal(True)

        label = QLabel(_("Go to line:"))
        self.lineedit = QLineEdit()
        validator = QIntValidator(self.lineedit)
        validator.setRange(1, editor.get_line_count())
        self.lineedit.setValidator(validator)
        self.lineedit.textChanged.connect(self.text_has_changed)
        cl_label = QLabel(_("Current line:"))
        cl_label_v = QLabel("<b>%d</b>" % editor.get_cursor_line_number())
        last_label = QLabel(_("Line count:"))
        last_label_v = QLabel("%d" % editor.get_line_count())

        glayout = QGridLayout()
        glayout.addWidget(label, 0, 0, Qt.AlignVCenter|Qt.AlignRight)
        glayout.addWidget(self.lineedit, 0, 1, Qt.AlignVCenter)
        glayout.addWidget(cl_label, 1, 0, Qt.AlignVCenter|Qt.AlignRight)
        glayout.addWidget(cl_label_v, 1, 1, Qt.AlignVCenter)
        glayout.addWidget(last_label, 2, 0, Qt.AlignVCenter|Qt.AlignRight)
        glayout.addWidget(last_label_v, 2, 1, Qt.AlignVCenter)

        bbox = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel,
                                Qt.Vertical, self)
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)
        btnlayout = QVBoxLayout()
        btnlayout.addWidget(bbox)
        btnlayout.addStretch(1)

        ok_button = bbox.button(QDialogButtonBox.Ok)
        ok_button.setEnabled(False)
        self.lineedit.textChanged.connect(
                     lambda text: ok_button.setEnabled(len(text) > 0))

        layout = QHBoxLayout()
        layout.addLayout(glayout)
        layout.addLayout(btnlayout)
        self.setLayout(layout)

        self.lineedit.setFocus()

    def text_has_changed(self, text):
        """Line edit's text has changed"""
        text = to_text_string(text)
        if text:
            self.lineno = int(text)
        else:
            self.lineno = None

    def get_line_number(self):
        """Return line number"""
        # It is import to avoid accessing Qt C++ object as it has probably
        # already been destroyed, due to the Qt.WA_DeleteOnClose attribute
        return self.lineno


#===============================================================================
# CodeEditor widget
#===============================================================================
class BlockUserData(QTextBlockUserData):
    def __init__(self, editor):
        QTextBlockUserData.__init__(self)
        self.editor = editor
        self.breakpoint = False
        self.breakpoint_condition = None
        self.code_analysis = []
        self.todo = ''
        self.editor.blockuserdata_list.append(self)

    def is_empty(self):
        return not self.breakpoint and not self.code_analysis and not self.todo

    def __del__(self):
        bud_list = self.editor.blockuserdata_list
        bud_list.pop(bud_list.index(self))


def get_file_language(filename, text=None):
    """Get file language from filename"""
    ext = osp.splitext(filename)[1]
    if ext.startswith('.'):
        ext = ext[1:] # file extension with leading dot
    language = ext
    if not ext:
        if text is None:
            text, _enc = encoding.read(filename)
        for line in text.splitlines():
            if not line.strip():
                continue
            if line.startswith('#!'):
               shebang = line[2:]
               if 'python' in shebang:
                   language = 'python'
            else:
                break
    return language


class CodeEditor(TextEditBaseWidget):
    """Source Code Editor Widget based exclusively on Qt"""

    LANGUAGES = {'Python': (sh.PythonSH, '#', PythonCFM),
                 'Cython': (sh.CythonSH, '#', PythonCFM),
                 'Fortran77': (sh.Fortran77SH, 'c', None),
                 'Fortran': (sh.FortranSH, '!', None),
                 'Idl': (sh.IdlSH, ';', None),
                 'Diff': (sh.DiffSH, '', None),
                 'GetText': (sh.GetTextSH, '#', None),
                 'Nsis': (sh.NsisSH, '#', None),
                 'Html': (sh.HtmlSH, '', None),
                 'Yaml': (sh.YamlSH, '#', None),
                 'Cpp': (sh.CppSH, '//', None),
                 'OpenCL': (sh.OpenCLSH, '//', None),
                 'Enaml': (sh.EnamlSH, '#', PythonCFM),
                 'Markdown': (sh.MarkdownSH, '#', None),
                }

    TAB_ALWAYS_INDENTS = ('py', 'pyw', 'python', 'c', 'cpp', 'cl', 'h')

    # Custom signal to be emitted upon completion of the editor's paintEvent
    painted = Signal(QPaintEvent)

    # To have these attrs when early viewportEvent's are triggered
    edge_line = None
    indent_guides = None

    breakpoints_changed = Signal()
    get_completions = Signal(bool)
    go_to_definition = Signal(int)
    sig_show_object_info = Signal(int)
    run_selection = Signal()
    run_cell_and_advance = Signal()
    run_cell = Signal()
    re_run_last_cell = Signal()
    go_to_definition_regex = Signal(int)
    sig_cursor_position_changed = Signal(int, int)
    focus_changed = Signal()
    sig_new_file = Signal(str)

    #: Signal emitted when a key is pressed
    key_pressed = Signal(QKeyEvent)

    #: Signal emitted when a new text is set on the widget
    new_text_set = Signal()

    def __init__(self, parent=None):
        TextEditBaseWidget.__init__(self, parent)

        self.setFocusPolicy(Qt.StrongFocus)

        # We use these object names to set the right background
        # color when changing color schemes or creating new
        # Editor windows. This seems to be a Qt bug.
        # Fixes Issue 2028
        if sys.platform == 'darwin':
            plugin_name = repr(parent)
            if 'editor' in plugin_name.lower():
                self.setObjectName('editor')
            elif 'help' in plugin_name.lower():
                self.setObjectName('help')
            elif 'historylog' in plugin_name.lower():
                self.setObjectName('historylog')
            elif 'configdialog' in plugin_name.lower():
                self.setObjectName('configdialog')

        # Caret (text cursor)
        self.setCursorWidth( CONF.get('main', 'cursor/width') )

        self.text_helper = TextHelper(self)

        self._panels = PanelsManager(self)

        # 79-col edge line
        self.edge_line = self.panels.register(EdgeLine(self),
                                              Panel.Position.FLOATING)

        # indent guides
        self.indent_guides = self.panels.register(IndentationGuide(self),
                                                  Panel.Position.FLOATING)

        # Blanks enabled
        self.blanks_enabled = False

        # Scrolling past the end of the document
        self.scrollpastend_enabled = False

        self.background = QColor('white')

        # Folding
        self.panels.register(FoldingPanel())

        # Line number area management
        self.linenumberarea = self.panels.register(LineNumberArea(self))
        
        # Class and Method/Function Dropdowns
        self.classfuncdropdown = self.panels.register(
            ClassFunctionDropdown(self),
            Panel.Position.TOP,
        )
        
        # Colors to be defined in _apply_highlighter_color_scheme()
        # Currentcell color and current line color are defined in base.py
        self.occurrence_color = None
        self.ctrl_click_color = None
        self.sideareas_color = None
        self.matched_p_color = None
        self.unmatched_p_color = None
        self.normal_color = None
        self.comment_color = None

        # --- Syntax highlight entrypoint ---
        #
        # - if set, self.highlighter is responsible for
        #   - coloring raw text data inside editor on load
        #   - coloring text data when editor is cloned
        #   - updating document highlight on line edits
        #   - providing color palette (scheme) for the editor
        #   - providing data for Outliner
        # - self.highlighter is not responsible for
        #   - background highlight for current line
        #   - background highlight for search / current line occurrences

        self.highlighter_class = sh.TextSH
        self.highlighter = None
        ccs = 'Spyder'
        if ccs not in sh.COLOR_SCHEME_NAMES:
            ccs = sh.COLOR_SCHEME_NAMES[0]
        self.color_scheme = ccs

        self.highlight_current_line_enabled = False

        # Scrollbar flag area
        self.scrollflagarea = self.panels.register(ScrollFlagArea(self),
                                                   Panel.Position.RIGHT)
        self.scrollflagarea.hide()
        self.warning_color = "#FFAD07"
        self.error_color = "#EA2B0E"
        self.todo_color = "#B4D4F3"
        self.breakpoint_color = "#30E62E"

        self.panels.refresh()

        self.document_id = id(self)

        # Indicate occurrences of the selected word
        self.cursorPositionChanged.connect(self.__cursor_position_changed)
        self.__find_first_pos = None
        self.__find_flags = None

        self.supported_language = False
        self.supported_cell_language = False
        self.classfunc_match = None
        self.comment_string = None
        self._kill_ring = QtKillRing(self)

        # Block user data
        self.blockuserdata_list = []

        # Update breakpoints if the number of lines in the file changes
        self.blockCountChanged.connect(self.update_breakpoints)

        # Highlight using Pygments highlighter timer
        # ---------------------------------------------------------------------
        # For files that use the PygmentsSH we parse the full file inside
        # the highlighter in order to generate the correct coloring.
        self.timer_syntax_highlight = QTimer(self)
        self.timer_syntax_highlight.setSingleShot(True)
        # We wait 300 ms to trigger a new coloring as this value is a good
        # proxy for estimating when an user has stopped typing
        self.timer_syntax_highlight.setInterval(300)
        self.timer_syntax_highlight.timeout.connect(
            self.run_pygments_highlighter)

        # Mark occurrences timer
        self.occurrence_highlighting = None
        self.occurrence_timer = QTimer(self)
        self.occurrence_timer.setSingleShot(True)
        self.occurrence_timer.setInterval(1500)
        self.occurrence_timer.timeout.connect(self.__mark_occurrences)
        self.occurrences = []
        self.occurrence_color = QColor(Qt.yellow).lighter(160)

        # Mark found results
        self.textChanged.connect(self.__text_has_changed)
        self.found_results = []
        self.found_results_color = QColor(Qt.magenta).lighter(180)

        # Context menu
        self.gotodef_action = None
        self.setup_context_menu()

        # Tab key behavior
        self.tab_indents = None
        self.tab_mode = True # see CodeEditor.set_tab_mode

        # Intelligent backspace mode
        self.intelligent_backspace = True

        self.go_to_definition_enabled = False
        self.close_parentheses_enabled = True
        self.close_quotes_enabled = False
        self.add_colons_enabled = True
        self.auto_unindent_enabled = True

        # Mouse tracking
        self.setMouseTracking(True)
        self.__cursor_changed = False
        self.ctrl_click_color = QColor(Qt.blue)

        # Breakpoints
        self.breakpoints = self.get_breakpoints()

        # Keyboard shortcuts
        self.shortcuts = self.create_shortcuts()

        # Code editor
        self.__visible_blocks = []  # Visible blocks, update with repaint
        self.painted.connect(self._draw_editor_cell_divider)

        self.verticalScrollBar().valueChanged.connect(
                                       lambda value: self.rehighlight_cells())

        # Editor Extensions
        self.editor_extensions = EditorExtensionsManager(self)

        self.editor_extensions.add(CloseQuotesExtension())

    def create_shortcuts(self):
        codecomp = config_shortcut(self.do_completion, context='Editor',
                                   name='Code Completion', parent=self)
        duplicate_line = config_shortcut(self.duplicate_line, context='Editor',
                                         name='Duplicate line', parent=self)
        copyline = config_shortcut(self.copy_line, context='Editor',
                                   name='Copy line', parent=self)
        deleteline = config_shortcut(self.delete_line, context='Editor',
                                     name='Delete line', parent=self)
        movelineup = config_shortcut(self.move_line_up, context='Editor',
                                     name='Move line up', parent=self)
        movelinedown = config_shortcut(self.move_line_down, context='Editor',
                                       name='Move line down', parent=self)
        gotodef = config_shortcut(self.do_go_to_definition, context='Editor',
                                  name='Go to definition', parent=self)
        toggle_comment = config_shortcut(self.toggle_comment, context='Editor',
                                         name='Toggle comment', parent=self)
        blockcomment = config_shortcut(self.blockcomment, context='Editor',
                                       name='Blockcomment', parent=self)
        unblockcomment = config_shortcut(self.unblockcomment, context='Editor',
                                         name='Unblockcomment', parent=self)
        transform_uppercase = config_shortcut(self.transform_to_uppercase,
                                              context='Editor',
                                              name='Transform to uppercase',
                                              parent=self)
        transform_lowercase = config_shortcut(self.transform_to_lowercase,
                                              context='Editor',
                                              name='Transform to lowercase',
                                              parent=self)

        indent = config_shortcut(lambda: self.indent(force=True),
                                 context='Editor', name='Indent', parent=self)
        unindent = config_shortcut(lambda: self.unindent(force=True),
                                   context='Editor', name='Unindent',
                                   parent=self)

        def cb_maker(attr):
            """Make a callback for cursor move event type, (e.g. "Start")
            """
            def cursor_move_event():
                cursor = self.textCursor()
                move_type = getattr(QTextCursor, attr)
                cursor.movePosition(move_type)
                self.setTextCursor(cursor)
            return cursor_move_event

        line_start = config_shortcut(cb_maker('StartOfLine'), context='Editor',
                                     name='Start of line', parent=self)
        line_end = config_shortcut(cb_maker('EndOfLine'), context='Editor',
                                   name='End of line', parent=self)

        prev_line = config_shortcut(cb_maker('Up'), context='Editor',
                                    name='Previous line', parent=self)
        next_line = config_shortcut(cb_maker('Down'), context='Editor',
                                    name='Next line', parent=self)

        prev_char = config_shortcut(cb_maker('Left'), context='Editor',
                                    name='Previous char', parent=self)
        next_char = config_shortcut(cb_maker('Right'), context='Editor',
                                    name='Next char', parent=self)

        prev_word = config_shortcut(cb_maker('StartOfWord'), context='Editor',
                                    name='Previous word', parent=self)
        next_word = config_shortcut(cb_maker('EndOfWord'), context='Editor',
                                    name='Next word', parent=self)

        kill_line_end = config_shortcut(self.kill_line_end, context='Editor',
                                        name='Kill to line end', parent=self)
        kill_line_start = config_shortcut(self.kill_line_start,
                                          context='Editor',
                                          name='Kill to line start',
                                          parent=self)
        yank = config_shortcut(self._kill_ring.yank, context='Editor',
                               name='Yank', parent=self)
        kill_ring_rotate = config_shortcut(self._kill_ring.rotate,
                                           context='Editor',
                                           name='Rotate kill ring',
                                           parent=self)

        kill_prev_word = config_shortcut(self.kill_prev_word, context='Editor',
                                         name='Kill previous word',
                                         parent=self)
        kill_next_word = config_shortcut(self.kill_next_word, context='Editor',
                                         name='Kill next word', parent=self)

        start_doc = config_shortcut(cb_maker('Start'), context='Editor',
                                    name='Start of Document', parent=self)

        end_doc = config_shortcut(cb_maker('End'), context='Editor',
                                  name='End of document', parent=self)

        undo = config_shortcut(self.undo, context='Editor',
                               name='undo', parent=self)
        redo = config_shortcut(self.redo, context='Editor',
                               name='redo', parent=self)
        cut = config_shortcut(self.cut, context='Editor',
                              name='cut', parent=self)
        copy = config_shortcut(self.copy, context='Editor',
                               name='copy', parent=self)
        paste = config_shortcut(self.paste, context='Editor',
                                name='paste', parent=self)
        delete = config_shortcut(self.delete, context='Editor',
                                 name='delete', parent=self)
        select_all = config_shortcut(self.selectAll, context='Editor',
                                     name='Select All', parent=self)
        array_inline = config_shortcut(lambda: self.enter_array_inline(),
                                       context='array_builder',
                                       name='enter array inline', parent=self)
        array_table = config_shortcut(lambda: self.enter_array_table(),
                                      context='array_builder',
                                      name='enter array table', parent=self)

        return [codecomp, duplicate_line, copyline, deleteline, movelineup,
                movelinedown, gotodef, toggle_comment, blockcomment,
                unblockcomment, transform_uppercase, transform_lowercase, 
                line_start, line_end, prev_line, next_line,
                prev_char, next_char, prev_word, next_word, kill_line_end,
                kill_line_start, yank, kill_ring_rotate, kill_prev_word,
                kill_next_word, start_doc, end_doc, undo, redo, cut, copy,
                paste, delete, select_all, array_inline, array_table, indent,
                unindent]

    def get_shortcut_data(self):
        """
        Returns shortcut data, a list of tuples (shortcut, text, default)
        shortcut (QShortcut or QAction instance)
        text (string): action/shortcut description
        default (string): default key sequence
        """
        return [sc.data for sc in self.shortcuts]

    def closeEvent(self, event):
        TextEditBaseWidget.closeEvent(self, event)
        if is_pyqt46:
            self.destroyed.emit()

    def get_document_id(self):
        return self.document_id

    def set_as_clone(self, editor):
        """Set as clone editor"""
        self.setDocument(editor.document())
        self.document_id = editor.get_document_id()
        self.highlighter = editor.highlighter
        self.eol_chars = editor.eol_chars
        self._apply_highlighter_color_scheme()

    #-----Widget setup and options
    def toggle_wrap_mode(self, enable):
        """Enable/disable wrap mode"""
        self.set_wrap_mode('word' if enable else None)

    @property
    def panels(self):
        """
        Returns a reference to the :class:`spyder.widgets.panels.managers.PanelsManager`
        used to manage the collection of installed panels
        """
        return self._panels

    def setup_editor(self, linenumbers=True, language=None, markers=False,
                     font=None, color_scheme=None, wrap=False, tab_mode=True,
                     intelligent_backspace=True, highlight_current_line=True,
                     highlight_current_cell=True, occurrence_highlighting=True,
                     scrollflagarea=True, edge_line=True, edge_line_columns=(79,),
                     codecompletion_auto=False, codecompletion_case=True,
                     codecompletion_enter=False, show_blanks=False,
                     calltips=None, go_to_definition=False,
                     close_parentheses=True, close_quotes=False,
                     add_colons=True, auto_unindent=True, indent_chars=" "*4,
                     tab_stop_width_spaces=4, cloned_from=None, filename=None,
                     occurrence_timeout=1500, show_class_func_dropdown=False,
                     indent_guides=False, scroll_past_end=False):

        # Code completion and calltips
        self.set_codecompletion_auto(codecompletion_auto)
        self.set_codecompletion_case(codecompletion_case)
        self.set_codecompletion_enter(codecompletion_enter)
        self.set_calltips(calltips)
        self.set_go_to_definition_enabled(go_to_definition)
        self.set_close_parentheses_enabled(close_parentheses)
        self.set_close_quotes_enabled(close_quotes)
        self.set_add_colons_enabled(add_colons)
        self.set_auto_unindent_enabled(auto_unindent)
        self.set_indent_chars(indent_chars)
        self.set_tab_stop_width_spaces(tab_stop_width_spaces)

        # Scrollbar flag area
        self.scrollflagarea.set_enabled(scrollflagarea)

        # Edge line
        self.edge_line.set_enabled(edge_line)
        self.edge_line.set_columns(edge_line_columns)

        # Indent guides
        self.indent_guides.set_enabled(indent_guides)
        if self.indent_chars == '\t':
            self.indent_guides.set_indentation_width(self.tab_stop_width_spaces)
        else:
            self.indent_guides.set_indentation_width(len(self.indent_chars))

        # Blanks
        self.set_blanks_enabled(show_blanks)

        # Scrolling past the end
        self.set_scrollpastend_enabled(scroll_past_end)

        # Line number area
        if cloned_from:
            self.setFont(font) # this is required for line numbers area
        self.linenumberarea.setup_margins(linenumbers, markers)

        # Lexer
        self.set_language(language, filename)

        # Highlight current cell
        self.set_highlight_current_cell(highlight_current_cell)

        # Highlight current line
        self.set_highlight_current_line(highlight_current_line)

        # Occurrence highlighting
        self.set_occurrence_highlighting(occurrence_highlighting)
        self.set_occurrence_timeout(occurrence_timeout)

        # Tab always indents (even when cursor is not at the begin of line)
        self.set_tab_mode(tab_mode)

        # Intelligent backspace
        self.toggle_intelligent_backspace(intelligent_backspace)

        if cloned_from is not None:
            self.set_as_clone(cloned_from)
            self.panels.refresh()
        elif font is not None:
            self.set_font(font, color_scheme)
        elif color_scheme is not None:
            self.set_color_scheme(color_scheme)

        self.toggle_wrap_mode(wrap)

        # Class/Function dropdown will be disabled if we're not in a Python file.
        self.classfuncdropdown.setVisible(show_class_func_dropdown
                                          and self.is_python_like())

    def set_tab_mode(self, enable):
        """
        enabled = tab always indent
        (otherwise tab indents only when cursor is at the beginning of a line)
        """
        self.tab_mode = enable

    def toggle_intelligent_backspace(self, state):
        self.intelligent_backspace = state

    def set_go_to_definition_enabled(self, enable):
        """Enable/Disable go-to-definition feature, which is implemented in
        child class -> Editor widget"""
        self.go_to_definition_enabled = enable

    def set_close_parentheses_enabled(self, enable):
        """Enable/disable automatic parentheses insertion feature"""
        self.close_parentheses_enabled = enable

    def set_close_quotes_enabled(self, enable):
        """Enable/disable automatic quote insertion feature"""
        self.close_quotes_enabled = enable
        quote_extension = self.editor_extensions.get(CloseQuotesExtension)
        if quote_extension is not None:
            quote_extension.enabled = enable

    def set_add_colons_enabled(self, enable):
        """Enable/disable automatic colons insertion feature"""
        self.add_colons_enabled = enable

    def set_auto_unindent_enabled(self, enable):
        """Enable/disable automatic unindent after else/elif/finally/except"""
        self.auto_unindent_enabled = enable

    def set_occurrence_highlighting(self, enable):
        """Enable/disable occurrence highlighting"""
        self.occurrence_highlighting = enable
        if not enable:
            self.__clear_occurrences()

    def set_occurrence_timeout(self, timeout):
        """Set occurrence highlighting timeout (ms)"""
        self.occurrence_timer.setInterval(timeout)

    def set_highlight_current_line(self, enable):
        """Enable/disable current line highlighting"""
        self.highlight_current_line_enabled = enable
        if self.highlight_current_line_enabled:
            self.highlight_current_line()
        else:
            self.unhighlight_current_line()

    def set_highlight_current_cell(self, enable):
        """Enable/disable current line highlighting"""
        hl_cell_enable = enable and self.supported_cell_language
        self.highlight_current_cell_enabled = hl_cell_enable
        if self.highlight_current_cell_enabled:
            self.highlight_current_cell()
        else:
            self.unhighlight_current_cell()

    def set_language(self, language, filename=None):
        self.tab_indents = language in self.TAB_ALWAYS_INDENTS
        self.comment_string = ''
        sh_class = sh.TextSH
        if language is not None:
            for (key, value) in ALL_LANGUAGES.items():
                if language.lower() in value:
                    self.supported_language = True
                    sh_class, comment_string, CFMatch = self.LANGUAGES[key]
                    self.comment_string = comment_string
                    if key in CELL_LANGUAGES:
                        self.supported_cell_language = True
                        self.cell_separators = CELL_LANGUAGES[key]
                    if CFMatch is None:
                        self.classfunc_match = None
                    else:
                        self.classfunc_match = CFMatch()
                    break
        if filename is not None and not self.supported_language:
            sh_class = sh.guess_pygments_highlighter(filename)
            self.support_language = sh_class is not sh.TextSH
        self._set_highlighter(sh_class)

    def _set_highlighter(self, sh_class):
        self.highlighter_class = sh_class
        if self.highlighter is not None:
            # Removing old highlighter
            # TODO: test if leaving parent/document as is eats memory
            self.highlighter.setParent(None)
            self.highlighter.setDocument(None)
        self.highlighter = self.highlighter_class(self.document(),
                                                  self.font(),
                                                  self.color_scheme)
        self._apply_highlighter_color_scheme()

        self.highlighter.fold_detector = IndentFoldDetector()
        self.highlighter.editor = self

    def is_json(self):
        return (isinstance(self.highlighter, sh.PygmentsSH) and
                self.highlighter._lexer.name == 'JSON')

    def is_python(self):
        return self.highlighter_class is sh.PythonSH

    def is_cython(self):
        return self.highlighter_class is sh.CythonSH

    def is_enaml(self):
        return self.highlighter_class is sh.EnamlSH

    def is_python_like(self):
        return self.is_python() or self.is_cython() or self.is_enaml()

    def intelligent_tab(self):
        """Provide intelligent behavoir for Tab key press"""
        leading_text = self.get_text('sol', 'cursor')
        if not leading_text.strip() or leading_text.endswith('#'):
            # blank line or start of comment
            self.indent_or_replace()
        elif self.in_comment_or_string() and not leading_text.endswith(' '):
            # in a word in a comment
            self.do_completion()
        elif leading_text.endswith('import ') or leading_text[-1] == '.':
            # blank import or dot completion
            self.do_completion()
        elif (leading_text.split()[0] in ['from', 'import'] and
              not ';' in leading_text):
            # import line with a single statement
            #  (prevents lines like: `import pdb; pdb.set_trace()`)
            self.do_completion()
        elif leading_text[-1] in '(,' or leading_text.endswith(', '):
            self.indent_or_replace()
        elif leading_text.endswith(' '):
            # if the line ends with a space, indent
            self.indent_or_replace()
        elif re.search(r"[^\d\W]\w*\Z", leading_text, re.UNICODE):
            # if the line ends with a non-whitespace character
            self.do_completion()
        else:
            self.indent_or_replace()

    def intelligent_backtab(self):
        """Provide intelligent behavoir for Shift+Tab key press"""
        leading_text = self.get_text('sol', 'cursor')
        if not leading_text.strip():
            # blank line
            self.unindent()
        elif self.in_comment_or_string():
            self.unindent()
        elif leading_text[-1] in '(,' or leading_text.endswith(', '):
            position = self.get_position('cursor')
            self.show_object_info(position)
        else:
            # if the line ends with any other character but comma
            self.unindent()

    def rehighlight(self):
        """
        Rehighlight the whole document to rebuild outline explorer data
        and import statements data from scratch
        """
        if self.highlighter is not None:
            self.highlighter.rehighlight()
        if self.highlight_current_cell_enabled:
            self.highlight_current_cell()
        else:
            self.unhighlight_current_cell()
        if self.highlight_current_line_enabled:
            self.highlight_current_line()
        else:
            self.unhighlight_current_line()

    def rehighlight_cells(self):
        """Rehighlight cells when moving the scrollbar"""
        if self.highlight_current_cell_enabled:
            self.highlight_current_cell()

    def remove_trailing_spaces(self):
        """Remove trailing spaces"""
        cursor = self.textCursor()
        cursor.beginEditBlock()
        cursor.movePosition(QTextCursor.Start)
        while True:
            cursor.movePosition(QTextCursor.EndOfBlock)
            text = to_text_string(cursor.block().text())
            length = len(text)-len(text.rstrip())
            if length > 0:
                cursor.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor,
                                    length)
                cursor.removeSelectedText()
            if cursor.atEnd():
                break
            cursor.movePosition(QTextCursor.NextBlock)
        cursor.endEditBlock()

    def fix_indentation(self):
        """Replace tabs by spaces"""
        text_before = to_text_string(self.toPlainText())
        text_after = sourcecode.fix_indentation(text_before)
        if text_before != text_after:
            self.setPlainText(text_after)
            self.document().setModified(True)

    def get_current_object(self):
        """Return current object (string) """
        source_code = to_text_string(self.toPlainText())
        offset = self.get_position('cursor')
        return sourcecode.get_primary_at(source_code, offset)

    @Slot()
    def delete(self):
        """Remove selected text"""
        if self.has_selected_text():
            self.remove_selected_text()

    #------Find occurrences
    def __find_first(self, text):
        """Find first occurrence: scan whole document"""
        flags = QTextDocument.FindCaseSensitively|QTextDocument.FindWholeWords
        cursor = self.textCursor()
        # Scanning whole document
        cursor.movePosition(QTextCursor.Start)
        regexp = QRegExp(r"\b%s\b" % QRegExp.escape(text), Qt.CaseSensitive)
        cursor = self.document().find(regexp, cursor, flags)
        self.__find_first_pos = cursor.position()
        return cursor

    def __find_next(self, text, cursor):
        """Find next occurrence"""
        flags = QTextDocument.FindCaseSensitively|QTextDocument.FindWholeWords
        regexp = QRegExp(r"\b%s\b" % QRegExp.escape(text), Qt.CaseSensitive)
        cursor = self.document().find(regexp, cursor, flags)
        if cursor.position() != self.__find_first_pos:
            return cursor

    def __cursor_position_changed(self):
        """Cursor position has changed"""
        line, column = self.get_cursor_line_column()
        self.sig_cursor_position_changed.emit(line, column)
        if self.highlight_current_cell_enabled:
            self.highlight_current_cell()
        else:
            self.unhighlight_current_cell()
        if self.highlight_current_line_enabled:
            self.highlight_current_line()
        else:
            self.unhighlight_current_line()
        if self.occurrence_highlighting:
            self.occurrence_timer.stop()
            self.occurrence_timer.start()

    def __clear_occurrences(self):
        """Clear occurrence markers"""
        self.occurrences = []
        self.clear_extra_selections('occurrences')
        self.scrollflagarea.update()

    def __highlight_selection(self, key, cursor, foreground_color=None,
                        background_color=None, underline_color=None,
                        underline_style=QTextCharFormat.SpellCheckUnderline,
                        update=False):
        extra_selections = self.get_extra_selections(key)
        selection = TextDecoration(cursor)
        if foreground_color is not None:
            selection.format.setForeground(foreground_color)
        if background_color is not None:
            selection.format.setBackground(background_color)
        if underline_color is not None:
            selection.format.setProperty(QTextFormat.TextUnderlineStyle,
                                         to_qvariant(underline_style))
            selection.format.setProperty(QTextFormat.TextUnderlineColor,
                                         to_qvariant(underline_color))
        selection.format.setProperty(QTextFormat.FullWidthSelection,
                                     to_qvariant(True))
        extra_selections.append(selection)
        self.set_extra_selections(key, extra_selections)
        if update:
            self.update_extra_selections()

    def __mark_occurrences(self):
        """Marking occurrences of the currently selected word"""
        self.__clear_occurrences()

        if not self.supported_language:
            return

        text = self.get_current_word()
        if text is None:
            return
        if self.has_selected_text() and self.get_selected_text() != text:
            return

        if (self.is_python_like()) and \
           (sourcecode.is_keyword(to_text_string(text)) or \
           to_text_string(text) == 'self'):
            return

        # Highlighting all occurrences of word *text*
        cursor = self.__find_first(text)
        self.occurrences = []
        while cursor:
            self.occurrences.append(cursor.blockNumber())
            self.__highlight_selection('occurrences', cursor,
                                       background_color=self.occurrence_color)
            cursor = self.__find_next(text, cursor)
        self.update_extra_selections()
        if len(self.occurrences) > 1 and self.occurrences[-1] == 0:
            # XXX: this is never happening with PySide but it's necessary
            # for PyQt4... this must be related to a different behavior for
            # the QTextDocument.find function between those two libraries
            self.occurrences.pop(-1)
        self.scrollflagarea.update()

    #-----highlight found results (find/replace widget)
    def highlight_found_results(self, pattern, words=False, regexp=False):
        """Highlight all found patterns"""
        pattern = to_text_string(pattern)
        if not pattern:
            return
        if not regexp:
            pattern = re.escape(to_text_string(pattern))
        pattern = r"\b%s\b" % pattern if words else pattern
        text = to_text_string(self.toPlainText())
        try:
            regobj = re.compile(pattern)
        except sre_constants.error:
            return
        extra_selections = []
        self.found_results = []
        for match in regobj.finditer(text):
            pos1, pos2 = match.span()
            selection = TextDecoration(self.textCursor())
            selection.format.setBackground(self.found_results_color)
            selection.cursor.setPosition(pos1)
            self.found_results.append(selection.cursor.blockNumber())
            selection.cursor.setPosition(pos2, QTextCursor.KeepAnchor)
            extra_selections.append(selection)
        self.set_extra_selections('find', extra_selections)
        self.update_extra_selections()

    def clear_found_results(self):
        """Clear found results highlighting"""
        self.found_results = []
        self.clear_extra_selections('find')
        self.scrollflagarea.update()

    def __text_has_changed(self):
        """Text has changed, eventually clear found results highlighting"""
        if self.found_results:
            self.clear_found_results()

    def get_linenumberarea_width(self):
        """
        Return current line number area width.

        This method is left for backward compatibility (BaseEditMixin
        define it), any changes should be in LineNumberArea class.
        """
        return self.linenumberarea.get_width()

    def calculate_real_position(self, point):
        """Add offset to a point, to take into account the panels."""
        point.setX(point.x()+self.panels.margin_size(Panel.Position.LEFT))
        point.setY(point.y()+self.panels.margin_size(Panel.Position.TOP))
        return point

    def get_linenumber_from_mouse_event(self, event):
        """Return line number from mouse event"""
        block = self.firstVisibleBlock()
        line_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(
                                                    self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        while block.isValid() and top < event.pos().y():
            block = block.next()
            if block.isVisible():  # skip collapsed blocks
                top = bottom
                bottom = top + self.blockBoundingRect(block).height()
                line_number += 1

        return line_number

    def select_lines(self, linenumber_pressed,
                                    linenumber_released):
        """Select line(s) after a mouse press/mouse press drag event"""
        find_block_by_line_number = self.document().findBlockByLineNumber
        move_n_blocks = (linenumber_released - linenumber_pressed)
        start_line = linenumber_pressed
        start_block = find_block_by_line_number(start_line - 1)

        cursor = self.textCursor()
        cursor.setPosition(start_block.position())

        # Select/drag downwards
        if move_n_blocks > 0:
            for n in range(abs(move_n_blocks) + 1):
                cursor.movePosition(cursor.NextBlock, cursor.KeepAnchor)
        # Select/drag upwards or select single line
        else:
            cursor.movePosition(cursor.NextBlock)
            for n in range(abs(move_n_blocks) + 1):
                cursor.movePosition(cursor.PreviousBlock, cursor.KeepAnchor)

        # Account for last line case
        if linenumber_released == self.blockCount():
            cursor.movePosition(cursor.EndOfBlock, cursor.KeepAnchor)
        else:
            cursor.movePosition(cursor.StartOfBlock, cursor.KeepAnchor)

        self.setTextCursor(cursor)

    #------Breakpoints
    def add_remove_breakpoint(self, line_number=None, condition=None,
                              edit_condition=False):
        """Add/remove breakpoint"""
        if not self.is_python_like():
            return
        if line_number is None:
            block = self.textCursor().block()
        else:
            block = self.document().findBlockByNumber(line_number-1)
        data = block.userData()
        if data:
            data.breakpoint = not data.breakpoint
            old_breakpoint_condition = data.breakpoint_condition
            data.breakpoint_condition = None
        else:
            data = BlockUserData(self)
            data.breakpoint = True
            old_breakpoint_condition = None
        if condition is not None:
            data.breakpoint_condition = condition
        if edit_condition:
            data.breakpoint = True
            condition = data.breakpoint_condition
            if old_breakpoint_condition is not None:
                condition = old_breakpoint_condition
            condition, valid = QInputDialog.getText(self,
                                        _('Breakpoint'),
                                        _("Condition:"),
                                        QLineEdit.Normal, condition)
            if valid:
                condition = str(condition)
                if not condition:
                    condition = None
                data.breakpoint_condition = condition
            else:
                data.breakpoint_condition = old_breakpoint_condition
                return
        if data.breakpoint:
            text = to_text_string(block.text()).strip()
            if len(text) == 0 or text.startswith('#') or text.startswith('"') \
               or text.startswith("'"):
                data.breakpoint = False
        block.setUserData(data)
        self.linenumberarea.update()
        self.scrollflagarea.update()
        self.breakpoints_changed.emit()

    def get_breakpoints(self):
        """Get breakpoints"""
        breakpoints = []
        block = self.document().firstBlock()
        for line_number in range(1, self.document().blockCount()+1):
            data = block.userData()
            if data and data.breakpoint:
                breakpoints.append((line_number, data.breakpoint_condition))
            block = block.next()
        return breakpoints

    def clear_breakpoints(self):
        """Clear breakpoints"""
        self.breakpoints = []
        for data in self.blockuserdata_list[:]:
            data.breakpoint = False
            # data.breakpoint_condition = None  # not necessary, but logical
            if data.is_empty():
                del data

    def set_breakpoints(self, breakpoints):
        """Set breakpoints"""
        self.clear_breakpoints()
        for line_number, condition in breakpoints:
            self.add_remove_breakpoint(line_number, condition)

    def update_breakpoints(self):
        """Update breakpoints"""
        self.breakpoints_changed.emit()

    #-----Code introspection
    def do_completion(self, automatic=False):
        """Trigger completion"""
        if not self.is_completion_widget_visible():
            self.get_completions.emit(automatic)

    def do_go_to_definition(self):
        """Trigger go-to-definition"""
        if not self.in_comment_or_string():
            self.go_to_definition.emit(self.textCursor().position())

    def show_object_info(self, position):
        """Trigger a calltip"""
        self.sig_show_object_info.emit(position)

    # -----blank spaces
    def set_blanks_enabled(self, state):
        """Toggle blanks visibility"""
        self.blanks_enabled = state
        option = self.document().defaultTextOption()
        option.setFlags(option.flags() | \
                        QTextOption.AddSpaceForLineAndParagraphSeparators)
        if self.blanks_enabled:
            option.setFlags(option.flags() | QTextOption.ShowTabsAndSpaces)
        else:
            option.setFlags(option.flags() & ~QTextOption.ShowTabsAndSpaces)
        self.document().setDefaultTextOption(option)
        # Rehighlight to make the spaces less apparent.
        self.rehighlight()

    def set_scrollpastend_enabled(self, state):
        """
        Allow user to scroll past the end of the document to have the last
        line on top of the screen
        """
        self.scrollpastend_enabled = state
        self.setCenterOnScroll(state)
        self.setDocument(self.document())

    def resizeEvent(self, event):
        """Reimplemented Qt method to handle p resizing"""
        TextEditBaseWidget.resizeEvent(self, event)
        self.panels.resize()

    def showEvent(self, event):
        """Overrides showEvent to update the viewport margins."""
        super(CodeEditor, self).showEvent(event)
        self.panels.refresh()


    #-----Misc.
    def _apply_highlighter_color_scheme(self):
        """Apply color scheme from syntax highlighter to the editor"""
        hl = self.highlighter
        if hl is not None:
            self.set_palette(background=hl.get_background_color(),
                             foreground=hl.get_foreground_color())
            self.currentline_color = hl.get_currentline_color()
            self.currentcell_color = hl.get_currentcell_color()
            self.occurrence_color = hl.get_occurrence_color()
            self.ctrl_click_color = hl.get_ctrlclick_color()
            self.sideareas_color = hl.get_sideareas_color()
            self.comment_color = hl.get_comment_color()
            self.normal_color = hl.get_foreground_color()
            self.matched_p_color = hl.get_matched_p_color()
            self.unmatched_p_color = hl.get_unmatched_p_color()

            self.edge_line.update_color()
            self.indent_guides.update_color()

    def apply_highlighter_settings(self, color_scheme=None):
        """Apply syntax highlighter settings"""
        if self.highlighter is not None:
            # Updating highlighter settings (font and color scheme)
            self.highlighter.setup_formats(self.font())
            if color_scheme is not None:
                self.set_color_scheme(color_scheme)
            else:
                self.highlighter.rehighlight()

    def get_outlineexplorer_data(self):
        """Get data provided by the Outline Explorer"""
        return self.highlighter.get_outlineexplorer_data()

    def set_font(self, font, color_scheme=None):
        """Set font"""
        # Note: why using this method to set color scheme instead of
        #       'set_color_scheme'? To avoid rehighlighting the document twice
        #       at startup.
        if color_scheme is not None:
            self.color_scheme = color_scheme
        self.setFont(font)
        self.panels.refresh()
        self.apply_highlighter_settings(color_scheme)

    def set_color_scheme(self, color_scheme):
        """Set color scheme for syntax highlighting"""
        self.color_scheme = color_scheme
        if self.highlighter is not None:
            # this calls self.highlighter.rehighlight()
            self.highlighter.set_color_scheme(color_scheme)
            self._apply_highlighter_color_scheme()
        if self.highlight_current_cell_enabled:
            self.highlight_current_cell()
        else:
            self.unhighlight_current_cell()
        if self.highlight_current_line_enabled:
            self.highlight_current_line()
        else:
            self.unhighlight_current_line()

    def set_text(self, text):
        """Set the text of the editor"""
        self.setPlainText(text)
        self.set_eol_chars(text)
        #if self.supported_language:
            #self.highlighter.rehighlight()

    def set_text_from_file(self, filename, language=None):
        """Set the text of the editor from file *fname*"""
        text, _enc = encoding.read(filename)
        if language is None:
            language = get_file_language(filename, text)
        self.set_language(language, filename)
        self.set_text(text)

    def append(self, text):
        """Append text to the end of the text widget"""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)

    @Slot()
    def paste(self):
        """
        Reimplement QPlainTextEdit's method to fix the following issue:
        on Windows, pasted text has only 'LF' EOL chars even if the original
        text has 'CRLF' EOL chars
        """
        clipboard = QApplication.clipboard()
        text = to_text_string(clipboard.text())
        if len(text.splitlines()) > 1:
            eol_chars = self.get_line_separator()
            clipboard.setText( eol_chars.join((text+eol_chars).splitlines()) )
        # Standard paste
        TextEditBaseWidget.paste(self)

    def get_block_data(self, block):
        """Return block data (from syntax highlighter)"""
        return self.highlighter.block_data.get(block)

    def get_fold_level(self, block_nb):
        """Is it a fold header line?
        If so, return fold level
        If not, return None"""
        block = self.document().findBlockByNumber(block_nb)
        return self.get_block_data(block).fold_level


#===============================================================================
#    High-level editor features
#===============================================================================
    @Slot()
    def center_cursor_on_next_focus(self):
        """QPlainTextEdit's "centerCursor" requires the widget to be visible"""
        self.centerCursor()
        self.focus_in.disconnect(self.center_cursor_on_next_focus)

    def go_to_line(self, line, word=''):
        """Go to line number *line* and eventually highlight it"""
        self.text_helper.goto_line(line, move=True, word=word)

    def exec_gotolinedialog(self):
        """Execute the GoToLineDialog dialog box"""
        dlg = GoToLineDialog(self)
        if dlg.exec_():
            self.go_to_line(dlg.get_line_number())

    def cleanup_code_analysis(self):
        """Remove all code analysis markers"""
        self.setUpdatesEnabled(False)
        self.clear_extra_selections('code_analysis')
        for data in self.blockuserdata_list[:]:
            data.code_analysis = []
            if data.is_empty():
                del data
        self.setUpdatesEnabled(True)
        # When the new code analysis results are empty, it is necessary
        # to update manually the scrollflag and linenumber areas (otherwise,
        # the old flags will still be displayed):
        self.scrollflagarea.update()
        self.linenumberarea.update()

    def process_code_analysis(self, check_results):
        """Analyze filename code with pyflakes"""
        self.cleanup_code_analysis()
        if check_results is None:
            # Not able to compile module
            return
        self.setUpdatesEnabled(False)
        cursor = self.textCursor()
        document = self.document()
        flags = QTextDocument.FindCaseSensitively|QTextDocument.FindWholeWords
        for message, line_number in check_results:
            error = 'syntax' in message
            # Note: line_number start from 1 (not 0)
            block = self.document().findBlockByNumber(line_number-1)
            data = block.userData()
            if not data:
                data = BlockUserData(self)
            data.code_analysis.append( (message, error) )
            block.setUserData(data)
            refs = re.findall(r"\'[a-zA-Z0-9_]*\'", message)
            for ref in refs:
                # Highlighting found references
                text = ref[1:-1]
                # Scanning line number *line* and following lines if continued
                def is_line_splitted(line_no):
                    text = to_text_string(
                                document.findBlockByNumber(line_no).text())
                    stripped = text.strip()
                    return stripped.endswith('\\') or stripped.endswith(',') \
                           or len(stripped) == 0
                line2 = line_number-1
                while line2 < self.blockCount()-1 and is_line_splitted(line2):
                    line2 += 1
                cursor.setPosition(block.position())
                cursor.movePosition(QTextCursor.StartOfBlock)
                regexp = QRegExp(r"\b%s\b" % QRegExp.escape(text),
                                 Qt.CaseSensitive)
                color = self.error_color if error else self.warning_color
                # Highlighting all occurrences (this is a compromise as pyflakes
                # do not provide the column number -- see Issue 709 on Spyder's
                # GoogleCode project website)
                cursor = document.find(regexp, cursor, flags)
                if cursor:
                    while cursor and cursor.blockNumber() <= line2 \
                          and cursor.blockNumber() >= line_number-1 \
                          and cursor.position() > 0:
                        self.__highlight_selection('code_analysis', cursor,
                                       underline_color=QColor(color))
                        cursor = document.find(text, cursor, flags)
        self.update_extra_selections()
        self.setUpdatesEnabled(True)
        self.linenumberarea.update()
        self.classfuncdropdown.update()

    def show_code_analysis_results(self, line_number, code_analysis):
        """Show warning/error messages"""
        msglist = [ msg for msg, _error in code_analysis ]
        self.show_calltip(_("Code analysis"), msglist,
                          color='#129625', at_line=line_number)

    def go_to_next_warning(self):
        """Go to next code analysis warning message
        and return new cursor position"""
        block = self.textCursor().block()
        line_count = self.document().blockCount()
        while True:
            if block.blockNumber()+1 < line_count:
                block = block.next()
            else:
                block = self.document().firstBlock()
            data = block.userData()
            if data and data.code_analysis:
                break
        line_number = block.blockNumber()+1
        self.go_to_line(line_number)
        self.show_code_analysis_results(line_number, data.code_analysis)
        return self.get_position('cursor')

    def go_to_previous_warning(self):
        """Go to previous code analysis warning message
        and return new cursor position"""
        block = self.textCursor().block()
        while True:
            if block.blockNumber() > 0:
                block = block.previous()
            else:
                block = self.document().lastBlock()
            data = block.userData()
            if data and data.code_analysis:
                break
        line_number = block.blockNumber()+1
        self.go_to_line(line_number)
        self.show_code_analysis_results(line_number, data.code_analysis)
        return self.get_position('cursor')


    #------Tasks management
    def go_to_next_todo(self):
        """Go to next todo and return new cursor position"""
        block = self.textCursor().block()
        line_count = self.document().blockCount()
        while True:
            if block.blockNumber()+1 < line_count:
                block = block.next()
            else:
                block = self.document().firstBlock()
            data = block.userData()
            if data and data.todo:
                break
        line_number = block.blockNumber()+1
        self.go_to_line(line_number)
        self.show_calltip(_("To do"), data.todo,
                          color='#3096FC', at_line=line_number)
        return self.get_position('cursor')

    def process_todo(self, todo_results):
        """Process todo finder results"""
        for data in self.blockuserdata_list[:]:
            data.todo = ''
            if data.is_empty():
                del data
        for message, line_number in todo_results:
            block = self.document().findBlockByNumber(line_number-1)
            data = block.userData()
            if not data:
                data = BlockUserData(self)
            data.todo = message
            block.setUserData(data)
        self.scrollflagarea.update()


    #------Comments/Indentation
    def add_prefix(self, prefix):
        """Add prefix to current line or selected line(s)"""
        cursor = self.textCursor()
        if self.has_selected_text():
            # Add prefix to selected line(s)
            start_pos, end_pos = cursor.selectionStart(), cursor.selectionEnd()

            # Let's see if selection begins at a block start
            first_pos = min([start_pos, end_pos])
            first_cursor = self.textCursor()
            first_cursor.setPosition(first_pos)
            begins_at_block_start = first_cursor.atBlockStart()

            cursor.beginEditBlock()
            cursor.setPosition(end_pos)
            # Check if end_pos is at the start of a block: if so, starting
            # changes from the previous block
            if cursor.atBlockStart():
                cursor.movePosition(QTextCursor.PreviousBlock)
                if cursor.position() < start_pos:
                    cursor.setPosition(start_pos)

            while cursor.position() >= start_pos:
                cursor.movePosition(QTextCursor.StartOfBlock)
                if (self.get_character(cursor.position()) == ' '
                        and '#' in prefix):
                    cursor.movePosition(QTextCursor.NextWord)
                cursor.insertText(prefix)
                if start_pos == 0 and cursor.blockNumber() == 0:
                    # Avoid infinite loop when indenting the very first line
                    break
                cursor.movePosition(QTextCursor.PreviousBlock)
                cursor.movePosition(QTextCursor.EndOfBlock)
            cursor.endEditBlock()
            if begins_at_block_start:
                cursor.setPosition(start_pos, QTextCursor.MoveAnchor)
                cursor.setPosition(end_pos, QTextCursor.KeepAnchor)
                self.setTextCursor(cursor)
        else:
            # Add prefix to current line
            cursor.beginEditBlock()
            cursor.movePosition(QTextCursor.StartOfBlock)
            if self.get_character(cursor.position()) == ' ' and '#' in prefix:
                cursor.movePosition(QTextCursor.NextWord)
            cursor.insertText(prefix)
            cursor.endEditBlock()

    def __is_cursor_at_start_of_block(self, cursor):
        cursor.movePosition(QTextCursor.StartOfBlock)

    def remove_suffix(self, suffix):
        """
        Remove suffix from current line (there should not be any selection)
        """
        cursor = self.textCursor()
        cursor.setPosition(cursor.position()-len(suffix),
                           QTextCursor.KeepAnchor)
        if to_text_string(cursor.selectedText()) == suffix:
            cursor.removeSelectedText()

    def remove_prefix(self, prefix):
        """Remove prefix from current line or selected line(s)"""
        cursor = self.textCursor()
        if self.has_selected_text():
            # Remove prefix from selected line(s)
            start_pos, end_pos = sorted([cursor.selectionStart(),
                                         cursor.selectionEnd()])
            cursor.setPosition(start_pos)
            if not cursor.atBlockStart():
                cursor.movePosition(QTextCursor.StartOfBlock)
                start_pos = cursor.position()
            cursor.beginEditBlock()
            cursor.setPosition(end_pos)
            # Check if end_pos is at the start of a block: if so, starting
            # changes from the previous block
            if cursor.atBlockStart():
                cursor.movePosition(QTextCursor.PreviousBlock)
                if cursor.position() < start_pos:
                    cursor.setPosition(start_pos)

            cursor.movePosition(QTextCursor.StartOfBlock)
            old_pos = None
            while cursor.position() >= start_pos:
                new_pos = cursor.position()
                if old_pos == new_pos:
                    break
                else:
                    old_pos = new_pos
                line_text = to_text_string(cursor.block().text())
                self._remove_prefix(prefix, cursor, line_text)
                cursor.movePosition(QTextCursor.PreviousBlock)
            cursor.endEditBlock()
        else:
            # Remove prefix from current line
            cursor.movePosition(QTextCursor.StartOfBlock)
            line_text = to_text_string(cursor.block().text())
            self._remove_prefix(prefix, cursor, line_text)

    def _remove_prefix(self, prefix, cursor, line_text):
        """Handle the remove of the prefix for a single line."""
        start_with_space = line_text.startswith(' ')
        if start_with_space:
            left_spaces = self._even_number_of_spaces(line_text)
        else:
            left_spaces = False
        if start_with_space:
            right_number_spaces = self._number_of_spaces(line_text, group=1)
        else:
            right_number_spaces = self._number_of_spaces(line_text)
        # Handle prefix remove for comments with spaces
        if (prefix.strip() and line_text.lstrip().startswith(prefix + ' ')
                or line_text.startswith(prefix + ' ') and '#' in prefix):
            cursor.movePosition(QTextCursor.Right,
                                QTextCursor.MoveAnchor,
                                line_text.find(prefix))
            if right_number_spaces == 1 and (left_spaces
                                             or not start_with_space):
                # Handle inserted '# ' with the count of the number of spaces
                # at the right and left of the prefix.
                cursor.movePosition(QTextCursor.Right,
                                    QTextCursor.KeepAnchor, len(prefix + ' '))
            else:
                # Handle manual insertion of '#'
                cursor.movePosition(QTextCursor.Right,
                                    QTextCursor.KeepAnchor, len(prefix))
            cursor.removeSelectedText()
        # Check for prefix without space
        elif (prefix.strip() and line_text.lstrip().startswith(prefix)
                or line_text.startswith(prefix)):
            cursor.movePosition(QTextCursor.Right,
                                QTextCursor.MoveAnchor,
                                line_text.find(prefix))
            cursor.movePosition(QTextCursor.Right,
                                QTextCursor.KeepAnchor, len(prefix))
            cursor.removeSelectedText()

    def _even_number_of_spaces(self, line_text, group=0):
        """
        Get if there is a correct indentation from a group of spaces of a line.
        """
        spaces = re.findall('\s+', line_text)
        if len(spaces) - 1 >= group:
            return len(spaces[group]) % 4 == 0

    def _number_of_spaces(self, line_text, group=0):
        """Get the number of spaces from a group of spaces in a line."""
        spaces = re.findall('\s+', line_text)
        if len(spaces) - 1 >= group:
            return len(spaces[group])


    def fix_indent(self, *args, **kwargs):
        """Indent line according to the preferences"""
        if self.is_python_like():
            return self.fix_indent_smart(*args, **kwargs)
        else:
            return self.simple_indentation(*args, **kwargs)


    def simple_indentation(self, forward=True, **kwargs):
        """
        Simply preserve the indentation-level of the previous line.
        """
        cursor = self.textCursor()
        block_nb = cursor.blockNumber()
        prev_block = self.document().findBlockByLineNumber(block_nb-1)
        prevline = to_text_string(prev_block.text())

        indentation = re.match(r"\s*", prevline).group()
        # Unident
        if not forward:
            indentation = indentation[len(self.indent_chars):]

        cursor.insertText(indentation)
        return False  # simple indentation don't fix indentation


    def fix_indent_smart(self, forward=True, comment_or_string=False):
        """
        Fix indentation (Python only, no text selection)
        forward=True: fix indent only if text is not enough indented
                      (otherwise force indent)
        forward=False: fix indent only if text is too much indented
                       (otherwise force unindent)

        Returns True if indent needed to be fixed
        """
        cursor = self.textCursor()
        block_nb = cursor.blockNumber()
        # find the line that contains our scope
        diff_paren = 0
        diff_brack = 0
        diff_curly = 0
        add_indent = False
        prevline = None
        prevtext = ""
        for prevline in range(block_nb-1, -1, -1):
            cursor.movePosition(QTextCursor.PreviousBlock)
            prevtext = to_text_string(cursor.block().text()).rstrip()

            # Remove inline comment
            inline_comment = prevtext.find('#')
            if inline_comment != -1:
                prevtext = prevtext[:inline_comment]

            if ((self.is_python_like() and
               not prevtext.strip().startswith('#') and prevtext) or
               prevtext):

                if not "return" in prevtext.strip().split()[:1] and \
                    (prevtext.strip().endswith(')') or
                     prevtext.strip().endswith(']') or
                     prevtext.strip().endswith('}')):

                    comment_or_string = True  # prevent further parsing

                elif prevtext.strip().endswith(':') and self.is_python_like():
                    add_indent = True
                    comment_or_string = True
                if (prevtext.count(')') > prevtext.count('(')):
                    diff_paren = prevtext.count(')') - prevtext.count('(')
                elif (prevtext.count(']') > prevtext.count('[')):
                    diff_brack = prevtext.count(']') - prevtext.count('[')
                elif (prevtext.count('}') > prevtext.count('{')):
                    diff_curly = prevtext.count('}') - prevtext.count('{')
                elif diff_paren or diff_brack or diff_curly:
                    diff_paren += prevtext.count(')') - prevtext.count('(')
                    diff_brack += prevtext.count(']') - prevtext.count('[')
                    diff_curly += prevtext.count('}') - prevtext.count('{')
                    if not (diff_paren or diff_brack or diff_curly):
                        break
                else:
                    break

        if prevline:
            correct_indent = self.get_block_indentation(prevline)
        else:
            correct_indent = 0

        indent = self.get_block_indentation(block_nb)

        if add_indent:
            if self.indent_chars == '\t':
                correct_indent += self.tab_stop_width_spaces
            else:
                correct_indent += len(self.indent_chars)

        if not comment_or_string:
            if prevtext.endswith(':') and self.is_python_like():
                # Indent
                if self.indent_chars == '\t':
                    correct_indent += self.tab_stop_width_spaces
                else:
                    correct_indent += len(self.indent_chars)
            elif self.is_python_like() and \
                (prevtext.endswith('continue') or
                 prevtext.endswith('break') or
                 prevtext.endswith('pass') or
                 ("return" in prevtext.strip().split()[:1] and
                  len(re.split(r'\(|\{|\[', prevtext)) ==
                  len(re.split(r'\)|\}|\]', prevtext)))):
                # Unindent
                if self.indent_chars == '\t':
                    correct_indent -= self.tab_stop_width_spaces
                else:
                    correct_indent -= len(self.indent_chars)
            elif len(re.split(r'\(|\{|\[', prevtext)) > 1:

                # Check if all braces are matching using a stack
                stack = ['dummy']  # Dummy elemet to avoid index errors
                deactivate = None
                for c in prevtext:
                    if deactivate is not None:
                        if c == deactivate:
                            deactivate = None
                    elif c in ["'", '"']:
                        deactivate = c
                    elif c in ['(', '[','{']:
                        stack.append(c)
                    elif c == ')' and stack[-1] == '(':
                        stack.pop()
                    elif c == ']' and stack[-1] == '[':
                        stack.pop()
                    elif c == '}' and stack[-1] == '{':
                        stack.pop()

                if len(stack) == 1:  # all braces matching
                    pass

                # Hanging indent
                # find out if the last one is (, {, or []})
                # only if prevtext is long that the hanging indentation
                elif (re.search(r'[\(|\{|\[]\s*$', prevtext) is not None and
                      ((self.indent_chars == '\t' and
                        self.tab_stop_width_spaces * 2 < len(prevtext)) or
                       (self.indent_chars.startswith(' ') and
                        len(self.indent_chars) * 2 < len(prevtext)))):
                    if self.indent_chars == '\t':
                        correct_indent += self.tab_stop_width_spaces * 2
                    else:
                        correct_indent += len(self.indent_chars) * 2
                else:
                    rlmap = {")":"(", "]":"[", "}":"{"}
                    for par in rlmap:
                        i_right = prevtext.rfind(par)
                        if i_right != -1:
                            prevtext = prevtext[:i_right]
                            for _i in range(len(prevtext.split(par))):
                                i_left = prevtext.rfind(rlmap[par])
                                if i_left != -1:
                                    prevtext = prevtext[:i_left]
                                else:
                                    break
                    else:
                        if prevtext.strip():
                            if len(re.split(r'\(|\{|\[', prevtext)) > 1:
                                #correct indent only if there are still opening brackets
                                prevexpr = re.split(r'\(|\{|\[', prevtext)[-1]
                                correct_indent = len(prevtext)-len(prevexpr)
                            else:
                                correct_indent = len(prevtext)

        if not (diff_paren or diff_brack or diff_curly) and \
           not prevtext.endswith(':') and prevline:
            cur_indent = self.get_block_indentation(block_nb - 1)
            is_blank = not self.get_text_line(block_nb - 1).strip()
            prevline_indent = self.get_block_indentation(prevline)
            trailing_text = self.get_text_line(block_nb).strip()

            if cur_indent < prevline_indent and \
               (trailing_text or is_blank):
                if cur_indent % len(self.indent_chars) == 0:
                    correct_indent = cur_indent
                else:
                    correct_indent = cur_indent \
                                   + (len(self.indent_chars) -
                                      cur_indent % len(self.indent_chars))

        if (forward and indent >= correct_indent) or \
           (not forward and indent <= correct_indent):
            # No indentation fix is necessary
            return False

        if correct_indent >= 0:
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.StartOfBlock)
            if self.indent_chars == '\t':
                indent = indent // self.tab_stop_width_spaces
            cursor.setPosition(cursor.position()+indent, QTextCursor.KeepAnchor)
            cursor.removeSelectedText()
            if self.indent_chars == '\t':
                indent_text = '\t' * (correct_indent // self.tab_stop_width_spaces) \
                            + ' ' * (correct_indent % self.tab_stop_width_spaces)
            else:
                indent_text = ' '*correct_indent
            cursor.insertText(indent_text)
            return True

    @Slot()
    def clear_all_output(self):
        """Removes all ouput in the ipynb format (Json only)"""
        try:
            nb = nbformat.reads(self.toPlainText(), as_version=4)
            if nb.cells:
                for cell in nb.cells:
                    if 'outputs' in cell:
                        cell['outputs'] = []
                    if 'prompt_number' in cell:
                        cell['prompt_number'] = None
            # We do the following rather than using self.setPlainText
            # to benefit from QTextEdit's undo/redo feature.
            self.selectAll()
            self.insertPlainText(nbformat.writes(nb))
        except Exception as e:
            QMessageBox.critical(self, _('Removal error'),
                           _("It was not possible to remove outputs from "
                             "this notebook. The error is:\n\n") + \
                             to_text_string(e))
            return

    @Slot()
    def convert_notebook(self):
        """Convert an IPython notebook to a Python script in editor"""
        try:
            nb = nbformat.reads(self.toPlainText(), as_version=4)
            script = nbexporter().from_notebook_node(nb)[0]
        except Exception as e:
            QMessageBox.critical(self, _('Conversion error'),
                                 _("It was not possible to convert this "
                                 "notebook. The error is:\n\n") + \
                                 to_text_string(e))
            return
        self.sig_new_file.emit(script)

    def indent(self, force=False):
        """
        Indent current line or selection

        force=True: indent even if cursor is not a the beginning of the line
        """
        leading_text = self.get_text('sol', 'cursor')
        if self.has_selected_text():
            self.add_prefix(self.indent_chars)
        elif force or not leading_text.strip() \
             or (self.tab_indents and self.tab_mode):
            if self.is_python_like():
                if not self.fix_indent(forward=True):
                    self.add_prefix(self.indent_chars)
            else:
                self.add_prefix(self.indent_chars)
        else:
            if len(self.indent_chars) > 1:
                length = len(self.indent_chars)
                self.insert_text(" "*(length-(len(leading_text) % length)))
            else:
                self.insert_text(self.indent_chars)

    def indent_or_replace(self):
        """Indent or replace by 4 spaces depending on selection and tab mode"""
        if (self.tab_indents and self.tab_mode) or not self.has_selected_text():
            self.indent()
        else:
            cursor = self.textCursor()
            if self.get_selected_text() == \
               to_text_string(cursor.block().text()):
                self.indent()
            else:
                cursor1 = self.textCursor()
                cursor1.setPosition(cursor.selectionStart())
                cursor2 = self.textCursor()
                cursor2.setPosition(cursor.selectionEnd())
                if cursor1.blockNumber() != cursor2.blockNumber():
                    self.indent()
                else:
                    self.replace(self.indent_chars)

    def unindent(self, force=False):
        """
        Unindent current line or selection

        force=True: unindent even if cursor is not a the beginning of the line
        """
        if self.has_selected_text():
            self.remove_prefix(self.indent_chars)
        else:
            leading_text = self.get_text('sol', 'cursor')
            if force or not leading_text.strip() \
               or (self.tab_indents and self.tab_mode):
                if self.is_python_like():
                    if not self.fix_indent(forward=False):
                        self.remove_prefix(self.indent_chars)
                elif leading_text.endswith('\t'):
                    self.remove_prefix('\t')
                else:
                    self.remove_prefix(self.indent_chars)

    @Slot()
    def toggle_comment(self):
        """Toggle comment on current line or selection"""
        cursor = self.textCursor()
        start_pos, end_pos = sorted([cursor.selectionStart(),
                                     cursor.selectionEnd()])
        cursor.setPosition(end_pos)
        last_line = cursor.block().blockNumber()
        if cursor.atBlockStart() and start_pos != end_pos:
            last_line -= 1
        cursor.setPosition(start_pos)
        first_line = cursor.block().blockNumber()
        # If the selection contains only commented lines and surrounding
        # whitespace, uncomment. Otherwise, comment.
        is_comment_or_whitespace = True
        at_least_one_comment = False
        for _line_nb in range(first_line, last_line+1):
            text = to_text_string(cursor.block().text()).lstrip()
            is_comment = text.startswith(self.comment_string)
            is_whitespace = (text == '')
            is_comment_or_whitespace *= (is_comment or is_whitespace)
            if is_comment:
                at_least_one_comment = True
            cursor.movePosition(QTextCursor.NextBlock)
        if is_comment_or_whitespace and at_least_one_comment:
            self.uncomment()
        else:
            self.comment()

    def is_comment(self, block):
        """Detect inline comments.

        Return True if the block is an inline comment.
        """
        if block is None:
            return False
        text = to_text_string(block.text()).lstrip()
        return text.startswith(self.comment_string)

    def comment(self):
        """Comment current line or selection."""
        self.add_prefix(self.comment_string + ' ')

    def uncomment(self):
        """Uncomment current line or selection."""
        if not self.unblockcomment():
            self.remove_prefix(self.comment_string)

    def __blockcomment_bar(self):
        return self.comment_string + ' ' + '=' * (78 - len(self.comment_string))

    def transform_to_uppercase(self):
        """Change to uppercase current line or selection."""
        cursor = self.textCursor()
        prev_pos = cursor.position()
        selected_text = to_text_string(cursor.selectedText())

        if len(selected_text) == 0:
            prev_pos = cursor.position()
            cursor.select(QTextCursor.WordUnderCursor)
            selected_text = to_text_string(cursor.selectedText())

        s = selected_text.upper()
        cursor.insertText(s)
        self.set_cursor_position(prev_pos)

    def transform_to_lowercase(self):
        """Change to lowercase current line or selection."""
        cursor = self.textCursor()
        prev_pos = cursor.position()
        selected_text = to_text_string(cursor.selectedText())

        if len(selected_text) == 0:
            prev_pos = cursor.position()
            cursor.select(QTextCursor.WordUnderCursor)
            selected_text = to_text_string(cursor.selectedText())

        s = selected_text.lower()
        cursor.insertText(s)
        self.set_cursor_position(prev_pos)

    def blockcomment(self):
        """Block comment current line or selection."""
        comline = self.__blockcomment_bar() + self.get_line_separator()
        cursor = self.textCursor()
        if self.has_selected_text():
            self.extend_selection_to_complete_lines()
            start_pos, end_pos = cursor.selectionStart(), cursor.selectionEnd()
        else:
            start_pos = end_pos = cursor.position()
        cursor.beginEditBlock()
        cursor.setPosition(start_pos)
        cursor.movePosition(QTextCursor.StartOfBlock)
        while cursor.position() <= end_pos:
            cursor.insertText(self.comment_string + " ")
            cursor.movePosition(QTextCursor.EndOfBlock)
            if cursor.atEnd():
                break
            cursor.movePosition(QTextCursor.NextBlock)
            end_pos += len(self.comment_string + " ")
        cursor.setPosition(end_pos)
        cursor.movePosition(QTextCursor.EndOfBlock)
        if cursor.atEnd():
            cursor.insertText(self.get_line_separator())
        else:
            cursor.movePosition(QTextCursor.NextBlock)
        cursor.insertText(comline)
        cursor.setPosition(start_pos)
        cursor.movePosition(QTextCursor.StartOfBlock)
        cursor.insertText(comline)
        cursor.endEditBlock()

    def unblockcomment(self):
        """Un-block comment current line or selection"""
        def __is_comment_bar(cursor):
            return to_text_string(cursor.block().text()
                           ).startswith(self.__blockcomment_bar())
        # Finding first comment bar
        cursor1 = self.textCursor()
        if __is_comment_bar(cursor1):
            return
        while not __is_comment_bar(cursor1):
            cursor1.movePosition(QTextCursor.PreviousBlock)
            if cursor1.atStart():
                break
        if not __is_comment_bar(cursor1):
            return False
        def __in_block_comment(cursor):
            cs = self.comment_string
            return to_text_string(cursor.block().text()).startswith(cs)
        # Finding second comment bar
        cursor2 = QTextCursor(cursor1)
        cursor2.movePosition(QTextCursor.NextBlock)
        while not __is_comment_bar(cursor2) and __in_block_comment(cursor2):
            cursor2.movePosition(QTextCursor.NextBlock)
            if cursor2.block() == self.document().lastBlock():
                break
        if not __is_comment_bar(cursor2):
            return False
        # Removing block comment
        cursor3 = self.textCursor()
        cursor3.beginEditBlock()
        cursor3.setPosition(cursor1.position())
        cursor3.movePosition(QTextCursor.NextBlock)
        while cursor3.position() < cursor2.position():
            cursor3.movePosition(QTextCursor.NextCharacter,
                                 QTextCursor.KeepAnchor)
            if not cursor3.atBlockEnd():
                # standard commenting inserts '# ' but a trailing space on an
                # empty line might be stripped.
                cursor3.movePosition(QTextCursor.NextCharacter,
                                     QTextCursor.KeepAnchor)
            cursor3.removeSelectedText()
            cursor3.movePosition(QTextCursor.NextBlock)
        for cursor in (cursor2, cursor1):
            cursor3.setPosition(cursor.position())
            cursor3.select(QTextCursor.BlockUnderCursor)
            cursor3.removeSelectedText()
        cursor3.endEditBlock()

    #------Kill ring handlers
    # Taken from Jupyter's QtConsole
    # Copyright (c) 2001-2015, IPython Development Team
    # Copyright (c) 2015-, Jupyter Development Team
    def kill_line_end(self):
        """Kill the text on the current line from the cursor forward"""
        cursor = self.textCursor()
        cursor.clearSelection()
        cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
        if not cursor.hasSelection():
            # Line deletion
            cursor.movePosition(QTextCursor.NextBlock,
                                QTextCursor.KeepAnchor)
        self._kill_ring.kill_cursor(cursor)
        self.setTextCursor(cursor)

    def kill_line_start(self):
        """Kill the text on the current line from the cursor backward"""
        cursor = self.textCursor()
        cursor.clearSelection()
        cursor.movePosition(QTextCursor.StartOfBlock,
                            QTextCursor.KeepAnchor)
        self._kill_ring.kill_cursor(cursor)
        self.setTextCursor(cursor)

    def _get_word_start_cursor(self, position):
        """Find the start of the word to the left of the given position. If a
           sequence of non-word characters precedes the first word, skip over
           them. (This emulates the behavior of bash, emacs, etc.)
        """
        document = self.document()
        position -= 1
        while (position and not
               is_letter_or_number(document.characterAt(position))):
            position -= 1
        while position and is_letter_or_number(document.characterAt(position)):
            position -= 1
        cursor = self.textCursor()
        cursor.setPosition(position + 1)
        return cursor

    def _get_word_end_cursor(self, position):
        """Find the end of the word to the right of the given position. If a
           sequence of non-word characters precedes the first word, skip over
           them. (This emulates the behavior of bash, emacs, etc.)
        """
        document = self.document()
        cursor = self.textCursor()
        position = cursor.position()
        cursor.movePosition(QTextCursor.End)
        end = cursor.position()
        while (position < end and
               not is_letter_or_number(document.characterAt(position))):
            position += 1
        while (position < end and
               is_letter_or_number(document.characterAt(position))):
            position += 1
        cursor.setPosition(position)
        return cursor

    def kill_prev_word(self):
        """Kill the previous word"""
        position = self.textCursor().position()
        cursor = self._get_word_start_cursor(position)
        cursor.setPosition(position, QTextCursor.KeepAnchor)
        self._kill_ring.kill_cursor(cursor)
        self.setTextCursor(cursor)

    def kill_next_word(self):
        """Kill the next word"""
        position = self.textCursor().position()
        cursor = self._get_word_end_cursor(position)
        cursor.setPosition(position, QTextCursor.KeepAnchor)
        self._kill_ring.kill_cursor(cursor)
        self.setTextCursor(cursor)

    #------Autoinsertion of quotes/colons
    def __get_current_color(self, cursor=None):
        """Get the syntax highlighting color for the current cursor position"""
        if cursor is None:
            cursor = self.textCursor()

        block = cursor.block()
        pos = cursor.position() - block.position()  # relative pos within block
        layout = block.layout()
        block_formats = layout.additionalFormats()

        if block_formats:
            # To easily grab current format for autoinsert_colons
            if cursor.atBlockEnd():
                current_format = block_formats[-1].format
            else:
                current_format = None
                for fmt in block_formats:
                    if (pos >= fmt.start) and (pos < fmt.start + fmt.length):
                        current_format = fmt.format
                if current_format is None:
                    return None
            color = current_format.foreground().color().name()
            return color
        else:
            return None

    def in_comment_or_string(self, cursor=None):
        """Is the cursor inside or next to a comment or string?"""
        if self.highlighter:
            if cursor is None:
                current_color = self.__get_current_color()
            else:
                current_color = self.__get_current_color(cursor=cursor)

            comment_color = self.highlighter.get_color_name('comment')
            string_color = self.highlighter.get_color_name('string')
            if (current_color == comment_color) or (current_color == string_color):
                return True
            else:
                return False
        else:
            return False

    def __colon_keyword(self, text):
        stmt_kws = ['def', 'for', 'if', 'while', 'with', 'class', 'elif',
                    'except']
        whole_kws = ['else', 'try', 'except', 'finally']
        text = text.lstrip()
        words = text.split()
        if any([text == wk for wk in whole_kws]):
            return True
        elif len(words) < 2:
            return False
        elif any([words[0] == sk for sk in stmt_kws]):
            return True
        else:
            return False

    def __forbidden_colon_end_char(self, text):
        end_chars = [':', '\\', '[', '{', '(', ',']
        text = text.rstrip()
        if any([text.endswith(c) for c in end_chars]):
            return True
        else:
            return False

    def __unmatched_braces_in_line(self, text):
        block = self.textCursor().block()
        line_pos = block.position()
        for pos, char in enumerate(text):
            if char in ['(', '[', '{']:
                match = self.find_brace_match(line_pos+pos, char, forward=True)
                if (match is None) or (match > line_pos+len(text)):
                    return True
            if char in [')', ']', '}']:
                match = self.find_brace_match(line_pos+pos, char, forward=False)
                if (match is None) or (match < line_pos):
                    return True
        return False

    def __has_colon_not_in_brackets(self, text):
        """
        Return whether a string has a colon which is not between brackets.
        This function returns True if the given string has a colon which is
        not between a pair of (round, square or curly) brackets. It assumes
        that the brackets in the string are balanced.
        """
        for pos, char in enumerate(text):
            if char == ':' and not self.__unmatched_braces_in_line(text[:pos]):
                return True
        return False

    def autoinsert_colons(self):
        """Decide if we want to autoinsert colons"""
        line_text = self.get_text('sol', 'cursor')
        if not self.textCursor().atBlockEnd():
            return False
        elif self.in_comment_or_string():
            return False
        elif not self.__colon_keyword(line_text):
            return False
        elif self.__forbidden_colon_end_char(line_text):
            return False
        elif self.__unmatched_braces_in_line(line_text):
            return False
        elif self.__has_colon_not_in_brackets(line_text):
            return False
        else:
            return True

    def next_char(self):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.NextCharacter,
                            QTextCursor.KeepAnchor)
        next_char = to_text_string(cursor.selectedText())
        return next_char

    def in_comment(self):
        if self.highlighter:
            current_color = self.__get_current_color()
            comment_color = self.highlighter.get_color_name('comment')
            if current_color == comment_color:
                return True
            else:
                return False
        else:
            return False


#===============================================================================
#    Qt Event handlers
#===============================================================================
    def setup_context_menu(self):
        """Setup context menu"""
        self.undo_action = create_action(
            self, _("Undo"), icon=ima.icon('undo'),
            shortcut=get_shortcut('editor', 'undo'), triggered=self.undo)
        self.redo_action = create_action(
            self, _("Redo"), icon=ima.icon('redo'),
            shortcut=get_shortcut('editor', 'redo'), triggered=self.redo)
        self.cut_action = create_action(
            self, _("Cut"), icon=ima.icon('editcut'),
            shortcut=get_shortcut('editor', 'cut'), triggered=self.cut)
        self.copy_action = create_action(
            self, _("Copy"), icon=ima.icon('editcopy'),
            shortcut=get_shortcut('editor', 'copy'), triggered=self.copy)
        self.paste_action = create_action(
            self, _("Paste"), icon=ima.icon('editpaste'),
            shortcut=get_shortcut('editor', 'paste'), triggered=self.paste)
        selectall_action = create_action(
            self, _("Select All"), icon=ima.icon('selectall'),
            shortcut=get_shortcut('editor', 'select all'),
            triggered=self.selectAll)
        toggle_comment_action = create_action(
            self, _("Comment")+"/"+_("Uncomment"), icon=ima.icon('comment'),
            shortcut=get_shortcut('editor', 'toggle comment'),
            triggered=self.toggle_comment)
        self.clear_all_output_action = create_action(
            self, _("Clear all ouput"), icon=ima.icon('ipython_console'),
            triggered=self.clear_all_output)
        self.ipynb_convert_action = create_action(
            self, _("Convert to Python script"), icon=ima.icon('python'),
            triggered=self.convert_notebook)
        self.gotodef_action = create_action(
            self, _("Go to definition"),
            shortcut=get_shortcut('editor', 'go to definition'),
            triggered=self.go_to_definition_from_cursor)

        # Run actions
        self.run_cell_action = create_action(
            self, _("Run cell"), icon=ima.icon('run_cell'),
            shortcut=QKeySequence(RUN_CELL_SHORTCUT),
            triggered=self.run_cell.emit)
        self.run_cell_and_advance_action = create_action(
            self, _("Run cell and advance"), icon=ima.icon('run_cell'),
            shortcut=QKeySequence(RUN_CELL_AND_ADVANCE_SHORTCUT),
            triggered=self.run_cell_and_advance.emit)
        self.re_run_last_cell_action = create_action(
            self, _("Re-run last cell"), icon=ima.icon('run_cell'),
            shortcut=get_shortcut('editor', 're-run last cell'),
            triggered=self.re_run_last_cell.emit)
        self.run_selection_action = create_action(
            self, _("Run &selection or current line"),
            icon=ima.icon('run_selection'),
            shortcut=get_shortcut('editor', 'run selection'),
            triggered=self.run_selection.emit)

        # Zoom actions
        zoom_in_action = create_action(
            self, _("Zoom in"), icon=ima.icon('zoom_in'),
            shortcut=QKeySequence(QKeySequence.ZoomIn),
            triggered=self.zoom_in.emit)
        zoom_out_action = create_action(
            self, _("Zoom out"), icon=ima.icon('zoom_out'),
            shortcut=QKeySequence(QKeySequence.ZoomOut),
            triggered=self.zoom_out.emit)
        zoom_reset_action = create_action(
            self, _("Zoom reset"), shortcut=QKeySequence("Ctrl+0"),
            triggered=self.zoom_reset.emit)

        # Build menu
        self.menu = QMenu(self)
        actions_1 = [self.run_cell_action, self.run_cell_and_advance_action,
                     self.re_run_last_cell_action, self.run_selection_action,
                     self.gotodef_action, None, self.undo_action,
                     self.redo_action, None, self.cut_action,
                     self.copy_action, self.paste_action, selectall_action]
        actions_2 = [None, zoom_in_action, zoom_out_action, zoom_reset_action,
                     None, toggle_comment_action]
        if nbformat is not None:
            nb_actions = [self.clear_all_output_action,
                          self.ipynb_convert_action, None]
            actions = actions_1 + nb_actions + actions_2
            add_actions(self.menu, actions)
        else:
            actions = actions_1 + actions_2
            add_actions(self.menu, actions)

        # Read-only context-menu
        self.readonly_menu = QMenu(self)
        add_actions(self.readonly_menu,
                    (self.copy_action, None, selectall_action,
                     self.gotodef_action))

    def keyReleaseEvent(self, event):
        """Override Qt method."""
        self.timer_syntax_highlight.start()
        super(CodeEditor, self).keyReleaseEvent(event)
        event.ignore()

    def keyPressEvent(self, event):
        """Reimplement Qt method"""
        event.ignore()
        self.key_pressed.emit(event)
        key = event.key()
        ctrl = event.modifiers() & Qt.ControlModifier
        shift = event.modifiers() & Qt.ShiftModifier
        text = to_text_string(event.text())
        if text:
            self.__clear_occurrences()
        if QToolTip.isVisible():
            self.hide_tooltip_if_necessary(key)

        # Handle the Qt Builtin key sequences
        checks = [('SelectAll', 'Select All'),
                  ('Copy', 'Copy'),
                  ('Cut', 'Cut'),
                  ('Paste', 'Paste')]

        for qname, name in checks:
            seq = getattr(QKeySequence, qname)
            sc = get_shortcut('editor', name)
            default = QKeySequence(seq).toString()
            if event == seq and sc != default:
                # if we have overridden it, call our action
                for shortcut in self.shortcuts:
                    qsc, name, keystr = shortcut.data
                    if keystr == default:
                        qsc.activated.emit()
                        event.ignore()
                        return

                # otherwise, pass it on to parent
                event.ignore()
                return

        if key in (Qt.Key_Enter, Qt.Key_Return):
            if not shift and not ctrl:
                if self.add_colons_enabled and self.is_python_like() and \
                  self.autoinsert_colons():
                    self.textCursor().beginEditBlock()
                    self.insert_text(':' + self.get_line_separator())
                    self.fix_indent()
                    self.textCursor().endEditBlock()
                elif self.is_completion_widget_visible() \
                   and self.codecompletion_enter:
                    self.select_completion_list()
                else:
                    # Check if we're in a comment or a string at the
                    # current position
                    cmt_or_str_cursor = self.in_comment_or_string()

                    # Check if the line start with a comment or string
                    cursor = self.textCursor()
                    cursor.setPosition(cursor.block().position(),
                                       QTextCursor.KeepAnchor)
                    cmt_or_str_line_begin = self.in_comment_or_string(
                                                cursor=cursor)

                    # Check if we are in a comment or a string
                    cmt_or_str = cmt_or_str_cursor and cmt_or_str_line_begin

                    self.textCursor().beginEditBlock()
                    TextEditBaseWidget.keyPressEvent(self, event)
                    self.fix_indent(comment_or_string=cmt_or_str)
                    self.textCursor().endEditBlock()
            elif shift:
                self.run_cell_and_advance.emit()
            elif ctrl:
                self.run_cell.emit()
        elif shift and key == Qt.Key_Delete:
            # Shift + Del is a Key sequence reserved by most OSes
            # https://github.com/spyder-ide/spyder/issues/3405
            self.delete_line()
        elif key == Qt.Key_Insert and not shift and not ctrl:
            self.setOverwriteMode(not self.overwriteMode())
        elif key == Qt.Key_Backspace and not shift and not ctrl:
            leading_text = self.get_text('sol', 'cursor')
            leading_length = len(leading_text)
            trailing_spaces = leading_length-len(leading_text.rstrip())
            if self.has_selected_text() or not self.intelligent_backspace:
                TextEditBaseWidget.keyPressEvent(self, event)
            else:
                trailing_text = self.get_text('cursor', 'eol')
                if not leading_text.strip() \
                   and leading_length > len(self.indent_chars):
                    if leading_length % len(self.indent_chars) == 0:
                        self.unindent()
                    else:
                        TextEditBaseWidget.keyPressEvent(self, event)
                elif trailing_spaces and not trailing_text.strip():
                    self.remove_suffix(leading_text[-trailing_spaces:])
                elif leading_text and trailing_text and \
                     leading_text[-1]+trailing_text[0] in ('()', '[]', '{}',
                                                           '\'\'', '""'):
                    cursor = self.textCursor()
                    cursor.movePosition(QTextCursor.PreviousCharacter)
                    cursor.movePosition(QTextCursor.NextCharacter,
                                        QTextCursor.KeepAnchor, 2)
                    cursor.removeSelectedText()
                else:
                    TextEditBaseWidget.keyPressEvent(self, event)
                    if self.is_completion_widget_visible():
                        self.completion_text = self.completion_text[:-1]
        elif key == Qt.Key_Period:
            self.insert_text(text)
            if (self.is_python_like()) and not \
              self.in_comment_or_string() and self.codecompletion_auto:
                # Enable auto-completion only if last token isn't a float
                last_obj = getobj(self.get_text('sol', 'cursor'))
                if last_obj and not last_obj.isdigit():
                    self.do_completion(automatic=True)
        elif key == Qt.Key_Home:
            self.stdkey_home(shift, ctrl)
        elif key == Qt.Key_End:
            # See Issue 495: on MacOS X, it is necessary to redefine this
            # basic action which should have been implemented natively
            self.stdkey_end(shift, ctrl)
        elif text == '(' and not self.has_selected_text():
            self.hide_completion_widget()
            self.handle_parentheses(text)
        elif (text in ('[', '{') and not self.has_selected_text() and
              self.close_parentheses_enabled):
            s_trailing_text = self.get_text('cursor', 'eol').strip()
            if len(s_trailing_text) == 0 or \
               s_trailing_text[0] in (',', ')', ']', '}'):
                self.insert_text({'{': '{}', '[': '[]'}[text])
                cursor = self.textCursor()
                cursor.movePosition(QTextCursor.PreviousCharacter)
                self.setTextCursor(cursor)
            else:
                TextEditBaseWidget.keyPressEvent(self, event)
        elif key in (Qt.Key_ParenRight, Qt.Key_BraceRight, Qt.Key_BracketRight)\
          and not self.has_selected_text() and self.close_parentheses_enabled \
          and not self.textCursor().atBlockEnd():
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.NextCharacter,
                                QTextCursor.KeepAnchor)
            text = to_text_string(cursor.selectedText())
            if text == {Qt.Key_ParenRight: ')', Qt.Key_BraceRight: '}',
                        Qt.Key_BracketRight: ']'}[key]:
                cursor.clearSelection()
                self.setTextCursor(cursor)
            else:
                TextEditBaseWidget.keyPressEvent(self, event)
        elif key == Qt.Key_Colon and not self.has_selected_text() \
             and self.auto_unindent_enabled:
            leading_text = self.get_text('sol', 'cursor')
            if leading_text.lstrip() in ('else', 'finally'):
                ind = lambda txt: len(txt)-len(txt.lstrip())
                prevtxt = to_text_string(self.textCursor(
                                                ).block().previous().text())
                if ind(leading_text) == ind(prevtxt):
                    self.unindent(force=True)
            TextEditBaseWidget.keyPressEvent(self, event)
        elif key == Qt.Key_Space and not shift and not ctrl \
             and not self.has_selected_text() and self.auto_unindent_enabled:
            leading_text = self.get_text('sol', 'cursor')
            if leading_text.lstrip() in ('elif', 'except'):
                ind = lambda txt: len(txt)-len(txt.lstrip())
                prevtxt = to_text_string(self.textCursor(
                                                ).block().previous().text())
                if ind(leading_text) == ind(prevtxt):
                    self.unindent(force=True)
            TextEditBaseWidget.keyPressEvent(self, event)
        elif key == Qt.Key_Tab:
            # Important note: <TAB> can't be called with a QShortcut because
            # of its singular role with respect to widget focus management
            if not self.has_selected_text() and not self.tab_mode:
                self.intelligent_tab()
            else:
                # indent the selected text
                self.indent_or_replace()
        elif key == Qt.Key_Backtab:
            # Backtab, i.e. Shift+<TAB>, could be treated as a QShortcut but
            # there is no point since <TAB> can't (see above)
            if not self.has_selected_text() and not self.tab_mode:
                self.intelligent_backtab()
            else:
                # indent the selected text
                self.unindent()
        elif not event.isAccepted():
            TextEditBaseWidget.keyPressEvent(self, event)
            if self.is_completion_widget_visible() and text:
                self.completion_text += text
        # Accept event to avoid it being handled by the parent
        event.accept()

    def run_pygments_highlighter(self):
        """Run pygments highlighter."""
        if isinstance(self.highlighter, sh.PygmentsSH):
            self.highlighter.make_charlist()

    def handle_parentheses(self, text):
        """Handle left and right parenthesis depending on editor config."""
        position = self.get_position('cursor')
        rest = self.get_text('cursor', 'eol').rstrip()
        valid = not rest or rest[0] in (',', ')', ']', '}')
        if self.close_parentheses_enabled and valid:
            self.insert_text('()')
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.PreviousCharacter)
            self.setTextCursor(cursor)
        else:
            self.insert_text(text)
        if self.is_python_like() and self.get_text('sol', 'cursor') and \
                self.calltips:
            self.sig_show_object_info.emit(position)

    def mouseMoveEvent(self, event):
        """Underline words when pressing <CONTROL>"""
        if self.has_selected_text():
            TextEditBaseWidget.mouseMoveEvent(self, event)
            return
        if self.go_to_definition_enabled and \
           event.modifiers() & Qt.ControlModifier:
            text = self.get_word_at(event.pos())
            if text and (self.is_python_like())\
               and not sourcecode.is_keyword(to_text_string(text)):
                if not self.__cursor_changed:
                    QApplication.setOverrideCursor(
                                                QCursor(Qt.PointingHandCursor))
                    self.__cursor_changed = True
                cursor = self.cursorForPosition(event.pos())
                cursor.select(QTextCursor.WordUnderCursor)
                self.clear_extra_selections('ctrl_click')
                self.__highlight_selection('ctrl_click', cursor, update=True,
                                foreground_color=self.ctrl_click_color,
                                underline_color=self.ctrl_click_color,
                                underline_style=QTextCharFormat.SingleUnderline)
                event.accept()
                return
        if self.__cursor_changed:
            QApplication.restoreOverrideCursor()
            self.__cursor_changed = False
            self.clear_extra_selections('ctrl_click')
        TextEditBaseWidget.mouseMoveEvent(self, event)

    def setPlainText(self, txt):
        """
        Extends setPlainText to emit the new_text_set signal.

        :param txt: The new text to set.
        :param mime_type: Associated mimetype. Setting the mime will update the
                          pygments lexer.
        :param encoding: text encoding
        """
        super(CodeEditor, self).setPlainText(txt)
        self.new_text_set.emit()

    def leaveEvent(self, event):
        """If cursor has not been restored yet, do it now"""
        if self.__cursor_changed:
            QApplication.restoreOverrideCursor()
            self.__cursor_changed = False
            self.clear_extra_selections('ctrl_click')
        TextEditBaseWidget.leaveEvent(self, event)

    @Slot()
    def go_to_definition_from_cursor(self, cursor=None):
        """Go to definition from cursor instance (QTextCursor)"""
        if not self.go_to_definition_enabled:
            return
        if cursor is None:
            cursor = self.textCursor()
        if self.in_comment_or_string():
            return
        position = cursor.position()
        text = to_text_string(cursor.selectedText())
        if len(text) == 0:
            cursor.select(QTextCursor.WordUnderCursor)
            text = to_text_string(cursor.selectedText())
        if not text is None:
            self.go_to_definition.emit(position)

    def mousePressEvent(self, event):
        """Reimplement Qt method"""
        if event.button() == Qt.LeftButton\
           and (event.modifiers() & Qt.ControlModifier):
            TextEditBaseWidget.mousePressEvent(self, event)
            cursor = self.cursorForPosition(event.pos())
            self.go_to_definition_from_cursor(cursor)
        else:
            TextEditBaseWidget.mousePressEvent(self, event)

    def contextMenuEvent(self, event):
        """Reimplement Qt method"""
        nonempty_selection = self.has_selected_text()
        self.copy_action.setEnabled(nonempty_selection)
        self.cut_action.setEnabled(nonempty_selection)
        self.clear_all_output_action.setVisible(self.is_json() and \
                                                nbformat is not None)
        self.ipynb_convert_action.setVisible(self.is_json() and \
                                             nbformat is not None)
        self.run_cell_action.setVisible(self.is_python())
        self.run_cell_and_advance_action.setVisible(self.is_python())
        self.run_selection_action.setVisible(self.is_python())
        self.re_run_last_cell_action.setVisible(self.is_python())
        self.gotodef_action.setVisible(self.go_to_definition_enabled \
                                       and self.is_python_like())

        # Code duplication go_to_definition_from_cursor and mouse_move_event
        cursor = self.textCursor()
        text = to_text_string(cursor.selectedText())
        if len(text) == 0:
            cursor.select(QTextCursor.WordUnderCursor)
            text = to_text_string(cursor.selectedText())

        self.undo_action.setEnabled( self.document().isUndoAvailable())
        self.redo_action.setEnabled( self.document().isRedoAvailable())
        menu = self.menu
        if self.isReadOnly():
            menu = self.readonly_menu
        menu.popup(event.globalPos())
        event.accept()

    #------ Drag and drop
    def dragEnterEvent(self, event):
        """Reimplement Qt method
        Inform Qt about the types of data that the widget accepts"""
        if mimedata2url(event.mimeData()):
            # Let the parent widget handle this
            event.ignore()
        else:
            TextEditBaseWidget.dragEnterEvent(self, event)

    def dropEvent(self, event):
        """Reimplement Qt method
        Unpack dropped data and handle it"""
        if mimedata2url(event.mimeData()):
            # Let the parent widget handle this
            event.ignore()
        else:
            TextEditBaseWidget.dropEvent(self, event)

    #------ Paint event
    def paintEvent(self, event):
        """Overrides paint event to update the list of visible blocks"""
        self.update_visible_blocks(event)
        TextEditBaseWidget.paintEvent(self, event)
        self.painted.emit(event)

    def update_visible_blocks(self, event):
        """Update the list of visible blocks/lines position"""
        self.__visible_blocks[:] = []
        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(
            self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        ebottom_top = 0
        ebottom_bottom = self.height()

        while block.isValid():
            visible = bottom <= ebottom_bottom
            if not visible:
                break
            if block.isVisible():
                self.__visible_blocks.append((top, blockNumber+1, block))
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            blockNumber = block.blockNumber()

    def _draw_editor_cell_divider(self):
        """Draw a line on top of a define cell"""
        if self.supported_cell_language:
            cell_line_color = self.comment_color
            painter = QPainter(self.viewport())
            pen = painter.pen()
            pen.setStyle(Qt.SolidLine)
            pen.setBrush(cell_line_color)
            painter.setPen(pen)

            for top, line_number, block in self.visible_blocks:
                if self.is_cell_separator(block):
                    painter.drawLine(4, top, self.width(), top)

    @property
    def visible_blocks(self):
        """
        Returns the list of visible blocks.

        Each element in the list is a tuple made up of the line top position,
        the line number (already 1 based), and the QTextBlock itself.

        :return: A list of tuple(top position, line number, block)
        :rtype: List of tuple(int, int, QtGui.QTextBlock)
        """
        return self.__visible_blocks

    def is_editor(self):
        return True


#===============================================================================
# CodeEditor's Printer
#===============================================================================

#TODO: Implement the header and footer support
class Printer(QPrinter):
    def __init__(self, mode=QPrinter.ScreenResolution, header_font=None):
        QPrinter.__init__(self, mode)
        self.setColorMode(QPrinter.Color)
        self.setPageOrder(QPrinter.FirstPageFirst)
        self.date = time.ctime()
        if header_font is not None:
            self.header_font = header_font

    # <!> The following method is simply ignored by QPlainTextEdit
    #     (this is a copy from QsciEditor's Printer)
    def formatPage(self, painter, drawing, area, pagenr):
        header = '%s - %s - Page %s' % (self.docName(), self.date, pagenr)
        painter.save()
        painter.setFont(self.header_font)
        painter.setPen(QColor(Qt.black))
        if drawing:
            painter.drawText(area.right()-painter.fontMetrics().width(header),
                             area.top()+painter.fontMetrics().ascent(), header)
        area.setTop(area.top()+painter.fontMetrics().height()+5)
        painter.restore()


#===============================================================================
# Editor + Class browser test
#===============================================================================
class TestWidget(QSplitter):
    def __init__(self, parent):
        QSplitter.__init__(self, parent)
        self.editor = CodeEditor(self)
        self.editor.setup_editor(linenumbers=True, markers=True, tab_mode=False,
                                 font=QFont("Courier New", 10),
                                 show_blanks=True, color_scheme='Zenburn')
        self.addWidget(self.editor)
        from spyder.widgets.editortools import OutlineExplorerWidget
        self.classtree = OutlineExplorerWidget(self)
        self.addWidget(self.classtree)
        self.classtree.edit_goto.connect(
                    lambda _fn, line, word: self.editor.go_to_line(line, word))
        self.setStretchFactor(0, 4)
        self.setStretchFactor(1, 1)
        self.setWindowIcon(ima.icon('spyder'))
 
    def load(self, filename):
        self.editor.set_text_from_file(filename)
        self.setWindowTitle("%s - %s (%s)" % (_("Editor"),
                                              osp.basename(filename),
                                              osp.dirname(filename)))
        self.classtree.set_current_editor(self.editor, filename, False, False)


def test(fname):
    from spyder.utils.qthelpers import qapplication
    app = qapplication(test_time=5)
    win = TestWidget(None)
    win.show()
    win.load(fname)
    win.resize(900, 700)

    from spyder.utils.codeanalysis import (check_with_pyflakes,
                                           check_with_pep8)
    source_code = to_text_string(win.editor.toPlainText())
    results = check_with_pyflakes(source_code, fname) + \
              check_with_pep8(source_code, fname)
    win.editor.process_code_analysis(results)

    sys.exit(app.exec_())


if __name__ == '__main__':
    if len(sys.argv) > 1:
        fname = sys.argv[1]
    else:
        fname = __file__
    test(fname)
