# -*- coding: utf-8 -*-
#
# Copyright © 2012 Spyder Development team
# Licensed under the terms of the MIT or BSD Licenses 
# (See every file for its license)

"""
spyderlib.utils.inspector
========================

Configuration files for the object inspector rich text mode
"""

import sys
<<<<<<< HEAD
from spyderlib.baseconfig import get_module_source_path
=======
from spyderlib.config.base import get_module_source_path
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
sys.path.insert(0, get_module_source_path(__name__))