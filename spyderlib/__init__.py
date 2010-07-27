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

__version__ = '2.0.0alpha3'
__license__ = __doc__

#TODO: Workspace is gone: find a way to implement the save on exit with the 
#      external console --> see the external console's closing method
#      --> show a window with checkboxes and... quickview of namespace contents?

#FIXME: Internal console MT: for i in range(100000): print i -> bug

#TODO: add an option to customize namespace browser refresh time out

#TODO: "Preferences": add color schemes for editor/console

#TODO: IPython: add "configurations" management

#TODO: File Explorer: add support for multiple selection

#TODO: Handling errors in project explorer I/O functions (i.e. find a way to 
# allow loading a corrupted project to be able to launch Spyder anyway)

#FIXME: When saving, collapsing corresponding class browser item
#       -> was it introduced following last bugfix on class browser?

#TODO: Implement code completion in code editor with rope:
# 1. QtEditor -> add completion support
# 3. Refactoring -> shell.py key press events --> in base class (shared with qteditor.py)
# 4. Implement: zoomIn, zoomOut

#TODO: QsciEditor was removed: remove (or rename) all the QScintilla-compat. methods (e.g. selectedText, hasSelectedText, etc.)

#TODO: remove all plugin cross references: use directly the 'main' attribute (rename it?)

#TODO: Option to inverse console colors

#TODO: Take a look at session management: adapt to new v2.0 features
