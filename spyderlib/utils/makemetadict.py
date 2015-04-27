# -*- coding: utf-8 -*-


from importlib import import_module
import os.path as osp
from spyderlib.config import CONF


# On startup, find the required implementation
make_meta_dict_inner_func = None

makemetadict_custom = CONF.get('variable_explorer', 'makemetadict/custom', False)

if makemetadict_custom and osp.exists(makemetadict_custom):
    mod = import_module(makemetadict_custom)
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

