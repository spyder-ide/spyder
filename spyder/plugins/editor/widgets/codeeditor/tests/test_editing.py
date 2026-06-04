"""Tests for CodeEditor LSP text change buffering and merge behavior."""

from __future__ import annotations

import pytest
from lsprotocol import types as lsp
from qtpy.QtCore import QPoint, QPointF, QMimeData, Qt
from qtpy.QtGui import QDragEnterEvent, QDropEvent, QTextCursor

from spyder.plugins.editor.widgets.codeeditor.tests.conftest import (
    codeeditor_factory,
)


def create_lsp_editor(qtbot, text):
    editor = codeeditor_factory()
    qtbot.addWidget(editor)
    editor.show()

    with editor.suspend_undo_recording():
        editor.setPlainText(text)

    editor.clear_undo_stack()
    editor.clear_extra_cursors()
    editor.completions_available = True
    editor.filename = "test.py"
    editor.language = "Python"
    editor.sync_mode = lsp.TextDocumentSyncKind.Incremental
    editor.setFocus()
    return editor


def set_cursor(editor, position, anchor=None):
    cursor = QTextCursor(editor.document())
    cursor.setPosition(position)
    if anchor is not None:
        cursor.setPosition(anchor, QTextCursor.KeepAnchor)
    editor.setTextCursor(cursor)
    return cursor


def block_position(editor, line, column=0):
    block = editor.document().findBlockByNumber(line)
    return block.position() + column


def flush_document_change(editor, qtbot):
    editor._commit_pending_edit()
    editor._server_requests_timer.stop()

    with qtbot.waitSignal(editor.sig_perform_completion_request, timeout=1000) as blocker:
        editor._process_server_requests()

    assert blocker.args[1] == lsp.TEXT_DOCUMENT_DID_CHANGE
    payload = blocker.args[2]
    assert editor._pending_server_requests == []
    return payload


def change_signature(change):
    rng = change.range
    return (
        rng.start.line,
        rng.start.character,
        rng.end.line,
        rng.end.character,
        change.text,
    )


def resolve_position(editor, position):
    if isinstance(position, tuple):
        line, column = position
        return block_position(editor, line, column)
    return position


def apply_single_cursor_steps(editor, steps):
    cursor = editor.textCursor()
    for step in steps:
        kind = step[0]
        if kind == "move":
            cursor.setPosition(resolve_position(editor, step[1]))
        elif kind == "select":
            cursor.setPosition(resolve_position(editor, step[1]))
            cursor.setPosition(
                resolve_position(editor, step[2]), QTextCursor.KeepAnchor
            )
        elif kind == "insert":
            cursor.insertText(step[1])
        elif kind == "delete":
            cursor.deleteChar()
        elif kind == "backspace":
            cursor.deletePreviousChar()
        elif kind == "remove":
            cursor.removeSelectedText()
        else:
            raise ValueError(f"Unknown step kind: {kind}")
        editor.setTextCursor(cursor)


def set_multicursor_selections(editor, selections):
    cursors = []
    for start, end in selections:
        cursor = QTextCursor(editor.document())
        cursor.setPosition(resolve_position(editor, start))
        cursor.setPosition(resolve_position(editor, end), QTextCursor.KeepAnchor)
        cursors.append(cursor)

    editor.setTextCursor(cursors[-1])
    editor.extra_cursors = cursors[:-1]
    editor.set_extra_cursor_selections()


def assert_document_change(editor, qtbot, expected_text, expected_changes):
    payload = flush_document_change(editor, qtbot)

    assert editor.toPlainText() == expected_text
    assert payload["version"] == 1
    assert len(payload["content_changes"]) == len(expected_changes)
    assert [change_signature(change) for change in payload["content_changes"]] == expected_changes
    return payload


def test_document_did_change_merges_sequential_single_cursor_inserts(qtbot):
    editor = create_lsp_editor(qtbot, "abc")

    apply_single_cursor_steps(
        editor,
        [
            ("move", (0, 1)),
            ("insert", "x"),
            ("insert", "y"),
        ],
    )

    assert_document_change(
        editor,
        qtbot,
        "axybc",
        [(
        0,
        1,
        0,
        1,
        "xy",
        )],
    )


@pytest.mark.parametrize(
    "text,steps,expected_text,expected_changes",
    [
        (
            "",
            [("insert", "ab"), ("backspace",)],
            "a",
            [(0, 0, 0, 0, "a")],
        ),
        (
            "abc",
            [("move", (0, 1)), ("delete",), ("insert", "X")],
            "aXc",
            [(0, 1, 0, 2, "X")],
        ),
        (
            "abc\ndef\nghi\n",
            [("select", (1, 0), (1, 3)), ("insert", "D\nE")],
            "abc\nD\nE\nghi\n",
            [(1, 0, 1, 3, "D\nE")],
        ),
        (
            "abc\ndef\nghi\n",
            [("select", (1, 0), (2, 0)), ("remove",)],
            "abc\nghi\n",
            [(1, 0, 2, 0, "")],
        ),
        (
            "abc",
            [("move", (0, 2)), ("insert", "\n")],
            "ab\nc",
            [(0, 2, 0, 2, "\n")],
        ),
        (
            "abc\ndef\n",
            [("select", (0, 2), (1, 1)), ("insert", "Q")],
            "abQef\n",
            [(0, 2, 1, 1, "Q")],
        ),
    ],
)
def test_document_did_change_single_cursor_edit_combinations(
    qtbot, text, steps, expected_text, expected_changes
):
    editor = create_lsp_editor(qtbot, text)

    apply_single_cursor_steps(editor, steps)

    assert_document_change(editor, qtbot, expected_text, expected_changes)


def test_document_did_change_merges_insert_followed_by_backspace(qtbot):
    editor = create_lsp_editor(qtbot, "")

    apply_single_cursor_steps(editor, [("insert", "ab"), ("backspace",)])

    assert_document_change(editor, qtbot, "a", [(0, 0, 0, 0, "a")])


def test_document_did_change_merges_delete_then_insert_at_same_position(qtbot):
    editor = create_lsp_editor(qtbot, "abc")

    apply_single_cursor_steps(editor, [("move", (0, 1)), ("delete",), ("insert", "X")])

    assert_document_change(editor, qtbot, "aXc", [(0, 1, 0, 2, "X")])


def test_document_did_change_reports_multiline_replacement(qtbot):
    editor = create_lsp_editor(qtbot, "abc\ndef\nghi\n")

    apply_single_cursor_steps(editor, [("select", (1, 0), (1, 3)), ("insert", "D\nE")])

    assert_document_change(
        editor,
        qtbot,
        "abc\nD\nE\nghi\n",
        [(1, 0, 1, 3, "D\nE")],
    )


def test_document_did_change_preserves_trailing_newline_ranges(qtbot):
    editor = create_lsp_editor(qtbot, "abc\ndef\nghi\n")

    apply_single_cursor_steps(editor, [("select", (1, 0), (2, 0)), ("remove",)])

    assert_document_change(editor, qtbot, "abc\nghi\n", [(1, 0, 2, 0, "")])


def test_document_did_change_deletes_first_character_before_blank_lines(qtbot):
    editor = create_lsp_editor(qtbot, "ba\n\n")

    apply_single_cursor_steps(editor, [("move", 1), ("delete",)])

    assert_document_change(editor, qtbot, "b\n\n", [(0, 1, 0, 2, "")])


def test_document_did_change_deletes_entire_line_inclusive_of_newline(qtbot):
    editor = create_lsp_editor(qtbot, "alpha\nbeta\ngamma\n")

    apply_single_cursor_steps(editor, [("select", (1, 0), (2, 0)), ("remove",)])

    assert_document_change(editor, qtbot, "alpha\ngamma\n", [(1, 0, 2, 0, "")])


def test_document_did_change_replaces_line_prefix_with_multiline_text(qtbot):
    editor = create_lsp_editor(qtbot, "one\ntwo\n")

    apply_single_cursor_steps(editor, [("select", (0, 0), (0, 3)), ("insert", "1\nuno")])

    assert_document_change(editor, qtbot, "1\nuno\ntwo\n", [(0, 0, 0, 3, "1\nuno")])


def test_document_did_change_replaces_multiline_span_across_blank_lines(qtbot):
    editor = create_lsp_editor(qtbot, "aa\n\nbb\ncc\n")

    apply_single_cursor_steps(
        editor,
        [("select", (0, 1), (3, 1)), ("insert", "X\nY\nZ")],
    )

    assert_document_change(
        editor,
        qtbot,
        "aX\nY\nZc\n",
        [(0, 1, 3, 1, "X\nY\nZ")],
    )


def test_document_did_change_removes_multiline_span_across_blank_lines(qtbot):
    editor = create_lsp_editor(qtbot, "aa\n\nbb\ncc\ndd\n")

    apply_single_cursor_steps(
        editor,
        [("select", (0, 1), (4, 1)), ("remove",)],
    )

    assert_document_change(
        editor,
        qtbot,
        "ad\n",
        [(0, 1, 4, 1, "")],
    )


@pytest.mark.parametrize(
    "text,selection,inserted,expected_text,expected_change",
    [
        (
            "alpha\nbeta\ngamma\n",
            ((0, 2), (1, 2)),
            "Z",
            "alZta\ngamma\n",
            (0, 2, 1, 2, "Z"),
        ),
        (
            "alpha\n\nbeta\ngamma\n",
            ((0, 1), (2, 2)),
            "X\nY",
            "aX\nYta\ngamma\n",
            (0, 1, 2, 2, "X\nY"),
        ),
        (
            "ab\ncd\nef\n",
            ((0, 1), (2, 1)),
            "Q\nR\nS",
            "aQ\nR\nSf\n",
            (0, 1, 2, 1, "Q\nR\nS"),
        ),
        (
            "line1\nline2\nline3\n",
            ((0, 0), (2, 0)),
            "joined",
            "joinedline3\n",
            (0, 0, 2, 0, "joined"),
        ),
        (
            "row1\nrow2\nrow3\n",
            ((1, 0), (2, 0)),
            "",
            "row1\nrow3\n",
            (1, 0, 2, 0, ""),
        ),
    ],
)
def test_document_did_change_multiline_replacement_matrix(
    qtbot, text, selection, inserted, expected_text, expected_change
):
    editor = create_lsp_editor(qtbot, text)

    apply_single_cursor_steps(
        editor,
        [("select", selection[0], selection[1]), ("insert", inserted)],
    )

    assert_document_change(editor, qtbot, expected_text, [expected_change])


def test_document_did_change_merges_multicursor_inserts_and_shifts_positions(qtbot):
    editor = create_lsp_editor(qtbot, "ab\ncd\n")

    main_cursor = set_cursor(editor, block_position(editor, 1, 1))
    extra_cursor = QTextCursor(editor.document())
    extra_cursor.setPosition(block_position(editor, 0, 1))
    editor.extra_cursors = [extra_cursor]
    editor.set_extra_cursor_selections()
    editor.setTextCursor(main_cursor)

    qtbot.keyClick(editor, "x")

    payload = flush_document_change(editor, qtbot)

    assert editor.toPlainText() == "axb\ncxd\n"
    assert payload["version"] == 1
    assert len(payload["content_changes"]) == 2
    assert [change_signature(change) for change in payload["content_changes"]] == [
        (0, 1, 0, 1, "x"),
        (1, 1, 1, 1, "x"),
    ]


def test_document_did_change_handles_three_cursor_column_inserts(qtbot):
    editor = create_lsp_editor(qtbot, "ab\ncd\nef\n")

    cursors = []
    for line in range(3):
        cursor = QTextCursor(editor.document())
        cursor.setPosition(block_position(editor, line, 1))
        cursors.append(cursor)

    editor.setTextCursor(cursors[-1])
    editor.extra_cursors = cursors[:-1]
    editor.set_extra_cursor_selections()

    qtbot.keyClick(editor, "x")

    payload = flush_document_change(editor, qtbot)

    assert editor.toPlainText() == "axb\ncxd\nexf\n"
    assert payload["version"] == 1
    assert len(payload["content_changes"]) == 1
    assert [change_signature(change) for change in payload["content_changes"]] == [
        (0, 1, 2, 1, "xb\ncxd\nex"),
    ]


def test_document_did_change_handles_multicursor_backspace(qtbot):
    editor = create_lsp_editor(qtbot, "ab\ncd\n")

    first = QTextCursor(editor.document())
    first.setPosition(block_position(editor, 0, 2))
    second = QTextCursor(editor.document())
    second.setPosition(block_position(editor, 1, 2))
    editor.setTextCursor(second)
    editor.extra_cursors = [first]
    editor.set_extra_cursor_selections()

    qtbot.keyClick(editor, Qt.Key.Key_Backspace)

    payload = flush_document_change(editor, qtbot)

    assert editor.toPlainText() == "a\nc\n"
    assert payload["version"] == 1
    assert len(payload["content_changes"]) == 1
    assert [change_signature(change) for change in payload["content_changes"]] == [
        (0, 1, 1, 2, "\nc"),
    ]


@pytest.mark.parametrize(
    "text,selections,key,expected_text,expected_changes",
    [
        (
            "aa\nbb\ncc\ndd\n",
            [((0, 0), (1, 0)), ((2, 0), (3, 0))],
            "x",
            "xbb\nxdd\n",
            [(0, 0, 3, 0, "xbb\nx")],
        ),
        (
            "aa\nbb\ncc\ndd\n",
            [((0, 0), (1, 0)), ((2, 0), (3, 0))],
            Qt.Key.Key_Backspace,
            "bb\ndd\n",
            [(0, 0, 2, 2, "bb")],
        ),
    ],
)
def test_document_did_change_multicursor_multiline_span_matrix(
    qtbot, text, selections, key, expected_text, expected_changes
):
    editor = create_lsp_editor(qtbot, text)

    set_multicursor_selections(editor, selections)

    if key == Qt.Key.Key_Backspace:
        qtbot.keyClick(editor, key)
    else:
        qtbot.keyClick(editor, key)

    payload = flush_document_change(editor, qtbot)

    assert editor.toPlainText() == expected_text
    assert payload["version"] == 1
    assert len(payload["content_changes"]) == len(expected_changes)
    assert [change_signature(change) for change in payload["content_changes"]] == expected_changes



