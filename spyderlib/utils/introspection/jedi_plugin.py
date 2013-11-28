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
from spyderlib.qt.QtGui import QApplication
from spyderlib import dependencies
from spyderlib.baseconfig import _, get_conf_path, DEBUG, debug_print
from spyderlib.utils import programs
from spyderlib.utils.debug import log_last_error, log_dt
from spyderlib.utils.sourcecode import split_source
from spyderlib.utils.introspection.base import (
    get_parent_until, python_like_exts, python_like_mod_finder,
    all_editable_exts, get_definition_from_file)
try:
    import jedi
except ImportError:
    jedi = None


JEDI_HELPER = None
NAME = 'jedi'
LOG_FILENAME = get_conf_path('introspection.log')
DEBUG_EDITOR = DEBUG >= 3
JEDI_REQVER = '>=0.7.0'
dependencies.add('jedi',
                 _("Editor's code completion, go-to-definition and help"),
                 required_version=JEDI_REQVER)
editor_widget = None

#-----------------------------------------------------------------------------
# Introspection API
#-----------------------------------------------------------------------------
def load_plugin():
    """Load the Jedi introspection plugin"""
    if programs.is_module_installed('jedi', JEDI_REQVER):
        global JEDI_HELPER
        JEDI_HELPER = JediHelper()
        return True
    else:
        return False


def get_completion_list(source_code, offset, filename):
    """Return a list of completion strings using Jedi"""
    return JEDI_HELPER.get_completion_list(source_code, offset, filename)


def get_calltip_and_docs(source_code, offset, filename):
    """Find the calltip and docs using Jedi"""
    return JEDI_HELPER.get_calltip_and_docs(source_code, offset, filename)


def get_definition_location(source_code, offset, filename):
    """Find a path and line number for a definition using Jedi"""
    return JEDI_HELPER.get_definition_location(source_code, offset, filename)


def set_pref(name, value):
    """Set a Jedi plugin preference to a value"""
    if name == 'extension_modules':
        mods = [mod for mod in value if not '.' in mod]
        JEDI_HELPER.extension_modules = mods
    
def validate():
    """Validate the Jedi plugin"""
    pass

#-----------------------------------------------------------------------------
# Implementation
#-----------------------------------------------------------------------------

if os.environ['QT_API'] == 'pyqt':
    AUTO_QT = 'PyQt4'
else:
    AUTO_QT = 'PySide'
    
    
class JediThread(QThread):
    """Thread to Handle Preloading Modules into Jedi"""
    sigMessageReady = Signal(object)
    
    def __init__(self, modules, lock):
        super(JediThread, self).__init__()
        if not isinstance(modules, list):
            modules = [modules]
        self.modules = modules
        self.lock = lock
        
    def run(self):
        """Preload modules into Jedi"""
        while editor_widget and editor_widget.window().is_starting_up:
            time.sleep(0.1)
        for module in self.modules:
            with self.lock:
                self.sigMessageReady.emit('Jedi loading %s...' % module)
                jedi.preload_module(module)
            time.sleep(0.01)

     
class JediHelper(object):
    """Helper object to interface with the Jedi Library"""
    jedi_lock = threading.Lock()

    def __init__(self):
        """Initialize the Jedi Helper object"""
        with self.jedi_lock:
            jedi.settings.case_insensitive_completion = False
        warmup_libs = ['numpy', 'matplotlib.pyplot']
        self.loading_message = 'Jedi Warming Up'
        self.jedi_thread = JediThread(warmup_libs, self.jedi_lock)
        self.jedi_thread.sigMessageReady.connect(self.set_message)
        self.jedi_thread.finished.connect(self.clear_message)
        self.jedi_thread.start()
        self.loaded_modules = warmup_libs
        self.extension_modules = []
        QTimer.singleShot(1500, self.refresh_libs)

    def refresh_libs(self):
        """ 
        Look for extension modules that are not in our loaded modules
        but are in the current document
        """
        QTimer.singleShot(1500, self.refresh_libs)
        if self.jedi_thread.isRunning():
            self.post_message(self.loading_message)
            return
        finfo = editor_widget.get_current_finfo()
        if not finfo:
            return
        missing_libs = set(self.extension_modules) - set(self.loaded_modules)
        code = finfo.get_source_code()
        pattern = '\W+QtCore\W+|\W+QtGui\W+'
        if not AUTO_QT in self.loaded_modules and re.search(pattern, code):
            self.get_libs([AUTO_QT, AUTO_QT + '.QtCore', AUTO_QT + '.QtGui'])
            return
        pattern = 'import {0}\W+|from {0}\W+'
        for lib in missing_libs:
            if re.search(pattern.format(lib), code):
                self.get_libs(lib)
                return
                
    def get_libs(self, libs):
        """Preload libraries into Jedi using a JediThread"""
        if not isinstance(libs, list):
            libs = [libs]
        self.loaded_modules.extend(libs)
        self.jedi_thread = JediThread(libs, self.jedi_lock)
        self.jedi_thread.sigMessageReady.connect(self.set_message)
        self.jedi_thread.finished.connect(self.clear_message)
        self.jedi_thread.start()
        
    def post_message(self, message, timeout=60000):
        """
        Post a message to the main window status bar with a timeout in ms
        """
        if editor_widget:
            editor_widget.window().statusBar().showMessage(message, timeout)
            QApplication.processEvents()
            
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

    def get_completion_list(self, source_code, offset, filename):
        """Get a list of word completions from Jedi"""
        line, col = self.get_line_col(source_code, offset)
        completions = self.get_jedi_object(source_code, line, col, filename,
                                           'completions')
        if completions:
            return [c.word for c in completions]
        else:
            return []

    def get_calltip_and_docs(self, source_code, offset, filename):
        """Get a formatted calltip and docstring from Jedi"""
        line, col = self.get_line_col(source_code, offset)
        call_def =  self.get_jedi_object(source_code, line, col, filename,
                                        'goto_definitions')
        if call_def:
            call_def = call_def[0]
            name = call_def.name
            if name is None:
                return
            mod_name = get_parent_until(call_def.module_path)
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
        else:
            return []
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
            return None, None
        return module_path, line_nr

    @staticmethod
    def find_in_builtin(info):
        """Find a definition in a builtin file"""
        module_path = info['module_path']
        line_nr = info['line_nr']
        ext = os.path.splitext(info['module_path'])[1]
        desc = info['description']
        name = info['name']
        if ext in python_like_exts() and (
                desc.startswith('import ') or desc.startswith('from ')):
            path = python_like_mod_finder(desc,
                                os.path.dirname(module_path), name)
            if path:
                info['module_path'] = module_path = path
                info['line_nr'] = line_nr = 1
        if ext in all_editable_exts():
            pattern = 'from.*\W{0}\W?.*c?import|import.*\W{0}'
            if not re.match(pattern.format(info['name']), desc):
                line_nr = get_definition_from_file(module_path, name, line_nr)
                if not line_nr:
                    module_path = None
        if not ext in all_editable_exts():
            line_nr = None
        return module_path, line_nr
    

if __name__ == '__main__':
    import pprint
    t0 = time.time()
    load_plugin()
    #source_code = "import numpy; numpy.ones"
    source_code = "import functools"
    pprint.pprint(get_calltip_and_docs(source_code, len(source_code),
                                       __file__))
    print 'completed in:', time.time() - t0
