from __future__ import print_function
import re
from collections import OrderedDict

from spyderlib.baseconfig import DEBUG, get_conf_path, debug_print
from spyderlib.utils.dochelpers import getsignaturefromtext
from spyderlib.utils import sourcecode
from spyderlib.utils.debug import log_last_error
from spyderlib.utils.introspection.module_completion import (module_completion,
                                                             get_preferred_submodules)
from spyderlib.py3compat import to_text_string

from spyderlib.qt.QtCore import SIGNAL, QThread, QObject


PLUGINS = ['jedi', 'rope', 'fallback']
LOG_FILENAME = get_conf_path('introspection.log')
DEBUG_EDITOR = DEBUG >= 3


class GetSubmodulesThread(QThread):

    """
    A thread to generate a list of submodules to be passed to Rope
    extension_modules preference
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
        try:
            self.result = func(self.info)
        except Exception as e:
            debug_print(e)
        self.emit(SIGNAL('introspection_complete()'))


class Info(object):

    """Store the information about an introspection request.
    """
    id_regex = re.compile(r'[^\d\W]\w*', re.UNICODE)
    func_call_regex = re.compile(r'([^\d\W]\w*)\([^\)\()]*\Z',
                                 re.UNICODE)

    def __init__(self, name, editor_widget, position=None):

        self.editor = editor_widget.get_current_editor()
        self.finfo = editor_widget.get_current_finfo()
        self.name = name
        self.source_code = self.finfo.get_source_code()
        self.filename = self.finfo.filename

        if position is None:
            position = self.editor.get_position('cursor')
        self.position = position

        lines = self.source_code[:position].splitlines()
        self.line_num = len(lines)
        self.line = lines[-1]

        tokens = re.split(self.id_regex, self.line, re.UNICODE)
        if len(tokens) >= 2 and tokens[-1] == '':
            self.object = tokens[-2]
        else:
            self.object = None
        func_call = re.findall(self.func_call_regex, self.line,
                               re.UNICODE)
        if func_call:
            self.func_call = func_call[-1]
            self.func_call_col = (self.line.index(self.func_call)
                                  + len(self.func_call))
            self.func_call_offset = (position - len(self.line)
                                     + self.func_call_col)
        else:
            self.func_call = None
            self.func_call_col = 0
            self.func_call_offset = position


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
        plugins = dict()
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

    def _handle_request(self, info, desired=None):
        if self._use_fallback(info):
            desired = 'fallback'
        self.pending = (info, desired)
        if self.busy:
            return
        self._handle_pending()

    def _handle_pending(self):
        if not self.pending:
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

    def _handle_info_response(self, help_info, info, prev_info):
        # make sure we are on the same line of text
        if info.line_num != prev_info.line_num:
            return

        if help_info['obj_fullname']:
            self.emit(SIGNAL(
                "send_to_inspector(QString,QString,QString,QString,bool)"),
                help_info['obj_fullname'], help_info['argspec'],
                help_info['note'], help_info['doc_text'],
                not prev_info.auto)

        if help_info['signature']:
            self.editor.show_calltip('Arguments', help_info['signature'],
                                     signature=True,
                                     at_position=prev_info.position)

    def _handle_definition_response(self, resp, info, prev_info):
        fname, lineno = resp
        self.emit(SIGNAL("edit_goto(QString,int,QString)"),
                  fname, lineno, "")

    def _use_fallback(self, info):
        editor = info.editor
        obj = info.object

        if not editor.is_python_like():
            return True
        elif editor.is_python_like() and sourcecode.is_keyword(obj):
            return True
        elif editor.in_comment_or_string():
            return True
        return False

    def _update_extension_modules(self):
        for plugin in self.plugins:
            plugin.set_pref('extension_modules',
                            self._submods_thread.submods)


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



class IntrospectionPlugin(object):

    def __init__(self, manager):
        self.manager = manager
        self.manager.connect(self, SIGNAL('introspection_completion(QString)'),
                             self.manager.introspection_complete)

    def load_plugin(self):
        raise NotImplementedError

    def get_completion_list(self, info):
        raise NotImplementedError

    def get_calltip_and_docs(self, info):
        raise NotImplementedError

    def get_definition_location(self, info):
        raise NotImplementedError

    def set_pref(self, name, value):
        """Set a plugin preference to a value"""
        pass

    def validate(self):
        """Validate the plugin"""
        pass
