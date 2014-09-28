# -*- coding: utf-8 -*-
#
# Copyright © 2013 The Spyder Development Team
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Introspection utilities used by Spyder
"""

from __future__ import print_function
import imp
import os
import os.path as osp
import re
import time
import functools

from spyderlib.baseconfig import DEBUG, get_conf_path, debug_print
from spyderlib.utils.debug import log_dt, log_last_error
from spyderlib.utils import sourcecode, encoding
from spyderlib.utils.dochelpers import getsignaturefromtext
from spyderlib.utils.introspection.plugin_manager import IntrospectionPlugin
from spyderlib.utils.introspection.module_completion import module_completion


PLUGINS = ['jedi', 'rope', 'fallback']
LOG_FILENAME = get_conf_path('introspection.log')
DEBUG_EDITOR = DEBUG >= 3


def memoize(obj):
    """
    Memoize objects to trade memory for execution speed

    Use a limited size cache to store the value, which takes into account
    The calling args and kwargs

    See https://wiki.python.org/moin/PythonDecoratorLibrary#Memoize
    """
    cache = obj.cache = {}

    @functools.wraps(obj)
    def memoizer(*args, **kwargs):
        key = str(args) + str(kwargs)
        if key not in cache:
            cache[key] = obj(*args, **kwargs)
        # only keep the most recent 100 entries
        if len(cache) > 100:
            cache.popitem(last=False)
        return cache[key]
    return memoizer


class FallbackPlugin(IntrospectionPlugin):
    """Basic Introspection Plugin for Spyder"""

    # ---- IntrospectionPlugin API --------------------------------------------
    name = 'fallback'

    def get_completions(self, info):
        """Return a list of completion strings"""
        return self.get_token_completion_list(source_code, offset, filename)

    def get_definition(self, info):
        """Find a path and line number for a definition"""
        return self.get_definition_location_regex(source_code, offset, 
                                                  filename)
    
    # ---- Private API -------------------------------------------------------

    @staticmethod
    def _token_based_completion(script, offset):
        """Simple completion based on python-like identifiers and whitespace"""
        base_tokens = split_words(script[:offset])
        base = base_tokens[-1]
        tokens = set(split_words(script))
        items = [item for item in tokens if
                 item.startswith(base) and len(item) > len(base)]
        if '.' in base:
            start = base.rfind('.') + 1
        else:
            start = 0
        items = [i[start:len(base)] + i[len(base):].split('.')[0] for i in items]
        return list(sorted(items))
            
    @memoize
    def python_like_mod_finder(self, import_line, alt_path=None, 
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
                    for ext in self.python_like_exts():
                        fname = '%s%s' % (stop_token, ext)
                        if osp.exists(osp.join(path, fname)):
                            return osp.join(path, fname)
                # from module import name
                for ext in self.python_like_exts():
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

    def _get_definition_location_regex(self, source_code, offset, filename):
        """
        Find the definition for an object within a set of source code
        
        This is used to find the path of python-like modules 
        (e.g. cython and enaml) for a goto definition
        """
        token = sourcecode.get_primary_at(source_code, offset)
        eol = sourcecode.get_eol_chars(source_code) or '\n'
        lines = source_code[:offset].split(eol)
        line_nr = None
        if '.' in token:
            temp = token.split('.')[-1]
            line_nr = self.get_definition_with_regex(source_code, temp, 
                                                     len(lines))
        if line_nr is None:
            line_nr = self.get_definition_with_regex(source_code, token, 
                                                 len(lines), True)
        if line_nr is None and '.' in token:
            temp = token.split('.')[-1]
            line_nr = self.get_definition_with_regex(source_code, temp, 
                                                 len(lines), True)
        if line_nr is None:
            return None, None
        line = source_code.split(eol)[line_nr - 1].strip()
        exts = self.python_like_exts()
        if not osp.splitext(filename)[-1] in exts:
            return filename, line_nr
        if line.startswith('import ') or line.startswith('from '):
            alt_path = osp.dirname(filename)
            source_file = self.python_like_mod_finder(line, alt_path=alt_path,
                                                 stop_token=token)
            if (not source_file or
                    not osp.splitext(source_file)[-1] in exts):
                line_nr = self.get_definition_with_regex(source_code, token, 
                                                         line_nr)
                return filename, line_nr
            mod_name = osp.basename(source_file).split('.')[0]
            if mod_name == token or mod_name == '__init__':
                return source_file, 1
            else:
                line_nr = self.get_definition_from_file(source_file, token)
                return source_file, line_nr
        return filename, line_nr
        
    @memoize
    def get_definition_from_file(self, filename, name, line_nr=-1):
        """Find the definition for an object in a filename"""
        with open(filename, 'rb') as fid:
            code = fid.read()
        code = encoding.decode(code)[0]
        return self.get_definition_with_regex(code, name, line_nr)
        
    @staticmethod
    def get_definition_with_regex(source, token, start_line=-1, 
                                  use_assignment=False):
        """
        Find the definition of an object within a source closest to a given line
        """
        if not token:
            return None
        if DEBUG_EDITOR:
            t0 = time.time()
        patterns = [  # python / cython keyword definitions
                    '^c?import.*\W{0}{1}',
                    'from.*\W{0}\W.*c?import ',
                    'from .* c?import.*\W{0}{1}',
                    'class\s*{0}{1}',
                    'c?p?def[^=]*\W{0}{1}',
                    'cdef.*\[.*\].*\W{0}{1}',
                    # enaml keyword definitions
                    'enamldef.*\W{0}{1}',
                    'attr.*\W{0}{1}',
                    'event.*\W{0}{1}',
                    'id\s*:.*\W{0}{1}']
        if use_assignment:
            patterns += ['.*\Wself.{0}{1}[^=!<>]*=[^=]',
                        '.*\W{0}{1}[^=!<>]*=[^=]',
                        'self.{0}{1}[^=!<>]*=[^=]',
                        '{0}{1}[^=!<>]*=[^=]']
        patterns = [pattern.format(token, r'[^0-9a-zA-Z.[]')
                    for pattern in patterns]
        pattern = re.compile('|^'.join(patterns))
        # add the trailing space to allow some regexes to match
        eol = sourcecode.get_eol_chars(source) or '\n'
        lines = source.split(eol)
        lines = [line.strip() + ' ' for line in lines]
        if start_line == -1:
            start_line = len(lines)
        matches = []
        for (index, line) in enumerate(lines):
            if re.match(pattern, line):
                matches.append(index + 1)
        # find the one closest to the start line (prefer before the start line)
        if matches:
            min_dist = len(lines)
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

    @staticmethod
    @memoize
    def get_parent_until(path):
        """
        Given a file path, determine the full module path
    
        e.g. '/usr/lib/python2.7/dist-packages/numpy/core/__init__.pyc' yields
        'numpy.core'
        """
        dirname = osp.dirname(path)
        try:
            mod = osp.basename(path)
            mod = osp.splitext(mod)[0]
            imp.find_module(mod, [dirname])
        except ImportError:
            return
        items = [mod]
        while 1:
            items.append(osp.basename(dirname))
            try:
                dirname = osp.dirname(dirname)
                imp.find_module('__init__', [dirname + os.sep])
            except ImportError:
                break
        return '.'.join(reversed(items))

    @staticmethod
    def python_like_exts():
        """Return a list of all python-like extensions"""
        exts = []
        for lang in sourcecode.PYTHON_LIKE_LANGUAGES:
            exts.extend(list(sourcecode.ALL_LANGUAGES[lang]))
        return ['.' + ext for ext in exts]
    
    @staticmethod
    def all_editable_exts():
        """Return a list of all editable extensions"""
        exts = []
        for (language, extensions) in sourcecode.ALL_LANGUAGES.items():
            exts.extend(list(extensions))
        return ['.' + ext for ext in exts]


# TODO: put these in the base plugin
def _get_module_completion(text):
    """Get completions for import statements using module_completion.
    """
    text = text.lstrip()
    comp_list = module_completion(text, self.path)
    words = text.split(' ')
    if text.startswith('import'):
        if ',' in words[-1]:
            words = words[-1].split(',')
    else:
        if '(' in words[-1]:
            words = words[:-2] + words[-1].split('(')
        if ',' in words[-1]:
            words = words[:-2] + words[-1].split(',')
    completion_text = words[-1]
    return comp_list, completion_text



def get_obj_info():

        source_code = self.get_source_code()
        offset = self.find_nearest_function_call(position)

        # Get calltip and docs
        helplist = self.introspection_plugin.get_calltip_and_docs(source_code,
                                                         offset, self.filename)
        if not helplist:
            return
        obj_fullname = ''
        signature = ''
        cts, doc_text = helplist

        obj_fullname, '', '', '', not auto

        if cts:
            cts = cts.replace('.__init__', '')
            parpos = cts.find('(')
            if parpos:
                obj_fullname = cts[:parpos]
                obj_name = obj_fullname.split('.')[-1]
                cts = cts.replace(obj_fullname, obj_name)
                signature = cts
                if ('()' in cts) or ('(...)' in cts):
                    # Either inspected object has no argument, or it's
                    # a builtin or an extension -- in this last case
                    # the following attempt may succeed:
                    signature = getsignaturefromtext(doc_text, obj_name)
        if not obj_fullname:
            obj_fullname = sourcecode.get_primary_at(source_code, offset)
        if obj_fullname and not obj_fullname.startswith('self.') and doc_text:
            # doc_text was generated by utils.dochelpers.getdoc
            if type(doc_text) is dict:
                obj_fullname = doc_text['name']
                argspec = doc_text['argspec']
                note = doc_text['note']
                doc_text = doc_text['docstring']
            elif signature:
                argspec_st = signature.find('(')
                argspec = signature[argspec_st:]
                module_end = obj_fullname.rfind('.')
                module = obj_fullname[:module_end]
                note = 'Present in %s module' % module
            else:
                argspec = ''
                note = ''
            
        elif obj_fullname:
            self.emit(SIGNAL(
                    "send_to_inspector(QString,QString,QString,QString,bool)"),
                    obj_fullname, '', '', '', not auto)
        if signature:
            self.editor.show_calltip('Arguments', signature, signature=True,
                                     at_position=position)



def split_words(string):
    """Split a string into unicode-aware words"""
    return re.findall(r"[\w.]+", string, re.UNICODE)
    

if __name__ == '__main__':
    p = IntrospectionPlugin()
    
    with open(__file__, 'rb') as fid:
        code = fid.read().decode('utf-8')
    code += '\nget_conf_path'
    path, line = p.get_definition_location_regex(code, len(code), __file__)
    assert path.endswith('baseconfig.py')
    
    comp = p.get_token_completion_list(code[:-2], len(code) - 2, None)
    assert comp == ['get_conf_path']
    
    code += '\np.get_token_completion_list'
    path, line = p.get_definition_location_regex(code, len(code), 'dummy.txt')
    assert path == 'dummy.txt'
    assert 'def get_token_completion_list(' in code.splitlines()[line - 1]
    
    code += '\np.python_like_mod_finder'
    path, line = p.get_definition_location_regex(code, len(code), 'dummy.txt')
    assert path == 'dummy.txt'
    assert 'def python_like_mod_finder' in code.splitlines()[line - 1]
    
    code += 'python_like_mod_finder'
    path, line = p.get_definition_location_regex(code, len(code), 'dummy.txt')
    assert line is None
    
    code = """
    class Test(object):
        def __init__(self):
            self.foo = bar
            
    t = Test()
    t.foo"""
    path, line = p.get_definition_location_regex(code, len(code), 'dummy.txt')
    assert line == 4

    ext = p.python_like_exts()
    assert '.py' in ext and '.pyx' in ext
    
    ext = p.all_editable_exts()
    assert '.cfg' in ext and '.iss' in ext
    
    path = p.get_parent_until(os.path.abspath(__file__))
    assert path == 'spyderlib.utils.introspection.base'
    
    line = 'from spyderlib.widgets.sourcecode.codeeditor import CodeEditor'
    path = p.python_like_mod_finder(line)
    assert path.endswith('codeeditor.py')
    path = p.python_like_mod_finder(line, stop_token='sourcecode')
    assert path.endswith('__init__.py') and 'sourcecode' in path
    
    path = p.get_parent_until(osp.expanduser(r'~/.spyder2/temp.py'))
    assert path == '.spyder2.temp'
    
    code = 'import re\n\nre'
    path, line = p.get_definition_location_regex(code, len(code), 'dummy.txt')
    assert path == 'dummy.txt' and line == 1
    
    code = 'self.proxy.widget; self.'
    comp = p.get_token_completion_list(code, len(code), None)
    assert comp == ['proxy']
    
    code = 'self.sigMessageReady.emit; self.'
    comp = p.get_token_completion_list(code, len(code), None)
    assert comp == ['sigMessageReady']
    
    code = encoding.to_unicode('álfa;á')
    comp = p.get_token_completion_list(code, len(code), None)
    assert comp == [encoding.to_unicode('álfa')]
    
