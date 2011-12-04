# -*- coding: utf-8 -*-
#
# Copyright © 2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""BSD socket interface communication utilities"""

import socket
import struct
import cPickle as pickle
import threading


SZ = struct.calcsize("l")


def write_packet(sock, data, already_pickled=False):
    """Write *data* to socket *sock*"""
    if already_pickled:
        sent_data = data
    else:
        sent_data = pickle.dumps(data, pickle.HIGHEST_PROTOCOL)
    sock.send(struct.pack("l", len(sent_data)) + sent_data)


def read_packet(sock, timeout=None):
    """
    Read data from socket *sock*
    Returns None if something went wrong
    """
    sock.settimeout(timeout)
    dlen, data = None, None
    try:
        datalen = sock.recv(SZ)
        dlen, = struct.unpack("l", datalen)
        data = ''
        while len(data) < dlen:
            data += sock.recv(dlen)
    except socket.timeout:
        raise
    except socket.error:
        data = None
    finally:
        sock.settimeout(None)
    if data is not None:
        try:
            return pickle.loads(data)
        except (EOFError, pickle.UnpicklingError):
            return


# Using a lock object to avoid communication issues described in Issue 857:
# http://code.google.com/p/spyderlib/issues/detail?id=857
COMMUNICATE_LOCK = threading.Lock()

# * Old com implementation *
# See solution (1) in Issue 434:
# http://code.google.com/p/spyderlib/issues/detail?id=434#c13
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
## See solution (2) in Issue 434:
## http://code.google.com/p/spyderlib/issues/detail?id=434#c13
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
