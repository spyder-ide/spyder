# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
spyder.plugins.remoteclient.widgets
===================================

Widgets for the Remote Client plugin.
"""


class AuthenticationMethod:
    """Enum for the different authentication methods we support."""

    Password = "password_login"
    KeyFile = "keyfile_login"
    ConfigFile = "configfile_login"
