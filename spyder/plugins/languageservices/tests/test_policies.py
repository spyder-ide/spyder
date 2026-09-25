# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for request policies and merge strategies."""

from lsprotocol import types as lsp
import pytest

from spyder.plugins.languageservices.api.policies import (
    DEFAULT_FEATURE_POLICIES,
    RequestMode,
    RequestPolicy,
    feature_method,
    feature_name,
    merge_completions,
    merge_definitions,
    merge_diagnostics,
    merge_folding_ranges,
    merge_strategy,
    register_merge_strategy,
)
from spyder.plugins.languageservices.api.provider import FEATURE_METHODS


def item(label, sort_text=None, data=None):
    return lsp.CompletionItem(label=label, sort_text=sort_text, data=data)


def test_every_feature_has_a_default_policy():
    assert set(DEFAULT_FEATURE_POLICIES) == set(FEATURE_METHODS)
    assert DEFAULT_FEATURE_POLICIES[lsp.TEXT_DOCUMENT_FORMATTING].mode is (
        RequestMode.EXCLUSIVE
    )
    assert DEFAULT_FEATURE_POLICIES[lsp.TEXT_DOCUMENT_COMPLETION].mode is (
        RequestMode.MERGE
    )


def test_feature_name_roundtrip():
    assert feature_name(lsp.TEXT_DOCUMENT_COMPLETION) == "completion"
    assert feature_method("completion") == lsp.TEXT_DOCUMENT_COMPLETION
    with pytest.raises(KeyError):
        feature_name("textDocument/nope")


def test_policy_from_conf_fills_gaps():
    default = RequestPolicy(mode=RequestMode.MERGE)
    assert RequestPolicy.from_conf(None, default) is default
    policy = RequestPolicy.from_conf(
        {"enabled": False, "providers": ["lsp", "fallback"]}, default
    )
    assert policy.mode is RequestMode.MERGE
    assert policy.enabled is False
    assert policy.providers == ("lsp", "fallback")
    assert policy.timeout_ms is None
    assert RequestPolicy.from_conf(policy.to_conf(), default) == policy


def test_policy_from_conf_ignores_mode():
    default = RequestPolicy(mode=RequestMode.EXCLUSIVE)
    policy = RequestPolicy.from_conf({"mode": "merge"}, default)
    assert policy.mode is RequestMode.EXCLUSIVE
    assert "mode" not in default.to_conf()


def test_merge_completions_dedupes_ranks_and_stamps_provider():
    merged = merge_completions(
        [
            ("lsp", lsp.CompletionList(is_incomplete=False, items=[
                item("foo", data={"resolve": True}), item(" bar ")])),
            ("fallback", [item("bar"), item("baz", sort_text="zz")]),
            ("snippets", None),
        ]
    )
    assert [i.label for i in merged] == ["foo", " bar ", "baz"]
    assert [i.sort_text for i in merged] == ["000_foo", "000_ bar ", "001_zz"]
    assert merged[0].data == {"resolve": True, "provider": "lsp"}
    assert merged[2].data == {"provider": "fallback"}
    assert merge_completions([("a", None), ("b", None)]) is None
    assert merge_completions([("a", [])]) == []


def test_merge_diagnostics_names_source():
    diag = lsp.Diagnostic(
        range=lsp.Range(lsp.Position(0, 0), lsp.Position(0, 1)), message="m"
    )
    named = lsp.Diagnostic(
        range=diag.range, message="n", source="pyflakes"
    )
    merged = merge_diagnostics([("pylsp", [named]), ("other", [diag])])
    assert [d.source for d in merged] == ["pyflakes", "other"]


def test_merge_definitions_normalizes():
    loc = lsp.Location(
        uri="file:///a", range=lsp.Range(lsp.Position(0, 0), lsp.Position(0, 0))
    )
    assert merge_definitions([("a", loc), ("b", [loc]), ("c", None)]) == [
        loc, loc
    ]
    assert merge_definitions([("a", None)]) is None


def test_merge_folding_ranges_dedupes():
    ranges = [
        lsp.FoldingRange(start_line=0, end_line=3),
        lsp.FoldingRange(start_line=0, end_line=3),
        lsp.FoldingRange(start_line=5, end_line=6),
    ]
    merged = merge_folding_ranges([("a", ranges[:2]), ("b", ranges[2:])])
    assert [(r.start_line, r.end_line) for r in merged] == [(0, 3), (5, 6)]


def test_register_merge_strategy():
    method = "textDocument/custom"
    assert merge_strategy(method)([("a", None), ("b", 1)]) == 1
    register_merge_strategy(method, lambda results: len(results))
    assert merge_strategy(method)([("a", None), ("b", 1)]) == 2
