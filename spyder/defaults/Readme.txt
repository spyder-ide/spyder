Copyright (c) Spyder Project Contributors
Licensed under the terms of the MIT License
(see spyder/__init__.py for details)

What is the purpose of this directory?
======================================

The files present here (licensed also MIT) are used to cleanly update user
configuration options from Spyder versions previous to 2.3. They way they did
an update was by resetting *all* config options to new defaults, which was
quite bad from a usability point of view. Now we compare new defaults against
a copy of their previous values and only change those that are different in
the user config file. This way almost all his/her values remain intact.

In particular:

* defaults-2.4.0.ini is used to do the update when the previous used version
  is between 2.1.9 and 2.3.0beta3

* defaults-3.0.0.ini is used when the previous version is 2.3.0beta4

Notes
=====

1. Please don't add more files here, unless you know what you're doing.
