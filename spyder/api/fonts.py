# -----------------------------------------------------------------------------
# Copyright (c) 2023- Spyder Project Contributors
#
# Released under the terms of the MIT License
# (see LICENSE.txt in the project root directory for details)
# -----------------------------------------------------------------------------

"""
Helper classes to get and set the fonts used in Spyder.
"""

# Third-party imports
from qtpy.QtGui import QFont

# Local imports
from spyder.config.gui import get_font


class SpyderFontType:
    """
    Font types used in Spyder plugins and the entire application.

    This enum is meant to be used to get the :class:`QFont` object
    corresponding to each type. These are:

    * :attr:`Monospace` is used in the :guilabel:`Editor`,
      :guilabel:`IPython Console` and :guilabel:`History` panes
    * :attr:`Interface` is used by the entire Spyder application
    * :attr:`MonospaceInterface` is used, for instance, by the
      :guilabel:`Variable Explorer` and corresponds to the :attr:`Monospace`
      font resized to look good together with the :attr:`Interface` font.

    .. note::

        The values names in this enum are a result of historical reasons
        that date from Spyder 2 and are not easy to change now.
    """

    Monospace: str = "font"
    """Monospace font, used for code, output and ``literal/verbatim text``.

    Used in, for example, the :guilabel:`Editor`, :guilabel:`IPython Console`
    and :guilabel:`History` panes.
    """

    Interface: str = "app_font"
    """Interface font, used throughout the Spyder application."""

    MonospaceInterface: str = "monospace_app_font"
    """:attr:`Monospace` font resized to work with the :attr:`Interface` font.

    Used, for instance, by the :guilabel:`Variable Explorer` and corresponds
    to the :attr:`Monospace` font resized to look good when used together with
    the :attr:`Interface` font.
    """


class SpyderFontsMixin:
    """Mixin to get the different Spyder font types from our config system."""

    @classmethod
    def get_font(cls, font_type: str, font_size_delta: int = 0) -> QFont:
        """
        Get a font type as a :class:`QFont` object.

        Parameters
        ----------
        font_type: str
            A Spyder font type, one of the :class:`SpyderFontType` enum values.
        font_size_delta: int, optional
            Increase or decrease the default font size by this amount.
            The default is 0.
        """
        return get_font(option=font_type, font_size_delta=font_size_delta)
