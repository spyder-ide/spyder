# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""Configuration changes must not repeatedly highlight unchanged documents."""
import pytest
from qtpy.QtGui import QFont, QTextOption
from lsprotocol import types as lsp

from spyder.config.manager import CONF
from spyder.plugins.editor.widgets.codeeditor import CodeEditor


@pytest.mark.parametrize('clone_first', [False, True])
def test_clone_diagnostics_keep_shared_error_markers(configured_editor, qtbot, clone_first):
    """A clone must not erase the canonical document's diagnostic metadata."""
    editor = configured_editor
    editor.set_text('a=\n')
    clone = CodeEditor(None)
    qtbot.addWidget(clone)
    clone.setup_editor(language='Python', cloned_from=editor, font=editor.font())
    diagnostics = [lsp.Diagnostic(
        range=lsp.Range(lsp.Position(0, 2), lsp.Position(0, 2)),
        message='invalid syntax', severity=lsp.DiagnosticSeverity.Error)]
    try:
        views = (clone, editor) if clone_first else (editor, clone)
        for view in views:
            with qtbot.waitSignal(view.sig_process_code_analysis):
                view.process_code_analysis(diagnostics)
        data = clone.document().firstBlock().userData()
        assert data.code_analysis == [('', 'E', lsp.DiagnosticSeverity.Error, 'invalid syntax')]
        for view in views:
            with qtbot.waitSignal(view.sig_process_code_analysis):
                view.process_code_analysis([])
        assert not data.code_analysis
    finally:
        clone.scrollflagarea.close()
        clone.decorations.close()
        clone.close()


def test_language_server_diagnostics_in_clone(completions_codeeditor, qtbot_module):
    """Actual pylsp notifications update and clear the secondary gutter."""
    editor, completion = completions_codeeditor
    clone = CodeEditor(None)
    qtbot_module.addWidget(clone)
    clone.setup_editor(language='Python', cloned_from=editor, font=editor.font())
    clone.filename = editor.filename
    clone.sig_perform_completion_request.connect(completion.send_request)
    completion.register_file('python', editor.filename, clone)
    clone.completions_available = True
    def has_error_marker():
        data = clone.document().firstBlock().userData()
        return data is not None and bool(data.code_analysis)
    try:
        clone.setPlainText('a=\n')
        qtbot_module.waitUntil(has_error_marker, timeout=30000)
        data = clone.document().firstBlock().userData()
        assert any(item[2] == lsp.DiagnosticSeverity.Error for item in data.code_analysis)
        assert clone.errors_present()
        clone.setPlainText('a = 1\n')
        qtbot_module.waitUntil(lambda: not clone.errors_present(), timeout=30000)
        data = clone.document().firstBlock().userData()
        assert data is None or not data.code_analysis
    finally:
        clone.scrollflagarea.close()
        clone.decorations.close()
        clone.close()


@pytest.fixture
def configured_editor(qtbot):
    editor = CodeEditor(None)
    editor.setup_editor(language='Python', color_scheme='spyder_themes.spyder/dark',
                        font=QFont('Monospace', 10), folding=False)
    editor.set_text('def example():\n    return 42\n')
    editor.rehighlight()
    editor._rehighlight_timer.stop()
    qtbot.addWidget(editor)
    yield editor
    editor.scrollflagarea.close()
    editor.decorations.close()
    editor.close()


@pytest.fixture
def highlight_calls(configured_editor, monkeypatch):
    calls = []
    original = configured_editor.highlighter.rehighlight

    def rehighlight():
        calls.append(True)
        return original()

    monkeypatch.setattr(configured_editor.highlighter, 'rehighlight', rehighlight)
    return calls


@pytest.mark.parametrize('enabled', [False, True])
def test_repeated_blanks_do_not_rehighlight(configured_editor, highlight_calls, enabled):
    editor = configured_editor
    editor.set_blanks_enabled(enabled)
    highlight_calls.clear()
    editor.set_blanks_enabled(enabled)
    assert not highlight_calls
    flags = editor.document().defaultTextOption().flags()
    assert bool(flags & QTextOption.ShowTabsAndSpaces) == enabled
    assert flags & QTextOption.AddSpaceForLineAndParagraphSeparators
    editor.set_blanks_enabled(not enabled)
    assert len(highlight_calls) == 1


def test_repeated_colors_do_not_rehighlight(configured_editor, highlight_calls):
    editor = configured_editor
    editor.set_color_scheme('spyder_themes.spyder/dark')
    assert not highlight_calls
    editor.set_color_scheme('spyder_themes.spyder/light')
    assert len(highlight_calls) == 1
    keyword = editor.document().firstBlock().layout().formats()[0].format
    assert keyword.foreground().color() == editor.highlighter.formats['keyword'].foreground().color()


def test_modified_named_scheme_is_applied(configured_editor, highlight_calls):
    editor = configured_editor
    previous = CONF.get('appearance', 'spyder_themes.spyder/dark/keyword', default=None)
    try:
        CONF.set('appearance', 'spyder_themes.spyder/dark/keyword', ('#123456', True, False))
        editor.set_color_scheme('spyder_themes.spyder/dark')
        assert len(highlight_calls) == 1
        keyword = editor.document().firstBlock().layout().formats()[0].format
        assert keyword.foreground().color().name() == '#123456'
    finally:
        CONF.set('appearance', 'spyder_themes.spyder/dark/keyword', previous)


def test_modified_shared_scheme_dictionary_is_applied(configured_editor):
    colors = configured_editor.highlighter.color_scheme.copy()
    colors['keyword'] = ('#111111', False, False)
    configured_editor.set_color_scheme(colors)
    colors['keyword'] = ('#222222', False, False)
    configured_editor.set_color_scheme(colors)
    keyword = configured_editor.document().firstBlock().layout().formats()[0].format
    assert keyword.foreground().color().name() == '#222222'


def test_same_colors_still_apply_changed_font(configured_editor, highlight_calls):
    editor = configured_editor
    editor.set_font(QFont('Monospace', 17), color_scheme='spyder_themes.spyder/dark')
    assert highlight_calls
    keyword = editor.document().firstBlock().layout().formats()[0].format
    assert keyword.font().pointSize() == 17


def test_shared_view_configuration(configured_editor, highlight_calls, qtbot):
    editor = configured_editor
    clone = CodeEditor(None)
    qtbot.addWidget(clone)
    clone.setup_editor(language='Python', cloned_from=editor,
                       font=editor.font(), color_scheme='spyder_themes.spyder/dark')
    try:
        assert clone.highlighter is editor.highlighter
        editor.set_color_scheme('spyder_themes.spyder/light')
        clone.set_color_scheme('spyder_themes.spyder/light')
        assert len(highlight_calls) == 1
        background = editor.highlighter.get_background_color().name()
        assert f'background: {background}' in editor.styleSheet()
        assert f'background: {background}' in clone.styleSheet()
        highlight_calls.clear()
        editor.set_blanks_enabled(True)
        clone.set_blanks_enabled(True)
        assert len(highlight_calls) == 1
    finally:
        clone.scrollflagarea.close()
        clone.decorations.close()
        clone.close()


@pytest.mark.parametrize('name', ['Same', '', 'Same, #2'])
def test_unchanged_cells_do_not_scan_document(configured_editor, monkeypatch, name):
    from spyder.plugins.outlineexplorer import api

    editor = configured_editor
    editor.set_text(f'# %% {name}\nvalue = 1\n# %% {name}\nvalue = 2\n')
    editor.rehighlight()
    cells = [cell for _, cell in editor.get_cell_list()]
    scans = []
    updates = []
    original = api.document_cells

    def document_cells(*args, **kwargs):
        scans.append(True)
        yield from original(*args, **kwargs)

    monkeypatch.setattr(api, 'document_cells', document_cells)
    cells[0].sig_update.connect(lambda: updates.append(True))
    editor.rehighlight()
    assert not scans
    assert updates
    first, second = [cell for _, cell in editor.get_cell_list()]
    assert first is cells[0] and second is cells[1]
    # Actual renaming must still notify subsequent duplicates and renumber them.
    second.sig_update.connect(lambda: updates.append(False))
    replacement = api.OutlineExplorerData(first.block, text='# %% Different',
        fold_level=first.fold_level, def_type=first.def_type,
        def_name='Different', color=first.color)
    replacement.cell_level = first.cell_level
    updates.clear()
    assert first.update(replacement)
    assert scans and updates == [True, False]
    assert second.def_name == (name or 'Unnamed Cell')
    replacement.cell_level += 1
    assert not first.update(replacement)
