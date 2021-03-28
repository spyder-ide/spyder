# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Stylesheet used in the entire application."""

# Standard library imports
import copy

# Third-party imports
import qdarkstyle
from qstylizer.parser import parse as parse_stylesheet


# =============================================================================
# ---- Application stylesheet
# =============================================================================
class AppStylesheet:
    """
    Class to build and access the stylesheet we use in the entire
    application.
    """

    def __init__(self):
        self._stylesheet = None
        self._stylesheet_as_string = None
        self._get_stylesheet()

    def as_string(self):
        """Return the stylesheet as a string."""
        return self._stylesheet_as_string

    def as_object(self):
        """
        Return the stylesheet as an object.

        This allows us to be modified for specific widgets.
        """
        return copy.deepcopy(self._stylesheet)

    def _get_stylesheet(self):
        """
        Get the stylesheet as a Qstylizer StyleSheet object.

        This takes the stylesheet from QDarkstyle and applies our
        customizations to it.
        """
        if self._stylesheet is None:
            stylesheet = qdarkstyle.load_stylesheet()
            self._stylesheet = parse_stylesheet(stylesheet)
            self._stylesheet_as_string = self._stylesheet.toString()

    def __str__(self):
        return self.as_string()


# =============================================================================
# ---- Exported constants
# =============================================================================
APP_STYLESHEET = AppStylesheet()
