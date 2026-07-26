# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Standard lib imports
import random

# Third-party imports
from lsprotocol import types as lsp
import pytest

# Local imports
from spyder.config.snippets import SNIPPETS


PY_SNIPPETS = SNIPPETS['python']


@pytest.mark.order(3)
@pytest.mark.parametrize('trigger', list(PY_SNIPPETS.keys()))
def test_snippet_completions(qtbot_module, snippets_completions, trigger):
    snippets, completions = snippets_completions
    end_trim = random.randrange(1, len(trigger))
    descriptions = PY_SNIPPETS[trigger]
    expected_snippets = []
    for description in descriptions:
        snippet_info = descriptions[description]
        text = snippet_info['text']
        remove_trigger = snippet_info['remove_trigger']
        expected_snippets.append({
            'insertText': text,
            'label': f'{trigger} ({description})',
            'filterText': trigger,
            'remove_trigger': remove_trigger,
        })

    trigger_text = trigger[:end_trim]
    snippets_request = {
        'file': '',
        'current_word': trigger_text
    }

    with qtbot_module.waitSignal(completions.sig_recv_snippets,
                                 timeout=3000) as blocker:
        snippets.send_request(
            'python',
            lsp.TEXT_DOCUMENT_COMPLETION,
            snippets_request
        )

    resp_snippets = blocker.args[0]
    resp_snippets = [x for x in resp_snippets if x.filter_text == trigger]
    resp_snippets = sorted(resp_snippets, key=lambda x: x.label)
    expected_snippets = sorted(expected_snippets, key=lambda x: x['label'])
    assert len(resp_snippets) == len(expected_snippets)
    for resp, exp in zip(resp_snippets, expected_snippets):
        assert resp.label == exp['label']
        assert resp.insert_text == exp['insertText']
        assert resp.filter_text == exp['filterText']
        assert (resp.data or {}).get('remove_trigger') == exp['remove_trigger']
