# Copyright 2017-2020 Palantir Technologies, Inc.
# Copyright 2021- Python Language Server Contributors.

import sys
import pytest
from pylsp import IS_WIN

IS_PY3 = sys.version_info.major == 3

unix_only = pytest.mark.skipif(IS_WIN, reason="Unix only")
windows_only = pytest.mark.skipif(not IS_WIN, reason="Windows only")
py3_only = pytest.mark.skipif(not IS_PY3, reason="Python3 only")
py2_only = pytest.mark.skipif(IS_PY3, reason="Python2 only")
