# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Status bar widgets."""

# Standard library imports
import datetime
import os.path as osp
from string import Template
import webbrowser

# Third-party imports
from markdown_it import MarkdownIt
from qtpy import QtModuleNotInstalledError
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


DONATIONS_URL = "https://www.spyder-ide.org/donate"
CHANGELOG_URL = (
    "https://github.com/spyder-ide/spyder/blob/6.x/changelogs/"
    "Spyder-6.md#version-612-2025-12-17"
)


class FakeInAppAppealDialog:
    """Fake class used as the in-app dialog in case it can't be built."""
    pass


class InAppAppealDialog(QDialog, SpyderFontsMixin):

    CONF_SECTION = "main"
    WIDTH = 530
    HEIGHT = 620 if WIN else 640  # TODO: Check on Win/Mac

    def __init__(self, parent=None):
        super().__init__(parent)

        # Leave this import here to make Spyder work without WebEngine.
        from spyder.widgets.browser import WebView

        # Attributes
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint
        )
        self.setFixedWidth(self.WIDTH)
        self.setFixedHeight(self.HEIGHT)
        self.setWindowIcon(ima.icon("inapp_appeal"))

        # Paths to content to be loaded
        appeal_page_dir = osp.join(
            get_module_source_path("spyder.plugins.application.widgets"),
            "appeal_page",
        )
        changelog_path = osp.join(appeal_page_dir, "changelog.md")
        self._appeal_page_path = osp.join(
            appeal_page_dir,
            "dark" if is_dark_interface() else "light",
            "index.html",
        )

        # Render changelog to html
        with open(changelog_path, "r") as f:
            changelog_md = f.read()

        self._changelog = (
            MarkdownIt(options_update={"breaks": True})
            .render(changelog_md)
            .strip()
            .replace("\n", "")
        )

        # Read html for appeal page
        with open(self._appeal_page_path, "r") as f:
            self._appeal_page = f.read()

        # Create webview to render the appeal message and changelog
        self._webview = WebView(self, handle_links=True)

        # Set font used in the view
        app_font = self.get_font(SpyderFontType.Interface)
        self._webview.set_font(app_font, size_delta=2)

        # Open links in external browser
        self._webview.page().linkClicked.connect(self._handle_link_clicks)

        # Layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._webview)
        self.setLayout(layout)

    def _handle_link_clicks(self, url):
        url = str(url.toString())
        if url.startswith('http'):
            start_file(url)

    def set_message(self, appeal: bool):
        template = Template(self._appeal_page)
        rendered_page = template.substitute(
            changelog_html=self._changelog,
            show_changelog="false" if appeal else "true",
        )

        # Load page
        self._webview.setHtml(
            rendered_page,
            QUrl.fromLocalFile(self._appeal_page_path)
        )


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
            self._create_appeal_dialog()

        if self._appeal_dialog is not FakeInAppAppealDialog:
            if self._appeal_dialog.isVisible():
                self._appeal_dialog.hide()
            else:
                self._appeal_dialog.show()
        else:
            webbrowser.open(DONATIONS_URL)

    def _create_appeal_dialog(self):
        try:
            self._appeal_dialog = InAppAppealDialog(self)
        except QtModuleNotInstalledError:
            # QtWebEngineWidgets is optional.
            # See spyder-ide/spyder#24905 for the details.
            self._appeal_dialog = FakeInAppAppealDialog

    def _show_dialog(self, show_appeal: bool):
        if self._appeal_dialog is not FakeInAppAppealDialog:
            if not self._appeal_dialog.isVisible():
                self._appeal_dialog.set_message(show_appeal)
                self._appeal_dialog.show()
        else:
            if show_appeal:
                webbrowser.open(DONATIONS_URL)
            else:
                webbrowser.open(CHANGELOG_URL)

    # ---- Public API
    # -------------------------------------------------------------------------
    def show_changelog(self):
        if self._appeal_dialog is None:
            self._create_appeal_dialog()

        if self._appeal_dialog is not FakeInAppAppealDialog:
            self._appeal_dialog.setWindowTitle(_("Changelog"))

        self._show_dialog(show_appeal=False)

    def show_appeal(self):
        if self._appeal_dialog is None:
            self._create_appeal_dialog()

        if self._appeal_dialog is not FakeInAppAppealDialog:
            self._appeal_dialog.setWindowTitle(_("Help Spyder"))

        self._show_dialog(show_appeal=True)

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
