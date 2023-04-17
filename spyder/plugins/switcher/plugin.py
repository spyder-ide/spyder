# -*- coding: utf-8 -*-
#
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Switcher Plugin.
"""

# Third-party imports
from qtpy.QtCore import Signal

# Standard library imports
import sys

# Local imports
from spyder.api.translations import _
from spyder.api.plugins import Plugins, SpyderPluginV2
from spyder.api.plugin_registration.decorators import (on_plugin_available,
                                                       on_plugin_teardown)
from spyder.plugins.switcher.container import SwitcherContainer
from spyder.plugins.mainmenu.api import ApplicationMenus, FileMenuSections
from spyder.py3compat import TEXT_TYPES


# --- Constants
# ----------------------------------------------------------------------------
class SwitcherActions:
    FileSwitcherAction = 'file switcher'
    SymbolFinderAction = 'symbol finder'


# --- Plugin
# ----------------------------------------------------------------------------
class Switcher(SpyderPluginV2):
    """
    Switcher plugin.
    """

    NAME = "switcher"
    OPTIONAL = [Plugins.MainMenu]
    CONTAINER_CLASS = SwitcherContainer
    CONF_SECTION = NAME
    CONF_FILE = False

    # --- Signals
    sig_rejected = Signal()
    """
    This signal is emitted when the plugin is dismissed.
    """

    sig_text_changed = Signal(TEXT_TYPES[-1])
    """
    This signal is emitted when the plugin search/filter text changes.

    Parameters
    ----------
    search_text: str
        The current search/filter text.
    """

    sig_item_changed = Signal(object)
    """
    This signal is emitted when the plugin current item changes.
    """

    sig_item_selected = Signal(object, TEXT_TYPES[-1], TEXT_TYPES[-1])
    """
    This signal is emitted when an item is selected from the switcher plugin
    list.

    Parameters
    ----------
    item: object
        The current selected item from the switcher list (QStandardItem).
    mode: str
        The current selected mode (open files "", symbol "@" or line ":").
    search_text: str
        Cleaned search/filter text.
    """

    sig_mode_selected = Signal(TEXT_TYPES[-1])
    """
    This signal is emitted when a mode is selected.

    Parameters
    ----------
    mode: str
        The selected mode (open files "", symbol "@" or line ":").
    """

    # --- SpyderPluginV2 API
    # ------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _("Switcher")

    def get_description(self):
        return _("A multi-purpose switcher.")

    def get_icon(self):
        return self.create_icon('filelist')

    def on_initialize(self):
        container = self.get_container()
        self._switcher = container.switcher
        self._modes = {}

        self._switcher.sig_rejected.connect(self.sig_rejected)
        self._switcher.sig_text_changed.connect(self.sig_text_changed)
        self._switcher.sig_item_changed.connect(self.sig_item_changed)
        self._switcher.sig_item_selected.connect(self.sig_item_selected)
        self._switcher.sig_mode_selected.connect(self.sig_mode_selected)

    @on_plugin_available(plugin=Plugins.MainMenu)
    def on_main_menu_available(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)
        for switcher_action in [
                SwitcherActions.FileSwitcherAction,
                SwitcherActions.SymbolFinderAction]:
            action = self.get_action(switcher_action)
            if sys.platform == 'darwin':
                before_section = FileMenuSections.Navigation
            else:
                before_section = FileMenuSections.Restart
            mainmenu.add_item_to_application_menu(
                action,
                menu_id=ApplicationMenus.File,
                section=FileMenuSections.Switcher,
                before_section=before_section
            )

    @on_plugin_teardown(plugin=Plugins.MainMenu)
    def on_main_menu_teardown(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)
        for switcher_action in [
                SwitcherActions.FileSwitcherAction,
                SwitcherActions.SymbolFinderAction]:
            action = self.get_action(switcher_action)
            mainmenu.remove_item_from_application_menu(
                action,
                menu_id=ApplicationMenus.File
            )

    # --- Public API
    # ------------------------------------------------------------------------

    # Switcher methods
    def set_placeholder_text(self, text):
        """Set the text appearing on the empty line edit."""
        self._switcher.set_placeholder_text(text)

    def setup(self):
        """Set-up list widget content based on the filtering."""
        self._switcher.setup()

    def set_position(self, top, parent=None):
        """Set the position of the dialog."""
        self._switcher.set_position(top, parent)

    # QDialog methods
    def show(self):
        """Show switcher widget with QT hide method for QDialog."""
        self._switcher.show()

    def hide(self):
        """Hide switcher widget with QT hide method for QDialog."""
        self._switcher.hide()

    def setVisible(self, visible):
        """Show or hide switcher widget with QT hide method for QDialog."""
        self._switcher.setVisible(visible)

    def isVisible(self):
        """Return if switcher widget is visible with QT hide method
        for QDialog."""
        return self._switcher.isVisible()

    # Item methods
    def current_item(self):
        """Return the current selected item in the list widget."""
        return self._switcher.current_item()

    def add_item(self, icon=None, title=None, description=None, shortcut=None,
                 section=None, data=None, tool_tip=None, action_item=False,
                 last_item=True):
        """Add switcher list item."""
        self._switcher.add_item(icon, title, description, shortcut,
                                section, data, tool_tip, action_item,
                                last_item)

    def add_separator(self):
        """Add separator item."""
        self._switcher.add_separator()

    def clear(self):
        """Remove all items from the list and clear the search text."""
        self._switcher.clear()

    # Mode methods
    def add_mode(self, token, description):
        """Add mode by token key and description."""
        self._switcher.add_mode(token, description)

    def get_mode(self):
        """Get the current mode the switcher is in."""
        self._switcher.get_mode()

    def remove_mode(self, token):
        """Remove mode by token key."""
        self._switcher.remove_mode(token)

    def clear_modes(self):
        """Delete all modes spreviously defined."""
        self._switcher.clear_modes()

    # Lineedit methods
    def set_search_text(self, string):
        """Set the content of the search text."""
        self._switcher.set_search_text(string)
