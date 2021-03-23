# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Text snippets configuration widgets.
"""

# Standard library imports
import bisect
import json

# Third party imports
from jsonschema.exceptions import ValidationError
from jsonschema import validate as json_validate
from qtpy.compat import to_qvariant
from qtpy.QtCore import Qt, Slot, QAbstractTableModel, QModelIndex, QSize
from qtpy.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog,
                            QDialogButtonBox, QGroupBox, QGridLayout, QLabel,
                            QLineEdit, QTableView, QVBoxLayout)

# Local imports
from spyder.config.base import _
from spyder.config.manager import CONF
from spyder.config.gui import get_font
from spyder.plugins.completion.api import SUPPORTED_LANGUAGES
from spyder.utils.snippets.ast import build_snippet_ast
from spyder.widgets.helperwidgets import ItemDelegate
from spyder.widgets.simplecodeeditor import SimpleCodeEditor


# Languages supported by the text snippets extension
LANGUAGE_NAMES = {x.lower(): x for x in SUPPORTED_LANGUAGES}
LANGUAGE_SET = {lang.lower() for lang in SUPPORTED_LANGUAGES}

PYTHON_POS = bisect.bisect_left(SUPPORTED_LANGUAGES, 'Python')
SUPPORTED_LANGUAGES_PY = list(SUPPORTED_LANGUAGES)
SUPPORTED_LANGUAGES_PY.insert(PYTHON_POS, 'Python')

LANGUAGE, ADDR, CMD = [0, 1, 2]

SNIPPETS_SCHEMA = {
    'type': 'array',
    'title': 'Snippets',
    'items': {
        'type': 'object',
        'required': ['language', 'triggers'],
        'properties': {
            'language': {
                'type': 'string',
                'description': 'Programming language',
                'enum': [lang.lower() for lang in SUPPORTED_LANGUAGES_PY]
            },
            'triggers': {
                'type': 'array',
                'description': (
                    'List of snippet triggers defined for this language'),
                'items': {
                    'type': 'object',
                    'description': '',
                    'required': ['trigger', 'descriptions'],
                    'properties': {
                        'trigger': {
                            'type': 'string',
                            'description': (
                                'Text that triggers a snippet family'),
                        },
                        'descriptions': {
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'description': 'Snippet information',
                                'required': ['description', 'snippet'],
                                'properties': {
                                    'description': {
                                        'type': 'string',
                                        'description': (
                                            'Description of the snippet')
                                    },
                                    'snippet': {
                                        'type': 'object',
                                        'description': 'Snippet information',
                                        'required': ['text', 'remove_trigger'],
                                        'properties': {
                                            'text': {
                                                'type': 'string',
                                                'description': (
                                                    'Snippet to insert')
                                            },
                                            'remove_trigger': {
                                                'type': 'boolean',
                                                'description': (
                                                    'If true, the snippet '
                                                    'should remove the text '
                                                    'that triggers it')
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}


def iter_snippets(language, get_option, set_option, snippets=None):
    language_snippets = []
    load_snippets = snippets is None
    if load_snippets:
        snippets = get_option(language.lower(), default={})
    for trigger in snippets:
        trigger_descriptions = snippets[trigger]
        for description in trigger_descriptions:
            if load_snippets:
                this_snippet = Snippet(language=language, trigger_text=trigger,
                                       description=description,
                                       get_option=get_option,
                                       set_option=set_option)
                this_snippet.load()
            else:
                current_snippet = trigger_descriptions[description]
                text = current_snippet['text']
                remove_trigger = current_snippet['remove_trigger']
                this_snippet = Snippet(language=language,
                                       trigger_text=trigger,
                                       description=description,
                                       snippet_text=text,
                                       remove_trigger=remove_trigger,
                                       get_option=get_option,
                                       set_option=set_option)
            language_snippets.append(this_snippet)
    return language_snippets


class Snippet:
    """Convenience class to store user snippets."""

    def __init__(self, language=None, trigger_text="", description="",
                 snippet_text="", remove_trigger=False, get_option=None,
                 set_option=None):
        self.index = 0
        self.language = language
        if self.language in LANGUAGE_NAMES:
            self.language = LANGUAGE_NAMES[self.language]

        self.trigger_text = trigger_text
        self.snippet_text = snippet_text
        self.description = description
        self.remove_trigger = remove_trigger
        self.initial_trigger_text = trigger_text
        self.initial_description = description
        self.set_option = set_option
        self.get_option = get_option

    def __repr__(self):
        return '[{0}] {1} ({2}): {3}'.format(
            self.language, self.trigger_text, self.description,
            repr(self.snippet_text))

    def __str__(self):
        return self.__repr__()

    def update(self, trigger_text, description_text, snippet_text,
               remove_trigger):
        self.trigger_text = trigger_text
        self.description = description_text
        self.snippet_text = snippet_text
        self.remove_trigger = remove_trigger

    def load(self):
        if self.language is not None and self.trigger_text != '':
            state = self.get_option(self.language.lower())
            trigger_info = state[self.trigger_text]
            snippet_info = trigger_info[self.description]
            self.snippet_text = snippet_info['text']
            self.remove_trigger = snippet_info['remove_trigger']

    def save(self):
        if self.language is not None:
            language = self.language.lower()
            current_state = self.get_option(language, default={})
            new_state = {
                'text': self.snippet_text,
                'remove_trigger': self.remove_trigger
            }
            if (self.initial_trigger_text != self.trigger_text or
                    self.initial_description != self.description):
                # Delete previous entry
                if self.initial_trigger_text in current_state:
                    trigger = current_state[self.initial_trigger_text]
                    trigger.pop(self.initial_description)
                    if len(trigger) == 0:
                        current_state.pop(self.initial_trigger_text)
            trigger_info = current_state.get(self.trigger_text, {})
            trigger_info[self.description] = new_state
            current_state[self.trigger_text] = trigger_info
            self.set_option(language, current_state,
                            recursive_notification=False)

    def delete(self):
        if self.language is not None:
            language = self.language.lower()
            current_state = self.get_option(language, default={})
            trigger = current_state[self.trigger_text]
            trigger.pop(self.description)
            if len(trigger) == 0:
                current_state.pop(self.trigger_text)
            self.set_option(language, current_state,
                            recursive_notification=False)


class SnippetEditor(QDialog):
    SNIPPET_VALID = _('Valid snippet')
    SNIPPET_INVALID = _('Invalid snippet')
    INVALID_CB_CSS = "QComboBox {border: 1px solid red;}"
    VALID_CB_CSS = "QComboBox {border: 1px solid green;}"
    INVALID_LINE_CSS = "QLineEdit {border: 1px solid red;}"
    VALID_LINE_CSS = "QLineEdit {border: 1px solid green;}"
    MIN_SIZE = QSize(850, 600)

    def __init__(self, parent, language=None, trigger_text='', description='',
                 snippet_text='', remove_trigger=False, trigger_texts=[],
                 descriptions=[], get_option=None, set_option=None):
        super(SnippetEditor, self).__init__(parent)

        snippet_description = _(
            "To add a new text snippet, you need to define the text "
            "that triggers it, a short description (two words maximum) "
            "of the snippet and if it should delete the trigger text when "
            "inserted. Finally, you need to define the snippet body to insert."
        )

        self.parent = parent
        self.trigger_text = trigger_text
        self.description = description
        self.remove_trigger = remove_trigger
        self.snippet_text = snippet_text
        self.descriptions = descriptions
        self.base_snippet = Snippet(
            language=language, trigger_text=trigger_text,
            snippet_text=snippet_text, description=description,
            remove_trigger=remove_trigger,
            get_option=get_option, set_option=set_option)

        # Widgets
        self.snippet_settings_description = QLabel(snippet_description)
        self.snippet_settings_description.setFixedWidth(450)

        # Trigger text
        self.trigger_text_label = QLabel(_('Trigger text:'))
        self.trigger_text_cb = QComboBox(self)
        self.trigger_text_cb.setEditable(True)

        # Description
        self.description_label = QLabel(_('Description:'))
        self.description_input = QLineEdit(self)

        # Remove trigger
        self.remove_trigger_cb = QCheckBox(
            _('Remove trigger text on insertion'), self)
        self.remove_trigger_cb.setToolTip(_('Check if the text that triggers '
                                            'this snippet should be removed '
                                            'when inserting it'))
        self.remove_trigger_cb.setChecked(self.remove_trigger)

        # Snippet body input
        self.snippet_label = QLabel(_('<b>Snippet text:</b>'))
        self.snippet_valid_label = QLabel(self.SNIPPET_INVALID, self)
        self.snippet_input = SimpleCodeEditor(None)

        # Dialog buttons
        self.bbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        self.button_ok = self.bbox.button(QDialogButtonBox.Ok)
        self.button_cancel = self.bbox.button(QDialogButtonBox.Cancel)

        # Widget setup
        self.setWindowTitle(_('Snippet editor'))

        self.snippet_settings_description.setWordWrap(True)
        self.trigger_text_cb.setToolTip(
            _('Trigger text for the current snippet'))
        self.trigger_text_cb.addItems(trigger_texts)

        if self.trigger_text != '':
            idx = trigger_texts.index(self.trigger_text)
            self.trigger_text_cb.setCurrentIndex(idx)

        self.description_input.setText(self.description)
        self.description_input.textChanged.connect(lambda _x: self.validate())

        text_inputs = (self.trigger_text, self.description, self.snippet_text)
        non_empty_text = all([x != '' for x in text_inputs])
        if non_empty_text:
            self.button_ok.setEnabled(True)

        self.snippet_input.setup_editor(
            language=language,
            color_scheme=get_option('selected', section='appearance'),
            wrap=False,
            highlight_current_line=True,
            font=get_font()
        )
        self.snippet_input.set_language(language)
        self.snippet_input.setToolTip(_('Snippet text completion to insert'))
        self.snippet_input.set_text(snippet_text)

        # Layout setup
        general_layout = QVBoxLayout()
        general_layout.addWidget(self.snippet_settings_description)

        snippet_settings_group = QGroupBox(_('Trigger information'))
        settings_layout = QGridLayout()
        settings_layout.addWidget(self.trigger_text_label, 0, 0)
        settings_layout.addWidget(self.trigger_text_cb, 0, 1)
        settings_layout.addWidget(self.description_label, 1, 0)
        settings_layout.addWidget(self.description_input, 1, 1)

        all_settings_layout = QVBoxLayout()
        all_settings_layout.addLayout(settings_layout)
        all_settings_layout.addWidget(self.remove_trigger_cb)
        snippet_settings_group.setLayout(all_settings_layout)
        general_layout.addWidget(snippet_settings_group)

        text_layout = QVBoxLayout()
        text_layout.addWidget(self.snippet_label)
        text_layout.addWidget(self.snippet_input)
        text_layout.addWidget(self.snippet_valid_label)
        general_layout.addLayout(text_layout)

        general_layout.addWidget(self.bbox)
        self.setLayout(general_layout)

        # Signals
        self.trigger_text_cb.editTextChanged.connect(self.validate)
        self.description_input.textChanged.connect(self.validate)
        self.snippet_input.textChanged.connect(self.validate)
        self.bbox.accepted.connect(self.accept)
        self.bbox.rejected.connect(self.reject)

        # Final setup
        if trigger_text != '' or snippet_text != '':
            self.validate()

    @Slot()
    def validate(self):
        trigger_text = self.trigger_text_cb.currentText()
        description_text = self.description_input.text()
        snippet_text = self.snippet_input.toPlainText()

        invalid = False
        try:
            build_snippet_ast(snippet_text)
            self.snippet_valid_label.setText(self.SNIPPET_VALID)
        except SyntaxError:
            invalid = True
            self.snippet_valid_label.setText(self.SNIPPET_INVALID)

        if trigger_text == '':
            invalid = True
            self.trigger_text_cb.setStyleSheet(self.INVALID_CB_CSS)
        else:
            self.trigger_text_cb.setStyleSheet(self.VALID_CB_CSS)

        if trigger_text in self.descriptions:
            if self.trigger_text != trigger_text:
                if description_text in self.descriptions[trigger_text]:
                    invalid = True
                    self.description_input.setStyleSheet(
                        self.INVALID_LINE_CSS)
                else:
                    self.description_input.setStyleSheet(
                        self.VALID_LINE_CSS)
            else:
                if description_text != self.description:
                    if description_text in self.descriptions[trigger_text]:
                        invalid = True
                        self.description_input.setStyleSheet(
                            self.INVALID_LINE_CSS)
                    else:
                        self.description_input.setStyleSheet(
                            self.VALID_LINE_CSS)
                else:
                    self.description_input.setStyleSheet(
                        self.VALID_LINE_CSS)

        self.button_ok.setEnabled(not invalid)

    def get_options(self):
        trigger_text = self.trigger_text_cb.currentText()
        description_text = self.description_input.text()
        snippet_text = self.snippet_input.toPlainText()
        remove_trigger = self.remove_trigger_cb.isChecked()
        self.base_snippet.update(
            trigger_text, description_text, snippet_text, remove_trigger)
        return self.base_snippet


class SnippetsModel(QAbstractTableModel):
    TRIGGER = 0
    DESCRIPTION = 1

    def __init__(self, parent, text_color=None, text_color_highlight=None):
        super(QAbstractTableModel, self).__init__()
        self.parent = parent

        self.snippets = []
        self.delete_queue = []
        self.snippet_map = {}
        self.rich_text = []
        self.normal_text = []
        self.letters = ''
        self.label = QLabel()
        self.widths = []

        # Needed to compensate for the HTMLDelegate color selection unawareness
        palette = parent.palette()
        if text_color is None:
            self.text_color = palette.text().color().name()
        else:
            self.text_color = text_color

        if text_color_highlight is None:
            self.text_color_highlight = \
                palette.highlightedText().color().name()
        else:
            self.text_color_highlight = text_color_highlight

    def sortByName(self):
        self.snippets = sorted(self.snippets, key=lambda x: x.trigger_text)
        self.reset()

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsEnabled
        return Qt.ItemFlags(QAbstractTableModel.flags(self, index))

    def data(self, index, role=Qt.DisplayRole):
        row = index.row()
        if not index.isValid() or not (0 <= row < len(self.snippets)):
            return to_qvariant()

        snippet = self.snippets[row]
        column = index.column()

        if role == Qt.DisplayRole:
            if column == self.TRIGGER:
                return to_qvariant(snippet.trigger_text)
            elif column == self.DESCRIPTION:
                return to_qvariant(snippet.description)
        elif role == Qt.TextAlignmentRole:
            return to_qvariant(int(Qt.AlignHCenter | Qt.AlignVCenter))
        elif role == Qt.ToolTipRole:
            return to_qvariant(_("Double-click to view or edit"))
        return to_qvariant()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.TextAlignmentRole:
            if orientation == Qt.Horizontal:
                return to_qvariant(int(Qt.AlignHCenter | Qt.AlignVCenter))
            return to_qvariant(int(Qt.AlignRight | Qt.AlignVCenter))
        if role != Qt.DisplayRole:
            return to_qvariant()
        if orientation == Qt.Horizontal:
            if section == self.TRIGGER:
                return to_qvariant(_('Trigger text'))
            elif section == self.DESCRIPTION:
                return to_qvariant(_('Description'))
        return to_qvariant()

    def rowCount(self, index=QModelIndex()):
        return len(self.snippets)

    def columnCount(self, index=QModelIndex()):
        return 2

    def row(self, row_num):
        return self.snippets[row_num]

    def reset(self):
        self.beginResetModel()
        self.endResetModel()


class SnippetModelsProxy:
    def __init__(self, parent):
        self.models = {}
        self.awaiting_queue = {}
        self.parent = parent

    def get_model(self, table, language, text_color=None):
        if language not in self.models:
            language_model = SnippetsModel(table, text_color=text_color)
            to_add = self.awaiting_queue.pop(language, [])
            self.load_snippets(language, language_model, to_add=to_add)
            self.models[language] = language_model
        language_model = self.models[language]
        return language_model

    def reload_model(self, language, defaults):
        if language in self.models:
            model = self.models[language]
            model.delete_queue = list(model.snippets)
            self.load_snippets(language, model, defaults)

    def load_snippets(self, language, model, snippets=None, to_add=[]):
        snippets = iter_snippets(language, self.parent.get_option,
                                 self.parent.set_option,
                                 snippets=snippets)
        for i, snippet in enumerate(snippets):
            snippet.index = i

        snippet_map = {(x.trigger_text, x.description): x
                       for x in snippets}

        # Merge loaded snippets
        for snippet in to_add:
            key = (snippet.trigger_text, snippet.description)
            if key in snippet_map:
                to_replace = snippet_map[key]
                snippet.index = to_replace.index
                snippet_map[key] = snippet
            else:
                snippet.index = len(snippet_map)
                snippet_map[key] = snippet

        model.snippets = list(snippet_map.values())
        model.snippet_map = snippet_map

    def save_snippets(self):
        language_changes = set({})
        for language in self.models:
            language_changes |= {language}
            language_model = self.models[language]

            while len(language_model.delete_queue) > 0:
                snippet = language_model.delete_queue.pop(0)
                snippet.delete()

            for snippet in language_model.snippets:
                snippet.save()

        for language in list(self.awaiting_queue.keys()):
            language_changes |= {language}
            language_queue = self.awaiting_queue.pop(language)
            for snippet in language_queue:
                snippet.save()
        return language_changes

    def update_or_enqueue(self, language, trigger, description, snippet):
        new_snippet = Snippet(
            language=language, trigger_text=trigger, description=description,
            snippet_text=snippet['text'],
            remove_trigger=snippet['remove_trigger'],
            get_option=self.parent.get_option,
            set_option=self.parent.set_option)

        if language in self.models:
            language_model = self.models[language]
            snippet_map = language_model.snippet_map
            key = (trigger, description)
            if key in snippet_map:
                old_snippet = snippet_map[key]
                new_snippet.index = old_snippet.index
                snippet_map[key] = new_snippet
            else:
                new_snippet.index = len(snippet_map)
                snippet_map[key] = new_snippet

            language_model.snippets = list(snippet_map.values())
            language_model.snippet_map = snippet_map
            language_model.reset()
        else:
            language_queue = self.awaiting_queue.get(language, [])
            language_queue.append(new_snippet)
            self.awaiting_queue[language] = language_queue

    def export_snippets(self, filename):
        snippets = []
        for language in self.models:
            language_model = self.models[language]
            language_snippets = {
                'language': language,
                'triggers': []
            }
            triggers = {}
            for snippet in language_model.snippets:
                default_trigger = {
                    'trigger': snippet.trigger_text,
                    'descriptions': []
                }
                snippet_info = triggers.get(
                    snippet.trigger_text, default_trigger)
                snippet_info['descriptions'].append({
                    'description': snippet.description,
                    'snippet': {
                        'text': snippet.snippet_text,
                        'remove_trigger': snippet.remove_trigger
                    }
                })
                triggers[snippet.trigger_text] = snippet_info
            language_snippets['triggers'] = list(triggers.values())
            snippets.append(language_snippets)

        with open(filename, 'w') as f:
            json.dump(snippets, f)

    def import_snippets(self, filename):
        errors = {}
        total_snippets = 0
        valid_snippets = 0
        with open(filename, 'r') as f:
            try:
                snippets = json.load(f)
            except ValueError as e:
                errors['loading'] = e.msg

        if len(errors) == 0:
            try:
                json_validate(instance=snippets, schema=SNIPPETS_SCHEMA)
            except ValidationError as e:
                index_path = ['snippets']
                for part in e.absolute_path:
                    index_path.append('[{0}]'.format(part))
                full_message = '{0} on instance {1}:<br>{2}'.format(
                    e.message, ''.join(index_path), e.instance
                )
                errors['validation'] = full_message

        if len(errors) == 0:
            for language_info in snippets:
                language = language_info['language']
                triggers = language_info['triggers']
                for trigger_info in triggers:
                    trigger = trigger_info['trigger']
                    descriptions = trigger_info['descriptions']
                    for description_info in descriptions:
                        description = description_info['description']
                        snippet = description_info['snippet']
                        snippet_text = snippet['text']
                        total_snippets += 1
                        try:
                            build_snippet_ast(snippet_text)
                            self.update_or_enqueue(
                                language, trigger, description, snippet)
                            valid_snippets += 1
                        except SyntaxError as e:
                            syntax_errors = errors.get('syntax', {})
                            key = '{0}/{1}/{2}'.format(
                                language, trigger, description)
                            syntax_errors[key] = e.msg
                            errors['syntax'] = syntax_errors

        return valid_snippets, total_snippets, errors


class SnippetTable(QTableView):
    def __init__(self, parent, proxy, language=None, text_color=None):
        super(SnippetTable, self).__init__()
        self._parent = parent
        self.language = language
        self.proxy = proxy
        self.source_model = proxy.get_model(
            self, language.lower(), text_color=text_color)
        self.setModel(self.source_model)
        self.setItemDelegateForColumn(CMD, ItemDelegate(self))
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSortingEnabled(True)
        self.setEditTriggers(QAbstractItemView.AllEditTriggers)
        self.selectionModel().selectionChanged.connect(self.selection)
        self.verticalHeader().hide()

        self.reset_plain()

    def focusOutEvent(self, e):
        """Qt Override."""
        # self.source_model.update_active_row()
        # self._parent.delete_btn.setEnabled(False)
        super(SnippetTable, self).focusOutEvent(e)

    def focusInEvent(self, e):
        """Qt Override."""
        super(SnippetTable, self).focusInEvent(e)
        self.selectRow(self.currentIndex().row())

    def selection(self, index):
        self.update()
        self.isActiveWindow()
        self._parent.delete_snippet_btn.setEnabled(True)

    def adjust_cells(self):
        """Adjust column size based on contents."""
        self.resizeColumnsToContents()
        fm = self.horizontalHeader().fontMetrics()
        names = [fm.width(s.description) for s in self.source_model.snippets]
        if names:
            self.setColumnWidth(CMD, max(names))
        self.horizontalHeader().setStretchLastSection(True)

    def reset_plain(self):
        self.source_model.reset()
        self.adjust_cells()
        self.sortByColumn(self.source_model.TRIGGER, Qt.AscendingOrder)
        self.selectionModel().selectionChanged.connect(self.selection)

    def update_language_model(self, language):
        self.language = language.lower()
        self.source_model = self.proxy.get_model(self, language.lower())
        self.setModel(self.source_model)
        self._parent.delete_snippet_btn.setEnabled(False)
        self.reset_plain()

    def delete_snippet(self, idx):
        snippet = self.source_model.snippets.pop(idx)
        self.source_model.delete_queue.append(snippet)
        self.source_model.snippet_map.pop(
            (snippet.trigger_text, snippet.description))
        self.source_model.reset()
        self.adjust_cells()
        self.sortByColumn(self.source_model.TRIGGER, Qt.AscendingOrder)

    def show_editor(self, new_snippet=False):
        snippet = Snippet(get_option=self._parent.get_option,
                          set_option=self._parent.set_option)
        if not new_snippet:
            idx = self.currentIndex().row()
            snippet = self.source_model.row(idx)

        snippets_keys = list(self.source_model.snippet_map.keys())
        trigger_texts = list({x[0] for x in snippets_keys})
        descriptions = {}
        for trigger, description in snippets_keys:
            trigger_descriptions = descriptions.get(trigger, set({}))
            trigger_descriptions |= {description}
            descriptions[trigger] = trigger_descriptions

        dialog = SnippetEditor(self, language=self.language.lower(),
                               trigger_text=snippet.trigger_text,
                               description=snippet.description,
                               remove_trigger=snippet.remove_trigger,
                               snippet_text=snippet.snippet_text,
                               trigger_texts=trigger_texts,
                               descriptions=descriptions,
                               get_option=self._parent.get_option,
                               set_option=self._parent.set_option)
        if dialog.exec_():
            snippet = dialog.get_options()
            key = (snippet.trigger_text, snippet.description)
            self.source_model.snippet_map[key] = snippet
            self.source_model.snippets = list(
                self.source_model.snippet_map.values())
            self.source_model.reset()
            self.adjust_cells()
            self.sortByColumn(LANGUAGE, Qt.AscendingOrder)
            self._parent.set_modified(True)

    def next_row(self):
        """Move to next row from currently selected row."""
        row = self.currentIndex().row()
        rows = self.source_model.rowCount()
        if row + 1 == rows:
            row = -1
        self.selectRow(row + 1)

    def previous_row(self):
        """Move to previous row from currently selected row."""
        row = self.currentIndex().row()
        rows = self.source_model.rowCount()
        if row == 0:
            row = rows
        self.selectRow(row - 1)

    def keyPressEvent(self, event):
        """Qt Override."""
        key = event.key()
        if key in [Qt.Key_Enter, Qt.Key_Return]:
            self.show_editor()
        elif key in [Qt.Key_Backtab]:
            self.parent().reset_btn.setFocus()
        elif key in [Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right]:
            super(SnippetTable, self).keyPressEvent(event)
        else:
            super(SnippetTable, self).keyPressEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Qt Override."""
        self.show_editor()
