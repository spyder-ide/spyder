# Copyright 2021- Python Language Server Contributors.

import logging

from pylsp import _utils, hookimpl

log = logging.getLogger(__name__)


def lsp_location(name):
    module_path = name.module_path
    if module_path is None or name.line is None or name.column is None:
        return None
    uri = module_path.as_uri()
    return {
        "uri": str(uri),
        "range": {
            "start": {"line": name.line - 1, "character": name.column},
            "end": {"line": name.line - 1, "character": name.column + len(name.name)},
        },
    }


@hookimpl
def pylsp_type_definition(config, document, position):
    try:
        kwargs = _utils.position_to_jedi_linecolumn(document, position)
        script = document.jedi_script()
        names = script.infer(**kwargs)
        definitions = [
            definition
            for definition in [lsp_location(name) for name in names]
            if definition is not None
        ]
        return definitions
    except Exception as e:
        log.debug("Failed to run type_definition: %s", e)
        return []
