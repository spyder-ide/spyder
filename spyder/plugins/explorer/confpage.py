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


class ExplorerConfigPage(PluginConfigPage):
    def setup_page(self):
        settings_group = QGroupBox(_("File associations"))
        # save_box = self.create_checkbox(_("Save file before analyzing it"),
        #                                 'save_before', default=True)

        # Widgets
        list_extensions = QListWidget()
        button_add = QPushButton(_('Add'))
        button_remove = QPushButton(_('Remove'))

        list_editors = QListWidget()
        button_add_editor = QPushButton(_('Add editor'))
        button_remove_editor = QPushButton(_('Remove editor'))
        button_move_up = QPushButton(_('Move up'))
        button_move_down = QPushButton(_('Move down'))

        layout_extensions = QHBoxLayout()
        layout_extensions.addWidget(list_extensions)

        layout_buttons_extensions = QVBoxLayout()
        layout_buttons_extensions.addWidget(button_add)
        layout_buttons_extensions.addWidget(button_remove)
        layout_buttons_extensions.addStretch()

        layout_editors = QHBoxLayout()
        layout_editors.addWidget(list_editors)

        layout_buttons_editors = QVBoxLayout()
        layout_buttons_editors.addWidget(button_add_editor)
        layout_buttons_editors.addWidget(button_move_up)
        layout_buttons_editors.addWidget(button_move_down)
        layout_buttons_editors.addWidget(button_remove_editor)
        layout_buttons_editors.addStretch()

        layout_extensions.addLayout(layout_buttons_extensions)
        layout_editors.addLayout(layout_buttons_editors)

        associations_widget_layout = QHBoxLayout()
        associations_widget_layout.addLayout(layout_extensions)
        associations_widget_layout.addLayout(layout_editors)

        general_widget = QWidget()

        associations_widget = QWidget()
        associations_widget.setLayout(associations_widget_layout)

        tabs = QTabWidget()
        tabs.addTab(self.create_tab(general_widget), _("General"))
        tabs.addTab(self.create_tab(associations_widget), _("File associations"))

        tab_layout = QVBoxLayout()
        tab_layout.addWidget(tabs)

        self.setLayout(tab_layout)
