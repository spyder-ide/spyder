# Copyright 2017-2020 Palantir Technologies, Inc.
# Copyright 2021- Python Language Server Contributors.

import logging
import os.path as osp

import parso

from pylsp import _utils, hookimpl, lsp

log = logging.getLogger(__name__)

# Map to the LSP type
# > Valid values for type are ``module``, `` class ``, ``instance``, ``function``,
# > ``param``, ``path``, ``keyword``, ``property`` and ``statement``.
# see: https://jedi.readthedocs.io/en/latest/docs/api-classes.html#jedi.api.classes.BaseName.type
_TYPE_MAP = {
    'module': lsp.CompletionItemKind.Module,
    'namespace': lsp.CompletionItemKind.Module,    # to be added in Jedi 0.18+
    'class': lsp.CompletionItemKind.Class,
    'instance': lsp.CompletionItemKind.Reference,
    'function': lsp.CompletionItemKind.Function,
    'param': lsp.CompletionItemKind.Variable,
    'path': lsp.CompletionItemKind.File,
    'keyword': lsp.CompletionItemKind.Keyword,
    'property': lsp.CompletionItemKind.Property,    # added in Jedi 0.18
    'statement': lsp.CompletionItemKind.Variable
}

# Types of parso nodes for which snippet is not included in the completion
_IMPORTS = ('import_name', 'import_from')

# Types of parso node for errors
_ERRORS = ('error_node', )


@hookimpl
def pylsp_completions(config, document, position):
    """Get formatted completions for current code position"""
    settings = config.plugin_settings('jedi_completion', document_path=document.path)
    code_position = _utils.position_to_jedi_linecolumn(document, position)

    code_position["fuzzy"] = settings.get("fuzzy", False)
    completions = document.jedi_script(use_document_path=True).complete(**code_position)

    if not completions:
        return None

    completion_capabilities = config.capabilities.get('textDocument', {}).get('completion', {})
    snippet_support = completion_capabilities.get('completionItem', {}).get('snippetSupport')

    should_include_params = settings.get('include_params')
    should_include_class_objects = settings.get('include_class_objects', True)

    include_params = snippet_support and should_include_params and use_snippets(document, position)
    include_class_objects = snippet_support and should_include_class_objects and use_snippets(document, position)

    ready_completions = [
        _format_completion(c, include_params)
        for c in completions
    ]

    if include_class_objects:
        for c in completions:
            if c.type == 'class':
                completion_dict = _format_completion(c, False)
                completion_dict['kind'] = lsp.CompletionItemKind.TypeParameter
                completion_dict['label'] += ' object'
                ready_completions.append(completion_dict)

    return ready_completions or None


def is_exception_class(name):
    """
    Determine if a class name is an instance of an Exception.

    This returns `False` if the name given corresponds with a instance of
    the 'Exception' class, `True` otherwise
    """
    try:
        return name in [cls.__name__ for cls in Exception.__subclasses__()]
    except AttributeError:
        # Needed in case a class don't uses new-style
        # class definition in Python 2
        return False


def use_snippets(document, position):
    """
    Determine if it's necessary to return snippets in code completions.

    This returns `False` if a completion is being requested on an import
    statement, `True` otherwise.
    """
    line = position['line']
    lines = document.source.split('\n', line)
    act_lines = [lines[line][:position['character']]]
    line -= 1
    last_character = ''
    while line > -1:
        act_line = lines[line]
        if (act_line.rstrip().endswith('\\') or
                act_line.rstrip().endswith('(') or
                act_line.rstrip().endswith(',')):
            act_lines.insert(0, act_line)
            line -= 1
            if act_line.rstrip().endswith('('):
                # Needs to be added to the end of the code before parsing
                # to make it valid, otherwise the node type could end
                # being an 'error_node' for multi-line imports that use '('
                last_character = ')'
        else:
            break
    if '(' in act_lines[-1].strip():
        last_character = ')'
    code = '\n'.join(act_lines).split(';')[-1].strip() + last_character
    tokens = parso.parse(code)
    expr_type = tokens.children[0].type
    return (expr_type not in _IMPORTS and
            not (expr_type in _ERRORS and 'import' in code))


def _format_completion(d, include_params=True):
    completion = {
        'label': _label(d),
        'kind': _TYPE_MAP.get(d.type),
        'detail': _detail(d),
        'documentation': _utils.format_docstring(d.docstring()),
        'sortText': _sort_text(d),
        'insertText': d.name
    }

    if d.type == 'path':
        path = osp.normpath(d.name)
        path = path.replace('\\', '\\\\')
        path = path.replace('/', '\\/')
        completion['insertText'] = path

    sig = d.get_signatures()
    if (include_params and sig and not is_exception_class(d.name)):
        positional_args = [param for param in sig[0].params
                           if '=' not in param.description and
                           param.name not in {'/', '*'}]

        if len(positional_args) > 1:
            # For completions with params, we can generate a snippet instead
            completion['insertTextFormat'] = lsp.InsertTextFormat.Snippet
            snippet = d.name + '('
            for i, param in enumerate(positional_args):
                snippet += '${%s:%s}' % (i + 1, param.name)
                if i < len(positional_args) - 1:
                    snippet += ', '
            snippet += ')$0'
            completion['insertText'] = snippet
        elif len(positional_args) == 1:
            completion['insertTextFormat'] = lsp.InsertTextFormat.Snippet
            completion['insertText'] = d.name + '($0)'
        else:
            completion['insertText'] = d.name + '()'

    return completion


def _label(definition):
    sig = definition.get_signatures()
    if definition.type in ('function', 'method') and sig:
        params = ', '.join(param.name for param in sig[0].params)
        return '{}({})'.format(definition.name, params)

    return definition.name


def _detail(definition):
    try:
        return definition.parent().full_name or ''
    except AttributeError:
        return definition.full_name or ''


def _sort_text(definition):
    """ Ensure builtins appear at the bottom.
    Description is of format <type>: <module>.<item>
    """

    # If its 'hidden', put it next last
    prefix = 'z{}' if definition.name.startswith('_') else 'a{}'
    return prefix.format(definition.name)
