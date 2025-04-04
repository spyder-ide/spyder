# Copyright 2017-2020 Palantir Technologies, Inc.
# Copyright 2021- Python Language Server Contributors.

import logging
import sys
from functools import lru_cache
from typing import List, Mapping, Sequence, Union

import pluggy
from pluggy._hooks import HookImpl

from pylsp import PYLSP, _utils, hookspecs, uris

# See compatibility note on `group` keyword:
#   https://docs.python.org/3/library/importlib.metadata.html#entry-points
if sys.version_info < (3, 10):  # pragma: no cover
    from importlib_metadata import entry_points
else:  # pragma: no cover
    from importlib.metadata import entry_points


log = logging.getLogger(__name__)

# Sources of config, first source overrides next source
DEFAULT_CONFIG_SOURCES = ["pycodestyle"]


class PluginManager(pluggy.PluginManager):
    def _hookexec(
        self,
        hook_name: str,
        methods: Sequence[HookImpl],
        kwargs: Mapping[str, object],
        firstresult: bool,
    ) -> Union[object, List[object]]:
        # called from all hookcaller instances.
        # enable_tracing will set its own wrapping function at self._inner_hookexec
        try:
            return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
        except Exception as e:
            log.warning(f"Failed to load hook {hook_name}: {e}", exc_info=True)
            return []


class Config:
    def __init__(self, root_uri, init_opts, process_id, capabilities) -> None:
        self._root_path = uris.to_fs_path(root_uri)
        self._root_uri = root_uri
        self._init_opts = init_opts
        self._process_id = process_id
        self._capabilities = capabilities

        self._settings = {}
        self._plugin_settings = {}

        self._config_sources = {}
        try:
            from .flake8_conf import Flake8Config

            self._config_sources["flake8"] = Flake8Config(self._root_path)
        except ImportError:
            pass
        try:
            from .pycodestyle_conf import PyCodeStyleConfig

            self._config_sources["pycodestyle"] = PyCodeStyleConfig(self._root_path)
        except ImportError:
            pass

        self._pm = PluginManager(PYLSP)
        self._pm.trace.root.setwriter(log.debug)
        self._pm.enable_tracing()
        self._pm.add_hookspecs(hookspecs)

        # Pluggy will skip loading a plugin if it throws a DistributionNotFound exception.
        # However I don't want all plugins to have to catch ImportError and re-throw. So here we'll filter
        # out any entry points that throw ImportError assuming one or more of their dependencies isn't present.
        for entry_point in entry_points(group=PYLSP):
            try:
                entry_point.load()
            except Exception as e:
                log.info(
                    "Failed to load %s entry point '%s': %s", PYLSP, entry_point.name, e
                )
                self._pm.set_blocked(entry_point.name)

        # Load the entry points into pluggy, having blocked any failing ones.
        # Despite the API name, recent Pluggy versions will use ``importlib_metadata``.
        self._pm.load_setuptools_entrypoints(PYLSP)

        for name, plugin in self._pm.list_name_plugin():
            if plugin is not None:
                log.info("Loaded pylsp plugin %s from %s", name, plugin)

        for plugin_conf in self._pm.hook.pylsp_settings(config=self):
            self._plugin_settings = _utils.merge_dicts(
                self._plugin_settings, plugin_conf
            )

        self._plugin_settings = _utils.merge_dicts(
            self._plugin_settings, self._init_opts.get("pylsp", {})
        )

        self._update_disabled_plugins()

    @property
    def disabled_plugins(self):
        return self._disabled_plugins

    @property
    def plugin_manager(self):
        return self._pm

    @property
    def init_opts(self):
        return self._init_opts

    @property
    def root_uri(self):
        return self._root_uri

    @property
    def process_id(self):
        return self._process_id

    @property
    def capabilities(self):
        return self._capabilities

    @lru_cache(maxsize=32)
    def settings(self, document_path=None):
        """Settings are constructed from a few sources:

            1. User settings, found in user's home directory
            2. Plugin settings, reported by PyLS plugins
            3. LSP settings, given to us from didChangeConfiguration
            4. Project settings, found in config files in the current project.

        Since this function is nondeterministic, it is important to call
        settings.cache_clear() when the config is updated
        """
        settings = {}
        sources = self._settings.get("configurationSources", DEFAULT_CONFIG_SOURCES)

        # Plugin configuration
        settings = _utils.merge_dicts(settings, self._plugin_settings)

        # LSP configuration
        settings = _utils.merge_dicts(settings, self._settings)

        # User configuration
        for source_name in reversed(sources):
            source = self._config_sources.get(source_name)
            if not source:
                continue
            source_conf = source.user_config()
            log.debug(
                "Got user config from %s: %s", source.__class__.__name__, source_conf
            )
            settings = _utils.merge_dicts(settings, source_conf)

        # Project configuration
        for source_name in reversed(sources):
            source = self._config_sources.get(source_name)
            if not source:
                continue
            source_conf = source.project_config(document_path or self._root_path)
            log.debug(
                "Got project config from %s: %s", source.__class__.__name__, source_conf
            )
            settings = _utils.merge_dicts(settings, source_conf)

        log.debug("With configuration: %s", settings)

        return settings

    def find_parents(self, path, names):
        root_path = uris.to_fs_path(self._root_uri)
        return _utils.find_parents(root_path, path, names)

    def plugin_settings(self, plugin, document_path=None):
        return (
            self.settings(document_path=document_path)
            .get("plugins", {})
            .get(plugin, {})
        )

    def update(self, settings) -> None:
        """Recursively merge the given settings into the current settings."""
        self.settings.cache_clear()
        self._settings = settings
        log.info("Updated settings to %s", self._settings)
        self._update_disabled_plugins()

    def _update_disabled_plugins(self) -> None:
        # All plugins default to enabled
        self._disabled_plugins = [
            plugin
            for name, plugin in self.plugin_manager.list_name_plugin()
            if not self.settings().get("plugins", {}).get(name, {}).get("enabled", True)
        ]
        log.info("Disabled plugins: %s", self._disabled_plugins)
