# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Editor config page."""

from qtpy.QtCore import Qt
from qtpy.QtWidgets import (QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                            QTabWidget, QVBoxLayout, QWidget)

from spyder.api.preferences import PluginConfigPage
from spyder.config.base import _
from spyder.config.manager import CONF
import spyder.utils.icon_manager as ima


NUMPYDOC = "https://numpydoc.readthedocs.io/en/latest/format.html"
GOOGLEDOC = "https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html"
DOCSTRING_SHORTCUT = CONF.get('shortcuts', 'editor/docstring')


class EditorConfigPage(PluginConfigPage):
    def get_name(self):
        return _("Editor")

    def get_icon(self):
        return ima.icon('edit')

    def setup_page(self):
        newcb = self.create_checkbox

        # --- Display tab ---
        showtabbar_box = newcb(_("Show tab bar"), 'show_tab_bar')
        showclassfuncdropdown_box = newcb(
                _("Show selector for classes and functions"),
                'show_class_func_dropdown')
        showindentguides_box = newcb(_("Show indent guides"),
                                     'indent_guides')
        showcodefolding_box = newcb(_("Show code folding"), 'code_folding')
        linenumbers_box = newcb(_("Show line numbers"), 'line_numbers')
        blanks_box = newcb(_("Show blank spaces"), 'blank_spaces')
        currentline_box = newcb(_("Highlight current line"),
                                'highlight_current_line')
        currentcell_box = newcb(_("Highlight current cell"),
                                'highlight_current_cell')
        wrap_mode_box = newcb(_("Wrap lines"), 'wrap')
        scroll_past_end_box = newcb(_("Scroll past the end"),
                                    'scroll_past_end')

        edgeline_box = newcb(_("Show vertical lines at"), 'edge_line')
        edgeline_edit = self.create_lineedit(
            "",
            'edge_line_columns',
            tip=("Enter values separated by commas"),
            alignment=Qt.Horizontal,
            regex="[0-9]+(,[0-9]+)*")
        edgeline_edit_label = QLabel(_("characters"))
        edgeline_box.toggled.connect(edgeline_edit.setEnabled)
        edgeline_box.toggled.connect(edgeline_edit_label.setEnabled)
        edgeline_edit.setEnabled(self.get_option('edge_line'))
        edgeline_edit_label.setEnabled(self.get_option('edge_line'))

        occurrence_box = newcb(_("Highlight occurrences after"),
                               'occurrence_highlighting')
        occurrence_spin = self.create_spinbox(
            "", _(" ms"),
            'occurrence_highlighting/timeout',
            min_=100, max_=1000000, step=100)
        occurrence_box.toggled.connect(occurrence_spin.spinbox.setEnabled)
        occurrence_box.toggled.connect(occurrence_spin.slabel.setEnabled)
        occurrence_spin.spinbox.setEnabled(
                self.get_option('occurrence_highlighting'))
        occurrence_spin.slabel.setEnabled(
                self.get_option('occurrence_highlighting'))

        display_g_layout = QGridLayout()
        display_g_layout.addWidget(edgeline_box, 0, 0)
        display_g_layout.addWidget(edgeline_edit.textbox, 0, 1)
        display_g_layout.addWidget(edgeline_edit_label, 0, 2)
        display_g_layout.addWidget(occurrence_box, 1, 0)
        display_g_layout.addWidget(occurrence_spin.spinbox, 1, 1)
        display_g_layout.addWidget(occurrence_spin.slabel, 1, 2)

        display_h_layout = QHBoxLayout()
        display_h_layout.addLayout(display_g_layout)
        display_h_layout.addStretch(1)

        display_layout = QVBoxLayout()
        display_layout.addWidget(showtabbar_box)
        display_layout.addWidget(showclassfuncdropdown_box)
        display_layout.addWidget(showindentguides_box)
        display_layout.addWidget(showcodefolding_box)
        display_layout.addWidget(linenumbers_box)
        display_layout.addWidget(blanks_box)
        display_layout.addWidget(currentline_box)
        display_layout.addWidget(currentcell_box)
        display_layout.addWidget(wrap_mode_box)
        display_layout.addWidget(scroll_past_end_box)
        display_layout.addLayout(display_h_layout)

        display_widget = QWidget()
        display_widget.setLayout(display_layout)

        # --- Source code tab ---
        closepar_box = newcb(
            _("Automatic insertion of parentheses, braces and brackets"),
            'close_parentheses')
        close_quotes_box = newcb(
            _("Automatic insertion of closing quotes"),
            'close_quotes')
        add_colons_box = newcb(
            _("Automatic insertion of colons after 'for', 'if', 'def', etc"),
            'add_colons')
        autounindent_box = newcb(
            _("Automatic indentation after 'else', 'elif', etc."),
            'auto_unindent')
        tab_mode_box = newcb(
            _("Tab always indent"),
            'tab_always_indent', default=False,
            tip=_("If enabled, pressing Tab will always indent,\n"
                  "even when the cursor is not at the beginning\n"
                  "of a line (when this option is enabled, code\n"
                  "completion may be triggered using the alternate\n"
                  "shortcut: Ctrl+Space)"))
        strip_mode_box = newcb(
            _("Automatically strip trailing spaces on changed lines"),
            'strip_trailing_spaces_on_modify', default=True,
            tip=_("If enabled, modified lines of code (excluding strings)\n"
                  "will have their trailing whitespace stripped when leaving them.\n"
                  "If disabled, only whitespace added by Spyder will be stripped."))
        ibackspace_box = newcb(
            _("Intelligent backspace"),
            'intelligent_backspace',
            default=True)
        removetrail_box = newcb(
            _("Automatically remove trailing spaces when saving files"),
            'always_remove_trailing_spaces',
            default=False)

        indent_chars_box = self.create_combobox(
            _("Indentation characters: "),
            ((_("2 spaces"), '*  *'),
             (_("3 spaces"), '*   *'),
             (_("4 spaces"), '*    *'),
             (_("5 spaces"), '*     *'),
             (_("6 spaces"), '*      *'),
             (_("7 spaces"), '*       *'),
             (_("8 spaces"), '*        *'),
             (_("Tabulations"), '*\t*')),
            'indent_chars')
        tabwidth_spin = self.create_spinbox(
            _("Tab stop width:"),
            _("spaces"),
            'tab_stop_width_spaces',
            default=4, min_=1, max_=8, step=1)

        def enable_tabwidth_spin(index):
            if index == 7:  # Tabulations
                tabwidth_spin.plabel.setEnabled(True)
                tabwidth_spin.spinbox.setEnabled(True)
            else:
                tabwidth_spin.plabel.setEnabled(False)
                tabwidth_spin.spinbox.setEnabled(False)

        indent_chars_box.combobox.currentIndexChanged.connect(
            enable_tabwidth_spin)

        indent_tab_grid_layout = QGridLayout()
        indent_tab_grid_layout.addWidget(indent_chars_box.label, 0, 0)
        indent_tab_grid_layout.addWidget(indent_chars_box.combobox, 0, 1)
        indent_tab_grid_layout.addWidget(tabwidth_spin.plabel, 1, 0)
        indent_tab_grid_layout.addWidget(tabwidth_spin.spinbox, 1, 1)
        indent_tab_grid_layout.addWidget(tabwidth_spin.slabel, 1, 2)

        indent_tab_layout = QHBoxLayout()
        indent_tab_layout.addLayout(indent_tab_grid_layout)
        indent_tab_layout.addStretch(1)

        sourcecode_layout = QVBoxLayout()
        sourcecode_layout.addWidget(closepar_box)
        sourcecode_layout.addWidget(autounindent_box)
        sourcecode_layout.addWidget(add_colons_box)
        sourcecode_layout.addWidget(close_quotes_box)
        sourcecode_layout.addWidget(tab_mode_box)
        sourcecode_layout.addWidget(ibackspace_box)
        sourcecode_layout.addWidget(removetrail_box)
        sourcecode_layout.addWidget(strip_mode_box)
        sourcecode_layout.addLayout(indent_tab_layout)

        sourcecode_widget = QWidget()
        sourcecode_widget.setLayout(sourcecode_layout)

        # --- Run code tab ---
        saveall_box = newcb(_("Save all files before running script"),
                            'save_all_before_run')
        focus_box = newcb(_("Maintain focus in the Editor after running cells "
                            "or selections"), 'focus_to_editor')
        run_cell_box = newcb(_("Copy full cell contents to the console when "
                               "running code cells"), 'run_cell_copy')

        run_layout = QVBoxLayout()
        run_layout.addWidget(saveall_box)
        run_layout.addWidget(focus_box)
        run_layout.addWidget(run_cell_box)

        run_widget = QWidget()
        run_widget.setLayout(run_layout)

        # --- Advanced tab ---
        # -- Templates
        template_btn = self.create_button(_("Edit template for new files"),
                                          self.plugin.edit_template)

        # -- Autosave
        autosave_group = QGroupBox(_('Autosave'))
        autosave_checkbox = newcb(
            _('Automatically save a copy of files with unsaved changes'),
            'autosave_enabled')
        autosave_spinbox = self.create_spinbox(
            _('Autosave interval: '),
            _('seconds'),
            'autosave_interval',
            min_=1, max_=3600)
        autosave_checkbox.toggled.connect(autosave_spinbox.setEnabled)

        autosave_layout = QVBoxLayout()
        autosave_layout.addWidget(autosave_checkbox)
        autosave_layout.addWidget(autosave_spinbox)
        autosave_group.setLayout(autosave_layout)

        # -- Docstring
        docstring_group = QGroupBox(_('Docstring type'))

        numpy_url = "<a href='{}'>Numpy</a>".format(NUMPYDOC)
        googledoc_url = "<a href='{}'>Google</a>".format(GOOGLEDOC)
        docstring_label = QLabel(
            _("Here you can select the type of docstrings ({} or {}) you "
              "want the editor to automatically introduce when pressing "
              "<tt>{}</tt> after a function/method/class "
              "declaration.").format(
                  numpy_url, googledoc_url, DOCSTRING_SHORTCUT))
        docstring_label.setOpenExternalLinks(True)
        docstring_label.setWordWrap(True)

        docstring_combo_choices = ((_("Numpy"), 'Numpydoc'),
                                   (_("Google"), 'Googledoc'),
                                   (_("Sphinx"), 'Sphinxdoc'),)
        docstring_combo = self.create_combobox(
            _("Type:"),
            docstring_combo_choices,
            'docstring_type')

        docstring_layout = QVBoxLayout()
        docstring_layout.addWidget(docstring_label)
        docstring_layout.addWidget(docstring_combo)
        docstring_group.setLayout(docstring_layout)

        # -- Annotations
        annotations_group = QGroupBox(_("Annotations"))
        annotations_label = QLabel(
            _("Display a marker to the left of line numbers when the "
              "following annotations appear at the beginning of a comment: "
              "<tt>TODO, FIXME, XXX, HINT, TIP, @todo, HACK, BUG, OPTIMIZE, "
              "!!!, ???</tt>"))
        annotations_label.setWordWrap(True)
        todolist_box = newcb(
            _("Display code annotations"),
            'todo_list')

        annotations_layout = QVBoxLayout()
        annotations_layout.addWidget(annotations_label)
        annotations_layout.addWidget(todolist_box)
        annotations_group.setLayout(annotations_layout)

        # -- EOL
        eol_group = QGroupBox(_("End-of-line characters"))
        eol_label = QLabel(_("When opening a text file containing "
                             "mixed end-of-line characters (this may "
                             "raise syntax errors in the consoles "
                             "on Windows platforms), Spyder may fix the "
                             "file automatically."))
        eol_label.setWordWrap(True)
        check_eol_box = newcb(_("Fix automatically and show warning "
                                "message box"),
                              'check_eol_chars', default=True)
        convert_eol_on_save_box = newcb(_("On Save: convert EOL characters"
                                          " to"),
                                        'convert_eol_on_save', default=False)
        eol_combo_choices = ((_("LF (UNIX)"), 'LF'),
                             (_("CRLF (Windows)"), 'CRLF'),
                             (_("CR (Mac)"), 'CR'),
                             )
        convert_eol_on_save_combo = self.create_combobox("",
                                                         eol_combo_choices,
                                                         ('convert_eol_on_'
                                                          'save_to'),
                                                         )
        convert_eol_on_save_box.toggled.connect(
                convert_eol_on_save_combo.setEnabled)
        convert_eol_on_save_combo.setEnabled(
                self.get_option('convert_eol_on_save'))

        eol_on_save_layout = QHBoxLayout()
        eol_on_save_layout.addWidget(convert_eol_on_save_box)
        eol_on_save_layout.addWidget(convert_eol_on_save_combo)

        eol_layout = QVBoxLayout()
        eol_layout.addWidget(eol_label)
        eol_layout.addWidget(check_eol_box)
        eol_layout.addLayout(eol_on_save_layout)
        eol_group.setLayout(eol_layout)

        # --- Tabs ---
        tabs = QTabWidget()
        tabs.addTab(self.create_tab(display_widget), _("Display"))
        tabs.addTab(self.create_tab(sourcecode_widget), _("Source code"))
        tabs.addTab(self.create_tab(run_widget), _('Run code'))
        tabs.addTab(self.create_tab(template_btn, autosave_group,
                                    docstring_group, annotations_group,
                                    eol_group),
                    _("Advanced settings"))

        vlayout = QVBoxLayout()
        vlayout.addWidget(tabs)
        self.setLayout(vlayout)
