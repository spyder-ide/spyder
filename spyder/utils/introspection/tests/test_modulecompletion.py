# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for module_completion.py
"""

# Test library imports
import pytest

# Local imports
from spyder.utils.introspection.module_completion import (module_completion, 
                                                          get_preferred_submodules)
from spyder.py3compat import PY3

def test_module_completion():
    """Test module_completion."""
    # Some simple tests.
    # Sort operations are done by the completion widget, so we have to
    # replicate them here.
    # We've chosen to use xml on most tests because it's on the standard
    # library. This way we can ensure they work on all plataforms.
    
    assert sorted(module_completion('import xml.')) == \
        ['xml.dom', 'xml.etree', 'xml.parsers', 'xml.sax']

    assert sorted(module_completion('import xml.d')) ==  ['xml.dom']

    assert module_completion('from xml.etree ') == ['import ']

    assert sorted(module_completion('from xml.etree import '), key=str.lower) ==\
        ['cElementTree', 'ElementInclude', 'ElementPath', 'ElementTree']

    assert module_completion('import sys, zl') == ['zlib']

    s = 'from xml.etree.ElementTree import '
    assert module_completion(s + 'V') == ['VERSION']

    if PY3:
        assert sorted(module_completion(s + 'VERSION, XM')) == \
            ['XML', 'XMLID', 'XMLParser', 'XMLPullParser']
    else:
        assert sorted(module_completion(s + 'VERSION, XM')) == \
            ['XML', 'XMLID', 'XMLParser', 'XMLTreeBuilder']

    assert module_completion(s + '(dum') == ['dump']

    assert module_completion(s + '(dump, Su') == ['SubElement']

    assert 'os.path' in get_preferred_submodules()

if __name__ == "__main__":
    pytest.main()
