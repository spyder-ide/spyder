# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
IPython Console mixins.
"""

# Local imports
from spyder.plugins.ipythonconsole.utils.kernel_handler import KernelHandler


class CachedKernelMixin:
    """Cached kernel mixin."""

    def __init__(self):
        super().__init__()
        self._cached_kernel_properties = None

    def close_cached_kernel(self):
        """Close the cached kernel."""
        if self._cached_kernel_properties is None:
            return
        kernel = self._cached_kernel_properties[-1]
        kernel.close(now=True)
        self._cached_kernel_properties = None

    def check_cached_kernel_spec(self, kernel_spec):
        """Test if kernel_spec corresponds to the cached kernel_spec."""
        if self._cached_kernel_properties is None:
            return False
        (
            cached_spec,
            cached_env,
            cached_argv,
            _,
        ) = self._cached_kernel_properties

        # Call interrupt_mode so the dict will be the same
        kernel_spec.interrupt_mode
        cached_spec.interrupt_mode

        if "PYTEST_CURRENT_TEST" in cached_env:
            # Make tests faster by using cached kernels
            # hopefully the kernel will never use PYTEST_CURRENT_TEST
            cached_env["PYTEST_CURRENT_TEST"] = (
                kernel_spec.env["PYTEST_CURRENT_TEST"])
        return (
            cached_spec.__dict__ == kernel_spec.__dict__
            and kernel_spec.argv == cached_argv
            and kernel_spec.env == cached_env
        )

    def get_cached_kernel(self, kernel_spec, cache=True):
        """Get a new kernel, and cache one for next time."""
        # Cache another kernel for next time.
        new_kernel_handler = KernelHandler.new_from_spec(kernel_spec)

        if not cache:
            # remove/don't use cache if requested
            self.close_cached_kernel()
            return new_kernel_handler

        # Check cached kernel has the same configuration as is being asked or
        # it crashed.
        cached_kernel_handler = None
        if self._cached_kernel_properties is not None:
            cached_kernel_handler = self._cached_kernel_properties[-1]
            if (
                not self.check_cached_kernel_spec(kernel_spec)
                or cached_kernel_handler._init_stderr
            ):
                # Close the kernel
                self.close_cached_kernel()
                cached_kernel_handler = None

        # Cache the new kernel
        self._cached_kernel_properties = (
            kernel_spec,
            kernel_spec.env,
            kernel_spec.argv,
            new_kernel_handler,
        )

        if cached_kernel_handler is None:
            return KernelHandler.new_from_spec(kernel_spec)

        return cached_kernel_handler
