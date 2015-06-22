# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
spyderlib.utils
===============

Spyder utilities
"""

import os

# Hack to be able to use our own versions of rope and pyflakes,
# included in our Windows installers
if os.name == 'nt':
    import os.path as osp
    import sys
    from spyderlib.baseconfig import get_module_source_path

    dirname = get_module_source_path(__name__)
    if osp.isdir(osp.join(dirname, 'rope')):
        sys.path.insert(0, dirname)
