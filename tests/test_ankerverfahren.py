"""Tests fuer ankerverfahren.py (Auftrag 2026-08-06).

Kein Netz, keine Schluessel des Betreibers -- der Selbsttest in
ankerverfahren.py selbst deckt bereits alles ab; diese Datei spiegelt
dieselben Faelle als pytest, damit sie in der Suite auftauchen
(`python3 -m pytest shared-knowledge/tests/ -q`), plus ein paar
Grenzfaelle extra.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import ankerverfahren as av  # type: ignore  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402
from cryptography.hazmat.primitives.serialization import (  # noqa: E402
    Encoding,
    NoEncryption,
    PrivateFormat,
)

BEREICH = {"von": 1, "bis": 4, "n": 4}
ZEIT = "2026-08-06T00:00:00+02:00"


# ─── RFC 3161: DER-Bau gegen unabhaengige Referenz (openssl ts -query) ──

def test_rfc3161_anfrage_matches_openssl_reference():
    # echo "testroot123" > x; openssl ts -query -data x -sha256 -no_nonce -cert -out x.tsq
    referenz_hex = (
        "30390201013031300d0609608648016503040201050004207ec49d9763530f"
        "5bea688883d86c5cdcc31d36bf4b4cb81b9cdec066eb4a2ff10101ff"
    )
    hashed = hashlib.sha256(b"testroot123\n").digest()
    assert av.rfc3161_anfrage_der(hashed).hex() == referenz_hex


def test_rfc3161_rejects_non_sha256_length():
    with pytest.raises(ValueError):
        av.rfc3161_anfrage_der(b"zu kurz")


def test_rfc3161_beleg_ist_trocken_ohne_schalter():
    beleg = av.rfc3161_beleg("aaaa", BEREICH, ZEIT)
    assert beleg["modus"] == "trocken"
    assert beleg["antwort_der_hex"] is None


def test_rfc3161_pruefe_passt_zur_eigenen_wurzel():
    beleg = av.rfc3161_beleg("aaaa", BEREICH, ZEIT)
    assert av.rfc3161_pruefe(beleg, "aaaa", BEREICH)


def test_rfc3161_pruefe_gegenprobe_andere_wurzel():
    beleg = av.rfc3161_beleg("aaaa", BEREICH, ZEIT)
    assert not av.rfc3161_pruefe(beleg, "bbbb", BEREICH)


def test_rfc3161_pruefe_gegenprobe_anderer_bereich():
    beleg = av.rfc3161_beleg("aaaa", BEREICH, ZEIT)
    assert not av.rfc3161_pruefe(beleg, "aaaa", {"von": 5, "bis": 8, "n": 4})


# ─── Gegenzeichnung ──────────────────────────────────────────────────────

def test_gegenzeichnung_ist_trocken_ohne_schalter():
    beleg = av.gegenzeichnung_beleg("cccc", BEREICH, ZEIT)
    assert beleg["modus"] == "trocken"
    assert beleg["signatur_hex"] is None


def test_gegenzeichnung_signieren_ohne_schluessel_wirft():
    with pytest.raises(ValueError):
        av.gegenzeichnung_beleg("cccc", BEREICH, ZEIT, signieren=True)


@pytest.fixture()
def testschluessel_pem() -> bytes:
    """NUR fuer diesen Test erzeugt -- niemals ein Schluessel des
    Betreibers, siehe Grenzen im Auftrag."""
    schluessel = Ed25519PrivateKey.generate()
    return schluessel.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())


def test_gegenzeichnung_signiert_und_prueft(testschluessel_pem):
    beleg = av.gegenzeichnung_beleg(
        "cccc", BEREICH, ZEIT, private_key_pem=testschluessel_pem, signieren=True
    )
    assert beleg["modus"] == "signiert"
    assert av.gegenzeichnung_pruefe(beleg, "cccc", BEREICH, ZEIT)


def test_gegenzeichnung_gegenprobe_andere_wurzel(testschluessel_pem):
    beleg = av.gegenzeichnung_beleg(
        "cccc", BEREICH, ZEIT, private_key_pem=testschluessel_pem, signieren=True
    )
    assert not av.gegenzeichnung_pruefe(beleg, "dddd", BEREICH, ZEIT)


def test_gegenzeichnung_gegenprobe_anderer_zeitstempel(testschluessel_pem):
    beleg = av.gegenzeichnung_beleg(
        "cccc", BEREICH, ZEIT, private_key_pem=testschluessel_pem, signieren=True
    )
    assert not av.gegenzeichnung_pruefe(beleg, "cccc", BEREICH, "2099-01-01T00:00:00+02:00")


def test_gegenzeichnung_gegenprobe_manipulierte_signatur(testschluessel_pem):
    beleg = av.gegenzeichnung_beleg(
        "cccc", BEREICH, ZEIT, private_key_pem=testschluessel_pem, signieren=True
    )
    manipuliert = dict(beleg)
    manipuliert["signatur_hex"] = "00" * 64
    assert not av.gegenzeichnung_pruefe(manipuliert, "cccc", BEREICH, ZEIT)


def test_gegenzeichnung_falscher_schluesseltyp_wirft():
    from cryptography.hazmat.primitives.asymmetric import rsa

    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = rsa_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    with pytest.raises(ValueError):
        av.gegenzeichnung_beleg("cccc", BEREICH, ZEIT, private_key_pem=pem, signieren=True)


# ─── generischer Einstieg ────────────────────────────────────────────────

def test_baue_und_pruefe_beleg_generisch(testschluessel_pem):
    beleg = av.baue_beleg(
        "gegenzeichnung", "eeee", BEREICH, ZEIT,
        private_key_pem=testschluessel_pem, signieren=True,
    )
    assert av.pruefe_beleg(beleg, "eeee", BEREICH, ZEIT)
    assert not av.pruefe_beleg(beleg, "ffff", BEREICH, ZEIT)


def test_baue_beleg_unbekanntes_verfahren_wirft():
    with pytest.raises(ValueError):
        av.baue_beleg("carrier-pigeon", "x", BEREICH, ZEIT)


def test_pruefe_beleg_unbekanntes_verfahren_wirft():
    with pytest.raises(ValueError):
        av.pruefe_beleg({"verfahren": "carrier-pigeon"}, "x", BEREICH, ZEIT)


# ─── Vergleichstabelle ────────────────────────────────────────────────────

def test_vergleichstabelle_hat_beweist_nicht_je_verfahren():
    for row in av.VERGLEICHSTABELLE:
        assert row["beweist_nicht"].strip()


def test_verfahren_info_hat_beweist_nicht_je_verfahren():
    for info in (av.RFC3161_INFO, av.GEGENZEICHNUNG_INFO):
        assert info.beweist_nicht
