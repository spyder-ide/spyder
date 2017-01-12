# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""
Tests for texteditor.py
"""

# Third party imports
import pytest

# Local imports
from spyder.py3compat import PY2
from spyder.widgets.variableexplorer.texteditor import TextEditor


# --- Tests
# -----------------------------------------------------------------------------

def test_texteditor_setup_and_check():
    if PY2:
        import string
        dig_its = string.digits;
        translate_digits = string.maketrans(dig_its,len(dig_its)*' ')
        editor = TextEditor(None)
        assert editor.setup_and_check(translate_digits)
    else:
        assert True

if __name__ == "__main__":
    pytest.main()
