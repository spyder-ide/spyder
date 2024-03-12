# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Testing utilities for the CodeEditor to be used with pytest.
"""

# Standard library imports
import os
import os.path as osp
from unittest.mock import Mock

# Third party imports
import pytest
from qtpy.QtGui import QFont
from qtpy.QtCore import QMimeData, QUrl
from qtpy.QtWidgets import QApplication

# Local imports
from spyder.config.manager import CONF
from spyder.plugins.completion.tests.conftest import (
    completion_plugin_all,
    completion_plugin_all_started,
    MainWindowMock,
    qtbot_module
)
from spyder.plugins.editor.widgets.codeeditor import CodeEditor
from spyder.plugins.explorer.widgets.tests.conftest import create_folders_files
from spyder.plugins.outlineexplorer.editor import OutlineExplorerProxyEditor
from spyder.plugins.outlineexplorer.main_widget import OutlineExplorerWidget
from spyder.utils.programs import is_module_installed
from spyder.widgets.findreplace import FindReplace


# ---- Base constants for assets
HERE = osp.dirname(osp.abspath(__file__))
ASSETS = osp.join(HERE, 'assets')

# ---- Constants for outline related test
AVAILABLE_CASES = ['text']
CASES = {
    case: {
        'file': osp.join(ASSETS, '{0}.py'.format(case)),
        'tree': osp.join(ASSETS, '{0}_trees.json'.format(case))
    }
    for case in AVAILABLE_CASES
}

# ---- Auxiliary constants and functions for formatting tests
autopep8 = pytest.param(
    'autopep8',
    marks=pytest.mark.skipif(
        os.name == 'nt',
        reason='autopep8 produces a different output on Windows'
    )
)

yapf = pytest.param(
    'yapf',
    marks=pytest.mark.skipif(
        is_module_installed('yapf', '<0.32.0'),
        reason='Versions older than 0.32 produce different outputs'
    )
)

black = pytest.param(
    'black',
    marks=pytest.mark.skipif(
        is_module_installed('python-lsp-black', '<2.0.0'),
        reason='Versions older than 2.0 use a different entrypoint name'
    )
)


def get_formatter_values(formatter, newline, range_fmt=False, max_line=False):
    if range_fmt:
        suffix = 'range'
    elif max_line:
        suffix = 'max_line'
    else:
        suffix = 'result'

    original_file = osp.join(ASSETS, 'original_file.py')
    formatted_file = osp.join(ASSETS, '{0}_{1}.py'.format(formatter, suffix))

    with open(original_file, 'r') as f:
        text = f.read()
    text = text.replace('\n', newline)

    with open(formatted_file, 'r') as f:
        result = f.read()
    result = result.replace('\n', newline)

    return text, result


# ---- Fixtures for outline functionality
@pytest.fixture
def outlineexplorer(qtbot):
    """Set up an OutlineExplorerWidget."""
    outlineexplorer = OutlineExplorerWidget(None, None, None)
    outlineexplorer.set_conf('show_fullpath', False)
    outlineexplorer.set_conf('show_all_files', True)
    outlineexplorer.set_conf('group_cells', True)
    outlineexplorer.set_conf('show_comments', True)
    outlineexplorer.set_conf('sort_files_alphabetically', False)
    outlineexplorer.set_conf('display_variables', True)

    # Fix the size of the outline explorer to prevent an
    # 'Unable to set geometry ' warning if the test fails.
    outlineexplorer.setFixedSize(400, 350)

    qtbot.addWidget(outlineexplorer)
    outlineexplorer.show()

    return outlineexplorer


# ---- Fixtures for CodeEditor class
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
def completions_codeeditor_outline(completions_codeeditor, outlineexplorer):
    editor, _ = completions_codeeditor
    editor.oe_proxy = OutlineExplorerProxyEditor(editor, editor.filename)
    outlineexplorer.register_editor(editor.oe_proxy)
    outlineexplorer.set_current_editor(
        editor.oe_proxy, update=False, clear=False)
    return editor, outlineexplorer


# ---- Other fixtures
@pytest.fixture
def copy_files_clipboard(create_folders_files):
    """Fixture to copy files/folders into the clipboard"""
    file_paths = create_folders_files[0]
    file_content = QMimeData()
    file_content.setUrls([QUrl.fromLocalFile(fname) for fname in file_paths])
    cb = QApplication.clipboard()
    cb.setMimeData(file_content, mode=cb.Clipboard)
    return file_paths
