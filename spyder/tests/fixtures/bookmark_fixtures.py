# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Fixtures to create editor and codeeditor.
"""

# Standard library imports
import os.path as osp
try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock  # Python 2

# Third party imports
import pytest
from qtpy.QtWidgets import QMainWindow

# Local imports
from spyder.utils.qthelpers import qapplication
from spyder.plugins.editor.widgets import editor
import spyder.plugins.editor.widgets.codeeditor as codeeditor


# -----------------------------------------------------------------------------
# --- Helper functions
# -----------------------------------------------------------------------------
def python_files(tmpdir_factory):
    """Create and save some python codes in temporary files."""
    tmpdir = tmpdir_factory.mktemp("files")
    tmpdir = osp.normcase(tmpdir.strpath)

    filenames = [osp.join(tmpdir, f) for f in
                 ('file1.py', 'file2.py', 'file3.py', 'file4.py')]
    for filename in filenames:
        with open(filename, 'w') as f:
            f.write("# -*- coding: utf-8 -*-\n"
                    "print(Hello World!)\n")

    return filenames, tmpdir


# -----------------------------------------------------------------------------
# --- Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture
def code_editor_bot(qtbot):
    """Create code editor with default Python code."""
    editor = codeeditor.CodeEditor(parent=None)
    indent_chars = ' ' * 4
    tab_stop_width_spaces = 4
    editor.setup_editor(language='Python', indent_chars=indent_chars,
                        tab_stop_width_spaces=tab_stop_width_spaces)
    # Mock the signal emit to test when it's been called.
    editor.sig_bookmarks_changed = Mock()
    text = ('def f1(a, b):\n'
            '"Double quote string."\n'
            '\n'  # Blank line.
            '    c = a * b\n'
            '    return c\n'
            )
    editor.set_text(text)
    return editor, qtbot


@pytest.fixture
def setup_editor(qtbot, monkeypatch, tmpdir_factory):
    """Set up the Editor plugin."""
    qapplication()
    from spyder.plugins.editor.plugin import Editor

    monkeypatch.setattr('spyder.plugins.editor.plugin.add_actions', Mock())

    class MainMock(QMainWindow):
        def __getattr__(self, attr):
            if attr.endswith('actions'):
                return []
            elif attr == 'projects':
                projects = Mock()
                projects.get_active_project.return_value = None
                return projects
            else:
                return Mock()

    window = MainMock()
    editor = Editor(window)

    expected_filenames, tmpdir = python_files(tmpdir_factory)

    def get_option(option, default=None):
        splitsettings = [(False,
                          osp.join(tmpdir, 'file1.py'),
                          [1, 1, 1, 1])]
        return {'layout_settings': {'splitsettings': splitsettings},
                'filenames': expected_filenames,
                'max_recent_files': 20
                }.get(option)
    editor.get_option = get_option

    editor.setup_open_files()
    window.setCentralWidget(editor)
    window.resize(640, 480)
    qtbot.addWidget(window)
    window.show()

    yield editor
