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
from qtpy.QtCore import QEvent
from qtpy.QtGui import QFocusEvent
from qtpy.QtWidgets import QMessageBox

# Local imports
from spyder.api.plugins import Plugins
from spyder.api.plugin_registration.registry import PLUGIN_REGISTRY
from spyder.config.manager import CONF
from spyder.plugins.maininterpreter.plugin import MainInterpreter
from spyder.plugins.preferences.tests.conftest import MainWindowMock
from spyder.utils.conda import get_list_conda_envs
from spyder.utils.pyenv import get_list_pyenv_envs


# Get envs to show them in the Main interpreter page. This is actually
# done in a thread in the MainInterpreter container.
# We're also recording the time needed to get them to compare it with the
# loading time of that config page.
t0 = time.time()
conda_envs = get_list_conda_envs()
pyenv_envs = get_list_pyenv_envs()
GET_ENVS_TIME = time.time() - t0


@pytest.mark.skipif(
    (
        (len(conda_envs) == 0 and len(pyenv_envs) == 0)
        or sys.platform == "darwin"
    ),
    reason="Makes no sense if conda and pyenv are not installed, fails on Mac",
)
def test_load_time(qtbot):
    # Create Preferences dialog
    main = MainWindowMock(None)
    preferences = main.get_plugin(Plugins.Preferences)

    PLUGIN_REGISTRY._update_plugin_info(MainInterpreter)
    PLUGIN_REGISTRY.register_plugin(main, MainInterpreter)

    # Create page and measure time to do it
    t0 = time.time()
    preferences.open_dialog()
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


@pytest.fixture
def interpreter_page(qtbot):
    """
    Main interpreter config page from a Preferences dialog.

    The options of the page are restored to their previous values after the
    test.
    """
    section = "main_interpreter"
    options = [
        "default",
        "custom",
        "custom_interpreter",
        "custom_interpreters_list",
        "executable",
    ]
    previous = {
        opt: CONF.get(section, opt)
        for opt in options
        if CONF.has_option(section, opt)
    }

    # Start without an executable so we can check it's set on apply
    CONF.set(section, "executable", "")

    # Create Preferences dialog
    main = MainWindowMock(None)
    preferences = main.get_plugin(Plugins.Preferences)

    PLUGIN_REGISTRY._update_plugin_info(MainInterpreter)
    PLUGIN_REGISTRY.register_plugin(main, MainInterpreter)

    preferences.open_dialog()
    container = preferences.get_container()
    dlg = container.dialog

    yield dlg.get_page()

    dlg.close()
    for opt in options:
        if opt in previous:
            CONF.set(section, opt, previous[opt])
        elif CONF.has_option(section, opt):
            CONF.remove_option(section, opt)


@pytest.mark.parametrize(
    "prefix, suffix",
    [("", "\n"), ("", "\r\n"), ("", " "), ("", "\t"), (" ", ""), ("\t", "\n")],
)
def test_custom_interpreter_surrounding_whitespace(
    interpreter_page, qtbot, mocker, prefix, suffix
):
    """
    Check that whitespace around a custom interpreter path entered in the
    page is accepted and removed before saving it.

    This is a regression test for spyder-ide/spyder#24955
    """
    mock_critical = mocker.patch.object(QMessageBox, "critical")
    page = interpreter_page

    # Select a custom interpreter path with whitespace around it
    page.cus_exec_radio.radiobutton.setChecked(True)
    page.pyexec_edit.setText(prefix + sys.executable + suffix)

    # Losing focus doesn't reset the path to its previous value
    combobox = page.cus_exec_combo.combobox
    combobox.focusOutEvent(QFocusEvent(QEvent.Type.FocusOut))
    qtbot.wait(200)
    assert page.pyexec_edit.text() == prefix + sys.executable + suffix

    # The path is considered valid and no error is shown
    assert page.is_valid()
    mock_critical.assert_not_called()

    # The path is saved without the whitespace and used as the interpreter
    page.apply_changes()
    section = "main_interpreter"
    assert CONF.get(section, "custom_interpreter") == sys.executable
    assert CONF.get(section, "executable") == sys.executable
    assert page.pyexec_edit.text() == sys.executable


def test_custom_interpreter_internal_selected(interpreter_page):
    """
    Check what's saved for the custom interpreter text when the internal
    interpreter is selected.
    """
    page = interpreter_page
    page.def_exec_radio.radiobutton.setChecked(True)

    # The placeholder value used for this option is left untouched
    page.pyexec_edit.setText(" ")
    page.strip_custom_interpreter()
    assert page.pyexec_edit.text() == " "

    # A path with surrounding whitespace is saved without it
    page.pyexec_edit.setText(sys.executable + "\n")
    page.apply_changes()
    assert CONF.get("main_interpreter", "custom_interpreter") == sys.executable
