# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see LICENSE.txt for details)
# -----------------------------------------------------------------------------

# Standard library imports
import sys
import time

# Third-party imports
import pytest

# Local imports
from spyder.api.plugins import Plugins
from spyder.api.plugin_registration.registry import PLUGIN_REGISTRY
from spyder.plugins.maininterpreter.plugin import MainInterpreter
from spyder.plugins.preferences.tests.conftest import MainWindowMock
from spyder.utils.conda import get_list_conda_envs
from spyder.utils.pyenv import get_list_pyenv_envs


# Get envs to show them in the Main interpreter page. This is actually
# done in a thread in the InterpreterStatus widget.
# We're also recording the time needed to get them to compare it with the
# loading time of that config page.
t0 = time.time()
conda_envs = get_list_conda_envs()
pyenv_envs = get_list_pyenv_envs()
GET_ENVS_TIME = time.time() - t0


@pytest.mark.skipif(
    ((len(conda_envs) == 0 and len(pyenv_envs) == 0) or
     sys.platform == 'darwin'),
    reason="Makes no sense if conda and pyenv are not installed, fails on mac"
)
def test_load_time(qtbot):
    # Create Preferences dialog
    main = MainWindowMock(None)
    preferences = main.get_plugin(Plugins.Preferences)

    PLUGIN_REGISTRY.register_plugin(main, MainInterpreter)

    # Create page and measure time to do it
    t0 = time.time()
    preferences.open_dialog(None)
    load_time = time.time() - t0

    container = preferences.get_container()
    dlg = container.dialog
    widget = dlg.get_page()

    # Assert the combobox is populated with the found envs
    assert widget.cus_exec_combo.combobox.count() > 0

    # Assert load time is smaller than the one required to get envs
    # directly. This means we're using the cached envs instead
    assert load_time < GET_ENVS_TIME

    # Load time should be small too because we perform simple validations
    # on the page.
    assert load_time < 0.5
