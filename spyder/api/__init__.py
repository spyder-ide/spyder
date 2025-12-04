# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Base classes, mixins and widgets for creating plugins to extend Spyder.

This API should be considered production-ready as of Spyder 6.0.
The API version is modified according to the following rules:

* If a module/class/method/function/signal is added, then the minor version
  will be incremented.

* If a module/class/method/function/signal is removed, renamed or changes its
  signature, then the major version will be incremented.

* Whenever possible, deprecation warnings and alerts will be employed to
  inform developers of breaking-compatibility changes in a future API release
  In such cases, the minor version will be increased and once the deprecated
  APIs are removed then the major version will be updated.
"""

from packaging.version import parse

version_info = (1, 4, 0)

__version__: str = str(parse('.'.join(map(str, version_info))))
"""
Spyder API version; minor bumped for additions/deprecations, major for breaks.

The minor version will be incremented when adding or deprecating an API,
(for example, a module, class, method, function, signal, constant, or similar)
while the major version will be incremented for all breaking API changes,
such as removing, renaming or changing the signature of an API.
"""
