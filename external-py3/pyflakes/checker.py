"""
Main module.

Implement the central Checker class.
Also, it models the Bindings and Scopes.
"""
import doctest
import os
import sys
try:
    builtin_vars = dir(__import__('builtins'))
    PY2 = False
except ImportError:
    builtin_vars = dir(__import__('__builtin__'))
    PY2 = True

try:
    import ast
    iter_child_nodes = ast.iter_child_nodes
except ImportError:     # Python 2.5
    import _ast as ast

    if 'decorator_list' not in ast.ClassDef._fields:
        # Patch the missing attribute 'decorator_list'
        ast.ClassDef.decorator_list = ()
        ast.FunctionDef.decorator_list = property(lambda s: s.decorators)

    def iter_child_nodes(node):
        """
        Yield all direct child nodes of *node*, that is, all fields that
        are nodes and all items of fields that are lists of nodes.
        """
        for name in node._fields:
            field = getattr(node, name, None)
            if isinstance(field, ast.AST):
                yield field
            elif isinstance(field, list):
                for item in field:
                    yield item
# Python >= 3.3 uses ast.Try instead of (ast.TryExcept + ast.TryFinally)
if hasattr(ast, 'Try'):
    ast_TryExcept = ast.Try
    ast_TryFinally = ()
else:
    ast_TryExcept = ast.TryExcept
    ast_TryFinally = ast.TryFinally

from pyflakes import messages


if PY2:
    def getNodeType(node_class):
        # workaround str.upper() which is locale-dependent
        return str(unicode(node_class.__name__).upper())
else:
    def getNodeType(node_class):
        return node_class.__name__.upper()


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


class Importation(Binding):
    """
    A binding created by an import statement.

    @ivar fullName: The complete name given to the import statement,
        possibly including multiple dotted components.
    @type fullName: C{str}
    """
    def __init__(self, name, source):
        self.fullName = name
        name = name.split('.')[0]
        super(Importation, self).__init__(name, source)


class Argument(Binding):
    """
    Represents binding a name as an argument.
    """


class Definition(Binding):
    """
    A binding that defines a function or a class.
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
    def names(self):
        """
        Return a list of the names referenced by this binding.
        """
        names = []
        if isinstance(self.source, ast.List):
            for node in self.source.elts:
                if isinstance(node, ast.Str):
                    names.append(node.s)
        return names


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
    withDoctest = ('PYFLAKES_NODOCTEST' not in os.environ)

    builtIns = set(builtin_vars).union(_MAGIC_GLOBALS)
    _customBuiltIns = os.environ.get('PYFLAKES_BUILTINS')
    if _customBuiltIns:
        builtIns.update(_customBuiltIns.split(','))
    del _customBuiltIns

    def __init__(self, tree, filename='(none)', builtins=None):
        self._nodeHandlers = {}
        self._deferredFunctions = []
        self._deferredAssignments = []
        self.deadScopes = []
        self.messages = []
        self.filename = filename
        if builtins:
            self.builtIns = self.builtIns.union(builtins)
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
            export = isinstance(scope.get('__all__'), ExportBinding)
            if export:
                all = scope['__all__'].names()
                if not scope.importStarred and \
                   os.path.basename(self.filename) != '__init__.py':
                    # Look for possible mistakes in the export list
                    undefined = set(all) - set(scope)
                    for name in undefined:
                        self.report(messages.UndefinedExport,
                                    scope['__all__'].source, name)
            else:
                all = []

            # Look for imported names that aren't used.
            for importation in scope.values():
                if isinstance(importation, Importation):
                    if not importation.used and importation.name not in all:
                        self.report(messages.UnusedImport,
                                    importation.source, importation.name)

    def pushScope(self, scopeClass=FunctionScope):
        self.scopeStack.append(scopeClass())

    def pushFunctionScope(self):    # XXX Deprecated
        self.pushScope(FunctionScope)

    def pushClassScope(self):       # XXX Deprecated
        self.pushScope(ClassScope)

    def report(self, messageClass, *args, **kwargs):
        self.messages.append(messageClass(self.filename, *args, **kwargs))

    def hasParent(self, node, kind):
        while hasattr(node, 'parent'):
            node = node.parent
            if isinstance(node, kind):
                return True

    def getCommonAncestor(self, lnode, rnode, stop=None):
        if not stop:
            stop = self.root
        if lnode is rnode:
            return lnode
        if stop in (lnode, rnode):
            return stop

        if not hasattr(lnode, 'parent') or not hasattr(rnode, 'parent'):
            return
        if (lnode.level > rnode.level):
            return self.getCommonAncestor(lnode.parent, rnode, stop)
        if (rnode.level > lnode.level):
            return self.getCommonAncestor(lnode, rnode.parent, stop)
        return self.getCommonAncestor(lnode.parent, rnode.parent, stop)

    def descendantOf(self, node, ancestors, stop=None):
        for a in ancestors:
            if self.getCommonAncestor(node, a, stop) not in (stop, None):
                return True
        return False

    def onFork(self, parent, lnode, rnode, items):
        return (self.descendantOf(lnode, items, parent) ^
                self.descendantOf(rnode, items, parent))

    def differentForks(self, lnode, rnode):
        """True, if lnode and rnode are located on different forks of IF/TRY"""
        ancestor = self.getCommonAncestor(lnode, rnode)
        if isinstance(ancestor, ast.If):
            for fork in (ancestor.body, ancestor.orelse):
                if self.onFork(ancestor, lnode, rnode, fork):
                    return True
        elif isinstance(ancestor, ast_TryExcept):
            body = ancestor.body + ancestor.orelse
            for fork in [body] + [[hdl] for hdl in ancestor.handlers]:
                if self.onFork(ancestor, lnode, rnode, fork):
                    return True
        elif isinstance(ancestor, ast_TryFinally):
            if self.onFork(ancestor, lnode, rnode, ancestor.body):
                return True
        return False

    def addBinding(self, node, value, reportRedef=True):
        """
        Called when a binding is altered.

        - `node` is the statement responsible for the change
        - `value` is the optional new value, a Binding instance, associated
          with the binding; if None, the binding is deleted if it exists.
        - if `reportRedef` is True (default), rebinding while unused will be
          reported.
        """
        redefinedWhileUnused = False
        if not isinstance(self.scope, ClassScope):
            for scope in self.scopeStack[::-1]:
                existing = scope.get(value.name)
                if (isinstance(existing, Importation)
                        and not existing.used
                        and (not isinstance(value, Importation) or
                             value.fullName == existing.fullName)
                        and reportRedef
                        and not self.differentForks(node, existing.source)):
                    redefinedWhileUnused = True
                    self.report(messages.RedefinedWhileUnused,
                                node, value.name, existing.source)

        existing = self.scope.get(value.name)
        if not redefinedWhileUnused and self.hasParent(value.source, ast.ListComp):
            if (existing and reportRedef
                    and not self.hasParent(existing.source, (ast.For, ast.ListComp))
                    and not self.differentForks(node, existing.source)):
                self.report(messages.RedefinedInListComp,
                            node, value.name, existing.source)

        if (isinstance(existing, Definition)
                and not existing.used
                and not self.differentForks(node, existing.source)):
            self.report(messages.RedefinedWhileUnused,
                        node, value.name, existing.source)
        else:
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

        parent = getattr(node, 'parent', None)
        if isinstance(parent, (ast.For, ast.comprehension, ast.Tuple, ast.List)):
            binding = Binding(name, node)
        elif (parent is not None and name == '__all__' and
              isinstance(self.scope, ModuleScope)):
            binding = ExportBinding(name, parent.value)
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

    def handleChildren(self, tree):
        for node in iter_child_nodes(tree):
            self.handleNode(node, tree)

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
        node.level = self.nodeDepth
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
            docstring, node_lineno = self.getDocstring(node.body[0])
            if not docstring:
                return
            examples = self._getDoctestExamples(docstring)
        except (ValueError, IndexError):
            # e.g. line 6 of the docstring for <string> has inconsistent
            # leading whitespace: ...
            return
        node_offset = self.offset or (0, 0)
        self.pushScope()
        for example in examples:
            try:
                tree = compile(example.source, "<doctest>", "exec", ast.PyCF_ONLY_AST)
            except SyntaxError:
                e = sys.exc_info()[1]
                position = (node_lineno + example.lineno + e.lineno,
                            example.indent + 4 + e.offset)
                self.report(messages.DoctestSyntaxError, node, position)
            else:
                self.offset = (node_offset[0] + node_lineno + example.lineno,
                               node_offset[1] + example.indent + 4)
                self.handleChildren(tree)
                self.offset = node_offset
        self.popScope()

    def ignore(self, node):
        pass

    # "stmt" type nodes
    RETURN = DELETE = PRINT = WHILE = IF = WITH = WITHITEM = RAISE = \
        TRYFINALLY = ASSERT = EXEC = EXPR = handleChildren

    CONTINUE = BREAK = PASS = ignore

    # "expr" type nodes
    BOOLOP = BINOP = UNARYOP = IFEXP = DICT = SET = YIELD = YIELDFROM = \
        COMPARE = CALL = REPR = ATTRIBUTE = SUBSCRIPT = LIST = TUPLE = \
        STARRED = handleChildren

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
    COMPREHENSION = KEYWORD = handleChildren

    def GLOBAL(self, node):
        """
        Keep track of globals declarations.
        """
        if isinstance(self.scope, FunctionScope):
            self.scope.globals.update(node.names)

    NONLOCAL = GLOBAL

    def LISTCOMP(self, node):
        # handle generators before element
        for gen in node.generators:
            self.handleNode(gen, node)
        self.handleNode(node.elt, node)

    def GENERATOREXP(self, node):
        self.pushScope(GeneratorScope)
        # handle generators before element
        for gen in node.generators:
            self.handleNode(gen, node)
        self.handleNode(node.elt, node)
        self.popScope()

    SETCOMP = GENERATOREXP

    def DICTCOMP(self, node):
        self.pushScope(GeneratorScope)
        for gen in node.generators:
            self.handleNode(gen, node)
        self.handleNode(node.key, node)
        self.handleNode(node.value, node)
        self.popScope()

    def FOR(self, node):
        """
        Process bindings for loop variables.
        """
        vars = []

        def collectLoopVars(n):
            if isinstance(n, ast.Name):
                vars.append(n.id)
            elif isinstance(n, ast.expr_context):
                return
            else:
                for c in iter_child_nodes(n):
                    collectLoopVars(c)

        collectLoopVars(node.target)
        for varn in vars:
            if (isinstance(self.scope.get(varn), Importation)
                    # unused ones will get an unused import warning
                    and self.scope[varn].used):
                self.report(messages.ImportShadowedByLoopVar,
                            node, varn, self.scope[varn].source)

        self.handleChildren(node)

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

    def FUNCTIONDEF(self, node):
        for deco in node.decorator_list:
            self.handleNode(deco, node)
        self.addBinding(node, FunctionDefinition(node.name, node))
        self.LAMBDA(node)
        if self.withDoctest:
            self.deferFunction(lambda: self.handleDoctests(node))

    def LAMBDA(self, node):
        args = []

        if PY2:
            def addArgs(arglist):
                for arg in arglist:
                    if isinstance(arg, ast.Tuple):
                        addArgs(arg.elts)
                    else:
                        if arg.id in args:
                            self.report(messages.DuplicateArgument,
                                        node, arg.id)
                        args.append(arg.id)
            addArgs(node.args.args)
            defaults = node.args.defaults
        else:
            for arg in node.args.args + node.args.kwonlyargs:
                if arg.arg in args:
                    self.report(messages.DuplicateArgument,
                                node, arg.arg)
                args.append(arg.arg)
                self.handleNode(arg.annotation, node)
            if hasattr(node, 'returns'):    # Only for FunctionDefs
                for annotation in (node.args.varargannotation,
                                   node.args.kwargannotation, node.returns):
                    self.handleNode(annotation, node)
            defaults = node.args.defaults + node.args.kw_defaults

        # vararg/kwarg identifiers are not Name nodes
        for wildcard in (node.args.vararg, node.args.kwarg):
            if not wildcard:
                continue
            if wildcard in args:
                self.report(messages.DuplicateArgument, node, wildcard)
            args.append(wildcard)
        for default in defaults:
            self.handleNode(default, node)

        def runFunction():

            self.pushScope()
            for name in args:
                self.addBinding(node, Argument(name, node), reportRedef=False)
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

    def ASSIGN(self, node):
        self.handleNode(node.value, node)
        for target in node.targets:
            self.handleNode(target, node)

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
        for child in iter_child_nodes(node):
            if child not in node.body:
                self.handleNode(child, node)

    TRYEXCEPT = TRY

    def EXCEPTHANDLER(self, node):
        # 3.x: in addition to handling children, we must handle the name of
        # the exception, which is not a Name node, but a simple string.
        if isinstance(node.name, str):
            self.handleNodeStore(node)
        self.handleChildren(node)
