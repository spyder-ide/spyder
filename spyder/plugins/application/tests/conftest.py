# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""Fixtures for the Application plugin tests."""

# Standard library imports
from unittest.mock import Mock, patch

# Third party imports
import pytest

# Local imports
from spyder.config.base import running_in_ci
from spyder.config.manager import CONF
from spyder.plugins.application.plugin import Application
from spyder.utils.stylesheet import APP_STYLESHEET


@pytest.fixture
def application_plugin(qapp, qtbot):
    main_window = Mock()
    CONF.set('main', 'recent_files', [])
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
