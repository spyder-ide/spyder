# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder API Version.

The API version should be modified according to the following rules:

1. If a module/class/method/function/signal is added, then the minor version
   must be increased.

2. If a module/class/method/function/signal is removed, renamed or changes its
   signature, then the major version must be increased.

3. Whenever possible, deprecation marks and alerts should be employed in
   order to inform developers of breaking-compatibility changes in a
   future API release. In such case, the minor version should be increased
   and once the deprecated APIs disappear then the major version should be
   updated.
"""

VERSION_INFO = (1, 3, 0)
__version__ = '.'.join(map(str, VERSION_INFO))
