# Copyright 2017-2020 Palantir Technologies, Inc.
# Copyright 2021- Python Language Server Contributors.

"""pytest configuration"""

import logging

from pylsp.__main__ import LOG_FORMAT

logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)


pytest_plugins = ["test.fixtures"]
