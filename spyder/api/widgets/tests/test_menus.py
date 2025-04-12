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

from spyder.api.widgets.menus import MENU_SEPARATOR, SpyderAction, SpyderMenu


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
