"""
Main module.

Implement the central Checker class.
Also, it models the Bindings and Scopes.
"""
import doctest
import os
import sys

PY2 = sys.version_info < (3, 0)
PY32 = sys.version_info < (3, 3)    # Python 2.5 to 3.2
PY33 = sys.version_info < (3, 4)    # Python 2.5 to 3.3
builtin_vars = dir(__import__('__builtin__' if PY2 else 'builtins'))

try:
    import ast
except ImportError:     # Python 2.5
    import _ast as ast

    if 'decorator_list' not in ast.ClassDef._fields:
        # Patch the missing attribute 'decorator_list'
        ast.ClassDef.decorator_list = ()
        ast.FunctionDef.decorator_list = property(lambda s: s.decorators)

from pyflakes import messages


if PY2:
    def getNodeType(node_class):
        # workaround str.upper() which is locale-dependent
        return str(unicode(node_class.__name__).upper())
else:
    def getNodeType(node_class):
        return node_class.__name__.upper()

# Python >= 3.3 uses ast.Try instead of (ast.TryExcept + ast.TryFinally)
if PY32:
    def getAlternatives(n):
        if isinstance(n, (ast.If, ast.TryFinally)):
            return [n.body]
        if isinstance(n, ast.TryExcept):
            return [n.body + n.orelse] + [[hdl] for hdl in n.handlers]
else:
    def getAlternatives(n):
        if isinstance(n, ast.If):
            return [n.body]
        if isinstance(n, ast.Try):
            return [n.body + n.orelse] + [[hdl] for hdl in n.handlers]


class _FieldsOrder(dict):
    """Fix order of AST node fields."""

    def _get_fields(self, node_class):
        # handle iter before target, and generators before element
        fields = node_class._fields
        if 'iter' in fields:
            key_first = 'iter'.find
        elif 'generators' in fields:
            key_first = 'generators'.find
        else:
            key_first = 'value'.find
        return tuple(sorted(fields, key=key_first, reverse=True))

    def __missing__(self, node_class):
        self[node_class] = fields = self._get_fields(node_class)
        return fields


def iter_child_nodes(node, omit=None, _fields_order=_FieldsOrder()):
    """
    Yield all direct child nodes of *node*, that is, all fields that
    are nodes and all items of fields that are lists of nodes.
    """
    for name in _fields_order[node.__class__]:
        if name == omit:
            continue
        field = getattr(node, name, None)
        if isinstance(field, ast.AST):
            yield field
        elif isinstance(field, list):
            for item in field:
                yield item


class Binding(object):
    """
    Represents the binding of a value to a name.

    The checker uses this to keep track of which names have been bound and
    which names have not. See L{Assignment} for a special type of binding that
    is checked with stricter rules.

    @ivar used: pair of (L{Scope}, line-number) indicating the scope and
                line number that this binding was last used
    """

    def __init__(self, name, source):
        self.name = name
        self.source = source
        self.used = False

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<%s object %r from line %r at 0x%x>' % (self.__class__.__name__,
                                                        self.name,
                                                        self.source.lineno,
                                                        id(self))

    def redefines(self, other):
        return isinstance(other, Definition) and self.name == other.name


class Definition(Binding):
    """
    A binding that defines a function or a class.
    """


class Importation(Definition):
    """
    A binding created by an import statement.

    @ivar fullName: The complete name given to the import statement,
        possibly including multiple dotted components.
    @type fullName: C{str}
    """

    def __init__(self, name, source):
        self.fullName = name
        self.redefined = []
        name = name.split('.')[0]
        super(Importation, self).__init__(name, source)

    def redefines(self, other):
        if isinstance(other, Importation):
            return self.fullName == other.fullName
        return isinstance(other, Definition) and self.name == other.name


class Argument(Binding):
    """
    Represents binding a name as an argument.
    """


class Assignment(Binding):
    """
    Represents binding a name with an explicit assignment.

    The checker will raise warnings for any Assignment that isn't used. Also,
    the checker does not consider assignments in tuple/list unpacking to be
    Assignments, rather it treats them as simple Bindings.
    """


class FunctionDefinition(Definition):
    pass


class ClassDefinition(Definition):
    pass


class ExportBinding(Binding):
    """
    A binding created by an C{__all__} assignment.  If the names in the list
    can be determined statically, they will be treated as names for export and
    additional checking applied to them.

    The only C{__all__} assignment that can be recognized is one which takes
    the value of a literal list containing literal strings.  For example::

        __all__ = ["foo", "bar"]

    Names which are imported and not otherwise used but appear in the value of
    C{__all__} will not have an unused import warning reported for them.
    """

    def __init__(self, name, source, scope):
        if '__all__' in scope and isinstance(source, ast.AugAssign):
            self.names = list(scope['__all__'].names)
        else:
            self.names = []
        if isinstance(source.value, (ast.List, ast.Tuple)):
            for node in source.value.elts:
                if isinstance(node, ast.Str):
                    self.names.append(node.s)
        super(ExportBinding, self).__init__(name, source)


class Scope(dict):
    importStarred = False       # set to True when import * is found

    def __repr__(self):
        scope_cls = self.__class__.__name__
        return '<%s at 0x%x %s>' % (scope_cls, id(self), dict.__repr__(self))


class ClassScope(Scope):
    pass


class FunctionScope(Scope):
    """
    I represent a name scope for a function.

    @ivar globals: Names declared 'global' in this function.
    """
    usesLocals = False
    alwaysUsed = set(['__tracebackhide__',
                      '__traceback_info__', '__traceback_supplement__'])

    def __init__(self):
        super(FunctionScope, self).__init__()
        # Simplify: manage the special locals as globals
        self.globals = self.alwaysUsed.copy()
        self.returnValue = None     # First non-empty return
        self.isGenerator = False    # Detect a generator

    def unusedAssignments(self):
        """
        Return a generator for the assignments which have not been used.
        """
        for name, binding in self.items():
            if (not binding.used and name not in self.globals
                    and not self.usesLocals
                    and isinstance(binding, Assignment)):
                yield name, binding


class GeneratorScope(Scope):
    pass


class ModuleScope(Scope):
    pass


# Globally defined names which are not attributes of the builtins module, or
# are only present on some platforms.
_MAGIC_GLOBALS = ['__file__', '__builtins__', 'WindowsError']


def getNodeName(node):
    # Returns node.id, or node.name, or None
    if hasattr(node, 'id'):     # One of the many nodes with an id
        return node.id
    if hasattr(node, 'name'):   # a ExceptHandler node
        return node.name


class Checker(object):
    """
    I check the cleanliness and sanity of Python code.

    @ivar _deferredFunctions: Tracking list used by L{deferFunction}.  Elements
        of the list are two-tuples.  The first element is the callable passed
        to L{deferFunction}.  The second element is a copy of the scope stack
        at the time L{deferFunction} was called.

    @ivar _deferredAssignments: Similar to C{_deferredFunctions}, but for
        callables which are deferred assignment checks.
    """

    nodeDepth = 0
    offset = None
    traceTree = False

    builtIns = set(builtin_vars).union(_MAGIC_GLOBALS)
    _customBuiltIns = os.environ.get('PYFLAKES_BUILTINS')
    if _customBuiltIns:
        builtIns.update(_customBuiltIns.split(','))
    del _customBuiltIns

    def __init__(self, tree, filename='(none)', builtins=None,
                 withDoctest='PYFLAKES_DOCTEST' in os.environ):
        self._nodeHandlers = {}
        self._deferredFunctions = []
        self._deferredAssignments = []
        self.deadScopes = []
        self.messages = []
        self.filename = filename
        if builtins:
            self.builtIns = self.builtIns.union(builtins)
        self.withDoctest = withDoctest
        self.scopeStack = [ModuleScope()]
        self.exceptHandlers = [()]
        self.futuresAllowed = True
        self.root = tree
        self.handleChildren(tree)
        self.runDeferred(self._deferredFunctions)
        # Set _deferredFunctions to None so that deferFunction will fail
        # noisily if called after we've run through the deferred functions.
        self._deferredFunctions = None
        self.runDeferred(self._deferredAssignments)
        # Set _deferredAssignments to None so that deferAssignment will fail
        # noisily if called after we've run through the deferred assignments.
        self._deferredAssignments = None
        del self.scopeStack[1:]
        self.popScope()
        self.checkDeadScopes()

    def deferFunction(self, callable):
        """
        Schedule a function handler to be called just before completion.

        This is used for handling function bodies, which must be deferred
        because code later in the file might modify the global scope. When
        `callable` is called, the scope at the time this is called will be
        restored, however it will contain any new bindings added to it.
        """
        self._deferredFunctions.append((callable, self.scopeStack[:], self.offset))

    def deferAssignment(self, callable):
        """
        Schedule an assignment handler to be called just after deferred
        function handlers.
        """
        self._deferredAssignments.append((callable, self.scopeStack[:], self.offset))

    def runDeferred(self, deferred):
        """
        Run the callables in C{deferred} using their associated scope stack.
        """
        for handler, scope, offset in deferred:
            self.scopeStack = scope
            self.offset = offset
            handler()

    @property
    def scope(self):
        return self.scopeStack[-1]

    def popScope(self):
        self.deadScopes.append(self.scopeStack.pop())

    def checkDeadScopes(self):
        """
        Look at scopes which have been fully examined and report names in them
        which were imported but unused.
        """
        for scope in self.deadScopes:
            if isinstance(scope.get('__all__'), ExportBinding):
                all_names = set(scope['__all__'].names)
                if not scope.importStarred and \
                   os.path.basename(self.filename) != '__init__.py':
                    # Look for possible mistakes in the export list
                    undefined = all_names.difference(scope)
                    for name in undefined:
                        self.report(messages.UndefinedExport,
                                    scope['__all__'].source, name)
            else:
                all_names = []

            # Look for imported names that aren't used.
            for value in scope.values():
                if isinstance(value, Importation):
                    used = value.used or value.name in all_names
                    if not used:
                        messg = messages.UnusedImport
                        self.report(messg, value.source, value.name)
                    for node in value.redefined:
                        if isinstance(self.getParent(node), ast.For):
                            messg = messages.ImportShadowedByLoopVar
                        elif used:
                            continue
                        else:
                            messg = messages.RedefinedWhileUnused
                        self.report(messg, node, value.name, value.source)

    def pushScope(self, scopeClass=FunctionScope):
        self.scopeStack.append(scopeClass())

    def report(self, messageClass, *args, **kwargs):
        self.messages.append(messageClass(self.filename, *args, **kwargs))

    def getParent(self, node):
        # Lookup the first parent which is not Tuple, List or Starred
        while True:
            node = node.parent
            if not hasattr(node, 'elts') and not hasattr(node, 'ctx'):
                return node

    def getCommonAncestor(self, lnode, rnode, stop):
        if stop in (lnode, rnode) or not (hasattr(lnode, 'parent') and
                                          hasattr(rnode, 'parent')):
            return None
        if lnode is rnode:
            return lnode

        if (lnode.depth > rnode.depth):
            return self.getCommonAncestor(lnode.parent, rnode, stop)
        if (lnode.depth < rnode.depth):
            return self.getCommonAncestor(lnode, rnode.parent, stop)
        return self.getCommonAncestor(lnode.parent, rnode.parent, stop)

    def descendantOf(self, node, ancestors, stop):
        for a in ancestors:
            if self.getCommonAncestor(node, a, stop):
                return True
        return False

    def differentForks(self, lnode, rnode):
        """True, if lnode and rnode are located on different forks of IF/TRY"""
        ancestor = self.getCommonAncestor(lnode, rnode, self.root)
        parts = getAlternatives(ancestor)
        if parts:
            for items in parts:
                if self.descendantOf(lnode, items, ancestor) ^ \
                   self.descendantOf(rnode, items, ancestor):
                    return True
        return False

    def addBinding(self, node, value):
        """
        Called when a binding is altered.

        - `node` is the statement responsible for the change
        - `value` is the new value, a Binding instance
        """
        # assert value.source in (node, node.parent):
        for scope in self.scopeStack[::-1]:
            if value.name in scope:
                break
        existing = scope.get(value.name)

        if existing and not self.differentForks(node, existing.source):

            parent_stmt = self.getParent(value.source)
            if isinstance(existing, Importation) and isinstance(parent_stmt, ast.For):
                self.report(messages.ImportShadowedByLoopVar,
                            node, value.name, existing.source)

            elif scope is self.scope:
                if (isinstance(parent_stmt, ast.comprehension) and
                        not isinstance(self.getParent(existing.source),
                                       (ast.For, ast.comprehension))):
                    self.report(messages.RedefinedInListComp,
                                node, value.name, existing.source)
                elif not existing.used and value.redefines(existing):
                    self.report(messages.RedefinedWhileUnused,
                                node, value.name, existing.source)

            elif isinstance(existing, Importation) and value.redefines(existing):
                existing.redefined.append(node)

        self.scope[value.name] = value

    def getNodeHandler(self, node_class):
        try:
            return self._nodeHandlers[node_class]
        except KeyError:
            nodeType = getNodeType(node_class)
        self._nodeHandlers[node_class] = handler = getattr(self, nodeType)
        return handler

    def handleNodeLoad(self, node):
        name = getNodeName(node)
        if not name:
            return
        # try local scope
        try:
            self.scope[name].used = (self.scope, node)
        except KeyError:
            pass
        else:
            return

        scopes = [scope for scope in self.scopeStack[:-1]
                  if isinstance(scope, (FunctionScope, ModuleScope))]
        if isinstance(self.scope, GeneratorScope) and scopes[-1] != self.scopeStack[-2]:
            scopes.append(self.scopeStack[-2])

        # try enclosing function scopes and global scope
        importStarred = self.scope.importStarred
        for scope in reversed(scopes):
            importStarred = importStarred or scope.importStarred
            try:
                scope[name].used = (self.scope, node)
            except KeyError:
                pass
            else:
                return

        # look in the built-ins
        if importStarred or name in self.builtIns:
            return
        if name == '__path__' and os.path.basename(self.filename) == '__init__.py':
            # the special name __path__ is valid only in packages
            return

        # protected with a NameError handler?
        if 'NameError' not in self.exceptHandlers[-1]:
            self.report(messages.UndefinedName, node, name)

    def handleNodeStore(self, node):
        name = getNodeName(node)
        if not name:
            return
        # if the name hasn't already been defined in the current scope
        if isinstance(self.scope, FunctionScope) and name not in self.scope:
            # for each function or module scope above us
            for scope in self.scopeStack[:-1]:
                if not isinstance(scope, (FunctionScope, ModuleScope)):
                    continue
                # if the name was defined in that scope, and the name has
                # been accessed already in the current scope, and hasn't
                # been declared global
                used = name in scope and scope[name].used
                if used and used[0] is self.scope and name not in self.scope.globals:
                    # then it's probably a mistake
                    self.report(messages.UndefinedLocal,
                                scope[name].used[1], name, scope[name].source)
                    break

        parent_stmt = self.getParent(node)
        if isinstance(parent_stmt, (ast.For, ast.comprehension)) or (
                parent_stmt != node.parent and
                not self.isLiteralTupleUnpacking(parent_stmt)):
            binding = Binding(name, node)
        elif name == '__all__' and isinstance(self.scope, ModuleScope):
            binding = ExportBinding(name, node.parent, self.scope)
        else:
            binding = Assignment(name, node)
        if name in self.scope:
            binding.used = self.scope[name].used
        self.addBinding(node, binding)

    def handleNodeDelete(self, node):
        name = getNodeName(node)
        if not name:
            return
        if isinstance(self.scope, FunctionScope) and name in self.scope.globals:
            self.scope.globals.remove(name)
        else:
            try:
                del self.scope[name]
            except KeyError:
                self.report(messages.UndefinedName, node, name)

    def handleChildren(self, tree, omit=None):
        for node in iter_child_nodes(tree, omit=omit):
            self.handleNode(node, tree)

    def isLiteralTupleUnpacking(self, node):
        if isinstance(node, ast.Assign):
            for child in node.targets + [node.value]:
                if not hasattr(child, 'elts'):
                    return False
            return True

    def isDocstring(self, node):
        """
        Determine if the given node is a docstring, as long as it is at the
        correct place in the node tree.
        """
        return isinstance(node, ast.Str) or (isinstance(node, ast.Expr) and
                                             isinstance(node.value, ast.Str))

    def getDocstring(self, node):
        if isinstance(node, ast.Expr):
            node = node.value
        if not isinstance(node, ast.Str):
            return (None, None)
        # Computed incorrectly if the docstring has backslash
        doctest_lineno = node.lineno - node.s.count('\n') - 1
        return (node.s, doctest_lineno)

    def handleNode(self, node, parent):
        if node is None:
            return
        if self.offset and getattr(node, 'lineno', None) is not None:
            node.lineno += self.offset[0]
            node.col_offset += self.offset[1]
        if self.traceTree:
            print('  ' * self.nodeDepth + node.__class__.__name__)
        if self.futuresAllowed and not (isinstance(node, ast.ImportFrom) or
                                        self.isDocstring(node)):
            self.futuresAllowed = False
        self.nodeDepth += 1
        node.depth = self.nodeDepth
        node.parent = parent
        try:
            handler = self.getNodeHandler(node.__class__)
            handler(node)
        finally:
            self.nodeDepth -= 1
        if self.traceTree:
            print('  ' * self.nodeDepth + 'end ' + node.__class__.__name__)

    _getDoctestExamples = doctest.DocTestParser().get_examples

    def handleDoctests(self, node):
        try:
            (docstring, node_lineno) = self.getDocstring(node.body[0])
            examples = docstring and self._getDoctestExamples(docstring)
        except (ValueError, IndexError):
            # e.g. line 6 of the docstring for <string> has inconsistent
            # leading whitespace: ...
            return
        if not examples:
            return
        node_offset = self.offset or (0, 0)
        self.pushScope()
        underscore_in_builtins = '_' in self.builtIns
        if not underscore_in_builtins:
            self.builtIns.add('_')
        for example in examples:
            try:
                tree = compile(example.source, "<doctest>", "exec", ast.PyCF_ONLY_AST)
            except SyntaxError:
                e = sys.exc_info()[1]
                position = (node_lineno + example.lineno + e.lineno,
                            example.indent + 4 + (e.offset or 0))
                self.report(messages.DoctestSyntaxError, node, position)
            else:
                self.offset = (node_offset[0] + node_lineno + example.lineno,
                               node_offset[1] + example.indent + 4)
                self.handleChildren(tree)
                self.offset = node_offset
        if not underscore_in_builtins:
            self.builtIns.remove('_')
        self.popScope()

    def ignore(self, node):
        pass

    # "stmt" type nodes
    DELETE = PRINT = FOR = WHILE = IF = WITH = WITHITEM = RAISE = \
        TRYFINALLY = ASSERT = EXEC = EXPR = ASSIGN = handleChildren

    CONTINUE = BREAK = PASS = ignore

    # "expr" type nodes
    BOOLOP = BINOP = UNARYOP = IFEXP = DICT = SET = \
        COMPARE = CALL = REPR = ATTRIBUTE = SUBSCRIPT = LIST = TUPLE = \
        STARRED = NAMECONSTANT = handleChildren

    NUM = STR = BYTES = ELLIPSIS = ignore

    # "slice" type nodes
    SLICE = EXTSLICE = INDEX = handleChildren

    # expression contexts are node instances too, though being constants
    LOAD = STORE = DEL = AUGLOAD = AUGSTORE = PARAM = ignore

    # same for operators
    AND = OR = ADD = SUB = MULT = DIV = MOD = POW = LSHIFT = RSHIFT = \
        BITOR = BITXOR = BITAND = FLOORDIV = INVERT = NOT = UADD = USUB = \
        EQ = NOTEQ = LT = LTE = GT = GTE = IS = ISNOT = IN = NOTIN = ignore

    # additional node types
    LISTCOMP = COMPREHENSION = KEYWORD = handleChildren

    def GLOBAL(self, node):
        """
        Keep track of globals declarations.
        """
        if isinstance(self.scope, FunctionScope):
            self.scope.globals.update(node.names)

    NONLOCAL = GLOBAL

    def GENERATOREXP(self, node):
        self.pushScope(GeneratorScope)
        self.handleChildren(node)
        self.popScope()

    DICTCOMP = SETCOMP = GENERATOREXP

    def NAME(self, node):
        """
        Handle occurrence of Name (which can be a load/store/delete access.)
        """
        # Locate the name in locals / function / globals scopes.
        if isinstance(node.ctx, (ast.Load, ast.AugLoad)):
            self.handleNodeLoad(node)
            if (node.id == 'locals' and isinstance(self.scope, FunctionScope)
                    and isinstance(node.parent, ast.Call)):
                # we are doing locals() call in current scope
                self.scope.usesLocals = True
        elif isinstance(node.ctx, (ast.Store, ast.AugStore)):
            self.handleNodeStore(node)
        elif isinstance(node.ctx, ast.Del):
            self.handleNodeDelete(node)
        else:
            # must be a Param context -- this only happens for names in function
            # arguments, but these aren't dispatched through here
            raise RuntimeError("Got impossible expression context: %r" % (node.ctx,))

    def RETURN(self, node):
        if node.value and not self.scope.returnValue:
            self.scope.returnValue = node.value
        self.handleNode(node.value, node)

    def YIELD(self, node):
        self.scope.isGenerator = True
        self.handleNode(node.value, node)

    YIELDFROM = YIELD

    def FUNCTIONDEF(self, node):
        for deco in node.decorator_list:
            self.handleNode(deco, node)
        self.LAMBDA(node)
        self.addBinding(node, FunctionDefinition(node.name, node))
        if self.withDoctest:
            self.deferFunction(lambda: self.handleDoctests(node))

    def LAMBDA(self, node):
        args = []
        annotations = []

        if PY2:
            def addArgs(arglist):
                for arg in arglist:
                    if isinstance(arg, ast.Tuple):
                        addArgs(arg.elts)
                    else:
                        args.append(arg.id)
            addArgs(node.args.args)
            defaults = node.args.defaults
        else:
            for arg in node.args.args + node.args.kwonlyargs:
                args.append(arg.arg)
                annotations.append(arg.annotation)
            defaults = node.args.defaults + node.args.kw_defaults

        # Only for Python3 FunctionDefs
        is_py3_func = hasattr(node, 'returns')

        for arg_name in ('vararg', 'kwarg'):
            wildcard = getattr(node.args, arg_name)
            if not wildcard:
                continue
            args.append(wildcard if PY33 else wildcard.arg)
            if is_py3_func:
                if PY33:  # Python 2.5 to 3.3
                    argannotation = arg_name + 'annotation'
                    annotations.append(getattr(node.args, argannotation))
                else:     # Python >= 3.4
                    annotations.append(wildcard.annotation)

        if is_py3_func:
            annotations.append(node.returns)

        if len(set(args)) < len(args):
            for (idx, arg) in enumerate(args):
                if arg in args[:idx]:
                    self.report(messages.DuplicateArgument, node, arg)

        for child in annotations + defaults:
            if child:
                self.handleNode(child, node)

        def runFunction():

            self.pushScope()
            for name in args:
                self.addBinding(node, Argument(name, node))
            if isinstance(node.body, list):
                # case for FunctionDefs
                for stmt in node.body:
                    self.handleNode(stmt, node)
            else:
                # case for Lambdas
                self.handleNode(node.body, node)

            def checkUnusedAssignments():
                """
                Check to see if any assignments have not been used.
                """
                for name, binding in self.scope.unusedAssignments():
                    self.report(messages.UnusedVariable, binding.source, name)
            self.deferAssignment(checkUnusedAssignments)

            if PY32:
                def checkReturnWithArgumentInsideGenerator():
                    """
                    Check to see if there is any return statement with
                    arguments but the function is a generator.
                    """
                    if self.scope.isGenerator and self.scope.returnValue:
                        self.report(messages.ReturnWithArgsInsideGenerator,
                                    self.scope.returnValue)
                self.deferAssignment(checkReturnWithArgumentInsideGenerator)
            self.popScope()

        self.deferFunction(runFunction)

    def CLASSDEF(self, node):
        """
        Check names used in a class definition, including its decorators, base
        classes, and the body of its definition.  Additionally, add its name to
        the current scope.
        """
        for deco in node.decorator_list:
            self.handleNode(deco, node)
        for baseNode in node.bases:
            self.handleNode(baseNode, node)
        if not PY2:
            for keywordNode in node.keywords:
                self.handleNode(keywordNode, node)
        self.pushScope(ClassScope)
        if self.withDoctest:
            self.deferFunction(lambda: self.handleDoctests(node))
        for stmt in node.body:
            self.handleNode(stmt, node)
        self.popScope()
        self.addBinding(node, ClassDefinition(node.name, node))

    def AUGASSIGN(self, node):
        self.handleNodeLoad(node.target)
        self.handleNode(node.value, node)
        self.handleNode(node.target, node)

    def IMPORT(self, node):
        for alias in node.names:
            name = alias.asname or alias.name
            importation = Importation(name, node)
            self.addBinding(node, importation)

    def IMPORTFROM(self, node):
        if node.module == '__future__':
            if not self.futuresAllowed:
                self.report(messages.LateFutureImport,
                            node, [n.name for n in node.names])
        else:
            self.futuresAllowed = False

        for alias in node.names:
            if alias.name == '*':
                self.scope.importStarred = True
                self.report(messages.ImportStarUsed, node, node.module)
                continue
            name = alias.asname or alias.name
            importation = Importation(name, node)
            if node.module == '__future__':
                importation.used = (self.scope, node)
            self.addBinding(node, importation)

    def TRY(self, node):
        handler_names = []
        # List the exception handlers
        for handler in node.handlers:
            if isinstance(handler.type, ast.Tuple):
                for exc_type in handler.type.elts:
                    handler_names.append(getNodeName(exc_type))
            elif handler.type:
                handler_names.append(getNodeName(handler.type))
        # Memorize the except handlers and process the body
        self.exceptHandlers.append(handler_names)
        for child in node.body:
            self.handleNode(child, node)
        self.exceptHandlers.pop()
        # Process the other nodes: "except:", "else:", "finally:"
        self.handleChildren(node, omit='body')

    TRYEXCEPT = TRY

    def EXCEPTHANDLER(self, node):
        # 3.x: in addition to handling children, we must handle the name of
        # the exception, which is not a Name node, but a simple string.
        if isinstance(node.name, str):
            self.handleNodeStore(node)
        self.handleChildren(node)
