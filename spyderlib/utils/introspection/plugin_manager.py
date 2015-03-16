# -*- coding: utf-8 -*-
#
# Copyright © 2015 The Spyder development team
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

from __future__ import print_function

import re
from collections import OrderedDict
import functools
import os.path as osp
import os
import imp
import time

from spyderlib.baseconfig import DEBUG, get_conf_path, debug_print
from spyderlib.utils.introspection.module_completion import (
    get_preferred_submodules)
from spyderlib.utils import sourcecode
from spyderlib.utils.debug import log_last_error

from spyderlib.qt.QtGui import QApplication
from spyderlib.qt.QtCore import Signal, QThread, QObject, QTimer


PLUGINS = ['rope', 'jedi', 'fallback']

LOG_FILENAME = get_conf_path('introspection.log')
DEBUG_EDITOR = DEBUG >= 3
LEAD_TIME_SEC = 0.25


class RequestHandler(QObject):

    """Handle introspection request.
    """

    introspection_complete = Signal()

    def __init__(self, code_info, plugins):
        super(RequestHandler, self).__init__()
        self.info = code_info
        self.timer = QTimer()
        self.timer.singleShot(LEAD_TIME_SEC * 1000, self._handle_timeout)
        self.waiting = True
        self.pending = {}
        self.result = None
        self.plugins = plugins
        self._start_time = time.time()
        self._threads = {}
        for plugin in plugins:
            self._make_async_call(plugin, code_info)

    def _handle_timeout(self):
        debug_print('got timeout')
        if self.pending:
            for plugin in self.plugins:
                if plugin.name in self.pending:
                    self._finalize(plugin.name, self.pending[plugin.name])
                    return
        self.waiting = False

    def _handle_incoming(self, name):
        # coerce to a str in case it is a QString
        name = str(name)
        self._threads[name].wait()
        if self.result:
            return
        result = self._threads[name].result
        if name == self.plugins[0].name or not self.waiting:
            self._finalize(name, result)
        else:
            self.pending[name] = result

    def _make_async_call(self, plugin, info):
        """Trigger an introspection job in a thread"""
        self._threads[str(plugin.name)] = thread = IntrospectionThread(plugin, info)
        thread.request_handled.connect(self._handle_incoming)
        thread.start()

    def _finalize(self, name, result):
        self.result = result
        self.waiting = False
        self.pending = None
        delta = time.time() - self._start_time
        debug_print('%s request from %s complete: "%s" in %.1f sec'
            % (self.info.name, name, str(result)[:100], delta))
        self.introspection_complete.emit()


class GetSubmodulesThread(QThread):

    """
    A thread to generate a list of submodules to be passed to
    introspection plugins
    """

    def __init__(self):
        super(GetSubmodulesThread, self).__init__()
        self.submods = []

    def run(self):
        self.submods = get_preferred_submodules()


class IntrospectionThread(QThread):

    """
    A thread to perform an introspection task
    """

    request_handled = Signal(str)

    def __init__(self, plugin, info):
        super(IntrospectionThread, self).__init__()
        self.plugin = plugin
        self.info = info
        self.result = None

    def run(self):
        func = getattr(self.plugin, 'get_%s' % self.info.name)
        self.plugin.busy = True
        try:
            self.result = func(self.info)
        except Exception as e:
            debug_print(e)
        self.plugin.busy = False
        self.request_handled.emit(self.plugin.name)


class CodeInfo(object):

    id_regex = re.compile(r'[^\d\W][\w\.]*', re.UNICODE)
    func_call_regex = re.compile(r'([^\d\W][\w\.]*)\([^\)\()]*\Z',
                                 re.UNICODE)

    def __init__(self, name, source_code, position, filename=None,
            is_python_like=True, **kwargs):
        self.__dict__.update(kwargs)
        self.name = name
        self.filename = filename
        self.source_code = source_code
        self.position = position
        self.is_python_like = is_python_like

        if position == 0:
            self.lines = []
            self.line_num = 0
            self.obj = None
            self.full_obj = None
        else:
            self._get_info()

    def _get_info(self):
        self.lines = self.source_code[:self.position].splitlines()
        self.line_num = len(self.lines)

        self.line = self.lines[-1]
        self.column = len(self.lines[-1])

        tokens = re.findall(self.id_regex, self.line)
        if tokens and self.line.endswith(tokens[-1]):
            self.obj = tokens[-1]
        else:
            self.obj = None

        self.full_obj = self.obj

        if self.obj:
            full_line = self.source_code.splitlines()[self.line_num - 1]
            rest = full_line[self.column:]
            match = re.match(self.id_regex, rest)
            if match:
                self.full_obj = self.obj + match.group()

        if (self.name in ['info', 'definition'] and (not self.obj)
                and self.is_python_like):
            func_call = re.findall(self.func_call_regex, self.line)
            if func_call:
                self.obj = func_call[-1]
                self.column = self.line.index(self.obj) + len(self.obj)
                self.position = self.position - len(self.line) + self.column

    def split_words(self, position=None):
        """
        Split our source code into valid identifiers.

        P"""
        if position is None:
            position = self.offset
        text = self.source_code[:position]
        return re.findall(self.id_regex, text)

    def __eq__(self, other):
        try:
            return self.__dict__ == other.__dict__
        except Exception:
            return False


class PluginManager(QObject):

    send_to_inspector = Signal(str, str, str, str, bool)
    edit_goto = Signal(str, int, str)

    def __init__(self, editor_widget):
        super(PluginManager, self).__init__()
        self.editor_widget = editor_widget
        self.pending = None
        self.busy = False
        self.load_plugins()
        self._submods_thread = GetSubmodulesThread()
        self._submods_thread.finished.connect(self._update_extension_modules)
        self._submods_thread.start()

    def load_plugins(self):
        """Get and load a plugin, checking in order of PLUGINS"""
        plugins = OrderedDict()
        for plugin_name in PLUGINS:
            mod_name = plugin_name + '_plugin'
            try:
                mod = __import__('spyderlib.utils.introspection.' + mod_name,
                                 fromlist=[mod_name])
                cls = getattr(mod, '%sPlugin' % plugin_name.capitalize())
                plugin = cls()
                plugin.load_plugin()
            except Exception as e:
                debug_print(e)
                if DEBUG_EDITOR:
                    log_last_error(LOG_FILENAME)
            else:
                plugins[plugin_name] = plugin
                debug_print('Instropection Plugin Loaded: %s' % plugin.name)
        self.plugins = plugins
        debug_print('Plugins loaded: %s' % self.plugins.keys())
        return plugins

    def _get_code_info(self, name, position=None, **kwargs):

        editor = self.editor_widget.get_current_editor()
        finfo = self.editor_widget.get_current_finfo()

        if position is None:
            position = editor.get_position('cursor')

        kwargs['editor'] = editor
        kwargs['finfo'] = finfo
        kwargs['editor_widget'] = self.editor_widget

        return CodeInfo(name, finfo.get_source_code(), position,
            finfo.filename, editor.is_python_like, **kwargs)

    def get_completions(self, automatic):
        """Get code completion"""
        info = self._get_code_info('completions', automatic=automatic)

        if 'jedi' in self.plugins and not self.plugins['jedi'].busy:
            self._handle_request(info)

        elif info.line.lstrip().startswith(('import ', 'from ')):
            self._handle_request(info, 'fallback')

        else:
            self._handle_request(info)

    def go_to_definition(self, position):
        """Go to definition"""
        info = self._get_code_info('definition', position)

        self._handle_request(info)

    def show_object_info(self, position, auto=True):
        """Show signature calltip and/or docstring in the Object Inspector"""
        # auto is True means that this method was called automatically,
        # i.e. the user has just entered an opening parenthesis -- in that
        # case, we don't want to force the object inspector to be visible,
        # to avoid polluting the window layout
        info = self._get_code_info('info', position, auto=auto)
        self._handle_request(info)

    def validate(self):
        """Validate the plugins"""
        if not self.busy:
            for plugin in self.plugins.values():
                plugin.validate()

    def is_editor_ready(self):
        """Check if the main app is starting up"""
        if self.editor_widget:
            window = self.editor_widget.window()
            if hasattr(window, 'is_starting_up') and not window.is_starting_up:
                return True

    def _handle_request(self, info, desired=None):
        """Handle an incoming request from the user."""
        debug_print('%s request:' % info.name)

        editor = info.editor
        if ((not editor.is_python_like())
                or sourcecode.is_keyword(info.obj)
                or editor.in_comment_or_string()):
            desired = 'fallback'

        self.pending = (info, desired)
        if not self.busy:
            self._handle_pending()

    def _handle_pending(self):
        """Handle any pending requests, sending them to the correct plugin."""
        if not self.pending:
            self._post_message('')
            return
        info, desired = self.pending
        if desired and self.plugins[desired].busy:
            return
        self.busy = True

        if desired:
            plugins = [self.plugins[desired]]
        elif info.name == 'definition' and not info.editor.is_python():
            plugins = [p for p in self.plugins.values() if not p.busy]
        else:
            # use all but the fallback
            plugins = [p for p in list(self.plugins.values())[:-1] if not p.busy]

        self.request = RequestHandler(info, plugins)
        self.request.introspection_complete.connect(
            self._introspection_complete)
        self.pending = None

    def _introspection_complete(self):
        """
        Handle an introspection response from the thread.

        Route the response to the correct handler, and then handle
        any pending requests.
        """
        self.busy = False
        result = self.request.result
        info = self.request.info
        current = self._get_code_info('current')

        if result and current.filename == info.filename:
            func = getattr(self, '_handle_%s_response' % info.name)
            try:
                func(result, current, info)
            except Exception as e:
                debug_print(e)
        elif current.filename == info.filename and info.name == 'definition':
            result = self.plugins['fallback'].get_definition(info)

        if info == self.pending:
            self.pending = None

        self._handle_pending()

    def _handle_completions_response(self, comp_list, info, prev_info):
        """
        Handle a `completions` response.

        Only handle the response if we are on the same line of text and
        on the same `obj` as the original request.
        """
        if info.line_num != prev_info.line_num:
            return
        completion_text = info.obj
        prev_text = prev_info.obj

        if prev_info.obj is None:
            completion_text = ''
            prev_text = ''

        if not completion_text.startswith(prev_text):
            return

        if info.full_obj and len(info.full_obj) > len(info.obj):
            new_list = [c for c in comp_list if c.startswith(info.full_obj)]
            if new_list:
                pos = info.editor.get_position('cursor')
                new_pos = pos + len(info.full_obj) - len(info.obj)
                info.editor.set_cursor_position(new_pos)
                completion_text = info.full_obj
                comp_list = new_list

        if '.' in completion_text:
            completion_text = completion_text.split('.')[-1]

        comp_list = [c.split('.')[-1]  for c in comp_list]
        comp_list = [c for c in comp_list if c.startswith(completion_text)]

        info.editor.show_completion_list(comp_list, completion_text,
                                         prev_info.automatic)

    def _handle_info_response(self, resp, info, prev_info):
        """
        Handle an `info` response, triggering a calltip and/or docstring.

        Only handle the response if we are on the same line of text as
        when the request was initiated.
        """
        if info.line_num != prev_info.line_num:
            return

        if resp['calltip']:
            info.editor.show_calltip('Arguments', resp['calltip'],
                                     signature=True,
                                     at_position=prev_info.position)

        if resp['name']:
            self.send_to_inspector.emit(
                resp['name'], resp['argspec'],
                resp['note'], resp['docstring'],
                not prev_info.auto)

    def _handle_definition_response(self, resp, info, prev_info):
        """Handle a `definition` response"""
        fname, lineno = resp
        self.edit_goto.emit(fname, lineno, "")

    def _update_extension_modules(self):
        """Set the extension_modules after submods thread finishes"""
        for plugin in self.plugins.values():
            plugin.set_pref('extension_modules',
                            self._submods_thread.submods)

    def _post_message(self, message, timeout=60000):
        """
        Post a message to the main window status bar with a timeout in ms
        """
        if self.editor_widget:
            statusbar = self.editor_widget.window().statusBar()
            statusbar.showMessage(message, timeout)
            QApplication.processEvents()


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


class IntrospectionPlugin(object):

    busy = False

    def load_plugin(self):
        """Initialize the plugin"""
        pass

    def get_completions(self, info):
        """Get a list of completions"""
        pass

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
        pass

    def get_definition(self, info):
        """Get a (filename, line_num) location for a definition"""
        pass

    def set_pref(self, name, value):
        """Set a plugin preference to a value"""
        pass

    def validate(self):
        """Validate the plugin"""
        pass

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


if __name__ == '__main__':
    code = 'import numpy'
    test = CodeInfo('test', code, len(code) - 2)
    assert test.obj == 'num'
    assert test.full_obj == 'numpy'
    test2 = CodeInfo('test', code, len(code) - 2)
    assert test == test2
