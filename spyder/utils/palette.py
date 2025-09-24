# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Palettes for dark and light themes used in Spyder.
"""

# Standard library imports
import logging
from spyder.utils.theme_manager import theme_manager

# Theme configuration
SELECTED_THEME = "dracula"  # Hardcoded theme selection for now

# =============================================================================
# ---- Theme manager integration
# =============================================================================

def _get_theme_palette():
    """
    Get SpyderPalette from theme manager.
    
    Returns
    -------
    class
        SpyderPalette class from the loaded theme, or None if loading fails.
    """
    try:
        # Load the theme
        palette_class, _ = theme_manager.load_theme(SELECTED_THEME)
        return palette_class
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to load theme '{SELECTED_THEME}': {e}")
        return None


# =============================================================================
# ---- Exported classes
# =============================================================================

# Try to get palette from theme manager first, fall back to original logic
_theme_palette = _get_theme_palette()

if _theme_palette is not None:
    # Use theme manager palette
    SpyderPalette = _theme_palette
