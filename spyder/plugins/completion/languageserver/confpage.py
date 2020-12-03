# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Language server preferences
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
from spyder.config.base import _
from spyder.config.manager import CONF
from spyder.config.gui import is_dark_interface
from spyder.config.snippets import SNIPPETS
from spyder.plugins.completion.languageserver.widgets.serversconfig import (
    LSPServerTable)
from spyder.plugins.completion.languageserver.widgets.snippetsconfig import (
    SnippetModelsProxy, SnippetTable, LSP_LANGUAGES_PY, PYTHON_POS)
from spyder.preferences.configdialog import GeneralConfigPage
from spyder.utils import icon_manager as ima
from spyder.utils.misc import check_connection_port

LSP_URL = "https://microsoft.github.io/language-server-protocol"


class LanguageServerConfigPage(GeneralConfigPage):
    """Language Server Protocol manager preferences."""
    CONF_SECTION = 'lsp-server'
    NAME = _('Completion and linting')
    ICON = ima.icon('lspserver')
    CTRL = "Cmd" if sys.platform == 'darwin' else "Ctrl"

    def setup_page(self):
        newcb = self.create_checkbox

        # --- Completion ---
        # Completion group
        self.completion_box = newcb(_("Enable code completion"),
                                    'code_completion')
        self.completion_hint_box = newcb(
            _("Show completion details"),
            'completions_hint',
            section='editor')
        self.completions_hint_after_ms = self.create_spinbox(
            _("Show completion detail after keyboard idle (ms):"), None,
            'completions_hint_after_ms', min_=0, max_=5000, step=10,
            tip=_("Default is 500"), section='editor')
        self.automatic_completion_box = newcb(
            _("Show completions on the fly"),
            'automatic_completions',
            section='editor')
        self.completions_after_characters = self.create_spinbox(
            _("Show automatic completions after characters entered:"), None,
            'automatic_completions_after_chars', min_=1, step=1,
            tip=_("Default is 3"), section='editor')
        self.completions_after_ms = self.create_spinbox(
            _("Show automatic completions after keyboard idle (ms):"), None,
            'automatic_completions_after_ms', min_=0, max_=5000, step=10,
            tip=_("Default is 300"), section='editor')
        code_snippets_box = newcb(_("Enable code snippets"), 'code_snippets')

        completion_layout = QGridLayout()
        completion_layout.addWidget(self.completion_box, 0, 0)
        completion_layout.addWidget(self.completion_hint_box, 1, 0)
        completion_layout.addWidget(self.completions_hint_after_ms.plabel,
                                    2, 0)
        completion_layout.addWidget(self.completions_hint_after_ms.spinbox,
                                    2, 1)
        completion_layout.addWidget(self.automatic_completion_box, 3, 0)
        completion_layout.addWidget(self.completions_after_characters.plabel,
                                    4, 0)
        completion_layout.addWidget(self.completions_after_characters.spinbox,
                                    4, 1)
        completion_layout.addWidget(self.completions_after_ms.plabel, 5, 0)
        completion_layout.addWidget(self.completions_after_ms.spinbox, 5, 1)
        completion_layout.addWidget(code_snippets_box, 6, 0)
        completion_layout.setColumnStretch(2, 6)
        completion_widget = QWidget()
        completion_widget.setLayout(completion_layout)

        self.completion_box.toggled.connect(self.check_completion_options)
        self.automatic_completion_box.toggled.connect(
            self.check_completion_options)

        # --- Introspection ---
        # Introspection group
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

        # --- Linting ---
        # Linting options
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
        linting_widget = QWidget()
        linting_widget.setLayout(linting_layout)

        linting_check.toggled.connect(underline_errors_box.setEnabled)

        # --- Code style and formatting tab ---
        # Code style label
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

        code_style_widget = QWidget()
        code_style_fmt_layout = QVBoxLayout()
        code_style_fmt_layout.addWidget(code_style_group)
        code_style_fmt_layout.addWidget(code_fmt_group)
        code_style_fmt_layout.addWidget(line_length_group)
        code_style_widget.setLayout(code_style_fmt_layout)

        # --- Docstring tab ---
        # Docstring style label
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

        docstring_style_widget = QWidget()
        docstring_style_widget.setLayout(docstring_style_layout)

        # --- Snippets tab ---
        self.snippets_language = 'python'
        grammar_url = (
            "<a href=\"{0}/specifications/specification-current#snippet_syntax\">"
            "{1}</a>".format(LSP_URL, _('the LSP grammar')))
        snippets_info_label = QLabel(
            _("Spyder allows to define custom completion snippets to use "
              "in addition to the ones offered by the Language Server "
              "Protocol (LSP). Each snippet should follow {}.<br><br> "
              "<b>Note:</b> All changes will be effective only when applying "
              "the settings").format(grammar_url))
        snippets_info_label.setOpenExternalLinks(True)
        snippets_info_label.setWordWrap(True)
        snippets_info_label.setAlignment(Qt.AlignJustify)

        self.snippets_language_cb = QComboBox(self)
        self.snippets_language_cb.setToolTip(
            _('Programming language provided by the LSP server'))
        self.snippets_language_cb.addItems(LSP_LANGUAGES_PY)
        self.snippets_language_cb.setCurrentIndex(PYTHON_POS)
        self.snippets_language_cb.currentTextChanged.connect(
            self.change_language_snippets)

        snippet_lang_group = QGroupBox(_('Language'))
        snippet_lang_layout = QVBoxLayout()
        snippet_lang_layout.addWidget(self.snippets_language_cb)
        snippet_lang_group.setLayout(snippet_lang_layout)

        self.snippets_proxy = SnippetModelsProxy()
        self.snippets_table = SnippetTable(
            self, self.snippets_proxy, language=self.snippets_language)
        self.snippets_table.setMaximumHeight(180)

        snippet_table_group = QGroupBox(_('Available snippets'))
        snippet_table_layout = QVBoxLayout()
        snippet_table_layout.addWidget(self.snippets_table)
        snippet_table_group.setLayout(snippet_table_layout)

        # Buttons
        self.reset_snippets_btn = QPushButton(_("Reset to default values"))
        self.new_snippet_btn = QPushButton(_("Create a new snippet"))
        self.delete_snippet_btn = QPushButton(
            _("Delete currently selected snippet"))
        self.delete_snippet_btn.setEnabled(False)
        self.export_snippets_btn = QPushButton(_("Export snippets to JSON"))
        self.import_snippets_btn = QPushButton(_("Import snippets from JSON"))

        # Slots connected to buttons
        self.new_snippet_btn.clicked.connect(self.create_new_snippet)
        self.reset_snippets_btn.clicked.connect(self.reset_default_snippets)
        self.delete_snippet_btn.clicked.connect(self.delete_snippet)
        self.export_snippets_btn.clicked.connect(self.export_snippets)
        self.import_snippets_btn.clicked.connect(self.import_snippets)

        # Buttons layout
        btns = [self.new_snippet_btn,
                self.delete_snippet_btn,
                self.reset_snippets_btn,
                self.export_snippets_btn,
                self.import_snippets_btn]
        sn_buttons_layout = QGridLayout()
        for i, btn in enumerate(btns):
            sn_buttons_layout.addWidget(btn, i, 1)
        sn_buttons_layout.setColumnStretch(0, 1)
        sn_buttons_layout.setColumnStretch(1, 2)
        sn_buttons_layout.setColumnStretch(2, 1)

        # Snippets layout
        snippets_layout = QVBoxLayout()
        snippets_layout.addWidget(snippets_info_label)
        snippets_layout.addWidget(snippet_lang_group)
        snippets_layout.addWidget(snippet_table_group)
        snippets_layout.addLayout(sn_buttons_layout)

        snippets_widget = QWidget()
        snippets_widget.setLayout(snippets_layout)

        # --- Advanced tab ---
        # Clients group
        clients_group = QGroupBox(_("Providers"))
        self.kite_enabled = newcb(_("Enable Kite "
                                    "(if the Kite engine is running)"),
                                  'enable',
                                  section='kite')
        self.fallback_enabled = newcb(_("Enable fallback completions"),
                                      'enable',
                                      section='fallback-completions')
        self.completions_wait_for_ms = self.create_spinbox(
            _("Time to wait for all providers to return (ms):"), None,
            'completions_wait_for_ms', min_=0, max_=5000, step=10,
            tip=_("Beyond this timeout, "
                  "the first available provider will be returned"),
            section='editor')

        clients_layout = QVBoxLayout()
        clients_layout.addWidget(self.kite_enabled)
        clients_layout.addWidget(self.fallback_enabled)
        clients_layout.addWidget(self.completions_wait_for_ms)
        clients_group.setLayout(clients_layout)

        kite_layout = QVBoxLayout()
        self.kite_cta = self.create_checkbox(
            _("Notify me when Kite can provide missing completions"
              " (but is unavailable)"),
            'call_to_action',
            section='kite')
        kite_layout.addWidget(self.kite_cta)
        kite_group = QGroupBox(_(
            'Kite configuration'))
        kite_group.setLayout(kite_layout)

        # Advanced label
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

        # --- Other servers tab ---
        # Section label
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
        servers_widget = QWidget()
        servers_layout = QVBoxLayout()
        servers_layout.addSpacing(-10)
        servers_layout.addWidget(servers_label)
        servers_layout.addWidget(table_group)
        servers_layout.addSpacing(10)
        servers_layout.addLayout(buttons_layout)
        servers_widget.setLayout(servers_layout)

        # --- Tabs organization ---
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_tab(completion_widget),
                         _('Completion'))
        self.tabs.addTab(self.create_tab(linting_widget), _('Linting'))
        self.tabs.addTab(self.create_tab(introspection_group, advanced_group),
                         _('Introspection'))
        self.tabs.addTab(self.create_tab(code_style_widget),
                         _('Code style and formatting'))
        self.tabs.addTab(self.create_tab(docstring_style_widget),
                         _('Docstring style'))
        self.tabs.addTab(self.create_tab(snippets_widget), _('Snippets'))
        self.tabs.addTab(self.create_tab(clients_group,
                                         lsp_advanced_group,
                                         kite_group),
                         _('Advanced'))
        self.tabs.addTab(self.create_tab(servers_widget), _('Other languages'))

        vlayout = QVBoxLayout()
        vlayout.addWidget(self.tabs)
        self.setLayout(vlayout)

    def check_completion_options(self, state):
        """Update enabled status of completion checboxes and spinboxes."""
        state = self.completion_box.isChecked()
        self.completion_hint_box.setEnabled(state)
        self.automatic_completion_box.setEnabled(state)

        state = state and self.automatic_completion_box.isChecked()
        self.completions_after_characters.spinbox.setEnabled(state)
        self.completions_after_characters.plabel.setEnabled(state)
        self.completions_after_ms.spinbox.setEnabled(state)
        self.completions_after_ms.plabel.setEnabled(state)

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

    def reset_to_default(self):
        CONF.reset_to_defaults(section='lsp-server')
        self.table.load_servers()
        self.load_from_conf()
        self.set_modified(True)

    def create_new_server(self):
        self.table.show_editor(new_server=True)

    def delete_server(self):
        idx = self.table.currentIndex().row()
        self.table.delete_server(idx)
        self.set_modified(True)
        self.delete_btn.setEnabled(False)

    def create_new_snippet(self):
        self.snippets_table.show_editor(new_snippet=True)

    def delete_snippet(self):
        idx = self.snippets_table.currentIndex().row()
        self.snippets_table.delete_snippet(idx)
        self.set_modified(True)
        self.delete_snippet_btn.setEnabled(False)

    def reset_default_snippets(self):
        language = self.snippets_language_cb.currentText()
        default_snippets_lang = copy.deepcopy(
            SNIPPETS.get(language.lower(), {}))
        self.snippets_proxy.reload_model(
            language.lower(), default_snippets_lang)
        self.snippets_table.reset_plain()
        self.set_modified(True)

    def change_language_snippets(self, language):
        self.snippets_table.update_language_model(language)

    def export_snippets(self):
        filename, _selfilter = getsavefilename(
            self, _("Save snippets"),
            'spyder_snippets.json',
            filters='JSON (*.json)',
            selectedfilter='',
            options=QFileDialog.HideNameFilterDetails)

        if filename:
            filename = osp.normpath(filename)
            self.snippets_proxy.export_snippets(filename)

    def import_snippets(self):
        filename, _sf = getopenfilename(
            self,
            _("Load snippets"),
            filters='JSON (*.json)',
            selectedfilter='',
            options=QFileDialog.HideNameFilterDetails,
        )

        if filename:
            filename = osp.normpath(filename)
            valid, total, errors = self.snippets_proxy.import_snippets(
                filename)
            modified = True
            if len(errors) == 0:
                QMessageBox.information(
                    self,
                    _('All snippets imported'),
                    _('{0} snippets were loaded successfully').format(valid),
                    QMessageBox.Ok)
            else:
                if 'loading' in errors:
                    modified = False
                    QMessageBox.critical(
                        self,
                        _('JSON malformed'),
                        _('There was an error when trying to load the '
                          'provided JSON file: <tt>{0}</tt>').format(
                              errors['loading']),
                        QMessageBox.Ok
                    )
                elif 'validation' in errors:
                    modified = False
                    QMessageBox.critical(
                        self,
                        _('Invalid snippet file'),
                        _('The provided snippet file does not comply with '
                          'the Spyder JSON snippets spec and therefore it '
                          'cannot be loaded.<br><br><tt>{}</tt>').format(
                              errors['validation']),
                        QMessageBox.Ok
                    )
                elif 'syntax' in errors:
                    syntax_errors = errors['syntax']
                    msg = []
                    for syntax_key in syntax_errors:
                        syntax_err = syntax_errors[syntax_key]
                        msg.append('<b>{0}</b>: {1}'.format(
                            syntax_key, syntax_err))
                    err_msg = '<br>'.join(msg)

                    QMessageBox.warning(
                        self,
                        _('Incorrect snippet format'),
                        _('Spyder was able to load {0}/{1} snippets '
                          'correctly, please check the following snippets '
                          'for any syntax errors: '
                          '<br><br>{2}').format(valid, total, err_msg),
                        QMessageBox.Ok
                    )
            self.set_modified(modified)

    def report_no_external_server(self, host, port, language):
        """
        Report that connection couldn't be established with
        an external server.
        """
        QMessageBox.critical(
            self,
            _("Error"),
            _("It appears there is no {language} language server listening "
              "at address:"
              "<br><br>"
              "<tt>{host}:{port}</tt>"
              "<br><br>"
              "Please verify that the provided information is correct "
              "and try again.").format(host=host, port=port,
                                       language=language.capitalize())
        )

    def report_no_address_change(self):
        """
        Report that server address has no changed after checking the
        external server option.
        """
        QMessageBox.critical(
            self,
            _("Error"),
            _("The address of the external server you are trying to connect "
              "to is the same as the one of the current internal server "
              "started by Spyder."
              "<br><br>"
              "Please provide a different address!")
        )

    def is_valid(self):
        """Check if config options are valid."""
        host = self.advanced_host.textbox.text()

        # If host is not local, the server must be external
        # and we need to automatically check the corresponding
        # option
        if host not in ['127.0.0.1', 'localhost']:
            self.external_server.setChecked(True)

        # Checks for extenal PyLS
        if self.external_server.isChecked():
            port = int(self.advanced_port.spinbox.text())

            # Check that host and port of the current server are
            # different from the new ones provided to connect to
            # an external server.
            lsp = self.main.completions.get_client('lsp')
            pyclient = lsp.clients.get('python')
            if pyclient is not None:
                instance = pyclient['instance']
                if (instance is not None and
                        not pyclient['config']['external']):
                    if (instance.server_host == host and
                            instance.server_port == port):
                        self.report_no_address_change()
                        return False

            # Check connection to LSP server using a TCP socket
            response = check_connection_port(host, port)
            if not response:
                self.report_no_external_server(host, port, 'python')
                return False

        return super(GeneralConfigPage, self).is_valid()

    def apply_settings(self, options):
        # Check regex of code style options
        try:
            code_style_filenames_matches = (
                self.code_style_filenames_match.textbox.text().split(","))
            for match in code_style_filenames_matches:
                re.compile(match.strip())
        except re.error:
            self.set_option('pycodestyle/filename', '')

        try:
            code_style_excludes = (
                self.code_style_exclude.textbox.text().split(","))
            for match in code_style_excludes:
                re.compile(match.strip())
        except re.error:
            self.set_option('pycodestyle/exclude', '')

        # Check regex of docstring style options
        try:
            docstring_style_match = (
                self.docstring_style_match.textbox.text())
            re.compile(docstring_style_match)
        except re.error:
            self.set_option('pydocstyle/match', '')

        try:
            docstring_style_match_dir = (
                self.docstring_style_match.textbox.text())
            re.compile(docstring_style_match_dir)
        except re.error:
            self.set_option('pydocstyle/match_dir', '')

        self.table.save_servers()
        self.snippets_proxy.save_snippets()

        # Update entries in the source menu
        for name, action in self.main.editor.checkable_actions.items():
            if name in options:
                section = self.CONF_SECTION
                if name == 'underline_errors':
                    section = 'editor'

                state = self.get_option(name, section=section)

                # Avoid triggering the action when this action changes state
                # See: spyder-ide/spyder#9915
                action.blockSignals(True)
                action.setChecked(state)
                action.blockSignals(False)

        # TODO: Reset Manager
        self.main.completions.update_configuration()

        # Update editor plugin options
        editor = self.main.editor
        editor_method_sec_opts = {
            'set_code_snippets_enabled': (self.CONF_SECTION, 'code_snippets'),
            'set_hover_hints_enabled':  (self.CONF_SECTION,
                                         'enable_hover_hints'),
            'set_format_on_save': (self.CONF_SECTION, 'format_on_save'),
            'set_automatic_completions_enabled': ('editor',
                                                  'automatic_completions'),
            'set_completions_hint_enabled': ('editor', 'completions_hint'),
            'set_completions_hint_after_ms': ('editor',
                                              'completions_hint_after_ms'),
            'set_underline_errors_enabled': ('editor', 'underline_errors'),
            'set_automatic_completions_after_chars': (
                'editor', 'automatic_completions_after_chars'),
            'set_automatic_completions_after_ms': (
                'editor', 'automatic_completions_after_ms'),
            'set_edgeline_columns': (self.CONF_SECTION,
                                     'pycodestyle/max_line_length'),
            'set_edgeline_enabled': ('editor', 'edge_line'),
        }
        for editorstack in editor.editorstacks:
            for method_name, (sec, opt) in editor_method_sec_opts.items():
                if opt in options:
                    method = getattr(editorstack, method_name)
                    method(self.get_option(opt, section=sec))
