# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

import os
import re
import codecs

import pytest

root_path = os.path.realpath(os.path.join(os.getcwd(), 'spyder'))


@pytest.mark.parametrize("pattern,exclude_patterns,message", [
    (r"isinstance\(.*,.*str\)", ['py3compat.py', 'example_latin1.py'],
     ("Don't use builtin isinstance() function,"
      "use spyder.py3compat.is_text_string() instead")),

    (r"^[\s\#]*\bprint\(((?!file=).)*\)", ['.*test.*', 'example.py',
                                           'example_latin1.py', 'binaryornot'],
     ("Don't use the print() function; ",
      "for debugging, use logging module instead")),

    (r"^[\s\#]*\bprint\s+(?!>>)((?!#).)*", ['.*test.*', 'example_latin1.py'],
     ("Don't use print statements; ",
      "for debugging, use the logging module instead.")),
])
def test_dont_use(pattern, exclude_patterns, message):
    """
    This test is used for discouraged using of some expresions that could
    introduce errors, and encourage use spyder function instead.

    If you want to skip some line from this test just use:
        # spyder: test-skip
    """
    pattern = re.compile(pattern + r"((?!# spyder: test-skip)\s)*$")

    found = 0
    for dir_name, _, file_list in os.walk(root_path):
        for fname in file_list:
            exclude = any([re.search(ex, fname) for ex in exclude_patterns])
            exclude = exclude or any([re.search(ex, dir_name) for ex in exclude_patterns])

            if fname.endswith('.py') and not exclude:
                file = os.path.join(dir_name, fname)

                with codecs.open(file, encoding="utf-8") as f:
                    for i, line in enumerate(f):
                        for match in re.finditer(pattern, line):
                            print("{}\nline:{}, {}".format(file, i + 1, line))
                            found += 1

    assert found == 0, "{}\n{} errors found".format(message, found)
