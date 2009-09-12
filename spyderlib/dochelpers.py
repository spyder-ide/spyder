# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Utilities and wrappers around inspect module"""

import inspect, re

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
        while len(token)==0 or re.match(SYMBOLS, token):
            token = tokens.pop()
        if token.endswith('.'):
            token = token[:-1]
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
    #TODO: Add exception handling: is it really necessary?
    return inspect.getdoc(obj)

def getsource(obj):
    """Wrapper around inspect.getsource"""
    try:
        src = inspect.getsource(obj)
    except TypeError:
        if hasattr(obj, '__class__'):
            src = inspect.getsource(obj.__class__)
        else:
            # Bindings like VTK or ITK require this case
            src = inspect.getdoc(obj)
    return src

def getargfromdoc(obj):
    """Get arguments from object doc"""
    doc = getdoc(obj)
    name = obj.__name__
    if (doc is None) or (not doc.find(name+'(')):
        return None
    return doc[doc.find(name+'(')+len(name)+1:doc.find(')')].split()

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
            if len(textlist[-1])>=32 or one_arg_per_line:
                textlist.append('')
    if inspect.isclass(obj):
        if len(textlist)==1:
            return None
        textlist.remove('self'+sep)
    return textlist

if __name__ == "__main__":
    print getargtxt('os.getcwd')
