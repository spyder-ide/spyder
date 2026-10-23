# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Snapshot of the methods Spyder's plugins expose to outside callers.

Exposed methods are a contract with agents and scripts, so changing their
names, descriptions or arguments must be intentional. If this test fails
because of a change you meant to make, update the snapshot by running this
test with the ``SPYDER_UPDATE_EXPOSED_API=1`` environment variable, and
review the diff of ``exposed_api.json``.
"""

# Standard library imports
import ast
from collections import Counter
from importlib.metadata import entry_points
import inspect
import json
import os
import os.path as osp

# Local imports
from spyder.api.plugins.exposed import get_exposed_methods
from spyder.plugins.mcpserver.exposed import describe_exposed

SNAPSHOT = osp.join(osp.dirname(__file__), "exposed_api.json")


def get_exposed_api() -> dict:
    """Describe the exposed methods of Spyder's own plugins."""
    api = {}
    for entry_point in entry_points(group="spyder.plugins"):
        if not entry_point.value.startswith("spyder.plugins."):
            continue

        plugin_class = entry_point.load()
        methods = [
            describe_exposed(func, spec).to_dict()
            for func, spec in get_exposed_methods(plugin_class).values()
        ]
        if methods:
            api[plugin_class.NAME] = sorted(
                methods, key=lambda method: method["name"]
            )
    return dict(sorted(api.items()))


def test_exposed_api():
    api = get_exposed_api()

    if os.environ.get("SPYDER_UPDATE_EXPOSED_API"):
        with open(SNAPSHOT, "w") as f:
            json.dump(api, f, indent=2, ensure_ascii=False)
            f.write("\n")

    with open(SNAPSHOT) as f:
        snapshot = json.load(f)

    assert api == snapshot, (
        "The exposed API changed. If that's intended, update the snapshot "
        "with SPYDER_UPDATE_EXPOSED_API=1 and review its diff."
    )


def test_exposed_names_are_unique():
    """Agents call tools by name, so names must be unique across plugins."""
    names = [
        method["name"]
        for methods in get_exposed_api().values()
        for method in methods
    ]
    assert len(names) == len(set(names))


def test_exposed_methods_dont_override_inherited_ones():
    """
    Exposed methods take arguments for outside callers, so they can't
    replace methods that Spyder calls with other arguments (e.g.
    ``save_file``). Give the method another name and keep the exposed name
    with ``expose(name=...)``.
    """
    for entry_point in entry_points(group="spyder.plugins"):
        if not entry_point.value.startswith("spyder.plugins."):
            continue

        plugin_class = entry_point.load()
        for attr_name in get_exposed_methods(plugin_class):
            for base in plugin_class.__mro__[1:]:
                assert attr_name not in vars(base), (
                    f"{plugin_class.__name__}.{attr_name} overrides "
                    f"{base.__name__}.{attr_name}"
                )


def test_exposed_methods_arent_redefined():
    """
    Exposed methods can't be defined twice in their class either, which
    replaces the first definition (e.g. an existing ``run_cell`` that Spyder
    calls with other arguments).
    """
    for entry_point in entry_points(group="spyder.plugins"):
        if not entry_point.value.startswith("spyder.plugins."):
            continue

        plugin_class = entry_point.load()
        exposed = set(get_exposed_methods(plugin_class))
        if not exposed:
            continue

        tree = ast.parse(inspect.getsource(inspect.getmodule(plugin_class)))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ClassDef)
                and node.name == plugin_class.__name__
            ):
                counts = Counter(
                    item.name
                    for item in node.body
                    if isinstance(item, ast.FunctionDef)
                )
                redefined = {
                    name for name in exposed if counts[name] > 1
                }
                assert not redefined, (
                    f"{plugin_class.__name__} defines {redefined} more than "
                    f"once"
                )
