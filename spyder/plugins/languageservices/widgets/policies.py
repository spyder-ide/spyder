# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Table editor for the per-feature request policies.

Each feature's mode (merge or exclusive) is fixed and shown read-only. A merge
feature exposes a checkable, reorderable list of providers (checked providers
answer it, top-to-bottom order is their priority). An exclusive feature exposes
a single-provider selector. Either feature can be disabled.
"""

from __future__ import annotations

# Third party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QListWidget,
    QListWidgetItem,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

# Local imports
from spyder.api.translations import _
from spyder.plugins.languageservices.api.policies import (
    DEFAULT_FEATURE_POLICIES,
    RequestMode,
    RequestPolicy,
    feature_name,
)
from spyder.plugins.languageservices.api.provider import FEATURE_METHODS

AUTO_PROVIDER = _("Auto (highest priority)")
MODE_LABELS = {
    RequestMode.MERGE: _("Merge"),
    RequestMode.EXCLUSIVE: _("Exclusive"),
}


class ProviderOrderList(QListWidget):
    """Checkable, drag-reorderable provider list for a merge feature.

    Checked providers answer the feature. Their top-to-bottom order is the
    request priority. When every provider is checked in global priority order
    the selection matches the default and :meth:`providers` reports an empty
    tuple.
    """

    def __init__(self, parent, provider_names: list[str]):
        super().__init__(parent)
        self._provider_names = list(provider_names)
        self.setDragDropMode(QListWidget.InternalMove)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._fill(self._provider_names, set(self._provider_names))
        row = self.sizeHintForRow(0) if self.count() else 0
        self.setFixedHeight(row * max(self.count(), 1) + 2 * self.frameWidth())

    def _fill(self, order: list[str], checked: set[str]) -> None:
        self.clear()
        for name in order:
            item = QListWidgetItem(name, self)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(
                Qt.Checked if name in checked else Qt.Unchecked
            )

    def set_providers(self, providers: tuple[str, ...]) -> None:
        """Show ``providers`` (ordered, checked). Empty means every provider in
        global priority order."""
        if not providers:
            self._fill(self._provider_names, set(self._provider_names))
            return
        checked = set(providers)
        rest = [n for n in self._provider_names if n not in checked]
        self._fill([*providers, *rest], checked)

    def providers(self) -> tuple[str, ...]:
        """Checked provider names in display order. Empty when the selection is
        every provider in global priority order."""
        names = [
            self.item(i).text()
            for i in range(self.count())
            if self.item(i).checkState() == Qt.Checked
        ]
        if names == self._provider_names:
            return ()
        return tuple(names)


class RequestPolicyTable(QTableWidget):
    """Each row holds a feature's fixed mode, an enable switch, the answering
    providers and a per-provider timeout."""

    COL_FEATURE, COL_MODE, COL_ENABLED, COL_PROVIDERS, COL_TIMEOUT = range(5)

    def __init__(self, parent, provider_names: list[str]):
        super().__init__(parent)
        self.provider_names = list(provider_names)
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels(
            [
                _("Feature"),
                _("Mode"),
                _("Enabled"),
                _("Providers"),
                _("Timeout (ms)"),
            ]
        )
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.setSelectionMode(QTableWidget.NoSelection)
        self._methods = list(FEATURE_METHODS)
        self.setRowCount(len(self._methods))
        for row, method in enumerate(self._methods):
            mode = DEFAULT_FEATURE_POLICIES[method].mode

            feature = QTableWidgetItem(feature_name(method).replace("_", " "))
            feature.setFlags(Qt.ItemIsEnabled)
            self.setItem(row, self.COL_FEATURE, feature)

            mode_item = QTableWidgetItem(MODE_LABELS[mode])
            mode_item.setFlags(Qt.ItemIsEnabled)
            self.setItem(row, self.COL_MODE, mode_item)

            enabled = QCheckBox(self)
            enabled.setChecked(True)
            self.setCellWidget(
                row, self.COL_ENABLED, self._centered(enabled)
            )

            if mode is RequestMode.MERGE:
                providers = ProviderOrderList(self, self.provider_names)
            else:
                providers = QComboBox(self)
                providers.addItem(AUTO_PROVIDER, None)
                for name in self.provider_names:
                    providers.addItem(name, name)
            self.setCellWidget(row, self.COL_PROVIDERS, providers)
            enabled.toggled.connect(providers.setEnabled)

            timeout = QSpinBox(self)
            timeout.setRange(0, 60000)
            timeout.setSingleStep(100)
            timeout.setSpecialValueText(_("Default"))
            self.setCellWidget(row, self.COL_TIMEOUT, timeout)
        self.resizeRowsToContents()

    def _centered(self, widget: QWidget) -> QWidget:
        holder = QWidget(self)
        layout = QHBoxLayout(holder)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(widget)
        return holder

    def _enabled_box(self, row: int) -> QCheckBox:
        return self.cellWidget(row, self.COL_ENABLED).findChild(QCheckBox)

    def load(self, policies: dict[str, dict | None]) -> None:
        """Show ``policies`` (feature name -> conf dict)."""
        for row, method in enumerate(self._methods):
            policy = RequestPolicy.from_conf(
                policies.get(feature_name(method)), DEFAULT_FEATURE_POLICIES[method]
            )
            self._enabled_box(row).setChecked(policy.enabled)
            providers = self.cellWidget(row, self.COL_PROVIDERS)
            if isinstance(providers, ProviderOrderList):
                providers.set_providers(policy.providers)
            else:
                selected = policy.providers[0] if policy.providers else None
                providers.setCurrentIndex(max(providers.findData(selected), 0))
            providers.setEnabled(policy.enabled)
            self.cellWidget(row, self.COL_TIMEOUT).setValue(
                policy.timeout_ms or 0
            )
        self.resizeRowsToContents()

    def policies(self) -> dict[str, dict]:
        """Feature name -> conf dict for every feature differing from its
        default."""
        result = {}
        for row, method in enumerate(self._methods):
            name = feature_name(method)
            timeout = self.cellWidget(row, self.COL_TIMEOUT).value()
            widget = self.cellWidget(row, self.COL_PROVIDERS)
            if isinstance(widget, ProviderOrderList):
                providers = widget.providers()
            else:
                selected = widget.currentData()
                providers = (selected,) if selected is not None else ()
            policy = RequestPolicy(
                mode=DEFAULT_FEATURE_POLICIES[method].mode,
                enabled=self._enabled_box(row).isChecked(),
                providers=providers,
                timeout_ms=timeout or None,
            )
            if policy != DEFAULT_FEATURE_POLICIES[method]:
                result[name] = policy.to_conf()
        return result
