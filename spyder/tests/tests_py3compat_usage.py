# -*- coding: utf-8 -*-

import os
import re

import pytest

root_path = os.path.realpath(os.path.join(os.getcwd(), 'spyder'))


@pytest.mark.parametrize("pattern,exclude_patterns,message", [
    ("isinstance\(.*,.*str\)", ['py3compat.py'],
     ("Don't use builtin isinstance() function,"
      "use spyder.py3compat.is_text_string() instead")),

    (r"(?<!_)print\(.*\)", ['.*test.*'],
     ("Don't use print functions, ",
      "for debuging you could use debug_print instead")),
])
def test_dont_use(pattern, exclude_patterns, message):
    pattern = re.compile(pattern)

    found = 0
    for dir_name, _, file_list in os.walk(root_path):
        for fname in file_list:
            exclude = any([re.search(ex, fname) for ex in exclude_patterns])

            if fname.endswith('.py') and not exclude:
                file = os.path.join(dir_name, fname)

                for i, line in enumerate(open(file)):
                    for match in re.finditer(pattern, line):
                        print("{}\nline:{}, {}".format(file, i + 1, line))
                        found += 1

    assert found == 0, "{}\n{} errors found".format(message, found)
