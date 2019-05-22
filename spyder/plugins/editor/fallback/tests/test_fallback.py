# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

import json
import os.path as osp

try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock  # Python 2

import pytest
from qtpy.QtCore import QObject, Signal
from diff_match_patch import diff_match_patch

from spyder.plugins.editor.fallback.actor import FallbackActor

DATA_PATH = osp.join(osp.dirname(osp.abspath(__file__)), "data")
TOKENS_FILE = osp.join(DATA_PATH, 'tokens.json')

language_list = ['c', 'cpp', 'css', 'erl', 'ex', 'html', 'java', 'jl',
                 'md', 'py', 'R']
extension_map = {
    'c': 'C', 'cpp': 'C++', 'css': 'CSS', 'erl': 'Erlang', 'ex': "Elixir",
    'html': 'HTML', 'java': 'Java', 'jl': 'Julia', 'md': 'Markdown',
    'py': 'Python', 'R': 'R'
}


class CodeEditorMock(QObject):
    sig_recv_tokens = Signal(list)

    def recieve_text_tokens(self, tokens):
        self.sig_recv_tokens.emit(tokens)


@pytest.fixture
def tokens_fixture():
    with open(TOKENS_FILE, 'r') as f:
        tokens = json.load(f)
    return tokens


@pytest.fixture
def file_fixture(tokens_fixture, request):
    ext = request.param
    filename = 'example.{0}'.format(ext)
    example_file = osp.join(DATA_PATH, filename)
    with open(example_file) as f:
        contents = f.read()
    return filename, set(tokens_fixture[filename]), contents


@pytest.fixture(scope="module")
def fallback_fixture(qtbot_module, request):
    fallback = FallbackActor(None)
    diff_match = diff_match_patch()
    editor = CodeEditorMock()
    qtbot_module.addWidget(editor)
    qtbot_module.addWidget(fallback)

    with qtbot_module.waitSignal(fallback.sig_fallback_ready, timeout=30000):
        fallback.start()

    def teardown():
        fallback.stop()

    request.addfinalizer(teardown)
    return fallback, editor, diff_match


def test_file_open_close(qtbot_module, fallback_fixture):
    fallback, editor, diff_match = fallback_fixture
    test_file = """
    # This is a test file
    a = 2
    """
    diff = diff_match.patch_make('', test_file)
    open_request = {
        'file': 'test.py',
        'type': 'update',
        'editor': editor,
        'msg': {
            'language': 'python',
            'diff': diff
        }
    }

    fallback.mailbox.put(open_request)
    qtbot_module.wait(1000)
    assert 'test.py' in fallback.file_tokens

    close_request = {
        'file': 'test.py',
        'type': 'close',
        'editor': editor,
        'msg': {}
    }
    fallback.mailbox.put(close_request)
    qtbot_module.wait(1000)
    assert 'test.py' not in fallback.file_tokens


@pytest.mark.parametrize('file_fixture', language_list, indirect=True)
def test_tokenize(qtbot_module, fallback_fixture, file_fixture):
    filename, expected_tokens, contents = file_fixture
    _, ext = osp.splitext(filename)
    print(filename)
    print(expected_tokens)
    fallback, editor, diff_match = fallback_fixture
    diff = diff_match.patch_make('', contents)
    open_request = {
        'file': filename,
        'type': 'update',
        'editor': editor,
        'msg': {
            'language': extension_map[ext[1:]],
            'diff': diff
        }
    }
    fallback.mailbox.put(open_request)
    qtbot_module.wait(1000)
    tokens_request = {
        'file': filename,
        'type': 'retrieve',
        'editor': editor,
        'msg': None
    }
    with qtbot_module.waitSignal(editor.sig_recv_tokens,
                                 timeout=3000) as blocker:
        fallback.mailbox.put(tokens_request)
    tokens = blocker.args
    tokens = {token['insertText'] for token in tokens[0]}
    print(expected_tokens - tokens)
    assert len(tokens | expected_tokens) == len(tokens)
