# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see LICENSE.txt for details)
# -----------------------------------------------------------------------------

# Third-party imports
import pytest

# Local imports
from spyder.config.manager import CONF
from spyder.plugins.appearance.plugin import Appearance
from spyder.widgets.config import SpyderConfigPage
from spyder.plugins.preferences.tests.conftest import (
    config_dialog, MainWindowMock)


def _variant_ids(widget):
    """Theme variant ids currently listed in the schemes combobox."""
    cb = widget.schemes_combobox
    out = []
    for i in range(cb.count()):
        data = cb.itemData(i)
        if data:
            out.append(data)
    return out


def _index_for_variant(widget, variant_id):
    idx = widget.schemes_combobox.findData(variant_id)
    assert idx != -1, f"Missing combobox entry for variant {variant_id!r}"
    return idx


@pytest.mark.parametrize(
    'config_dialog',
    [[MainWindowMock, [], [Appearance]]],
    indirect=True)
def test_apply_theme_variant_requests_restart(config_dialog, mocker, qtbot):
    """Changing the selected theme variant applies config and asks for restart."""
    mocker.patch.object(
        SpyderConfigPage, "prompt_restart_required", return_value=True
    )
    mocker.patch.object(SpyderConfigPage, "restart")
    mocker.patch.object(CONF, "disable_notifications")

    dlg = config_dialog
    widget = dlg.get_page()

    variant_ids = _variant_ids(widget)
    if len(variant_ids) < 2:
        pytest.skip("Need at least two theme variants in Appearance preferences")

    initial = widget.current_scheme
    others = [v for v in variant_ids if v != initial]
    assert others, "Expected a second theme variant besides the current one"

    assert SpyderConfigPage.prompt_restart_required.call_count == 0
    assert SpyderConfigPage.restart.call_count == 0
    assert CONF.disable_notifications.call_count == 0

    other = others[0]
    widget.schemes_combobox.setCurrentIndex(_index_for_variant(widget, other))
    dlg.apply_btn.click()
    assert SpyderConfigPage.prompt_restart_required.call_count == 1
    assert SpyderConfigPage.restart.call_count == 1
    assert CONF.disable_notifications.call_count == 1

    widget.schemes_combobox.setCurrentIndex(_index_for_variant(widget, initial))
    dlg.apply_btn.click()
    assert SpyderConfigPage.prompt_restart_required.call_count == 2
    assert SpyderConfigPage.restart.call_count == 2
    assert CONF.disable_notifications.call_count == 2

    third_candidates = [v for v in variant_ids if v not in (initial, other)]
    if third_candidates:
        third = third_candidates[0]
        widget.schemes_combobox.setCurrentIndex(_index_for_variant(widget, third))
        dlg.apply_btn.click()
        assert SpyderConfigPage.prompt_restart_required.call_count == 3
        assert SpyderConfigPage.restart.call_count == 3
        assert CONF.disable_notifications.call_count == 3
