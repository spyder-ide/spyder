# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Language Server Protocol configuration tabs.
"""

# Standard library imports
import copy
import os.path as osp
import re
import sys

# Third party imports
from qtpy.compat import getsavefilename, getopenfilename
from qtpy.QtCore import Qt, Slot
from qtpy.QtWidgets import (QComboBox, QGroupBox, QGridLayout, QLabel,
                            QMessageBox, QPushButton, QTabWidget, QVBoxLayout,
                            QWidget, QFileDialog)

# Local imports
from spyder.api.preferences import SpyderPreferencesTab
from spyder.config.base import _
from spyder.config.manager import CONF
from spyder.config.gui import is_dark_interface
from spyder.plugins.completion.api import SUPPORTED_LANGUAGES
from spyder.plugins.completion.providers.languageserver.widgets.serversconfig import (
    LSPServerTable)
# from spyder.plugins.completion.languageserver.widgets.snippetsconfig import (
#     SnippetModelsProxy, SnippetTable, LSP_LANGUAGES_PY, PYTHON_POS)
# from spyder.plugins.completion.manager.api import LSP_LANGUAGES
from spyder.plugins.preferences.api import GeneralConfigPage
from spyder.utils import icon_manager as ima
from spyder.utils.misc import check_connection_port

LSP_URL = "https://microsoft.github.io/language-server-protocol"


class IntrospectionConfigTab(SpyderPreferencesTab):
    """Introspection settings tab."""

    TITLE = _('Introspection')
    CTRL = "Cmd" if sys.platform == 'darwin' else "Ctrl"

    def __init__(self, parent):
        super().__init__(parent)
        newcb = self.create_checkbox

        introspection_group = QGroupBox(_("Basic features"))
        goto_definition_box = newcb(
            _("Enable Go to definition"),
            'jedi_definition',
            tip=_("If enabled, left-clicking on an object name while \n"
                  "pressing the {} key will go to that object's definition\n"
                  "(if resolved).").format(self.CTRL))
        follow_imports_box = newcb(_("Follow imports when going to a "
                                     "definition"),
                                   'jedi_definition/follow_imports')
        show_signature_box = newcb(_("Show calltips"), 'jedi_signature_help')
        enable_hover_hints_box = newcb(
            _("Enable hover hints"),
            'enable_hover_hints',
            tip=_("If enabled, hovering the mouse pointer over an object\n"
                  "name will display that object's signature and/or\n"
                  "docstring (if present)."))
        introspection_layout = QVBoxLayout()
        introspection_layout.addWidget(goto_definition_box)
        introspection_layout.addWidget(follow_imports_box)
        introspection_layout.addWidget(show_signature_box)
        introspection_layout.addWidget(enable_hover_hints_box)
        introspection_group.setLayout(introspection_layout)

        goto_definition_box.toggled.connect(follow_imports_box.setEnabled)

        # Advanced group
        advanced_group = QGroupBox(_("Advanced"))
        modules_textedit = self.create_textedit(
            _("Preload the following modules to make completion faster "
              "and more accurate:"),
            'preload_modules'
        )
        if is_dark_interface():
            modules_textedit.textbox.setStyleSheet(
                "border: 1px solid #32414B;"
            )

        advanced_layout = QVBoxLayout()
        advanced_layout.addWidget(modules_textedit)
        advanced_group.setLayout(advanced_layout)

        layout = QVBoxLayout()
        layout.addWidget(introspection_group)
        layout.addWidget(advanced_group)
        layout.addStretch(1)
        self.setLayout(layout)


class LintingConfigPage(SpyderPreferencesTab):
    """Linting configuration tab."""

    TITLE = _('Linting')

    def __init__(self, parent):
        super().__init__(parent)
        newcb = self.create_checkbox

        linting_label = QLabel(_("Spyder can optionally highlight syntax "
                                 "errors and possible problems with your "
                                 "code in the editor."))
        linting_label.setOpenExternalLinks(True)
        linting_label.setWordWrap(True)
        linting_check = self.create_checkbox(
            _("Enable basic linting"),
            'pyflakes')
        underline_errors_box = newcb(
            _("Underline errors and warnings"),
            'underline_errors',
            section='editor')
        linting_complexity_box = self.create_checkbox(
            _("Enable complexity linting with the Mccabe package"),
            'mccabe')

        # Linting layout
        linting_layout = QVBoxLayout()
        linting_layout.addWidget(linting_label)
        linting_layout.addWidget(linting_check)
        linting_layout.addWidget(underline_errors_box)
        linting_layout.addWidget(linting_complexity_box)
        self.setLayout(linting_layout)
        linting_check.toggled.connect(underline_errors_box.setEnabled)


class FormattingStyleConfigTab(SpyderPreferencesTab):
    """Code style and formatting tab."""

    TITLE = _('Code style and formatting')

    def __init__(self, parent):
        super().__init__(parent)
        newcb = self.create_checkbox

        pep_url = (
            '<a href="https://www.python.org/dev/peps/pep-0008">PEP 8</a>')
        code_style_codes_url = _(
            "<a href='http://pycodestyle.pycqa.org/en/stable"
            "/intro.html#error-codes'>pycodestyle error codes</a>")
        code_style_label = QLabel(
            _("Spyder can use pycodestyle to analyze your code for "
              "conformance to the {} convention. You can also "
              "manually show or hide specific warnings by their "
              "{}.").format(pep_url, code_style_codes_url))
        code_style_label.setOpenExternalLinks(True)
        code_style_label.setWordWrap(True)

        # Code style checkbox
        self.code_style_check = self.create_checkbox(
            _("Enable code style linting"),
            'pycodestyle')

        # Code style options
        self.code_style_filenames_match = self.create_lineedit(
            _("Only check filenames matching these patterns:"),
            'pycodestyle/filename', alignment=Qt.Horizontal, word_wrap=False,
            placeholder=_("Check Python files: *.py"))
        self.code_style_exclude = self.create_lineedit(
            _("Exclude files or directories matching these patterns:"),
            'pycodestyle/exclude', alignment=Qt.Horizontal, word_wrap=False,
            placeholder=_("Exclude all test files: (?!test_).*\\.py"))
        code_style_select = self.create_lineedit(
            _("Show the following errors or warnings:").format(
                code_style_codes_url),
            'pycodestyle/select', alignment=Qt.Horizontal, word_wrap=False,
            placeholder=_("Example codes: E113, W391"))
        code_style_ignore = self.create_lineedit(
            _("Ignore the following errors or warnings:"),
            'pycodestyle/ignore', alignment=Qt.Horizontal, word_wrap=False,
            placeholder=_("Example codes: E201, E303"))
        self.code_style_max_line_length = self.create_spinbox(
            _("Maximum allowed line length:"), None,
            'pycodestyle/max_line_length', min_=10, max_=500, step=1,
            tip=_("Default is 79"))

        vertical_line_box = newcb(
            _("Show vertical line at that length"), 'edge_line',
            section='editor')

        # Code style layout
        code_style_g_layout = QGridLayout()
        code_style_g_layout.addWidget(
            self.code_style_filenames_match.label, 1, 0)
        code_style_g_layout.addWidget(
            self.code_style_filenames_match.textbox, 1, 1)
        code_style_g_layout.addWidget(self.code_style_exclude.label, 2, 0)
        code_style_g_layout.addWidget(self.code_style_exclude.textbox, 2, 1)
        code_style_g_layout.addWidget(code_style_select.label, 3, 0)
        code_style_g_layout.addWidget(code_style_select.textbox, 3, 1)
        code_style_g_layout.addWidget(code_style_ignore.label, 4, 0)
        code_style_g_layout.addWidget(code_style_ignore.textbox, 4, 1)

        # Set Code style options enabled/disabled
        code_style_g_widget = QWidget()
        code_style_g_widget.setLayout(code_style_g_layout)
        code_style_g_widget.setEnabled(self.get_option('pycodestyle'))
        self.code_style_check.toggled.connect(code_style_g_widget.setEnabled)

        # Code style layout
        code_style_group = QGroupBox(_("Code style"))
        code_style_layout = QVBoxLayout()
        code_style_layout.addWidget(code_style_label)
        code_style_layout.addWidget(self.code_style_check)
        code_style_layout.addWidget(code_style_g_widget)
        code_style_group.setLayout(code_style_layout)

        # Maximum allowed line length layout
        line_length_group = QGroupBox(_("Line length"))
        line_length_layout = QVBoxLayout()
        line_length_layout.addWidget(self.code_style_max_line_length)
        line_length_layout.addWidget(vertical_line_box)
        line_length_group.setLayout(line_length_layout)

        # Code formatting label
        autopep8_url = (
            "<a href='https://github.com/hhatto/autopep8'>Autopep8</a>"
        )
        yapf_url = (
            "<a href='https://github.com/google/yapf'>Yapf</a>"
        )
        black_url = (
            "<a href='https://black.readthedocs.io/en/stable'>Black</a>"
        )
        code_fmt_label = QLabel(
            _("Spyder can use {0}, {1} or {2} to format your code for "
              "conformance to the {3} convention.").format(
                  autopep8_url, yapf_url, black_url, pep_url))
        code_fmt_label.setOpenExternalLinks(True)
        code_fmt_label.setWordWrap(True)

        # Code formatting providers
        code_fmt_provider = self.create_combobox(
            _("Choose the code formatting provider: "),
            (("autopep8", 'autopep8'),
             ("black", 'black')),
            'formatting')

        # Autoformat on save
        format_on_save_box = newcb(
            _("Autoformat files on save"),
            'format_on_save',
            tip=_("If enabled, autoformatting will take place when "
                  "saving a file"))

        # Code formatting layout
        code_fmt_group = QGroupBox(_("Code formatting"))
        code_fmt_layout = QVBoxLayout()
        code_fmt_layout.addWidget(code_fmt_label)
        code_fmt_layout.addWidget(code_fmt_provider)
        code_fmt_layout.addWidget(format_on_save_box)
        code_fmt_group.setLayout(code_fmt_layout)

        code_style_fmt_layout = QVBoxLayout()
        code_style_fmt_layout.addWidget(code_style_group)
        code_style_fmt_layout.addWidget(code_fmt_group)
        code_style_fmt_layout.addWidget(line_length_group)
        self.setLayout(code_style_fmt_layout)


class DocstringConfigTab(SpyderPreferencesTab):
    """Docstring style configuration tab."""

    TITLE = _('Docstring style')

    def __init__(self, parent):
        super().__init__(parent)

        numpy_url = (
            "<a href='https://numpydoc.readthedocs.io/en/"
            "latest/format.html'>Numpy</a>")
        pep257_url = (
            "<a href='https://www.python.org/dev/peps/pep-0257/'>PEP 257</a>")
        docstring_style_codes = _(
            "<a href='http://www.pydocstyle.org/en/stable"
            "/error_codes.html'>page</a>")
        docstring_style_label = QLabel(
            _("Here you can decide if you want to perform style analysis on "
              "your docstrings according to the {} or {} conventions. You can "
              "also decide if you want to show or ignore specific errors, "
              "according to the codes found on this {}.").format(
                  numpy_url, pep257_url, docstring_style_codes))
        docstring_style_label.setOpenExternalLinks(True)
        docstring_style_label.setWordWrap(True)

        # Docstring style checkbox
        self.docstring_style_check = self.create_checkbox(
            _("Enable docstring style linting"),
            'pydocstyle')

        # Docstring style options
        docstring_style_convention = self.create_combobox(
            _("Choose the convention used to lint docstrings: "),
            (("Numpy", 'numpy'),
             ("PEP 257", 'pep257'),
             ("Custom", 'custom')),
            'pydocstyle/convention')
        self.docstring_style_select = self.create_lineedit(
            _("Show the following errors:"),
            'pydocstyle/select', alignment=Qt.Horizontal, word_wrap=False,
            placeholder=_("Example codes: D413, D414"))
        self.docstring_style_ignore = self.create_lineedit(
            _("Ignore the following errors:"),
            'pydocstyle/ignore', alignment=Qt.Horizontal, word_wrap=False,
            placeholder=_("Example codes: D107, D402"))
        self.docstring_style_match = self.create_lineedit(
            _("Only check filenames matching these patterns:"),
            'pydocstyle/match', alignment=Qt.Horizontal, word_wrap=False,
            placeholder=_("Skip test files: (?!test_).*\\.py"))
        self.docstring_style_match_dir = self.create_lineedit(
            _("Only check in directories matching these patterns:"),
            'pydocstyle/match_dir', alignment=Qt.Horizontal, word_wrap=False,
            placeholder=_("Skip dot directories: [^\\.].*"))

        # Custom option handling
        docstring_style_convention.combobox.currentTextChanged.connect(
                self.setup_docstring_style_convention)
        current_convention = docstring_style_convention.combobox.currentText()
        self.setup_docstring_style_convention(current_convention)

        # Docstring style layout
        docstring_style_g_layout = QGridLayout()
        docstring_style_g_layout.addWidget(
            docstring_style_convention.label, 1, 0)
        docstring_style_g_layout.addWidget(
            docstring_style_convention.combobox, 1, 1)
        docstring_style_g_layout.addWidget(
            self.docstring_style_select.label, 2, 0)
        docstring_style_g_layout.addWidget(
            self.docstring_style_select.textbox, 2, 1)
        docstring_style_g_layout.addWidget(
            self.docstring_style_ignore.label, 3, 0)
        docstring_style_g_layout.addWidget(
            self.docstring_style_ignore.textbox, 3, 1)
        docstring_style_g_layout.addWidget(
            self.docstring_style_match.label, 4, 0)
        docstring_style_g_layout.addWidget(
            self.docstring_style_match.textbox, 4, 1)
        docstring_style_g_layout.addWidget(
            self.docstring_style_match_dir.label, 5, 0)
        docstring_style_g_layout.addWidget(
            self.docstring_style_match_dir.textbox, 5, 1)

        # Set Docstring style options enabled/disabled
        docstring_style_g_widget = QWidget()
        docstring_style_g_widget.setLayout(docstring_style_g_layout)
        docstring_style_g_widget.setEnabled(self.get_option('pydocstyle'))
        self.docstring_style_check.toggled.connect(
            docstring_style_g_widget.setEnabled)

        # Docstring style layout
        docstring_style_layout = QVBoxLayout()
        docstring_style_layout.addWidget(docstring_style_label)
        docstring_style_layout.addWidget(self.docstring_style_check)
        docstring_style_layout.addWidget(docstring_style_g_widget)

        self.setLayout(docstring_style_layout)

    @Slot(str)
    def setup_docstring_style_convention(self, text):
        """Handle convention changes."""
        if text == 'Custom':
            self.docstring_style_select.label.setText(
                _("Show the following errors:"))
            self.docstring_style_ignore.label.setText(
                _("Ignore the following errors:"))
        else:
            self.docstring_style_select.label.setText(
                _("Show the following errors in addition "
                  "to the specified convention:"))
            self.docstring_style_ignore.label.setText(
                _("Ignore the following errors in addition "
                  "to the specified convention:"))


class AdvancedConfigTab(SpyderPreferencesTab):
    """PyLS advanced configuration tab."""

    TITLE = _('Advanced')

    def __init__(self, parent):
        super().__init__(parent)

        lsp_advanced_group = QGroupBox(_(
            'Python Language Server configuration'))
        advanced_label = QLabel(
            _("<b>Warning</b>: Only modify these values if "
              "you know what you're doing!"))
        advanced_label.setWordWrap(True)
        advanced_label.setAlignment(Qt.AlignJustify)

        # Advanced settings checkbox
        self.advanced_options_check = self.create_checkbox(
            _("Enable advanced settings"), 'advanced/enabled')

        # Advanced options
        self.advanced_module = self.create_lineedit(
            _("Module for the Python language server: "),
            'advanced/module', alignment=Qt.Horizontal,
            word_wrap=False)
        self.advanced_host = self.create_lineedit(
            _("IP Address and port to bind the server to: "),
            'advanced/host', alignment=Qt.Horizontal,
            word_wrap=False)
        self.advanced_port = self.create_spinbox(
            ":", "", 'advanced/port', min_=1, max_=65535, step=1)
        self.external_server = self.create_checkbox(
            _("This is an external server"),
            'advanced/external')
        self.use_stdio = self.create_checkbox(
            _("Use stdio pipes to communicate with server"),
            'advanced/stdio')
        self.use_stdio.stateChanged.connect(self.disable_tcp)
        self.external_server.stateChanged.connect(self.disable_stdio)

        # Advanced layout
        advanced_g_layout = QGridLayout()
        advanced_g_layout.addWidget(self.advanced_module.label, 1, 0)
        advanced_g_layout.addWidget(self.advanced_module.textbox, 1, 1)
        advanced_g_layout.addWidget(self.advanced_host.label, 2, 0)

        advanced_host_port_g_layout = QGridLayout()
        advanced_host_port_g_layout.addWidget(self.advanced_host.textbox, 1, 0)
        advanced_host_port_g_layout.addWidget(self.advanced_port.plabel, 1, 1)
        advanced_host_port_g_layout.addWidget(self.advanced_port.spinbox, 1, 2)
        advanced_g_layout.addLayout(advanced_host_port_g_layout, 2, 1)

        # External server and stdio options layout
        advanced_server_layout = QVBoxLayout()
        advanced_server_layout.addWidget(self.external_server)
        advanced_server_layout.addWidget(self.use_stdio)

        advanced_options_layout = QVBoxLayout()
        advanced_options_layout.addLayout(advanced_g_layout)
        advanced_options_layout.addLayout(advanced_server_layout)

        # Set advanced options enabled/disabled
        advanced_options_widget = QWidget()
        advanced_options_widget.setLayout(advanced_options_layout)
        advanced_options_widget.setEnabled(self.get_option('advanced/enabled'))
        self.advanced_options_check.toggled.connect(
            advanced_options_widget.setEnabled)
        self.advanced_options_check.toggled.connect(
            self.show_advanced_warning)

        # Advanced options layout
        advanced_layout = QVBoxLayout()
        advanced_layout.addWidget(advanced_label)
        advanced_layout.addWidget(self.advanced_options_check)
        advanced_layout.addWidget(advanced_options_widget)

        lsp_advanced_group.setLayout(advanced_layout)

        layout = QVBoxLayout()
        layout.addWidget(lsp_advanced_group)
        self.setLayout(layout)

    def disable_tcp(self, state):
        if state == Qt.Checked:
            self.advanced_host.textbox.setEnabled(False)
            self.advanced_port.spinbox.setEnabled(False)
            self.external_server.stateChanged.disconnect()
            self.external_server.setChecked(False)
            self.external_server.setEnabled(False)
        else:
            self.advanced_host.textbox.setEnabled(True)
            self.advanced_port.spinbox.setEnabled(True)
            self.external_server.setChecked(False)
            self.external_server.setEnabled(True)
            self.external_server.stateChanged.connect(self.disable_stdio)

    def disable_stdio(self, state):
        if state == Qt.Checked:
            self.advanced_host.textbox.setEnabled(True)
            self.advanced_port.spinbox.setEnabled(True)
            self.advanced_module.textbox.setEnabled(False)
            self.use_stdio.stateChanged.disconnect()
            self.use_stdio.setChecked(False)
            self.use_stdio.setEnabled(False)
        else:
            self.advanced_host.textbox.setEnabled(True)
            self.advanced_port.spinbox.setEnabled(True)
            self.advanced_module.textbox.setEnabled(True)
            self.use_stdio.setChecked(False)
            self.use_stdio.setEnabled(True)
            self.use_stdio.stateChanged.connect(self.disable_tcp)

    @Slot(bool)
    def show_advanced_warning(self, state):
        """
        Show a warning when trying to modify the PyLS advanced
        settings.
        """
        # Don't show warning if the option is already enabled.
        # This avoids showing it when the Preferences dialog
        # is created.
        if self.get_option('advanced/enabled'):
            return

        # Show warning when toggling the button state
        if state:
            QMessageBox.warning(
                self,
                _("Warning"),
                _("<b>Modifying these options can break code completion!!</b>"
                  "<br><br>"
                  "If that's the case, please reset your Spyder preferences "
                  "by going to the menu"
                  "<br><br>"
                  "<tt>Tools > Reset Spyder to factory defaults</tt>"
                  "<br><br>"
                  "instead of reporting a bug."))


class OtherLanguagesConfigTab(SpyderPreferencesTab):
    """LSP server configuration for other languages."""

    TITLE = _('Other languages')

    def __init__(self, parent):
        super().__init__(parent)

        servers_label = QLabel(
            _("Spyder uses the <a href=\"{lsp_url}\">Language Server "
              "Protocol</a> to provide code completion and linting "
              "for its Editor. Here, you can setup and configure LSP servers "
              "for languages other than Python, so Spyder can provide such "
              "features for those languages as well."
              ).format(lsp_url=LSP_URL))
        servers_label.setOpenExternalLinks(True)
        servers_label.setWordWrap(True)
        servers_label.setAlignment(Qt.AlignJustify)

        # Servers table
        table_group = QGroupBox(_('Available servers:'))
        self.table = LSPServerTable(self, text_color=ima.MAIN_FG_COLOR)
        self.table.setMaximumHeight(150)
        table_layout = QVBoxLayout()
        table_layout.addWidget(self.table)
        table_group.setLayout(table_layout)

        # Buttons
        self.reset_btn = QPushButton(_("Reset to default values"))
        self.new_btn = QPushButton(_("Set up a new server"))
        self.delete_btn = QPushButton(_("Delete currently selected server"))
        self.delete_btn.setEnabled(False)

        # Slots connected to buttons
        self.new_btn.clicked.connect(self.create_new_server)
        self.reset_btn.clicked.connect(self.reset_to_default)
        self.delete_btn.clicked.connect(self.delete_server)

        # Buttons layout
        btns = [self.new_btn, self.delete_btn, self.reset_btn]
        buttons_layout = QGridLayout()
        for i, btn in enumerate(btns):
            buttons_layout.addWidget(btn, i, 1)
        buttons_layout.setColumnStretch(0, 1)
        buttons_layout.setColumnStretch(1, 2)
        buttons_layout.setColumnStretch(2, 1)

        # Combined layout
        servers_layout = QVBoxLayout()
        servers_layout.addSpacing(-10)
        servers_layout.addWidget(servers_label)
        servers_layout.addWidget(table_group)
        servers_layout.addSpacing(10)
        servers_layout.addLayout(buttons_layout)

        self.setLayout(servers_layout)

    def create_new_server(self):
        self.table.show_editor(new_server=True)

    def delete_server(self):
        idx = self.table.currentIndex().row()
        self.table.delete_server(idx)
        self.set_modified(True)
        self.delete_btn.setEnabled(False)

    def reset_to_default(self):
        # TODO: Improve this logic when more languages are added on the
        # configuration
        # Remove all non-Python servers
        for language in SUPPORTED_LANGUAGES:
            language = language.lower()
            conf = self.get_option(language, default=None)
            if conf is not None:
                self.table.delete_server_by_lang(language)

    def apply_settings(self):
        return self.table.save_servers()

# LSP provider tabs
TABS = [
    LintingConfigPage,
    IntrospectionConfigTab,
    FormattingStyleConfigTab,
    DocstringConfigTab,
    AdvancedConfigTab,
    OtherLanguagesConfigTab
]
