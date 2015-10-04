#!/bin/bash

$PYTHON setup.py install

rm -rf $PREFIX/man
rm -rf $PREFIX/share
rm -f $PREFIX/bin/spyder_win_post_install.py
