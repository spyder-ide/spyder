# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for start.py
"""

# Standard library imports
import os
import os.path as osp

# Third-party imports
import pytest

# Local imports
from spyder.app import start
from spyder.app.cli_options import get_options
from spyder.config.base import get_conf_path
from spyder.config.manager import CONF


@pytest.fixture
def bad_hdpi_settings():
    """
    Set a custom scale factor that could make Spyder unusable and restore the
    defaults afterwards.
    """
    theme = CONF.get('appearance', 'selected')

    CONF.set('main', 'normal_screen_resolution', False)
    CONF.set('main', 'high_dpi_scaling', False)
    CONF.set('main', 'high_dpi_custom_scale_factor', True)
    CONF.set('main', 'high_dpi_custom_scale_factors', '9.5')
    CONF.set('appearance', 'selected', 'spyder_themes.spyder/light')

    yield

    reset_file = get_conf_path(start.HDPI_RESET_FILE)
    if osp.isfile(reset_file):
        os.remove(reset_file)

    start.set_hdpi_defaults()
    CONF.set('appearance', 'selected', theme)


@pytest.fixture
def no_spyder(monkeypatch):
    """Prevent Spyder from being started by start.main."""
    def start_spyder(*args, **kwargs):
        raise AssertionError("Spyder must not be started")

    monkeypatch.setattr('spyder.app.mainwindow.main', start_spyder)


def assert_hdpi_defaults():
    for option in start.HDPI_OPTIONS:
        assert CONF.get('main', option) == CONF.get_default('main', option)


def test_reset_hdpi_settings(bad_hdpi_settings):
    """
    Check that the high DPI settings are reset to their defaults and that the
    reset is requested for the next time Spyder starts.
    """
    assert start.reset_hdpi_settings() == 0

    assert_hdpi_defaults()
    assert osp.isfile(get_conf_path(start.HDPI_RESET_FILE))

    # Other options are not affected
    assert CONF.get('appearance', 'selected') == 'spyder_themes.spyder/light'


def test_apply_pending_hdpi_reset(bad_hdpi_settings):
    """
    Check that a reset requested while Spyder was running is applied, even if
    that Spyder restored its scale factor when saving its settings.
    """
    start.reset_hdpi_settings()

    # Simulate a running Spyder saving its settings
    CONF.set('main', 'high_dpi_custom_scale_factor', True)
    CONF.set('main', 'high_dpi_custom_scale_factors', '9.5')

    start.apply_pending_hdpi_reset()

    assert_hdpi_defaults()
    assert not osp.isfile(get_conf_path(start.HDPI_RESET_FILE))

    # Settings changed afterwards are kept the next time Spyder starts
    CONF.set('main', 'high_dpi_custom_scale_factor', True)
    start.apply_pending_hdpi_reset()
    assert CONF.get('main', 'high_dpi_custom_scale_factor') is True


@pytest.mark.parametrize(
    "argv, exit_code, is_reset",
    [
        (['--reset-hdpi-settings'], 0, True),
        (['--reset-hdpi-settings', '--safe-mode'], 1, False),
    ]
)
def test_main_reset_hdpi_settings(bad_hdpi_settings, no_spyder, monkeypatch,
                                  argv, exit_code, is_reset):
    """
    Check that main resets the high DPI settings and exits without starting
    Spyder, unless safe mode is used.
    """
    monkeypatch.setattr(start, 'CLI_OPTIONS', get_options(argv)[0])

    assert start.main() == exit_code
    assert CONF.get('main', 'high_dpi_custom_scale_factor') is not is_reset


@pytest.fixture
def restore_environ():
    """Restore the environment variables that start.main changes."""
    environ = dict(os.environ)
    yield
    os.environ.clear()
    os.environ.update(environ)


def test_main_applies_pending_hdpi_reset(bad_hdpi_settings, restore_environ,
                                         monkeypatch):
    """
    Check that a pending reset is applied before the scale factor is set when
    Spyder starts, even if the wrong one was passed by a restart.
    """
    start.reset_hdpi_settings()
    CONF.set('main', 'high_dpi_custom_scale_factor', True)
    CONF.set('main', 'high_dpi_custom_scale_factors', '9.5')

    scale_factors = []

    def start_spyder(*args, **kwargs):
        scale_factors.append(os.environ['QT_SCALE_FACTOR'])

    monkeypatch.setattr('spyder.app.mainwindow.main', start_spyder)
    monkeypatch.setattr(
        start, 'CLI_OPTIONS', get_options(['--new-instance'])[0]
    )
    os.environ['QT_SCALE_FACTOR'] = '9.5'

    start.main()

    assert scale_factors == ['']
    assert_hdpi_defaults()


def test_apply_pending_hdpi_reset_removed(bad_hdpi_settings, monkeypatch):
    """
    Check that there's no error if the reset file is removed by another
    instance started at the same time.
    """
    start.reset_hdpi_settings()

    def remove_file(path):
        raise FileNotFoundError(path)

    monkeypatch.setattr(start.os, 'remove', remove_file)
    start.apply_pending_hdpi_reset()

    assert_hdpi_defaults()


def test_show_message_console(monkeypatch, capsys):
    """Check that messages are printed if there is a console."""
    def show_dialog(*args):
        raise AssertionError("No dialog must be shown")

    monkeypatch.setattr('qtpy.QtWidgets.QMessageBox.information', show_dialog)

    start.show_message("Test message")
    assert capsys.readouterr().out == "Test message\n"


def test_show_message_no_console(qtbot, monkeypatch):
    """
    Check that messages are shown in a dialog with the default scaling if
    there is no console.
    """
    messages = []
    monkeypatch.setattr(
        'qtpy.QtWidgets.QMessageBox.information',
        lambda parent, title, text: messages.append(text)
    )
    monkeypatch.setattr(start.sys, 'stdout', None)
    monkeypatch.setenv('QT_SCALE_FACTOR', '9.5')
    monkeypatch.setenv('QT_SCREEN_SCALE_FACTORS', '9.5;9.5')

    start.show_message("Test message")

    assert messages == ["Test message"]
    assert 'QT_SCALE_FACTOR' not in os.environ
    assert 'QT_SCREEN_SCALE_FACTORS' not in os.environ


if __name__ == "__main__":
    pytest.main()
