# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""Fixtures for the Editor plugin tests."""

import os.path as osp
from unittest.mock import MagicMock, Mock

from qtpy.QtCore import QCoreApplication, Qt

from spyder.api.plugins import Plugins
from spyder.utils.qthelpers import qapplication

# This is needed to avoid an error because QtAwesome
# needs a QApplication to work correctly.
QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
app = qapplication()

from qtpy.QtWidgets import QMainWindow
import pytest

from spyder.config.manager import CONF
from spyder.plugins.editor.plugin import Editor


@pytest.fixture
def mock_RecoveryDialog(monkeypatch):
    """Mock the RecoveryDialog in the editor plugin."""
    mock = MagicMock()
    monkeypatch.setattr('spyder.plugins.editor.utils.autosave.RecoveryDialog',
                        mock)
    return mock


@pytest.fixture
def editor_plugin(qtbot, monkeypatch):
    """Set up the Editor plugin."""
    monkeypatch.setattr(
        'spyder.plugins.editor.widgets.main_widget.add_actions',
        Mock()
    )

    class MainMock(QMainWindow):
        def __getattr__(self, attr):
            if attr.endswith('actions'):
                return []
            else:
                return Mock()

        def get_plugin(self, plugin_name, error=True):
            if plugin_name in [
                    Plugins.IPythonConsole,
                    Plugins.Projects,
                    Plugins.Debugger]:
                return None
            else:
                return Mock()

    window = MainMock()
    configuration = CONF
    editor = Editor(window, configuration)
    editor.on_initialize()
    editor.update_font()  # Set initial font
    window.setCentralWidget(editor.get_widget())
    window.resize(640, 480)
    qtbot.addWidget(window)
    window.show()

    yield editor

    editor.on_close()
    CONF.remove_option('editor', 'autosave_mapping')


@pytest.fixture(scope="module")
def python_files(tmpdir_factory):
    """Create and save some python codes in temporary files."""
    tmpdir = tmpdir_factory.mktemp("files")
    tmpdir = osp.normcase(tmpdir.strpath)

    filenames = [osp.join(tmpdir, f) for f in
                 ('file1.py', 'file2.py', 'file3.py', 'file4.py',
                  'untitled4.py')]
    for filename in filenames:
        with open(filename, 'w', newline='') as f:
            f.write("# -*- coding: utf-8 -*-\n"
                    "print('Hello World!')\n")

    return filenames, tmpdir


@pytest.fixture
def editor_plugin_open_files(request, editor_plugin, python_files):
    """
    Setup an Editor with a set of open files, given a past file in focus.

    If no/None ``last_focused_filename`` is passed, the ``"layout_settings"``
    key is not included in the options dict.
    If no/None ``expected_current_filename``, is assumed to be the first file.
    """
    def _get_editor_open_files(last_focused_filename,
                               expected_current_filename):
        editor = editor_plugin
        expected_filenames, tmpdir = python_files

        if expected_current_filename is None:
            expected_current_filename = expected_filenames[0]
        expected_current_filename = osp.join(tmpdir, expected_current_filename)

        options_dict = {
            # For tests
            'filenames': expected_filenames,
            'max_recent_files': 20,
            # To make tests pass
            'indent_chars': '*    *',
            'show_tab_bar': True,
            'code_folding': True,
            'edge_line': True,
            'indent_guides': False,
            'scroll_past_end': False,
            'line_numbers': True,
            'occurrence_highlighting/timeout': 1500,
            'tab_stop_width_spaces': 4,
            'show_class_func_dropdown': False,
            'file_uuids': {},
            'bookmarks': {},
            # From help section:
            'connect/editor': False,
            # From completions:
            (
                'provider_configuration',
                'lsp',
                'values',
                'enable_hover_hints'
            ): True,
            (
                'provider_configuration',
                'lsp',
                'values',
                'format_on_save'
            ): False,
            (
                "provider_configuration",
                "lsp",
                "values",
                "pycodestyle/max_line_length",
            ): 79,
        }

        if last_focused_filename is not None:
            splitsettings = [(False,
                              osp.join(tmpdir, last_focused_filename),
                              [1] * len(expected_filenames))]
            layout_dict = {'layout_settings': {'splitsettings': splitsettings}}
            options_dict.update(layout_dict)

        def get_conf(option, default=None, section=None):
            return options_dict.get(option)

        def set_conf(option, value):
            options_dict[option] = value

        editor.get_conf = get_conf
        editor.set_conf = set_conf
        editor.get_widget().get_conf = get_conf
        editor.get_widget().set_conf = set_conf

        editor.setup_open_files()
        return editor, expected_filenames, expected_current_filename

    return _get_editor_open_files
