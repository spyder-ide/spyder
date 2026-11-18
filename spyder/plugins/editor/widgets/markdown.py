# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
"""On-demand Markdown views of the editor's unchanged source document."""

import os.path as osp
import re

from qtpy.QtCore import QTimer, QUrl, Signal
from qtpy.QtGui import (
    QColor, QDesktopServices, QFont, QImage, QImageReader, QPalette, QTextBlockFormat, QTextCharFormat,
    QTextCursor, QTextDocument, QTextFormat, QTextTable)
from qtpy.QtWidgets import (
    QActionGroup, QHBoxLayout, QLabel, QStackedWidget, QTextBrowser, QVBoxLayout, QWidget)

from spyder.api.translations import _
from spyder.utils.fonts import get_family, get_font
from spyder.config.utils import EDIT_EXTENSIONS
from spyder.utils.icon_manager import ima
from spyder_themes.spyder import SpyderPaletteDark, SpyderPaletteLight
from spyder.utils.qthelpers import create_toolbutton
from spyder.widgets.mixins import BaseEditMixin


class MarkdownBrowser(BaseEditMixin, QTextBrowser):
    """Native searchable text, with no automatic network/resource navigation."""

    focused = Signal()

    def __init__(self, parent):
        QTextBrowser.__init__(self, parent)
        BaseEditMixin.__init__(self)
        self.setOpenLinks(False)
        self.setOpenExternalLinks(False)
        self.setReadOnly(True)
        font = QFont(get_font(option='app_font', font_size_delta=1))
        font.setFamily(get_family([
            'Microsoft YaHei UI', 'PingFang SC', 'Noto Sans CJK SC', 'Segoe UI']))
        self.setFont(font)
        self.preview_font = font
        self.resource_bytes = 0
        self.preview_theme = 'auto'
        self.document().setDocumentMargin(16)

    def createStandardContextMenu(self, *args):
        menu = super().createStandardContextMenu(*args)
        menu.addSeparator()
        themes = menu.addMenu(_('Preview theme'))
        group = QActionGroup(themes)
        for theme, label in [('auto', _('Follow Spyder')),
                             ('light', _('Light')), ('dark', _('Dark'))]:
            action = themes.addAction(label)
            action.setData(theme)
            action.setCheckable(True)
            action.setChecked(theme == self.preview_theme)
            group.addAction(action)
        group.triggered.connect(lambda action: self.set_preview_theme(action.data()))
        return menu

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu(event.pos())
        try:
            menu.exec_(event.globalPos())
        finally:
            menu.deleteLater()

    def set_preview_theme(self, theme):
        self.preview_theme = theme
        self.setStyleSheet('')
        self.setPalette(QPalette())
        self.style().polish(self)
        if theme != 'auto':
            colors = SpyderPaletteLight if theme == 'light' else SpyderPaletteDark
            # A local rule also overrides the application's text-widget QSS.
            self.setStyleSheet(
                'MarkdownBrowser { '
                f'background-color: {colors.COLOR_BACKGROUND_1}; '
                f'color: {colors.COLOR_TEXT_1}; '
                f'selection-background-color: {colors.COLOR_ACCENT_1}; '
                f'selection-color: {colors.COLOR_TEXT_1}; }}')
            palette = self.palette()
            palette.setColor(QPalette.Link, QColor(colors.ICON_2))
            palette.setColor(QPalette.Mid, QColor(colors.COLOR_BACKGROUND_4))
            self.setPalette(palette)
        self.update_document_colors()

    def update_document_colors(self):
        # Qt stores link foregrounds in the document, not just its palette.
        links = []
        block = self.document().begin()
        while block.isValid():
            fragments = block.begin()
            while not fragments.atEnd():
                fragment = fragments.fragment()
                if fragment.charFormat().anchorHref():
                    links.append((fragment.position(), fragment.length()))
                fragments += 1
            block = block.next()
        style = QTextCharFormat()
        style.setForeground(self.palette().link())
        cursor = QTextCursor(self.document())
        for position, length in links:
            cursor.setPosition(position)
            cursor.setPosition(position + length, QTextCursor.KeepAnchor)
            cursor.mergeCharFormat(style)
        for frame in self.document().rootFrame().childFrames():
            if isinstance(frame, QTextTable):
                style = frame.format()
                style.setBorderBrush(self.palette().mid())
                frame.setFormat(style)

    @property
    def filename(self):
        return self.source_editor.filename

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.focused.emit()

    def loadResource(self, resource_type, name):
        url = self.document().baseUrl().resolved(name)
        path = url.toLocalFile()
        if (resource_type != QTextDocument.ImageResource or not url.isLocalFile()
                or url.host() or path.startswith(('//', '\\\\'))):
            return None
        try:
            if not osp.isfile(path) or osp.getsize(path) > 20 * 1024 ** 2:
                return None
        except OSError:
            return None
        reader = QImageReader(path)
        size = reader.size()
        if size.width() <= 0 or size.height() <= 0 or size.width() * size.height() > 16000000:
            return None
        depth = QImage.toPixelFormat(reader.imageFormat()).bitsPerPixel()
        image_bytes = ((size.width() * depth + 31) // 32) * 4 * size.height()
        if not depth or self.resource_bytes + image_bytes > 64 * 1024 ** 2:
            return None
        image = reader.read()
        if self.resource_bytes + image.sizeInBytes() > 64 * 1024 ** 2:
            return None
        self.resource_bytes += image.sizeInBytes()
        return image


class MarkdownPage(QStackedWidget):
    """A view-local source/preview page, allocated only on explicit request."""

    view_changed = Signal()
    open_file = Signal(str)

    def __init__(self, editor):
        super().__init__()
        self.editor = editor
        self.addWidget(editor)
        panel = QWidget(self)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        self.browser = MarkdownBrowser(panel)
        self.browser.source_editor = editor
        self.browser.anchorClicked.connect(self.open_link)
        layout.addWidget(self.browser)
        self.navigation = QWidget(panel)
        tools = QHBoxLayout(self.navigation)
        tools.setContentsMargins(0, 0, 0, 0)
        tools.setSpacing(0)
        self.previous_page = create_toolbutton(
            self.navigation, icon=ima.icon('previous'), tip=_('Previous page'),
            triggered=self.show_previous_page)
        self.next_page = create_toolbutton(
            self.navigation, icon=ima.icon('next'), tip=_('Next page'),
            triggered=self.show_next_page)
        self.position = QLabel(self.navigation)
        self.navigation.setToolTip(_(
            'Paged Markdown may split syntax across pages. Source contains the complete original text.'))
        tools.addWidget(self.previous_page)
        tools.addWidget(self.position)
        tools.addWidget(self.next_page)
        self.addWidget(panel)
        self.render_timer = QTimer(self)
        self.render_timer.setSingleShot(True)
        self.render_timer.setInterval(400)
        self.render_timer.timeout.connect(self.render)
        self.editor.textChanged.connect(self.schedule_render)
        self.page_start = self.page_end = 0
        self.page_history = []
        self.heading_breaks = set()
        self.cache_key = None
        self.rendered_key = None
        self.text = ''
        self.closed = False

    def set_preview(self, enabled):
        self.render_timer.stop()
        self.setCurrentIndex(int(enabled))
        if enabled:
            self.render()
        self.view_changed.emit()

    def current_view(self):
        return self.browser if self.currentIndex() else self.editor

    def schedule_render(self):
        if not self.closed and self.currentIndex() and self.isVisible():
            self.render_timer.start()

    def page_end_at(self, start):
        end = min(len(self.text), start + 50000)
        lines = self.text[start:end].splitlines(keepends=True)
        end = start + len(''.join(lines[:1000]))
        boundary = self.text.rfind('\n\n', start, end)
        if end < len(self.text) and boundary > (start + end) // 2:
            end = boundary + 2
        return min((cut for cut in self.heading_breaks if start < cut < end), default=end)

    def go_to_heading(self, line):
        """Locate the exact source heading without leaving the rendered view."""
        from markdown_it import MarkdownIt
        from lsprotocol import types as lsp
        if any(symbol.kind == lsp.SymbolKind.String
               and symbol.range.start.line == line - 1
               for symbol in self.editor.oe_proxy.info or []):
            return False  # The outline's explicit "Additional headings (open source)" entry.
        self.render()
        source_block = self.editor.document().findBlockByNumber(line - 1)
        if not source_block.isValid():
            return False
        cursor = QTextCursor(source_block)
        cursor.setPosition(0, QTextCursor.KeepAnchor)
        # QTextCursor positions count UTF-16 units; Python slices do not.
        offset = len(cursor.selectedText())
        if offset >= len(self.text):
            return False
        if not self.page_start <= offset < self.page_end:
            self.page_start = 0
            self.page_history.clear()
            while offset >= (end := self.page_end_at(self.page_start)):
                self.page_history.append(self.page_start)
                self.page_start = end
            self.render()
        tokens = MarkdownIt('commonmark').disable(['inline', 'html_block']).parse(
            self.text[self.page_start:self.page_end])
        headings = [token for token in tokens if token.type == 'heading_open']
        local_line = line - 1 - self.text.count('\n', 0, self.page_start)
        heading = next((index for index, token in enumerate(headings)
                        if token.map[0] == local_line), None)
        blocks = []
        block = self.browser.document().begin()
        while block.isValid():
            if block.blockFormat().headingLevel():
                blocks.append(block)
            block = block.next()
        if heading is None or len(blocks) != len(headings):
            # Qt can split a multiline heading, or a page can split Setext
            # syntax. Reuse the source boundary instead of guessing a block.
            self.heading_breaks.add(offset)
            if self.page_start != offset:
                self.page_history.append(self.page_start)
            self.page_start = offset
            self.render()
            block = self.browser.document().begin()
        else:
            block = blocks[heading]
        if not block.isValid() or not block.blockFormat().headingLevel():
            return False
        self.browser.setTextCursor(QTextCursor(block))
        self.browser.ensureCursorVisible()
        return True

    def render(self):
        if self.closed or not self.currentIndex():
            return
        key = (self.editor.document().revision(), self.editor.filename)
        if key != self.cache_key:
            self.text = self.editor.toPlainText()
            self.page_start = 0
            self.page_history.clear()
            self.heading_breaks.clear()
            self.cache_key = key
        if self.rendered_key == (key, self.page_start):
            return
        self.rendered_key = (key, self.page_start)
        scroll = self.browser.verticalScrollBar().value()
        self.page_end = self.page_end_at(self.page_start)
        # A fresh preview document releases the previous page's image cache.
        document = QTextDocument(self.browser)
        previous_document = self.browser.document()
        previous_document.setParent(None)
        self.browser.setDocument(document)
        document.setUndoRedoEnabled(False)
        previous_document.deleteLater()
        self.browser.resource_bytes = 0
        document.setDefaultFont(self.browser.preview_font)
        document.setDocumentMargin(16)
        document.setBaseUrl(QUrl.fromLocalFile(self.editor.filename))
        document.setMarkdown(self.text[self.page_start:self.page_end],
                             QTextDocument.MarkdownFeature(
                                 QTextDocument.MarkdownDialectGitHub | QTextDocument.MarkdownNoHTML))
        cursor = QTextCursor(document)
        cursor.select(QTextCursor.Document)
        spacing = QTextBlockFormat()
        height_type = QTextBlockFormat.ProportionalHeight
        spacing.setLineHeight(145, getattr(height_type, 'value', height_type))
        cursor.mergeBlockFormat(spacing)
        headings = {}
        block = document.begin()
        while block.isValid():
            level = block.blockFormat().headingLevel()
            if level:
                slug = re.sub(r'[^\w\- ]', '', block.text().casefold()).replace(' ', '-')
                count = headings.get(slug, 0)
                anchor = slug + (f'-{count}' if count else '')
                while anchor in headings:
                    count += 1
                    anchor = f'{slug}-{count}'
                headings[slug] = count + 1
                headings[anchor] = 1
                style = QTextCharFormat()
                style.setAnchorNames([anchor])
                style.setProperty(QTextFormat.FontSizeAdjustment, 0)
                style.setFontPointSize(self.browser.preview_font.pointSizeF()
                                       * {1: 1.6, 2: 1.35, 3: 1.15}.get(level, 1.05))
                cursor = QTextCursor(block)
                cursor.select(QTextCursor.BlockUnderCursor)
                cursor.mergeCharFormat(style)
            block = block.next()
        for frame in document.rootFrame().childFrames():
            if isinstance(frame, QTextTable):
                style = frame.format()
                style.setCellPadding(6)
                style.setCellSpacing(0)
                style.setBorder(0.5)
                frame.setFormat(style)
        self.browser.update_document_colors()
        paged = self.page_start > 0 or self.page_end < len(self.text)
        self.navigation.setVisible(paged)
        self.previous_page.setEnabled(bool(self.page_history))
        self.next_page.setEnabled(self.page_end < len(self.text))
        page_number = str(len(self.page_history) + 1)
        self.position.setText(page_number)
        self.position.setToolTip(_('Page %s') % page_number)
        self.position.setAccessibleName(self.position.toolTip())
        self.browser.verticalScrollBar().setValue(scroll)
        self.view_changed.emit()

    def show_next_page(self):
        self.page_history.append(self.page_start)
        self.page_start = self.page_end
        self.render()
        self.browser.verticalScrollBar().setValue(0)

    def show_previous_page(self):
        self.page_start = self.page_history.pop()
        self.render()
        self.browser.verticalScrollBar().setValue(0)

    def open_link(self, url):
        if not url.isValid():
            return
        if url.scheme() in ('http', 'https') and url.host():
            QDesktopServices.openUrl(url)
        elif not url.scheme() and not url.path() and url.fragment():
            self.browser.scrollToAnchor(url.fragment())
        else:
            resolved = self.browser.document().baseUrl().resolved(url)
            path = resolved.toLocalFile()
            if (resolved.isLocalFile() and not resolved.host()
                    and not path.startswith(('//', '\\\\')) and osp.isfile(path)
                    and osp.splitext(path)[1].lower() in EDIT_EXTENSIONS):
                self.open_file.emit(path)

    def showEvent(self, event):
        super().showEvent(event)
        if self.currentIndex():
            self.schedule_render()

    def hideEvent(self, event):
        self.render_timer.stop()
        super().hideEvent(event)

    def dispose(self, detach_source=True):
        if self.closed:
            return
        self.closed = True
        self.render_timer.stop()
        self.editor.textChanged.disconnect(self.schedule_render)
        if detach_source:
            self.editor.setParent(None)
        if getattr(self.editor, 'markdown_page', None) is self:
            del self.editor.markdown_page
        self.editor = None
        self.browser.source_editor = None
        self.text = ''
        self.navigation.deleteLater()
        self.deleteLater()
