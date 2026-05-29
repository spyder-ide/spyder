# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Fallback completion actor.

This takes a plain text/source file and returns the individual words
written on it and the keywords associated by Pygments to the
programming language of that file.
"""

# Standard library imports
import logging

# Third-party imports
from lsprotocol import types as lsp
from pygments.lexers import get_lexer_by_name
from qtpy.QtCore import QObject, QThread, QMutex, QMutexLocker, Signal, Slot

# Local imports
from spyder.plugins.completion.providers.fallback.utils import (
    get_keywords, get_words, is_prefix_valid)


FALLBACK_COMPLETION = "Fallback"

logger = logging.getLogger(__name__)


class FallbackActor(QObject):
    #: Signal emitted when the Thread is ready
    sig_fallback_ready = Signal()
    sig_set_tokens = Signal(int, object)
    sig_mailbox = Signal(dict)

    def __init__(self, parent):
        QObject.__init__(self)
        self.stopped = False
        self.daemon = True
        self.mutex = QMutex()
        self.file_tokens = {}
        self.thread = QThread(None)
        self.moveToThread(self.thread)

        self.thread.started.connect(self.started)
        self.sig_mailbox.connect(self.handle_msg)

    def tokenize(self, text, offset, language, current_word):
        """
        Return all tokens in `text` and all keywords associated by
        Pygments to `language`.
        """
        valid = is_prefix_valid(text, offset, language)
        if not valid:
            return []

        # Get language keywords provided by Pygments
        try:
            lexer = get_lexer_by_name(language)
            keywords = get_keywords(lexer)
        except Exception:
            keywords = []
        keyword_set = set(keywords)
        keywords = [
            lsp.CompletionItem(
                label=keyword,
                kind=lsp.CompletionItemKind.Keyword,
                insert_text=keyword,
                sort_text=keyword,
                filter_text=keyword,
                data={'provider': FALLBACK_COMPLETION},
            )
            for keyword in keywords
        ]

        # Get file tokens
        tokens = get_words(text, offset, language)
        tokens = [
            lsp.CompletionItem(
                label=token,
                kind=lsp.CompletionItemKind.Text,
                insert_text=token,
                sort_text=token,
                filter_text=token,
                data={'provider': FALLBACK_COMPLETION},
            )
            for token in tokens
        ]
        for token in tokens:
            if token.label not in keyword_set:
                keywords.append(token)

        # Filter matching results
        if current_word is not None:
            current_word = current_word.lower()
            keywords = [
                k
                for k in keywords
                if current_word in (k.insert_text or k.label).lower()
            ]

        return keywords

    def stop(self):
        """Stop actor."""
        with QMutexLocker(self.mutex):
            logger.debug("Fallback plugin stopping...")
            self.thread.quit()
            self.thread.wait()

    def start(self):
        """Start thread."""
        self.thread.start()

    def started(self):
        """Thread started."""
        logger.debug('Fallback plugin starting...')
        self.sig_fallback_ready.emit()

    @Slot(dict)
    def handle_msg(self, message):
        """Handle one message"""
        msg_type, _id, file, msg = [
            message[k] for k in ('type', 'id', 'file', 'msg')]
        logger.debug(u'Perform request {0} with id {1}'.format(msg_type, _id))
        if msg_type == lsp.TEXT_DOCUMENT_DID_OPEN:
            self.file_tokens[file] = {
                'text': msg['text'],
                'offset': msg['offset'],
                'language': msg['language'],
            }
        elif msg_type == lsp.TEXT_DOCUMENT_DID_CHANGE:
            self._apply_content_changes(file, msg.get('content_changes', []))
        elif msg_type == lsp.TEXT_DOCUMENT_DID_CLOSE:
            self.file_tokens.pop(file, {})
        elif msg_type == lsp.TEXT_DOCUMENT_COMPLETION:
            tokens = []
            if file in self.file_tokens:
                text_info = self.file_tokens[file]
                tokens = self.tokenize(
                    text_info['text'],
                    text_info['offset'],
                    text_info['language'],
                    msg['current_word'])
            self.sig_set_tokens.emit(_id, tokens)

    def _apply_content_changes(self, file, content_changes):
        """
        Apply incremental content changes to the stored file text.

        Parameters
        ----------
        file : str
            File path/URI identifier.
        content_changes : list
            List of changes, each being either:
            - lsp.TextDocumentContentChangePartial (incremental range change)
            - lsp.TextDocumentContentChangeWholeDocument (full document replacement)
        """
        if not content_changes:
            return

        text_info = self.file_tokens.get(file)
        if not text_info:
            return

        current_text = text_info['text']

        for change in content_changes:
            # Handle whole document replacement
            if hasattr(change, 'text') and not hasattr(change, 'range'):
                current_text = change.text
                continue

            # Handle incremental range-based changes
            if hasattr(change, 'range'):
                current_text = self._apply_range_change(
                    current_text, change.range, change.text
                )

        text_info['text'] = current_text

    def _apply_range_change(self, text, range, new_text):
        """
        Apply a range-based text change to the document text.

        Parameters
        ----------
        text : str
            Current document text.
        range : lsp.Range
            Start and end positions of the change.
        new_text : str
            Text to insert at the range.

        Returns
        -------
        str
            Updated document text.
        """
        lines = text.splitlines(keepends=True)

        # Calculate byte offset from line/character position
        start_offset = self._line_col_to_offset(
            lines, range.start.line, range.start.character
        )
        end_offset = self._line_col_to_offset(
            lines, range.end.line, range.end.character
        )

        # Replace the range with new text
        return text[:start_offset] + new_text + text[end_offset:]

    def _line_col_to_offset(self, lines, line, character):
        """
        Convert 0-based line and character position to text offset.

        Parameters
        ----------
        lines : list[str]
            Document split by newlines.
        line : int
            0-based line number.
        character : int
            0-based character position on the line.

        Returns
        -------
        int
            Offset position in the original text.
        """
        # Sum lengths of all previous lines. `lines` was created with
        # `splitlines(keepends=True)`, so each entry already includes its
        # line ending (if present) and we must not add extra newline
        # characters here.
        prev_lines_len = 0
        max_line_index = min(line, len(lines))
        for i in range(max_line_index):
            prev_lines_len += len(lines[i])

        # If the requested line is beyond the current document, clamp to end
        if line >= len(lines):
            return prev_lines_len

        # Work on the line content without its line ending for column counting
        target_line = lines[line]
        if target_line.endswith('\r\n'):
            line_content = target_line[:-2]
        elif target_line.endswith('\n') or target_line.endswith('\r'):
            line_content = target_line[:-1]
        else:
            line_content = target_line

        # LSP positions use UTF-16 code units. Python strings use code points
        # (UCS-4 on this build), so characters outside the BMP count as two
        # UTF-16 units. Walk the line and find the Python index that
        # corresponds to the requested UTF-16 column.
        utf16_units = 0
        idx = 0
        target_len = len(line_content)
        while idx < target_len and utf16_units < character:
            cp = ord(line_content[idx])
            utf16_units += 1 if cp <= 0xFFFF else 2
            idx += 1

        # Return the offset in Python string indices
        return prev_lines_len + idx
