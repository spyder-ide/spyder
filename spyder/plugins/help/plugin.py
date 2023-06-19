# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Help Plugin.
"""

# Standard library imports
import os

# Third party imports
from qtpy.QtCore import Signal

# Local imports
from spyder.api.exceptions import SpyderAPIError
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.api.translations import _
from spyder.config.base import get_conf_path
from spyder.config.fonts import DEFAULT_SMALL_DELTA
from spyder.plugins.help.confpage import HelpConfigPage
from spyder.plugins.help.widgets import HelpWidget


class HelpActions:
    # Documentation related
    ShowSpyderTutorialAction = "spyder_tutorial_action"


class Help(SpyderDockablePlugin):
    """
    Docstrings viewer widget.
    """
    NAME = 'help'
    REQUIRES = [Plugins.Preferences, Plugins.Console, Plugins.Editor]
    OPTIONAL = [Plugins.IPythonConsole, Plugins.Shortcuts, Plugins.MainMenu]
    TABIFY = Plugins.VariableExplorer
    WIDGET_CLASS = HelpWidget
    CONF_SECTION = NAME
    CONF_WIDGET_CLASS = HelpConfigPage
    CONF_FILE = False
    LOG_PATH = get_conf_path(CONF_SECTION)
    FONT_SIZE_DELTA = DEFAULT_SMALL_DELTA
    DISABLE_ACTIONS_WHEN_HIDDEN = False

    # Signals
    sig_focus_changed = Signal()  # TODO: What triggers this?

    sig_render_started = Signal()
    """This signal is emitted to inform a help text rendering has started."""

    sig_render_finished = Signal()
    """This signal is emitted to inform a help text rendering has finished."""

    # --- SpyderDocakblePlugin API
    #  -----------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _('Help')

    def get_description(self):
        return _(
            'Get rich text documentation from the editor and the console')

    def get_icon(self):
        return self.create_icon('help')

    def on_initialize(self):
        widget = self.get_widget()

        # Expose widget signals on the plugin
        widget.sig_render_started.connect(self.sig_render_started)
        widget.sig_render_finished.connect(self.sig_render_finished)

        # self.sig_focus_changed.connect(self.main.plugin_focus_changed)
        widget.set_history(self.load_history())
        widget.sig_item_found.connect(self.save_history)

        self.tutorial_action = self.create_action(
            HelpActions.ShowSpyderTutorialAction,
            text=_("Spyder tutorial"),
            triggered=self.show_tutorial,
            register_shortcut=False,
        )

    @on_plugin_available(plugin=Plugins.Console)
    def on_console_available(self):
        widget = self.get_widget()
        internal_console = self.get_plugin(Plugins.Console)
        internal_console.sig_help_requested.connect(self.set_object_text)
        widget.set_internal_console(internal_console)

    @on_plugin_available(plugin=Plugins.Editor)
    def on_editor_available(self):
        editor = self.get_plugin(Plugins.Editor)
        editor.sig_help_requested.connect(self.set_editor_doc)

    @on_plugin_available(plugin=Plugins.IPythonConsole)
    def on_ipython_console_available(self):
        ipyconsole = self.get_plugin(Plugins.IPythonConsole)

        ipyconsole.sig_shellwidget_changed.connect(self.set_shellwidget)
        ipyconsole.sig_shellwidget_created.connect(self.set_shellwidget)
        ipyconsole.sig_render_plain_text_requested.connect(
            self.show_plain_text)
        ipyconsole.sig_render_rich_text_requested.connect(
            self.show_rich_text)

        ipyconsole.sig_help_requested.connect(self.set_object_text)

    @on_plugin_available(plugin=Plugins.Preferences)
    def on_preferences_available(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.register_plugin_preferences(self)

    @on_plugin_available(plugin=Plugins.Shortcuts)
    def on_shortcuts_available(self):
        shortcuts = self.get_plugin(Plugins.Shortcuts)

        # See: spyder-ide/spyder#6992
        shortcuts.sig_shortcuts_updated.connect(self.show_intro_message)

        if self.is_plugin_available(Plugins.MainMenu):
            self._setup_menus()

    @on_plugin_available(plugin=Plugins.MainMenu)
    def on_main_menu_available(self):
        if self.is_plugin_enabled(Plugins.Shortcuts):
            if self.is_plugin_available(Plugins.Shortcuts):
                self._setup_menus()
        else:
            self._setup_menus()

    @on_plugin_teardown(plugin=Plugins.Console)
    def on_console_teardown(self):
        widget = self.get_widget()
        internal_console = self.get_plugin(Plugins.Console)
        internal_console.sig_help_requested.disconnect(self.set_object_text)
        widget.set_internal_console(None)

    @on_plugin_teardown(plugin=Plugins.Editor)
    def on_editor_teardown(self):
        editor = self.get_plugin(Plugins.Editor)
        editor.sig_help_requested.disconnect(self.set_editor_doc)

    @on_plugin_teardown(plugin=Plugins.IPythonConsole)
    def on_ipython_console_teardown(self):
        ipyconsole = self.get_plugin(Plugins.IPythonConsole)

        ipyconsole.sig_shellwidget_changed.disconnect(self.set_shellwidget)
        ipyconsole.sig_shellwidget_created.disconnect(
            self.set_shellwidget)
        ipyconsole.sig_render_plain_text_requested.disconnect(
            self.show_plain_text)
        ipyconsole.sig_render_rich_text_requested.disconnect(
            self.show_rich_text)

        ipyconsole.sig_help_requested.disconnect(self.set_object_text)

    @on_plugin_teardown(plugin=Plugins.Preferences)
    def on_preferences_teardown(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.deregister_plugin_preferences(self)

    @on_plugin_teardown(plugin=Plugins.Shortcuts)
    def on_shortcuts_teardown(self):
        shortcuts = self.get_plugin(Plugins.Shortcuts)
        shortcuts.sig_shortcuts_updated.disconnect(self.show_intro_message)

    @on_plugin_teardown(plugin=Plugins.MainMenu)
    def on_main_menu_teardown(self):
        self._remove_menus()

    def update_font(self):
        color_scheme = self.get_color_scheme()
        font = self.get_font()
        rich_font = self.get_font(rich_text=True)

        widget = self.get_widget()
        widget.set_plain_text_font(font, color_scheme=color_scheme)
        widget.set_rich_text_font(rich_font, font)
        widget.set_plain_text_color_scheme(color_scheme)

    def on_close(self, cancelable=False):
        self.save_history()
        return True

    def apply_conf(self, options_set, notify=False):
        super().apply_conf(options_set)

        # To make auto-connection changes take place instantly
        try:
            editor = self.get_plugin(Plugins.Editor)
            editor.apply_plugin_settings({'connect_to_oi'})
        except SpyderAPIError:
            pass

    # --- Private API
    # ------------------------------------------------------------------------
    def _setup_menus(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)
        shortcuts = self.get_plugin(Plugins.Shortcuts)
        shortcuts_summary_action = None
        if shortcuts:
            from spyder.plugins.shortcuts.plugin import ShortcutActions
            shortcuts_summary_action = ShortcutActions.ShortcutSummaryAction
        if mainmenu:
            from spyder.plugins.mainmenu.api import (
                ApplicationMenus, HelpMenuSections)
            # Documentation actions
            mainmenu.add_item_to_application_menu(
                self.tutorial_action,
                menu_id=ApplicationMenus.Help,
                section=HelpMenuSections.Documentation,
                before=shortcuts_summary_action,
                before_section=HelpMenuSections.Support)

    def _remove_menus(self):
        from spyder.plugins.mainmenu.api import ApplicationMenus
        mainmenu = self.get_plugin(Plugins.MainMenu)
        mainmenu.remove_item_from_application_menu(
            HelpActions.ShowSpyderTutorialAction,
            menu_id=ApplicationMenus.Help)

    # --- Public API
    # ------------------------------------------------------------------------
    def set_shellwidget(self, shellwidget):
        """
        Set IPython Console `shelwidget` as the current shellwidget.

        Parameters
        ----------
        shellwidget: spyder.plugins.ipyconsole.widgets.shell.ShellWidget
            The shell widget that is going to be connected to Help.
        """
        shellwidget._control.set_help_enabled(
            self.get_conf('connect/ipython_console'))
        self.get_widget().set_shell(shellwidget)

    def load_history(self, obj=None):
        """
        Load history from a text file in the user configuration directory.
        """
        if os.path.isfile(self.LOG_PATH):
            with open(self.LOG_PATH, 'r') as fh:
                lines = fh.read().split('\n')

            history = [line.replace('\n', '') for line in lines]
        else:
            history = []

        return history

    def save_history(self):
        """
        Save history to a text file in the user configuration directory.
        """
        # Don't fail when saving search history to disk
        # See spyder-ide/spyder#8878 and spyder-ide/spyder#6864
        try:
            search_history = '\n'.join(self.get_widget().get_history())
            with open(self.LOG_PATH, 'w') as fh:
                fh.write(search_history)
        except (UnicodeEncodeError, UnicodeDecodeError, EnvironmentError):
            pass

    def show_tutorial(self):
        """Show the Spyder tutorial."""
        self.switch_to_plugin()
        self.get_widget().show_tutorial()

    def show_intro_message(self):
        """Show the IPython introduction message."""
        self.get_widget().show_intro_message()

    def show_rich_text(self, text, collapse=False, img_path=''):
        """
        Show help in rich mode.

        Parameters
        ----------
        text: str
            Plain text to display.
        collapse: bool, optional
            Show collapsable sections as collapsed/expanded. Default is False.
        img_path: str, optional
            Path to folder with additional images needed to correctly
            display the rich text help. Default is ''.
        """
        self.switch_to_plugin()
        self.get_widget().show_rich_text(text, collapse=collapse,
                                         img_path=img_path)

    def show_plain_text(self, text):
        """
        Show help in plain mode.

        Parameters
        ----------
        text: str
            Plain text to display.
        """
        self.switch_to_plugin()
        self.get_widget().show_plain_text(text)

    def set_object_text(self, options_dict):
        """
        Set object's name in Help's combobox.

        Parameters
        ----------
        options_dict: dict
            Dictionary of data. See the example for the expected keys.

        Examples
        --------
        >>> help_data = {
            'name': str,
            'force_refresh': bool,
        }

        See Also
        --------
        :py:meth:spyder.widgets.mixins.GetHelpMixin.show_object_info
        """
        self.switch_to_plugin()
        self.get_widget().set_object_text(
            options_dict['name'],
            ignore_unknown=options_dict['ignore_unknown'],
        )

    def set_editor_doc(self, help_data):
        """
        Set content for help data sent from the editor.

        Parameters
        ----------
        help_data: dict
            Dictionary of data. See the example for the expected keys.

        Examples
        --------
        >>> help_data = {
            'obj_text': str,
            'name': str,
            'argspec': str,
            'note': str,
            'docstring': str,
            'force_refresh': bool,
            'path': str,
        }

        See Also
        --------
        :py:meth:spyder.plugins.editor.widgets.editor.EditorStack.send_to_help
        """
        force_refresh = help_data.pop('force_refresh', False)
        self.switch_to_plugin()
        self.get_widget().set_editor_doc(
            help_data,
            force_refresh=force_refresh,
        )
