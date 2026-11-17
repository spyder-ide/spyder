# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""Tests for the Application config page."""

# Third-party imports
import pytest

# Local imports
from spyder.api.plugin_registration.registry import PLUGIN_REGISTRY
from spyder.api.plugins import Plugins
from spyder.config.manager import CONF
from spyder.plugins.application.confpage import MAX_CUSTOM_SCALE_FACTOR
from spyder.plugins.application.plugin import Application
from spyder.plugins.preferences.tests.conftest import (  # noqa
    config_dialog,
    MainWindowMock
)


@pytest.fixture
def custom_scale_factor(request):
    """Save a custom scale factor in the config for the duration of a test."""
    option = 'high_dpi_custom_scale_factors'
    previous = CONF.get('main', option)
    CONF.set('main', option, request.param)
    yield request.param
    CONF.set('main', option, previous)


@pytest.fixture
def delete_container(qtbot):
    """
    Delete the container of the Application plugin created for the dialog.

    This needs to be requested before ``config_dialog`` so it's done after the
    dialog is closed. Otherwise, the tests in test_container.py segfault when
    run locally after these ones, because their fixture sets the app
    stylesheet outside CIs.
    """
    yield
    container = PLUGIN_REGISTRY.get_plugin(Plugins.Application).get_container()
    container.close()
    container.deleteLater()
    qtbot.wait(100)


def is_acceptable(page, text):
    """Return True if the custom scale factor validator accepts `text`."""
    textbox = page.custom_scaling_edit.textbox
    textbox.setText(text)
    return textbox.hasAcceptableInput()


@pytest.mark.parametrize(
    'config_dialog',
    [[MainWindowMock, [], [Application]]],
    indirect=True
)
@pytest.mark.parametrize(
    "text, acceptable",
    [
        # Whole numbers are complete values
        ("1", True),
        ("2", True),
        (str(MAX_CUSTOM_SCALE_FACTOR), True),
        # Floats up to the maximum
        ("1.5", True),
        ("2.", True),
        ("4.75", True),
        (f"{MAX_CUSTOM_SCALE_FACTOR}.0", True),
        # Several screens
        ("1.5;2", True),
        (f"2;{MAX_CUSTOM_SCALE_FACTOR}", True),
        ("1.5;", False),  # Still being typed
        # Values above the maximum
        (str(MAX_CUSTOM_SCALE_FACTOR + 1), False),
        (f"{MAX_CUSTOM_SCALE_FACTOR}.5", False),
        (f"{MAX_CUSTOM_SCALE_FACTOR}.01", False),
        ("10", False),
        ("99.0", False),
        (f"1.5;{MAX_CUSTOM_SCALE_FACTOR + 1}", False),
        # Values below 1 are still not allowed
        ("0", False),
        ("0.5", False),
        # Other invalid text
        ("a", False),
        ("-1", False),
        ("1..5", False),
    ]
)
def test_custom_scale_factor_validator(
    delete_container, config_dialog, text, acceptable  # noqa
):
    """
    The custom scale factor accepts whole numbers and rejects values above
    the maximum.

    This is a regression test for spyder-ide/spyder#26495.
    """
    page = config_dialog.get_page()
    assert is_acceptable(page, text) == acceptable


@pytest.mark.parametrize(
    'config_dialog',
    [[MainWindowMock, [], [Application]]],
    indirect=True
)
def test_custom_scale_factor_typing(
    delete_container, config_dialog, qtbot  # noqa
):
    """Typing a value above the maximum is blocked as it's typed."""
    page = config_dialog.get_page()
    textbox = page.custom_scaling_edit.textbox
    page.custom_scaling_radio.radiobutton.setChecked(True)

    textbox.clear()
    qtbot.keyClicks(textbox, "2")
    assert textbox.text() == "2"
    assert textbox.hasAcceptableInput()

    textbox.clear()
    qtbot.keyClicks(textbox, "99.0")
    assert textbox.text() == ""
    assert not textbox.hasAcceptableInput()

    textbox.clear()
    qtbot.keyClicks(textbox, f"{MAX_CUSTOM_SCALE_FACTOR}.5")
    assert textbox.text() == f"{MAX_CUSTOM_SCALE_FACTOR}."

    # A semicolon can be typed to start the value for another screen
    textbox.clear()
    qtbot.keyClicks(textbox, "1.5;")
    assert textbox.text() == "1.5;"
    assert not textbox.hasAcceptableInput()
    qtbot.keyClicks(textbox, "6")
    assert textbox.text() == "1.5;"


@pytest.mark.parametrize(
    'config_dialog',
    [[MainWindowMock, [], [Application]]],
    indirect=True
)
@pytest.mark.parametrize('custom_scale_factor', ["99.0"], indirect=True)
def test_custom_scale_factor_saved_above_max(
    custom_scale_factor, delete_container, config_dialog  # noqa
):
    """
    A value above the maximum saved before the limit was added is shown as is
    and saved unchanged when the page is applied.
    """
    page = config_dialog.get_page()
    textbox = page.custom_scaling_edit.textbox
    assert textbox.text() == custom_scale_factor
    assert not textbox.hasAcceptableInput()

    page.changed_options.add('high_dpi_custom_scale_factors')
    page.save_to_conf()
    assert CONF.get('main', 'high_dpi_custom_scale_factors') == "99.0"
