# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)


"""Spyder global registries for actions, toolbuttons, toolbars and menus."""

# Standard library imports
import inspect
import logging
from typing import Any, Optional, Dict
import warnings
import weakref

logger = logging.getLogger(__name__)


def get_createaction_caller():
    """Get file and line where `create_action` is called."""
    frames = []
    for frame in inspect.stack():
        code_context = frame.code_context[0]
        if 'create_action' in code_context:
            frames.append(f'{frame.filename}:{frame.lineno}')
        elif 'self.create_action' in code_context:
            frames.append(f'{frame.filename}:{frame.lineno}')
    frames = ', '.join(frames)
    return frames


class SpyderRegistry:
    """General registry for global references (per plugin) in Spyder."""

    def __init__(self, obj_type: str = ''):
        self.registry_map = {}
        self.obj_type = obj_type

    def register_reference(self, obj: Any, key: str,
                           plugin: Optional[str] = None,
                           context: Optional[str] = None):
        """
        Register a reference `obj` for a given plugin key on a given context.

        Parameters
        ----------
        obj: Any
            Object to register as a reference.
        key: str
            String identifier used to store the object reference.
        plugin: Optional[str]
            Plugin key used to store the reference. Should belong to
            :class:`spyder.api.plugins.Plugins`. If None, then the object will
            be stored under the global `main` key.
        context: Optional[str]
            Additional key used to store and identify the object reference.
            In any Spyder plugin implementation, this context may refer to an
            identifier of a widget. This context enables plugins to define
            multiple actions with the same key that live on different widgets.
            If None, this context will default to the special `__global`
            identifier.
        """
        plugin = plugin if plugin is not None else 'main'
        context = context if context is not None else '__global'

        plugin_contexts = self.registry_map.get(plugin, {})
        context_references = plugin_contexts.get(
            context, weakref.WeakValueDictionary())

        if key in context_references:
            try:
                frames = get_createaction_caller()
                warnings.warn(
                    f'There already exists a reference {context_references[key]} '
                    f'with key {key} under the context {context} of plugin '
                    f'{plugin}. The new reference {obj} will overwrite the '
                    f'previous reference. Hint: {obj} should have a different '
                    f'key. See {frames}')
            except RuntimeError:
                # Do not raise exception if a wrapped Qt Object was deleted.
                pass

        logger.debug(f'Registering {obj} ({key}) under context {context} for '
                     f'plugin {plugin}')
        context_references[key] = obj
        plugin_contexts[context] = context_references
        self.registry_map[plugin] = plugin_contexts

    def get_reference(self, key: str,
                      plugin: Optional[str] = None,
                      context: Optional[str] = None) -> Any:
        """
        Retrieve an stored object reference under a given key of a specific
        context of a given plugin key.

        Parameters
        ----------
        key: str
            String identifier used to retrieve the object.
        plugin: Optional[str]
            Plugin key used to store the reference. Should belong to
            :class:`spyder.api.plugins.Plugins`. If None, then the object will
            be retrieved from the global `main` key.
        context: Optional[str]
            Additional key that was used to store the object reference.
            In any Spyder plugin implementation, this context may refer to an
            identifier of a widget. This context enables plugins to define
            multiple actions with the same key that live on different widgets.
            If None, this context will default to the special `__global`
            identifier.

        Returns
        -------
        obj: Any
            The object that was stored under the given key identifier.

        Raises
        ------
        KeyError
            If neither of `key`, `plugin` or `context` were found in the
            registry.
        """
        plugin = plugin if plugin is not None else 'main'
        context = context if context is not None else '__global'

        plugin_contexts = self.registry_map[plugin]
        context_references = plugin_contexts[context]
        return context_references[key]

    def get_references(self, plugin: Optional[str] = None,
                       context: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieve all stored object references under the context of a
        given plugin key.

        Parameters
        ----------
        plugin: Optional[str]
            Plugin key used to store the reference. Should belong to
            :class:`spyder.api.plugins.Plugins`. If None, then the object will
            be retrieved from the global `main` key.
        context: Optional[str]
            Additional key that was used to store the object reference.
            In any Spyder plugin implementation, this context may refer to an
            identifier of a widget. This context enables plugins to define
            multiple actions with the same key that live on different widgets.
            If None, this context will default to the special `__global`
            identifier.

        Returns
        -------
        objs: Dict[str, Any]
            A dict that contains the actions mapped by their corresponding
            keys.
        """
        plugin = plugin if plugin is not None else 'main'
        context = context if context is not None else '__global'

        plugin_contexts = self.registry_map.get(plugin, {})
        context_references = plugin_contexts.get(
            context, weakref.WeakValueDictionary())
        return context_references

    def reset_registry(self):
        self.registry_map = {}

    def __str__(self) -> str:
        return f'SpyderRegistry[{self.obj_type}, {self.registry_map}]'


ACTION_REGISTRY = SpyderRegistry('SpyderAction')
TOOLBUTTON_REGISTRY = SpyderRegistry('QToolButton')
TOOLBAR_REGISTRY = SpyderRegistry('QToolBar')
MENU_REGISTRY = SpyderRegistry('QMenu')
