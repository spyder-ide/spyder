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
try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock # Python 2

# Third party imports
import pytest
from qtpy.QtGui import QFont

# Local imports
from spyder.config.manager import CONF
from spyder.plugins.editor.tests.conftest import (
    editor_plugin, editor_plugin_open_files, python_files)
from spyder.plugins.completion.languageserver.tests.conftest import (
    qtbot_module, MainWindowMock, MainWindowWidgetMock)
from spyder.plugins.editor.widgets.codeeditor import CodeEditor
from spyder.plugins.editor.widgets.editor import EditorStack
from spyder.plugins.completion.manager.plugin import CompletionManager
from spyder.plugins.explorer.widgets.tests.conftest import create_folders_files
from spyder.py3compat import PY2, to_text_string
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
                        automatic_completions_after_ms=200,
                        folding=False)
    editor.resize(640, 480)
    return editor


@pytest.fixture
def setup_editor(qtbot):
    """
    Set up EditorStack with CodeEditor containing some Python code.
    The cursor is at the empty line below the code.
    Returns tuple with EditorStack and CodeEditor.
    """
    text = ('a = 1\n'
            'print(a)\n'
            '\n'
            'x = 2')  # a newline is added at end
    editorStack = EditorStack(None, [])
    editorStack.set_find_widget(FindReplace(editorStack))
    editorStack.set_io_actions(Mock(), Mock(), Mock(), Mock())
    finfo = editorStack.new('foo.py', 'utf-8', text)
    qtbot.addWidget(editorStack)
    return editorStack, finfo.editor


@pytest.fixture
def fallback_codeeditor(qtbot_module, request):
    """CodeEditor instance with Fallback enabled."""

    completions = CompletionManager(None, ['fallback'])
    completions.start()
    completions.start_client('python')
    completions.language_status['python']['fallback'] = True
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
    fallback = completions.get_client('fallback')
    return editor, fallback


@pytest.fixture
def snippets_codeeditor(qtbot_module, request):
    """CodeEditor instance with text snippets enabled."""
    completions = CompletionManager(None, ['snippets'])
    completions.start()
    completions.start_client('python')
    completions.language_status['python']['snippets'] = True
    qtbot_module.addWidget(completions)

    # Create a CodeEditor instance
    editor = codeeditor_factory()
    qtbot_module.addWidget(editor)
    editor.show()

    # Redirect editor snippets requests to SnippetsActor
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
    snippets = completions.get_client('snippets')
    snippets.update_configuration()
    return editor, snippets


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


@pytest.fixture(scope='function')
def lsp_plugin(qtbot_module, request):
    # Activate pycodestyle and pydocstyle
    CONF.set('lsp-server', 'pycodestyle', True)
    CONF.set('lsp-server', 'pydocstyle', True)
    CONF.set('lsp-server', 'stdio', False)
    CONF.set('lsp-server', 'code_snippets', False)

    # Create the manager
    os.environ['SPY_TEST_USE_INTROSPECTION'] = 'True'

    main = MainWindowMock()
    completions = CompletionManager(main, ['lsp'])
    completions.start()
    with qtbot_module.waitSignal(
            main.editor.sig_lsp_initialized, timeout=30000):
        completions.start_client('python')
    completions.language_status['python']['lsp'] = True

    def teardown():
        completions.shutdown()
        os.environ['SPY_TEST_USE_INTROSPECTION'] = 'False'
        CONF.set('lsp-server', 'pycodestyle', False)
        CONF.set('lsp-server', 'pydocstyle', False)

    request.addfinalizer(teardown)
    return completions


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
def lsp_codeeditor(lsp_plugin, qtbot_module, request, capsys):
    """CodeEditor instance with LSP services activated."""
    # Create a CodeEditor instance
    editor = codeeditor_factory()
    qtbot_module.addWidget(editor)

    # Redirect editor LSP requests to lsp_manager
    editor.sig_perform_completion_request.connect(lsp_plugin.send_request)

    editor.filename = 'test.py'
    editor.language = 'Python'
    lsp_plugin.register_file('python', 'test.py', editor)
    capabilities = lsp_plugin.main.editor.completion_capabilities['python']
    editor.start_completion_services()
    editor.register_completion_capabilities(capabilities)

    with qtbot_module.waitSignal(editor.lsp_response_signal, timeout=30000):
        editor.document_did_open()

    def teardown():
        editor.completion_widget.hide()
        editor.tooltip_widget.hide()
        editor.hide()

        # Capture stderr and assert there are no errors
        sys_stream = capsys.readouterr()
        sys_err = sys_stream.err

        if PY2:
            sys_err = to_text_string(sys_err).encode('utf-8')
        assert sys_err == ''

    request.addfinalizer(teardown)
    lsp_plugin = lsp_plugin.get_client('lsp')

    editor.show()

    return editor, lsp_plugin


@pytest.fixture
def search_codeeditor(lsp_codeeditor, qtbot_module, request):
    code_editor, _ = lsp_codeeditor
    find_replace = FindReplace(None, enable_replace=True)
    find_replace.set_editor(code_editor)
    qtbot_module.addWidget(find_replace)

    def teardown():
        find_replace.hide()

    request.addfinalizer(teardown)

    return code_editor, find_replace
