# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Debugger Plugin."""

from qtpy.QtCore import Signal, Slot

# Local imports
from spyder.config.base import _
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.plugins.debugger.confpage import DebuggerConfigPage
from spyder.plugins.debugger.widgets.main_widget import (
    DebuggerWidget)
from spyder.api.shellconnect.mixins import ShellConnectMixin
from spyder.utils.qthelpers import MENU_SEPARATOR
from spyder.config.manager import CONF
from spyder.plugins.mainmenu.api import ApplicationMenus


class DebuggerActions:
    DebugCurrentFile = 'debug file'
    DebugCurrentCell = 'debug cell'


class Debugger(SpyderDockablePlugin, ShellConnectMixin):
    """Debugger plugin."""

    NAME = 'debugger'
    REQUIRES = [Plugins.IPythonConsole, Plugins.Preferences]
    OPTIONAL = [Plugins.Editor, Plugins.VariableExplorer, Plugins.MainMenu]
    TABIFY = [Plugins.VariableExplorer, Plugins.Help]
    WIDGET_CLASS = DebuggerWidget
    CONF_SECTION = NAME
    CONF_FILE = False
    CONF_WIDGET_CLASS = DebuggerConfigPage
    DISABLE_ACTIONS_WHEN_HIDDEN = False

    sig_debug_file = Signal()
    """This signal is emitted to request the current file to be debugged."""

    sig_debug_cell = Signal()
    """This signal is emitted to request the current cell to be debugged."""

    # ---- SpyderDockablePlugin API
    # ------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _('Debugger')

    def get_description(self):
        return _('Display and explore frames while debugging.')

    def get_icon(self):
        return self.create_icon('dictedit')

    def on_initialize(self):
        self.create_action(
            DebuggerActions.DebugCurrentFile,
            text=_("&Debug file"),
            tip=_("Debug file"),
            icon=self.create_icon('debug'),
            triggered=self.sig_debug_file,
            register_shortcut=True,
        )

        self.create_action(
            DebuggerActions.DebugCurrentCell,
            text=_("Debug cell"),
            tip=_("Debug cell"),
            icon=self.create_icon('debug_cell'),
            triggered=self.sig_debug_cell,
            register_shortcut=True,
        )

    @Slot()
    def debug_file(self):
        """
        Debug current script.
        Should only be called when an editor is avilable.
        """
        editor = self.get_plugin(Plugins.Editor)
        editor.switch_to_plugin()
        editor.run_file(method="debugfile")

    @Slot()
    def debug_cell(self):
        '''
        Debug Current cell.
        Should only be called when an editor is avilable.
        '''
        editor = self.get_plugin(Plugins.Editor)
        editor.run_cell(method="debugcell")

    @on_plugin_available(plugin=Plugins.Preferences)
    def on_preferences_available(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.register_plugin_preferences(self)

    @on_plugin_teardown(plugin=Plugins.Preferences)
    def on_preferences_teardown(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.deregister_plugin_preferences(self)

    @on_plugin_available(plugin=Plugins.Editor)
    def on_editor_available(self):
        editor = self.get_plugin(Plugins.Editor)
        self.get_widget().edit_goto.connect(editor.load)

        # The editor is avilable, connect signal.
        self.sig_debug_file.connect(self.debug_file)
        self.sig_debug_cell.connect(self.debug_cell)
        CONF.config_shortcut(
            self.debug_file,
            context=self.CONF_SECTION,
            name=DebuggerActions.DebugCurrentFile,
            parent=editor)
        CONF.config_shortcut(
            self.debug_cell,
            context=self.CONF_SECTION,
            name=DebuggerActions.DebugCurrentCell,
            parent=editor)
        debug_file_action = self.get_action(
            DebuggerActions.DebugCurrentFile)
        debug_cell_action = self.get_action(
            DebuggerActions.DebugCurrentCell)
        self.main.debug_toolbar_actions += [
            debug_file_action, debug_cell_action]

    @on_plugin_teardown(plugin=Plugins.Editor)
    def on_editor_teardown(self):
        editor = self.get_plugin(Plugins.Editor)
        self.get_widget().edit_goto.disconnect(editor.load)
        self.sig_debug_file.disconnect(self.debug_file)
        self.sig_debug_cell.disconnect(self.debug_cell)

    @on_plugin_available(plugin=Plugins.VariableExplorer)
    def on_variable_explorer_available(self):
        self.get_widget().sig_show_namespace.connect(
            self.show_namespace_in_variable_explorer)

    @on_plugin_teardown(plugin=Plugins.VariableExplorer)
    def on_variable_explorer_teardown(self):
        self.get_widget().sig_show_namespace.disconnect(
            self.show_namespace_in_variable_explorer)

    @on_plugin_available(plugin=Plugins.MainMenu)
    def on_main_menu_available(self):
        debug_file_action = self.get_action(
            DebuggerActions.DebugCurrentFile)
        debug_cell_action = self.get_action(
            DebuggerActions.DebugCurrentCell)

        self.main.debug_menu_actions = [
                debug_file_action,
                debug_cell_action,
                MENU_SEPARATOR,
            ] + self.main.debug_menu_actions

    @on_plugin_teardown(plugin=Plugins.MainMenu)
    def on_main_menu_teardown(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)

        mainmenu.remove_item_from_application_menu(
            DebuggerActions.DebugCurrentFile,
            menu_id=ApplicationMenus.Debug
        )
        mainmenu.remove_item_from_application_menu(
            DebuggerActions.DebugCurrentCell,
            menu_id=ApplicationMenus.Debug
        )

    # ---- Public API
    # ------------------------------------------------------------------------
    def show_namespace_in_variable_explorer(self, namespace, shellwidget):
        """
        Find the right variable explorer widget and show the namespace.

        This should only be called when there is a Variable explorer
        """
        variable_explorer = self.get_plugin(Plugins.VariableExplorer)
        if variable_explorer is None:
            return
        nsb = variable_explorer.get_widget_for_shellwidget(shellwidget)
        nsb.process_remote_view(namespace)
