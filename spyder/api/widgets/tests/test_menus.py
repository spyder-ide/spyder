# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Tests for menus.py .
"""

from spyder.api.widgets.menus import (
    MENU_SEPARATOR,
    OptionsMenuSections,
    PluginMainWidgetOptionsMenu,
    SpyderAction,
    SpyderMenu,
)


def test_add_action_with_before_section(qtbot):
    """
    Check that the actions in a menu are in the right order if
    before_section is used.
    """
    action1 = SpyderAction('action1', action_id='action1')
    action2 = SpyderAction('action2', action_id='action2')
    action3 = SpyderAction('action3', action_id='action3')
    action4 = SpyderAction('action4', action_id='action4')

    menu = SpyderMenu()
    menu.add_action(action1, section='section1', before_section='section2')
    menu.add_action(action4, section='section4')
    menu.add_action(action2, section='section2', before_section='section3')
    menu.add_action(action3, section='section3', before_section='section4')

    result = menu.get_actions()
    expected = [
        action1,
        MENU_SEPARATOR,
        action2,
        MENU_SEPARATOR,
        action3,
        MENU_SEPARATOR,
        action4,
        MENU_SEPARATOR
    ]
    assert result == expected


def test_options_menu_switch_tabs_section_above_bottom(qtbot):
    """
    Check that the switch tabs section is rendered between the plugin
    sections and the bottom section, regardless of the order it was added.
    """
    bottom = SpyderAction('bottom', action_id='bottom')
    switch = SpyderAction('switch', action_id='switch')
    plugin = SpyderAction('plugin', action_id='plugin')

    menu = PluginMainWidgetOptionsMenu()
    menu.add_action(bottom, section=OptionsMenuSections.Bottom)
    menu.add_action(switch, section=OptionsMenuSections.SwitchTabs)
    menu.add_action(plugin, section='plugin_section')
    menu.render()

    result = [action for action in menu.actions() if not action.isSeparator()]
    assert result == [plugin, switch, bottom]
