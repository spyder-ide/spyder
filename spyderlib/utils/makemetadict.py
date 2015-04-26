# -*- coding: utf-8 -*-

from contextlib import contextmanager
from collections import OrderedDict

def make_meta_dict(value):
    """
    This wraps the user's code, giving a stacktrace on errors, but still
    returning a valid output.  The idea is that the make_meta_dict_user
    is actually located in a separate file that can be modified by the
    user (like the startup.py scripts).
    """
    try:
        return make_meta_dict_user(value)
    except Exception:
        import traceback
        print(traceback.format_exc())
        return {}
        
@contextmanager
def ignore(*exceptions):  
    try:
        yield
    except exceptions:
        pass
 
def make_meta_dict_user(value):
    """
    This function is called when the user moves over a variable in the 
    variable explorer (when in compact mode).  ``value`` is the actual
    variable in question.  
    
    The function should return a dictionary-like object with "simple" meta data
    to be rendered as a list of key-values.  Note we suggest using an OrderedDict
    in order to control the order in which the keys are displayed.
    
    If an "html" key is present in the dictionary, that data wil be interpreted
    as raw html and rendered after the simple meta data.  
    Search for "richtext-html-subset qt" to find out exactly what html is
    supported.
    
    Note that ``value`` may be a copy or may be the original value, so
    so do not modify it inplace, but conversely do not rely on "is"
    comparisons for caching or other comparisons.
            
    You can display multiple images, but here we try to guess what kind
    of graphical representation would best suit the given data.  If you 
    don't like that you can change it!
    
    Although this function may be long each bit of it should be kept 
    fairly independent...you  may want to split it into lots of little
    functions and then call then explictly call each in turn, wrapped
    in the lazy ignore(Exception).
    """
    meta = OrderedDict()
    class DudObject():
        pass
    
    try:
        from numpy import (array, ndarray, isnan, nanmax, 
                              nanmin, nanmean, nan, ma)
        from numpy import sum as np_sum
        from numpy.ma import MaskedArray
    except ImportError:
        ndarray = MaskedArray = DudObject  # analysis:ignore
        
    if isinstance(value, (ndarray, MaskedArray)):   
        with ignore(Exception):
            meta['min'] = nanmin(value)                
        with ignore(Exception):
            meta['max'] = nanmax(value)
        if isinstance(value,MaskedArray):
            with ignore(Exception): 
                meta['masked'] = str(value.size - value.count())                
        with ignore(Exception):
            # next line will throw ValueError if dtype does not support nans
            test_nan = array(nan, dtype=value.dtype) # analysis:ignore
            n_nan = np_sum(isnan(value))
            meta['NaNs'] = n_nan                    
        with ignore(Exception):
            meta['mean'] = nanmean(value)
        with ignore(Exception):
            n_bytes = value.nbytes
            if n_bytes < 1024*2:
                meta['memory'] = str(n_bytes) + 'B' 
            elif n_bytes < (1024**2)*2:
                meta['memory'] = str(round(n_bytes/(1024.0), 1)) + 'KB' 
            else:
                meta['memory'] = str(round(n_bytes/(1024.0**2), 1)) + 'MB' 

        with ignore(Exception):
            can_make_images = False
            from io import BytesIO
            from PIL import Image, ImageDraw
            from base64 import b64encode
            def img_to_html(img, alt_text='data img'):
                b = BytesIO()  
                img.save(b, format='png')
                return '<img alt="' + alt_text +'"'\
                            + ' src="data:image/png;base64,' \
                            +  b64encode(b.getvalue()) + '" />'
            can_make_images = True
        image_list = []
        
        # If we have a 2D array which is bigger than 6x6, make a thumbnail                   
        with ignore(Exception):
            if can_make_images and value.ndim == 2 and value.shape[0] > 6 and value.shape[1] > 6:
                from matplotlib import cm
                from matplotlib.colors import Normalize
                if not ma.isMaskedArray(value):
                    value = ma.array(value, mask=isnan(value))  
                img = Image.fromarray(cm.jet(Normalize()(value), bytes=True))
                img.thumbnail((128,128))
                image_list.append(img_to_html(img, "matshow image"))
                
        # If we have a long 1d array, then show a simple line plot 
        # unless the line plot fills more than half the axes area
        with ignore(Exception):
            if value.squeeze().ndim == 1 and value.size > 15:
                from numpy import (linspace, max as np_max, min as np_min, 
                                   corrcoef, arange)
                img = Image.new("RGBA", (128,128))
                draw = ImageDraw.Draw(img)
                value = value.squeeze()
                value = value - np_min(value)
                fill_color = (255,0,0,255)
                draw.line(zip(linspace(0,127,value.size),
                         127-value * 127./np_max(value)),
                        fill_color)   
                filled_count = next(count for count, color in img.getcolors()\
                                            if color == fill_color)
                if filled_count < 0.5*img.size[0]*img.size[1]:
                    image_list.append(img_to_html(img,"1d line plot"))
                    meta['corrcoef'] = corrcoef(arange(len(value)),value)[0,1]
                    
        # If we have a 2xn or nx2 with large n, then do a scatter plot
        with ignore(Exception):
            if value.squeeze().ndim == 2 and min(value.shape) == 2 and \
                    max(value.shape) > 15:
                from numpy import (max as np_max, min as np_min, corrcoef)
                img = Image.new("RGBA", (128,128))
                draw = ImageDraw.Draw(img)
                value = value.squeeze()
                value = value if value.shape[0] == 2 else value.T
                value = value - np_min(value, axis=1, keepdims=True)
                fill_color = (0,0,255,255)
                draw.point(zip(value[0]*127./np_max(value[0]),
                         127-value[1]*127./np_max(value[1])),
                         fill_color)   
                filled_count = next(count for count, color in img.getcolors()\
                                            if color == fill_color)
                if filled_count < 0.5*img.size[0]*img.size[1]:
                    image_list.append(img_to_html(img,"xy scatter plot"))
                    meta['corrcoef'] = corrcoef(value[0],value[1])[0,1]
            
        if len(image_list) > 0:
            meta['html'] = ' '.join(image_list)
    return meta