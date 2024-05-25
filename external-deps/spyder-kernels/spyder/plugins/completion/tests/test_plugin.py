# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# ----------------------------------------------------------------------------

"""CompletionPlugin tests."""

# Third party imports
import pytest
from qtpy.QtCore import QObject, Signal, Slot

# Local imports
from spyder.plugins.completion.api import (
    SpyderCompletionProvider, CompletionRequestTypes)


class DummyCompletionReceiver(QObject):
    """Dummy class that can handle LSP responses."""
    sig_response = Signal(str, dict)

    @Slot(str, dict)
    def handle_response(self, method, params):
        self.sig_response.emit(method, params)


class FakeProvider(SpyderCompletionProvider):
    COMPLETION_PROVIDER_NAME = 'fake'
    CONF_DEFAULTS = [
        ('key1', 'value1'),
        ('key2', 'value2'),
        ('key3', 'value3'),
        ('key4', 4)
    ]
    CONF_VERSION = "0.1.0"


@pytest.fixture
def completion_receiver(completion_plugin_all_started):
    completion_plugin, _ = completion_plugin_all_started
    receiver = DummyCompletionReceiver(None)
    return completion_plugin, receiver


def test_configuration_merge(completion_plugin_all):
    first_defaults = dict(FakeProvider.CONF_DEFAULTS)
    first_version = FakeProvider.CONF_VERSION

    # Check that a new completion provider configuration is registered without
    # changes
    result = completion_plugin_all._merge_default_configurations(
        FakeProvider, FakeProvider.COMPLETION_PROVIDER_NAME, {}
    )
    (conf_version, conf_values, conf_defaults) = result

    assert conf_version == first_version
    assert conf_values == first_defaults
    assert conf_defaults == first_defaults

    # Add a new value to the initial default configuration without changing the
    # version
    second_config = first_defaults.copy()
    second_config['extra_value'] = ['value']

    FakeProvider.CONF_DEFAULTS = [(k, v) for k, v in second_config.items()]

    prev_config = {
        FakeProvider.COMPLETION_PROVIDER_NAME: {
            'version': first_version,
            'values': first_defaults,
            'defaults': first_defaults
        }
    }

    result = completion_plugin_all._merge_default_configurations(
        FakeProvider, FakeProvider.COMPLETION_PROVIDER_NAME, prev_config
    )
    (conf_version, conf_values, conf_defaults) = result

    assert conf_version == first_version
    assert conf_values == second_config
    assert conf_defaults == second_config

    # Assert that default values cannot be changed without a bump in the minor
    # version
    config = first_defaults.copy()
    config['key4'] = 5

    third_config = first_defaults.copy()
    third_config['key4'] = -1

    FakeProvider.CONF_DEFAULTS = [(k, v) for k, v in third_config.items()]

    prev_config = {
        FakeProvider.COMPLETION_PROVIDER_NAME: {
            'version': first_version,
            'values': config,
            'defaults': first_defaults
        }
    }

    result = completion_plugin_all._merge_default_configurations(
        FakeProvider, FakeProvider.COMPLETION_PROVIDER_NAME, prev_config
    )
    (conf_version, conf_values, conf_defaults) = result

    assert conf_version == first_version
    assert conf_values == config
    assert conf_defaults == first_defaults

    # Assert that default values can be replaced with new ones when the
    # minor version number is bumped.
    config['key1'] = 'othervalue'
    expected_config = config.copy()
    expected_config['key4'] = -1

    FakeProvider.CONF_VERSION = "0.1.1"

    result = completion_plugin_all._merge_default_configurations(
        FakeProvider, FakeProvider.COMPLETION_PROVIDER_NAME, prev_config
    )
    (conf_version, conf_values, conf_defaults) = result

    assert conf_version == "0.1.1"
    assert conf_values == expected_config
    assert conf_defaults == third_config

    # Ensure that default values cannot be removed if the major version is not
    # bumped
    fourth_config = third_config.copy()
    fourth_config.pop('key2')

    FakeProvider.CONF_DEFAULTS = [(k, v) for k, v in fourth_config.items()]

    result = completion_plugin_all._merge_default_configurations(
        FakeProvider, FakeProvider.COMPLETION_PROVIDER_NAME, prev_config
    )
    (conf_version, conf_values, conf_defaults) = result

    assert conf_version == "0.1.1"
    assert conf_values == expected_config
    assert conf_defaults == third_config

    # Remove an option when the major version is bumped.
    FakeProvider.CONF_VERSION = "1.0.0"
    expected_config.pop('key2')

    result = completion_plugin_all._merge_default_configurations(
        FakeProvider, FakeProvider.COMPLETION_PROVIDER_NAME, prev_config
    )
    (conf_version, conf_values, conf_defaults) = result

    assert conf_version == "1.0.0"
    assert conf_values == expected_config
    assert conf_defaults == fourth_config


def test_provider_detection(completion_plugin_all):
    print(completion_plugin_all.providers)
    assert len(completion_plugin_all.providers) == 3


@pytest.mark.order(1)
def test_plugin_completion_gather(qtbot_module, completion_receiver):
    completion, receiver = completion_receiver

    # Parameters to perform a textDocument/didOpen request
    params = {
        'file': 'test.py',
        'language': 'python',
        'version': 1,
        'text': "# This is some text with some classe\nimport os\n\ncla",
        'response_instance': receiver,
        'offset': 1,
        'selection_start': 0,
        'selection_end': 0,
        'codeeditor': receiver,
        'requires_response': False
    }

    with qtbot_module.waitSignal(receiver.sig_response, timeout=30000) as blocker:
        completion.send_request(
            'python', CompletionRequestTypes.DOCUMENT_DID_OPEN, params)

    # Parameters to perform a textDocument/completion request
    params = {
        'file': 'test.py',
        'line': 2,
        'column': 3,
        'offset': 50,
        'selection_start': 0,
        'selection_end': 0,
        'current_word': 'cla',
        'codeeditor': receiver,
        'response_instance': receiver,
        'requires_response': True
    }

    with qtbot_module.waitSignal(receiver.sig_response, timeout=30000) as blocker:
        completion.send_request(
            'python', CompletionRequestTypes.DOCUMENT_COMPLETION, params)

    _, response = blocker.args

    response = response['params']
    provider_set = {x['provider'] for x in response}

    # Assert the response contains information from all the providers
    provider_set == {'LSP', 'Fallback', 'Snippets'}


@pytest.mark.order(1)
def test_plugin_first_response_request(qtbot_module, completion_receiver):
    completion, receiver = completion_receiver

    # Parameters to perform a textDocument/didOpen request
    params = {
        'file': 'test2.py',
        'language': 'python',
        'version': 2,
        'text': "# This is some text with some classe\nimport os\n\n",
        'response_instance': receiver,
        'offset': 1,
        'diff': '',
        'selection_start': 0,
        'selection_end': 0,
        'codeeditor': receiver,
        'requires_response': False
    }

    with qtbot_module.waitSignal(receiver.sig_response, timeout=30000) as blocker:
        completion.send_request(
            'python', CompletionRequestTypes.DOCUMENT_DID_OPEN, params)


    params = {
        'file': 'test2.py',
        'line': 1,
        'column': 8,
        'offset': 43,
        'diff': '',
        'response_instance': receiver,
        'codeeditor': receiver,
        'requires_response': True
    }

    with qtbot_module.waitSignal(receiver.sig_response, timeout=30000) as blocker:
        completion.send_request(
            'python', CompletionRequestTypes.DOCUMENT_HOVER, params)

    _, response = blocker.args
    assert len(response['params']) > 0
