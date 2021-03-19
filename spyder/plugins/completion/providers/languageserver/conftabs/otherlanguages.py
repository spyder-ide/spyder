# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Language Server Protocol configuration tabs.
"""

# Third party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (QGroupBox, QGridLayout, QLabel,
                            QPushButton, QVBoxLayout)

# Local imports
from spyder.api.preferences import SpyderPreferencesTab
from spyder.config.base import _
from spyder.plugins.completion.api import SUPPORTED_LANGUAGES
from spyder.plugins.completion.providers.languageserver.widgets import (
    LSPServerTable)
from spyder.utils.icon_manager import ima

LSP_URL = "https://microsoft.github.io/language-server-protocol"


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
