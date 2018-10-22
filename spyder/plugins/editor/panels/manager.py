# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2013-2016 Colin Duquesnoy and others (see pyqode/AUTHORS.rst)
# Copyright (c) 2016- Spyder Project Contributors (see AUTHORS.txt)
#
# Distributed under the terms of the MIT License
# (see NOTICE.txt in the Spyder root directory for details)
# -----------------------------------------------------------------------------

"""
Contains the panels controller, drawing the panel inside CodeEditor's margins.

Not all panels are using PanelsManager, but future panels should use it.

Adapted from pyqode/core/managers/panels.py of the
`PyQode project <https://github.com/pyQode/pyQode>`_.
Original file:
<https://github.com/pyQode/pyqode.core/blob/master/pyqode/core/managers/panels.py>
"""

import logging


# Local imports
from spyder.api.manager import Manager
from spyder.api.panel import Panel
from spyder.py3compat import is_text_string


logger = logging.getLogger(__name__)


class PanelsManager(Manager):
    """
    Manage the list of panels and draw them inside the margins of
    CodeEditor widgets.
    """
    def __init__(self, editor):
        super(PanelsManager, self).__init__(editor)
        self._cached_cursor_pos = (-1, -1)
        self._margin_sizes = (0, 0, 0, 0)
        self._top = self._left = self._right = self._bottom = -1
        self._panels = {
            Panel.Position.TOP: {},
            Panel.Position.LEFT: {},
            Panel.Position.RIGHT: {},
            Panel.Position.BOTTOM: {},
            Panel.Position.FLOATING: {}
        }
        try:
            editor.blockCountChanged.connect(self._update_viewport_margins)
            editor.updateRequest.connect(self._update)
        except AttributeError:
            # QTextEdit
            editor.document().blockCountChanged.connect(
                self._update_viewport_margins)

    def register(self, panel, position=Panel.Position.LEFT):
        """
        Installs a panel on the editor.

        :param panel: Panel to install
        :param position: Position where the panel must be installed.
        :return: The installed panel
        """
        assert panel is not None
        pos_to_string = {
            Panel.Position.BOTTOM: 'bottom',
            Panel.Position.LEFT: 'left',
            Panel.Position.RIGHT: 'right',
            Panel.Position.TOP: 'top',
            Panel.Position.FLOATING: 'floating'
        }
        logger.debug('adding panel %s at %s' % (panel.name,
                                                pos_to_string[position]))
        panel.order_in_zone = len(self._panels[position])
        self._panels[position][panel.name] = panel
        panel.position = position
        panel.on_install(self.editor)
        logger.debug('panel %s installed' % panel.name)
        return panel

    def remove(self, name_or_klass):
        """
        Removes the specified panel.

        :param name_or_klass: Name or class of the panel to remove.
        :return: The removed panel
        """
        logger.debug('removing panel %s' % name_or_klass)
        panel = self.get(name_or_klass)
        panel.on_uninstall()
        panel.hide()
        panel.setParent(None)
        return self._panels[panel.position].pop(panel.name, None)

    def clear(self):
        """Removes all panel from the CodeEditor."""
        for i in range(4):
            while len(self._panels[i]):
                key = sorted(list(self._panels[i].keys()))[0]
                panel = self.remove(key)
                panel.setParent(None)
                panel.deleteLater()

    def get(self, name_or_klass):
        """
        Gets a specific panel instance.

        :param name_or_klass: Name or class of the panel to retrieve.
        :return: The specified panel instance.
        """
        if not is_text_string(name_or_klass):
            name_or_klass = name_or_klass.__name__
        for zone in range(4):
            try:
                panel = self._panels[zone][name_or_klass]
            except KeyError:
                pass
            else:
                return panel
        raise KeyError(name_or_klass)

    def keys(self):
        """Returns the list of installed panel names."""
        return self._modes.keys()

    def values(self):
        """Returns the list of installed panels."""
        return self._modes.values()

    def __iter__(self):
        lst = []
        for zone, zone_dict in self._panels.items():
            for name, panel in zone_dict.items():
                lst.append(panel)
        return iter(lst)

    def __len__(self):
        lst = []
        for zone, zone_dict in self._panels.items():
            for name, panel in zone_dict.items():
                lst.append(panel)
        return len(lst)

    def panels_for_zone(self, zone):
        """
        Gets the list of panels attached to the specified zone.

        :param zone: Panel position.

        :return: List of panels instances.
        """
        return list(self._panels[zone].values())

    def refresh(self):
        """Refreshes the editor panels (resize and update margins)."""
        logger.debug('Refresh panels')
        self.resize()
        self._update(self.editor.contentsRect(), 0,
                     force_update_margins=True)

    def resize(self):
        """Resizes panels."""
        crect = self.editor.contentsRect()
        view_crect = self.editor.viewport().contentsRect()
        s_bottom, s_left, s_right, s_top = self._compute_zones_sizes()
        tw = s_left + s_right
        th = s_bottom + s_top
        w_offset = crect.width() - (view_crect.width() + tw)
        h_offset = crect.height() - (view_crect.height() + th)
        left = 0
        panels = self.panels_for_zone(Panel.Position.LEFT)
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
        panels = self.panels_for_zone(Panel.Position.RIGHT)
        panels.sort(key=lambda panel: panel.order_in_zone, reverse=True)
        for panel in panels:
            if not panel.isVisible():
                continue
            size_hint = panel.sizeHint()
            panel.setGeometry(
                crect.right() - right - size_hint.width() - w_offset,
                crect.top() + s_top,
                size_hint.width(),
                crect.height() - s_bottom - s_top - h_offset)
            right += size_hint.width()
        top = 0
        panels = self.panels_for_zone(Panel.Position.TOP)
        panels.sort(key=lambda panel: panel.order_in_zone)
        for panel in panels:
            if not panel.isVisible():
                continue
            size_hint = panel.sizeHint()
            panel.setGeometry(crect.left(),
                              crect.top() + top,
                              crect.width() - w_offset,
                              size_hint.height())
            top += size_hint.height()
        bottom = 0
        panels = self.panels_for_zone(Panel.Position.BOTTOM)
        panels.sort(key=lambda panel: panel.order_in_zone)
        for panel in panels:
            if not panel.isVisible():
                continue
            size_hint = panel.sizeHint()
            panel.setGeometry(
                crect.left(),
                crect.bottom() - bottom - size_hint.height() - h_offset,
                crect.width() - w_offset,
                size_hint.height())
            bottom += size_hint.height()

    def update_floating_panels(self):
        """Update foating panels."""
        crect = self.editor.contentsRect()
        panels = self.panels_for_zone(Panel.Position.FLOATING)
        for panel in panels:
            if not panel.isVisible():
                continue
            panel.set_geometry(crect)

    def _update(self, rect, delta_y, force_update_margins=False):
        """Updates panels."""
        if not self:
            return
        for zones_id, zone in self._panels.items():
            if zones_id == Panel.Position.TOP or \
               zones_id == Panel.Position.BOTTOM:
                continue
            panels = list(zone.values())
            for panel in panels:
                if panel.scrollable and delta_y:
                    panel.scroll(0, delta_y)
                line, col = self.editor.get_cursor_line_column()
                oline, ocol = self._cached_cursor_pos
                if line != oline or col != ocol or panel.scrollable:
                    panel.update(0, rect.y(), panel.width(), rect.height())
                self._cached_cursor_pos = self.editor.get_cursor_line_column()
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
        for panel in self.panels_for_zone(Panel.Position.LEFT):
            if panel.isVisible():
                width = panel.sizeHint().width()
                left += width
        for panel in self.panels_for_zone(Panel.Position.RIGHT):
            if panel.isVisible():
                width = panel.sizeHint().width()
                right += width
        for panel in self.panels_for_zone(Panel.Position.TOP):
            if panel.isVisible():
                height = panel.sizeHint().height()
                top += height
        for panel in self.panels_for_zone(Panel.Position.BOTTOM):
            if panel.isVisible():
                height = panel.sizeHint().height()
                bottom += height
        self._margin_sizes = (top, left, right, bottom)
        self.editor.setViewportMargins(left, top, right, bottom)

    def margin_size(self, position=Panel.Position.LEFT):
        """
        Gets the size of a specific margin.

        :param position: Margin position. See
            :class:`spyder.api.Panel.Position`
        :return: The size of the specified margin
        :rtype: float
        """
        return self._margin_sizes[position]

    def _compute_zones_sizes(self):
        """Compute panel zone sizes."""
        # Left panels
        left = 0
        for panel in self.panels_for_zone(Panel.Position.LEFT):
            if not panel.isVisible():
                continue
            size_hint = panel.sizeHint()
            left += size_hint.width()
        # Right panels
        right = 0
        for panel in self.panels_for_zone(Panel.Position.RIGHT):
            if not panel.isVisible():
                continue
            size_hint = panel.sizeHint()
            right += size_hint.width()
        # Top panels
        top = 0
        for panel in self.panels_for_zone(Panel.Position.TOP):
            if not panel.isVisible():
                continue
            size_hint = panel.sizeHint()
            top += size_hint.height()
        # Bottom panels
        bottom = 0
        for panel in self.panels_for_zone(Panel.Position.BOTTOM):
            if not panel.isVisible():
                continue
            size_hint = panel.sizeHint()
            bottom += size_hint.height()
        self._top, self._left, self._right, self._bottom = (
            top, left, right, bottom)
        return bottom, left, right, top
