
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
import re
import logging

# Qt imports
from qtpy.QtCore import QObject, QThread, QMutex, QMutexLocker, Signal, Slot

# Other imports
import pygments
from pygments.lexers import get_lexer_by_name
from diff_match_patch import diff_match_patch

# Local imports
from spyder.plugins.editor.lsp import CompletionItemKind
from spyder.plugins.editor.fallback.utils import get_keywords, get_words


logger = logging.getLogger(__name__)


class FallbackActor(QObject):
    #: Signal emitted when the Thread is ready
    sig_fallback_ready = Signal()
    sig_set_tokens = Signal(object, list)
    sig_mailbox = Signal(dict)

    def __init__(self, parent):
        QObject.__init__(self)
        self.stopped = False
        self.daemon = True
        self.mutex = QMutex()
        self.file_tokens = {}
        self.diff_patch = diff_match_patch()
        self.thread = QThread()
        self.moveToThread(self.thread)

        self.thread.started.connect(self.started)
        self.sig_mailbox.connect(self.handle_msg)

    def tokenize(self, text, language):
        """
        Return all tokens in `text` and all keywords associated by
        Pygments to `language`.
        """
        try:
            lexer = get_lexer_by_name(language)
            keywords = get_keywords(lexer)
        except Exception:
            keywords = []
        keyword_set = set(keywords)
        keywords = [{'kind': CompletionItemKind.KEYWORD,
                     'insertText': keyword,
                     'sortText': keyword[0].lower(),
                     'filterText': keyword, 'documentation': ''}
                    for keyword in keywords]
        # logger.debug(keywords)
        # tokens = list(lexer.get_tokens(text))
        # logger.debug(tokens)
        tokens = get_words(text, language)
        tokens = [{'kind': CompletionItemKind.TEXT, 'insertText': token,
                   'sortText': token[0].lower(),
                   'filterText': token, 'documentation': ''}
                  for token in tokens]
        for token in tokens:
            if token['insertText'] not in keyword_set:
                keywords.append(token)
        return keywords

    def stop(self):
        """Stop actor."""
        with QMutexLocker(self.mutex):
            logger.debug("Fallback plugin stopping...")
            self.thread.quit()

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
        msg_type, file, msg, editor = [
            message[k] for k in ('type', 'file', 'msg', 'editor')]
        if msg_type == 'update':
            if file not in self.file_tokens:
                self.file_tokens[file] = {
                    'text': '', 'language': msg['language']}
            diff = msg['diff']
            text = self.file_tokens[file]
            text, _ = self.diff_patch.patch_apply(
                diff, text['text'])
            self.file_tokens[file]['text'] = text
        elif msg_type == 'close':
            self.file_tokens.pop(file, {})
        elif msg_type == 'retrieve':
            tokens = []
            if file in self.file_tokens:
                text_info = self.file_tokens[file]
                tokens = self.tokenize(
                    text_info['text'], text_info['language'])
            self.sig_set_tokens.emit(editor, tokens)
