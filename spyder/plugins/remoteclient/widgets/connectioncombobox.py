# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Dialog to handle remote connections."""

# Standard library imports
from __future__ import annotations

# Third party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QWidget

# Local imports
from spyder.api.translations import _
from spyder.api.widgets.comboboxes import SpyderComboBox
from spyder.plugins.remoteclient.api.protocol import ConnectionStatus
from spyder.widgets.config import ConfigAccessMixin


class ConnectionComboBox(SpyderComboBox, ConfigAccessMixin):
    """
    Combobox to display remote connections available.
    """
    CONF_SECTION="remoteclient"

    def __init__(
        self,
        parent: QWidget | None = None,
        items_elide_mode: Qt.TextElideMode | None = None,
        item_template: str | None = None,
        default_item: tuple | None = None,
    ) -> None:
        super().__init__(parent=parent, items_elide_mode=items_elide_mode)
        self._item_template = item_template
        self._default_item = default_item

        # -- Setup
        self._setup_connections()

    # ---- Private API
    # -------------------------------------------------------------------------
    def _setup_connections(self) -> None:
        """Add the connection info items to the combobox."""
        # Add default item
        if self._default_item:
            self.addItem(*self._default_item)
            self.setCurrentText(self._default_item[0])

        # Add items for active remote machines/connections
        servers = self.get_option("servers", default={})
        
        for server_id in servers.keys():
            server_status = self.get_option(f"{server_id}/status")
            if server_status == ConnectionStatus.Active:
                server_auth = self.get_option(f"{server_id}/auth_method")
                server_name = self.get_option(f"{server_id}/{server_auth}/name")
                item_text = server_name
                if self._item_template:
                    item_text = self._item_template.format(
                        server_name=server_name
                    )
                self.addItem(item_text, server_id)


def test():
    import sys
    
    from qtpy.QtWidgets import QVBoxLayout
    
    from spyder.utils.qthelpers import qapplication
    from spyder.utils.stylesheet import APP_STYLESHEET

    app = qapplication()  # noqa
    app.setStyleSheet(str(APP_STYLESHEET))

    widget = QWidget()
    layout = QVBoxLayout(widget)
    combobox = ConnectionComboBox(
        parent=widget,
        item_template="Project in {server_name} server",
        default_item=(_("Local project"), None),
    )
    layout.addWidget(combobox)
    widget.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    test()
