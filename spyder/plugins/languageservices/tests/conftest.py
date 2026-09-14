# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Fixtures for the language services plugin tests."""

import pytest

from spyder.api.plugins.tests import *  # noqa: F401, F403
from spyder.plugins.languageservices.plugin import LanguageServices


@pytest.fixture(scope="session")
def plugins_cls():
    yield [("language_services", LanguageServices)]


@pytest.fixture(autouse=True)
def no_entry_point_providers(monkeypatch):
    """Keep the plugin free of the built-in providers (they start language
    servers). Tests register the providers they need."""
    monkeypatch.setattr(
        "spyder.plugins.languageservices.plugin.entry_points",
        lambda group: [],
    )
