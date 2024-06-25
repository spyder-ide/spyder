# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Tests for the preferences dialog.
"""

from spyder.plugins.variableexplorer.widgets.preferences import (
    PreferencesDialog)


def test_preferences_float_format(qtbot):
    """
    Test that reading and setting float_format works.
    """
    dialog = PreferencesDialog('dataframe')
    dialog.float_format = 'old'
    assert dialog.format_input.text() == 'old'

    dialog.format_input.setText('new')
    assert dialog.float_format == 'new'


def test_preferences_background(qtbot):
    """
    Test default and varying background buttons.
    """
    dialog = PreferencesDialog('dataframe')
    dialog.varying_background = True

    assert dialog.varying_background
    assert not dialog.default_background_button.isChecked()
    assert dialog.varying_background_button.isChecked()
    assert dialog.global_button.isEnabled()
    assert dialog.by_column_button.isEnabled()

    dialog.default_background_button.toggle()

    assert not dialog.varying_background
    assert dialog.default_background_button.isChecked()
    assert not dialog.varying_background_button.isChecked()
    assert not dialog.global_button.isEnabled()
    assert not dialog.by_column_button.isEnabled()

    dialog.varying_background_button.toggle()

    assert dialog.varying_background
    assert not dialog.default_background_button.isChecked()
    assert dialog.varying_background_button.isChecked()
    assert dialog.global_button.isEnabled()
    assert dialog.by_column_button.isEnabled()


def test_preferences_coloring_algo(qtbot):
    """
    Test coloring algo buttons (global and by column)
    """
    dialog = PreferencesDialog('dataframe')
    dialog.varying_background = True
    dialog.global_algo = True

    assert dialog.global_algo
    assert dialog.global_button.isChecked()
    assert not dialog.by_column_button.isChecked()

    dialog.by_column_button.toggle()

    assert not dialog.global_algo
    assert not dialog.global_button.isChecked()
    assert dialog.by_column_button.isChecked()

    dialog.global_button.toggle()

    assert dialog.global_algo
    assert dialog.global_button.isChecked()
    assert not dialog.by_column_button.isChecked()


def test_preferences_for_arrays(qtbot):
    """
    Check that dialog for arrays does not have coloring algo buttons.
    """
    dialog = PreferencesDialog('array')
    assert 'global_button' not in dir(dialog)
    assert 'by_column_button' not in dir(dialog)
