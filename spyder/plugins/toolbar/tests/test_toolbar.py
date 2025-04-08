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
        ApplicationToolbars.Main,
        ApplicationToolbars.WorkingDirectory,
    ]

    # Check the horizontal order obtained the displayed toolbar doesn't change
    # after sorting it.
    current_order = [
        toolbar.get_application_toolbar(id_).x()
        for id_ in expected_order
    ]
    assert current_order == sorted(current_order)


def test_restore_toolbars_order(toolbar, qtbot):
    """
    Check that if a toolbar is moved by users to a different position, then the
    new order is restored during the next startup.
    """
    new_order = [
        ApplicationToolbars.Debug,
        ApplicationToolbars.File,
        ApplicationToolbars.Run,
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

    # Check the list of available toolbars was saved to our config system
    assert toolbar.get_conf("last_toolbars")

    # Reload toolbars as if a new Spyder session was started
    toolbar.on_mainwindow_visible()
    qtbot.wait(500)

    # Check the order of displayed toolbars is the expected one
    current_order = [
        toolbar.get_application_toolbar(id_).pos().x()
        for id_ in new_order
    ]
    assert current_order == sorted(current_order)


def test_reorder_toolbars(toolbar, qtbot):
    """
    Check that if a toolbar is removed, then toolbars are reordered the next
    time with the working directory being shown to the right.
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

    # Simulate that a toolbar was present in the last sesstion and then removed
    last_toolbars = toolbar.get_conf("last_toolbars")
    toolbar.set_conf("last_toolbars", last_toolbars + ["foo_toolbar"])

    # Reload toolbars as if a new Spyder session was started
    toolbar.on_mainwindow_visible()

    # Check the working directory toolbar is to the right of the rest
    current_order = [app_toolbar.x() for app_toolbar in toolbar.toolbarslist]
    assert all([cwd_toolbar.x() >= pos for pos in current_order])
