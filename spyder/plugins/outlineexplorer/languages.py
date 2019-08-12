# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Outline explorer, languages specific implementations."""

# Standard library imports
import re


#===============================================================================
# Class browser
#===============================================================================
class PythonCFM(object):
    """
    Collection of helpers to match functions and classes
    for Python language
    This has to be reimplemented for other languages for the outline explorer
    to be supported (not implemented yet: outline explorer won't be populated
    unless the current script is a Python script)
    """
    def __get_name(self, statmt, text):
        match = re.match(r'[\ ]*%s ([a-zA-Z0-9_]*)[\ ]*[\(|\:]' % statmt, text)
        if match is not None:
            return match.group(1)

    def get_function_name(self, text):
        return self.__get_name('def', text)

    def get_class_name(self, text):
        return self.__get_name('class', text)
