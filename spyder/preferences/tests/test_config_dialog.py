# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for configdialog.py
"""

def test_config(qtbot, global_config_dialog):
    qtbot.wait(1000)
    for index in range(global_config_dialog.pages_widget.count()):
        configpage = global_config_dialog.get_page(index)
        assert configpage.is_valid()
