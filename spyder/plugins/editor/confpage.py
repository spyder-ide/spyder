# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Editor config page."""

from qtpy.QtWidgets import (
    QButtonGroup,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)

from spyder.api.config.decorators import on_conf_change
from spyder.api.config.mixins import SpyderConfigurationObserver
from spyder.api.preferences import PluginConfigPage
from spyder.config.base import _
from spyder.config.manager import CONF
from spyder.plugins.editor.widgets.mouse_shortcuts import MouseShortcutEditor


NUMPYDOC = "https://numpydoc.readthedocs.io/en/latest/format.html"
GOOGLEDOC = (
    "https://sphinxcontrib-napoleon.readthedocs.io/en/latest/"
    "example_google.html"
)
SPHINXDOC = (
    "https://sphinx-rtd-tutorial.readthedocs.io/en/latest/docstrings.html"
)
DOCSTRING_SHORTCUT = CONF.get('shortcuts', 'editor/docstring')


class EditorConfigPage(PluginConfigPage, SpyderConfigurationObserver):

    def __init__(self, plugin, parent):
        PluginConfigPage.__init__(self, plugin, parent)
        SpyderConfigurationObserver.__init__(self)

        self.removetrail_box = None
        self.add_newline_box = None
        self.remove_trail_newline_box = None

    def setup_page(self):
        newcb = self.create_checkbox

        # ---- Display tab
        # -- Interface group
        interface_group = QGroupBox(_("Interface"))
        showtabbar_box = newcb(
            _("Show tab bar"),
            'show_tab_bar',
            tip=_(
                "If hidden, the file switcher, Outline pane and Ctrl-Tab\n"
                "can still be used to navigate between open files."
            ),
        )
        show_filename_box = newcb(
            _("Show full file path above editor"),
            'show_filename_toolbar',
            tip=_(
                "If hidden, the full file path is still shown when hovering "
                "over its tab."
            ),
        )
        showclassfuncdropdown_box = newcb(
            _("Show class/function selector"),
            'show_class_func_dropdown',
            tip=_(
                "For quick browsing and switching between classes/functions "
                "in a file."
            ),
        )
        scroll_past_end_box = newcb(
            _("Allow scrolling past file end"), 'scroll_past_end'
        )

        interface_layout = QVBoxLayout()
        interface_layout.addWidget(showtabbar_box)
        interface_layout.addWidget(show_filename_box)
        interface_layout.addWidget(showclassfuncdropdown_box)
        interface_layout.addWidget(scroll_past_end_box)
        interface_group.setLayout(interface_layout)

        # -- Helpers group
        helpers_group = QGroupBox(_("Helpers"))
        showindentguides_box = newcb(_("Show indent guides"), 'indent_guides')
        showcodefolding_box = newcb(
            _("Show code folding"),
            'code_folding',
            tip=_("Allow collapsing and uncollapsing code by indent level"),
        )
        linenumbers_box = newcb(_("Show line numbers"), 'line_numbers')
        breakpoints_box = newcb(
            _("Show debugger breakpoints"),
            'editor_debugger_panel',
            section='debugger',
        )
        todolist_box = newcb(
            _("Show code annotations"),
            'todo_list',
            tip=_(
                "Display a marker to the left of line numbers when the "
                "following annotations appear at the beginning of a comment: "
                "<tt>TODO, FIXME, XXX, HINT, TIP, @todo, HACK, BUG, OPTIMIZE, "
                "!!!, ???</tt> (and their lowercase variants)"
            ),
        )

        helpers_layout = QVBoxLayout()
        helpers_layout.addWidget(showindentguides_box)
        helpers_layout.addWidget(showcodefolding_box)
        helpers_layout.addWidget(linenumbers_box)
        helpers_layout.addWidget(breakpoints_box)
        helpers_layout.addWidget(todolist_box)
        helpers_group.setLayout(helpers_layout)

        # -- Highlight group
        highlight_group = QGroupBox(_("Highlight"))
        currentline_box = newcb(
            _("Highlight current line"), 'highlight_current_line'
        )
        currentcell_box = newcb(
            _("Highlight current cell"), 'highlight_current_cell'
        )
        occurrence_box = newcb(
            _("Highlight occurrences of selected text after"),
            'occurrence_highlighting',
        )
        occurrence_spin = self.create_spinbox(
            "",
            _(" milliseconds"),
            'occurrence_highlighting/timeout',
            min_=100,  # 0.1 seconds
            max_=60_000,  # 1 minute
            step=100,  # 0.1 seconds
        )

        occurrence_box.checkbox.toggled.connect(
            occurrence_spin.spinbox.setEnabled
        )
        occurrence_box.checkbox.toggled.connect(
            occurrence_spin.slabel.setEnabled
        )
        occurrence_spin.spinbox.setEnabled(
            self.get_option('occurrence_highlighting')
        )
        occurrence_spin.slabel.setEnabled(
            self.get_option('occurrence_highlighting')
        )

        occurrence_glayout = QGridLayout()
        occurrence_glayout.addWidget(occurrence_box, 0, 0)
        occurrence_glayout.addWidget(occurrence_spin.spinbox, 0, 1)
        occurrence_glayout.addWidget(occurrence_spin.slabel, 0, 2)

        occurrence_layout = QHBoxLayout()
        occurrence_layout.addLayout(occurrence_glayout)
        occurrence_layout.addStretch(1)

        highlight_layout = QVBoxLayout()
        highlight_layout.addWidget(currentline_box)
        highlight_layout.addWidget(currentcell_box)
        highlight_layout.addLayout(occurrence_layout)
        highlight_group.setLayout(highlight_layout)

        # ---- Source code tab
        # -- Automatic changes group
        automatic_group = QGroupBox(_("Automatic changes"))
        closepar_box = newcb(
            _("Automatically insert closing parentheses, brackets and braces"),
            'close_parentheses',
            tip=_("Insert a matching closing bracket when typing an open one"),
        )
        close_quotes_box = newcb(
            _("Automatically insert closing quotes"),
            'close_quotes',
            tip=_("Insert a matching closing quote when typing an open one"),
        )
        add_colons_box = newcb(
            _("Automatically insert colons after 'for', 'if', 'def', etc"),
            'add_colons',
        )
        autounindent_box = newcb(
            _("Automatically un-indent 'else', 'elif', etc"),
            'auto_unindent',
            tip=_(
                "Un-indent further block-level keywords "
                "when added inside an 'if', etc block"
            ),
        )

        automatic_layout = QVBoxLayout()
        automatic_layout.addWidget(closepar_box)
        automatic_layout.addWidget(close_quotes_box)
        automatic_layout.addWidget(add_colons_box)
        automatic_layout.addWidget(autounindent_box)
        automatic_group.setLayout(automatic_layout)

        # -- Trailing whitespace group
        whitespace_group = QGroupBox(_("Trailing whitespace"))
        self.removetrail_box = newcb(
            _("Strip all trailing spaces on save"),
            'always_remove_trailing_spaces',
            default=False,
        )
        strip_mode_box = newcb(
            _("Strip trailing spaces on changed lines"),
            'strip_trailing_spaces_on_modify',
            default=True,
            tip=_(
                "If enabled, modified lines of code (excluding strings)\n"
                "will have trailing whitespace stripped when leaving them.\n"
                "If disabled, only whitespace added by Spyder will be "
                "stripped."
            ),
        )
        self.add_newline_box = newcb(
            _("Automatically add missing end-of-file newline on save"),
            'add_newline',
            default=False,
            tip=_(
                "If enabled, a trailing newline character (line break) will "
                "automatically be appended to the end of the file\n"
                "if the file does not already end with one, "
                "to conform to standard text file conventions."
            ),
        )
        self.remove_trail_newline_box = newcb(
            _("Strip blank lines at end of file on save"),
            'always_remove_trailing_newlines',
            default=False,
            tip=_(
                "Any extra newlines at the end of the file besides the first "
                "one will be stripped."
            ),
        )

        # Disable the fix-on-save options if autoformatting is enabled
        format_on_save = CONF.get(
            'completions',
            ('provider_configuration', 'lsp', 'values', 'format_on_save'),
            False,
        )
        self.on_format_save_state(format_on_save)

        whitespace_layout = QVBoxLayout()
        whitespace_layout.addWidget(self.removetrail_box)
        whitespace_layout.addWidget(strip_mode_box)
        whitespace_layout.addWidget(self.add_newline_box)
        whitespace_layout.addWidget(self.remove_trail_newline_box)
        whitespace_group.setLayout(whitespace_layout)

        # -- Identation group
        indentation_group = QGroupBox(_("Indentation"))
        indent_chars_box = self.create_combobox(
            _("Indentation characters: "),
            (
                (_("2 spaces"), "*  *"),
                (_("3 spaces"), "*   *"),
                (_("4 spaces"), "*    *"),
                (_("5 spaces"), "*     *"),
                (_("6 spaces"), "*      *"),
                (_("7 spaces"), "*       *"),
                (_("8 spaces"), "*        *"),
                (_("Tabulations"), "*\t*"),
            ),
            "indent_chars",
        )
        tabwidth_spin = self.create_spinbox(
            _("Tab stop width:"),
            _("spaces"),
            "tab_stop_width_spaces",
            default=4,
            min_=1,
            max_=8,
            step=1,
        )
        ibackspace_box = newcb(
            _("Intelligent backspace"),
            'intelligent_backspace',
            tip=_(
                "Make the backspace key automatically remove the number of "
                "indentation characters set above."
            ),
            default=True,
        )
        tab_mode_box = newcb(
            _("Tab always indents"),
            'tab_always_indent',
            default=False,
            tip=_(
                "If enabled, pressing Tab will always add an indent,\n"
                "even when the cursor is not at the beginning of a line.\n"
                "Code completion can still be triggered using the shortcut "
                "Ctrl+Space."
            ),
        )

        def enable_tabwidth_spin(index):
            if index == 7:  # Tabulations
                tabwidth_spin.plabel.setEnabled(True)
                tabwidth_spin.spinbox.setEnabled(True)
            else:
                tabwidth_spin.plabel.setEnabled(False)
                tabwidth_spin.spinbox.setEnabled(False)

        indent_chars_box.combobox.currentIndexChanged.connect(
            enable_tabwidth_spin
        )

        indent_tab_grid_layout = QGridLayout()
        indent_tab_grid_layout.addWidget(indent_chars_box.label, 0, 0)
        indent_tab_grid_layout.addWidget(indent_chars_box.combobox, 0, 1)
        indent_tab_grid_layout.addWidget(tabwidth_spin.plabel, 1, 0)
        indent_tab_grid_layout.addWidget(tabwidth_spin.spinbox, 1, 1)
        indent_tab_grid_layout.addWidget(tabwidth_spin.slabel, 1, 2)

        indent_tab_layout = QHBoxLayout()
        indent_tab_layout.addLayout(indent_tab_grid_layout)
        indent_tab_layout.addStretch(1)

        indentation_layout = QVBoxLayout()
        indentation_layout.addLayout(indent_tab_layout)
        indentation_layout.addWidget(ibackspace_box)
        indentation_layout.addWidget(tab_mode_box)
        indentation_group.setLayout(indentation_layout)

        # -- EOL group
        eol_group = QGroupBox(_("End-of-line characters"))
        fix_eol_box = newcb(
            _("Fix mixed end-of-lines automatically and show warning dialog"),
            'check_eol_chars',
            default=True,
            tip=_(
                "When opening a file containing mixed end-of-line characters\n"
                "(which may raise syntax errors in the console on Windows),\n"
                "Spyder will convert them automatically if enabled."
            ),
        )
        convert_eol_on_save_box = newcb(
            _("Convert end-of-line characters to the following on save:"),
            'convert_eol_on_save',
            default=False,
        )
        eol_combo_choices = (
            ("LF (Linux/macOS)", 'LF'),
            ("CRLF (Windows)", 'CRLF'),
            (_("CR (legacy Mac)"), 'CR'),
        )
        convert_eol_on_save_combo = self.create_combobox(
            "",
            eol_combo_choices,
            'convert_eol_on_save_to',
        )

        convert_eol_on_save_box.checkbox.toggled.connect(
            convert_eol_on_save_combo.setEnabled
        )
        convert_eol_on_save_combo.setEnabled(
            self.get_option('convert_eol_on_save')
        )

        eol_on_save_layout = QHBoxLayout()
        eol_on_save_layout.addWidget(convert_eol_on_save_box)
        eol_on_save_layout.addWidget(convert_eol_on_save_combo)

        eol_layout = QVBoxLayout()
        eol_layout.addWidget(fix_eol_box)
        eol_layout.addLayout(eol_on_save_layout)
        eol_group.setLayout(eol_layout)

        # ---- Advanced tab
        # -- Template group
        template_group = QGroupBox(_("Template"))
        template_button = self.create_button(
            text=_("Edit new file template"),
            callback=self.plugin.edit_template,
            set_modified_on_click=True,
        )

        template_layout = QVBoxLayout()
        template_layout.addSpacing(3)
        template_layout.addWidget(template_button)
        template_group.setLayout(template_layout)

        # -- Autosave group
        autosave_group = QGroupBox(_("Autosave"))
        autosave_checkbox = newcb(
            _("Automatically save a backup copy of unsaved files"),
            'autosave_enabled',
            tip=_(
                "If Spyder quits unexpectedly, it will offer to recover"
                "them on next launch"
            ),
        )
        autosave_spinbox = self.create_spinbox(
            _("Autosave interval: "),
            _("seconds"),
            'autosave_interval',
            min_=1,
            max_=3600,
        )

        autosave_checkbox.checkbox.toggled.connect(autosave_spinbox.setEnabled)

        autosave_layout = QVBoxLayout()
        autosave_layout.addWidget(autosave_checkbox)
        autosave_layout.addWidget(autosave_spinbox)
        autosave_group.setLayout(autosave_layout)

        # -- Docstring group
        docstring_group = QGroupBox(_("Docstring style"))
        numpy_url = "<a href='{}'>Numpy</a>".format(NUMPYDOC)
        googledoc_url = "<a href='{}'>Google</a>".format(GOOGLEDOC)
        sphinx_url = "<a href='{}'>Sphinx</a>".format(SPHINXDOC)
        docstring_label = QLabel(
            _(
                "Select the style of docstrings ({numpy}, {google} or {sphinx}) "
                "to generate when pressing <kbd>{shortcut}</kbd> after a "
                "function, method or class declaration"
            ).format(
                numpy=numpy_url,
                google=googledoc_url,
                sphinx=sphinx_url,
                shortcut=DOCSTRING_SHORTCUT,
            ),
        )
        docstring_label.setOpenExternalLinks(True)
        docstring_label.setWordWrap(True)
        docstring_combo_choices = (
            ("Numpy", 'Numpydoc'),
            ("Google", 'Googledoc'),
            ("Sphinx", 'Sphinxdoc'),
        )
        docstring_combo = self.create_combobox(
            _("Style:"),
            docstring_combo_choices,
            'docstring_type',
        )

        docstring_layout = QVBoxLayout()
        docstring_layout.addWidget(docstring_label)
        docstring_layout.addWidget(docstring_combo)
        docstring_group.setLayout(docstring_layout)

        # -- Multi-cursor group
        multicursor_group = QGroupBox(_("Multi-cursor"))
        multicursor_box = newcb(
            _("Enable multi-cursor support"),
            'multicursor_support',
            tip=_(
                "Allows adding additional cursors and columns of cursors "
                "for simultaneous editing"
            ),
        )

        multicursor_layout = QVBoxLayout()
        multicursor_layout.addWidget(multicursor_box)
        multicursor_group.setLayout(multicursor_layout)

        # -- Multi-cursor paste group
        multicursor_paste_group = QGroupBox(_("Multi-cursor paste behavior"))
        multicursor_paste_bg = QButtonGroup(multicursor_paste_group)
        entire_clip_radio = self.create_radiobutton(
            _("Always paste the entire clipboard for each cursor"),
            "multicursor_paste/always_full",
            button_group=multicursor_paste_bg,
        )
        conditional_spread_radio = self.create_radiobutton(
            _(
                "Paste one line per cursor if the number of lines and cursors "
                "match"
            ),
            "multicursor_paste/conditional_spread",
            button_group=multicursor_paste_bg,
        )
        always_spread_radio = self.create_radiobutton(
            _(
                "Always paste one line per cursor if there is more than one "
                "line in the clipboard"
            ),
            "multicursor_paste/always_spread",
            button_group=multicursor_paste_bg,
        )

        multicursor_box.checkbox.toggled.connect(
            multicursor_paste_group.setEnabled
        )
        multicursor_paste_group.setEnabled(
            self.get_option("multicursor_support")
        )

        multicursor_paste_layout = QVBoxLayout()
        multicursor_paste_layout.addWidget(entire_clip_radio)
        multicursor_paste_layout.addWidget(conditional_spread_radio)
        multicursor_paste_layout.addWidget(always_spread_radio)
        multicursor_paste_group.setLayout(multicursor_paste_layout)

        # -- Mouse shortcuts group
        mouse_shortcuts_group = QGroupBox(_("Mouse shortcuts"))
        mouse_shortcuts_button = self.create_button(
            lambda: MouseShortcutEditor(self).exec_(),
            _("Edit mouse shortcut modifiers"),
        )

        mouse_shortcuts_layout = QVBoxLayout()
        mouse_shortcuts_layout.addWidget(mouse_shortcuts_button)
        mouse_shortcuts_group.setLayout(mouse_shortcuts_layout)

        # --- Tabs ---
        self.create_tab(
            _("Display"),
            [
                interface_group,
                helpers_group,
                highlight_group,
            ],
        )

        self.create_tab(
            _("Source code"),
            [
                automatic_group,
                whitespace_group,
                indentation_group,
                eol_group,
            ],
        )

        self.create_tab(
            _("Advanced"),
            [
                template_group,
                autosave_group,
                docstring_group,
                multicursor_group,
                multicursor_paste_group,
                mouse_shortcuts_group,
            ],
        )

    @on_conf_change(
        option=('provider_configuration', 'lsp', 'values', 'format_on_save'),
        section='completions',
    )
    def on_format_save_state(self, value):
        """
        Change options following the `format_on_save` completion option.

        Parameters
        ----------
        value : bool
            If the completion `format_on_save` option is enabled or disabled.

        Returns
        -------
        None.

        """
        options = [
            self.removetrail_box,
            self.add_newline_box,
            self.remove_trail_newline_box,
        ]
        for option in options:
            if option:
                if value:
                    option.setToolTip(
                        _(
                            "This option is disabled since the "
                            "<i>Autoformat files on save</i> option is active."
                        )
                    )
                else:
                    option.setToolTip("")
                option.setDisabled(value)
