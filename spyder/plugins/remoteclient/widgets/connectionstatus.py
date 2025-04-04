# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Connection status widget."""

from collections.abc import Iterable
import logging

import qstylizer.style
from qtpy.QtGui import QTextCursor
from qtpy.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from spyder.api.config.mixins import SpyderConfigurationAccessor
from spyder.api.fonts import SpyderFontType, SpyderFontsMixin
from spyder.api.translations import _
from spyder.api.widgets.mixins import SvgToScaledPixmap
from spyder.plugins.remoteclient.api import MAX_CLIENT_MESSAGES
from spyder.plugins.remoteclient.api.protocol import (
    ConnectionInfo,
    ConnectionStatus,
    RemoteClientLog,
)
from spyder.plugins.remoteclient.widgets import AuthenticationMethod
from spyder.utils.palette import SpyderPalette
from spyder.utils.stylesheet import AppStyle, MAC
from spyder.widgets.simplecodeeditor import SimpleCodeEditor


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

LOG_LEVEL_TO_FMT_STRING = {
    # It could be confusing to users to see a "Debug" message, so we prefer to
    # show it as "Info".
    logging.DEBUG: "<b>Info:</b>",
    logging.INFO: "<b>Info:</b>",
    logging.WARNING: (
        f'<span style="color:{STATUS_TO_COLOR[ConnectionStatus.Connecting]};">'
        f'<b>Warning:</b></span>'
    ),
    logging.ERROR: (
        f'<span style="color:{STATUS_TO_COLOR[ConnectionStatus.Error]};">'
        f'<b>Error:</b></span>'
    ),
    logging.CRITICAL: (
        f'<span style="color:{STATUS_TO_COLOR[ConnectionStatus.Error]};">'
        f'<b>Critical:</b></span>'
    ),
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
        self._image_label = QLabel(self)
        self._log_label = QLabel(_("Connection messages"))
        self._log_widget = SimpleCodeEditor(self)
        self._copy_logs_button = QPushButton(_("Copy messages"))

        # Initial settings
        self._set_initial_text_in_labels()
        self._set_stylesheet()

        self._log_widget.setMaximumBlockCount(MAX_CLIENT_MESSAGES)
        self._log_widget.setReadOnly(True)
        self._log_widget.setMinimumHeight(210 if MAC else 230)
        self._log_widget.setPlaceholderText(_("No logs to show"))

        self._copy_logs_button.setEnabled(False)
        self._copy_logs_button.clicked.connect(self._copy_logs)

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

        # Top layout
        top_layout = QHBoxLayout()
        top_layout.addLayout(info_layout)
        top_layout.setStretchFactor(info_layout, 2)
        top_layout.addStretch()
        top_layout.addLayout(image_layout)

        # Bottom layout
        bottom_layout = QVBoxLayout()
        bottom_layout.setSpacing(0)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.addWidget(self._log_label)
        bottom_layout.addWidget(self._log_widget)

        copy_layout = QHBoxLayout()
        copy_layout.addStretch()
        copy_layout.addWidget(self._copy_logs_button)
        bottom_layout.addSpacing(6)
        bottom_layout.addLayout(copy_layout)

        # Final layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(top_layout)
        layout.addSpacing(6 * AppStyle.MarginSize)
        layout.addLayout(bottom_layout)
        self.setLayout(layout)

    # ---- Public API
    # -------------------------------------------------------------------------
    def update_status(self, info: ConnectionInfo):
        """Update graphical elements related to the connection status."""
        status = info["status"]
        message = info["message"]

        self._set_icon(status)
        self._set_text_in_labels(status)
        self._message_label.setText(message)

    def add_log(self, log: RemoteClientLog):
        """Add a new log message to the log widget."""
        if not self._copy_logs_button.isEnabled():
            self._copy_logs_button.setEnabled(True)

        formatted_log = (
            # Message
            f"<p>{LOG_LEVEL_TO_FMT_STRING[log['level']]} {log['message']}</p>"
            # Small vertical space to separate logs
            f"<div style='font-size: 2pt;font-weight: normal;'><p></p></div>"
        )

        # Move cursor so that new logs are always shown at the end
        self._log_widget.moveCursor(QTextCursor.End)
        self._log_widget.appendHtml(formatted_log)
        self._log_widget.moveCursor(QTextCursor.End)

    def add_logs(self, logs: Iterable):
        """Add saved log messages to the log widget."""
        for log in logs:
            self.add_log(log)

    # ---- Private API
    # -------------------------------------------------------------------------
    def _set_stylesheet(self):
        """Set stylesheet for elements in this widget."""
        # -- Style of important labels
        font_size = self.get_font(SpyderFontType.Interface).pointSize()
        important_labels_css = qstylizer.style.StyleSheet()
        important_labels_css.QLabel.setValues(
            fontSize=f"{font_size + 1}pt",
        )

        # Remove automatic indent added by Qt
        important_labels_css.setValues(**{'qproperty-indent': '0'})

        for label in [self._connection_label, self._message_label]:
            label.setStyleSheet(important_labels_css.toString())

        # -- Style of other info labels
        other_info_labels_css = qstylizer.style.StyleSheet()
        other_info_labels_css.setValues(
            marginLeft=f"{9 * AppStyle.MarginSize}px"
        )
        for label in [self._status_label, self._user_label]:
            label.setStyleSheet(other_info_labels_css.toString())

        # -- Style of log widgets
        log_label_css = qstylizer.style.StyleSheet()
        log_label_css.QLabel.setValues(
            # Increase padding (the default one is too small).
            padding=f"{2 * AppStyle.MarginSize}px",
            # Make it a bit different from a default QPushButton to not drag
            # the same amount of attention to it.
            backgroundColor=SpyderPalette.COLOR_BACKGROUND_3,
            # Remove bottom rounded borders
            borderBottomLeftRadius='0px',
            borderBottomRightRadius='0px',
            # This is necessary to align the label to the text above it
            marginLeft="2px",
        )
        self._log_label.setStyleSheet(log_label_css.toString())

        self._log_widget.css.QPlainTextEdit.setValues(
            # Remove these borders to make it appear attached to the top label
            borderTop="0px",
            borderTopLeftRadius='0px',
            borderTopRightRadius='0px',
            # Match border color with the top label one and avoid to change
            # that color when the widget is given focus
            borderLeft=f"1px solid {SpyderPalette.COLOR_BACKGROUND_3}",
            borderRight=f"1px solid {SpyderPalette.COLOR_BACKGROUND_3}",
            borderBottom=f"1px solid {SpyderPalette.COLOR_BACKGROUND_3}",
            # This is necessary to align the widget to the top label
            marginLeft="2px",
            # Increase padding a bit to make text look better
            paddingLeft="6px",
            paddingRight="6px",
            paddingTop="6px",
            # No need to have this due to the scrollbar
            paddingBottom="0px",
        )
        self._log_widget.setStyleSheet(self._log_widget.css.toString())

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

    def _copy_logs(self, clicked):
        """Copy log messages to clipboard."""
        text = self._log_widget.toPlainText()
        QApplication.clipboard().setText(text)
