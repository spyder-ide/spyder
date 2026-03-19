# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Mixin to handle inline completions.
"""

from spyder.plugins.editor.utils.editor import BlockUserData
from spyder.utils import sourcecode


class InlineCompletionsMixin:

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
        line, column = self.get_cursor_line_column()
        block = self.document().findBlockByNumber(line)
        initial_position = cursor.position()
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

        # Insert text
        cursor.insertText(text)

        # Move cursor back to the initial position (that's how VSCode works)
        self.set_cursor_position(initial_position)

        # If text is multiline, add inline completions data to all new blocks
        for i, line in enumerate(text.splitlines()):
            # Don't do anything for the first line because it was done above
            if i == 0:
                continue

            new_data = BlockUserData(self)
            new_data.inline_completion_start = 0
            self.document().findBlockByNumber(block_nb + i).setUserData(
                new_data
            )

        # This is necessary to apply the inline highlighting for multiline text
        self.rehighlight()
