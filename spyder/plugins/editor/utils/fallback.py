
# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Fallback completion actor.
This plugin takes a plain text/source file and returns the individual words
written on it.
"""

# Standard library imports
import re
import logging
from queue import Queue

# Qt imports
from qtpy.QtCore import QThread, QMutex, QMutexLocker

# Other imports
from diff_match_patch import diff_match_patch

logger = logging.getLogger(__name__)

# CamelCase and snake_case regex:
# Get all valid tokens that start by a letter (Unicode) and are
# followed by a sequence of letters, numbers or underscores of length > 0
all_regex = re.compile(r'[^\W\d_]\w+')

# CamelCase, snake_case and kebab-case regex:
# Same as above, but it also considers words separated by "-"
kebab_regex = re.compile(r'[^\W\d_]\w+[-\w]*')


class FallbackActor(QThread):
    # Set of languages that allow kebab-case
    LANGUAGE_REGEX = {
        'css': kebab_regex,
        'scss': kebab_regex,
        'html': kebab_regex,
        'xml': kebab_regex
    }

    def __init__(self, parent):
        QThread.__init__(self, parent)
        self.mailbox = Queue()
        self.stopped = False
        self.daemon = True
        self.mutex = QMutex()
        self.file_tokens = {}
        self.diff_patch = diff_match_patch()

    def tokenize(self, text, language):
        regex = self.LANGUAGE_REGEX.get(language, all_regex)
        return {x for x in regex.findall(text) if x != ''}

    def stop(self):
        with QMutexLocker(self.mutex):
            self.stopped = True

    def run(self):
        logger.debug('Fallback plugin starting...')
        while True:
            with QMutexLocker(self.mutex):
                if self.stopped:
                    logger.debug("Fallback plugin stopping...")
            message = self.mailbox.get()
            msg_type, file, msg, editor = [
                message[k] for k in ('type', 'file', 'msg', 'editor')]
            if msg_type == 'update':
                if file not in self.file_tokens:
                    self.file_tokens[file] = {
                        'text': '', 'language': msg['language']}
                diff = msg['diff']
                text = self.file_tokens[file]
                # patches = self.diff_patch.patch_fromText(diff)
                text, _ = self.diff_patch.patch_apply(
                    diff, text['text'])
                self.file_tokens[file]['text'] = text
            elif msg_type == 'retrieve':
                tokens = []
                if file in self.file_tokens:
                    text_info = self.file_tokens[file]
                    tokens = list(self.tokenize(
                        text_info['text'], text_info['language']))
                editor.recieve_text_tokens(tokens)
