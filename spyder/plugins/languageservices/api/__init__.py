# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Public API of the language services plugin."""

from spyder.plugins.languageservices.api.errors import (
    DocumentNotOpenError,
    LanguageAlreadyRegisteredError,
    LanguageServicesError,
    ProviderAlreadyRegisteredError,
    ProviderError,
    ProviderNotFoundError,
    UnknownLanguageError,
)
from spyder.plugins.languageservices.api.languages import (
    Language,
    LanguageSpec,
)

__all__ = [
    "DocumentNotOpenError",
    "Language",
    "LanguageAlreadyRegisteredError",
    "LanguageServicesError",
    "LanguageSpec",
    "ProviderAlreadyRegisteredError",
    "ProviderError",
    "ProviderNotFoundError",
    "UnknownLanguageError",
]
