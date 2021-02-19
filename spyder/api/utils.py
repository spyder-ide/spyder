# -*- coding: utf-8 -*-
#
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
API utilities.
"""


def get_class_values(cls):
    """
    Get the attribute values for the class enumerations used in our
    API.

    Idea from:
    https://stackoverflow.com/a/17249228/438386
    """
    return [v for (k, v) in cls.__dict__.items() if k[:1] != '_']
