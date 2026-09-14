# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder extensions to the LSP symbol kinds and their icons."""

from enum import IntEnum

from lsprotocol.types import SymbolKind


class SpyderSymbolKind(IntEnum):
    """Symbol kinds ``pyls_spyder`` reports beyond the LSP specification."""

    #: Block comments shown in the outline explorer.
    BlockComment = 224
    #: Code cells shown in the outline explorer.
    Cell = 225


SYMBOL_KIND_ICON = {
    SymbolKind.File: "file",
    SymbolKind.Module: "module",
    SymbolKind.Namespace: "namespace",
    SymbolKind.Package: "package",
    SymbolKind.Class: "class",
    SymbolKind.Method: "method",
    SymbolKind.Property: "property",
    SymbolKind.Field: "field",
    SymbolKind.Constructor: "constructor",
    SymbolKind.Enum: "enum",
    SymbolKind.Interface: "interface",
    SymbolKind.Function: "function",
    SymbolKind.Variable: "variable",
    SymbolKind.Constant: "constant",
    SymbolKind.String: "string",
    SymbolKind.Number: "number",
    SymbolKind.Boolean: "boolean",
    SymbolKind.Array: "array",
    SymbolKind.Object: "object",
    SymbolKind.Key: "key",
    SymbolKind.Null: "null",
    SymbolKind.EnumMember: "enum_member",
    SymbolKind.Struct: "struct",
    SymbolKind.Event: "event",
    SymbolKind.Operator: "operator",
    SymbolKind.TypeParameter: "type_parameter",
    SpyderSymbolKind.BlockComment: "blockcomment",
    SpyderSymbolKind.Cell: "cell",
}
"""Icon identifier of every symbol kind."""
