# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Frames Explorer Plugin."""
# Local imports
from spyder.config.base import _
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.plugins.framesexplorer.confpage import FramesExplorerConfigPage
from spyder.plugins.framesexplorer.widgets.main_widget import (
    FramesExplorerWidget)
from spyder.api.shellconnect.mixins import ShellConnectMixin


class FramesExplorer(SpyderDockablePlugin, ShellConnectMixin):
    """Frames Explorer plugin."""

    NAME = 'frames_explorer'
    REQUIRES = [Plugins.IPythonConsole, Plugins.Preferences,
                Plugins.Editor]
    TABIFY = None
    WIDGET_CLASS = FramesExplorerWidget
    CONF_SECTION = NAME
    CONF_FILE = False
    CONF_WIDGET_CLASS = FramesExplorerConfigPage
    DISABLE_ACTIONS_WHEN_HIDDEN = False

    # ---- SpyderDockablePlugin API
    # ------------------------------------------------------------------------
    def get_name(self):
        return _('Frames explorer')

    def get_description(self):
        return _('Display, explore frames in the current kernel.')

    def get_icon(self):
        return self.create_icon('dictedit')

    def on_initialize(self):
        pass

    @on_plugin_available(plugin=Plugins.Preferences)
    def on_preferences_available(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.register_plugin_preferences(self)

    @on_plugin_available(plugin=Plugins.Editor)
    def on_editor_available(self):
        editor = self.get_plugin(Plugins.Editor)
        self.get_widget().edit_goto.connect(editor.load)

    @on_plugin_teardown(plugin=Plugins.Editor)
    def on_editor_teardown(self):
        editor = self.get_plugin(Plugins.Editor)
        self.get_widget().edit_goto.disconnect(editor.load)

    @on_plugin_teardown(plugin=Plugins.Preferences)
    def on_preferences_teardown(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.deregister_plugin_preferences(self)

    # ---- Public API
    # ------------------------------------------------------------------------
    def current_widget(self):
        """
        Return the current widget displayed at the moment.

        Returns
        -------
        spyder.plugins.spyder.plugins.framesexplorer.widgets.framesbrowser.
            FramesBrowser
        """
        return self.get_widget().current_widget()
