# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Create a stand-alone executable"""

try:
    from guidata.disthelpers import Distribution
except ImportError:
    raise ImportError("This script requires guidata 1.4+")

import spyder


def create_executable():
    """Build executable using ``guidata.disthelpers``"""
    dist = Distribution()
    dist.setup(name="Example", version="1.1",
               description="Embedding Spyder Qt shell",
               script="example.pyw", target_name="example.exe")
    spyder.add_to_distribution(dist)
    #dist.add_modules('matplotlib')  # Uncomment if you need matplotlib
    dist.excludes += ['IPython']
    # Building executable
    dist.build('cx_Freeze')


if __name__ == '__main__':
    create_executable()
