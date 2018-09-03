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

# Third party imports
from qtpy.QtCore import Qt

# Local imports
from spyder.widgets import findinfiles
from spyder.widgets.findinfiles import (FindInFilesWidget, SearchInComboBox,
                                        EXTERNAL_PATHS, SELECT_OTHER, CWD,
                                        CLEAR_LIST, PROJECT, FILE_PATH,
                                        QMessageBox)
from spyder.py3compat import PY2

LOCATION = osp.realpath(osp.join(os.getcwd(), osp.dirname(__file__)))
NONASCII_DIR = osp.join(LOCATION, u"èáïü Øαôå 字分误")
if not osp.exists(NONASCII_DIR):
    os.makedirs(NONASCII_DIR)


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


@pytest.fixture
def searchin_combobox_bot(qtbot):
    """Set up SearchInComboBox combobox."""
    external_path_history = [
            LOCATION,
            osp.dirname(LOCATION),
            osp.dirname(osp.dirname(LOCATION)),
            osp.dirname(osp.dirname(osp.dirname(LOCATION))),
            osp.dirname(LOCATION),
            osp.join(LOCATION, 'path_that_does_not_exist')
            ]
    searchin_combobox = SearchInComboBox(external_path_history)
    qtbot.addWidget(searchin_combobox)
    return searchin_combobox, qtbot


def expected_results():
    results = {'spam.txt': [(1, 0), (1, 5), (3, 22)],
               'spam.py': [(2, 7), (5, 1), (7, 12)],
               'spam.cpp': [(2, 9), (6, 15), (8, 2), (11, 4),
                            (11, 10), (13, 12)]
               }
    return results


def expected_case_unsensitive_results():
    results = {'spam.txt': [(1, 10)],
               'ham.txt': [(1, 0), (1, 10), (3, 0), (4, 0),
                           (5, 4), (9, 0), (10, 0)]}
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
    assert expected_results() == matches


def test_exclude_extension_regex(qtbot):
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


def test_exclude_extension_string(qtbot):
    find_in_files = setup_findinfiles(qtbot, exclude="*.py",
                                      exclude_regexp=False)
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


def test_exclude_extension_empty_regex(qtbot):
    find_in_files = setup_findinfiles(qtbot, exclude="")
    find_in_files.set_search_text("spam")
    find_in_files.find_options.set_directory(osp.join(LOCATION, "data"))
    find_in_files.find()
    blocker = qtbot.waitSignal(find_in_files.sig_finished)
    blocker.wait()
    matches = process_search_results(find_in_files.result_browser.data)
    assert expected_results() == matches


def test_exclude_extension_string(qtbot):
    find_in_files = setup_findinfiles(qtbot, exclude="",
                                      exclude_regexp=False)
    find_in_files.set_search_text("spam")
    find_in_files.find_options.set_directory(osp.join(LOCATION, "data"))
    find_in_files.find()
    blocker = qtbot.waitSignal(find_in_files.sig_finished)
    blocker.wait()
    matches = process_search_results(find_in_files.result_browser.data)
    assert expected_results() == matches


def test_exclude_extension_multiple_string(qtbot):
    find_in_files = setup_findinfiles(qtbot, exclude="*.py, *.cpp",
                                      exclude_regexp=False)
    find_in_files.set_search_text("spam")
    find_in_files.find_options.set_directory(osp.join(LOCATION, "data"))
    find_in_files.find()
    blocker = qtbot.waitSignal(find_in_files.sig_finished)
    blocker.wait()
    matches = process_search_results(find_in_files.result_browser.data)
    files_filtered = True
    for file in matches:
        filename, ext = osp.splitext(file)
        if ext in ['.py', '.cpp']:
            print(ext)
            files_filtered = False
            break
    assert files_filtered


@pytest.mark.parametrize("line_input", ['nnnnn', 'ñandú'])
def test_truncate_result_with_different_input(qtbot, line_input):
    """
    Issue: 6218 - checking if truncate_result raise UnicodeDecodeError
    """

    # with
    find_in_files = setup_findinfiles(qtbot)
    slice_start = 1
    slice_end = 2

    if PY2:
        line_input_expected = line_input.decode('utf-8')
    else:
        line_input_expected = line_input

    expected_result = u'%s<b>%s</b>%s' % (
        line_input_expected[:slice_start],
        line_input_expected[slice_start:slice_end],
        line_input_expected[slice_end:])

    # when
    truncated_line = find_in_files.result_browser.truncate_result(
        line_input, slice_start, slice_end)

    # then
    assert truncated_line == expected_result


def test_case_unsensitive_search(qtbot):
    find_in_files = setup_findinfiles(qtbot, case_sensitive=False)
    find_in_files.set_search_text('ham')
    find_in_files.find_options.set_directory(osp.join(LOCATION, "data"))
    find_in_files.find()
    blocker = qtbot.waitSignal(find_in_files.sig_finished)
    blocker.wait()
    matches = process_search_results(find_in_files.result_browser.data)
    print(matches)
    assert expected_case_unsensitive_results() == matches


def test_case_sensitive_search(qtbot):
    find_in_files = setup_findinfiles(qtbot)
    find_in_files.set_search_text('HaM')
    find_in_files.find_options.set_directory(osp.join(LOCATION, "data"))
    find_in_files.find()
    blocker = qtbot.waitSignal(find_in_files.sig_finished)
    blocker.wait()
    matches = process_search_results(find_in_files.result_browser.data)
    print(matches)
    assert matches == {'ham.txt': [(9, 0)]}


# ---- Tests for SearchInComboBox

def test_add_external_paths(searchin_combobox_bot, mocker):
    """
    Test that the external_path_history is added correctly to the
    combobox and test that adding new external path to the combobox
    with the QFileDialog is working as expected.
    """
    searchin_combobox, qtbot = searchin_combobox_bot
    searchin_combobox.show()

    # Assert that the external_path_history was added correctly to the
    # combobox
    expected_results = [
            LOCATION,
            osp.dirname(osp.dirname(LOCATION)),
            osp.dirname(osp.dirname(osp.dirname(LOCATION))),
            osp.dirname(LOCATION)
            ]
    assert searchin_combobox.count() == len(expected_results)+EXTERNAL_PATHS
    assert searchin_combobox.get_external_paths() == expected_results
    for i, expected_result in enumerate(expected_results):
        assert expected_result == searchin_combobox.itemText(i+EXTERNAL_PATHS)

    # Add a new external path to the combobox. The new path is added at the
    # end of the combobox.
    new_path = NONASCII_DIR
    mocker.patch('spyder.widgets.findinfiles.getexistingdirectory',
                 return_value=new_path)
    searchin_combobox.setCurrentIndex(SELECT_OTHER)

    expected_results.append(new_path)
    assert searchin_combobox.count() == len(expected_results)+EXTERNAL_PATHS
    assert searchin_combobox.get_external_paths() == expected_results
    assert searchin_combobox.currentIndex() == searchin_combobox.count()-1

    # Add an external path that is already listed in the combobox. In this
    # case, the new path is removed from the list and is added back at the end.
    new_path = LOCATION
    mocker.patch('spyder.widgets.findinfiles.getexistingdirectory',
                 return_value=new_path)
    searchin_combobox.setCurrentIndex(SELECT_OTHER)

    expected_results.pop(0)
    expected_results.append(new_path)
    assert searchin_combobox.count() == len(expected_results)+EXTERNAL_PATHS
    assert searchin_combobox.get_external_paths() == expected_results
    assert searchin_combobox.currentIndex() == searchin_combobox.count()-1

    # Cancel the action of adding a new external path. In this case, the
    # expected results do not change.
    mocker.patch('spyder.widgets.findinfiles.getexistingdirectory',
                 return_value='')
    searchin_combobox.setCurrentIndex(SELECT_OTHER)

    assert searchin_combobox.count() == len(expected_results)+EXTERNAL_PATHS
    assert searchin_combobox.get_external_paths() == expected_results
    assert searchin_combobox.currentIndex() == CWD


def test_clear_this_list(searchin_combobox_bot, mocker):
    """
    Test the option in the searchin combobox to clear the list of
    external paths.
    """
    searchin_combobox, qtbot = searchin_combobox_bot
    searchin_combobox.show()

    # Cancel the Clear the list action and assert the result.
    mocker.patch.object(QMessageBox, 'question', return_value=QMessageBox.No)
    searchin_combobox.setCurrentIndex(CLEAR_LIST)

    expected_results = [
            LOCATION,
            osp.dirname(osp.dirname(LOCATION)),
            osp.dirname(osp.dirname(osp.dirname(LOCATION))),
            osp.dirname(LOCATION)
            ]
    assert searchin_combobox.count() == len(expected_results)+EXTERNAL_PATHS
    assert searchin_combobox.get_external_paths() == expected_results
    assert searchin_combobox.currentIndex() == CWD

    # Clear the list of external paths and assert that the list of
    # external paths is empty.
    mocker.patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes)
    searchin_combobox.setCurrentIndex(CLEAR_LIST)

    assert searchin_combobox.count() == EXTERNAL_PATHS
    assert searchin_combobox.get_external_paths() == []
    assert searchin_combobox.currentIndex() == CWD


def test_delete_path(searchin_combobox_bot, mocker):
    """
    Test that the selected external path in the combobox view is removed
    correctly when the Delete key is pressed.
    """
    searchin_combobox, qtbot = searchin_combobox_bot
    searchin_combobox.show()

    expected_results = [
            LOCATION,
            osp.dirname(osp.dirname(LOCATION)),
            osp.dirname(osp.dirname(osp.dirname(LOCATION))),
            osp.dirname(LOCATION)
            ]

    searchin_combobox.showPopup()
    assert searchin_combobox.currentIndex() == CWD
    assert searchin_combobox.view().currentIndex().row() == CWD

    # Assert that the delete action does nothing when the selected item in
    # the combobox view is not an external path.
    for i in range(EXTERNAL_PATHS):
        searchin_combobox.view().setCurrentIndex(
            searchin_combobox.model().index(i, 0))
        qtbot.keyPress(searchin_combobox.view(), Qt.Key_Delete)

    assert searchin_combobox.count() == len(expected_results)+EXTERNAL_PATHS
    assert searchin_combobox.get_external_paths() == expected_results
    assert searchin_combobox.currentIndex() == CWD

    # Delete the first external path in the list.
    searchin_combobox.view().setCurrentIndex(
            searchin_combobox.model().index(EXTERNAL_PATHS, 0))
    qtbot.keyPress(searchin_combobox.view(), Qt.Key_Delete)

    expected_results.pop(0)
    assert searchin_combobox.count() == len(expected_results)+EXTERNAL_PATHS
    assert searchin_combobox.get_external_paths() == expected_results
    assert searchin_combobox.currentIndex() == EXTERNAL_PATHS
    assert searchin_combobox.view().currentIndex().row() == EXTERNAL_PATHS

    # Delete the second external path in the remaining list.
    searchin_combobox.view().setCurrentIndex(
            searchin_combobox.model().index(EXTERNAL_PATHS+1, 0))
    qtbot.keyPress(searchin_combobox.view(), Qt.Key_Delete)

    expected_results.pop(1)
    assert searchin_combobox.count() == len(expected_results)+EXTERNAL_PATHS
    assert searchin_combobox.get_external_paths() == expected_results
    assert searchin_combobox.currentIndex() == EXTERNAL_PATHS+1
    assert searchin_combobox.view().currentIndex().row() == EXTERNAL_PATHS+1

    # Delete the last external path in the list.
    searchin_combobox.view().setCurrentIndex(
            searchin_combobox.model().index(searchin_combobox.count()-1, 0))
    qtbot.keyPress(searchin_combobox.view(), Qt.Key_Delete)

    expected_results.pop()
    assert searchin_combobox.count() == len(expected_results)+EXTERNAL_PATHS
    assert searchin_combobox.get_external_paths() == expected_results
    assert searchin_combobox.currentIndex() == searchin_combobox.count()-1
    assert (searchin_combobox.view().currentIndex().row() ==
            searchin_combobox.count()-1)

    # Delete the last remaining external path in the list.
    searchin_combobox.view().setCurrentIndex(
            searchin_combobox.model().index(EXTERNAL_PATHS, 0))
    qtbot.keyPress(searchin_combobox.view(), Qt.Key_Delete)

    assert searchin_combobox.count() == EXTERNAL_PATHS
    assert searchin_combobox.get_external_paths() == []
    assert searchin_combobox.currentIndex() == CWD
    assert searchin_combobox.view().currentIndex().row() == CWD


def test_set_project_path(qtbot):
    """
    Test setting the project path of the SearchInComboBox from the
    FindInFilesWidget.
    """
    findinfiles_widget = setup_findinfiles(qtbot)
    find_options = findinfiles_widget.find_options
    path_selection_combo = find_options.path_selection_combo
    findinfiles_widget.show()

    assert path_selection_combo.model().item(PROJECT, 0).isEnabled() is False
    assert find_options.project_path is None
    assert path_selection_combo.project_path is None

    # Set the project path to an existing directory. For the purpose of this
    # test, it doesn't need to be a valid Spyder project path.
    project_path = NONASCII_DIR
    find_options.set_project_path(project_path)
    assert path_selection_combo.model().item(PROJECT, 0).isEnabled() is True
    assert find_options.project_path == project_path
    assert path_selection_combo.project_path == project_path

    # Disable the project path search in the widget.
    path_selection_combo.setCurrentIndex(PROJECT)
    find_options.disable_project_search()
    assert path_selection_combo.model().item(PROJECT, 0).isEnabled() is False
    assert find_options.project_path is None
    assert path_selection_combo.project_path is None
    assert path_selection_combo.currentIndex() == CWD


def test_current_search_path(qtbot):
    """
    Test that the expected search path is returned for the corresponding
    option selected in the SearchInComboBox. This test is done using the
    FindInFilesWidget.
    """
    external_paths = [
            LOCATION,
            osp.dirname(LOCATION),
            osp.dirname(osp.dirname(LOCATION)),
            NONASCII_DIR
            ]

    findinfiles_widget = setup_findinfiles(
            qtbot, external_path_history=external_paths)
    find_options = findinfiles_widget.find_options
    path_selection_combo = find_options.path_selection_combo
    findinfiles_widget.show()

    # Set the project, file, and spyder path of the SearchInComboBox.
    # For the purpose of this test, the project path doesn't need to be a
    # valid Spyder project path.

    directory = NONASCII_DIR
    project_path = NONASCII_DIR
    file_path = osp.join(directory, "spam.py")

    find_options.set_directory(directory)
    assert find_options.path == directory
    assert path_selection_combo.path == directory

    find_options.set_project_path(project_path)
    assert find_options.project_path == project_path
    assert path_selection_combo.project_path == project_path

    find_options.set_file_path(file_path)
    assert find_options.file_path == file_path
    assert path_selection_combo.file_path == file_path

    # Assert that the good path is returned for each option selected.

    # Test for the current working directory :
    path_selection_combo.setCurrentIndex(CWD)
    assert path_selection_combo.get_current_searchpath() == directory
    assert path_selection_combo.is_file_search() is False
    # Test for the project path :
    path_selection_combo.setCurrentIndex(PROJECT)
    assert path_selection_combo.get_current_searchpath() == project_path
    assert path_selection_combo.is_file_search() is False
    # Test for the file path :
    path_selection_combo.setCurrentIndex(FILE_PATH)
    assert path_selection_combo.get_current_searchpath() == file_path
    assert path_selection_combo.is_file_search() is True
    # Test for the external file path :
    for i, path in enumerate(external_paths):
        path_selection_combo.setCurrentIndex(EXTERNAL_PATHS+i)
        assert path_selection_combo.get_current_searchpath() == path
        assert path_selection_combo.is_file_search() is False


def test_max_history(qtbot, mocker):
    """
    Test that the specified maximum number of external path is observed.
    """
    findinfiles.MAX_PATH_HISTORY = 3
    searchin_combobox, qtbot = searchin_combobox_bot(qtbot)
    searchin_combobox.show()

    # In this case, the first path of the external_path_history was removed to
    # respect the MAX_PATH_HISTORY of 3.
    expected_results = [
            osp.dirname(osp.dirname(LOCATION)),
            osp.dirname(osp.dirname(osp.dirname(LOCATION))),
            osp.dirname(LOCATION)
            ]
    assert searchin_combobox.count() == len(expected_results)+EXTERNAL_PATHS
    assert searchin_combobox.get_external_paths() == expected_results


if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-v', '-rw'])
