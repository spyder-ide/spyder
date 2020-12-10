# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# ----------------------------------------------------------------------------

"""
Tests for configdialog.py
"""

# Standard library imports
import time

# Local imports
from spyder.preferences.configdialog import ConfigDialog
from spyder.preferences.tests.conftest import MainWindowMock
from spyder.utils.conda import get_list_conda_envs
from spyder.utils.pyenv import get_list_pyenv_envs


# Get envs to show them in the Main interpreter page. This is actually
# done in a thread in the InterpreterStatus widget.
# We also recording the time needed to get them to compare it with the
# loading time of that config page.
t0 = time.time()
get_list_conda_envs()
get_list_pyenv_envs()
GET_ENVS_TIME = time.time() - t0


def test_config_dialog_save_to_conf(global_config_dialog):
    for index in range(global_config_dialog.pages_widget.count()):
        configpage = global_config_dialog.get_page(index)
        configpage.save_to_conf()
        _save_lang = getattr(configpage, '_save_lang', None)

        if _save_lang:
            _save_lang()

        assert configpage.is_valid()


def test_maininterpreter_page(qtbot):
    from spyder.preferences.maininterpreter import MainInterpreterConfigPage

    # Create Preferences dialog
    dlg = ConfigDialog()
    dlg.show()
    qtbot.addWidget(dlg)

    # Create page and measure time to do it
    t0 = time.time()
    widget = MainInterpreterConfigPage(dlg, main=MainWindowMock())
    widget.initialize()
    load_time = time.time() - t0

    # Add page to Preferences
    dlg.add_page(widget)

    # Assert the combobox is populated with the found envs
    assert widget.cus_exec_combo.combobox.count() > 0

    # Assert load time is smaller than the one required to get envs
    # directly. This means we're using the cached envs instead
    assert load_time < GET_ENVS_TIME

    # Load time should be small too because we perform simple validations
    # on the page.
    assert load_time < 0.5
