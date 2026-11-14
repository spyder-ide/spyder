# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for the pygls client glue."""

from spyder.plugins.languageservices.providers.lsp.pygls_client import (
    configuration_section,
)

SETTINGS = {"python": {"pythonPath": "/py", "pyrefly": {"x": 1}}, "flat": 2}


def test_configuration_section_lookup():
    # Servers ask for one section per item (pyrefly asks for "python").
    assert configuration_section(SETTINGS, "python") == SETTINGS["python"]
    assert configuration_section(SETTINGS, "python.pyrefly") == {"x": 1}
    assert configuration_section(SETTINGS, "flat") == 2
    # No section means the whole settings object.
    assert configuration_section(SETTINGS, None) is SETTINGS
    # Unknown sections have no value (LSP: null).
    assert configuration_section(SETTINGS, "rust") is None
    assert configuration_section(SETTINGS, "python.missing") is None
    assert configuration_section(SETTINGS, "flat.deeper") is None
