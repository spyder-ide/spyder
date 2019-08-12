# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""File explorer configuration page."""

# Third party imports
from qtpy.QtWidgets import QTabWidget, QVBoxLayout, QWidget

# Local imports
from spyder.api.preferences import PluginConfigPage
from spyder.config.base import _
from spyder.py3compat import to_text_string
from spyder.plugins.explorer.widgets.fileassociations import (
    FileAssociationsWidget)


class ExplorerConfigPage(PluginConfigPage):

    def setup_page(self):
        # Variables
        newcb = self.create_checkbox

        # Widgets
        general_widget = QWidget()
        check_show_all = newcb(_("Show all files"), 'show_all')
        check_icon = newcb(_("Show icons and text"), 'show_icontext')
        check_single_click = newcb(_("Single click to open files"),
                                   'single_click_to_open')
        edit_filename_filters = self.create_textedit(
            _("Edit filename filters..."),
            'name_filters',
            tip=("Enter values separated by commas"),
            content_type=list,
        )
        associations_widget = QWidget()
        self.edit_file_associations = self.create_textedit(
            '',
            'file_associations',
            content_type=dict,
        )
        file_associations = FileAssociationsWidget()

        # Widget setup
        file_associations.load_values(self.get_option('file_associations'))
        # The actual config data is stored on this text edit set to invisible
        self.edit_file_associations.setVisible(False)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(check_show_all)
        layout.addWidget(check_icon)
        layout.addWidget(check_single_click)
        layout.addWidget(edit_filename_filters)
        general_widget.setLayout(layout)

        layout_file = QVBoxLayout()
        layout_file.addWidget(file_associations)
        layout_file.addWidget(self.edit_file_associations)
        associations_widget.setLayout(layout_file)

        tabs = QTabWidget()
        tabs.addTab(self.create_tab(general_widget), _("General"))
        tabs.addTab(self.create_tab(associations_widget),
                    _("File associations"))

        tab_layout = QVBoxLayout()
        tab_layout.addWidget(tabs)

        self.setLayout(tab_layout)

        # Signals
        file_associations.sig_data_changed.connect(self.update_associations)

    def update_associations(self, data):
        """
        Update the content of the text edit used to store the config data.
        """
        textedit = self.edit_file_associations.textbox
        textedit.setPlainText(to_text_string(data))
