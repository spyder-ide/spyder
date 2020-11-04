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
from __future__ import division, print_function

from unicodedata import category
import logging
import os.path as osp
import re
import sre_constants
import sys
import textwrap
import time

# Third party imports
from three_merge import merge
from diff_match_patch import diff_match_patch
from qtpy.compat import to_qvariant
from qtpy.QtCore import (QEvent, QPoint, QRegExp, Qt, QTimer, QThread, QUrl,
                         Signal, Slot)
from qtpy.QtGui import (QColor, QCursor, QFont, QIntValidator,
                        QKeySequence, QPaintEvent, QPainter, QMouseEvent,
                        QTextCharFormat, QTextCursor, QDesktopServices,
                        QKeyEvent, QTextDocument, QTextFormat, QTextOption,
                        QTextFrameFormat)
from qtpy.QtPrintSupport import QPrinter
from qtpy.QtWidgets import (QApplication, QDialog, QDialogButtonBox,
                            QGridLayout, QHBoxLayout, QLabel,
                            QLineEdit, QMenu, QMessageBox, QSplitter,
                            QToolTip, QVBoxLayout, QScrollBar)
from spyder_kernels.utils.dochelpers import getobj

# %% This line is for cell execution testing


# Local imports
from spyder.api.panel import Panel
from spyder.config.base import _, get_debug_level, running_under_pytest
from spyder.config.manager import CONF
from spyder.plugins.editor.api.decoration import TextDecoration
from spyder.plugins.editor.extensions import (CloseBracketsExtension,
                                              CloseQuotesExtension,
                                              DocstringWriterExtension,
                                              QMenuOnlyForEnter,
                                              EditorExtensionsManager,
                                              SnippetsExtension)
from spyder.plugins.completion.kite.widgets.calltoaction import (
    KiteCallToAction)
from spyder.plugins.completion.manager.api import (LSPRequestTypes,
                                                   TextDocumentSyncKind,
                                                   DiagnosticSeverity)
from spyder.plugins.editor.panels import (ClassFunctionDropdown,
                                          DebuggerPanel, EdgeLine,
                                          FoldingPanel, IndentationGuide,
                                          LineNumberArea, PanelsManager,
                                          ScrollFlagArea)
from spyder.plugins.editor.utils.editor import (TextHelper, BlockUserData)
from spyder.plugins.editor.utils.debugger import DebuggerManager
# from spyder.plugins.editor.utils.folding import IndentFoldDetector, FoldScope
from spyder.plugins.editor.utils.kill_ring import QtKillRing
from spyder.plugins.editor.utils.languages import ALL_LANGUAGES, CELL_LANGUAGES
from spyder.plugins.completion.manager.decorators import (
    request, handles, class_register)
from spyder.plugins.editor.widgets.base import TextEditBaseWidget
from spyder.plugins.outlineexplorer.languages import PythonCFM
from spyder.plugins.outlineexplorer.api import (OutlineExplorerData as OED,
                                                is_cell_header)
from spyder.py3compat import PY2, to_text_string, is_string, is_text_string
from spyder.utils import encoding, programs, sourcecode
from spyder.utils import icon_manager as ima
from spyder.utils import syntaxhighlighters as sh
from spyder.utils.qthelpers import (add_actions, create_action, file_uri,
                                    mimedata2url)
from spyder.utils.vcs import get_git_remotes, remote_to_url
from spyder.utils.qstringhelpers import qstring_length
from spyder.widgets.helperwidgets import MessageCheckBox

try:
    import nbformat as nbformat
    from nbconvert import PythonExporter as nbexporter
except Exception:
    nbformat = None  # analysis:ignore

logger = logging.getLogger(__name__)

# Timeout to update decorations (through a QTimer) when a position
# changed is detected in the vertical scrollbar or when releasing
# the up/down arrow keys.
UPDATE_DECORATIONS_TIMEOUT = 500  # miliseconds

# %% This line is for cell execution testing
def is_letter_or_number(char):
    """Returns whether the specified unicode character is a letter or a number.
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
        glayout.addWidget(label, 0, 0, Qt.AlignVCenter | Qt.AlignRight)
        glayout.addWidget(self.lineedit, 0, 1, Qt.AlignVCenter)
        glayout.addWidget(cl_label, 1, 0, Qt.AlignVCenter | Qt.AlignRight)
        glayout.addWidget(cl_label_v, 1, 1, Qt.AlignVCenter)
        glayout.addWidget(last_label, 2, 0, Qt.AlignVCenter | Qt.AlignRight)
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


@class_register
class CodeEditor(TextEditBaseWidget):
    """Source Code Editor Widget based exclusively on Qt"""

    LANGUAGES = {
        'Python': (sh.PythonSH, '#', PythonCFM),
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
        # Every other language
        'None': (sh.TextSH, '', None),
    }

    TAB_ALWAYS_INDENTS = ('py', 'pyw', 'python', 'c', 'cpp', 'cl', 'h')

    # Custom signal to be emitted upon completion of the editor's paintEvent
    painted = Signal(QPaintEvent)

    # To have these attrs when early viewportEvent's are triggered
    edge_line = None
    indent_guides = None

    sig_breakpoints_changed = Signal()
    sig_debug_stop = Signal((int,), ())
    sig_debug_start = Signal()
    sig_breakpoints_saved = Signal()
    sig_filename_changed = Signal(str)
    sig_bookmarks_changed = Signal()
    get_completions = Signal(bool)
    go_to_definition = Signal(str, int, int)
    sig_show_object_info = Signal(int)
    sig_run_selection = Signal()
    sig_run_cell_and_advance = Signal()
    sig_run_cell = Signal()
    sig_re_run_last_cell = Signal()
    sig_debug_cell = Signal()
    go_to_definition_regex = Signal(str, int, int)
    sig_cursor_position_changed = Signal(int, int)
    sig_new_file = Signal(str)
    sig_refresh_formatting = Signal(bool)

    #: Signal emitted when the editor loses focus
    sig_focus_changed = Signal()

    #: Signal emitted when a key is pressed
    sig_key_pressed = Signal(QKeyEvent)

    #: Signal emitted when a key is released
    sig_key_released = Signal(QKeyEvent)

    #: Signal emitted when the alt key is pressed and the left button of the
    #  mouse is clicked
    sig_alt_left_mouse_pressed = Signal(QMouseEvent)

    #: Signal emitted when the alt key is pressed and the cursor moves over
    #  the editor
    sig_alt_mouse_moved = Signal(QMouseEvent)

    #: Signal emitted when the cursor leaves the editor
    sig_leave_out = Signal()

    #: Signal emitted when the flags need to be updated in the scrollflagarea
    sig_flags_changed = Signal()

    #: Signal emitted when the syntax color theme of the editor.
    sig_theme_colors_changed = Signal(dict)

    #: Signal emitted when a new text is set on the widget
    new_text_set = Signal()

    # -- LSP signals
    #: Signal emitted when an LSP request is sent to the LSP manager
    sig_perform_completion_request = Signal(str, str, dict)

    #: Signal emitted when a response is received from an LSP server
    # For now it's only used on tests, but it could be used to track
    # and profile LSP diagnostics.
    lsp_response_signal = Signal(str, object)

    #: Signal to display object information on the Help plugin
    sig_display_object_info = Signal(str, bool)

    #: Signal only used for tests
    # TODO: Remove it!
    sig_signature_invoked = Signal(dict)

    #: Signal emmited when processing code analysis warnings is finished
    sig_process_code_analysis = Signal()

    # Used for testing. When the mouse moves with Ctrl/Cmd pressed and
    # a URI is found, this signal is emmited
    sig_uri_found = Signal(str)

    # Used for testing. When the mouse moves with Ctrl/Cmd pressed and
    # the mouse left button is pressed, this signal is emmited
    sig_go_to_uri = Signal(str)

    sig_file_uri_preprocessed = Signal(str)
    """
    This signal is emitted when the go to uri for a file has been
    preprocessed.

    Parameters
    ----------
    fpath: str
        The preprocessed file path.
    """

    # Signal with the info about the current completion item documentation
    # str: object name
    # str: object signature/documentation
    # bool: force showing the info
    sig_show_completion_object_info = Signal(str, str, bool)

    # Used to indicate if text was inserted into the editor
    sig_text_was_inserted = Signal()

    # Used to indicate that text will be inserted into the editor
    sig_will_insert_text = Signal(str)

    # Used to indicate that a text selection will be removed
    sig_will_remove_selection = Signal(tuple, tuple)

    # Used to indicate that text will be pasted
    sig_will_paste_text = Signal(str)

    # Used to indicate that an undo operation will take place
    sig_undo = Signal()

    # Used to indicate that an undo operation will take place
    sig_redo = Signal()

    # Used to start the status spinner in the editor
    sig_start_operation_in_progress = Signal()

    # Used to start the status spinner in the editor
    sig_stop_operation_in_progress = Signal()

    def __init__(self, parent=None):
        TextEditBaseWidget.__init__(self, parent)

        self.setFocusPolicy(Qt.StrongFocus)

        # Projects
        self.current_project_path = None

        # Caret (text cursor)
        self.setCursorWidth( CONF.get('main', 'cursor/width') )

        self.text_helper = TextHelper(self)

        self._panels = PanelsManager(self)

        # Mouse moving timer / Hover hints handling
        # See: mouseMoveEvent
        self.tooltip_widget.sig_help_requested.connect(
            self.show_object_info)
        self.tooltip_widget.sig_completion_help_requested.connect(
            self.show_completion_object_info)
        self._last_point = None
        self._last_hover_word = None
        self._last_hover_cursor = None
        self._timer_mouse_moving = QTimer(self)
        self._timer_mouse_moving.setInterval(350)
        self._timer_mouse_moving.setSingleShot(True)
        self._timer_mouse_moving.timeout.connect(self._handle_hover)

        # Typing keys / handling on the fly completions
        # See: keyPressEvent
        self._last_key_pressed_text = ''
        self._last_pressed_key = None
        self._timer_autocomplete = QTimer(self)
        self._timer_autocomplete.setSingleShot(True)
        self._timer_autocomplete.timeout.connect(self._handle_completions)

        # Handle completions hints
        self._completions_hint_idle = False
        self._timer_completions_hint = QTimer(self)
        self._timer_completions_hint.setSingleShot(True)
        self._timer_completions_hint.timeout.connect(
            self._set_completions_hint_idle)
        self.completion_widget.sig_completion_hint.connect(
            self.show_hint_for_completion)

        # Goto uri
        self._last_hover_pattern_key = None
        self._last_hover_pattern_text = None

        # 79-col edge line
        self.edge_line = self.panels.register(EdgeLine(self),
                                              Panel.Position.FLOATING)

        # indent guides
        self.indent_guides = self.panels.register(IndentationGuide(self),
                                                  Panel.Position.FLOATING)
        # Blanks enabled
        self.blanks_enabled = False

        # Underline errors and warnings
        self.underline_errors_enabled = False

        # Scrolling past the end of the document
        self.scrollpastend_enabled = False

        self.background = QColor('white')

        # Folding
        self.panels.register(FoldingPanel())

        # Debugger panel (Breakpoints)
        self.debugger = DebuggerManager(self)
        self.panels.register(DebuggerPanel())
        # Update breakpoints if the number of lines in the file changes
        self.blockCountChanged.connect(self.debugger.update_breakpoints)

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

        # Vertical scrollbar
        # This is required to avoid a "RuntimeError: no access to protected
        # functions or signals for objects not created from Python" in
        # Linux Ubuntu. See spyder-ide/spyder#5215.
        self.setVerticalScrollBar(QScrollBar())

        # Highlights and flag colors
        self.warning_color = "#FFAD07"
        self.error_color = "#EA2B0E"
        self.todo_color = "#B4D4F3"
        self.breakpoint_color = "#30E62E"
        self.occurrence_color = QColor(Qt.yellow).lighter(160)
        self.found_results_color = QColor(Qt.magenta).lighter(180)

        # Scrollbar flag area
        self.scrollflagarea = self.panels.register(ScrollFlagArea(self),
                                                   Panel.Position.RIGHT)
        self.panels.refresh()

        self.document_id = id(self)

        # Indicate occurrences of the selected word
        self.cursorPositionChanged.connect(self.__cursor_position_changed)
        self.__find_first_pos = None
        self.__find_flags = None

        self.language = None
        self.supported_language = False
        self.supported_cell_language = False
        self.classfunc_match = None
        self.comment_string = None
        self._kill_ring = QtKillRing(self)

        # Block user data
        self.blockCountChanged.connect(self.update_bookmarks)

        # Highlight using Pygments highlighter timer
        # ---------------------------------------------------------------------
        # For files that use the PygmentsSH we parse the full file inside
        # the highlighter in order to generate the correct coloring.
        self.timer_syntax_highlight = QTimer(self)
        self.timer_syntax_highlight.setSingleShot(True)
        self.timer_syntax_highlight.timeout.connect(
            self.run_pygments_highlighter)

        # Mark occurrences timer
        self.occurrence_highlighting = None
        self.occurrence_timer = QTimer(self)
        self.occurrence_timer.setSingleShot(True)
        self.occurrence_timer.setInterval(1500)
        self.occurrence_timer.timeout.connect(self.__mark_occurrences)
        self.occurrences = []

        # Update decorations
        self.update_decorations_timer = QTimer(self)
        self.update_decorations_timer.setSingleShot(True)
        self.update_decorations_timer.setInterval(UPDATE_DECORATIONS_TIMEOUT)
        self.update_decorations_timer.timeout.connect(
            self.update_decorations)
        self.verticalScrollBar().valueChanged.connect(
            lambda value: self.update_decorations_timer.start())

        # Mark found results
        self.textChanged.connect(self.__text_has_changed)
        self.found_results = []

        # Docstring
        self.writer_docstring = DocstringWriterExtension(self)

        # Context menu
        self.gotodef_action = None
        self.setup_context_menu()

        # Tab key behavior
        self.tab_indents = None
        self.tab_mode = True  # see CodeEditor.set_tab_mode

        # Intelligent backspace mode
        self.intelligent_backspace = True

        # Automatic (on the fly) completions
        self.automatic_completions = True
        self.automatic_completions_after_chars = 3
        self.automatic_completions_after_ms = 300

        # Code Folding
        self.code_folding = True

        # Completions hint
        self.completions_hint = True
        self.completions_hint_after_ms = 500

        self.close_parentheses_enabled = True
        self.close_quotes_enabled = False
        self.add_colons_enabled = True
        self.auto_unindent_enabled = True

        # Autoformat on save
        self.format_on_save = False

        # Mouse tracking
        self.setMouseTracking(True)
        self.__cursor_changed = False
        self._mouse_left_button_pressed = False
        self.ctrl_click_color = QColor(Qt.blue)

        self.bookmarks = self.get_bookmarks()

        # Keyboard shortcuts
        self.shortcuts = self.create_shortcuts()

        # Paint event
        self.__visible_blocks = []  # Visible blocks, update with repaint
        self.painted.connect(self._draw_editor_cell_divider)

        # Outline explorer
        self.oe_proxy = None

        # Line stripping
        self.last_change_position = None
        self.last_position = None
        self.last_auto_indent = None
        self.skip_rstrip = False
        self.strip_trailing_spaces_on_modify = True

        # Hover hints
        self.hover_hints_enabled = None

        # Language Server
        self.lsp_requests = {}
        self.filename = None
        self.completions_available = False
        self.text_version = 0
        self.save_include_text = True
        self.open_close_notifications = True
        self.sync_mode = TextDocumentSyncKind.FULL
        self.will_save_notify = False
        self.will_save_until_notify = False
        self.enable_hover = True
        self.auto_completion_characters = []
        self.signature_completion_characters = []
        self.go_to_definition_enabled = False
        self.find_references_enabled = False
        self.highlight_enabled = False
        self.formatting_enabled = False
        self.range_formatting_enabled = False
        self.document_symbols_enabled = False
        self.formatting_characters = []
        self.rename_support = False
        self.completion_args = None
        self.folding_supported = False
        self.is_cloned = False
        self.operation_in_progress = False
        self._diagnostics = []

        # Editor Extensions
        self.editor_extensions = EditorExtensionsManager(self)
        self.editor_extensions.add(CloseQuotesExtension())
        self.editor_extensions.add(SnippetsExtension())
        self.editor_extensions.add(CloseBracketsExtension())

        # Text diffs across versions
        self.differ = diff_match_patch()
        self.previous_text = ''
        self.word_tokens = []
        self.patch = []
        self.text_diff = ([], '')
        self.leading_whitespaces = {}

        # re-use parent of completion_widget (usually the main window)
        completion_parent = self.completion_widget.parent()
        self.kite_call_to_action = KiteCallToAction(self, completion_parent)

        # Some events should not be triggered during undo/redo
        # such as line stripping
        self.is_undoing = False
        self.is_redoing = False

    # --- Helper private methods
    # ------------------------------------------------------------------------

    # --- Hover/Hints
    def _should_display_hover(self, point):
        """Check if a hover hint should be displayed:"""
        if not self._mouse_left_button_pressed:
            return (self.hover_hints_enabled and point
                    and self.get_word_at(point))

    def _handle_hover(self):
        """Handle hover hint trigger after delay."""
        self._timer_mouse_moving.stop()
        pos = self._last_point

        # These are textual characters but should not trigger a completion
        # FIXME: update per language
        ignore_chars = ['(', ')', '.']

        if self._should_display_hover(pos):
            key, pattern_text, cursor = self.get_pattern_at(pos)
            text = self.get_word_at(pos)
            if pattern_text:
                ctrl_text = 'Cmd' if sys.platform == "darwin" else 'Ctrl'
                if key in ['file']:
                    hint_text = ctrl_text + ' + ' + _('click to open file')
                elif key in ['mail']:
                    hint_text = ctrl_text + ' + ' + _('click to send email')
                elif key in ['url']:
                    hint_text = ctrl_text + ' + ' + _('click to open url')
                else:
                    hint_text = ctrl_text + ' + ' + _('click to open')

                hint_text = '<span>&nbsp;{}&nbsp;</span>'.format(hint_text)

                self.show_tooltip(text=hint_text, at_point=pos)
                return

            cursor = self.cursorForPosition(pos)
            cursor_offset = cursor.position()
            line, col = cursor.blockNumber(), cursor.columnNumber()
            self._last_point = pos
            if text and self._last_hover_word != text:
                if all(char not in text for char in ignore_chars):
                    self._last_hover_word = text
                    self.request_hover(line, col, cursor_offset)
                else:
                    self.hide_tooltip()
        elif not self.is_completion_widget_visible():
            self.hide_tooltip()

    def blockuserdata_list(self):
        """Get the list of all user data in document."""
        block = self.document().firstBlock()
        while block.isValid():
            data = block.userData()
            if data:
                yield data
            block = block.next()

    def outlineexplorer_data_list(self):
        """Get the list of all user data in document."""
        for data in self.blockuserdata_list():
            if data.oedata:
                yield data.oedata

    # ---- Keyboard Shortcuts

    def create_cursor_callback(self, attr):
        """Make a callback for cursor move event type, (e.g. "Start")"""
        def cursor_move_event():
            cursor = self.textCursor()
            move_type = getattr(QTextCursor, attr)
            cursor.movePosition(move_type)
            self.setTextCursor(cursor)
        return cursor_move_event

    def create_shortcuts(self):
        """Create the local shortcuts for the CodeEditor."""
        shortcut_context_name_callbacks = (
            ('editor', 'code completion', self.do_completion),
            ('editor', 'duplicate line down', self.duplicate_line_down),
            ('editor', 'duplicate line up', self.duplicate_line_up),
            ('editor', 'delete line', self.delete_line),
            ('editor', 'move line up', self.move_line_up),
            ('editor', 'move line down', self.move_line_down),
            ('editor', 'go to new line', self.go_to_new_line),
            ('editor', 'go to definition', self.go_to_definition_from_cursor),
            ('editor', 'toggle comment', self.toggle_comment),
            ('editor', 'blockcomment', self.blockcomment),
            ('editor', 'unblockcomment', self.unblockcomment),
            ('editor', 'transform to uppercase', self.transform_to_uppercase),
            ('editor', 'transform to lowercase', self.transform_to_lowercase),
            ('editor', 'indent', lambda: self.indent(force=True)),
            ('editor', 'unindent', lambda: self.unindent(force=True)),
            ('editor', 'start of line',
             self.create_cursor_callback('StartOfLine')),
            ('editor', 'end of line',
             self.create_cursor_callback('EndOfLine')),
            ('editor', 'previous line', self.create_cursor_callback('Up')),
            ('editor', 'next line', self.create_cursor_callback('Down')),
            ('editor', 'previous char', self.create_cursor_callback('Left')),
            ('editor', 'next char', self.create_cursor_callback('Right')),
            ('editor', 'previous word',
             self.create_cursor_callback('PreviousWord')),
            ('editor', 'next word', self.create_cursor_callback('NextWord')),
            ('editor', 'kill to line end', self.kill_line_end),
            ('editor', 'kill to line start', self.kill_line_start),
            ('editor', 'yank', self._kill_ring.yank),
            ('editor', 'rotate kill ring', self._kill_ring.rotate),
            ('editor', 'kill previous word', self.kill_prev_word),
            ('editor', 'kill next word', self.kill_next_word),
            ('editor', 'start of document',
             self.create_cursor_callback('Start')),
            ('editor', 'end of document',
             self.create_cursor_callback('End')),
            ('editor', 'undo', self.undo),
            ('editor', 'redo', self.redo),
            ('editor', 'cut', self.cut),
            ('editor', 'copy', self.copy),
            ('editor', 'paste', self.paste),
            ('editor', 'delete', self.delete),
            ('editor', 'select all', self.selectAll),
            ('editor', 'docstring',
             self.writer_docstring.write_docstring_for_shortcut),
            ('editor', 'autoformatting', self.format_document_or_range),
            ('array_builder', 'enter array inline', self.enter_array_inline),
            ('array_builder', 'enter array table', self.enter_array_table)
            )

        shortcuts = []
        for context, name, callback in shortcut_context_name_callbacks:
            shortcuts.append(
                CONF.config_shortcut(
                    callback, context=context, name=name, parent=self))
        return shortcuts

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

    def get_document_id(self):
        return self.document_id

    def set_as_clone(self, editor):
        """Set as clone editor"""
        self.setDocument(editor.document())
        self.document_id = editor.get_document_id()
        self.highlighter = editor.highlighter
        self.eol_chars = editor.eol_chars
        self._apply_highlighter_color_scheme()

    # ---- Widget setup and options
    def toggle_wrap_mode(self, enable):
        """Enable/disable wrap mode"""
        self.set_wrap_mode('word' if enable else None)

    def toggle_line_numbers(self, linenumbers=True, markers=False):
        """Enable/disable line numbers."""
        self.linenumberarea.setup_margins(linenumbers, markers)

    @property
    def panels(self):
        """
        Returns a reference to the
        :class:`spyder.widgets.panels.managers.PanelsManager`
        used to manage the collection of installed panels
        """
        return self._panels

    def setup_editor(self,
                     linenumbers=True,
                     language=None,
                     markers=False,
                     font=None,
                     color_scheme=None,
                     wrap=False,
                     tab_mode=True,
                     strip_mode=False,
                     intelligent_backspace=True,
                     automatic_completions=True,
                     automatic_completions_after_chars=3,
                     automatic_completions_after_ms=300,
                     completions_hint=True,
                     completions_hint_after_ms=500,
                     hover_hints=True,
                     code_snippets=True,
                     highlight_current_line=True,
                     highlight_current_cell=True,
                     occurrence_highlighting=True,
                     scrollflagarea=True,
                     edge_line=True,
                     edge_line_columns=(79,),
                     show_blanks=False,
                     underline_errors=False,
                     close_parentheses=True,
                     close_quotes=False,
                     add_colons=True,
                     auto_unindent=True,
                     indent_chars=" "*4,
                     tab_stop_width_spaces=4,
                     cloned_from=None,
                     filename=None,
                     occurrence_timeout=1500,
                     show_class_func_dropdown=False,
                     indent_guides=False,
                     scroll_past_end=False,
                     show_debug_panel=True,
                     folding=True,
                     remove_trailing_spaces=False,
                     remove_trailing_newlines=False,
                     add_newline=False,
                     format_on_save=False):
        """
        Set-up configuration for the CodeEditor instance.

        Usually the parameters here are related with a configurable preference
        in the Preference Dialog and Editor configurations:

        linenumbers: Enable/Disable line number panel. Default True.
        language: Set editor language for example python. Default None.
        markers: Enable/Disable markers panel. Used to show elements like
            Code Analysis. Default False.
        font: Base font for the Editor to use. Default None.
        color_scheme: Initial color scheme for the Editor to use. Default None.
        wrap: Enable/Disable line wrap. Default False.
        tab_mode: Enable/Disable using Tab as delimiter between word,
            Default True.
        strip_mode: strip_mode: Enable/Disable striping trailing spaces when
            modifying the file. Default False.
        intelligent_backspace: Enable/Disable automatically unindenting
            inserted text (unindenting happens if the leading text length of
            the line isn't module of the length of indentation chars being use)
            Default True.
        automatic_completions: Enable/Disable automatic completions.
            The behavior of the trigger of this the completions can be
            established with the two following kwargs. Default True.
        automatic_completions_after_chars: Number of charts to type to trigger
            an automatic completion. Default 3.
        automatic_completions_after_ms: Number of milliseconds to pass before
            an autocompletion is triggered. Default 300.
        completions_hint: Enable/Disable documentation hints for completions.
            Default True.
        completions_hint_after_ms: Number of milliseconds over a completion
            item to show the documentation hint. Default 500.
        hover_hints: Enable/Disable documentation hover hints. Default True.
        code_snippets: Enable/Disable code snippets completions. Default True.
        highlight_current_line: Enable/Disable current line highlighting.
            Default True.
        highlight_current_cell: Enable/Disable current cell highlighting.
            Default True.
        occurrence_highlighting: Enable/Disable highlighting of current word
            occurrence in the file. Default True.
        scrollflagarea : Enable/Disable flag area that shows at the left of
            the scroll bar. Default True.
        edge_line: Enable/Disable vertical line to show max number of
            characters per line. Customizable number of columns in the
            following kwarg. Default True.
        edge_line_columns: Number of columns/characters where the editor
            horizontal edge line will show. Default (79,).
        show_blanks: Enable/Disable blanks highlighting. Default False.
        underline_errors: Enable/Disable showing and underline to highlight
            errors. Default False.
        close_parentheses: Enable/Disable automatic parentheses closing
            insertion. Default True.
        close_quotes: Enable/Disable automatic closing of quotes.
            Default False.
        add_colons: Enable/Disable automatic addition of colons. Default True.
        auto_unindent: Enable/Disable automatically unindentation before else,
            elif, finally or except statements. Default True.
        indent_chars: Characters to use for indentation. Default " "*4.
        tab_stop_width_spaces: Enable/Disable using tabs for indentation.
            Default 4.
        cloned_from: Editor instance used as template to instantiate this
            CodeEditor instance. Default None.
        filename: Initial filename to show. Default None.
        occurrence_timeout : Timeout in milliseconds to start highlighting
            matches/occurrences for the current word under the cursor.
            Default 1500 ms.
        show_class_func_dropdown: Enable/Disable a Matlab like widget to show
            classes and functions available in the current file. Default False.
        indent_guides: Enable/Disable highlighting of code indentation.
            Default False.
        scroll_past_end: Enable/Disable possibility to scroll file passed
            its end. Default False.
        show_debug_panel: Enable/Disable debug panel. Default True.
        folding: Enable/Disable code folding. Default True.
        remove_trailing_spaces: Remove trailing whitespaces on lines.
            Default False.
        remove_trailing_newlines: Remove extra lines at the end of the file.
            Default False.
        add_newline: Add a newline at the end of the file if there is not one.
            Default False.
        format_on_save: Autoformat file automatically when saving.
            Default False.
        """

        self.set_close_parentheses_enabled(close_parentheses)
        self.set_close_quotes_enabled(close_quotes)
        self.set_add_colons_enabled(add_colons)
        self.set_auto_unindent_enabled(auto_unindent)
        self.set_indent_chars(indent_chars)

        # Show/hide the debug panel depending on the language and parameter
        self.set_debug_panel(show_debug_panel, language)

        # Show/hide folding panel depending on parameter
        self.toggle_code_folding(folding)

        # Scrollbar flag area
        self.scrollflagarea.set_enabled(scrollflagarea)

        # Debugging
        self.debugger.set_filename(filename)

        # Edge line
        self.edge_line.set_enabled(edge_line)
        self.edge_line.set_columns(edge_line_columns)

        # Indent guides
        self.toggle_identation_guides(indent_guides)
        if self.indent_chars == '\t':
            self.indent_guides.set_indentation_width(self.tab_stop_width_spaces)
        else:
            self.indent_guides.set_indentation_width(len(self.indent_chars))

        # Blanks
        self.set_blanks_enabled(show_blanks)

        # Remove trailing whitespaces
        self.set_remove_trailing_spaces(remove_trailing_spaces)

        # Remove trailing newlines
        self.set_remove_trailing_newlines(remove_trailing_newlines)

        # Add newline at the end
        self.set_add_newline(add_newline)

        # Scrolling past the end
        self.set_scrollpastend_enabled(scroll_past_end)

        # Line number area and indent guides
        if cloned_from:
            self.setFont(font) # this is required for line numbers area
            # Needed to show indent guides for splited editor panels
            # See spyder-ide/spyder#10900
            self.patch = cloned_from.patch
            self.is_cloned = True
        self.toggle_line_numbers(linenumbers, markers)

        # Lexer
        self.filename = filename
        self.set_language(language, filename)

        # Underline errors and warnings
        self.set_underline_errors_enabled(underline_errors)

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

        # Automatic completions
        self.toggle_automatic_completions(automatic_completions)
        self.set_automatic_completions_after_chars(
            automatic_completions_after_chars)
        self.set_automatic_completions_after_ms(automatic_completions_after_ms)

        # Completions hint
        self.toggle_completions_hint(completions_hint)
        self.set_completions_hint_after_ms(completions_hint_after_ms)

        # Hover hints
        self.toggle_hover_hints(hover_hints)

        # Code snippets
        self.toggle_code_snippets(code_snippets)

        # Autoformat on save
        self.toggle_format_on_save(format_on_save)

        if cloned_from is not None:
            self.set_as_clone(cloned_from)
            self.panels.refresh()
        elif font is not None:
            self.set_font(font, color_scheme)
        elif color_scheme is not None:
            self.set_color_scheme(color_scheme)

        # Set tab spacing after font is set
        self.set_tab_stop_width_spaces(tab_stop_width_spaces)

        self.toggle_wrap_mode(wrap)

        # Class/Function dropdown will be disabled if we're not in a Python file.
        self.classfuncdropdown.setVisible(show_class_func_dropdown
                                          and self.is_python_like())

        self.set_strip_mode(strip_mode)

    # --- Language Server Protocol methods -----------------------------------
    # ------------------------------------------------------------------------
    @Slot(str, dict)
    def handle_response(self, method, params):
        if method in self.handler_registry:
            handler_name = self.handler_registry[method]
            handler = getattr(self, handler_name)
            handler(params)
            # This signal is only used on tests.
            # It could be used to track and profile LSP diagnostics.
            self.lsp_response_signal.emit(method, params)

    def emit_request(self, method, params, requires_response):
        """Send request to LSP manager."""
        params['requires_response'] = requires_response
        params['response_instance'] = self
        self.sig_perform_completion_request.emit(
            self.language.lower(), method, params)

    def log_lsp_handle_errors(self, message):
        """
        Log errors when handling LSP responses.

        This works when debugging is on or off.
        """
        if get_debug_level() > 0:
            # We log the error normally when running on debug mode.
            logger.error(message, exc_info=True)
        else:
            # We need this because logger.error activates our error
            # report dialog but it doesn't show the entire traceback
            # there. So we intentionally leave an error in this call
            # to get the entire stack info generated by it, which
            # gives the info we need from users.
            if PY2:
                logger.error(message, exc_info=True)
                print(message, file=sys.stderr)
            else:
                logger.error('%', 1, stack_info=True)

    # ------------- LSP: Configuration and protocol start/end ----------------
    def start_completion_services(self):
        """Start completion services for this instance."""
        self.completions_available = True

        if self.is_cloned:
            additional_msg = " cloned editor"
        else:
            additional_msg = ""
            self.document_did_open()

        logger.debug(u"Completion services available for{0}: {1}".format(
            additional_msg, self.filename))

    def register_completion_capabilities(self, capabilities):
        """
        Register completion server capabilities.

        Parameters
        ----------
        capabilities: dict
            Capabilities supported by a language server.
        """
        sync_options = capabilities['textDocumentSync']
        completion_options = capabilities['completionProvider']
        signature_options = capabilities['signatureHelpProvider']
        range_formatting_options = (
            capabilities['documentOnTypeFormattingProvider'])
        self.open_close_notifications = sync_options.get('openClose', False)
        self.sync_mode = sync_options.get('change', TextDocumentSyncKind.NONE)
        self.will_save_notify = sync_options.get('willSave', False)
        self.will_save_until_notify = sync_options.get('willSaveWaitUntil',
                                                       False)
        self.save_include_text = sync_options['save']['includeText']
        self.enable_hover = capabilities['hoverProvider']
        self.folding_supported = capabilities.get(
            'foldingRangeProvider', False)
        self.auto_completion_characters = (
            completion_options['triggerCharacters'])
        self.signature_completion_characters = (
            signature_options['triggerCharacters'] + ['='])  # FIXME:
        self.go_to_definition_enabled = capabilities['definitionProvider']
        self.find_references_enabled = capabilities['referencesProvider']
        self.highlight_enabled = capabilities['documentHighlightProvider']
        self.formatting_enabled = capabilities['documentFormattingProvider']
        self.range_formatting_enabled = (
            capabilities['documentRangeFormattingProvider'])
        self.document_symbols_enabled = (
            capabilities['documentSymbolProvider']
        )
        self.formatting_characters.append(
            range_formatting_options['firstTriggerCharacter'])
        self.formatting_characters += (
            range_formatting_options.get('moreTriggerCharacter', []))

        if self.formatting_enabled:
            self.format_action.setEnabled(True)
            self.sig_refresh_formatting.emit(True)

        self.completions_available = True

    def stop_completion_services(self):
        logger.debug('Stopping completion services for %s' % self.filename)
        self.completions_available = False

    @request(method=LSPRequestTypes.DOCUMENT_DID_OPEN, requires_response=False)
    def document_did_open(self):
        """Send textDocument/didOpen request to the server."""
        cursor = self.textCursor()
        params = {
            'file': self.filename,
            'language': self.language,
            'version': self.text_version,
            'text': self.toPlainText(),
            'codeeditor': self,
            'offset': cursor.position(),
            'selection_start': cursor.selectionStart(),
            'selection_end': cursor.selectionEnd(),
        }
        return params

    # ------------- LSP: Symbols ---------------------------------------
    @request(method=LSPRequestTypes.DOCUMENT_SYMBOL)
    def request_symbols(self):
        """Request document symbols."""
        if not self.document_symbols_enabled:
            return
        if self.oe_proxy is not None:
            self.oe_proxy.emit_request_in_progress()
        params = {'file': self.filename}
        return params

    @handles(LSPRequestTypes.DOCUMENT_SYMBOL)
    def process_symbols(self, params):
        """Handle symbols response."""
        try:
            symbols = params['params']
            symbols = [] if symbols is None else symbols
            self.classfuncdropdown.update_data(symbols)
            if self.oe_proxy is not None:
                self.oe_proxy.update_outline_info(symbols)
        except RuntimeError:
            # This is triggered when a codeeditor instance was removed
            # before the response can be processed.
            return
        except Exception:
            self.log_lsp_handle_errors("Error when processing symbols")

    # ------------- LSP: Linting ---------------------------------------
    @request(
        method=LSPRequestTypes.DOCUMENT_DID_CHANGE, requires_response=False)
    def document_did_change(self, text=None):
        """Send textDocument/didChange request to the server."""
        self.text_version += 1
        text = self.toPlainText()
        self.patch = self.differ.patch_make(self.previous_text, text)
        self.previous_text = text
        cursor = self.textCursor()
        params = {
            'file': self.filename,
            'version': self.text_version,
            'text': text,
            'diff': self.patch,
            'offset': cursor.position(),
            'selection_start': cursor.selectionStart(),
            'selection_end': cursor.selectionEnd(),
        }
        return params

    @handles(LSPRequestTypes.DOCUMENT_PUBLISH_DIAGNOSTICS)
    def process_diagnostics(self, params):
        """Handle linting response."""
        try:
            # The LSP spec doesn't require that folding and symbols
            # are treated in the same way as linting, i.e. to be
            # recomputed on didChange, didOpen and didSave. However,
            # we think that's necessary to maintain accurate folding
            # and symbols all the time. Therefore, we decided to add
            # these requests here.
            self.request_folding()

            # Tests don't pass with this request here.
            if not running_under_pytest():
                self.request_symbols()

            self.process_code_analysis(params['params'])
        except RuntimeError:
            # This is triggered when a codeeditor instance was removed
            # before the response can be processed.
            return
        except Exception:
            self.log_lsp_handle_errors("Error when processing linting")

    # ------------- LSP: Completion ---------------------------------------
    @request(method=LSPRequestTypes.DOCUMENT_COMPLETION)
    def do_completion(self, automatic=False):
        """Trigger completion."""
        cursor = self.textCursor()
        current_word = self.get_current_word(
            completion=True,
            valid_python_variable=False
        )

        params = {
            'file': self.filename,
            'line': cursor.blockNumber(),
            'column': cursor.columnNumber(),
            'offset': cursor.position(),
            'selection_start': cursor.selectionStart(),
            'selection_end': cursor.selectionEnd(),
            'current_word': current_word
        }
        self.completion_args = (self.textCursor().position(), automatic)
        return params

    @handles(LSPRequestTypes.DOCUMENT_COMPLETION)
    def process_completion(self, params):
        """Handle completion response."""
        args = self.completion_args
        if args is None:
            # This should not happen
            return
        self.completion_args = None
        position, automatic = args

        start_cursor = self.textCursor()
        start_cursor.movePosition(QTextCursor.StartOfBlock)
        line_text = self.get_text(start_cursor.position(), 'eol')
        leading_whitespace = self.compute_whitespace(line_text)
        indentation_whitespace = ' ' * leading_whitespace
        eol_char = self.get_line_separator()

        try:
            completions = params['params']
            completions = ([] if completions is None else
                           [completion for completion in completions
                            if completion.get('insertText')
                            or completion.get('textEdit', {}).get('newText')])
            prefix = self.get_current_word(completion=True,
                                           valid_python_variable=False)
            if (len(completions) == 1
                    and completions[0].get('insertText') == prefix
                    and not completions[0].get('textEdit', {}).get('newText')):
                completions.pop()

            replace_end = self.textCursor().position()
            under_cursor = self.get_current_word_and_position(completion=True)
            if under_cursor:
                word, replace_start = under_cursor
            else:
                word = ''
                replace_start = replace_end
            first_letter = ''
            if len(word) > 0:
                first_letter = word[0]

            def sort_key(completion):
                if 'textEdit' in completion:
                    text_insertion =  completion['textEdit']['newText']
                else:
                    text_insertion = completion['insertText']
                first_insert_letter = text_insertion[0]
                case_mismatch = (
                    (first_letter.isupper() and first_insert_letter.islower())
                    or
                    (first_letter.islower() and first_insert_letter.isupper())
                )
                # False < True, so case matches go first
                return (case_mismatch, completion['sortText'])

            completion_list = sorted(completions, key=sort_key)

            # Allow for textEdit completions to be filtered by Spyder
            # if on-the-fly completions are disabled, only if the
            # textEdit range matches the word under the cursor.
            for completion in completion_list:
                if 'textEdit' in completion:
                    c_replace_start = completion['textEdit']['range']['start']
                    c_replace_end = completion['textEdit']['range']['end']
                    if (c_replace_start == replace_start
                            and c_replace_end == replace_end):
                        insert_text = completion['textEdit']['newText']
                        completion['filterText'] = insert_text
                        completion['insertText'] = insert_text
                        del completion['textEdit']

                if 'insertText' in completion:
                    insert_text = completion['insertText']
                    insert_text_lines = insert_text.splitlines()
                    reindented_text = [insert_text_lines[0]]
                    for insert_line in insert_text_lines[1:]:
                        insert_line = indentation_whitespace + insert_line
                        reindented_text.append(insert_line)
                    reindented_text = eol_char.join(reindented_text)
                    completion['insertText'] = reindented_text

            self.completion_widget.show_list(
                completion_list, position, automatic)

            self.kite_call_to_action.handle_processed_completions(completions)
        except RuntimeError:
            # This is triggered when a codeeditor instance was removed
            # before the response can be processed.
            self.kite_call_to_action.hide_coverage_cta()
            return
        except Exception:
            self.log_lsp_handle_errors('Error when processing completions')

    # ------------- LSP: Signature Hints ------------------------------------
    @request(method=LSPRequestTypes.DOCUMENT_SIGNATURE)
    def request_signature(self):
        """Ask for signature."""
        self.document_did_change('')
        line, column = self.get_cursor_line_column()
        offset = self.get_position('cursor')
        params = {
            'file': self.filename,
            'line': line,
            'column': column,
            'offset': offset
        }
        return params

    @handles(LSPRequestTypes.DOCUMENT_SIGNATURE)
    def process_signatures(self, params):
        """Handle signature response."""
        try:
            signature_params = params['params']

            if (signature_params is not None and
                    'activeParameter' in signature_params):
                self.sig_signature_invoked.emit(signature_params)
                signature_data = signature_params['signatures']
                documentation = signature_data['documentation']

                # The language server returns encoded text with
                # spaces defined as `\xa0`
                documentation = documentation.replace(u'\xa0', ' ')

                parameter_idx = signature_params['activeParameter']
                parameters = signature_data['parameters']
                parameter = None
                if len(parameters) > 0 and parameter_idx < len(parameters):
                    parameter_data = parameters[parameter_idx]
                    parameter = parameter_data['label']

                signature = signature_data['label']

                # This method is part of spyder/widgets/mixins
                self.show_calltip(
                    signature=signature,
                    parameter=parameter,
                    language=self.language,
                    documentation=documentation,
                )
        except RuntimeError:
            # This is triggered when a codeeditor instance was removed
            # before the response can be processed.
            return
        except Exception:
            self.log_lsp_handle_errors("Error when processing signature")

    # ------------- LSP: Hover/Mouse ---------------------------------------
    @request(method=LSPRequestTypes.DOCUMENT_CURSOR_EVENT)
    def request_cursor_event(self):
        text = self.toPlainText()
        cursor = self.textCursor()
        params = {
            'file': self.filename,
            'version': self.text_version,
            'text': text,
            'offset': cursor.position(),
            'selection_start': cursor.selectionStart(),
            'selection_end': cursor.selectionEnd(),
        }
        return params

    @request(method=LSPRequestTypes.DOCUMENT_HOVER)
    def request_hover(self, line, col, offset, show_hint=True, clicked=True):
        """Request hover information."""
        params = {
            'file': self.filename,
            'line': line,
            'column': col,
            'offset': offset
        }
        self._show_hint = show_hint
        self._request_hover_clicked = clicked
        return params

    @handles(LSPRequestTypes.DOCUMENT_HOVER)
    def handle_hover_response(self, contents):
        """Handle hover response."""
        if running_under_pytest():
            try:
                from unittest.mock import Mock
            except ImportError:
                from mock import Mock  # Python 2

            # On some tests this is returning a Mock
            if isinstance(contents, Mock):
                return

        try:
            content = contents['params']

            if isinstance(content, list):
                # Prevent sporious errors when a client return a list
                return

            self.sig_display_object_info.emit(content,
                                              self._request_hover_clicked)
            if content is not None and self._show_hint and self._last_point:
                # This is located in spyder/widgets/mixins.py
                word = self._last_hover_word
                content = content.replace(u'\xa0', ' ')
                self.show_hint(content, inspect_word=word,
                               at_point=self._last_point)
                self._last_point = None
        except RuntimeError:
            # This is triggered when a codeeditor instance was removed
            # before the response can be processed.
            return
        except Exception:
            self.log_lsp_handle_errors("Error when processing hover")

    # ------------- LSP: Go To Definition ----------------------------
    @Slot()
    @request(method=LSPRequestTypes.DOCUMENT_DEFINITION)
    def go_to_definition_from_cursor(self, cursor=None):
        """Go to definition from cursor instance (QTextCursor)."""
        if (not self.go_to_definition_enabled or
                self.in_comment_or_string()):
            return

        if cursor is None:
            cursor = self.textCursor()

        text = to_text_string(cursor.selectedText())

        if len(text) == 0:
            cursor.select(QTextCursor.WordUnderCursor)
            text = to_text_string(cursor.selectedText())

        if text is not None:
            line, column = self.get_cursor_line_column()
            params = {
                'file': self.filename,
                'line': line,
                'column': column
            }
            return params

    @handles(LSPRequestTypes.DOCUMENT_DEFINITION)
    def handle_go_to_definition(self, position):
        """Handle go to definition response."""
        try:
            position = position['params']
            if position is not None:
                def_range = position['range']
                start = def_range['start']
                if self.filename == position['file']:
                    self.go_to_line(start['line'] + 1,
                                    start['character'],
                                    None,
                                    word=None)
                else:
                    self.go_to_definition.emit(position['file'],
                                               start['line'] + 1,
                                               start['character'])
        except RuntimeError:
            # This is triggered when a codeeditor instance was removed
            # before the response can be processed.
            return
        except Exception:
            self.log_lsp_handle_errors(
                "Error when processing go to definition")

    # ------------- LSP: Document/Selection formatting --------------------
    def format_document_or_range(self):
        if self.has_selected_text() and self.range_formatting_enabled:
            self.format_document_range()
        else:
            self.format_document()

    @request(method=LSPRequestTypes.DOCUMENT_FORMATTING)
    def format_document(self):
        if not self.formatting_enabled:
            return

        using_spaces = self.indent_chars != '\t'
        tab_size = (len(self.indent_chars) if using_spaces else
                    self.tab_stop_width_spaces)
        params = {
            'file': self.filename,
            'options': {
                'tab_size': tab_size,
                'insert_spaces': using_spaces,
                'trim_trailing_whitespace': self.remove_trailing_spaces,
                'insert_final_new_line': self.add_newline,
                'trim_final_new_lines': self.remove_trailing_newlines
            }
        }

        # Sets the document into read-only and updates its corresponding
        # tab name to display the filename into parenthesis
        self.setReadOnly(True)
        self.document().setModified(True)
        self.sig_start_operation_in_progress.emit()
        self.operation_in_progress = True

        return params

    @request(method=LSPRequestTypes.DOCUMENT_RANGE_FORMATTING)
    def format_document_range(self):
        if not self.range_formatting_enabled or not self.has_selected_text():
            return

        start, end = self.get_selection_start_end()
        start_line, start_col = start
        end_line, end_col = end
        using_spaces = self.indent_chars != '\t'
        tab_size = (len(self.indent_chars) if using_spaces else
                    self.tab_stop_width_spaces)

        fmt_range = {
            'start': {
                'line': start_line,
                'character': start_col
            },
            'end': {
                'line': end_line,
                'character': end_col
            }
        }
        params = {
            'file': self.filename,
            'range': fmt_range,
            'options': {
                'tab_size': tab_size,
                'insert_spaces': using_spaces,
                'trim_trailing_whitespace': self.remove_trailing_spaces,
                'insert_final_new_line': self.add_newline,
                'trim_final_new_lines': self.remove_trailing_newlines
            }
        }

        # Sets the document into read-only and updates its corresponding
        # tab name to display the filename into parenthesis
        self.setReadOnly(True)
        self.document().setModified(True)
        self.sig_start_operation_in_progress.emit()
        self.operation_in_progress = True

        return params

    @handles(LSPRequestTypes.DOCUMENT_FORMATTING)
    def handle_document_formatting(self, edits):
        try:
            self._apply_document_edits(edits)
        except RuntimeError:
            # This is triggered when a codeeditor instance was removed
            # before the response can be processed.
            return
        except Exception:
            self.log_lsp_handle_errors("Error when processing document "
                                       "formatting")
        finally:
            # Remove read-only parenthesis and highlight document modification
            self.setReadOnly(False)
            self.document().setModified(False)
            self.document().setModified(True)
            self.sig_stop_operation_in_progress.emit()
            self.operation_in_progress = False

    @handles(LSPRequestTypes.DOCUMENT_RANGE_FORMATTING)
    def handle_document_range_formatting(self, edits):
        try:
            self._apply_document_edits(edits)
        except RuntimeError:
            # This is triggered when a codeeditor instance was removed
            # before the response can be processed.
            return
        except Exception:
            self.log_lsp_handle_errors("Error when processing document "
                                       "selection formatting")
        finally:
            # Remove read-only parenthesis and highlight document modification
            self.setReadOnly(False)
            self.document().setModified(False)
            self.document().setModified(True)
            self.sig_stop_operation_in_progress.emit()
            self.operation_in_progress = False

    def _apply_document_edits(self, edits):
        """Apply a set of atomic document edits to the current editor text."""
        edits = edits['params']
        if edits is None:
            return

        texts = []
        diffs = []
        text = self.toPlainText()
        text_tokens = list(text)
        merged_text = None
        for edit in edits:
            edit_range = edit['range']
            repl_text = edit['newText']
            start, end = edit_range['start'], edit_range['end']
            start_line, start_col = start['line'], start['character']
            end_line, end_col = end['line'], end['character']

            start_pos = self.get_position_line_number(start_line, start_col)
            end_pos = self.get_position_line_number(end_line, end_col)

            text_tokens = list(text_tokens)
            this_edit = list(repl_text)

            if end_line == self.document().blockCount():
                end_pos = self.get_position('eof')
                end_pos += 1

            if (end_pos == len(text_tokens) and
                    text_tokens[end_pos - 1] == '\n'):
                end_pos += 1

            this_edition = (text_tokens[:max(start_pos - 1, 0)] +
                            this_edit +
                            text_tokens[end_pos - 1:])

            text_edit = ''.join(this_edition)
            if merged_text is None:
                merged_text = text_edit
            else:
                merged_text = merge(text_edit, merged_text, text)

        if merged_text is not None:
            cursor = self.textCursor()
            cursor.beginEditBlock()
            cursor.movePosition(QTextCursor.Start)
            cursor.movePosition(QTextCursor.End,
                                QTextCursor.KeepAnchor)
            cursor.insertText(merged_text)
            cursor.endEditBlock()
            self.document_did_change()

    # ------------- LSP: Code folding ranges -------------------------------
    def compute_whitespace(self, line):
        tab_size = self.tab_stop_width_spaces
        whitespace_regex = re.compile(r'(\s+).*')
        whitespace_match = whitespace_regex.match(line)
        total_whitespace = 0
        if whitespace_match is not None:
            whitespace_chars = whitespace_match.group(1)
            whitespace_chars = whitespace_chars.replace(
                '\t', tab_size * ' ')
            total_whitespace = len(whitespace_chars)
        return total_whitespace

    def update_whitespace_count(self, line, column):
        self.leading_whitespaces = {}
        lines = to_text_string(self.toPlainText()).splitlines()
        for i, text in enumerate(lines):
            total_whitespace = self.compute_whitespace(text)
            self.leading_whitespaces[i] = total_whitespace

    def cleanup_folding(self):
        """Cleanup folding pane."""
        folding_panel = self.panels.get(FoldingPanel)
        folding_panel.folding_regions = {}

    @request(method=LSPRequestTypes.DOCUMENT_FOLDING_RANGE)
    def request_folding(self):
        """Request folding."""
        if not self.folding_supported or not self.code_folding:
            return
        params = {'file': self.filename}
        return params

    @handles(LSPRequestTypes.DOCUMENT_FOLDING_RANGE)
    def handle_folding_range(self, response):
        """Handle folding response."""
        try:
            ranges = response['params']
            folding_panel = self.panels.get(FoldingPanel)

            # Update folding
            text = self.toPlainText()
            self.text_diff = (self.differ.diff_main(self.previous_text, text),
                              self.previous_text)
            folding_panel.update_folding(ranges)

            # Update indent guides, which depend on folding
            if self.indent_guides._enabled and len(self.patch) > 0:
                line, column = self.get_cursor_line_column()
                self.update_whitespace_count(line, column)
        except RuntimeError:
            # This is triggered when a codeeditor instance was removed
            # before the response can be processed.
            return
        except Exception:
            self.log_lsp_handle_errors("Error when processing folding")

        # Tests for the class function selector need this.
        if running_under_pytest():
            self.request_symbols()

    # ------------- LSP: Save/close file -----------------------------------
    @request(method=LSPRequestTypes.DOCUMENT_DID_SAVE,
             requires_response=False)
    def notify_save(self):
        """Send save request."""
        params = {'file': self.filename}
        if self.save_include_text:
            params['text'] = self.toPlainText()
        return params

    @request(method=LSPRequestTypes.DOCUMENT_DID_CLOSE,
             requires_response=False)
    def notify_close(self):
        """Send close request."""
        if self.completions_available:
            params = {
                'file': self.filename,
                'codeeditor': self
            }
            return params

    # -------------------------------------------------------------------------
    def set_debug_panel(self, show_debug_panel, language):
        """Enable/disable debug panel."""
        debugger_panel = self.panels.get(DebuggerPanel)
        if (is_text_string(language) and
                language.lower() in ALL_LANGUAGES['Python'] and
                show_debug_panel):
            debugger_panel.setVisible(True)
        else:
            debugger_panel.setVisible(False)

    def update_debugger_panel_state(self, state, last_step, force=False):
        """Update debugger panel state."""
        debugger_panel = self.panels.get(DebuggerPanel)
        if force:
            debugger_panel.start_clean()
            return
        elif state and 'fname' in last_step:
            fname = last_step['fname']
            if (fname and self.filename
                    and osp.normcase(fname) == osp.normcase(self.filename)):
                debugger_panel.start_clean()
                return
        debugger_panel.stop_clean()

    def set_folding_panel(self, folding):
        """Enable/disable folding panel."""
        folding_panel = self.panels.get(FoldingPanel)
        folding_panel.setVisible(folding)

    def set_tab_mode(self, enable):
        """
        enabled = tab always indent
        (otherwise tab indents only when cursor is at the beginning of a line)
        """
        self.tab_mode = enable

    def set_strip_mode(self, enable):
        """
        Strip all trailing spaces if enabled.
        """
        self.strip_trailing_spaces_on_modify = enable

    def toggle_intelligent_backspace(self, state):
        self.intelligent_backspace = state

    def toggle_automatic_completions(self, state):
        self.automatic_completions = state

    def toggle_hover_hints(self, state):
        self.hover_hints_enabled = state

    def toggle_code_snippets(self, state):
        self.code_snippets = state

    def toggle_format_on_save(self, state):
        self.format_on_save = state

    def toggle_code_folding(self, state):
        self.code_folding = state
        self.set_folding_panel(state)
        if not state and self.indent_guides._enabled:
            self.code_folding = True

    def toggle_identation_guides(self, state):
        if state and not self.code_folding:
            self.code_folding = True
        self.indent_guides.set_enabled(state)

    def toggle_completions_hint(self, state):
        """Enable/disable completion hint."""
        self.completions_hint = state

    def set_automatic_completions_after_chars(self, number):
        """
        Set the number of characters after which auto completion is fired.
        """
        self.automatic_completions_after_chars = number

    def set_automatic_completions_after_ms(self, ms):
        """
        Set the amount of time in ms after which auto completion is fired.
        """
        self.automatic_completions_after_ms = ms

    def set_completions_hint_after_ms(self, ms):
        """
        Set the amount of time in ms after which the completions hint is shown.
        """
        self.completions_hint_after_ms = ms

    def set_close_parentheses_enabled(self, enable):
        """Enable/disable automatic parentheses insertion feature"""
        self.close_parentheses_enabled = enable
        bracket_extension = self.editor_extensions.get(CloseBracketsExtension)
        if bracket_extension is not None:
            bracket_extension.enabled = enable

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

    def set_underline_errors_enabled(self, state):
        """Toggle the underlining of errors and warnings."""
        self.underline_errors_enabled = state
        if state:
            self.document_did_change()
        else:
            self.clear_extra_selections('code_analysis_underline')

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
        self.language = 'Text'
        self.supported_language = False
        sh_class = sh.TextSH
        language = 'None' if language is None else language
        if language is not None:
            for (key, value) in ALL_LANGUAGES.items():
                if language.lower() in value:
                    self.supported_language = True
                    sh_class, comment_string, CFMatch = self.LANGUAGES[key]
                    self.language = key
                    self.comment_string = comment_string
                    if key in CELL_LANGUAGES:
                        self.supported_cell_language = True
                        self.has_cell_separators = True
                    if CFMatch is None:
                        self.classfunc_match = None
                    else:
                        self.classfunc_match = CFMatch()
                    break

        if filename is not None and not self.supported_language:
            sh_class = sh.guess_pygments_highlighter(filename)
            self.support_language = sh_class is not sh.TextSH
            if self.support_language:
                # Pygments report S for the lexer name of R files
                if sh_class._lexer.name == 'S':
                    self.language = 'R'
                else:
                    self.language = sh_class._lexer.name

        self._set_highlighter(sh_class)
        self.completion_widget.set_language(self.language)

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
        self.highlighter._cell_list = []
        self.highlighter.sig_new_cell.connect(self.add_to_cell_list)
        self._apply_highlighter_color_scheme()

        self.highlighter.editor = self

    def add_to_cell_list(self, oedata):
        """Add new cell to cell list."""
        if self.highlighter is None:
            return
        self.highlighter._cell_list.append(oedata)

    def get_cell_list(self):
        """Get all cells."""
        if self.highlighter is None:
            return []
        # Filter out old cells
        def good(oedata):
            return oedata.is_valid() and oedata.def_type == oedata.CELL

        self.highlighter._cell_list = [
            oedata for oedata in self.highlighter._cell_list if good(oedata)]

        return sorted(
            {oedata.get_block_number(): oedata
             for oedata in self.highlighter._cell_list}.items())

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
        """Provide intelligent behavior for Tab key press."""
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
        """Rehighlight the whole document."""
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

    def trim_trailing_spaces(self):
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
        self.document_did_change()

    def trim_trailing_newlines(self):
        """Remove extra newlines at the end of the document."""
        cursor = self.textCursor()
        cursor.beginEditBlock()
        cursor.movePosition(QTextCursor.End)
        line = cursor.blockNumber()
        this_line = self.get_text_line(line)
        previous_line = self.get_text_line(line - 1)

        while this_line == '':
            cursor.movePosition(QTextCursor.PreviousBlock,
                                QTextCursor.KeepAnchor)

            if self.add_newline:
                if this_line == '' and previous_line != '':
                    cursor.movePosition(QTextCursor.NextBlock,
                                        QTextCursor.KeepAnchor)

            line -= 1
            if line == 0:
                break

            this_line = self.get_text_line(line)
            previous_line = self.get_text_line(line - 1)

        if not self.add_newline:
            cursor.movePosition(QTextCursor.EndOfBlock,
                                QTextCursor.KeepAnchor)

        cursor.removeSelectedText()
        cursor.endEditBlock()
        self.document_did_change()

    def add_newline_to_file(self):
        """Add a newline to the end of the file if it does not exist."""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        line = cursor.blockNumber()
        this_line = self.get_text_line(line)
        if this_line != '':
            cursor.beginEditBlock()
            cursor.movePosition(QTextCursor.EndOfBlock)
            cursor.insertText(self.get_line_separator())
            cursor.endEditBlock()
            self.document_did_change()

    def fix_indentation(self):
        """Replace tabs by spaces."""
        text_before = to_text_string(self.toPlainText())
        text_after = sourcecode.fix_indentation(text_before, self.indent_chars)
        if text_before != text_after:
            # We do the following rather than using self.setPlainText
            # to benefit from QTextEdit's undo/redo feature.
            self.selectAll()
            self.skip_rstrip = True
            self.insertPlainText(text_after)
            self.document_did_change()
            self.skip_rstrip = False

    def get_current_object(self):
        """Return current object (string) """
        source_code = to_text_string(self.toPlainText())
        offset = self.get_position('cursor')
        return sourcecode.get_primary_at(source_code, offset)

    @Slot()
    def delete(self):
        """Remove selected text or next character."""
        if not self.has_selected_text():
            cursor = self.textCursor()
            position = cursor.position()
            if not cursor.atEnd():
                cursor.setPosition(position + 1, QTextCursor.KeepAnchor)
            self.setTextCursor(cursor)
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

        # Strip if needed
        self.strip_trailing_spaces()

    def __clear_occurrences(self):
        """Clear occurrence markers"""
        self.occurrences = []
        self.clear_extra_selections('occurrences')
        self.sig_flags_changed.emit()

    def get_selection(self, cursor, foreground_color=None,
                      background_color=None, underline_color=None,
                      outline_color=None,
                      underline_style=QTextCharFormat.SingleUnderline):
        """Get selection."""
        if cursor is None:
            return

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
        if outline_color is not None:
            selection.set_outline(outline_color)
        return selection

    def highlight_selection(self, key, cursor, foreground_color=None,
                            background_color=None, underline_color=None,
                            outline_color=None,
                            underline_style=QTextCharFormat.SingleUnderline,
                            update=False):

        selection = self.get_selection(
            cursor, foreground_color, background_color, underline_color,
            outline_color, underline_style)
        if selection is None:
            return
        extra_selections = self.get_extra_selections(key)
        extra_selections.append(selection)
        self.set_extra_selections(key, extra_selections)
        if update:
            self.update_extra_selections()

    def __mark_occurrences(self):
        """Marking occurrences of the currently selected word"""
        self.__clear_occurrences()

        if not self.supported_language:
            return

        text = self.get_selected_text().strip()
        if not text:
            text = self.get_current_word()
        if text is None:
            return
        if (self.has_selected_text() and
                self.get_selected_text().strip() != text):
            return

        if (self.is_python_like() and
                (sourcecode.is_keyword(to_text_string(text)) or
                 to_text_string(text) == 'self')):
            return

        # Highlighting all occurrences of word *text*
        cursor = self.__find_first(text)
        self.occurrences = []
        extra_selections = self.get_extra_selections('occurrences')
        first_occurrence = None
        while cursor:
            self.occurrences.append(cursor.blockNumber())
            selection = self.get_selection(cursor)
            if len(selection.cursor.selectedText()) > 0:
                extra_selections.append(selection)
                if len(extra_selections) == 1:
                    first_occurrence = selection
                else:
                    selection.format.setBackground(self.occurrence_color)
                    first_occurrence.format.setBackground(
                        self.occurrence_color)
            cursor = self.__find_next(text, cursor)
        self.set_extra_selections('occurrences', extra_selections)
        self.update_extra_selections()

        if len(self.occurrences) > 1 and self.occurrences[-1] == 0:
            # XXX: this is never happening with PySide but it's necessary
            # for PyQt4... this must be related to a different behavior for
            # the QTextDocument.find function between those two libraries
            self.occurrences.pop(-1)
        self.sig_flags_changed.emit()

    #-----highlight found results (find/replace widget)
    def highlight_found_results(self, pattern, word=False, regexp=False,
                                case=False):
        """Highlight all found patterns"""
        pattern = to_text_string(pattern)
        if not pattern:
            return
        if not regexp:
            pattern = re.escape(to_text_string(pattern))
        pattern = r"\b%s\b" % pattern if word else pattern
        text = to_text_string(self.toPlainText())
        re_flags = re.MULTILINE if case else re.IGNORECASE | re.MULTILINE
        try:
            regobj = re.compile(pattern, flags=re_flags)
        except sre_constants.error:
            return
        extra_selections = []
        self.found_results = []
        for match in regobj.finditer(text):
            pos1, pos2 = sh.get_span(match)
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
        self.sig_flags_changed.emit()

    def __text_has_changed(self):
        """Text has changed, eventually clear found results highlighting"""
        self.last_change_position = self.textCursor().position()
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
        point.setX(point.x() + self.panels.margin_size(Panel.Position.LEFT))
        point.setY(point.y() + self.panels.margin_size(Panel.Position.TOP))
        return point

    def calculate_real_position_from_global(self, point):
        """Add offset to a point, to take into account the panels."""
        point.setX(point.x() - self.panels.margin_size(Panel.Position.LEFT))
        point.setY(point.y() + self.panels.margin_size(Panel.Position.TOP))
        return point

    def get_linenumber_from_mouse_event(self, event):
        """Return line number from mouse event"""
        block = self.firstVisibleBlock()
        line_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(
                                                    self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        folding_panel = self.panels.get(FoldingPanel)
        while block.isValid() and top < event.pos().y():
            block = block.next()
            if block.isVisible():  # skip collapsed blocks
                top = bottom
                bottom = top + self.blockBoundingRect(block).height()
            line_number += 1
        return line_number

    def select_lines(self, linenumber_pressed, linenumber_released):
        """Select line(s) after a mouse press/mouse press drag event"""
        find_block_by_number = self.document().findBlockByNumber
        move_n_blocks = (linenumber_released - linenumber_pressed)
        start_line = linenumber_pressed
        start_block = find_block_by_number(start_line - 1)

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

    # ----- Code bookmarks
    def add_bookmark(self, slot_num, line=None, column=None):
        """Add bookmark to current block's userData."""
        if line is None:
            # Triggered by shortcut, else by spyder start
            line, column = self.get_cursor_line_column()
        block = self.document().findBlockByNumber(line)
        data = block.userData()
        if not data:
            data = BlockUserData(self)
        if slot_num not in data.bookmarks:
            data.bookmarks.append((slot_num, column))
        block.setUserData(data)
        self.sig_bookmarks_changed.emit()

    def get_bookmarks(self):
        """Get bookmarks by going over all blocks."""
        bookmarks = {}
        block = self.document().firstBlock()
        for line_number in range(0, self.document().blockCount()):
            data = block.userData()
            if data and data.bookmarks:
                for slot_num, column in data.bookmarks:
                    bookmarks[slot_num] = [line_number, column]
            block = block.next()
        return bookmarks

    def clear_bookmarks(self):
        """Clear bookmarks for all blocks."""
        self.bookmarks = {}
        for data in self.blockuserdata_list():
            data.bookmarks = []

    def set_bookmarks(self, bookmarks):
        """Set bookmarks when opening file."""
        self.clear_bookmarks()
        for slot_num, bookmark in bookmarks.items():
            self.add_bookmark(slot_num, bookmark[1], bookmark[2])

    def update_bookmarks(self):
        """Emit signal to update bookmarks."""
        self.sig_bookmarks_changed.emit()

    # -----Code introspection
    def show_completion_object_info(self, name, signature):
        """Trigger show completion info in Help Pane."""
        force = True
        self.sig_show_completion_object_info.emit(name, signature, force)

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

            self.sig_theme_colors_changed.emit(
                {'occurrence': self.occurrence_color})

    def apply_highlighter_settings(self, color_scheme=None):
        """Apply syntax highlighter settings"""
        if self.highlighter is not None:
            # Updating highlighter settings (font and color scheme)
            self.highlighter.setup_formats(self.font())
            if color_scheme is not None:
                self.set_color_scheme(color_scheme)
            else:
                self.highlighter.rehighlight()

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
        self.document_did_change(text)

        if (isinstance(self.highlighter, sh.PygmentsSH)
                and not running_under_pytest()):
            self.highlighter.make_charlist()

    def set_text_from_file(self, filename, language=None):
        """Set the text of the editor from file *fname*"""
        self.filename = filename
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
        self.document_did_change()

    @Slot()
    def paste(self):
        """
        Insert text or file/folder path copied from clipboard.

        Reimplement QPlainTextEdit's method to fix the following issue:
        on Windows, pasted text has only 'LF' EOL chars even if the original
        text has 'CRLF' EOL chars.
        The function also changes the clipboard data if they are copied as
        files/folders but does not change normal text data except if they are
        multiple lines. Since we are changing clipboard data we cannot use
        paste, which directly pastes from clipboard instead we use
        insertPlainText and pass the formatted/changed text without modifying
        clipboard content.
        """
        clipboard = QApplication.clipboard()
        text = to_text_string(clipboard.text())
        if clipboard.mimeData().hasUrls():
            # Have copied file and folder urls pasted as text paths.
            # See spyder-ide/spyder#8644 for details.
            urls = clipboard.mimeData().urls()
            if all([url.isLocalFile() for url in urls]):
                if len(urls) > 1:
                    sep_chars = ',' + self.get_line_separator()
                    text = sep_chars.join('"' + url.toLocalFile().
                                          replace(osp.os.sep, '/')
                                          + '"' for url in urls)
                else:
                    text = urls[0].toLocalFile().replace(osp.os.sep, '/')
        if len(text.splitlines()) > 1:
            eol_chars = self.get_line_separator()
            text = eol_chars.join((text + eol_chars).splitlines())
        self.skip_rstrip = True
        self.sig_will_paste_text.emit(text)
        TextEditBaseWidget.insertPlainText(self, text)
        self.sig_text_was_inserted.emit()

        self.document_did_change(text)
        self.skip_rstrip = False

    @Slot()
    def cut(self):
        """Reimplement cut to signal listeners about changes on the text."""
        has_selected_text = self.has_selected_text()
        if not has_selected_text:
            return
        start, end = self.get_selection_start_end()
        self.sig_will_remove_selection.emit(start, end)
        TextEditBaseWidget.cut(self)
        self.sig_text_was_inserted.emit()
        self.document_did_change('')

    @Slot()
    def undo(self):
        """Reimplement undo to decrease text version number."""
        if self.document().isUndoAvailable():
            self.text_version -= 1
            self.skip_rstrip = True
            self.is_undoing = True
            TextEditBaseWidget.undo(self)
            self.document_did_change('')
            self.sig_undo.emit()
            self.sig_text_was_inserted.emit()
            self.is_undoing = False
            self.skip_rstrip = False

    @Slot()
    def redo(self):
        """Reimplement redo to increase text version number."""
        if self.document().isRedoAvailable():
            self.text_version += 1
            self.skip_rstrip = True
            self.is_redoing = True
            TextEditBaseWidget.redo(self)
            self.document_did_change('text')
            self.sig_redo.emit()
            self.sig_text_was_inserted.emit()
            self.is_redoing = False
            self.skip_rstrip = False

# =============================================================================
#    High-level editor features
# =============================================================================
    @Slot()
    def center_cursor_on_next_focus(self):
        """QPlainTextEdit's "centerCursor" requires the widget to be visible"""
        self.centerCursor()
        self.focus_in.disconnect(self.center_cursor_on_next_focus)

    def go_to_line(self, line, start_column=0, end_column=0, word=''):
        """Go to line number *line* and eventually highlight it"""
        self.text_helper.goto_line(line, column=start_column,
                                   end_column=end_column, move=True,
                                   word=word)

    def exec_gotolinedialog(self):
        """Execute the GoToLineDialog dialog box"""
        dlg = GoToLineDialog(self)
        if dlg.exec_():
            self.go_to_line(dlg.get_line_number())

    def cleanup_code_analysis(self):
        """Remove all code analysis markers"""
        self.setUpdatesEnabled(False)
        self.clear_extra_selections('code_analysis_highlight')
        self.clear_extra_selections('code_analysis_underline')
        for data in self.blockuserdata_list():
            data.code_analysis = []

        self.setUpdatesEnabled(True)
        # When the new code analysis results are empty, it is necessary
        # to update manually the scrollflag and linenumber areas (otherwise,
        # the old flags will still be displayed):
        self.sig_flags_changed.emit()
        self.linenumberarea.update()

    def _process_code_analysis(self, underline):
        """
        Process all code analysis results.

        Parameters
        ----------
        underline: bool
            Determines if errors and warnings are going to be set in
            the line number area or underlined. It's better to separate
            these two processes for perfomance reasons. That's because
            setting errors can be done in a thread whereas underlining
            them can't.
        """
        document = self.document()
        for diagnostic in self._diagnostics:
            source = diagnostic.get('source', '')
            msg_range = diagnostic['range']
            start = msg_range['start']
            end = msg_range['end']
            code = diagnostic.get('code', 'E')
            message = diagnostic['message']
            severity = diagnostic.get(
                'severity', DiagnosticSeverity.ERROR)

            block = document.findBlockByNumber(start['line'])
            data = block.userData()
            if not data:
                data = BlockUserData(self)

            if underline:
                block_nb = block.blockNumber()
                first, last = self.get_buffer_block_numbers()

                if (self.underline_errors_enabled and
                        first <= block_nb <= last):
                    error = severity == DiagnosticSeverity.ERROR
                    color = self.error_color if error else self.warning_color
                    color = QColor(color)
                    color.setAlpha(255)
                    block.color = color

                    data.selection_start = start
                    data.selection_end = end

                    self.highlight_selection('code_analysis_underline',
                                             data._selection(),
                                             underline_color=block.color)
            else:
                data.code_analysis.append((source, code, severity, message))
                block.setUserData(data)

    def set_errors(self):
        """Set errors and warnings in the line number area."""
        self._process_code_analysis(underline=False)

    def underline_errors(self):
        """Underline errors and warnings."""
        self._process_code_analysis(underline=True)

    def finish_code_analysis(self):
        """Finish processing code analysis results."""
        self.linenumberarea.update()
        self.underline_errors()
        self.update_extra_selections()
        self.sig_process_code_analysis.emit()
        self.sig_flags_changed.emit()

    def process_code_analysis(self, diagnostics):
        """Process all code analysis results."""
        self.cleanup_code_analysis()
        self._diagnostics = diagnostics

        # Process diagnostics in a thread to improve performance.
        self.update_diagnostics = QThread()
        self.update_diagnostics.run = self.set_errors
        self.update_diagnostics.finished.connect(self.finish_code_analysis)
        self.update_diagnostics.start()

    def hide_tooltip(self):
        """
        Hide the tooltip widget.

        The tooltip widget is a special QLabel that looks like a tooltip,
        this method is here so it can be hidden as necessary. For example,
        when the user leaves the Linenumber area when hovering over lint
        warnings and errors.
        """
        self._timer_mouse_moving.stop()
        self._last_hover_word = None
        self.clear_extra_selections('code_analysis_highlight')
        if self.tooltip_widget.isVisible():
            self.tooltip_widget.hide()

    def _set_completions_hint_idle(self):
        self._completions_hint_idle = True
        self.completion_widget.trigger_completion_hint()

    # --- Hint for completions
    def show_hint_for_completion(self, word, documentation, at_point):
        """Show hint for completion element."""
        if self.completions_hint and self._completions_hint_idle:
            documentation = documentation.replace(u'\xa0', ' ')
            completion_doc = {'name': word,
                              'signature': documentation}

            if documentation and len(documentation) > 0:
                self.show_hint(
                    documentation,
                    inspect_word=word,
                    at_point=at_point,
                    completion_doc=completion_doc,
                    max_lines=self._DEFAULT_MAX_LINES,
                    max_width=self._DEFAULT_COMPLETION_HINT_MAX_WIDTH)
                self.tooltip_widget.move(at_point)
                return
        self.hide_tooltip()

    def update_decorations(self):
        """Update decorations on the visible portion of the screen."""
        if self.underline_errors_enabled:
            self.underline_errors()
            self.update_extra_selections()
        else:
            self.decorations.update()

    def show_code_analysis_results(self, line_number, block_data):
        """Show warning/error messages."""
        # Diagnostic severity
        icons = {
            DiagnosticSeverity.ERROR: 'error',
            DiagnosticSeverity.WARNING: 'warning',
            DiagnosticSeverity.INFORMATION: 'information',
            DiagnosticSeverity.HINT: 'hint',
        }

        code_analysis = block_data.code_analysis

        # Size must be adapted from font
        fm = self.fontMetrics()
        size = fm.height()
        template = (
            '<img src="data:image/png;base64, {}"'
            ' height="{size}" width="{size}" />&nbsp;'
            '{} <i>({} {})</i>'
        )

        msglist = []
        max_lines_msglist = 25
        sorted_code_analysis = sorted(code_analysis, key=lambda i: i[2])
        for src, code, sev, msg in sorted_code_analysis:
            if src == 'pylint' and '[' in msg and ']' in msg:
                # Remove extra redundant info from pylint messages
                msg = msg.split(']')[-1]

            msg = msg.strip()
            # Avoid messing TODO, FIXME
            # Prevent error if msg only has one element
            if len(msg) > 1:
                msg = msg[0].upper() + msg[1:]

            # Get individual lines following paragraph format and handle
            # symbols like '<' and '>' to not mess with br tags
            msg = msg.replace('<', '&lt;').replace('>', '&gt;')
            paragraphs = msg.splitlines()
            new_paragraphs = []
            long_paragraphs = 0
            lines_per_message = 6
            for paragraph in paragraphs:
                new_paragraph = textwrap.wrap(
                    paragraph,
                    width=self._DEFAULT_MAX_HINT_WIDTH)
                if lines_per_message > 2:
                    if len(new_paragraph) > 1:
                        new_paragraph = '<br>'.join(new_paragraph[:2]) + '...'
                        long_paragraphs += 1
                        lines_per_message -= 2
                    else:
                        new_paragraph = '<br>'.join(new_paragraph)
                        lines_per_message -= 1
                    new_paragraphs.append(new_paragraph)

            if len(new_paragraphs) > 1:
                # Define max lines taking into account that in the same
                # tooltip you can find multiple warnings and messages
                # and each one can have multiple lines
                if long_paragraphs != 0:
                    max_lines = 3
                    max_lines_msglist -= max_lines * 2
                else:
                    max_lines = 5
                    max_lines_msglist -= max_lines
                msg = '<br>'.join(new_paragraphs[:max_lines]) + '<br>'
            else:
                msg = '<br>'.join(new_paragraphs)

            base_64 = ima.base64_from_icon(icons[sev], size, size)
            if max_lines_msglist >= 0:
                msglist.append(template.format(base_64, msg, src,
                                               code, size=size))

        if msglist:
            self.show_tooltip(
                title=_("Code analysis"),
                text='\n'.join(msglist),
                title_color='#129625',
                at_line=line_number,
                with_html_format=True
            )
            self.highlight_line_warning(block_data)

    def highlight_line_warning(self, block_data):
        """Highlight errors and warnings in this editor."""
        self.clear_extra_selections('code_analysis_highlight')
        self.highlight_selection('code_analysis_highlight',
                                 block_data._selection(),
                                 background_color=block_data.color,
                                 update=True)
        self.linenumberarea.update()

    def get_current_warnings(self):
        """
        Get all warnings for the current editor and return
        a list with the message and line number.
        """
        block = self.document().firstBlock()
        line_count = self.document().blockCount()
        warnings = []
        while True:
            data = block.userData()
            if data and data.code_analysis:
                for warning in data.code_analysis:
                    warnings.append([warning[-1], block.blockNumber() + 1])
            # See spyder-ide/spyder#9924
            if block.blockNumber() + 1 == line_count:
                break
            block = block.next()
        return warnings

    def go_to_next_warning(self):
        """
        Go to next code warning message and return new cursor position.
        """
        block = self.textCursor().block()
        line_count = self.document().blockCount()
        for _ in range(line_count):
            line_number = block.blockNumber() + 1
            if line_number < line_count:
                block = block.next()
            else:
                block = self.document().firstBlock()

            data = block.userData()
            if data and data.code_analysis:
                line_number = block.blockNumber() + 1
                self.go_to_line(line_number)
                self.show_code_analysis_results(line_number, data)
                return self.get_position('cursor')

    def go_to_previous_warning(self):
        """
        Go to previous code warning message and return new cursor position.
        """
        block = self.textCursor().block()
        line_count = self.document().blockCount()
        for _ in range(line_count):
            line_number = block.blockNumber() + 1
            if line_number > 1:
                block = block.previous()
            else:
                block = self.document().lastBlock()

            data = block.userData()
            if data and data.code_analysis:
                line_number = block.blockNumber() + 1
                self.go_to_line(line_number)
                self.show_code_analysis_results(line_number, data)
                return self.get_position('cursor')

    def cell_list(self):
        """Get the outline explorer data for all cells."""
        for oedata in self.outlineexplorer_data_list():
            if oedata.def_type == OED.CELL:
                yield oedata

    def get_cell_code(self, cell):
        """
        Get cell code for a given cell.

        If the cell doesn't exist, raises an exception
        """
        selected_block = None
        if is_string(cell):
            for oedata in self.cell_list():
                if oedata.def_name == cell:
                    selected_block = oedata.block
                    break
        else:
            if cell == 0:
                selected_block = self.document().firstBlock()
            else:
                cell_list = list(self.cell_list())
                if cell <= len(cell_list):
                    selected_block = cell_list[cell - 1].block

        if not selected_block:
            raise RuntimeError("Cell {} not found.".format(repr(cell)))

        cursor = QTextCursor(selected_block)
        cell_code, _ = self.get_cell_as_executable_code(cursor)
        return cell_code

    def get_cell_count(self):
        """Get number of cells in document."""
        return 1 + len(list(self.cell_list()))


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
        self.show_tooltip(
            title=_("To do"),
            text=data.todo,
            title_color='#3096FC',
            at_line=line_number,
        )

        return self.get_position('cursor')

    def process_todo(self, todo_results):
        """Process todo finder results"""
        for data in self.blockuserdata_list():
            data.todo = ''

        for message, line_number in todo_results:
            block = self.document().findBlockByNumber(line_number - 1)
            data = block.userData()
            if not data:
                data = BlockUserData(self)
            data.todo = message
            block.setUserData(data)
        self.sig_flags_changed.emit()


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

            cursor.beginEditBlock()
            cursor.setPosition(end_pos)
            # Check if end_pos is at the start of a block: if so, starting
            # changes from the previous block
            if cursor.atBlockStart():
                cursor.movePosition(QTextCursor.PreviousBlock)
                if cursor.position() < start_pos:
                    cursor.setPosition(start_pos)
            move_number = self.__spaces_for_prefix()

            while cursor.position() >= start_pos:
                cursor.movePosition(QTextCursor.StartOfBlock)
                line_text = to_text_string(cursor.block().text())
                if (self.get_character(cursor.position()) == ' '
                        and '#' in prefix and not line_text.isspace()
                        or (not line_text.startswith(' ')
                            and line_text != '')):
                    cursor.movePosition(QTextCursor.Right,
                                        QTextCursor.MoveAnchor,
                                        move_number)
                    cursor.insertText(prefix)
                elif '#' not in prefix:
                    cursor.insertText(prefix)
                if cursor.blockNumber() == 0:
                    # Avoid infinite loop when indenting the very first line
                    break
                cursor.movePosition(QTextCursor.PreviousBlock)
                cursor.movePosition(QTextCursor.EndOfBlock)
            cursor.endEditBlock()
        else:
            # Add prefix to current line
            cursor.beginEditBlock()
            cursor.movePosition(QTextCursor.StartOfBlock)
            if self.get_character(cursor.position()) == ' ' and '#' in prefix:
                cursor.movePosition(QTextCursor.NextWord)
            cursor.insertText(prefix)
            cursor.endEditBlock()
        self.document_did_change()

    def __spaces_for_prefix(self):
        """Find the less indented level of text."""
        cursor = self.textCursor()
        if self.has_selected_text():
            # Add prefix to selected line(s)
            start_pos, end_pos = cursor.selectionStart(), cursor.selectionEnd()

            # Let's see if selection begins at a block start
            first_pos = min([start_pos, end_pos])
            first_cursor = self.textCursor()
            first_cursor.setPosition(first_pos)

            cursor.beginEditBlock()
            cursor.setPosition(end_pos)
            # Check if end_pos is at the start of a block: if so, starting
            # changes from the previous block
            if cursor.atBlockStart():
                cursor.movePosition(QTextCursor.PreviousBlock)
                if cursor.position() < start_pos:
                    cursor.setPosition(start_pos)

            number_spaces = -1
            while cursor.position() >= start_pos:
                cursor.movePosition(QTextCursor.StartOfBlock)
                line_text = to_text_string(cursor.block().text())
                start_with_space = line_text.startswith(' ')
                left_number_spaces = self.__number_of_spaces(line_text)
                if not start_with_space:
                    left_number_spaces = 0
                if ((number_spaces == -1
                        or number_spaces > left_number_spaces)
                        and not line_text.isspace() and line_text != ''):
                    number_spaces = left_number_spaces
                if cursor.blockNumber() == 0:
                    # Avoid infinite loop when indenting the very first line
                    break
                cursor.movePosition(QTextCursor.PreviousBlock)
                cursor.movePosition(QTextCursor.EndOfBlock)
            cursor.endEditBlock()
        return number_spaces

    def __is_cursor_at_start_of_block(self, cursor):
        cursor.movePosition(QTextCursor.StartOfBlock)

    def remove_suffix(self, suffix):
        """
        Remove suffix from current line (there should not be any selection)
        """
        cursor = self.textCursor()
        cursor.setPosition(cursor.position() - qstring_length(suffix),
                           QTextCursor.KeepAnchor)
        if to_text_string(cursor.selectedText()) == suffix:
            cursor.removeSelectedText()
            self.document_did_change()

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
                self.__remove_prefix(prefix, cursor, line_text)
                cursor.movePosition(QTextCursor.PreviousBlock)
            cursor.endEditBlock()
        else:
            # Remove prefix from current line
            cursor.movePosition(QTextCursor.StartOfBlock)
            line_text = to_text_string(cursor.block().text())
            self.__remove_prefix(prefix, cursor, line_text)

    def __remove_prefix(self, prefix, cursor, line_text):
        """Handle the removal of the prefix for a single line."""
        start_with_space = line_text.startswith(' ')
        if start_with_space:
            left_spaces = self.__even_number_of_spaces(line_text)
        else:
            left_spaces = False
        if start_with_space:
            right_number_spaces = self.__number_of_spaces(line_text, group=1)
        else:
            right_number_spaces = self.__number_of_spaces(line_text)
        # Handle prefix remove for comments with spaces
        if (prefix.strip() and line_text.lstrip().startswith(prefix + ' ')
                or line_text.startswith(prefix + ' ') and '#' in prefix):
            cursor.movePosition(QTextCursor.Right,
                                QTextCursor.MoveAnchor,
                                line_text.find(prefix))
            if (right_number_spaces == 1
                    and (left_spaces or not start_with_space)
                    or (not start_with_space and right_number_spaces % 2 != 0)
                    or (left_spaces and right_number_spaces % 2 != 0)):
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

        self.document_did_change()

    def __even_number_of_spaces(self, line_text, group=0):
        """
        Get if there is a correct indentation from a group of spaces of a line.
        """
        spaces = re.findall(r'\s+', line_text)
        if len(spaces) - 1 >= group:
            return len(spaces[group]) % len(self.indent_chars) == 0

    def __number_of_spaces(self, line_text, group=0):
        """Get the number of spaces from a group of spaces in a line."""
        spaces = re.findall(r'\s+', line_text)
        if len(spaces) - 1 >= group:
            return len(spaces[group])

    def __get_brackets(self, line_text, closing_brackets=[]):
        """
        Return unmatched opening brackets and left-over closing brackets.

        (str, []) -> ([(pos, bracket)], [bracket], comment_pos)

        Iterate through line_text to find unmatched brackets.

        Returns three objects as a tuple:
        1) bracket_stack:
            a list of tuples of pos and char of each unmatched opening bracket
        2) closing brackets:
            this line's unmatched closing brackets + arg closing_brackets.
            If this line ad no closing brackets, arg closing_brackets might
            be matched with previously unmatched opening brackets in this line.
        3) Pos at which a # comment begins. -1 if it doesn't.'
        """
        # Remove inline comment and check brackets
        bracket_stack = []  # list containing this lines unmatched opening
        # same deal, for closing though. Ignore if bracket stack not empty,
        # since they are mismatched in that case.
        bracket_unmatched_closing = []
        comment_pos = -1
        deactivate = None
        escaped = False
        pos, c = None, None
        for pos, c in enumerate(line_text):
            # Handle '\' inside strings
            if escaped:
                escaped = False
            # Handle strings
            elif deactivate:
                if c == deactivate:
                    deactivate = None
                elif c == "\\":
                    escaped = True
            elif c in ["'", '"']:
                deactivate = c
            # Handle comments
            elif c == "#":
                comment_pos = pos
                break
            # Handle brackets
            elif c in ('(', '[', '{'):
                bracket_stack.append((pos, c))
            elif c in (')', ']', '}'):
                if bracket_stack and bracket_stack[-1][1] == \
                        {')': '(', ']': '[', '}': '{'}[c]:
                    bracket_stack.pop()
                else:
                    bracket_unmatched_closing.append(c)
        del pos, deactivate, escaped
        # If no closing brackets are left over from this line,
        # check the ones from previous iterations' prevlines
        if not bracket_unmatched_closing:
            for c in list(closing_brackets):
                if bracket_stack and bracket_stack[-1][1] == \
                        {')': '(', ']': '[', '}': '{'}[c]:
                    bracket_stack.pop()
                    closing_brackets.remove(c)
                else:
                    break
        del c
        closing_brackets = bracket_unmatched_closing + closing_brackets
        return (bracket_stack, closing_brackets, comment_pos)

    def fix_indent(self, *args, **kwargs):
        """Indent line according to the preferences"""
        if self.is_python_like():
            ret = self.fix_indent_smart(*args, **kwargs)
        else:
            ret = self.simple_indentation(*args, **kwargs)
        self.document_did_change()
        return ret

    def simple_indentation(self, forward=True, **kwargs):
        """
        Simply preserve the indentation-level of the previous line.
        """
        cursor = self.textCursor()
        block_nb = cursor.blockNumber()
        prev_block = self.document().findBlockByNumber(block_nb - 1)
        prevline = to_text_string(prev_block.text())

        indentation = re.match(r"\s*", prevline).group()
        # Unident
        if not forward:
            indentation = indentation[len(self.indent_chars):]

        cursor.insertText(indentation)
        return False  # simple indentation don't fix indentation

    def fix_indent_smart(self, forward=True, comment_or_string=False,
                         cur_indent=None):
        """
        Fix indentation (Python only, no text selection)

        forward=True: fix indent only if text is not enough indented
                      (otherwise force indent)
        forward=False: fix indent only if text is too much indented
                       (otherwise force unindent)

        comment_or_string: Do not adjust indent level for
            unmatched opening brackets and keywords

        max_blank_lines: maximum number of blank lines to search before giving
            up

        cur_indent: current indent. This is the indent before we started
            processing. E.g. when returning, indent before rstrip.

        Returns True if indent needed to be fixed

        Assumes self.is_python_like() to return True
        """
        cursor = self.textCursor()
        block_nb = cursor.blockNumber()
        # find the line that contains our scope
        line_in_block = False
        visual_indent = False
        add_indent = 0  # How many levels of indent to add
        prevline = None
        prevtext = ""
        empty_lines = True

        closing_brackets = []
        for prevline in range(block_nb - 1, -1, -1):
            cursor.movePosition(QTextCursor.PreviousBlock)
            prevtext = to_text_string(cursor.block().text()).rstrip()

            bracket_stack, closing_brackets, comment_pos = self.__get_brackets(
                prevtext, closing_brackets)

            if not prevtext:
                continue

            if prevtext.endswith((':', '\\')):
                # Presume a block was started
                line_in_block = True  # add one level of indent to correct_indent
                # Does this variable actually do *anything* of relevance?
                # comment_or_string = True

            if bracket_stack or not closing_brackets:
                break

            if prevtext.strip() != '':
                empty_lines = False

        if empty_lines and prevline is not None and prevline < block_nb - 2:
            # The previous line is too far, ignore
            prevtext = ''
            prevline = block_nb - 2
            line_in_block = False

        # splits of prevtext happen a few times. Let's just do it once
        words = re.split(r'[\s\(\[\{\}\]\)]', prevtext.lstrip())

        if line_in_block:
            add_indent += 1

        if prevtext and not comment_or_string:
            if bracket_stack:
                # Hanging indent
                if prevtext.endswith(('(', '[', '{')):
                    add_indent += 1
                    if words[0] in ('class', 'def', 'elif', 'except', 'for',
                                    'if', 'while', 'with'):
                        add_indent += 1
                    elif not (  # I'm not sure this block should exist here
                            (
                                self.tab_stop_width_spaces
                                if self.indent_chars == '\t' else
                                len(self.indent_chars)
                            ) * 2 < len(prevtext)):
                        visual_indent = True
                else:
                    # There's stuff after unmatched opening brackets
                    visual_indent = True
            elif (words[-1] in ('continue', 'break', 'pass',)
                  or words[0] == "return" and not line_in_block
                  ):
                add_indent -= 1

        if prevline:
            prevline_indent = self.get_block_indentation(prevline)
        else:
            prevline_indent = 0

        if visual_indent:  # can only be true if bracket_stack
            correct_indent = bracket_stack[-1][0] + 1
        elif add_indent:
            # Indent
            if self.indent_chars == '\t':
                correct_indent = prevline_indent + self.tab_stop_width_spaces * add_indent
            else:
                correct_indent = prevline_indent + len(self.indent_chars) * add_indent
        else:
            correct_indent = prevline_indent

        # TODO untangle this block
        if prevline and not bracket_stack and not prevtext.endswith(':'):
            if forward:
                # Keep indentation of previous line
                ref_line = block_nb - 1
            else:
                # Find indentation context
                ref_line = prevline
            if cur_indent is None:
                cur_indent = self.get_block_indentation(ref_line)
            is_blank = not self.get_text_line(ref_line).strip()
            trailing_text = self.get_text_line(block_nb).strip()
            # If brackets are matched and no block gets opened
            # Match the above line's indent and nudge to the next multiple of 4

            if cur_indent < prevline_indent and (trailing_text or is_blank):
                # if line directly above is blank or there is text after cursor
                # Ceiling division
                correct_indent = -(-cur_indent // len(self.indent_chars)) * \
                    len(self.indent_chars)

        indent = self.get_block_indentation(block_nb)

        if correct_indent >= 0 and not (
                indent == correct_indent or
                forward and indent > correct_indent or
                not forward and indent < correct_indent
                ):
            # Insert the determined indent
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
        return False

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
            self.skip_rstrip = True
            self.insertPlainText(nbformat.writes(nb))
            self.skip_rstrip = False
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
        elif (force or not leading_text.strip() or
                (self.tab_indents and self.tab_mode)):
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
            if (self.get_selected_text() ==
                    to_text_string(cursor.block().text())):
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
            if self.indent_chars == "\t":
                # Tabs, remove one tab
                self.remove_prefix(self.indent_chars)
            else:
                # Spaces
                space_count = len(self.indent_chars)
                leading_spaces = self.__spaces_for_prefix()
                remainder = leading_spaces % space_count
                if remainder:
                    # Get block on "space multiple grid".
                    # See spyder-ide/spyder#5734.
                    self.remove_prefix(" "*remainder)
                else:
                    # Unindent one space multiple
                    self.remove_prefix(self.indent_chars)
        else:
            leading_text = self.get_text('sol', 'cursor')
            if (force or not leading_text.strip() or
                    (self.tab_indents and self.tab_mode)):
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
        blockcomment = self.unblockcomment()
        if not blockcomment:
            self.remove_prefix(self.comment_string)

    def __blockcomment_bar(self, compatibility=False):
        """Handle versions of blockcomment bar for backwards compatibility."""
        # Blockcomment bar in Spyder version >= 4
        blockcomment_bar = self.comment_string + ' ' + '=' * (
                                    79 - len(self.comment_string + ' '))
        if compatibility:
            # Blockcomment bar in Spyder version < 4
            blockcomment_bar = self.comment_string + '=' * (
                                    79 - len(self.comment_string))
        return blockcomment_bar

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
        self.document_did_change()

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
        self.document_did_change()

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
        self.document_did_change()

    def unblockcomment(self):
        """Un-block comment current line or selection."""
        # Needed for backward compatibility with Spyder previous blockcomments.
        # See spyder-ide/spyder#2845.
        unblockcomment = self.__unblockcomment()
        if not unblockcomment:
            unblockcomment =  self.__unblockcomment(compatibility=True)
        else:
            return unblockcomment
        self.document_did_change()

    def __unblockcomment(self, compatibility=False):
        """Un-block comment current line or selection helper."""
        def __is_comment_bar(cursor):
            return to_text_string(cursor.block().text()
                           ).startswith(
                         self.__blockcomment_bar(compatibility=compatibility))
        # Finding first comment bar
        cursor1 = self.textCursor()
        if __is_comment_bar(cursor1):
            return
        while not __is_comment_bar(cursor1):
            cursor1.movePosition(QTextCursor.PreviousBlock)
            if cursor1.blockNumber() == 0:
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
                if not compatibility:
                    cursor3.movePosition(QTextCursor.NextCharacter,
                                         QTextCursor.KeepAnchor)
            cursor3.removeSelectedText()
            cursor3.movePosition(QTextCursor.NextBlock)
        for cursor in (cursor2, cursor1):
            cursor3.setPosition(cursor.position())
            cursor3.select(QTextCursor.BlockUnderCursor)
            cursor3.removeSelectedText()
        cursor3.endEditBlock()
        return True

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
        self.document_did_change()

    def kill_line_start(self):
        """Kill the text on the current line from the cursor backward"""
        cursor = self.textCursor()
        cursor.clearSelection()
        cursor.movePosition(QTextCursor.StartOfBlock,
                            QTextCursor.KeepAnchor)
        self._kill_ring.kill_cursor(cursor)
        self.setTextCursor(cursor)
        self.document_did_change()

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
        self.document_did_change()

    def kill_next_word(self):
        """Kill the next word"""
        position = self.textCursor().position()
        cursor = self._get_word_end_cursor(position)
        cursor.setPosition(position, QTextCursor.KeepAnchor)
        self._kill_ring.kill_cursor(cursor)
        self.setTextCursor(cursor)
        self.document_did_change()

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

    def __has_colon_not_in_brackets(self, text):
        """
        Return whether a string has a colon which is not between brackets.
        This function returns True if the given string has a colon which is
        not between a pair of (round, square or curly) brackets. It assumes
        that the brackets in the string are balanced.
        """
        bracket_ext = self.editor_extensions.get(CloseBracketsExtension)
        for pos, char in enumerate(text):
            if (char == ':' and
                    not bracket_ext.unmatched_brackets_in_line(text[:pos])):
                return True
        return False

    def autoinsert_colons(self):
        """Decide if we want to autoinsert colons"""
        bracket_ext = self.editor_extensions.get(CloseBracketsExtension)
        self.completion_widget.hide()
        line_text = self.get_text('sol', 'cursor')
        if not self.textCursor().atBlockEnd():
            return False
        elif self.in_comment_or_string():
            return False
        elif not self.__colon_keyword(line_text):
            return False
        elif self.__forbidden_colon_end_char(line_text):
            return False
        elif bracket_ext.unmatched_brackets_in_line(line_text):
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

    def in_comment(self, cursor=None):
        if self.highlighter:
            current_color = self.__get_current_color(cursor)
            comment_color = self.highlighter.get_color_name('comment')
            if current_color == comment_color:
                return True
            else:
                return False
        else:
            return False

    def in_string(self, cursor=None):
        if self.highlighter:
            current_color = self.__get_current_color(cursor)
            string_color = self.highlighter.get_color_name('string')
            if current_color == string_color:
                return True
            else:
                return False
        else:
            return False

    # ------ Qt Event handlers
    def setup_context_menu(self):
        """Setup context menu"""
        self.undo_action = create_action(
            self, _("Undo"), icon=ima.icon('undo'),
            shortcut=CONF.get_shortcut('editor', 'undo'), triggered=self.undo)
        self.redo_action = create_action(
            self, _("Redo"), icon=ima.icon('redo'),
            shortcut=CONF.get_shortcut('editor', 'redo'), triggered=self.redo)
        self.cut_action = create_action(
            self, _("Cut"), icon=ima.icon('editcut'),
            shortcut=CONF.get_shortcut('editor', 'cut'), triggered=self.cut)
        self.copy_action = create_action(
            self, _("Copy"), icon=ima.icon('editcopy'),
            shortcut=CONF.get_shortcut('editor', 'copy'), triggered=self.copy)
        self.paste_action = create_action(
            self, _("Paste"), icon=ima.icon('editpaste'),
            shortcut=CONF.get_shortcut('editor', 'paste'),
            triggered=self.paste)
        selectall_action = create_action(
            self, _("Select All"), icon=ima.icon('selectall'),
            shortcut=CONF.get_shortcut('editor', 'select all'),
            triggered=self.selectAll)
        toggle_comment_action = create_action(
            self, _("Comment")+"/"+_("Uncomment"), icon=ima.icon('comment'),
            shortcut=CONF.get_shortcut('editor', 'toggle comment'),
            triggered=self.toggle_comment)
        self.clear_all_output_action = create_action(
            self, _("Clear all ouput"), icon=ima.icon('ipython_console'),
            triggered=self.clear_all_output)
        self.ipynb_convert_action = create_action(
            self, _("Convert to Python script"), icon=ima.icon('python'),
            triggered=self.convert_notebook)
        self.gotodef_action = create_action(
            self, _("Go to definition"),
            shortcut=CONF.get_shortcut('editor', 'go to definition'),
            triggered=self.go_to_definition_from_cursor)

        # Run actions
        self.run_cell_action = create_action(
            self, _("Run cell"), icon=ima.icon('run_cell'),
            shortcut=CONF.get_shortcut('editor', 'run cell'),
            triggered=self.sig_run_cell.emit)
        self.run_cell_and_advance_action = create_action(
            self, _("Run cell and advance"), icon=ima.icon('run_cell'),
            shortcut=CONF.get_shortcut('editor', 'run cell and advance'),
            triggered=self.sig_run_cell_and_advance.emit)
        self.re_run_last_cell_action = create_action(
            self, _("Re-run last cell"), icon=ima.icon('run_cell'),
            shortcut=CONF.get_shortcut('editor', 're-run last cell'),
            triggered=self.sig_re_run_last_cell.emit)
        self.run_selection_action = create_action(
            self, _("Run &selection or current line"),
            icon=ima.icon('run_selection'),
            shortcut=CONF.get_shortcut('editor', 'run selection'),
            triggered=self.sig_run_selection.emit)

        self.debug_cell_action = create_action(
            self, _("Debug cell"), icon=ima.icon('debug_cell'),
            shortcut=CONF.get_shortcut('editor', 'debug cell'),
            triggered=self.sig_debug_cell.emit)

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

        # Docstring
        writer = self.writer_docstring
        self.docstring_action = create_action(
            self, _("Generate docstring"),
            shortcut=CONF.get_shortcut('editor', 'docstring'),
            triggered=writer.write_docstring_at_first_line_of_function)

        # Document formatting
        formatter = CONF.get('lsp-server', 'formatting')
        self.format_action = create_action(
            self,
            _('Format file or selection with {0}').format(
                formatter.capitalize()),
            shortcut=CONF.get_shortcut('editor', 'autoformatting'),
            triggered=self.format_document_or_range)

        self.format_action.setEnabled(False)

        # Build menu
        self.menu = QMenu(self)
        actions_1 = [self.run_cell_action, self.run_cell_and_advance_action,
                     self.re_run_last_cell_action, self.run_selection_action,
                     self.gotodef_action, None, self.undo_action,
                     self.redo_action, None, self.cut_action,
                     self.copy_action, self.paste_action, selectall_action]
        actions_2 = [None, zoom_in_action, zoom_out_action, zoom_reset_action,
                     None, toggle_comment_action, self.docstring_action,
                     self.format_action]
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
        self.sig_key_released.emit(event)
        key = event.key()
        direction_keys = {Qt.Key_Up, Qt.Key_Left, Qt.Key_Right, Qt.Key_Down}
        if key in direction_keys:
            self.request_cursor_event()

        # Update decorations after releasing these keys because they don't
        # trigger the emission of the valueChanged signal in
        # verticalScrollBar.
        # See https://bugreports.qt.io/browse/QTBUG-25365
        if key in {Qt.Key_Up,  Qt.Key_Down}:
            self.update_decorations_timer.start()

        # This necessary to run our Pygments highlighter again after the
        # user generated text changes
        if event.text():
            # Stop the active timer and start it again to not run it on
            # every event
            if self.timer_syntax_highlight.isActive():
                self.timer_syntax_highlight.stop()

            # Adjust interval to rehighlight according to the lines
            # present in the file
            total_lines = self.get_line_count()
            if total_lines < 1000:
                self.timer_syntax_highlight.setInterval(600)
            elif total_lines < 2000:
                self.timer_syntax_highlight.setInterval(800)
            else:
                self.timer_syntax_highlight.setInterval(1000)
            self.timer_syntax_highlight.start()

        self._restore_editor_cursor_and_selections()
        super(CodeEditor, self).keyReleaseEvent(event)
        event.ignore()

    def event(self, event):
        """Qt method override."""
        if event.type() == QEvent.ShortcutOverride:
            event.ignore()
            return False
        else:
            return super(CodeEditor, self).event(event)

    def _start_completion_timer(self):
        """Helper to start timer or complete."""
        if self.automatic_completions_after_ms > 0:
            self._timer_autocomplete.start(
                self.automatic_completions_after_ms)
        else:
            self._handle_completions()

    def _handle_keypress_event(self, event):
        """Handle keypress events."""
        TextEditBaseWidget.keyPressEvent(self, event)

        # Trigger the following actions only if the event generates
        # a text change.
        text = to_text_string(event.text())
        if text:
            self.document_did_change()
            self.sig_text_was_inserted.emit()

    def keyPressEvent(self, event):
        """Reimplement Qt method."""
        tab_pressed = False
        if self.completions_hint_after_ms > 0:
            self._completions_hint_idle = False
            self._timer_completions_hint.start(self.completions_hint_after_ms)
        else:
            self._set_completions_hint_idle()

        # Send the signal to the editor's extension.
        event.ignore()
        self.sig_key_pressed.emit(event)

        self.kite_call_to_action.handle_key_press(event)

        key = event.key()
        text = to_text_string(event.text())
        has_selection = self.has_selected_text()
        ctrl = event.modifiers() & Qt.ControlModifier
        shift = event.modifiers() & Qt.ShiftModifier

        if text:
            self.__clear_occurrences()

            # Only ask for completions if there's some text generated
            # as part of the event. Events such as pressing Crtl,
            # Shift or Alt don't generate any text.
            # Fixes spyder-ide/spyder#11021
            self._start_completion_timer()

        if key in {Qt.Key_Up, Qt.Key_Left, Qt.Key_Right, Qt.Key_Down}:
            self.hide_tooltip()

        if QToolTip.isVisible():
            self.hide_tooltip_if_necessary(key)

        if event.isAccepted():
            # The event was handled by one of the editor extension.
            return

        if key in [Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt,
                   Qt.Key_Meta, Qt.KeypadModifier]:
            # The user pressed only a modifier key.
            if ctrl:
                pos = self.mapFromGlobal(QCursor.pos())
                pos = self.calculate_real_position_from_global(pos)
                if self._handle_goto_uri_event(pos):
                    event.accept()
                    return

                if self._handle_goto_definition_event(pos):
                    event.accept()
                    return
            return

        # ---- Handle hard coded and builtin actions
        operators = {'+', '-', '*', '**', '/', '//', '%', '@', '<<', '>>',
                     '&', '|', '^', '~', '<', '>', '<=', '>=', '==', '!='}
        delimiters = {',', ':', ';', '@', '=', '->', '+=', '-=', '*=', '/=',
                      '//=', '%=', '@=', '&=', '|=', '^=', '>>=', '<<=', '**='}

        if text not in self.auto_completion_characters:
            if text in operators or text in delimiters:
                self.completion_widget.hide()
        if key in (Qt.Key_Enter, Qt.Key_Return):
            if not shift and not ctrl:
                if (self.add_colons_enabled and self.is_python_like() and
                        self.autoinsert_colons()):
                    self.textCursor().beginEditBlock()
                    self.insert_text(':' + self.get_line_separator())
                    if self.strip_trailing_spaces_on_modify:
                        self.fix_and_strip_indent()
                    else:
                        self.fix_indent()
                    self.textCursor().endEditBlock()
                elif self.is_completion_widget_visible():
                    self.select_completion_list()
                else:
                    self.textCursor().beginEditBlock()
                    cur_indent = self.get_block_indentation(
                        self.textCursor().blockNumber())
                    self._handle_keypress_event(event)
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

                    if self.strip_trailing_spaces_on_modify:
                        self.fix_and_strip_indent(
                            comment_or_string=cmt_or_str,
                            cur_indent=cur_indent)
                    else:
                        self.fix_indent(comment_or_string=cmt_or_str,
                                        cur_indent=cur_indent)
                    self.textCursor().endEditBlock()
        elif key == Qt.Key_Insert and not shift and not ctrl:
            self.setOverwriteMode(not self.overwriteMode())
        elif key == Qt.Key_Backspace and not shift and not ctrl:
            leading_text = self.get_text('sol', 'cursor')
            leading_length = len(leading_text)
            trailing_spaces = leading_length - len(leading_text.rstrip())
            if has_selection or not self.intelligent_backspace:
                self._handle_keypress_event(event)
            else:
                trailing_text = self.get_text('cursor', 'eol')
                matches = ('()', '[]', '{}', '\'\'', '""')
                if (not leading_text.strip() and
                        (leading_length > len(self.indent_chars))):
                    if leading_length % len(self.indent_chars) == 0:
                        self.unindent()
                    else:
                        self._handle_keypress_event(event)
                elif trailing_spaces and not trailing_text.strip():
                    self.remove_suffix(leading_text[-trailing_spaces:])
                elif (leading_text and trailing_text and
                        (leading_text[-1] + trailing_text[0] in matches)):
                    cursor = self.textCursor()
                    cursor.movePosition(QTextCursor.PreviousCharacter)
                    cursor.movePosition(QTextCursor.NextCharacter,
                                        QTextCursor.KeepAnchor, 2)
                    cursor.removeSelectedText()
                    self.document_did_change()
                else:
                    self._handle_keypress_event(event)
        elif key == Qt.Key_Home:
            self.stdkey_home(shift, ctrl)
        elif key == Qt.Key_End:
            # See spyder-ide/spyder#495: on MacOS X, it is necessary to
            # redefine this basic action which should have been implemented
            # natively
            self.stdkey_end(shift, ctrl)
        elif text in self.auto_completion_characters:
            self.insert_text(text)
            if text == ".":
                if not self.in_comment_or_string():
                    text = self.get_text('sol', 'cursor')
                    last_obj = getobj(text)
                    prev_char = text[-2] if len(text) > 1 else ''
                    if (prev_char in {')', ']', '}'} or
                            (last_obj and not last_obj.isdigit())):
                        # Completions should be triggered immediately when
                        # an autocompletion character is introduced.
                        self.do_completion(automatic=True)
            else:
                self.do_completion(automatic=True)
        elif (text in self.signature_completion_characters and
                not self.has_selected_text()):
            self.insert_text(text)
            self.request_signature()
        elif (key == Qt.Key_Colon and not has_selection and
                self.auto_unindent_enabled):
            leading_text = self.get_text('sol', 'cursor')
            if leading_text.lstrip() in ('else', 'finally'):
                ind = lambda txt: len(txt) - len(txt.lstrip())
                prevtxt = (to_text_string(self.textCursor().block().
                           previous().text()))
                if self.language == 'Python':
                    prevtxt = prevtxt.rstrip()
                if ind(leading_text) == ind(prevtxt):
                    self.unindent(force=True)
            self._handle_keypress_event(event)
        elif (key == Qt.Key_Space and not shift and not ctrl and not
                has_selection and self.auto_unindent_enabled):
            self.completion_widget.hide()
            leading_text = self.get_text('sol', 'cursor')
            if leading_text.lstrip() in ('elif', 'except'):
                ind = lambda txt: len(txt)-len(txt.lstrip())
                prevtxt = (to_text_string(self.textCursor().block().
                           previous().text()))
                if self.language == 'Python':
                    prevtxt = prevtxt.rstrip()
                if ind(leading_text) == ind(prevtxt):
                    self.unindent(force=True)
            self._handle_keypress_event(event)
        elif key == Qt.Key_Tab and not ctrl:
            # Important note: <TAB> can't be called with a QShortcut because
            # of its singular role with respect to widget focus management
            tab_pressed = True
            if not has_selection and not self.tab_mode:
                self.intelligent_tab()
            else:
                # indent the selected text
                self.indent_or_replace()
        elif key == Qt.Key_Backtab and not ctrl:
            # Backtab, i.e. Shift+<TAB>, could be treated as a QShortcut but
            # there is no point since <TAB> can't (see above)
            tab_pressed = True
            if not has_selection and not self.tab_mode:
                self.intelligent_backtab()
            else:
                # indent the selected text
                self.unindent()
            event.accept()
        elif not event.isAccepted():
            self._handle_keypress_event(event)

        self._last_key_pressed_text = text
        self._last_pressed_key = key
        if self.automatic_completions_after_ms == 0 and not tab_pressed:
            self._handle_completions()

        if not event.modifiers():
            # Accept event to avoid it being handled by the parent.
            # Modifiers should be passed to the parent because they
            # could be shortcuts
            event.accept()

    def _handle_completions(self):
        """Handle on the fly completions after delay."""
        cursor = self.textCursor()
        pos = cursor.position()
        cursor.select(QTextCursor.WordUnderCursor)
        text = to_text_string(cursor.selectedText())

        key = self._last_pressed_key
        if key is not None:
            if key in [Qt.Key_Return, Qt.Key_Escape,
                       Qt.Key_Tab, Qt.Key_Backtab, Qt.Key_Space]:
                self._last_pressed_key = None
                return

        # Correctly handle completions when Backspace key is pressed.
        # We should not show the widget if deleting a space before a word.
        if key == Qt.Key_Backspace:
            cursor.setPosition(pos - 1, QTextCursor.MoveAnchor)
            cursor.select(QTextCursor.WordUnderCursor)
            prev_text = to_text_string(cursor.selectedText())
            cursor.setPosition(pos - 1, QTextCursor.MoveAnchor)
            cursor.setPosition(pos, QTextCursor.KeepAnchor)
            prev_char = cursor.selectedText()
            if prev_text == '' or prev_char in (u'\u2029', ' ', '\t'):
                return

        # Text might be after a dot '.'
        if text == '':
            cursor.setPosition(pos - 1, QTextCursor.MoveAnchor)
            cursor.select(QTextCursor.WordUnderCursor)
            text = to_text_string(cursor.selectedText())
            if text != '.':
                text = ''

        # WordUnderCursor fails if the cursor is next to a right brace.
        # If the returned text starts with it, we move to the left.
        if text.startswith((')', ']', '}')):
            cursor.setPosition(pos - 1, QTextCursor.MoveAnchor)
            cursor.select(QTextCursor.WordUnderCursor)
            text = to_text_string(cursor.selectedText())

        self.document_did_change(text)

        is_backspace = (
            self.is_completion_widget_visible() and key == Qt.Key_Backspace)

        if (len(text) >= self.automatic_completions_after_chars
                and self._last_key_pressed_text or is_backspace):
            # Perform completion on the fly
            if self.automatic_completions and not self.in_comment_or_string():
                # Variables can include numbers and underscores
                if (text.isalpha() or text.isalnum() or '_' in text
                        or '.' in text):
                    self.do_completion(automatic=True)
                    self._last_key_pressed_text = ''
                    self._last_pressed_key = None

    def fix_and_strip_indent(self, *args, **kwargs):
        """
        Automatically fix indent and strip previous automatic indent.

        args and kwargs are forwarded to self.fix_indent
        """
        # Fix indent
        cursor_before = self.textCursor().position()
        # A change just occurred on the last line (return was pressed)
        if cursor_before > 0:
            self.last_change_position = cursor_before - 1
        self.fix_indent(*args, **kwargs)
        cursor_after = self.textCursor().position()
        # Remove previous spaces and update last_auto_indent
        nspaces_removed = self.strip_trailing_spaces()
        self.last_auto_indent = (cursor_before - nspaces_removed,
                                 cursor_after - nspaces_removed)
        self.document_did_change()

    def run_pygments_highlighter(self):
        """Run pygments highlighter."""
        if isinstance(self.highlighter, sh.PygmentsSH):
            self.highlighter.make_charlist()

    def get_pattern_at(self, coordinates):
        """
        Return key, text and cursor for pattern (if found at coordinates).
        """
        return self.get_pattern_cursor_at(self.highlighter.patterns,
                                          coordinates)

    def get_pattern_cursor_at(self, pattern, coordinates):
        """
        Find pattern located at the line where the coordinate is located.

        This returns the actual match and the cursor that selects the text.
        """
        cursor, key, text = None, None, None
        break_loop = False

        # Check if the pattern is in line
        line = self.get_line_at(coordinates)
        match = pattern.search(line)

        while match:
            for key, value in list(match.groupdict().items()):
                if value:
                    start, end = sh.get_span(match)

                    # Get cursor selection if pattern found
                    cursor = self.cursorForPosition(coordinates)
                    cursor.movePosition(QTextCursor.StartOfBlock)
                    line_start_position = cursor.position()

                    cursor.setPosition(line_start_position + start,
                                       cursor.MoveAnchor)
                    start_rect = self.cursorRect(cursor)
                    cursor.setPosition(line_start_position + end,
                                       cursor.MoveAnchor)
                    end_rect = self.cursorRect(cursor)
                    bounding_rect = start_rect.united(end_rect)

                    # Check coordinates are located within the selection rect
                    if bounding_rect.contains(coordinates):
                        text = line[start:end]
                        cursor.setPosition(line_start_position + start,
                                           cursor.KeepAnchor)
                        break_loop = True
                        break

            if break_loop:
                break

            match = pattern.search(line, end)

        return key, text, cursor

    def _preprocess_file_uri(self, uri):
        """Format uri to conform to absolute or relative file paths."""
        fname = uri.replace('file://', '')
        if fname[-1] == '/':
            fname = fname[:-1]

        # ^/ is used to denote the current project root
        if fname.startswith("^/"):
            if self.current_project_path is not None:
                fname = osp.join(self.current_project_path, fname[2:])
            else:
                fname = fname.replace("^/", "~/")

        if fname.startswith("~/"):
            fname = osp.expanduser(fname)

        dirname = osp.dirname(osp.abspath(self.filename))
        if osp.isdir(dirname):
            if not osp.isfile(fname):
                # Maybe relative
                fname = osp.join(dirname, fname)

        self.sig_file_uri_preprocessed.emit(fname)

        return fname

    def _handle_goto_definition_event(self, pos):
        """Check if goto definition can be applied and apply highlight."""
        text = self.get_word_at(pos)
        if text and not sourcecode.is_keyword(to_text_string(text)):
            if not self.__cursor_changed:
                QApplication.setOverrideCursor(QCursor(Qt.PointingHandCursor))
                self.__cursor_changed = True
            cursor = self.cursorForPosition(pos)
            cursor.select(QTextCursor.WordUnderCursor)
            self.clear_extra_selections('ctrl_click')
            self.highlight_selection(
                'ctrl_click', cursor, update=True,
                foreground_color=self.ctrl_click_color,
                underline_color=self.ctrl_click_color,
                underline_style=QTextCharFormat.SingleUnderline)
            return True
        else:
            return False

    def _handle_goto_uri_event(self, pos):
        """Check if go to uri can be applied and apply highlight."""
        key, pattern_text, cursor = self.get_pattern_at(pos)
        if key and pattern_text and cursor:
            self._last_hover_pattern_key = key
            self._last_hover_pattern_text = pattern_text

            color = self.ctrl_click_color

            if key in ['file']:
                fname = self._preprocess_file_uri(pattern_text)
                if not osp.isfile(fname):
                    color = QColor(255, 80, 80)

            self.clear_extra_selections('ctrl_click')
            self.highlight_selection(
                'ctrl_click', cursor, update=True,
                foreground_color=color,
                underline_color=color,
                underline_style=QTextCharFormat.SingleUnderline)

            if not self.__cursor_changed:
                QApplication.setOverrideCursor(
                    QCursor(Qt.PointingHandCursor))
                self.__cursor_changed = True

            self.sig_uri_found.emit(pattern_text)
            return True
        else:
            self._last_hover_pattern_key = key
            self._last_hover_pattern_text = pattern_text
            return False

    def go_to_uri_from_cursor(self, uri):
        """Go to url from cursor and defined hover patterns."""
        key = self._last_hover_pattern_key
        full_uri = uri

        if key in ['file']:
            fname = self._preprocess_file_uri(uri)

            if osp.isfile(fname) and encoding.is_text_file(fname):
                # Open in editor
                self.go_to_definition.emit(fname, 0, 0)
            else:
                # Use external program
                fname = file_uri(fname)
                programs.start_file(fname)
        elif key in ['mail', 'url']:
            if '@' in uri and not uri.startswith('mailto:'):
                full_uri = 'mailto:' + uri
            quri = QUrl(full_uri)
            QDesktopServices.openUrl(quri)
        elif key in ['issue']:
            # Issue URI
            repo_url = uri.replace('#', '/issues/')
            if uri.startswith(('gh-', 'bb-', 'gl-')):
                number = uri[3:]
                remotes = get_git_remotes(self.filename)
                remote = remotes.get('upstream', remotes.get('origin'))
                if remote:
                    full_uri = remote_to_url(remote) + '/issues/' + number
                else:
                    full_uri = None
            elif uri.startswith('gh:') or ':' not in uri:
                # Github
                repo_and_issue = repo_url
                if uri.startswith('gh:'):
                    repo_and_issue = repo_url[3:]
                full_uri = 'https://github.com/' + repo_and_issue
            elif uri.startswith('gl:'):
                # Gitlab
                full_uri = 'https://gitlab.com/' + repo_url[3:]
            elif uri.startswith('bb:'):
                # Bitbucket
                full_uri = 'https://bitbucket.org/' + repo_url[3:]

            if full_uri:
                quri = QUrl(full_uri)
                QDesktopServices.openUrl(quri)
            else:
                QMessageBox.information(
                    self,
                    _('Information'),
                    _('This file is not part of a local repository or '
                      'upstream/origin remotes are not defined!'),
                    QMessageBox.Ok,
                )
        self.sig_go_to_uri.emit(uri)
        self.hide_tooltip()
        return full_uri

    def line_range(self, position):
        """
        Get line range from position.
        """
        if position is None:
            return None
        if position >= self.document().characterCount():
            return None
        # Check if still on the line
        cursor = self.textCursor()
        cursor.setPosition(position)
        line_range = (cursor.block().position(),
                      cursor.block().position()
                      + cursor.block().length() - 1)
        return line_range

    def strip_trailing_spaces(self):
        """
        Strip trailing spaces if needed.

        Remove trailing whitespace on leaving a non-string line containing it.
        Return the number of removed spaces.
        """
        if not running_under_pytest():
            if not self.hasFocus():
                # Avoid problem when using split editor
                return 0
        # Update current position
        current_position = self.textCursor().position()
        last_position = self.last_position
        self.last_position = current_position

        if self.skip_rstrip:
            return 0

        line_range = self.line_range(last_position)
        if line_range is None:
            # Doesn't apply
            return 0

        def pos_in_line(pos):
            """Check if pos is in last line."""
            if pos is None:
                return False
            return line_range[0] <= pos <= line_range[1]

        if pos_in_line(current_position):
            # Check if still on the line
            return 0

        # Check if end of line in string
        cursor = self.textCursor()
        cursor.setPosition(line_range[1])

        if (not self.strip_trailing_spaces_on_modify
                or self.in_string(cursor=cursor)):
            if self.last_auto_indent is None:
                return 0
            elif (self.last_auto_indent !=
                  self.line_range(self.last_auto_indent[0])):
                # line not empty
                self.last_auto_indent = None
                return 0
            line_range = self.last_auto_indent
            self.last_auto_indent = None
        elif not pos_in_line(self.last_change_position):
            # Should process if pressed return or made a change on the line:
            return 0

        cursor.setPosition(line_range[0])
        cursor.setPosition(line_range[1],
                           QTextCursor.KeepAnchor)
        # remove spaces on the right
        text = cursor.selectedText()
        strip = text.rstrip()
        # I think all the characters we can strip are in a single QChar.
        # Therefore there shouldn't be any length problems.
        N_strip = qstring_length(text[len(strip):])

        if N_strip > 0:
            # Select text to remove
            cursor.setPosition(line_range[1] - N_strip)
            cursor.setPosition(line_range[1],
                               QTextCursor.KeepAnchor)
            cursor.removeSelectedText()
            self.document_did_change()
            # Correct last change position
            self.last_change_position = line_range[1]
            self.last_position = self.textCursor().position()
            return N_strip
        return 0

    def mouseMoveEvent(self, event):
        """Underline words when pressing <CONTROL>"""
        # Restart timer every time the mouse is moved
        # This is needed to correctly handle hover hints with a delay
        self._timer_mouse_moving.start()

        pos = event.pos()
        self._last_point = pos
        alt = event.modifiers() & Qt.AltModifier
        ctrl = event.modifiers() & Qt.ControlModifier
        shift = event.modifiers() & Qt.ShiftModifier

        if alt:
            self.sig_alt_mouse_moved.emit(event)
            event.accept()
            return

        if ctrl:
            if self._handle_goto_uri_event(pos):
                event.accept()
                return

        if self.has_selected_text():
            TextEditBaseWidget.mouseMoveEvent(self, event)
            return

        if self.go_to_definition_enabled and ctrl:
            if self._handle_goto_definition_event(pos):
                event.accept()
                return

        if self.__cursor_changed:
            self._restore_editor_cursor_and_selections()
        else:
            if (not self._should_display_hover(pos)
                    and not self.is_completion_widget_visible()):
                self.hide_tooltip()

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

    def focusOutEvent(self, event):
        """Extend Qt method"""
        self.sig_focus_changed.emit()
        self._restore_editor_cursor_and_selections()
        super(CodeEditor, self).focusOutEvent(event)

    def focusInEvent(self, event):
        formatting_enabled = getattr(self, 'formatting_enabled', False)
        self.sig_refresh_formatting.emit(formatting_enabled)
        super(CodeEditor, self).focusInEvent(event)

    def leaveEvent(self, event):
        """Extend Qt method"""
        self.sig_leave_out.emit()
        self._restore_editor_cursor_and_selections()
        TextEditBaseWidget.leaveEvent(self, event)

    def mousePressEvent(self, event):
        """Override Qt method."""
        self.hide_tooltip()
        self.kite_call_to_action.handle_mouse_press(event)

        ctrl = event.modifiers() & Qt.ControlModifier
        alt = event.modifiers() & Qt.AltModifier
        pos = event.pos()
        self._mouse_left_button_pressed = event.button() == Qt.LeftButton

        if event.button() == Qt.LeftButton and ctrl:
            TextEditBaseWidget.mousePressEvent(self, event)
            cursor = self.cursorForPosition(pos)
            uri = self._last_hover_pattern_text
            if uri:
                self.go_to_uri_from_cursor(uri)
            else:
                self.go_to_definition_from_cursor(cursor)
        elif event.button() == Qt.LeftButton and alt:
            self.sig_alt_left_mouse_pressed.emit(event)
        else:
            TextEditBaseWidget.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        """Override Qt method."""
        if event.button() == Qt.LeftButton:
            self._mouse_left_button_pressed = False

        self.request_cursor_event()
        TextEditBaseWidget.mouseReleaseEvent(self, event)

    def contextMenuEvent(self, event):
        """Reimplement Qt method"""
        nonempty_selection = self.has_selected_text()
        self.copy_action.setEnabled(nonempty_selection)
        self.cut_action.setEnabled(nonempty_selection)
        self.clear_all_output_action.setVisible(self.is_json() and
                                                nbformat is not None)
        self.ipynb_convert_action.setVisible(self.is_json() and
                                             nbformat is not None)
        self.run_cell_action.setVisible(self.is_python())
        self.run_cell_and_advance_action.setVisible(self.is_python())
        self.run_selection_action.setVisible(self.is_python())
        self.re_run_last_cell_action.setVisible(self.is_python())
        self.gotodef_action.setVisible(self.go_to_definition_enabled)

        formatter = CONF.get('lsp-server', 'formatting')
        self.format_action.setText(_(
            'Format file or selection with {0}').format(
                formatter.capitalize()))

        # Check if a docstring is writable
        writer = self.writer_docstring
        writer.line_number_cursor = self.get_line_number_at(event.pos())
        result = writer.get_function_definition_from_first_line()

        if result:
            self.docstring_action.setEnabled(True)
        else:
            self.docstring_action.setEnabled(False)

        # Code duplication go_to_definition_from_cursor and mouse_move_event
        cursor = self.textCursor()
        text = to_text_string(cursor.selectedText())
        if len(text) == 0:
            cursor.select(QTextCursor.WordUnderCursor)
            text = to_text_string(cursor.selectedText())

        self.undo_action.setEnabled(self.document().isUndoAvailable())
        self.redo_action.setEnabled(self.document().isRedoAvailable())
        menu = self.menu
        if self.isReadOnly():
            menu = self.readonly_menu
        menu.popup(event.globalPos())
        event.accept()

    def _restore_editor_cursor_and_selections(self):
        """Restore the cursor and extra selections of this code editor."""
        if self.__cursor_changed:
            self.__cursor_changed = False
            QApplication.restoreOverrideCursor()
            self.clear_extra_selections('ctrl_click')
            self._last_hover_pattern_key = None
            self._last_hover_pattern_text = None

    #------ Drag and drop
    def dragEnterEvent(self, event):
        """
        Reimplemented Qt method.

        Inform Qt about the types of data that the widget accepts.
        """
        logger.debug("dragEnterEvent was received")
        all_urls = mimedata2url(event.mimeData())
        if all_urls:
            # Let the parent widget handle this
            logger.debug("Let the parent widget handle this dragEnterEvent")
            event.ignore()
        else:
            logger.debug("Call TextEditBaseWidget dragEnterEvent method")
            TextEditBaseWidget.dragEnterEvent(self, event)

    def dropEvent(self, event):
        """
        Reimplemented Qt method.

        Unpack dropped data and handle it.
        """
        logger.debug("dropEvent was received")
        if mimedata2url(event.mimeData()):
            logger.debug("Let the parent widget handle this")
            event.ignore()
        else:
            logger.debug("Call TextEditBaseWidget dropEvent method")
            TextEditBaseWidget.dropEvent(self, event)
            self.document_did_change()

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
                if is_cell_header(block):
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

    def popup_docstring(self, prev_text, prev_pos):
        """Show the menu for generating docstring."""
        line_text = self.textCursor().block().text()
        if line_text != prev_text:
            return

        if prev_pos != self.textCursor().position():
            return

        writer = self.writer_docstring
        if writer.get_function_definition_from_below_last_line():
            point = self.cursorRect().bottomRight()
            point = self.calculate_real_position(point)
            point = self.mapToGlobal(point)

            self.menu_docstring = QMenuOnlyForEnter(self)
            self.docstring_action = create_action(
                self, _("Generate docstring"), icon=ima.icon('TextFileIcon'),
                triggered=writer.write_docstring)
            self.menu_docstring.addAction(self.docstring_action)
            self.menu_docstring.setActiveAction(self.docstring_action)
            self.menu_docstring.popup(point)

    def delayed_popup_docstring(self):
        """Show context menu for docstring.

        This method is called after typing '''. After typing ''', this function
        waits 300ms. If there was no input for 300ms, show the context menu.
        """
        line_text = self.textCursor().block().text()
        pos = self.textCursor().position()

        timer = QTimer()
        timer.singleShot(300, lambda: self.popup_docstring(line_text, pos))

    def set_current_project_path(self, root_path=None):
        """
        Set the current active project root path.

        Parameters
        ----------
        root_path: str or None, optional
            Path to current project root path. Default is None.
        """
        self.current_project_path = root_path

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
        self.setWindowIcon(ima.icon('spyder'))

    def load(self, filename):
        self.editor.set_text_from_file(filename)
        self.setWindowTitle("%s - %s (%s)" % (_("Editor"),
                                              osp.basename(filename),
                                              osp.dirname(filename)))
        self.editor.hide_tooltip()


def test(fname):
    from spyder.utils.qthelpers import qapplication
    app = qapplication(test_time=5)
    win = TestWidget(None)
    win.show()
    win.load(fname)
    win.resize(900, 700)
    sys.exit(app.exec_())


if __name__ == '__main__':
    if len(sys.argv) > 1:
        fname = sys.argv[1]
    else:
        fname = __file__
    test(fname)
