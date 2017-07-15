# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)


"""Code introspection and linting utillites."""

from spyder.config.base import DEV


# Language server communication verbosity at server logs.
TRACE = 'messages'
if DEV:
    TRACE = 'verbose'


# Spyder editor capabilities
EDITOR_CAPABILITES = {
    "workspace": {
        "applyEdit": True,
        "workspaceEdit": {
            "documentChanges": False
        },
        "didChangeConfiguration": {
            "dynamicRegistration": True
        },
        "didChangeWatchedFiles": {
            "dynamicRegistration": True
        },
        "symbol": {
            "dynamicRegistration": True
        },
        "executeCommand": {
            "dynamicRegistration": True
        }
    },
    "textDocument": {
        "synchronization": {
            "dynamicRegistration": True,
            "willSave": True,
            "willSaveWaitUntil": True,
            "didSave": True
        },
        "completion": {
            "dynamicRegistration": True,
            "completionItem": {
                "snippetSupport": True
            }
        },
        "hover": {
            "dynamicRegistration": True
        },
        "signatureHelp": {
            "dynamicRegistration": True
        },
        "references": {
            "dynamicRegistration": True
        },
        "documentHighlight": {
            "dynamicRegistration": True
        },
        "documentSymbol": {
            "dynamicRegistration": True
        },
        "formatting": {
            "dynamicRegistration": True
        },
        "rangeFormatting": {
            "dynamicRegistration": True
        },
        "onTypeFormatting": {
            "dynamicRegistration": True
        },
        "definition": {
            "dynamicRegistration": True
        },
        "codeAction": {
            "dynamicRegistration": True
        },
        "codeLens": {
            "dynamicRegistration": True
        },
        "documentLink": {
            "dynamicRegistration": True
        },
        "rename": {
            "dynamicRegistration": True
        }
    }
}
