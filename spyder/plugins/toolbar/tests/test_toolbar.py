# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

from unittest.mock import MagicMock

from qtpy.QtWidgets import QMainWindow
import pytest

from spyder.config.manager import CONF
from spyder.plugins.toolbar.api import ApplicationToolbars
from spyder.plugins.toolbar.plugin import Toolbar
from spyder.plugins.workingdirectory.plugin import WorkingDirectory


class MainWindow(QMainWindow):

    _cli_options = MagicMock()

    def get_plugin(self, name, error=True):
        return MagicMock()


@pytest.fixture
def toolbar(qtbot):
    # Create toolbar plugin
    main_window = MainWindow()
    toolbar = Toolbar(main_window, configuration=CONF)
    toolbar.on_initialize()

    # Add working directory toolbar
    cwd = WorkingDirectory(main_window, None)
    cwd.on_initialize()
    toolbar.add_application_toolbar(cwd.get_container().toolbar)

    # Add buttons to the other toolbars
    actions = [
        (ApplicationToolbars.File, "filenew"),
        (ApplicationToolbars.Run, "run"),
        (ApplicationToolbars.Debug, "debug"),
        (ApplicationToolbars.ControlDebugger, "arrow-step-over"),
        (ApplicationToolbars.Main, "python"),
    ]

    for i, item in enumerate(actions):
        toolbar.create_action(
            f"action_{i}",
            text="Action {i}",
            icon=toolbar.create_icon(item[1]),
            triggered=lambda: True,
        )

        toolbar.add_item_to_application_toolbar(
            toolbar.get_action(f"action_{i}"),
            toolbar_id=item[0],
        )

    # Show toolbars and main window
    toolbar.on_mainwindow_visible()
    toolbar.toggle_lock(True)
    main_window.show()
    return toolbar


def test_default_order(toolbar):
    """Check toolbars are displayed in their default order."""
    expected_order = [
        ApplicationToolbars.File,
        ApplicationToolbars.Run,
        ApplicationToolbars.Debug,
        ApplicationToolbars.ControlDebugger,
        ApplicationToolbars.Main,
        ApplicationToolbars.WorkingDirectory,
    ]

    # Check the control debugger toolbar is hidden by default
    control_debugger = toolbar.get_application_toolbar(
        ApplicationToolbars.ControlDebugger
    )
    assert not control_debugger.isVisible()

    # Make control debugger visible so Qt can correctly get its x position
    control_debugger.setVisible(True)

    # Check the horizontal order obtained the displayed toolbar doesn't change
    # after sorting it.
    current_order = [
        toolbar.get_application_toolbar(id_).x()
        for id_ in expected_order
    ]
    assert current_order == sorted(current_order)


def test_restore_toolbar_order(toolbar, qtbot):
    """
    Check that if a toolbar is moved by users to a different position, then the
    new order is saved on close and restored during the next startup.
    """
    new_order = [
        ApplicationToolbars.Debug,
        ApplicationToolbars.File,
        ApplicationToolbars.Run,
        ApplicationToolbars.ControlDebugger,
        ApplicationToolbars.Main,
    ]

    # Select two toolbars to change their order
    file_toolbar = toolbar.get_application_toolbar(ApplicationToolbars.File)
    debug_toolbar = toolbar.get_application_toolbar(ApplicationToolbars.Debug)

    # Move the debug toolbar to be before the file one
    toolbar.get_main().insertToolBar(file_toolbar, debug_toolbar)
    qtbot.wait(500)
    assert debug_toolbar.x() < file_toolbar.x()

    # Close toolbar plugin (which is called when the main window is closed)
    toolbar.on_close(False)

    # Check the order was saved as expected to our config system
    assert toolbar.get_conf("toolbars_order") == new_order

    # Reload toolbars as if a new Spyder session was started
    toolbar.on_mainwindow_visible()
    qtbot.wait(500)

    # Check the order of displayed toolbars is the expected one
    current_order = [
        toolbar.get_application_toolbar(id_).pos().x()
        for id_ in new_order
    ]
    assert current_order == sorted(current_order)


def test_no_toolbar_after_working_directory(toolbar, qtbot):
    """
    Check that any toolbar that is placed to the right of the working directory
    is repositioned to its left during the next startup.
    """
    # Select the toolbars we are going to move
    cwd_toolbar = toolbar.get_application_toolbar(
        ApplicationToolbars.WorkingDirectory
    )
    debug_toolbar = toolbar.get_application_toolbar(ApplicationToolbars.Debug)

    # Move the working directory toolbar to be before the debug one
    toolbar.get_main().insertToolBar(debug_toolbar, cwd_toolbar)
    qtbot.wait(500)
    assert cwd_toolbar.x() < debug_toolbar.x()

    # Close toolbar plugin (which is called when the main window is closed)
    toolbar.on_close(False)
    qtbot.wait(500)

    # Reload toolbars as if a new Spyder session was started
    toolbar.on_mainwindow_visible()

    # Check the working directory toolbar is to the right of the rest
    current_order = [app_toolbar.x() for app_toolbar in toolbar.toolbarslist]
    assert all([cwd_toolbar.x() >= pos for pos in current_order])
