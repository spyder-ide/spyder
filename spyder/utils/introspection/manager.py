# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Standard library imports
from __future__ import print_function
from collections import OrderedDict
import time
import logging

# Third party imports
from qtpy.QtCore import QObject, QTimer, Signal
from qtpy.QtWidgets import QApplication

# Local imports
from spyder import dependencies
from spyder.config.base import _, DEBUG, get_conf_path
from spyder.utils import sourcecode
from spyder.utils.introspection.plugin_client import PluginClient
from spyder.utils.introspection.utils import CodeInfo

logger = logging.getLogger(__name__)

PLUGINS = ['rope', 'jedi', 'fallback']

LOG_FILENAME = get_conf_path('introspection.log')
DEBUG_EDITOR = DEBUG >= 3
LEAD_TIME_SEC = 0.25


ROPE_REQVER = '>=0.9.4'
dependencies.add('rope',
                 _("Editor's code completion, go-to-definition and help"),
                 required_version=ROPE_REQVER)

JEDI_REQVER = '>=0.9.0'
dependencies.add('jedi',
                 _("Editor's code completion, go-to-definition and help"),
                 required_version=JEDI_REQVER)


class PluginManager(QObject):

    introspection_complete = Signal(object)

    def __init__(self, executable, extra_path=None):

        super(PluginManager, self).__init__()
        plugins = OrderedDict()
        for name in PLUGINS:
            try:
                plugin = PluginClient(name, executable, extra_path=extra_path)
                plugin.run()
            except Exception as e:
                logger.exception('Introspection Plugin Failed: %s', name)
                continue
            logger.debug('Introspection Plugin Loaded: %s', name)
            plugins[name] = plugin
            plugin.received.connect(self.handle_response)
        self.plugins = plugins
        self.timer = QTimer()
        self.desired = []
        self.ids = dict()
        self.info = None
        self.request = None
        self.pending = None
        self.pending_request = None
        self.waiting = False

    def send_request(self, info):
        """Handle an incoming request from the user."""
        if self.waiting:
            if info.serialize() != self.info.serialize():
                self.pending_request = info
            else:
                logger.debug('skipping duplicate request')
            return
        logger.debug('%s request', info.name)
        desired = None
        self.info = info
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
            self.desired = [desired]
        elif (info.name == 'definition' and not info.editor.is_python() or
              info.name == 'info'):
            self.desired = list(self.plugins.keys())
        else:
            # Use all but the fallback
            plugins = list(self.plugins.values())[:-1]
            self.desired = list(self.plugins.keys())[:-1]

        self._start_time = time.time()
        self.waiting = True
        method = 'get_%s' % info.name
        value = info.serialize()
        self.ids = dict()
        for plugin in plugins:
            request_id = plugin.request(method, value)
            self.ids[request_id] = plugin.name
        self.timer.stop()
        self.timer.singleShot(LEAD_TIME_SEC * 1000, self._handle_timeout)

    def validate(self):
        for plugin in self.plugins.values():
            plugin.request('validate')

    def handle_response(self, response):
        name = self.ids.get(response['request_id'], None)
        if not name:
            return
        if response.get('error', None):
            logger.debug('Response error: %s', response['error'])
            return
        if name == self.desired[0] or not self.waiting:
            if response.get('result', None):
                self._finalize(response)
        else:
            self.pending = response

    def close(self):
        for name, plugin in self.plugins.items():
            plugin.close()
            logger.debug("Introspection Plugin Closed: %s", name)

    def _finalize(self, response):
        self.waiting = False
        self.pending = None
        if self.info:
            delta = time.time() - self._start_time
            logger.debug('%s request from %s finished: "%.100s" in %.1f sec',
                         self.info.name, response['name'], response['result'],
                         delta)
            response['info'] = self.info
            self.introspection_complete.emit(response)
            self.info = None
        if self.pending_request:
            info = self.pending_request
            self.pending_request = None
            self.send_request(info)

    def _handle_timeout(self):
        self.waiting = False
        if self.pending:
            self._finalize(self.pending)
        else:
            logger.debug('No valid responses acquired')


class IntrospectionManager(QObject):

    send_to_help = Signal(str, str, str, str, bool)
    edit_goto = Signal(str, int, str)

    def __init__(self, executable=None, extra_path=None):
        super(IntrospectionManager, self).__init__()
        self.editor_widget = None
        self.pending = None
        self.extra_path = extra_path
        self.executable = executable
        self.plugin_manager = PluginManager(executable, extra_path)
        self.plugin_manager.introspection_complete.connect(
            self._introspection_complete)

    def change_executable(self, executable):
        self.executable = executable
        self._restart_plugin()

    def change_extra_path(self, extra_path):
        if extra_path != self.extra_path:
            self.extra_path = extra_path
            self._restart_plugin()

    def _restart_plugin(self):
        self.plugin_manager.close()
        self.plugin_manager = PluginManager(self.executable,
                                            extra_path=self.extra_path)
        self.plugin_manager.introspection_complete.connect(
            self._introspection_complete)

    def set_editor_widget(self, editor_widget):
        self.editor_widget = editor_widget

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
        self.plugin_manager.send_request(info)

    def go_to_definition(self, position):
        """Go to definition"""
        info = self._get_code_info('definition', position)
        self.plugin_manager.send_request(info)

    def show_object_info(self, position, auto=True):
        """Show signature calltip and/or docstring in the Help plugin"""
        # auto is True means that this method was called automatically,
        # i.e. the user has just entered an opening parenthesis -- in that
        # case, we don't want to force Help to be visible, to avoid polluting
        # the window layout
        info = self._get_code_info('info', position, auto=auto)
        self.plugin_manager.send_request(info)

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
        result = response.get('result', None)
        if result is None:
            return
        info = response['info']
        current = self._get_code_info(response['info']['name'])

        if result and current.filename == info.filename:
            func = getattr(self, '_handle_%s_result' % info.name)
            try:
                func(result, current, info)
            except Exception as e:
                logger.exception("Error handling introspection result")

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

