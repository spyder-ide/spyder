# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for the main window
"""

import pytest
from qtpy.QtCore import Qt

from spyder.app.cli_options import get_options
from spyder.app.mainwindow import initialize, run_spyder


@pytest.fixture
def main_window():
    app = initialize()
    options, args = get_options()
    widget = run_spyder(app, options, args)
    return widget


def test_issue_4066(main_window, qtbot):
    """
    Test for a segfault when these steps are followed:

    1. Open an object present in the Variable Explorer (e.g. a list).
    2. Delete that object in its corresponding console while its
       editor is still opem.
    3. Closing that editor by pressing its *Ok* button.
    """
    # Create the object
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=6000)
    shell.execute('myobj = [1, 2, 3]')

    # Open editor associated with that object and get a reference to it
    nsb = main_window.variableexplorer.get_focus_widget()
    qtbot.waitUntil(lambda: nsb.editor.model.rowCount() > 0, timeout=500)
    nsb.editor.setFocus()
    nsb.editor.edit_item()
    obj_editor_id = list(nsb.editor.delegate._editors.keys())[0]
    obj_editor = nsb.editor.delegate._editors[obj_editor_id]['editor']

    # Move to the IPython console and delete that object
    main_window.ipyconsole.get_focus_widget().setFocus()
    shell.execute('del myobj')
    qtbot.waitUntil(lambda: nsb.editor.model.rowCount() == 0, timeout=500)

    # Close editor
    ok_widget = obj_editor.bbox.button(obj_editor.bbox.Ok)
    qtbot. mouseClick(ok_widget, Qt.LeftButton)


if __name__ == "__main__":
    pytest.main()
