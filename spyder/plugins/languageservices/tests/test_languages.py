# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for the Language enum."""

import pytest

from spyder.plugins.completion.api import SUPPORTED_LANGUAGES
from spyder.plugins.languageservices.api.errors import (
    LanguageAlreadyRegisteredError,
    UnknownLanguageError,
)
from spyder.plugins.languageservices.api.languages import (
    Language,
    LanguageSpec,
)


def test_members_expose_spec_fields():
    assert Language.PYTHON.name == "Python"
    assert Language.PYTHON.extensions == ("py", "pyw", "python", "pyt", "pyi")
    assert Language.PYTHON.language_id == "python"


def test_lookups():
    assert Language.from_name("python") is Language.PYTHON
    assert Language.from_extension(".PY") is Language.PYTHON
    assert Language.from_extension("ipy") is Language.IPYTHON
    assert Language.from_filename("/tmp/foo.pyx") is Language.CYTHON
    assert Language.from_language_id("python") == frozenset(
        {Language.PYTHON, Language.IPYTHON}
    )
    assert Language.from_language_id("rust") == frozenset({Language.RUST})


@pytest.mark.parametrize(
    "lookup",
    [
        lambda: Language.from_name("klingon"),
        lambda: Language.from_extension("kli"),
        lambda: Language.from_filename("noext"),
        lambda: Language.from_filename("x.kli"),
        lambda: Language.from_language_id("klingon"),
    ],
)
def test_lookup_failures_raise(lookup):
    with pytest.raises(UnknownLanguageError):
        lookup()


def test_find():
    assert Language.find(name="Python") is Language.PYTHON
    assert Language.find(extension="rs") is Language.RUST
    assert Language.find(filename="a.jl") is Language.JULIA
    assert Language.find(language_id="python") is Language.PYTHON
    assert Language.find(language_id="rust") is Language.RUST
    assert Language.find(name="klingon") is None
    with pytest.raises(TypeError):
        Language.find()
    with pytest.raises(TypeError):
        Language.find(name="Python", extension="py")


def test_register_adds_member():
    member = Language.register("Test Lang", (".tlang", "tl2"), "testlang")
    assert isinstance(member, Language)
    assert member is Language.TEST_LANG
    assert member is Language["TEST_LANG"]
    assert Language(member.value) is member
    assert member in list(Language)
    assert member.extensions == ("tlang", "tl2")
    assert Language.from_name("test lang") is member
    assert Language.from_extension("tl2") is member
    assert Language.from_language_id("testlang") == frozenset({member})


def test_register_rejects_clashes():
    with pytest.raises(LanguageAlreadyRegisteredError):
        Language.register("python", ("zzz",), "zzz")
    with pytest.raises(LanguageAlreadyRegisteredError):
        Language.register("Zzz", ("py",), "zzz")
    with pytest.raises(UnknownLanguageError):
        Language.from_extension("zzz")


def test_spec_validation():
    with pytest.raises(ValueError):
        LanguageSpec("", ("x",), "x")
    with pytest.raises(ValueError):
        LanguageSpec("X", ("x", "x"), "x")
    with pytest.raises(ValueError):
        LanguageSpec("X", ("",), "x")
    with pytest.raises(ValueError):
        LanguageSpec("X", ("x",), "")


def test_supported_languages_is_derived():
    assert "Python" not in SUPPORTED_LANGUAGES
    assert "IPython" not in SUPPORTED_LANGUAGES
    for name in ("Bash", "Cpp", "Fortran", "Html", "Rust", "TypeScript"):
        assert name in SUPPORTED_LANGUAGES
    assert SUPPORTED_LANGUAGES == sorted(SUPPORTED_LANGUAGES, key=str.lower)


def test_language_name_uniqueness():
    seen_names: dict[str, Language] = {}
    for language in Language:
        if language.name in seen_names:
            raise AssertionError(
                f"Language name {language.name!r} is not unique: "
                f"{language} and {seen_names[language.name]} both have it"
            )
        seen_names[language.name] = language
