# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Testing utilities to be used with pytest.
"""

# Stdlib imports
import os
from unittest.mock import Mock

# Third party imports
import pytest
from qtpy.QtGui import QFont
from qtpy.QtCore import QMimeData, QUrl
from qtpy.QtWidgets import QApplication

# Local imports
from spyder.config.manager import CONF
from spyder.plugins.editor.tests.conftest import (
    editor_plugin, editor_plugin_open_files, python_files)
from spyder.plugins.completion.tests.conftest import (
    qtbot_module, MainWindowMock, completion_plugin_all_started,
    completion_plugin_all)
from spyder.plugins.editor.widgets.codeeditor import CodeEditor
from spyder.plugins.editor.widgets.editor import EditorStack
from spyder.plugins.explorer.widgets.tests.conftest import create_folders_files
from spyder.py3compat import to_text_string
from spyder.widgets.findreplace import FindReplace


def codeeditor_factory():
    editor = CodeEditor(parent=None)
    editor.setup_editor(language='Python',
                        tab_mode=False,
                        markers=True,
                        close_quotes=True,
                        close_parentheses=True,
                        color_scheme='spyder/dark',
                        font=QFont("Monospace", 10),
                        automatic_completions=True,
                        automatic_completions_after_chars=1,
                        folding=False)
    editor.eol_chars = '\n'
    editor.resize(640, 480)
    return editor


def editor_factory(new_file=True, text=None):
    editorstack = EditorStack(None, [])
    editorstack.set_find_widget(FindReplace(editorstack))
    editorstack.set_io_actions(Mock(), Mock(), Mock(), Mock())
    if new_file:
        if not text:
            text = ('a = 1\n'
                    'print(a)\n'
                    '\n'
                    'x = 2')  # a newline is added at end
        finfo = editorstack.new('foo.py', 'utf-8', text)
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
        completion_plugin_all_started, qtbot_module, request, capsys,
        tmp_path):
    """Editorstack instance with LSP services activated."""
    # Create a CodeEditor instance
    editorstack, editor = editor_factory(new_file=False)
    qtbot_module.addWidget(editorstack)

    completion_plugin, capabilities = completion_plugin_all_started
    completion_plugin.wait_for_ms = 2000

    CONF.set('completions', 'enable_code_snippets', False)
    completion_plugin.after_configuration_update([])
    CONF.notify_section_all_observers('completions')

    file_path = tmp_path / 'test.py'
    editor = editorstack.new(str(file_path), 'utf-8', '').editor
    # Redirect editor LSP requests to lsp_manager
    editor.sig_perform_completion_request.connect(
        completion_plugin.send_request)

    completion_plugin.register_file('python', str(file_path), editor)
    editor.register_completion_capabilities(capabilities)

    with qtbot_module.waitSignal(
            editor.completions_response_signal, timeout=30000):
        editor.start_completion_services()

    def teardown():
        editor.completion_widget.hide()
        editor.tooltip_widget.hide()
        editor.hide()

        # Capture stderr and assert there are no errors
        sys_stream = capsys.readouterr()
        sys_err = sys_stream.err
        assert sys_err == ''

    request.addfinalizer(teardown)

    editorstack.show()

    return file_path, editorstack, editor, completion_plugin


@pytest.fixture
def kite_codeeditor(qtbot_module, request):
    """
    CodeEditor instance with Kite enabled.

    NOTE: This fixture only works if used with kite installed.
    If running in the CI, the installation of Kite could be accomplished by
    spyder/plugins/completion/kite/utils/tests/test_install.py::test_kite_install

    Any test running with this fixture should run after the installation
    test mentioned above.
    """
    main = MainWindowWidgetMock()
    completions = CompletionManager(main, ['kite'])
    completions.start()
    completions.start_client('python')
    completions.language_status['python']['kite'] = True
    qtbot_module.addWidget(completions)

    # Create a CodeEditor instance
    editor = codeeditor_factory()
    qtbot_module.addWidget(editor)
    editor.show()

    # Redirect editor fallback requests to FallbackActor
    editor.sig_perform_completion_request.connect(completions.send_request)
    editor.filename = 'test.py'
    editor.language = 'Python'
    editor.completions_available = True
    qtbot_module.wait(2000)

    def teardown():
        completions.shutdown()
        editor.hide()
        editor.completion_widget.hide()

    request.addfinalizer(teardown)
    kite = completions.get_client('kite')
    CONF.set('kite', 'show_installation_dialog', False)
    CONF.set('kite', 'show_onboarding', False)
    CONF.set('kite', 'call_to_action', False)
    kite.update_configuration()
    return editor, kite


@pytest.fixture
def mock_completions_codeeditor(qtbot_module, request):
    """CodeEditor instance with ability to mock the completions response.

    Returns a tuple of (editor, mock_response). Tests using this fixture should
    set `mock_response.side_effect = lambda lang, method, params: {}`.
    """
    # Create a CodeEditor instance
    editor = codeeditor_factory()
    qtbot_module.addWidget(editor)
    editor.show()

    mock_response = Mock()

    def perform_request(lang, method, params):
        resp = mock_response(lang, method, params)
        print("DEBUG {}".format(resp))
        if resp is not None:
            editor.handle_response(method, resp)
    editor.sig_perform_completion_request.connect(perform_request)

    editor.filename = 'test.py'
    editor.language = 'Python'
    editor.completions_available = True
    qtbot_module.wait(2000)

    def teardown():
        editor.hide()
        editor.completion_widget.hide()
    request.addfinalizer(teardown)

    return editor, mock_response


@pytest.fixture
def completions_codeeditor(completion_plugin_all_started, qtbot_module,
                           request, capsys, tmp_path):
    """CodeEditor instance with LSP services activated."""
    # Create a CodeEditor instance
    editor = codeeditor_factory()
    qtbot_module.addWidget(editor)

    completion_plugin, capabilities = completion_plugin_all_started
    completion_plugin.wait_for_ms = 2000

    CONF.set('completions', 'enable_code_snippets', False)
    completion_plugin.after_configuration_update([])
    CONF.notify_section_all_observers('completions')

    # Redirect editor LSP requests to lsp_manager
    editor.sig_perform_completion_request.connect(
        completion_plugin.send_request)

    file_path = tmp_path / 'test.py'
    file_path.write_text('')

    editor.filename = str(file_path)
    editor.language = 'Python'

    completion_plugin.register_file('python', str(file_path), editor)
    editor.register_completion_capabilities(capabilities)

    with qtbot_module.waitSignal(
            editor.completions_response_signal, timeout=30000):
        editor.start_completion_services()

    def teardown():
        editor.completion_widget.hide()
        editor.tooltip_widget.hide()
        editor.hide()

        # Capture stderr and assert there are no errors
        sys_stream = capsys.readouterr()
        sys_err = sys_stream.err

        assert sys_err == ''

    request.addfinalizer(teardown)

    editor.show()

    return editor, completion_plugin


@pytest.fixture
def search_codeeditor(completions_codeeditor, qtbot_module, request):
    code_editor, _ = completions_codeeditor
    find_replace = FindReplace(code_editor, enable_replace=True)
    find_replace.set_editor(code_editor)
    qtbot_module.addWidget(find_replace)

    def teardown():
        find_replace.hide()

    request.addfinalizer(teardown)

    return code_editor, find_replace


@pytest.fixture
def codeeditor(qtbot):
    widget = CodeEditor(None)
    widget.setup_editor(linenumbers=True,
                        markers=True,
                        tab_mode=False,
                        font=QFont("Courier New", 10),
                        show_blanks=True, color_scheme='spyder/dark',
                        scroll_past_end=True)
    widget.setup_editor(language='Python')
    widget.resize(640, 480)
    widget.show()
    yield widget
    widget.close()


@pytest.fixture
def copy_files_clipboard(create_folders_files):
    """Fixture to copy files/folders into the clipboard"""
    file_paths = create_folders_files[0]
    file_content = QMimeData()
    file_content.setUrls([QUrl.fromLocalFile(fname) for fname in file_paths])
    cb = QApplication.clipboard()
    cb.setMimeData(file_content, mode=cb.Clipboard)
    return file_paths
