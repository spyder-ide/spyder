import functools
import rope.base.pynames
from rope.base import ast, utils
from rope.refactor.importutils import importinfo
from rope.refactor.importutils import actions


class ModuleImports(object):

    def __init__(self, pycore, pymodule, import_filter=None):
        self.pycore = pycore
        self.pymodule = pymodule
        self.separating_lines = 0
        self.filter = import_filter

    @property
    @utils.saveit
    def imports(self):
        finder = _GlobalImportFinder(self.pymodule, self.pycore)
        result = finder.find_import_statements()
        self.separating_lines = finder.get_separating_line_count()
        if self.filter is not None:
            for import_stmt in result:
                if not self.filter(import_stmt):
                    import_stmt.readonly = True
        return result

    def _get_unbound_names(self, defined_pyobject):
        visitor = _GlobalUnboundNameFinder(self.pymodule, defined_pyobject)
        ast.walk(self.pymodule.get_ast(), visitor)
        return visitor.unbound

    def remove_unused_imports(self):
        can_select = _OneTimeSelector(self._get_unbound_names(self.pymodule))
        visitor = actions.RemovingVisitor(
            self.pycore, self._current_folder(), can_select)
        for import_statement in self.imports:
            import_statement.accept(visitor)

    def get_used_imports(self, defined_pyobject):
        result = []
        can_select = _OneTimeSelector(self._get_unbound_names(defined_pyobject))
        visitor = actions.FilteringVisitor(
            self.pycore, self._current_folder(), can_select)
        for import_statement in self.imports:
            new_import = import_statement.accept(visitor)
            if new_import is not None and not new_import.is_empty():
                result.append(new_import)
        return result

    def get_changed_source(self):
        imports = self.imports
        after_removing = self._remove_imports(imports)
        imports = [stmt for stmt in imports
                   if not stmt.import_info.is_empty()]

        first_non_blank = self._first_non_blank_line(after_removing, 0)
        first_import = self._first_import_line() - 1
        result = []
        # Writing module docs
        result.extend(after_removing[first_non_blank:first_import])
        # Writing imports
        sorted_imports = sorted(imports, key = functools.cmp_to_key(self._compare_import_locations))
        for stmt in sorted_imports:
            start = self._get_import_location(stmt)
            if stmt != sorted_imports[0]:
                result.append('\n' * stmt.blank_lines)
            result.append(stmt.get_import_statement() + '\n')
        if sorted_imports and first_non_blank < len(after_removing):
            result.append('\n' * self.separating_lines)

        # Writing the body
        first_after_imports = self._first_non_blank_line(after_removing,
                                                         first_import)
        result.extend(after_removing[first_after_imports:])
        return ''.join(result)

    def _get_import_location(self, stmt):
        start = stmt.get_new_start()
        if start is None:
            start = stmt.get_old_location()[0]
        return start

    def _compare_import_locations(self, stmt1, stmt2):
        def get_location(stmt):
            if stmt.get_new_start() is not None:
                return stmt.get_new_start()
            else:
                return stmt.get_old_location()[0]
        return get_location(stmt1) - get_location(stmt2)

    def _remove_imports(self, imports):
        lines = self.pymodule.source_code.splitlines(True)
        after_removing = []
        last_index = 0
        for stmt in imports:
            start, end = stmt.get_old_location()
            after_removing.extend(lines[last_index:start - 1])
            last_index = end - 1
            for i in range(start, end):
                after_removing.append('')
        after_removing.extend(lines[last_index:])
        return after_removing

    def _first_non_blank_line(self, lines, lineno):
        result = lineno
        for line in lines[lineno:]:
            if line.strip() == '':
                result += 1
            else:
                break
        return result

    def add_import(self, import_info):
        visitor = actions.AddingVisitor(self.pycore, [import_info])
        for import_statement in self.imports:
            if import_statement.accept(visitor):
                break
        else:
            lineno = self._get_new_import_lineno()
            blanks = self._get_new_import_blanks()
            self.imports.append(importinfo.ImportStatement(
                                import_info, lineno, lineno,
                                blank_lines=blanks))

    def _get_new_import_blanks(self):
        return 0

    def _get_new_import_lineno(self):
        if self.imports:
            return self.imports[-1].end_line
        return 1

    def filter_names(self, can_select):
        visitor = actions.RemovingVisitor(
            self.pycore, self._current_folder(), can_select)
        for import_statement in self.imports:
            import_statement.accept(visitor)

    def expand_stars(self):
        can_select = _OneTimeSelector(self._get_unbound_names(self.pymodule))
        visitor = actions.ExpandStarsVisitor(
            self.pycore, self._current_folder(), can_select)
        for import_statement in self.imports:
            import_statement.accept(visitor)

    def remove_duplicates(self):
        added_imports = []
        for import_stmt in self.imports:
            visitor = actions.AddingVisitor(self.pycore,
                                            [import_stmt.import_info])
            for added_import in added_imports:
                if added_import.accept(visitor):
                    import_stmt.empty_import()
            else:
                added_imports.append(import_stmt)

    def get_relative_to_absolute_list(self):
        visitor = rope.refactor.importutils.actions.RelativeToAbsoluteVisitor(
            self.pycore, self._current_folder())
        for import_stmt in self.imports:
            if not import_stmt.readonly:
                import_stmt.accept(visitor)
        return visitor.to_be_absolute

    def get_self_import_fix_and_rename_list(self):
        visitor = rope.refactor.importutils.actions.SelfImportVisitor(
            self.pycore, self._current_folder(), self.pymodule.get_resource())
        for import_stmt in self.imports:
            if not import_stmt.readonly:
                import_stmt.accept(visitor)
        return visitor.to_be_fixed, visitor.to_be_renamed

    def _current_folder(self):
        return self.pymodule.get_resource().parent

    def sort_imports(self):
        # IDEA: Sort from import list
        visitor = actions.SortingVisitor(self.pycore, self._current_folder())
        for import_statement in self.imports:
            import_statement.accept(visitor)
        in_projects = sorted(visitor.in_project, key = self._compare_imports)
        third_party = sorted(visitor.third_party, key = self._compare_imports)
        standards = sorted(visitor.standard, key = self._compare_imports)
        future = sorted(visitor.future, key = self._compare_imports)
        blank_lines = 0
        last_index = self._first_import_line()
        last_index = self._move_imports(future, last_index, 0)
        last_index = self._move_imports(standards, last_index, 1)
        last_index = self._move_imports(third_party, last_index, 1)
        last_index = self._move_imports(in_projects, last_index, 1)
        self.separating_lines = 2

    def _first_import_line(self):
        nodes = self.pymodule.get_ast().body
        lineno = 0
        if self.pymodule.get_doc() is not None:
            lineno = 1
        if len(nodes) > lineno:
            lineno = self.pymodule.logical_lines.logical_line_in(
                nodes[lineno].lineno)[0]
        else:
            lineno = self.pymodule.lines.length()
        while lineno > 1:
            line = self.pymodule.lines.get_line(lineno - 1)
            if line.strip() == '':
                lineno -= 1
            else:
                break
        return lineno

    def _compare_imports(self, stmt):
        str = stmt.get_import_statement()
        return (str.startswith('from '), str)

    def _move_imports(self, imports, index, blank_lines):
        if imports:
            imports[0].move(index, blank_lines)
            index += 1
            if len(imports) > 1:
                for stmt in imports[1:]:
                    stmt.move(index)
                    index += 1
        return index

    def handle_long_imports(self, maxdots, maxlength):
        visitor = actions.LongImportVisitor(
            self._current_folder(), self.pycore, maxdots, maxlength)
        for import_statement in self.imports:
            if not import_statement.readonly:
                import_statement.accept(visitor)
        for import_info in visitor.new_imports:
            self.add_import(import_info)
        return visitor.to_be_renamed

    def remove_pyname(self, pyname):
        """Removes pyname when imported in ``from mod import x``"""
        visitor = actions.RemovePyNameVisitor(self.pycore, self.pymodule,
                                              pyname, self._current_folder())
        for import_stmt in self.imports:
            import_stmt.accept(visitor)


class _OneTimeSelector(object):

    def __init__(self, names):
        self.names = names
        self.selected_names = set()

    def __call__(self, imported_primary):
        if self._can_name_be_added(imported_primary):
            for name in self._get_dotted_tokens(imported_primary):
                self.selected_names.add(name)
            return True
        return False

    def _get_dotted_tokens(self, imported_primary):
        tokens = imported_primary.split('.')
        for i in range(len(tokens)):
            yield '.'.join(tokens[:i + 1])

    def _can_name_be_added(self, imported_primary):
        for name in self._get_dotted_tokens(imported_primary):
            if name in self.names and name not in self.selected_names:
                return True
        return False


class _UnboundNameFinder(object):

    def __init__(self, pyobject):
        self.pyobject = pyobject

    def _visit_child_scope(self, node):
        pyobject = self.pyobject.get_module().get_scope().\
                   get_inner_scope_for_line(node.lineno).pyobject
        visitor = _LocalUnboundNameFinder(pyobject, self)
        for child in ast.get_child_nodes(node):
            ast.walk(child, visitor)

    def _FunctionDef(self, node):
        self._visit_child_scope(node)

    def _ClassDef(self, node):
        self._visit_child_scope(node)

    def _Name(self, node):
        if self._get_root()._is_node_interesting(node) and \
           not self.is_bound(node.id):
            self.add_unbound(node.id)

    def _Attribute(self, node):
        result = []
        while isinstance(node, ast.Attribute):
            result.append(node.attr)
            node = node.value
        if isinstance(node, ast.Name):
            result.append(node.id)
            primary = '.'.join(reversed(result))
            if self._get_root()._is_node_interesting(node) and \
               not self.is_bound(primary):
                self.add_unbound(primary)
        else:
            ast.walk(node, self)

    def _get_root(self):
        pass

    def is_bound(self, name, propagated=False):
        pass

    def add_unbound(self, name):
        pass


class _GlobalUnboundNameFinder(_UnboundNameFinder):

    def __init__(self, pymodule, wanted_pyobject):
        super(_GlobalUnboundNameFinder, self).__init__(pymodule)
        self.unbound = set()
        self.names = set()
        for name, pyname in pymodule._get_structural_attributes().items():
            if not isinstance(pyname, (rope.base.pynames.ImportedName,
                                       rope.base.pynames.ImportedModule)):
                self.names.add(name)
        wanted_scope = wanted_pyobject.get_scope()
        self.start = wanted_scope.get_start()
        self.end = wanted_scope.get_end() + 1

    def _get_root(self):
        return self

    def is_bound(self, primary, propagated=False):
        name = primary.split('.')[0]
        if name in self.names:
            return True
        return False

    def add_unbound(self, name):
        names = name.split('.')
        for i in range(len(names)):
            self.unbound.add('.'.join(names[:i + 1]))

    def _is_node_interesting(self, node):
        return self.start <= node.lineno < self.end


class _LocalUnboundNameFinder(_UnboundNameFinder):

    def __init__(self, pyobject, parent):
        super(_LocalUnboundNameFinder, self).__init__(pyobject)
        self.parent = parent

    def _get_root(self):
        return self.parent._get_root()

    def is_bound(self, primary, propagated=False):
        name = primary.split('.')[0]
        if propagated:
            names = self.pyobject.get_scope().get_propagated_names()
        else:
            names = self.pyobject.get_scope().get_names()
        if name in names or self.parent.is_bound(name, propagated=True):
            return True
        return False

    def add_unbound(self, name):
        self.parent.add_unbound(name)


class _GlobalImportFinder(object):

    def __init__(self, pymodule, pycore):
        self.current_folder = None
        if pymodule.get_resource():
            self.current_folder = pymodule.get_resource().parent
            self.pymodule = pymodule
        self.pycore = pycore
        self.imports = []
        self.pymodule = pymodule
        self.lines = self.pymodule.lines

    def visit_import(self, node, end_line):
        start_line = node.lineno
        import_statement = importinfo.ImportStatement(
            importinfo.NormalImport(self._get_names(node.names)),
            start_line, end_line, self._get_text(start_line, end_line),
            blank_lines=self._count_empty_lines_before(start_line))
        self.imports.append(import_statement)

    def _count_empty_lines_before(self, lineno):
        result = 0
        for current in range(lineno - 1, 0, -1):
            line = self.lines.get_line(current)
            if line.strip() == '':
                result += 1
            else:
                break
        return result

    def _count_empty_lines_after(self, lineno):
        result = 0
        for current in range(lineno + 1, self.lines.length()):
            line = self.lines.get_line(current)
            if line.strip() == '':
                result += 1
            else:
                break
        return result

    def get_separating_line_count(self):
        if not self.imports:
            return 0
        return self._count_empty_lines_after(self.imports[-1].end_line - 1)

    def _get_text(self, start_line, end_line):
        result = []
        for index in range(start_line, end_line):
            result.append(self.lines.get_line(index))
        return '\n'.join(result)

    def visit_from(self, node, end_line):
        level = 0
        if node.level:
            level = node.level
        import_info = importinfo.FromImport(
            node.module or '', # see comment at rope.base.ast.walk
            level, self._get_names(node.names))
        start_line = node.lineno
        self.imports.append(importinfo.ImportStatement(
                            import_info, node.lineno, end_line,
                            self._get_text(start_line, end_line),
                            blank_lines=self._count_empty_lines_before(start_line)))

    def _get_names(self, alias_names):
        result = []
        for alias in alias_names:
            result.append((alias.name, alias.asname))
        return result

    def find_import_statements(self):
        nodes = self.pymodule.get_ast().body
        for index, node in enumerate(nodes):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                lines = self.pymodule.logical_lines
                end_line = lines.logical_line_in(node.lineno)[1] + 1
            if isinstance(node, ast.Import):
                self.visit_import(node, end_line)
            if isinstance(node, ast.ImportFrom):
                self.visit_from(node, end_line)
        return self.imports
