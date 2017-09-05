# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""Tests for snippets.py"""

import pytest
import os

from spyder.utils.snippets import Snippet, SnippetManager

snippet_text = """
[test_snippet]
    prefix = 'test'
    language = 'python'
    content = '''
for i in range(${1:repetitions}):
    ${2:pass}
'''
"""

snippet_result = "for i in range(repetitions):\n    pass"

@pytest.fixture
def snippet_file(tmpdir_factory):
    """
    Fixture for create a temporary snippet file.

    Returns:
        str: Path of temporary snippet file.
    """
    snippet_file = tmpdir_factory.mktemp('snippets').join("test_snippet.toml")
    snippet_file.write(snippet_text)
    return str(snippet_file)


@pytest.fixture
def snippet_manager(snippet_file, monkeypatch):
    """
    Fixture for SnippetManager.

    Load with a tmp configuration path, and a test snippet.
    """
    dirname = os.path.dirname(snippet_file)
    monkeypatch.setattr('spyder.utils.snippets.get_conf_path',
                        lambda *args: dirname)

    return SnippetManager()


def test_snippet():
    """Test Snippet class"""
    content = ('class ${1:SomeClass}():\n' '    ${2:pass}')
    snippet = Snippet('test',
                      language="python",
                      prefix='test',
                      content=content)

    assert snippet.text() == "class SomeClass():\n    pass"

    assert list(snippet.variables_position()) == [(6, 9), (8, 4)]


def test_snippets_manager(snippet_manager):
    """Test SnnipetManager, loading an searching an snippet."""
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
