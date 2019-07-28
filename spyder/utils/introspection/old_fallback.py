# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Introspection utilities used by Spyder
"""

from __future__ import print_function
import imp
import os
import os.path as osp
import re
import time

from pygments.token import Token

from spyder.utils.debug import log_dt
from spyder.utils import encoding
from spyder.utils.introspection.manager import (DEBUG_EDITOR, LOG_FILENAME,
                                                IntrospectionPlugin)
from spyder.utils.introspection.utils import (default_info_response,
                                              memoize,
                                              find_lexer_for_filename,
                                              get_keywords)
from spyder.plugins.editor.utils import languages


class FallbackPlugin(IntrospectionPlugin):
    """Basic Introspection Plugin for Spyder"""

    # ---- IntrospectionPlugin API --------------------------------------------
    name = 'fallback'

    def get_completions(self, info):
        """Return a list of (completion, type) tuples

        Simple completion based on python-like identifiers and whitespace
        """
        if not info['obj']:
            return
        items = []
        obj = info['obj']
        if info['context']:
            lexer = find_lexer_for_filename(info['filename'])
            # get a list of token matches for the current object
            tokens = lexer.get_tokens(info['source_code'])
            for (context, token) in tokens:
                token = token.strip()
                if (context in info['context'] and
                        token.startswith(obj) and
                        obj != token):
                    items.append(token)
            # add in keywords if not in a string
            if context not in Token.Literal.String:
                try:
                    keywords = get_keywords(lexer)
                    items.extend(k for k in keywords if k.startswith(obj))
                except Exception:
                    pass
        else:
            tokens = set(re.findall(info['id_regex'], info['source_code']))
            items = [item for item in tokens if
                 item.startswith(obj) and len(item) > len(obj)]
            if '.' in obj:
                start = obj.rfind('.') + 1
            else:
                start = 0

            items = [i[start:len(obj)] + i[len(obj):].split('.')[0]
                 for i in items]
        # get path completions
        # get last word back to a space or a quote character
        match = re.search(r'''[ "\']([\w\.\\\\/]+)\Z''', info['line'])
        if match:
            items += _complete_path(match.groups()[0])
        return [(i, '') for i in sorted(items)]

    def get_definition(self, info):
        """
        Find the definition for an object within a set of source code

        This is used to find the path of python-like modules
        (e.g. cython and enaml) for a goto definition
        """
        if not info['is_python_like']:
            return
        token = info['obj']
        lines = info['lines']
        source_code = info['source_code']
        filename = info['filename']

        line_nr = None
        if token is None:
            return
        if '.' in token:
            token = token.split('.')[-1]

        line_nr = get_definition_with_regex(source_code, token,
                                            len(lines))
        if line_nr is None:
            return
        line = info['line']
        exts = python_like_exts()
        if not osp.splitext(filename)[-1] in exts:
            return filename, line_nr
        if line.startswith('import ') or line.startswith('from '):
            alt_path = osp.dirname(filename)
            source_file = python_like_mod_finder(line, alt_path=alt_path,
                                                 stop_token=token)
            if (not source_file or
                    not osp.splitext(source_file)[-1] in exts):
                line_nr = get_definition_with_regex(source_code, token,
                                                    line_nr)
                return filename, line_nr
            mod_name = osp.basename(source_file).split('.')[0]
            if mod_name == token or mod_name == '__init__':
                return source_file, 1
            else:
                with open(filename, 'rb') as fid:
                    code = fid.read()
                code = encoding.decode(code)[0]
                line_nr = get_definition_with_regex(code, token)

        return filename, line_nr

    def get_info(self, info):
        """Get a formatted calltip and docstring from Fallback"""
        if info['docstring']:
            if info['filename']:
                filename = os.path.basename(info['filename'])
                filename = os.path.splitext(filename)[0]
            else:
                filename = '<module>'
            resp = dict(docstring=info['docstring'],
                        name=filename,
                        note='',
                        argspec='',
                        calltip=None)
            return resp
        else:
            return default_info_response()


@memoize
def python_like_mod_finder(import_line, alt_path=None,
                           stop_token=None):
    """
    Locate a module path based on an import line in an python-like file

    import_line is the line of source code containing the import
    alt_path specifies an alternate base path for the module
    stop_token specifies the desired name to stop on

    This is used to a find the path to python-like modules
    (e.g. cython and enaml) for a goto definition.
    """
    if stop_token and '.' in stop_token:
        stop_token = stop_token.split('.')[-1]
    tokens = re.split(r'\W', import_line)
    if tokens[0] in ['from', 'import']:
        # find the base location
        try:
            _, path, _ = imp.find_module(tokens[1])
        except ImportError:
            if alt_path:
                path = osp.join(alt_path, tokens[1])
            else:
                path = None
        if path:
            path = osp.realpath(path)
            if not tokens[1] == stop_token:
                for part in tokens[2:]:
                    if part in ['import', 'cimport', 'as']:
                        break
                    path = osp.join(path, part)
                    if part == stop_token:
                        break
            # from package import module
            if stop_token and not stop_token in path:
                for ext in python_like_exts():
                    fname = '%s%s' % (stop_token, ext)
                    if osp.exists(osp.join(path, fname)):
                        return osp.join(path, fname)
            # from module import name
            for ext in python_like_exts():
                fname = '%s%s' % (path, ext)
                if osp.exists(fname):
                    return fname
            # if it is a file, return it
            if osp.exists(path) and not osp.isdir(path):
                return path
            # default to the package file
            path = osp.join(path, '__init__.py')
            if osp.exists(path):
                return path


def get_definition_with_regex(source, token, start_line=-1):
    """
    Find the definition of an object within a source closest to a given line
    """
    if not token:
        return None
    if DEBUG_EDITOR:
        t0 = time.time()
    patterns = [  # python / cython keyword definitions
                r'^c?import.*\W{0}{1}',
                r'from.*\W{0}\W.*c?import ',
                r'from .* c?import.*\W{0}{1}',
                r'class\s*{0}{1}',
                r'c?p?def[^=]*\W{0}{1}',
                r'cdef.*\[.*\].*\W{0}{1}',
                # enaml keyword definitions
                r'enamldef.*\W{0}{1}',
                r'attr.*\W{0}{1}',
                r'event.*\W{0}{1}',
                r'id\s*:.*\W{0}{1}']

    matches = get_matches(patterns, source, token, start_line)

    if not matches:
        patterns = [r'.*\Wself.{0}{1}[^=!<>]*=[^=]',
                    r'.*\W{0}{1}[^=!<>]*=[^=]',
                    r'self.{0}{1}[^=!<>]*=[^=]',
                    r'{0}{1}[^=!<>]*=[^=]']
        matches = get_matches(patterns, source, token, start_line)
    # find the one closest to the start line (prefer before the start line)
    if matches:
        min_dist = len(source.splitlines())
        best_ind = 0
        for match in matches:
            dist = abs(start_line - match)
            if match <= start_line or not best_ind:
                if dist < min_dist:
                    min_dist = dist
                    best_ind = match
    if matches:
        if DEBUG_EDITOR:
            log_dt(LOG_FILENAME, 'regex definition match', t0)
        return best_ind
    else:
        if DEBUG_EDITOR:
            log_dt(LOG_FILENAME, 'regex definition failed match', t0)
        return None


def get_matches(patterns, source, token, start_line):
    patterns = [pattern.format(token, r'[^0-9a-zA-Z.[]')
                for pattern in patterns]
    pattern = re.compile(r'|^'.join(patterns))
    # add the trailing space to allow some regexes to match
    lines = [line.strip() + ' ' for line in source.splitlines()]
    if start_line == -1:
        start_line = len(lines)
    matches = []
    for (index, line) in enumerate(lines):
        if re.match(pattern, line):
            matches.append(index + 1)
    return matches


def python_like_exts():
    """Return a list of all python-like extensions"""
    exts = []
    for lang in languages.PYTHON_LIKE_LANGUAGES:
        exts.extend(list(languages.ALL_LANGUAGES[lang]))
    return ['.' + ext for ext in exts]


def all_editable_exts():
    """Return a list of all editable extensions"""
    exts = []
    for (language, extensions) in languages.ALL_LANGUAGES.items():
        exts.extend(list(extensions))
    return ['.' + ext for ext in exts]


def _listdir(root):
    "List directory 'root' appending the path separator to subdirs."
    res = []
    root = os.path.expanduser(root)
    try:
        for name in os.listdir(root):
            path = os.path.join(root, name)
            if os.path.isdir(path):
                name += os.sep
            res.append(name)
    except:
        pass  # no need to report invalid paths
    return res


def _complete_path(path=None):
    """Perform completion of filesystem path.
    https://stackoverflow.com/questions/5637124/tab-completion-in-pythons-raw-input
    """
    if not path:
        return _listdir('.')
    dirname, rest = os.path.split(path)
    tmp = dirname if dirname else '.'
    res = [p for p in _listdir(tmp) if p.startswith(rest)]
    # more than one match, or single match which does not exist (typo)
    if len(res) > 1 or not os.path.exists(path):
        return res
    # resolved to a single directory, so return list of files below it
    if os.path.isdir(path):
        return [p for p in _listdir(path)]
    # exact file match terminates this completion
    return [path + ' ']
