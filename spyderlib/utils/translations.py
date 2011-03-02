# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Translation utilities"""

import sys, os, os.path as osp

def get_module_path(modname):
    """Return module *modname* base path"""
    return osp.abspath(osp.dirname(sys.modules[modname].__file__))

def get_module_locale_path(modname):
    localepath = getattr(sys.modules[modname],'LOCALEPATH', '')
    if localepath != '':
        return localepath
    else:
        localepath = osp.join(get_module_path(modname), "locale")
        if not osp.isdir(localepath):
            # Assuming py2exe distribution
            localepath = osp.join(sys.prefix, modname, "locale")
        return localepath

def get_translation(modname, dirname=None):
    if dirname is None:
        dirname = modname
    # fixup environment var LANG in case it's unknown
    if "LANG" not in os.environ:
        import locale
        lang = locale.getdefaultlocale()[0]
        if lang is not None:
            os.environ["LANG"] = lang
    import gettext
    try:
        _trans = gettext.translation(modname, get_module_locale_path(dirname),
                                     codeset="utf-8")
        lgettext = _trans.lgettext
        def translate_gettext(x):
            if isinstance(x, unicode):
                x = x.encode("utf-8")
            return unicode(lgettext(x), "utf-8")
        return translate_gettext
    except IOError, _e:
        #print "Not using translations (%s)" % _e
        def translate_dumb(x):
            if not isinstance(x, unicode):
                return unicode(x, "utf-8")
            return x
        return translate_dumb
