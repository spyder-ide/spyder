# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

import pytest

from qtpy.QtCore import QObject, Signal

from spyder.plugins.completion.fallback.plugin import FallbackPlugin
from spyder.plugins.completion.languageserver.tests.conftest import (
    qtbot_module)


class CompletionManagerMock(QObject):
    sig_recv_tokens = Signal(list)

    def handle_response(self, client, req_id, response):
        tokens = list(response['params'])
        self.sig_recv_tokens.emit(list(tokens))


@pytest.fixture(scope='module')
def fallback_completions(qtbot_module, request):
    fallback = FallbackPlugin(None)
    completions = CompletionManagerMock(None)
    qtbot_module.addWidget(fallback)
    qtbot_module.addWidget(completions)

    with qtbot_module.waitSignal(fallback.sig_plugin_ready, timeout=30000):
        fallback.start()

    def teardown():
        fallback.shutdown()

    request.addfinalizer(teardown)

    fallback.sig_response_ready.connect(completions.handle_response)
    return fallback, completions
