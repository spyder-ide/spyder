"""Tests for tabs widgets."""

from pathlib import Path

from qtpy.QtCore import QEvent, QPoint, QPointF, Qt
from qtpy.QtGui import QMouseEvent
from qtpy.QtTest import QTest
from qtpy.QtWidgets import QApplication, QWidget

from spyder.widgets.tabs import BaseTabs


def make_tabs(qtbot, names):
    """Create tabs whose tooltips contain their paths."""
    tabs = BaseTabs(None, menu_use_tooltips=True)
    qtbot.addWidget(tabs)
    pages = []
    for name in names:
        page = QWidget()
        pages.append(page)
        index = tabs.addTab(page, Path(name).name)
        tabs.setTabToolTip(index, name)
    tabs.update_browse_tabs_menu()
    return tabs, pages


def mouse_event(event_type, position, modifiers):
    """Create a left-button mouse event."""
    buttons = (
        Qt.NoButton
        if event_type == QEvent.MouseButtonRelease
        else Qt.LeftButton
    )
    return QMouseEvent(
        event_type,
        QPointF(position),
        Qt.LeftButton,
        buttons,
        modifiers,
    )


def test_browse_tabs_menu_elides_long_paths(qtbot):
    """Long paths are elided and only shortened paths get tooltips."""
    long_path = "C:/" + "very-long-directory/" * 20 + "module.py"
    tabs, _pages = make_tabs(qtbot, ["first.py", long_path])
    actions = tabs.browse_tabs_menu.actions()

    assert actions[0].text() == "first.py"
    assert actions[0].property("full_path_tooltip") == ""
    assert "…" in actions[1].text()
    assert actions[1].property("full_path_tooltip") == long_path


def test_browse_tabs_menu_tooltip_restores_common_path(qtbot, tmp_path):
    """The tooltip restores a common directory omitted from menu text."""
    paths = [tmp_path / "first.py", tmp_path / "second.py"]
    for path in paths:
        path.touch()

    tabs, _pages = make_tabs(qtbot, [str(path) for path in paths])
    actions = tabs.browse_tabs_menu.actions()

    assert actions[0].text() == "first.py"
    assert actions[0].property("full_path_tooltip") == str(paths[0])


def test_regular_browse_action_switches_tabs(qtbot):
    """A regular click still selects its tab."""
    tabs, pages = make_tabs(qtbot, ["first.py", "second.py"])

    tabs.browse_tabs_menu.actions()[1].trigger()

    assert tabs.currentWidget() is pages[1]


def test_shift_drag_reorders_and_keeps_menu_open(qtbot):
    """Shift-drag reorders tabs and permits another action afterwards."""
    tabs, pages = make_tabs(
        qtbot, ["first.py", "second.py", "third.py", "fourth.py"]
    )
    menu = tabs.browse_tabs_menu
    menu.popup(QPoint(100, 100))
    qtbot.waitUntil(menu.isVisible)
    source_position = menu.actionGeometry(menu.actions()[0]).center()
    target_rect = menu.actionGeometry(menu.actions()[2])
    target_position = QPoint(
        target_rect.center().x(),
        target_rect.center().y() + target_rect.height() // 4,
    )
    moved = []
    tabs.tabBar().tabMoved.connect(lambda old, new: moved.append((old, new)))

    QTest.mousePress(menu, Qt.LeftButton, Qt.ShiftModifier, source_position)
    assert menu.drag_action is menu.actions()[0]
    menu.mouseMoveEvent(mouse_event(
        QEvent.MouseMove, target_position, Qt.ShiftModifier
    ))
    assert menu.drop_action is menu.actions()[2]
    assert menu.drop_after
    QTest.mouseRelease(menu, Qt.LeftButton, Qt.ShiftModifier, target_position)
    QApplication.processEvents()

    assert moved == [(0, 2)]
    assert menu.isVisible()
    assert [tabs.widget(index) for index in range(tabs.count())] == [
        pages[1], pages[2], pages[0], pages[3]
    ]
    assert [action.text() for action in menu.actions()] == [
        "second.py", "third.py", "first.py", "fourth.py"
    ]

    # The moved action must select its new tab index, not its old one.
    menu.actions()[2].trigger()
    assert tabs.currentWidget() is pages[0]


def test_shift_drag_across_native_columns(qtbot):
    """Shift-drag works between columns created by the native menu."""
    names = [f"module-{index:03d}.py" for index in range(100)]
    tabs, pages = make_tabs(qtbot, names)
    menu = tabs.browse_tabs_menu
    menu.popup(QPoint(0, 0))
    qtbot.waitUntil(menu.isVisible)
    actions = menu.actions()
    source_rect = menu.actionGeometry(actions[0])
    target_index = next(
        index for index, action in enumerate(actions)
        if menu.actionGeometry(action).left() > source_rect.left()
    )
    target_rect = menu.actionGeometry(actions[target_index])
    target_position = QPoint(
        target_rect.center().x(),
        target_rect.center().y() + target_rect.height() // 4,
    )

    QTest.mousePress(
        menu, Qt.LeftButton, Qt.ShiftModifier, source_rect.center()
    )
    QTest.mouseRelease(
        menu, Qt.LeftButton, Qt.ShiftModifier, target_position
    )
    QApplication.processEvents()

    assert tabs.widget(target_index) is pages[0]
    assert menu.isVisible()


def test_shift_click_without_movement_does_nothing(qtbot):
    """Shift-click alone neither selects nor moves a tab."""
    tabs, pages = make_tabs(qtbot, ["first.py", "second.py"])
    menu = tabs.browse_tabs_menu
    menu.ensurePolished()
    menu.adjustSize()
    position = menu.actionGeometry(menu.actions()[1]).center()

    menu.mousePressEvent(mouse_event(
        QEvent.MouseButtonPress, position, Qt.ShiftModifier
    ))
    menu.mouseReleaseEvent(mouse_event(
        QEvent.MouseButtonRelease, position, Qt.ShiftModifier
    ))

    assert tabs.currentWidget() is pages[0]
    assert menu.drag_action is None


def test_plain_press_does_not_start_drag(qtbot):
    """A plain left-button press retains native menu behavior."""
    tabs, _pages = make_tabs(qtbot, ["first.py", "second.py"])
    menu = tabs.browse_tabs_menu
    menu.ensurePolished()
    menu.adjustSize()
    position = menu.actionGeometry(menu.actions()[0]).center()

    menu.mousePressEvent(mouse_event(
        QEvent.MouseButtonPress, position, Qt.NoModifier
    ))

    assert menu.drag_action is None
