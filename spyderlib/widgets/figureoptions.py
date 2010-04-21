# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Module that provides a GUI-based editor for matplotlib's figure options"""

from spyderlib.widgets.formlayout import fedit
from spyderlib.config import get_icon

import matplotlib.cm, matplotlib.image


COLORMAPS = matplotlib.cm.datad.keys()
INTERPOLATIONS = matplotlib.image.AxesImage._interpd.keys()

LINESTYLES = {
              '-': 'Solid',
              '--': 'Dashed',
              '-.': 'DashDot',
              ':': 'Dotted',
              'steps': 'Steps',
              'none': 'None',
              }

MARKERS = {
           'none': 'None',
           'o': 'circles',
           '^': 'triangle_up',
           'v': 'triangle_down',
           '<': 'triangle_left',
           '>': 'triangle_right',
           's': 'square',
           '+': 'plus',
           'x': 'cross',
           '*': 'star',
           'D': 'diamond',
           'd': 'thin_diamond',
           '1': 'tripod_down',
           '2': 'tripod_up',
           '3': 'tripod_left',
           '4': 'tripod_right',
           'h': 'hexagon',
           'H': 'rotated_hexagon',
           'p': 'pentagon',
           '|': 'vertical_line',
           '_': 'horizontal_line',
           '.': 'dots',
           }

COLORS = {'b': '#0000ff', 'g': '#00ff00', 'r': '#ff0000', 'c': '#ff00ff',
          'm': '#ff00ff', 'y': '#ffff00', 'k': '#000000', 'w': '#ffffff'}


def col2hex(color):
    """Convert matplotlib color to hex"""
    return COLORS.get(color, color)

def figure_edit(axes, parent=None):
    """Edit matplotlib figure options"""
    sep = (None, None) # separator
    
    has_curve = len(axes.get_lines()) > 0
    has_image = len(axes.get_images()) > 0
    
    # Get / General
    xmin, xmax = axes.get_xlim()
    ymin, ymax = axes.get_ylim()
    general = [('Title', axes.get_title()),
               sep,
               (None, "<b>X-Axis</b>"),
               ('Min', xmin), ('Max', xmax),
               ('Label', axes.get_xlabel()),
               ('Scale', [axes.get_xscale(), 'linear', 'log']),
               sep,
               (None, "<b>Y-Axis</b>"),
               ('Min', ymin), ('Max', ymax),
               ('Label', axes.get_ylabel()),
               ('Scale', [axes.get_yscale(), 'linear', 'log'])
               ]

    if has_curve:
        # Get / Curves
        linedict = {}
        for line in axes.get_lines():
            label = line.get_label()
            if label == '_nolegend_':
                continue
            linedict[label] = line
        curves = []
        linestyles = LINESTYLES.items()
        markers = MARKERS.items()
        curvelabels = sorted(linedict.keys())
        for label in curvelabels:
            line = linedict[label]
            curvedata = [
                         ('Label', label),
                         sep,
                         (None, '<b>Line</b>'),
                         ('Style', [line.get_linestyle()] + linestyles),
                         ('Width', line.get_linewidth()),
                         ('Color', col2hex(line.get_color())),
                         sep,
                         (None, '<b>Marker</b>'),
                         ('Style', [line.get_marker()] + markers),
                         ('Size', line.get_markersize()),
                         ('Facecolor', col2hex(line.get_markerfacecolor())),
                         ('Edgecolor', col2hex(line.get_markeredgecolor())),
                         ]
            curves.append([curvedata, label, ""])
        
    if has_image:
        # Get / Images
        imagedict = {}
        for image in axes.get_images():
            label = image.get_label()
            if label == '_nolegend_':
                continue
            imagedict[label] = image
        images = []
        interpolations = zip(INTERPOLATIONS, INTERPOLATIONS)
        colormaps = zip(COLORMAPS, COLORMAPS)
        imagelabels = sorted(imagedict.keys())
        for label in imagelabels:
            image = imagedict[label]
            xmin, xmax, ymin, ymax = image.get_extent()
            cmap_name = image.get_cmap().name
            imagedata = [
                         ('Label', label),
                         sep,
                         ('Colormap', [cmap_name] + colormaps),
                         ('Alpha', image.get_alpha()),
                         ('Interpolation',
                          [image.get_interpolation()] + interpolations),
                         ('Resize filter radius', image.get_filterrad()),
                         sep,
                         (None, '<b>Extent</b>'),
                         ('xmin', xmin), ('xmax', xmax),
                         ('ymin', ymin), ('ymax', ymax),
                         ]
            images.append([imagedata, label, ""])
        
    datalist = [(general, "Axes", "")]
    if has_curve:
        datalist.append((curves, "Curves", ""))
    if has_image:
        datalist.append((images, "Images", ""))
        
    def apply_callback(data):
        """This function will be called to apply changes"""
        if has_curve and has_image:
            general, curves, images = data
        elif has_curve:
            general, curves = data
        elif has_image:
            general, images = data
        else:
            general, = data
            
        # Set / General
        title, xmin, xmax, xlabel, xscale, ymin, ymax, ylabel, yscale = general
        axes.set_xscale(xscale)
        axes.set_yscale(yscale)
        axes.set_title(title)
        axes.set_xlim(xmin, xmax)
        axes.set_xlabel(xlabel)
        axes.set_ylim(ymin, ymax)
        axes.set_ylabel(ylabel)
        
        if has_curve:
            # Set / Curves
            for index, curveopts in enumerate(curves):
                line = linedict[curvelabels[index]]
                label, linestyle, linewidth, color, marker, markersize, \
                    markerfacecolor, markeredgecolor = curveopts
                line.set_label(label)
                line.set_linestyle(linestyle)
                line.set_linewidth(linewidth)
                line.set_color(color)
                if marker is not 'none':
                    line.set_marker(marker)
                    line.set_markersize(markersize)
                    line.set_markerfacecolor(markerfacecolor)
                    line.set_markeredgecolor(markeredgecolor)
        
        if has_image:
            # Set / Images
            for index, imageopts in enumerate(images):
                image = imagedict[imagelabels[index]]
                
                label, cmap_name, alpha, interpolation, \
                    filterrad, xmin, xmax, ymin, ymax = imageopts
                image.set_label(label)
                image.set_cmap(matplotlib.cm.get_cmap(cmap_name))
                if alpha >= 0 and alpha <= 1:
                    # Ignoring invalid values
                    image.set_alpha(alpha)
                image.set_interpolation(interpolation)
                if filterrad > 0:
                    # Ignoring invalid values
                    image.set_filterrad(filterrad)
                image.set_extent((xmin, xmax, ymin, ymax))
            
        # Redraw
        if axes.get_legend() is not None:
            axes.legend()
        figure = axes.get_figure()
        figure.canvas.draw()
        
    data = fedit(datalist, title="Figure options", parent=parent,
                 icon=get_icon('options.svg'), apply=apply_callback)
    if data is not None:
        apply_callback(data)
    