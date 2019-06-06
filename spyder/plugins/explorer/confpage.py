# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""File explorer configuration page."""

# Third party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QGroupBox, QLabel, QVBoxLayout, QListWidget, QPushButton, QHBoxLayout, QWidget, QTabWidget

# Local imports
from spyder.api.preferences import PluginConfigPage
from spyder.config.base import _
from spyder.widgets.fileassociations import FileAssociationsWidget


class ExplorerConfigPage(PluginConfigPage):
    def setup_page(self):
        newcb = self.create_checkbox

        # Widgets
        general_widget = QWidget()
        check_show_hidden = newcb(_("Show hidden files"), 'show_hidden')
        check_show_all = newcb(_("Show all files"), 'show_all')
        check_icon = newcb(_("Show icons and text"), 'show_icontext')
        check_single_click = newcb(_("Single click to open files"), 'single_click_to_open')
        edit_filename_filters = self.create_textedit(
            _("Edit filename filters..."),
            'name_filters',
            tip=("Enter values separated by commas"),
            content_type=list,
        )
        associations_widget = FileAssociationsWidget()

        # Layouts
        layout = QVBoxLayout()
        layout.addWidget(check_show_hidden)
        layout.addWidget(check_show_all)
        layout.addWidget(check_icon)
        layout.addWidget(check_single_click)
        layout.addWidget(edit_filename_filters)
        general_widget.setLayout(layout)

        tabs = QTabWidget()
        tabs.addTab(self.create_tab(general_widget), _("General"))
        tabs.addTab(self.create_tab(associations_widget), _("File associations"))

        tab_layout = QVBoxLayout()
        tab_layout.addWidget(tabs)

        self.setLayout(tab_layout)
