# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for the language services preferences page."""

from unittest.mock import Mock

from qtpy.QtCore import Signal
from qtpy.QtWidgets import QMainWindow, QVBoxLayout
import pytest

from spyder.api.preferences import SpyderPreferencesTab
from spyder.config.manager import CONF
from spyder.plugins.languageservices.api.languages import Language
from spyder.plugins.languageservices.api.provider import (
    LanguageServicesProvider,
)
from spyder.plugins.languageservices.plugin import LanguageServices
from spyder.plugins.languageservices.widgets.policies import (
    ProviderOrderList,
    RequestPolicyTable,
)
from spyder.plugins.preferences.tests.conftest import config_dialog  # noqa


class MainWindowMock(QMainWindow):
    sig_setup_finished = Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self.statusbar = Mock()
        self.console = Mock()


class TabbedTab(SpyderPreferencesTab):
    TITLE = "Tabbed"

    def __init__(self, parent):
        super().__init__(parent)
        self.box = self.create_checkbox("Flag", "flag")
        layout = QVBoxLayout()
        layout.addWidget(self.box)
        self.setLayout(layout)

    def apply_settings(self):
        self.set_option("manual", "applied")
        return {"manual"}


class TabbedProvider(LanguageServicesProvider):
    NAME = "tabbed"
    CONF_DEFAULTS = [("flag", False), ("manual", "")]
    CONF_TABS = [TabbedTab]

    def supported_languages(self):
        return frozenset({Language.PYTHON})


@pytest.fixture
def tabbed_entry_point(mocker):
    entry_point = Mock()
    entry_point.load.return_value = TabbedProvider
    mocker.patch(
        "spyder.plugins.languageservices.plugin.entry_points",
        return_value=[entry_point],
    )


@pytest.mark.parametrize(
    "config_dialog",
    [[MainWindowMock, [], [LanguageServices]]],
    indirect=True,
)
def test_config_dialog(tabbed_entry_point, config_dialog):
    configpage = config_dialog.get_page()
    assert configpage
    titles = [
        configpage.tabs.tabText(i) for i in range(configpage.tabs.count())
    ]
    assert titles == ["General", "Tabbed"]

    tab = next(t for t in configpage.provider_tabs)
    assert not tab.box.checkbox.isChecked()
    tab.box.checkbox.click()
    configpage.save_to_conf()
    configpage.apply_callback()

    assert CONF.get(
        "language_services", ("providers", "tabbed", "values", "flag")
    ) is True
    assert CONF.get(
        "language_services", ("providers", "tabbed", "values", "manual")
    ) == "applied"
    assert "flag" not in CONF.options("language_services")

    # Request policy table round-trips through the configuration. Formatting is
    # an exclusive feature, so its providers cell is a single-provider selector
    # (index 0 is "Auto", index 1 the first provider).
    table = configpage.policies_table
    row = table._methods.index("textDocument/formatting")
    table.cellWidget(row, table.COL_PROVIDERS).setCurrentIndex(1)
    configpage.save_to_conf()
    configpage.apply_callback()
    assert CONF.get("language_services", "request_policies") == {
        "formatting": {
            "enabled": True,
            "providers": ["tabbed"],
            "timeout_ms": None,
        }
    }


def test_provider_order_list_reports_selection(qtbot):
    widget = ProviderOrderList(None, ["a", "b", "c"])
    qtbot.addWidget(widget)
    # Every provider checked in global order is the default. The selection is
    # empty.
    assert widget.providers() == ()
    # An explicit subset keeps its given order.
    widget.set_providers(("b", "a"))
    assert widget.providers() == ("b", "a")
    widget.set_providers(())
    assert widget.providers() == ()


def test_request_policy_table_merge_roundtrips(qtbot):
    table = RequestPolicyTable(None, ["a", "b"])
    qtbot.addWidget(table)
    table.load({})
    assert table.policies() == {}
    row = table._methods.index("textDocument/completion")
    table.cellWidget(row, table.COL_PROVIDERS).set_providers(("b",))
    assert table.policies()["completion"] == {
        "enabled": True,
        "providers": ["b"],
        "timeout_ms": None,
    }
    table._enabled_box(row).setChecked(False)
    assert table.policies()["completion"]["enabled"] is False
