# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for bsdsocket.py
"""

# Standard library imports
import os
import socket

# Test library imports
import pytest

# Local imports
from spyder.utils.bsdsocket import write_packet, read_packet

@pytest.mark.skipif(os.name == 'nt',
                    reason="A non-blocking socket operation cannot "
                           "be completed in Windows immediately")
def test_bsdsockets():
    """Test write-read packet methods."""
    # socket read/write testing - client and server in one thread

    # (techtonik): the stuff below is placed into public domain
    address = ("127.0.0.1", 9999)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setblocking(0)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind( address )
    server.listen(2)

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect( address )

    client.send("data to be catched".encode('utf-8'))
    # accepted server socket is the one we can read from
    # note that it is different from server socket
    accsock, addr = server.accept()
    assert accsock.recv(4096) == b'data to be catched'

    # Testing BSD socket write_packet/read_packet
    write_packet(client, "a tiny piece of data")
    read = read_packet(accsock)
    assert read == "a tiny piece of data"

    client.close()
    server.close()


if __name__ == "__main__":
    pytest.main()
