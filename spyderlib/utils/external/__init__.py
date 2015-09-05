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
<<<<<<< HEAD
    from spyderlib.baseconfig import get_module_source_path
=======
    from spyderlib.config.base import get_module_source_path
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f

    dirname = get_module_source_path(__name__)
    if osp.isdir(osp.join(dirname, 'rope')):
        sys.path.insert(0, dirname)
