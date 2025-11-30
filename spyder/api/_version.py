# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder API version; minor bumped for additions/deprecations, major for breaks.

The API version should be modified according to the following rules:

* If a module/class/method/function/signal is added, then the minor version
  must be incremented.

* If a module/class/method/function/signal is removed, renamed or changes its
  signature, then the major version must be incremented.

* Whenever possible, deprecation warnings and alerts should be employed to
  inform developers of breaking-compatibility changes in a future API release
  In such cases, the minor version should be increased and once the deprecated
  APIs disappear then the major version should be updated.
"""

VERSION_INFO = (1, 4, 0)

__version__ = '.'.join(map(str, VERSION_INFO))
"""
Spyder API version; minor bumped for additions/deprecations, major for breaks.

The minor version will be incremented when adding or deprecating an API,
(for example, a module, class, method, function, signal, constant, or similar)
while the major version will be incremented for all breaking API changes,
such as removing, renaming or changing the signature of an API.
"""
