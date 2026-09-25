# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Programming languages known to Spyder.

:class:`Language` is the single source of truth for language names, file
extensions and LSP ``languageId`` values. External plugins register new
languages at runtime with :meth:`Language.register`.
"""

from __future__ import annotations

# Standard library imports
import os.path as osp
from dataclasses import dataclass
from enum import Enum
from typing import Any

# Local imports
from spyder.plugins.languageservices.api.errors import (
    LanguageAlreadyRegisteredError,
    UnknownLanguageError,
)


@dataclass(frozen=True)
class LanguageSpec:
    """Static description of a programming language."""

    name: str
    """Display name, e.g. ``"Python"``. Unique (case-insensitive)."""

    extensions: tuple[str, ...]
    """Lowercase file extensions without the dot. Each one is unique."""

    language_id: str
    """LSP ``languageId``. Shared between languages served by the same
    servers (``IPYTHON`` and ``PYTHON`` both use ``"python"``)."""

    def __post_init__(self):
        if not self.name:
            raise ValueError("A language needs a non-empty name")
        if not self.language_id:
            raise ValueError(f"Language {self.name!r} needs a language_id")
        normalized = tuple(ext.lower().lstrip(".") for ext in self.extensions)
        if any(not ext for ext in normalized):
            raise ValueError(
                f"Language {self.name!r} has an empty file extension"
            )
        if len(set(normalized)) != len(normalized):
            raise ValueError(
                f"Language {self.name!r} lists an extension twice"
            )
        object.__setattr__(self, "extensions", normalized)


class Language(Enum):
    """Programming language known to Spyder.

    Members can be added at runtime with :meth:`register`. All lookups are
    served from indexes rebuilt on every registration.
    """

    PYTHON = LanguageSpec(
        "Python", ("py", "pyw", "python", "pyt", "pyi"), "python"
    )
    IPYTHON = LanguageSpec("IPython", ("ipy", "ipython"), "python")
    CYTHON = LanguageSpec("Cython", ("pyx", "pxi", "pxd"), "cython")
    ENAML = LanguageSpec("Enaml", ("enaml",), "enaml")
    FORTRAN77 = LanguageSpec("Fortran77", ("f", "for", "f77"), "fortran77")
    FORTRAN = LanguageSpec(
        "Fortran", ("f90", "f95", "f2k", "f03", "f08"), "fortran"
    )
    IDL = LanguageSpec("Idl", ("pro",), "idl")
    DIFF = LanguageSpec("Diff", ("diff", "patch", "rej"), "diff")
    GETTEXT = LanguageSpec("GetText", ("po", "pot"), "gettext")
    NSIS = LanguageSpec("Nsis", ("nsi", "nsh"), "nsis")
    HTML = LanguageSpec("Html", ("htm", "html"), "html")
    CPP = LanguageSpec(
        "Cpp", ("c", "cc", "cpp", "cxx", "h", "hh", "hpp", "hxx"), "cpp"
    )
    OPENCL = LanguageSpec("OpenCL", ("cl",), "opencl")
    YAML = LanguageSpec("Yaml", ("yaml", "yml"), "yaml")
    MARKDOWN = LanguageSpec("Markdown", ("md", "mdw", "pyz"), "markdown")

    BASH = LanguageSpec("Bash", ("sh", "bash"), "shellscript")
    CSHARP = LanguageSpec("C#", ("cs",), "csharp")
    CSS = LanguageSpec("CSS/LESS/SASS", ("css", "less", "sass", "scss"), "css")
    GO = LanguageSpec("Go", ("go",), "go")
    GRAPHQL = LanguageSpec("GraphQL", ("graphql", "gql"), "graphql")
    GROOVY = LanguageSpec("Groovy", ("groovy", "gvy", "gy", "gsh"), "groovy")
    ELIXIR = LanguageSpec("Elixir", ("ex", "exs"), "elixir")
    ERLANG = LanguageSpec("Erlang", ("erl", "hrl"), "erlang")
    HAXE = LanguageSpec("Haxe", ("hx", "hxml"), "haxe")
    JAVA = LanguageSpec("Java", ("java",), "java")
    JAVASCRIPT = LanguageSpec(
        "JavaScript", ("js", "mjs", "cjs", "jsx"), "javascript"
    )
    JSON = LanguageSpec("JSON", ("json", "jsonc"), "json")
    JULIA = LanguageSpec("Julia", ("jl",), "julia")
    KOTLIN = LanguageSpec("Kotlin", ("kt", "kts"), "kotlin")
    OCAML = LanguageSpec("OCaml", ("ml", "mli"), "ocaml")
    PHP = LanguageSpec("PHP", ("php", "phtml"), "php")
    R = LanguageSpec("R", ("r", "rmd"), "r")
    RUST = LanguageSpec("Rust", ("rs",), "rust")
    SCALA = LanguageSpec("Scala", ("scala", "sc"), "scala")
    SWIFT = LanguageSpec("Swift", ("swift",), "swift")
    TYPESCRIPT = LanguageSpec("TypeScript", ("ts", "tsx"), "typescript")

    # ---- Properties ---------------------------------------------------------
    @property
    def name(self) -> str:  # type: ignore[override]
        """Display name of the language."""
        return self.value.name

    @property
    def extensions(self) -> tuple[str, ...]:
        """Lowercase file extensions (without dot) of the language."""
        return self.value.extensions

    @property
    def language_id(self) -> str:
        """LSP ``languageId`` of the language."""
        return self.value.language_id

    # ---- Registration -------------------------------------------------------
    @classmethod
    def register(
        cls,
        name: str,
        extensions: tuple[str, ...] | list[str],
        language_id: str,
    ) -> Language:
        """Add a new language at runtime.

        Parameters
        ----------
        name: str
            Display name, unique among all languages (case-insensitive).
        extensions: tuple[str, ...]
            File extensions (with or without a leading dot).
        language_id: str
            LSP ``languageId``. May be shared with existing languages.

        Returns
        -------
        Language
            The new member.

        Raises
        ------
        LanguageAlreadyRegisteredError
            If ``name`` or any extension is already taken.
        """
        spec = LanguageSpec(name, tuple(extensions), language_id)
        indexes = cls.__indexes()
        if spec.name.lower() in indexes["by_name"]:
            raise LanguageAlreadyRegisteredError(
                f"A language named {spec.name!r} already exists"
            )
        for ext in spec.extensions:
            if ext in indexes["by_extension"]:
                owner = indexes["by_extension"][ext]
                raise LanguageAlreadyRegisteredError(
                    f"Extension {ext!r} already belongs to {owner.name!r}"
                )

        member_name = _member_identifier(spec.name)
        if member_name in cls._member_map_:
            raise LanguageAlreadyRegisteredError(
                f"Member identifier {member_name!r} already exists"
            )

        member = object.__new__(cls)
        member._value_ = spec
        member._name_ = member_name
        member.__objclass__ = cls
        member.__init__(spec)

        cls._member_map_[member_name] = member
        cls._member_names_.append(member_name)
        cls._value2member_map_[spec] = member
        type.__setattr__(cls, member_name, member)
        cls.__rebuild_indexes()
        return member

    # ---- Lookups ------------------------------------------------------------
    @classmethod
    def from_name(cls, name: str) -> Language:
        """Return the language called ``name`` (case-insensitive)."""
        language = cls.__indexes()["by_name"].get(name.lower())
        if language is None:
            raise UnknownLanguageError(f"Unknown language name: {name!r}")
        return language

    @classmethod
    def from_extension(cls, extension: str) -> Language:
        """Return the language owning ``extension`` (dot optional)."""
        key = extension.lower().lstrip(".")
        language = cls.__indexes()["by_extension"].get(key)
        if language is None:
            raise UnknownLanguageError(
                f"No language uses the extension {extension!r}"
            )
        return language

    @classmethod
    def from_filename(cls, filename: str) -> Language:
        """Return the language of ``filename`` based on its extension."""
        _, ext = osp.splitext(filename)
        if not ext:
            raise UnknownLanguageError(
                f"{filename!r} has no extension to infer a language from"
            )
        return cls.from_extension(ext)

    @classmethod
    def from_language_id(cls, language_id: str) -> frozenset[Language]:
        """Return every language using the LSP ``language_id``."""
        languages = cls.__indexes()["by_language_id"].get(language_id)
        if not languages:
            raise UnknownLanguageError(
                f"No language uses the language_id {language_id!r}"
            )
        return languages

    @classmethod
    def find(
        cls,
        *,
        name: str | None = None,
        extension: str | None = None,
        filename: str | None = None,
        language_id: str | None = None,
    ) -> Language | None:
        """Look a language up by exactly one key, returning ``None`` on miss.

        ``language_id`` resolves to the language whose name equals the id
        (case-insensitive) when several share it, else to the only match.
        """
        keys = {
            "name": name,
            "extension": extension,
            "filename": filename,
            "language_id": language_id,
        }
        given = [key for key, value in keys.items() if value is not None]
        if len(given) != 1:
            raise TypeError(
                "Language.find() takes exactly one lookup key, got "
                f"{given or 'none'}"
            )
        try:
            if name is not None:
                return cls.from_name(name)
            if extension is not None:
                return cls.from_extension(extension)
            if filename is not None:
                return cls.from_filename(filename)
            candidates = cls.from_language_id(language_id)
        except UnknownLanguageError:
            return None
        if len(candidates) == 1:
            return next(iter(candidates))
        for candidate in candidates:
            if candidate.name.lower() == language_id.lower():
                return candidate
        return None

    # ---- Indexes ------------------------------------------------------------
    @classmethod
    def __indexes(cls) -> dict[str, dict[str, Any]]:
        indexes = cls.__dict__.get("_Language__index_cache")
        if indexes is None:
            indexes = cls.__rebuild_indexes()
        return indexes

    @classmethod
    def __rebuild_indexes(cls) -> dict[str, dict[str, Any]]:
        by_name: dict[str, Language] = {}
        by_extension: dict[str, Language] = {}
        by_language_id: dict[str, set[Language]] = {}
        for language in cls:
            by_name[language.name.lower()] = language
            for ext in language.extensions:
                by_extension[ext] = language
            by_language_id.setdefault(language.language_id, set()).add(
                language
            )
        indexes = {
            "by_name": by_name,
            "by_extension": by_extension,
            "by_language_id": {
                key: frozenset(value) for key, value in by_language_id.items()
            },
        }
        type.__setattr__(cls, "_Language__index_cache", indexes)
        return indexes

    def __repr__(self) -> str:
        return f"<Language.{self._name_}: {self.name!r}>"


def _member_identifier(name: str) -> str:
    """Derive an enum member identifier from a display name."""
    identifier = "".join(ch if ch.isalnum() else "_" for ch in name).upper()
    identifier = identifier.strip("_") or "LANGUAGE"
    if identifier[0].isdigit():
        identifier = f"LANG_{identifier}"
    return identifier
