# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""Native Editor fixture and an independently docked secondary pane."""
import pytest
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QDockWidget

from spyder.config.manager import CONF
from spyder.plugins.editor.tests.conftest import editor_plugin  # noqa: F401

@pytest.fixture
def reference(editor_plugin, qtbot):  # noqa: F811
    from spyder.plugins.referenceeditor.plugin import ReferenceEditor
    plugin = ReferenceEditor(editor_plugin.main, CONF)
    plugin.on_initialize()
    pane = plugin.get_widget()
    pane.set_conf('layout_settings', None)
    pane.set_editor_manager(editor_plugin.get_widget())
    dock = QDockWidget('Secondary editor', editor_plugin.main)
    dock.setWidget(pane)
    editor_plugin.main.addDockWidget(Qt.RightDockWidgetArea, dock)
    qtbot.addWidget(dock)
    yield pane
    pane.on_close()
