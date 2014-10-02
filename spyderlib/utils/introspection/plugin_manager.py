from __future__ import print_function
import re
from collections import OrderedDict
import functools
import os.path as osp
import os
import imp

from spyderlib.baseconfig import DEBUG, get_conf_path, debug_print
from spyderlib.utils.introspection.module_completion import (
    get_preferred_submodules)
from spyderlib.utils import sourcecode
from spyderlib.utils.debug import log_last_error

from spyderlib.qt.QtGui import QApplication
from spyderlib.qt.QtCore import SIGNAL, QThread, QObject


PLUGINS = ['jedi', 'rope', 'fallback']

LOG_FILENAME = get_conf_path('introspection.log')
DEBUG_EDITOR = DEBUG >= 3


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
        self.emit(SIGNAL('submods_ready()'))


class IntrospectionThread(QThread):

    """
    A thread to perform an introspection task
    """

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
        self.emit(SIGNAL('introspection_complete()'))


class CodeInfo(object):

    id_regex = re.compile(r'[^\d\W][\w\.]*', re.UNICODE)
    func_call_regex = re.compile(r'([^\d\W][\w\.]*)\([^\)\()]*\Z',
                                 re.UNICODE)

    def __init__(self, name, source_code, position, filename=None,
            is_python_like=True):
        self.name = name
        self.filename = filename
        self.source_code = source_code
        self.position = position
        self.is_python_like = is_python_like

        self.lines = source_code[:position].splitlines()
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
            full_line = source_code.splitlines()[self.line_num - 1]
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
                self.position = position - len(self.line) + self.column

    def split_words(self, position=None):
        """
        Split our source code into valid identifiers.

        P"""
        if position is None:
            position = self.offset
        text = self.source_code[:position]
        return re.findall(self.id_regex, text)


class Info(CodeInfo):

    """Store the information about an introspection request.
    """
    def __init__(self, name, editor_widget, position=None):

        self.editor = editor_widget.get_current_editor()
        self.finfo = editor_widget.get_current_finfo()
        self.name = name
        self.source_code = self.finfo.get_source_code()
        self.filename = self.finfo.filename

        if position is None:
            position = self.editor.get_position('cursor')
        self.position = position
        super(Info, self).__init__(name, self.source_code, position,
            self.filename, self.editor.is_python_like())


class PluginManager(QObject):

    def __init__(self, editor_widget):
        super(PluginManager, self).__init__()
        self.editor_widget = editor_widget
        self.pending = None
        self.busy = False
        self.load_plugins()
        self._submods_thread = GetSubmodulesThread()
        self.connect(self._submods_thread, SIGNAL('submods_ready()'),
                     self._update_extension_modules)
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

    def get_completions(self, automatic):
        """Get code completion"""
        info = Info('completions', self.editor_widget)
        info.automatic = automatic

        if 'jedi' in self.plugins and not self.plugins['jedi'].busy:
            self._handle_request(info, 'jedi')

        elif info.line.startswith(('import ', 'from ')):
            self._handle_request(info, 'fallback')

        else:
            self._handle_request(info)

    def go_to_definition(self, position):
        """Go to definition"""
        info = Info('definition', self.editor_widget, position)
        self._handle_request(info)

    def show_object_info(self, position, auto=True):
        """Show signature calltip and/or docstring in the Object Inspector"""
        # auto is True means that this method was called automatically,
        # i.e. the user has just entered an opening parenthesis -- in that
        # case, we don't want to force the object inspector to be visible,
        # to avoid polluting the window layout
        info = Info('info', self.editor_widget, position)
        info.auto = auto
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
        if desired is None or self.plugins[desired].busy:
            for plugin in self.plugins.values():
                if not plugin.busy:
                    self._make_async_call(plugin, info)
                    return
        else:
            self._make_async_call(self.plugins[desired], info)

    def _make_async_call(self, plugin, info):
        """Trigger an introspection job in a thread"""
        self.busy = True
        self.pending = None
        debug_print('%s async call' % info.name)
        self._thread = IntrospectionThread(plugin, info)
        self._post_message('Getting %s from %s plugin'
                           % (info.name, plugin.name))
        self.connect(self._thread, SIGNAL('introspection_complete()'),
                     self._introspection_complete)
        self._thread.start()

    def _introspection_complete(self):
        """
        Handle an introspection response from the thread.

        Route the response to the correct handler, and then handle
        any pending requests.
        """
        self.busy = False
        result = self._thread.result
        info = self._thread.info
        current = Info('current', self.editor_widget)

        debug_print('%s request from %s complete: %s'
            % (info.name, self._thread.plugin.name, result))

        if not result and self.pending:
            pass
        elif not result:
            index = list(self.plugins.values()).index(self._thread.plugin)
            for plugin in list(self.plugins.values())[index + 1:]:
                if not plugin.busy:
                    self._make_async_call(plugin, info)
                    return
        elif current.filename == info.filename:
            func = getattr(self, '_handle_%s_response' % info.name)
            try:
                func(result, current, info)
            except Exception as e:
                debug_print(e)
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
            if not resp['docstring']:
                resp['docstring'] = resp['calltip']

        if resp['name']:
            self.emit(SIGNAL(
                "send_to_inspector(QString,QString,QString,QString,bool)"),
                resp['name'], resp['argspec'],
                resp['note'], resp['docstring'],
                not prev_info.auto)

    def _handle_definition_response(self, resp, info, prev_info):
        """Handle a `definition` response"""
        fname, lineno = resp
        self.emit(SIGNAL("edit_goto(QString,int,QString)"),
                  fname, lineno, "")

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
