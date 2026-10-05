"""Sprachdateien: gleich in jeder Sprache, und benutzt.

Der Vertrag ist einfach: eine neue Sprache ist eine neue Datei in
`scrinium/language/`, sonst wird nichts angefasst. Das schuetzt nur, wenn
alle Sprachdateien dieselben Schluessel haben - das prueft dieser Test.
"""

from __future__ import annotations

import os

import pytest

from scrinium import texts


@pytest.fixture(autouse=True)
def zurueck():
    texts.set_language("de")
    yield
    texts.set_language("de")


def test_de_and_en_present():
    assert set(texts.languages()) == {"de", "en"}


def test_languages_share_keys():
    texts.set_language("de")
    de = set(texts.all_keys())
    texts.set_language("en")
    en = set(texts.all_keys())
    assert de == en, (
        f"nur in de: {sorted(de - en)}\n"
        f"nur in en: {sorted(en - de)}"
    )


@pytest.mark.parametrize("key", [
    "fenster.titel",
    "fenster.werkzeuge",
    "fenster.keine_werkzeuge",
    "fenster.werkzeug_starten",
    "werkzeug.bereit",
    "werkzeug.ein",
    "werkzeug.aus",
    "downloadsorter.name",
    "downloadsorter.fertig",
    "downloadsorter.uebersprungen",
    "downloadsorter.rueckgaengig",
    "fehler.allgemein",
])
def test_important_key_in_both(key):
    texts.set_language("de")
    de = texts.sag(key)
    texts.set_language("en")
    en = texts.sag(key)
    assert de != key, f"{key} fehlt auf Deutsch"
    assert en != key, f"{key} fehlt auf Englisch"


def test_placeholders_replaced():
    texts.set_language("de")
    assert "3" in texts.sag("downloadsorter.fertig", anzahl=3)
    texts.set_language("en")
    assert "3" in texts.sag("downloadsorter.fertig", anzahl=3)


def test_language_switches_text():
    texts.set_language("de")
    de = texts.sag("fenster.werkzeuge")
    texts.set_language("en")
    en = texts.sag("fenster.werkzeuge")
    assert de != en


def test_unknown_language_noop():
    texts.set_language("de")
    vorher = texts.sag("fenster.werkzeuge")
    assert texts.set_language("xyz") == "de"
    assert texts.sag("fenster.werkzeuge") == vorher


def test_missing_key_is_visible():
    """Kein stiller Ersatztext - man soll den Schluessel sehen."""
    assert texts.sag("gibt.es.nicht") == "gibt.es.nicht"


def test_placeholder_without_arg_safe():
    assert isinstance(texts.sag("downloadsorter.fertig"), str)


def test_broken_placeholder_safe():
    texts.set_language("de")
    # falscher Platzhalter -> Text kommt trotzdem zurueck
    out = texts.sag("downloadsorter.fertig", falsch=1)
    assert isinstance(out, str) and out


def test_only_existing_languages():
    assert texts.language() in texts.languages()