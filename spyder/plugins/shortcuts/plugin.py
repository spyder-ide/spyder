# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Shortcuts Plugin.
"""

# Standard library imports
import configparser
import sys

# Third party imports
from qtpy.QtCore import Qt, Signal, Slot
from qtpy.QtGui import QKeySequence
from qtpy.QtWidgets import QAction, QShortcut

# Local imports
from spyder.api.plugins import Plugins, SpyderPluginV2
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.api.translations import _
from spyder.plugins.mainmenu.api import ApplicationMenus, HelpMenuSections
from spyder.plugins.shortcuts.confpage import ShortcutsConfigPage
from spyder.plugins.shortcuts.widgets.summary import ShortcutsSummaryDialog
from spyder.utils.qthelpers import add_shortcut_to_tooltip, SpyderAction


class ShortcutActions:
    ShortcutSummaryAction = "show_shortcut_summary_action"


# --- Plugin
# ----------------------------------------------------------------------------
class Shortcuts(SpyderPluginV2):
    """
    Shortcuts Plugin.
    """

    NAME = 'shortcuts'
    # TODO: Fix requires to reflect the desired order in the preferences
    REQUIRES = [Plugins.Preferences]
    OPTIONAL = [Plugins.MainMenu]
    CONF_WIDGET_CLASS = ShortcutsConfigPage
    CONF_SECTION = NAME
    CONF_FILE = False
    CAN_BE_DISABLED = False

    # --- Signals
    # ------------------------------------------------------------------------
    sig_shortcuts_updated = Signal()
    """
    This signal is emitted to inform shortcuts have been updated.
    """

    # --- SpyderPluginV2 API
    # ------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _("Keyboard shortcuts")

    def get_description(self):
        return _("Manage application, widget and actions shortcuts.")

    def get_icon(self):
        return self.create_icon('keyboard')

    def on_initialize(self):
        self._shortcut_data = []
        self.create_action(
            ShortcutActions.ShortcutSummaryAction,
            text=_("Shortcuts Summary"),
            triggered=self.show_summary,
            register_shortcut=True,
            context=Qt.ApplicationShortcut,
        )

    @on_plugin_available(plugin=Plugins.Preferences)
    def on_preferences_available(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.register_plugin_preferences(self)

    @on_plugin_available(plugin=Plugins.MainMenu)
    def on_main_menu_available(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)
        shortcuts_action = self.get_action(
            ShortcutActions.ShortcutSummaryAction)

        # Add to Help menu.
        mainmenu.add_item_to_application_menu(
            shortcuts_action,
            menu_id=ApplicationMenus.Help,
            section=HelpMenuSections.Documentation,
            before_section=HelpMenuSections.Support
        )

    @on_plugin_teardown(plugin=Plugins.Preferences)
    def on_preferences_teardown(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.deregister_plugin_preferences(self)

    @on_plugin_teardown(plugin=Plugins.MainMenu)
    def on_main_menu_teardown(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)
        mainmenu.remove_item_from_application_menu(
            ShortcutActions.ShortcutSummaryAction,
            menu_id=ApplicationMenus.Help
        )

    def on_mainwindow_visible(self):
        self.apply_shortcuts()

    # --- Public API
    # ------------------------------------------------------------------------
    def get_shortcut_data(self):
        """
        Return the registered shortcut data from the main application window.
        """
        return self._shortcut_data

    def reset_shortcuts(self):
        """Reset shrotcuts."""
        if self._conf:
            self._conf.reset_shortcuts()

    @Slot()
    def show_summary(self):
        """Reset shortcuts."""
        dlg = ShortcutsSummaryDialog(None)
        dlg.exec_()

    def register_shortcut(self, qaction_or_qshortcut, context, name,
                          add_shortcut_to_tip=True, plugin_name=None):
        """
        Register QAction or QShortcut to Spyder main application,
        with shortcut (context, name, default)
        """
        self._shortcut_data.append((qaction_or_qshortcut, context,
                                   name, add_shortcut_to_tip, plugin_name))

    def unregister_shortcut(self, qaction_or_qshortcut, context, name,
                            add_shortcut_to_tip=True, plugin_name=None):
        """
        Unregister QAction or QShortcut from Spyder main application.
        """
        data = (qaction_or_qshortcut, context, name, add_shortcut_to_tip,
                plugin_name)

        if data in self._shortcut_data:
            self._shortcut_data.remove(data)

    def apply_shortcuts(self):
        """
        Apply shortcuts settings to all widgets/plugins.
        """
        toberemoved = []

        # TODO: Check shortcut existence based on action existence, so that we
        # can update shortcut names without showing the old ones on the
        # preferences
        for index, (qobject, context, name, add_shortcut_to_tip,
                    plugin_name) in enumerate(self._shortcut_data):
            try:
                shortcut_sequence = self.get_shortcut(context, name,
                                                      plugin_name)
            except (configparser.NoSectionError, configparser.NoOptionError):
                # If shortcut does not exist, save it to CONF. This is an
                # action for which there is no shortcut assigned (yet) in
                # the configuration
                self.set_shortcut(context, name, '', plugin_name)
                shortcut_sequence = ''

            if shortcut_sequence:
                keyseq = QKeySequence(shortcut_sequence)
            else:
                # Needed to remove old sequences that were cleared.
                # See spyder-ide/spyder#12992
                keyseq = QKeySequence()

            # Do not register shortcuts for the toggle view action.
            # The shortcut will be displayed only on the menus and handled by
            # about to show/hide signals.
            if (name.startswith('switch to')
                    and isinstance(qobject, SpyderAction)):
                keyseq = QKeySequence()

            try:
                if isinstance(qobject, QAction):
                    if (sys.platform == 'darwin'
                            and qobject._shown_shortcut == 'missing'):
                        qobject._shown_shortcut = keyseq
                    else:
                        qobject.setShortcut(keyseq)

                    if add_shortcut_to_tip:
                        add_shortcut_to_tooltip(qobject, context, name)
                elif isinstance(qobject, QShortcut):
                    qobject.setKey(keyseq)
            except RuntimeError:
                # Object has been deleted
                toberemoved.append(index)

        for index in sorted(toberemoved, reverse=True):
            self._shortcut_data.pop(index)

        self.sig_shortcuts_updated.emit()

    def get_shortcut(self, context, name, plugin_name=None):
        """
        Get keyboard shortcut (key sequence string).

        Parameters
        ----------
        context:
            Context must be either '_' for global or the name of a plugin.
        name: str
            Name of the shortcut.
        plugin_id: spyder.api.plugins.SpyderpluginV2 or None
            The plugin for which the shortcut is registered. Default is None.

        Returns
        -------
        Shortcut
            A shortcut object.
        """
        return self._conf.get_shortcut(context, name, plugin_name=plugin_name)

    def set_shortcut(self, context, name, keystr, plugin_id=None):
        """
        Set keyboard shortcut (key sequence string).

        Parameters
        ----------
        context:
            Context must be either '_' for global or the name of a plugin.
        name: str
            Name of the shortcut.
        keystr: str
            Shortcut keys in string form.
        plugin_id: spyder.api.plugins.SpyderpluginV2 or None
            The plugin for which the shortcut is registered. Default is None.
        """
        self._conf.set_shortcut(context, name, keystr, plugin_name=plugin_id)
