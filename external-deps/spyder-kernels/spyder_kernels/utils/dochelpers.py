# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)
# -----------------------------------------------------------------------------

"""Utilities and wrappers around inspect module"""

from __future__ import print_function

import inspect
import re

# Local imports:
from spyder_kernels.py3compat import (is_text_string, builtins, get_meth_func,
                                      get_meth_class_inst, get_meth_class,
                                      get_func_defaults, to_text_string, PY2)


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
    token = None
    try:
        while token is None or re.match(SYMBOLS, token):
            token = tokens.pop()
        if token.endswith('.'):
            token = token[:-1]
        if token.startswith('.'):
            # Invalid object name
            return None
        if last:
            #XXX: remove this statement as well as the "last" argument
            token += txt[ txt.rfind(token) + len(token) ]
        token += txt_end
        if token:
            return token
    except IndexError:
        return None


def getobjdir(obj):
    """
    For standard objects, will simply return dir(obj)
    In special cases (e.g. WrapITK package), will return only string elements
    of result returned by dir(obj)
    """
    return [item for item in dir(obj) if is_text_string(item)]


def getdoc(obj):
    """
    Return text documentation from an object. This comes in a form of
    dictionary with four keys:

    name:
      The name of the inspected object
    argspec:
      It's argspec
    note:
      A phrase describing the type of object (function or method) we are
      inspecting, and the module it belongs to.
    docstring:
      It's docstring
    """
    
    docstring = inspect.getdoc(obj) or inspect.getcomments(obj) or ''
    
    # Most of the time doc will only contain ascii characters, but there are
    # some docstrings that contain non-ascii characters. Not all source files
    # declare their encoding in the first line, so querying for that might not
    # yield anything, either. So assume the most commonly used
    # multi-byte file encoding (which also covers ascii). 
    try:
        docstring = to_text_string(docstring)
    except:
        pass
    
    # Doc dict keys
    doc = {'name': '',
           'argspec': '',
           'note': '',
           'docstring': docstring}
    
    if callable(obj):
        try:
            name = obj.__name__
        except AttributeError:
            doc['docstring'] = docstring
            return doc
        if inspect.ismethod(obj):
            imclass = get_meth_class(obj)
            if get_meth_class_inst(obj) is not None:
                doc['note'] = 'Method of %s instance' \
                              % get_meth_class_inst(obj).__class__.__name__
            else:
                doc['note'] = 'Unbound %s method' % imclass.__name__
            obj = get_meth_func(obj)
        elif hasattr(obj, '__module__'):
            doc['note'] = 'Function of %s module' % obj.__module__
        else:
            doc['note'] = 'Function'
        doc['name'] = obj.__name__
        if inspect.isfunction(obj):
            if PY2:
                args, varargs, varkw, defaults = inspect.getargspec(obj)
                doc['argspec'] = inspect.formatargspec(
                    args, varargs, varkw, defaults,
                    formatvalue=lambda o:'='+repr(o))
            else:
                # This is necessary to catch errors for objects without a
                # signature, like numpy.where.
                # Fixes spyder-ide/spyder#21148
                try:
                    sig = inspect.signature(obj)
                except ValueError:
                    sig = getargspecfromtext(doc['docstring'])
                    if not sig:
                        sig = '(...)'
                doc['argspec'] = str(sig)
            if name == '<lambda>':
                doc['name'] = name + ' lambda '
                doc['argspec'] = doc['argspec'][1:-1] # remove parentheses
        else:
            argspec = getargspecfromtext(doc['docstring'])
            if argspec:
                doc['argspec'] = argspec
                # Many scipy and numpy docstrings begin with a function
                # signature on the first line. This ends up begin redundant
                # when we are using title and argspec to create the
                # rich text "Definition:" field. We'll carefully remove this
                # redundancy but only under a strict set of conditions:
                # Remove the starting charaters of the 'doc' portion *iff*
                # the non-whitespace characters on the first line 
                # match *exactly* the combined function title 
                # and argspec we determined above.
                signature = doc['name'] + doc['argspec']
                docstring_blocks = doc['docstring'].split("\n\n")
                first_block = docstring_blocks[0].strip()
                if first_block == signature:
                    doc['docstring'] = doc['docstring'].replace(
                                                     signature, '', 1).lstrip()
            else:
                doc['argspec'] = '(...)'
        
        # Remove self from argspec
        argspec = doc['argspec']
        doc['argspec'] = argspec.replace('(self)', '()').replace('(self, ', '(')
        
    return doc


def getsource(obj):
    """Wrapper around inspect.getsource"""
    try:
        try:
            src = to_text_string(inspect.getsource(obj))
        except TypeError:
            if hasattr(obj, '__class__'):
                src = to_text_string(inspect.getsource(obj.__class__))
            else:
                # Bindings like VTK or ITK require this case
                src = getdoc(obj)
        return src
    except (TypeError, IOError):
        return


def getsignaturefromtext(text, objname):
    """Get object signature from text (i.e. object documentation)."""
    if isinstance(text, dict):
        text = text.get('docstring', '')

    # Regexps
    args_re = r'(\(.+?\))'
    if objname:
        signature_re = objname + args_re
    else:
        identifier_re = r'(\w+)'
        signature_re = identifier_re + args_re

    # Grabbing signatures
    if not text:
        text = ''

    sigs = re.findall(signature_re, text)

    # The most relevant signature is usually the first one. There could be
    # others in doctests or other places, but those are not so important.
    sig = ''
    if sigs:
        if PY2:
            # We don't have an easy way to check if the identifier detected by
            # signature_re is a valid one in Python 2. So, we simply select the
            # first match.
            sig = sigs[0] if objname else sigs[0][1]
        else:
            # Default signatures returned by IPython.
            # Notes:
            # * These are not real signatures but only used to provide a
            #   placeholder.
            # * We skip them if we can find other signatures in `text`.
            # * This is necessary because we also use this function in Spyder
            #   to parse the content of inspect replies that come from the
            #   kernel, which can include these signatures.
            default_ipy_sigs = [
                '(*args, **kwargs)',
                '(self, /, *args, **kwargs)'
            ]

            if objname:
                real_sigs = [s for s in sigs if s not in default_ipy_sigs]

                if real_sigs:
                    sig = real_sigs[0]
                else:
                    sig = sigs[0]
            else:
                valid_sigs = [s for s in sigs if s[0].isidentifier()]

                if valid_sigs:
                    real_sigs = [
                        s for s in valid_sigs if s[1] not in default_ipy_sigs
                    ]

                    if real_sigs:
                        sig = real_sigs[0][1]
                    else:
                        sig = valid_sigs[0][1]

    return sig


def getargspecfromtext(text):
    """
    Try to get the formatted argspec of a callable from the first block of its
    docstring.
    
    This will return something like `(x, y, k=1)`.
    """
    blocks = text.split("\n\n")
    first_block = blocks[0].strip().replace('\n', '')
    return getsignaturefromtext(first_block, '')


def getargsfromtext(text, objname):
    """Get arguments from text (object documentation)."""
    signature = getsignaturefromtext(text, objname)
    if signature:
        argtxt = signature[signature.find('(') + 1:-1]
        return argtxt.split(',')


def getargsfromdoc(obj):
    """Get arguments from object doc"""
    if obj.__doc__ is not None:
        return getargsfromtext(obj.__doc__, obj.__name__)


def getargs(obj):
    """Get the names and default values of a function's arguments"""
    if inspect.isfunction(obj) or inspect.isbuiltin(obj):
        func_obj = obj
    elif inspect.ismethod(obj):
        func_obj = get_meth_func(obj)
    elif inspect.isclass(obj) and hasattr(obj, '__init__'):
        func_obj = getattr(obj, '__init__')
    else:
        return []

    if not hasattr(func_obj, '__code__'):
        # Builtin: try to extract info from doc
        args = getargsfromdoc(func_obj)
        if args is not None:
            return args
        else:
            # Example: PyQt5
            return getargsfromdoc(obj)

    args, _, _ = inspect.getargs(func_obj.__code__)
    if not args:
        return getargsfromdoc(obj)

    # Supporting tuple arguments in def statement:
    for i_arg, arg in enumerate(args):
        if isinstance(arg, list):
            args[i_arg] = "(%s)" % ", ".join(arg)

    defaults = get_func_defaults(func_obj)
    if defaults is not None:
        for index, default in enumerate(defaults):
            args[index + len(args) - len(defaults)] += '=' + repr(default)

    if inspect.isclass(obj) or inspect.ismethod(obj):
        if len(args) == 1:
            return None

    # Remove 'self' from args
    if 'self' in args:
        args.remove('self')

    return args


def getargtxt(obj, one_arg_per_line=True):
    """
    Get the names and default values of a function's arguments
    Return list with separators (', ') formatted for calltips
    """
    args = getargs(obj)
    if args:
        sep = ', '
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
            if 'self'+sep in textlist:
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
    if base not in builtins.__dict__ and base not in namespace:
        if force_import:
            try:
                module = __import__(base, globals(), namespace)
                if base not in globals():
                    globals()[base] = module
                namespace[base] = module
            except Exception:
                return False
        else:
            return False
    for attr in attr_list:
        try:
            attr_not_found = not hasattr(eval(base, namespace), attr)
        except (AttributeError, SyntaxError, TypeError):
            return False
        if attr_not_found:
            if force_import:
                try:
                    __import__(base+'.'+attr, globals(), namespace)
                except (ImportError, SyntaxError):
                    return False
            else:
                return False
        base += '.'+attr
    return True
