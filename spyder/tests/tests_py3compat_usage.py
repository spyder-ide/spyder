# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------


# Standard library imports
import os
import re


root_path = os.path.realpath(os.path.join(os.getcwd(), 'spyder'))

pattern = re.compile("isinstance\(.*,.*str\)")


def test_dont_use_isinstance_str():
    found = False
    for dir_name, _, file_list in os.walk(root_path):
        for fname in file_list:
            if fname.endswith('.py') and fname != 'py3compat.py':
                file = os.path.join(dir_name, fname)

                for i, line in enumerate(open(file)):
                    for match in re.finditer(pattern, line):
                        print("{}\nline:{}, {}".format(file, i + 1, line))
                        found = True

    assert found == False, ("Don't use builtin isinstance() function,"
                            "use spyder.py3compat.is_text_string() instead")
