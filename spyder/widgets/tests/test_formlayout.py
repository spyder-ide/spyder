# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for formlayout.py
"""

# Standard library imports
from __future__ import print_function
import datetime
import os

# Third party imports
from qtpy.QtWidgets import QApplication

# Test library imports
import pytest

# Local imports
from spyder.widgets.formlayout import FormDialog

def fedit(data, title="", comment="", icon=None, parent=None, apply=None):
    """
    Create form dialog and return result
    (if Cancel button is pressed, return None)
    
    data: datalist, datagroup
    title: string
    comment: string
    icon: QIcon instance
    parent: parent QWidget
    apply: apply callback (function)
    
    datalist: list/tuple of (field_name, field_value)
    datagroup: list/tuple of (datalist *or* datagroup, title, comment)
    
    -> one field for each member of a datalist
    -> one tab for each member of a top-level datagroup
    -> one page (of a multipage widget, each page can be selected with a combo
       box) for each member of a datagroup inside a datagroup
       
    Supported types for field_value:
      - int, float, str, unicode, bool
      - colors: in Qt-compatible text form, i.e. in hex format or name (red,...)
                (automatically detected from a string)
      - list/tuple:
          * the first element will be the selected index (or value)
          * the other elements can be couples (key, value) or only values
    """
    # Create a QApplication instance if no instance currently exists
    # (e.g. if the module is used directly from the interpreter)
    test_travis = os.environ.get('TEST_CI_WIDGETS', None)
    if test_travis is not None:
        from spyder.utils.qthelpers import qapplication
        _app = qapplication(test_time=1)
    elif QApplication.startingUp():
        _app = QApplication([])

    dialog = FormDialog(data, title, comment, icon, parent, apply)
    if dialog.exec_():
        return dialog.get()

def create_datalist_example():
    return [('str', 'this is a string'),
            ('str', """this is a 
            MULTILINE
            string"""),
            ('list', [0, '1', '3', '4']),
            ('list2', ['--', ('none', 'None'), ('--', 'Dashed'),
                       ('-.', 'DashDot'), ('-', 'Solid'),
                       ('steps', 'Steps'), (':', 'Dotted')]),
            ('float', 1.2),
            (None, 'Other:'),
            ('int', 12),
            ('font', ('Arial', 10, False, True)),
            ('color', '#123409'),
            ('bool', True),
            ('date', datetime.date(2010, 10, 10)),
            ('datetime', datetime.datetime(2010, 10, 10)),
            ]
        
def create_datagroup_example():
    datalist = create_datalist_example()
    return ((datalist, "Category 1", "Category 1 comment"),
            (datalist, "Category 2", "Category 2 comment"),
            (datalist, "Category 3", "Category 3 comment"))
    
#--------- datalist example
def apply_test(data):
    datalist = create_datalist_example()
    print("data:", data)
    print("result:", fedit(datalist, title="Example",
                           comment="This is just an <b>example</b>.",
                           apply=apply_test))
    
    #--------- datagroup example
    datagroup = create_datagroup_example()
    print("result:", fedit(datagroup, "Global title"))
    
    #--------- datagroup inside a datagroup example
    datalist = create_datalist_example()
    datagroup = create_datagroup_example()
    print("result:", fedit(((datagroup, "Title 1", "Tab 1 comment"),
                            (datalist, "Title 2", "Tab 2 comment"),
                            (datalist, "Title 3", "Tab 3 comment")),
                            "Global title"))

if __name__ == "__main__":
    pytest.main()
