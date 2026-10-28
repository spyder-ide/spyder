# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""Shared document ownership, independent views and native save behavior."""
import pytest
from qtpy.QtCore import QCoreApplication, QEvent, Qt
from spyder.config.manager import CONF


def test_master_extensions_and_shared_history(reference, editor_plugin, tmp_path):
    """Master's extension API and document versions survive lazy cloning."""
    from qtpy.QtCore import QSize
    from qtpy.QtGui import QTextCursor
    from spyder.plugins.editor.api.editorextension import EditorExtension
    from spyder.plugins.editor.api.panel import Panel, PanelPosition

    class CustomExtension(EditorExtension):
        pass

    class CustomPanel(Panel):
        def sizeHint(self):
            return QSize(12, 12)

    editor_plugin.add_extension(CustomExtension)
    editor_plugin.add_panel(CustomPanel, PanelPosition.LEFT)
    manager = editor_plugin.get_widget()
    filename = tmp_path / 'extended.py'
    filename.write_text('first\nsecond\n', encoding='utf-8')
    manager.load(str(filename))
    source = manager.get_current_editor()
    source.moveCursor(QTextCursor.End)
    reference.load(str(filename))
    clone = reference.get_focus_widget()
    assert CustomExtension in clone.external_extensions
    assert (CustomPanel, PanelPosition.LEFT) in clone.external_panels
    assert clone.editor_extensions.get(CustomExtension).editor is clone
    assert clone.panels.get(CustomPanel).editor is clone
    clone.set_cursor_position(0)
    clone.insert_text('changed ')
    clone.undo()
    assert source.toPlainText() == 'first\nsecond\n'
    assert clone.textCursor().position() == 0
    assert source.textCursor().position() == len('first\nsecond\n')
    source.redo()
    assert clone.toPlainText() == 'changed first\nsecond\n'
    assert source.text_version == clone.text_version
    clone.setPlainText('replacement\n')
    assert source.toPlainText() == 'replacement\n'
    assert source.text_version == clone.text_version
    assert not source.undo_stack.can_undo()

def test_creation_is_lazy_and_shared(reference, editor_plugin, tmp_path):
    manager = editor_plugin.get_widget()
    assert reference.splitter is None
    assert len(manager.editorstacks) == 1
    filename = tmp_path / 'reference.py'
    filename.write_text('value = 3\n', encoding='utf-8')
    manager.load(str(filename))
    reference.ensure_editor()
    primary = manager.editorstacks[0].get_current_editor()
    secondary = reference.get_focus_widget()
    assert primary is not secondary
    assert primary.document() is secondary.document()
    assert len(manager.editorstacks) == 2
    assert not reference.splitter.editorstack.is_closable
    assert reference.get_main_toolbar().isHidden()
    assert reference._corner_toolbar.isHidden()
    assert reference.get_action('open_reference_file') not in (
        reference.splitter.editorstack.top_toolbar.actions())
    reference.splitter.editorstack._EditorStack__setup_menu()
    assert reference.get_action('open_reference_file') in (
        reference.splitter.editorstack.menu.actions())
    assert reference.close_action in (
        reference.splitter.editorstack._EditorStack__get_main_widget_actions())
    assert reference.splitter.editorstack.top_toolbar.widgetForAction(
        reference.splitter.editorstack.top_toolbar.actions()[0]
    ) is reference.splitter.editorstack.fname_label


@pytest.mark.parametrize('close_split', [False, True])
def test_closed_clone_releases_shared_undo_view(reference, editor_plugin, tmp_path, close_split):
    manager = editor_plugin.get_widget()
    filename = tmp_path / 'lifetime.py'
    filename.write_text('first\nsecond\n', encoding='utf-8')
    manager.load(str(filename))
    source = manager.editorstacks[0].get_current_editor()
    reference.load(str(filename))
    stack = reference.splitter.editorstack
    if close_split:
        reference.splitter.split(Qt.Vertical)
        stack = reference.splitter.widget(1).editorstack
    clone = stack.get_current_editor()
    clone.insert_text('changed ')
    if close_split:
        stack.close()
    else:
        stack.close_file()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    source.setPlainText('replacement\n')
    source.insert_text('kept ')
    source.undo()
    assert source.toPlainText() == 'replacement\n'
    source.redo()
    assert source.toPlainText() == 'kept replacement\n'


def test_unfocused_clone_edit_snapshots(reference, editor_plugin, tmp_path):
    manager = editor_plugin.get_widget()
    filename = tmp_path / 'snapshots.py'
    filename.write_text('first\nsecond\n', encoding='utf-8')
    manager.load(str(filename))
    reference.load(str(filename))
    clone = reference.get_focus_widget()
    manager.editorstacks[0].get_current_editor().setFocus()
    clone.insert_text('added ')
    clone._commit_pending_edit()
    clone.set_cursor_position(len('added first\n'))
    clone.insert_text('next ')
    clone.undo()
    assert clone.toPlainText() == 'added first\nsecond\n'
    assert clone.textCursor().position() == len('added first\n')
    clone.undo()
    assert clone.toPlainText() == 'first\nsecond\n'


def test_reference_tabs_only_load_selected_files(reference, editor_plugin, tmp_path):
    """Do not clone the primary session or include subsequent primary opens."""
    manager = editor_plugin.get_widget()
    filenames = []
    for number in range(12):
        filename = tmp_path / f'primary_{number}.py'
        filename.write_text(f'value = {number}\n', encoding='utf-8')
        filenames.append(str(filename))
    manager.load(filenames)
    primary = manager.editorstacks[0]
    primary.set_current_filename(filenames[0])
    reference.ensure_editor()
    secondary = reference.splitter.editorstack
    assert [info.filename for info in secondary.data] == [filenames[0]]
    reference.load(filenames[4])
    assert [info.filename for info in secondary.data] == [filenames[0], filenames[4]]
    primary.get_current_editor().setFocus()
    added = tmp_path / 'primary_only.py'
    added.write_text('added = 1\n', encoding='utf-8')
    manager.load(str(added), editorwindow=manager)
    assert [info.filename for info in secondary.data] == [filenames[0], filenames[4]]
    secondary.close_file(0)
    assert primary.has_filename(filenames[0]) is not None
    assert [info.filename for info in secondary.data] == [filenames[4]]
    primary.close_file(primary.has_filename(filenames[4]))
    assert [info.filename for info in secondary.data] == [filenames[4]]
    assert not primary.tabs.isTabVisible(primary.has_filename(filenames[4]))
    assert primary.has_filename(str(added)) is not None


def test_restore_missing_reference_keeps_surviving_file_line(reference, tmp_path):
    missing = str(tmp_path / 'missing.py')
    surviving = tmp_path / 'surviving.py'
    surviving.write_text('value = 1\n' * 30, encoding='utf-8')
    reference.set_conf('layout_settings', {
        'splitsettings': [(False, str(surviving), [5, 20])],
        'filenames': [[missing, str(surviving)]]})
    reference.ensure_editor()
    assert reference.get_focus_widget().get_cursor_line_number() == 20


@pytest.mark.parametrize('primary_first', [True, False])
@pytest.mark.parametrize('answer', ['cancel', 'save', 'discard'])
def test_close_only_current_view_until_last_view_prompts(
        reference, editor_plugin, monkeypatch, tmp_path, primary_first, answer):
    from qtpy.QtWidgets import QMessageBox
    filename = tmp_path / 'shared.md'
    filename.write_text('# Original\n', encoding='utf-8')
    manager = editor_plugin.get_widget()
    manager.load(str(filename))
    primary = manager.editorstacks[0]
    reference.load(str(filename))
    secondary = reference.splitter.editorstack
    primary.save_dialog_on_tests = secondary.save_dialog_on_tests = True
    document = primary.get_current_editor().document()
    secondary.get_current_editor().insert_text('# Unsaved\n')
    baseline = manager.autosave.file_hashes[str(filename)]
    first, last = (primary, secondary) if primary_first else (secondary, primary)
    def unexpected_prompt(dialog):
        pytest.fail('Closing one shared view must not prompt to save the document')
    monkeypatch.setattr(QMessageBox, 'exec_', unexpected_prompt)
    first.close_file(first.has_filename(str(filename)))
    assert last.get_current_editor().document() is document
    assert '# Unsaved' in last.get_current_editor().toPlainText()
    assert document.isModified()
    assert filename.read_text(encoding='utf-8') == '# Original\n'
    assert manager.autosave.file_hashes[str(filename)] == baseline
    if first is primary:
        assert not first.tabs.isTabVisible(first.has_filename(str(filename)))
    else:
        assert first.has_filename(str(filename)) is None
    response = {'cancel': QMessageBox.Cancel, 'save': QMessageBox.Yes,
                'discard': QMessageBox.No}[answer]
    monkeypatch.setattr(QMessageBox, 'exec_', lambda dialog: response)
    last.close_file(last.has_filename(str(filename)))
    if answer == 'cancel':
        assert last.get_current_editor().document() is document
        assert last.tabs.isTabVisible(last.has_filename(str(filename)))
        assert document.isModified()
        if first is primary:
            assert not primary.tabs.isTabVisible(primary.has_filename(str(filename)))
        document.setModified(False)
    else:
        assert primary.has_filename(str(filename)) is None
        assert secondary.has_filename(str(filename)) is None
        assert str(filename) not in manager.autosave.file_hashes
    assert ('# Unsaved' in filename.read_text(encoding='utf-8')) == (answer == 'save')


def test_last_untitled_view_save_cancel_and_renamed_close(reference, editor_plugin, monkeypatch, tmp_path):
    from qtpy.QtWidgets import QMessageBox
    manager = editor_plugin.get_widget()
    primary = manager.editorstacks[0]
    manager.new(editorstack=primary, text='unsaved = True\n')
    filename = primary.get_current_filename()
    reference.transfer_tab(primary)
    secondary = reference.splitter.editorstack
    editor = secondary.get_current_editor()
    editor.insert_text('# keep\n')
    secondary.save_dialog_on_tests = True
    monkeypatch.setattr(QMessageBox, 'exec_', lambda dialog: QMessageBox.Yes)
    destination = tmp_path / 'saved.py'
    monkeypatch.setattr(type(primary), 'select_savename', lambda *args: None)
    secondary.close_file()
    assert secondary.get_current_editor() is editor
    assert editor.document().isModified()
    assert not primary.tabs.isTabVisible(primary.has_filename(filename))
    other = tmp_path / 'other.py'
    other.write_text('other = 1\n', encoding='utf-8')
    manager.load(str(other), editorwindow=manager)
    other_editor = primary.get_current_editor()
    other_editor.insert_text('# preserve\n')
    monkeypatch.setattr(type(primary), 'select_savename', lambda *args: str(destination))
    secondary.close_file()
    assert destination.read_text(encoding='utf-8') == '# keep\nunsaved = True\n'
    assert primary.has_filename(str(destination)) is None
    assert secondary.has_filename(str(destination)) is None
    assert primary.data[primary.has_filename(str(other))].editor is other_editor
    assert other_editor.document().isModified()
    other_editor.document().setModified(False)


def test_reference_focus_preserves_global_save_and_autosave(reference, editor_plugin, tmp_path):
    manager = editor_plugin.get_widget()
    first = tmp_path / 'modified.py'
    second = tmp_path / 'reference.py'
    first.write_text('value = 1\n', encoding='utf-8')
    second.write_text('reference = 1\n', encoding='utf-8')
    manager.load([str(first), str(second)])
    primary = manager.editorstacks[0]
    original = primary.data[primary.has_filename(str(first))].editor
    primary.set_current_filename(str(second))
    reference.ensure_editor()
    reference.get_focus_widget().setFocus()
    manager.set_last_focused_editorstack(None, reference.splitter.editorstack)
    manager.save_focused_editorstack()
    assert manager.get_current_editorstack() is reference.splitter.editorstack
    original.insert_text('# changed\n')
    assert manager.get_editor(str(first)) is original
    from spyder.plugins.application.api import ApplicationActions
    action_states = {}
    manager.sig_file_action_enabled.connect(action_states.__setitem__)
    manager.refresh_save_actions()
    assert action_states[ApplicationActions.SaveAll]
    manager.autosave.do_autosave()
    assert str(first) in manager.autosave.name_mapping
    reference.splitter.editorstack.save_all()
    assert '# changed' in first.read_text(encoding='utf-8')
    assert not original.document().isModified()


@pytest.mark.parametrize('method', ['save_as', 'save_copy_as'])
@pytest.mark.parametrize('destination_in_reference', [False, True])
def test_reference_save_to_primary_only_file_has_one_document(
        reference, editor_plugin, tmp_path, monkeypatch, method, destination_in_reference):
    manager = editor_plugin.get_widget()
    first = tmp_path / 'first.py'
    second = tmp_path / 'destination.py'
    first.write_text('first = 1\n', encoding='utf-8')
    second.write_text('destination = 2\n', encoding='utf-8')
    manager.load([str(first), str(second)])
    primary = manager.editorstacks[0]
    primary.set_current_filename(str(first))
    reference.ensure_editor()
    secondary = reference.splitter.editorstack
    if destination_in_reference:
        reference.load(str(second))
        secondary.set_current_filename(str(first))
    monkeypatch.setattr(type(secondary), 'select_savename', lambda *_: str(second))
    assert getattr(secondary, method)()
    assert [info.filename for info in primary.data].count(str(second)) == 1
    assert second.read_text(encoding='utf-8') == 'first = 1\n'
    assert secondary.get_current_editor().document() is primary.data[
        primary.has_filename(str(second))].editor.document()


@pytest.mark.parametrize('method', ['save_as', 'save_copy_as'])
def test_cancel_reference_save_collision_keeps_both_documents(
        reference, editor_plugin, tmp_path, monkeypatch, method):
    from qtpy.QtWidgets import QMessageBox
    manager = editor_plugin.get_widget()
    first = tmp_path / 'source.py'
    second = tmp_path / 'destination.py'
    first.write_text('source = 1\n', encoding='utf-8')
    second.write_text('destination = 2\n', encoding='utf-8')
    manager.load([str(first), str(second)])
    primary = manager.editorstacks[0]
    primary.set_current_filename(str(first))
    reference.ensure_editor()
    destination = primary.data[primary.has_filename(str(second))].editor
    destination.insert_text('# keep unsaved\n')
    primary.save_dialog_on_tests = True
    secondary = reference.splitter.editorstack
    monkeypatch.setattr(type(secondary), 'select_savename', lambda *_: str(second))
    monkeypatch.setattr(QMessageBox, 'exec_', lambda *_: QMessageBox.Cancel)
    assert not getattr(secondary, method)()
    assert [info.filename for info in primary.data] == [str(first), str(second)]
    assert not primary.data[0].newly_created
    assert destination.document().isModified()
    assert '# keep unsaved' in destination.toPlainText()
    assert second.read_text(encoding='utf-8') == 'destination = 2\n'
    destination.document().setModified(False)


def test_secondary_factory_preferences_are_independent_without_path(reference, editor_plugin, qtbot):
    from spyder.plugins.preferences.widgets.configdialog import ConfigDialog
    options = ('use_primary_settings', 'show_filename_toolbar')
    previous = {option: reference.get_conf(option) for option in options}
    try:
        for option in options:
            reference.set_conf(option, CONF.get_default('reference_editor', option))
        dialog = ConfigDialog(editor_plugin.main)
        qtbot.addWidget(dialog)
        page = reference._plugin.CONF_WIDGET_CLASS(reference._plugin, dialog)
        page.initialize()
        controls = {option: checkbox for checkbox, (_, option, _) in page.checkboxes.items()}
        assert not controls['use_primary_settings'].isChecked()
        assert not controls['show_filename_toolbar'].isChecked()
        assert all(group.isEnabled() for group in page.custom_groups)
        reference.ensure_editor()
        assert reference.splitter.editorstack.top_toolbar.isHidden()
        for option in reference.editor_options:
            if option != 'show_filename_toolbar':
                assert CONF.get_default('reference_editor', option) == CONF.get_default('editor', option)
    finally:
        for option, value in previous.items():
            reference.set_conf(option, value)


def test_secondary_focus_does_not_take_over_primary_outline(reference, editor_plugin, tmp_path):
    manager = editor_plugin.get_widget()
    filename = tmp_path / 'primary_outline.py'
    filename.write_text('def primary_function():\n    return 1\n', encoding='utf-8')
    manager.load(str(filename))
    primary_tree = manager.outlineexplorer.treewidget
    primary_proxy = primary_tree.current_editor
    reference.ensure_editor()
    reference.get_focus_widget().setFocus()
    reference.splitter.editorstack.refresh()
    assert primary_tree.current_editor is primary_proxy
    assert reference.get_focus_widget().oe_proxy not in primary_tree.editor_ids


@pytest.mark.parametrize('copy', [False, True])
def test_transfer_primary_view_preserves_document_and_undo(reference, editor_plugin, tmp_path, copy):
    manager = editor_plugin.get_widget()
    filename = tmp_path / 'transfer.py'
    filename.write_text('value = 1\n', encoding='utf-8')
    manager.load(str(filename))
    primary = manager.editorstacks[0]
    editor = primary.get_current_editor()
    editor.insert_text('# unsaved\n')
    count = primary.get_stack_count()
    target = reference.transfer_tab(primary, copy=copy)
    assert target.document() is editor.document()
    assert primary.get_stack_count() == count
    assert primary.tabs.isTabVisible(primary.has_filename(str(filename))) == copy
    assert '# unsaved' in target.toPlainText()
    assert filename.read_text(encoding='utf-8') == 'value = 1\n'
    target.undo()
    assert editor.toPlainText() == 'value = 1\n'
    target_count = reference.splitter.editorstack.get_stack_count()
    if copy:
        reference.transfer_tab(primary, copy=True)
    assert reference.splitter.editorstack.get_stack_count() == target_count


@pytest.mark.parametrize('copy', [False, True])
def test_transfer_back_reveals_primary_without_duplicate(reference, editor_plugin, tmp_path, copy):
    manager = editor_plugin.get_widget()
    filename = tmp_path / 'return.py'
    filename.write_text('value = 2\n', encoding='utf-8')
    manager.load(str(filename))
    primary = manager.editorstacks[0]
    original = primary.get_current_editor()
    reference.transfer_tab(primary)
    secondary = reference.splitter.editorstack
    secondary.get_current_editor().insert_text('# keep\n')
    target = reference.transfer_tab(secondary, copy=copy)
    assert target is original
    assert target.document().isModified()
    assert primary.tabs.isTabVisible(primary.has_filename(str(filename)))
    assert (secondary.has_filename(str(filename)) is not None) == copy
    assert '# keep' in original.toPlainText()


def test_failed_target_does_not_remove_source_view(reference, editor_plugin, monkeypatch, tmp_path):
    manager = editor_plugin.get_widget()
    first, second = tmp_path / 'initial.py', tmp_path / 'source.py'
    first.write_text('first = 1\n', encoding='utf-8')
    second.write_text('second = 2\n', encoding='utf-8')
    manager.load(str(first))
    reference.ensure_editor()
    manager.load(str(second), editorwindow=manager)
    primary = manager.editorstacks[0]
    original = primary.get_current_editor()
    monkeypatch.setattr(reference, 'load', lambda filename: None)
    assert reference.transfer_tab(primary) is None
    assert primary.tabs.isTabVisible(primary.has_filename(str(second)))
    assert primary.get_current_editor() is original
    assert reference.splitter.editorstack.has_filename(str(second)) is None


def test_application_close_cancels_pending_scrollflag_work(editor_plugin, qtbot, tmp_path):
    filename = tmp_path / 'closing.py'
    filename.write_text('value = 7\n', encoding='utf-8')
    manager = editor_plugin.get_widget()
    manager.load(str(filename))
    panel = manager.get_current_editor().scrollflagarea
    try:
        with qtbot.assertNotEmitted(panel._update_flags_thread.started):
            panel.update_flags()
            manager.on_close()
            panel.update_flags.flush()
            qtbot.wait(50)
    finally:
        panel.close()


@pytest.mark.parametrize('secondary', [False, True])
def test_open_document_outline_navigation_does_not_load_again(
        reference, editor_plugin, monkeypatch, tmp_path, qtbot, secondary):
    manager = editor_plugin.get_widget()
    filename = tmp_path / 'navigation.py'
    filename.write_text('first = 1\nsecond = 2\n', encoding='utf-8')
    manager.load(str(filename))
    primary = manager.editorstacks[0]
    if secondary:
        reference.load(str(filename))
    stack = reference.splitter.editorstack if secondary else primary
    document = stack.get_current_editor().document()
    def unexpected_load(*args, **kwargs):
        pytest.fail('Navigation must reuse the existing document')
    monkeypatch.setattr(primary, 'load', unexpected_load)
    with (qtbot.assertNotEmitted(manager.starting_long_process),
          qtbot.assertNotEmitted(manager.ending_long_process)):
        if secondary:
            reference.load(str(filename), goto=2, word='second', from_outline=True)
        else:
            editor_plugin.load_edit_goto(str(filename), 2, 'second')
    assert stack.get_current_editor().get_cursor_line_number() == 2
    assert stack.get_current_editor().document() is document
    assert not document.isModified()
