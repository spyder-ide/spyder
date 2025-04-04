import socket
import sys
import os


if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    SYS_EXEC = sys.executable
else:
    SYS_EXEC = 'spyder-remote-server'


def get_free_port():
    """Request a free port from the OS."""
    with socket.socket() as s:
        s.bind(('', 0))
        return s.getsockname()[1]


def generate_token():
    """Generate a random token."""
    return os.urandom(64).hex()
