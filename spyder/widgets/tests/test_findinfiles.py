# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for findinfiles.py
"""

# Test library imports
import os
import pytest
import os.path as osp
from pytestqt import qtbot

# Local imports
import spyder.widgets.findinfiles
from spyder.widgets.findinfiles import FindInFilesWidget

LOCATION = os.path.realpath(os.path.join(os.getcwd(),
                                         os.path.dirname(__file__)))


def process_search_results(results):
    """
    Transform result representation from the output of the widget to the
    test framework comparison representation.
    """
    matches = {}
    for result in results.values():
        file, line, col = result
        filename = osp.basename(file)
        if filename not in matches:
            matches[filename] = []
        matches[filename].append((line, col))
        matches[filename] = sorted(matches[filename])
    return matches


@pytest.fixture
def setup_findinfiles(qtbot, *args, **kwargs):
    """Set up find in files widget."""
    widget = FindInFilesWidget(None, *args, **kwargs)
    qtbot.addWidget(widget)
    return widget


def expected_results():
    results = {'spam.txt': [(1, 0), (1, 5), (3, 22)],
               'spam.py': [(2, 7), (5, 1), (7, 12)],
               'spam.cpp': [(2, 9), (6, 15), (8, 2), (11, 4),
                            (11, 10), (13, 12)]
               }
    return results


def test_findinfiles(qtbot):
    """Run find in files widget."""
    find_in_files = setup_findinfiles(qtbot)
    find_in_files.resize(640, 480)
    find_in_files.show()
    assert find_in_files


def test_find_in_files_search(qtbot):
    """
    Test the find in files utility by searching a string located on a set of
    known files.

    The results of the test should be equal to the expected search result
    values.
    """
    find_in_files = setup_findinfiles(qtbot)
    find_in_files.set_search_text("spam")
    find_in_files.find_options.set_directory(osp.join(LOCATION, "data"))
    find_in_files.find()
    blocker = qtbot.waitSignal(find_in_files.sig_finished)
    blocker.wait()
    matches = process_search_results(find_in_files.result_browser.data)
    print(matches)
    assert expected_results() == matches


def test_exclude_extension(qtbot):
    find_in_files = setup_findinfiles(qtbot, exclude="\.py$")
    find_in_files.set_search_text("spam")
    find_in_files.find_options.set_directory(osp.join(LOCATION, "data"))
    find_in_files.find()
    blocker = qtbot.waitSignal(find_in_files.sig_finished)
    blocker.wait()
    matches = process_search_results(find_in_files.result_browser.data)
    files_filtered = True
    for file in matches:
        filename, ext = osp.splitext(file)
        if ext == '.py':
            files_filtered = False
            break
    assert files_filtered


if __name__ == "__main__":
    pytest.main()
