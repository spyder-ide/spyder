# Copyright 2017 Palantir Technologies, Inc.
import logging
from pyls import hookimpl, lsp, _utils

log = logging.getLogger(__name__)


@hookimpl
def pyls_document_highlight(document, position):
    code_position = _utils.position_to_jedi_linecolumn(document, position)
    usages = document.jedi_script().get_references(**code_position)

    def is_valid(definition):
        return definition.line is not None and definition.column is not None

    def local_to_document(definition):
        return not definition.module_path or str(definition.module_path) == document.path

    return [{
        'range': {
            'start': {'line': d.line - 1, 'character': d.column},
            'end': {'line': d.line - 1, 'character': d.column + len(d.name)}
        },
        'kind': lsp.DocumentHighlightKind.Write if d.is_definition() else lsp.DocumentHighlightKind.Read
    } for d in usages if is_valid(d) and local_to_document(d)]
