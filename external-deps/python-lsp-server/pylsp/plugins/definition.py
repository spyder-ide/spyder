# Copyright 2017-2020 Palantir Technologies, Inc.
# Copyright 2021- Python Language Server Contributors.
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List

import jedi

from pylsp import _utils, hookimpl, uris

if TYPE_CHECKING:
    from jedi.api import Script
    from jedi.api.classes import Name

    from pylsp.config.config import Config
    from pylsp.workspace import Document

log = logging.getLogger(__name__)


MAX_JEDI_GOTO_HOPS = 100


def _resolve_definition(
    maybe_defn: Name, script: Script, settings: Dict[str, Any]
) -> Name:
    for _ in range(MAX_JEDI_GOTO_HOPS):
        if maybe_defn.is_definition() or maybe_defn.module_path != script.path:
            break
        defns = script.goto(
            follow_imports=settings.get("follow_imports", True),
            follow_builtin_imports=settings.get("follow_builtin_imports", True),
            line=maybe_defn.line,
            column=maybe_defn.column,
        )
        if len(defns) == 1:
            maybe_defn = defns[0]
        else:
            break
    return maybe_defn


@hookimpl
def pylsp_definitions(
    config: Config, document: Document, position: Dict[str, int]
) -> List[Dict[str, Any]]:
    settings = config.plugin_settings("jedi_definition")
    code_position = _utils.position_to_jedi_linecolumn(document, position)
    script = document.jedi_script(use_document_path=True)
    auto_import_modules = jedi.settings.auto_import_modules

    try:
        jedi.settings.auto_import_modules = []
        definitions = script.goto(
            follow_imports=settings.get("follow_imports", True),
            follow_builtin_imports=settings.get("follow_builtin_imports", True),
            **code_position,
        )
        definitions = [_resolve_definition(d, script, settings) for d in definitions]
    finally:
        jedi.settings.auto_import_modules = auto_import_modules

    follow_builtin_defns = settings.get("follow_builtin_definitions", True)
    return [
        {
            "uri": uris.uri_with(document.uri, path=str(d.module_path)),
            "range": {
                "start": {"line": d.line - 1, "character": d.column},
                "end": {"line": d.line - 1, "character": d.column + len(d.name)},
            },
        }
        for d in definitions
        if d.is_definition() and (follow_builtin_defns or _not_internal_definition(d))
    ]


def _not_internal_definition(definition: Name) -> bool:
    return (
        definition.line is not None
        and definition.column is not None
        and definition.module_path is not None
        and not definition.in_builtin_module()
    )
