# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Jedi Introspection Plugin
"""
import re
import os.path as osp
import sys
import time

from spyder_kernels.utils.dochelpers import getsignaturefromtext

from spyder.config.base import debug_print
from spyder.utils import programs
from spyder.utils.debug import log_last_error, log_dt
from spyder.utils.introspection.manager import (
    DEBUG_EDITOR, LOG_FILENAME, IntrospectionPlugin)
from spyder.utils.introspection.utils import (default_info_response,
                                              get_parent_until)
from spyder.utils.introspection.manager import JEDI_REQVER

try:
    try:
        from spyder.utils.introspection import jedi_patch
        jedi = jedi_patch.apply()
    except ImportError:
        import jedi
except ImportError:
    jedi = None

JEDI_010 = programs.is_module_installed('jedi', '>=0.10.0')


class JediPlugin(IntrospectionPlugin):
    """
    Jedi based introspection plugin for jedi

    Experimental Editor's code completion, go-to-definition and help
    """

    # ---- IntrospectionPlugin API --------------------------------------------
    name = 'jedi'

    def load_plugin(self):
        """Load the Jedi introspection plugin"""
        if not programs.is_module_installed('jedi', JEDI_REQVER):
            raise ImportError('Requires Jedi %s' % JEDI_REQVER)
        jedi.settings.case_insensitive_completion = False
        for lib in ['numpy', 'matplotlib']:
            jedi.preload_module(lib)

    def get_completions(self, info):
        """Return a list of (completion, type) tuples"""
        completions = self.get_jedi_object('completions', info)
        if DEBUG_EDITOR:
            log_last_error(LOG_FILENAME, str("comp: " + str(completions)[:100]))
        if completions is not None:
            completions = [(c.name, c.type) for c in completions]
        else:
            completions = []
        debug_print(str(completions)[:100])
        return completions

    def get_info(self, info):
        """
        Find the calltip and docs

        Returns a dict like the following:
           {'note': 'Function of numpy.core.numeric...',
            'argspec': "(shape, dtype=None, order='C')'
            'docstring': 'Return an array of given...'
            'name': 'ones',
            'calltip': 'ones(shape, dtype=None, order='C')'}
        """
        call_def = self.get_jedi_object('goto_definitions', info)

        for cd in call_def:
            # For compatibility with Jedi 0.11
            try:
                cd.doc = cd.docstring()
            except AttributeError:
                pass

            if cd.doc and not cd.doc.rstrip().endswith(')'):
                call_def = cd
                break
        else:
            try:
                call_def = call_def[0]
            except IndexError:
                return default_info_response()

        name = call_def.name
        if name is None:
            return default_info_response()

        if call_def.module_path:
            mod_name = get_parent_until(call_def.module_path)
        else:
            mod_name = None

        if not mod_name:
            mod_name = call_def.module_name

        if call_def.doc.startswith(name + '('):
            calltip = getsignaturefromtext(call_def.doc, name)
            argspec = calltip[calltip.find('('):]
            docstring = call_def.doc[call_def.doc.find(')') + 3:]
        elif call_def.doc and '(' in call_def.doc.splitlines()[0]:
            calltip = call_def.doc.splitlines()[0]
            name = call_def.doc.split('(')[0]
            docstring = call_def.doc[call_def.doc.find(')') + 3:]
            argspec = calltip[calltip.find('('):]
        else:
            calltip = name + '(...)'
            argspec = '()'
            docstring = call_def.doc

        if call_def.type == 'module':
            note = 'Module %s' % mod_name
            argspec = ''
            calltip = name
        elif call_def.type == 'class':
            note = 'Class in %s module' % mod_name
        elif call_def.doc.startswith('%s(self' % name):
            class_name = call_def.full_name.split('.')[-2]
            note = 'Method of %s class in %s module' % (
                class_name.capitalize(), mod_name)
        else:
            note = '%s in %s module' % (call_def.type.capitalize(),
                                        mod_name)

        argspec = argspec.replace(' = ', '=')
        calltip = calltip.replace(' = ', '=')
        debug_print(call_def.name)

        doc_info = dict(name=name, argspec=argspec,
                        note=note, docstring=docstring, calltip=calltip)
        return doc_info

    def get_definition(self, info):
        """
        Find a definition location using Jedi

        Follows gotos until a definition is found, or it reaches a builtin
        module.  Falls back on token lookup if it is in an enaml file or does
        not find a match
        """
        line, filename = info['line_num'], info['filename']
        def_info, module_path, line_nr = None, None, None
        gotos = self.get_jedi_object('goto_assignments', info)

        if gotos:
            def_info = self.get_definition_info(gotos[0])
        if def_info and def_info['goto_next']:
            defns = self.get_jedi_object('goto_definitions', info)
            new_info = None
            if defns:
                new_info = self.get_definition_info(defns[0])
            if new_info and not new_info['in_builtin']:
                def_info = new_info
        elif not def_info:
            return

        # handle builtins -> try and find the module
        if def_info and def_info['in_builtin']:
            module_path, line_nr = self.find_in_builtin(def_info)
        elif def_info:
            module_path = def_info['module_path']
            line_nr = def_info['line_nr']

        # Handle failures to find module_path and line_nr
        if module_path == filename and line_nr == line:
            return
        elif module_path is None:
            return

        return module_path, line_nr

    # ---- Private API -------------------------------------------------------

    def get_jedi_object(self, func_name, info, use_filename=True):
        """Call a desired function on a Jedi Script and return the result"""
        if not jedi:
            return
        if DEBUG_EDITOR:
            t0 = time.time()
        # override IPython qt_loaders ImportDenier behavior
        metas = sys.meta_path
        for meta in metas:
            if (meta.__class__.__name__ == 'ImportDenier'
                    and hasattr(meta, 'forbid')):
                sys.meta_path.remove(meta)

        if use_filename:
            filename = info['filename']
        else:
            filename = None

        try:
            if JEDI_010:
                script = jedi.api.Script(info['source_code'], info['line_num'],
                                         info['column'], filename,
                                         sys_path=info['sys_path'])
            else:
                script = jedi.api.Script(info['source_code'], info['line_num'],
                                         info['column'], filename)
            func = getattr(script, func_name)
            val = func()
        except Exception as e:
            val = None
            debug_print('Jedi error (%s)' % func_name)
            debug_print(str(e))
            if DEBUG_EDITOR:
                log_last_error(LOG_FILENAME, str(e))
        if DEBUG_EDITOR:
            log_dt(LOG_FILENAME, func_name, t0)
        if not val and filename:
            return self.get_jedi_object(func_name, info, False)
        else:
            return val

    @staticmethod
    def get_definition_info(defn):
        """Extract definition information from the Jedi definition object"""
        try:
            module_path = defn.module_path
            name = defn.name
            if hasattr(defn, 'line_nr'):
                line_nr = defn.line_nr
            else:
                line_nr = defn.line
            description = defn.description
            in_builtin = defn.in_builtin_module()
        except Exception as e:
            if DEBUG_EDITOR:
                log_last_error(LOG_FILENAME, 'Get Defintion: %s' % e)
            return None
        pattern = r'class\s+{0}|def\s+{0}|self.{0}\s*=|{0}\s*='.format(name)
        if not re.match(pattern, description):
            goto_next = True
        else:
            goto_next = False
        return dict(module_path=module_path, line_nr=line_nr,
                    description=description, name=name, in_builtin=in_builtin,
                    goto_next=goto_next)

    def find_in_builtin(self, info):
        """Find a definition in a builtin file"""
        module_path = info['module_path']
        line_nr = info['line_nr']

        if module_path is None:
            return None, None

        ext = osp.splitext(info['module_path'])[1]
        desc = info['description']
        name = info['name']
        if ext in self.python_like_exts() and (
                desc.startswith('import ') or desc.startswith('from ')):
            path = self.python_like_mod_finder(desc,
                                          osp.dirname(module_path), name)
            if path:
                info['module_path'] = module_path = path
                info['line_nr'] = line_nr = 1

        if ext in self.all_editable_exts():
            pattern = r'from.*\W{0}\W?.*c?import|import.*\W{0}'
            if not re.match(pattern.format(info['name']), desc):
                line_nr = self.get_definition_from_file(module_path, name,
                                                        line_nr)
                if not line_nr:
                    module_path = None

        if not ext in self.all_editable_exts():
            line_nr = None

        return module_path, line_nr
