# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""Fixtures for the Spyder Remote Client plugin tests."""

from __future__ import annotations
from concurrent.futures import Future
import os
import typing

import pytest

from spyder.api.asyncdispatcher import AsyncDispatcher
from spyder.plugins.remoteclient.plugin import RemoteClient

T = typing.TypeVar("T")

pytest_plugins = [
    "spyder.api.plugins.pytest",
    "spyder.plugins.remoteclient.tests.fixtures",
]

def await_future(future: Future[T], timeout=10) -> T:
    """Wait for a future to finish or timeout."""
    return future.result(timeout=timeout)


def run_async(func: typing.Callable[..., typing.Awaitable[T]], *args, **kwargs):
    """Run an async function in the event loop."""
    return AsyncDispatcher(loop="test")(func)(*args, **kwargs)


def mark_remote_test(func):
    remote_client_tests = os.environ.get(
        'SPYDER_TEST_REMOTE_CLIENT', False
    )
    return pytest.mark.skipif(
        remote_client_tests is False,
        reason="Skipping as SPYDER_TEST_REMOTE_CLIENT is not set"
    )(func)


@pytest.fixture(scope="session")
def plugins_cls():
    yield [("remote_client", RemoteClient)]
