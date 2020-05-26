# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Generic object editor dialog
"""

# Standard library imports
from __future__ import print_function

# Third party imports
from qtpy.QtCore import QObject

# Local imports
from spyder.py3compat import is_text_string


class DialogKeeper(QObject):
    def __init__(self):
        QObject.__init__(self)
        self.dialogs = {}
        self.namespace = None

    def set_namespace(self, namespace):
        self.namespace = namespace

    def create_dialog(self, dialog, refname, func):
        self.dialogs[id(dialog)] = dialog, refname, func
        dialog.accepted.connect(
                     lambda eid=id(dialog): self.editor_accepted(eid))
        dialog.rejected.connect(
                     lambda eid=id(dialog): self.editor_rejected(eid))
        dialog.show()
        dialog.activateWindow()
        dialog.raise_()

    def editor_accepted(self, dialog_id):
        dialog, refname, func = self.dialogs[dialog_id]
        self.namespace[refname] = func(dialog)
        self.dialogs.pop(dialog_id)

    def editor_rejected(self, dialog_id):
        self.dialogs.pop(dialog_id)

keeper = DialogKeeper()


def create_dialog(obj, obj_name):
    """Creates the editor dialog and returns a tuple (dialog, func) where func
    is the function to be called with the dialog instance as argument, after
    quitting the dialog box

    The role of this intermediate function is to allow easy monkey-patching.
    (uschmitt suggested this indirection here so that he can monkey patch
    oedit to show eMZed related data)
    """
    # Local import
    from spyder_kernels.utils.nsview import (ndarray, FakeObject,
                                             Image, is_known_type, DataFrame,
                                             Series)
    from spyder.plugins.variableexplorer.widgets.texteditor import TextEditor
    from spyder.plugins.variableexplorer.widgets.arrayeditor import (
            ArrayEditor)
    from spyder.widgets.collectionseditor import CollectionsEditor

    if DataFrame is not FakeObject:
        from spyder.plugins.variableexplorer.widgets.dataframeeditor import (
                DataFrameEditor)

    conv_func = lambda data: data
    readonly = not is_known_type(obj)
    if isinstance(obj, ndarray) and ndarray is not FakeObject:
        dialog = ArrayEditor()
        if not dialog.setup_and_check(obj, title=obj_name,
                                      readonly=readonly):
            return
    elif isinstance(obj, Image) and Image is not FakeObject \
      and ndarray is not FakeObject:
        dialog = ArrayEditor()
        import numpy as np
        data = np.array(obj)
        if not dialog.setup_and_check(data, title=obj_name,
                                      readonly=readonly):
            return
        from spyder.pil_patch import Image
        conv_func = lambda data: Image.fromarray(data, mode=obj.mode)
    elif isinstance(obj, (DataFrame, Series)) and DataFrame is not FakeObject:
        dialog = DataFrameEditor()
        if not dialog.setup_and_check(obj):
            return
    elif is_text_string(obj):
        dialog = TextEditor(obj, title=obj_name, readonly=readonly)
    else:
        dialog = CollectionsEditor()
        dialog.setup(obj, title=obj_name, readonly=readonly)

    def end_func(dialog):
        return conv_func(dialog.get_value())

    return dialog, end_func


def oedit(obj, modal=True, namespace=None):
    """Edit the object 'obj' in a GUI-based editor and return the edited copy
    (if Cancel is pressed, return None)

    The object 'obj' is a container

    Supported container types:
    dict, list, set, tuple, str/unicode or numpy.array

    (instantiate a new QApplication if necessary,
    so it can be called directly from the interpreter)
    """
    # Local import
    from spyder.utils.qthelpers import qapplication
    app = qapplication()

    if modal:
        obj_name = ''
    else:
        assert is_text_string(obj)
        obj_name = obj
        if namespace is None:
            namespace = globals()
        keeper.set_namespace(namespace)
        obj = namespace[obj_name]
        # keep QApplication reference alive in the Python interpreter:
        namespace['__qapp__'] = app

    result = create_dialog(obj, obj_name)
    if result is None:
        return
    dialog, end_func = result

    if modal:
        if dialog.exec_():
            return end_func(dialog)
    else:
        keeper.create_dialog(dialog, obj_name, end_func)
        import os
        if os.name == 'nt':
            app.exec_()


#==============================================================================
# Tests
#==============================================================================
def test():
    """Run object editor test"""
    import datetime
    import numpy as np
    from spyder.pil_patch import Image
    data = np.random.randint(1, 256, size=(100, 100)).astype('uint8')
    image = Image.fromarray(data)
    example = {'str': 'kjkj kj k j j kj k jkj',
               'list': [1, 3, 4, 'kjkj', None],
               'set': {1, 2, 1, 3, None, 'A', 'B', 'C', True, False},
               'dict': {'d': 1, 'a': np.random.rand(10, 10), 'b': [1, 2]},
               'float': 1.2233,
               'array': np.random.rand(10, 10),
               'image': image,
               'date': datetime.date(1945, 5, 8),
               'datetime': datetime.datetime(1945, 5, 8),
               }
    image = oedit(image)
    class Foobar(object):
        def __init__(self):
            self.text = "toto"
    foobar = Foobar()

    print(oedit(foobar))  # spyder: test-skip
    print(oedit(example))  # spyder: test-skip
    print(oedit(np.random.rand(10, 10)))  # spyder: test-skip
    print(oedit(oedit.__doc__))  # spyder: test-skip
    print(example)  # spyder: test-skip


if __name__ == "__main__":
    test()
