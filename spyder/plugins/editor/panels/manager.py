# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2013-2016 Colin Duquesnoy and others (see pyqode/AUTHORS.rst)
# Copyright (c) 2016- Spyder Project Contributors (see AUTHORS.txt)
#
# Distributed under the terms of the MIT License
# (see NOTICE.txt in the Spyder root directory for details)
# -----------------------------------------------------------------------------

"""
Editor panels manager.

It draws all panels inside a CodeEditor.
"""

# Standard library imports
from __future__ import annotations
import logging
from typing import TYPE_CHECKING

# Local imports
from spyder.plugins.editor.api.manager import Manager
from spyder.plugins.editor.api.panel import Panel, PanelPosition


if TYPE_CHECKING:
    from spyder.plugins.editor.widgets.codeeditor import CodeEditor


logger = logging.getLogger(__name__)


class PanelsManager(Manager):
    """
    Manage panels and draw them inside the margins of a CodeEditor widget.
    """

    def __init__(self, editor: "CodeEditor"):
        super().__init__(editor)
        self._cached_cursor_pos = (-1, -1)
        self._margin_sizes = (0, 0, 0, 0)
        self._top = self._left = self._right = self._bottom = -1
        self._panels = {
            PanelPosition.TOP: {},
            PanelPosition.LEFT: {},
            PanelPosition.RIGHT: {},
            PanelPosition.BOTTOM: {},
            PanelPosition.FLOATING: {}
        }

        try:
            editor.blockCountChanged.connect(self._update_viewport_margins)
            editor.updateRequest.connect(self._update)
        except AttributeError:
            # QTextEdit
            editor.document().blockCountChanged.connect(
                self._update_viewport_margins
            )

    def register(self, panel: Panel, position=PanelPosition.LEFT) -> Panel:
        """
        Register a panel in a CodeEditor.

        Paramaters
        ----------
        panel: Panel
            The panel to install.
        position: PanelPosition
            Position where the panel must be installed.

        Returns
        -------
        panel: Panel
            The installed panel.
        """
        assert panel is not None
        pos_to_string = {
            PanelPosition.BOTTOM: 'bottom',
            PanelPosition.LEFT: 'left',
            PanelPosition.RIGHT: 'right',
            PanelPosition.TOP: 'top',
            PanelPosition.FLOATING: 'floating'
        }
        logger.debug(
            "adding panel %s at %s" % (panel.name, pos_to_string[position])
        )

        panel.order_in_zone = len(self._panels[position])
        self._panels[position][panel.name] = panel
        panel.position = position
        panel.on_install(self.editor)

        return panel

    def remove(self, name_or_class: str | type[Panel]) -> Panel:
        """
        Remove the specified panel.

        Paramaters
        ----------
        name_or_class: str or type[Panel]
            Name or class of the panel to remove.

        Returns
        -------
        panel: Panel
            The removed panel.
        """
        logger.debug('Removing panel %s' % name_or_class)
        panel = self.get(name_or_class)
        panel.on_uninstall()
        panel.hide()
        panel.setParent(None)
        return self._panels[panel.position].pop(panel.name, None)

    def clear(self) -> None:
        """Remove all panels from the editor."""
        for zone in PanelPosition:
            while len(self._panels[zone]):
                key = sorted(list(self._panels[zone].keys()))[0]
                panel = self.remove(key)
                panel.setParent(None)

    def get(self, name_or_class: str | type[Panel]) -> Panel:
        """
        Get a specific panel.

        Paramaters
        ----------
        name_or_class: str or type[Panel]
            Name or class of the panel to get.

        Returns
        -------
        panel: Panel
            The specified panel instance.

        Raises
        ------
        KeyError
            If panel is not among the installed ones.
        """
        if not isinstance(name_or_class, str):
            name_or_class = name_or_class.__name__

        for zone in PanelPosition:
            try:
                panel = self._panels[zone][name_or_class]
            except KeyError:
                pass
            else:
                return panel

        raise KeyError(name_or_class)

    def __iter__(self):
        lst = []
        for __, zone_dict in self._panels.items():
            for __, panel in zone_dict.items():
                lst.append(panel)
        return iter(lst)

    def __len__(self):
        lst = []
        for __, zone_dict in self._panels.items():
            for __, panel in zone_dict.items():
                lst.append(panel)
        return len(lst)

    def panels_for_zone(self, zone: PanelPosition) -> list[Panel]:
        """
        Get the list of panels attached to the specified zone.

        Paramaters
        ----------
        zone: PanelPosition
            The zone to get the panels for.

        Returns
        -------
        list[Panel]
        """
        return list(self._panels[zone].values())

    def refresh(self) -> None:
        """Refresh the editor panels (resize and update margins)."""
        self.resize()
        self._update(self.editor.contentsRect(), 0, force_update_margins=True)

    def resize(self):
        """Resize panels."""
        crect = self.editor.contentsRect()
        view_crect = self.editor.viewport().contentsRect()
        s_bottom, s_left, s_right, s_top = self._compute_zones_sizes()
        tw = s_left + s_right
        th = s_bottom + s_top
        w_offset = crect.width() - (view_crect.width() + tw)
        h_offset = crect.height() - (view_crect.height() + th)

        left = 0
        panels = self.panels_for_zone(PanelPosition.LEFT)
        panels.sort(key=lambda panel: panel.order_in_zone, reverse=True)
        for panel in panels:
            if not panel.isVisible():
                continue
            panel.adjustSize()
            size_hint = panel.sizeHint()
            panel.setGeometry(crect.left() + left,
                              crect.top() + s_top,
                              size_hint.width(),
                              crect.height() - s_bottom - s_top - h_offset)
            left += size_hint.width()

        right = 0
        panels = self.panels_for_zone(PanelPosition.RIGHT)
        panels.sort(key=lambda panel: panel.order_in_zone, reverse=True)
        for panel in panels:
            if not panel.isVisible():
                continue
            size_hint = panel.sizeHint()
            panel.setGeometry(
                crect.right() - right - size_hint.width() - w_offset,
                crect.top(),
                size_hint.width(),
                crect.height() - h_offset)
            right += size_hint.width()

        top = 0
        panels = self.panels_for_zone(PanelPosition.TOP)
        panels.sort(key=lambda panel: panel.order_in_zone)
        for panel in panels:
            if not panel.isVisible():
                continue
            size_hint = panel.sizeHint()
            panel.setGeometry(crect.left(),
                              crect.top() + top,
                              crect.width() - s_right - w_offset,
                              size_hint.height())
            top += size_hint.height()

        bottom = 0
        panels = self.panels_for_zone(PanelPosition.BOTTOM)
        panels.sort(key=lambda panel: panel.order_in_zone)
        for panel in panels:
            if not panel.isVisible():
                continue
            size_hint = panel.sizeHint()
            panel.setGeometry(
                crect.left(),
                crect.bottom() - bottom - size_hint.height() - h_offset,
                crect.width() - s_right - w_offset,
                size_hint.height())
            bottom += size_hint.height()

    def update_floating_panels(self):
        """Update floating panels."""
        crect = self.editor.contentsRect()
        panels = self.panels_for_zone(PanelPosition.FLOATING)
        for panel in panels:
            if not panel.isVisible():
                continue
            panel.set_geometry(crect)

    def _update(self, rect, delta_y, force_update_margins=False):
        """Update panels."""
        if not self:
            return
        line, col = self.editor.get_cursor_line_column()
        oline, ocol = self._cached_cursor_pos
        for zones_id, zone in self._panels.items():
            if (
                zones_id == PanelPosition.TOP
                or zones_id == PanelPosition.BOTTOM
            ):
                continue
            panels = list(zone.values())
            for panel in panels:
                if panel.scrollable and delta_y:
                    panel.scroll(0, delta_y)
                if line != oline or col != ocol or panel.scrollable:
                    panel.update(0, rect.y(), panel.width(), rect.height())
        self._cached_cursor_pos = line, col
        if (rect.contains(self.editor.viewport().rect()) or
                force_update_margins):
            self._update_viewport_margins()
        self.update_floating_panels()

    def _update_viewport_margins(self):
        """Update viewport margins."""
        top = 0
        left = 0
        right = 0
        bottom = 0

        for panel in self.panels_for_zone(PanelPosition.LEFT):
            if panel.isVisible():
                width = panel.sizeHint().width()
                left += width

        for panel in self.panels_for_zone(PanelPosition.RIGHT):
            if panel.isVisible():
                width = panel.sizeHint().width()
                right += width

        for panel in self.panels_for_zone(PanelPosition.TOP):
            if panel.isVisible():
                height = panel.sizeHint().height()
                top += height

        for panel in self.panels_for_zone(PanelPosition.BOTTOM):
            if panel.isVisible():
                height = panel.sizeHint().height()
                bottom += height

        new_size = (top, left, right, bottom)
        if new_size != self._margin_sizes:
            self._margin_sizes = new_size
            self.editor.setViewportMargins(left, top, right, bottom)

    def margin_size(self, position=PanelPosition.LEFT) -> float:
        """
        Get the margin size of a specific position.

        Paramaters
        ----------
        position: PanelPosition
            The position to get the margin for.

        Returns
        -------
        float:
            The margin size of the specified position.
        """
        return self._margin_sizes[position.value]

    def _compute_zones_sizes(self):
        """Compute panel zone sizes."""
        # Left panels
        left = 0
        for panel in self.panels_for_zone(PanelPosition.LEFT):
            if not panel.isVisible():
                continue
            size_hint = panel.sizeHint()
            left += size_hint.width()

        # Right panels
        right = 0
        for panel in self.panels_for_zone(PanelPosition.RIGHT):
            if not panel.isVisible():
                continue
            size_hint = panel.sizeHint()
            right += size_hint.width()

        # Top panels
        top = 0
        for panel in self.panels_for_zone(PanelPosition.TOP):
            if not panel.isVisible():
                continue
            size_hint = panel.sizeHint()
            top += size_hint.height()

        # Bottom panels
        bottom = 0
        for panel in self.panels_for_zone(PanelPosition.BOTTOM):
            if not panel.isVisible():
                continue
            size_hint = panel.sizeHint()
            bottom += size_hint.height()
        self._top, self._left, self._right, self._bottom = (
            top, left, right, bottom)

        return bottom, left, right, top
