# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Summaries of profiling results, for the Profiler's exposed methods (e.g.
used by AI agents).
"""

# Standard library imports
from __future__ import annotations

from collections.abc import Callable
import pstats
from typing import Literal

# Time a function spent itself, in it and the functions it called, or the
# number of times it was called
SortKey = Literal["local", "total", "calls"]

# Function key used by pstats: (filename, line, name)
FunctionKey = tuple[str, int, str]


def make_is_library(
    is_builtin: Callable[[FunctionKey], bool],
) -> Callable[[FunctionKey], bool]:
    """
    Tell library code apart from the user's with the Profiler's
    ``is_builtin`` check, but counting code run directly in the console
    (e.g. profiled with ``%%profile``) as the user's.
    """

    def is_library(key: FunctionKey) -> bool:
        filename = key[0]
        if filename == "<string>" or filename.startswith("<ipython-input"):
            return False
        return is_builtin(key)

    return is_library


def is_profiler_frame(key: FunctionKey) -> bool:
    """
    Whether ``key`` is part of the profiling machinery (e.g. the ``exec``
    that runs the profiled code) rather than the code itself.
    """
    filename, line, name = key
    if name == "<method 'disable' of '_lsprof.Profiler' objects>":
        return True
    return (filename, line) == ("~", 0) and name.startswith(
        ("<built-in method exec>", "<built-in method builtins.exec>")
    )


def describe_function(
    key: FunctionKey,
    stats: pstats.Stats,
    is_library: Callable[[FunctionKey], bool],
) -> dict:
    """Timing of a function, as a dict for outside callers."""
    primitive_calls, calls, local_time, total_time, _callers = (
        stats.stats[key]
    )
    filename, line, name = key
    return {
        "function": name,
        "file": None if filename == "~" else filename,
        "line": line or None,
        "calls": calls,
        "primitive_calls": primitive_calls,
        "local_time": round(local_time, 6),
        "total_time": round(total_time, 6),
        "library": is_library(key),
    }


def summarize_profile(
    stats: pstats.Stats,
    is_library: Callable[[FunctionKey], bool],
    sort: SortKey = "local",
    limit: int = 20,
    include_libraries: bool = True,
) -> dict:
    """
    Summarize profiling results: the total time and the functions that took
    the most time.

    Parameters
    ----------
    stats : pstats.Stats
        Profiling results.
    is_library : Callable
        Whether a function is from a library (including the standard library
        and built-ins) rather than the user's code.
    sort : str
        Sort functions by ``local`` time (spent in the function itself),
        ``total`` time (including the functions it called) or ``calls``.
    limit : int
        Maximum number of functions.
    include_libraries : bool
        Whether to include library functions.
    """
    index = {"local": 2, "total": 3, "calls": 1}[sort]
    keys = [key for key in stats.stats if not is_profiler_frame(key)]
    if not include_libraries:
        keys = [key for key in keys if not is_library(key)]
    keys.sort(key=lambda key: stats.stats[key][index], reverse=True)

    return {
        "total_time": round(stats.total_tt, 6),
        "functions_called": len(stats.stats),
        "sorted_by": sort,
        "functions": [
            describe_function(key, stats, is_library)
            for key in keys[:limit]
        ],
    }


def find_functions(stats: pstats.Stats, function: str) -> list[FunctionKey]:
    """
    Find functions by name (e.g. ``solve``), qualified name or location
    (``file.py:12``, where the file can be a full path or its end).
    """
    if ":" in function and function.rsplit(":", 1)[1].isdigit():
        filename, line = function.rsplit(":", 1)
        return [
            key
            for key in stats.stats
            if key[1] == int(line)
            and (key[0] == filename or key[0].endswith(filename))
        ]

    return [
        key
        for key in stats.stats
        if key[2] == function or key[2].endswith("." + function)
    ]


def describe_callers_and_callees(
    key: FunctionKey,
    stats: pstats.Stats,
    is_library: Callable[[FunctionKey], bool],
    limit: int = 20,
) -> dict:
    """
    Timing of a function with the functions that called it and the ones it
    called, sorted by the time spent through each of them.
    """
    if not hasattr(stats, "all_callees"):
        stats.calc_callees()

    # Callers: time spent in this function when called from each one
    callers = [
        {
            **describe_function(caller, stats, is_library),
            "calls_to_function": timing[0],
            "time_in_function": round(timing[3], 6),
        }
        for caller, timing in stats.stats[key][4].items()
        if not is_profiler_frame(caller)
    ]
    callers.sort(key=lambda caller: caller["time_in_function"], reverse=True)

    # Callees: time spent in each one when called from this function
    callees = [
        {
            **describe_function(callee, stats, is_library),
            "calls_from_function": timing[0],
            "time_from_function": round(timing[3], 6),
        }
        for callee, timing in stats.all_callees.get(key, {}).items()
    ]
    callees.sort(key=lambda callee: callee["time_from_function"], reverse=True)

    return {
        **describe_function(key, stats, is_library),
        "callers": callers[:limit],
        "callees": callees[:limit],
    }
