# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

import pytest

from spyder.plugins.editor.fallback.actor import FallbackActor
from spyder.plugins.editor.lsp.tests.conftest import qtbot_module


@pytest.fixture(scope='module')
def fallback(qtbot_module, request):
    fallback = FallbackActor(None)
    qtbot_module.addWidget(fallback)

    with qtbot_module.waitSignal(fallback.sig_fallback_ready, timeout=30000):
        fallback.start()

    def teardown():
        fallback.stop()

    request.addfinalizer(teardown)

    def call_editor(editor, tokens):
        editor.receive_text_tokens(tokens)

    fallback.sig_set_tokens.connect(call_editor)
    return fallback
