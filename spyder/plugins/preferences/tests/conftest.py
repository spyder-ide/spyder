# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# ----------------------------------------------------------------------------

"""
Testing utilities to be used with pytest.
"""

# Standard library imports
import sys
import types
from unittest.mock import Mock, MagicMock

# Third party imports
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QWidget, QMainWindow
import pytest

# Local imports
from spyder.api.plugins import Plugins
from spyder.api.plugin_registration.registry import PLUGIN_REGISTRY
from spyder.app.cli_options import get_options
from spyder.config.manager import CONF
from spyder.plugins.preferences.plugin import Preferences
from spyder.utils.icon_manager import ima


class MainWindowMock(QMainWindow):
    register_shortcut = Mock()

    def __init__(self, parent):
        super().__init__(parent)
        self.default_style = None
        self.widgetlist = []
        self.thirdparty_plugins = []
        self.shortcut_data = []
        self.prefs_dialog_instance = None
        self._APPLICATION_TOOLBARS = MagicMock()

        self.console = Mock()

        # To provide command line options for plugins that need them
        sys_argv = [sys.argv[0]]  # Avoid options passed to pytest
        self._cli_options = get_options(sys_argv)[0]

        PLUGIN_REGISTRY.reset()
        PLUGIN_REGISTRY.sig_plugin_ready.connect(self.register_plugin)
        PLUGIN_REGISTRY.register_plugin(self, Preferences)

        # Load shortcuts for tests
        for context, name, __ in CONF.iter_shortcuts():
            self.shortcut_data.append((None, context, name, None, None))

        for attr in ['mem_status', 'cpu_status']:
            mock_attr = Mock()
            setattr(mock_attr, 'toolTip', lambda: '')
            setattr(mock_attr, 'setToolTip', lambda x: '')
            setattr(mock_attr, 'prefs_dialog_instance', lambda: '')
            setattr(self, attr, mock_attr)

    def register_plugin(self, plugin_name, external=False):
        plugin = PLUGIN_REGISTRY.get_plugin(plugin_name)
        plugin._register(omit_conf=True)

    def get_plugin(self, plugin_name, error=True):
        if plugin_name in PLUGIN_REGISTRY:
            return PLUGIN_REGISTRY.get_plugin(plugin_name)

    def set_prefs_size(self, size):
        pass


class ConfigDialogTester(QWidget):
    def __init__(self, parent, main_class,
                 general_config_plugins, plugins):
        super().__init__(parent)
        self._main = main_class(self) if main_class else None
        if self._main is None:
            self._main = MainWindowMock(self)

        def set_prefs_size(self, size):
            pass

        def register_plugin(self, plugin_name, external=False):
            plugin = PLUGIN_REGISTRY.get_plugin(plugin_name)
            plugin._register()

        def get_plugin(self, plugin_name, error=True):
            if plugin_name in PLUGIN_REGISTRY:
                return PLUGIN_REGISTRY.get_plugin(plugin_name)
            return None

        setattr(self._main, 'register_plugin',
                types.MethodType(register_plugin, self._main))
        setattr(self._main, 'get_plugin',
                types.MethodType(get_plugin, self._main))
        setattr(self._main, 'set_prefs_size',
                types.MethodType(set_prefs_size, self._main))

        PLUGIN_REGISTRY.reset()
        PLUGIN_REGISTRY.sig_plugin_ready.connect(self._main.register_plugin)
        PLUGIN_REGISTRY.register_plugin(self._main, Preferences)

        if plugins:
            for Plugin in plugins:
                if hasattr(Plugin, 'CONF_WIDGET_CLASS'):
                    for required in (Plugin.REQUIRES or []):
                        if required not in PLUGIN_REGISTRY:
                            PLUGIN_REGISTRY.plugin_registry[required] = MagicMock()

                    PLUGIN_REGISTRY.register_plugin(self._main, Plugin)
                else:
                    plugin = Plugin(self._main)
                    preferences = self._main.get_plugin(Plugins.Preferences)
                    preferences.register_plugin_preferences(plugin)


@pytest.fixture
def global_config_dialog(qtbot):
    """
    Fixture that includes the general preferences options.

    These options are the ones not tied to a specific plugin.
    """
    mainwindow = MainWindowMock(None)
    qtbot.addWidget(mainwindow)

    preferences = Preferences(mainwindow, CONF)
    preferences.open_dialog(None)
    container = preferences.get_container()
    dlg = container.dialog

    yield dlg

    dlg.close()


@pytest.fixture
def config_dialog(qtbot, request, mocker):
    mocker.patch.object(ima, 'icon', lambda x, *_: QIcon())
    main_class, general_config_plugins, plugins = request.param

    main_ref = ConfigDialogTester(
        None, main_class, general_config_plugins, plugins)
    qtbot.addWidget(main_ref)

    preferences = main_ref._main.get_plugin(Plugins.Preferences)
    preferences.open_dialog(None)
    container = preferences.get_container()
    dlg = container.dialog

    yield dlg

    dlg.close()
