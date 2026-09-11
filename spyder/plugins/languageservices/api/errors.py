# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Exceptions raised by the language services API."""


class LanguageServicesError(Exception):
    """Base class for every error raised by the language services API."""


class UnknownLanguageError(LanguageServicesError, LookupError):
    """No :class:`Language` member matches the requested lookup key."""


class LanguageAlreadyRegisteredError(LanguageServicesError, ValueError):
    """A :class:`Language` with the same name or extension already exists."""


class DocumentNotOpenError(LanguageServicesError, KeyError):
    """A request references a document uri that was never opened."""


class ProviderError(LanguageServicesError):
    """A provider cannot be registered, started or found."""


class ProviderNotFoundError(ProviderError, KeyError):
    """No provider is registered under the requested name."""


class ProviderAlreadyRegisteredError(ProviderError, ValueError):
    """A provider with the same name is already registered."""
