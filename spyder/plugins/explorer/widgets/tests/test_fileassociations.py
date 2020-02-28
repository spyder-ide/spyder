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
from qtpy.QtCore import Qt, QTimer
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


def test_apps_dialog(qtbot, tmp_path):
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
    if os.name == 'nt':
        path_obj = tmp_path / ("some-new-app" + ext)
        path_obj.write_bytes(b'\x00\x00')
        fpath = str(path_obj)
    elif sys.platform == 'darwin':
        path_obj = tmp_path / ("some-new-app" + ext)
        path_obj.mkdir()
        fpath = str(path_obj)
    else:
        path_obj = tmp_path / ("some-new-app" + ext)
        path_obj.write_text(u'''
[Desktop Entry]
Name=Suer app
Type=Application
Exec=/something/bleerp
Icon=/blah/blah.xpm
''')
        fpath = str(path_obj)

    widget.browse(fpath)
    assert widget.list.count() == 4

    # Test browse valid duplicate
    widget.browse(fpath)
    assert widget.list.count() == 4


def create_timer(func, interval=500):
    """Helper function to help interact with modal dialogs."""
    timer = QTimer()
    timer.setInterval(interval)
    timer.setSingleShot(True)
    timer.timeout.connect(func)
    timer.start()
    return timer


def test_file_assoc_widget(file_assoc_widget):
    qtbot, widget = file_assoc_widget

    # Test data
    assert widget.data == widget.test_data

    # Test add invalid associations
    extension = 'blooper.foo,'

    def interact_with_dialog_1():
        qtbot.keyClicks(widget._dlg_input.lineedit, extension)
        assert widget._dlg_input.lineedit.text() == extension
        assert not widget._dlg_input.button_ok.isEnabled()
        qtbot.keyClick(widget._dlg_input.button_cancel, Qt.Key_Return)

    _ = create_timer(interact_with_dialog_1)
    qtbot.mouseClick(widget.button_add, Qt.LeftButton)

    # Test add valid association
    extension = '*.zpam,MANIFEST.in'

    def interact_with_dialog_2():
        qtbot.keyClicks(widget._dlg_input.lineedit, extension)
        qtbot.keyClick(widget._dlg_input.button_ok, Qt.Key_Return)

    _ = create_timer(interact_with_dialog_2)
    qtbot.mouseClick(widget.button_add, Qt.LeftButton)
    assert widget.list_extensions.count() == 3
    assert widget.list_extensions.item(2).text() == extension

    # Test add invalid association programmatically
    widget.add_association(value='mehh')
    assert widget.list_extensions.count() == 3

    # Test add valid association programmatically
    widget.add_association(value='*.boom')
    assert widget.list_extensions.count() == 4

    # Test add repeated association programmatically
    widget.add_association(value='*.csv')
    assert widget.list_extensions.count() == 4
    widget._add_association(value='*.csv')
    assert widget.list_extensions.count() == 4

    # Test edit association
    extension = '*.zpam'

    def interact_with_dialog_3():
        widget._dlg_input.lineedit.clear()
        qtbot.keyClicks(widget._dlg_input.lineedit, extension)
        qtbot.keyClick(widget._dlg_input.button_ok, Qt.Key_Return)

    _ = create_timer(interact_with_dialog_3)
    qtbot.mouseClick(widget.button_edit, Qt.LeftButton)
    assert widget.list_extensions.count() == 4
    assert widget.list_extensions.item(2).text() == extension

    # Test remove associations
    qtbot.mouseClick(widget.button_remove, Qt.LeftButton)
    assert widget.list_extensions.count() == 3

    # Test set default
    widget.list_applications.setCurrentRow(1)
    qtbot.mouseClick(widget.button_default, Qt.LeftButton)
    assert 'App name 2' in widget.list_applications.item(0).text()

    # Test add application
    def interact_with_dialog_4():
        assert not widget._dlg_applications.button_ok.isEnabled()
        count = widget._dlg_applications.list.count()
        if count > 0:
            widget._dlg_applications.list.setCurrentRow(count - 1)
            qtbot.keyClick(widget._dlg_applications.button_ok, Qt.Key_Return)
        else:
            qtbot.keyClick(widget._dlg_applications.button_cancel,
                           Qt.Key_Return)

    _ = create_timer(interact_with_dialog_4)
    qtbot.mouseClick(widget.button_add_application, Qt.LeftButton)
    count = widget.list_applications.count()
    assert count in [2, 3]

    # Test add repeated application programmatically
    app_name, app_path = widget.test_data['*.csv'][0]
    widget._add_application(app_name, app_path)
    count = widget.list_applications.count()
    assert count in [2, 3]

    # Test remove application
    widget.list_applications.setCurrentRow(0)
    qtbot.mouseClick(widget.button_remove_application, Qt.LeftButton)
    count = widget.list_applications.count()
    assert count in [1, 2]
    assert 'App name 1' in widget.list_applications.item(0).text()
