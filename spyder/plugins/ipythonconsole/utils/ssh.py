# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Utilities to connect to kernels through ssh."""

import atexit
import os

from qtpy.QtWidgets import QMessageBox
if not os.name == 'nt':
    import pexpect

from spyder.config.base import _


def _stop_tunnel(cmd):
    pexpect.run(cmd)


def openssh_tunnel(self, lport, rport, server, remoteip='127.0.0.1',
                   keyfile=None, password=None, timeout=0.4):
    """
    We decided to replace pyzmq's openssh_tunnel method to work around
    issue https://github.com/zeromq/pyzmq/issues/589 which was solved
    in pyzmq https://github.com/zeromq/pyzmq/pull/615
    """
    ssh = "ssh "
    if keyfile:
        ssh += "-i " + keyfile

    if ':' in server:
        server, port = server.split(':')
        ssh += " -p %s" % port

    cmd = "%s -O check %s" % (ssh, server)
    (output, exitstatus) = pexpect.run(cmd, withexitstatus=True)
    if not exitstatus:
        pid = int(output[output.find("(pid=")+5:output.find(")")])
        cmd = "%s -O forward -L 127.0.0.1:%i:%s:%i %s" % (
            ssh, lport, remoteip, rport, server)
        (output, exitstatus) = pexpect.run(cmd, withexitstatus=True)
        if not exitstatus:
            atexit.register(_stop_tunnel, cmd.replace("-O forward",
                                                      "-O cancel",
                                                      1))
            return pid
    cmd = "%s -f -S none -L 127.0.0.1:%i:%s:%i %s sleep %i" % (
                                  ssh, lport, remoteip, rport, server, timeout)

    # pop SSH_ASKPASS from env
    env = os.environ.copy()
    env.pop('SSH_ASKPASS', None)

    ssh_newkey = 'Are you sure you want to continue connecting'
    tunnel = pexpect.spawn(cmd, env=env)
    failed = False
    while True:
        try:
            i = tunnel.expect([ssh_newkey, '[Pp]assword:'], timeout=.1)
            if i == 0:
                host = server.split('@')[-1]
                question = _("The authenticity of host <b>%s</b> can't be "
                             "established. Are you sure you want to continue "
                             "connecting?") % host
                reply = QMessageBox.question(self, _('Warning'), question,
                                             QMessageBox.Yes | QMessageBox.No,
                                             QMessageBox.No)
                if reply == QMessageBox.Yes:
                    tunnel.sendline('yes')
                    continue
                else:
                    tunnel.sendline('no')
                    raise RuntimeError(
                       _("The authenticity of the host can't be established"))
            if i == 1 and password is not None:
                tunnel.sendline(password)
        except pexpect.TIMEOUT:
            continue
        except pexpect.EOF:
            if tunnel.exitstatus:
                raise RuntimeError(_("Tunnel '%s' failed to start") % cmd)
            else:
                return tunnel.pid
        else:
            if failed or password is None:
                raise RuntimeError(_("Could not connect to remote host"))
                # TODO: Use this block when pyzmq bug #620 is fixed
                # # Prompt a passphrase dialog to the user for a second attempt
                # password, ok = QInputDialog.getText(self, _('Password'),
                #             _('Enter password for: ') + server,
                #             echo=QLineEdit.Password)
                # if ok is False:
                #      raise RuntimeError('Could not connect to remote host.')
            tunnel.sendline(password)
            failed = True
