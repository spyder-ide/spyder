"""Undo stack support for CodeEditor."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime

from qtpy.QtCore import QTimer, Signal  # type: ignore
from qtpy.QtGui import QTextCursor
from qtpy.QtWidgets import QUndoCommand, QUndoStack

from spyder.plugins.editor.widgets.base import TextEditBaseWidget

logger = logging.getLogger(__name__)

_COMMIT_TIMEOUT_MS = 1_200  # 1.2 seconds, similar to Qt's default


@dataclass(frozen=True)
class CursorState:
    """Cursors snapshot of the editor state.

    Stores `QTextCursor` objects captured at the time of the snapshot.
    """

    main_cursor: QTextCursor
    extra_cursors: tuple[QTextCursor, ...]

    def __eq__(self, other):
        if not isinstance(other, CursorState):
            return NotImplemented
        return self.signature() == other.signature()

    def signature(self) -> tuple:
        """Create a comparable signature for cursor state continuity checks."""
        return (
            self.main_cursor.position(),
            self.main_cursor.anchor(),
            tuple((c.position(), c.anchor()) for c in self.extra_cursors),
        )


@dataclass(frozen=True)
class TextDelta:
    """Single document change item"""

    position: int
    inserted_text: str = ""
    removed_text: str = ""

    def reverse(self) -> TextDelta:
        """Return the reverse of this delta, i.e. a delta that would undo this change."""
        return TextDelta(
            position=self.position,
            inserted_text=self.removed_text,
            removed_text=self.inserted_text,
        )

    def normalized(self) -> TextDelta:
        """Return a normalized delta.

        When both inserted/removed text are present, strip any common prefix
        and suffix. This produces a smaller, canonical delta and can turn
        a replace into a pure insert/remove.
        """
        inserted = self.inserted_text
        removed = self.removed_text
        position = self.position

        if not inserted or not removed:
            return self

        # Strip common prefix.
        common_prefix = 0
        max_prefix = min(len(inserted), len(removed))
        while (
            common_prefix < max_prefix
            and inserted[common_prefix] == removed[common_prefix]
        ):
            common_prefix += 1
        if common_prefix:
            inserted = inserted[common_prefix:]
            removed = removed[common_prefix:]
            position += common_prefix

        # Strip common suffix.
        common_suffix = 0
        max_suffix = min(len(inserted), len(removed))
        while (
            common_suffix < max_suffix
            and inserted[-(common_suffix + 1)] == removed[-(common_suffix + 1)]
        ):
            common_suffix += 1
        if common_suffix:
            inserted = inserted[:-common_suffix]
            removed = removed[:-common_suffix]

        return TextDelta(
            position=position, inserted_text=inserted, removed_text=removed
        )

    def exploded(self) -> tuple[TextDelta, ...]:
        """Explode a delta into simpler deltas when possible.

        Qt (or multi-cursor editing logic) can sometimes report a single
        contiguous *replace* for what is logically two disjoint insertions
        (e.g. inserting at two cursors with unchanged text between them).

        If `inserted_text` contains `removed_text` as a contiguous substring
        exactly once, then the net effect is "insert prefix" + "insert suffix"
        while keeping the removed segment unchanged, i.e. there is no logical
        removal. In that case we split into one or two pure insert deltas.
        """
        delta = self.normalized()
        if not delta.inserted_text or not delta.removed_text:
            return (delta,)

        removed = delta.removed_text
        inserted = delta.inserted_text

        start = inserted.find(removed)
        if start == -1:
            return (delta,)
        if inserted.rfind(removed) != start:
            return (delta,)

        prefix = inserted[:start]
        suffix = inserted[start + len(removed) :]
        if not prefix and not suffix:
            return (
                TextDelta(position=delta.position, inserted_text="", removed_text=""),
            )
        elif not prefix:
            return (
                TextDelta(
                    position=delta.position + len(removed),
                    inserted_text=suffix,
                    removed_text="",
                ),
            )
        elif not suffix:
            return (
                TextDelta(
                    position=delta.position, inserted_text=prefix, removed_text=""
                ),
            )
        else:
            return (
                TextDelta(
                    position=delta.position, inserted_text=prefix, removed_text=""
                ),
                TextDelta(
                    position=delta.position + len(prefix) + len(removed),
                    inserted_text=suffix,
                    removed_text="",
                ),
            )

    @staticmethod
    def merge_text_delta(left: TextDelta, right: TextDelta) -> TextDelta | None:
        """Apply merge rules for insert/remove deltas."""
        left = left.normalized()

        # Sequential inserts.
        if (
            left.removed_text == ""
            and right.removed_text == ""
            and left.inserted_text
            and right.inserted_text
            and left.position + len(left.inserted_text) == right.position
        ):
            return TextDelta(
                position=left.position,
                inserted_text=left.inserted_text + right.inserted_text,
                removed_text="",
            )

        # Replacement inside a previous pure-insert: when the new delta is a
        # replace whose removed_text lies entirely inside the previous
        # inserted_text, replace that substring and keep it as a pure insert.
        if (
            left.removed_text == ""
            and left.inserted_text
            and right.removed_text
            and right.inserted_text
            and left.position <= right.position
            and right.position + len(right.removed_text) <= left.position + len(left.inserted_text)
        ):
            offset = right.position - left.position
            if left.inserted_text[offset : offset + len(right.removed_text)] == right.removed_text:
                new_inserted = (
                    left.inserted_text[:offset]
                    + right.inserted_text
                    + left.inserted_text[offset + len(right.removed_text) :]
                )
                return TextDelta(position=left.position, inserted_text=new_inserted, removed_text="")

        # Fold removals of text that was just inserted back into the insert.
        if (
            left.removed_text == ""
            and right.inserted_text == ""
            and left.inserted_text
            and right.removed_text
            and left.position <= right.position
            and right.position + len(right.removed_text)
            <= left.position + len(left.inserted_text)
        ):
            offset = right.position - left.position
            if left.inserted_text[offset : offset + len(right.removed_text)] == right.removed_text:
                return TextDelta(
                    position=left.position,
                    inserted_text=(
                        left.inserted_text[:offset]
                        + left.inserted_text[offset + len(right.removed_text) :]
                    ),
                    removed_text="",
                )

        # Treat a removal followed by an insertion at the same location as a
        # replacement at that location.
        if (
            left.inserted_text == ""
            and right.removed_text == ""
            and left.removed_text
            and right.inserted_text
            and right.position == left.position
        ):
            return TextDelta(
                position=left.position,
                inserted_text=right.inserted_text,
                removed_text=left.removed_text,
            )

        # Removal to the right
        if (
            left.inserted_text == ""
            and right.inserted_text == ""
            and left.removed_text
            and right.removed_text
            and left.position == right.position
        ):
            return TextDelta(
                position=left.position,
                inserted_text="",
                removed_text=left.removed_text + right.removed_text,
            )

        # Removal to the left
        if (
            left.inserted_text == ""
            and right.inserted_text == ""
            and left.removed_text
            and right.removed_text
            and right.position + len(right.removed_text) == left.position
        ):
            return TextDelta(
                position=right.position,
                inserted_text="",
                removed_text=right.removed_text + left.removed_text,
            )

        # Partially overlapping removals: merge into a single removal that
        # covers the union of both ranges. Fill overlapping characters from
        # either side (tests assume overlapping content matches where they
        # overlap).
        if (
            left.inserted_text == ""
            and right.inserted_text == ""
            and left.removed_text
            and right.removed_text
        ):
            a_start, a_end = left.position, left.position + len(left.removed_text)
            b_start, b_end = right.position, right.position + len(right.removed_text)
            # Check for overlap or adjacency
            if not (a_end < b_start or b_end < a_start):
                new_start = min(a_start, b_start)
                new_end = max(a_end, b_end)
                length = new_end - new_start
                chars: list[str | None] = [None] * length
                # write left removed_text
                for i, ch in enumerate(left.removed_text):
                    chars[left.position - new_start + i] = ch
                # write right removed_text (overwrites matching overlap)
                for i, ch in enumerate(right.removed_text):
                    chars[right.position - new_start + i] = ch

                # Replace any None with empty string (shouldn't happen for
                # fully covered unions in our tests) and join
                new_removed = "".join(c if c is not None else "" for c in chars)
                return TextDelta(position=new_start, inserted_text="", removed_text=new_removed)

        # Replace deltas (insert+remove)
        # common patterns during multicursor or multiline edits.
        if (
            left.inserted_text
            and left.removed_text
            and right.inserted_text
            and right.removed_text
        ):
            # New delta overwrites the previous replacement at the same place.
            # (e.g. replace A->B, then immediately replace B->C)
            if (
                right.position == left.position
                and right.removed_text == left.inserted_text
            ):
                return TextDelta(
                    position=left.position,
                    inserted_text=right.inserted_text,
                    removed_text=left.removed_text,
                )

            # New replacement happens inside the previous inserted text and
            # replaces a suffix of it.
            if left.inserted_text.endswith(right.removed_text):
                overlap_start = len(left.inserted_text) - len(right.removed_text)
                if right.position == left.position + overlap_start:
                    return TextDelta(
                        position=left.position,
                        inserted_text=left.inserted_text[:overlap_start]
                        + right.inserted_text,
                        removed_text=left.removed_text,
                    )

            # New replacement happens inside the previous inserted text and
            # replaces a prefix of it.
            if (
                left.inserted_text.startswith(right.removed_text)
                and right.position == left.position
            ):
                return TextDelta(
                    position=left.position,
                    inserted_text=right.inserted_text
                    + left.inserted_text[len(right.removed_text) :],
                    removed_text=left.removed_text,
                )

            # New replacement happens inside the previous inserted text at an
            # arbitrary offset (not only prefix/suffix). Replace that substring
            # with the new inserted text when the positions align.
            idx = left.inserted_text.find(right.removed_text)
            if idx != -1:
                expected_pos = left.position + idx
                if right.position == expected_pos:
                    new_inserted = (
                        left.inserted_text[:idx]
                        + right.inserted_text
                        + left.inserted_text[idx + len(right.removed_text) :]
                    )
                    return TextDelta(
                        position=left.position,
                        inserted_text=new_inserted,
                        removed_text=left.removed_text,
                    )

            # (moved insertion-bridging rule below)

        # A pure insert that lands within (or immediately after) the text
        # inserted by a previous replacement: extend that inserted text.
        # right.position is in new-document coords, so the valid range is
        # [left.position, left.position + len(left.inserted_text)].
        if (
            left.inserted_text
            and left.removed_text
            and right.inserted_text
            and right.removed_text == ""
            and left.position <= right.position <= left.position + len(left.inserted_text)
        ):
            offset = right.position - left.position
            new_inserted = (
                left.inserted_text[:offset]
                + right.inserted_text
                + left.inserted_text[offset:]
            )
            return TextDelta(
                position=left.position,
                inserted_text=new_inserted,
                removed_text=left.removed_text,
            )

        # If an insertion (pure insert) happens inside or immediately adjacent
        # to a previous pure removal, treat it as a replacement at that location.
        # Only apply when `right` is a pure insert and `left` is a pure removal.
        if (
            left.removed_text
            and not left.inserted_text
            and right.inserted_text
            and right.removed_text == ""
            and right.position == left.position
        ):
            return TextDelta(
                position=left.position,
                inserted_text=right.inserted_text,
                removed_text=left.removed_text,
            )

        return None

    def net_length(self) -> int:
        """Net document length change caused by a delta."""
        return len(self.inserted_text) - len(self.removed_text)

    def shift(self, shift: int) -> TextDelta:
        """Return a copy of this delta with position shifted by the given amount."""
        if not shift:
            return self
        return TextDelta(
            position=self.position + shift,
            inserted_text=self.inserted_text,
            removed_text=self.removed_text,
        )


@dataclass
class EditBlock:
    """Logical edit unit that can be merged with subsequent edits when possible."""
    before: CursorState
    deltas: list[TextDelta]
    after: CursorState
    timestamp: datetime = datetime.now().astimezone()

    def reverse(self) -> EditBlock:
        """Return the reverse of this edit, i.e. an edit that would undo this change."""
        return EditBlock(
            before=self.after,
            deltas=[delta.reverse() for delta in reversed(self.deltas)],
            after=self.before,
            timestamp=datetime.now().astimezone(),
        )

    def merge(self, other: EditBlock) -> bool:
        if not other.deltas:
            return False
        if self.after != other.before:
            return False
        if not self.deltas:
            self.deltas = other.deltas
            self.after = other.after
            self.timestamp = other.timestamp
            return True
        if not other.deltas:
            self.after = other.after
            self.timestamp = other.timestamp
            return True

        for delta in other.deltas:
            for i, current in enumerate(self.deltas):
                merged = TextDelta.merge_text_delta(current, delta)
                if merged is None:
                    continue

                length_diff = merged.net_length() - current.net_length()
                self.deltas[i] = merged

                if length_diff:
                    for j in range(i + 1, len(self.deltas)):
                        if self.deltas[j].position >= current.position:
                            self.deltas[j] = self.deltas[j].shift(length_diff)
                break
            else:
                self.deltas.append(delta)

        self.after = other.after
        self.timestamp = other.timestamp
        return True

    def __str__(self):
        return f"EditBlock(before={self.before}, deltas={self.deltas}, after={self.after}, timestamp={self.timestamp.isoformat()})"


class EditCommand(QUndoCommand):  # type: ignore[misc]
    def __init__(self, edit: EditBlock, editor: EditsStackMixin):
        super().__init__(str(edit))
        self._edit = edit
        self._editor = editor
        self._initialized = False

    def redo(self):
        if not self._initialized:
            self._initialized = True
            return
        with self._editor.suspend_undo_recording():
            self._editor.apply_edit(self._edit)
        self._editor.sig_document_change.emit(self._edit)

    def undo(self):
        reversed_edit = self._edit.reverse()
        with self._editor.suspend_undo_recording():
            self._editor.apply_edit(reversed_edit)
        self._editor.sig_document_change.emit(reversed_edit)


class EditsStackMixin(TextEditBaseWidget):
    """Mixin for undo/redo and changes tracking logic.

    Changes are captured from `QTextDocument.contentsChange`, grouped into
    edit blocks, and then pushed as one `QUndoCommand`.
    """
    sig_document_change = Signal(EditBlock)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._undo_stack = QUndoStack(self)
        self.__edit_block_tstmp = None
        self.__edit_block = False
        self._undo_recording_depth = 0
        self._undo_last_text = str(
            self.toPlainText()
        ).encode("utf-16-le")  # TODO: optimize to avoid full text snapshots
        self.__undo_cursor_state = self._capture_cursor_state()
        self._undo_last_revision = 0
        self.__pending_edit: EditBlock | None = None
        self._commit_timer = QTimer(self)
        self._commit_timer.setSingleShot(True)
        self._commit_timer.timeout.connect(self._commit_pending_edit)
        document = self.document()
        assert document is not None
        self._undo_last_revision = document.revision()
        document.setUndoRedoEnabled(False)
        document.contentsChange.connect(self._on_document_contents_change)
        self.sig_cursor_position_changed.connect(self._on_cursor_position_changed)

    @property
    def undo_stack(self):
        """Return the editor undo stack."""
        return self._undo_stack

    def clear_undo_stack(self):
        """Clear the editor undo stack and any pending edit capture."""
        logger.debug("Clearing custom undo stack")
        self._undo_stack.clear()
        self.__pending_edit = None
        self._undo_last_text = str(self.toPlainText()).encode("utf-16-le")
        self.__undo_cursor_state = self._capture_cursor_state()
        document = self.document()
        self._undo_last_revision = document.revision() if document is not None else 0

    @contextmanager
    def suspend_undo_recording(self):
        """Temporarily disable undo recording while applying a state."""
        self._undo_recording_depth += 1
        try:
            yield
        finally:
            self._undo_recording_depth -= 1

    def _capture_cursor_state(self) -> CursorState:
        cursor = self.textCursor()
        # store copies of the QTextCursor objects so the undo entry keeps the
        # cursor state as it was when the edit happened
        main_copy = QTextCursor(cursor)
        extra_copies = tuple(
            QTextCursor(extra) for extra in getattr(self, "extra_cursors", [])
        )
        return CursorState(main_cursor=main_copy, extra_cursors=extra_copies)

    def _on_cursor_position_changed(self, *args):
        """Keep the stored cursor state in sync with cursor movements.

        This is needed so edits that happen after a pure cursor move capture a
        correct `before` state.

        Important: during an actual text edit, Qt can emit cursor-position
        changes around the same time as `contentsChange`. We avoid overwriting
        the pre-edit snapshot by only updating when the document revision has
        not changed since the last recorded revision.
        """
        current_state = self._capture_cursor_state()
        document = self.document()
        if document is None:
            return

        if self._undo_recording_depth > 0:
            self.__undo_cursor_state = current_state
            self._undo_last_revision = document.revision()
            return

        # Only treat this as a cursor-only move if the document revision
        # hasn't changed since we last recorded an editor state. This prevents
        # cursor-position signals emitted during an edit from overwriting the
        # pre-edit cursor snapshot (needed so undo restores the caret to just
        # before the inserted text).
        if document.revision() != self._undo_last_revision:
            # QTextDocument.revision() can also change due to formatting (e.g.
            # syntax highlighting) without any plain-text edits. If the text is
            # unchanged, resync our stored revision so subsequent cursor moves
            # keep the pre-edit snapshot fresh.
            if (str(self.toPlainText()).encode("utf-16-le") == self._undo_last_text):
                self._undo_last_revision = document.revision()
            else:
                return

        self.__undo_cursor_state = current_state

    def _apply_cursor_state(self, state: CursorState):
        main = state.main_cursor
        cursor = QTextCursor(self.document())
        cursor.setPosition(main.selectionStart())
        cursor.setPosition(main.selectionEnd(), QTextCursor.KeepAnchor)
        self.setTextCursor(cursor)

        extra_cursors = []
        for stored in state.extra_cursors:
            extra_cursor = QTextCursor(self.document())
            extra_cursor.setPosition(stored.selectionStart())
            extra_cursor.setPosition(stored.selectionEnd(), QTextCursor.KeepAnchor)
            extra_cursors.append(extra_cursor)

        self.extra_cursors = extra_cursors
        if extra_cursors:
            self.set_extra_cursor_selections()
        else:
            self.clear_extra_cursors()

    def apply_edit(self, edit: EditBlock):
        for delta in edit.deltas:
            self._apply_delta(delta)
        self._apply_cursor_state(edit.after)

    def _apply_delta(self, delta: TextDelta):
        cursor = QTextCursor(self.document())
        cursor.setPosition(delta.position)
        cursor.beginEditBlock()
        if delta.removed_text:
            cursor.setPosition(
                delta.position + len(delta.removed_text),
                QTextCursor.KeepAnchor,
            )
            cursor.removeSelectedText()
        if delta.inserted_text:
            cursor.setPosition(delta.position)
            cursor.insertText(delta.inserted_text)
        cursor.endEditBlock()

    def _commit_pending_edit(self):
        if self.__pending_edit is None:
            return

        command = EditCommand(
            self.__pending_edit,
            self,
        )
        self.__pending_edit = None

        self._undo_stack.push(command)
        self.sig_document_change.emit(command._edit)

    def _on_document_contents_change(
        self,
        position: int,
        chars_removed: int,
        chars_added: int,
    ):
        document = self.document()
        if document is None:
            return

        if self._undo_recording_depth > 0:
            self._undo_last_text = str(self.toPlainText()).encode("utf-16-le")
            self.__undo_cursor_state = self._capture_cursor_state()
            self._undo_last_revision = document.revision()
            return

        # Create a fresh cursor as contentsChange sometimes resets document's
        # internal cursor, causing `textCursor()` to return an invalid/null cursor.
        cursor = QTextCursor(document)
        # Qt always appends an implicit paragraph separator at the end of the document,
        # clamp the selection to end of document to avoid out-of-range.
        cursor.movePosition(QTextCursor.End)
        end = min(position + chars_added, cursor.position())
        cursor.setPosition(position)
        cursor.setPosition(end, QTextCursor.KeepAnchor)

        bytes_position = position * 2
        bytes_removed_position = bytes_position + chars_removed * 2

        removed_text = self._undo_last_text[
            bytes_position : bytes_removed_position
        ].decode("utf-16-le")

        delta = TextDelta(
            position=position,
            inserted_text=self.get_selected_text(cursor),
            removed_text=removed_text,
        )

        self._undo_last_text = (
            self._undo_last_text[:bytes_position]
            + delta.inserted_text.encode("utf-16-le")
            + self._undo_last_text[bytes_removed_position:]
        )

        self._undo_last_revision = document.revision()

        if not delta.inserted_text and not delta.removed_text:
            self.__undo_cursor_state = self._capture_cursor_state()
            return

        current_cursor = self._capture_cursor_state()
        edit = EditBlock(
            before=self.__undo_cursor_state,
            deltas=[d for d in delta.exploded() if (d.inserted_text or d.removed_text)],
            after=current_cursor,
        )
        self.__undo_cursor_state = current_cursor

        if self.__pending_edit is None:
            self.__pending_edit = edit
        elif self.__edit_block_tstmp is not None and self.__pending_edit.timestamp == self.__edit_block_tstmp:
            self._commit_pending_edit()
            self.__pending_edit = edit
        elif not self.__pending_edit.merge(edit):
            self._commit_pending_edit()
            self.__pending_edit = edit

        if not self.__edit_block:
            self._commit_timer.start(_COMMIT_TIMEOUT_MS)

    @contextmanager
    def single_edit_block(self):
        """Context manager to group multiple edits into a single undo entry."""
        self.__edit_block = True
        if self.__pending_edit is not None:
            self.__edit_block_tstmp = self.__pending_edit.timestamp

        try:
            yield
        finally:
            if self.__pending_edit is not None and self.__pending_edit.timestamp != self.__edit_block_tstmp:
                self._commit_pending_edit()
            self.__edit_block_tstmp = None
            self.__edit_block = False
