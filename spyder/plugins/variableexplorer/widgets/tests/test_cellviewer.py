"""Cell inspection must preserve values and avoid eager nested rendering."""
import json
from unittest.mock import Mock, patch

import numpy as np
from pandas import DataFrame
import pytest
from qtpy.QtCore import QEvent, QPoint, QPointF, QRect, Qt
from qtpy.QtGui import (
    QDesktopServices, QKeySequence, QMouseEvent, QTextCursor, QTextDocument,
    QTextTable, QWheelEvent,
)
from qtpy.QtTest import QTest
from qtpy.QtWidgets import QApplication, QLineEdit, QTextBrowser

from spyder.plugins.variableexplorer.widgets.dataframeeditor import DataFrameEditor
from spyder.plugins.variableexplorer.widgets.cellviewer import CellViewer


@pytest.fixture
def copied_text(monkeypatch):
    """Capture the OS boundary without changing cell serialization or clicks."""
    clipboard = Mock()
    monkeypatch.setattr(QApplication, 'clipboard', lambda: clipboard)
    return clipboard.setText


def test_markdown_and_raw_are_separate(qtbot):
    text = '# 项目\n\n**重点**与 `code`\n\n- 一\n- 二\n\n| 字段 | 值 |\n| --- | --- |\n| 用户 | 1200 |'
    viewer = CellViewer(text, 'application_content')
    qtbot.addWidget(viewer)
    assert viewer.raw.toPlainText() == text
    viewer.tabs.setCurrentWidget(viewer.preview)
    assert '项目' in viewer.preview.toPlainText()
    assert '**重点**' not in viewer.preview.toPlainText()
    assert viewer.raw.toPlainText() == text
    assert viewer.preview.font().pointSizeF() > viewer.font().pointSizeF()
    document = viewer.preview.document()
    assert document.find('重点').charFormat().fontWeight() > document.find('与').charFormat().fontWeight()
    assert document.find('与').blockFormat().lineHeight() >= 140
    assert any(isinstance(frame, QTextTable)
               for frame in document.rootFrame().childFrames())
    assert viewer.preview.toPlainText().rstrip().endswith('1200')
    assert not viewer.load_more.isEnabled()


@pytest.mark.parametrize('address, allowed', [
    ('https://example.org/video?id=123#details', True),
    ('http://example.org/docs', True),
    ('file:///C:/private.txt', False),
    ('javascript:alert%281%29', False),
    ('data:text/plain,private', False),
    ('custom://application/open', False),
    ('https:missing-host', False),
])
def test_markdown_click_opens_only_web_links(qtbot, monkeypatch, address, allowed):
    text = f'[Open link]({address})'
    viewer = CellViewer(text)
    qtbot.addWidget(viewer)
    viewer.tabs.setCurrentWidget(viewer.preview)
    viewer.show()
    opened = []
    monkeypatch.setattr(QDesktopServices, 'openUrl', lambda url: opened.append(url.toString()) or True)
    cursor = viewer.preview.document().find('Open link')
    cursor.setPosition(cursor.selectionStart() + 2)
    point = viewer.preview.cursorRect(cursor).center()
    assert viewer.preview.anchorAt(point) == address
    with qtbot.waitSignal(viewer.preview.anchorClicked):
        qtbot.mouseClick(viewer.preview.viewport(), Qt.LeftButton, pos=point)
    assert opened == ([address] if allowed else [])
    assert viewer.raw.toPlainText() == text
    assert viewer.preview.toPlainText() == 'Open link'


def test_json_tree_keeps_types_and_nested_text(qtbot):
    viewer = CellViewer('{"name":"中文", "nested":{"enabled":true}}')
    qtbot.addWidget(viewer)
    assert viewer.tabs.currentWidget() is viewer.tree
    root = viewer.tree.topLevelItem(0)
    viewer.tree.expandItem(root)
    nested = root.child(1)
    viewer.tree.expandItem(nested)
    assert nested.child(0).text(1) == 'True'
    assert nested.child(0).text(2) == 'bool'


def test_scrolling_a_float_array_loads_the_visible_continuation(qtbot):
    viewer = CellViewer(np.arange(650, dtype=np.float32))
    qtbot.addWidget(viewer)
    viewer.show()
    root = viewer.tree.topLevelItem(0)
    first = root.child(0)
    for _ in range(40):
        event = QWheelEvent(QPointF(50, 100),
                            QPointF(viewer.tree.viewport().mapToGlobal(QPoint(50, 100))), QPoint(),
                            QPoint(0, -12000), Qt.NoButton, Qt.NoModifier,
                            Qt.NoScrollPhase, False)
        QApplication.sendEvent(viewer.tree.viewport(), event)
        QApplication.processEvents()
    assert root.childCount() == 650
    assert root.entries is None
    assert root.child(0) is first
    assert [root.child(index).value for index in range(650)] == list(range(650))


def test_load_all_finishes_one_list_without_recursively_expanding_children(qtbot):
    viewer = CellViewer({'items': [{'value': index} for index in range(12000)]})
    qtbot.addWidget(viewer)
    viewer.show()
    items = viewer.tree.topLevelItem(0).child(0)
    viewer.tree.expandItem(items)
    viewer.tree.setCurrentItem(items)
    viewer.tree.scrollToBottom()
    qtbot.mouseClick(viewer.load_all_button, Qt.LeftButton)
    assert items.childCount() < 12000
    qtbot.waitUntil(lambda: not viewer.loading_timer.isActive(), timeout=10000)
    assert items.childCount() == 12000
    assert items.entries is None
    assert not items.child(0).isExpanded()
    assert items.child(0).childCount() == 1
    assert not viewer.status.isVisible()
    assert viewer.load_all_button.width() >= viewer.load_all_button.sizeHint().width()


def test_load_all_can_stop_and_resume_after_a_resource_pause(qtbot):
    viewer = CellViewer(list(range(3000)))
    qtbot.addWidget(viewer)
    viewer.show()
    viewer.tree_load_limit = 600
    root = viewer.tree.topLevelItem(0)
    qtbot.mouseClick(viewer.load_all_button, Qt.LeftButton)
    qtbot.waitUntil(lambda: not viewer.loading_timer.isActive())
    assert 200 < root.childCount() < 3000
    assert viewer.status.isVisible()
    assert 'paused' in viewer.status.text().lower()
    viewer.tree_load_limit = 100000
    qtbot.mouseClick(viewer.load_all_button, Qt.LeftButton)
    qtbot.mouseClick(viewer.load_all_button, Qt.LeftButton)
    stopped_count = root.childCount()
    qtbot.wait(40)
    assert root.childCount() == stopped_count
    assert not viewer.loading_timer.isActive()
    qtbot.mouseClick(viewer.load_all_button, Qt.LeftButton)
    qtbot.waitUntil(lambda: not viewer.loading_timer.isActive())
    assert root.childCount() == 3000
    assert not viewer.status.isVisible()


def test_leaving_or_collapsing_the_tree_cancels_list_loading(qtbot):
    viewer = CellViewer(list(range(10000)))
    qtbot.addWidget(viewer)
    viewer.show()
    root = viewer.tree.topLevelItem(0)
    viewer.tree.setCurrentItem(root.child(5))
    qtbot.mouseClick(viewer.load_all_button, Qt.LeftButton)
    assert viewer.loading_item is root
    viewer.tabs.setCurrentWidget(viewer.raw)
    assert not viewer.loading_timer.isActive()
    assert viewer.load_all_button.isHidden()
    viewer.tabs.setCurrentWidget(viewer.tree)
    qtbot.mouseClick(viewer.load_all_button, Qt.LeftButton)
    qtbot.mouseClick(viewer.collapse_button, Qt.LeftButton)
    assert not viewer.loading_timer.isActive()
    assert viewer.loading_item is None
    stopped_count = root.childCount()
    qtbot.wait(40)
    assert root.childCount() == stopped_count


def test_scrolling_after_a_load_pause_clears_the_completed_status(qtbot):
    viewer = CellViewer(list(range(500)))
    qtbot.addWidget(viewer)
    viewer.show()
    viewer.tree_load_limit = 200
    qtbot.mouseClick(viewer.load_all_button, Qt.LeftButton)
    qtbot.waitUntil(lambda: not viewer.loading_timer.isActive())
    assert viewer.status.isVisible()
    viewer.tree.scrollToBottom()
    QApplication.processEvents()
    assert viewer.tree.topLevelItem(0).entries is None
    assert viewer.status.isHidden()
    assert viewer.loading_item is None


def test_collapsing_a_loading_lists_ancestor_stops_hidden_work(qtbot):
    viewer = CellViewer({'outer': {'items': list(range(5000))}})
    qtbot.addWidget(viewer)
    viewer.show()
    outer = viewer.tree.topLevelItem(0).child(0)
    viewer.tree.expandItem(outer)
    items = outer.child(0)
    viewer.tree.expandItem(items)
    viewer.tree.setCurrentItem(items)
    qtbot.mouseClick(viewer.load_all_button, Qt.LeftButton)
    viewer.tree.collapseItem(outer)
    stopped_count = items.childCount()
    qtbot.waitUntil(lambda: not viewer.loading_timer.isActive())
    assert items.childCount() == stopped_count


@pytest.mark.parametrize('expanded', [False, True])
def test_list_load_budget_counts_nested_placeholder_nodes(qtbot, expanded):
    viewer = CellViewer({'items': [[index] for index in range(3000)]})
    qtbot.addWidget(viewer)
    viewer.show()
    items = viewer.tree.topLevelItem(0).child(0)
    if expanded:
        viewer.tree.expandItem(items)
    viewer.tree.setCurrentItem(items)
    viewer.tree_load_limit = 600
    flags = Qt.MatchContains | Qt.MatchRecursive
    before = len(viewer.tree.findItems('', flags))
    qtbot.mouseClick(viewer.load_all_button, Qt.LeftButton)
    qtbot.waitUntil(lambda: not viewer.loading_timer.isActive())
    assert len(viewer.tree.findItems('', flags)) - before == viewer.loading_work
    assert viewer.loading_work == 600


def test_large_text_is_not_silently_truncated(qtbot, copied_text):
    text = '内容\n' * 100000
    viewer = CellViewer(text)
    qtbot.addWidget(viewer)
    viewer.show()
    assert 0 < len(viewer.raw.toPlainText()) < len(text)
    assert not viewer.status.isHidden()
    viewer.copy_source()
    assert copied_text.call_args.args[0] == text
    assert viewer.raw.textCursor().position() == 0
    assert viewer.raw.verticalScrollBar().value() == 0
    while viewer.load_more.isEnabled():
        qtbot.mouseClick(viewer.load_more, Qt.LeftButton)
    assert viewer.raw.toPlainText() == text
    assert viewer.status.isHidden()
    assert '300000' in viewer.tabs.tabToolTip(0)


@pytest.mark.parametrize('text', ['', 'Text'])
def test_complete_text_counts_are_on_tabs_not_in_the_reading_footer(qtbot, text):
    viewer = CellViewer(text)
    qtbot.addWidget(viewer)
    for widget in (viewer.raw, viewer.preview, viewer.raw):
        viewer.tabs.setCurrentWidget(widget)
        assert viewer.status.isHidden()
        assert str(len(text)) in viewer.tabs.tabToolTip(viewer.tabs.currentIndex())
        assert not viewer.load_more.isEnabled()


@pytest.mark.parametrize('readonly', [False, True])
def test_double_click_opens_viewer_without_changing_dataframe(qtbot, readonly):
    value = '# 申请内容\n\n' + '详细说明' * 100
    frame = DataFrame({'content': [value]})
    editor = DataFrameEditor(readonly=readonly)
    qtbot.addWidget(editor)
    assert editor.setup_and_check(frame)
    editor.show()
    view = editor.dataTable
    index = view.model().index(0, 0)
    qtbot.mouseClick(view.viewport(), Qt.LeftButton, pos=view.visualRect(index).center())
    qtbot.mouseDClick(view.viewport(), Qt.LeftButton, pos=view.visualRect(index).center())
    qtbot.waitUntil(lambda: bool(view.findChildren(CellViewer)))
    viewer = view.findChildren(CellViewer)[0]
    assert viewer.raw.toPlainText() == value
    assert frame.iat[0, 0] == value
    viewer.close()


def test_polars_struct_cells(qtbot):
    polars = pytest.importorskip('polars')
    frame = polars.DataFrame({'details': [{'name': '项目', 'scores': [1, 2]}]})
    viewer = CellViewer(frame.item(0, 'details'))
    qtbot.addWidget(viewer)
    assert viewer.tree.topLevelItem(0).child(0).text(1) == '项目'


@pytest.mark.parametrize('converted', [False, True])
def test_polars_list_through_dataframe_double_click(qtbot, converted):
    polars = pytest.importorskip('polars')
    frame = polars.DataFrame({'items': [[{'name': '项目'}, {'name': '另一个'}]]})
    if converted:
        pytest.importorskip('pyarrow')
    value = frame.to_pandas().iat[0, 0] if converted else frame.item(0, 0)
    editor = DataFrameEditor()
    qtbot.addWidget(editor)
    assert editor.setup_and_check(DataFrame({'items': [value]}))
    editor.show()
    view = editor.dataTable
    position = view.visualRect(view.model().index(0, 0)).center()
    qtbot.mouseClick(view.viewport(), Qt.LeftButton, pos=position)
    qtbot.mouseDClick(view.viewport(), Qt.LeftButton, pos=position)
    qtbot.waitUntil(lambda: bool(view.findChildren(CellViewer)))
    viewer = view.findChildren(CellViewer)[0]
    root = viewer.tree.topLevelItem(0)
    assert root.childCount() == 2
    viewer.tree.expandItem(root.child(0))
    assert root.child(0).child(0).text(1) == '项目'
    viewer.close()


def test_nested_large_text_uses_bounded_preview(qtbot):
    value = {'text': 'x' * 2000000}
    viewer = CellViewer(value)
    qtbot.addWidget(viewer)
    assert viewer.status.isHidden()
    viewer.tabs.setCurrentWidget(viewer.raw)
    assert not viewer.status.isHidden()
    assert len(viewer.raw.toPlainText()) < 1000
    assert viewer.tree.topLevelItem(0).child(0).value == value['text']
    viewer.tabs.setCurrentWidget(viewer.tree)
    assert viewer.status.isHidden()


def test_manual_continuation_loads_another_batch(qtbot, copied_text):
    viewer = CellViewer(list(range(500)))
    qtbot.addWidget(viewer)
    root = viewer.tree.topLevelItem(0)
    viewer.tree.setCurrentItem(root.child(root.childCount() - 1))
    viewer.copy_source()
    copied_text.assert_not_called()
    viewer._inspect_item(root.child(root.childCount() - 1), 0)
    assert root.child(399).text(1) == '399'


@pytest.mark.parametrize('value, expected', [
    ('# 标题\n\n**完整内容**', '# 标题\n\n**完整内容**'),
    ({'comment': '完整字段值'}, '完整字段值'),
    (4.5, '4.5'),
])
def test_copy_click_preserves_source_or_selected_value(qtbot, copied_text, value, expected):
    viewer = CellViewer(value)
    qtbot.addWidget(viewer)
    viewer.show()
    if viewer.tree is not None:
        viewer.tree.setCurrentItem(viewer.tree.topLevelItem(0).child(0))
    elif viewer.preview is not None:
        viewer.tabs.setCurrentWidget(viewer.preview)
    button = viewer.copy_button
    original = button.icon().pixmap(24, 24).toImage()
    qtbot.mouseClick(button, Qt.LeftButton)
    assert copied_text.call_args.args[0] == expected
    assert button.icon().pixmap(24, 24).toImage() != original


def test_copy_feedback_restarts_and_restores_icon(qtbot, copied_text):
    viewer = CellViewer('text')
    qtbot.addWidget(viewer)
    viewer.show()
    button = viewer.copy_button
    original = button.icon().pixmap(24, 24).toImage()
    with patch.object(viewer.copy_timer, 'start', wraps=viewer.copy_timer.start) as restart:
        qtbot.mouseClick(button, Qt.LeftButton)
        qtbot.mouseClick(button, Qt.LeftButton)
    assert restart.call_count == 2
    assert button.icon().pixmap(24, 24).toImage() != original
    viewer.copy_timer.stop()
    viewer.copy_timer.timeout.emit()
    assert button.icon().pixmap(24, 24).toImage() == original


def test_system_clipboard_receives_copied_text(qtbot):
    viewer = CellViewer('clipboard integration')
    qtbot.addWidget(viewer)
    viewer.copy_source()
    assert QApplication.clipboard().text() == 'clipboard integration'


@pytest.mark.parametrize('markdown', [False, True])
def test_native_find_supports_regex_and_both_directions(qtbot, markdown):
    viewer = CellViewer('# Heading\n\n**Target1** other Target22 target33')
    qtbot.addWidget(viewer)
    editor = viewer.preview if markdown else viewer.raw
    viewer.tabs.setCurrentWidget(editor)
    finder = viewer.find_widget
    assert finder.editor is editor
    finder.search_text.setEditText(r'Target\d+')
    finder.re_button.setChecked(True)
    finder.case_button.setChecked(True)
    editor.moveCursor(QTextCursor.Start)
    for find, expected in [(finder.find_next, 'Target1'), (finder.find_next, 'Target22'),
                           (finder.find_previous, 'Target1')]:
        assert find(set_focus=False)
        assert editor.textCursor().selectedText() == expected
    assert editor.get_number_matches('Target', case=True) == 2
    assert editor.isReadOnly()


@pytest.mark.parametrize('markdown', [False, True])
def test_replace_shortcut_cannot_change_readonly_cell_text(qtbot, markdown):
    text = 'target and target'
    viewer = CellViewer(text)
    qtbot.addWidget(viewer)
    editor = viewer.preview if markdown else viewer.raw
    viewer.tabs.setCurrentWidget(editor)
    viewer.show()
    viewer.activateWindow()
    qtbot.waitUntil(viewer.isActiveWindow)
    editor.setFocus()
    qtbot.waitUntil(editor.hasFocus)
    viewer.find_widget.search_text.setEditText('target')
    QTest.keySequence(editor, QKeySequence(viewer.find_widget.get_shortcut('replace all')))
    assert editor.toPlainText() == text
    assert viewer.value == text


@pytest.mark.parametrize('markdown', [False, True])
def test_find_highlights_all_matches_and_clears_on_tab_or_hide(qtbot, markdown):
    viewer = CellViewer('# 项目\n\n😀 项目与项目\n\nProject project projects\n\n项目')
    qtbot.addWidget(viewer)
    viewer.show()
    if markdown:
        viewer.tabs.setCurrentWidget(viewer.preview)
    finder = viewer.find_widget
    finder.show()
    editor = finder.editor
    original = editor.toPlainText()
    finder.search_text.setEditText('项目')
    finder.find()
    assert [item.cursor.selectedText() for item in editor.extraSelections()] == ['项目'] * 4
    assert editor.textCursor().selectedText() == '项目'
    finder.words_button.setChecked(True)
    assert [item.cursor.selectedText() for item in editor.extraSelections()] == ['项目'] * 2
    finder.words_button.setChecked(False)
    finder.search_text.setEditText('project')
    finder.find()
    assert len(editor.extraSelections()) == 3
    finder.case_button.setChecked(True)
    assert len(editor.extraSelections()) == 2
    finder.words_button.setChecked(True)
    assert [item.cursor.selectedText() for item in editor.extraSelections()] == ['project']
    finder.words_button.setChecked(False)
    finder.re_button.setChecked(True)
    finder.search_text.setEditText(r'项目|[Pp]roject\b')
    finder.find()
    assert len(editor.extraSelections()) == 6
    finder.search_text.setEditText('😀')
    finder.find()
    assert [item.cursor.selectedText() for item in editor.extraSelections()] == ['😀']
    finder.search_text.setEditText(r'项目\n+😀')
    finder.find()
    assert len(editor.extraSelections()) == 1
    finder.search_text.setEditText('[')
    finder.find()
    assert not editor.extraSelections()
    finder.re_button.setChecked(False)
    finder.search_text.setEditText('')
    qtbot.keyClicks(finder.search_text.lineEdit(), 'project')
    qtbot.waitUntil(lambda: len(editor.extraSelections()) == 2)
    viewer.tabs.setCurrentWidget(viewer.raw if markdown else viewer.preview)
    assert not editor.extraSelections()
    assert len(finder.editor.extraSelections()) == 2
    finder.search_text.setEditText('')
    finder.find()
    assert not finder.editor.extraSelections()
    finder.search_text.setEditText('project')
    finder.find()
    finder.hide()
    assert not finder.editor.extraSelections()
    assert editor.toPlainText() == original


def test_find_shortcut_on_tree_focuses_loaded_field_search(qtbot):
    viewer = CellViewer({'name': 'Target'})
    qtbot.addWidget(viewer)
    viewer.show()
    viewer.activateWindow()
    qtbot.waitUntil(viewer.isActiveWindow)
    viewer.tree.setFocus()
    qtbot.waitUntil(viewer.tree.hasFocus)
    QTest.keySequence(viewer.tree, QKeySequence(viewer.find_widget.get_shortcut('find text')))
    qtbot.waitUntil(viewer.search.hasFocus)
    assert not viewer.find_widget.isVisible()
    viewer.search.setText('name')
    viewer.find_next()
    assert viewer.tree.currentItem().text(0) == 'name'
    viewer.find_widget.find_next(set_focus=False)
    assert viewer.tree.currentItem().text(0) == 'name'
    viewer.find_widget.find_previous(set_focus=False)
    assert viewer.tree.currentItem().text(0) == 'name'


def test_reader_layout_keeps_actions_and_translated_tabs_in_tab_row(qtbot, monkeypatch):
    from spyder.plugins.variableexplorer.widgets import cellviewer
    monkeypatch.setattr(cellviewer, '_', lambda text: f'translated {text}')
    viewer = CellViewer('# Heading\n\nContent', 'application_content · row 0')
    qtbot.addWidget(viewer)
    viewer.show()
    viewer.resize(560, 500)
    qtbot.waitUntil(viewer.isVisible)
    assert viewer.tabs.cornerWidget(Qt.TopRightCorner) is not None
    assert not viewer.find_widget.isVisible()
    assert viewer.status.isHidden()
    assert viewer.raw.geometry().height() > viewer.height() * 0.65
    assert viewer.raw.isReadOnly()
    assert viewer.tabs.tabText(0) == 'translated Raw text'
    assert 'application_content · row 0' in viewer.windowTitle()


@pytest.mark.parametrize('column', [0, 1, 2])
def test_tree_columns_support_dragging_and_narrow_windows(qtbot, column):
    viewer = CellViewer({'name': '项目', 'rating': 4.5})
    qtbot.addWidget(viewer)
    viewer.show()
    viewer.resize(560, 500)
    qtbot.waitUntil(viewer.isVisible)
    header = viewer.tree.header()
    assert header.sectionViewportPosition(2) + header.sectionSize(2) <= viewer.tree.viewport().width()
    assert header.sectionSize(1) > header.sectionSize(2)
    for delta in (-40, 70):
        original = header.sectionSize(column)
        boundary = header.sectionViewportPosition(column) + original - 1
        start = QPoint(boundary, header.height() // 2)
        end = start + QPoint(delta, 0)
        qtbot.mousePress(header.viewport(), Qt.LeftButton, pos=start)
        QApplication.sendEvent(header.viewport(), QMouseEvent(
            QEvent.MouseMove, QPointF(end), Qt.NoButton, Qt.LeftButton, Qt.NoModifier))
        qtbot.mouseRelease(header.viewport(), Qt.LeftButton, pos=end)
        assert abs(header.sectionSize(column) - (original + delta)) <= 1
    if column == 1:
        widths = [header.sectionSize(index) for index in range(3)]
        viewer.tree.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        qtbot.waitUntil(viewer.tree.verticalScrollBar().isVisible)
        assert [header.sectionSize(index) for index in range(3)] == widths
    field_width, type_width = header.sectionSize(0), header.sectionSize(2)
    viewer.resize(1000, 500)
    qtbot.waitUntil(lambda: viewer.width() == 1000)
    assert header.sectionSize(0) == field_width
    assert header.sectionSize(2) == type_width
    assert abs(header.length() - viewer.tree.viewport().width()) <= 1


def test_tree_find_cycles_in_display_order_without_duplicate_rows(qtbot):
    viewer = CellViewer({'target': 'target', 'other': 'target'})
    qtbot.addWidget(viewer)
    viewer.search.setText('target')
    rows = []
    for _ in range(3):
        viewer.find_next()
        rows.append(viewer.tree.currentItem().text(0))
    assert rows == ['target', 'other', 'target']


def test_tree_keeps_long_keys_and_searches_full_loaded_values(qtbot):
    key = 'long key ' * 40 + '<b>literal</b>'
    viewer = CellViewer({'long': 'x' * 400 + 'needle', 'short': 'needle', key: {'child': 1}})
    qtbot.addWidget(viewer)
    viewer.search.setText('needle')
    viewer.find_next()
    assert viewer.tree.currentItem().text(0) == 'long'
    viewer.find_next()
    assert viewer.tree.currentItem().text(0) == 'short'
    document = QTextDocument()
    document.setHtml(viewer.tree.topLevelItem(0).child(2).toolTip(0))
    assert document.toPlainText() == key


@pytest.mark.parametrize('field', [
    '请描述一次你打破常规并付诸实践的经历',
    '为什么会选这个想法来做项目？这个想法是从哪里来的？你在这个行业有什么专业知识？' * 2,
    'long_json_field_without_spaces_' * 8 + '<b>literal</b>',
])
def test_container_double_click_opens_leaf_with_complete_field(qtbot, field):
    from spyder.utils.stylesheet import APP_STYLESHEET, AppStyle
    viewer = CellViewer({'nested': {field: 'details'}})
    qtbot.addWidget(viewer)
    viewer.setStyleSheet(APP_STYLESHEET.to_string())
    viewer.show()
    container = viewer.tree.topLevelItem(0).child(0)
    position = viewer.tree.visualItemRect(container).center()
    qtbot.mouseClick(viewer.tree.viewport(), Qt.LeftButton, pos=position)
    qtbot.mouseDClick(viewer.tree.viewport(), Qt.LeftButton, pos=position)
    assert container.isExpanded()
    assert not viewer.findChildren(CellViewer)
    leaf = container.child(0)
    position = viewer.tree.visualItemRect(leaf).center()
    qtbot.mouseClick(viewer.tree.viewport(), Qt.LeftButton, pos=position)
    qtbot.mouseDClick(viewer.tree.viewport(), Qt.LeftButton, pos=position)
    assert len(viewer.findChildren(CellViewer)) == 1
    child = viewer.findChildren(CellViewer)[0]
    child.resize(560, 500)
    qtbot.waitUntil(child.isVisible)
    heading = child.layout().itemAt(0).widget()
    assert isinstance(heading, QTextBrowser)
    assert heading.toPlainText() == field
    assert heading.isReadOnly()
    assert heading.textInteractionFlags() & Qt.TextSelectableByMouse
    assert child.width() == 560
    height_limit = 4 * heading.fontMetrics().lineSpacing() + 2 * AppStyle.MarginSize + 2
    assert heading.height() <= height_limit
    if heading.document().size().height() <= height_limit - 2:
        assert heading.verticalScrollBar().maximum() == 0
        assert heading.viewport().height() >= heading.document().size().height()
    lines = heading.document().firstBlock().layout()
    assert all(lines.lineAt(index).naturalTextWidth() <= heading.viewport().width() + 1
               for index in range(lines.lineCount()))
    heading.selectAll()
    assert heading.textCursor().selectedText() == field
    assert child.raw.toPlainText() == 'details'


def test_window_fits_small_available_screen(qtbot, monkeypatch):
    from types import SimpleNamespace
    viewer = CellViewer('text')
    qtbot.addWidget(viewer)
    available = QRect(0, 0, 800, 600)
    monkeypatch.setattr(viewer, 'screen', lambda: SimpleNamespace(availableGeometry=lambda: available))
    viewer.show()
    assert available.contains(viewer.frameGeometry())


def test_long_json_is_parsed_only_on_request(qtbot):
    text = json.dumps({'text': 'x' * 200001})
    viewer = CellViewer(text)
    qtbot.addWidget(viewer)
    assert viewer.raw.toPlainText() != text
    assert viewer.tree is not None
    viewer.tabs.setCurrentWidget(viewer.tree)
    assert viewer.tree.topLevelItemCount() == 0
    assert viewer.expand_button.isHidden()
    qtbot.mouseClick(viewer.load_more, Qt.LeftButton)
    root = viewer.tree.topLevelItem(0)
    assert root.child(0).value == 'x' * 200001
    assert not viewer.expand_button.isHidden()
    assert viewer.value == text


def test_long_markdown_pages_reach_the_end_without_accumulating_text(qtbot):
    viewer = CellViewer('[Link](https://example.com)\n\n' + 'text ' * 40001 + '\n\n**ending**')
    qtbot.addWidget(viewer)
    viewer.tabs.setCurrentWidget(viewer.preview)
    assert 'Link' in viewer.preview.toPlainText()
    assert 'ending' not in viewer.preview.toPlainText()
    qtbot.mouseClick(viewer.load_more, Qt.LeftButton)
    assert 'ending' in viewer.preview.toPlainText()
    assert '**ending**' not in viewer.preview.toPlainText()
    assert 'Link' not in viewer.preview.toPlainText()
    assert len(viewer.preview.toPlainText()) < 200000
    assert not viewer.load_more.isEnabled()
    qtbot.mouseClick(viewer.previous_page, Qt.LeftButton)
    assert 'Link' in viewer.preview.toPlainText()
    assert 'ending' not in viewer.preview.toPlainText()
    assert not viewer.status.isHidden()


def test_markdown_with_many_paragraphs_keeps_each_page_bounded(qtbot):
    viewer = CellViewer('paragraph\n\n' * 10000)
    qtbot.addWidget(viewer)
    viewer.show()
    viewer.tabs.setCurrentWidget(viewer.preview)
    assert viewer.preview.textCursor().position() == 0
    assert viewer.preview.verticalScrollBar().value() == 0
    assert viewer.preview.document().blockCount() <= 1000
    first_page = viewer.preview.toPlainText()
    qtbot.mouseClick(viewer.load_more, Qt.LeftButton)
    assert viewer.preview.document().blockCount() <= 1000
    qtbot.mouseClick(viewer.previous_page, Qt.LeftButton)
    assert viewer.preview.toPlainText() == first_page


def test_invalid_large_json_keeps_the_original_text_available(qtbot):
    text = '{"text": "' + 'x' * 200001
    viewer = CellViewer(text)
    qtbot.addWidget(viewer)
    viewer.tabs.setCurrentWidget(viewer.tree)
    qtbot.mouseClick(viewer.load_more, Qt.LeftButton)
    assert not viewer.load_more.isEnabled()
    assert 'Invalid JSON' in viewer.status.text()
    assert not viewer.status.isHidden()
    assert viewer.value == text
    viewer.tabs.setCurrentWidget(viewer.raw)
    assert viewer.raw.toPlainText() == text[:200000]


@pytest.mark.parametrize('value, replacement, expected', [('x' * 80, 'edited', 'edited'), (5, '12', 12)])
def test_double_click_keeps_native_editing_for_short_text_and_numbers(qtbot, value, replacement, expected):
    editor = DataFrameEditor()
    qtbot.addWidget(editor)
    assert editor.setup_and_check(DataFrame({'content': [value]}))
    editor.show()
    view = editor.dataTable
    position = view.visualRect(view.model().index(0, 0)).center()
    qtbot.mouseClick(view.viewport(), Qt.LeftButton, pos=position)
    qtbot.mouseDClick(view.viewport(), Qt.LeftButton, pos=position)
    assert not view.findChildren(CellViewer)
    field = view.findChild(QLineEdit)
    assert field is not None
    field.setText(replacement)
    qtbot.keyClick(field, Qt.Key_Return)
    qtbot.waitUntil(lambda: view.model().get_value(0, 0) == expected)


def test_context_edit_still_updates_long_text_cells(qtbot):
    editor = DataFrameEditor()
    qtbot.addWidget(editor)
    value = 'long text ' * 100
    assert editor.setup_and_check(DataFrame({'content': [value]}))
    editor.show()
    view = editor.dataTable
    view.setCurrentIndex(view.model().index(0, 0))
    view.edit_action.trigger()
    field = view.findChild(QLineEdit)
    assert field is not None
    assert field.text() == value
    qtbot.keyClick(field, Qt.Key_Return)
    assert view.model().get_value(0, 0) == value
    view.edit_action.trigger()
    field = view.findChild(QLineEdit)
    field.setText('edited text')
    qtbot.keyClick(field, Qt.Key_Return)
    qtbot.waitUntil(lambda: view.model().get_value(0, 0) == 'edited text')


def test_one_click_expands_nested_fields_and_collapses_all(qtbot):
    viewer = CellViewer([{'name': 'first', 'details': {'score': 1}}, {'items': list(range(450))}])
    qtbot.addWidget(viewer)
    viewer.show()
    qtbot.mouseClick(viewer.expand_button, Qt.LeftButton)
    qtbot.waitUntil(lambda: not viewer.expansion_timer.isActive())
    root = viewer.tree.topLevelItem(0)
    assert root.isExpanded()
    assert root.child(0).isExpanded()
    assert root.child(0).child(1).isExpanded()
    assert root.child(0).child(1).child(0).text(1) == '1'
    assert root.child(1).child(0).childCount() == 450
    assert root.child(1).child(0).entries is None
    qtbot.mouseClick(viewer.collapse_button, Qt.LeftButton)
    assert not root.isExpanded()
    assert not root.child(0).isExpanded()
    assert not root.child(0).child(1).isExpanded()
    viewer.tabs.setCurrentWidget(viewer.raw)
    assert not viewer.expand_button.isVisible()
    assert not viewer.collapse_button.isVisible()
    viewer.tabs.setCurrentWidget(viewer.tree)
    qtbot.mouseClick(viewer.expand_button, Qt.LeftButton)
    qtbot.waitUntil(lambda: not viewer.expansion_timer.isActive())
    assert root.child(0).child(1).isExpanded()


def test_leaving_structure_pauses_expansion_until_explicit_resume(qtbot):
    viewer = CellViewer(list(range(1000)))
    qtbot.addWidget(viewer)
    viewer.show()
    qtbot.mouseClick(viewer.expand_button, Qt.LeftButton)
    assert viewer.expansion_timer.isActive()
    viewer.tabs.setCurrentWidget(viewer.raw)
    assert not viewer.expansion_timer.isActive()
    root = viewer.tree.topLevelItem(0)
    count = root.childCount()
    qtbot.wait(40)
    assert root.childCount() == count
    viewer.tabs.setCurrentWidget(viewer.tree)
    assert not viewer.expansion_timer.isActive()
    assert viewer.expand_button.isEnabled()
    qtbot.mouseClick(viewer.expand_button, Qt.LeftButton)
    qtbot.waitUntil(lambda: not viewer.expansion_timer.isActive())
    assert root.childCount() == 1000
    assert root.entries is None


def test_bulk_expansion_pauses_and_collapse_cancels_pending_work(qtbot):
    viewer = CellViewer(list(range(20000)))
    qtbot.addWidget(viewer)
    viewer.show()
    qtbot.mouseClick(viewer.expand_button, Qt.LeftButton)
    qtbot.waitUntil(lambda: not viewer.expansion_timer.isActive())
    root = viewer.tree.topLevelItem(0)
    assert 200 < root.childCount() < 20000
    assert viewer.expansion_iterator is not None
    assert 'paused' in viewer.status.text().lower()
    assert viewer.status.isVisible()
    loaded = root.childCount()
    qtbot.mouseClick(viewer.expand_button, Qt.LeftButton)
    assert viewer.expansion_timer.isActive()
    qtbot.waitUntil(lambda: root.childCount() > loaded)
    qtbot.mouseClick(viewer.collapse_button, Qt.LeftButton)
    assert not viewer.expansion_timer.isActive()
    assert viewer.expansion_iterator is None
    assert not root.isExpanded()
    assert viewer.status.isHidden()


def test_deep_expansion_can_resume_and_cycle_references_stop(qtbot):
    deep = 1
    for _ in range(80):
        deep = {'child': deep}
    cycle = []
    cycle.append(cycle)
    viewer = CellViewer({'deep': deep, 'cycle': cycle})
    qtbot.addWidget(viewer)
    viewer.show()
    qtbot.mouseClick(viewer.expand_button, Qt.LeftButton)
    qtbot.waitUntil(lambda: not viewer.expansion_timer.isActive())
    assert viewer.expansion_iterator is not None
    for _ in range(4):
        if viewer.expansion_iterator is None:
            break
        qtbot.mouseClick(viewer.expand_button, Qt.LeftButton)
        qtbot.waitUntil(lambda: not viewer.expansion_timer.isActive())
    assert viewer.expansion_iterator is None
    root = viewer.tree.topLevelItem(0)
    assert root.child(1).child(0).childCount() == 0


@pytest.mark.parametrize('operation', ['expand', 'load'])
def test_closing_during_bulk_tree_work_releases_the_window(qtbot, copied_text, operation):
    viewer = CellViewer(list(range(20000)))
    # Explicit destruction below replaces qtbot's later close-on-teardown.
    viewer.show()
    qtbot.mouseClick(viewer.copy_button, Qt.LeftButton)
    assert viewer.copy_timer.isActive()
    qtbot.mouseClick(viewer.expand_button if operation == 'expand' else viewer.load_all_button, Qt.LeftButton)
    assert (viewer.expansion_timer if operation == 'expand' else viewer.loading_timer).isActive()
    with qtbot.waitSignal(viewer.destroyed):
        viewer.close()
