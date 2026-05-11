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

logger = logging.getLogger(__name__)


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
        # Check if config is ready before trying to use it
        from spyder.config.base import _is_conf_ready

        # Export only the selected theme to config BEFORE loading it
        # This ensures the selected theme's colors are available
        # Don't export all themes as it loads all theme resources unnecessarily
        # Only do this if config is ready to avoid segfaults
        from spyder.utils.theme_manager import ThemeManager

        if _is_conf_ready():
            try:
                from spyder.config.manager import CONF
                selected = CONF.get("appearance", "selected",
                                    default="spyder_themes.spyder/dark")
            except (
                AttributeError, ImportError, RuntimeError, OSError,
            ) as conf_error:
                logger.warning(
                    "Config not available yet, using default theme: %s",
                    conf_error,
                )
                selected = "spyder_themes.spyder/dark"
        else:
            logger.debug("Config not ready yet, using default theme")
            selected = "spyder_themes.spyder/dark"

        selected = ThemeManager.canonical_theme_variant_id(selected)

        if _is_conf_ready():
            try:
                if "/" in selected:
                    theme_name, ui_mode = selected.rsplit("/", 1)
                    theme_manager.export_theme_to_config(
                        theme_name, ui_mode, replace=False
                    )
            except Exception as theme_exp:
                logger.warning(
                    f"Failed to export selected theme to config: {theme_exp}")

        if "/" in selected:
            theme_name, ui_mode = selected.rsplit("/", 1)
        else:
            theme_name = selected
            ui_mode = "dark"

        # Load the theme
        palette_class, _ = theme_manager.load_theme(theme_name, ui_mode)
        return palette_class

    except Exception as e:
        logger.error(f"Failed to load theme from config: {e}")
        # Try to load default theme as fallback
        try:
            logger.info("Attempting to load default theme as fallback")
            palette_class, _ = theme_manager.load_theme(
                "spyder_themes.spyder", "dark")
            return palette_class
        except Exception as fallback_error:
            logger.error(f"Failed to load default theme: {fallback_error}")
            # Return None instead of raising - let __getattr__ handle it
            return None


# =============================================================================
# ---- Exported classes
# =============================================================================

# Lazy loading: don't load palette at import time to avoid accessing config
# before it's initialized. Load it on first access instead.
_theme_palette = None
_theme_palette_loaded = False


def __getattr__(name):
    """
    Lazy loading of SpyderPalette to avoid accessing config at import time.

    This function is called when an attribute is accessed that doesn't exist
    in the module's __dict__. This allows us to defer loading the palette
    until it's actually needed, avoiding segfaults when config isn't ready.
    """
    global _theme_palette, _theme_palette_loaded

    if name == 'SpyderPalette':
        if not _theme_palette_loaded:
            _theme_palette_loaded = True
            try:
                _theme_palette = _get_theme_palette()
            except Exception as e:
                logger.error(f"Error loading theme palette: {e}")
                _theme_palette = None

            if _theme_palette is not None:
                return _theme_palette
            else:
                # If theme loading completely fails, raise an error with
                # helpful message
                raise ImportError(
                    "Failed to load SpyderPalette. Ensure spyder_themes is "
                    "installed and contains the 'spyder' theme."
                )
        elif _theme_palette is not None:
            return _theme_palette
        else:
            raise ImportError(
                "Failed to load SpyderPalette. Ensure spyder_themes is "
                "installed and contains the 'spyder' theme."
            )

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
