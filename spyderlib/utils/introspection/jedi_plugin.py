# -*- coding: utf-8 -*-
#
# Copyright © 2013 The Spyder Development Team
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Jedi Introspection Plugin
"""
import re
import os
import time
import threading

from spyderlib.qt.QtCore import QThread, Signal, QTimer

from spyderlib import dependencies
from spyderlib.baseconfig import _, debug_print
from spyderlib.utils import programs
from spyderlib.utils.debug import log_last_error, log_dt
from spyderlib.utils.sourcecode import split_source
from spyderlib.utils.introspection.base import (
    DEBUG_EDITOR, LOG_FILENAME, IntrospectionPlugin, fallback)

try:
    import jedi
except ImportError:
    jedi = None

JEDI_REQVER = '>=0.7.0'
dependencies.add('jedi',
                 _("(Experimental) Editor's code completion,"
                   " go-to-definition and help"),
                 required_version=JEDI_REQVER)


class JediThread(QThread):
    """Thread to Handle Preloading Modules into Jedi"""
    sigMessageReady = Signal(object)

    def __init__(self, modules, parent):
        super(JediThread, self).__init__()
        if not isinstance(modules, list):
            modules = [modules]
        self.modules = modules
        self.parent = parent

    def run(self):
        """Preload modules into Jedi"""
        while not self.parent.is_editor_ready():
            time.sleep(0.1)
        for module in self.modules:
            with self.parent.jedi_lock:
                self.sigMessageReady.emit('Jedi loading %s...' % module)
                jedi.preload_module(module)
            time.sleep(0.01)


class JediPlugin(IntrospectionPlugin):
    """
    Jedi based introspection plugin for jedi
    
    Experimental Editor's code completion, go-to-definition and help
    """
    
    jedi_lock = threading.Lock()
    
    # ---- IntrospectionPlugin API --------------------------------------------
    name = 'jedi'

    def load_plugin(self):
        """Load the Jedi introspection plugin"""
        if not programs.is_module_installed('jedi', JEDI_REQVER):
            raise ImportError('Requires Jedi %s' % JEDI_REQVER)
        with self.jedi_lock:
            jedi.settings.case_insensitive_completion = False
        warmup_libs = ['numpy', 'matplotlib.pyplot']
        self.loading_message = 'Jedi Warming Up'
        self.jedi_thread = JediThread(warmup_libs, self)
        self.jedi_thread.sigMessageReady.connect(self.set_message)
        self.jedi_thread.finished.connect(self.clear_message)
        self.jedi_thread.start()
        self.loaded_modules = warmup_libs
        self.extension_modules = []
        QTimer.singleShot(1500, self.refresh_libs)

    @fallback
    def get_completion_list(self, source_code, offset, filename):
        """Return a list of completion strings"""
        
        line, col = self.get_line_col(source_code, offset)
        completions = self.get_jedi_object(source_code, line, col, filename,
                                           'completions')
        if completions:
            return [c.word for c in completions]
        else:
            raise ValueError

    @fallback
    def get_calltip_and_docs(self, source_code, offset, filename):
        """
        Find the calltip and docs

        Calltip is a string with the function or class and its arguments
            e.g. 'match(patern, string, flags=0)'
                 'ones(shape, dtype=None, order='C')'
        Docs is a a string or a dict with the following keys:
           e.g. 'Try to apply the pattern at the start of the string...'
           or {'note': 'Function of numpy.core.numeric...',
               'argspec': "(shape, dtype=None, order='C')'
               'docstring': 'Return an array of given...'
               'name': 'ones'}
        """
        line, col = self.get_line_col(source_code, offset)
        call_def = self.get_jedi_object(source_code, line, col, filename,
                                        'goto_definitions')
        if call_def:
            return self.parse_call_def(call_def)
        else:
            raise ValueError

    @fallback
    def get_definition_location(self, source_code, offset, filename):
        """
        Find a definition location using Jedi

        Follows gotos until a definition is found, or it reaches a builtin
        module.  Falls back on token lookup if it is in an enaml file or does
        not find a match
        """
        line, col = self.get_line_col(source_code, offset)
        info, module_path, line_nr = None, None, None
        gotos = self.get_jedi_object(source_code, line, col, filename,
                                     'goto_assignments')
        if gotos:
            info = self.get_definition_info(gotos[0])
        if info and info['goto_next']:
            defns = self.get_jedi_object(source_code, line, col, filename,
                                         'goto_definitions')
            if defns:
                new_info = self.get_definition_info(defns[0])
            if not new_info['in_builtin']:
                info = new_info
        # handle builtins -> try and find the module
        if info and info['in_builtin']:
            module_path, line_nr = self.find_in_builtin(info)
        elif info:
            module_path = info['module_path']
            line_nr = info['line_nr']
        if module_path == filename and line_nr == line:
            raise ValueError
        return module_path, line_nr

    def set_pref(self, name, value):
        """Set a plugin preference to a value"""
        if name == 'extension_modules':
            mods = [mod for mod in value if not '.' in mod]
            self.extension_modules = mods

    # ---- Private API -------------------------------------------------------

    def refresh_libs(self):
        """
        Look for extension modules that are not in our loaded modules
        but are in the current document
        """
        QTimer.singleShot(1500, self.refresh_libs)
        if self.jedi_thread.isRunning():
            self.post_message(self.loading_message)
            return
        source = self.get_current_source()
        if not source:
            return
        missing_libs = set(self.extension_modules) - set(self.loaded_modules)
        pattern = '\W+QtCore\W+|\W+QtGui\W+'
        default_qt = self.default_qt()
        if not default_qt in self.loaded_modules and re.search(pattern,
                                                               source):
            self.get_libs([default_qt, default_qt + '.QtCore',
                           default_qt + '.QtGui'])
            return
        pattern = 'import {0}\W+|from {0}\W+'
        for lib in missing_libs:
            if re.search(pattern.format(lib), source):
                self.get_libs(lib)
                return

    def default_qt(self):
        """
        Look for a the default QT API to preload for an ambiguous Qt import

        Such as `from spyderlib.qt import QtCore`
        """
        if os.environ['QT_API'] == 'pyqt':
            return 'PyQt4'
        else:
            return 'PySide'

    def get_libs(self, libs):
        """Preload libraries into Jedi using a JediThread"""
        if not isinstance(libs, list):
            libs = [libs]
        self.loaded_modules.extend(libs)
        self.jedi_thread = JediThread(libs, self)
        self.jedi_thread.sigMessageReady.connect(self.set_message)
        self.jedi_thread.finished.connect(self.clear_message)
        self.jedi_thread.start()

    def set_message(self, message):
        """Set our current loading message"""
        self.loading_message = message

    def clear_message(self):
        """Clear our current loading message and the main window statusbar"""
        self.loading_message = ''
        self.post_message('', 0)

    def get_line_col(self, source_code, offset):
        """Get a line and column given source code and an offset"""
        if not source_code:
            return 1, 1
        source_code = source_code[:offset]
        lines = split_source(source_code)
        return len(lines), len(lines[-1])

    def get_jedi_object(self, source_code, line, col, filename, func_name):
        """Call a desired function on a Jedi Script and return the result"""
        if not jedi:
            return
        if DEBUG_EDITOR:
            t0 = time.time()
        with self.jedi_lock:
            try:
                script = jedi.Script(source_code, line, col, filename)
                func = getattr(script, func_name)
                val = func()
            except Exception as e:
                val = None
                debug_print('Jedi error (%s)' % func_name)
                if DEBUG_EDITOR:
                    log_last_error(LOG_FILENAME, str(e))
        if DEBUG_EDITOR:
            log_dt(LOG_FILENAME, func_name, t0)
        if not val and filename:
            return self.get_jedi_object(source_code, line, col, None,
                                        func_name)
        else:
            return val

    def parse_call_def(self, call_def):
        """Get a formatted calltip and docstring from Jedi"""
        call_def = call_def[0]
        name = call_def.name
        if name is None:
            return
        mod_name = self.get_parent_until(call_def.module_path)
        if not mod_name:
            mod_name = call_def.module_name
        if call_def.doc.startswith(name + '('):
            calltip = call_def.doc[:call_def.doc.find(')') + 1]
            calltip = calltip.replace('\n', '')
            calltip = calltip.replace(' ', '')
            calltip = calltip.replace(',', ', ')
            argspec = calltip[calltip.find('('):]
            docstring = call_def.doc[call_def.doc.find(')') + 3:]
        else:
            calltip = name + '()'
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
        doc_text = dict(name=call_def.name, argspec=argspec,
                        note=note, docstring=docstring)
        return calltip, doc_text

    @staticmethod
    def get_definition_info(defn):
        """Extract definition information from the Jedi definition object"""
        try:
            module_path = defn.module_path
            name = defn.name
            line_nr = defn.line_nr
            description = defn.description
            in_builtin = defn.in_builtin_module()
        except Exception as e:
            if DEBUG_EDITOR:
                log_last_error(LOG_FILENAME, 'Get Defintion: %s' % e)
            return None
        pattern = 'class\s+{0}|def\s+{0}|self.{0}\s*=|{0}\s*='.format(name)
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
        ext = os.path.splitext(info['module_path'])[1]
        desc = info['description']
        name = info['name']
        if ext in self.python_like_exts() and (
                desc.startswith('import ') or desc.startswith('from ')):
            path = self.python_like_mod_finder(desc,
                                          os.path.dirname(module_path), name)
            if path:
                info['module_path'] = module_path = path
                info['line_nr'] = line_nr = 1
        if ext in self.all_editable_exts():
            pattern = 'from.*\W{0}\W?.*c?import|import.*\W{0}'
            if not re.match(pattern.format(info['name']), desc):
                line_nr = self.get_definition_from_file(module_path, name, 
                                                        line_nr)
                if not line_nr:
                    module_path = None
        if not ext in self.all_editable_exts():
            line_nr = None
        return module_path, line_nr


if __name__ == '__main__':
    
    p = JediPlugin()
    p.load_plugin()

    source_code = "import numpy; numpy.ones("
    calltip, docs = p.get_calltip_and_docs(source_code, len(source_code),
                                           __file__)
    assert calltip.startswith('ones(') and docs['name'] == 'ones'
    
    source_code = "import n"
    completions = p.get_completion_list(source_code, len(source_code),
                                        __file__)
    assert 'numpy' in completions 
    
    source_code = "import matplotlib.pyplot as plt; plt.imsave"
    path, line_nr = p.get_definition_location(source_code, len(source_code),
                                            __file__)
    assert 'pyplot.py' in path 
    
    source_code = 'from .base import memoize'
    path, line_nr = p.get_definition_location(source_code, len(source_code),
                                            __file__)
    assert 'base.py' in path and 'introspection' in path
