# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
"""Markdown headings expressed in the outline's existing symbol format."""

from markdown_it import MarkdownIt
from lsprotocol import types as lsp

from spyder.api.translations import _


def markdown_symbols(text):
    """Parse section ranges, excluding fenced/indented code and HTML blocks."""
    parser = MarkdownIt('commonmark').disable('inline')
    environment = {}
    tokens = parser.parse(text, environment)
    last_line = text.count('\n')
    symbols = []
    sections = []
    for index, token in enumerate(tokens):
        if token.type != 'heading_open':
            continue
        level = int(token.tag[1:])
        start = token.map[0]
        if len(symbols) == 2000:
            for section_level, section in sections:
                section.range.end.line = start - 1
            source_range = lsp.Range(lsp.Position(start, 0), lsp.Position(last_line, 0))
            symbols.append(lsp.DocumentSymbol(
                name=_('Additional headings (open source)'),
                kind=lsp.SymbolKind.String, range=source_range,
                selection_range=source_range))
            break
        while sections and sections[-1][0] >= level:
            sections.pop()[1].range.end.line = start - 1
        content = tokens[index + 1].content
        inline = []
        parser.inline.parse(content, parser, environment, inline)
        name = ''.join(child.content if child.type not in ('softbreak', 'hardbreak') else ' '
                       for child in inline if child.type in (
                           'text', 'code_inline', 'image', 'softbreak', 'hardbreak'))
        symbol = lsp.DocumentSymbol(
            name=name, kind=lsp.SymbolKind.Namespace,
            range=lsp.Range(lsp.Position(start, 0), lsp.Position(last_line, 0)),
            selection_range=lsp.Range(lsp.Position(start, 0), lsp.Position(start, 0)))
        symbols.append(symbol)
        sections.append((level, symbol))
    return symbols
