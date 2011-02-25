# -*- coding: utf-8 -*-
"""
Created on Wed Feb 23 15:44:03 2011

@author: Pierre Raybaut
"""

import time, os.path as osp

import rope.base.project
import rope.base.libutils
import rope.contrib.codeassist

## ROPE_PREFS = {
##               'ignore_syntax_errors': True,
##               'ignore_bad_imports': True,
##               'automatic_soa': False,
##               'perform_doa': False,
##               'import_dynload_stdmods': False,
##               'soa_followed_calls': 2,
##               'extension_modules': [
##         "PyQt4", "PyQt4.QtGui", "QtGui", "PyQt4.QtCore", "QtCore",
##         "PyQt4.QtScript", "QtScript", "os.path", "numpy", "scipy", "PIL",
##         "OpenGL", "array", "audioop", "binascii", "cPickle", "cStringIO",
##         "cmath", "collections", "datetime", "errno", "exceptions", "gc",
##         "imageop", "imp", "itertools", "marshal", "math", "mmap", "msvcrt",
##         "nt", "operator", "os", "parser", "rgbimg", "signal", "strop", "sys",
##         "thread", "time", "wx", "wxPython", "xxsubtype", "zipimport", "zlib"],
##               }

def ropetest():
    project = rope.base.project.Project('src')#, **ROPE_PREFS)
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
    
if __name__ == '__main__':
    ropetest()