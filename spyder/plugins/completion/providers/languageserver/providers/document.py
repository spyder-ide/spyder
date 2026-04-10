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
from spyder.plugins.completion.api import (
    CompletionRequestTypes, InsertTextFormat, CompletionItemKind,
    ClientConstants)
from spyder.plugins.completion.providers.languageserver.providers.utils import (
    path_as_uri, process_uri, snake_to_camel)
from spyder.plugins.completion.providers.languageserver.decorators import (
    handles, send_request, send_notification)


LSP_COMPLETION = "LSP"

logger = logging.getLogger(__name__)


def _completion_item_to_dict(item: lsp.CompletionItem, must_resolve: bool) -> dict:
    """Convert a lsprotocol CompletionItem to Spyder's internal dict format."""
    kind = item.kind
    kind_value = kind.value if kind is not None else CompletionItemKind.TEXT

    fmt = item.insert_text_format
    if fmt is None:
        insert_fmt = InsertTextFormat.PLAIN_TEXT
    else:
        insert_fmt = fmt.value

    doc = item.documentation
    if isinstance(doc, lsp.MarkupContent):
        doc_str = doc.value
    else:
        doc_str = doc or ''

    return {
        'label': item.label,
        'kind': kind_value,
        'detail': item.detail or '',
        'documentation': doc_str,
        'sortText': item.sort_text or item.label,
        'filterText': item.filter_text or item.label,
        'insertTextFormat': insert_fmt,
        'insertText': item.insert_text or item.label,
        'provider': LSP_COMPLETION,
        'resolve': must_resolve,
    }


class DocumentProvider:
    def register_file(self, filename, codeeditor):
        filename = path_as_uri(filename)
        if filename not in self.watched_files:
            self.watched_files[filename] = []
        self.watched_files[filename].append(codeeditor)

    # ------------------------------------------------------------------
    # Diagnostics (server -> client notification)
    # ------------------------------------------------------------------

    @handles(CompletionRequestTypes.DOCUMENT_PUBLISH_DIAGNOSTICS)
    def process_document_diagnostics(
        self, params: lsp.PublishDiagnosticsParams, *args
    ) -> None:
        uri = params.uri
        diagnostics = []
        for d in (params.diagnostics or []):
            severity = d.severity
            diag = {
                'range': {
                    'start': {
                        'line': d.range.start.line,
                        'character': d.range.start.character,
                    },
                    'end': {
                        'line': d.range.end.line,
                        'character': d.range.end.character,
                    },
                },
                'code': d.code,
                'source': d.source,
                'message': d.message,
                'severity': severity.value if severity is not None else 1,
            }
            diagnostics.append(diag)

        if uri in self.watched_files:
            for callback in self.watched_files[uri]:
                callback.handle_response(
                    CompletionRequestTypes.DOCUMENT_PUBLISH_DIAGNOSTICS,
                    {'params': diagnostics},
                )
        else:
            logger.debug('Received diagnostics for file not open: %s', uri)

    # ------------------------------------------------------------------
    # textDocument/didChange
    # ------------------------------------------------------------------

    @send_notification(method=CompletionRequestTypes.DOCUMENT_DID_CHANGE)
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

    @send_notification(method=CompletionRequestTypes.DOCUMENT_DID_OPEN)
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

    @send_request(method=CompletionRequestTypes.DOCUMENT_COMPLETION)
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

    @handles(CompletionRequestTypes.DOCUMENT_COMPLETION)
    def process_document_completion(self, response, req_id):
        if isinstance(response, lsp.CompletionList):
            items = response.items or []
            is_incomplete = response.is_incomplete
        elif isinstance(response, list):
            items = response
            is_incomplete = False
        else:
            items = []
            is_incomplete = False

        must_resolve = self.server_capabilites.get(
            'completionProvider', {}
        ).get('resolveProvider', False)

        result = [_completion_item_to_dict(item, must_resolve) for item in items]

        if req_id in self.req_reply:
            self.req_reply[req_id](
                CompletionRequestTypes.DOCUMENT_COMPLETION,
                {'params': result},
            )

    # ------------------------------------------------------------------
    # completionItem/resolve
    # ------------------------------------------------------------------

    @send_request(method=CompletionRequestTypes.COMPLETION_RESOLVE)
    def completion_resolve_request(self, params):
        item_dict = params['completion_item']
        # Reconstruct lsprotocol CompletionItem from Spyder's stored dict.
        kind_val = item_dict.get('kind', CompletionItemKind.TEXT)
        fmt_val = item_dict.get(
            'insertTextFormat', InsertTextFormat.PLAIN_TEXT
        )
        return lsp.CompletionItem(
            label=item_dict.get('label', ''),
            kind=lsp.CompletionItemKind(kind_val),
            detail=item_dict.get('detail') or None,
            documentation=item_dict.get('documentation') or None,
            sort_text=item_dict.get('sortText') or None,
            filter_text=item_dict.get('filterText') or None,
            insert_text=item_dict.get('insertText') or None,
            insert_text_format=lsp.InsertTextFormat(fmt_val),
        )

    @handles(CompletionRequestTypes.COMPLETION_RESOLVE)
    def handle_completion_resolve(self, response: lsp.CompletionItem, req_id):
        result = _completion_item_to_dict(response, must_resolve=False)
        result['provider'] = LSP_COMPLETION

        if req_id in self.req_reply:
            self.req_reply[req_id](
                CompletionRequestTypes.COMPLETION_RESOLVE,
                {'params': result},
            )

    # ------------------------------------------------------------------
    # textDocument/signatureHelp
    # ------------------------------------------------------------------

    @send_request(method=CompletionRequestTypes.DOCUMENT_SIGNATURE)
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

    @handles(CompletionRequestTypes.DOCUMENT_SIGNATURE)
    def process_signature_completion(
        self, response: lsp.SignatureHelp, req_id
    ):
        result = None
        if response and response.signatures:
            active = response.active_signature or 0
            sig = response.signatures[active]
            doc = sig.documentation
            doc_str = doc.value if isinstance(doc, lsp.MarkupContent) else (doc or '')
            params_list = []
            for p in (sig.parameters or []):
                p_doc = p.documentation
                p_doc_str = (
                    p_doc.value if isinstance(p_doc, lsp.MarkupContent)
                    else (p_doc or '')
                )
                label = p.label
                if isinstance(label, tuple):
                    label = sig.label[label[0]:label[1]]
                params_list.append({
                    'label': label,
                    'documentation': p_doc_str,
                })
            result = {
                'label': sig.label,
                'documentation': doc_str,
                'parameters': params_list,
                'activeParameter': response.active_parameter or 0,
                'provider': LSP_COMPLETION,
            }

        if req_id in self.req_reply:
            self.req_reply[req_id](
                CompletionRequestTypes.DOCUMENT_SIGNATURE,
                {'params': result},
            )

    # ------------------------------------------------------------------
    # textDocument/hover
    # ------------------------------------------------------------------

    @send_request(method=CompletionRequestTypes.DOCUMENT_HOVER)
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

    @handles(CompletionRequestTypes.DOCUMENT_HOVER)
    def process_hover_result(self, result: lsp.Hover, req_id):
        contents = None
        if result is not None:
            raw = result.contents
            if isinstance(raw, lsp.MarkupContent):
                contents = raw.value
            elif isinstance(raw, lsp.MarkedStringWithLanguage):
                # lsp.MarkedString is Union[str, MarkedStringWithLanguage]
                # in lsprotocol 2025.0.0; use the concrete class instead.
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
                CompletionRequestTypes.DOCUMENT_HOVER,
                {'params': contents},
            )

    # ------------------------------------------------------------------
    # textDocument/documentSymbol
    # ------------------------------------------------------------------

    @send_request(method=CompletionRequestTypes.DOCUMENT_SYMBOL)
    def document_symbol_request(self, params):
        return lsp.DocumentSymbolParams(
            text_document=lsp.TextDocumentIdentifier(
                uri=path_as_uri(params['file']),
            ),
        )

    @handles(CompletionRequestTypes.DOCUMENT_SYMBOL)
    def process_document_symbol_request(self, result, req_id):
        # result is list[DocumentSymbol] | list[SymbolInformation] | None
        # Convert to a list of plain dicts for downstream consumers.
        symbols = _symbols_to_list(result)
        if req_id in self.req_reply:
            self.req_reply[req_id](
                CompletionRequestTypes.DOCUMENT_SYMBOL,
                {'params': symbols},
            )

    # ------------------------------------------------------------------
    # textDocument/definition
    # ------------------------------------------------------------------

    @send_request(method=CompletionRequestTypes.DOCUMENT_DEFINITION)
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

    @handles(CompletionRequestTypes.DOCUMENT_DEFINITION)
    def process_go_to_definition(self, result, req_id):
        location = None
        if isinstance(result, list) and result:
            loc = result[0]
            location = _location_to_dict(loc)
        elif isinstance(result, lsp.Location):
            location = _location_to_dict(result)
        elif isinstance(result, lsp.LocationLink):
            location = _location_link_to_dict(result)

        if req_id in self.req_reply:
            self.req_reply[req_id](
                CompletionRequestTypes.DOCUMENT_DEFINITION,
                {'params': location},
            )

    # ------------------------------------------------------------------
    # textDocument/foldingRange
    # ------------------------------------------------------------------

    @send_request(method=CompletionRequestTypes.DOCUMENT_FOLDING_RANGE)
    def folding_range_request(self, params):
        return lsp.FoldingRangeParams(
            text_document=lsp.TextDocumentIdentifier(
                uri=path_as_uri(params['file']),
            ),
        )

    @handles(CompletionRequestTypes.DOCUMENT_FOLDING_RANGE)
    def process_folding_range(self, result, req_id):
        ranges = []
        for r in (result or []):
            ranges.append({
                'startLine': r.start_line,
                'endLine': r.end_line,
                'kind': r.kind.value if r.kind else None,
            })
        if req_id in self.req_reply:
            self.req_reply[req_id](
                CompletionRequestTypes.DOCUMENT_FOLDING_RANGE,
                {'params': ranges},
            )

    # ------------------------------------------------------------------
    # textDocument/willSave
    # ------------------------------------------------------------------

    @send_notification(method=CompletionRequestTypes.DOCUMENT_WILL_SAVE)
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

    @send_notification(method=CompletionRequestTypes.DOCUMENT_DID_SAVE)
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

    @send_notification(method=CompletionRequestTypes.DOCUMENT_DID_CLOSE)
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

    @send_request(method=CompletionRequestTypes.DOCUMENT_FORMATTING)
    def document_formatting_request(self, params):
        options = {
            snake_to_camel(k): v for k, v in params['options'].items()
        }
        return lsp.DocumentFormattingParams(
            text_document=lsp.TextDocumentIdentifier(
                uri=path_as_uri(params['file']),
            ),
            options=lsp.FormattingOptions(**options),
        )

    @handles(CompletionRequestTypes.DOCUMENT_FORMATTING)
    def process_document_formatting(self, result, req_id):
        edits = _text_edits_to_list(result)
        if req_id in self.req_reply:
            self.req_reply[req_id](
                CompletionRequestTypes.DOCUMENT_FORMATTING,
                {'params': edits},
            )

    # ------------------------------------------------------------------
    # textDocument/rangeFormatting
    # ------------------------------------------------------------------

    @send_request(method=CompletionRequestTypes.DOCUMENT_RANGE_FORMATTING)
    def document_range_formatting_request(self, params):
        options = {
            snake_to_camel(k): v for k, v in params['options'].items()
        }
        rng = params['range']
        return lsp.DocumentRangeFormattingParams(
            text_document=lsp.TextDocumentIdentifier(
                uri=path_as_uri(params['file']),
            ),
            options=lsp.FormattingOptions(**options),
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

    @handles(CompletionRequestTypes.DOCUMENT_RANGE_FORMATTING)
    def process_document_range_formatting(self, result, req_id):
        edits = _text_edits_to_list(result)
        if req_id in self.req_reply:
            self.req_reply[req_id](
                CompletionRequestTypes.DOCUMENT_RANGE_FORMATTING,
                {'params': edits},
            )


# ---------------------------------------------------------------------------
# Private conversion helpers
# ---------------------------------------------------------------------------

def _range_to_dict(r: lsp.Range) -> dict:
    return {
        'start': {'line': r.start.line, 'character': r.start.character},
        'end': {'line': r.end.line, 'character': r.end.character},
    }


def _location_to_dict(loc: lsp.Location) -> dict:
    return {
        'uri': loc.uri,
        'file': process_uri(loc.uri),
        'range': _range_to_dict(loc.range),
    }


def _location_link_to_dict(link: lsp.LocationLink) -> dict:
    return {
        'uri': link.target_uri,
        'file': process_uri(link.target_uri),
        'range': _range_to_dict(link.target_range),
    }


def _text_edits_to_list(result) -> list:
    if not result:
        return []
    out = []
    for edit in result:
        out.append({
            'range': _range_to_dict(edit.range),
            'newText': edit.new_text,
        })
    return out


def _symbol_to_dict(sym) -> dict:
    """Convert DocumentSymbol or SymbolInformation to a plain dict."""
    if isinstance(sym, lsp.DocumentSymbol):
        children = [_symbol_to_dict(c) for c in (sym.children or [])]
        kind = sym.kind
        return {
            'name': sym.name,
            'kind': kind.value if kind else 0,
            'range': _range_to_dict(sym.range),
            'selectionRange': _range_to_dict(sym.selection_range),
            'children': children,
        }
    else:  # SymbolInformation
        kind = sym.kind
        return {
            'name': sym.name,
            'kind': kind.value if kind else 0,
            'location': _location_to_dict(sym.location),
            'containerName': sym.container_name,
        }


def _symbols_to_list(result) -> list:
    if not result:
        return []
    return [_symbol_to_dict(s) for s in result]
