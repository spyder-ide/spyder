# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
spyder.plugins.remoteclient.api
===============================

Remote Client Plugin API.
"""

from spyder.plugins.remoteclient.api.modules import *  # noqa

# ---- Constants
# -----------------------------------------------------------------------------

# Max number of logged messages from the client that will be saved.
MAX_CLIENT_MESSAGES = 1000

class RemoteClientActions:
    ManageConnections = "manage connections"
