# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""The API for Spyder's IPython Console."""

from qtconsole.base_frontend_mixin import BaseFrontendMixin
import spyder.plugins.ipythonconsole.plugin as ipyplugin


class IPythonAPIMixin(object):
    """Support communication between SpyderPluginWidget and IPython kernels."""
    message_handler_class = BaseFrontendMixin

    def __init__(self, main, register_handler=False):
        super(IPythonAPIMixin, self).__init__(main)
        self.ipyconsole = main.ipyconsole
        if register_handler:
            self.ipyconsole._handler_creators.append(self)
        self._handlers = []

    def create_handler(self, kernel_manager, kernel_client):
        handler = self.message_handler_class()
        handler.kernel_manager = kernel_manager
        handler.kernel_client = kernel_client
        self._handlers.append(handler)

    def set_kernelSpec(self, kernelSpec):
        """Use a different kernel spec for the spyder kernels."""
        ipyplugin.SpyderKernelSpec = kernelSpec
