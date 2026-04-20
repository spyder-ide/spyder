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
from qtpy.QtWidgets import QHBoxLayout, QLabel, QWidget

# Local imports
from spyder.api.config.mixins import SpyderConfigurationAccessor
from spyder.api.translations import _
from spyder.api.widgets.comboboxes import SpyderComboBox


class ConnectionComboBox(SpyderComboBox, SpyderConfigurationAccessor):
    """
    Widget to display remote connections available.
    """

    CONF_SECTION = "remoteclient"

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

        # -- Setup items
        self._setup_connections()

    # ---- Public API
    # -------------------------------------------------------------------------
    @staticmethod
    def create_combobox(
        label: str = _("Server:"),
        parent: QWidget | None = None,
        items_elide_mode: Qt.TextElideMode | None = None,
        item_template: str = "{server_name}",
        default_item: tuple = (_("Local"), None),
    ) -> QWidget:
        """
        Create a connection combobox instance inside a layout with a label.

        Parameters
        ----------
        label : str, optional
            Text to use for label in the left side of the combobox.
            The default is _("Server:").
        parent : QWidget, optional
            Parent widget to set. The default is None.
        items_elide_mode : Qt.TextElideMode, optional
            Elide mode items should use. The default is None.
        item_template : str, optional
            Template to use when creating an item label. The default is "{server_name}".
        default_item : tuple, optional
            Default item to add to the combobox. The default is (_("Local"), None).

        Returns
        -------
        QWidget
            Wrapper widget containing label and actual combobox widgets.
        """
        layout = QHBoxLayout()
        widget = QWidget(parent)
        widget.label = QLabel(label)
        widget.combobox = ConnectionComboBox(
            parent=widget,
            items_elide_mode=items_elide_mode,
            item_template=item_template,
            default_item=default_item,
        )
        layout.addWidget(widget.label)
        layout.addWidget(widget.combobox)
        layout.addStretch(1)
        widget.setLayout(layout)

        return widget

    def get_current_server_id(self) -> str:
        return self.currentData()

    # ---- Private API
    # -------------------------------------------------------------------------
    def _setup_connections(self) -> None:
        """Add the connection info items to the combobox."""
        # Add default item
        if self._default_item:
            self.addItem(*self._default_item)
            self.setCurrentText(self._default_item[0])

        # Add item per remote machine/connection available
        servers = self.get_conf("servers", default={})

        for server_id in servers.keys():
            server_auth = self.get_conf(f"{server_id}/auth_method")
            server_name = self.get_conf(f"{server_id}/{server_auth}/name")
            item_text = server_name
            if self._item_template:
                item_text = self._item_template.format(server_name=server_name)
            self.addItem(item_text, server_id)


def test() -> None:
    import sys

    from spyder.utils.qthelpers import qapplication
    from spyder.utils.stylesheet import APP_STYLESHEET

    app = qapplication()  # noqa
    app.setStyleSheet(str(APP_STYLESHEET))

    combobox_widget = ConnectionComboBox.create_combobox()
    combobox = combobox_widget.combobox
    combobox.currentTextChanged.connect(
        lambda: print(combobox.get_current_server_id())
    )
    combobox_widget.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    test()
