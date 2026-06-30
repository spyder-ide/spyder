"""Undo stack support for CodeEditor."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from sys import byteorder as sys_byteorder
from typing import Iterable, Literal

from qtpy.QtCore import QTimer, Signal  # type: ignore
from qtpy.QtGui import QTextCursor

from spyder.plugins.editor.widgets.base import TextEditBaseWidget

logger = logging.getLogger(__name__)

_COMMIT_TIMEOUT_MS = 1_200  # 1.2 seconds, similar to Qt's default

QT_UTF16_ENCODING = "utf-16-le" if sys_byteorder == "little" else "utf-16-be"

class UTF16String:
    __slots__ = ("_byteorder", "_encoding", "_bytes")

    _byteorder: Literal['little', 'big']
    _encoding: str
    _bytes: bytes

    def __init__(self, text: str | bytes | bytearray = b"", byteorder: Literal['little', 'big'] = sys_byteorder):
        self._byteorder = byteorder
        self._encoding = "utf-16-le" if byteorder == "little" else "utf-16-be"
        if isinstance(text, bytes):
            self._bytes = text
        elif isinstance(text, bytearray):
            self._bytes = bytes(text)
        elif isinstance(text, str):
            self._bytes = text.encode(self._encoding)
        else:
            msg = f"UTF16String must be initialized with str or bytes, got {type(text).__name__}"
            raise TypeError(msg)

    def __eq__(self, other) -> bool:
        if isinstance(other, UTF16String):
            return self._bytes == other._bytes
        if isinstance(other, str):
            return str(self) == other
        return NotImplemented

    def __bool__(self) -> bool:
        return bool(self._bytes)

    def __len__(self) -> int:
        return len(self._bytes) // 2

    def __iter__(self):
        for byte_char in range(0, len(self._bytes), 2):
            yield UTF16String(self._bytes[byte_char:byte_char + 2], self._byteorder)

    def __getitem__(self, index) -> UTF16String:
        # ``index`` is a position in UTF-16 code units; each code unit is two
        # bytes, so positions map to byte offsets via ``* 2``.
        length = len(self)
        if isinstance(index, slice):
            start, stop, step = index.indices(length)
            if step == 1:
                return UTF16String(
                    self._bytes[start * 2:stop * 2], self._byteorder
                )
            # A plain byte-slice step would break the 2-byte code units, so
            # gather each selected code unit explicitly.
            result = bytearray()
            for i in range(start, stop, step):
                result += self._bytes[i * 2:i * 2 + 2]
            return UTF16String(bytes(result), self._byteorder)

        if isinstance(index, int):
            if index < 0:
                index += length
            if index < 0 or index >= length:
                raise IndexError("UTF16String index out of range")
            return UTF16String(self._bytes[index * 2:index * 2 + 2], self._byteorder)

        return NotImplemented

    def __add__(self, other):
        if isinstance(other, UTF16String):
            return UTF16String(str(self) + str(other), self._byteorder)
        elif isinstance(other, str):
            return UTF16String(str(self) + other, self._byteorder)
        return NotImplemented

    def __repr__(self) -> str:
        return f"UTF16String({str(self)!r})"

    def __str__(self) -> str:
        return self._bytes.decode(self._encoding)

    def count(self, sub: str | UTF16String) -> int:
        if isinstance(sub, UTF16String):
            return self._bytes.count(sub._bytes)
        return self._bytes.count(sub.encode(self._encoding))

    def find(self, sub: str | UTF16String) -> int:
        if isinstance(sub, UTF16String):
            return self._bytes.find(sub._bytes) // 2
        return self._bytes.find(sub.encode(self._encoding)) // 2

    def rfind(self, sub: str | UTF16String) -> int:
        if isinstance(sub, UTF16String):
            return self._bytes.rfind(sub._bytes) // 2
        return self._bytes.rfind(sub.encode(self._encoding)) // 2

    def startswith(self, prefix: str | UTF16String) -> bool:
        if isinstance(prefix, UTF16String):
            return self._bytes.startswith(prefix._bytes)
        return self._bytes.startswith(prefix.encode(self._encoding))

    def endswith(self, suffix: str | UTF16String) -> bool:
        if isinstance(suffix, UTF16String):
            return self._bytes.endswith(suffix._bytes)
        return self._bytes.endswith(suffix.encode(self._encoding))

    @classmethod
    def join(cls, iterable: Iterable[UTF16String | str], byteorder: Literal["big", "little"] = sys_byteorder) -> UTF16String:
        return cls("".join(str(item) for item in iterable), byteorder)

@dataclass(frozen=True, slots=True)
class CursorState:
    """Cursors snapshot of the editor state.

    Stores `states` objects captured at the time of the snapshot.
    """

    main_cursor: tuple[int, int]  # (selectionStart, selectionEnd)
    extra_cursors: tuple[tuple[int, int], ...]

    def __eq__(self, other):
        if not isinstance(other, CursorState):
            return NotImplemented
        return self.signature() == other.signature()

    def signature(self) -> tuple:
        """Create a comparable signature for cursor state continuity checks."""
        return (
            self.main_cursor,
            self.extra_cursors,
        )

    @classmethod
    def from_editor(cls, editor: TextEditBaseWidget) -> CursorState:
        """Capture the current cursor state from the editor."""
        main_cursor = editor.textCursor()
        main_state = (main_cursor.selectionStart(), main_cursor.selectionEnd())
        extra_states = tuple(
            (c.selectionStart(), c.selectionEnd())
            for c in getattr(editor, "extra_cursors", [])
        )
        return cls(main_cursor=main_state, extra_cursors=extra_states)

@dataclass(frozen=True, slots=True)
class TextDelta:
    """Single document change item"""

    position: int
    line: int
    col: int

    inserted_text: UTF16String = field(default_factory=UTF16String)
    removed_text: UTF16String = field(default_factory=UTF16String)

    def get_end_line_col(self) -> tuple[int, int]:
        """Return the line and column after this delta is applied."""
        return self._advance_line_col(self.line, self.col, self.removed_text)

    def reverse(self) -> TextDelta:
        """Return the reverse of this delta, i.e. a delta that would undo this change."""
        return TextDelta(
            position=self.position,
            line=self.line,
            col=self.col,
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

        if not inserted or not removed:
            return self

        position = self.position
        line = self.line
        col = self.col

        # Strip common prefix.
        common_prefix = 0
        max_prefix = min(len(inserted), len(removed))
        while (
            common_prefix < max_prefix
            and inserted[common_prefix] == removed[common_prefix]
        ):
            common_prefix += 1

        if common_prefix:
            line, col = self._advance_line_col(line, col, inserted[:common_prefix])
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
            position=position,
            line=line,
            col=col,
            inserted_text=inserted,
            removed_text=removed
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
                TextDelta(
                    position=delta.position,
                    line=delta.line,
                    col=delta.col,
                    
                    
                ),
            )
        elif not prefix:
            # The suffix is inserted after the unchanged `removed` segment.
            suffix_line, suffix_col = self._advance_line_col(
                delta.line, delta.col, removed
            )
            return (
                TextDelta(
                    position=delta.position + len(removed),
                    line=suffix_line,
                    col=suffix_col,
                    inserted_text=suffix,
                    
                ),
            )
        elif not suffix:
            return (
                TextDelta(
                    position=delta.position,
                    line=delta.line,
                    col=delta.col,
                    inserted_text=prefix,
                    
                ),
            )
        else:
            # The suffix is inserted after the prefix and the unchanged
            # `removed` segment.
            suffix_line, suffix_col = self._advance_line_col(
                delta.line, delta.col, prefix + removed
            )
            return (
                TextDelta(
                    position=delta.position,
                    line=delta.line,
                    col=delta.col,
                    inserted_text=prefix,
                    
                ),
                TextDelta(
                    position=delta.position + len(prefix) + len(removed),
                    line=suffix_line,
                    col=suffix_col,
                    inserted_text=suffix,
                    
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
                line=left.line,
                col=left.col,
                inserted_text=left.inserted_text + right.inserted_text,
                
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
            and right.position + len(right.removed_text)
            <= left.position + len(left.inserted_text)
        ):
            offset = right.position - left.position
            if (
                left.inserted_text[offset : offset + len(right.removed_text)]
                == right.removed_text
            ):
                new_inserted = (
                    left.inserted_text[:offset]
                    + right.inserted_text
                    + left.inserted_text[offset + len(right.removed_text) :]
                )
                return TextDelta(
                    position=left.position,
                    line=left.line,
                    col=left.col,
                    inserted_text=new_inserted,
                    
                )

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
            if (
                left.inserted_text[offset : offset + len(right.removed_text)]
                == right.removed_text
            ):
                return TextDelta(
                    position=left.position,
                    line=left.line,
                    col=left.col,
                    inserted_text=(
                        left.inserted_text[:offset]
                        + left.inserted_text[offset + len(right.removed_text) :]
                    ),
                    
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
                line=left.line,
                col=left.col,
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
                line=left.line,
                col=left.col,
                
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
                line=right.line,
                col=right.col,
                
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
                chars: list[UTF16String | None] = [None] * length
                # write left removed_text
                for i, ch in enumerate(left.removed_text):
                    chars[left.position - new_start + i] = ch
                # write right removed_text (overwrites matching overlap)
                for i, ch in enumerate(right.removed_text):
                    chars[right.position - new_start + i] = ch

                # Replace any None with empty string (shouldn't happen for
                # fully covered unions in our tests) and join
                new_removed = UTF16String.join(c if c is not None else "" for c in chars)
                # The union starts at whichever delta has the lower position.
                base = left if left.position <= right.position else right
                return TextDelta(
                    position=new_start,
                    line=base.line,
                    col=base.col,
                    
                    removed_text=new_removed,
                )

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
                    line=left.line,
                    col=left.col,
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
                        line=left.line,
                        col=left.col,
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
                    line=left.line,
                    col=left.col,
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
                        line=left.line,
                        col=left.col,
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
            and left.position
            <= right.position
            <= left.position + len(left.inserted_text)
        ):
            offset = right.position - left.position
            new_inserted = (
                left.inserted_text[:offset]
                + right.inserted_text
                + left.inserted_text[offset:]
            )
            return TextDelta(
                position=left.position,
                line=left.line,
                col=left.col,
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
                line=left.line,
                col=left.col,
                inserted_text=right.inserted_text,
                removed_text=left.removed_text,
            )

        return None

    def net_length(self) -> int:
        """Net document length change caused by a delta."""
        return len(self.inserted_text) - len(self.removed_text)

    def net_newlines(self) -> int:
        """Net change in the document's newline count caused by a delta."""
        return self.inserted_text.count("\n") - self.removed_text.count("\n")

    def shift(
        self, shift: int, line_shift: int = 0, col_shift: int = 0
    ) -> TextDelta:
        """Return a copy of this delta with position/line/col shifted.

        ``shift`` moves the absolute character ``position``; ``line_shift`` and
        ``col_shift`` move the ``line`` and ``col`` coordinates. ``col_shift``
        should only be supplied for deltas that share the line on which the
        preceding edit changed its length.
        """
        if not shift and not line_shift and not col_shift:
            return self
        return TextDelta(
            position=self.position + shift,
            line=self.line + line_shift,
            col=self.col + col_shift,
            inserted_text=self.inserted_text,
            removed_text=self.removed_text,
        )

    @staticmethod
    def _advance_line_col(line: int, col: int, text: UTF16String) -> tuple[int, int]:
        """Advance a ``(line, col)`` position over ``text``.

        Each newline increments the line and resets the column to the number of
        characters following the last newline; otherwise the column simply grows
        by the length of ``text``.
        """
        newlines = text.count("\n")
        if newlines:
            return line + newlines, len(text) - text.rfind("\n") - 1
        return line, col + len(text)


@dataclass(slots=True)
class EditBlock:
    """Logical edit unit that can be merged with subsequent edits when possible."""

    before: CursorState
    deltas: list[TextDelta]
    after: CursorState
    timestamp: datetime = field(default_factory=lambda: datetime.now().astimezone())

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
                line_diff = merged.net_newlines() - current.net_newlines()

                current_end_line = current.line + current.inserted_text.count("\n")

                # The merge changed how many characters live on the line where
                # the edited region ends; deltas sharing that line move with it.
                if (
                    current.inserted_text.count("\n")
                    or current.removed_text.count("\n")
                    or merged.inserted_text.count("\n")
                    or merged.removed_text.count("\n")
                ):
                    # Multi-line edit: fall back to the shift in the end column
                    # of the inserted text.
                    _, current_end_col = TextDelta._advance_line_col(
                        current.line, current.col, current.inserted_text
                    )
                    _, merged_end_col = TextDelta._advance_line_col(
                        merged.line, merged.col, merged.inserted_text
                    )
                    col_diff = merged_end_col - current_end_col
                else:
                    # Single-line edit: following columns shift by the net number
                    # of characters added or removed. Using the inserted end
                    # column alone would miss net removals.
                    col_diff = length_diff

                self.deltas[i] = merged

                if length_diff or line_diff or col_diff:
                    for j in range(i + 1, len(self.deltas)):
                        other_delta = self.deltas[j]
                        if other_delta.position >= current.position:
                            same_line = other_delta.line == current_end_line
                            self.deltas[j] = other_delta.shift(
                                length_diff,
                                line_diff,
                                col_diff if same_line else 0,
                            )
                break
            else:
                self.deltas.append(delta)

        self.after = other.after
        self.timestamp = other.timestamp
        return True

    def __str__(self):
        return f"EditBlock(before={self.before}, deltas={self.deltas}, after={self.after}, timestamp={self.timestamp.isoformat()})"


class UndoStack:
    __slots__ = ("__stack", "__index")

    def __init__(self):
        self.__stack = []
        self.__index = -1

    def count(self) -> int:
        return len(self.__stack)

    @property
    def index(self) -> int:
        return self.__index

    def push(self, edit: EditBlock):
        if self.__index < len(self.__stack) - 1:
            self.__stack = self.__stack[: self.__index + 1]

        self.__stack.append(edit)
        self.__index += 1

    def get_previous(self) -> EditBlock:
        if self.__index < 0:
            raise IndexError("No previous command in the undo stack.")
    
        edit = self.__stack[self.__index]
        self.__index -= 1
        return edit
    
    def get_next(self) -> EditBlock:
        if self.__index >= len(self.__stack) - 1:
            raise IndexError("No next command in the undo stack.")
        self.__index += 1
        return self.__stack[self.__index]

    def clear(self):
        self.__stack.clear()
        self.__index = -1

    def can_redo(self) -> bool:
        return self.__index < len(self.__stack) - 1
    
    def can_undo(self) -> bool:
        return self.__index >= 0


class EditsStackMixin(TextEditBaseWidget):
    """Mixin for undo/redo and changes tracking logic.

    Changes are captured from `QTextDocument.contentsChange`, grouped into
    edit blocks, and then pushed as one `QUndoCommand`.
    """

    sig_document_change = Signal(EditBlock)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._undo_stack = UndoStack()
        self.__edit_block_tstmp = None
        self.__edit_block = False
        self.__revision_in_sync = False
        self.__undo_recording_depth = 0
        self.__undo_last_text = bytearray(
            self.toPlainText().encode(QT_UTF16_ENCODING)
        )  # TODO: optimize to avoid full text snapshots
        self.__undo_cursor_state = CursorState.from_editor(self)
        self.__undo_last_revision = 0
        self.__pending_edit: EditBlock | None = None
        self._commit_timer = QTimer(self)
        self._commit_timer.setSingleShot(True)
        self._commit_timer.setInterval(_COMMIT_TIMEOUT_MS)
        self._commit_timer.timeout.connect(self._commit_pending_edit)
        document = self.document()
        assert document is not None
        self.__undo_last_revision = document.revision()
        document.setUndoRedoEnabled(False)
        document.contentsChange.connect(self._on_document_contents_change)
        self.sig_cursor_position_changed.connect(self._on_cursor_position_changed)

    def undo(self):
        edit = self.undo_stack.get_previous()
        reversed_edit = edit.reverse()
        with self.suspend_undo_recording():
            self.apply_edit(reversed_edit)
        self.sig_document_change.emit(reversed_edit)

    def redo(self):
        edit = self.undo_stack.get_next()
        with self.suspend_undo_recording():
            self.apply_edit(edit)
        self.sig_document_change.emit(edit)

    @property
    def undo_stack(self):
        """Return the editor undo stack."""
        return self._undo_stack

    def clear_undo_stack(self):
        """Clear the editor undo stack and any pending edit capture."""
        logger.debug("Clearing custom undo stack")
        self._undo_stack.clear()
        self.__pending_edit = None
        self.__undo_cursor_state = CursorState.from_editor(self)
        document = self.document()
        self.__undo_last_revision = document.revision() if document is not None else 0
        self.__revision_in_sync = False  # revision changes after setting text

    @contextmanager
    def suspend_undo_recording(self):
        """Temporarily disable undo recording while applying a state."""
        self.__undo_recording_depth += 1
        try:
            yield
        finally:
            self.__undo_recording_depth -= 1

    def _on_cursor_position_changed(self, *args):
        """Keep the stored cursor state in sync with cursor movements.

        This is needed so edits that happen after a pure cursor move capture a
        correct `before` state.

        Important: during an actual text edit, Qt can emit cursor-position
        changes around the same time as `contentsChange`. We avoid overwriting
        the pre-edit snapshot by only updating when the document revision has
        not changed since the last recorded revision.
        """
        current_state = CursorState.from_editor(self)
        document = self.document()
        if document is None:
            return

        if self.__undo_recording_depth > 0:
            self.__revision_in_sync = True
            self.__undo_cursor_state = current_state
            self.__undo_last_revision = document.revision()
            return

        current_revision = document.revision()

        if (
            self.__revision_in_sync is False
            and self.__undo_last_revision != current_revision
        ):
            self.__revision_in_sync = True
            self.__undo_cursor_state = current_state
            self.__undo_last_revision = current_revision
            return

        # Only treat this as a cursor-only move if the document revision
        # hasn't changed since we last recorded an editor state. This prevents
        # cursor-position signals emitted during an edit from overwriting the
        # pre-edit cursor snapshot (needed so undo restores the caret to just
        # before the inserted text).
        if current_revision != self.__undo_last_revision:
            return

        self.__undo_cursor_state = current_state

    def _apply_cursor_state(self, state: CursorState):
        main = state.main_cursor
        cursor = QTextCursor(self.document())
        cursor.setPosition(main[0])
        cursor.setPosition(main[1], QTextCursor.KeepAnchor)
        self.setTextCursor(cursor)

        extra_cursors = []
        for stored in state.extra_cursors:
            extra_cursor = QTextCursor(self.document())
            extra_cursor.setPosition(stored[0])
            extra_cursor.setPosition(stored[1], QTextCursor.KeepAnchor)
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
            cursor.insertText(str(delta.inserted_text))
        cursor.endEditBlock()

    def _commit_pending_edit(self):
        if self.__pending_edit is None:
            return

        edit = self.__pending_edit
        self.__pending_edit = None

        self._undo_stack.push(edit)
        self.sig_document_change.emit(edit)

    def _on_document_contents_change(
        self,
        position: int,
        chars_removed: int,
        chars_added: int,
    ):
        document = self.document()
        if document is None:
            return
        # Create a fresh cursor as contentsChange sometimes resets document's
        # internal cursor, causing `textCursor()` to return an invalid/null cursor.
        cursor = QTextCursor(document)
        # Qt always appends an implicit paragraph separator at the end of the document,
        # clamp the selection to end of document to avoid out-of-range.
        cursor.movePosition(QTextCursor.End)
        end = min(position + chars_added, cursor.position())
        cursor.setPosition(position)
        line = cursor.blockNumber()
        # QTextCursor.columnNumber() is unreliable when contentsChange is emitted
        col = position - cursor.block().position()
        cursor.setPosition(end, QTextCursor.KeepAnchor)

        bytes_position = position * 2
        bytes_removed_position = bytes_position + chars_removed * 2

        delta = TextDelta(
            position=position,
            line=line,
            col=col,
            inserted_text=UTF16String(self.get_selected_text(cursor)),
            removed_text=UTF16String(self.__undo_last_text[
                bytes_position:bytes_removed_position
            ]),
        )

        self.__undo_last_revision = document.revision()

        if self.__revision_in_sync is False:
            self.__revision_in_sync = True

        if not delta.inserted_text and not delta.removed_text:
            self.__undo_cursor_state = CursorState.from_editor(self)
            return

        self.__undo_last_text[bytes_position:bytes_removed_position] = (
            delta.inserted_text._bytes
        )

        if self.__undo_recording_depth > 0:
            self.__undo_cursor_state = CursorState.from_editor(self)
            return

        edit = EditBlock(
            before=self.__undo_cursor_state,
            deltas=[d for d in delta.exploded() if (d.inserted_text or d.removed_text)],
            after=CursorState.from_editor(self),
        )
        self.__undo_cursor_state = edit.after

        if self.__pending_edit is None:
            self.__pending_edit = edit
        elif (
            self.__edit_block_tstmp is not None
            and self.__pending_edit.timestamp == self.__edit_block_tstmp
        ):
            self._commit_pending_edit()
            self.__pending_edit = edit
        elif not self.__pending_edit.merge(edit):
            self._commit_pending_edit()
            self.__pending_edit = edit

        if not self.__edit_block:
            self._commit_timer.start()

    @contextmanager
    def single_edit_block(self):
        """Context manager to group multiple edits into a single undo entry."""
        self.__edit_block = True
        if self.__pending_edit is not None:
            self.__edit_block_tstmp = self.__pending_edit.timestamp

        try:
            yield
        finally:
            if (
                self.__pending_edit is not None
                and self.__pending_edit.timestamp != self.__edit_block_tstmp
            ):
                self._commit_pending_edit()
            self.__edit_block_tstmp = None
            self.__edit_block = False
