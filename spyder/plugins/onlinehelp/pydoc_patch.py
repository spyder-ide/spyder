# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""PyDoc patch"""
# Standard libray
import io
import os
import platform
import urllib
import sys
import tokenize
import warnings


# Local imports
from spyder.config.gui import is_dark_interface
from spyder.py3compat import PY2

if PY2:
    from pydoc import HTMLDoc
else:
    from pydoc import (
        describe, format_exception_only, Helper, HTMLDoc, ModuleScanner,
        locate)


class CustomHTMLDoc(HTMLDoc):
    """Custom HTMLDoc class to pass a css to HTML served with PyDoc."""

    def page(self, title, contents):
        """Format an HTML page."""
        if is_dark_interface():
            css_path = "static/css/dark_pydoc.css"
        else:
            css_path = "static/css/light_pydoc.css"

        css_link = (
            '<link rel="stylesheet" type="text/css" href="%s">' %
            css_path)
        html_page = '''\
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">
<html><head><title>Pydoc: %s</title>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
%s</head><body><div style="clear:both;padding-top:.5em;">%s</div>
</body></html>''' % (title, css_link, contents)

        return html_page


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
            if is_dark_interface():
                css_path = "static/css/dark_pydoc.css"
            else:
                css_path = "static/css/light_pydoc.css"

            css_link = (
                '<link rel="stylesheet" type="text/css" href="%s">' %
                css_path)
            html_page = '''\
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">
<html><head><title>Pydoc: %s</title>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
%s</head><body>%s<div style="clear:both;padding-top:.5em;">%s</div>
</body></html>''' % (title, css_link, html_navbar(), contents)

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
                <div style='text-align:center'>
                  <a href="index.html">Module Index</a>
                  : <a href="topics.html">Topics</a>
                  : <a href="keywords.html">Keywords</a>
                </div>
                <div>
                    <form action="get" style='display:inline;'>
                      <input type=text name=key size=15>
                      <input type=submit value="Get">
                    </form>&nbsp;
                    <form action="search" style='display:inline;'>
                      <input type=text name=key size=15>
                      <input type=submit value="Search">
                    </form>
                </div>
            </div>
            """ % (version, html.escape(platform.platform(terse=True)))

    def html_index():
        """Index page."""
        def bltinlink(name):
            return '<a href="%s.html">%s</a>' % (name, name)

        heading = html.heading(
            '<big><big><strong>Index of Modules</strong></big></big>',
            '#ffffff', '#7799ee')
        names = [name for name in sys.builtin_module_names
                 if name != '__main__']
        contents = html.multicolumn(names, bltinlink)
        contents = [heading, '<p>' + html.bigsection(
            'Built-in Modules', '#ffffff', '#ee77aa', contents)]

        seen = {}
        for dir in sys.path:
            contents.append(html.index(dir, seen))

        contents.append(
            '<p align=right><font color="#909090" face="helvetica,'
            'arial"><strong>pydoc</strong> by Ka-Ping Yee'
            '&lt;ping@lfw.org&gt;</font>')
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

            def onerror(modname):
                pass

            ModuleScanner().run(callback, key, onerror=onerror)

        # format page
        def bltinlink(name):
            return '<a href="%s.html">%s</a>' % (name, name)

        results = []
        heading = html.heading(
            '<big><big><strong>Search Results</strong></big></big>',
            '#ffffff', '#7799ee')
        for name, desc in search_result:
            results.append(bltinlink(name) + desc)
        contents = heading + html.bigsection(
            'key = %s' % key, '#ffffff', '#ee77aa', '<br>'.join(results))
        return 'Search Results', contents

    def html_getfile(path):
        """Get and display a source file listing safely."""
        path = urllib.parse.unquote(path)
        with tokenize.open(path) as fp:
            lines = html.escape(fp.read())
        body = '<pre>%s</pre>' % lines
        heading = html.heading(
            '<big><big><strong>File Listing</strong></big></big>',
            '#ffffff', '#7799ee')
        contents = heading + html.bigsection(
            'File: %s' % path, '#ffffff', '#ee77aa', body)
        return 'getfile %s' % path, contents

    def html_topics():
        """Index of topic texts available."""
        def bltinlink(name):
            return '<a href="topic?key=%s">%s</a>' % (name, name)

        heading = html.heading(
            '<big><big><strong>INDEX</strong></big></big>',
            '#ffffff', '#7799ee')
        names = sorted(Helper.topics.keys())

        contents = html.multicolumn(names, bltinlink)
        contents = heading + html.bigsection(
            'Topics', '#ffffff', '#ee77aa', contents)
        return 'Topics', contents

    def html_keywords():
        """Index of keywords."""
        heading = html.heading(
            '<big><big><strong>INDEX</strong></big></big>',
            '#ffffff', '#7799ee')
        names = sorted(Helper.keywords.keys())

        def bltinlink(name):
            return '<a href="topic?key=%s">%s</a>' % (name, name)

        contents = html.multicolumn(names, bltinlink)
        contents = heading + html.bigsection(
            'Keywords', '#ffffff', '#ee77aa', contents)
        return 'Keywords', contents

    def html_topicpage(topic):
        """Topic or keyword help page."""
        buf = io.StringIO()
        htmlhelp = Helper(buf, buf)
        contents, xrefs = htmlhelp._gettopic(topic)
        if topic in htmlhelp.keywords:
            title = 'KEYWORD'
        else:
            title = 'TOPIC'
        heading = html.heading(
            '<big><big><strong>%s</strong></big></big>' % title,
            '#ffffff', '#7799ee')
        contents = '<pre>%s</pre>' % html.markup(contents)
        contents = html.bigsection(topic, '#ffffff', '#ee77aa', contents)
        if xrefs:
            xrefs = sorted(xrefs.split())

            def bltinlink(name):
                return '<a href="topic?key=%s">%s</a>' % (name, name)

            xrefs = html.multicolumn(xrefs, bltinlink)
            xrefs = html.section('Related help topics: ',
                                 '#ffffff', '#ee77aa', xrefs)
        return ('%s %s' % (title, topic),
                ''.join((heading, contents, xrefs)))

    def html_getobj(url):
        obj = locate(url, forceload=1)
        if obj is None and url != 'None':
            raise ValueError('could not find object')
        title = describe(obj)
        content = html.document(obj, url)
        return title, content

    def html_error(url, exc):
        heading = html.heading(
            '<big><big><strong>Error</strong></big></big>',
            '#ffffff', '#7799ee')
        contents = '<br>'.join(html.escape(line) for line in
                               format_exception_only(type(exc), exc))
        contents = heading + html.bigsection(url, '#ffffff', '#bb0000',
                                             contents)
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
                    raise ValueError('bad pydoc url')
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
    raise TypeError('unknown content type %r for url %s' % (content_type, url))


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
