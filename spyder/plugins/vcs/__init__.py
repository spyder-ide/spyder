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
except ImportError:
    pass
else:
    PLUGIN_CLASSES = [PLUGIN_CLASS]
