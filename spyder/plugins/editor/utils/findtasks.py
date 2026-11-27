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
TASKS_PATTERN = (
    r"#\s*(TODO|todo|FIXME|fixme|XXX|xxx|HINT|hint|TIP|tip|@todo|@TODO|"
    r"HACK|hack|BUG|bug|OPTIMIZE|optimize|!!!|\?\?\?)([^#]*)"
)


def find_tasks(source_code, custom_patterns=''):
    """Find tasks in source code (TODO, FIXME, XXX, ...)."""
    results = []
    
    # Default patterns
    default_patterns = (
        r"TODO|todo|FIXME|fixme|XXX|xxx|HINT|hint|TIP|tip|@todo|@TODO|"
        r"HACK|hack|BUG|bug|OPTIMIZE|optimize|!!!|\?\?\?"
    )
    
    # Add custom patterns if provided
    pattern_parts = [default_patterns]
    if custom_patterns.strip():
        # Split by comma, strip whitespace, validate (alphanumeric + underscore)
        custom_list = [p.strip() for p in custom_patterns.split(',')]
        # Filter valid patterns (letters, numbers, underscore only)
        valid_custom = [p for p in custom_list if p and re.match(r'^\w+$', p)]
        if valid_custom:
            pattern_parts.append('|'.join(valid_custom))
    
    full_pattern = '|'.join(pattern_parts)
    TASKS_PATTERN = rf"#\s*({full_pattern})([^#]*)"
    
    for line, text in enumerate(source_code.splitlines()):
        for todo in re.findall(TASKS_PATTERN, text):
            todo_text = (todo[-1].strip(' :').capitalize() if todo[-1]
                         else todo[-2])
            results.append((todo_text, line + 1))
    return results