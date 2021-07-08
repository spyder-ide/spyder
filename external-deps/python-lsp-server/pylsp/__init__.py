# Copyright 2017-2020 Palantir Technologies, Inc.
# Copyright 2021- Python Language Server Contributors.

import os
import pluggy
from ._version import __version__

PYLSP = 'pylsp'
IS_WIN = os.name == 'nt'

hookspec = pluggy.HookspecMarker(PYLSP)
hookimpl = pluggy.HookimplMarker(PYLSP)

__all__ = [__version__]
