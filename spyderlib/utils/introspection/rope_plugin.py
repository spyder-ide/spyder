# -*- coding: utf-8 -*-
#
# Copyright © 2013 The Spyder Development Team
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Rope introspection plugin
"""

import time

from spyderlib import dependencies
from spyderlib.baseconfig import get_conf_path, _, STDERR
from spyderlib.utils import encoding, programs
from spyderlib.py3compat import PY2
from spyderlib.utils.dochelpers import getsignaturefromtext
from spyderlib.utils import sourcecode
from spyderlib.utils.debug import log_last_error, log_dt
from spyderlib.utils.introspection.plugin_manager import (
    DEBUG_EDITOR, LOG_FILENAME, IntrospectionPlugin)
try:
    try:
        from spyderlib import rope_patch
        rope_patch.apply()
    except ImportError:
        # rope 0.9.2/0.9.3 is not installed
        pass
    import rope.base.libutils
    import rope.contrib.codeassist
except ImportError:
    pass


ROPE_REQVER = '>=0.9.2'
dependencies.add('rope',
                 _("Editor's code completion, go-to-definition and help"),
                 required_version=ROPE_REQVER)

#TODO: The following preferences should be customizable in the future
ROPE_PREFS = {'ignore_syntax_errors': True,
              'ignore_bad_imports': True,
              'soa_followed_calls': 2,
              'extension_modules': [],
              }


class RopePlugin(IntrospectionPlugin):
    """
    Rope based introspection plugin for jedi
    
    Editor's code completion, go-to-definition and help
    """
    
    project = None
    
    # ---- IntrospectionPlugin API --------------------------------------------
    name = 'rope'
    
    def load_plugin(self):
        """Load the Rope introspection plugin"""
        if not programs.is_module_installed('rope', ROPE_REQVER):
            raise ImportError('Requires Rope %s' % ROPE_REQVER)
        self.project = None
        self.create_rope_project(root_path=get_conf_path())

    def get_completions(self, info):
        """Get a list of completions using Rope"""
        if self.project is None:
            return
        filename = info.filename
        source_code = info.source_code
        offset = info.position

        if PY2:
            filename = filename.encode('utf-8')
        else:
            #TODO: test if this is working without any further change in
            # Python 3 with a user account containing unicode characters
            pass
        try:
            resource = rope.base.libutils.path_to_resource(self.project,
                                                           filename)
        except Exception as _error:
            if DEBUG_EDITOR:
                log_last_error(LOG_FILENAME, "path_to_resource: %r" % filename)
            resource = None
        try:
            if DEBUG_EDITOR:
                t0 = time.time()
            proposals = rope.contrib.codeassist.code_assist(self.project,
                                    source_code, offset, resource, maxfixes=3)
            proposals = rope.contrib.codeassist.sorted_proposals(proposals)
            if DEBUG_EDITOR:
                log_dt(LOG_FILENAME, "code_assist/sorted_proposals", t0)
            return [proposal.name for proposal in proposals]
        except Exception as _error:  #analysis:ignore
            if DEBUG_EDITOR:
                log_last_error(LOG_FILENAME, "get_completion_list")

    def get_info(self, info):
        """Get a formatted calltip and docstring from Rope"""
        if self.project is None:
            return
        filename = info.filename
        source_code = info.source_code
        offset = info.position

        if PY2:
            filename = filename.encode('utf-8')
        else:
            #TODO: test if this is working without any further change in
            # Python 3 with a user account containing unicode characters
            pass
        try:
            resource = rope.base.libutils.path_to_resource(self.project,
                                                           filename)
        except Exception as _error:
            if DEBUG_EDITOR:
                log_last_error(LOG_FILENAME, "path_to_resource: %r" % filename)
            resource = None
        try:
            if DEBUG_EDITOR:
                t0 = time.time()
            cts = rope.contrib.codeassist.get_calltip(
                            self.project, source_code, offset, resource,
                            ignore_unknown=False, remove_self=True, maxfixes=3)
            if DEBUG_EDITOR:
                log_dt(LOG_FILENAME, "get_calltip", t0)
            if cts is not None:
                while '..' in cts:
                    cts = cts.replace('..', '.')
                if '(.)' in cts:
                    cts = cts.replace('(.)', '(...)')
            try:
                doc_text = rope.contrib.codeassist.get_doc(self.project,
                                     source_code, offset, resource, maxfixes=3)
                if DEBUG_EDITOR:
                    log_dt(LOG_FILENAME, "get_doc", t0)
            except Exception as _error:
                doc_text = ''
                if DEBUG_EDITOR:
                    log_last_error(LOG_FILENAME, "get_doc")
            return self.handle_info(cts, doc_text, source_code, offset)
        except Exception as _error:  #analysis:ignore
            if DEBUG_EDITOR:
                log_last_error(LOG_FILENAME, "get_calltip_text")

    def handle_info(self, cts, doc_text, source_code, offset):

        obj_fullname = ''
        calltip = ''
        argspec = ''
        note = ''

        if cts:
            cts = cts.replace('.__init__', '')
            parpos = cts.find('(')
            if parpos:
                obj_fullname = cts[:parpos]
                obj_name = obj_fullname.split('.')[-1]
                cts = cts.replace(obj_fullname, obj_name)
                calltip = cts
                if ('()' in cts) or ('(...)' in cts):
                    # Either inspected object has no argument, or it's
                    # a builtin or an extension -- in this last case
                    # the following attempt may succeed:
                    calltip = getsignaturefromtext(doc_text, obj_name)
        if not obj_fullname:
            obj_fullname = sourcecode.get_primary_at(source_code, offset)
        if obj_fullname and not obj_fullname.startswith('self.'):
            # doc_text was generated by utils.dochelpers.getdoc
            if type(doc_text) is dict:
                obj_fullname = doc_text['name'] or obj_fullname
                argspec = doc_text['argspec']
                note = doc_text['note']
                doc_text = doc_text['docstring']
            elif calltip:
                argspec_st = calltip.find('(')
                argspec = calltip[argspec_st:]
                module_end = obj_fullname.rfind('.')
                module = obj_fullname[:module_end]
                note = 'Present in %s module' % module

        return dict(name=obj_fullname, argspec=argspec, note=note,
            docstring=doc_text, calltip=calltip)

    def get_definition(self, info):
        """Find a definition location using Rope"""
        if self.project is None:
            return

        filename = info.filename
        source_code = info.source_code
        offset = info.position

        if PY2:
            filename = filename.encode('utf-8')
        else:
            #TODO: test if this is working without any further change in
            # Python 3 with a user account containing unicode characters
            pass
        try:
            resource = rope.base.libutils.path_to_resource(self.project,
                                                           filename)
        except Exception as _error:
            if DEBUG_EDITOR:
                log_last_error(LOG_FILENAME, "path_to_resource: %r" % filename)
            resource = None
        try:
            if DEBUG_EDITOR:
                t0 = time.time()
            resource, lineno = rope.contrib.codeassist.get_definition_location(
                    self.project, source_code, offset, resource, maxfixes=3)
            if DEBUG_EDITOR:
                log_dt(LOG_FILENAME, "get_definition_location", t0)
            if resource is not None:
                filename = resource.real_path
            if filename and lineno:
                return filename, lineno
        except Exception as _error:  #analysis:ignore
            if DEBUG_EDITOR:
                log_last_error(LOG_FILENAME, "get_definition_location")

    def validate(self):
        """Validate the Rope project"""
        if self.project is not None:
            self.project.validate(self.project.root)

    def set_pref(self, key, value):
        """Set a Rope preference"""
        if self.project is not None:
            self.project.prefs.set(key, value)

    # ---- Private API -------------------------------------------------------

    def create_rope_project(self, root_path):
        """Create a Rope project on a desired path"""
        if PY2:
            root_path = encoding.to_fs_from_unicode(root_path)
        else:
            #TODO: test if this is working without any further change in
            # Python 3 with a user account containing unicode characters
            pass
        try:
            import rope.base.project
            self.project = rope.base.project.Project(root_path, **ROPE_PREFS)
        except ImportError:
            print >>STDERR, 'project error'
            self.project = None
            if DEBUG_EDITOR:
                log_last_error(LOG_FILENAME,
                               "create_rope_project: %r" % root_path)
        except TypeError:
            # Compatibility with new Mercurial API (>= 1.3).
            # New versions of rope (> 0.9.2) already handle this issue
            self.project = None
            if DEBUG_EDITOR:
                log_last_error(LOG_FILENAME,
                               "create_rope_project: %r" % root_path)
        self.validate()

    def close_rope_project(self):
        """Close the Rope project"""
        if self.project is not None:
            self.project.close()


if __name__ == '__main__':

    from spyderlib.utils.introspection.plugin_manager import CodeInfo
    
    p = RopePlugin()
    p.load_plugin()

    source_code = "import numpy; numpy.ones"
    docs = p.get_info(CodeInfo('info', source_code, len(source_code),
                                           __file__))
    assert 'ones(' in docs['calltip'] and 'ones(' in docs['docstring']
    
    source_code = "import numpy; n"
    completions = p.get_completions(CodeInfo('completions', source_code,
        len(source_code), __file__))
    assert 'numpy' in completions 
    
    source_code = "import matplotlib.pyplot as plt; plt.imsave"
    path, line_nr = p.get_definition(CodeInfo('definition', source_code,
        len(source_code), __file__))
    assert 'pyplot.py' in path 

    code = '''
def test(a, b):
    """Test docstring"""
    pass
test(1,'''
    path, line = p.get_definition(CodeInfo('definition', code, len(code),
        'dummy.txt'))
    assert line == 2

    docs = p.get_info(CodeInfo('info', code, len(code), __file__))
    assert 'Test docstring' in docs['docstring']
