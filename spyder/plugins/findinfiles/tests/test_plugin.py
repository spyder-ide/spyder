# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""Test scripts for `findinfiles` plugin."""

# Standard library imports
import os
import os.path as osp

# 3rd party imports
import pytest

# Local imports
from spyder.config.manager import CONF
from spyder.plugins.findinfiles.plugin import FindInFiles
from spyder.plugins.findinfiles.widgets import SELECT_OTHER

LOCATION = osp.realpath(osp.join(os.getcwd(), osp.dirname(__file__)))
NONASCII_DIR = osp.join(LOCATION, "èáïü Øαôå 字分误")
if not osp.exists(NONASCII_DIR):
    os.makedirs(NONASCII_DIR)


@pytest.fixture
def findinfiles(qtbot):
    """Set up SearchInComboBox combobox."""
    findinfiles_plugin = FindInFiles(None, configuration=CONF)

    # qtbot wants to close the widget
    findinfiles_plugin.close = lambda: True
    qtbot.addWidget(findinfiles_plugin)

    return findinfiles_plugin


# ---- Tests for FindInFiles plugin
@pytest.mark.first
def test_closing_plugin(findinfiles, qtbot, mocker):
    """
    Test that the external paths listed in the combobox are saved and loaded
    correctly from the spyder config file.
    """
    path_selection_combo = findinfiles.get_widget().path_selection_combo
    path_selection_combo.clear_external_paths()
    assert path_selection_combo.get_external_paths() == []

    # Add external paths to the path_selection_combo.
    expected_results = [
        LOCATION,
        osp.dirname(LOCATION),
        osp.dirname(osp.dirname(LOCATION)),
        NONASCII_DIR,
    ]
    for external_path in expected_results:
        mocker.patch('spyder.plugins.findinfiles.widgets.getexistingdirectory',
                     return_value=external_path)
        path_selection_combo.setCurrentIndex(SELECT_OTHER)

    assert path_selection_combo.get_external_paths() == expected_results

    findinfiles.on_close()
    path_history = findinfiles.get_widget().get_option('path_history')
    assert path_history == expected_results

    # Close the plugin and assert that the external_path_history
    # has been saved and loaded as expected.
    path_selection_combo = findinfiles.get_widget().path_selection_combo
    assert path_selection_combo.get_external_paths() == expected_results


if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-v', '-rw'])
