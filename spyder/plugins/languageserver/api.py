# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Language server API.
"""

# Supported LSP programming languages
LSP_LANGUAGES = [
    'Bash',
    'C#',
    'Cpp',
    'CSS/LESS/SASS',
    'Go',
    'GraphQL',
    'Groovy',
    'Elixir',
    'Erlang',
    'Fortran',
    'Haxe',
    'HTML',
    'Java',
    'JavaScript',
    'JSON',
    'Julia',
    'Kotlin',
    'OCaml',
    'PHP',
    'R',
    'Rust',
    'Scala',
    'Swift',
    'TypeScript',
]


# ----------------------- INTERNAL CONSTANTS ------------------------
class ClientConstants:
    """Internal LSP Client constants."""

    CANCEL = 'lsp-cancel'
