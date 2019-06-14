# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# ----------------------------------------------------------------------------
"""
Tests for explorer plugin utilities.
"""

# Standard imports
import os
import os.path as osp
import sys

# Third party imports
import pytest

# Local imports
from spyder.plugins.explorer.widgets.fileassociations import (
    ApplicationsDialog, FileAssociationsWidget, InputTextDialog)


def test_input_text_dialog(qtbot):
    widget = InputTextDialog()
    qtbot.addWidget(widget)
    widget.show()

    # Test empty
    widget.validate()
    assert not widget.button_ok.isEnabled()

    # Test text
    widget.set_text('hello')
    widget.validate()
    assert widget.button_ok.isEnabled()

    # Test regex ok enabled
    widget.set_text('')
    widget.set_regex_validation('hello')
    qtbot.keyClicks(widget.lineedit, 'hello world!')
    assert widget.text() == 'hello'
    assert widget.button_ok.isEnabled()
    widget.validate()

    # Test regex ok disabled
    widget.set_text('')
    widget.set_regex_validation('hello')
    qtbot.keyClicks(widget.lineedit, 'hell')
    assert not widget.button_ok.isEnabled()
    widget.validate()


def test_apps_dialog(qtbot):
    widget = ApplicationsDialog()
    qtbot.addWidget(widget)
    widget.show()

    if os.name == 'nt':
        ext = '.exe'
    elif sys.platform == 'darwin':
        ext = '.app'
    else:
        ext = '.desktop'

    mock_apps = {
        'some app 1': '/some/fake/some app 1' + ext,
        'some app 2': '/some/fake/path/some app 2' + ext,
        'some app 3': '/some/fake/path/some app 3' + ext,
    }
    widget.setup(mock_apps)

    # Test filter
    qtbot.keyClicks(widget.edit_filter, '1')
    count_hidden = 0
    for row in range(widget.list.count()):
        item = widget.list.item(row)
        count_hidden += int(item.isHidden())
    assert count_hidden == 2

    # Test selected app
    widget.list.setCurrentItem(widget.list.item(0))
    assert widget.application_name == 'some app 1'
    assert widget.application_path == '/some/fake/some app 1' + ext

    # Test extension label
    widget.set_extension('.hello')
    assert '.hello' in widget.label.text()

    # Test reset filter
    widget.edit_filter.setText('')
    count_hidden = 0
    for row in range(widget.list.count()):
        item = widget.list.item(row)
        count_hidden += int(item.isHidden())
    assert count_hidden == 0

    # Test browse invalid
    fpath = '/some/other/path'
    widget.browse(fpath)
    assert widget.list.count() == 3

    # Test browse valid
    fpath = '/some/other/valid-app' + ext
    widget.browse(fpath)
    assert widget.list.count() == 4
    assert widget.application_name == os.path.basename(fpath).split('.')[0]
    assert widget.application_path == fpath

    # Test browse duplicate
    fpath = '/some/fake/path/some app 2' + ext
    widget.browse(fpath)
    assert widget.list.count() == 4
    assert widget.list.currentRow() == 1


def test_file_assoc_widget(file_assoc_widget):
    qtbot, widget = file_assoc_widget
    qtbot.wait(4000)

    # Test add associations

    # Test remove associations

    # Test edit associations

    # Test add application

    # Test remove application

    # Test set default
