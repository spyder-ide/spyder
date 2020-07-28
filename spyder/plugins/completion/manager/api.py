# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
LSP client, code introspection and linting utilities.
"""

from qtpy.QtCore import QObject, Signal
from spyder.api.plugins import SpyderPlugin


class SpyderCompletionPlugin(QObject, SpyderPlugin):
    """
    Spyder plugin API for completion clients.

    All completion clients must implement this interface in order to interact
    with Spyder CodeEditor and Projects manager.
    """

    # Use this signal to send a response back to the completion manager
    # str: Completion client name
    # int: Request sequence identifier
    # dict: Response dictionary
    sig_response_ready = Signal(str, int, dict)

    # Use this signal to indicate that the plugin is ready
    sig_plugin_ready = Signal(str)

    # ---------------------------- ATTRIBUTES ---------------------------------

    # Name of the completion service
    # Status: Required
    COMPLETION_CLIENT_NAME = None

    def __init__(self, parent):
        QObject.__init__(self, parent)
        SpyderPlugin.__init__(self, parent)
        self.main = parent

    def register_file(self, language, filename, codeeditor):
        """
        Register file to perform completions.
        If a language client is not available for a given file, then this
        method should keep a queue, such that files can be initialized once
        a server is available.

        Parameters
        ----------
        language: str
            Programming language of the given file
        filename: str
            Filename to register
        codeeditor: spyder.plugins.editor.widgets.codeeditor.CodeEditor
            Codeeditor to send the client configurations
        """
        pass

    def send_request(self, language, req_type, req, req_id):
        """
        Process completion/introspection request from Spyder.

        Parameters
        ----------
        language: str
            Programming language for the incoming request
        req_type: str
            Type of request, one of
            :class:`spyder.plugins.completion.CompletionTypes`
        req: dict
            Request body
            {
                'filename': str,
                **kwargs: request-specific parameters
            }
        req_id: int
            Request identifier for response
        """
        pass

    def send_notification(self, language, notification_type, notification):
        """
        Send notification to completion server based on Spyder changes.

        Parameters
        ----------
        language: str
            Programming language for the incoming request
        notification_type: str
            Type of request, one of
            :class:`spyder.plugins.completion.CompletionTypes`
        notification: dict
            Request body
            {
                'filename': str,
                **kwargs: request-specific parameters
            }
        """
        pass

    def send_response(self, response, resp_id):
        """
        Send response for server request.

        Parameters
        ----------
        response: dict
            Response body for server
            {
                **kwargs: response-specific keys
            }
        resp_id: int
            Request identifier for response
        """
        pass

    def broadcast_notification(self, notification_type, notification):
        """
        Send a broadcast notification across all programming languages.

        Parameters
        ----------
        req_type: str
            Type of request, one of
            :class:`spyder.plugins.completion.CompletionTypes`
        req: dict
            Request body
            {
                **kwargs: notification-specific parameters
            }
        req_id: int
            Request identifier for response, None if notification
        """
        pass

    def update_configuration(self):
        """Handle completion option configuration updates."""
        pass

    def project_path_update(self, project_path, update_kind):
        """
        Handle project path updates on Spyder.

        Parameters
        ----------
        project_path: str
            Path to the project folder modified
        update_kind: str
            Path update kind, one of
            :class:`spyder.plugins.completion.WorkspaceUpdateKind`
        """
        pass

    def start_client(self, language):
        """
        Start completions/introspection services for a given language.

        Parameters
        ----------
        language: str
            Programming language to start analyzing

        Returns
        -------
        bool
            True if language client could be started, otherwise False.
        """
        return False

    def stop_client(self, language):
        """
        Stop completions/introspection services for a given language.

        Parameters
        ----------
        language: str
            Programming language to stop analyzing
        """
        pass

    def start(self):
        """Start completion plugin."""
        self.sig_plugin_ready.emit(self.COMPLETION_CLIENT_NAME)

    def shutdown(self):
        """Stop completion plugin."""
        pass


# Supported LSP programming languages
LSP_LANGUAGES = [
    'Bash', 'C#', 'Cpp', 'CSS/LESS/SASS', 'Go', 'GraphQL', 'Groovy', 'Elixir',
    'Erlang', 'Fortran', 'Haxe', 'HTML', 'Java', 'JavaScript', 'JSON',
    'Julia', 'Kotlin', 'OCaml', 'PHP', 'R', 'Rust', 'Scala', 'Swift',
    'TypeScript'
]

# -------------------- WORKSPACE CONFIGURATION CONSTANTS ----------------------


class ResourceOperationKind:
    """LSP workspace resource operations."""
    # The client is able to create workspace files and folders
    CREATE = 'create'
    # The client is able to rename workspace files and folders
    RENAME = 'rename'
    # The client is able to delete workspace files and folders
    DELETE = 'delete'


class FileChangeType:
    CREATED = 1
    CHANGED = 2
    DELETED = 3


class FailureHandlingKind:
    """LSP workspace modification error codes."""
    # Applying the workspace change is simply aborted if one
    # of the changes provided fails. All operations executed before, stay.
    ABORT = 'abort'
    # All the operations succeed or no changes at all.
    TRANSACTIONAL = 'transactional'
    # The client tries to undo the applied operations, best effort strategy.
    UNDO = 'undo'
    # The textual changes are applied transactionally, whereas
    # creation/deletion/renaming operations are aborted.
    TEXT_ONLY_TRANSACTIONAL = 'textOnlyTransactional'


class SymbolKind:
    """LSP workspace symbol constants."""
    FILE = 1
    MODULE = 2
    NAMESPACE = 3
    PACKAGE = 4
    CLASS = 5
    METHOD = 6
    PROPERTY = 7
    FIELD = 8
    CONSTRUCTOR = 9
    ENUM = 10
    INTERFACE = 11
    FUNCTION = 12
    VARIABLE = 13
    CONSTANT = 14
    STRING = 15
    NUMBER = 16
    BOOLEAN = 17
    ARRAY = 18
    OBJECT = 19
    KEY = 20
    NULL = 21
    ENUM_MEMBER = 22
    STRUCT = 23
    EVENT = 24
    OPERATOR = 25
    TYPE_PARAMETER = 26


# -------------------- CLIENT CONFIGURATION SETTINGS --------------------------

# WorkspaceClientCapabilities define capabilities the
# editor / tool provides on the workspace

WORKSPACE_CAPABILITIES = {
    # The client supports applying batch edits to the workspace.
    # Request: An array of `TextDocumentEdit`s to express changes
    #          to n different text documents
    "applyEdit": True,

    # Workspace edition settings
    "workspaceEdit": {
        # The client supports versioned document changes.
        "documentChanges": True,
        # The resource operations that the client supports
        "resourceOperations": [ResourceOperationKind.CREATE,
                               ResourceOperationKind.RENAME,
                               ResourceOperationKind.DELETE],
        # Failure handling strategy applied by the client.
        "failureHandling": FailureHandlingKind.TRANSACTIONAL
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
        "dynamicRegistration": True,
        # Specific capabilities for the `SymbolKind` in the `workspace/symbol`
        # request.
        "symbolKind": {
            # The symbol kind values the client supports.
            "valueSet": [value for value in SymbolKind.__dict__.values()
                         if isinstance(value, int)]
        }
    },
    # The client has support for workspace folders.
    "workspaceFolders": True,
    # The client supports `workspace/configuration` requests.
    "configuration": True
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

# Workspace options.

WORKSPACE_OPTIONS = {
    # The server has support for workspace folders
    'workspaceFolders': {
        'supported': False,
        'changeNotifications': False
    }
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

    # Workspace specific server capabillities.
    'workspace': WORKSPACE_OPTIONS,

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
    INITIALIZED = 'initialized'
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
    WORKSPACE_FOLDERS = 'workspace/workspaceFolders'
    WORKSPACE_FOLDERS_CHANGE = 'workspace/didChangeWorkspaceFolders'
    WORKSPACE_CONFIGURATION = 'workspace/configuration'
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
    DOCUMENT_FOLDING_RANGE = 'textDocument/foldingRange'
    DOCUMENT_RANGE_FORMATTING = 'textDocument/rangeFormatting'
    DOCUMENT_ON_TYPE_FORMATTING = 'textDocument/onTypeFormatting'
    DOCUMENT_DEFINITION = 'textDocument/definition'
    DOCUMENT_CODE_ACTION = 'textDocument/codeAction'
    DOCUMENT_CODE_LENS = 'textDocument/codeLens'
    CODE_LENS_RESOLVE = 'codeLens/resolve'
    DOCUMENT_LINKS = 'textDocument/documentLink'
    DOCUMENT_LINK_RESOLVE = 'documentLink/resolve'
    DOCUMENT_RENAME = 'textDocument/rename'
    # Spyder extensions to LSP
    DOCUMENT_CURSOR_EVENT = 'textDocument/cursorEvent'

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

# ----------------------- WORKSPACE UPDATE CONSTANTS ----------------


class WorkspaceUpdateKind:
    ADDITION = 'addition'
    DELETION = 'deletion'
