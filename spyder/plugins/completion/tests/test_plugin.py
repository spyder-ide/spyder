# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# ----------------------------------------------------------------------------

"""CompletionPlugin tests."""

# Third party imports
import pytest

# Local imports
from spyder.plugins.completion.api import SpyderCompletionProvider


class FakeProvider(SpyderCompletionProvider):
    COMPLETION_PROVIDER_NAME = 'fake'
    CONF_DEFAULTS = [
        ('key1', 'value1'),
        ('key2', 'value2'),
        ('key3', 'value3'),
        ('key4', 4)
    ]
    CONF_VERSION = "0.1.0"


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


def test_no_builtin_providers(completion_plugin_all):
    """Spyder's own providers live in the LanguageServices plugin."""
    assert completion_plugin_all.providers == {}
