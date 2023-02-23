# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Profiler Plugin.
"""

# Third party imports
from qtpy.QtCore import Signal

# Local imports
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.api.translations import _
from spyder.plugins.mainmenu.api import ApplicationMenus
from spyder.plugins.profiler.confpage import ProfilerConfigPage
from spyder.plugins.profiler.widgets.main_widget import (ProfilerWidget,
                                                         is_profiler_installed)
from spyder.plugins.run.widgets import get_run_configuration


# --- Constants
# ----------------------------------------------------------------------------
class ProfilerActions:
    ProfileCurrentFile = 'profile_current_filename_action'


# --- Plugin
# ----------------------------------------------------------------------------
class Profiler(SpyderDockablePlugin):
    """
    Profiler (after python's profile and pstats).
    """

    NAME = 'profiler'
    REQUIRES = [Plugins.Preferences, Plugins.Editor]
    OPTIONAL = [Plugins.MainMenu]
    TABIFY = [Plugins.Help]
    WIDGET_CLASS = ProfilerWidget
    CONF_SECTION = NAME
    CONF_WIDGET_CLASS = ProfilerConfigPage
    CONF_FILE = False

    # --- Signals
    # ------------------------------------------------------------------------
    sig_started = Signal()
    """This signal is emitted to inform the profiling process has started."""

    sig_finished = Signal()
    """This signal is emitted to inform the profile profiling has finished."""

    # --- SpyderDockablePlugin API
    # ------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _("Profiler")

    def get_description(self):
        return _("Profile your scripts and find bottlenecks.")

    def get_icon(self):
        return self.create_icon('profiler')

    def on_initialize(self):
        widget = self.get_widget()
        widget.sig_started.connect(self.sig_started)
        widget.sig_finished.connect(self.sig_finished)

        run_action = self.create_action(
            ProfilerActions.ProfileCurrentFile,
            text=_("Run profiler"),
            tip=_("Run profiler"),
            icon=self.create_icon('profiler'),
            triggered=self.run_profiler,
            register_shortcut=True,
        )

        run_action.setEnabled(is_profiler_installed())

    @on_plugin_available(plugin=Plugins.Editor)
    def on_editor_available(self):
        widget = self.get_widget()
        editor = self.get_plugin(Plugins.Editor)
        widget.sig_edit_goto_requested.connect(editor.load)

    @on_plugin_available(plugin=Plugins.Preferences)
    def on_preferences_available(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.register_plugin_preferences(self)

    @on_plugin_available(plugin=Plugins.MainMenu)
    def on_main_menu_available(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)
        run_action = self.get_action(ProfilerActions.ProfileCurrentFile)

        mainmenu.add_item_to_application_menu(
            run_action, menu_id=ApplicationMenus.Run)

    @on_plugin_teardown(plugin=Plugins.Editor)
    def on_editor_teardown(self):
        widget = self.get_widget()
        editor = self.get_plugin(Plugins.Editor)
        widget.sig_edit_goto_requested.disconnect(editor.load)

    @on_plugin_teardown(plugin=Plugins.Preferences)
    def on_preferences_teardown(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.deregister_plugin_preferences(self)

    @on_plugin_teardown(plugin=Plugins.MainMenu)
    def on_main_menu_teardown(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)

        mainmenu.remove_item_from_application_menu(
            ProfilerActions.ProfileCurrentFile,
            menu_id=ApplicationMenus.Run
        )

    # --- Public API
    # ------------------------------------------------------------------------
    def run_profiler(self):
        """
        Run profiler.

        Notes
        -----
        This method will check if the file on the editor can be saved first.
        """
        editor = self.get_plugin(Plugins.Editor)
        if editor.save():
            self.switch_to_plugin()
            self.analyze(editor.get_current_filename())

    def stop_profiler(self):
        """
        Stop profiler.
        """
        self.get_widget().stop()

    def analyze(self, filename):
        """
        Run profile analysis on `filename`.

        Parameters
        ----------
        filename: str
            Path to file to analyze.
        """
        wdir, args = None, []
        runconf = get_run_configuration(filename)
        if runconf is not None:
            if runconf.wdir_enabled:
                wdir = runconf.wdir

            if runconf.args_enabled:
                args = runconf.args

        self.get_widget().analyze(
            filename,
            wdir=wdir,
            args=args
        )
