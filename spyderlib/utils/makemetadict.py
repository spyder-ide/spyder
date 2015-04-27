# -*- coding: utf-8 -*-
import os.path as osp
from spyderlib.config import CONF


# On startup, find the required implementation
make_meta_dict_inner_func = None

mod_custom_path = CONF.get('variable_explorer', 'make_meta_dict', False)
makemetadict_def = CONF.get('variable_explorer', 'makemetadict/default', False)

if not makemetadict_def and osp.exists(str(mod_custom_path)):
    # Loading a module form file path seems to be messy:
    # http://stackoverflow.com/a/67692/2399799
    mod_custom_name, _ = osp.splitext(mod_custom_path)
    mod = None
    try:
        import imp
        mod = imp.load_source(mod_custom_name, mod_custom_path)
    except Exception:
        try:
            import importlib.machinery
            mod = importlib.machinery\
                            .SourceFileLoader(mod_custom_name, mod_custom_path)\
                            .load_module(mod_custom_name)
        except Exception:
            pass  # mod is still None, use default...
    if mod is not None:
        make_meta_dict_inner_func = getattr(mod, 'make_meta_dict', None)
        
if make_meta_dict_inner_func is None:
    from spyderlib.make_meta_dict_default import make_meta_dict
    make_meta_dict_inner_func = make_meta_dict


def make_meta_dict(value):
    """
    This wraps the user's code, giving a stacktrace on errors, but still
    returning a valid output.  The idea is that the make_meta_dict_user
    is actually located in a separate file that can be modified by the
    user (like the startup.py scripts).
    """
    try:
        return make_meta_dict_inner_func(value)
    except Exception:
        import traceback
        print(traceback.format_exc())
        return {}

