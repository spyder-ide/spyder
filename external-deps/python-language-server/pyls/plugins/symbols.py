# Copyright 2017 Palantir Technologies, Inc.
import logging
import os

from pyls import hookimpl
from pyls.lsp import SymbolKind

log = logging.getLogger(__name__)


@hookimpl
def pyls_document_symbols(config, document):
    # pylint: disable=broad-except
    # pylint: disable=too-many-nested-blocks
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-branches
    symbols_settings = config.plugin_settings('jedi_symbols')
    all_scopes = symbols_settings.get('all_scopes', True)
    add_import_symbols = symbols_settings.get('include_import_symbols', True)

    use_document_path = False
    document_dir = os.path.normpath(os.path.dirname(document.path))
    if not os.path.isfile(os.path.join(document_dir, '__init__.py')):
        use_document_path = True

    definitions = document.jedi_names(use_document_path, all_scopes=all_scopes)
    module_name = document.dot_path
    symbols = []
    exclude = set({})
    redefinitions = {}
    while definitions != []:
        d = definitions.pop(0)
        if not add_import_symbols:
            sym_full_name = d.full_name
            if sym_full_name is not None:
                if (not sym_full_name.startswith(module_name) and
                        not sym_full_name.startswith('__main__')):
                    continue

        if _include_def(d) and document.path == d.module_path:
            tuple_range = _tuple_range(d)
            if tuple_range in exclude:
                continue

            kind = redefinitions.get(tuple_range, None)
            if kind is not None:
                exclude |= {tuple_range}

            if d.type == 'statement':
                if d.description.startswith('self'):
                    kind = 'field'

            symbol = {
                'name': d.name,
                'containerName': _container(d),
                'location': {
                    'uri': document.uri,
                    'range': _range(d),
                },
                'kind': _kind(d) if kind is None else _SYMBOL_KIND_MAP[kind],
            }
            symbols.append(symbol)

            if d.type == 'class':
                try:
                    defined_names = list(d.defined_names())
                    for method in defined_names:
                        if method.type == 'function':
                            redefinitions[_tuple_range(method)] = 'method'
                        elif method.type == 'statement':
                            redefinitions[_tuple_range(method)] = 'field'
                        else:
                            redefinitions[_tuple_range(method)] = method.type
                    definitions = list(defined_names) + definitions
                except Exception:
                    pass
    return symbols


def _include_def(definition):
    return (
        # Don't tend to include parameters as symbols
        definition.type != 'param' and
        # Unused vars should also be skipped
        definition.name != '_' and
        _kind(definition) is not None
    )


def _container(definition):
    try:
        # Jedi sometimes fails here.
        parent = definition.parent()
        # Here we check that a grand-parent exists to avoid declaring symbols
        # as children of the module.
        if parent.parent():
            return parent.name
    except:  # pylint: disable=bare-except
        return None

    return None


def _range(definition):
    # This gets us more accurate end position
    definition = definition._name.tree_name.get_definition()
    (start_line, start_column) = definition.start_pos
    (end_line, end_column) = definition.end_pos
    return {
        'start': {'line': start_line - 1, 'character': start_column},
        'end': {'line': end_line - 1, 'character': end_column}
    }


def _tuple_range(definition):
    definition = definition._name.tree_name.get_definition()
    return (definition.start_pos, definition.end_pos)


_SYMBOL_KIND_MAP = {
    'none': SymbolKind.Variable,
    'type': SymbolKind.Class,
    'tuple': SymbolKind.Class,
    'dict': SymbolKind.Class,
    'dictionary': SymbolKind.Class,
    'function': SymbolKind.Function,
    'lambda': SymbolKind.Function,
    'generator': SymbolKind.Function,
    'class': SymbolKind.Class,
    'instance': SymbolKind.Class,
    'method': SymbolKind.Method,
    'builtin': SymbolKind.Class,
    'builtinfunction': SymbolKind.Function,
    'module': SymbolKind.Module,
    'file': SymbolKind.File,
    'xrange': SymbolKind.Array,
    'slice': SymbolKind.Class,
    'traceback': SymbolKind.Class,
    'frame': SymbolKind.Class,
    'buffer': SymbolKind.Array,
    'dictproxy': SymbolKind.Class,
    'funcdef': SymbolKind.Function,
    'property': SymbolKind.Property,
    'import': SymbolKind.Module,
    'keyword': SymbolKind.Variable,
    'constant': SymbolKind.Constant,
    'variable': SymbolKind.Variable,
    'value': SymbolKind.Variable,
    'param': SymbolKind.Variable,
    'statement': SymbolKind.Variable,
    'boolean': SymbolKind.Boolean,
    'int': SymbolKind.Number,
    'longlean': SymbolKind.Number,
    'float': SymbolKind.Number,
    'complex': SymbolKind.Number,
    'string': SymbolKind.String,
    'unicode': SymbolKind.String,
    'list': SymbolKind.Array,
    'field': SymbolKind.Field
}


def _kind(d):
    """ Return the VSCode Symbol Type """
    return _SYMBOL_KIND_MAP.get(d.type)
