# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Request policies and merge strategies.

A :class:`RequestPolicy` decides which providers answer an LSP request and
how their answers are combined. A merge strategy combines the answers of
several providers for one method.
"""

from __future__ import annotations

# Standard library imports
import enum
from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from typing import Any

# Third party imports
from lsprotocol import types as lsp

# Local imports
from spyder.plugins.languageservices.api.provider import (
    FEATURE_METHODS,
    FEATURE_NAMES,
)


class RequestMode(str, enum.Enum):
    """How providers take part in a request."""

    MERGE = "merge"
    """Every provider is asked and the answers are merged."""

    EXCLUSIVE = "exclusive"
    """A single provider is asked (``preferred`` or the highest priority)."""


@dataclass(frozen=True)
class RequestPolicy:
    """Policy applied to one LSP request method.

    ``mode`` is fixed per feature (see :data:`DEFAULT_POLICIES`) and is not part
    of the user configuration. Only ``enabled``, ``providers`` and
    ``timeout_ms`` are configurable.
    """

    mode: RequestMode = RequestMode.MERGE
    enabled: bool = True
    """Whether the feature is answered at all."""
    providers: tuple[str, ...] = ()
    """Providers answering the feature, in priority order. Empty selects every
    supporting provider in global priority order (for ``EXCLUSIVE``, its
    highest-priority provider). A non-empty tuple both restricts the feature to
    the named providers and orders them, overriding their global priority."""
    timeout_ms: int | None = None
    """Per-provider timeout. ``None`` uses the plugin-wide default."""

    def to_conf(self) -> dict[str, Any]:
        """Serialize the configurable fields to the configuration
        representation. ``mode`` is fixed per feature and is not stored."""
        return {
            "enabled": self.enabled,
            "providers": list(self.providers),
            "timeout_ms": self.timeout_ms,
        }

    @classmethod
    def from_conf(
        cls, data: dict[str, Any] | None, default: RequestPolicy
    ) -> RequestPolicy:
        """Build a policy from configuration, filling gaps from ``default``.

        ``mode`` always comes from ``default``. Any ``mode`` in ``data`` is
        ignored, since the mode is fixed per feature.
        """
        if not data:
            return default
        policy = default
        if "enabled" in data and data["enabled"] is not None:
            policy = replace(policy, enabled=bool(data["enabled"]))
        if "providers" in data and data["providers"] is not None:
            policy = replace(policy, providers=tuple(data["providers"]))
        if "timeout_ms" in data:
            policy = replace(policy, timeout_ms=data["timeout_ms"])
        return policy


MergeStrategy = Callable[[list[tuple[str, Any]]], Any]
"""Combine ``[(provider NAME, result), ...]`` (priority order) into one."""

_MERGE_STRATEGIES: dict[str, MergeStrategy] = {}


def register_merge_strategy(method: str, strategy: MergeStrategy) -> None:
    """Set the strategy merging the answers to the LSP ``method``."""
    _MERGE_STRATEGIES[method] = strategy


def merge_strategy(method: str) -> MergeStrategy:
    """Strategy merging answers to ``method`` (first non-None by default)."""
    return _MERGE_STRATEGIES.get(method, first_non_none)


def feature_name(method: str) -> str:
    """Configuration key of the LSP ``method`` (its feature name)."""
    try:
        return FEATURE_METHODS[method]
    except KeyError as exc:
        raise KeyError(f"{method!r} is not a language services feature") from exc


def feature_method(name: str) -> str:
    """LSP method of the feature ``name``."""
    try:
        return FEATURE_NAMES[name]
    except KeyError as exc:
        raise KeyError(f"{name!r} is not a language services feature") from exc


# ---- Strategies ------------------------------------------------------------
def first_non_none(results: list[tuple[str, Any]]) -> Any:
    for _, result in results:
        if result is not None:
            return result
    return None


def concatenate(results: list[tuple[str, Any]]) -> list | None:
    merged: list = []
    found = False
    for _, result in results:
        if result is None:
            continue
        found = True
        merged.extend(result)
    return merged if found else None


def _completion_items(result: Any) -> Iterable[lsp.CompletionItem]:
    if result is None:
        return ()
    if isinstance(result, lsp.CompletionList):
        return result.items or ()
    return result


def merge_completions(
    results: list[tuple[str, Any]],
) -> list[lsp.CompletionItem] | None:
    """Merge completion answers.

    Items are deduplicated by stripped label (first provider wins),
    ``sort_text`` is prefixed with the provider's rank so earlier providers
    sort first, and ``item.data["provider"]`` records the provider NAME.
    """
    if all(result is None for _, result in results):
        return None
    merged: list[lsp.CompletionItem] = []
    seen: set[str] = set()
    for rank, (name, result) in enumerate(results):
        for item in _completion_items(result):
            key = item.label.strip()
            if key in seen:
                continue
            seen.add(key)
            original = item.sort_text or item.label
            item.sort_text = f"{rank:03d}_{original}"
            data = item.data if isinstance(item.data, dict) else {}
            item.data = {**data, "provider": name}
            merged.append(item)
    return merged


def merge_diagnostics(
    results: list[tuple[str, list[lsp.Diagnostic] | None]],
) -> list[lsp.Diagnostic]:
    """Concatenate diagnostics, naming the provider in empty ``source``."""
    merged: list[lsp.Diagnostic] = []
    for name, diagnostics in results:
        for diagnostic in diagnostics or ():
            if not diagnostic.source:
                diagnostic.source = name
            merged.append(diagnostic)
    return merged


def merge_definitions(results: list[tuple[str, Any]]) -> list | None:
    """Normalize ``Location | list[Location] | list[LocationLink]`` and
    concatenate."""
    normalized = []
    for name, result in results:
        if result is None:
            continue
        if isinstance(result, (lsp.Location, lsp.LocationLink)):
            result = [result]
        normalized.append((name, list(result)))
    return concatenate(normalized)


def merge_folding_ranges(
    results: list[tuple[str, Any]],
) -> list[lsp.FoldingRange] | None:
    """Concatenate, dropping ranges with the same start and end lines."""
    merged = concatenate(results)
    if merged is None:
        return None
    unique: list[lsp.FoldingRange] = []
    seen: set[tuple[int, int]] = set()
    for folding_range in merged:
        key = (folding_range.start_line, folding_range.end_line)
        if key in seen:
            continue
        seen.add(key)
        unique.append(folding_range)
    return unique


register_merge_strategy(lsp.TEXT_DOCUMENT_COMPLETION, merge_completions)
register_merge_strategy(lsp.TEXT_DOCUMENT_PUBLISH_DIAGNOSTICS, merge_diagnostics)
register_merge_strategy(lsp.TEXT_DOCUMENT_DEFINITION, merge_definitions)
register_merge_strategy(lsp.TEXT_DOCUMENT_REFERENCES, concatenate)
register_merge_strategy(lsp.TEXT_DOCUMENT_DOCUMENT_SYMBOL, concatenate)
register_merge_strategy(lsp.TEXT_DOCUMENT_FOLDING_RANGE, merge_folding_ranges)
register_merge_strategy(lsp.TEXT_DOCUMENT_CODE_ACTION, concatenate)
register_merge_strategy(lsp.WORKSPACE_SYMBOL, concatenate)

_EXCLUSIVE = RequestPolicy(mode=RequestMode.EXCLUSIVE)
_MERGE = RequestPolicy(mode=RequestMode.MERGE)

DEFAULT_FEATURE_POLICIES: dict[str, RequestPolicy] = {
    lsp.TEXT_DOCUMENT_COMPLETION: _MERGE,
    lsp.COMPLETION_ITEM_RESOLVE: _EXCLUSIVE,
    lsp.TEXT_DOCUMENT_HOVER: _MERGE,
    lsp.TEXT_DOCUMENT_SIGNATURE_HELP: _EXCLUSIVE,
    lsp.TEXT_DOCUMENT_DEFINITION: _MERGE,
    lsp.TEXT_DOCUMENT_REFERENCES: _MERGE,
    lsp.TEXT_DOCUMENT_DOCUMENT_SYMBOL: _MERGE,
    lsp.TEXT_DOCUMENT_FOLDING_RANGE: _MERGE,
    lsp.TEXT_DOCUMENT_FORMATTING: _EXCLUSIVE,
    lsp.TEXT_DOCUMENT_RANGE_FORMATTING: _EXCLUSIVE,
    lsp.TEXT_DOCUMENT_CODE_ACTION: _MERGE,
    lsp.TEXT_DOCUMENT_RENAME: _EXCLUSIVE,
    lsp.WORKSPACE_SYMBOL: _MERGE,
    lsp.WORKSPACE_EXECUTE_COMMAND: _EXCLUSIVE,
}
"""Policy of every feature when the configuration has no entry."""
