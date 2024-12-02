# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Testing utilities for Editor/EditorStack widgets to be used with pytest.
"""

# Stdlib imports
from unittest.mock import Mock

# Third party imports
import pytest

# Local imports
from spyder.config.manager import CONF
from spyder.plugins.editor.tests.conftest import (
    editor_plugin,
    editor_plugin_open_files,
    python_files,
)
from spyder.plugins.completion.tests.conftest import (
    qtbot_module,
    completion_plugin_all_started,
    completion_plugin_all,
)
from spyder.plugins.editor.widgets.editorstack import EditorStack
from spyder.plugins.editor.widgets.codeeditor.tests.conftest import (
    outlineexplorer,
)
from spyder.widgets.findreplace import FindReplace


def editor_factory(new_file=True, text=None):
    editorstack = EditorStack(None, [], False)
    editorstack.set_find_widget(FindReplace(editorstack))
    editorstack.set_io_actions(Mock(), Mock(), Mock(), Mock())
    if new_file:
        if not text:
            text = (
                "a = 1\n" "print(a)\n" "\n" "x = 2"
            )  # a newline is added at end
        finfo = editorstack.new("foo.py", "utf-8", text)
        return editorstack, finfo.editor
    return editorstack, None


@pytest.fixture
def setup_editor(qtbot):
    """
    Set up EditorStack with CodeEditor containing some Python code.
    The cursor is at the empty line below the code.
    Returns tuple with EditorStack and CodeEditor.
    """
    editorstack, code_editor = editor_factory()
    qtbot.addWidget(editorstack)
    return editorstack, code_editor


@pytest.fixture
def completions_editor(
    completion_plugin_all_started, qtbot_module, request, capsys, tmp_path
):
    """Editorstack instance with LSP services activated."""
    # Create a CodeEditor instance
    editorstack, editor = editor_factory(new_file=False)
    qtbot_module.addWidget(editorstack)

    completion_plugin, capabilities = completion_plugin_all_started
    completion_plugin.wait_for_ms = 2000

    CONF.set("completions", "enable_code_snippets", False)
    completion_plugin.after_configuration_update([])
    CONF.notify_section_all_observers("completions")

    file_path = tmp_path / "test.py"
    editor = editorstack.new(str(file_path), "utf-8", "").editor
    # Redirect editor LSP requests to lsp_manager
    editor.sig_perform_completion_request.connect(
        completion_plugin.send_request
    )

    completion_plugin.register_file("python", str(file_path), editor)
    editor.register_completion_capabilities(capabilities)

    with qtbot_module.waitSignal(
        editor.completions_response_signal, timeout=30000
    ):
        editor.start_completion_services()

    def teardown():
        editor.completion_widget.hide()
        editor.tooltip_widget.hide()
        editor.hide()

        # Capture stderr and assert there are no errors
        sys_stream = capsys.readouterr()
        sys_err = sys_stream.err
        assert sys_err == ""

        editorstack.close()

    request.addfinalizer(teardown)

    editorstack.show()

    return file_path, editorstack, editor, completion_plugin
