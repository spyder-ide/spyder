# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
spyder.plugins.remoteclient
===========================

Remote Client Plugin.
"""

# Required version of spyder-remote-services
SPYDER_REMOTE_MIN_VERSION = "1.0.0"
SPYDER_REMOTE_MAX_VERSION = "2.0.0"
SPYDER_REMOTE_VERSION = (
    f">={SPYDER_REMOTE_MIN_VERSION},<{SPYDER_REMOTE_MAX_VERSION}"
)

# jupyter server's extension name for spyder-remote-services
SPYDER_PLUGIN_NAME = "spyder-services"
