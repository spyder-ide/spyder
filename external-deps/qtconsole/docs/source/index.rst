.. _qtconsole:

==========================
The Qt Console for Jupyter
==========================

:Release: |release|
:Date: |today|

To start the Qt console::

    $ jupyter qtconsole

.. toctree::
   :maxdepth: 2

   installation
   config_options
   changelog

Overview
========
The Qt console is a very lightweight application that largely feels like a
terminal, but provides a number of enhancements only possible in a GUI, such as
inline figures, proper multi-line editing with syntax highlighting, graphical
calltips, and much more. The Qt console can use any Jupyter kernel.

.. figure:: _images/qtconsole.png
    :width: 400px
    :alt: Qt console with embedded plots
    :align: center
    :target: _images/qtconsole.png

    The Qt console with IPython, using inline matplotlib plots.

The Qt console frontend has hand-coded emacs-style bindings for text
navigation. This is not yet configurable.

.. tip::

   Since the Qt console tries hard to behave like a terminal, by default it
   immediately executes single lines of input that are complete.  If you want
   to force multi-line input, hit :kbd:`Ctrl-Enter` at the end of the first line
   instead of :kbd:`Enter`, and it will open a new line for input.  At any
   point in a multi-line block, you can force its execution (without having to
   go to the bottom) with :kbd:`Shift-Enter`.


Inline graphics
===============

One of the most exciting features of the Qt Console is embedded figures.
You can plot with matplotlib in IPython, or the plotting library of choice
in your kernel.

.. image:: figs/besselj.png
    :width: 519px


.. _saving:

Saving and Printing
===================

The Qt Console has the ability to save your current session, as either HTML or
XHTML. Your inline figures will be PNG in HTML, or inlined as SVG in XHTML.
PNG images have the option to be either in an external folder, as in many
browsers' "Webpage, Complete" option, or inlined as well, for a larger, but
more portable file.

.. note::

    Export to SVG+XHTML requires that you are using SVG figures, which is *not*
    the default.  To switch the inline figure format in IPython to use SVG, do:

    .. sourcecode:: ipython

        In [10]: %config InlineBackend.figure_format = 'svg'

    Or, you can add the same line (c.Inline... instead of %config Inline...) to
    your config files.

    This will only affect figures plotted after making this call


The widget also exposes the ability to print directly, via the default print
shortcut or context menu.


See these examples of :download:`png/html<figs/jn.html>` and
:download:`svg/xhtml <figs/jn.xhtml>` output. Note that syntax highlighting
does not survive export. This is a known issue, and is being investigated.


Colors and Highlighting
=======================

Terminal IPython has always had some coloring, but never syntax
highlighting. There are a few simple color choices, specified by the ``colors``
flag or ``%colors`` magic:

* LightBG for light backgrounds
* Linux for dark backgrounds
* NoColor for a simple colorless terminal

The Qt widget, however, has full syntax highlighting as you type, handled by
the `pygments`_ library. The ``style`` argument exposes access to any style by
name that can be found by pygments, and there are several already
installed.


Screenshot of ``jupyter qtconsole --style monokai``, which uses the 'monokai'
theme:

.. image:: figs/colors_dark.png
    :width: 627px

.. Note::

    Calling ``jupyter qtconsole -h`` will show all the style names that
    pygments can find on your system.

You can also pass the filename of a custom CSS stylesheet, if you want to do
your own coloring, via the ``stylesheet`` argument.  The default LightBG
stylesheet:

.. sourcecode:: css

    QPlainTextEdit, QTextEdit { background-color: white;
            color: black ;
            selection-background-color: #ccc}
    .error { color: red; }
    .in-prompt { color: navy; }
    .in-prompt-number { font-weight: bold; }
    .out-prompt { color: darkred; }
    .out-prompt-number { font-weight: bold; }
    /* .inverted is used to highlight selected completion */
    .inverted { background-color: black ; color: white; }

Fonts
=====

The Qt console is configurable via the ConsoleWidget. To change these, set the
``font_family`` or ``font_size`` traits of the ConsoleWidget. For instance, to
use 9pt Anonymous Pro::

    $> jupyter qtconsole --ConsoleWidget.font_family="Anonymous Pro" --ConsoleWidget.font_size=9

Process Management
==================

With the two-process ZMQ model, the frontend does not block input during
execution. This means that actions can be taken by the frontend while the
Kernel is executing, or even after it crashes. The most basic such command is
via 'Ctrl-.', which restarts the kernel.  This can be done in the middle of a
blocking execution. The frontend can also know, via a heartbeat mechanism, that
the kernel has died. This means that the frontend can safely restart the
kernel.

.. _multiple_consoles:

Multiple Consoles
-----------------

Since the Kernel listens on the network, multiple frontends can connect to it.
These do not have to all be qt frontends - any Jupyter frontend can connect and
run code.

Other frontends can connect to your kernel, and share in the execution. This is
great for collaboration.  The ``--existing`` flag means connect to a kernel
that already exists.  Starting other consoles
with that flag will not try to start their own kernel, but rather connect to
yours.  :file:`kernel-12345.json` is a small JSON file with the ip, port, and
authentication information necessary to connect to your kernel. By default, this file
will be in your Jupyter runtime directory.  If it is somewhere else,
you will need to use the full path of the connection file, rather than
just its filename.

If you need to find the connection info to send, and don't know where your connection file
lives, there are a couple of ways to get it. If you are already running a console
connected to an IPython kernel, you can use the ``%connect_info`` magic to display the information
necessary to connect another frontend to the kernel.

.. sourcecode:: ipython

    In [2]: %connect_info
    {
      "stdin_port":50255,
      "ip":"127.0.0.1",
      "hb_port":50256,
      "key":"70be6f0f-1564-4218-8cda-31be40a4d6aa",
      "shell_port":50253,
      "iopub_port":50254
    }

    Paste the above JSON into a file, and connect with:
        $> ipython <app> --existing <file>
    or, if you are local, you can connect with just:
        $> ipython <app> --existing kernel-12345.json
    or even just:
        $> ipython <app> --existing
    if this is the most recent kernel you have started.

Otherwise, you can find a connection file by name (and optionally profile) with
:func:`jupyter_client.find_connection_file`:

.. sourcecode:: bash

    $> python -c "from jupyter_client import find_connection_file;\
    print(find_connection_file('kernel-12345.json'))"
    /home/you/Library/Jupyter/runtime/kernel-12345.json


.. _kernel_security:

Security
--------

.. warning::

    Since the ZMQ code currently has no encryption, listening on an
    external-facing IP is dangerous.  You are giving any computer that can see
    you on the network the ability to connect to your kernel, and view your traffic.
    Read the rest of this section before listening on external ports
    or running a kernel on a shared machine.

By default (for security reasons), the kernel only listens on localhost, so you
can only connect multiple frontends to the kernel from your local machine. You
can specify to listen on an external interface by specifying the ``ip``
argument::

    $> jupyter qtconsole --ip=192.168.1.123

If you specify the ip as 0.0.0.0 or '*', that means all interfaces, so any
computer that can see yours on the network can connect to the kernel.

Messages are not encrypted, so users with access to the ports your kernel is using will be
able to see any output of the kernel. They will **NOT** be able to issue shell commands as
you due to message signatures.

.. warning::

    If you disable message signatures, then any user with access to the ports your
    kernel is listening on can issue arbitrary code as you. **DO NOT** disable message
    signatures unless you have a lot of trust in your environment.

The one security feature Jupyter does provide is protection from unauthorized execution.
Jupyter's messaging system will sign messages with HMAC digests using a shared-key. The key
is never sent over the network, it is only used to generate a unique hash for each message,
based on its content. When the kernel receives a message, it will check that the digest
matches, and discard the message. You can use any file that only you have access to to
generate this key, but the default is just to generate a new UUID.

.. _ssh_tunnels:

SSH Tunnels
-----------

Sometimes you want to connect to machines across the internet, or just across
a LAN that either doesn't permit open ports or you don't trust the other
machines on the network.  To do this, you can use SSH tunnels.  SSH tunnels
are a way to securely forward ports on your local machine to ports on another
machine, to which you have SSH access.

In simple cases, Jupyter's tools can forward ports over ssh by simply adding the
``--ssh=remote`` argument to the usual ``--existing...`` set of flags for connecting
to a running kernel, after copying the JSON connection file (or its contents) to
the second computer.

.. warning::

    Using SSH tunnels does *not* increase localhost security.  In fact, when
    tunneling from one machine to another *both* machines have open
    ports on localhost available for connections to the kernel.

There are two primary models for using SSH tunnels with Jupyter.  The first
is to have the Kernel listen only on localhost, and connect to it from
another machine on the same LAN.

First, let's start a kernel on machine **worker**, listening only
on loopback::

    user@worker $> ipython kernel
    [IPKernelApp] To connect another client to this kernel, use:
    [IPKernelApp] --existing kernel-12345.json

In this case, the IP that you would connect
to would still be 127.0.0.1, but you want to specify the additional ``--ssh`` argument
with the hostname of the kernel (in this example, it's 'worker')::

    user@client $> jupyter qtconsole  --ssh=worker --existing /path/to/kernel-12345.json

Which will write a new connection file with the forwarded ports, so you can reuse them::

    [JupyterQtConsoleApp] To connect another client via this tunnel, use:
    [JupyterQtConsoleApp] --existing kernel-12345-ssh.json

Note again that this opens ports on the *client* machine that point to your kernel.

.. note::

    the ssh argument is simply passed to openssh, so it can be fully specified ``user@host:port``
    but it will also respect your aliases, etc. in :file:`.ssh/config` if you have any.

The second pattern is for connecting to a machine behind a firewall across the internet
(or otherwise wide network). This time, we have a machine **login** that you have ssh access
to, which can see **kernel**, but **client** is on another network. The important difference
now is that **client** can see **login**, but *not* **worker**. So we need to forward ports from
client to worker *via* login. This means that the kernel must be started listening
on external interfaces, so that its ports are visible to `login`::

    user@worker $> ipython kernel --ip=0.0.0.0
    [IPKernelApp] To connect another client to this kernel, use:
    [IPKernelApp] --existing kernel-12345.json

Which we can connect to from the client with::

    user@client $> jupyter qtconsole --ssh=login --ip=192.168.1.123 --existing /path/to/kernel-12345.json

.. note::

    The IP here is the address of worker as seen from *login*, and need only be specified if
    the kernel used the ambiguous 0.0.0.0 (all interfaces) address. If it had used
    192.168.1.123 to start with, it would not be needed.


Manual SSH tunnels
------------------

It's possible that Jupyter's ssh helper functions won't work for you, for various
reasons.  You can still connect to remote machines, as long as you set up the tunnels
yourself.  The basic format of forwarding a local port to a remote one is::

    [client] $> ssh <server> <localport>:<remoteip>:<remoteport> -f -N

This will forward local connections to **localport** on client to **remoteip:remoteport**
*via* **server**. Note that remoteip is interpreted relative to *server*, not the client.
So if you have direct ssh access to the machine to which you want to forward connections,
then the server *is* the remote machine, and remoteip should be server's IP as seen from the
server itself, i.e. 127.0.0.1.  Thus, to forward local port 12345 to remote port 54321 on
a machine you can see, do::

    [client] $> ssh machine 12345:127.0.0.1:54321 -f -N

But if your target is actually on a LAN at 192.168.1.123, behind another machine called **login**,
then you would do::

    [client] $> ssh login 12345:192.168.1.16:54321 -f -N

The ``-f -N`` on the end are flags that tell ssh to run in the background,
and don't actually run any commands beyond creating the tunnel.

.. seealso::

    A short discussion of ssh tunnels: http://www.revsys.com/writings/quicktips/ssh-tunnel.html



Stopping Kernels and Consoles
-----------------------------

Since there can be many consoles per kernel, the shutdown mechanism and dialog
are probably more complicated than you are used to. Since you don't always want
to shutdown a kernel when you close a window, you are given the option to just
close the console window or also close the Kernel and *all other windows*. Note
that this only refers to all other *local* windows, as remote Consoles are not
allowed to shutdown the kernel, and shutdowns do not close Remote consoles (to
allow for saving, etc.).

Rules:

    * Restarting the kernel automatically clears all *local* Consoles, and prompts remote
      Consoles about the reset.
    * Shutdown closes all *local* Consoles, and notifies remotes that
      the Kernel has been shutdown.
    * Remote Consoles may not restart or shutdown the kernel.

Qt and the REPL
===============

.. note::

    This section is relevant regardless of the frontend you use to write Qt
    Code. This section is mostly there as it is easy to get confused and assume
    that writing Qt code in the QtConsole should change from usual Qt code. It
    should not. If you get confused, take a step back, and try writing your
    code using the pure terminal based ``jupyter console`` that does not
    involve Qt.

An important part of working with the REPL – QtConsole, Jupyter notebook,
IPython terminal – when you are writing your own Qt code is to remember that
user code (in the kernel) is *not* in the same process as the frontend.  This
means that there is not necessarily any Qt code running in the kernel, and
under most normal circumstances there isn't. This is true even if you are
running the QtConsole.

.. warning::

    When executing code from the qtconsole prompt, it is **not possible** to
    access the QtApplication instance of the QtConsole itself.


A common problem listed in the PyQt4 Gotchas_ is the fact that Python's garbage
collection will destroy Qt objects (Windows, etc.) once there is no longer a
Python reference to them, so you have to hold on to them.  For instance, in:

.. sourcecode:: python

    from PyQt4 import QtGui

    def make_window():
        win = QtGui.QMainWindow()

    def make_and_return_window():
        win = QtGui.QMainWindow()
        return win

:func:`make_window` will never draw a window, because garbage collection will
destroy it before it is drawn, whereas :func:`make_and_return_window` lets the
caller decide when the window object should be destroyed.  If, as a developer,
you know that you always want your objects to last as long as the process, you
can attach them to the ``QApplication`` instance itself:

.. sourcecode:: python

    from PyQt4 import QtGui, QtCore

    # do this just once:
    app = QtCore.QCoreApplication.instance()
    if not app:
        # we are in the kernel in most of the case there is NO qt code running. 
        # we need to create a Gui APP.
        app = QtGui.QApplication([])
    app.references = set()
    # then when you create Windows, add them to the set
    def make_window():
        win = QtGui.QMainWindow()
        app.references.add(win)

Now the ``QApplication`` itself holds a reference to ``win``, so it will never be
garbage collected until the application itself is destroyed.

.. _Gotchas: http://pyqt.sourceforge.net/Docs/PyQt4/gotchas.html#garbage-collection

Embedding the QtConsole in a Qt application
-------------------------------------------

There are a few options to integrate the Jupyter Qt console with your own
application:

* Use :class:`qtconsole.rich_jupyter_widget.RichJupyterWidget` in your
  Qt application. This will embed the console widget in your GUI and start the
  kernel in a separate process, so code typed into the console cannot access
  objects in your application. See :file:`examples/embed_qtconsole.py` for an
  example.

* Start an IPython kernel inside a PyQt application (
  `ipkernel_qtapp.py <https://github.com/ipython/ipykernel/blob/master/examples/embedding/ipkernel_qtapp.py>`_
  in the ``ipykernel`` repository shows how to do this). Then launch the Qt
  console in a separate process to connect to it. This means that the console
  will be in a separate window from your application's UI, but the code entered
  by the user runs in your application.

* Start a special IPython kernel, the
  :class:`ipykernel.inprocess.ipkernel.InProcessKernel`, which allows a
  QtConsole in the same process. See :file:`examples/inprocess_qtconsole.py`
  for an example. This allows both the kernel and the console interface to be
  part of your application, but it is not well supported. We encourage you to
  use one of the above options instead if you can.

Regressions
===========

There are some features, where the qt console lags behind the Terminal
frontend:

* !cmd input: Due to our use of pexpect, we cannot pass input to subprocesses
  launched using the '!' escape, so you should never call a command that
  requires interactive input.  For such cases, use the terminal IPython.  This
  will not be fixed, as abandoning pexpect would significantly degrade the
  console experience.

.. _PyQt: https://www.riverbankcomputing.com/software/pyqt/download
.. _pygments: http://pygments.org/
