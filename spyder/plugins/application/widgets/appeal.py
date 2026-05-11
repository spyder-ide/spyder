# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""In-app appeal dialog."""

# Standard library imports
import os.path as osp
from string import Template

# Third-party imports
from markdown_it import MarkdownIt
from qtpy.QtCore import Qt, QUrl
from qtpy.QtWidgets import QDialog, QVBoxLayout

# Local imports
from spyder.api.fonts import SpyderFontType, SpyderFontsMixin
from spyder.config.base import get_module_source_path
from spyder.config.gui import is_dark_interface
from spyder.utils.icon_manager import ima
from spyder.utils.qthelpers import start_file
from spyder.utils.stylesheet import WIN


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
