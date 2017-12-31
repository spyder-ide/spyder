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
import os.path as osp

# 3rd party imports
import pytest

# Local imports
from spyder.config.main import EXCLUDE_PATTERNS
from spyder.plugins.findinfiles import FindInFiles


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

def test_closing_plugin(qtbot):
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
            osp.dirname(__file__),
            osp.dirname(osp.dirname(osp.dirname(__file__))),
            osp.dirname(osp.dirname(osp.dirname(osp.dirname(__file__)))),
            osp.dirname(osp.dirname(__file__))
            ]
    for external_path in expected_results:
        path_selection_combo.add_external_path(external_path)
    assert path_selection_combo.get_external_paths() == expected_results

    # Force the options to be saved to the config file. Something needs to be
    # set in the search_text combobox first or else the find in files options
    # won't be save to the config file (see PR #6095).
    findinfiles_plugin.find_options.search_text.set_current_text("test")
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
