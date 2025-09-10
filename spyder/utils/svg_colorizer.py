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

            # Apply the color to all matching elements and remove the class attribute
            # to prevent any class-based styling from overriding our fill color
            for element in elements:
                element.attrib["fill"] = new_color
                element.attrib["style"] = f"fill:{new_color};"
                # Remove the class attribute after setting the fill color
                if "class" in element.attrib:
                    del element.attrib["class"]

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
            # Use XML declaration to ensure proper rendering
            xml_declaration = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
            svg_string = etree.tostring(self.root, encoding="utf-8", pretty_print=True).decode("utf-8")
            # Add XML declaration if not present
            if not svg_string.startswith('<?xml'):
                svg_string = f"{xml_declaration}\n{svg_string}"
            return svg_string
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

    def extract_colored_paths(self, theme_colors):
        """
        Extract SVG paths with their associated colors from the theme.
        
        Instead of modifying the SVG in place, this method returns a structured
        representation of the SVG with paths and their colors for external rendering.
        This approach enables direct rendering of SVG elements with proper colorization
        without modifying the original SVG file.
        
        Parameters
        ----------
        theme_colors : dict
            Dictionary mapping color names (class attributes) to hex color values
            Example: {'ICON_1': '#FF0000', 'ICON_2': '#00FF00'}
            
        Returns
        -------
        dict or None
            A dictionary containing SVG metadata and colored paths:
            {
                'viewbox': str or None,  # SVG viewBox attribute
                'width': int,           # SVG width
                'height': int,          # SVG height
                'paths': [              # List of paths with their colors
                    {
                        'path_data': str,  # The SVG path data
                        'color': str,      # The hex color for this path
                        'attrs': dict      # Original attributes except 'class'
                    },
                    ...
                ]
            }
            Returns None if there was an error
        """
        if self.root is None:
            log.warning("No SVG data to extract paths from.")
            return None
            
        if not theme_colors:
            log.warning("Empty theme colors dictionary provided.")
            return None
            
        try:
            # Get SVG dimensions
            width = int(self.root.get('width', '24'))
            height = int(self.root.get('height', '24'))
            viewbox = self.root.get('viewBox')
            
            # Result structure
            result = {
                'viewbox': viewbox,
                'width': width,
                'height': height,
                'paths': []
            }
            
            # Find all path elements
            paths = self.root.xpath("//svg:path", namespaces=self.SVG_NAMESPACE)
            
            default_color = theme_colors.get('ICON_1', '#FAFAFA')  # Default color if no match
            
            # Process each path
            for path in paths:
                # Get path data
                path_data = path.get('d', '')
                if not path_data:
                    continue
                    
                # Extract class to determine color
                class_attr = path.get('class')
                
                # Determine color based on class
                color = default_color
                if class_attr and class_attr in theme_colors:
                    color = theme_colors[class_attr]
                    
                # Get all attributes except class
                attrs = {k: v for k, v in path.items() if k != 'class'}
                
                # Add to result
                result['paths'].append({
                    'path_data': path_data,
                    'color': color,
                    'attrs': attrs
                })
                
            return result
            
        except Exception as e:
            log.error(f"Error extracting colored paths: {str(e)}")
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
            Example: {'ICON_1': '#FF0000', 'ICON_2': '#00FF00'}

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
        
    @classmethod
    def get_colored_paths(cls, icon_path, theme_colors):
        """
        Class method to extract colored paths from an SVG icon.
        
        This method provides a structured representation of the SVG with paths
        and their colors based on the theme, which can be used for direct
        rendering without modifying the original SVG.
        
        Parameters
        ----------
        icon_path : str
            Path to the SVG file
        theme_colors : dict
            Dictionary mapping color names (class attributes) to hex color values
            Example: {'ICON_1': '#FF0000', 'ICON_2': '#00FF00'}
            
        Returns
        -------
        dict or None
            A dictionary containing SVG metadata and colored paths.
            See extract_colored_paths() for the structure.
        """
        log.debug(f"Extracting colored paths from SVG: {icon_path}")
        
        # Create a new colorizer instance
        icon = cls(icon_path)
        if icon.root is None:
            return None
            
        return icon.extract_colored_paths(theme_colors)
