# -*- coding: utf-8 -*-
"""
Spyder License Agreement (MIT License)
--------------------------------------

Copyright (c) 2009-2013 Pierre Raybaut
Copyright (c) 2013-2015 The Spyder Development Team

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""

__version__ = '2.3.7'
__license__ = __doc__
__project_url__ = 'https://github.com/spyder-ide/spyder'
__forum_url__   = 'http://groups.google.com/group/spyderlib'

# Dear (Debian, RPM, ...) package makers, please feel free to customize the
# following path to module's data (images) and translations:
DATAPATH = LOCALEPATH = DOCPATH = MATHJAXPATH = JQUERYPATH = ''


import os
# Directory of the current file
__dir__ = os.path.dirname(os.path.abspath(__file__))


def add_to_distribution(dist):
    """Add package to py2exe/cx_Freeze distribution object
    Extension to guidata.disthelpers"""
    try:
        dist.add_qt_bindings()
    except AttributeError:
        raise ImportError("This script requires guidata 1.5+")
    for _modname in ('spyderlib', 'spyderplugins'):
        dist.add_module_data_files(_modname, ("", ),
                                   ('.png', '.svg', '.html', '.png', '.txt',
                                    '.js', '.inv', '.ico', '.css', '.doctree',
                                    '.qm', '.py',),
                                   copy_to_root=False)


def get_versions(reporev=True):
    """Get version information for components used by Spyder"""
    import sys
    import platform
    import spyderlib.qt
    import spyderlib.qt.QtCore

    revision = None
    if reporev:
        from spyderlib.utils import vcs
        revision = vcs.get_git_revision(os.path.dirname(__dir__))

    if not sys.platform == 'darwin':  # To avoid a crash with our Mac app
        system = platform.system()
    else:
        system = 'Darwin'
    
    return {
        'spyder': __version__,
        'python': platform.python_version(),  # "2.7.3"
        'bitness': 64 if sys.maxsize > 2**32 else 32,
        'qt': spyderlib.qt.QtCore.__version__,
        'qt_api': spyderlib.qt.API_NAME,      # PySide or PyQt4
        'qt_api_ver': spyderlib.qt.__version__,
        'system': system,   # Linux, Windows, ...
        'revision': revision,  # '9fdf926eccce'
    }
