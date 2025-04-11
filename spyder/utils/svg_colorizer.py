#!/usr/bin/env python

import logging

log = logging.getLogger(__name__)

# Import the lxml library for XML parsing.
try:
    from lxml import etree
    log.debug("running svg_colorizer with lxml.etree")
except ImportError:
    import xml.etree.ElementTree as etree
    log.debug("running svg_colorizer with Python's xml.etree.ElementTree")

# Methods for colorization.
class SVGColorize:
    """
    A class for modifying SVG files by changing the fill colors of elements
    with specific class attributes.

    This implementation uses lxml for XML parsing and XPath for element selection,
    providing a reliable and maintainable way to manipulate SVG files.
    """

    def __init__(self, svg_path):
        """
        Initialize the SVGColorize object with the path to an SVG file.

        Parameters
        ----------
        svg_path : str
            Path to the SVG file to be colorized
        """
        try:
            self.tree = etree.parse(svg_path)
            self.root = self.tree.getroot()
        except etree.XMLSyntaxError as e:
            print(f"Error parsing SVG file: {e}")
            self.tree = None
            self.root = None

    def change_fill_color_by_class(self, class_name, new_color):
        """
        Change the fill color of all elements with the specified class.

        Parameters
        ----------
        class_name : str
            The class attribute value to target (e.g., 'primary', 'secondary')
        new_color : str
            The new fill color to apply (e.g., '#ff0000', '#44DEB0')
        """
        if self.root is None:
            print("No SVG data to modify.")
            return
        ns = {"svg": "http://www.w3.org/2000/svg"}
        elements = self.root.xpath(f"//svg:*[@class='{class_name}']", namespaces=ns)
        for element in elements:
            element.attrib["fill"] = new_color

    def save_to_string(self):
        """
        Convert the modified SVG to a string.

        Returns
        -------
        str or None
            The SVG as a string, or None if there was an error
        """
        if self.root is None:
            print("No SVG data to save.")
            return None
        return etree.tostring(self.root).decode()

    def save_to_file(self, output_path):
        """
        Save the modified SVG to a file.

        Parameters
        ----------
        output_path : str
            Path where the modified SVG will be saved
        """
        if self.tree is None:
            print("No SVG data to save.")
            return
        if output_path is None:
            print("Empty path.")
            return
        self.tree.write(output_path, pretty_print=True)
        
    def colorize(self, color_primary, color_secondary="", color_tertiary=""):
        """
        Apply colors to SVG elements with specific class attributes.
        
        Parameters
        ----------
        color_primary : str
            Color to apply to elements with class="primary"
        color_secondary : str, optional
            Color to apply to elements with class="secondary"
        color_tertiary : str, optional
            Color to apply to elements with class="tertiary"
            
        Returns
        -------
        str or None
            The colorized SVG as a string, or None if there was an error
        """
        self.change_fill_color_by_class("primary", color_primary)
        
        if color_secondary:
            self.change_fill_color_by_class("secondary", color_secondary)
            
        if color_tertiary:
            self.change_fill_color_by_class("tertiary", color_tertiary)
            
        return self.save_to_string()
        
    @classmethod
    def colorize_icon(cls, icon_path, color_primary, color_secondary="", color_tertiary=""):
        """
        Class method to colorize an SVG icon in a single call.
        
        Parameters
        ----------
        icon_path : str
            Path to the SVG file
        color_primary : str
            Color to apply to elements with class="primary"
        color_secondary : str, optional
            Color to apply to elements with class="secondary"
        color_tertiary : str, optional
            Color to apply to elements with class="tertiary"
            
        Returns
        -------
        str or None
            The colorized SVG as a string, or None if there was an error
        """
        icon = cls(icon_path)
        return icon.colorize(color_primary, color_secondary, color_tertiary)

    def colorize_from_theme(self, theme_colors):
        """
        Apply colors from theme configuration to SVG elements.
        
        Parameters
        ----------
        theme_colors : dict
            Dictionary mapping semantic color names to hex color values
            
        Returns
        -------
        str or None
            The colorized SVG as a string, or None if there was an error
        """
        for color_name, color_value in theme_colors.items():
            self.change_fill_color_by_class(color_name, color_value)
            
        return self.save_to_string()
        
    @classmethod
    def colorize_icon_from_theme(cls, icon_path, theme_colors):
        """
        Class method to colorize an SVG icon using theme colors.
        
        Parameters
        ----------
        icon_path : str
            Path to the SVG file
        theme_colors : dict
            Dictionary mapping semantic color names to hex color values
            
        Returns
        -------
        str or None
            The colorized SVG as a string, or None if there was an error
        """
        icon = cls(icon_path)
        return icon.colorize_from_theme(theme_colors)
