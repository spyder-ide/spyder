# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# ----------------------------------------------------------------------------

"""
Testing utilities to be used with pytest.
"""

import traceback

try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock  # Python 2

# Third party imports
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QMainWindow
import pytest

# Local imports
from spyder.config.manager import CONF
from spyder.plugins.shortcuts.widgets.table import load_shortcuts_data
from spyder.preferences.configdialog import ConfigDialog
from spyder.preferences.general import MainConfigPage
from spyder.utils import icon_manager as ima


class MainWindowMock(QMainWindow):
    register_shortcut = Mock()

    def __init__(self):
        super().__init__(None)
        self.default_style = None
        self.widgetlist = []
        self.thirdparty_plugins = []
        self.shortcut_data = []
        self.prefs_dialog_instance = None
        self.console = Mock()

        # Load shortcuts for tests
        for context, name, __ in CONF.iter_shortcuts():
            self.shortcut_data.append((None, context, name, None, None))

        for attr in ['mem_status', 'cpu_status']:
            mock_attr = Mock()
            setattr(mock_attr, 'toolTip', lambda: '')
            setattr(mock_attr, 'setToolTip', lambda x: '')
            setattr(mock_attr, 'is_supported', lambda: True)
            setattr(mock_attr, 'prefs_dialog_instance', lambda: '')
            setattr(self, attr, mock_attr)

    def create_plugin_conf_widget(self, plugin):
        """
        Create configuration dialog box page widget.
        """
        config_dialog = self.prefs_dialog_instance
        if plugin.CONF_WIDGET_CLASS is not None and config_dialog is not None:
            conf_widget = plugin.CONF_WIDGET_CLASS(plugin, config_dialog)
            conf_widget.initialize()
            return conf_widget


class ConfigDialogTester(ConfigDialog):

    def __init__(self, params):
        main_class, general_config_plugins, plugins = params
        self._main = main_class() if main_class else None
        if self._main is None:
            self._main = MainWindowMock()

        super(ConfigDialogTester, self).__init__(parent=None)
        self._main.prefs_dialog_instance = self

        if general_config_plugins:
            for widget_class in general_config_plugins:
                widget = widget_class(self, main=self._main)
                widget.initialize()
                self.add_page(widget)

        if plugins:
            for plugin in plugins:
                try:
                    # New API
                    plugin = plugin(parent=self._main, configuration=CONF)
                    if plugin.NAME == "shortcuts":
                        plugin.get_shortcut_data = (
                            lambda: load_shortcuts_data())

                    widget = self._main.create_plugin_conf_widget(plugin)
                except Exception as e:
                    traceback.print_exc()
                    # Old API
                    plugin = plugin(parent=self._main)
                    widget = plugin._create_configwidget(self, self._main)

                if widget:
                    self.add_page(widget)

        self.show()


@pytest.fixture
def global_config_dialog(qtbot):
    """
    Fixture that includes the general preferences options.

    These options are the ones not tied to a specific plugin.
    """
    dlg = ConfigDialog()
    dlg.show()

    qtbot.addWidget(dlg)
    for widget_class in [MainConfigPage]:
        widget = widget_class(dlg, main=MainWindowMock())
        widget.initialize()
        dlg.add_page(widget)

    return dlg


@pytest.fixture
def config_dialog(qtbot, request, mocker):
    mocker.patch.object(ima, 'icon', lambda x, icon_path=None: QIcon())
    dlg = ConfigDialogTester(request.param)
    qtbot.addWidget(dlg)
    dlg.show()
    return dlg
