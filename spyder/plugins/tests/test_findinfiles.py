# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""Test scripts for `findinfiles` plugin."""

# Standard library imports
import re
import os
import os.path as osp

# 3rd party imports
import pytest

# Local imports
from spyder.config.main import EXCLUDE_PATTERNS
from spyder.plugins.findinfiles import FindInFiles
from spyder.widgets.findinfiles import SELECT_OTHER

LOCATION = osp.realpath(osp.join(os.getcwd(), osp.dirname(__file__)))
NONASCII_DIR = osp.join(LOCATION, u"èáïü Øαôå 字分误")
if not osp.exists(NONASCII_DIR):
    os.makedirs(NONASCII_DIR)


@pytest.fixture
def findinfiles_bot(qtbot):
    """Set up SearchInComboBox combobox."""
    findinfiles_plugin = FindInFiles()
    qtbot.addWidget(findinfiles_plugin)
    return findinfiles_plugin, qtbot


def check_regex(patterns):
    """
    Check that regular expression patterns provided by compiling them.
    Return a list of booleans for each of the provided patterns.
    """
    checks = []
    for pattern in patterns:
        try:
            re.compile(pattern)
            is_valid = True
        except re.error:
            is_valid = False
        checks.append(is_valid)
    return checks


def test_exclude_patterns_are_valid_regex():
    checks = check_regex(EXCLUDE_PATTERNS)
    assert all(checks)


# ---- Tests for FindInFiles plugin

def test_closing_plugin(qtbot, mocker):
    """
    Test that the external paths listed in the combobox are saved and loaded
    correctly from the spyder config file.
    """
    findinfiles_plugin, qtbot = findinfiles_bot(qtbot)
    path_selection_combo = findinfiles_plugin.find_options.path_selection_combo
    path_selection_combo.clear_external_paths()
    assert path_selection_combo.get_external_paths() == []

    # Add external paths to the path_selection_combo.
    expected_results = [
            LOCATION,
            osp.dirname(LOCATION),
            osp.dirname(osp.dirname(LOCATION)),
            NONASCII_DIR
            ]
    for external_path in expected_results:
        mocker.patch('spyder.widgets.findinfiles.getexistingdirectory',
                     return_value=external_path)
        path_selection_combo.setCurrentIndex(SELECT_OTHER)
    assert path_selection_combo.get_external_paths() == expected_results

    findinfiles_plugin.closing_plugin()
    assert findinfiles_plugin.get_option('path_history') == expected_results

    # Close and restart the plugin and assert that the external_path_history
    # has been saved and loaded as expected.
    findinfiles_plugin.close()
    findinfiles_plugin, qtbot = findinfiles_bot(qtbot)
    path_selection_combo = findinfiles_plugin.find_options.path_selection_combo
    assert path_selection_combo.get_external_paths() == expected_results



if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-v', '-rw'])
