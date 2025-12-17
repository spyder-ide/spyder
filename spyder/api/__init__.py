# -----------------------------------------------------------------------------
# Copyright (c) 2016- Spyder Project Contributors
#
# Released under the terms of the MIT License
# (see LICENSE.txt in the project root directory for details)
# -----------------------------------------------------------------------------

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

VERSION_INFO: tuple[int, int, int] = (2, 0, 0)
"""Tuple form of API version, broken down into ``(major, minor, micro)``."""

__version__: str = str(".".join(map(str, VERSION_INFO)))
"""
Spyder API version; minor bumped for additions/deprecations, major for breaks.

The minor version will be incremented when adding or deprecating an API,
(for example, a module, class, method, function, signal, constant, or similar)
while the major version will be incremented for all breaking API changes,
such as removing, renaming or changing the signature of an API.
"""
