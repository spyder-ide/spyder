# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Third party imports
from qtpy.QtCore import QSize, Signal, Slot
from qtpy.QtWidgets import QDialog, QDialogButtonBox, QHBoxLayout, QPushButton
from superqt.utils import qdebounced

# Local imports
from spyder.api.widgets.dialogs import SpyderDialogButtonBox
from spyder.config.base import _, load_lang_conf
from spyder.config.manager import CONF
from spyder.utils.icon_manager import ima
from spyder.utils.stylesheet import MAC, WIN
from spyder.widgets.sidebardialog import SidebarDialog


class ConfigDialog(SidebarDialog):
    """Preferences dialog."""

    # Signals
    check_settings = Signal()
    sig_size_changed = Signal(QSize)
    sig_reset_preferences_requested = Signal()

    # Constants
    TITLE = _("Preferences")
    ICON = ima.icon('configure')
    MIN_WIDTH = 940 if MAC else (875 if WIN else 920)
    MIN_HEIGHT = 700 if MAC else (660 if WIN else 670)

    def __init__(self, parent=None):
        SidebarDialog.__init__(self, parent)

        # Attributes
        self.main = parent

        # Ensures that the config is present on spyder first run
        CONF.set('main', 'interface_language', load_lang_conf())

    # ---- Public API
    # -------------------------------------------------------------------------
    def get_index_by_name(self, name):
        """Return page index by CONF_SECTION name."""
        for idx in range(self.pages_widget.count()):
            page = self.get_page(idx)

            # This is the case for separators
            if page is None:
                continue

            try:
                # New API
                section = page.plugin.NAME
            except AttributeError:
                section = page.CONF_SECTION

            if section == name:
                return idx
        else:
            return None

    def check_all_settings(self):
        """
        This method is called to check all configuration page settings after
        configuration dialog has been shown.
        """
        self.check_settings.emit()

    # ---- SidebarDialog API
    # -------------------------------------------------------------------------
    def button_clicked(self, button):
        if button is self.apply_btn:
            # Apply button was clicked
            configpage = self.get_page()
            if not configpage.is_valid():
                return
            configpage.apply_changes()

    def current_page_changed(self, index):
        widget = self.get_page(index)
        self.apply_btn.setVisible(widget.apply_callback is not None)
        self.apply_btn.setEnabled(widget.is_modified)

    def add_page(self, page, initialize=False):
        # Signals
        self.check_settings.connect(page.check_settings)
        page.apply_button_enabled.connect(self.apply_btn.setEnabled)
        super().add_page(page, initialize=initialize)

    def create_buttons(self):
        bbox = SpyderDialogButtonBox(
            QDialogButtonBox.Ok
            | QDialogButtonBox.Apply
            | QDialogButtonBox.Cancel
        )
        self.apply_btn = bbox.button(QDialogButtonBox.Apply)

        # This is needed for our tests
        self.ok_btn = bbox.button(QDialogButtonBox.Ok)

        button_reset = QPushButton(_('Reset to defaults'))
        button_reset.clicked.connect(self.sig_reset_preferences_requested)
        bbox.addButton(button_reset, QDialogButtonBox.ResetRole)

        layout = QHBoxLayout()
        layout.addWidget(bbox)

        return bbox, layout

    # ---- Qt methods
    # -------------------------------------------------------------------------
    @Slot()
    def accept(self):
        for index in range(self.pages_widget.count()):
            configpage = self.get_page(index)

            # This can be the case for separators, which doesn't have a config
            # page.
            if configpage is None:
                continue

            if not configpage.is_valid():
                return

            configpage.apply_changes()

        QDialog.accept(self)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._on_resize()

    # ---- Private API
    # -------------------------------------------------------------------------
    @qdebounced(timeout=40)
    def _on_resize(self):
        """
        We name this method differently from SidebarDialog._on_resize_event
        because we want to debounce this as well.
        """
        self.sig_size_changed.emit(self.size())
