
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

logger = logging.getLogger(__name__)

# Get all valid tokens that start by a letter and are
# followed by a sequence of letters, numbers or underscores of length > 0
regex = re.compile(r'[a-zA-Z]\w+')


class FallbackActor(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.mailbox = Queue
        self.stopped = False
        self.daemon = True
        self.mutex = Lock()
        self.file_tokens = {}

    def run(self):
        logger.debug('Fallback plugin starting...')
        while True:
            with self.mutex():
                if self.stopped:
                    logger.debug("Fallback plugin stopping...")
