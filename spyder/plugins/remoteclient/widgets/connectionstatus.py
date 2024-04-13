# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Connection status widget."""

import qstylizer.style
from qtpy.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from spyder.api.config.fonts import SpyderFontType, SpyderFontsMixin
from spyder.api.config.mixins import SpyderConfigurationAccessor
from spyder.api.translations import _
from spyder.api.widgets.mixins import SvgToScaledPixmap
from spyder.plugins.remoteclient.api.protocol import (
    ConnectionInfo,
    ConnectionStatus,
)
from spyder.plugins.remoteclient.widgets import AuthenticationMethod
from spyder.utils.palette import SpyderPalette
from spyder.utils.stylesheet import AppStyle


# ---- Constants
# -----------------------------------------------------------------------------
STATUS_TO_TRANSLATION_STRINGS = {
    ConnectionStatus.Inactive: _("Inactive"),
    ConnectionStatus.Connecting: _("Connecting..."),
    ConnectionStatus.Active: _("Active"),
    ConnectionStatus.Stopping: _("Stopping..."),
    ConnectionStatus.Error: _("Error"),
}

STATUS_TO_COLOR = {
    ConnectionStatus.Inactive: SpyderPalette.COLOR_OCCURRENCE_5,
    ConnectionStatus.Connecting: SpyderPalette.COLOR_WARN_4,
    ConnectionStatus.Active: SpyderPalette.COLOR_SUCCESS_3,
    ConnectionStatus.Stopping: SpyderPalette.COLOR_WARN_4,
    ConnectionStatus.Error: SpyderPalette.COLOR_ERROR_2,
}

STATUS_TO_ICON = {
    ConnectionStatus.Inactive: "connection_disconnected",
    ConnectionStatus.Connecting: "connection_waiting",
    ConnectionStatus.Active: "connection_connected",
    ConnectionStatus.Stopping: "connection_waiting",
    ConnectionStatus.Error: "connection_error",
}


# ---- Widget
# -----------------------------------------------------------------------------
class ConnectionStatusWidget(
    QWidget,
    SpyderFontsMixin,
    SvgToScaledPixmap,
    SpyderConfigurationAccessor,
):

    CONF_SECTION = "remoteclient"

    def __init__(self, parent, host_id):
        super().__init__(parent)
        self.host_id = host_id

        # TODO: Address this for configfile login
        if self._auth_method != AuthenticationMethod.ConfigFile:
            self.address = self.get_conf(
                f"{host_id}/{self._auth_method}/address"
            )
            username = self.get_conf(f"{host_id}/{self._auth_method}/username")
        else:
            self.address = ""
            username = ""

        # Widgets
        self._connection_label = QLabel(self)
        self._status_label = QLabel(self)
        self._user_label = QLabel(_("Username: {}").format(username), self)
        self._message_label = QLabel(self)
        self._message_label.setWordWrap(True)

        # Image
        self._image_label = QLabel(self)

        # Initial text and style
        self._set_initial_text_in_labels()
        self._set_stylesheet()

        # Info layout
        info_layout = QVBoxLayout()
        info_layout.setSpacing(0)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.addWidget(self._connection_label)
        info_layout.addWidget(self._status_label)
        info_layout.addWidget(self._user_label)
        info_layout.addSpacing(4 * AppStyle.MarginSize)
        info_layout.addWidget(self._message_label)
        info_layout.addStretch()

        # This is necessary to align the image on the top side to the info
        # widgets to the left
        image_layout = QVBoxLayout()
        image_layout.setContentsMargins(0, 2 * AppStyle.MarginSize, 0, 0)
        image_layout.addWidget(self._image_label)

        # Final layout
        layout = QHBoxLayout()
        layout.addLayout(info_layout)
        layout.setStretchFactor(info_layout, 2)
        layout.addSpacing(4 * AppStyle.MarginSize)
        layout.addLayout(image_layout)
        layout.setStretchFactor(image_layout, 1)
        self.setLayout(layout)

    # ---- Public API
    # -------------------------------------------------------------------------
    def update_status(self, info: ConnectionInfo):
        status = info["status"]
        message = info["message"]

        self._set_icon(status)
        self._set_text_in_labels(status)
        self._message_label.setText(message)

    # ---- Private API
    # -------------------------------------------------------------------------
    def _set_stylesheet(self):
        """Set stylesheet for elements in this widget."""
        # Increase font size of connection label
        font_size = self.get_font(SpyderFontType.Interface).pointSize()
        important_labels_css = qstylizer.style.StyleSheet()
        important_labels_css.QLabel.setValues(
            fontSize=f"{font_size + 1}pt",
        )
        for label in [self._connection_label, self._message_label]:
            label.setStyleSheet(important_labels_css.toString())

        # Indent status and user labels inside the connection one
        other_labels_css = qstylizer.style.StyleSheet()
        other_labels_css.setValues(
            marginLeft=f"{9 * AppStyle.MarginSize}px"
        )
        for label in [self._status_label, self._user_label]:
            label.setStyleSheet(other_labels_css.toString())

    def _set_initial_text_in_labels(self):
        status = self.get_conf(
            f"{self.host_id}/status", default=ConnectionStatus.Inactive
        )
        self._set_text_in_labels(status)
        self._set_icon(status)

        message = self.get_conf(f"{self.host_id}/status_message", default="")
        if not message:
            # This can only happen at startup or if the connection has never
            # been used
            message = _("The connection hasn't been used")
        self._message_label.setText(message)

    def _set_text_in_labels(self, status):
        color = STATUS_TO_COLOR[status]
        localized_status = STATUS_TO_TRANSLATION_STRINGS[status]

        self._connection_label.setText(
            _('Connection to: <span style="color:{}">{}<span>').format(
                color, self.address
            )
        )

        self._status_label.setText(
            _('Status: <span style="color:{}">{}<span>').format(
                color, localized_status
            )
        )

    def _set_icon(self, status):
        self._image_label.setPixmap(
            self.svg_to_scaled_pixmap(STATUS_TO_ICON[status], rescale=1)
        )

    @property
    def _auth_method(self):
        """Get authentication method."""
        return self.get_conf(f"{self.host_id}/auth_method")
