"""Sprachdateien: gleich in jeder Sprache, und benutzt.

Der Vertrag ist einfach: eine neue Sprache ist eine neue Datei in
`scrinium/sprache/`, sonst wird nichts angefasst. Das schuetzt nur, wenn
alle Sprachdateien dieselben Schluessel haben - das prueft dieser Test.
"""

from __future__ import annotations

import os

import pytest

from scrinium import texte


@pytest.fixture(autouse=True)
def zurueck():
    texte.sprache_setzen("de")
    yield
    texte.sprache_setzen("de")


def test_de_und_en_sind_da():
    assert set(texte.sprachen()) == {"de", "en"}


def test_sprachen_haben_dieselben_schluessel():
    texte.sprache_setzen("de")
    de = set(texte.alle_schluessel())
    texte.sprache_setzen("en")
    en = set(texte.alle_schluessel())
    assert de == en, (
        f"nur in de: {sorted(de - en)}\n"
        f"nur in en: {sorted(en - de)}"
    )


@pytest.mark.parametrize("schluessel", [
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
def test_wichtiger_schluessel_in_beiden_sprachen(schluessel):
    texte.sprache_setzen("de")
    de = texte.sag(schluessel)
    texte.sprache_setzen("en")
    en = texte.sag(schluessel)
    assert de != schluessel, f"{schluessel} fehlt auf Deutsch"
    assert en != schluessel, f"{schluessel} fehlt auf Englisch"


def test_platzhalter_werden_ersetzt():
    texte.sprache_setzen("de")
    assert "3" in texte.sag("downloadsorter.fertig", anzahl=3)
    texte.sprache_setzen("en")
    assert "3" in texte.sag("downloadsorter.fertig", anzahl=3)


def test_sprache_wechselt_den_text():
    texte.sprache_setzen("de")
    de = texte.sag("fenster.werkzeuge")
    texte.sprache_setzen("en")
    en = texte.sag("fenster.werkzeuge")
    assert de != en


def test_unbekannte_sprache_aendert_nichts():
    texte.sprache_setzen("de")
    vorher = texte.sag("fenster.werkzeuge")
    assert texte.sprache_setzen("xyz") == "de"
    assert texte.sag("fenster.werkzeuge") == vorher


def test_fehlender_schluessel_ist_sichtbar():
    """Kein stiller Ersatztext - man soll den Schluessel sehen."""
    assert texte.sag("gibt.es.nicht") == "gibt.es.nicht"


def test_platzhalter_ohne_angabe_knallt_nicht():
    assert isinstance(texte.sag("downloadsorter.fertig"), str)


def test_kaputte_platzhalter_knallen_nicht():
    texte.sprache_setzen("de")
    # falscher Platzhalter -> Text kommt trotzdem zurueck
    out = texte.sag("downloadsorter.fertig", falsch=1)
    assert isinstance(out, str) and out


def test_moechte_nur_vorhandene_sprachen():
    assert texte.sprache() in texte.sprachen()