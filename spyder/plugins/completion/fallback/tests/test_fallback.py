# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

import json
import os.path as osp

import pytest
from diff_match_patch import diff_match_patch
from spyder.plugins.completion.languageserver import LSPRequestTypes
from spyder.plugins.completion.fallback.utils import get_words


DATA_PATH = osp.join(osp.dirname(osp.abspath(__file__)), "data")
TOKENS_FILE = osp.join(DATA_PATH, 'tokens.json')

language_list = ['c', 'cpp', 'css', 'erl', 'ex', 'html', 'java', 'jl',
                 'md', 'py', 'R']
extension_map = {
    'c': 'C', 'cpp': 'C++', 'css': 'CSS', 'erl': 'Erlang', 'ex': "Elixir",
    'html': 'HTML', 'java': 'Java', 'jl': 'Julia', 'md': 'Markdown',
    'py': 'Python', 'R': 'R'
}

TEST_FILE = """
# This is a test file
a = 2
"""

TEST_FILE_UPDATE = """
# This is a test file
a = 2

def func(args):
    pass
"""


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
def fallback_fixture(fallback_completions, qtbot_module, request):
    fallback, completions = fallback_completions
    diff_match = diff_match_patch()
    return fallback, completions, diff_match


@pytest.mark.slow
def test_file_open_close(qtbot_module, fallback_fixture):
    fallback, completions, diff_match = fallback_fixture

    open_request = {
        'file': 'test.py',
        'text': TEST_FILE,
        'offset': -1,
    }
    fallback.send_request(
        'python', LSPRequestTypes.DOCUMENT_DID_OPEN, open_request)
    qtbot_module.wait(1000)
    assert 'test.py' in fallback.fallback_actor.file_tokens

    close_request = {
        'file': 'test.py',
    }
    fallback.send_request(
        'python', LSPRequestTypes.DOCUMENT_DID_CLOSE, close_request)
    qtbot_module.wait(1000)
    assert 'test.py' not in fallback.fallback_actor.file_tokens


def test_get_words():
    source = 'foo bar123 baz car456'
    tokens = get_words(source, 5, 'python')
    assert set(tokens) == {'foo', 'baz', 'car456'}


@pytest.mark.slow
@pytest.mark.parametrize('file_fixture', language_list, indirect=True)
def test_tokenize(qtbot_module, fallback_fixture, file_fixture):
    filename, expected_tokens, contents = file_fixture
    _, ext = osp.splitext(filename)
    language = extension_map[ext[1:]]
    fallback, completions, diff_match = fallback_fixture
    # diff = diff_match.patch_make('', contents)
    open_request = {
        'file': filename,
        'text': contents,
        'offset': -1,
    }
    fallback.send_request(
        language, LSPRequestTypes.DOCUMENT_DID_OPEN, open_request)
    qtbot_module.wait(1000)

    tokens_request = {
        'file': filename
    }
    with qtbot_module.waitSignal(completions.sig_recv_tokens,
                                 timeout=3000) as blocker:
        fallback.send_request(
            language, LSPRequestTypes.DOCUMENT_COMPLETION, tokens_request)
    tokens = blocker.args
    tokens = {token['insertText'] for token in tokens[0]}
    assert len(expected_tokens - tokens) == 0


@pytest.mark.slow
def test_token_update(qtbot_module, fallback_fixture):
    fallback, completions, diff_match = fallback_fixture

    # diff = diff_match.patch_make('', TEST_FILE)
    open_request = {
        'file': 'test.py',
        'text': TEST_FILE,
        'offset': -1,
    }
    fallback.send_request(
        'python', LSPRequestTypes.DOCUMENT_DID_OPEN, open_request)
    qtbot_module.wait(1000)

    tokens_request = {
        'file': 'test.py',
    }
    with qtbot_module.waitSignal(completions.sig_recv_tokens,
                                 timeout=3000) as blocker:
        fallback.send_request(
            'python', LSPRequestTypes.DOCUMENT_COMPLETION, tokens_request)
    initial_tokens = blocker.args[0]
    initial_tokens = {token['insertText'] for token in initial_tokens}
    assert 'args' not in initial_tokens

    diff = diff_match.patch_make(TEST_FILE, TEST_FILE_UPDATE)
    update_request = {
        'file': 'test.py',
        'diff': diff,
        'offset': -1,
    }
    fallback.send_request(
        'python', LSPRequestTypes.DOCUMENT_DID_CHANGE, update_request)
    qtbot_module.wait(1000)
    with qtbot_module.waitSignal(completions.sig_recv_tokens,
                                 timeout=3000) as blocker:
        fallback.send_request(
            'python', LSPRequestTypes.DOCUMENT_COMPLETION, tokens_request)
    updated_tokens = blocker.args[0]
    updated_tokens = {token['insertText'] for token in updated_tokens}
    assert 'args' in updated_tokens
