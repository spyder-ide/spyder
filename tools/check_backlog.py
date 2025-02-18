#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
"""
Public API signature checker.

This script compares a “base” version of a Python module with an updated
version by parsing both files using AST and extracting their signatures
(functions, classes, and public methods/assignments). It then compares the
signatures between the base and updated versions. Any addition, removal, or
change in signature is flagged as an API change.

Finally, the script reads a chagelog file and checks that each API change (using
the public API name extracted from the signature) is mentioned in the "API
changes" section for the current version.
"""
from __future__ import annotations

import argparse
import ast
import logging
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from enum import Enum, auto
from functools import cached_property, wraps
from pathlib import Path

# Get the current version from Spyder.
try:
    from spyder import __version__
except ImportError:
    sys.stderr.write("Error: Could not import Spyder to get __version__.\n")
    sys.exit(1)

if sys.version_info >= (3, 9):
    _unparse = ast.unparse
else:
    import astor
    def _unparse(node):
        return astor.to_source(node).strip()


_logger = logging.getLogger(Path(__file__).stem)


CHAGELOG_DIR = Path("changelogs")


def generate_to(cls):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return cls(func(*args, **kwargs))
        return wrapper
    return decorator


def get_current_changelog():
    major = __version__.split(".")[0]
    return CHAGELOG_DIR / f"Spyder-{major}.md"


def get_current_version():
    # PEP 440 compliant
    m = re.match(r"(d+(\.\d)*)((a|b|rc)\d)?(.post\d)?(.dev\d)?", __version__)
    # Exclude pre-releases
    if m and (m.group(4) or m.group(6)):
        return None

    if m:
        return m.group(1)

    sys.stderr.write(f"Could not extract a valid version from {__version__}.\n")
    sys.exit(1)


class SignatureType(Enum):
    FUNCTION = auto()
    ASYNC_FUNCTION = auto()
    CLASS = auto()
    ASSIGNMENT = auto()

    def __str__(self):
        return self.name[:min(5, len(self.name))]


class SignatureItem:
    def __init__(self, module, sig_type, name, arguments=None):
        self._module = module
        self._sig_type = sig_type
        self._name = name
        self._arguments = frozenset() if arguments is None else frozenset(arguments)

        _logger.debug("Created SignatureItem: %s", self)

    def __hash__(self):
        return hash((self.module, self.sig_type, self.name, self.arguments))

    def __eq__(self, other):
        if not isinstance(other, SignatureItem):
            msg = f"Cannot compare SignatureItem with {type(other)}"
            raise TypeError(msg)

        return self.__hash__() == other.__hash__()

    def __repr__(self):
        return (
            f"{self.module}:{self.sig_type}:{self.name}" +
            (f"({', '.join(self.arguments)})" if self.arguments else "")
        )

    @property
    def module(self):
        return self._module

    @property
    def sig_type(self):
        return self._sig_type

    @property
    def name(self):
        return self._name

    @property
    def arguments(self):
        return self._arguments

    def is_included(self, other):
        return other.module + "." + other.name in self.module

    def is_renamed(self, other):
        return self.module == other.module and self.sig_type == other.sig_type and self.arguments == other.arguments and self.name != other.name

    def is_args_changed(self, other):
        return self.module == other.module and self.sig_type == other.sig_type and self.name == other.name and self.arguments != other.arguments

    @classmethod
    def function_signature(cls, node, parent_id=""):
        """
        Reconstruct a function signature (for both module functions and methods)
        ignoring type annotations and default values.
        """
        # Skip non-public (unless dunder)
        if node.name.startswith("_") and not (node.name.startswith("__") and node.name.endswith("__")):
            yield from []
        params = []
        # Positional-only arguments (Python 3.8+)
        if hasattr(node.args, "posonlyargs") and node.args.posonlyargs:
            posonly = [arg.arg for arg in node.args.posonlyargs]
            params.extend(posonly)
            params.append("/")
        # Regular arguments
        if node.args.args:
            params.extend(arg.arg for arg in node.args.args)
        # Vararg (*args)
        if node.args.vararg:
            params.append("*" + node.args.vararg.arg)
        elif node.args.kwonlyargs:
            params.append("*")
        # Keyword-only arguments
        if node.args.kwonlyargs:
            params.extend(arg.arg for arg in node.args.kwonlyargs)
        # Kwarg (**kwargs)
        if node.args.kwarg:
            params.append("**" + node.args.kwarg.arg)

        yield cls(
            module=parent_id,
            sig_type=SignatureType.ASYNC_FUNCTION if isinstance(node, ast.AsyncFunctionDef) else SignatureType.FUNCTION,
            name=node.name,
            arguments=params,
        )

    @classmethod
    def class_signature(cls, node, parent_id=""):
        """
        Reconstruct a class signature, including base classes.
        """
        if node.name.startswith("_"):
            yield from []

        sig = node.name

        yield cls(
            module=parent_id,
            sig_type=SignatureType.CLASS,
            name=sig,
            arguments={_unparse(b) for b in node.bases} if node.bases else set(),
        )
        new_parent = parent_id + "." + node.name
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                yield from cls.function_signature(item, new_parent)
            elif isinstance(item, (ast.Assign, ast.AnnAssign)):
                yield from cls.assignment_signature(item, new_parent)

    @classmethod
    def assignment_signature(cls, node, parent_id=""):
        """
        Build a simple assignment signature by listing variable names.
        """
        if isinstance(node, ast.Assign):
            for t in node.targets:
                var_name = t.id if isinstance(t, ast.Name) else _unparse(t)
                if var_name.startswith("_"):
                    continue
                yield cls(
                    module=parent_id,
                    sig_type=SignatureType.ASSIGNMENT,
                    name=var_name,
                )
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                var_name = node.target.id
            else:
                var_name = _unparse(node.target)
            if not var_name.startswith("_"):
                yield cls(
                    module=parent_id,
                    sig_type=SignatureType.ASSIGNMENT,
                    name=var_name,
                )

    @classmethod
    @generate_to(set)
    def get_signatures(cls, source: str, module: str):
        tree = ast.parse(source)
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                yield from cls.function_signature(node, module)
            elif isinstance(node, ast.ClassDef):
                yield from cls.class_signature(node, module)
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                yield from cls.assignment_signature(node, module)


class EntryType(Enum):
    NEW = auto()
    OLD = auto()
    UPD_NAME = auto()
    UPD_ARGS = auto()

    def __str__(self):
        return self.name.title()


class Entry:
    def __init__(self, old_signature=None, new_signature=None):
        if old_signature is None and new_signature is None:
            msg = "Either old_signature or new_signature must be provided."
            raise ValueError(msg)
        if old_signature and new_signature and old_signature.sig_type != new_signature.sig_type:
            msg = "Old and new signatures must be of the same type."
            raise ValueError(msg)

        self.old_signature = old_signature
        self.new_signature = new_signature

        _logger.debug("Created Entry: %s", self)

    def __repr__(self):
        if self.old_signature is None:
            return f"Entry({self.new_signature})"
        if self.new_signature is None:
            return f"Entry({self.old_signature})"
        return f"Entry({self.old_signature} -> {self.new_signature})"

    @cached_property
    def sig_type(self):
        if self.old_signature is None:
            return self.new_signature.sig_type

        return self.old_signature.sig_type

    @cached_property
    def is_sig_type_class(self):
        return self.sig_type == SignatureType.CLASS

    @cached_property
    def type(self):
        if self.old_signature is None:
            return EntryType.NEW

        if self.new_signature is None:
            return EntryType.OLD

        if self.old_signature.name != self.new_signature.name:
            return EntryType.UPD_NAME

        return EntryType.UPD_ARGS

    @cached_property
    def new_module(self):
        if self.new_signature is None:
            return None

        return self.new_signature.module

    @cached_property
    def old_module(self):
        if self.old_signature is None:
            return None

        return self.old_signature.module

    @cached_property
    def new_name(self):
        if self.new_signature is None:
            return None

        return self.new_signature.name

    @cached_property
    def old_name(self):
        if self.old_signature is None:
            return None

        return self.old_signature.name

    @cached_property
    def new_args(self):
        if self.type == EntryType.NEW:
            return self.new_signature.arguments
        if self.type == EntryType.UPD_ARGS:
            return self.new_signature.arguments - self.old_signature.arguments
        return None

    @cached_property
    def old_args(self):
        if self.type == EntryType.OLD:
            return self.old_signature.arguments
        if self.type == EntryType.UPD_ARGS:
            return self.old_signature.arguments - self.new_signature.arguments
        return None

    def is_included(self, entries):
        if self.type == EntryType.NEW:
            return any(
                self.new_signature.is_included(entry.new_signature) for entry in entries if entry.type == EntryType.NEW
            )
        if self.type == EntryType.OLD:
            return any(
                self.old_signature.is_included(entry.old_signature) for entry in entries if entry.type == EntryType.OLD
            )
        return False

    @classmethod
    def create_new(cls, signature):
        return cls(new_signature=signature)

    @classmethod
    def create_old(cls, signature):
        return cls(old_signature=signature)

    @classmethod
    @generate_to(set)
    def map_entries(cls, old_signatures: set[SignatureItem], new_signatures: set[SignatureItem]):
        dif_signatures_new = (new_signatures - old_signatures)
        diff_signatures_old = (old_signatures - new_signatures)

        while dif_signatures_new:
            new_sig = dif_signatures_new.pop()
            for old_sig in diff_signatures_old:
                if new_sig.is_renamed(old_sig):
                    diff_signatures_old.remove(old_sig)
                    yield Entry(new_sig, old_sig)
                    break
                if new_sig.is_args_changed(old_sig):
                    diff_signatures_old.remove(old_sig)
                    yield Entry(old_sig, new_sig)
                    break
            yield Entry.create_new(new_sig)

        yield from map(Entry.create_old, diff_signatures_old)


class ChagelogAPI:
    def __init__(self, api_items):
        self._api_items = api_items

    def check(self, entry):
        if entry.type == EntryType.NEW:
            return any(entry.new_module in item and entry.new_name in item for item in self._api_items)
        if entry.type == EntryType.OLD:
            return any(entry.old_module in item and entry.old_name in item for item in self._api_items)
        if entry.type == EntryType.UPD_NAME:
            return any(entry.old_module in item and entry.old_name and entry.new_name in item for item in self._api_items)

        # EntryType.UPD_ARGS
        test_args = lambda item: all(arg in item for arg in entry.new_args | entry.old_args)
        return any(entry.new_module in item and entry.new_name in item and test_args(item) for item in self._api_items)

    def get_missing(self, entries: set[Entry]):
        classes = filter(lambda x: x.is_sig_type_class, entries)

        pool = ThreadPoolExecutor()

        class_in_chagelog = [
            entry for (check, entry) in pool.map(lambda x: (self.check(x), x), classes) if check
        ]

        _logger.debug("Classes in chagelog: %s", class_in_chagelog)

        def not_class_items(entry):
            return not entry.is_included(class_in_chagelog)

        not_included_in_class = filter(not_class_items, entries)

        return (
            entry for (check, entry) in pool.map(lambda x: (self.check(x), x), not_included_in_class) if not check
        )

    @classmethod
    def from_file(cls, filename, version):
        try:
            chagelog_text = filename.read_text(encoding="utf-8")
        except (ValueError, OSError) as e:
            sys.stderr.write(f"Error reading chagelog file: {e}\n")
            return None

        version_header_re = rf"##\s+Version\s+{re.escape(version)}"
        version_match = re.search(version_header_re, chagelog_text)
        if not version_match:
            sys.stderr.write(f"Could not find a chagelog section for version {version}.\n")
            return None

        start = version_match.end()
        next_section_match = re.search(r"\n##\s+", chagelog_text[start:])
        end = start + next_section_match.start() if next_section_match else len(chagelog_text)
        version_section = chagelog_text[start:end]
        api_header_match = re.search(r"###\s+API changes\s*(?:\n|-)+", version_section)
        if not api_header_match:
            sys.stderr.write(f"Could not find a '### API changes' section in version {current_version}.\n")
            return None
        api_start = api_header_match.end()
        next_subsec_match = re.search(r"\n###\s+", version_section[api_start:])
        api_end = api_start + next_subsec_match.start() if next_subsec_match else len(version_section)
        api_section = version_section[api_start:api_end].strip()

        api_items = []
        current_item = []
        for line in api_section.splitlines():
            if re.match(r"^\s*\*\s+", line):
                if current_item:
                    api_items.append("\n".join(current_item).strip())
                current_item = [line]
            else:
                current_item.append(line)
        if current_item:
            api_items.append("\n".join(current_item).strip())

        return cls(api_items)

    @staticmethod
    def format_missing_item(entry):
        if entry.type in {EntryType.NEW, EntryType.OLD}:
            return (
                f"{entry.type} API `{entry.new_signature or entry.old_signature}` missing in changelog:\n"
                f" - `{entry.new_module or entry.old_module}` mention not found.\n"
                f" - `{entry.new_name or entry.old_name}` mention not found.\n"
            )
        if entry.type == EntryType.UPD_NAME:
            return (
                f"Updated API `{entry.old_signature} -> {entry.new_signature}` missing in changelog:\n"
                f" - `{entry.new_module}` mention not found.\n"
                f" - `{entry.old_name}` mention not found.\n"
                f" - `{entry.new_name}` mention not found.\n"
            )

        msg = (
            f"Updated API `{entry.old_signature} -> {entry.new_signature}` missing in changelog:\n"
            f" - `{entry.new_module}` mention not found.\n"
            f" - `{entry.new_name}` mention not found.\n"
        )
        for arg in entry.new_args | entry.old_args:
            msg += f" - `{arg}` mention not found.\n"

        return msg


_HDR_PAT = re.compile(r"^@@ -(\d+),?(\d+)? \+(\d+),?(\d+)? @@$")


def apply_patch(diff, *, revert=False):
    p = diff.splitlines(keepends=True)

    i = 0
    while i < len(p) + 1 and p[i].startswith("---"):
        i += 1

    filename = Path(p[i - 1][6:])
    file = filename.read_text(encoding="utf-8")
    s = file.splitlines(keepends=True)

    i += 2
    t = ""
    sl = 0
    (midx, sign) = (1, "+") if not revert else (3, "-")
    while i < len(p):
        m = _HDR_PAT.match(p[i])
        if not m:
            msg = "Cannot process diff"
            raise RuntimeError(msg)
        i += 1
        l = int(m.group(midx)) - 1 + (m.group(midx + 1) == "0")
        t += "".join(s[sl:l])
        sl = l
        while i < len(p) and p[i][0] != "@":
            if i + 1 < len(p) and p[i + 1][0] == "\\":
                line = p[i][:-1]
                i += 2
            else:
                line = p[i]
                i += 1
            if len(line) > 0:
                if line[0] == sign or line[0] == " ":
                    t += line[1:]
                sl += line[0] != sign
    t += "".join(s[sl:])
    return t, file, filename


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Compare API signatures between a base file and an updated file and check changes against the chagelog."
    )
    parser.add_argument(
        "diff",
        nargs="?",
        type=argparse.FileType("r", encoding="utf-8"),
        default=sys.stdin,
        help="Path to git diff file (default: STDIN)",
    )
    parser.add_argument(
        "--chagelog",
        default=get_current_changelog(),
        type=Path,
        help="Path to the changelog file (e.g. CHANGELOG.md).",
    )
    parser.add_argument(
        "--version",
        default=get_current_version(),
        type=str,
        help="Version to check in the changelog.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser.parse_args()


def main():
    args = parse_arguments()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    if args.version is None:
        sys.stdout.write("Skipping pre-release version.\n")
        sys.exit(0)

    old_file, new_file, filename = apply_patch(args.diff.read(), revert=True)

    module = ".".join([*filename.parts[:-1], filename.stem])

    old_signatures = SignatureItem.get_signatures(old_file, module)
    new_signatures = SignatureItem.get_signatures(new_file, module)

    entries = Entry.map_entries(old_signatures, new_signatures)

    if not entries:
        sys.stdout.write("No public API changes detected.\n")
        sys.exit(0)

    changelog = ChagelogAPI.from_file(args.chagelog, args.version)
    if changelog is None:
        sys.exit(1)

    missing_entries = changelog.get_missing(entries)

    try:
        first_missing_entry = next(missing_entries)
    except StopIteration:
        sys.stdout.write("All public API changes are properly logged in the chagelog.\n")
        sys.exit(0)

    sys.stdout.write(changelog.format_missing_item(first_missing_entry))

    for item in missing_entries:
        sys.stdout.write(changelog.format_missing_item(item))

    sys.exit(1)


if __name__ == "__main__":
    main()
