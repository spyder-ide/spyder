# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# ----------------------------------------------------------------------------

"""Tests for the in-app appeal widget."""

# Local imports
from spyder.plugins.application.widgets.appeal import InAppAppealDialog
from spyder.plugins.help.tests.test_plugin import check_text


def test_inapp_appeal(qtbot):  # noqa
    """Test in-app appeal widget."""
    widget = InAppAppealDialog()
    webpage = widget._webview.page()
    widget.show()

    # Check text in Appeal view
    widget.set_message(appeal=True)

    for text in ["independent project", "support", "NumFOCUS"]:
        qtbot.waitUntil(lambda: check_text(webpage, text), timeout=6000)

    # Check text in Changelog view
    widget.set_message(appeal=False)

    for text in ["Changes in version", "Important fixes", "Full changelog"]:
        qtbot.waitUntil(lambda: check_text(webpage, text), timeout=6000)
