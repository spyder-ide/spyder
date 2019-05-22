# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)


"""
LSP client, code introspection and linting utilities.
"""

from spyder.config.base import DEV


# Language server communication verbosity at server logs.
TRACE = 'messages'
if DEV:
    TRACE = 'verbose'

# Supported LSP programming languages
LSP_LANGUAGES = [
    'C#', 'CSS/LESS/SASS', 'Go', 'GraphQL', 'Groovy', 'Haxe', 'HTML',
    'Java', 'JavaScript', 'JSON', 'Julia', 'OCaml', 'PHP',
    'Rust', 'Scala', 'Swift', 'TypeScript', 'Erlang', 'Fortran',
    'Elixir'
]

# -------------------- CLIENT CONFIGURATION SETTINGS --------------------------

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

CLIENT_CAPABILITES = {
    "workspace": WORKSPACE_CAPABILITIES,
    "textDocument": TEXT_EDITOR_CAPABILITES
}


# -------------------- SERVER CONFIGURATION SETTINGS --------------------------

# Text document synchronization mode constants

class TextDocumentSyncKind:
    """Text document synchronization modes supported by a lsp-server"""
    NONE = 0  # Text synchronization is not supported
    FULL = 1  # Text synchronization requires all document contents
    INCREMENTAL = 2  # Partial text synchronization is supported


# Save options.

SAVE_OPTIONS = {
    # The client is supposed to include the content on save.
    'includeText': True
}

# Text synchronization capabilities

TEXT_DOCUMENT_SYNC_OPTIONS = {
    # Open and close notifications are sent to the server.
    'openClose': True,

    # Change notifications are sent to the server.
    # See TextDocumentSyncKind.NONE, TextDocumentSyncKind.FULL
    # and TextDocumentSyncKind.INCREMENTAL.
    'change': TextDocumentSyncKind.NONE,

    # Will save notifications are sent to the server.
    'willSave': False,

    # Will save wait until requests are sent to the server.
    'willSaveWaitUntil': False,

    # Save notifications are sent to the server.
    'save': SAVE_OPTIONS
}


# Code completion options

COMPLETION_OPTIONS = {
    # The server provides support to resolve additional
    # information for a completion item.
    'resolveProvider': False,

    # The characters that trigger completion automatically.
    'triggerCharacters': []
}

# Signature help options

SIGNATURE_HELP_OPTIONS = {
    # The characters that trigger signature help automatically.
    'triggerCharacters': []
}

# Code lens options

CODE_LENS_OPTIONS = {
    # Code lens has a resolve provider as well.
    'resolveProvider': False
}

# Format document on type options

DOCUMENT_ON_TYPE_FORMATTING_OPTIONS = {
    # A character on which formatting should be triggered, like `}`.
    'firstTriggerCharacter': None,

    # More trigger characters.
    'moreTriggerCharacter': [],
}


# Document link options

DOCUMENT_LINK_OPTIONS = {
    # Document links have a resolve provider as well.
    'resolveProvider': False
}

# Execute command options.

EXECUTE_COMMAND_OPTIONS = {
    # The commands to be executed on the server
    'commands': []
}


# Server available capabilites options as defined by the protocol.

SERVER_CAPABILITES = {
    # Defines how text documents are synced.
    # Is either a detailed structure defining each notification or
    # for backwards compatibility the TextDocumentSyncKind number.
    'textDocumentSync': TEXT_DOCUMENT_SYNC_OPTIONS,

    # The server provides hover support.
    'hoverProvider': False,

    # The server provides completion support.
    'completionProvider': COMPLETION_OPTIONS,

    # The server provides signature help support.
    'signatureHelpProvider': SIGNATURE_HELP_OPTIONS,

    # The server provides goto definition support.
    'definitionProvider': False,

    # The server provides find references support.
    'referencesProvider': False,

    # The server provides document highlight support.
    'documentHighlightProvider': False,

    # The server provides document symbol support.
    'documentSymbolProvider': False,

    # The server provides workspace symbol support.
    'workspaceSymbolProvider': False,

    # The server provides code actions.
    'codeActionProvider': False,

    # The server provides code lens.
    'codeLensProvider': CODE_LENS_OPTIONS,

    # The server provides document formatting.
    'documentFormattingProvider': False,

    # The server provides document range formatting.
    'documentRangeFormattingProvider': False,

    # The server provides document formatting on typing.
    'documentOnTypeFormattingProvider': DOCUMENT_ON_TYPE_FORMATTING_OPTIONS,

    # The server provides rename support.
    'renameProvider': False,

    # The server provides document link support.
    'documentLinkProvider': DOCUMENT_LINK_OPTIONS,

    # The server provides execute command support.
    'executeCommandProvider': EXECUTE_COMMAND_OPTIONS,

    # Experimental server capabilities.
    'experimental': None
}


class LSPEventTypes:
    """Language Server Protocol event types."""
    DOCUMENT = 'textDocument'
    WORKSPACE = 'workspace'
    WINDOW = 'window'
    CODE_LENS = 'codeLens'


class LSPRequestTypes:
    """Language Server Protocol request/response types."""
    # General requests
    INITIALIZE = 'initialize'
    SHUTDOWN = 'shutdown'
    EXIT = 'exit'
    CANCEL_REQUEST = '$/cancelRequest'
    # Window requests
    WINDOW_SHOW_MESSAGE = 'window/showMessage'
    WINDOW_SHOW_MESSAGE_REQUEST = 'window/showMessageRequest'
    WINDOW_LOG_MESSAGE = 'window/logMessage'
    TELEMETRY_EVENT = 'telemetry/event'
    # Client capabilities requests
    CLIENT_REGISTER_CAPABILITY = 'client/registerCapability'
    CLIENT_UNREGISTER_CAPABILITY = 'client/unregisterCapability'
    # Workspace requests
    WORKSPACE_CONFIGURATION_CHANGE = 'workspace/didChangeConfiguration'
    WORKSPACE_WATCHED_FILES_UPDATE = 'workspace/didChangeWatchedFiles'
    WORKSPACE_SYMBOL = 'workspace/symbol'
    WORKSPACE_EXECUTE_COMMAND = 'workspace/executeCommand'
    WORKSPACE_APPLY_EDIT = 'workspace/applyEdit'
    # Document requests
    DOCUMENT_PUBLISH_DIAGNOSTICS = 'textDocument/publishDiagnostics'
    DOCUMENT_DID_OPEN = 'textDocument/didOpen'
    DOCUMENT_DID_CHANGE = 'textDocument/didChange'
    DOCUMENT_WILL_SAVE = 'textDocument/willSave'
    DOCUMENT_WILL_SAVE_UNTIL = 'textDocument/willSaveWaitUntil'
    DOCUMENT_DID_SAVE = 'textDocument/didSave'
    DOCUMENT_DID_CLOSE = 'textDocument/didClose'
    DOCUMENT_COMPLETION = 'textDocument/completion'
    COMPLETION_RESOLVE = 'completionItem/resolve'
    DOCUMENT_HOVER = 'textDocument/hover'
    DOCUMENT_SIGNATURE = 'textDocument/signatureHelp'
    DOCUMENT_REFERENCES = ' textDocument/references'
    DOCUMENT_HIGHLIGHT = 'textDocument/documentHighlight'
    DOCUMENT_SYMBOL = 'textDocument/documentSymbol'
    DOCUMENT_FORMATTING = 'textDocument/formatting'
    DOCUMENT_RANGE_FORMATTING = 'textDocument/rangeFormatting'
    DOCUMENT_ON_TYPE_FORMATTING = 'textDocument/onTypeFormatting'
    DOCUMENT_DEFINITION = 'textDocument/definition'
    DOCUMENT_CODE_ACTION = 'textDocument/codeAction'
    DOCUMENT_CODE_LENS = 'textDocument/codeLens'
    CODE_LENS_RESOLVE = 'codeLens/resolve'
    DOCUMENT_LINKS = 'textDocument/documentLink'
    DOCUMENT_LINK_RESOLVE = 'documentLink/resolve'
    DOCUMENT_RENAME = 'textDocument/rename'

# -------------------- LINTING RESPONSE RELATED VALUES ------------------------


class DiagnosticSeverity:
    """LSP diagnostic severity levels."""
    ERROR = 1
    WARNING = 2
    INFORMATION = 3
    HINT = 4

# ----------------- AUTO-COMPLETION RESPONSE RELATED VALUES -------------------


class CompletionItemKind:
    """LSP completion element categories."""
    TEXT = 1
    METHOD = 2
    FUNCTION = 3
    CONSTRUCTOR = 4
    FIELD = 5
    VARIABLE = 6
    CLASS = 7
    INTERFACE = 8
    MODULE = 9
    PROPERTY = 10
    UNIT = 11
    VALUE = 12
    ENUM = 13
    KEYWORD = 14
    SNIPPET = 15
    COLOR = 16
    FILE = 17
    REFERENCE = 18


class InsertTextFormat:
    """LSP completion text interpretations."""
    PLAIN_TEXT = 1
    SNIPPET = 2

# ----------------- SAVING REQUEST RELATED VALUES -------------------


class TextDocumentSaveReason:
    """LSP text document saving action causes."""
    MANUAL = 1
    AFTER_DELAY = 2
    FOCUS_OUT = 3

# ----------------------- INTERNAL CONSTANTS ------------------------


class ClientConstants:
    """Internal LSP Client constants."""
    CANCEL = 'lsp-cancel'
