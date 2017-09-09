# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""Tests for snippets.py"""

import pytest
import os

from spyder.utils.snippets import Snippet, SnippetManager

snippet_test = """
[test_snippet]
    prefix = 'test'
    language = 'python'
    content = '''
for i in range(${1:repetitions}):
    ${2:pass}
'''
"""

snippet_test_result = "for i in range(repetitions):\n    pass"

bad_snippet = """
[test_snippet]
    prefix = 'test2'
    language = 'python'
"""


@pytest.fixture
def snippets_dir(tmpdir_factory):
    """
    Fixture for create a temporary snippet file.

    Returns:
        str: Path of temporary snippet file.
    """
    dir_ = tmpdir_factory.mktemp('snippets')
    for fname, text in [["test_snippet.toml", snippet_test],
                        ["bad_snippet.toml", bad_snippet]]:
        snippet_file = dir_.join(fname)
        snippet_file.write(text)
    return str(dir_)


@pytest.fixture
def snippet_manager(snippets_dir, monkeypatch):
    """
    Fixture for SnippetManager.

    Load with a tmp configuration path, and a test snippet.
    """
    monkeypatch.setattr('spyder.utils.snippets.get_conf_path',
                        lambda *args: snippets_dir)

    return SnippetManager()


def test_snippet():
    """Test Snippet class"""
    content = ('class ${1:SomeClass}():\n' '    ${2:pass}')
    snippet = Snippet('test',
                      language="python",
                      prefix='test',
                      content=content)

    assert snippet.text == "class SomeClass():\n    pass"

    assert list(snippet.variables_position) == [(6, 9), (23, 4)]


def test_snippets_manager(snippet_manager):
    """Test SnippetManager, loading an searching an snippet."""
    assert snippet_manager.search_snippet("not_exist") is None

    test_snippet = snippet_manager.search_snippet("test")
    assert isinstance(test_snippet, Snippet)
    assert test_snippet.language == 'python'


def test_save_snippet(snippet_manager):
    """Test loading and re-saving a snippet."""
    test_snippet = snippet_manager.search_snippet("test")
    snippet_manager.save_snippet(test_snippet, "copy_snippet.toml")

    fcopy = os.path.join(snippet_manager.path, "copy_snippet.toml")
    snippet_copy = snippet_manager.load_snippet_file(fcopy)['test']
    assert snippet_copy == test_snippet


if __name__ == '__main__':
    pytest.main()
