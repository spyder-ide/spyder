# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for marking plugin methods as exposed."""

# Local imports
from spyder.api.plugins import expose
from spyder.api.plugins.exposed import (
    ExposedSpec,
    get_exposed_methods,
    get_exposed_spec,
)


class Base:

    @expose
    def plain(self) -> str:
        """Exposed without options."""
        return "plain"

    @expose(name="renamed", read_only=True)
    def with_options(self) -> str:
        """Exposed with options."""
        return "options"

    @expose
    def overridden(self) -> str:
        """Exposed in the base class only."""

    def not_exposed(self) -> str:
        """Not exposed."""

    @property
    def broken(self):
        raise RuntimeError("Properties aren't evaluated")


class Child(Base):

    def overridden(self) -> str:
        """Overridden without the decorator."""


def test_expose_only_marks():
    """The decorator returns the same function, just marked."""
    assert Base().plain() == "plain"
    assert Base().with_options() == "options"
    assert get_exposed_spec(Base.plain) == ExposedSpec()
    assert get_exposed_spec(Base.with_options) == ExposedSpec(
        name="renamed", read_only=True
    )
    assert get_exposed_spec(Base.not_exposed) is None


def test_get_exposed_methods():
    assert set(get_exposed_methods(Base)) == {
        "plain",
        "with_options",
        "overridden",
    }

    # Overriding a method without the decorator stops exposing it
    assert set(get_exposed_methods(Child)) == {"plain", "with_options"}
