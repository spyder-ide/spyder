# -*- coding: utf-8 -*-

# TODO: ideally this file should be user-editable like the startup.py file

from contextlib import contextmanager
from collections import OrderedDict

def make_meta_dict(value):
    """
    This wraps the user's code, giving a stacktrace on errors, but still
    returning a valid output.
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
    to be rendered as a list of key-values.
    
    If an "html" key is present in the dictionary, that data wil be interpreted
    as raw html and rendered after the simple meta data.    
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
            if value.ndim == 2 and value.shape[0] > 6 and value.shape[1] > 6:
                # we have a 2D array which is bigger than 6x6, so make a thumbnail
                from io import BytesIO
                from PIL import Image
                from base64 import b64encode
                from matplotlib import cm
                from matplotlib.colors import Normalize
                b = BytesIO()  
                if not ma.isMaskedArray(value):
                    value = ma.array(value, mask=isnan(value))  
                img = Image.fromarray(cm.jet(Normalize()(value), bytes=True))
                img.thumbnail((128,128))
                img.save(b, format='png')
                meta['html'] = '<img alt="2d array" src="data:image/png;base64,' + \
                                b64encode(b.getvalue()) + '" />'       
    return meta