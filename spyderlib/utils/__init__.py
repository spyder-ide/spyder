# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
spyderlib.utils
===============

Spyder's utilities
"""

def select_port(default_port=20128):
    """Find and return a non used port"""
    import socket
    while True:
        try:
            sock = socket.socket(socket.AF_INET,
                                 socket.SOCK_STREAM,
                                 socket.IPPROTO_TCP)
#            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind( ("127.0.0.1", default_port) )
        except socket.error, _msg:
            default_port += 1
        else:
            break
        finally:
            sock.close()
            sock = None
    return default_port
