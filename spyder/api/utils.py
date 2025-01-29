# -*- coding: utf-8 -*-
#
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
API utilities.
"""
from abc import ABCMeta as BaseABCMeta


def get_class_values(cls):
    """
    Get the attribute values for the class enumerations used in our API.

    Idea from: https://stackoverflow.com/a/17249228/438386
    """
    return [v for (k, v) in cls.__dict__.items() if k[:1] != '_']


class PrefixNode:
    """Utility class used to represent a prefixed string tuple."""

    def __init__(self, path=None):
        self.children = {}
        self.path = path

    def __iter__(self):
        prefix = [((self.path,), self)]
        while prefix != []:
            current_prefix, node = prefix.pop(0)
            prefix += [(current_prefix + (c,), node.children[c])
                       for c in node.children]
            yield current_prefix

    def add_path(self, path):
        prefix, *rest = path
        if prefix not in self.children:
            self.children[prefix] = PrefixNode(prefix)

        if len(rest) > 0:
            child = self.children[prefix]
            child.add_path(rest)


class PrefixedTuple(PrefixNode):
    """Utility class to store and iterate over prefixed string tuples."""

    def __iter__(self):
        for key in self.children:
            child = self.children[key]
            for prefix in child:
                yield prefix


class classproperty(property):
    """
    Decorator to declare class constants as properties that require additional
    computation.

    Taken from: https://stackoverflow.com/a/7864317/438386
    """

    def __get__(self, cls, owner):
        return classmethod(self.fget).__get__(None, owner)()


class DummyAttribute:
    """
    Dummy class to mark abstract attributes.
    """
    pass


def abstract_attribute(obj=None):
    """
    Decorator to mark abstract attributes. Must be used in conjunction with the
    ABCMeta metaclass.
    """
    if obj is None:
        obj = DummyAttribute()
    obj.__is_abstract_attribute__ = True
    return obj


class ABCMeta(BaseABCMeta):
    """
    Metaclass to mark abstract classes.

    Adds support for abstract attributes. If a class has abstract attributes
    and is instantiated, a NotImplementedError is raised.

    Usage
    -----
    class MyABC(metaclass=ABCMeta):
        @abstract_attribute
        def my_abstract_attribute(self):
            pass

    class MyClassOK(MyABC):
        def __init__(self):
            self.my_abstract_attribute = 1

    class MyClassNotOK(MyABC):
        pass

    Raises
    ------
    NotImplementedError
        When it's not possible to instantiate an abstract class with abstract
        attributes.
    """

    def __call__(cls, *args, **kwargs):
        # Collect all abstract-attribute names from the entire MRO
        abstract_attr_names = set()
        for base in cls.__mro__:
            for name, value in base.__dict__.items():
                if getattr(value, '__is_abstract_attribute__', False):
                    abstract_attr_names.add(name)

        for name, value in cls.__dict__.items():
            if not getattr(value, '__is_abstract_attribute__', False):
                abstract_attr_names.discard(name)

        if abstract_attr_names:
            raise NotImplementedError(
                "Can't instantiate abstract class "
                "{} with abstract attributes: {}".format(
                    cls.__name__,
                    ", ".join(abstract_attr_names)
                )
            )

        return super().__call__(*args, **kwargs)
