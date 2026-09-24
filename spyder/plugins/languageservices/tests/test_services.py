# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for the request fan-out and merge of LanguageServicesAPI."""

import asyncio

from lsprotocol import types as lsp
import pytest

from spyder.plugins.languageservices.api.errors import (
    DocumentNotOpenError,
    ProviderAlreadyRegisteredError,
    ProviderError,
    ProviderNotFoundError,
)
from spyder.plugins.languageservices.api.languages import Language
from spyder.plugins.languageservices.api.provider import (
    LanguageServicesProvider,
    ProviderConfigAccessor,
)
from spyder.plugins.languageservices.services import (
    LanguageServicesAPI,
    merge_capabilities,
)

URI = "file:///a.py"
RANGE = lsp.Range(lsp.Position(0, 0), lsp.Position(0, 1))


class FakeProvider(LanguageServicesProvider):
    NAME = "fake"
    PRIORITY = 100

    def __init__(
        self,
        name,
        priority=100,
        languages=(Language.PYTHON,),
        completions=(),
        hover=None,
        capabilities=None,
        delay=0.0,
        error=None,
    ):
        self.NAME = name
        self.PRIORITY = priority
        self._languages = frozenset(languages)
        self._completions = list(completions)
        self._hover = hover
        self._capabilities = capabilities
        self._delay = delay
        self._error = error
        self.calls = []
        self.opened = []
        self.closed = []
        self.started = False
        super().__init__(None, ProviderConfigAccessor(name))

    def supported_languages(self):
        return self._languages

    def capabilities(self, language):
        return self._capabilities

    async def start(self):
        self.started = True

    async def stop(self):
        self.started = False

    async def did_open(self, params):
        self.opened.append(params.text_document.uri)

    async def did_close(self, params):
        self.closed.append(params.text_document.uri)

    async def _answer(self, method, params, result):
        self.calls.append(method)
        if self._delay:
            await asyncio.sleep(self._delay)
        if self._error is not None:
            raise self._error
        return result

    async def completion(self, params):
        return await self._answer(
            "completion",
            params,
            [lsp.CompletionItem(label=label) for label in self._completions],
        )

    async def hover(self, params):
        return await self._answer("hover", params, self._hover)

    async def formatting(self, params):
        return await self._answer(
            "formatting", params, [lsp.TextEdit(range=RANGE, new_text=self.NAME)]
        )

    async def resolve_completion_item(self, item):
        return await self._answer(
            "resolve", item, lsp.CompletionItem(label=f"{item.label}:{self.NAME}")
        )


def did_open(uri=URI, language_id="python", text="x\n"):
    return lsp.DidOpenTextDocumentParams(
        text_document=lsp.TextDocumentItem(
            uri=uri, language_id=language_id, version=1, text=text
        )
    )


def completion_params(uri=URI):
    return lsp.CompletionParams(
        text_document=lsp.TextDocumentIdentifier(uri),
        position=lsp.Position(0, 0),
    )


def hover_params(uri=URI):
    return lsp.HoverParams(
        text_document=lsp.TextDocumentIdentifier(uri),
        position=lsp.Position(0, 0),
    )


def formatting_params(uri=URI):
    return lsp.DocumentFormattingParams(
        text_document=lsp.TextDocumentIdentifier(uri),
        options=lsp.FormattingOptions(tab_size=4, insert_spaces=True),
    )


def diagnostics_params(uri, *messages, version=None):
    return lsp.PublishDiagnosticsParams(
        uri=uri,
        version=version,
        diagnostics=[
            lsp.Diagnostic(range=RANGE, message=m) for m in messages
        ],
    )


class Recorder:
    def __init__(self, signal):
        self.calls = []
        signal.connect(lambda *args: self.calls.append(args))


@pytest.fixture
def api():
    conf = {}

    def get_conf(option, default):
        return conf.get(option, default)

    api = LanguageServicesAPI(get_conf)
    api.conf = conf
    return api


async def setup_api(api, *providers, open_doc=True):
    for provider in providers:
        api.register_provider(provider)
        await api.start_provider(provider.NAME)
    if open_doc:
        await api.open_document(did_open())


def test_register_and_unregister(api):
    p = api.register_provider(FakeProvider("a"))
    assert api.get_provider("a") is p
    with pytest.raises(ProviderAlreadyRegisteredError):
        api.register_provider(FakeProvider("a"))
    with pytest.raises(ProviderNotFoundError):
        api.get_provider("zzz")
    asyncio.run(api.start_provider("a"))
    with pytest.raises(ProviderError):
        api.unregister_provider("a")
    asyncio.run(api.stop_provider("a"))
    assert api.unregister_provider("a") is p
    assert api.provider_names() == []


def test_request_requires_open_document(api):
    asyncio.run(setup_api(api, FakeProvider("a"), open_doc=False))
    with pytest.raises(DocumentNotOpenError):
        asyncio.run(api.completion(completion_params()))


def test_completion_is_merged_in_priority_order(api):
    asyncio.run(
        setup_api(
            api,
            FakeProvider("low", priority=200, completions=["b", "c"]),
            FakeProvider("high", priority=10, completions=["a", "b"]),
            FakeProvider("rust", languages=(Language.RUST,), completions=["z"]),
        )
    )
    items = asyncio.run(api.completion(completion_params()))
    assert [(i.label, i.data["provider"]) for i in items] == [
        ("a", "high"), ("b", "high"), ("c", "low")
    ]
    assert api.get_provider("rust").calls == []


def test_hover_first_non_none(api):
    hover = lsp.Hover(contents="doc")
    asyncio.run(
        setup_api(
            api,
            FakeProvider("a", priority=1),
            FakeProvider("b", priority=2, hover=hover),
        )
    )
    assert asyncio.run(api.hover(hover_params())) is hover


def test_exclusive_uses_highest_priority_or_selected(api):
    asyncio.run(
        setup_api(api, FakeProvider("a", priority=1), FakeProvider("b", priority=2))
    )
    edits = asyncio.run(api.formatting(formatting_params()))
    assert [e.new_text for e in edits] == ["a"]
    assert api.get_provider("b").calls == []

    api.conf[("request_policies", "formatting")] = {"providers": ["b"]}
    edits = asyncio.run(api.formatting(formatting_params()))
    assert [e.new_text for e in edits] == ["b"]

    # A selected provider that is unavailable leaves the feature unanswered.
    api.conf[("request_policies", "formatting")] = {"providers": ["missing"]}
    assert asyncio.run(api.formatting(formatting_params())) is None


def test_unselected_provider_is_skipped(api):
    asyncio.run(
        setup_api(
            api,
            FakeProvider("a", priority=1, completions=["a"]),
            FakeProvider("b", priority=2, completions=["b"]),
        )
    )
    api.conf[("request_policies", "completion")] = {"providers": ["b"]}
    items = asyncio.run(api.completion(completion_params()))
    assert [i.label for i in items] == ["b"]


def test_merge_order_overrides_global_priority(api):
    asyncio.run(
        setup_api(
            api,
            FakeProvider("a", priority=1, completions=["a"]),
            FakeProvider("b", priority=2, completions=["b"]),
        )
    )
    api.conf[("request_policies", "completion")] = {"providers": ["b", "a"]}
    items = asyncio.run(api.completion(completion_params()))
    assert [i.label for i in items] == ["b", "a"]


def test_disabled_feature_is_unanswered(api):
    asyncio.run(
        setup_api(api, FakeProvider("a", priority=1, completions=["a"]))
    )
    api.conf[("request_policies", "completion")] = {"enabled": False}
    assert asyncio.run(api.completion(completion_params())) is None


def test_timeout_drops_slow_provider(api):
    asyncio.run(
        setup_api(
            api,
            FakeProvider("slow", priority=1, completions=["s"], delay=0.5),
            FakeProvider("fast", priority=2, completions=["f"]),
        )
    )
    api.conf["request_timeout_ms"] = 50
    items = asyncio.run(api.completion(completion_params()))
    assert [i.label for i in items] == ["f"]


def test_exception_is_reported_and_others_survive(api):
    asyncio.run(
        setup_api(
            api,
            FakeProvider("bad", priority=1, error=RuntimeError("boom")),
            FakeProvider("good", priority=2, completions=["g"]),
        )
    )
    errors = Recorder(api.sig_exception_occurred)
    items = asyncio.run(api.completion(completion_params()))
    assert [i.label for i in items] == ["g"]
    assert len(errors.calls) == 1
    report = errors.calls[0][0]
    assert report["is_traceback"] and "boom" in report["text"]
    assert "'bad'" in report["title"]


def test_cancellation_propagates_to_providers(api):
    slow = FakeProvider("slow", completions=["s"], delay=5)
    asyncio.run(setup_api(api, slow))

    async def run():
        task = asyncio.ensure_future(api.completion(completion_params()))
        await asyncio.sleep(0.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(run())
    assert slow.calls == ["completion"]


def test_resolve_routes_to_stamped_provider(api):
    resolve_caps = lsp.ServerCapabilities(
            completion_provider=lsp.CompletionOptions(resolve_provider=True)
        )
    no_resolve_caps = lsp.ServerCapabilities(
        completion_provider=lsp.CompletionOptions(resolve_provider=False)
    )
    asyncio.run(
        setup_api(
            api,
            FakeProvider("a", priority=1, completions=["x"], capabilities=no_resolve_caps), 
            FakeProvider("b", priority=2, completions=["y"], capabilities=resolve_caps)
        )
    )
    items = asyncio.run(api.completion(completion_params()))
    assert asyncio.run(api.resolve_completion_item(items[0])) is None
    assert asyncio.run(api.resolve_completion_item(items[1])).label == "y:b"
    assert api.get_provider("a").calls == ['completion']
    unstamped = lsp.CompletionItem(label="x")
    assert asyncio.run(api.resolve_completion_item(unstamped)) is None


def test_late_provider_announces_language_for_reopen(api):
    # A provider that starts serving an already-open document's language must
    # emit sig_capabilities_changed so document owners re-send didOpen, even
    # when the merged capabilities do not change.
    caps = lsp.ServerCapabilities(hover_provider=True)
    early = FakeProvider("early", capabilities=caps)
    asyncio.run(setup_api(api, early))
    before = api.capabilities(Language.PYTHON)
    changed = Recorder(api.sig_capabilities_changed)

    late = FakeProvider("late", capabilities=caps)
    api.register_provider(late)
    asyncio.run(api.start_provider("late"))

    after = api.capabilities(Language.PYTHON)
    assert after == before
    assert (Language.PYTHON, after) in changed.calls

    asyncio.run(
        api.close_document(
            lsp.DidCloseTextDocumentParams(lsp.TextDocumentIdentifier(URI))
        )
    )
    assert api.documents.documents == {}


def test_diagnostics_are_merged_and_cleared(api):
    a = FakeProvider("a", priority=1)
    b = FakeProvider("b", priority=2)
    asyncio.run(setup_api(api, a, b))
    published = Recorder(api.sig_diagnostics)

    b.sig_diagnostics.emit(diagnostics_params(URI, "from b", version=1))
    a.sig_diagnostics.emit(diagnostics_params(URI, "from a"))
    assert [d.message for d in published.calls[-1][0].diagnostics] == [
        "from a", "from b"
    ]
    assert [d.source for d in published.calls[-1][0].diagnostics] == [
        "a", "b"
    ]

    # Unknown documents are ignored
    a.sig_diagnostics.emit(diagnostics_params("file:///nope.py", "x"))
    assert len(published.calls) == 2

    asyncio.run(api.stop_provider("a"))
    params = published.calls[-1][0]
    assert params.uri == URI
    assert [d.message for d in params.diagnostics] == ["from b"]

    asyncio.run(api.stop_provider("b"))
    assert published.calls[-1][0].diagnostics == []


def test_capabilities_and_language_lifecycle(api):
    caps_a = lsp.ServerCapabilities(
        completion_provider=lsp.CompletionOptions(trigger_characters=["."]),
        hover_provider=True,
        text_document_sync=lsp.TextDocumentSyncKind.Full,
    )
    caps_b = lsp.ServerCapabilities(
        completion_provider=lsp.CompletionOptions(
            trigger_characters=["("], resolve_provider=True
        ),
        document_formatting_provider=True,
        text_document_sync=lsp.TextDocumentSyncKind.Incremental,
    )
    changed = Recorder(api.sig_capabilities_changed)
    stopped = Recorder(api.sig_language_stopped)
    a = FakeProvider("a", priority=1, capabilities=caps_a)
    b = FakeProvider("b", priority=2, capabilities=caps_b)
    asyncio.run(setup_api(api, a, b, open_doc=False))

    assert api.supported_languages() == frozenset({Language.PYTHON})
    merged = api.capabilities(Language.PYTHON)
    assert merged.completion_provider.trigger_characters == [".", "("]
    assert merged.completion_provider.resolve_provider is True
    assert merged.hover_provider is True
    assert merged.document_formatting_provider is True
    assert merged.text_document_sync is lsp.TextDocumentSyncKind.Incremental
    assert merged.position_encoding == lsp.PositionEncodingKind.Utf16
    assert changed.calls[-1] == (Language.PYTHON, merged)

    # Only providers whose capabilities allow a method receive it
    assert [p.NAME for p in api.providers_for(
        Language.PYTHON, lsp.TEXT_DOCUMENT_FORMATTING)] == ["b"]
    assert [p.NAME for p in api.providers_for(
        Language.PYTHON, lsp.TEXT_DOCUMENT_HOVER)] == ["a"]

    asyncio.run(api.stop_provider("b"))
    assert api.capabilities(Language.PYTHON).document_formatting_provider is None
    assert stopped.calls == []
    asyncio.run(api.stop_provider("a"))
    assert stopped.calls == [(Language.PYTHON,)]
    assert changed.calls[-1] == (Language.PYTHON, None)
    assert not api.is_language_supported(Language.PYTHON)


def test_start_failure_is_reported(api):
    class Broken(FakeProvider):
        async def start(self):
            raise RuntimeError("cannot start")

    api.register_provider(Broken("broken"))
    errors = Recorder(api.sig_exception_occurred)
    with pytest.raises(RuntimeError):
        asyncio.run(api.start_provider("broken"))
    assert not api.is_started("broken")
    assert "cannot start" in errors.calls[0][0]["text"]


def test_merge_capabilities_none():
    assert merge_capabilities([None, None]) is None
    merged = merge_capabilities([None, lsp.ServerCapabilities(hover_provider=True)])
    assert merged.hover_provider is True
    assert merged.completion_provider is None
