# -*- coding: utf-8 -*-
#
# Copyright © 2018 André Roberge - mod_pydoc
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""PyDoc patch"""
# Standard libray
import builtins
import io
import inspect
import os
import pkgutil
import platform
import re
import sys
import tokenize
import warnings


# Local imports
from spyder.config.base import _, DEV
from spyder.config.gui import is_dark_interface, get_font
from spyder.py3compat import PY2, to_text_string

if not PY2:
    from pydoc import (
        classname, classify_class_attrs, describe, Doc, format_exception_only,
        Helper, HTMLRepr, _is_bound_method, ModuleScanner, locate, replace,
        visiblename, isdata, getdoc, deque, _split_list)

    class CustomHTMLDoc(Doc):
        """
        Formatter class for HTML documentation.

        See:
        https://github.com/aroberge/mod_pydoc/blob/master/mod_pydoc/pydoc.py
        """

        # ------------------------------------------ HTML formatting utilities

        _repr_instance = HTMLRepr()
        repr = _repr_instance.repr
        escape = _repr_instance.escape

        def page(self, title, contents):
            """Format an HTML page."""
            return '''\
<!doctype html>
<html><head><title>Python: %s</title>
<meta charset="UTF-8">
</head><body>
%s
</body></html>''' % (title, contents)

        def heading(self, title, extras=''):
            """Format a page heading."""
            return '''
    <table class="heading">
    <tr><td>{}</td><td class="align_right normal">{}</td></tr></table>
        '''.format(title, extras or '&nbsp;')

        def html_section(
                self, title, contents, width=6,
                prelude='', marginalia=None, gap='&nbsp;',
                css_class=''):
            """Format a section with a heading."""
            result = '''
    <table class="{}">
    <tr>
    <td colspan="3">
    {}</td></tr>
        '''.format(css_class, title)
            if prelude:
                result = result + '''
    <tr><td rowspan="2">{}</td>
    <td colspan="2">{}</td></tr>
    <tr><td>{}</td>'''.format(marginalia, prelude, gap)
            elif marginalia:
                result = result + '''
    <tr><td>{}</td><td>{}</td>'''.format(marginalia, gap)

            contents = '{}</td></tr></table><br>'.format(contents)
            return result + '\n<td class="inner_table">' + contents

        def bigsection(self, title, *args, **kwargs):
            """Format a section with a big heading."""
            title = '<span class="section_title">{}</span>'.format(title)
            return self.html_section(title, *args, **kwargs)

        def preformat(self, text):
            """Format literal preformatted text."""
            text = self.escape(text.expandtabs())
            return replace(text, '\n\n', '\n \n', '\n\n', '\n \n',
                                 ' ', '&nbsp;', '\n', '<br>\n')

        def multicolumn(self, list, format, cols=4):
            """Format a list of items into a multi-column list."""
            result = ''
            rows = (len(list)+cols-1)//cols
            for col in range(cols):
                result = (
                    result + '<td style="width:%d%%;vertical-align:text-top">'
                    % (100//cols))
                for i in range(rows*col, rows*col+rows):
                    if i < len(list):
                        result = result + format(list[i]) + '<br>\n'
                result = result + '</td>'
            return '<table style="width:100%%"><tr>%s</tr></table>' % result

        def grey(self, text):
            """Grey span."""
            return '<span class="grey">%s</span>' % text

        def namelink(self, name, *dicts):
            """Make a link for an identifier, given name-to-URL mappings."""
            for dict in dicts:
                if name in dict:
                    return '<a href="%s">%s</a>' % (dict[name], name)
            return name

        def classlink(self, object, modname):
            """Make a link for a class."""
            name, module = object.__name__, sys.modules.get(object.__module__)
            if hasattr(module, name) and getattr(module, name) is object:
                return '<a href="%s.html#%s">%s</a>' % (
                    module.__name__, name, classname(object, modname))
            return classname(object, modname)

        def modulelink(self, object):
            """Make a link for a module."""
            return '<a href="%s.html">%s</a>' % (
                object.__name__, object.__name__)

        def modpkglink(self, modpkginfo):
            """Make a link for a module or package to display in an index."""
            name, path, ispackage, shadowed = modpkginfo
            if shadowed:
                return self.grey(name)
            if path:
                url = '%s.%s.html' % (path, name)
            else:
                url = '%s.html' % name
            if ispackage:
                text = '%s&nbsp;(package)' % name
            else:
                text = name
            return '<a href="%s">%s</a>' % (url, text)

        def filelink(self, url, path):
            """Make a link to source file."""
            return '<a href="file:%s">%s</a>' % (url, path)

        def markup(self, text, escape=None, funcs={}, classes={}, methods={}):
            """
            Mark up some plain text, given a context of symbols to look for.

            Each context dictionary maps object names to anchor names.
            """
            escape = escape or self.escape
            results = []
            here = 0
            pattern = re.compile(r'\b((http|ftp)://\S+[\w/]|'
                                 r'RFC[- ]?(\d+)|'
                                 r'PEP[- ]?(\d+)|'
                                 r'(self\.)?(\w+))')
            while True:
                match = pattern.search(text, here)
                if not match:
                    break
                start, end = match.span()
                results.append(escape(text[here:start]))

                all, scheme, rfc, pep, selfdot, name = match.groups()
                if scheme:
                    url = escape(all).replace('"', '&quot;')
                    results.append('<a href="%s">%s</a>' % (url, url))
                elif rfc:
                    url = 'http://www.rfc-editor.org/rfc/rfc%d.txt' % int(rfc)
                    results.append('<a href="%s">%s</a>' % (url, escape(all)))
                elif pep:
                    url = 'http://www.python.org/dev/peps/pep-%04d/' % int(pep)
                    results.append('<a href="%s">%s</a>' % (url, escape(all)))
                elif text[end:end+1] == '(':
                    results.append(
                        self.namelink(name, methods, funcs, classes))
                elif selfdot:
                    results.append('self.%s' % name)
                else:
                    results.append(self.namelink(name, classes))
                here = end
            results.append(escape(text[here:]))
            return ''.join(results)

        # --------------------------------------------- type-specific routines

        def formattree(self, tree, modname, parent=None):
            """
            Produce HTML for a class tree as given by inspect.getclasstree().
            """
            result = ''
            for entry in tree:
                if type(entry) is type(()):
                    c, bases = entry
                    result = result + '<dt>'
                    result = result + self.classlink(c, modname)
                    if bases and bases != (parent,):
                        parents = []
                        for base in bases:
                            parents.append(self.classlink(base, modname))
                        result = result + '(' + ', '.join(parents) + ')'
                    result = result + '\n</dt>'
                elif type(entry) is type([]):
                    result = result + '<dd>\n%s</dd>\n' % self.formattree(
                        entry, modname, c)
            return '<dl><dt></dt>\n%s<dd></dd></dl>\n' % result

        def docmodule(self, object, name=None, mod=None, *ignored):
            """Produce HTML documentation for a module object."""
            name = object.__name__  # ignore the passed-in name
            try:
                all = object.__all__
            except AttributeError:
                all = None
            parts = name.split('.')
            links = []
            for i in range(len(parts)-1):
                links.append(
                    '<a href="{}.html" class="docmodule_link">{}</a>'.format(
                         '.'.join(parts[:i+1]), parts[i]))
            head = '.'.join(links + parts[-1:])
            try:
                path = inspect.getabsfile(object)
                url = path
                if sys.platform == 'win32':
                    import nturl2path
                    url = nturl2path.pathname2url(path)
                filelink = self.filelink(url, path)
            except TypeError:
                filelink = '(built-in)'
            info = []
            if hasattr(object, '__version__'):
                version = str(object.__version__)
                if version[:11] == '$' + 'Revision: ' and version[-1:] == '$':
                    version = version[11:-1].strip()
                info.append('version %s' % self.escape(version))
            if hasattr(object, '__date__'):
                info.append(self.escape(str(object.__date__)))
            if info:
                head = head + ' (%s)' % ', '.join(info)
            docloc = self.getdocloc(object)
            if docloc is not None:
                docloc = (
                    '<br><a href="%(docloc)s">Module Reference</a>' % locals())
            else:
                docloc = ''
            extras = '<a href=".">index</a><br>' + filelink + docloc
            result = self.heading(head, extras)

            modules = inspect.getmembers(object, inspect.ismodule)

            classes, cdict = [], {}
            for key, value in inspect.getmembers(object, inspect.isclass):
                # if __all__ exists, believe it.  Otherwise use old heuristic.
                if (all is not None or
                        (inspect.getmodule(value) or object) is object):
                    if visiblename(key, all, object):
                        classes.append((key, value))
                        cdict[key] = cdict[value] = '#' + key
            for key, value in classes:
                for base in value.__bases__:
                    key, modname = base.__name__, base.__module__
                    module = sys.modules.get(modname)
                    if modname != name and module and hasattr(module, key):
                        if getattr(module, key) is base:
                            if key not in cdict:
                                cdict[key] = cdict[base] = (
                                    modname + '.html#' + key)
            funcs, fdict = [], {}
            for key, value in inspect.getmembers(object, inspect.isroutine):
                # if __all__ exists, believe it.  Otherwise use old heuristic.
                if (all is not None or
                        inspect.isbuiltin(value) or
                        inspect.getmodule(value) is object):
                    if visiblename(key, all, object):
                        funcs.append((key, value))
                        fdict[key] = '#-' + key
                        if inspect.isfunction(value):
                            fdict[value] = fdict[key]
            data = []
            for key, value in inspect.getmembers(object, isdata):
                if visiblename(key, all, object):
                    data.append((key, value))

            doc = self.markup(getdoc(object), self.preformat, fdict, cdict)
            doc = doc and '<code>{}</code>'.format(doc)
            result = result + '<p>%s</p>\n' % doc

            if hasattr(object, '__path__'):
                modpkgs = []
                for importer, modname, ispkg in pkgutil.iter_modules(
                        object.__path__):
                    modpkgs.append((modname, name, ispkg, 0))
                modpkgs.sort()
                contents = self.multicolumn(modpkgs, self.modpkglink)
                result = result + self.bigsection(
                    'Package Contents', contents, css_class="package")
            elif modules:
                contents = self.multicolumn(
                    modules, lambda t: self.modulelink(t[1]))
                result = result + self.bigsection(
                    'Modules', contents, css_class="module")

            if classes:
                classlist = [value for (key, value) in classes]
                contents = [
                    self.formattree(inspect.getclasstree(classlist, 1), name)]
                for key, value in classes:
                    contents.append(
                        self.document(value, key, name, fdict, cdict))
                result = result + self.bigsection(
                    'Classes', ' '.join(contents), css_class="classes")
            if funcs:
                contents = []
                for key, value in funcs:
                    contents.append(
                        self.document(value, key, name, fdict, cdict))
                result = result + self.bigsection(
                    'Functions', ' '.join(contents), css_class="functions")
            if data:
                contents = []
                for key, value in data:
                    contents.append(self.document(value, key))
                result = result + self.bigsection(
                    'Data', '<br>\n'.join(contents), css_class="data")
            if hasattr(object, '__author__'):
                contents = self.markup(str(object.__author__), self.preformat)
                result = result + self.bigsection(
                    'Author', contents, css_class="author")
            if hasattr(object, '__credits__'):
                contents = self.markup(str(object.__credits__), self.preformat)
                result = result + self.bigsection(
                    'Credits', contents, css_class="credits")

            return result

        def docclass(self, object, name=None, mod=None, funcs={}, classes={},
                     *ignored):
            """Produce HTML documentation for a class object."""
            realname = object.__name__
            name = name or realname
            bases = object.__bases__

            contents = []
            push = contents.append

            # Cute little class to pump out a horizontal rule between sections.
            class HorizontalRule:
                def __init__(self):
                    self.needone = 0

                def maybe(self):
                    if self.needone:
                        push('<hr>\n')
                    self.needone = 1
            hr = HorizontalRule()

            # List the mro, if non-trivial.
            mro = deque(inspect.getmro(object))
            if len(mro) > 2:
                hr.maybe()
                push('<dl><dt>Method resolution order:</dt>\n')
                for base in mro:
                    push('<dd>%s</dd>\n' % self.classlink(base,
                                                          object.__module__))
                push('</dl>\n')

            def spill(msg, attrs, predicate):
                ok, attrs = _split_list(attrs, predicate)
                if ok:
                    hr.maybe()
                    push(msg)
                    for name, kind, homecls, value in ok:
                        try:
                            value = getattr(object, name)
                        except Exception:
                            # Some descriptors may meet a failure
                            # in their __get__.
                            # (bug aroberge/mod_pydoc#1785)
                            push(self._docdescriptor(name, value, mod))
                        else:
                            push(self.document(
                                value, name, mod, funcs, classes, mdict,
                                object))
                        push('\n')
                return attrs

            def spilldescriptors(msg, attrs, predicate):
                ok, attrs = _split_list(attrs, predicate)
                if ok:
                    hr.maybe()
                    push(msg)
                    for name, kind, homecls, value in ok:
                        push(self._docdescriptor(name, value, mod))
                return attrs

            def spilldata(msg, attrs, predicate):
                ok, attrs = _split_list(attrs, predicate)
                if ok:
                    hr.maybe()
                    push(msg)
                    for name, kind, homecls, value in ok:
                        base = self.docother(getattr(object, name), name, mod)
                        if callable(value) or inspect.isdatadescriptor(value):
                            doc = getattr(value, "__doc__", None)
                        else:
                            doc = None
                        if doc is None:
                            push('<dl><dt>%s</dt><dd></dd></dl>\n' % base)
                        else:
                            doc = self.markup(getdoc(value), self.preformat,
                                              funcs, classes, mdict)
                            doc = '<dd><code>%s</code></dd>' % doc
                            push('<dl><dt>%s%s</dt></dl>\n' % (base, doc))
                        push('\n')
                return attrs

            attrs = [(name, kind, cls, value)
                     for name, kind, cls, value in classify_class_attrs(object)
                     if visiblename(name, obj=object)]

            mdict = {}
            for key, kind, homecls, value in attrs:
                mdict[key] = anchor = '#' + name + '-' + key
                try:
                    value = getattr(object, name)
                except Exception:
                    # Some descriptors may meet a failure in their __get__.
                    # (bug #1785)
                    pass
                try:
                    # The value may not be hashable (e.g., a data attr with
                    # a dict or list value).
                    mdict[value] = anchor
                except TypeError:
                    pass

            while attrs:
                if mro:
                    thisclass = mro.popleft()
                else:
                    thisclass = attrs[0][2]
                attrs, inherited = _split_list(
                    attrs, lambda t: t[2] is thisclass)

                if thisclass is builtins.object:
                    attrs = inherited
                    continue
                elif thisclass is object:
                    tag = 'defined here'
                else:
                    tag = 'inherited from %s' % self.classlink(
                        thisclass, object.__module__)
                tag += ':<br>\n'

                # Sort attrs by name.
                attrs.sort(key=lambda t: t[0])

                # Pump out the attrs, segregated by kind.
                attrs = spill('Methods %s' % tag, attrs,
                              lambda t: t[1] == 'method')
                attrs = spill('Class methods %s' % tag, attrs,
                              lambda t: t[1] == 'class method')
                attrs = spill('Static methods %s' % tag, attrs,
                              lambda t: t[1] == 'static method')
                attrs = spilldescriptors('Data descriptors %s' % tag, attrs,
                                         lambda t: t[1] == 'data descriptor')
                attrs = spilldata('Data and other attributes %s' % tag, attrs,
                                  lambda t: t[1] == 'data')
                assert attrs == []
                attrs = inherited

            contents = ''.join(contents)

            if name == realname:
                title = '<span id="%s" class="signature"> class %s</span>' % (
                    name, realname)
            else:
                title = (
                    '%s = <span id="%s" class="signature">class %s</span>' % (
                        name, name, realname))
            if bases:
                parents = []
                for base in bases:
                    parents.append(self.classlink(base, object.__module__))
                title = title + '(%s)' % ', '.join(parents)
            doc = self.markup(
                getdoc(object), self.preformat, funcs, classes, mdict)
            doc = doc and '<code>%s<br>&nbsp;</code>' % doc

            return self.html_section(
                title, contents, 3, doc, css_class="docclass")

        def formatvalue(self, object):
            """Format an argument default value as text."""
            return self.grey('=' + self.repr(object))

        def docroutine(self, object, name=None, mod=None,
                       funcs={}, classes={}, methods={}, cl=None):
            """Produce HTML documentation for a function or method object."""
            realname = object.__name__
            name = name or realname
            anchor = (cl and cl.__name__ or '') + '-' + name
            note = ''
            skipdocs = 0
            if _is_bound_method(object):
                imclass = object.__self__.__class__
                if cl:
                    if imclass is not cl:
                        note = ' from ' + self.classlink(imclass, mod)
                else:
                    if object.__self__ is not None:
                        note = ' method of %s instance' % self.classlink(
                            object.__self__.__class__, mod)
                    else:
                        note = ' unbound %s method' % self.classlink(
                            imclass, mod)

            if name == realname:
                title = '<span id="%s" class="signature">%s</span>' % (
                    anchor, realname)
            else:
                if (cl and realname in cl.__dict__ and
                        cl.__dict__[realname] is object):
                    reallink = '<a href="#%s">%s</a>' % (
                        cl.__name__ + '-' + realname, realname)
                    skipdocs = 1
                else:
                    reallink = realname
                title = '<span id="%s" class="signature">%s</span> = %s' % (
                    anchor, name, reallink)
            argspec = None
            if inspect.isroutine(object):
                try:
                    signature = inspect.signature(object)
                except (ValueError, TypeError):
                    signature = None
                if signature:
                    argspec = str(signature)
                    if realname == '<lambda>':
                        title = '%s <em>lambda</em> ' % name
                        # XXX lambda's won't usually have
                        # func_annotations['return']
                        # since the syntax doesn't support but it is possible.
                        # So removing parentheses isn't truly safe.
                        argspec = argspec[1:-1]  # remove parentheses
            if not argspec:
                argspec = '(...)'

            decl = title + argspec + (note and self.grey(note))

            if skipdocs:
                return '<dl><dt>%s</dt><dd></dd></dl>\n' % decl
            else:
                doc = self.markup(
                    getdoc(object), self.preformat, funcs, classes, methods)
                doc = doc and '<dd><code>%s</code></dd>' % doc
                return '<dl><dt>%s</dt><dd></dd>%s</dl>\n' % (decl, doc)

        def _docdescriptor(self, name, value, mod):
            results = []
            push = results.append

            if name:
                push('<dl><dt>%s</dt>\n' % name)
            if value.__doc__ is not None:
                doc = self.markup(getdoc(value), self.preformat)
                push('<dd><code>%s</code></dd>\n' % doc)
            push('<dd></dd></dl>\n')

            return ''.join(results)

        def docproperty(self, object, name=None, mod=None, cl=None):
            """Produce html documentation for a property."""
            return self._docdescriptor(name, object, mod)

        def docother(self, object, name=None, mod=None, *ignored):
            """Produce HTML documentation for a data object."""
            lhs = name and '%s = ' % name or ''
            return lhs + self.repr(object)

        def docdata(self, object, name=None, mod=None, cl=None):
            """Produce html documentation for a data descriptor."""
            return self._docdescriptor(name, object, mod)

        def index(self, dir, shadowed=None):
            """Generate an HTML index for a directory of modules."""
            modpkgs = []
            if shadowed is None:
                shadowed = {}
            for importer, name, ispkg in pkgutil.iter_modules([dir]):
                if any((0xD800 <= ord(ch) <= 0xDFFF) for ch in name):
                    # ignore a module if its name contains a
                    # surrogate character
                    continue
                modpkgs.append((name, '', ispkg, name in shadowed))
                shadowed[name] = 1

            modpkgs.sort()
            if len(modpkgs):
                contents = self.multicolumn(modpkgs, self.modpkglink)
                return self.bigsection(dir, contents, css_class="index")
            else:
                return ''


def _url_handler(url, content_type="text/html"):
    """Pydoc url handler for use with the pydoc server.

    If the content_type is 'text/css', the _pydoc.css style
    sheet is read and returned if it exits.

    If the content_type is 'text/html', then the result of
    get_html_page(url) is returned.

    See https://github.com/python/cpython/blob/master/Lib/pydoc.py
    """
    class _HTMLDoc(CustomHTMLDoc):

        def page(self, title, contents):
            """Format an HTML page."""
            rich_text_font = get_font(option="rich_font").family()
            plain_text_font = get_font(option="font").family()

            if is_dark_interface():
                css_path = "static/css/dark_pydoc.css"
            else:
                css_path = "static/css/light_pydoc.css"

            css_link = (
                '<link rel="stylesheet" type="text/css" href="%s">' %
                css_path)

            code_style = (
                '<style>code {font-family: "%s"}</style>' % plain_text_font)

            html_page = '''\
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">
<html><head><title>Pydoc: %s</title>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
%s%s</head><body style="clear:both;font-family:'%s'">
%s<div style="clear:both;padding-top:.7em;">%s</div>
</body></html>''' % (title, css_link, code_style, rich_text_font,
                     html_navbar(), contents)

            return html_page

        def filelink(self, url, path):
            return '<a href="getfile?key=%s">%s</a>' % (url, path)

    html = _HTMLDoc()

    def html_navbar():
        version = html.escape("%s [%s, %s]" % (platform.python_version(),
                                               platform.python_build()[0],
                                               platform.python_compiler()))
        return """
            <div style='float:left'>
                Python %s<br>%s
            </div>
            <div style='float:right'>
                <div style='text-align:right; padding-bottom:.7em;'>
                  <a href="index.html">Module Index</a>
                  : <a href="topics.html">Topics</a>
                  : <a href="keywords.html">Keywords</a>
                </div>
                <div style='text-align:right;'>
                    <form action="search" style='display:inline;'>
                      <input class="input-search" type=text name=key size="22">
                      <input class="submit-search" type=submit value="Search">
                    </form>
                </div>
            </div>
            """ % (version, html.escape(platform.platform(terse=True)))

    def html_index():
        """Index page."""
        def bltinlink(name):
            return '<a href="%s.html">%s</a>' % (name, name)

        heading = html.heading('<span>Index of Modules</span>')
        names = [name for name in sys.builtin_module_names
                 if name != '__main__']
        contents = html.multicolumn(names, bltinlink)
        contents = [heading, '<p>' + html.bigsection(
            'Built-in Modules', contents, css_class="builtin_modules")]

        seen = {}
        for dir in sys.path:

            contents.append(html.index(dir, seen))

        contents.append(
            '<p class="ka_ping_yee"><strong>pydoc</strong> by Ka-Ping Yee'
            '&lt;ping@lfw.org&gt;</p>')
        return 'Index of Modules', ''.join(contents)

    def html_search(key):
        """Search results page."""
        # scan for modules
        search_result = []

        def callback(path, modname, desc):
            if modname[-9:] == '.__init__':
                modname = modname[:-9] + ' (package)'
            search_result.append((modname, desc and '- ' + desc))

        with warnings.catch_warnings():
            warnings.filterwarnings('ignore')  # ignore problems during import
            ModuleScanner().run(callback, key)

        # format page
        def bltinlink(name):
            return '<a href="%s.html">%s</a>' % (name, name)

        results = []
        heading = html.heading('Search Results')

        for name, desc in search_result:
            results.append(bltinlink(name) + desc)
        contents = heading + html.bigsection(
            'key = {}'.format(key), '<br>'.join(results), css_class="search")
        return 'Search Results', contents

    def html_getfile(path):
        """Get and display a source file listing safely."""
        path = path.replace('%20', ' ')
        with tokenize.open(path) as fp:
            lines = html.escape(fp.read())
        body = '<pre>%s</pre>' % lines
        heading = html.heading('File Listing')

        contents = heading + html.bigsection('File: {}'.format(path), body,
                                             css_class="getfile")
        return 'getfile %s' % path, contents

    def html_topics():
        """Index of topic texts available."""
        def bltinlink(name):
            return '<a href="topic?key=%s">%s</a>' % (name, name)

        heading = html.heading('Index of Topics') + '<br>'
        names = sorted(Helper.topics.keys())

        contents = html.multicolumn(names, bltinlink)
        contents = heading + html.bigsection(
            'Topics', contents, css_class="topics")
        return 'Topics', contents

    def html_keywords():
        """Index of keywords."""
        heading = html.heading('Index of Keywords')
        names = sorted(Helper.keywords.keys())

        def bltinlink(name):
            return '<a href="topic?key=%s">%s</a>' % (name, name)

        contents = html.multicolumn(names, bltinlink)
        contents = heading + '<br>' + html.bigsection(
            'Keywords', contents, css_class="keywords")
        return 'Keywords', contents

    def html_topicpage(topic):
        """Topic or keyword help page."""
        buf = io.StringIO()
        htmlhelp = Helper(buf, buf)
        contents, xrefs = htmlhelp._gettopic(topic)
        if topic in htmlhelp.keywords:
            title = 'Keyword'
        else:
            title = 'Topic'
        heading = html.heading(title)
        contents = '<pre>%s</pre>' % html.markup(contents)
        contents = html.bigsection(topic, contents, css_class="topics")
        if xrefs:
            xrefs = sorted(xrefs.split())

            def bltinlink(name):
                return '<a href="topic?key=%s">%s</a>' % (name, name)

            xrefs = html.multicolumn(xrefs, bltinlink)
            xrefs = html.html_section('Related help topics: ', xrefs,
                                      css_class="topics")
        return ('%s %s' % (title, topic),
                ''.join((heading, contents, xrefs)))

    def html_getobj(url):
        obj = locate(url, forceload=1)
        if obj is None and url != 'None':
            raise ValueError(
                _('There was an error while retrieving documentation '
                  'for the object you requested: Object could not be found'))
        title = describe(obj)
        content = html.document(obj, url)
        return title, content

    def html_error(url, exc):
        heading = html.heading('Error')
        if DEV:
            contents = '<br>'.join(html.escape(line) for line in
                                   format_exception_only(type(exc), exc))
        else:
            contents = '%s' % to_text_string(exc)
        contents = heading + html.bigsection(url, contents, css_class="error")
        return "Error - %s" % url, contents

    def get_html_page(url):
        """Generate an HTML page for url."""
        complete_url = url
        if url.endswith('.html'):
            url = url[:-5]
        try:
            if url in ("", "index"):
                title, content = html_index()
            elif url == "topics":
                title, content = html_topics()
            elif url == "keywords":
                title, content = html_keywords()
            elif '=' in url:
                op, _, url = url.partition('=')
                if op == "search?key":
                    title, content = html_search(url)
                elif op == "getfile?key":
                    title, content = html_getfile(url)
                elif op == "topic?key":
                    # try topics first, then objects.
                    try:
                        title, content = html_topicpage(url)
                    except ValueError:
                        title, content = html_getobj(url)
                elif op == "get?key":
                    # try objects first, then topics.
                    if url in ("", "index"):
                        title, content = html_index()
                    else:
                        try:
                            title, content = html_getobj(url)
                        except ValueError:
                            title, content = html_topicpage(url)
                else:
                    raise ValueError(
                        _('There was an error while retrieving documentation '
                          'for the object you requested: Bad URL %s') % url)
            else:
                title, content = html_getobj(url)
        except Exception as exc:
            # Catch any errors and display them in an error page.
            title, content = html_error(complete_url, exc)
        return html.page(title, content)

    if url.startswith('/'):
        url = url[1:]
    if content_type == 'text/css':
        path_here = os.path.dirname(os.path.realpath(__file__))
        css_path = os.path.join(path_here, url)
        with open(css_path) as fp:
            return ''.join(fp.readlines())
    elif content_type == 'text/html':
        return get_html_page(url)
    # Errors outside the url handler are caught by the server.
    raise TypeError(
        _('There was an error while retrieving documentation '
          'for the object you requested: unknown content type %r for url %s')
          % (content_type, url))


def _start_server(urlhandler, hostname, port):
    """
    Start an HTTP server thread on a specific port.

    This is a reimplementation of `pydoc._start_server` to handle connection
    errors for 'do_GET'.

    Taken from PyDoc: https://github.com/python/cpython/blob/3.7/Lib/pydoc.py
    """
    import http.server
    import email.message
    import select
    import threading
    import time

    class DocHandler(http.server.BaseHTTPRequestHandler):

        def do_GET(self):
            """Process a request from an HTML browser.

            The URL received is in self.path.
            Get an HTML page from self.urlhandler and send it.
            """
            if self.path.endswith('.css'):
                content_type = 'text/css'
            else:
                content_type = 'text/html'
            self.send_response(200)
            self.send_header(
                'Content-Type', '%s; charset=UTF-8' % content_type)
            self.end_headers()
            try:
                self.wfile.write(self.urlhandler(
                    self.path, content_type).encode('utf-8'))
            except ConnectionAbortedError:
                # Needed to handle error when client closes the connection,
                # for example when the client stops the load of the previously
                # requested page. See spyder-ide/spyder#10755
                pass
            except BrokenPipeError:
                # Needed to handle permission error when trying to open a port
                # for the web server of the online help.
                # See spyder-ide/spyder#13388
                pass

        def log_message(self, *args):
            # Don't log messages.
            pass

    class DocServer(http.server.HTTPServer):

        def __init__(self, host, port, callback):
            self.host = host
            self.address = (self.host, port)
            self.callback = callback
            self.base.__init__(self, self.address, self.handler)
            self.quit = False

        def serve_until_quit(self):
            while not self.quit:
                rd, wr, ex = select.select([self.socket.fileno()], [], [], 1)
                if rd:
                    self.handle_request()
            self.server_close()

        def server_activate(self):
            self.base.server_activate(self)
            if self.callback:
                self.callback(self)

    class ServerThread(threading.Thread):

        def __init__(self, urlhandler, host, port):
            self.urlhandler = urlhandler
            self.host = host
            self.port = int(port)
            threading.Thread.__init__(self)
            self.serving = False
            self.error = None

        def run(self):
            """Start the server."""
            try:
                DocServer.base = http.server.HTTPServer
                DocServer.handler = DocHandler
                DocHandler.MessageClass = email.message.Message
                DocHandler.urlhandler = staticmethod(self.urlhandler)
                docsvr = DocServer(self.host, self.port, self.ready)
                self.docserver = docsvr
                docsvr.serve_until_quit()
            except Exception as e:
                self.error = e

        def ready(self, server):
            self.serving = True
            self.host = server.host
            self.port = server.server_port
            self.url = 'http://%s:%d/' % (self.host, self.port)

        def stop(self):
            """Stop the server and this thread nicely."""
            self.docserver.quit = True
            self.join()
            # explicitly break a reference cycle: DocServer.callback
            # has indirectly a reference to ServerThread.
            self.docserver = None
            self.serving = False
            self.url = None

    thread = ServerThread(urlhandler, hostname, port)
    thread.start()
    # Wait until thread.serving is True to make sure we are
    # really up before returning.
    while not thread.error and not thread.serving:
        time.sleep(.01)
    return thread
