# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Shell helpers"""

import re

def get_error_match(text):
    """Return error match"""
    return re.match(r'  File "(.*)", line (\d*)', text)
