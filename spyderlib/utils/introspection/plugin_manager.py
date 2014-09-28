from __future__ import print_function
import re

from spyderlib.baseconfig import DEBUG, get_conf_path, debug_print
from spyderlib.utils.dochelpers import getsignaturefromtext
from spyderlib.utils import sourcecode
from spyderlib.utils.introspection.module_completion import (module_completion,
                                                      get_preferred_submodules)


from spyderlib.qt.QtCore import SIGNAL


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


self.submods_thread = GetSubmodulesThread()
self.connect(self.submods_thread, SIGNAL('submods_ready()'),
             self.update_extension_modules)
self.submods_thread.start()


def update_extension_modules(self):
    self.introspection_plugin.set_pref('extension_modules',
                                   self.submods_thread.submods)

class Info(object):
    """Store the information about an introspection request.
    """
    id_regex = re.compile(r'[^\d\W]\w*', re.UNICODE)
    func_call_regex = re.compile(r'([^\d\W]\w*)\([^\)\()]*\Z',
        re.UNICODE)

    def __init__(self, name, source_code, offset, filename):
        self.name = name
        self.source_code = source_code
        self.offset = offset
        self.filename = filename

        lines = source_code[:offset].splitlines()
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
            self.func_call_offset = (offset - len(self.line)
                + self.func_call_col)
        else:
            self.func_call = None
            self.func_call_col = 0
            self.func_call_offset = offset


class PluginManager(object):

    def __init__(self, editor_widget):
        self.editor_widget = editor_widget
        self.pending = None
        self.busy = False
        self.load_plugins()

    def load_plugins(self):
        """Get and load a plugin, checking in order of PLUGINS"""
        plugins = []
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
                plugins.append(plugin)
                debug_print('Instropection Plugin Loaded: %s' % plugin.name)
        self.plugins = plugins
        return plugins

    def get_completion_list(self, source_code, offset, filename):
        """Return a list of completion strings"""
        self._handle_request('completion_list', source_code, offset, filename)

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
        self._handle_request('calltip_and_docs', source_code, offset, filename)

    def get_definition_location(self, source_code, offset, filename):
        """Find a path and line number for a definition"""
        self._handle_request('definition_location', source_code, offset,
            filename)

    def set_pref(self, name, value):
        """Set a plugin preference to a value"""
        if not self.busy:
            for plugin in self.plugins:
                plugin.set_pref(name, value)

    def validate(self):
        """Validate the plugin"""
        if not self.busy:
            for plugin in self.plugins:
                plugin.validate()

    def _handle_request(self, name, source_code, offset, filename):
        self.pending = Info(name, source_code, offset, filename)
        if self.busy:
            return
        self._handle_pending()

    def _handle_pending(self):
        if not self.pending:
            return
        if not self.plugins[0].busy:
            self._make_async_call(self.plugins[0], self.pending)
        else:
            # fall back on basic introspector
            self._make_async_call(self.plugins[-1], self.pending)

    def _make_async_call(self, plugin, info):
        self.busy = True
        func = getattr(plugin, 'get_%s' % info)
        # TODO: do this in a separate QThread
        func(info)

    def introspection_complete(self, plugin_name):
        self.busy = False
        plugin = self.plugins[plugin_name]
        result = plugin.result
        if not result and self.pending:
            self._handle_pending()
        elif not result:
            index = self.plugins.index(plugin_name)
            if index + 1 < len(self.plugins):
                self._make_async_call(self.plugins[index + 1],
                    plugin.info)
        else:
            self._handle_response(result)

    def _handle_response(self, info):
        pass


    def trigger_code_completion(self, automatic, token_based=False):
        """Trigger code completion"""
        source_code = self.get_source_code()
        offset = self.editor.get_position('cursor')
        text = self.editor.get_text('sol', 'cursor')

        jedi = self.introspection_plugin.name == 'jedi'

        comp_list = ''
        if not jedi and text.lstrip().startswith(('import ', 'from ')):
            comp_list, completion_text = self.get_module_completion(text)
        else:
            if token_based:
                func = self.introspection_plugin.get_token_completion_list
            else:
                func = self.introspection_plugin.get_completion_list
            comp_list = func(source_code, offset, self.filename)
            if comp_list:
                completion_text = re.findall(r"[\w.]+", text, re.UNICODE)[-1]
                if '.' in completion_text:
                    completion_text = completion_text.split('.')[-1]
        if (not comp_list) and jedi and text.lstrip().startswith(('import ',
                                                                  'from ')):
            comp_list, completion_text = self.get_module_completion(text)
        if comp_list:
            self.editor.show_completion_list(comp_list, completion_text,
                                         automatic)

    def get_module_completion(self, text):
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

    def trigger_token_completion(self, automatic):
        """Trigger a completion using tokens only"""
        self.trigger_code_completion(automatic, token_based=True)


    def find_nearest_function_call(self, position):
        """Find the nearest function call at or prior to current position"""
        source_code = self.get_source_code()
        position = min(len(source_code) - 1, position)
        orig_pos = position
        # find the first preceding opening parens (keep track of closing parens)
        if not position or not source_code[position] == '(':
            close_parens = 0
            position -= 1
            while position and not (source_code[position] == '(' and close_parens == 0):
                if source_code[position] == ')':
                    close_parens += 1
                elif source_code[position] == '(' and close_parens:
                    close_parens -= 1
                position -= 1
                if source_code[position] in ['\n', '\r']:
                    position = orig_pos
                    break
        if position and source_code[position] == '(':
            position -= 1

        return position

    def show_object_info(self, position, auto=True):
        """Show signature calltip and/or docstring in the Object Inspector"""
        # auto is True means that this method was called automatically,
        # i.e. the user has just entered an opening parenthesis -- in that
        # case, we don't want to force the object inspector to be visible,
        # to avoid polluting the window layout
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
            self.emit(SIGNAL(
                    "send_to_inspector(QString,QString,QString,QString,bool)"),
                    obj_fullname, argspec, note, doc_text, not auto)
        elif obj_fullname:
            self.emit(SIGNAL(
                    "send_to_inspector(QString,QString,QString,QString,bool)"),
                    obj_fullname, '', '', '', not auto)
        if signature:
            self.editor.show_calltip('Arguments', signature, signature=True,
                                     at_position=position)

    def go_to_definition(self, position, regex=False):
        """Go to definition"""
        source_code = self.get_source_code()
        offset = position
        if regex:
            func = self.introspection_plugin.get_definition_location_regex
        else:
            func = self.introspection_plugin.get_definition_location
        fname, lineno = func(source_code, offset, self.filename)
        if fname is not None and lineno is not None:
            self.emit(SIGNAL("edit_goto(QString,int,QString)"),
                      fname, lineno, "")

    def go_to_definition_regex(self, position):
        """Go to definition using regex lookups"""
        self.go_to_definition(position, regex=True)

    def get_module_completion(self, text):
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
