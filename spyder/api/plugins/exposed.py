# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Mark plugin methods that can be called from outside Spyder's plugins.

Plugins mark methods with :func:`expose` to make them available to clients
that drive Spyder from the outside, such as AI agents (through the MCP server
plugin). Plugins don't depend on those clients: the decorator only marks the
method, and clients collect the marked methods of every plugin with
:func:`get_exposed_methods`.

Exposed methods are a contract with outside callers, so they must:

* Take JSON-compatible arguments, with type hints (``str``, ``int``,
  ``float``, ``bool``, ``list``, ``dict``, ``Literal`` and optional values of
  those). Their descriptions come from the ``Parameters`` section of the
  docstring, in numpydoc format.
* Return data: ``None``, strings, numbers, booleans, lists and dicts of
  them, or :class:`Image` objects (also inside lists and dicts). Methods that
  take time (e.g. running code in a console) return a
  :class:`concurrent.futures.Future` that is resolved with the data later.
* Raise :class:`ExposedCallError` (or resolve their future with it) when the
  call can't be completed, with a message that tells the caller what to do.
* Never open dialogs or wait for user input, which would block Spyder.

Exposed methods always run in the main Qt thread.

Example
-------
A plugin exposes a method that returns data right away, and one that
finishes later::

    from concurrent.futures import Future

    from spyder.api.plugins import (
        ExposedCallError, SpyderDockablePlugin, expose
    )

    class MyPlugin(SpyderDockablePlugin):

        @expose(read_only=True)
        def list_items(self, pattern: str = "") -> list:
            \"\"\"
            List the items shown in My plugin.

            Parameters
            ----------
            pattern : str, optional
                Only list the items whose name contains it.
            \"\"\"
            return [
                {"name": item.name, "size": item.size}
                for item in self.get_widget().items
                if pattern in item.name
            ]

        @expose(destructive=True)
        def remove_item(self, name: str) -> Future:
            \"\"\"
            Remove an item from My plugin.

            Parameters
            ----------
            name : str
                Name of the item, as given by list_items.
            \"\"\"
            if name not in self.get_widget().names():
                raise ExposedCallError(
                    f"There's no item {name}. Use list_items to see them."
                )
            future = Future()
            self.get_widget().remove(
                name, on_done=lambda: future.set_result(None)
            )
            return future

The first line of the docstring, and its description of each parameter, is
what callers read to decide when and how to call the method, so write them
for someone that doesn't know Spyder's internals.

Working with the caller
-----------------------
Clients run exposed methods within :func:`calling_as`, which says who is
calling (a :class:`Caller`) and how to reach them while the method runs (a
:class:`CallContext`). Inside an exposed method:

* :func:`current_caller` tells callers apart, e.g. to only let an agent
  interrupt the code it started. It's ``None`` when the method isn't called
  from outside.
* :func:`current_call_context` lets the method ask the caller's user a
  question where they are already looking (e.g. an agent's chat), with
  :meth:`CallContext.ask_user`, and report what it's doing with
  :meth:`CallContext.report_progress`. Check
  :attr:`CallContext.can_ask_user` first: if the client can't ask, refuse
  changes that need the user's confirmation instead of making them::

      @expose(destructive=True)
      def reset_items(self) -> Future:
          \"\"\"Remove all the items from My plugin.\"\"\"
          context = current_call_context()
          if not context.can_ask_user:
              raise ExposedCallError(
                  "This needs the user's confirmation. Ask them to do it "
                  "in My plugin."
              )

          result = Future()

          def on_answer(answer):
              if answer.result() == _("Remove"):
                  self.get_widget().clear()
                  result.set_result(None)
              else:
                  result.set_exception(
                      ExposedCallError("The user chose not to do it.")
                  )

          context.ask_user(
              _("Remove all the items from My plugin?"),
              [_("Remove"), _("Cancel")],
          ).add_done_callback(on_answer)
          return result

Both are context variables, so read them when the method is called, not in
callbacks that run later. To call other exposed methods on behalf of the
same caller from such a callback, run them within
``calling_as(caller, context)`` again.
"""

# Standard library imports
from __future__ import annotations

from collections.abc import Callable, Iterator
from concurrent.futures import Future
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import functools
from typing import Any


@dataclass(frozen=True)
class ExposedSpec:
    """Options given to :func:`expose`, stored on the marked method."""

    name: str | None = None
    """
    Name for callers. By default, the method name. Set it to keep the name
    stable if the method is renamed.
    """

    description: str | None = None
    """Description for callers. By default, the method's docstring."""

    read_only: bool = False
    """Whether the method doesn't change any state."""

    destructive: bool = False
    """Whether the method may make changes that can't be undone."""


@dataclass
class Image:
    """An image returned by an exposed method."""

    data: bytes
    """Image data, e.g. the contents of a PNG file."""

    mime_type: str = "image/png"
    """MIME type of the data, e.g. ``image/png`` or ``image/svg+xml``."""


@dataclass(frozen=True)
class Caller:
    """An outside caller of exposed methods, e.g. an AI agent session."""

    id: str
    """Unique id of the caller."""

    name: str
    """Name shown to users, e.g. ``Agent 2``."""


class CallContext:
    """
    What an exposed method can do with the client that called it while it
    runs: ask the client's user a question where they're already looking
    (e.g. an AI agent's interface), and report progress.

    This base class is the one used when the client doesn't support it (or
    there's no client): it can't ask and ignores progress.
    """

    can_ask_user: bool = False
    """Whether the client can ask its user a question."""

    def ask_user(
        self,
        message: str,
        choices: list[str],
        title: str = "",
        default: str | None = None,
    ) -> Future:
        """
        Ask the client's user to pick one of ``choices``, with ``default``
        (one of them) picked at first, if given.

        Returns
        -------
        Future
            Resolved in the main Qt thread with the choice, or ``None`` if
            the user declined or dismissed the question (or the client can't
            ask).
        """
        future: Future = Future()
        future.set_result(None)
        return future

    def report_progress(self, message: str) -> None:
        """
        Tell the client what the call is doing, e.g. waiting for the user.
        It also keeps clients from giving up on calls that take a while.
        """


_current_caller: ContextVar[Caller | None] = ContextVar(
    "spyder_exposed_caller", default=None
)
_current_context: ContextVar[CallContext | None] = ContextVar(
    "spyder_exposed_call_context", default=None
)


def current_caller() -> Caller | None:
    """
    Return who is calling the exposed method that is running, or ``None`` if
    it's not called from outside (e.g. by the user through Spyder's
    interface).

    Methods that finish later (returning a future) must read it when they're
    called, not when they finish.
    """
    return _current_caller.get()


def current_call_context() -> CallContext:
    """
    Return the context of the call to the exposed method that is running,
    e.g. to ask the caller's user to confirm something. Like
    :func:`current_caller`, read it when the method is called.
    """
    return _current_context.get() or CallContext()


@contextmanager
def calling_as(
    caller: Caller | None, context: CallContext | None = None
) -> Iterator[None]:
    """
    Run exposed methods called inside this block on behalf of ``caller``,
    with ``context`` to reach it while they run.
    """
    token = _current_caller.set(caller)
    context_token = _current_context.set(context)
    try:
        yield
    finally:
        _current_context.reset(context_token)
        _current_caller.reset(token)


class ExposedCallError(Exception):
    """
    Error to report to the caller of an exposed method.

    Its message should explain what went wrong and, if possible, what the
    caller can do about it.
    """


def expose(
    func: Callable | None = None,
    *,
    name: str | None = None,
    description: str | None = None,
    read_only: bool = False,
    destructive: bool = False,
) -> Callable:
    """
    Mark a plugin method as callable from outside Spyder's plugins.

    The method itself doesn't change. Overriding a marked method in a
    subclass without the decorator stops exposing it.

    Parameters
    ----------
    func : Callable, optional
        Method to decorate, passed automatically when the decorator is used
        without arguments.
    name : str, optional
        Name for callers. By default, the method name.
    description : str, optional
        Description for callers. By default, the method's docstring without
        its sections (``Parameters``, ``Returns``, etc).
    read_only : bool, optional
        Whether the method doesn't change any state. The default is
        ``False``.
    destructive : bool, optional
        Whether the method may make changes that can't be undone. The
        default is ``False``.
    """
    if func is None:
        return functools.partial(
            expose,
            name=name,
            description=description,
            read_only=read_only,
            destructive=destructive,
        )

    func._spyder_exposed = ExposedSpec(
        name=name,
        description=description,
        read_only=read_only,
        destructive=destructive,
    )
    return func


def get_exposed_spec(func: Any) -> ExposedSpec | None:
    """Return the options of a method marked with :func:`expose`, if any."""
    spec = getattr(func, "_spyder_exposed", None)
    return spec if isinstance(spec, ExposedSpec) else None


def get_exposed_methods(
    cls: type,
) -> dict[str, tuple[Callable, ExposedSpec]]:
    """
    Return the methods of ``cls`` marked with :func:`expose`.

    Parameters
    ----------
    cls : type
        Class to inspect, usually a plugin class.

    Returns
    -------
    dict
        Maps the attribute name of each exposed method to the (unbound)
        function and its options.
    """
    methods = {}
    for attr_name in dir(cls):
        try:
            attr = getattr(cls, attr_name)
        except Exception:
            continue
        spec = get_exposed_spec(attr)
        if spec is not None and callable(attr):
            methods[attr_name] = (attr, spec)
    return methods
