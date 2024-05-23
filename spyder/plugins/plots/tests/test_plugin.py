# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Tests for the Plots plugin.
"""

from unittest.mock import Mock

import pytest

from spyder.config.manager import CONF
from spyder.plugins.plots.plugin import Plots
from spyder.plugins.plots.widgets.main_widget import PlotsWidgetActions
from spyder.plugins.plots.widgets.tests.test_plots_widgets import (
    add_figures_to_browser,
)
from spyder.utils.stylesheet import APP_STYLESHEET


@pytest.fixture
def plots_plugin(qapp, qtbot):
    plots = Plots(None, configuration=CONF)
    plots.get_widget().setMinimumSize(700, 500)
    plots.get_widget().add_shellwidget(Mock())
    qtbot.addWidget(plots.get_widget())
    # qapp.setStyleSheet(str(APP_STYLESHEET))
    plots.get_widget().show()
    return plots


def test_fit_action(plots_plugin, tmpdir, qtbot):
    """Test that the fit action works as expected."""
    main_widget = plots_plugin.get_widget()

    # Action should not be checked when no plots are available
    assert not main_widget.fit_action.isChecked()

    # Add some plots
    figbrowser = main_widget.current_widget()
    figviewer = figbrowser.figviewer
    add_figures_to_browser(figbrowser, 2, tmpdir)

    # Action should be checked now and zoom factor less than 100%
    assert main_widget.fit_action.isChecked()
    assert main_widget.zoom_disp.value() < 100

    # Plot should be zoomed in at full size when unchecking action
    main_widget.fit_action.setChecked(False)
    assert main_widget.zoom_disp.value() == 100
    qtbot.wait(200)
    assert figviewer.horizontalScrollBar().isVisible()

    # Action should be checked for next plot
    main_widget.next_plot()
    assert main_widget.fit_action.isChecked()

    # Action should be unchecked when going back to the previous plot
    main_widget.previous_plot()
    assert not main_widget.fit_action.isChecked()

    # Plot should be fitted when checking the action again
    main_widget.fit_action.setChecked(True)
    assert main_widget.zoom_disp.value() < 100
    qtbot.wait(200)
    assert not figviewer.horizontalScrollBar().isVisible()


def test_zoom_actions(plots_plugin, qtbot, tmpdir):
    """Test that the behavior of the zoom actions work as expected."""
    main_widget = plots_plugin.get_widget()
    zoom_in_action = main_widget.get_action(PlotsWidgetActions.ZoomIn)
    zoom_out_action = main_widget.get_action(PlotsWidgetActions.ZoomOut)

    # Zoom in/out actions should be disabled when no plots are available
    assert not zoom_in_action.isEnabled()
    assert not zoom_out_action.isEnabled()

    # Add some plots
    figbrowser = main_widget.current_widget()
    figviewer = figbrowser.figviewer
    add_figures_to_browser(figbrowser, 3, tmpdir)

    # Zoom in/out actions should be enabled now
    assert zoom_in_action.isEnabled()
    assert zoom_out_action.isEnabled()

    # Zoom in first plot twice
    for __ in range(2):
        main_widget.zoom_in()
        qtbot.wait(100)

    # Save zoom and scrollbar values to test them later
    qtbot.wait(200)
    zoom_1 = main_widget.zoom_disp.value()
    vscrollbar = figviewer.verticalScrollBar()
    hscrollbar = figviewer.horizontalScrollBar()
    vscrollbar_value_1 = vscrollbar.value()
    hscrollbar_value_1 = hscrollbar.value()

    # Fit action should be unchecked now
    assert not main_widget.fit_action.isChecked()

    # Next plot should be still fitted
    main_widget.next_plot()
    assert main_widget.fit_action.isChecked()
    assert main_widget.zoom_disp.value() < 100
    assert not hscrollbar.isVisible()
    assert not vscrollbar.isVisible()

    # Zoom out twice this plot
    for __ in range(2):
        main_widget.zoom_out()
        qtbot.wait(100)

    # Fit action should be unchecked now
    assert not main_widget.fit_action.isChecked()

    # Save zoom level for later
    zoom_2 = main_widget.zoom_disp.value()

    # Next plot should be still fitted
    main_widget.next_plot()
    assert main_widget.fit_action.isChecked()

    # Return to the first plot
    for __ in range(2):
        main_widget.previous_plot()
        qtbot.wait(100)

    # Check zoom level and scrollbars are restored
    qtbot.wait(200)
    assert main_widget.zoom_disp.value() == zoom_1
    assert vscrollbar.value() == vscrollbar_value_1
    assert hscrollbar.value() == hscrollbar_value_1

    # Move to next plot and check zoom level is restored
    main_widget.next_plot()
    assert main_widget.zoom_disp.value() == zoom_2
