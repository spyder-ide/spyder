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
from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QKeySequence
from qtpy.QtWidgets import QAction, QShortcut

# Local imports
from spyder.api.plugins import Plugins, SpyderPluginV2
from spyder.api.translations import get_translation
from spyder.plugins.mainmenu.api import ApplicationMenus, HelpMenuSections
from spyder.plugins.shortcuts.confpage import ShortcutsConfigPage
from spyder.plugins.shortcuts.widgets.summary import ShortcutsSummaryDialog
from spyder.utils.qthelpers import add_shortcut_to_tooltip, SpyderAction

# Localization
_ = get_translation('spyder')


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

    # --- Signals
    # ------------------------------------------------------------------------
    sig_shortcuts_updated = Signal()
    """
    This signal is emitted to inform shortcuts have been updated.
    """

    # --- SpyderPluginV2 API
    # ------------------------------------------------------------------------
    def get_name(self):
        return _("Keyboard shortcuts")

    def get_description(self):
        return _("Manage application, widget and actions shortcuts.")

    def get_icon(self):
        return self.create_icon('keyboard')

    def register(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.register_plugin_preferences(self)

        self._shortcut_data = []
        shortcuts_action = self.create_action(
            ShortcutActions.ShortcutSummaryAction,
            text=_("Shortcuts Summary"),
            triggered=lambda: self.show_summary(),
            register_shortcut=True,
            context=Qt.ApplicationShortcut,
        )

        # Add to Help menu.
        if mainmenu:
            help_menu = mainmenu.get_application_menu(ApplicationMenus.Help)
            mainmenu.add_item_to_application_menu(
                shortcuts_action,
                help_menu,
                section=HelpMenuSections.Documentation,
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
