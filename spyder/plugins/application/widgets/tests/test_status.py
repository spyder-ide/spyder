# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# ----------------------------------------------------------------------------

"""Tests for status bar widget."""

# Standard library imports
import datetime

# Third-party imports
from flaky import flaky

# Local imports
from spyder.plugins.statusbar.widgets.tests.test_status import status_bar  # noqa
from spyder.plugins.application.widgets.status import InAppAppealStatus


@flaky(max_runs=5)
def test_inapp_appeal_status_bar(status_bar, qtbot):  # noqa
    """Test in-app appeal status bar widget."""
    plugin, window = status_bar
    widget = InAppAppealStatus(window)
    plugin.add_status_widget(widget)

    # The widget should be visible on a clean config
    assert widget.isVisible()

    # The last day the widget is shown should be today
    today = datetime.date.today()
    widget.get_conf("last_inapp_appeal") == str(today)

    # The widget should be visible during a day
    qtbot.wait(1000)
    widget.update_status()
    assert widget.isVisible()

    # The widget should be hidden if it was shown less than DAYS_TO_SHOW_AGAIN
    # ago
    some_days_ago = today - datetime.timedelta(
        days=widget.DAYS_TO_SHOW_AGAIN - 5
    )
    widget.set_conf("last_inapp_appeal", str(some_days_ago))
    widget.update_status()
    assert not widget.isVisible()

    # But it should be visible again if it was shown DAYS_TO_SHOW_AGAIN ago
    days_to_show_again = today - datetime.timedelta(
        days=widget.DAYS_TO_SHOW_AGAIN
    )
    widget.set_conf("last_inapp_appeal", str(days_to_show_again))
    widget.update_status()
    assert widget.isVisible()
