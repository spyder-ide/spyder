# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Object Editor Dialog based on PyQt4
"""


def oedit(obj):
    """
    Edit the object 'obj' in a GUI-based editor and return the edited copy
    (if Cancel is pressed, return None)

    The object 'obj' is a container
    
    Supported container types:
    dict, list, tuple, str/unicode or numpy.array
    
    (instantiate a new QApplication if necessary,
    so it can be called directly from the interpreter)
    """
    # Local import
    from spyderlib.widgets.texteditor import TextEditor
    from spyderlib.widgets.dicteditor import DictEditor, ndarray, FakeObject
    from spyderlib.widgets.arrayeditor import ArrayEditor
    from spyderlib.utils.qthelpers import qapplication
    _app = qapplication()

    if isinstance(obj, ndarray) and ndarray is not FakeObject:
        dialog = ArrayEditor()
        if dialog.setup_and_check(obj):
            if dialog.exec_():
                return obj
    elif isinstance(obj, (str, unicode)):
        dialog = TextEditor(obj)
        if dialog.exec_():
            return dialog.get_copy()
    elif isinstance(obj, (dict, tuple, list)):
        dialog = DictEditor(obj)
        if dialog.exec_():
            return dialog.get_copy()
    else:
        raise RuntimeError("Unsupported datatype")


def test():
    """Run object editor test"""
    import datetime
    import numpy as np
    example = {'str': 'kjkj kj k j j kj k jkj',
               'list': [1, 3, 4, 'kjkj', None],
               'dict': {'d': 1, 'a': np.random.rand(10, 10), 'b': [1, 2]},
               'float': 1.2233,
               'array': np.random.rand(10, 10),
               'date': datetime.date(1945, 5, 8),
               'datetime': datetime.datetime(1945, 5, 8),
               }
    print "result:", oedit(example)
    print "result:", oedit(np.random.rand(10, 10))
    print "result:", oedit(oedit.__doc__)
    
if __name__ == "__main__":
    test()
