# -*- coding: utf-8 -*-
#
# Copyright © 2009- The Spyder Development Team
# Licensed under the terms of the MIT License
#

"""
"""

# Third party imports
from qtpy.QtCore import Qt
from pytestqt import qtbot  # analysis:ignore

# Local imports
from spyderlib.widgets.arraybuilder import NumpyArrayDialog


class TestNumpyArrayBuilder:
    def test_array_inline_array(self, qtbot):  # analysis:ignore
        dlg = NumpyArrayDialog(inline=True)
        dlg.show()
        qtbot.addWidget(dlg)

        qtbot.keyClicks(dlg.widget, '1 2 3  4 5 6')
        qtbot.keyPress(dlg.widget, Qt.Key_Return)

        expected_value = 'np.array([[1, 2, 3],\n          [4, 5, 6]])'
        value = dlg.text()
        assert expected_value == value

    def test_array_inline_matrix(self, qtbot):  # analysis:ignore
        dlg = NumpyArrayDialog(inline=True)
        dlg.show()
        qtbot.addWidget(dlg)

        qtbot.keyClicks(dlg.widget, '4 5 6  7 8 9')
        qtbot.keyPress(dlg.widget, Qt.Key_Return, modifier=Qt.ControlModifier)

        expected_value = 'np.matrix([[4, 5, 6],\n           [7, 8, 9]])'
        value = dlg.text()
        assert expected_value == value

    def test_array_inline_array_invalid(self, qtbot):  # analysis:ignore
        dlg = NumpyArrayDialog(inline=True)
        dlg.show()
        qtbot.addWidget(dlg)

        qtbot.keyClicks(dlg.widget, '1 2  3 4  5 6 7')
        qtbot.keyPress(dlg.widget, Qt.Key_Return)
        dlg.update_warning()

        assert not dlg.is_valid()

    def test_array_inline_1d_array(self, qtbot):  # analysis:ignore
        dlg = NumpyArrayDialog(inline=True)
        dlg.show()
        qtbot.addWidget(dlg)

        qtbot.keyClicks(dlg.widget, '4 5 6')
        qtbot.keyPress(dlg.widget, Qt.Key_Return, modifier=Qt.ControlModifier)

        expected_value = 'np.matrix([4, 5, 6])'
        value = dlg.text()
        assert expected_value == value

    def test_array_inline_nan_array(self, qtbot):  # analysis:ignore
        dlg = NumpyArrayDialog(inline=True)
        dlg.show()
        qtbot.addWidget(dlg)

        qtbot.keyClicks(dlg.widget, '4 nan 6 8 9')
        qtbot.keyPress(dlg.widget, Qt.Key_Return, modifier=Qt.ControlModifier)

        expected_value = 'np.matrix([4, np.nan, 6, 8, 9])'
        value = dlg.text()
        assert expected_value == value

    def test_array_inline_force_float_array(self, qtbot):  # analysis:ignore
        dlg = NumpyArrayDialog(inline=True, force_float=True)
        dlg.show()
        qtbot.addWidget(dlg)

        qtbot.keyClicks(dlg.widget, '4 5 6 8 9')
        qtbot.keyPress(dlg.widget, Qt.Key_Return, modifier=Qt.ControlModifier)

        expected_value = 'np.matrix([4.0, 5.0, 6.0, 8.0, 9.0])'
        value = dlg.text()
        assert expected_value == value

    def test_array_inline_force_float_error_array(self, qtbot):  # analysis:ignore
        dlg = NumpyArrayDialog(inline=True, force_float=True)
        dlg.show()
        qtbot.addWidget(dlg)

        qtbot.keyClicks(dlg.widget, '4 5 6 a 9')
        qtbot.keyPress(dlg.widget, Qt.Key_Return, modifier=Qt.ControlModifier)

        expected_value = 'np.matrix([4.0, 5.0, 6.0, a, 9.0])'
        value = dlg.text()
        assert expected_value == value

    def test_array_table_array(self, qtbot):  # analysis:ignore
        dlg = NumpyArrayDialog(inline=False)
        dlg.show()
        qtbot.addWidget(dlg)

        qtbot.keyClick(dlg.widget, Qt.Key_1)
        qtbot.keyClick(dlg.widget, Qt.Key_Tab)
        qtbot.keyClick(dlg.widget, Qt.Key_2)
        qtbot.keyClick(dlg.widget, Qt.Key_Tab)
        qtbot.keyClick(dlg.widget, Qt.Key_Backtab)  # Needed hack
        qtbot.keyClick(dlg.widget, Qt.Key_3)
        qtbot.keyClick(dlg.widget, Qt.Key_Tab)
        qtbot.keyClick(dlg.widget, Qt.Key_4)
        qtbot.keyClick(dlg.widget, Qt.Key_Tab)
        qtbot.keyClick(dlg.widget, Qt.Key_5)
        qtbot.keyClick(dlg.widget, Qt.Key_Tab)
        qtbot.keyClick(dlg.widget, Qt.Key_6)
        qtbot.keyClick(dlg.widget, Qt.Key_Tab)  # Needed hack
        qtbot.keyClick(dlg.widget, Qt.Key_Return, modifier=Qt.NoModifier)

        expected_value = 'np.array([[1, 2, 3],\n          [4, 5, 6]])'
        value = dlg.text()
        assert expected_value == value

    def test_array_table_matrix(self, qtbot):  # analysis:ignore
        dlg = NumpyArrayDialog(inline=False)
        dlg.show()
        qtbot.addWidget(dlg)

        qtbot.keyClick(dlg.widget, Qt.Key_1)
        qtbot.keyClick(dlg.widget, Qt.Key_Tab)
        qtbot.keyClick(dlg.widget, Qt.Key_2)
        qtbot.keyClick(dlg.widget, Qt.Key_Tab)
        qtbot.keyClick(dlg.widget, Qt.Key_Backtab)  # Needed hack
        qtbot.keyClick(dlg.widget, Qt.Key_3)
        qtbot.keyClick(dlg.widget, Qt.Key_Tab)
        qtbot.keyClick(dlg.widget, Qt.Key_4)
        qtbot.keyClick(dlg.widget, Qt.Key_Tab)
        qtbot.keyClick(dlg.widget, Qt.Key_5)
        qtbot.keyClick(dlg.widget, Qt.Key_Tab)
        qtbot.keyClick(dlg.widget, Qt.Key_6)
        qtbot.keyClick(dlg.widget, Qt.Key_Tab)  # Needed hack
        qtbot.keyClick(dlg.widget, Qt.Key_Return, modifier=Qt.ControlModifier)

        expected_value = 'np.matrix([[1, 2, 3],\n           [4, 5, 6]])'
        value = dlg.text()
        assert expected_value == value

    def test_array_table_array_empty_items(self, qtbot):  # analysis:ignore
        dlg = NumpyArrayDialog(inline=False)
        dlg.show()
        qtbot.addWidget(dlg)

        qtbot.keyClick(dlg.widget, Qt.Key_Tab)
        qtbot.keyClick(dlg.widget, Qt.Key_2)
        qtbot.keyClick(dlg.widget, Qt.Key_Tab)
        qtbot.keyClick(dlg.widget, Qt.Key_Backtab)  # Needed hack
        qtbot.keyClick(dlg.widget, Qt.Key_3)
        qtbot.keyClick(dlg.widget, Qt.Key_Tab)
        qtbot.keyClick(dlg.widget, Qt.Key_Tab)
        qtbot.keyClick(dlg.widget, Qt.Key_5)
        qtbot.keyClick(dlg.widget, Qt.Key_Tab)
        qtbot.keyClick(dlg.widget, Qt.Key_6)
        qtbot.keyClick(dlg.widget, Qt.Key_Tab)  # Needed hack
        qtbot.keyClick(dlg.widget, Qt.Key_Return, modifier=Qt.NoModifier)

        expected_value = 'np.array([[0, 2, 3],\n          [0, 5, 6]])'
        value = dlg.text()
        assert expected_value == value

    def test_array_table_array_spaces_in_item(self, qtbot):  # analysis:ignore
        dlg = NumpyArrayDialog(inline=False)
        dlg.show()
        qtbot.addWidget(dlg)

        qtbot.keyClicks(dlg.widget, '   ')
        qtbot.keyClick(dlg.widget, Qt.Key_Tab)
        qtbot.keyClick(dlg.widget, Qt.Key_2)
        qtbot.keyClick(dlg.widget, Qt.Key_Tab)
        qtbot.keyClick(dlg.widget, Qt.Key_Backtab)
        qtbot.keyClick(dlg.widget, Qt.Key_3)
        qtbot.keyClick(dlg.widget, Qt.Key_Tab)
        qtbot.keyClick(dlg.widget, Qt.Key_Tab)
        qtbot.keyClick(dlg.widget, Qt.Key_5)
        qtbot.keyClick(dlg.widget, Qt.Key_Tab)
        qtbot.keyClick(dlg.widget, Qt.Key_6)
        qtbot.keyClick(dlg.widget, Qt.Key_Tab)  # Needed hack
        qtbot.keyClick(dlg.widget, Qt.Key_Return, modifier=Qt.NoModifier)

        expected_value = 'np.array([[0, 2, 3],\n          [0, 5, 6]])'
        value = dlg.text()
        assert expected_value == value

    def test_array_table_matrix_empty(self, qtbot):  # analysis:ignore
        dlg = NumpyArrayDialog(inline=False)
        dlg.show()
        qtbot.addWidget(dlg)

        qtbot.keyClick(dlg.widget, Qt.Key_Return, modifier=Qt.NoModifier)

        expected_value = ''
        value = dlg.text()
        assert expected_value == value
