# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
"""
Command-line interface for menuinst in Spyder installer
"""

import sys
from pathlib import Path
from argparse import ArgumentParser

from menuinst import api

_base = Path(sys.prefix)
_target = _base / "envs/spyder-runtime"
_menu = _target / "Menu/spyder-menu.json"


def shortcut(**args):
    _, menu_items = api._load(**args)
    print(menu_items[0]._paths()[0])


# ---- Parser for common option items
_parser = ArgumentParser()
_parser.add_argument(
    "--menu",
    dest="metadata_or_path",
    default=str(_menu),
    metavar="PATH",
    type=lambda x: str(Path(x).absolute()),
    help="Path to menu.json file"
)
_parser.add_argument(
    "--target",
    dest="target_prefix",
    default=str(_target),
    type=lambda x: str(Path(x).absolute()),
    help="Path to target environment prefix"
)
_parser.add_argument(
    "--base",
    dest="base_prefix",
    default=str(_base),
    type=lambda x: str(Path(x).absolute()),
    help="Path to base environment prefix"
)

# ---- Main parser for menuinst_cli
parser = ArgumentParser(
    description="Command-line interface for menuinst in Spyder installer"
)
subparsers = parser.add_subparsers(
    title="subcommands",
    required=True,
)

# ---- Subcommand parsers
parser_install = subparsers.add_parser(
    "install", help="Install shortcut.",
    description="Install shortcut.",
    parents=[_parser],
    conflict_handler="resolve",
)
parser_install.set_defaults(func=api.install)

parser_remove = subparsers.add_parser(
    "remove", help="Remove shortcut.",
    description="Remove shortcut.",
    parents=[_parser],
    conflict_handler="resolve",
)
parser_remove.set_defaults(func=api.remove)

parser_shortcut = subparsers.add_parser(
    "shortcut", help="Print shortcut path.",
    description="Print shortcut path.",
    parents=[_parser],
    conflict_handler="resolve",
)
parser_shortcut.add_argument(
    "--mode", dest="_mode", choices=["system", "user"], default="user",
    help="Whether to perform system or user install."
)
parser_shortcut.set_defaults(func=shortcut)

args = vars(parser.parse_args())
func = args.pop("func")
func(**args)
