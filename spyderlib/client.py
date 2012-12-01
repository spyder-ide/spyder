# -*- coding: utf-8 -*-
#
# Copyright © 2012 The Spyder development team
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Simple socket client used to send the first arg passed to the Spyder executable
to an already running instance.

The arg can be a Python script or files with these extensions: .spydata, .mat,
.npy, or .h5, which can be imported by the Variable Explorer.
"""

import os.path as osp
import socket
import time

from spyderlib.cli_options import get_options
from spyderlib.config import CONF

def main():
    options, args = get_options()

    if args:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM,
                               socket.IPPROTO_TCP)
        port = CONF.get('main', 'open_files_port')
        
        # Wait ~50 secs to for the server to be up
        # Taken from http://stackoverflow.com/a/4766598/438386
        for x in xrange(200):
            try:
                client.connect(("127.0.0.1", port))
                client.send(osp.abspath(args[0]))
                client.close()
            except socket.error:
                time.sleep(0.25)
                continue
            break
        
        return
    else:
        return

if __name__ == "__main__":
    main()
