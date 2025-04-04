# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Switcher Item Widget."""

# Standard library imports
import os
import sys

# Third party imports
from qtpy.QtCore import (QSize, Qt)
from qtpy.QtGui import QStandardItem, QTextDocument

# Local imports
from spyder.config.utils import is_ubuntu
from spyder.py3compat import to_text_string


class SwitcherBaseItem(QStandardItem):
    """Base List Item."""

    _PADDING = 5
    _WIDTH = 400
    _TEMPLATE = None

    def __init__(self, parent=None, styles=None, use_score=True):
        """Create basic List Item."""
        super().__init__()

        # Style
        self._width = self._WIDTH
        self._padding = self._PADDING
        self._styles = styles if styles else {}
        self._action_item = False
        self._score = -1
        self._height = self._get_height()
        self._use_score = use_score

        # Setup
        # self._height is a float from QSizeF but
        # QSize() expects a QSize or (int, int) as parameters
        self.setSizeHint(QSize(0, int(self._height)))

    def _render_text(self):
        """Render the html template for this item."""
        raise NotImplementedError

    def _set_rendered_text(self):
        """Set the rendered html template as text of this item."""
        self.setText(self._render_text())

    def _set_styles(self):
        """Set the styles for this item."""
        raise NotImplementedError

    def _get_height(self):
        """
        Return the expected height of this item's text, including
        the text margins.
        """
        raise NotImplementedError

    # ---- API
    def set_width(self, value):
        """Set the content width."""
        self._width = value - (self._padding * 3)
        self._set_rendered_text()

    def get_width(self):
        """Return the content width."""
        return self._width

    def get_height(self):
        """Return the content height."""
        return self._height

    def get_score(self):
        """Return the fuzzy matchig score."""
        return self._score

    def set_score(self, value):
        """Set the search text fuzzy match score."""
        if self._use_score:
            self._score = value
            self._set_rendered_text()

    def is_action_item(self):
        """Return whether the item is of action type."""
        return bool(self._action_item)

    # ---- Qt overrides
    def refresh(self):
        """Override Qt."""
        super().refresh()
        self._set_styles()
        self._set_rendered_text()


class SwitcherSeparatorItem(SwitcherBaseItem):
    """
    Separator Item represented as <hr>.

    Based on HTML delegate.

    See: https://doc.qt.io/qt-5/richtext-html-subset.html
    """

    _SEPARATOR = '_'
    _STYLE_ATTRIBUTES = ['color', 'font_size']
    _TEMPLATE = \
        u'''<table cellpadding="{padding}" cellspacing="0" width="{width}"
                  height="{height}" border="0">
  <tr><td valign="top" align="center"><hr></td></tr>
</table>'''

    def __init__(self, parent=None, styles=None):
        """Separator Item represented as <hr>."""
        super().__init__(parent=parent, styles=styles)
        self.setFlags(Qt.NoItemFlags)
        self._set_rendered_text()

    # ---- Helpers
    def _set_styles(self):
        """Set the styles for this item."""
        for attr in self._STYLE_ATTRIBUTES:
            if attr not in self._styles:
                self._styles[attr] = self._STYLES[attr]

        rich_font = self._styles['font_size']

        if sys.platform == 'darwin':
            font_size = rich_font
        elif os.name == 'nt':
            font_size = rich_font
        elif is_ubuntu():
            font_size = rich_font - 2
        else:
            font_size = rich_font - 2

        self._styles['font_size'] = font_size

    def _render_text(self):
        """Render the html template for this item."""
        padding = self._padding
        width = self._width
        height = self.get_height()
        text = self._TEMPLATE.format(width=width, height=height,
                                     padding=padding, **self._styles)
        return text

    def _get_height(self):
        """
        Return the expected height of this item's text, including
        the text margins.
        """
        doc = QTextDocument()
        doc.setHtml('<hr>')
        doc.setDocumentMargin(self._PADDING)
        return doc.size().height()


class SwitcherItem(SwitcherBaseItem):
    """
    Switcher item with title, description, shortcut and section.

    SwitcherItem: [title description    <shortcut> section]

    Based on HTML delegate.
    See: https://doc.qt.io/qt-5/richtext-html-subset.html
    """

    _FONT_SIZE = 10
    _STYLE_ATTRIBUTES = ['title_color', 'description_color', 'section_color',
                         'shortcut_color', 'title_font_size',
                         'description_font_size', 'section_font_size',
                         'shortcut_font_size']
    _TEMPLATE = u'''
<table width="{width}" max_width="{width}" height="{height}"
                          cellpadding="{padding}">
  <tr>
    <td valign="middle">
      <span style="color:{title_color};font-size:{title_font_size}pt">
        {title}
      </span>
      &nbsp;&nbsp;
      <em>
        <span
         style="color:{description_color};font-size:{description_font_size}pt">
          <span>{description}</span>
        </span>
      </em>
    </td>
    <td valign="middle" align="right" float="right">
      <span style="color:{shortcut_color};font-size:{shortcut_font_size}pt">
         <code><i>{shortcut}</i></code>
      </span>&nbsp;
      <span style="color:{section_color};font-size:{section_font_size}pt">
         {section}
      </span>
    </td>
  </tr>
</table>'''

    def __init__(self, parent=None, icon=None, title=None, description=None,
                 shortcut=None, section=None, data=None, tool_tip=None,
                 action_item=False, styles=None, score=-1, use_score=True):
        """Switcher item with title, description, shortcut and section."""
        super().__init__(parent=parent, styles=styles, use_score=use_score)

        self._title = title if title else ''
        self._rich_title = ''
        self._shortcut = shortcut if shortcut else ''
        self._description = description if description else ''
        self._section = section if section else ''
        self._icon = icon
        self._data = data
        self._score = score
        self._action_item = action_item

        # Section visibility is computed by the setup_sections method of the
        # switcher.
        self._section_visible = False

        # Setup
        self.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

        if icon:
            self.setIcon(icon)
            # TODO: Change fixed icon size value
            self._icon_width = 20
        else:
            self._icon_width = 0

        self._set_styles()
        self._set_rendered_text()

    # ---- Helpers
    def _render_text(self, title=None, description=None, section=None):
        """Render the html template for this item."""
        if self._rich_title:
            title = self._rich_title
        else:
            title = title if title else self._title

        # TODO: Based on width this should elide/shorten
        description = description if description else self._description

        if self._section_visible:
            section = section if section else self._section
        else:
            section = ''

        padding = self._PADDING
        width = int(self._width - self._icon_width)
        height = int(self.get_height())
        self.setSizeHint(QSize(width, height))

        shortcut = '&lt;' + self._shortcut + '&gt;' if self._shortcut else ''

        title = to_text_string(title, encoding='utf-8')
        section = to_text_string(section, encoding='utf-8')
        description = to_text_string(description, encoding='utf-8')
        shortcut = to_text_string(shortcut, encoding='utf-8')

        text = self._TEMPLATE.format(width=width, height=height, title=title,
                                     section=section, description=description,
                                     padding=padding, shortcut=shortcut,
                                     **self._styles)
        return text

    def _set_styles(self):
        """Set the styles for this item."""
        for attr in self._STYLE_ATTRIBUTES:
            if attr not in self._styles:
                self._styles[attr] = self._STYLES[attr]

    def _get_height(self):
        """
        Return the expected height of this item's text, including
        the text margins.
        """
        doc = QTextDocument()
        try:
            doc.setHtml('<span style="font-size:{}pt">Title</span>'
                        .format(self._styles['title_font_size']))
        except KeyError:
            doc.setHtml('<span>Title</span>')
        doc.setDocumentMargin(self._PADDING)
        return doc.size().height()

    # ---- API
    def set_icon(self, icon):
        """Set the QIcon for the list item."""
        self._icon = icon
        self.setIcon(icon)

    def get_icon(self):
        """Return the QIcon for the list item."""
        return self._icon

    def set_title(self, value):
        """Set the main text (title) of the item."""
        self._title = value
        self._set_rendered_text()

    def get_title(self):
        """Return the the main text (title) of the item."""
        return self._title

    def set_rich_title(self, value):
        """Set the rich title version (filter highlight) of the item."""
        self._rich_title = value
        self._set_rendered_text()

    def get_rich_title(self):
        """Return the rich title version (filter highlight) of the item."""
        return self._rich_title

    def set_description(self, value):
        """Set the item description text."""
        self._description = value
        self._set_rendered_text()

    def get_description(self):
        """Return the item description text."""
        return self._description

    def set_shortcut(self, value):
        """Set the shortcut for the item action."""
        self._shortcut = value
        self._set_rendered_text()

    def get_shortcut(self, value):
        """Return the shortcut for the item action."""
        return self._shortcut

    def set_tooltip(self, value):
        """Set the tooltip text for the item."""
        super().setTooltip(value)

    def set_data(self, value):
        """Set the additional data associated to the item."""
        self._data = value

    def get_data(self):
        """Return the additional data associated to the item."""
        return self._data

    def set_section(self, value):
        """Set the item section name."""
        self._section = value
        self._set_rendered_text()

    def get_section(self):
        """Return the item section name."""
        return self._section

    def set_section_visible(self, value):
        """Set visibility of the item section."""
        self._section_visible = value
        self._set_rendered_text()

    def set_action_item(self, value):
        """Enable/disable the action type for the item."""
        self._action_item = value
        self._set_rendered_text()
