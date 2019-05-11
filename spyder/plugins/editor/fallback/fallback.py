
# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Fallback completion actor.
This plugin takes a plain text/source file and returns the individual words
written on it.
"""

import re
import logging
from queue import Queue
from threading import Thread, Lock
from diff_match_patch import diff_match_patch

logger = logging.getLogger(__name__)

# Get all valid tokens that start by a letter and are
# followed by a sequence of letters, numbers or underscores of length > 0
regex = re.compile(r'[a-zA-Z]\w+')


class FallbackActor(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.mailbox = Queue()
        self.stopped = False
        self.daemon = True
        self.mutex = Lock()
        self.file_tokens = {}
        self.diff_patch = diff_match_patch()

    def tokenize(self, text):
        return {x for x in regex.split(text) if x != ''}

    def run(self):
        logger.debug('Fallback plugin starting...')
        while True:
            with self.mutex():
                if self.stopped:
                    logger.debug("Fallback plugin stopping...")
            message = self.mailbox.get()
            msg_type, file, msg, editor = [
                message[k] for k in ('type', 'file', 'msg')]
            if msg_type == 'update':
                if file not in self.file_tokens:
                    self.file_tokens[file] = ''
                diff = msg['diff']
                text = self.file_tokens[file]
                patches = self.diff_patch.patch_fromText(diff)
                self.file_tokens[file], _ = self.diff_patch.patch_apply(
                    patches, text)
            elif msg_type == 'retrieve':
                tokens = []
                if file in self.file_tokens:
                    text = self.file_tokens[file]
                    tokens = list(self.tokenize(text))
                editor.recieve_text_tokens(tokens)
