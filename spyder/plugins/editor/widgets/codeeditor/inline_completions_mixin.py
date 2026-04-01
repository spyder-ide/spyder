# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Mixin to handle inline completions.
"""

from __future__ import annotations

from qtpy.QtGui import QTextDocument

from spyder.plugins.editor.utils.editor import BlockUserData
from spyder.utils import sourcecode


class InlineCompletionsMixin:

    def __init__(self):

        self._inline_blocks: list[int] = []
        self._inline_initial_position: int = 0
        self._inline_text: str = ""

    def do_inline_completions(self, text: str):
        """
        Introduce inline completions in the current position.

        These are also called ghost completions.

        Parameters
        ----------
        text: str
            The text to introduce. It can contain multiple lines.
        """
        cursor = self.textCursor()
        self._inline_initial_position = cursor.position()

        line, column = self.get_cursor_line_column()
        block = self.document().findBlockByNumber(line)
        block_nb = cursor.blockNumber()

        # Create BlockUserData in current block if it's not available
        data = block.userData()
        if not data:
            data = BlockUserData(self)

        # Add inline completion data
        data.inline_completion_start = column
        block.setUserData(data)

        # Make completion eols match the file ones
        file_eol = self.get_line_separator()
        completion_eol = sourcecode.get_eol_chars(text)
        if completion_eol != file_eol:
            text = text.strip().replace(completion_eol, file_eol)
        else:
            text = text.strip()

        # Save text
        self._inline_text = text

        # Insert text.
        # NOTE: This is surrounded by beginEditBlock/endEditBlock so that the
        # undo that is called when rejecting the completion only removes this
        # text and doesn't undo other previous edits.
        cursor.beginEditBlock()
        self.insert_text(text)
        cursor.endEditBlock()

        # Move cursor back to the initial position (that's how VSCode works)
        self.set_cursor_position(self._inline_initial_position)

        # Track blocks with inline completion text
        self._inline_blocks.append(block_nb)

        # If text is multiline, add inline completions data to all new blocks
        for i in range(len(text.splitlines())):
            # Don't do anything for the first line because it was done above
            if i == 0:
                continue

            new_data = BlockUserData(self)
            new_data.inline_completion_start = 0

            new_block = block_nb + i
            self.document().findBlockByNumber(new_block).setUserData(new_data)
            self._inline_blocks.append(new_block)

        # This is necessary to apply the inline highlighting for multiline text
        self.rehighlight()

    def accept_inline_completions(self):
        """Accept entered inline completions."""
        for block_nb in self._inline_blocks:
            data = self.document().findBlockByNumber(block_nb).userData()
            data.inline_completion_start = None

        # To change colors from inline to regular format
        self.rehighlight()

        # To work with new completions
        self._reset_inline_attrs()

    def reject_inline_completions(self):
        """Reject entered inline completions."""
        if not self._inline_blocks:
            return

        # This method is called as part of _cursor_position_changed, so we
        # need to disconnect it as a slot to not call it twice after the undo
        # below that removes the completion
        self.cursorPositionChanged.disconnect(self._cursor_position_changed)

        # Save initial position to restore it after the undo
        cursor = self.textCursor()
        initial_position = cursor.position()

        # Undo inserted text
        self.undo(delete_inline_completions=True)

        # Prevent redo
        self.document().clearUndoRedoStacks(QTextDocument.RedoStack)

        # Move cursor to a suitable position after the rejection
        if initial_position <= self._inline_initial_position:
            # If the cursor moves to a position before the completion, then we
            # leave the cursor there
            final_position = initial_position
        elif (
            self._inline_initial_position
            < initial_position
            <= self._inline_initial_position + len(self._inline_text)
        ):
            # If the cursor moves to a position inside the completion, then we
            # move it to where it was inserted
            final_position = self._inline_initial_position
        else:
            # If the cursor moves to a position after the completion, then we
            # need to substract the number of characters of the rejected text
            # to place it where it'd be expected
            final_position = initial_position - len(self._inline_text)

        self.set_cursor_position(final_position)

        # Remove inline completion metadata for the first block in case the
        # completion was introduced in the middle of it
        if self._inline_blocks:
            first_block_nb = self._inline_blocks[0]
            data = self.document().findBlockByNumber(first_block_nb).userData()

            if data:
                data.inline_completion_start = None

        # To work with new completions
        self._reset_inline_attrs()

        # Reconnect disconnected slot above
        self.cursorPositionChanged.connect(self._cursor_position_changed)

    def _reset_inline_attrs(self):
        self._inline_blocks = []
        self._inline_initial_position = 0
        self._inline_text = ""
