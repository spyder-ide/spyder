# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

from argparse import ArgumentDefaultsHelpFormatter, RawDescriptionHelpFormatter
from logging import Formatter, StreamHandler, getLogger
from pathlib import Path

fmt = Formatter('%(asctime)s [%(levelname)s] [%(name)s] -> %(message)s')
h = StreamHandler()
h.setFormatter(fmt)
logger = getLogger('Installer')
logger.addHandler(h)
logger.setLevel('INFO')

HERE = Path(__file__).parent
SPYREPO = HERE.parent
RESOURCES = HERE / "resources"
BUILD = HERE / "build"
DIST = HERE / "dist"


class DocFormatter(
    RawDescriptionHelpFormatter,
    ArgumentDefaultsHelpFormatter
):
    pass
