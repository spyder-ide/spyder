# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
"""Read-only, bounded previews for text and structured dataframe cells."""

from collections.abc import Mapping
from html import escape
from itertools import chain, islice
import json
import reprlib

from qtpy.QtCore import QElapsedTimer, QRegularExpression, QSignalBlocker, Qt, QTimer
from qtpy.QtGui import QColor, QDesktopServices, QTextBlockFormat, QTextCursor, QTextDocument, QTextOption, QTextTable
from qtpy.QtWidgets import (
    QApplication, QDialogButtonBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QPlainTextEdit, QPushButton, QSizePolicy, QTabWidget, QTextBrowser, QTextEdit, QToolTip,
    QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator, QVBoxLayout, QWidget,
)
from spyder_kernels.utils.lazymodules import numpy as np

from spyder.api.fonts import SpyderFontsMixin, SpyderFontType
from spyder.api.translations import _
from spyder.plugins.variableexplorer.widgets.basedialog import BaseDialog
from spyder.widgets.findreplace import FindReplace
from spyder.widgets.mixins import BaseEditMixin
from spyder.utils.icon_manager import ima
from spyder.utils.palette import SpyderPalette
from spyder.utils.qthelpers import create_toolbutton
from spyder.utils.stylesheet import AppStyle


def is_structured(value):
    """Recognize nested cell scalars without converting arrays or importing Polars."""
    return (isinstance(value, (Mapping, list, tuple)) or
            isinstance(value, np.ndarray) and value.ndim > 0 or
            type(value).__module__.startswith('polars') and
            type(value).__name__ == 'Series')


def structure_preview(value):
    """Serialize a bounded snapshot; never walk or encode the whole container."""
    remaining = 200

    def snapshot(current, ancestors=()):
        nonlocal remaining
        remaining -= 1
        if remaining < 0 or len(ancestors) > 6:
            return '…'
        if isinstance(current, str):
            return current if len(current) <= 300 else current[:300] + '…'
        if not is_structured(current):
            return current if type(current) in (int, float, bool, type(None)) else reprlib.repr(current)
        if id(current) in ancestors:
            return '<cycle>'
        ancestors += (id(current),)
        if isinstance(current, Mapping):
            result = {str(key)[:200]: snapshot(child, ancestors)
                      for key, child in islice(current.items(), min(20, max(0, remaining)))}
            if len(current) > len(result):
                result['…'] = '…'
            return result
        result = [snapshot(child, ancestors) for child in islice(current, min(20, max(0, remaining)))]
        if len(current) > len(result):
            result.append('…')
        return result

    return json.dumps(snapshot(value), ensure_ascii=False, indent=2)


class PlainTextView(BaseEditMixin, QPlainTextEdit):
    """Plain text with Spyder's shared search protocol."""

    def __init__(self, parent=None):
        QPlainTextEdit.__init__(self, parent)
        BaseEditMixin.__init__(self)


class MarkdownBrowser(BaseEditMixin, QTextBrowser):
    """Render cell text without fetching linked images or local resources."""

    def __init__(self, parent=None):
        QTextBrowser.__init__(self, parent)
        BaseEditMixin.__init__(self)
        self.anchorClicked.connect(self.open_web_link)

    def open_web_link(self, url):
        """Open explicitly clicked web links, never local files or custom schemes."""
        if url.isValid() and url.scheme() in ('http', 'https') and url.host():
            QDesktopServices.openUrl(url)

    def loadResource(self, resource_type, name):
        return None


class FieldView(QTextBrowser):
    """Keep long keys readable without taking over the value preview."""

    def __init__(self, text):
        super().__init__()
        self.setPlainText(text)
        self.setStyleSheet('QTextBrowser { border: 0; padding: 0; background: transparent; }')
        self.document().setDocumentMargin(AppStyle.MarginSize)
        self.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.setFixedHeight(min(int(self.document().size().height()) + 2,
                                4 * self.fontMetrics().lineSpacing() +
                                2 * AppStyle.MarginSize + 2))


class CellFindReplace(FindReplace):
    """Route the native find shortcut to fields when inspecting a tree."""

    def set_editor(self, editor, refresh=True):
        # Our targets are BaseEditMixin text views, never a CodeEditor/WebView.
        # Avoid loading those unrelated editor and browser stacks on cell open.
        if self.editor is not editor:
            self.clear_matches()
        self.editor = editor
        self.is_code_editor = False
        if refresh:
            self.refresh()
        if self.isHidden():
            self.clear_matches()

    def find(self, *args, **kwargs):
        result = super().find(*args, **kwargs)
        if self.editor is not None and not self.isHidden():
            if kwargs.get('start_highlight_timer', False):
                self.highlight_timer.start()
            else:
                self.highlight_matches()
        return result

    def highlight_matches(self):
        """Decorate the loaded document without changing its selected match."""
        if self.editor is None or self.isHidden():
            return
        text = self.search_text.currentText()
        pattern = text if self.re_button.isChecked() else QRegularExpression.escape(text)
        if self.words_button.isChecked():
            pattern = rf'\b{pattern}\b'
        options = QRegularExpression.MultilineOption | QRegularExpression.UseUnicodePropertiesOption
        expression = QRegularExpression(pattern, options)
        if not self.case_button.isChecked():
            expression.setPatternOptions(expression.patternOptions() | QRegularExpression.CaseInsensitiveOption)
        selections = []
        if text and expression.isValid():
            matches = expression.globalMatch(self.editor.toPlainText())
            while matches.hasNext():
                match = matches.next()
                if not match.capturedLength():
                    continue
                selection = QTextEdit.ExtraSelection()
                selection.format.setBackground(QColor(SpyderPalette.COLOR_OCCURRENCE_4))
                selection.cursor = QTextCursor(self.editor.document())
                selection.cursor.setPosition(match.capturedStart())
                selection.cursor.setPosition(match.capturedEnd(), QTextCursor.KeepAnchor)
                selections.append(selection)
        self.editor.setExtraSelections(selections)

    def clear_matches(self):
        super().clear_matches()
        self.highlight_timer.stop()
        if self.editor is not None:
            self.editor.setExtraSelections([])

    def show(self, hide_replace=True):
        if self.editor is None:
            self.parent().search.setFocus()
            return
        super().show(hide_replace=True)

    def find_next(self, set_focus=True):
        if self.editor is None:
            return self.parent().find_next()
        return super().find_next(set_focus)

    def find_previous(self, set_focus=True):
        if self.editor is None:
            return self.parent().find_next(backward=True)
        return super().find_previous(set_focus)


class StructureTree(QTreeWidget):
    """Let users resize every column while values absorb window width changes."""

    def resizeEvent(self, event):
        width = self.width()
        changed = width != getattr(self, '_last_width', None)
        self._last_width = width
        super().resizeEvent(event)
        if changed:
            remaining = self.viewport().width() - self.columnWidth(0) - self.columnWidth(2)
            self.setColumnWidth(1, max(self.header().minimumSectionSize(), remaining))


class StructureItem(QTreeWidgetItem):
    """Keep Python values outside Qt's recursively converted QVariant data."""

    def __init__(self, parent, key, value, ancestors=()):
        container = is_structured(value)
        cycle = container and id(value) in ancestors
        summary = (_('Cycle reference') if cycle else
                   _('%s items') % len(value) if container else
                   value[:300] if isinstance(value, str) else reprlib.repr(value))
        self.key = str(key)
        super().__init__(parent, [self.key[:300], summary, type(value).__name__])
        if len(self.key) > 300:
            self.setToolTip(0, f'<p style="white-space: pre-wrap">{escape(self.key)}</p>')
        self.value = value
        self.ancestors = ancestors + (id(value),)
        self.entries = None
        if container and len(value) and not cycle:
            entries = value.items() if isinstance(value, Mapping) else enumerate(value)
            self.entries = iter(entries)
            QTreeWidgetItem(self, [_('Expand to load')])

    def fetch(self, limit=200):
        if self.entries is None:
            return 0
        # Only the placeholder is removed; already loaded rows stay intact.
        self.takeChild(self.childCount() - 1)
        created = 0
        for key, value in islice(self.entries, limit):
            child = StructureItem(self, key, value, self.ancestors)
            created += 1 + child.childCount()
        try:
            key, value = next(self.entries)
        except StopIteration:
            self.entries = None
        else:
            self.entries = chain(((key, value),), self.entries)
            QTreeWidgetItem(self, [_('Load more…')])
        return created


class CellViewer(BaseDialog, SpyderFontsMixin):
    """Inspect a cell without modifying or eagerly formatting its contents."""

    # Bound automatic parsing, rendering and raw document insertion separately.
    text_chunk = 200000
    tree_load_limit = 100000

    def __init__(self, value, title='', parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowFlags(Qt.Window)
        self.setFont(self.get_font(SpyderFontType.Interface))
        self.setWindowTitle(_('Cell contents') + (f' — {title}' if title else ''))
        self.setMinimumSize(520, 360)
        self.value = value
        self.offset = 0
        structured = value if is_structured(value) else None
        self.raw_text = value if isinstance(value, str) else None
        self.markdown_start = self.markdown_end = 0
        self.markdown_history = []
        if isinstance(value, str) and len(value) <= self.text_chunk:
            try:
                parsed = json.loads(value)
            except (ValueError, RecursionError):
                pass
            else:
                if isinstance(parsed, (dict, list)):
                    structured = parsed

        layout = QVBoxLayout(self)
        margin = AppStyle.MarginSize
        layout.setContentsMargins(2 * margin, margin, 2 * margin, margin)
        layout.setSpacing(margin)
        if title and isinstance(parent, CellViewer):
            layout.addWidget(FieldView(title))
        self.status = QLabel()
        self.status.setTextFormat(Qt.PlainText)
        self.status.setWordWrap(True)
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.raw = PlainTextView()
        self.raw.setReadOnly(True)
        self.raw.setFont(self.get_font(SpyderFontType.MonospaceInterface))
        self.tabs.addTab(self.raw, _('Raw text'))
        self.preview = None
        self.tree = None
        pending_json = isinstance(value, str) and len(value) > self.text_chunk and value.lstrip().startswith(('{', '['))
        if structured is not None or pending_json:
            self.tree = StructureTree()
            self.tree.setHeaderLabels([_('Field / index'), _('Value'), _('Type')])
            self.tree.setAlternatingRowColors(True)
            self.tree.setUniformRowHeights(True)
            self.tree.setColumnWidth(0, 200)
            self.tree.header().setStretchLastSection(False)
            self.tree.header().setSectionResizeMode(QHeaderView.Interactive)
            self.tree.itemExpanded.connect(self._expand)
            self.tree.itemDoubleClicked.connect(self._inspect_item)
            self.tabs.addTab(self.tree, _('Structure'))
            if structured is not None:
                root = StructureItem(self.tree, '$', structured)
                self.tree.expandItem(root)
                self.tree.setCurrentItem(root)
                self.tabs.setCurrentWidget(self.tree)
        if isinstance(value, str):
            self.preview = MarkdownBrowser()
            self.preview.setFont(self.get_font(SpyderFontType.Interface, font_size_delta=2))
            self.preview.document().setDocumentMargin(3 * margin)
            self.preview.setOpenLinks(False)
            self.preview.setOpenExternalLinks(False)
            self.tabs.addTab(self.preview, _('Markdown'))
        layout.addWidget(self.tabs, 1)

        self.find_widget = CellFindReplace(self, enable_replace=False)
        self.find_widget.search_text.lineEdit().setStyleSheet('background: transparent;')
        layout.addWidget(self.find_widget)
        self.find_widget.hide()

        tools = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(_('Find fields and values…'))
        self.search.setToolTip(_('Searches loaded field names and complete string values, not just their summaries. Unloaded fields are not searched.'))
        self.search.setClearButtonEnabled(True)
        self.search.returnPressed.connect(self.find_next)
        tools.addWidget(self.search, 1)
        self.tree_find = QPushButton(_('Find next field'))
        self.tree_find.clicked.connect(self.find_next)
        tools.addWidget(self.tree_find)
        layout.addLayout(tools)
        actions = QWidget()
        action_layout = QHBoxLayout(actions)
        action_layout.setContentsMargins(0, 0, 0, margin)
        action_layout.setSpacing(margin)
        if self.tree is not None:
            self.loading_item = None
            self.loading_timer = QTimer(self)
            self.loading_timer.setInterval(10)
            self.loading_timer.timeout.connect(self._load_tree_batch)
            self.expansion_iterator = None
            self.expansion_timer = QTimer(self)
            self.expansion_timer.setInterval(10)
            self.expansion_timer.timeout.connect(self._expand_batch)
            self.expand_button = create_toolbutton(
                self, icon=ima.icon('expand'), tip=_('Expand all'), triggered=self._expand_all)
            self.collapse_button = create_toolbutton(
                self, icon=ima.icon('collapse'), tip=_('Collapse all'), triggered=self._collapse_all)
            action_layout.addWidget(self.collapse_button)
            action_layout.addWidget(self.expand_button)
            self.load_all_button = QPushButton(_('Load all'))
            self.load_all_button.setToolTip(_('Load all immediate items of the selected container; nested containers stay collapsed.'))
            self.load_all_button.clicked.connect(self._load_all_tree)
            action_layout.addWidget(self.load_all_button)
            self.tree.verticalScrollBar().valueChanged.connect(self._fetch_visible_items)
            self.tree.currentItemChanged.connect(self._show_tab)
        self.previous_page = create_toolbutton(
            self, icon=ima.icon('previous'), tip=_('Previous Markdown page'),
            triggered=self._previous_markdown_page)
        action_layout.addWidget(self.previous_page)
        self.load_more = QPushButton(_('Load more'))
        self.load_more.clicked.connect(self._load_more)
        action_layout.addWidget(self.load_more)
        action_layout.addWidget(create_toolbutton(
            self, icon=ima.icon('find'), tip=_('Find'),
            triggered=self.find_widget.show))
        self.copy_button = create_toolbutton(
            self, icon=ima.icon('editcopy'),
            tip=_('Copy source') if isinstance(value, str) else _('Copy selected preview'),
            triggered=self.copy_source)
        action_layout.addWidget(self.copy_button)
        self.copy_timer = QTimer(self)
        self.copy_timer.setSingleShot(True)
        self.copy_timer.setInterval(1500)
        self.copy_timer.timeout.connect(self._reset_copy_feedback)
        self.tabs.setCornerWidget(actions, Qt.TopRightCorner)
        if self.tree is not None:
            self.load_all_button.ensurePolished()
            self.load_all_button.setMinimumWidth(self.load_all_button.sizeHint().width())
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        footer = QHBoxLayout()
        footer.addWidget(self.status, 1)
        footer.addWidget(buttons)
        layout.addLayout(footer)
        self.tabs.currentChanged.connect(self._show_tab)
        self._show_tab()

    def set_dynamic_width_and_height(self, screen_geometry):
        """Center the final size within the usable screen, including its frame."""
        available = self.screen().availableGeometry()
        self.resize(min(1000, available.width() - 60), min(740, available.height() - 80))
        frame = self.frameGeometry()
        frame.moveCenter(available.center())
        self.move(frame.topLeft())

    def _expand(self, item):
        if isinstance(item, StructureItem) and item.entries is not None:
            item.fetch()

    def _fetch_visible_items(self):
        if (self.tabs.currentWidget() is not self.tree or
                self.loading_timer.isActive() or self.expansion_timer.isActive()):
            return
        item = self.tree.itemAt(0, 0)
        while item is not None and self.tree.visualItemRect(item).top() < self.tree.viewport().height():
            if not isinstance(item, StructureItem) and isinstance(item.parent(), StructureItem):
                with QSignalBlocker(self.tree.verticalScrollBar()):
                    item.parent().fetch()
                self._show_tab()
                return
            item = self.tree.itemBelow(item)

    def _selected_container(self):
        item = self.tree.currentItem()
        if item is not None and (not isinstance(item, StructureItem) or not is_structured(item.value)):
            item = item.parent()
        return item if isinstance(item, StructureItem) else None

    def _load_all_tree(self):
        if self.loading_timer.isActive():
            self.loading_timer.stop()
            self.loading_item = None
        else:
            item = self._selected_container()
            if item is None or item.entries is None:
                return
            self.expansion_timer.stop()
            self.expansion_iterator = None
            self.loading_item = item
            self.loading_work = 0
            with QSignalBlocker(self.tree):
                self.tree.expandItem(item)
            self.loading_timer.start()
        self._show_tab()

    def _load_tree_batch(self):
        item = self.loading_item
        elapsed = QElapsedTimer()
        elapsed.start()
        with QSignalBlocker(self.tree.verticalScrollBar()):
            # Collapsing an ancestor hides this row without changing isExpanded.
            while (self.tree.visualItemRect(item).isValid() and item.isExpanded() and
                   item.entries is not None and self.loading_work + 2 <= self.tree_load_limit):
                # A new child can also own one lazy placeholder node.
                self.loading_work += item.fetch(min(200, (self.tree_load_limit - self.loading_work) // 2))
                if elapsed.elapsed() >= 8:
                    self._show_tab()
                    return
        self.loading_timer.stop()
        if item.entries is None or not item.isExpanded() or not self.tree.visualItemRect(item).isValid():
            self.loading_item = None
        self._show_tab()

    def _inspect_item(self, item, column):
        if isinstance(item, StructureItem):
            if not is_structured(item.value):
                CellViewer(item.value, item.key, self).show()
        elif isinstance(item.parent(), StructureItem):
            item.parent().fetch()
            self._show_tab()

    def _expand_all(self):
        self.loading_timer.stop()
        self.loading_item = None
        if self.expansion_iterator is None:
            self.expansion_iterator = QTreeWidgetItemIterator(self.tree)
        item = self.expansion_iterator.value()
        if not isinstance(item, StructureItem):
            return
        self.expansion_work = 0
        self.expansion_depth = len(item.ancestors) + 32
        self.expand_button.setEnabled(False)
        self.expansion_timer.start()

    def _expand_batch(self):
        """Let Qt process input between bounded batches of lazy tree loading."""
        elapsed = QElapsedTimer()
        elapsed.start()
        while elapsed.elapsed() < 8:
            item = self.expansion_iterator.value()
            if item is None:
                self.expansion_iterator = None
                break
            if (self.expansion_work >= 5000 or
                    isinstance(item, StructureItem) and item.childCount() and
                    len(item.ancestors) >= self.expansion_depth):
                break
            before = item.childCount()
            if isinstance(item, StructureItem) and before:
                if not item.isExpanded():
                    self.tree.expandItem(item)
                elif item.entries is not None:
                    item.fetch()
            self.expansion_work += max(1, item.childCount() - before)
            if not isinstance(item, StructureItem) or item.entries is None:
                self.expansion_iterator += 1
        else:
            return
        self.expansion_timer.stop()
        self._show_tab()

    def _collapse_all(self):
        self.loading_timer.stop()
        self.loading_item = None
        self.expansion_timer.stop()
        self.expansion_iterator = None
        self.tree.collapseAll()
        self._show_tab()

    def _show_tab(self, index=0):
        current = self.tabs.currentWidget()
        in_tree = current is self.tree
        if self.tree is not None and not in_tree:
            self.loading_timer.stop()
            self.loading_item = None
            self.expansion_timer.stop()
        can_load = False
        if current is self.raw and self.raw.document().isEmpty():
            if self.raw_text is None:
                # Bound formatting itself, including individual string leaves.
                self.raw_text = structure_preview(self.value)
            self._append_text()
        if current is self.raw:
            status = (_('%s / %s characters loaded') % (self.offset, len(self.value))
                      if isinstance(self.value, str) else
                      _('Bounded JSON preview · use Structure for complete fields'))
            can_load = self.offset < len(self.raw_text)
            self.load_more.setText(_('Load more'))
        elif in_tree:
            if (self.loading_item is not None and self.loading_item.entries is None and
                    not self.loading_timer.isActive()):
                self.loading_item = None
            can_load = self.tree.topLevelItemCount() == 0
            root = self.tree.topLevelItem(0)
            status = (_('JSON not parsed · load on request') if can_load else
                      ''
                      if isinstance(root, StructureItem) else _('Invalid JSON · use Source to inspect the text'))
            if self.expansion_iterator is not None and not self.expansion_timer.isActive():
                status = _('Expansion paused to keep the interface responsive · click Expand all to continue')
            if self.loading_item is not None:
                status = (_('Loading items · %s / %s') % (
                    self.loading_item.childCount() - int(self.loading_item.entries is not None),
                    len(self.loading_item.value)) if self.loading_timer.isActive() else
                    _('Loading paused to limit memory use · click Load all to continue'))
            self.load_more.setText(_('Load JSON'))
        elif current is self.preview:
            self.markdown_end = self.markdown_start + len('\n'.join(
                self.value[self.markdown_start:self.markdown_start + self.text_chunk].split('\n', 1000)[:1000]))
            boundary = self.value.rfind('\n\n', self.markdown_start, self.markdown_end)
            if self.markdown_end < len(self.value) and boundary > (self.markdown_start + self.markdown_end) // 2:
                self.markdown_end = boundary + 2
            can_load = self.markdown_end < len(self.value)
            status = (_('Markdown · %s–%s / %s characters (paged)') % (
                self.markdown_start, self.markdown_end, len(self.value))
                if self.markdown_start or can_load else _('Markdown · %s characters') % len(self.value))
            self.load_more.setText(_('Next page'))
            if self.preview.document().isEmpty():
                self.preview.document().setMarkdown(
                    self.value[self.markdown_start:self.markdown_end],
                    QTextDocument.MarkdownFeature(
                        QTextDocument.MarkdownDialectGitHub | QTextDocument.MarkdownNoHTML))
                cursor = QTextCursor(self.preview.document())
                cursor.select(QTextCursor.Document)
                spacing = QTextBlockFormat()
                height_type = QTextBlockFormat.ProportionalHeight
                spacing.setLineHeight(145, getattr(height_type, 'value', height_type))
                cursor.mergeBlockFormat(spacing)
                for frame in self.preview.document().rootFrame().childFrames():
                    if isinstance(frame, QTextTable):
                        style = frame.format()
                        style.setCellPadding(6)
                        style.setCellSpacing(0)
                        style.setBorder(0.5)
                        style.setBorderBrush(self.preview.palette().mid())
                        frame.setFormat(style)
                self.preview.moveCursor(QTextCursor.Start)
        if current in (self.raw, self.preview):
            self.tabs.setTabToolTip(self.tabs.currentIndex(), status)
            if isinstance(self.value, str) and not can_load and not (current is self.preview and self.markdown_start):
                status = ''
        self.status.setText(status)
        self.status.setVisible(bool(status))
        self.status.setToolTip(_('Paged Markdown may split syntax across pages. Source contains the complete original text.')
                               if current is self.preview and (self.markdown_start or can_load) else '')
        self.load_more.setEnabled(can_load)
        self.load_more.setVisible(can_load)
        self.load_more.setToolTip(_('Parse the complete JSON value; large inputs require additional time and memory.')
                                 if in_tree else '')
        self.previous_page.setVisible(current is self.preview and bool(self.markdown_history))
        if self.tree is not None:
            ready = isinstance(self.tree.topLevelItem(0), StructureItem)
            container = self._selected_container()
            loading = self.loading_timer.isActive()
            self.load_all_button.setVisible(in_tree and ready)
            self.load_all_button.setText(_('Stop') if loading else _('Load all'))
            self.load_all_button.setEnabled(loading or container is not None and container.entries is not None)
            self.expand_button.setVisible(in_tree and ready)
            self.collapse_button.setVisible(in_tree and ready)
            self.expand_button.setEnabled(ready and not self.expansion_timer.isActive() and not loading)
            self.collapse_button.setEnabled(ready)
        self.search.setVisible(in_tree)
        self.tree_find.setVisible(in_tree)
        self.find_widget.set_editor(None if in_tree else current)
        if in_tree:
            self.find_widget.hide()

    def _append_text(self):
        if self.raw_text is None:
            return
        position = self.raw.textCursor().position()
        cursor = self.raw.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(self.raw_text[self.offset:self.offset + self.text_chunk])
        cursor.setPosition(position)
        self.raw.setTextCursor(cursor)
        self.offset = min(self.offset + self.text_chunk, len(self.raw_text))

    def _load_more(self):
        if self.tabs.currentWidget() is self.raw:
            self._append_text()
        elif self.tabs.currentWidget() is self.preview:
            self.markdown_history.append(self.markdown_start)
            self.markdown_start = self.markdown_end
            self.preview.clear()
        elif self.tabs.currentWidget() is self.tree:
            try:
                parsed = json.loads(self.value)
            except (ValueError, RecursionError) as error:
                QTreeWidgetItem(self.tree, [_('Cannot parse JSON'), str(error)])
            else:
                root = StructureItem(self.tree, '$', parsed)
                self.tree.expandItem(root)
                self.tree.setCurrentItem(root)
        self._show_tab()

    def _previous_markdown_page(self):
        self.markdown_start = self.markdown_history.pop()
        self.preview.clear()
        self._show_tab()

    def find_next(self, backward=False):
        text = self.search.text().casefold()
        if not text:
            return
        if self.tabs.currentWidget() is self.tree:
            matches = []
            iterator = QTreeWidgetItemIterator(self.tree)
            while iterator.value():
                item = iterator.value()
                if isinstance(item, StructureItem):
                    value = item.value if isinstance(item.value, str) else item.text(1)
                    if text in item.key.casefold() or text in value.casefold():
                        matches.append(item)
                iterator += 1
            if matches:
                current = self.tree.currentItem()
                step = -1 if backward else 1
                position = (matches.index(current) + step) % len(matches) if current in matches else (len(matches) - 1 if backward else 0)
                self.tree.setCurrentItem(matches[position])
                self.tree.scrollToItem(matches[position])

    def _reset_copy_feedback(self):
        self.copy_button.setIcon(ima.icon('editcopy'))

    def copy_source(self):
        value = self.value
        if not isinstance(value, str) and self.tree is not None:
            item = self.tree.currentItem()
            if not isinstance(item, StructureItem):
                return
            value = item.value
        QApplication.clipboard().setText(value if isinstance(value, str) else structure_preview(value))
        self.copy_button.setIcon(ima.icon('DialogApplyButton'))
        QToolTip.showText(self.copy_button.mapToGlobal(self.copy_button.rect().bottomLeft()),
                          _('Copied to clipboard'), self.copy_button, self.copy_button.rect(), 1500)
        self.copy_timer.start()
