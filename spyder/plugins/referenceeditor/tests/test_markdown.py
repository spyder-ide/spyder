# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""Bounded Markdown rendering and native outline integration."""
import pytest
from qtpy.QtCore import QCoreApplication, QEvent, Qt
from qtpy.QtWidgets import QApplication


def test_preview_tab_focus_updates_its_native_outline(reference, editor_plugin, qtbot, tmp_path):
    from spyder.config.manager import CONF
    from spyder.plugins.referenceeditor.outline import ReferenceOutline
    plugin = ReferenceOutline(editor_plugin.main, CONF)
    plugin.on_initialize()
    outline = plugin.get_widget()
    qtbot.addWidget(outline)
    reference.set_outlineexplorer(outline)
    for name in ('first.md', 'second.md'):
        filename = tmp_path / name
        filename.write_text('# Heading\n', encoding='utf-8')
        reference.load(str(filename))
        stack = reference.splitter.editorstack
        stack.set_markdown_preview(True)
    first = stack.data[0].editor
    second = stack.data[1].editor
    outline.treewidget.set_current_editor(second.oe_proxy, False)
    stack.get_current_view().setFocus()
    qtbot.mouseClick(stack.tabs.tabBar(), Qt.LeftButton,
                     pos=stack.tabs.tabBar().tabRect(0).center())
    assert stack.get_current_view() is first.markdown_page.browser
    assert outline.treewidget.current_editor is first.oe_proxy
    manager = editor_plugin.get_widget()
    assert manager.get_current_editorstack() is stack
    manager.find()
    assert reference.find_widget.isVisible()
    assert reference.find_widget.editor is first.markdown_page.browser

@pytest.mark.parametrize('secondary', [False, True])
def test_markdown_preview_preserves_source_and_shared_undo(reference, editor_plugin, qtbot, tmp_path, secondary):
    from spyder.api.translations import _
    manager = editor_plugin.get_widget()
    filename = tmp_path / 'guide.md'
    text = '# Guide\n\nA **bold** paragraph.\n\n| Key | Value |\n| --- | --- |\n| x | 42 |\n'
    filename.write_text(text, encoding='utf-8')
    manager.load(str(filename))
    if secondary:
        reference.load(str(filename))
    stack = reference.splitter.editorstack if secondary else manager.editorstacks[0]
    editor = stack.get_current_editor()
    editor.insert_text('Unsaved\n\n')
    original = editor.toPlainText()
    document = editor.document()
    assert not hasattr(editor, 'markdown_page')
    assert stack.markdown_button.text() == _('Preview')
    qtbot.mouseClick(stack.markdown_button, Qt.LeftButton)
    browser = stack.get_current_view()
    assert browser is not editor and browser.isReadOnly()
    assert stack.markdown_button.text() == _('Source code')
    assert 'Guide' in browser.toPlainText() and '42' in browser.toPlainText()
    assert '**bold**' not in browser.toPlainText()
    assert 'guide' in browser.document().find('Guide').charFormat().anchorNames()
    assert editor.toPlainText() == original and editor.document() is document
    assert filename.read_text(encoding='utf-8') == text
    assert stack.find_widget.editor is browser
    other = tmp_path / 'other.md'
    other.write_text('# Other\n', encoding='utf-8')
    manager.load(str(other), editorwindow=reference if secondary else manager)
    assert stack.markdown_button.text() == _('Preview')
    stack.set_current_filename(str(filename))
    assert stack.get_current_view() is browser
    assert stack.markdown_button.text() == _('Source code')
    qtbot.mouseClick(stack.markdown_button, Qt.LeftButton)
    assert stack.get_current_view() is editor
    assert stack.markdown_button.text() == _('Preview')
    editor.undo()
    assert editor.toPlainText() == text


@pytest.mark.parametrize('secondary', [False, True])
def test_markdown_preview_bounds_large_pages_without_changing_source(
        reference, editor_plugin, qtbot, tmp_path, secondary):
    filename = tmp_path / 'large.md'
    text = ('# Heading\n\nA paragraph with **bold** text.\n\n' * 5000)
    filename.write_text(text, encoding='utf-8')
    editor_plugin.get_widget().load(str(filename))
    if secondary:
        reference.load(str(filename))
    stack = (reference.splitter.editorstack if secondary
             else editor_plugin.get_widget().editorstacks[0])
    stack.set_markdown_preview(True)
    QApplication.processEvents()
    page = stack.get_current_editor().markdown_page
    assert 0 < page.page_end <= 50000
    assert page.next_page.isVisible()
    assert page.position.text() == '1'
    # Pagination belongs to the existing tab header, not a second bottom row.
    assert page.next_page.mapTo(stack, page.next_page.rect().center()).y() < page.mapTo(stack, page.rect().topLeft()).y()
    assert page.browser.height() >= page.currentWidget().height() - 2
    first_end = page.page_end
    page.next_page.click()
    assert page.page_start == first_end
    assert page.position.text() == '2'
    page.previous_page.click()
    assert page.page_start == 0
    assert stack.get_current_editor().toPlainText() == text
    stack.set_markdown_preview(False)
    assert not page.navigation.isVisible()
    stack.set_markdown_preview(True)
    assert page.navigation.isVisible()
    short = tmp_path / 'short.md'
    short.write_text('# Short\n', encoding='utf-8')
    if secondary:
        reference.load(str(short))
    else:
        editor_plugin.get_widget().load(str(short))
    stack.set_markdown_preview(True)
    assert not page.navigation.isVisible()
    assert not stack.markdown_navigation.isVisible()
    stack.set_current_filename(str(filename))
    assert page.navigation.isVisible()
    destroyed = []
    page.navigation.destroyed.connect(lambda: destroyed.append(True))
    stack.close_file(stack.has_filename(str(filename)))
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    qtbot.waitUntil(lambda: bool(destroyed))
    assert not stack.markdown_navigation.isVisible()


def test_preview_releases_replaced_documents(editor_plugin, tmp_path):
    filename = tmp_path / 'release.md'
    filename.write_text('# First\n', encoding='utf-8')
    manager = editor_plugin.get_widget()
    manager.load(str(filename))
    stack = manager.editorstacks[0]
    stack.set_markdown_preview(True)
    page = stack.get_current_editor().markdown_page
    destroyed = []
    for index in range(4):
        page.browser.document().destroyed.connect(lambda: destroyed.append(True))
        page.editor.insert_text(f'Update {index}\n')
        page.render()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    assert len(destroyed) == 4


def test_preview_split_close_rebinds_search(reference, editor_plugin, tmp_path):
    filename = tmp_path / 'split-preview.md'
    filename.write_text('# Visible **preview**\n', encoding='utf-8')
    manager = editor_plugin.get_widget()
    manager.load(str(filename))
    primary = manager.editorstacks[0]
    primary.set_markdown_preview(True)
    reference.load(str(filename))
    reference.splitter.split(Qt.Horizontal)
    child = reference.splitter.widget(1).editorstack
    child.set_markdown_preview(True)
    manager.set_last_focused_editorstack(reference, child)
    child.close()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    assert reference.find_widget.editor is reference.splitter.editorstack.get_current_view()
    assert manager.find_widget.editor is primary.get_current_view()


def test_markdown_preview_resources_are_local_images_only(reference, editor_plugin, tmp_path):
    from qtpy.QtCore import QUrl
    from qtpy.QtGui import QImage, QTextDocument
    filename = tmp_path / 'images.md'
    filename.write_text('![Test](image.png)\n', encoding='utf-8')
    image = QImage(16, 16, QImage.Format_RGB32)
    image.fill(Qt.red)
    image.save(str(tmp_path / 'image.png'))
    editor_plugin.get_widget().load(str(filename))
    stack = editor_plugin.get_widget().editorstacks[0]
    stack.set_markdown_preview(True)
    browser = stack.get_current_view()
    assert not browser.loadResource(QTextDocument.ImageResource, QUrl('image.png')).isNull()
    assert browser.loadResource(QTextDocument.ImageResource, QUrl('https://example.com/image.png')) is None
    assert browser.loadResource(QTextDocument.ImageResource, QUrl('file://server/share/image.png')) is None
    assert browser.loadResource(QTextDocument.StyleSheetResource, QUrl('image.png')) is None
    browser.resource_bytes = 64 * 1024 ** 2
    assert browser.loadResource(QTextDocument.ImageResource, QUrl('image.png')) is None


def test_markdown_image_budget_counts_high_bit_depth(qtbot, monkeypatch, tmp_path):
    from qtpy.QtCore import QUrl
    from qtpy.QtGui import QImage, QTextDocument
    from spyder.plugins.editor.widgets import markdown
    image = QImage(2, 2, QImage.Format_RGBA64)
    image.fill(Qt.red)
    filename = tmp_path / 'high-depth.png'
    assert image.save(str(filename))
    decoded = []
    class ObservedReader(markdown.QImageReader):
        def read(self):
            decoded.append(True)
            return super().read()
    monkeypatch.setattr(markdown, 'QImageReader', ObservedReader)
    browser = markdown.MarkdownBrowser(None)
    qtbot.addWidget(browser)
    browser.resource_bytes = 64 * 1024 ** 2 - 24
    assert browser.loadResource(QTextDocument.ImageResource, QUrl.fromLocalFile(str(filename))) is None
    assert not decoded


@pytest.mark.parametrize('titles, anchors', [
    (['a', 'a-1', 'a'], ['a', 'a-1', 'a-2']),
    (['a', 'a', 'a-1'], ['a', 'a-1', 'a-1-1']),
])
def test_markdown_heading_anchors_are_unique(editor_plugin, tmp_path, titles, anchors):
    from qtpy.QtGui import QTextCursor
    filename = tmp_path / 'anchors.md'
    filename.write_text('\n\n'.join('# ' + title for title in titles), encoding='utf-8')
    manager = editor_plugin.get_widget()
    manager.load(str(filename))
    stack = manager.editorstacks[0]
    stack.set_markdown_preview(True)
    block = stack.get_current_view().document().begin()
    actual = []
    while block.isValid():
        if block.blockFormat().headingLevel():
            actual.extend(QTextCursor(block).charFormat().anchorNames())
        block = block.next()
    assert actual == anchors


@pytest.mark.parametrize('hard_break', ['\\', '  '])
def test_markdown_outline_after_multiline_heading_targets_correct_block(
        editor_plugin, tmp_path, hard_break):
    from spyder.plugins.outlineexplorer.markdown import markdown_symbols
    filename = tmp_path / 'multiline.md'
    text = f'First{hard_break}\nsecond\n==========\n\n# Target\n'
    filename.write_text(text, encoding='utf-8')
    manager = editor_plugin.get_widget()
    manager.load(str(filename))
    stack = manager.editorstacks[0]
    stack.set_markdown_preview(True)
    page = stack.get_current_editor().markdown_page
    assert page.go_to_heading(5)
    assert stack.get_current_view() is page.browser
    assert page.browser.textCursor().block().text() == 'Target'
    assert markdown_symbols(text)[0].name == 'First second'


@pytest.mark.parametrize('change', ['edit', 'page'])
def test_markdown_render_refreshes_visible_search_count(editor_plugin, tmp_path, change):
    from spyder.api.translations import _
    filename = tmp_path / 'matches.md'
    text = '# First\n\nneedle\n\n'
    if change == 'page':
        text += 'padding\n\n' * 600 + '# Second\n\nneedle needle\n'
    filename.write_text(text, encoding='utf-8')
    manager = editor_plugin.get_widget()
    manager.load(str(filename))
    stack = manager.editorstacks[0]
    stack.set_markdown_preview(True)
    page = stack.get_current_editor().markdown_page
    find = stack.find_widget
    find.show()
    find.search_text.setEditText('needle')
    assert find.find()
    if change == 'edit':
        page.editor.set_text('# Changed\n\nneedle needle\n')
        page.render()
    else:
        page.next_page.click()
    assert find.matches_string == f"2 {_('matches')}"
    assert not page.browser.textCursor().hasSelection()


@pytest.mark.parametrize('secondary', [False, True])
def test_markdown_outline_navigation_keeps_preview_and_finds_exact_heading(
        reference, editor_plugin, tmp_path, secondary):
    manager = editor_plugin.get_widget()
    filename = tmp_path / 'heading-navigation.md'
    lines = ['# Repeated **title**', '', 'FIRST occurrence 😀', '',
             '```markdown', '# Repeated **title**', '```', '']
    lines += ['Paragraph 😀 with enough text to exercise pagination.', ''] * 850
    second_line = len(lines) + 1
    lines += ['Repeated **title**', '==================', '', 'SECOND occurrence', '']
    lines += ['More text.', ''] * 60
    third_line = len(lines) + 1
    lines += ['# Repeated **title**', '', 'THIRD occurrence', '']
    text = '\n'.join(lines)
    filename.write_text(text, encoding='utf-8-sig')
    manager.load(str(filename))
    if secondary:
        reference.load(str(filename))
    stack = reference.splitter.editorstack if secondary else manager.editorstacks[0]
    other = manager.editorstacks[0] if secondary else None
    loaded = stack.get_current_editor().toPlainText()
    loaded_exactly = loaded == text
    assert loaded_exactly, (len(loaded), len(text), repr(loaded[:80]), repr(text[:80]))
    stack.set_markdown_preview(True)
    page = stack.get_current_editor().markdown_page
    source_document = stack.get_current_editor().document()
    for line, occurrence in [(second_line, 'SECOND'), (third_line, 'THIRD'), (1, 'FIRST')]:
        if secondary:
            reference.load(str(filename), goto=line, word='Repeated title', from_outline=True)
        else:
            editor_plugin.load_edit_goto(str(filename), line, 'Repeated title')
        assert stack.get_current_view() is page.browser
        heading = page.browser.textCursor().block()
        assert heading.text() == 'Repeated title'
        assert heading.next().text().startswith(occurrence)
        assert page.page_start <= sum(len(item) + 1 for item in lines[:line - 1]) < page.page_end
        assert stack.get_current_editor().document() is source_document
        source_text = stack.get_current_editor().toPlainText()
        source_unchanged = source_text == text
        assert source_unchanged, (len(source_text), len(text), repr(source_text[:80]), repr(text[:80]))
        assert not source_document.isModified()
        if other is not None:
            assert other.get_current_view() is other.get_current_editor()
    manager.load(str(filename), goto=second_line, editorwindow=reference if secondary else manager)
    assert stack.get_current_view() is stack.get_current_editor()
    assert stack.get_current_editor().get_cursor_line_number() == second_line


def test_markdown_outline_parses_real_headings_and_section_ranges():
    from spyder.plugins.outlineexplorer.markdown import markdown_symbols
    text = ('# **Guide**\n\n## [Usage](https://example.com)\n\n'
            '```md\n# Not a heading\n```\n\n'
            'Details\n-------\n\n### 中文 `code`\n\n# End\n')
    symbols = markdown_symbols(text)
    assert [item.name for item in symbols] == ['Guide', 'Usage', 'Details', '中文 code', 'End']
    assert [(item.range.start.line, item.range.end.line)
            for item in symbols] == [(0, 12), (2, 7), (8, 12), (11, 12), (13, 14)]
    assert markdown_symbols('[Guide][ref]\n=====\n\n[ref]: https://example.com\n')[0].name == 'Guide'


def test_markdown_outline_overflow_opens_source(editor_plugin, tmp_path):
    from spyder.plugins.outlineexplorer.markdown import markdown_symbols
    filename = tmp_path / 'many-headings.md'
    text = '# Heading\n' * 2100
    filename.write_text(text, encoding='utf-8')
    manager = editor_plugin.get_widget()
    manager.load(str(filename))
    stack = manager.editorstacks[0]
    editor = stack.get_current_editor()
    editor.oe_proxy.info = markdown_symbols(text)
    assert len(editor.oe_proxy.info) == 2001
    stack.set_markdown_preview(True)
    line = editor.oe_proxy.info[-1].range.start.line + 1
    editor_plugin.load_edit_goto(str(filename), line, '')
    assert stack.get_current_view() is editor
    assert editor.get_cursor_line_number() == line


def test_markdown_outline_discards_stale_results(reference, editor_plugin, qtbot, tmp_path, monkeypatch):
    from threading import Event
    from spyder.plugins.outlineexplorer import markdown
    parser = markdown.markdown_symbols
    started, release = Event(), Event()
    calls = []
    def delayed_parser(text):
        calls.append(text)
        if len(calls) == 1:
            started.set()
            release.wait(3)
        return parser(text)
    monkeypatch.setattr(markdown, 'markdown_symbols', delayed_parser)
    filename = tmp_path / 'stale.md'
    filename.write_text('# Old\n', encoding='utf-8')
    manager = editor_plugin.get_widget()
    manager.outlineexplorer.treewidget.is_visible = True
    manager.load(str(filename))
    editor = manager.editorstacks[0].get_current_editor()
    updates = []
    editor.oe_proxy.sig_outline_explorer_data_changed.connect(
        lambda symbols: updates.append([item.name for item in symbols]))
    try:
        qtbot.waitUntil(started.is_set)
        editor.setPlainText('# New\n')
        editor.oe_proxy.request_symbols()
        qtbot.wait(500)
        assert calls == ['# Old\n']
        release.set()
        qtbot.waitUntil(lambda: ['New'] in updates)
        assert ['Old'] not in updates
    finally:
        release.set()
