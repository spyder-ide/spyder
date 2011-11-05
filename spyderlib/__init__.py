# -*- coding: utf-8 -*-
"""
Spyder License Agreement (MIT License)
--------------------------------------

Copyright (c) 2009-2011 Pierre Raybaut

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

__version__ = '2.1.2'
__license__ = __doc__
__project_url__ = 'http://spyderlib.googlecode.com'
__forum_url__   = 'http://groups.google.com/group/spyderlib'

# Dear (Debian, RPM, ...) package makers, please feel free to customize the
# following path to module's data (images) and translations:
DATAPATH = LOCALEPATH = DOCPATH = ''

def add_to_distribution(dist):
    """Add package to py2exe/cx_Freeze distribution object
    Extension to guidata.disthelpers"""
    dist.add_modules('PyQt4')
    for _modname in ('spyderlib', 'spyderplugins'):
        dist.add_module_data_files(_modname, ("", ),
                                   ('.png', '.svg', '.html', '.png', '.txt',
                                    '.js', '.inv', '.ico', '.css', '.doctree',
                                    '.qm', '.py',),
                                   copy_to_root=False)
