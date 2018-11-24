# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

import logging
logger = logging.getLogger(__name__)


class SpyderMessageHandler(object):
    """
    Message handler for Spyder messages.

    Each shell widget has one instance of it to handle the messages sent
    by its kernel. Using the IPythonAPIMixin, plugins can register additional
    global handlers.
    """

    registered_handlers = {}

    def __init__(self):
        # create copy of global message handlers
        self._handlers = self.registered_handlers.copy()

    def handle_message(self, msg):
        """Dispatches the message to its handler."""
        spyder_msg_type = msg['content'].get('spyder_msg_type')
        if spyder_msg_type not in self._handlers:
            logger.debug("No such spyder message type: %s", spyder_msg_type)
            return
        self._handlers[spyder_msg_type](msg)

    def add_handler(self, spyder_msg_type, handler):
        """Add shell local hander."""
        self._handlers[spyder_msg_type] = handler
