# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Debugger Plugin Configuration Page."""

# Third party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QGroupBox, QVBoxLayout, QLabel

# Local imports
from spyder.config.base import _
from spyder.api.preferences import PluginConfigPage


class DebuggerConfigPage(PluginConfigPage):

    def setup_page(self):
        newcb = self.create_checkbox

        # ---- Debug ----
        # Pdb run lines Group
        pdb_run_lines_group = QGroupBox(_("Run code while debugging"))
        pdb_run_lines_label = QLabel(_(
            "You can run several lines of code on each new prompt while "
            "debugging. Please introduce each one separated by semicolons and "
            "a space, for example:<br>"
            "<i>import matplotlib.pyplot as plt; import numpy as np</i>")
        )
        pdb_run_lines_label.setWordWrap(True)
        pdb_run_lines_edit = self.create_lineedit(
            _("Lines:"), 'startup/pdb_run_lines', '', alignment=Qt.Horizontal)

        pdb_run_lines_layout = QVBoxLayout()
        pdb_run_lines_layout.addWidget(pdb_run_lines_label)
        pdb_run_lines_layout.addWidget(pdb_run_lines_edit)
        pdb_run_lines_group.setLayout(pdb_run_lines_layout)

        # Debug Group
        debug_group = QGroupBox(_("Interaction"))
        debug_layout = QVBoxLayout()

        prevent_closing_box = newcb(
            _("Prevent editor from closing files while debugging"),
            'pdb_prevent_closing',
            tip=_("This option prevents the user from closing a file while"
                  " it is debugged."))
        debug_layout.addWidget(prevent_closing_box)

        continue_box = newcb(
            _("Stop debugging on first line of files without breakpoints"),
            'pdb_stop_first_line',
            tip=_("This option lets you decide if the debugger should"
                  " stop on the first line while debugging if no breakpoints"
                  " are present."))
        debug_layout.addWidget(continue_box)

        libraries_box = newcb(
            _("Ignore Python libraries while debugging"), 'pdb_ignore_lib',
            tip=_("This option lets you decide if the debugger should "
                  "ignore the system libraries while debugging."))
        debug_layout.addWidget(libraries_box)

        execute_events_box = newcb(
            _("Process execute events while debugging"), 'pdb_execute_events',
            tip=_("This option lets you decide if the debugger should "
                  "process the 'execute events' after each prompt, such as "
                  "matplotlib <tt>show</tt> command."))
        debug_layout.addWidget(execute_events_box)

        exclamation_mark_box = newcb(
            _("Use exclamation mark prefix for Pdb commands"),
            'pdb_use_exclamation_mark',
            tip=_("This option lets you decide if the Pdb commands should "
                  "be prefixed by an exclamation mark. This helps in "
                  "separating Pdb commands from Python code."))
        debug_layout.addWidget(exclamation_mark_box)

        debug_group.setLayout(debug_layout)

        filter_group = QGroupBox(_("Execution Inspector"))
        filter_data = [
            ('exclude_internal', _("Exclude internal frames when inspecting execution")),
        ]
        filter_boxes = [self.create_checkbox(text, option)
                        for option, text in filter_data]

        filter_layout = QVBoxLayout()
        for box in filter_boxes:
            filter_layout.addWidget(box)
        filter_group.setLayout(filter_layout)

        vlayout = QVBoxLayout()
        vlayout.addWidget(debug_group)
        vlayout.addWidget(pdb_run_lines_group)
        vlayout.addWidget(filter_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)
