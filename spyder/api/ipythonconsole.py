# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""The API for Spyder's IPython Console."""

from spyder.plugins.ipythonconsole.utils.messagehandler import SpyderMessageHandler

class IPythonAPIMixin(object):
    """Support communication between SpyderPluginWidget and the IPython kernels."""

    def __init__(self, main=None):
        super(IPythonAPIMixin, self).__init__(main)
        self.main = main
        self.ipyconsole = main.ipyconsole

    def register_message_handler(self, name, func):
        """
        Register a message handler for Spyder-IPython kernel communication.

        All Spyder messages with ``spyder_msg_type==name``
        will be handled by the given function.
        """
        SpyderMessageHandler.registered_handlers[name] = func

    def set_kernelSpec(self, kernelSpec):
        """Use a different kernel spec for the spyder kernels."""
        self.ipyconsole._kernelSpec = kernelSpec
