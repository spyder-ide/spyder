"""Classes handling iconic fonts"""

from __future__ import print_function
from spyderlib.qt.QtCore import Qt, QObject, QPoint, QRect, qRound, QByteArray
from spyderlib.qt.QtGui import (QIcon, QColor, QIconEngine, QPainter, QPixmap,
                                QFontDatabase, QFont)
import json
import os
from six import unichr


_default_options = {
    'color': QColor(50, 50, 50),
    'color_disabled': QColor(150, 150, 150),
    'opacity': 1.0,
    'scale_factor': 1.0,
}


def set_global_defaults(**kwargs):
    """Set global defaults for all icons"""
    valid_options = ['active', 'animation', 'color', 'color_active',
                     'color_disabled', 'color_selected', 'disabled', 'offset',
                     'scale_factor', 'selected']
    for kw in kwargs:
        if kw in valid_options:
            _default_options[kw] = kwargs[kw]
        else:
            error = "Invalid option '{0}'".format(kw)
            raise KeyError(error)


class CharIconPainter:

    """Char icon painter"""

    def paint(self, iconic, painter, rect, mode, state, options):
        """Main paint method"""
        for opt in options:
            self._paint_icon(iconic, painter, rect, mode, state, opt)

    def _paint_icon(self, iconic, painter, rect, mode, state, options):
        """Paint a single icon"""
        painter.save()
        color, char = options['color'], options['char']

        if mode == QIcon.Disabled:
            color = options.get('color_disabled', color)
            char = options.get('disabled', char)
        elif mode == QIcon.Active:
            color = options.get('color_active', color)
            char = options.get('active', char)
        elif mode == QIcon.Selected:
            color = options.get('color_selected', color)
            char = options.get('selected', char)

        painter.setPen(QColor(color))
        # A 16 pixel-high icon yields a font size of 14, which is pixel perfect
        # for font-awesome. 16 * 0.875 = 14
        # The reason for not using full-sized glyphs is the negative bearing of
        # fonts.
        draw_size = 0.875 * qRound(rect.height() * options['scale_factor'])
        prefix = options['prefix']

        # Animation setup hook
        animation = options.get('animation')
        if animation is not None:
            animation.setup(self, painter, rect)

        painter.setFont(iconic.font(prefix, draw_size))
        if 'offset' in options:
            rect = QRect(rect)
            rect.translate(options['offset'][0] * rect.width(),
                           options['offset'][1] * rect.height())

        painter.setOpacity(options.get('opacity', 1.0))

        painter.drawText(rect, Qt.AlignCenter | Qt.AlignVCenter, char)
        painter.restore()


class CharIconEngine(QIconEngine):

    """Specialization of QIconEngine used to draw font-based icons"""

    def __init__(self, iconic, painter, options):
        super(CharIconEngine, self).__init__()
        self.iconic = iconic 
        self.painter = painter
        self.options = options

    def paint(self, painter, rect, mode, state):
        self.painter.paint(
            self.iconic, painter, rect, mode, state, self.options)

    def pixmap(self, size, mode, state):
        pm = QPixmap(size)
        pm.fill(Qt.transparent)
        self.paint(QPainter(pm), QRect(QPoint(0, 0), size), mode, state)
        return pm


class IconicFont(QObject):

    """Main class for managing iconic fonts"""

    def __init__(self, *args):
        """Constructor

        :param *args: tuples
            Each positional argument is a tuple of 3 or 4 values
            - The prefix string to be used when accessing a given font set
            - The ttf font filename
            - The json charmap filename
            - Optionally, the directory containing these files. When not
              provided, the files will be looked up in ./fonts/
        """
        super(IconicFont, self).__init__()
        self.painter = CharIconPainter()
        self.painters = {}
        self.fontname = {}
        self.charmap = {}
        for fargs in args:
            self.load_font(*fargs)

    def load_font(self, prefix, ttf_filename, charmap_filename, directory=None):
        """Loads a font file and the associated charmap

        If `directory` is None, the files will be looked up in ./fonts/

        Arguments
        ---------
        prefix: str
            prefix string to be used when accessing a given font set
        ttf_filename: str
            ttf font filename
        charmap_filename: str
            charmap filename
        directory: str or None, optional
            directory for font and charmap files
        """

        def hook(obj):
            result = {}
            for key in obj:
                result[key] = unichr(int(obj[key], 16))
            return result

        if directory is None:
            directory = os.path.join(
                os.path.dirname(os.path.realpath(__file__)), 'fonts')

        with open(os.path.join(directory, charmap_filename), 'r') as codes:
            self.charmap[prefix] = json.load(codes, object_hook=hook)

        id_ = QFontDatabase.addApplicationFont(os.path.join(directory, ttf_filename))

        loadedFontFamilies = QFontDatabase.applicationFontFamilies(id_)

        if(loadedFontFamilies):
            self.fontname[prefix] = loadedFontFamilies[0]
        else:
            print('Font is empty')

    def icon(self, *names, **kwargs):
        """Returns a QIcon object corresponding to the provided icon name
        (including prefix)

        Arguments
        ---------
        names: list of str
            icon name, of the form PREFIX.NAME

        options: dict
            options to be passed to the icon painter
        """
        options_list = kwargs.pop('options', [{}] * len(names))
        general_options = kwargs

        if len(options_list) != len(names):
            error = '"options" must be a list of size {0}'.format(len(names))
            raise Exception(error)

        parsed_options = []
        for i in range(len(options_list)):
            specific_options = options_list[i]
            parsed_options.append(self._parse_options(specific_options,
                                                      general_options,
                                                      names[i]))

        # Process high level API
        api_options = parsed_options

        return self._icon_by_painter(self.painter, api_options)

    def _parse_options(self, specific_options, general_options, name):
        """ """
        options = dict(_default_options, **general_options)
        options.update(specific_options)

        # Handle icons for states
        icon_kw = ['disabled', 'active', 'selected', 'char']
        names = [options.get(kw, name) for kw in icon_kw]
        prefix, chars = self._get_prefix_chars(names)
        options.update(dict(zip(*(icon_kw, chars))))
        options.update({'prefix': prefix})

        # Handle colors for states
        color_kw = ['color_active', 'color_selected']
        colors = [options.get(kw, options['color']) for kw in color_kw]
        options.update(dict(zip(*(color_kw, colors))))

        return options

    def _get_prefix_chars(self, names):
        """ """
        chars = []
        for name in names:
            if '.' in name:
                prefix, n = name.split('.')
                if prefix in self.charmap:
                    if n in self.charmap[prefix]:
                        chars.append(self.charmap[prefix][n])
                    else:
                        error = 'Invalid icon name "{0}" in font "{1}"'.format(
                            n, prefix)
                        raise Exception(error)
                else:
                    error = 'Invalid font prefix "{0}"'.format(prefix)
                    raise Exception(error)
            else:
                raise Exception('Invalid icon name')

        return prefix, chars

    def font(self, prefix, size):
        """Returns QFont corresponding to the given prefix and size

        Arguments
        ---------
        prefix: str
            prefix string of the loaded font
        size: int
            size for the font
        """
        font = QFont(self.fontname[prefix])
        font.setPixelSize(size)
        return font

    def set_custom_icon(self, name, painter):
        """Associates a user-provided CharIconPainter to an icon name
        The custom icon can later be addressed by calling
        icon('custom.NAME') where NAME is the provided name for that icon.

        Arguments
        ---------
        name: str
            name of the custom icon
        painter: CharIconPainter
            The icon painter, implementing
            `paint(self, iconic, painter, rect, mode, state, options)`
        """
        self.painters[name] = painter

    def _custom_icon(self, name, **kwargs):
        """Returns the custom icon corresponding to the given name"""
        options = dict(_default_options, **kwargs)
        if name in self.painters:
            painter = self.painters[name]
            return self._icon_by_painter(painter, options)
        else:
            return QIcon()

    def _icon_by_painter(self, painter, options):
        """Returns the icon corresponding to the given painter"""
        engine = CharIconEngine(self, painter, options)
        return QIcon(engine)
