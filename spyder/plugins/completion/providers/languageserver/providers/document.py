# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder Language Server Protocol Client document handler routines."""

# Standard library imports
import logging

# Third-party imports
from lsprotocol import types as lsp

# Local imports
from spyder.plugins.completion.providers.languageserver.providers.utils import (
    path_as_uri, process_uri)
from spyder.plugins.completion.providers.languageserver.decorators import (
    handles, send_request, send_notification)


LSP_COMPLETION = "LSP"

logger = logging.getLogger(__name__)


class DocumentProvider:
    def register_file(self, filename, codeeditor):
        filename = path_as_uri(filename)
        if filename not in self.watched_files:
            self.watched_files[filename] = []
        self.watched_files[filename].append(codeeditor)

    # ------------------------------------------------------------------
    # Diagnostics (server -> client notification)
    # ------------------------------------------------------------------

    @handles(lsp.TEXT_DOCUMENT_PUBLISH_DIAGNOSTICS)
    def process_document_diagnostics(
        self, params: lsp.PublishDiagnosticsParams, *args
    ) -> None:
        uri = params.uri
        diagnostics = params.diagnostics or []

        if uri in self.watched_files:
            for callback in self.watched_files[uri]:
                callback.handle_response(
                    lsp.TEXT_DOCUMENT_PUBLISH_DIAGNOSTICS,
                    diagnostics,
                )
        else:
            logger.debug('Received diagnostics for file not open: %s', uri)

    # ------------------------------------------------------------------
    # textDocument/didChange
    # ------------------------------------------------------------------

    @send_notification(method=lsp.TEXT_DOCUMENT_DID_CHANGE)
    def document_changed(self, params):
        return lsp.DidChangeTextDocumentParams(
            text_document=lsp.VersionedTextDocumentIdentifier(
                uri=path_as_uri(params['file']),
                version=params['version'],
            ),
            content_changes=[
                lsp.TextDocumentContentChangeWholeDocument(
                    text=params['text'],
                )
            ],
        )

    # ------------------------------------------------------------------
    # textDocument/didOpen
    # ------------------------------------------------------------------

    @send_notification(method=lsp.TEXT_DOCUMENT_DID_OPEN)
    def document_open(self, editor_params):
        uri = path_as_uri(editor_params['file'])
        if uri not in self.watched_files:
            self.register_file(editor_params['file'], editor_params['codeeditor'])
        return lsp.DidOpenTextDocumentParams(
            text_document=lsp.TextDocumentItem(
                uri=uri,
                language_id=editor_params['language'],
                version=editor_params['version'],
                text=editor_params['text'],
            ),
        )

    # ------------------------------------------------------------------
    # textDocument/completion
    # ------------------------------------------------------------------

    @send_request(method=lsp.TEXT_DOCUMENT_COMPLETION)
    def document_completion_request(self, params):
        return lsp.CompletionParams(
            text_document=lsp.TextDocumentIdentifier(
                uri=path_as_uri(params['file']),
            ),
            position=lsp.Position(
                line=params['line'],
                character=params['column'],
            ),
        )

    @handles(lsp.TEXT_DOCUMENT_COMPLETION)
    def process_document_completion(self, response, req_id):
        if isinstance(response, lsp.CompletionList):
            items = response.items or []
        elif isinstance(response, list):
            items = response
        else:
            items = []

        cp = self.server_capabilites.completion_provider if self.server_capabilites else None
        must_resolve = bool(cp and cp.resolve_provider)

        # Annotate each item with provider metadata in .data
        result = []
        for item in items:
            # Preserve existing .data (server may have put something there)
            existing = item.data or {}
            item.data = dict(existing) if isinstance(existing, dict) else {}
            item.data['provider'] = LSP_COMPLETION
            item.data['resolve'] = must_resolve
            result.append(item)

        if req_id in self.req_reply:
            self.req_reply[req_id](
                lsp.TEXT_DOCUMENT_COMPLETION,
                result,
            )

    # ------------------------------------------------------------------
    # completionItem/resolve
    # ------------------------------------------------------------------

    @send_request(method=lsp.COMPLETION_ITEM_RESOLVE)
    def completion_resolve_request(self, params):
        return params['completion_item']

    @handles(lsp.COMPLETION_ITEM_RESOLVE)
    def handle_completion_resolve(self, response: lsp.CompletionItem, req_id):
        if req_id in self.req_reply:
            self.req_reply[req_id](
                lsp.COMPLETION_ITEM_RESOLVE,
                response,
            )

    # ------------------------------------------------------------------
    # textDocument/signatureHelp
    # ------------------------------------------------------------------

    @send_request(method=lsp.TEXT_DOCUMENT_SIGNATURE_HELP)
    def signature_help_request(self, params):
        return lsp.SignatureHelpParams(
            text_document=lsp.TextDocumentIdentifier(
                uri=path_as_uri(params['file']),
            ),
            position=lsp.Position(
                line=params['line'],
                character=params['column'],
            ),
        )

    @handles(lsp.TEXT_DOCUMENT_SIGNATURE_HELP)
    def process_signature_completion(
        self, response: lsp.SignatureHelp, req_id
    ):
        if req_id in self.req_reply:
            self.req_reply[req_id](
                lsp.TEXT_DOCUMENT_SIGNATURE_HELP,
                response,
            )

    # ------------------------------------------------------------------
    # textDocument/hover
    # ------------------------------------------------------------------

    @send_request(method=lsp.TEXT_DOCUMENT_HOVER)
    def hover_request(self, params):
        return lsp.HoverParams(
            text_document=lsp.TextDocumentIdentifier(
                uri=path_as_uri(params['file']),
            ),
            position=lsp.Position(
                line=params['line'],
                character=params['column'],
            ),
        )

    @handles(lsp.TEXT_DOCUMENT_HOVER)
    def process_hover_result(self, result: lsp.Hover, req_id):
        contents = None
        if result is not None:
            raw = result.contents
            if isinstance(raw, lsp.MarkupContent):
                contents = raw.value
            elif isinstance(raw, lsp.MarkedStringWithLanguage):
                contents = raw.value
            elif isinstance(raw, str):
                contents = raw
            elif isinstance(raw, (list, tuple)):
                parts = []
                for entry in raw:
                    if isinstance(entry, lsp.MarkupContent):
                        parts.append(entry.value)
                    elif isinstance(entry, lsp.MarkedStringWithLanguage):
                        parts.append(entry.value)
                    elif isinstance(entry, str):
                        parts.append(entry)
                    else:
                        parts.append(str(entry))
                contents = '\n\n'.join(parts)

        if req_id in self.req_reply:
            self.req_reply[req_id](
                lsp.TEXT_DOCUMENT_HOVER,
                contents,
            )

    # ------------------------------------------------------------------
    # textDocument/documentSymbol
    # ------------------------------------------------------------------

    @send_request(method=lsp.TEXT_DOCUMENT_DOCUMENT_SYMBOL)
    def document_symbol_request(self, params):
        return lsp.DocumentSymbolParams(
            text_document=lsp.TextDocumentIdentifier(
                uri=path_as_uri(params['file']),
            ),
        )

    @handles(lsp.TEXT_DOCUMENT_DOCUMENT_SYMBOL)
    def process_document_symbol_request(self, result, req_id):
        # result is list[DocumentSymbol] | list[SymbolInformation] | None
        symbols = result or []
        if req_id in self.req_reply:
            self.req_reply[req_id](
                lsp.TEXT_DOCUMENT_DOCUMENT_SYMBOL,
                symbols,
            )

    # ------------------------------------------------------------------
    # textDocument/definition
    # ------------------------------------------------------------------

    @send_request(method=lsp.TEXT_DOCUMENT_DEFINITION)
    def go_to_definition_request(self, params):
        return lsp.DefinitionParams(
            text_document=lsp.TextDocumentIdentifier(
                uri=path_as_uri(params['file']),
            ),
            position=lsp.Position(
                line=params['line'],
                character=params['column'],
            ),
        )

    @handles(lsp.TEXT_DOCUMENT_DEFINITION)
    def process_go_to_definition(self, result, req_id):
        # Normalise to a single location (first item if list)
        location = None
        if isinstance(result, list) and result:
            location = result[0]
        elif isinstance(result, (lsp.Location, lsp.LocationLink)):
            location = result

        if req_id in self.req_reply:
            self.req_reply[req_id](
                lsp.TEXT_DOCUMENT_DEFINITION,
                location,
            )

    # ------------------------------------------------------------------
    # textDocument/foldingRange
    # ------------------------------------------------------------------

    @send_request(method=lsp.TEXT_DOCUMENT_FOLDING_RANGE)
    def folding_range_request(self, params):
        return lsp.FoldingRangeParams(
            text_document=lsp.TextDocumentIdentifier(
                uri=path_as_uri(params['file']),
            ),
        )

    @handles(lsp.TEXT_DOCUMENT_FOLDING_RANGE)
    def process_folding_range(self, result, req_id):
        ranges = result or []
        if req_id in self.req_reply:
            self.req_reply[req_id](
                lsp.TEXT_DOCUMENT_FOLDING_RANGE,
                ranges,
            )

    # ------------------------------------------------------------------
    # textDocument/willSave
    # ------------------------------------------------------------------

    @send_notification(method=lsp.TEXT_DOCUMENT_WILL_SAVE)
    def document_will_save_notification(self, params):
        return lsp.WillSaveTextDocumentParams(
            text_document=lsp.TextDocumentIdentifier(
                uri=path_as_uri(params['file']),
            ),
            reason=lsp.TextDocumentSaveReason(params['reason']),
        )

    # ------------------------------------------------------------------
    # textDocument/didSave
    # ------------------------------------------------------------------

    @send_notification(method=lsp.TEXT_DOCUMENT_DID_SAVE)
    def document_did_save_notification(self, params):
        return lsp.DidSaveTextDocumentParams(
            text_document=lsp.TextDocumentIdentifier(
                uri=path_as_uri(params['file']),
            ),
            text=params.get('text'),
        )

    # ------------------------------------------------------------------
    # textDocument/didClose
    # ------------------------------------------------------------------

    @send_notification(method=lsp.TEXT_DOCUMENT_DID_CLOSE)
    def document_did_close(self, params):
        codeeditor = params['codeeditor']
        filename = path_as_uri(params['file'])

        if filename not in self.watched_files:
            return None  # Nothing to close, cancel.

        editors = self.watched_files[filename]
        if len(editors) > 1:
            # Other editors still have the file open; just deregister this one.
            for i, editor in enumerate(editors):
                if id(codeeditor) == id(editor):
                    editors.pop(i)
                    break
            return None  # Don't send didClose to server yet.

        # Last editor, deregister and send didClose.
        for i, editor in enumerate(editors):
            if id(codeeditor) == id(editor):
                editors.pop(i)
                break
        if not editors:
            self.watched_files.pop(filename, None)

        return lsp.DidCloseTextDocumentParams(
            text_document=lsp.TextDocumentIdentifier(uri=filename),
        )

    # ------------------------------------------------------------------
    # textDocument/formatting
    # ------------------------------------------------------------------

    @send_request(method=lsp.TEXT_DOCUMENT_FORMATTING)
    def document_formatting_request(self, params):
        return lsp.DocumentFormattingParams(
            text_document=lsp.TextDocumentIdentifier(
                uri=path_as_uri(params['file']),
            ),
            options=lsp.FormattingOptions(**params['options']),
        )

    @handles(lsp.TEXT_DOCUMENT_FORMATTING)
    def process_document_formatting(self, result, req_id):
        edits = result or []
        if req_id in self.req_reply:
            self.req_reply[req_id](
                lsp.TEXT_DOCUMENT_FORMATTING,
                edits,
            )

    # ------------------------------------------------------------------
    # textDocument/rangeFormatting
    # ------------------------------------------------------------------

    @send_request(method=lsp.TEXT_DOCUMENT_RANGE_FORMATTING)
    def document_range_formatting_request(self, params):
        rng = params['range']
        return lsp.DocumentRangeFormattingParams(
            text_document=lsp.TextDocumentIdentifier(
                uri=path_as_uri(params['file']),
            ),
            options=lsp.FormattingOptions(**params['options']),
            range=lsp.Range(
                start=lsp.Position(
                    line=rng['start']['line'],
                    character=rng['start']['character'],
                ),
                end=lsp.Position(
                    line=rng['end']['line'],
                    character=rng['end']['character'],
                ),
            ),
        )

    @handles(lsp.TEXT_DOCUMENT_RANGE_FORMATTING)
    def process_document_range_formatting(self, result, req_id):
        edits = result or []
        if req_id in self.req_reply:
            self.req_reply[req_id](
                lsp.TEXT_DOCUMENT_RANGE_FORMATTING,
                edits,
            )
