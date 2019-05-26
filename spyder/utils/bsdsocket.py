# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""BSD socket interface communication utilities"""

# Be extra careful here. The interface is used to communicate with subprocesses
# by redirecting output streams through a socket. Any exception in this module
# and failure to read out buffers will most likely lock up Spyder.

import os
import socket
import struct
import threading
import errno
import traceback

# Local imports
from spyder.config.base import get_debug_level, STDERR
DEBUG_EDITOR = get_debug_level() >= 3
from spyder.py3compat import pickle
PICKLE_HIGHEST_PROTOCOL = 2


def temp_fail_retry(error, fun, *args):
    """Retry to execute function, ignoring EINTR error (interruptions)"""
    while 1:
        try:
            return fun(*args)
        except error as e:
            eintr = errno.WSAEINTR if os.name == 'nt' else errno.EINTR
            if e.args[0] == eintr:
                continue
            raise


SZ = struct.calcsize("l")


def write_packet(sock, data, already_pickled=False):
    """Write *data* to socket *sock*"""
    if already_pickled:
        sent_data = data
    else:
        sent_data = pickle.dumps(data, PICKLE_HIGHEST_PROTOCOL)
    sent_data = struct.pack("l", len(sent_data)) + sent_data
    nsend = len(sent_data)
    while nsend > 0:
        nsend -= temp_fail_retry(socket.error, sock.send, sent_data)


def read_packet(sock, timeout=None):
    """
    Read data from socket *sock*
    Returns None if something went wrong
    """
    sock.settimeout(timeout)
    dlen, data = None, None
    try:
        if os.name == 'nt':
            #  Windows implementation
            datalen = sock.recv(SZ)
            dlen, = struct.unpack("l", datalen)
            data = b''
            while len(data) < dlen:
                data += sock.recv(dlen)
        else:
            #  Linux/MacOSX implementation
            #  Thanks to eborisch:
            #  See issue 1106
            datalen = temp_fail_retry(socket.error, sock.recv,
                                      SZ, socket.MSG_WAITALL)
            if len(datalen) == SZ:
                dlen, = struct.unpack("l", datalen)
                data = temp_fail_retry(socket.error, sock.recv,
                                       dlen, socket.MSG_WAITALL)
    except socket.timeout:
        raise
    except socket.error:
        data = None
    finally:
        sock.settimeout(None)
    if data is not None:
        try:
            return pickle.loads(data)
        except Exception:
            # Catch all exceptions to avoid locking spyder
            if DEBUG_EDITOR:
                traceback.print_exc(file=STDERR)
            return


# Using a lock object to avoid communication issues described in Issue 857
COMMUNICATE_LOCK = threading.Lock()

# * Old com implementation *
# See solution (1) in Issue 434, comment 13:
def communicate(sock, command, settings=[]):
    """Communicate with monitor"""
    try:
        COMMUNICATE_LOCK.acquire()
        write_packet(sock, command)
        for option in settings:
            write_packet(sock, option)
        return read_packet(sock)
    finally:
        COMMUNICATE_LOCK.release()

## new com implementation:
## See solution (2) in Issue 434, comment 13:
#def communicate(sock, command, settings=[], timeout=None):
#    """Communicate with monitor"""
#    write_packet(sock, command)
#    for option in settings:
#        write_packet(sock, option)
#    if timeout == 0.:
#        # non blocking socket is not really supported:
#        # setting timeout to 0. here is equivalent (in current monitor's
#        # implementation) to say 'I don't need to receive anything in return'
#        return
#    while True:
#        output = read_packet(sock, timeout=timeout)
#        if output is None:
#            return
#        output_command, output_data = output
#        if command == output_command:
#            return output_data
#        elif DEBUG:
#            logging.debug("###### communicate/warning /Begin ######")
#            logging.debug("was expecting '%s', received '%s'" \
#                          % (command, output_command))
#            logging.debug("###### communicate/warning /End   ######")


class PacketNotReceived(object):
    pass

PACKET_NOT_RECEIVED = PacketNotReceived()


if __name__ == '__main__':
    if not os.name == 'nt':
        # socket read/write testing - client and server in one thread

        # (techtonik): the stuff below is placed into public domain
        print("-- Testing standard Python socket interface --")  # spyder: test-skip

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
        print('..got "%s" from %s' % (accsock.recv(4096), addr))  # spyder: test-skip

        # accsock.close()
        # client.send("more data for recv")
        #socket.error: [Errno 9] Bad file descriptor
        # accsock, addr = server.accept()
        #socket.error: [Errno 11] Resource temporarily unavailable


        print("-- Testing BSD socket write_packet/read_packet --")  # spyder: test-skip

        write_packet(client, "a tiny piece of data")
        print('..got "%s" from read_packet()' % (read_packet(accsock)))  # spyder: test-skip

        client.close()
        server.close()

        print("-- Done.")  # spyder: test-skip
