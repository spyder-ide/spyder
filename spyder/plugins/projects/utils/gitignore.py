# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Matching of paths against gitignore patterns."""

from __future__ import annotations

# Standard lib imports
from collections.abc import Iterable, Sequence
from enum import Enum
import logging
import os
from pathlib import Path
import re
import sys
from typing import Literal, NamedTuple

logger = logging.getLogger(__name__)

# Git matches case-insensitively by default on these systems (core.ignorecase)
_FLAGS = re.DOTALL | (
    re.IGNORECASE if os.name == "nt" or sys.platform == "darwin" else 0
)


class GitignorePattern(NamedTuple):
    """A gitignore pattern, see `parse_gitignore`."""

    regex: str
    negate: bool
    dir_only: bool


def _translate_bracket(glob: str, i: int) -> tuple[str, int]:
    """
    Translate the bracket expression that starts after the "[" at
    `glob[i - 1]`, returning the regex and the index after its "]".
    """
    n = len(glob)
    negate = glob[i:i + 1] in ("!", "^")
    if negate:
        i += 1

    chars: list[str] = []
    while True:
        if i == n:
            raise ValueError("unclosed [")
        c = glob[i]
        if c == "]" and chars:
            break
        if c == "\\":
            i += 1
            if i == n:
                raise ValueError("unclosed [")
            chars.append(re.escape(glob[i]))
        elif c == "-" and chars and glob[i + 1:i + 2] not in ("]", ""):
            chars.append("-")
        else:
            chars.append(re.escape(c))
        i += 1

    body = "".join(chars)
    return (f"[^{body}/]" if negate else f"(?!/)[{body}]"), i + 1


def _strip_trailing_spaces(line: str) -> str:
    """Remove the trailing spaces not escaped with a backslash."""
    end = i = 0
    while i < len(line):
        if line[i] == "\\":
            i = end = min(i + 2, len(line))
        else:
            i += 1
            if line[i - 1] != " ":
                end = i
    return line[:end]


class _Wildcard(Enum):
    STAR = "*"
    GLOBSTAR = "**"


_Token = str | Literal[_Wildcard.STAR]
_Component = list[_Token] | Literal[_Wildcard.GLOBSTAR]


def _split_components(glob: str) -> list[_Component]:
    """
    Split a glob into path components, each a list of single-character
    regexes and `_Wildcard.STAR`, or `_Wildcard.GLOBSTAR` for a "**"
    component.
    """
    tokens: list[_Token] = []
    components: list[_Component] = [tokens]
    i, n = 0, len(glob)
    while i < n:
        c = glob[i]
        i += 1
        if c == "/":
            tokens = []
            components.append(tokens)
        elif c == "*":
            start = i - 1
            while glob[i:i + 1] == "*":
                i += 1
            if (
                i - start == 2
                and not tokens
                and (i == n or glob[i] == "/")
            ):
                components[-1] = _Wildcard.GLOBSTAR
            elif not tokens or tokens[-1] is not _Wildcard.STAR:
                tokens.append(_Wildcard.STAR)
        elif c == "?":
            tokens.append("[^/]")
        elif c == "[":
            bracket_regex, i = _translate_bracket(glob, i)
            tokens.append(bracket_regex)
        elif c == "\\":
            if i == n:
                raise ValueError("trailing backslash")
            tokens.append(re.escape(glob[i]))
            i += 1
        else:
            tokens.append(re.escape(c))

    return components


def _translate_component(tokens: Iterable[_Token]) -> str:
    chunks: list[list[str]] = [[]]
    for token in tokens:
        if token is _Wildcard.STAR:
            chunks.append([])
        else:
            chunks[-1].append(token)

    regex = "".join(chunks[0])
    if len(chunks) > 1:
        # Taking the leftmost match of each chunk between two stars is always
        # right, so atomic groups can rule out backtracking, which is
        # exponential in the number of stars.
        for chunk in chunks[1:-1]:
            regex += f"(?>[^/]*?{''.join(chunk)})"
        regex += "[^/]*" + "".join(chunks[-1])
    return regex


def translate_glob(glob: str) -> str:
    """
    Translate a gitignore glob to a regular expression.

    Raises ValueError for globs git never matches.
    """
    # Components between "**" components
    groups: list[list[str]] = [[]]
    for component in _split_components(glob):
        if component is _Wildcard.GLOBSTAR:
            if len(groups) == 1 or groups[-1]:
                groups.append([])
        else:
            groups[-1].append(_translate_component(component))

    regex = "/".join(groups[0])
    last = len(groups) - 1
    for k, group in enumerate(groups[1:], 1):
        if not group:
            regex += "/.*" if regex else ".*"
            continue

        # As with stars within a component, the leftmost match of a group
        # between two "**" is always right.
        group_regex = "(?:[^/]*/)*?" + "/".join(group)
        if k < last:
            group_regex = f"(?>{group_regex}(?=/))"
        regex += ("/" if regex else "") + group_regex

    return regex


def parse_gitignore(
    lines: Iterable[str], prefix: str = ""
) -> list[GitignorePattern]:
    """
    Parse the lines of a gitignore file.

    Parameters
    ----------
    lines: iterable of str
        Lines of the file.
    prefix: str
        Path of the file's folder relative to the folder paths will be matched
        against, with a trailing "/" (empty if it's the same folder).

    Returns
    -------
    list of GitignorePattern
        (regex, negate, dir_only) for each pattern, in file order. The
        regexes match "<name>\\0<path>", where <path> is relative to the
        folder paths are matched against and <name> is its last component.
    """
    patterns: list[GitignorePattern] = []
    for line in lines:
        line = _strip_trailing_spaces(line.rstrip("\r\n"))
        if not line or line.startswith("#"):
            continue

        negate = line.startswith("!")
        if negate:
            line = line[1:]

        dir_only = line.endswith("/")
        if dir_only:
            line = line[:-1]

        anchored = "/" in line
        if line.startswith("/"):
            line = line[1:]
        if not line:
            continue

        # Unanchored patterns match the name only, not every path level
        try:
            if anchored:
                regex = (
                    r"[^\0]*\0" + re.escape(prefix) + translate_glob(line)
                )
            else:
                regex = translate_glob(line) + r"\0.*"
            re.compile(regex, _FLAGS)
        except (ValueError, re.error) as error:
            logger.warning(f"Skipping gitignore pattern {line!r}: {error}")
            continue

        patterns.append(GitignorePattern(regex, negate, dir_only))

    return patterns


def read_gitignore(
    path: str | os.PathLike[str], prefix: str = ""
) -> list[GitignorePattern]:
    """Parse a gitignore file, see `parse_gitignore`."""
    try:
        with open(path, encoding="utf-8-sig", errors="surrogateescape") as f:
            return parse_gitignore(f, prefix)
    except OSError as error:
        logger.debug(f"Could not read {path}: {error}")
        return []


class GitignoreRules:
    """
    Gitignore patterns, with later patterns taking precedence as in git.

    All patterns are combined in a single regular expression, so matching
    takes one regex search regardless of how many patterns there are.
    """

    def __init__(self, patterns: Iterable[GitignorePattern] = ()):
        self.patterns = tuple(patterns)
        self._dir_regex, self._dir_negate = self._compile(self.patterns)
        self._file_regex, self._file_negate = self._compile(
            [p for p in self.patterns if not p.dir_only]
        )

    @staticmethod
    def _compile(
        patterns: Sequence[GitignorePattern],
    ) -> tuple[re.Pattern[str] | None, tuple[bool | None, ...]]:
        if not patterns:
            return None, ()

        # With fullmatch, the first alternative that matches wins, so they're
        # listed from the last pattern to the first.
        patterns = patterns[::-1]
        regex = re.compile("|".join(f"({p.regex})" for p in patterns), _FLAGS)
        return regex, (None, *(p.negate for p in patterns))

    def extended(
        self, patterns: Iterable[GitignorePattern]
    ) -> GitignoreRules:
        """Return new rules with `patterns` taking precedence over these."""
        return GitignoreRules(self.patterns + tuple(patterns))

    def ignores(self, path: str, is_dir: bool) -> bool:
        """
        Check if `path`, relative to the folder the patterns were parsed for
        and with "/" as separator, is ignored.
        """
        if is_dir:
            regex, negate = self._dir_regex, self._dir_negate
        else:
            regex, negate = self._file_regex, self._file_negate

        if regex is None:
            return False

        name = path.rpartition("/")[2]
        match = regex.fullmatch(f"{name}\0{path}")
        if match is None:
            return False
        assert match.lastindex is not None
        return not negate[match.lastindex]


def find_repository_root(path: str | os.PathLike[str]) -> Path | None:
    """Return the closest folder at or above `path` with a .git entry."""
    path = Path(path).resolve()
    for folder in (path, *path.parents):
        if (folder / ".git").exists():
            return folder
    return None
