# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Custom Spyder Outstream class.
"""

from ipykernel.iostream import OutStream


class TTYOutStream(OutStream):
    """Subclass of OutStream that represents a TTY."""

    def __init__(self, session, pub_thread, name, pipe=None, echo=None, *,
                 watchfd=True):
        super().__init__(session, pub_thread, name, pipe,
                         echo=echo, watchfd=watchfd, isatty=True)
