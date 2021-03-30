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
import qstylizer
from qstylizer.parser import parse as parse_stylesheet

# Local imports
from spyder.utils.palette import QStylePalette


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

            # Add our customizations
            self._customize_stylesheet()

            # Save stylesheet as a string for quick access
            self._stylesheet_as_string = self._stylesheet.toString()

    def _customize_stylesheet(self):
        """Apply our customizations to the stylesheet."""
        css = self._stylesheet

        # Remove padding and border for QStackedWidget (used in Plots
        # and the Variable Explorer)
        css['QStackedWidget'].setValues(
            border='0px',
            padding='0px',
        )

        # Remove margin when pressing buttons
        css["QToolButton:pressed"].setValues(
            margin='0px'
        )

        # Remove padding when pressing main menus
        css['QMenuBar::item:pressed'].setValues(
            padding='0px'
        )

        # Remove border and padding for main toolbar
        css.QToolBar.setValues(
            borderBottom='0px',
            padding='0px',
            spacing='0px',
        )

    def __str__(self):
        return self.as_string()


# =============================================================================
# ---- Other stylesheets
# =============================================================================
class ApplicationToolbarStylesheet:
    """Stylesheet for application toolbars."""

    BUTTON_WIDTH = '2.8em'
    BUTTON_HEIGHT = '2.8em'
    BUTTON_MARGIN_LEFT = '0.25em'
    BUTTON_MARGIN_RIGHT = '0.25em'

    def __init__(self):
        self._stylesheet = None
        self._get_stylesheet()

    def _get_stylesheet(self):
        """Get the stylesheet as a Qstylizer StyleSheet object."""
        if self._stylesheet is None:
            css = qstylizer.style.StyleSheet()

            css.QToolButton.setValues(
                width=self.BUTTON_WIDTH,
                height=self.BUTTON_HEIGHT,
                marginLeft=self.BUTTON_MARGIN_RIGHT,
                marginRight=self.BUTTON_MARGIN_RIGHT,
                border='0px',
                padding='0px',
            )

            css.QToolBar.setValues(
                backgroundColor=QStylePalette.COLOR_BACKGROUND_4
            )

            self._stylesheet = css

    def __str__(self):
        return self._stylesheet.toString()


# =============================================================================
# ---- Exported constants
# =============================================================================
APP_STYLESHEET = AppStylesheet()
APP_TOOLBAR_STYLESHEET = ApplicationToolbarStylesheet()
