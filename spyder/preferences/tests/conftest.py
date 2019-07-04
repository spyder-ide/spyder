# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# ----------------------------------------------------------------------------

"""
Testing utilities to be used with pytest.
"""

try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock  # Python 2

# Third party imports
from qtpy.QtGui import QIcon
import pytest

# Local imports
from spyder.preferences.appearance import AppearanceConfigPage
from spyder.preferences.configdialog import ConfigDialog
from spyder.preferences.general import MainConfigPage
from spyder.preferences.shortcuts import ShortcutsConfigPage
from spyder.utils import icon_manager as ima


class MainWindowMock:
    def __init__(self):
        self.default_style = None
        self.widgetlist = []
        self.thirdparty_plugins = []

        for attr in ['mem_status', 'cpu_status']:
            mock_attr = Mock()
            setattr(mock_attr, 'toolTip', lambda: '')
            setattr(mock_attr, 'setToolTip', lambda x: '')
            setattr(mock_attr, 'is_supported', lambda: True)
            setattr(self, attr, mock_attr)


class ConfigDialogTester(ConfigDialog):

    def __init__(self, params):
        main_class, general_config_plugins, plugins = params
        self._main = main_class() if main_class else None
        super(ConfigDialogTester, self).__init__(parent=None)

        if general_config_plugins:
            for widget_class in general_config_plugins:
                widget = widget_class(self, main=self._main)
                widget.initialize()
                self.add_page(widget)

        if plugins:
            for plugin in plugins:
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

    from spyder.preferences.maininterpreter import MainInterpreterConfigPage
    from spyder.preferences.runconfig import RunConfigPage

    qtbot.addWidget(dlg)
    for widget_class in [AppearanceConfigPage, MainConfigPage,
                         MainInterpreterConfigPage, ShortcutsConfigPage,
                         RunConfigPage]:
        widget = widget_class(dlg, main=MainWindowMock())
        widget.initialize()
        dlg.add_page(widget)
    return dlg


@pytest.fixture
def config_dialog(qtbot, request, mocker):
    mocker.patch.object(ima, 'icon', lambda x, y=None: QIcon())
    dlg = ConfigDialogTester(request.param)
    qtbot.addWidget(dlg)
    dlg.show()
    return dlg
