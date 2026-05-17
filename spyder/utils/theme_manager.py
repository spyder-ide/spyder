# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Theme manager for Spyder's new theming system.
"""

# Standard library imports
import configparser
from functools import lru_cache
import importlib
import logging
from pathlib import Path

import yaml

from spyder.api.config.mixins import SpyderConfigurationAccessor
from spyder.api.translations import _

logger = logging.getLogger(__name__)


COLOR_SCHEME_KEYS = {
    "background":     _("Background:"),
    "currentline":    _("Current line:"),
    "currentcell":    _("Current cell:"),
    "occurrence":     _("Occurrence:"),
    "ctrlclick":      _("Link:"),
    "sideareas":      _("Side areas:"),
    "matched_p":      _("Matched <br>parens:"),
    "unmatched_p":    _("Unmatched <br>parens:"),
    "normal":         _("Normal text:"),
    "keyword":        _("Keyword:"),
    "builtin":        _("Builtin:"),
    "definition":     _("Definition:"),
    "comment":        _("Comment:"),
    "string":         _("String:"),
    "number":         _("Number:"),
    "instance":       _("Instance:"),
    "magic":          _("Magic:"),
    "symbol":         _("Symbol:"),
}


COLOR_SCHEME_DEFAULT_VALUES = {
    "background":  "#19232D",
    "currentline": "#3a424a",
    "currentcell": "#292d3e",
    "occurrence":  "#1A72BB",
    "ctrlclick":   "#179ae0",
    "sideareas":   "#222b35",
    "matched_p":   "#0bbe0b",
    "unmatched_p": "#ff4340",
    "normal":     ("#ffffff", False, False),
    "keyword":    ("#c670e0", False, False),
    "builtin":    ("#fab16c", False, False),
    "definition": ("#57d6e4", True, False),
    "comment":    ("#999999", False, False),
    "string":     ("#b0e686", False, True),
    "number":     ("#faed5c", False, False),
    "instance":   ("#ee6772", False, True),
    "magic":      ("#c670e0", False, False),
    "symbol":     ("#ff0000", False, False),
}


class ThemeManager(SpyderConfigurationAccessor):
    """Manager for Spyder's theming system."""

    CONF_SECTION = "appearance"

    def __init__(self):
        self._current_theme = None
        self._current_palette = None
        self._current_stylesheet = None
        self._current_theme_module = None  # Store the loaded theme module
        self._loaded_resource_modules = {}  # Keep references to resource modules
        # Resource files to load after Qt is initialized
        self._pending_resource_files = []

    @staticmethod
    def get_available_themes():
        """Get list of available themes from registered theme packages."""
        themes = []

        # List of theme packages to search
        theme_packages = ["spyder_themes"]

        for package_name in theme_packages:
            try:
                package = importlib.import_module(package_name)
                if hasattr(package, "THEMES") and hasattr(
                        package, "get_theme_module"):
                    # Iterate through registered themes
                    for theme_name in package.THEMES:
                        try:
                            theme_module = package.get_theme_module(theme_name)
                            # Validate theme has required attributes
                            if hasattr(theme_module, "THEME_ID") and (
                                hasattr(theme_module, "SpyderPaletteDark")
                                or hasattr(theme_module, "SpyderPaletteLight")
                            ):
                                full_theme_name = f"{package_name}.{theme_name}"
                                try:
                                    ThemeManager._load_theme_metadata(
                                        full_theme_name)
                                except Exception as exc:
                                    logger.warning(
                                        "Ignoring theme '%s': invalid or missing metadata: %s",
                                        full_theme_name,
                                        exc,
                                    )
                                    continue
                                # Store full module path for loading
                                themes.append(full_theme_name)
                        except (ImportError, AttributeError, ValueError):
                            # Skip invalid themes
                            pass
            except ImportError:
                # Package not installed, skip
                pass

        return sorted(themes)

    @staticmethod
    @lru_cache(maxsize=None)
    def _theme_root_path(theme_name):
        """Filesystem root of an installed theme package (importable module path)."""
        theme_module = importlib.import_module(theme_name)
        return Path(theme_module.__path__[0])

    @staticmethod
    def get_theme_modes(theme_name):
        """
        Get available UI modes for a theme.

        ``theme.yaml`` must include a ``variants`` mapping with ``dark`` and/or
        ``light`` set to ``true`` or ``false``. Only those two keys are allowed.
        Each mode set to ``true`` must have the corresponding
        ``SpyderPaletteDark`` or ``SpyderPaletteLight`` class on the theme module.
        At least one variant must be enabled.
        """
        meta = ThemeManager._load_theme_metadata(theme_name)
        theme_module = importlib.import_module(theme_name)

        code_modes = []
        if hasattr(theme_module, "SpyderPaletteDark"):
            code_modes.append("dark")
        if hasattr(theme_module, "SpyderPaletteLight"):
            code_modes.append("light")

        variants = meta.get("variants")
        if variants is None:
            raise ValueError(
                f"Theme '{theme_name}': metadata must declare 'variants' "
                f"(dark and light booleans)"
            )
        if not isinstance(variants, dict):
            raise ValueError(
                f"Theme '{theme_name}': metadata 'variants' must be a mapping"
            )
        unknown = [k for k in variants if k not in ("dark", "light")]
        if unknown:
            raise ValueError(
                f"Theme '{theme_name}': metadata 'variants' has unknown keys "
                f"{unknown!r}; only 'dark' and 'light' are allowed"
            )
        ordered = []
        for mode in ("dark", "light"):
            if mode not in variants:
                continue
            val = variants[mode]
            if val is True:
                if mode not in code_modes:
                    raise ValueError(
                        f"Theme '{theme_name}': metadata enables variant "
                        f"'{mode}' but the corresponding palette class is not "
                        f"defined"
                    )
                ordered.append(mode)
            elif val is False:
                continue
            else:
                raise ValueError(
                    f"Theme '{theme_name}': metadata 'variants.{mode}' must be "
                    f"true or false, got {val!r}"
                )
        if not ordered:
            raise ValueError(
                f"Theme '{theme_name}': metadata 'variants' must enable at least "
                f"one of 'dark', 'light'"
            )
        return ordered

    @staticmethod
    def get_available_theme_variants():
        """Get list of available theme/mode combinations."""
        variants = []
        for theme_name in ThemeManager.get_available_themes():
            for mode in ThemeManager.get_theme_modes(theme_name):
                variants.append(f"{theme_name}/{mode}")

        return sorted(variants)

    @staticmethod
    def canonical_theme_variant_id(variant):
        """
        Normalize a theme variant id to the ``spyder_themes.<module>/<mode>`` form.

        If the segment before ``/`` already starts with ``spyder_themes.``,
        ``variant`` is returned unchanged. Legacy values like ``spyder/dark``
        become ``spyder_themes.spyder/dark``.

        Parameters
        ----------
        variant : str
            Theme variant string, or empty.

        Returns
        -------
        str
            Canonical variant id, or the original value if it has no ``/``.
        """
        if not variant or "/" not in variant:
            return variant
        theme_part, mode = variant.rsplit("/", 1)
        if not theme_part.startswith("spyder_themes."):
            return f"spyder_themes.{theme_part}/{mode}"
        return variant

    @staticmethod
    def get_theme_display_name(theme_variant):
        """
        Get display name for a theme variant.

        Parameters
        ----------
        theme_variant : str
            Theme variant in format 'package.theme/mode' (e.g., 'spyder_themes.dracula/dark')

        Returns
        -------
        str
            User-friendly display name (e.g., 'Dracula Dark')
        """
        meta = ThemeManager.get_theme_metadata(theme_variant)
        if "display_name" not in meta:
            raise ValueError(
                f"Theme metadata for '{theme_variant}' does not contain "
                f"'display_name'"
            )
        theme_name = meta["display_name"]
        mode = meta.get("mode")
        if mode:
            return f"{theme_name} ({str(mode).title()})"

        return str(theme_name)

    @staticmethod
    @lru_cache(maxsize=None)
    def _load_theme_metadata(theme_name):
        """
        Load raw metadata from ``theme.yaml`` for a theme module.

        Parameters
        ----------
        theme_name : str
            Theme module path (e.g. ``spyder_themes.dracula``).

        Returns
        -------
        dict
            Parsed metadata mapping.

        Raises
        ------
        ValueError
            If the file is missing or contains invalid metadata.
        """
        theme_path = ThemeManager._theme_root_path(theme_name)
        metadata_file = theme_path / "theme.yaml"

        if not metadata_file.exists():
            raise ValueError(f"Missing metadata file: {metadata_file}")

        try:
            with open(metadata_file, "r", encoding="utf-8") as fh:
                metadata = yaml.safe_load(fh)
        except Exception as exc:
            raise ValueError(
                f"Failed to parse metadata file {metadata_file}: {exc}")

        if not isinstance(metadata, dict):
            raise ValueError(
                f"Theme metadata in {metadata_file} must be a mapping")

        return metadata

    @staticmethod
    def get_theme_metadata(theme_variant, field=None):
        """
        Get metadata for a theme variant from ``theme.yaml``.

        Parameters
        ----------
        theme_variant : str
            Theme variant in format ``package.theme/mode`` or theme module path.
        field : str, optional
            Specific metadata field to return. If omitted, returns full metadata.

        Returns
        -------
        dict or object
            Full metadata mapping (plus runtime keys) or the selected field value.

        Raises
        ------
        ValueError
            If metadata is missing/invalid or requested field does not exist.
        """
        canonical = ThemeManager.canonical_theme_variant_id(theme_variant)
        if "/" in canonical:
            theme_name, mode = canonical.rsplit("/", 1)
        else:
            theme_name = canonical
            mode = None

        # Runtime keys (``theme``, ``mode``, ``id``) override YAML homonyms.
        metadata = dict(ThemeManager._load_theme_metadata(theme_name))
        metadata["theme"] = theme_name
        metadata["mode"] = mode
        metadata["id"] = canonical if mode else theme_name

        if field is None:
            return metadata

        if field not in metadata:
            raise ValueError(
                f"Theme metadata field '{field}' not found for '{theme_variant}'"
            )
        return metadata[field]

    def get_color_scheme_from_palette(self, palette):
        """
        Extract syntax highlighting colors from a theme palette.

        Parameters
        ----------
        palette : class
            Theme palette class with EDITOR_* attributes

        Returns
        -------
        dict
            Dictionary with syntax color scheme in the format expected by
            set_color_scheme(), compatible with COLOR_SCHEME_KEYS format.
        """
        # Map palette EDITOR_* attributes to COLOR_SCHEME_KEYS format
        color_scheme = {
            "background": palette.EDITOR_BACKGROUND,
            "currentline": palette.EDITOR_CURRENTLINE,
            "currentcell": palette.EDITOR_CURRENTCELL,
            "occurrence": palette.EDITOR_OCCURRENCE,
            "ctrlclick": palette.EDITOR_CTRLCLICK,
            "sideareas": palette.EDITOR_SIDEAREAS,
            "matched_p": palette.EDITOR_MATCHED_P,
            "unmatched_p": palette.EDITOR_UNMATCHED_P,
            "normal": palette.EDITOR_NORMAL,
            "keyword": palette.EDITOR_KEYWORD,
            "builtin": palette.EDITOR_BUILTIN,
            "definition": palette.EDITOR_DEFINITION,
            "comment": palette.EDITOR_COMMENT,
            "string": palette.EDITOR_STRING,
            "number": palette.EDITOR_NUMBER,
            "instance": palette.EDITOR_INSTANCE,
            "magic": palette.EDITOR_MAGIC,
            "symbol": palette.EDITOR_SYMBOL,
        }

        return color_scheme

    def get_color_scheme(self, name):
        """
        Resolve syntax colors for a scheme id.

        Theme variants (``spyder_themes.<theme>/<mode>``) use the installed
        theme palette as the base and apply per-key overrides from the
        ``appearance`` section when those options exist (user edits in
        Preferences).
        """

        # Highlighter default ``'Spyder'``
        if name and str(name).lower() == "spyder" or not name:
            name = self.get_conf(
                "selected", default="spyder_themes.spyder/dark"
            )

        canonical = self.canonical_theme_variant_id(name)

        logger.debug(
            "get_color_scheme called with name=%s, canonical=%s",
            name,
            canonical
        )

        if "/" in canonical:
            theme_name, ui_mode = canonical.rsplit("/", 1)
            palette, _ = self._load_theme_internal(theme_name, ui_mode)
            base = self.get_color_scheme_from_palette(palette)
            merged = {}

            for key in COLOR_SCHEME_KEYS:
                try:
                    override = self.get_conf(f"{canonical}/{key}")
                except configparser.NoOptionError:
                    override = None

                merged[key] = override if override is not None else base[key]

            logger.debug(
                "Merged theme %s/%s with config overrides",
                theme_name,
                ui_mode,
            )
            return merged

        scheme = {}
        missing_in_config = []
        for key in COLOR_SCHEME_KEYS:
            try:
                scheme[key] = self.get_conf(f"{canonical}/{key}")
            except Exception:
                missing_in_config.append(key)

        if missing_in_config and "/" in canonical:
            try:
                theme_name, ui_mode = canonical.rsplit("/", 1)
                palette, _ = self._load_theme_internal(theme_name, ui_mode)
                theme_colors = self.get_color_scheme_from_palette(palette)
                for key in missing_in_config:
                    scheme[key] = theme_colors[key]
            except Exception as e:
                logger.warning(
                    "Failed to fill missing colors from theme: %s", e
                )
                for key in missing_in_config:
                    scheme[key] = COLOR_SCHEME_DEFAULT_VALUES[key]
        elif missing_in_config:
            for key in missing_in_config:
                scheme[key] = COLOR_SCHEME_DEFAULT_VALUES[key]

        return scheme

    def is_dark_interface(self):
        """
        Check if current interface is dark mode.

        Determines the interface mode by inspecting the selected theme variant.
        Theme variants follow the format 'theme_name/mode' (e.g., 'solarized/dark').
        Returns True if config is not ready to avoid segfaults during initialization.
        """
        # Use default value if config doesn't exist or isn't initialized yet
        selected = self.get_conf(
            "selected", default="spyder_themes.spyder/dark"
        )

        selected = self.canonical_theme_variant_id(selected)

        if "/" in selected:
            _, ui_mode = selected.rsplit("/", 1)
            return ui_mode == "dark"

        # Default to dark if no mode specified (shouldn't happen with new
        # themes)
        return True

    def export_theme_to_config(self, theme_name, ui_mode, replace=False):
        """
        Export theme data to the user configuration file.

        When ``replace`` is True, writes the full package palette for the
        variant (used when resetting a scheme). When False, only updates
        the variant display name: colors are resolved at read time by merging
        the installed theme with ``appearance`` overrides
        (see ``syntaxhighlighters.get_color_scheme``), so the stock palette
        is not written on every startup.
        """
        from spyder.config.manager import CONF

        # Remember current theme to restore later
        current_theme = self._current_theme

        # Build the full theme variant name (e.g., "solarized/dark")
        variant_name = f"{theme_name}/{ui_mode}"

        if replace:
            # Load the theme to get its palette (without auto-export to avoid
            # circular calls)
            palette, _ = self._load_theme_internal(theme_name, ui_mode)
            color_scheme = self.get_color_scheme_from_palette(palette)
            section = "appearance"
            for key, value in color_scheme.items():
                option = f"{variant_name}/{key}"
                CONF.set(section, option, value)

        # Also save the display name for the theme variant
        display_name = ThemeManager.get_theme_display_name(variant_name)
        CONF.set("appearance", f"{variant_name}/name", display_name)

        # Restore original theme if different from what we just exported
        if current_theme and current_theme != theme_name:
            try:
                # Determine ui_mode from current interface state
                restore_ui_mode = (
                    "dark" if self.is_dark_interface() else "light"
                )
                self._load_theme_internal(current_theme, restore_ui_mode)
            except Exception:
                # If restoration fails, just continue
                pass

    def export_all_themes_to_config(self):
        """
        Ensure every theme variant has a display name in the config.

        Per-key colors are not written here: they are merged at read time
        (package palette plus optional ``appearance`` overrides).
        """
        from spyder.config.manager import CONF

        # Remember the current theme to restore it after exporting all themes
        current_theme = self._current_theme

        for theme_name in self.get_available_themes():
            for ui_mode in self.get_theme_modes(theme_name):
                variant_name = f"{theme_name}/{ui_mode}"

                try:
                    CONF.get("appearance", f"{variant_name}/name")
                except Exception:
                    try:
                        display_name = ThemeManager.get_theme_display_name(
                            variant_name
                        )
                        CONF.set("appearance",
                                 f"{variant_name}/name", display_name)
                        logger.info(
                            "Registered theme name for %s in config", variant_name)
                    except Exception as e:
                        logger.warning(
                            "Failed to register theme name for %s: %s", variant_name, e)

        # Restore original theme if needed
        if current_theme and current_theme != self._current_theme:
            try:
                # Determine ui_mode from current interface state
                restore_ui_mode = (
                    "dark" if self.is_dark_interface() else "light"
                )
                self.load_theme(current_theme, restore_ui_mode)
            except Exception:
                # If restoration fails, just continue with the current theme
                pass

    def _load_theme_internal(self, theme_name, ui_mode=None):
        """Load theme using standard package import."""
        if ui_mode is None:
            ui_mode = "dark" if self.is_dark_interface() else "light"

        ThemeManager._load_theme_metadata(theme_name)

        # Import theme module using full module path
        theme_module = importlib.import_module(theme_name)

        # Get palette class
        if ui_mode == "dark":
            if not hasattr(theme_module, "SpyderPaletteDark"):
                raise ValueError(
                    f"Theme '{theme_name}' has no SpyderPaletteDark class")
            palette_class = theme_module.SpyderPaletteDark
        else:
            if not hasattr(theme_module, "SpyderPaletteLight"):
                raise ValueError(
                    f"Theme '{theme_name}' has no SpyderPaletteLight class"
                )
            palette_class = theme_module.SpyderPaletteLight

        # Load stylesheet
        stylesheet = self._load_stylesheet(theme_name, ui_mode)

        return palette_class, stylesheet

    def load_theme(self, theme_name, ui_mode=None):
        """
        Load a theme by name.

        Loads the palette and stylesheet into this manager. Per-key syntax
        colors are not written to the user config here; see
        ``syntaxhighlighters.get_color_scheme`` for how editor colors are
        resolved.

        Parameters
        ----------
        theme_name : str
            Name of the theme to load
        ui_mode : str, optional
            'dark' or 'light'. If None, uses current interface mode.

        Returns
        -------
        tuple
            (palette, stylesheet) for the loaded theme
        """
        # Use internal method to load theme
        palette, stylesheet = self._load_theme_internal(theme_name, ui_mode)

        # Store current theme info
        self._current_theme = theme_name
        self._current_palette = palette
        self._current_stylesheet = stylesheet

        from spyder.config.manager import CONF

        variant_name = f"{theme_name}/{ui_mode}"
        try:
            CONF.get("appearance", f"{variant_name}/name")
        except Exception:
            display_name = ThemeManager.get_theme_display_name(variant_name)
            CONF.set("appearance", f"{variant_name}/name", display_name)

        return palette, stylesheet

    def _load_stylesheet(self, theme_name, ui_mode):
        """Load the QSS stylesheet for a theme."""
        theme_path = ThemeManager._theme_root_path(theme_name)

        # Stylesheet and qtpy-based resource modules from spyder-themes
        # (``darkstyle_rc.py`` / ``lightstyle_rc.py``).
        if ui_mode == "dark":
            qss_file = theme_path / "dark" / "darkstyle.qss"
            rc_file = theme_path / "dark" / "darkstyle_rc.py"
        else:
            qss_file = theme_path / "light" / "lightstyle.qss"
            rc_file = theme_path / "light" / "lightstyle_rc.py"

        if not qss_file.exists():
            raise ValueError(
                f"Stylesheet not found for theme '{theme_name}' in {ui_mode} mode"
            )

        if not rc_file.exists():
            logger.debug(
                "No theme resource module found for '%s' (%s mode) at %s",
                theme_name,
                ui_mode,
                rc_file,
            )
            rc_file = None

        # Load the resources if they exist, but defer loading until Qt is initialized
        # Loading resources before Qt is ready can cause segfaults during Qt
        # initialization
        if rc_file is not None:
            # Store the resource file path for later loading
            # Don't load it now to avoid segfaults during Qt initialization
            # We'll load it later when Qt is fully initialized
            if not hasattr(self, '_pending_resource_files'):
                self._pending_resource_files = []
            if rc_file not in self._pending_resource_files:
                self._pending_resource_files.append(rc_file)

        with open(qss_file, "r", encoding="utf-8") as f:
            return f.read()

    def _load_theme_resources(self, rc_file):
        """
        Load theme resources into Qt resource system.

        This should only be called after Qt is fully initialized to avoid segfaults.
        """
        try:
            # Double-check that Qt is initialized before loading resources
            from qtpy.QtWidgets import QApplication
            if QApplication.instance() is None:
                import logging
                logger = logging.getLogger(__name__)
                logger.debug(
                    f"QApplication not initialized, skipping resource loading for {rc_file}"
                )
                return

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
            logger.warning(
                f"Failed to load theme resources from {rc_file}: {e}")

    def get_current_theme(self):
        """Get the currently loaded theme name."""
        return self._current_theme

    def get_current_stylesheet(self):
        """Get the currently loaded stylesheet."""
        return self._current_stylesheet

    def load_pending_resources(self):
        """
        Load any pending theme resources that were deferred during initialization.

        This should be called after Qt is fully initialized to avoid segfaults.
        """
        if hasattr(
                self, '_pending_resource_files') and self._pending_resource_files:
            for rc_file in list(self._pending_resource_files):
                try:
                    self._load_theme_resources(rc_file)
                    self._pending_resource_files.remove(rc_file)
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(
                        f"Failed to load pending resource {rc_file}: {e}")


# Global theme manager instance
theme_manager = ThemeManager()
