# -*- coding: utf-8 -*-
#
# Copyright © 2015 The Spyder development team
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

from __future__ import print_function

from collections import OrderedDict
import time

from spyderlib.config.base import DEBUG, get_conf_path, debug_print
from spyderlib.utils import sourcecode
from spyderlib.utils.debug import log_last_error

from spyderlib.qt.QtGui import QApplication
from spyderlib.qt.QtCore import Signal, QThread, QObject, QTimer

from spyderlib.utils.introspection.utils import CodeInfo

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
        debug_print('got timeout: %s' % self.plugins)
        if self.pending:
            for plugin in self.plugins:
                if plugin.name in self.pending:
                    self._finalize(plugin.name, self.pending[plugin.name])
                    return
        self.waiting = False

    def _handle_incoming(self, name):
        # coerce to a str in case it is a QString
        name = str(name)
        try:
            self._threads[name].wait()
        except AttributeError:
            return
        if self.result:
            return
        result = self._threads[name].result
        if name == self.plugins[0].name or not self.waiting:
            if result:
                self._finalize(name, result)
            else:
                debug_print('No valid responses acquired')
                self.introspection_complete.emit()
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
        debug_print('%s request from %s finished: "%s" in %.1f sec'
            % (self.info.name, name, str(result)[:100], delta))
        self.introspection_complete.emit()


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


class PluginManager(QObject):

    send_to_help = Signal(str, str, str, str, bool)
    edit_goto = Signal(str, int, str)

    def __init__(self, editor_widget):
        super(PluginManager, self).__init__()
        self.editor_widget = editor_widget
        self.pending = None
        self.busy = False
        self.load_plugins()

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
        in_comment_or_string = editor.in_comment_or_string()

        if position is None:
            position = editor.get_position('cursor')

        kwargs['editor'] = editor
        kwargs['finfo'] = finfo
        kwargs['editor_widget'] = self.editor_widget

        return CodeInfo(name, finfo.get_source_code(), position,
            finfo.filename, editor.is_python_like, in_comment_or_string,
            **kwargs)

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
        """Show signature calltip and/or docstring in the Help plugin"""
        # auto is True means that this method was called automatically,
        # i.e. the user has just entered an opening parenthesis -- in that
        # case, we don't want to force Help to be visible, to avoid polluting
        # the window layout
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
        debug_print('%s request' % info.name)

        editor = info.editor
        if ((not editor.is_python_like())
                or sourcecode.is_keyword(info.obj)
                or (editor.in_comment_or_string() and info.name != 'info')):
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
        elif (info.name == 'definition' and not info.editor.is_python()
              or info.name == 'info'):
            plugins = [p for p in self.plugins.values() if not p.busy]
        else:
            # use all but the fallback
            plugins = [p for p in list(self.plugins.values())[:-1]
                       if not p. busy]

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
            new_list = [(c, t) for (c, t) in comp_list
                        if c.startswith(info.full_obj)]
            if new_list:
                pos = info.editor.get_position('cursor')
                new_pos = pos + len(info.full_obj) - len(info.obj)
                info.editor.set_cursor_position(new_pos)
                completion_text = info.full_obj
                comp_list = new_list

        if '.' in completion_text:
            completion_text = completion_text.split('.')[-1]

        comp_list = [(c.split('.')[-1], t) for (c, t) in comp_list]
        comp_list = [(c, t) for (c, t) in comp_list
                     if c.startswith(completion_text)]

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
            self.send_to_help.emit(
                resp['name'], resp['argspec'],
                resp['note'], resp['docstring'],
                not prev_info.auto)

    def _handle_definition_response(self, resp, info, prev_info):
        """Handle a `definition` response"""
        fname, lineno = resp
        self.edit_goto.emit(fname, lineno, "")

    def _post_message(self, message, timeout=60000):
        """
        Post a message to the main window status bar with a timeout in ms
        """
        if self.editor_widget:
            try:
                statusbar = self.editor_widget.window().statusBar()
                statusbar.showMessage(message, timeout)
                QApplication.processEvents()
            except AttributeError:
                pass


class IntrospectionPlugin(object):

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

    def validate(self):
        """Validate the plugin"""
        pass

