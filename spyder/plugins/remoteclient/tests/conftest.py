# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""Fixtures for the Spyder Remote Client plugin tests."""

from __future__ import annotations
from concurrent.futures import Future
import typing

import pytest

from spyder.api.plugins.tests import *  # noqa
from spyder.api.asyncdispatcher import AsyncDispatcher
from spyder.plugins.remoteclient.plugin import RemoteClient
from spyder.plugins.remoteclient.tests.fixtures import *  # noqa


T = typing.TypeVar("T")


def await_future(future: Future[T], timeout=10) -> T:
    """Wait for a future to finish or timeout."""
    return future.result(timeout=timeout)


def run_async(
    func: typing.Callable[..., typing.Awaitable[T]], *args, **kwargs
):
    """Run an async function in the event loop."""
    return AsyncDispatcher(loop="test")(func)(*args, **kwargs)


def mark_remote_test(func):
    """
    Decorator for tests that require --remote-client in order to run.
    """
    return pytest.mark.remote_test(func)


@pytest.fixture(scope="session")
def plugins_cls():
    yield [("remote_client", RemoteClient)]
