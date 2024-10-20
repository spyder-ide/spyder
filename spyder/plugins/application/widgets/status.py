# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Status bar widgets."""

# Standard library imports
import os.path as osp
import datetime

# Third-party imports
from qtpy.QtCore import Qt, QUrl
from qtpy.QtWidgets import QDialog, QVBoxLayout

# Local imports
from spyder.api.fonts import SpyderFontType, SpyderFontsMixin
from spyder.api.widgets.status import BaseTimerStatus
from spyder.api.translations import _
from spyder.config.base import get_module_source_path
from spyder.config.gui import is_dark_interface
from spyder.utils.icon_manager import ima
from spyder.utils.qthelpers import start_file
from spyder.utils.stylesheet import WIN
from spyder.widgets.browser import WebView


class InAppAppealDialog(QDialog, SpyderFontsMixin):

    CONF_SECTION = "main"
    WIDTH = 530
    HEIGHT = 620 if WIN else 665

    def __init__(self, parent=None):
        super().__init__(parent)

        # Attributes
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint
        )
        self.setFixedWidth(self.WIDTH)
        self.setFixedHeight(self.HEIGHT)
        self.setWindowTitle(_("Help Spyder"))
        self.setWindowIcon(ima.icon("inapp_appeal"))

        # Path to the appeal page
        appeal_page_path = osp.join(
            get_module_source_path("spyder.plugins.application.widgets"),
            "appeal_page",
            "dark" if is_dark_interface() else "light",
            "index.html",
        )

        # Create webview to render the appeal message
        webview = WebView(self, handle_links=True)

        # Set font used in the view
        app_font = self.get_font(SpyderFontType.Interface)
        webview.set_font(app_font, size_delta=2)

        # Load page
        webview.load(QUrl.fromLocalFile(appeal_page_path))

        # Open links in external browser
        webview.page().linkClicked.connect(self._handle_link_clicks)

        # Layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(webview)
        self.setLayout(layout)

    def _handle_link_clicks(self, url):
        url = str(url.toString())
        if url.startswith('http'):
            start_file(url)


class InAppAppealStatus(BaseTimerStatus):
    """Status bar widget for current file read/write mode."""

    ID = "inapp_appeal_status"
    CONF_SECTION = "main"
    INTERACT_ON_CLICK = True

    DAYS_TO_SHOW_AGAIN = 15

    def __init__(self, parent=None):
        super().__init__(parent)

        self._is_shown = False
        self._appeal_dialog = None

        # We don't need to show a label for this widget
        self.label_value.setVisible(False)

        # Update status every hour
        self.set_interval(60 * 60 * 1000)

        # Show appeal on click
        self.sig_clicked.connect(self._on_click)

    # ---- Private API
    # -------------------------------------------------------------------------
    def _on_click(self):
        """Handle widget clicks."""
        if self._appeal_dialog is None:
            self._appeal_dialog = InAppAppealDialog(self)

        if self._appeal_dialog.isVisible():
            self._appeal_dialog.hide()
        else:
            self._appeal_dialog.show()

    # ---- Public API
    # -------------------------------------------------------------------------
    def show_appeal(self):
        if self._appeal_dialog is None:
            self._appeal_dialog = InAppAppealDialog(self)

        if not self._appeal_dialog.isVisible():
            self._appeal_dialog.show()

    # ---- StatusBarWidget API
    # -------------------------------------------------------------------------
    def get_icon(self):
        return self.create_icon("inapp_appeal")

    def update_status(self):
        """
        Show widget for a day after a certain number of days, then hide it.
        """
        today = datetime.date.today()
        last_date = self.get_conf("last_inapp_appeal", default="")

        if last_date:
            delta = today - datetime.date.fromisoformat(last_date)
            if 0 < delta.days < self.DAYS_TO_SHOW_AGAIN:
                self.setVisible(False)
            else:
                self.setVisible(True)
                self.set_conf("last_inapp_appeal", str(today))
        else:
            self.set_conf("last_inapp_appeal", str(today))

    def get_tooltip(self):
        return _("Help Spyder!")

    # ---- Qt methods
    # -------------------------------------------------------------------------
    def showEvent(self, event):
        super().showEvent(event)

        # Hide widget if necessary at startup
        if not self._is_shown:
            self.update_status()
            self._is_shown = True
