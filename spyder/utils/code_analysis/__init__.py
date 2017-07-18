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


# WorkspaceClientCapabilities define capabilities the
# editor / tool provides on the workspace

WORKSPACE_CAPABILITIES = {
    # The client supports applying batch edits to the workspace.
    # Request: An array of `TextDocumentEdit`s to express changes
    #          to n different text documents
    "applyEdit": True,

    # The client supports versioned document changes.
    "workspaceEdit": {
        "documentChanges": False
    },

    # Did change configuration notification supports dynamic registration.
    "didChangeConfiguration": {
        # Reload server settings dynamically
        "dynamicRegistration": True
    },

    # The watched files notification is sent from the client to the server
    # when the client detects changes to files watched by
    # the language client.
    "didChangeWatchedFiles": {
        # Can be turned on/off dynamically
        "dynamicRegistration": True
    },

    # The workspace symbol request is sent from the client to the server to
    # list project-wide symbols matching the query string.
    "symbol": {
        # Can be turned on/off dynamically
        "dynamicRegistration": True
    },

    # The workspace/executeCommand request is sent from the client to the
    # server to trigger command execution on the server. In most cases the
    # server creates a WorkspaceEdit structure and applies the changes to
    # the workspace using the request workspace/applyEdit which is sent from
    # the server to the client.
    "executeCommand": {
        # Can be turned on/off dynamically
        "dynamicRegistration": True
    }
}

# TextDocumentClientCapabilities define capabilities the editor / tool
# provides on text documents.

TEXT_EDITOR_CAPABILITES = {
    # Editor supports file watching and synchronization (Required)
    "synchronization": {
        # File synchronization can be turned on/off.
        "dynamicRegistration": True,

        # The client (Spyder) will send a willSave notification
        # to the server when a file is about to be saved.
        "willSave": True,

        # The client (Spyder) supports sending a will save request and
        # waits for a response providing text edits which will
        # be applied to the document before it is saved.
        "willSaveWaitUntil": True,

        # The client (Spyder) supports did save notifications.
        # The document save notification is sent from the client to
        # the server when the document was saved in the client.
        "didSave": True
    },

    # Editor supports code completion operations.
    # The Completion request is sent from the client to the server to
    # compute completion items at a given cursor position.
    "completion": {
        # Code completion can be turned on/off dynamically.
        "dynamicRegistration": True,

        # Client (Spyder) supports snippets as insert text.
        # A snippet can define tab stops and placeholders with `$1`, `$2`
        # and `${3:foo}`. `$0` defines the final tab stop, it defaults to
        # the end of the snippet. Placeholders with equal identifiers are
        # linked, that is typing in one will update others too.
        "completionItem": {
            "snippetSupport": True
        }
    },

    # The hover request is sent from the client to the server to request
    # hover information at a given text document position.
    "hover": {
        # Hover introspection can be turned on/off dynamically.
        "dynamicRegistration": True
    },

    # The signature help request is sent from the client to the server to
    # request signature information at a given cursor position.
    "signatureHelp": {
        # Function/Class/Method signature hinting can be turned on/off
        # dynamically.
        "dynamicRegistration": True
    },

    # Editor allows to find references.
    # The references request is sent from the client to the server to resolve
    # project-wide references for the symbol denoted by the given text
    # document position.
    "references": {
        # Find references can be turned on/off dynamically.
        "dynamicRegistration": True
    },

    # Editor allows to highlight different text sections at the same time.
    # The document highlight request is sent from the client to the server to
    # resolve a document highlights for a given text document position
    "documentHighlight": {
        # Code highlighting can be turned on/off dynamically.
        "dynamicRegistration": True
    },

    # Editor supports finding symbols on a document.
    # The document symbol request is sent from the client to the server to list
    # all symbols found in a given text document.
    "documentSymbol": {
        # Find symbols on document can be turned on/off dynamically.
        "dynamicRegistration": True
    },

    # Editor allows to autoformat all the document.
    # The document formatting request is sent from the server to the client to
    # format a whole document.
    "formatting": {
        # Document formatting can be turned on/off dynamically.
        "dynamicRegistration": True
    },

    # Editor can autoformat only a selected region on a document.
    # The document range formatting request is sent from the client to the
    # server to format a given range in a document.
    "rangeFormatting": {
        # Partial document formatting can be turned on/off dynamically.
        "dynamicRegistration": True
    },

    # Editor allows to format a document while an edit is taking place.
    # The document on type formatting request is sent from the client to the
    # server to format parts of the document during typing.
    "onTypeFormatting": {
        # On-Type formatting can be turned on/off dynamically.
        "dynamicRegistration": True
    },

    # Editor has an option to go to a function/class/method definition.
    # The goto definition request is sent from the client to the server to
    # resolve the definition location of a symbol at a given text document
    # position.
    "definition": {
        # Go-to-definition can be turned on/off dynamically.
        "dynamicRegistration": True
    },

    # Editor can give/highlight refactor tips/solutions.
    # The code action request is sent from the client to the server to compute
    # commands for a given text document and range. These commands are
    # typically code fixes to either fix problems or to beautify/refactor code.
    "codeAction": {
        # Code hints can be turned on/off dynamically.
        "dynamicRegistration": True
    },

    # Editor can display additional commands/statistics per each line.
    # The code lens request is sent from the client to the server to compute
    # code lenses for a given text document.
    # A code lens represents a command that should be shown along with
    # source text, like the number of references, a way to run tests, etc.
    "codeLens": {
        # Code lens can be turned on/off dynamically.
        "dynamicRegistration": True
    },

    # Editor allows to find cross-document link references.
    # The document links request is sent from the client to the server to
    # request the location of links in a document.
    # A document link is a range in a text document that links to an internal
    # or external resource, like another text document or a web site.
    "documentLink": {
        # Finding document cross-references can be turned on/off dynamically.
        "dynamicRegistration": True
    },

    # Editor allows to rename a variable/function/reference globally
    # on a document.
    # The rename request is sent from the client to the server to perform
    # a workspace-wide rename of a symbol.
    "rename": {
        "dynamicRegistration": True
    }
}


# Spyder editor and workspace capabilities

EDITOR_CAPABILITES = {
    "workspace": WORKSPACE_CAPABILITIES,
    "textDocument": TEXT_EDITOR_CAPABILITES
}
