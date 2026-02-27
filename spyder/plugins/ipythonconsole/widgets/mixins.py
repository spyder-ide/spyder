# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
IPython Console mixins.
"""

# Standard library imports
import os
import os.path as osp

# Third-party imports
from packaging.version import parse

# Local imports
from spyder.plugins.ipythonconsole.utils.kernel_handler import KernelHandler
from spyder.utils.conda import conda_version, find_conda


class CachedKernelMixin:
    """Cached kernel mixin."""

    def __init__(self):
        super().__init__()
        self._cached_kernel_properties = None
        self._conda_exec = find_conda()

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

        # Don't use cache if requested or needed
        if (
            not cache
            # Conda 25.3.0 changed the way env activation works, which makes
            # activating kernels fail when using cached kernels.
            # Fixes spyder-ide/spyder#24132
            or (
                os.name == "nt"
                and self._conda_exec is not None  # See spyder-ide/spyder#24421
                and "conda" in osp.basename(self._conda_exec)
                and conda_version() in (parse("25.3.0"), parse("25.3.1"))
            )
        ):
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
