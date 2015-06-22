# -*- coding: utf-8 -*-
#
# Copyright © 2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
spyderlib.utils.external
========================

External libraries needed for Spyder to work.
Put here only untouched libraries, else put them in utils.
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
