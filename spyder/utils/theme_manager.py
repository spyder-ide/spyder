# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Theme manager for Spyder's new theming system.
"""

# Standard library imports
import sys
from pathlib import Path

# Local imports
from spyder.config.gui import is_dark_interface

# Theme configuration
SELECTED_THEME = "solarized"  # Hardcoded theme selection for now

class ThemeManager:
    """Manager for Spyder's new theming system."""
    
    def __init__(self):
        self._themes_dir = Path(__file__).parent / "themes"
        self._current_theme = None
        self._current_palette = None
        self._current_stylesheet = None
        self._current_theme_module = None  # Store the loaded theme module
        self._loaded_resource_modules = {}  # Keep references to resource modules
        self._current_interface_mode = None  # Track current interface mode

        # Mapping from old syntax settings keys to new palette attributes
        self._syntax_setting_mapping = {
            'background': 'EDITOR_BACKGROUND',
            'currentline': 'EDITOR_CURRENTLINE',
            'currentcell': 'EDITOR_CURRENTCELL',
            'occurrence': 'EDITOR_OCCURRENCE',
            'ctrlclick': 'EDITOR_CTRLCLICK',
            'sideareas': 'EDITOR_SIDEAREAS',
            'matched_p': 'EDITOR_MATCHED_P',
            'unmatched_p': 'EDITOR_UNMATCHED_P',
            'normal': 'EDITOR_NORMAL',
            'keyword': 'EDITOR_KEYWORD',
            'magic': 'EDITOR_MAGIC',
            'builtin': 'EDITOR_BUILTIN',
            'definition': 'EDITOR_DEFINITION',
            'comment': 'EDITOR_COMMENT',
            'string': 'EDITOR_STRING',
            'number': 'EDITOR_NUMBER',
            'instance': 'EDITOR_INSTANCE',
        }
        
    def get_available_themes(self):
        """Get list of available themes."""
        if not self._themes_dir.exists():
            return []
        
        themes = []
        for theme_dir in self._themes_dir.iterdir():
            if theme_dir.is_dir() and (theme_dir / "palette.py").exists():
                themes.append(theme_dir.name)
            else:
                raise RuntimeError("Theme directory structure is invalid: missing palette.py in a theme subdirectory.")
        
        return sorted(themes)
    
    def load_theme(self, theme_name, interface_mode=None):
        """
        Load a theme by name.
        
        Parameters
        ----------
        theme_name : str
            Name of the theme to load
        interface_mode : str, optional
            'dark' or 'light'. If None, uses current interface mode.
        
        Returns
        -------
        tuple
            (palette, stylesheet) for the loaded theme
        """
        if interface_mode is None:
            interface_mode = 'dark' if is_dark_interface() else 'light'
        
        theme_path = self._themes_dir / theme_name
        
        if not theme_path.exists():
            raise ValueError(f"Theme '{theme_name}' not found")
        
        # Import the theme module
        theme_module_path = theme_path / "palette.py"
        if not theme_module_path.exists():
            raise ValueError(f"Theme '{theme_name}' has no palette.py")
        
        # Add the theme directory to sys.path temporarily
        theme_dir_str = str(theme_path)
        if theme_dir_str not in sys.path:
            sys.path.insert(0, theme_dir_str)
        
        try:
            # First, load the colorsystem module if it exists
            colorsystem_path = theme_path / "colorsystem.py"
            colorsystem_namespace = {}
            if colorsystem_path.exists():
                with open(colorsystem_path, 'r', encoding='utf-8') as f:
                    colorsystem_code = f.read()
                exec(colorsystem_code, colorsystem_namespace)
            
            # Import the theme module using exec
            with open(theme_module_path, 'r', encoding='utf-8') as f:
                theme_code = f.read()
            
            # Create a namespace for the theme module with necessary globals
            theme_namespace = {
                '__name__': f'{theme_name}_palette',
                '__file__': str(theme_module_path),
                '__package__': theme_name,
            }
            
            # Add colorsystem classes to the namespace
            theme_namespace.update(colorsystem_namespace)
            
            # Remove the colorsystem import since we've already loaded it
            # This handles the case where theme files use "from .colorsystem import"
            # TODO: fix this in ThemeWeaver
            import re
            theme_code_fixed = re.sub(r'from \.colorsystem import.*\n', '', theme_code)
            
            # Execute the theme code in the namespace
            exec(theme_code_fixed, theme_namespace)
            
            # Create a simple module-like object
            class ThemeModule:
                def __init__(self, namespace):
                    self.__dict__.update(namespace)
            
            theme_module = ThemeModule(theme_namespace)
            
            # Get the SpyderPalette from the theme (it's already set based on interface mode)
            palette_class = getattr(theme_module, 'SpyderPalette', None)
            
            if palette_class is None:
                raise ValueError(f"Theme '{theme_name}' has no SpyderPalette defined")
            
            # The palette is now a class, not an instance, so we can use it directly
            # or create an instance if needed
            palette = palette_class
            
            # Load the stylesheet
            stylesheet = self._load_stylesheet(theme_name, interface_mode)
            
            # Store current theme info
            self._current_theme = theme_name
            self._current_palette = palette
            self._current_stylesheet = stylesheet
            self._current_theme_module = theme_namespace  # Store the theme module
            self._current_interface_mode = interface_mode
            
            return palette, stylesheet
            
        finally:
            # Remove theme directory from sys.path
            if theme_dir_str in sys.path:
                sys.path.remove(theme_dir_str)
    
    def _load_stylesheet(self, theme_name, interface_mode):
        """Load the QSS stylesheet for a theme."""
        theme_path = self._themes_dir / theme_name
        
        if interface_mode == 'dark':
            qss_file = theme_path / "dark" / "darkstyle.qss"
            rc_file = theme_path / "dark" / "pyqt5_darkstyle_rc.py"
        else:
            qss_file = theme_path / "light" / "lightstyle.qss"
            rc_file = theme_path / "light" / "pyqt5_lightstyle_rc.py"
        
        if not qss_file.exists():
            raise ValueError(f"Stylesheet not found for theme '{theme_name}' in {interface_mode} mode")
        
        # Load the resources if they exist
        if rc_file.exists():
            self._load_theme_resources(rc_file)
        
        with open(qss_file, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _load_theme_resources(self, rc_file):
        """Load theme resources into Qt resource system."""
        try:
            # Import the resource module directly (like QDarkStyleSheet does)
            import importlib.util
            import logging
            
            logger = logging.getLogger(__name__)
            
            # Create a unique module name based on the file path
            module_name = f"theme_resources_{rc_file.stem}_{hash(str(rc_file)) % 10000}"
            
            spec = importlib.util.spec_from_file_location(module_name, rc_file)
            resource_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(resource_module)
            
            # Keep a reference to the module to prevent garbage collection
            self._loaded_resource_modules[str(rc_file)] = resource_module
            
            logger.info(f"Successfully loaded theme resources from {rc_file}")
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to load theme resources from {rc_file}: {e}")
    
    def get_current_theme(self):
        """Get the currently loaded theme name."""
        return self._current_theme
    
    
    def get_current_stylesheet(self):
        """Get the currently loaded stylesheet."""
        return self._current_stylesheet


# Global theme manager instance
theme_manager = ThemeManager()
