# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Tests for the Application plugin.
"""

from unittest.mock import Mock, patch

import pytest

from spyder.api.plugins import Plugins
from spyder.config.base import running_in_ci
from spyder.config.manager import CONF
from spyder.plugins.application.plugin import Application
from spyder.utils.stylesheet import APP_STYLESHEET


@pytest.fixture
def application_plugin(qapp, qtbot):
    main_window = Mock()
    application = Application(None, configuration=CONF)
    application.main = application._main = main_window
    application.on_initialize()
    container = application.get_container()
    container.setMinimumSize(700, 500)
    qtbot.addWidget(container)
    if not running_in_ci():
        qapp.setStyleSheet(str(APP_STYLESHEET))
    with qtbot.waitExposed(container):
        container.show()

    with patch.object(application, 'get_plugin'):
        yield application


def test_new_file(application_plugin):
    """
    Test that triggering the "New file" action calls the new() function in
    the Editor plugin.
    """
    container = application_plugin.get_container()
    container.new_action.trigger()

    application_plugin.get_plugin.assert_called_with(Plugins.Editor)
    editor_plugin = application_plugin.get_plugin.return_value
    editor_plugin.new.assert_called()
