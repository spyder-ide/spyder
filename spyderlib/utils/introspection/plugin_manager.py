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
from spyderlib.qt.QtCore import Signal, QObject, QTimer

from spyderlib.utils.introspection.utils import CodeInfo
from spyderlib.utils.introspection.plugin_client import PluginClient

PLUGINS = ['rope', 'jedi', 'fallback']

LOG_FILENAME = get_conf_path('introspection.log')
DEBUG_EDITOR = DEBUG >= 3
LEAD_TIME_SEC = 0.25


class PluginManager(QObject):

    response_received = Signal(object)

    def __init__(self):
        super(PluginManager, self).__init__()
        plugins = OrderedDict()
        for name in PLUGINS:
            try:
                plugin = PluginClient(name)
            except Exception:
                debug_print('Introspection Plugin Failed: %s' % name)
                continue
            debug_print('Introspection Plugin Loaded: %s' % name)
            plugins[name] = plugin
            plugin.request_handled.connect(self._handle_response)
        self.plugins = plugins
        self.timer = QTimer()
        self.request = None
        self.pending = None
        debug_print('Plugins loaded: %s' % self.plugins.keys())

    def send_request(self, info):
        """Handle an incoming request from the user."""
        debug_print('%s request' % info.name)

        editor = info.editor
        if (info.name == 'completion' and 'jedi' not in self.plugins and
                info.line.lstrip().startswith(('import ', 'from '))):
            desired = 'fallback'

        if ((not editor.is_python_like()) or
                sourcecode.is_keyword(info.obj) or
                (editor.in_comment_or_string() and info.name != 'info')):
            desired = 'fallback'

        plugins = self.plugins.values()
        if desired:
            plugins = [self.plugins[desired]]
        elif (info.name == 'definition' and not info.editor.is_python() or
              info.name == 'info'):
            pass
        else:
            # Use all but the fallback
            plugins = list(self.plugins.values)[::-1]

        self._start_time = time.time()
        request = dict(method='get_%s' % info.name,
                       args=[info.__dict__],
                       request_id=id(info))
        for plugin in plugins:
            plugin.send(request)
        self.timer.stop()
        self.timer.singleShot(LEAD_TIME_SEC * 1000, self._handle_timeout)
        self.request = request
        self.waiting = True

    def validate(self):
        message = dict(method='validate')
        for plugin in self.plugins.values():
            plugin.send(message)

    def handle_response(self, response):
        if (self.request is None or
                response['request_id'] != self.request['request_id']):
            return
        name = response['plugin_name']
        if name == self.plugins[0].plugin_name or not self.waiting:
            if response['result']:
                self._finalize(response)
            else:
                debug_print('No valid responses acquired')
                self.introspection_complete.emit()
        else:
            self.pending = response

    def _finalize(self, response):
        self.result = response['result']
        self.waiting = False
        self.pending = None
        delta = time.time() - self._start_time
        debug_print('%s request from %s finished: "%s" in %.1f sec'
            % (self.info.name, response['plugin_name'],
               str(self.result)[:100], delta))
        self.response_received.emit(response)

    def _handle_timeout(self):
        self.waiting = False
        if self.pending:
            self._finalize(self.pending)


class IntrospectionManager(QObject):

    send_to_help = Signal(str, str, str, str, bool)
    edit_goto = Signal(str, int, str)

    def __init__(self, editor_widget):
        super(IntrospectionManager, self).__init__()
        self.editor_widget = editor_widget
        self.pending = None
        self.plugin_manager = PluginManager()
        self.plugin_manager.response_received.connect(
            self._introspection_complete)

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
        self.plugin_manager.handle_request(info)

    def go_to_definition(self, position):
        """Go to definition"""
        info = self._get_code_info('definition', position)
        self.plugin_manager.handle_request(info)

    def show_object_info(self, position, auto=True):
        """Show signature calltip and/or docstring in the Help plugin"""
        # auto is True means that this method was called automatically,
        # i.e. the user has just entered an opening parenthesis -- in that
        # case, we don't want to force Help to be visible, to avoid polluting
        # the window layout
        info = self._get_code_info('info', position, auto=auto)
        self.plugin_manager.handle_request(info)

    def validate(self):
        """Validate the plugins"""
        self.plugin_manager.validate()

    def is_editor_ready(self):
        """Check if the main app is starting up"""
        if self.editor_widget:
            window = self.editor_widget.window()
            if hasattr(window, 'is_starting_up') and not window.is_starting_up:
                return True

    def _introspection_complete(self, response):
        """
        Handle an introspection response completion.

        Route the response to the correct handler.
        """
        result = response['result']
        info = response['info']
        current = self._get_code_info('current')

        if result and current.filename == info.filename:
            func = getattr(self, '_handle_%s_response' % info.name)
            try:
                func(result, current, info)
            except Exception as e:
                debug_print(e)

    def _handle_completions_result(self, comp_list, info, prev_info):
        """
        Handle a `completions` result.

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

    def _handle_info_result(self, resp, info, prev_info):
        """
        Handle an `info` result, triggering a calltip and/or docstring.

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

    def _handle_definition_result(self, resp, info, prev_info):
        """Handle a `definition` result"""
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

