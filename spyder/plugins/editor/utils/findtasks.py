# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Source code analysis utilities.
"""

import re

# Local import
from spyder.config.base import get_debug_level

DEBUG_EDITOR = get_debug_level() >= 3

# =============================================================================
# Find tasks - TODOs
# =============================================================================
TASKS_PATTERN = r"(^|#)[ ]*(TODO|FIXME|XXX|HINT|TIP|@todo|" \
                r"HACK|BUG|OPTIMIZE|!!!|\?\?\?)([^#]*)"


def find_tasks(source_code):
    """Find tasks in source code (TODO, FIXME, XXX, ...)."""
    results = []
    for line, text in enumerate(source_code.splitlines()):
        for todo in re.findall(TASKS_PATTERN, text):
            todo_text = (todo[-1].strip(' :').capitalize() if todo[-1]
                         else todo[-2])
            results.append((todo_text, line + 1))
    return results
