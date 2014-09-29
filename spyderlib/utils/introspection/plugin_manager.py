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
        super(GetSubmodulesThread, self).__init__()
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

        if (self.name in ['info', 'definition'] and (not self.obj)
                and self.is_python_like):
            func_call = re.findall(self.func_call_regex, self.line)
            if func_call:
                self.obj = func_call[-1]
                self.column = self.line.index(self.obj) + len(self.obj)
                self.position = position - len(self.line) + self.column

    def split_words(self, position=None):
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
                plugin.load_plugin(self)
            except Exception:
                if DEBUG_EDITOR:
                    log_last_error(LOG_FILENAME)
            else:
                plugins[plugin_name] = plugin
                debug_print('Instropection Plugin Loaded: %s' % plugin.name)
        self.plugins = plugins
        return plugins

    def get_completions(self, automatic):
        """Get code completion"""
        info = Info('completions', self.editor_widget)
        info.automatic = automatic

        if 'jedi' in self.plugins and not self.plugins['jedi'].busy:
            self._handle_request(info, 'jedi')

        elif info['line'].startswith(('import ', 'from ')):
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
        editor = info.editor
        if ((not editor.is_python_like())
                or sourcecode.is_keyword(info.object)
                or editor.in_comment_or_string()):
            desired = 'fallback'

        self.pending = (info, desired)
        if not self.busy:
            self._handle_pending()

    def _handle_pending(self):
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
        self.busy = True
        self._thread = IntrospectionThread(plugin, info)
        self._post_message('Getting %s from %s plugin'
                           % info.name, plugin.name)
        self.connect(self._thread, SIGNAL('introspection_complete()'),
                     self._introspection_complete)
        self._thread.start()

    def _introspection_complete(self):
        self.busy = False
        result = self._thread.result
        info = self._thread.info
        current = Info('current', self.editor_widget)

        if not result and self.pending:
            pass
        elif not result:
            index = list(self.plugins.values()).index[self._thread.plugin]
            for plugin in list(self.plugins.values())[index:]:
                if not plugin.busy:
                    self._make_async_call(plugin, info)
                    return
        elif current.filename == info.filename:
            func = getattr(self, '_handle_%s_response' % result.name)
            try:
                func(result, current, info)
            except Exception as e:
                debug_print(e)
        self._handle_pending()

    def _handle_completion_response(self, comp_list, info, prev_info):
        # make sure we are on the same line with the same base obj
        if info.line_num != prev_info.line_num:
            return
        completion_text = info.obj
        if not completion_text.startswith(prev_info.obj):
            return

        comp_list = [c for c in comp_list if c.startswith(completion_text)]
        info.editor.show_completion_list(comp_list, completion_text,
                                         prev_info.automatic)

    def _handle_info_response(self, resp, info, prev_info):
        # make sure we are on the same line of text
        if info.line_num != prev_info.line_num:
            return

        if resp['name']:
            self.emit(SIGNAL(
                "send_to_inspector(QString,QString,QString,QString,bool)"),
                resp['name'], resp['argspec'],
                resp['note'], resp['doc_text'],
                not prev_info.auto)

        if resp['calltip']:
            self.editor.show_calltip('Arguments', resp['calltip'],
                                     signature=True,
                                     at_position=prev_info.position)

    def _handle_definition_response(self, resp, info, prev_info):
        fname, lineno = resp
        self.emit(SIGNAL("edit_goto(QString,int,QString)"),
                  fname, lineno, "")

    def _update_extension_modules(self):
        for plugin in self.plugins:
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

    def load_plugin(self):
        pass

    def get_completions(self, info):
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
