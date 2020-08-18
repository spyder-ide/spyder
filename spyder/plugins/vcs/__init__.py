#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""Spyder VCS Plugin."""

try:
    from .plugin import VCS as PLUGIN_CLASS
except ImportError as ex:
    import traceback
    traceback.print_exc()
else:
    PLUGIN_CLASSES = [PLUGIN_CLASS]
