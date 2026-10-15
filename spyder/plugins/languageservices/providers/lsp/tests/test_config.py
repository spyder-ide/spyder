# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for ServerConfig."""

import pytest

from spyder.plugins.languageservices.providers.lsp.config import (
    AUTO_LANGUAGES,
    ServerConfig,
)


def test_roundtrip_and_defaults():
    config = ServerConfig(name="rust", cmd="rust-analyzer", stdio=True,
                          languages=["rust"])
    data = config.to_conf()
    assert "name" not in data
    assert data["languages"] == ["rust"]
    assert ServerConfig.from_conf("rust", data) == config
    assert ServerConfig(name="x").auto_languages
    assert ServerConfig(name="x").languages == AUTO_LANGUAGES


def test_validation():
    with pytest.raises(ValueError):
        ServerConfig(name="")
    with pytest.raises(ValueError):
        ServerConfig(name="x", stdio=True, external=True)
    with pytest.raises(ValueError):
        ServerConfig.from_conf("x", {"nope": 1})


def test_needs_restart():
    base = ServerConfig(name="x", cmd="a", configurations={"k": 1})
    assert not base.needs_restart(base.with_changes(configurations={"k": 2}))
    assert base.needs_restart(base.with_changes(cmd="b"))
    assert base.needs_restart(base.with_changes(port=1))
    assert not base.needs_restart(base.with_changes(languages=("go",)))
