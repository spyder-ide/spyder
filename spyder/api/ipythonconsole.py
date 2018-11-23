# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
This module contains the ipython console API
"""

from spyder.plugins.ipythonconsole.utils.messagehandler import SpyderMessageHandler

class IPythonAPIMixin:
    """Mixin class for SpyderPluginWidget to support communication between the widget and the
ipython kernels"""

    def __init__(self, main=None):
        super(IPythonAPIMixin, self).__init__(main)
        self.main = main
        self.ipyconsole = main.ipyconsole

    def registerMessageHandler(self, name, func):
        """Register a message handler for communication between the ipython kernel and
the spyder app. All spyder messages with spyder_msg_type=name will be handled by the given function"""
        SpyderMessageHandler.registered_handlers[name] = func

    def setKernelSpec(self, kernelSpec):
        """Use a different kernel spec for the spyder kernels."""
        self.ipyconsole._kernelSpec = kernelSpec
