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
import os.path as osp

# Third party imports
from flaky import flaky
import pytest
from qtpy.QtCore import Qt

# Local imports
from spyder.plugins.findinfiles import widgets
from spyder.plugins.findinfiles.widgets import (FindInFilesWidget, SearchInComboBox,
                                                EXTERNAL_PATHS, SELECT_OTHER, CWD,
                                                CLEAR_LIST, PROJECT, FILE_PATH,
                                                QMessageBox, SearchThread)
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
def findinfiles(qtbot, request):
    """Set up find in files widget."""
    if getattr(request, 'param', False):
        param = request.param
    else:
        param = None

    if param:
        widget = FindInFilesWidget(None, **param)
    else:
        widget = FindInFilesWidget(None)

    widget.resize(640, 480)
    qtbot.addWidget(widget)
    widget.show()
    return widget


@pytest.fixture
def searchin_combobox(qtbot, request):
    """Set up SearchInComboBox combobox."""
    from spyder.plugins.findinfiles import widgets

    if getattr(request, 'param', False):
        param = request.param
    else:
        param = None

    if param and param.get('max_history_path'):
        widgets.MAX_PATH_HISTORY = param.get('max_history_path')

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
    return searchin_combobox


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


@flaky(max_runs=5)
def test_find_in_files_search(findinfiles, qtbot):
    """
    Test the find in files utility by searching a string located on a set of
    known files.

    The results of the test should be equal to the expected search result
    values.
    """
    findinfiles.set_search_text("spam")
    findinfiles.find_options.set_directory(osp.join(LOCATION, "data"))
    findinfiles.find()
    blocker = qtbot.waitSignal(findinfiles.sig_finished)
    blocker.wait()
    matches = process_search_results(findinfiles.result_browser.data)
    assert expected_results() == matches


@pytest.mark.parametrize('findinfiles',
                         [{'exclude': r"\.py$", 'exclude_regexp': True}],
                         indirect=True)
def test_exclude_extension_regex(findinfiles, qtbot):
    findinfiles.set_search_text("spam")
    findinfiles.find_options.set_directory(osp.join(LOCATION, "data"))
    findinfiles.find()
    blocker = qtbot.waitSignal(findinfiles.sig_finished)
    blocker.wait()
    matches = process_search_results(findinfiles.result_browser.data)
    files_filtered = True
    for file in matches:
        filename, ext = osp.splitext(file)
        if ext == '.py':
            files_filtered = False
            break
    assert files_filtered


@pytest.mark.parametrize('findinfiles',
                         [{'exclude': "*.py", 'exclude_regexp': False}],
                         indirect=True)
def test_exclude_extension_string(findinfiles, qtbot):
    findinfiles.set_search_text("spam")
    findinfiles.find_options.set_directory(osp.join(LOCATION, "data"))
    findinfiles.find()
    blocker = qtbot.waitSignal(findinfiles.sig_finished)
    blocker.wait()
    matches = process_search_results(findinfiles.result_browser.data)
    files_filtered = True
    for file in matches:
        filename, ext = osp.splitext(file)
        if ext == '.py':
            files_filtered = False
            break
    assert files_filtered


@pytest.mark.parametrize('findinfiles',
                         [{'exclude': "", 'exclude_regexp': True}],
                         indirect=True)
def test_exclude_extension_empty_regex(findinfiles, qtbot):
    findinfiles.set_search_text("spam")
    findinfiles.find_options.set_directory(osp.join(LOCATION, "data"))
    findinfiles.find()
    blocker = qtbot.waitSignal(findinfiles.sig_finished)
    blocker.wait()
    matches = process_search_results(findinfiles.result_browser.data)
    assert expected_results() == matches


@pytest.mark.parametrize('findinfiles',
                         [{'exclude': "", 'exclude_regexp': False}],
                         indirect=True)
def test_exclude_extension_string_no_regexp(findinfiles, qtbot):
    findinfiles.set_search_text("spam")
    findinfiles.find_options.set_directory(osp.join(LOCATION, "data"))
    findinfiles.find()
    blocker = qtbot.waitSignal(findinfiles.sig_finished)
    blocker.wait()
    matches = process_search_results(findinfiles.result_browser.data)
    assert expected_results() == matches


@pytest.mark.parametrize('findinfiles',
                         [{'exclude': "*.py, *.cpp", 'exclude_regexp': False}],
                         indirect=True)
def test_exclude_extension_multiple_string(findinfiles, qtbot):
    findinfiles.set_search_text("spam")
    findinfiles.find_options.set_directory(osp.join(LOCATION, "data"))
    findinfiles.find()
    blocker = qtbot.waitSignal(findinfiles.sig_finished)
    blocker.wait()
    matches = process_search_results(findinfiles.result_browser.data)
    files_filtered = True
    for file in matches:
        filename, ext = osp.splitext(file)
        if ext in ['.py', '.cpp']:
            files_filtered = False
            break
    assert files_filtered


@pytest.mark.parametrize("line_input", ['nnnnn', 'ñandú'])
def test_truncate_result_with_different_input(findinfiles, qtbot, line_input):
    """
    Issue: 6218 - checking if truncate_result raise UnicodeDecodeError
    """

    # with
    slice_start = 1
    slice_end = 2

    if PY2:
        line_input_expected = line_input.decode('utf-8')
    else:
        line_input_expected = line_input

    expected_result = u'<span style="color:None">%s<b>%s</b>%s</span>' % (
        line_input_expected[:slice_start],
        line_input_expected[slice_start:slice_end],
        line_input_expected[slice_end:])

    # when
    thread = SearchThread(None, '')
    truncated_line = thread.truncate_result(line_input, slice_start,
                                            slice_end)
    # then
    assert truncated_line == expected_result


@pytest.mark.parametrize('findinfiles',
                         [{'case_sensitive': False}],
                         indirect=True)
def test_case_unsensitive_search(findinfiles, qtbot):
    findinfiles.set_search_text('ham')
    findinfiles.find_options.set_directory(osp.join(LOCATION, "data"))
    findinfiles.find()
    blocker = qtbot.waitSignal(findinfiles.sig_finished)
    blocker.wait()
    matches = process_search_results(findinfiles.result_browser.data)
    print(matches)
    assert expected_case_unsensitive_results() == matches


@pytest.mark.parametrize('findinfiles',
                         [{'case_sensitive': True}],
                         indirect=True)
def test_case_sensitive_search(findinfiles, qtbot):
    findinfiles.set_search_text('HaM')
    findinfiles.find_options.set_directory(osp.join(LOCATION, "data"))
    findinfiles.find()
    blocker = qtbot.waitSignal(findinfiles.sig_finished)
    blocker.wait()
    matches = process_search_results(findinfiles.result_browser.data)
    print(matches)
    assert matches == {'ham.txt': [(9, 0)]}


@pytest.mark.parametrize('findinfiles',
                         [{'search_text_regexp': True}],
                         indirect=True)
def test_search_regexp_error(findinfiles, qtbot):
    findinfiles.set_search_text("\\")
    findinfiles.find_options.set_directory(osp.join(LOCATION, "data"))
    findinfiles.find()
    tooltip = findinfiles.find_options.search_text.toolTip()
    assert findinfiles.find_options.REGEX_ERROR in tooltip


@pytest.mark.parametrize('findinfiles',
                         [{'exclude': "\\", 'exclude_regexp': True}],
                         indirect=True)
def test_exclude_regexp_error(findinfiles, qtbot):
    findinfiles.set_search_text("foo")
    findinfiles.find_options.set_directory(osp.join(LOCATION, "data"))
    findinfiles.find()
    tooltip = findinfiles.find_options.exclude_pattern.toolTip()
    assert findinfiles.find_options.REGEX_ERROR in tooltip


# ---- Tests for SearchInComboBox

def test_add_external_paths(searchin_combobox, mocker):
    """
    Test that the external_path_history is added correctly to the
    combobox and test that adding new external path to the combobox
    with the QFileDialog is working as expected.
    """
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
    mocker.patch('spyder.plugins.findinfiles.widgets.getexistingdirectory',
                 return_value=new_path)
    searchin_combobox.setCurrentIndex(SELECT_OTHER)

    expected_results.append(new_path)
    assert searchin_combobox.count() == len(expected_results)+EXTERNAL_PATHS
    assert searchin_combobox.get_external_paths() == expected_results
    assert searchin_combobox.currentIndex() == searchin_combobox.count()-1

    # Add an external path that is already listed in the combobox. In this
    # case, the new path is removed from the list and is added back at the end.
    new_path = LOCATION
    mocker.patch('spyder.plugins.findinfiles.widgets.getexistingdirectory',
                 return_value=new_path)
    searchin_combobox.setCurrentIndex(SELECT_OTHER)

    expected_results.pop(0)
    expected_results.append(new_path)
    assert searchin_combobox.count() == len(expected_results)+EXTERNAL_PATHS
    assert searchin_combobox.get_external_paths() == expected_results
    assert searchin_combobox.currentIndex() == searchin_combobox.count()-1

    # Cancel the action of adding a new external path. In this case, the
    # expected results do not change.
    mocker.patch('spyder.plugins.findinfiles.widgets.getexistingdirectory',
                 return_value='')
    searchin_combobox.setCurrentIndex(SELECT_OTHER)

    assert searchin_combobox.count() == len(expected_results)+EXTERNAL_PATHS
    assert searchin_combobox.get_external_paths() == expected_results
    assert searchin_combobox.currentIndex() == CWD


def test_clear_this_list(searchin_combobox, mocker):
    """
    Test the option in the searchin combobox to clear the list of
    external paths.
    """
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


def test_delete_path(searchin_combobox, qtbot, mocker):
    """
    Test that the selected external path in the combobox view is removed
    correctly when the Delete key is pressed.
    """
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


def test_set_project_path(findinfiles, qtbot):
    """
    Test setting the project path of the SearchInComboBox from the
    FindInFilesWidget.
    """
    find_options = findinfiles.find_options
    path_selection_combo = find_options.path_selection_combo
    findinfiles.show()

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


@pytest.mark.parametrize('findinfiles',
                         [{'external_path_history': [LOCATION,
                                                     osp.dirname(LOCATION),
                                                     osp.dirname(osp.dirname(LOCATION)),
                                                     NONASCII_DIR]}],
                         indirect=True)
def test_current_search_path(findinfiles, qtbot):
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

    find_options = findinfiles.find_options
    path_selection_combo = find_options.path_selection_combo
    findinfiles.show()

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


@pytest.mark.parametrize('searchin_combobox',
                         [{'max_history_path': 3}],
                         indirect=True)
def test_max_history(searchin_combobox, mocker):
    """
    Test that the specified maximum number of external path is observed.
    """
    searchin_combobox.show()

    # In this case, the first path of the external_path_history was removed to
    # respect the MAX_PATH_HISTORY of 3.
    expected_results = [
            osp.dirname(osp.dirname(LOCATION)),
            osp.dirname(osp.dirname(osp.dirname(LOCATION))),
            osp.dirname(LOCATION)
    ]
    assert searchin_combobox.count() == len(expected_results) + EXTERNAL_PATHS
    assert searchin_combobox.get_external_paths() == expected_results


def test_max_results(findinfiles, qtbot):
    """Test max results correspond to expected results."""
    value = 2
    findinfiles.set_max_results(value)
    findinfiles.set_search_text("spam")
    findinfiles.find_options.set_directory(osp.join(LOCATION, "data"))

    findinfiles.find()
    blocker = qtbot.waitSignal(findinfiles.sig_max_results_reached)
    blocker.wait()

    print(len(findinfiles.result_browser.data), value)
    assert len(findinfiles.result_browser.data) == value

    # Restore defaults
    findinfiles.set_max_results(1000)


if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-v', '-rw'])
