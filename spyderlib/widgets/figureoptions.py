# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Module that provides a GUI-based editor for matplotlib's figure options"""

from spyderlib.widgets.formlayout import fedit
from spyderlib.config import get_icon

import matplotlib.cm, matplotlib.image
from matplotlib.colors import rgb2hex, is_color_like


COLORMAPS = matplotlib.cm.datad.keys()
INTERPOLATIONS = matplotlib.image.AxesImage._interpd.keys()

LINESTYLES = {
              '-': 'solid "-"',
              '--': 'dashed "--"',
              '-.': 'dash_dot "-."',
              ':': 'dotted ":"',
              'none': 'None',
              }

# LINESTYLES2 is required because the matplotlib API does not support the same linestyles for patches as for lines 
LINESTYLES2 = {
              'solid': 'solid -',
              'dashed': 'dashed --',
              'dashdot': 'dashdot -.',
              'dotted': 'dotted :',
              }
              
LEG_locs  =  {
             0  : 'best         0',
             1  : 'upper right  1',
             2  : 'upper left   2',
             3  : 'lower left   3',
             4  : 'lower right  4',
             5  : 'right        5',
             6  : 'center left  6',
             7  : 'center right 7',
             8  : 'lower center 8',
             9  : 'upper center 9',
             10 : 'center      10',
             }
MARKERS = {
           'none': 'None',
           'o': 'circle "o"',
           '^': 'triangle_up "^"',
           'v': 'triangle_down "v"',
           '<': 'triangle_left "<"',
           '>': 'triangle_right ">"',
           's': 'square "s"',
           '+': 'plus "+"',
           'x': 'cross "x"',
           '*': 'star "*"',
           'D': 'diamond "D"',
           'd': 'thin_diamond "d"',
           '1': 'tripod_down "1"',
           '2': 'tripod_up "2"',
           '3': 'tripod_left "3"',
           '4': 'tripod_right "4"',
           'h': 'hexagon "h"',
           'H': 'rotated_hexagon "H"',
           'p': 'pentagon "p"',
           '|': 'vertical_line "|"',
           '_': 'horizontal_line "_"',
           '.': 'dot "."',
           ',': 'pixel ","',
           }

COLORS = {'b': '#0000ff', 'g': '#008000', 'r': '#ff0000', 'c': '#00ffff',
          'm': '#ff00ff', 'y': '#ffff00', 'k': '#000000', 'w': '#ffffff'}


def col2hex(color):
    """Convert matplotlib color to hex"""
    if isinstance(color, tuple) and len(color) == 3:
        output = rgb2hex(color) #RGB tuple format 
    else :
        output = COLORS.get(color, color)
    return output

def figure_edit(axes, parent=None):
    """Edit matplotlib figure options"""
    sep = (None, None) # separator
    leg = axes.legend_
    loc = 0 if (leg is None) else leg._loc  
    has_legend = (leg is not None)
    has_curve = len(axes.get_lines()) > 0
    has_image = len(axes.get_images()) > 0
    has_patch = len(axes.patches)     > 0
    has_text  = len(axes.texts)       > 0

    # Get / General
    xmin, xmax = axes.get_xlim()
    ymin, ymax = axes.get_ylim()
    autoXY = (axes.get_autoscalex_on(), axes.get_autoscaley_on())
    general = [('Title', axes.get_title()),
               ('AutoXY', [autoXY, 
               ((0, 0), 'None'), ((1, 0), 'X only'), ((0, 1), 'Y only'), ((1, 1), 'All')]),
               ('Equal', axes.get_aspect()=='equal'),
               ('Legend', has_legend),
               ('Loc', [loc] + LEG_locs.items()),
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

    def get_class_name(obj, prefix="matplotlib.patches."):
        """returns the Class Name"""
        return str(type(obj)).lstrip("<class '").lstrip(prefix).rstrip("'>")

    if has_curve:
        # Get / Curves
        linedict = {}
        for line in axes.get_lines():
            label = line.get_label()
            if label == '_nolegend_':
                continue
            linedict[label] = line
        curves = []
        linestyles = sorted(LINESTYLES.items())
        markers = sorted(MARKERS.items(), key=lambda (k,v): (v,k))
        curvelabels = sorted(linedict.keys())
        for label in curvelabels:
            line = linedict[label]
            markevery = 1 if line.get_markevery() is None else line.get_markevery()
            curvedata = [
                         ('Label', label),
                         ('Visible', line.get_visible()),
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
                         ('Every', markevery),
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

    if has_patch:
        for i, elt in enumerate(axes.patches):
            if elt.get_label()=='':
                label=get_class_name(elt, prefix="matplotlib.patches.") 
                elt.set_label("_" + label.lower() + str(i).zfill(2))
        patchdict = {}
        linestyles = sorted(LINESTYLES2.items())
        for patch in axes.patches:
            label = patch.get_label()
            patchdict[label] = patch
        patches=[]
        patchlabels = sorted(patchdict.keys())
        for label in patchlabels:
            patch = patchdict[label]
            patchdata = [('Label', label),
                         ('Zorder', patch.get_zorder()),
                         ('Visible', patch.get_visible()),
                         sep,
                         (None, '<b>Patch Edge</b>'),
                         ('Style', [patch.get_linestyle()] + linestyles),
                         ('Width', patch.get_linewidth()),
                         ('Edgecolor', col2hex(patch.get_edgecolor())),                         
                         sep,
                         (None, '<b>Patch Face</b>'),
                         ('Fill', patch.get_fill()),                         
                         ('Facecolor', col2hex(patch.get_facecolor())),
                         ('Alpha', patch.get_alpha()),                                                 
                         ]
            patches.append([patchdata, label, ""])

    if has_text: 
        for i, elt in enumerate(axes.texts):
            if elt.get_label()=='':
                label=get_class_name(elt, prefix="matplotlib.text.") 
                elt.set_label("_" + label.lower() + str(i).zfill(2))
        textdict = {}
        for text in axes.texts:
            label = text.get_label()
            textdict[label] = text
        texts=[]
        textlabels = sorted(textdict.keys())
        for label in textlabels:
            text = textdict[label]
            xpos, ypos = text.get_position()
            is_bold = (text.get_weight() == "bold")
            fontcolor=text.get_color()
            textdata = [ ('Label', label),
                         ('Visible', text.get_visible()),
                         ('Content', text.get_text()),
                         sep,
                         (None, '<b>Position</b>'),
                         ('X', xpos),
                         ('Y', ypos),
                         ('Halign', [text.get_ha()] + ['left', 'center', 'right']),
                         ('Valign', [text.get_va()] + ['top', 'center', 'bottom', 'baseline']),
                         sep,
                         (None, '<b>Style</b>'),
                         ('Size', int(text.get_size())),
                         ('Bold', is_bold),
                         ('Color', col2hex(fontcolor)),
                         ]
            texts.append([textdata, label, ""])
        
    datalist = [(general, "Axes", "")]
    if has_curve:
        datalist.append((curves, "Curves", ""))
    if has_image:
        datalist.append((images, "Images", ""))
    if has_patch: 
        datalist.append((patches, "Patches", ""))
    if has_text:  
        datalist.append((texts,   "Texts",   ""))
        
    def apply_callback(data):
        """This function will be called to apply changes"""

        def validate_color(value):
            if not is_color_like(value): value='None'
            return value         

        general = data[0]
        ind = 0
        if has_curve:
            ind += 1
            curves = data[ind]
        if has_image:
            ind += 1
            images = data[ind]
        if has_patch:
            ind += 1
            patches = data[ind]
        if has_text:
            ind += 1
            texts = data[ind]
            
        # Set / General
        title, autoXY, equal, has_legend, loc, xmin, xmax, xlabel, \
            xscale, ymin, ymax, ylabel, yscale = general        
        autoX, autoY = autoXY
        axes.set_xscale(xscale)
        axes.set_yscale(yscale)
        axes.set_autoscalex_on(autoX)
        axes.set_autoscaley_on(autoY)
        axes.set_title(title)
        axes.set_xlim(xmin, xmax)
        axes.set_xlabel(xlabel)
        axes.set_ylim(ymin, ymax)
        axes.set_ylabel(ylabel)
        if equal : 
            axes.set_aspect("equal")
        else :
            axes.set_aspect("auto")
        
        has_label = False
        if has_curve:
            # Set / Curves
            for index, curveopts in enumerate(curves):
                line = linedict[curvelabels[index]]
                label, visible, linestyle, linewidth, color, marker, \
                    markersize, markerfacecolor, markeredgecolor, markevery = curveopts
                if not label.startswith('_') : 
                    has_label=True 
                line.set_label(label)
                line.set_visible(visible)

                line.set_linestyle(linestyle)
                line.set_linewidth(linewidth)                                    
                line.set_color(validate_color(color))
                line.set_markeredgecolor(validate_color(markeredgecolor))
                line.set_markerfacecolor(validate_color(markerfacecolor))
                line.set_markersize(markersize)
                if marker == 'none': 
                    marker='None'
                line.set_marker(marker)
                markevery = markevery if markevery>0 else 1
                line.set_markevery(markevery)	
        
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
                
        if has_patch:
            for index, patch_elt in enumerate(patches):
                patch = patchdict[patchlabels[index]]
                label, zorder, visible, linestyle, linewidth, \
                    edgecolor, fill, facecolor, alpha = patch_elt
                if not label.startswith('_') :
                    has_label = True 
                patch.set_label(label)
                patch.set_zorder(zorder)
                patch.set_visible(visible)
                patch.set_ls(linestyle)
                patch.set_lw(linewidth)                                    
                patch.set_fill(fill)
                patch.set_alpha(alpha)
                patch.set_ec(validate_color(edgecolor))
                patch.set_fc(validate_color(facecolor))

        if has_text:
            for index, text_elt in enumerate(texts):
                text = textdict[textlabels[index]]                
                label, visible, text_content, xpos, ypos, halign, \
                    valign, fontsize, is_bold, fontcolor = text_elt
                text.set_label(label)

                text.set_visible(visible)
                text.set_text(text_content)
                text.set_x(xpos)
                text.set_y(ypos)
                text.set_ha(halign)
                text.set_va(valign)
                if is_bold : 
                    text.set_weight("bold")
                else: 
                    text.set_weight('normal')
                text.set_size(fontsize)
                text.set_color(validate_color(fontcolor))
                
        if has_curve: 
            if has_legend and has_label: 
                axes.legend(loc=loc)
            else:
                axes.legend_ = None
        elif has_legend: 
            axes.legend(loc=loc)
        else:
            axes.legend_ = None
            
        # Redraw
        if axes.get_legend() is not None:
            axes.legend()
        figure = axes.get_figure()
        figure.canvas.draw()
        
    data = fedit(datalist, title="Figure options", parent=parent,
                 icon=get_icon('options.svg'), apply=apply_callback)
    if data is not None:
        apply_callback(data)
    