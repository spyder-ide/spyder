# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Preference tab listing the language servers of the LSP provider."""

# Third party imports
from qtpy.QtCore import QSize, Qt
from qtpy.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout

# Local imports
from spyder.api.preferences import SpyderPreferencesTab
from spyder.api.translations import _
from spyder.plugins.languageservices.providers.lsp.widgets.serversconfig import (
    LSPServerTable,
)
from spyder.utils.icon_manager import ima
from spyder.utils.stylesheet import AppStyle

LSP_URL = "https://microsoft.github.io/language-server-protocol"


class ServersConfigTab(SpyderPreferencesTab):
    """Servers table with add/delete/reset buttons."""

    TITLE = _("Language servers")

    def __init__(self, parent):
        super().__init__(parent)

        servers_label = QLabel(
            _(
                'Spyder uses the <a href="{lsp_url}">Language Server '
                "Protocol</a> to provide code completion and linting for "
                "its Editor. Here, you can set up and configure the servers "
                "Spyder connects to, for any language."
            ).format(lsp_url=LSP_URL)
        )
        servers_label.setOpenExternalLinks(True)
        servers_label.setWordWrap(True)
        servers_label.setAlignment(Qt.AlignJustify)

        table_label = QLabel(_("Available servers:"))
        self.table = LSPServerTable(self)
        self.table.setMaximumHeight(200)

        table_layout = QHBoxLayout()
        table_layout.addSpacing(2 * AppStyle.MarginSize)
        table_layout.addWidget(self.table)
        table_layout.addSpacing(2 * AppStyle.MarginSize)

        self.new_btn = QPushButton(icon=ima.icon("edit_add"))
        self.new_btn.setToolTip(_("Set up a new server"))
        self.delete_btn = QPushButton(icon=ima.icon("editclear"))
        self.delete_btn.setToolTip(_("Delete currently selected server"))
        self.reset_btn = QPushButton(icon=ima.icon("restart"))
        self.reset_btn.setToolTip(_("Remove all servers"))
        self.delete_btn.setEnabled(False)

        self.new_btn.clicked.connect(self.create_new_server)
        self.reset_btn.clicked.connect(self.reset_to_default)
        self.delete_btn.clicked.connect(self.delete_server)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        for btn in (self.new_btn, self.delete_btn, self.reset_btn):
            btn.setIconSize(
                QSize(AppStyle.ConfigPageIconSize, AppStyle.ConfigPageIconSize)
            )
            buttons_layout.addWidget(btn)
        buttons_layout.addStretch()

        layout = QVBoxLayout()
        layout.addWidget(servers_label)
        layout.addSpacing(3 * AppStyle.MarginSize)
        layout.addWidget(table_label)
        layout.addLayout(table_layout)
        layout.addSpacing(AppStyle.MarginSize)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def server_names(self):
        return self.table.server_names()

    def create_new_server(self):
        self.table.show_editor(new_server=True)

    def delete_server(self):
        self.table.delete_server(self.table.currentIndex().row())
        self.set_modified(True)
        self.delete_btn.setEnabled(False)

    def reset_to_default(self):
        self.table.clear_servers()
        self.set_modified(True)

    def apply_settings(self):
        return self.table.save_servers()
