# -*- coding: utf-8 -*-
"""
Spyder License Agreement (MIT License)
--------------------------------------

Copyright (c) 2009 Pierre Raybaut

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

__version__ = '2.0alpha1'
__license__ = __doc__

#TODO: Workspace is gone: find a way to implement the save on exit with the 
#      external console --> see the external console's closing method
#TODO: Workspace is gone: reimplement the import_data from file explorer:
#                self.connect(self.explorer, SIGNAL("import_data(QString)"),
#                             self.workspace.import_data)
#      and from project explorer:
#                self.connect(self.projectexplorer,
#                             SIGNAL("import_data(QString)"),
#                             self.workspace.import_data)

#FIXME: IPython // Big bug with GUI file dialogs on win32: open/save/...

#FIXME: Internal console MT: for i in range(100000): print i -> bug

#TODO: add an option to customize namespace browser refresh time out

#TODO: regroup plugin settings in a new menu (or dlg box??) "Preferences"

#TODO: IPython: add "configurations" management

#TODO: File Explorer: add support for multiple selection
