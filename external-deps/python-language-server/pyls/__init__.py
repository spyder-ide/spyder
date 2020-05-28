# Copyright 2017 Palantir Technologies, Inc.
import os
import sys
import pluggy
from ._version import get_versions

if sys.version_info[0] < 3:
    from future.standard_library import install_aliases
    install_aliases()

__version__ = get_versions()['version']
del get_versions

PYLS = 'pyls'

hookspec = pluggy.HookspecMarker(PYLS)
hookimpl = pluggy.HookimplMarker(PYLS)

IS_WIN = os.name == 'nt'
