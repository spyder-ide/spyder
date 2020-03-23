# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)
# -----------------------------------------------------------------------------

"""
API to communicate between the Spyder IDE and the Spyder kernel.
It uses Jupyter Comms for messaging. The messages are sent by calling an
arbitrary function, with the limitation that the arguments have to be
picklable. If the function must return, the call must be blocking.

In addition, the frontend can interrupt the kernel to process the message sent.
This allows, for example, to set a breakpoint in pdb while the debugger is
running. The message will only be delivered when the kernel is checking the
event loop, or if pdb is waiting for an input.

Example:

On one side:

    ```
    def hello_str(msg):
        print('Hello ' + msg + '!')

    def add(a, d):
        return a + b

    left_comm.register_call_handler('add_numbers', add)
    left_comm.register_call_handler('print_hello', hello_str)
    ```

On the other:

    ```
    right_comm.remote_call().print_hello('world')
    res =  right_comm.remote_call(blocking=True).add_numbers(1, 2)
    print('1 + 2 = ' + str(res))
    ```

Which prints on the right side (The one with the `left_comm`):

    ```
    Hello world!
    ```

And on the left side:

    ```
    1 + 2 = 3
    ```
"""

from spyder_kernels.comms.commbase import CommError
