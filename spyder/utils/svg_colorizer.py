# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Standard library imports
import logging

# Third party imports
from lxml import etree
from qtpy.QtCore import QByteArray
from qtpy.QtGui import QColor, QPainter, QPixmap
from qtpy.QtSvg import QSvgRenderer

log = logging.getLogger(__name__)


class SVGColorize:
    """
    A class for modifying SVG files by changing the fill colors of elements
    with specific class attributes.

    This implementation uses lxml for XML parsing and XPath for element
    selection, providing a reliable and maintainable way to manipulate SVG
    files.

    The main purpose of this class is to allow theme-based colorization of SVG 
    icons in Spyder. Icons can contain elements with special class names that 
    correspond to theme color variables, allowing them to adapt to different UI
    themes.
    """

    # Define the SVG namespace
    SVG_NAMESPACE = {"svg": "http://www.w3.org/2000/svg"}

    def __init__(self, svg_path):
        """
        Initialize the instance with the path to an SVG file.

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

    def _find_elements_by_class(self, class_name):
        """
        Find all SVG elements with the specified class.

        Parameters
        ----------
        class_name : str
            The class attribute value to search for

        Returns
        -------
        list
            List of elements with the specified class
        """
        if self.root is None:
            return []

        try:
            return self.root.xpath(
                f"//svg:*[@class='{class_name}']", 
                namespaces=self.SVG_NAMESPACE
            )
        except Exception as e:
            log.error(
                f"Error finding elements with class '{class_name}': {str(e)}"
            )
            return []

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
            xml_declaration = (
                '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
            )
            svg_string = etree.tostring(
                self.root, encoding="utf-8", pretty_print=True
            ).decode("utf-8")

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

    def extract_colored_paths(self, theme_colors):
        """
        Extract SVG paths with their associated colors from the theme.

        Instead of modifying the SVG in place, this method returns a structured
        representation of the SVG with paths and their colors for external
        rendering. This approach enables direct rendering of SVG elements with
        proper colorization without modifying the original SVG file.

        Parameters
        ----------
        theme_colors : dict
            Dictionary mapping color names (class attributes) to hex color
            values. Example: {'ICON_1': '#FF0000', 'ICON_2': '#00FF00'}

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
            width = int(float(self.root.get('width', '24')))
            height = int(float(self.root.get('height', '24')))
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

            # Default color if no match
            default_color = theme_colors.get('ICON_1', '#FAFAFA')

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
    def get_colored_paths(cls, icon_path, theme_colors, debug=False):
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
            Dictionary mapping color names (class attributes) to hex color
            values. Example: {'ICON_1': '#FF0000', 'ICON_2': '#00FF00'}
            
        Returns
        -------
        dict or None
            A dictionary containing SVG metadata and colored paths.
            See extract_colored_paths for the structure.
        """
        if debug:
            log.debug(f"Extracting colored paths from SVG: {icon_path}")

        # Create a new colorizer instance
        icon = cls(icon_path)
        if icon.root is None:
            return None

        return icon.extract_colored_paths(theme_colors)
    
    def render_colored_svg(self, paths, size, width, height, viewbox=None):
        """
        Render colored SVG paths to a pixmap.

        Parameters
        ----------
        paths : list
            List of path dictionaries with 'path_data' and 'color'
        size : int
            Size of the pixmap to create (used as the maximum dimension)
        width : int
            Original SVG width
        height : int
            Original SVG height
        viewbox : str or None
            SVG viewBox attribute if available

        Returns
        -------
        QPixmap
            A pixmap with all paths rendered with their respective colors
        """

        # Calculate proper dimensions preserving aspect ratio
        aspect_ratio = width / height
        if width > height:
            # Width is larger, use size as width
            pixmap_width = size
            pixmap_height = int(size / aspect_ratio)
        else:
            # Height is larger or equal, use size as height
            pixmap_height = size
            pixmap_width = int(size * aspect_ratio)

        # Create transparent pixmap for the icon with proper aspect ratio
        pixmap = QPixmap(pixmap_width, pixmap_height)
        pixmap.fill(QColor(0, 0, 0, 0))  # Transparent

        # Painter for compositing all parts
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Process each path
        for path_data in paths:
            path_d = path_data.get('path_data', '')
            color = QColor(path_data.get('color', '#FAFAFA'))

            if not path_d:
                continue

            # Create a temporary SVG with just this path
            svg_template = (
                f'<svg xmlns="http://www.w3.org/2000/svg" '
                f'width="{width}" height="{height}"'
            )

            # Add viewBox if available
            if viewbox:
                svg_template += f' viewBox="{viewbox}"'

            svg_template += f'><path d="{path_d}"/></svg>'

            # Render the path and apply color
            temp_bytes = QByteArray(svg_template.encode('utf-8'))
            temp_pixmap = QPixmap(pixmap_width, pixmap_height)
            temp_pixmap.fill(QColor(0, 0, 0, 0))  # Transparent

            # Render the path
            temp_renderer = QSvgRenderer(temp_bytes)
            temp_painter = QPainter(temp_pixmap)
            temp_renderer.render(temp_painter)
            temp_painter.end()

            # Apply color to the path
            temp_painter = QPainter(temp_pixmap)
            temp_painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
            temp_painter.fillRect(temp_pixmap.rect(), color)
            temp_painter.end()

            # Composite this path onto the main pixmap
            painter.drawPixmap(0, 0, temp_pixmap)

        # Finish compositing
        painter.end()
        return pixmap
