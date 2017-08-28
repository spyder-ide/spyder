# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Rope introspection plugin
"""

import time
import imp

from spyder.config.base import get_conf_path, STDERR
from spyder.utils import encoding, programs
from spyder.py3compat import PY2
from spyder.utils.dochelpers import getsignaturefromtext
from spyder.utils import sourcecode
from spyder.utils.debug import log_last_error, log_dt
from spyder.utils.introspection.manager import (
    DEBUG_EDITOR, LOG_FILENAME, IntrospectionPlugin)
from spyder.utils.introspection.module_completion import (
    get_preferred_submodules)
from spyder.utils.introspection.manager import ROPE_REQVER

try:
    try:
        from spyder.utils.introspection import rope_patch
        rope_patch.apply()
    except ImportError:
        # rope is not installed
        pass
    import rope.base.libutils
    import rope.contrib.codeassist
except ImportError:
    pass


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
        submods = get_preferred_submodules()
        actual = []
        for submod in submods:
            try:
                imp.find_module(submod)
                actual.append(submod)
            except ImportError:
                pass
        if self.project is not None:
            self.project.prefs.set('extension_modules', actual)

    def get_completions(self, info):
        """Get a list of (completion, type) tuples using Rope"""
        if self.project is None:
            return []
        filename = info['filename']
        source_code = info['source_code']
        offset = info['position']

        # Set python path into rope project
        self.project.prefs.set('python_path', info['sys_path'])

        # Prevent Rope from returning import completions because
        # it can't handle them. Only Jedi can do it!
        lines = sourcecode.split_source(source_code[:offset])
        last_line = lines[-1].lstrip()
        if (last_line.startswith('import ') or last_line.startswith('from ')) \
          and not ';' in last_line:
            return []

        if filename is not None:
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
            return [(proposal.name, proposal.type) for proposal in proposals]
        except Exception as _error:  #analysis:ignore
            if DEBUG_EDITOR:
                log_last_error(LOG_FILENAME, "get_completion_list")
        return []

    def get_info(self, info):
        """Get a formatted calltip and docstring from Rope"""
        if self.project is None:
            return
        filename = info['filename']
        source_code = info['source_code']
        offset = info['position']

        # Set python path into rope project
        self.project.prefs.set('python_path', info['sys_path'])

        if filename is not None:
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

        if not doc_text and not calltip:
            return

        return dict(name=obj_fullname, argspec=argspec, note=note,
            docstring=doc_text, calltip=calltip)

    def get_definition(self, info):
        """Find a definition location using Rope"""
        if self.project is None:
            return

        filename = info['filename']
        source_code = info['source_code']
        offset = info['position']

        # Set python path into rope project
        self.project.prefs.set('python_path', info['sys_path'])
        if filename is not None:
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
            try:
                self.project.validate(self.project.root)
            except RuntimeError:
                pass

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
            self.project = None
            if DEBUG_EDITOR:
                log_last_error(LOG_FILENAME,
                               "create_rope_project: %r" % root_path)
        self.validate()

    def close_rope_project(self):
        """Close the Rope project"""
        if self.project is not None:
            self.project.close()
