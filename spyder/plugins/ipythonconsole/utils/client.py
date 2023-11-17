# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""Kernel Client subclass."""

# Third party imports
from qtpy.QtCore import Signal
from qtconsole.client import QtKernelClient, QtZMQSocketChannel
from traitlets import Type


class SpyderKernelClient(QtKernelClient):
    # Enable receiving messages on control channel.
    # Useful for pdb completion
    control_channel_class = Type(QtZMQSocketChannel)
    sig_spyder_kernel_info = Signal(object)

    def _handle_kernel_info_reply(self, rep):
        """Check spyder-kernels version."""
        super()._handle_kernel_info_reply(rep)
        spyder_kernels_info = rep["content"].get("spyder_kernels_info", None)
        self.sig_spyder_kernel_info.emit(spyder_kernels_info)
