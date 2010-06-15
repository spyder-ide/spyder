# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Utilities and wrappers around inspect module"""

import inspect, re

# Local imports:
from spyderlib.utils import encoding

SYMBOLS = r"[^\'\"a-zA-Z0-9_.]"

def getobj(txt, last=False):
    """Return the last valid object name in string"""
    txt_end = ""
    for startchar, endchar in ["[]", "()"]:
        if txt.endswith(endchar):
            pos = txt.rfind(startchar)
            if pos:
                txt_end = txt[pos:]
                txt = txt[:pos]
    tokens = re.split(SYMBOLS, txt)
    token = ""
    try:
        while len(token) == 0 or re.match(SYMBOLS, token):
            token = tokens.pop()
        if token.endswith('.'):
            token = token[:-1]
        if token.startswith('.'):
            # Invalid object name
            return None
        if last:
            #XXX: remove this statement as well as the "last" argument
            token += txt[ txt.rfind(token) + len(token) ]
        return token + txt_end
    except IndexError:
        return None

def getobjdir(obj):
    """
    For standard objects, will simply return dir(obj)
    In special cases (e.g. WrapITK package), will return only string elements
    of result returned by dir(obj)
    """
    return [item for item in dir(obj) if isinstance(item, basestring)]

def getdoc(obj):
    """Wrapper around inspect.getdoc"""
    return encoding.to_unicode( inspect.getdoc(obj) )

def getsource(obj):
    """Wrapper around inspect.getsource"""
    try:
        try:
            src = encoding.to_unicode( inspect.getsource(obj) )
        except TypeError:
            if hasattr(obj, '__class__'):
                src = encoding.to_unicode( inspect.getsource(obj.__class__) )
            else:
                # Bindings like VTK or ITK require this case
                src = getdoc(obj)
        return src
    except (TypeError, IOError):
        return

def getargfromdoc(obj):
    """Get arguments from object doc"""
    doc = getdoc(obj)
    name = obj.__name__
    if (doc is None) or (not doc.find(name+'(')):
        return None
    argtxt = doc[doc.find(name+'(')+len(name)+1:doc.find(')')]
    if argtxt == u'...':
        return None
    else:
        return argtxt.split()

def getargtxt(obj, one_arg_per_line=True):
    """Get the names and default values of a function's arguments"""
    sep = ', '
    if inspect.isfunction(obj) or inspect.isbuiltin(obj):
        func_obj = obj
    elif inspect.ismethod(obj):
        func_obj = obj.im_func
    elif inspect.isclass(obj) and hasattr(obj, '__init__'):
        func_obj = getattr(obj, '__init__')
    else:
        return None
    if not hasattr(func_obj, 'func_code'):
        # Builtin: try to extract info from getdoc
        return getargfromdoc(func_obj)
    args, _, _ = inspect.getargs(func_obj.func_code)
    if not args:
        return getargfromdoc(obj)
    
    # Supporting tuple arguments in def statement:
    for i_arg, arg in enumerate(args):
        if isinstance(arg, list):
            args[i_arg] = "(%s)" % ", ".join(arg)
            
    defaults = func_obj.func_defaults
    if defaults is not None:
        for index, default in enumerate(defaults):
            args[index+len(args)-len(defaults)] += '='+repr(default)
    textlist = None
    for i_arg, arg in enumerate(args):
        if textlist is None:
            textlist = ['']
        textlist[-1] += arg
        if i_arg < len(args)-1:
            textlist[-1] += sep
            if len(textlist[-1]) >= 32 or one_arg_per_line:
                textlist.append('')
    if inspect.isclass(obj) or inspect.ismethod(obj):
        if len(textlist) == 1:
            return None
        textlist.remove('self'+sep)
    return textlist


def isdefined(obj, force_import=False, namespace=None):
    """Return True if object is defined in namespace
    If namespace is None --> namespace = locals()"""
    if namespace is None:
        namespace = locals()
    attr_list = obj.split('.')
    base = attr_list.pop(0)
    if len(base) == 0:
        return False
    import __builtin__
    if base not in __builtin__.__dict__ and base not in namespace:
        if force_import:
            try:
                module = __import__(base, globals(), namespace)
                if base not in globals():
                    globals()[base] = module
                namespace[base] = module
            except ImportError:
                return False
        else:
            return False
    for attr in attr_list:
        if not hasattr(eval(base, namespace), attr):
            if force_import:
                try:
                    __import__(base+'.'+attr, globals(), namespace)
                except ImportError:
                    return False
            else:
                return False
        base += '.'+attr
    return True
    

if __name__ == "__main__":
    class Test(object):
        def method(self, x, y=2, (u, v, w)=(None, 0, 0)):
            pass
    print getargtxt(Test.__init__)
    print getargtxt(Test.method)
    print isdefined('numpy.take', force_import=True)
    print isdefined('__import__')
    print getobj('globals')
    print getobj('globals().keys')
    print isdefined('.keys', force_import=True)
