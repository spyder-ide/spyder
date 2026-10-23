# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for the summaries of profiling results."""

# Standard library imports
import cProfile
import pstats

# Third-party imports
import pytest

# Local imports
from spyder.plugins.profiler.summary import (
    describe_callers_and_callees,
    find_functions,
    make_is_library,
    summarize_profile,
)

CODE = """
def slow():
    return sum(i * i for i in range(200_000))

def fast():
    return 1

def main():
    for _ in range(3):
        slow()
        fast()
    return sorted(range(1000))

main()
"""


@pytest.fixture
def stats(tmp_path):
    """Results of profiling CODE like Spyder's ``%%profile`` magic."""
    filename = str(tmp_path / "profile.prof")
    namespace = {}
    cProfile.runctx(CODE, namespace, namespace, filename)
    stats = pstats.Stats(filename)
    stats.calc_callees()
    return stats


def is_builtin(key):
    """Like the Profiler's check: built-ins and non-file code."""
    return key[0] == "~" or key[0].startswith("<")


@pytest.fixture
def is_library():
    return make_is_library(is_builtin)


def test_summary(stats, is_library):
    summary = summarize_profile(stats, is_library, limit=50)
    names = [function["function"] for function in summary["functions"]]

    # Code profiled in the console is the user's, built-ins aren't
    slow = summary["functions"][names.index("slow")]
    assert slow["calls"] == 3
    assert slow["file"] == "<string>"
    assert slow["line"] == 2
    assert not slow["library"]
    assert slow["total_time"] >= slow["local_time"] > 0
    builtin_sum = summary["functions"][
        names.index("<built-in method builtins.sum>")
    ]
    assert builtin_sum["library"]
    assert builtin_sum["file"] is None

    # Profiling machinery is left out
    assert not any("exec" in name or "disable" in name for name in names)

    # Including the functions they call, the code calling main is first.
    # The order of the rest depends on timings, which can be off when the
    # machine is busy, so only check they're sorted.
    by_total = summarize_profile(stats, is_library, sort="total", limit=3)
    assert by_total["functions"][0]["function"] == "<module>"
    totals = [f["total_time"] for f in by_total["functions"]]
    assert totals == sorted(totals, reverse=True)

    by_calls = summarize_profile(stats, is_library, sort="calls", limit=1)
    assert by_calls["functions"][0]["function"] == "<genexpr>"

    user_code = summarize_profile(
        stats, is_library, include_libraries=False, limit=50
    )
    assert all(not f["library"] for f in user_code["functions"])
    assert {"slow", "fast", "main"} <= {
        f["function"] for f in user_code["functions"]
    }

    assert summary["total_time"] > 0
    assert len(summarize_profile(stats, is_library, limit=2)["functions"]) == 2


def test_find_functions(stats):
    assert [key[2] for key in find_functions(stats, "slow")] == ["slow"]
    assert [key[2] for key in find_functions(stats, "<string>:5")] == ["fast"]
    assert find_functions(stats, "missing") == []


def test_callers_and_callees(stats, is_library):
    (main,) = find_functions(stats, "main")
    details = describe_callers_and_callees(main, stats, is_library)
    assert details["function"] == "main"
    assert [caller["function"] for caller in details["callers"]] == [
        "<module>"
    ]

    callees = {callee["function"]: callee for callee in details["callees"]}
    assert callees["slow"]["calls_from_function"] == 3
    assert callees["fast"]["calls_from_function"] == 3

    # Callees are sorted by the time spent through them
    assert details["callees"][0]["function"] == "slow"
