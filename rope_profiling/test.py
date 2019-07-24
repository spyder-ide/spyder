# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------


# Standard library imports
import os.path as osp
import time

# Third party imports
import rope.base.project
import rope.base.libutils
import rope.contrib.codeassist


ROPE_PREFS = {
               'ignore_syntax_errors': True,
               'ignore_bad_imports': True,
               'automatic_soa': False,
               'perform_doa': False,
               'import_dynload_stdmods': False,
               'soa_followed_calls': 2,
               'extension_modules': [
         "PyQt4", "PyQt4.QtGui", "QtGui", "PyQt4.QtCore", "QtCore",
         "PyQt4.QtScript", "QtScript", "os.path", "numpy", "scipy", "PIL",
         "OpenGL", "array", "audioop", "binascii", "cPickle", "cStringIO",
         "cmath", "collections", "datetime", "errno", "exceptions", "gc",
         "imageop", "imp", "itertools", "marshal", "math", "mmap", "msvcrt",
         "nt", "operator", "os", "parser", "rgbimg", "signal", "strop", "sys",
         "thread", "time", "wx", "wxPython", "xxsubtype", "zipimport", "zlib"],
               }

def ropetest():
    project = rope.base.project.Project('src', **ROPE_PREFS)
    project.validate(project.root)

    filename = osp.join('src', 'script.py')
    source_code = file(filename, 'rb').read()
    offset = len(source_code)

    resource = rope.base.libutils.path_to_resource(project, filename)

    t0 = time.time()

    proposals = rope.contrib.codeassist.code_assist(project, source_code,
                                                    offset, resource)
    proposals = rope.contrib.codeassist.sorted_proposals(proposals)

    print "%s: %d ms" % ("completion", 10*round(1e2*(time.time()-t0)))
    print 'loadtxt' in [proposal.name for proposal in proposals]

pydocextractor = rope.contrib.codeassist.PyDocExtractor()

def get_pyobject(project, source_code, offset, resource=None, maxfixes=1):
    fixer = rope.contrib.codeassist.fixsyntax.FixSyntax(project.pycore,
                                        source_code, resource, maxfixes)
    pyname = fixer.pyname_at(offset)
    if pyname is None:
        return None
    return pyname.get_object()

def get_calltip_from_pyobject(pyobject,
                              ignore_unknown=False, remove_self=False):
    return pydocextractor.get_calltip(pyobject, ignore_unknown, remove_self)

def get_doc_from_pyobject(pyobject):
    return pydocextractor.get_doc(pyobject)


from spyder import rope_patch
rope_patch.apply()

def other_features():
    project = rope.base.project.Project('src', **ROPE_PREFS)
    project.validate(project.root)

    filename = osp.join('src', 'script2.py')
    source_code = file(filename, 'rb').read()
    offset = len(source_code)

    resource = rope.base.libutils.path_to_resource(project, filename)

    t0 = time.time()

    cts = rope.contrib.codeassist.get_calltip(
                                    project, source_code, offset, resource)
    doc_text = rope.contrib.codeassist.get_doc(
                                    project, source_code, offset, resource)
    def_loc = rope.contrib.codeassist.get_definition_location(
                                    project, source_code, offset, resource)

    msg = "Testing other rope instrospection features"
    print msg
    print "="*len(msg)
    print ""
    print "%s: %d ms" % ("elapsed time", 10*round(1e2*(time.time()-t0)))
    print ""
    print 'calltip:', cts
    print 'definition location:', def_loc
    print 'doc:'
    print '*** DOCUMENTATION ***' + '*'*60
    print doc_text
    print '*********************' + '*'*60


if __name__ == '__main__':
    # ropetest()
    other_features()
