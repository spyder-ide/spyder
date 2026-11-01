# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Functions evaluated in the kernel to inspect its state.

Spyder never calls these functions directly: their source is sent to the
kernel (see ``execution.call_kernel_helper``), so each one must be
self-contained (with its imports inside) and work on any Python version
supported by spyder-kernels. They return JSON.
"""


def spyder_summarize_variable(name, namespace):
    """Summarize the variable ``name``, e.g. the shape and head of arrays."""
    import json
    import sys

    def short(text, limit=3000):
        text = str(text)
        return text if len(text) <= limit else text[:limit] + "..."

    parts = name.split(".")
    if parts[0] not in namespace:
        raise NameError(f"There's no variable called {parts[0]!r}")
    obj = namespace[parts[0]]
    for part in parts[1:]:
        obj = getattr(obj, part)

    obj_type = type(obj)
    info = {
        "name": name,
        "type": f"{obj_type.__module__}.{obj_type.__qualname__}",
    }
    pd = sys.modules.get("pandas")
    np = sys.modules.get("numpy")

    if pd is not None and isinstance(obj, pd.DataFrame):
        info["shape"] = list(obj.shape)
        info["columns"] = {
            str(column): str(dtype)
            for column, dtype in list(obj.dtypes.items())[:200]
        }
        missing = obj.isna().sum()
        info["missing_values"] = {
            str(column): int(count)
            for column, count in missing.items()
            if count
        }
        with pd.option_context(
            "display.max_columns", 30, "display.width", 250
        ):
            info["head"] = short(obj.head(10).to_string(), 6000)
            try:
                info["describe"] = short(obj.describe().to_string(), 6000)
            except Exception:
                pass
    elif pd is not None and isinstance(obj, pd.Series):
        info["shape"] = list(obj.shape)
        info["dtype"] = str(obj.dtype)
        info["missing_values"] = int(obj.isna().sum())
        info["head"] = short(obj.head(10).to_string())
        try:
            info["describe"] = short(obj.describe().to_string())
        except Exception:
            pass
    elif np is not None and isinstance(obj, np.ndarray):
        info["shape"] = list(obj.shape)
        info["dtype"] = str(obj.dtype)
        if obj.size and np.issubdtype(obj.dtype, np.number):
            try:
                info["min"] = float(np.nanmin(obj))
                info["max"] = float(np.nanmax(obj))
                info["mean"] = float(np.nanmean(obj))
                info["nan_count"] = int(np.isnan(obj).sum())
            except Exception:
                pass
        info["preview"] = short(
            np.array2string(obj, threshold=100, max_line_width=120)
        )
    elif isinstance(obj, dict):
        info["length"] = len(obj)
        info["keys"] = short(repr(list(obj)[:50]))
        info["preview"] = short(repr(obj))
    elif isinstance(obj, (list, tuple, set, frozenset)):
        info["length"] = len(obj)
        info["preview"] = short(repr(obj))
    else:
        info["repr"] = short(repr(obj))

    return json.dumps(info, default=str)


def spyder_object_help(name, namespace):
    """Get the signature and docstring of ``name``, e.g. ``np.linspace``."""
    import importlib
    import inspect
    import json

    parts = name.split(".")
    if parts[0] in namespace:
        obj = namespace[parts[0]]
        rest = parts[1:]
    else:
        # Not defined in the console, e.g. pandas.DataFrame.merge
        for index in range(len(parts), 0, -1):
            try:
                obj = importlib.import_module(".".join(parts[:index]))
            except ImportError:
                continue
            rest = parts[index:]
            break
        else:
            raise NameError(f"Can't find {name!r}")
    for part in rest:
        obj = getattr(obj, part)

    info = {"name": name, "type": type(obj).__name__}
    try:
        info["signature"] = f"{name}{inspect.signature(obj)}"
    except (TypeError, ValueError):
        pass

    doc = inspect.getdoc(obj) or ""
    info["doc"] = doc if len(doc) <= 8000 else doc[:8000] + "..."

    module_name = getattr(obj, "__module__", None) or getattr(
        obj, "__name__", None
    )
    if module_name:
        info["module"] = module_name
        try:
            package = importlib.import_module(module_name.split(".")[0])
        except Exception:
            package = None
        version = getattr(package, "__version__", None)
        if version:
            info["package_version"] = str(version)
    try:
        info["file"] = inspect.getsourcefile(obj)
    except TypeError:
        pass

    return json.dumps(info, default=str)


def spyder_input_history(count):
    """
    Get the last ``count`` inputs of the console's current session, oldest
    first.
    """
    import json

    from IPython import get_ipython

    # Session 0 is the current one, which is read from memory
    history = list(get_ipython().history_manager.get_range(0, raw=True))
    return json.dumps(
        [
            {"line": line, "input": source}
            for _session, line, source in history[-count:]
            if source.strip()
        ]
    )
