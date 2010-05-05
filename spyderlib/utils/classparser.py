# -*- coding: utf-8 -*-
"""
Python class/function parser

Derived from "Demo/parser/example.py" from Python distribution

******************************** WARNING ***************************************
    This module is not used anymore in Spyder since v1.1.0.
    However, it will still be part of spyderlib module for a little while -
    we never know, it could be useful...
********************************************************************************
"""

import os
import parser
import symbol
from types import ListType, TupleType


def get_info(fileName):
    source = open(fileName, "U").read() + "\n"
    basename = os.path.basename(os.path.splitext(fileName)[0])
    ast = parser.suite(source)
    return ModuleInfo(ast.totuple(line_info=True), basename)

def get_classes(filename):
    """
    Return classes (with methods) and functions of module *filename*:
    [ (class1_lineno, class1_name, [ (method1_lineno, method1_name), ]),
      (func1_lineno, func1_name, None),]
    """
    moduleinfo = get_info(filename)
    classes = []
    for classname in moduleinfo.get_class_names():
        clinfo = moduleinfo.get_class_info(classname)
        methods = []
        for methodname in clinfo.get_method_names():
            minfo = clinfo.get_method_info(methodname)
            methods.append( (minfo.get_lineno(), methodname) )
        methods.sort()
        classes.append( (clinfo.get_lineno(), classname, methods) )
    for funcname in moduleinfo.get_function_names():
        finfo = moduleinfo.get_function_info(funcname)
        classes.append( (finfo.get_lineno(), funcname, None) )
    classes.sort()
    return classes


class SuiteInfoBase:
    _name = ''
    _lineno = -1
    #  This pattern identifies compound statements, allowing them to be readily
    #  differentiated from simple statements.
    #
    COMPOUND_STMT_PATTERN = (
        symbol.stmt,
        (symbol.compound_stmt, ['compound'])
        )

    def __init__(self, tree = None):
        self._class_info = {}
        self._function_info = {}
        if tree:
            self._extract_info(tree)

    def _extract_info(self, tree):
        # extract docstring
        # discover inner definitions
        for node in tree[1:]:
            found, vars = match(self.COMPOUND_STMT_PATTERN, node)
            if found:
                cstmt = vars['compound']
                if cstmt[0] == symbol.funcdef:
                    func_info = FunctionInfo(cstmt)
                    self._function_info[func_info._name] = func_info
                elif cstmt[0] == symbol.classdef:
                    class_info = ClassInfo(cstmt)
                    self._class_info[class_info._name] = class_info

    def get_name(self):
        return self._name
        
    def get_lineno(self):
        return self._lineno

    def get_class_names(self):
        return self._class_info.keys()

    def get_class_info(self, name):
        return self._class_info[name]

    def __getitem__(self, name):
        try:
            return self._class_info[name]
        except KeyError:
            return self._function_info[name]


class SuiteFuncInfo:
    #  Mixin class providing access to function names and info.

    def get_function_names(self):
        return self._function_info.keys()

    def get_function_info(self, name):
        return self._function_info[name]


class FunctionInfo(SuiteInfoBase, SuiteFuncInfo):
    def __init__(self, tree = None):
        index = 2
        prefix = ''
        if tree[1][0] == symbol.decorators:
            index += 1
            prefix = '@'
        self._name = prefix + tree[index][1]
        self._lineno = tree[index][2]
        SuiteInfoBase.__init__(self, tree and tree[-1] or None)


class ClassInfo(SuiteInfoBase):
    def __init__(self, tree = None):
        self._name = tree[2][1]
        self._lineno = tree[2][2]
        SuiteInfoBase.__init__(self, tree and tree[-1] or None)

    def get_method_names(self):
        return self._function_info.keys()

    def get_method_info(self, name):
        return self._function_info[name]


class ModuleInfo(SuiteInfoBase, SuiteFuncInfo):
    def __init__(self, tree = None, name = "<string>"):
        self._name = name
        self._lineno = 0
        if tree[0] == symbol.encoding_decl:
            self._encoding = tree[2]
            tree = tree[1]
        else:
            self._encoding = 'ascii'
        SuiteInfoBase.__init__(self, tree)


def match(pattern, data, vars=None):
    """Match `data' to `pattern', with variable extraction.

    pattern
        Pattern to match against, possibly containing variables.

    data
        Data to be checked and against which variables are extracted.

    vars
        Dictionary of variables which have already been found.  If not
        provided, an empty dictionary is created.

    The `pattern' value may contain variables of the form ['varname'] which
    are allowed to match anything.  The value that is matched is returned as
    part of a dictionary which maps 'varname' to the matched value.  'varname'
    is not required to be a string object, but using strings makes patterns
    and the code which uses them more readable.

    This function returns two values: a boolean indicating whether a match
    was found and a dictionary mapping variable names to their associated
    values.
    """
    if vars is None:
        vars = {}
    if type(pattern) is ListType:       # 'variables' are ['varname']
        vars[pattern[0]] = data
        return 1, vars
    if type(pattern) is not TupleType:
        return (pattern == data), vars
    if len(data) != len(pattern):
        return 0, vars
    for pattern, data in map(None, pattern, data):
        same, vars = match(pattern, data, vars)
        if not same:
            break
    return same, vars


if __name__ == '__main__':
    import sys, time
    t0 = time.time()
    classes = get_classes(sys.argv[1])
    print "Elapsed time: %s ms" % round((time.time()-t0)*1000)
#    from pprint import pprint
#    pprint(classes)
