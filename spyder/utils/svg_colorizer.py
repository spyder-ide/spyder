# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Standard library imports
import logging

# Third party imports
from lxml import etree

log = logging.getLogger(__name__)


class SVGColorize:
    """
    A class for modifying SVG files by changing the fill colors of elements
    with specific class attributes.

    This implementation uses lxml for XML parsing and XPath for element selection,
    providing a reliable and maintainable way to manipulate SVG files.

    The main purpose of this class is to allow theme-based colorization of SVG 
    icons in Spyder. Icons can contain elements with special class names that 
    correspond to theme color variables, allowing them to adapt to different UI themes.
    """

    # Define the SVG namespace
    SVG_NAMESPACE = {"svg": "http://www.w3.org/2000/svg"}

    def __init__(self, svg_path):
        """
        Initialize the SVGColorize object with the path to an SVG file.

        Parameters
        ----------
        svg_path : str
            Path to the SVG file to be colorized
        """
        self.tree = None
        self.root = None

        try:
            log.debug(f"Parsing SVG file: {svg_path}")
            self.tree = etree.parse(svg_path)
            self.root = self.tree.getroot()
        except etree.XMLSyntaxError as e:
            log.error(f"Error parsing SVG file {svg_path}: {str(e)}")
        except FileNotFoundError as e:
            log.error(f"SVG file not found {svg_path}: {str(e)}")
        except Exception as e:
            log.error(f"Unexpected error with SVG file {svg_path}: {str(e)}")

    def change_fill_color_by_class(self, class_name, new_color):
        """
        Change the fill color of all elements with the specified class.

        Parameters
        ----------
        class_name : str
            The class attribute value to target (e.g., 'main-color', 'action-color')
        new_color : str
            The new fill color to apply (e.g., '#ff0000', '#44DEB0')

        Returns
        -------
        bool
            True if at least one element was modified, False otherwise
        """
        if self.root is None:
            log.warning("No SVG data to modify.")
            return False

        try:
            # Find all elements with the specified class
            elements = self.root.xpath(
                f"//svg:*[@class='{class_name}']", namespaces=self.SVG_NAMESPACE
            )

            # Apply the color to all matching elements
            for element in elements:
                element.attrib["fill"] = new_color

            if not elements:
                log.debug(f"No elements found with class '{class_name}'")

            return len(elements) > 0
        except Exception as e:
            log.error(
                f"Error changing fill color for class '{class_name}': {str(e)}")
            return False

    def save_to_string(self):
        """
        Convert the modified SVG to a string.

        Returns
        -------
        str or None
            The SVG as a string, or None if there was an error
        """
        if self.root is None:
            log.warning("No SVG data to save to string.")
            return None

        try:
            return etree.tostring(self.root, encoding="utf-8").decode("utf-8")
        except Exception as e:
            log.error(f"Error converting SVG to string: {str(e)}")
            return None

    def save_to_file(self, output_path):
        """
        Save the modified SVG to a file.

        Parameters
        ----------
        output_path : str
            Path where the modified SVG will be saved

        Returns
        -------
        bool
            True if file was saved successfully, False otherwise
        """
        if self.tree is None:
            log.warning("No SVG data to save to file.")
            return False

        if not output_path:
            log.warning("Empty output path provided.")
            return False

        try:
            self.tree.write(output_path, pretty_print=True, encoding="utf-8")
            log.debug(f"SVG file saved to {output_path}")
            return True
        except Exception as e:
            log.error(f"Error saving SVG to file {output_path}: {str(e)}")
            return False

    def colorize_from_theme(self, theme_colors):
        """
        Apply colors from theme configuration to SVG elements.

        This method looks for elements with class attributes matching keys in the 
        theme_colors dictionary and applies the corresponding color values to those elements.

        Parameters
        ----------
        theme_colors : dict
            Dictionary mapping color names (class attributes) to hex color values
            Example: {'main-color': '#FF0000', 'action-color': '#00FF00'}

        Returns
        -------
        str or None
            The colorized SVG as a string, or None if there was an error
        """
        if self.root is None:
            log.warning("No SVG data to colorize from theme.")
            return None

        if not theme_colors:
            log.warning("Empty theme colors dictionary provided.")
            return None

        try:
            # Apply each color from the theme dictionary to elements with matching class
            modified = False
            for color_name, color_value in theme_colors.items():
                if self.change_fill_color_by_class(color_name, color_value):
                    modified = True

            if not modified:
                log.debug("No elements were modified during colorization")

            return self.save_to_string()
        except Exception as e:
            log.error(f"Error applying theme colors: {str(e)}")
            return None

    @classmethod
    def colorize_icon_from_theme(cls, icon_path, theme_colors):
        """
        Class method to colorize an SVG icon using theme colors.

        This is the main entry point for colorizing SVG icons in Spyder.
        It creates a new SVGColorize instance, applies the theme colors,
        and returns the colorized SVG as a string.

        Parameters
        ----------
        icon_path : str
            Path to the SVG file
        theme_colors : dict
            Dictionary mapping color names (class attributes) to hex color values
            Example: {'main-color': '#FF0000', 'action-color': '#00FF00'}

        Returns
        -------
        str or None
            The colorized SVG as a string, or None if there was an error
        """
        log.debug(f"Colorizing SVG icon: {icon_path}")

        # Create a new colorizer instance
        icon = cls(icon_path)
        if icon.root is None:
            return None

        return icon.colorize_from_theme(theme_colors)
