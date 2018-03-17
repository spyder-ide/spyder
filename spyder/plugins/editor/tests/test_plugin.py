# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""Tests for the Editor plugin."""

# Standard library imports
import os
import os.path as osp
import shutil
try:
    from unittest.mock import MagicMock, Mock
except ImportError:
    from mock import MagicMock, Mock  # Python 2

# Third party imports
import pytest
from qtpy.QtWidgets import QMainWindow

# Local imports
from spyder.config.main import CONF
from spyder.utils.qthelpers import qapplication
app = qapplication()
from spyder.plugins.editor.plugin import AutosaveComponent, Editor


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def setup_editor(qtbot, monkeypatch):
    """Set up the Editor plugin."""
    # monkeypatch.setattr('spyder.dependencies', Mock())
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

        def get_spyder_pythonpath(*args):
            return []

    window = MainMock()
    editor = Editor(window)
    window.setCentralWidget(editor)
    window.resize(640, 480)
    qtbot.addWidget(window)
    window.show()

    yield editor
    editor.close()

    CONF.remove_option('editor', 'autosave_mapping')


@pytest.fixture(scope="module")
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


@pytest.fixture
def editor_open_files(request, setup_editor, python_files):
    """
    Setup an Editor with a set of open files, given a past file in focus.

    If no/None ``last_focused_filename`` is passed, the ``"layout_settings"``
    key is not included in the options dict.
    If no/None ``expected_current_filename``, is assumed to be the first file.
    """
    def _get_editor_open_files(last_focused_filename,
                               expected_current_filename):
        editor = setup_editor
        expected_filenames, tmpdir = python_files
        if expected_current_filename is None:
            expected_current_filename = expected_filenames[0]
        expected_current_filename = osp.join(tmpdir, expected_current_filename)
        options_dict = {
            'filenames': expected_filenames,
            'max_recent_files': 20,
            }
        if last_focused_filename is not None:
            splitsettings = [(False,
                              osp.join(tmpdir, last_focused_filename),
                              [1] * len(expected_filenames))]
            layout_dict = {'layout_settings': {'splitsettings': splitsettings}}
            options_dict.update(layout_dict)

        def get_option(option, default=None):
            return options_dict.get(option)
        editor.get_option = get_option

        editor.setup_open_files()
        return editor, expected_filenames, expected_current_filename

    return _get_editor_open_files


# =============================================================================
# ---- Tests
# =============================================================================
def test_basic_initialization(setup_editor):
    """Test Editor plugin initialization."""
    editor = setup_editor

    # Assert that editor exists
    assert editor is not None


@pytest.mark.parametrize(
    'last_focused_filename, expected_current_filename',
    [('other_file.py', 'file1.py'),
     ('file1.py', 'file1.py'),
     ('file2.py', 'file2.py'),
     ('file4.py', 'file4.py')
     ])
def test_setup_open_files(editor_open_files, last_focused_filename,
                          expected_current_filename):
    """Test Editor plugin open files setup.

    Test that the file order is preserved during the Editor plugin setup and
    that the current file correspond to the last focused file.
    """
    editor_factory = editor_open_files
    editor, expected_filenames, expected_current_filename = (
        editor_factory(last_focused_filename, expected_current_filename))

    current_filename = editor.get_current_editorstack().get_current_filename()
    current_filename = osp.normcase(current_filename)
    assert current_filename == expected_current_filename
    filenames = editor.get_current_editorstack().get_filenames()
    filenames = [osp.normcase(f) for f in filenames]
    assert filenames == expected_filenames


def test_setup_open_files_cleanprefs(editor_open_files):
    """Test that Editor successfully opens files if layout is not defined.

    Regression test for #8458 .
    """
    editor_factory = editor_open_files
    editor, expected_filenames, expected_current_filename = (
        editor_factory(None, None))

    filenames = editor.get_current_editorstack().get_filenames()
    filenames = [osp.normcase(f) for f in filenames]
    assert filenames == expected_filenames
    current_filename = editor.get_current_editorstack().get_current_filename()
    current_filename = osp.normcase(current_filename)
    assert current_filename == expected_current_filename


def test_renamed_tree(setup_editor, mocker):
    """Test editor.renamed_tree().

    This tests that the file renaming functions are called correctly,
    but does not test that all the renaming happens in File Explorer,
    Project Explorer, and Editor widget as those aren't part of the plugin.
    """
    editor = setup_editor
    mocker.patch.object(editor, 'get_filenames')
    mocker.patch.object(editor, 'renamed')
    editor.get_filenames.return_value = ['/test/directory/file1.py',
                                         '/test/directory/file2.txt',
                                         '/home/spyder/testing/file3.py',
                                         '/test/directory/file4.rst']

    editor.renamed_tree('/test/directory', '/test/dir')
    assert editor.renamed.call_count == 3
    assert editor.renamed.called_with(source='/test/directory/file1.py',
                                      dest='test/dir/file1.py')
    assert editor.renamed.called_with(source='/test/directory/file2.txt',
                                      dest='test/dir/file2.txt')
    assert editor.renamed.called_with(source='/test/directory/file4.rst',
                                      dest='test/dir/file4.rst')


def test_no_template(setup_editor):
    """
    Test that new files can be opened when no template is found.
    """
    editor = setup_editor

    # Move template to another file to simulate the lack of it
    template = editor.TEMPLATE_PATH
    shutil.move(template, osp.join(osp.dirname(template), 'template.py.old'))

    # Open a new file
    editor.new()

    # Get contents
    code_editor = editor.get_focus_widget()
    contents = code_editor.get_text('sof', 'eof')

    # Assert contents are empty
    assert not contents

    # Revert template back
    shutil.move(osp.join(osp.dirname(template), 'template.py.old'), template)


def test_editor_has_autosave_component(setup_editor):
    """Test that Editor includes an AutosaveComponent."""
    editor, qtbot = setup_editor
    assert type(editor.autosave) == AutosaveComponent


def test_autosave_component_timer(qtbot, mocker):
    """Test that AutosaveCompenent calls do_autosave() on timer."""
    mocker.patch.object(AutosaveComponent, 'AUTOSAVE_DELAY', 100)
    mocker.patch.object(AutosaveComponent, 'do_autosave')
    addon = AutosaveComponent(None)
    addon.do_autosave.assert_not_called()
    qtbot.wait(500)
    addon.do_autosave.assert_called()


def test_autosave_component_do_autosave(setup_editor, mocker):
    """Test that AutosaveComponent's do_autosave() calls the current editor
    stack's autosave_all()."""
    editor, qtbot = setup_editor
    editorStack = editor.get_current_editorstack()
    mocker.patch.object(editorStack.autosave, 'autosave_all')
    editor.autosave.do_autosave()
    editorStack.autosave.autosave_all.assert_called()


def test_editor_transmits_sig_option_changed(setup_editor):
    editor, qtbot = setup_editor
    editorStack = editor.get_current_editorstack()
    with qtbot.waitSignal(editor.sig_option_changed) as blocker:
        editorStack.sig_option_changed.emit('autosave_mapping', {1: 2})
    assert blocker.args == ['autosave_mapping', {1: 2}]


def test_editor_sets_autosave_mapping_on_first_editorstack(setup_editor):
    """Check that first editor stack gets autosave mapping from config."""
    editor, qtbot = setup_editor
    editorStack = editor.get_current_editorstack()
    assert editorStack.autosave_mapping == {}


def test_editor_syncs_autosave_mapping_among_editorstacks(setup_editor):
    """Check that when an editorstack emits a sig_option_changed for
    autosave_mapping, the autosave mapping of all other editorstacks is
    updated."""
    editor, qtbot = setup_editor
    editor.editorsplitter.split()
    assert len(editor.editorstacks) == 2
    old_mapping = {}
    for editorstack in editor.editorstacks:
        assert editorstack.autosave_mapping == old_mapping
    new_mapping = {'ham': 'spam'}
    editor.get_current_editorstack().sig_option_changed.emit(
            'autosave_mapping', new_mapping)
    for editorstack in editor.editorstacks:
        if editorstack == editor.get_current_editorstack():
            assert editorstack.autosave_mapping == old_mapping
        else:
            assert editorstack.autosave_mapping == new_mapping


def test_editor_calls_recoverydialog_exec_if_nonempty(qtbot, monkeypatch):
    """Check that editor tries to exec a recovery dialog on construction."""
    mock_RecoveryDialog = MagicMock()
    monkeypatch.setattr('spyder.plugins.editor.plugin.RecoveryDialog',
                        mock_RecoveryDialog)
    setup_editor_iter = setup_editor(qtbot, monkeypatch)
    editor, qtbot = next(setup_editor_iter)
    mock_RecoveryDialog.return_value.exec_if_nonempty.assert_called()


if __name__ == "__main__":
    pytest.main(['-x', os.path.basename(__file__), '-vv', '-rw'])
