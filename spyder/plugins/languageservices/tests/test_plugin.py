# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for the LanguageServices plugin."""

from lsprotocol import types as lsp
import pytest

from spyder.api.asyncdispatcher import AsyncDispatcher
from spyder.config.manager import CONF
from spyder.plugins.languageservices.api.languages import Language
from spyder.plugins.languageservices.api.provider import (
    LanguageServicesProvider,
)
from spyder.plugins.languageservices.plugin import LanguageServices
from spyder.plugins.languageservices.services import LANGUAGE_SERVICES_LOOP


URI = "file:///plugin_test.py"


def run(coro_func, *args):
    return AsyncDispatcher(
        loop=LANGUAGE_SERVICES_LOOP, early_return=False, timeout=10
    )(coro_func)(*args)


class EchoProvider(LanguageServicesProvider):
    NAME = "echo"
    PRIORITY = 50
    CONF_DEFAULTS = [("greeting", "hi"), ("count", 1)]
    CONF_VERSION = "0.1.0"

    def __init__(self, plugin, config=None):
        super().__init__(plugin, config)
        self.running = False

    def supported_languages(self):
        return frozenset({Language.PYTHON})

    async def start(self):
        self.running = True

    async def stop(self):
        self.running = False

    async def completion(self, params):
        return [lsp.CompletionItem(label=self.get_conf("greeting"))]


@pytest.fixture
def provider(language_services, qtbot):
    provider = language_services.register_provider(EchoProvider)
    qtbot.waitUntil(lambda: language_services.is_provider_started("echo"))

    yield provider

    language_services.unregister_provider("echo")


def test_plugin_loads_without_providers(language_services):
    assert language_services.provider_names() == []
    assert language_services.supported_languages() == frozenset()
    assert not language_services.is_language_supported(Language.PYTHON)


def test_provider_registration_and_config(language_services, provider):
    assert language_services.provider_names() == ["echo"]
    assert provider.running
    assert language_services.is_language_supported(Language.PYTHON)

    # Defaults were merged into the plugin's configuration namespace
    stored = CONF.get("language_services", ("providers", "echo"))
    assert stored["values"] == {"greeting": "hi", "count": 1}
    assert stored["enable"] is True
    assert provider.get_conf("greeting") == "hi"

    provider.set_conf("greeting", "hello")
    assert CONF.get(
        "language_services", ("providers", "echo", "values", "greeting")
    ) == "hello"


def test_completion_request_through_plugin(language_services, provider, qtbot):
    run(
        language_services.services_api.open_document,
        lsp.DidOpenTextDocumentParams(
            text_document=lsp.TextDocumentItem(
                uri=URI, language_id="python", version=1, text="x\n"
            )
        ),
    )
    params = lsp.CompletionParams(
        text_document=lsp.TextDocumentIdentifier(URI),
        position=lsp.Position(0, 0),
    )

    # Coroutine API
    items = run(language_services.services_api.completion, params)
    assert [i.label for i in items] == ["hi"]

    # Qt future API
    results = []

    @AsyncDispatcher.QtSlot
    def on_done(future):
        results.append(future.result())

    future = language_services.completion(params)
    future.connect(on_done)
    qtbot.waitUntil(lambda: bool(results))
    assert [i.label for i in results[0]] == ["hi"]
    assert results[0][0].data["provider"] == "echo"

    run(
        language_services.services_api.close_document,
        lsp.DidCloseTextDocumentParams(lsp.TextDocumentIdentifier(URI)),
    )


def test_enable_toggle_starts_and_stops(language_services, provider, qtbot):
    language_services.set_conf(("providers", "echo", "enable"), False)
    language_services.after_configuration_update(
        [("providers", "echo", "enable")]
    )
    qtbot.waitUntil(lambda: not language_services.is_provider_started("echo"))
    assert not provider.running

    language_services.set_conf(("providers", "echo", "enable"), True)
    language_services.after_configuration_update([("providers", "echo")])
    qtbot.waitUntil(lambda: language_services.is_provider_started("echo"))
    assert provider.running


def test_merge_default_configurations():
    class P(LanguageServicesProvider):
        NAME = "p"
        CONF_DEFAULTS = [("a", 1), ("b", 2)]
        CONF_VERSION = "0.1.0"

    confs = {}
    entry = LanguageServices._merge_default_configurations(P, confs)
    assert entry == {
        "version": "0.1.0", "values": {"a": 1, "b": 2},
        "defaults": {"a": 1, "b": 2}, "enable": True,
        "enable_default": True,
    }

    # User value survives a new option and an unchanged version
    entry["values"]["a"] = 10
    P.CONF_DEFAULTS = [("a", 1), ("b", 2), ("c", 3)]
    entry = LanguageServices._merge_default_configurations(P, confs)
    assert entry["values"] == {"a": 10, "b": 2, "c": 3}

    # Minor bump overwrites values whose default changed
    P.CONF_DEFAULTS = [("a", 5), ("b", 2), ("c", 3)]
    P.CONF_VERSION = "0.2.0"
    entry = LanguageServices._merge_default_configurations(P, confs)
    assert entry["values"]["a"] == 5 and entry["version"] == "0.2.0"

    # Major bump removes dropped options
    P.CONF_DEFAULTS = [("a", 5)]
    P.CONF_VERSION = "1.0.0"
    entry = LanguageServices._merge_default_configurations(P, confs)
    assert entry["values"] == {"a": 5} and entry["defaults"] == {"a": 5}


def test_merge_keeps_disabled_by_default():
    class P(LanguageServicesProvider):
        NAME = "p"
        ENABLED_BY_DEFAULT = False

    confs = {}
    entry = LanguageServices._merge_default_configurations(P, confs)
    assert entry["enable"] is False

    # The user's choice survives later merges
    entry["enable"] = True
    entry = LanguageServices._merge_default_configurations(P, confs)
    assert entry["enable"] is True

    # An entry stored without the key gets the provider's default
    del entry["enable"]
    entry = LanguageServices._merge_default_configurations(P, confs)
    assert entry["enable"] is False


def test_merge_applies_changed_enable_default():
    class P(LanguageServicesProvider):
        NAME = "p"
        ENABLED_BY_DEFAULT = False

    # Entries stored before the key existed were created enabled
    confs = {"p": {"version": "0.1.0", "values": {}, "defaults": {},
                   "enable": True}}
    entry = LanguageServices._merge_default_configurations(P, confs)
    assert entry["enable"] is False
    assert entry["enable_default"] is False

    # The reset happens once: the user can enable the provider again
    entry["enable"] = True
    entry = LanguageServices._merge_default_configurations(P, confs)
    assert entry["enable"] is True

    # A provider that becomes enabled by default is turned on
    P.ENABLED_BY_DEFAULT = True
    entry["enable"] = False
    entry = LanguageServices._merge_default_configurations(P, confs)
    assert entry["enable"] is True


def test_disabled_by_default_provider_does_not_start(language_services, qtbot):
    class Dormant(EchoProvider):
        NAME = "dormant"
        ENABLED_BY_DEFAULT = False

    provider = language_services.register_provider(Dormant)
    try:
        assert not language_services.is_provider_enabled("dormant")
        assert not language_services.is_provider_started("dormant")
        assert not provider.running

        language_services.set_conf(("providers", "dormant", "enable"), True)
        language_services.after_configuration_update(
            [("providers", "dormant", "enable")]
        )
        qtbot.waitUntil(
            lambda: language_services.is_provider_started("dormant")
        )
        assert provider.running
    finally:
        language_services.unregister_provider("dormant")
        providers = CONF.get("language_services", "providers")
        providers.pop("dormant", None)
        CONF.set("language_services", "providers", providers)


class FakeFormatter(LanguageServicesProvider):
    PRIORITY = 2

    def supported_languages(self):
        return frozenset({Language.PYTHON})

    def capabilities(self, language):
        return lsp.ServerCapabilities(
            document_formatting_provider=True,
            document_range_formatting_provider=True,
        )

    async def formatting(self, params):
        return [lsp.TextEdit(lsp.Range(lsp.Position(0, 0), lsp.Position(0, 0)), self.NAME)]

    async def range_formatting(self, params):
        return await self.formatting(params)


class FormatterA(FakeFormatter):
    NAME = "formatter_a"


class FormatterB(FakeFormatter):
    NAME = "formatter_b"


@pytest.fixture
def restore_formatter():
    yield
    CONF.set("editor", "formatter", CONF.get_default("editor", "formatter"))
    CONF.set("language_services", "request_policies", {})


def test_formatter_option_selects_formatting_provider(
    language_services, restore_formatter, qtbot
):
    # Startup routes formatting to the configured formatter
    CONF.set("language_services", "request_policies", {})
    language_services.on_initialize()
    policies = CONF.get("language_services", "request_policies")
    default = CONF.get_default("editor", "formatter")
    assert policies["formatting"]["providers"] == [default]
    assert policies["range_formatting"]["providers"] == [default]

    for Provider in (FormatterA, FormatterB):
        language_services.register_provider(Provider)
        qtbot.waitUntil(
            lambda: language_services.is_provider_started(Provider.NAME)
        )
    run(
        language_services.services_api.open_document,
        lsp.DidOpenTextDocumentParams(
            text_document=lsp.TextDocumentItem(
                uri=URI, language_id="python", version=1, text="x\n"
            )
        ),
    )
    options = lsp.FormattingOptions(tab_size=4, insert_spaces=True)
    formatting = lsp.DocumentFormattingParams(
        text_document=lsp.TextDocumentIdentifier(URI), options=options
    )
    range_formatting = lsp.DocumentRangeFormattingParams(
        text_document=lsp.TextDocumentIdentifier(URI),
        range=lsp.Range(lsp.Position(0, 0), lsp.Position(1, 0)),
        options=options,
    )

    def answering():
        edits = run(language_services.services_api.formatting, formatting)
        range_edits = run(
            language_services.services_api.range_formatting, range_formatting
        )
        return (
            None if edits is None else edits[0].new_text,
            None if range_edits is None else range_edits[0].new_text,
        )

    # No provider of the default formatter is registered here
    assert answering() == (None, None)

    # Other policy fields survive a formatter change
    CONF.set(
        "language_services",
        "request_policies",
        {"formatting": {"enabled": True, "providers": [], "timeout_ms": 1234}},
    )
    CONF.set("editor", "formatter", "formatter_b")
    assert answering() == ("formatter_b", "formatter_b")
    policies = CONF.get("language_services", "request_policies")
    assert policies["formatting"]["timeout_ms"] == 1234

    CONF.set("editor", "formatter", "formatter_a")
    assert answering() == ("formatter_a", "formatter_a")

    run(
        language_services.services_api.close_document,
        lsp.DidCloseTextDocumentParams(lsp.TextDocumentIdentifier(URI)),
    )
    for Provider in (FormatterA, FormatterB):
        language_services.unregister_provider(Provider.NAME)
