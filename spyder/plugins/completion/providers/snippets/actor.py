
# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Text snippets completion actor.

This plugin takes a set of user-defined custom text snippets to insert on a
given source file.
"""

# Standard library imports
import logging

# Qt imports
from qtpy.QtCore import QObject, QThread, QMutex, QMutexLocker, Signal, Slot

# Local imports
from spyder.plugins.completion.api import CompletionItemKind
from spyder.plugins.completion.api import CompletionRequestTypes
from spyder.plugins.completion.providers.snippets.trie import Trie


SNIPPETS_COMPLETION = "Snippets"

logger = logging.getLogger(__name__)


class SnippetsActor(QObject):
    #: Signal emitted when the Thread is ready
    sig_snippets_ready = Signal()
    sig_snippets_response = Signal(int, dict)
    sig_update_snippets = Signal(dict)
    sig_mailbox = Signal(dict)

    def __init__(self, parent):
        QObject.__init__(self)
        self.stopped = False
        self.daemon = True
        self.mutex = QMutex()
        self.language_snippets = {}
        self.thread = QThread()
        self.moveToThread(self.thread)

        self.thread.started.connect(self.started)
        self.sig_mailbox.connect(self.handle_msg)
        self.sig_update_snippets.connect(self.update_snippets)

    def stop(self):
        """Stop actor."""
        with QMutexLocker(self.mutex):
            logger.debug("Snippets plugin stopping...")
            self.thread.quit()

    def start(self):
        """Start thread."""
        self.thread.start()

    def started(self):
        """Thread started."""
        logger.debug('Snippets plugin starting...')
        self.sig_snippets_ready.emit()

    @Slot(dict)
    def update_snippets(self, snippets):
        """Update available snippets."""
        logger.debug('Updating snippets...')
        for language in snippets:
            lang_snippets = snippets[language]
            lang_trie = Trie()
            for trigger in lang_snippets:
                trigger_descriptions = lang_snippets[trigger]
                lang_trie[trigger] = (trigger, trigger_descriptions)
            self.language_snippets[language] = lang_trie

    @Slot(dict)
    def handle_msg(self, message):
        """Handle one message"""
        msg_type, _id, file, msg = [
            message[k] for k in ('type', 'id', 'file', 'msg')]
        logger.debug(u'Perform request {0} with id {1}'.format(msg_type, _id))
        if msg_type == CompletionRequestTypes.DOCUMENT_COMPLETION:
            language = msg['language']
            current_word = msg['current_word']
            snippets = []

            if current_word is None:
                snippets = {'params': snippets}
                self.sig_snippets_response.emit(_id, snippets)
                return

            if language in self.language_snippets:
                language_snippets = self.language_snippets[language]
                if language_snippets[current_word]:
                    for node in language_snippets[current_word]:
                        trigger, info = node.value
                        for description in info:
                            description_snippet = info[description]
                            text = description_snippet['text']
                            remove_trigger = description_snippet[
                                'remove_trigger']
                            snippets.append({
                                'kind': CompletionItemKind.SNIPPET,
                                'insertText': text,
                                'label': f'{trigger} ({description})',
                                'sortText': f'zzz{trigger}',
                                'filterText': trigger,
                                'documentation': '',
                                'provider': SNIPPETS_COMPLETION,
                                'remove_trigger': remove_trigger
                            })

            snippets = {'params': snippets}
            self.sig_snippets_response.emit(_id, snippets)
