# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
PEP 810 lazy-import policy for Spyder.

Assign ``__lazy_modules__ = LAZY_IMPORTS`` in a module to defer its imports of
the heavy third-party packages listed in ``_LAZY``. Only those packages are
made lazy, so modules with import-time side effects (Qt bindings, zmq,
``spyder.requirements``) always stay eager. Ignored on Python < 3.15.
"""

_LAZY = frozenset({
    "chardet",    # encoding detection; only needed when reading files
    "docutils",   # rich help rendering
    "jinja2",     # rich help / templating
    "keyring",    # credential storage (pulls heavy jaraco.* deps)
    "lxml",       # SVG colorizing
    "nbconvert",  # notebook export (pulls bs4/pandoc)
    "requests",   # network access
    "sphinx",     # rich help rendering
})


class _LazyImports:
    """``__lazy_modules__`` policy object: ``name in LAZY_IMPORTS`` is True for
    packages that are safe to defer (matched by top-level package name)."""

    __slots__ = ()

    def __contains__(self, name):
        return name.partition(".")[0] in _LAZY


LAZY_IMPORTS = _LazyImports()
