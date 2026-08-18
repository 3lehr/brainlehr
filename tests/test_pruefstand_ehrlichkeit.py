"""Pruefstein zu L-0e0ab6 ("Der Pruefstand misst mit, und er ist nie die
Wirklichkeit") -- eskaliert 2026-08-15T10:05:00+0200, 7 Vorkommen, bis heute
reiner Text ohne Mechanismus (docs/PLAN_PRUEFSTEIN_PRUEFSTAND_2026-08-18.md).

Die sieben Vorkommen haben verschiedene Symptome und lassen sich nicht durch
ein Praedikat erkennen. Gemeinsam ist ihnen der Melder, der das achte
Vorkommen (L-234e85, 2026-08-18) tatsaechlich gefangen hat: die Stelle, an
der ein erwartetes Rot durch einen fehlenden `strict=True` still Gruen wird.
Dieser Pruefstein sitzt deshalb an genau diesem Detektor, nicht an der Lehre
selbst.

Zwei Praedikate ueber tests/*.py:

A) Jede `pytest.mark.xfail(...)`-Markierung traegt `strict=True` UND ein
   `reason=`. Ohne `strict` wird ein XPASS nicht gemeldet -- der Melder, der
   heute als einziger anschlug, faellt aus.
B) Eine Testdatei mit xfail-Tests darf nicht ausschliesslich daraus bestehen.
   Ein rotes Gate ohne Positivfall belegt nicht, dass der Pruefaufbau
   ueberhaupt bis zur gemessenen Stelle durchkommt.

Werkzeug: das `ast`-Modul, keine Zeilen-Regex -- ein `# xfail` im Kommentar
oder das Wort in einem Docstring darf nicht treffen (Falschtreffer-Probe
unten).

Entscheidung zu `pytest.xfail(...)` (Aufrufform im Testkoerper, nicht der
Marker): NICHT mitgeprueft. `pytest.xfail()` kennt kein `strict`-Schluesselwort
-- das Verhalten haengt an der globalen `xfail_strict`-Ini, nicht an der
Aufrufstelle. Praedikat A pruefbar zu machen wuerde eine Eigenschaft
verlangen, die diese Aufrufform gar nicht tragen kann. Kein Vorkommen dieser
Form existiert heute in tests/*.py (siehe test_negativkontrolle_keine_treffer
unten als Beleg, dass die Erhebung das ueberhaupt haette bemerkt).

Ausnahme von `strict=True` (deliberate, kein Verstoss): der Marker traegt
im `reason=`-Text woertlich die Wendung "Bewusst NICHT strict". Bewusst KEINE
Zeilennummern-Liste -- eine Ausnahme an eine Zeile zu binden drueckt sich vor
Drift: verschiebt sich die Datei, deckt dieselbe Zeilennummer entweder nichts
mehr ab (laut, ungefaehrlich) oder still einen ANDEREN, neu hinzugekommenen
Marker (ein stiller Freispruch -- genau die Fehlerklasse, gegen die dieser
Pruefstein gebaut ist). Die Wendung muss im `reason=`-Argument selbst stehen;
im Kommentar oder Docstring daneben zaehlt sie nicht (Grenzfall-Test unten).
tests/test_sichtbarkeit_ausgabeform.py:75 traegt diese Wendung heute woertlich
im `reason=` und ist damit keine Ausnahme mehr, die separat gefuehrt werden
muss -- der Pruefstein erkennt sie selbst.

tests/test_alle_selftests.py ist eine fremde, uncommittete Arbeitskopie (siehe
`git status --short`) und bleibt aus der Wirklichkeits-Pruefung aussen vor, um
nicht fremde Arbeit zu bewerten.
"""
from __future__ import annotations

import ast
import textwrap
from dataclasses import dataclass
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SELBST = Path(__file__).name

# Wendung, die -- nur im reason=-Text selbst -- eine bewusste Nicht-Strict-
# Markierung von einem Versaeumnis unterscheidet. Siehe Modul-Docstring.
BEWUSSTE_AUSNAHME_WENDUNG = "Bewusst NICHT strict"

# Fremde, uncommittete Arbeitskopie -- nicht Teil der Wirklichkeits-Pruefung.
AUSGESCHLOSSEN = {"test_alle_selftests.py", SELBST}


@dataclass(frozen=True)
class Befund:
    datei: str
    zeile: int
    was: str


def _ist_xfail_call(node: ast.AST) -> bool:
    """True fuer Aufrufe der Form pytest.mark.xfail(...)."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "xfail"
        and isinstance(func.value, ast.Attribute)
        and func.value.attr == "mark"
    )


def _xfail_marker_namen(baum: ast.AST) -> set[str]:
    """Modulvariablen, deren Wert ein pytest.mark.xfail(...)-Aufruf ist
    (z.B. `WARTET = pytest.mark.xfail(...)`, spaeter als `@WARTET` benutzt)."""
    namen: set[str] = set()
    for node in ast.walk(baum):
        if isinstance(node, ast.Assign) and _ist_xfail_call(node.value):
            for ziel in node.targets:
                if isinstance(ziel, ast.Name):
                    namen.add(ziel.id)
    return namen


def _reason_text(kw_value: ast.expr) -> str | None:
    """Text eines reason=-Arguments, wenn er als String-Literal vorliegt
    (auch implizit ueber Klammern verkettete Literale -- der Parser fasst
    die schon zu einem einzigen ast.Constant zusammen). None bei dynamisch
    zusammengesetztem Text (z.B. f-String, +-Verkettung)."""
    if isinstance(kw_value, ast.Constant) and isinstance(kw_value.value, str):
        return kw_value.value
    return None


def _praedikat_a(quelltext: str, dateiname: str) -> list[Befund]:
    """Jede xfail-Markierung braucht strict=True UND reason=. Ausnahme: der
    reason=-Text selbst traegt woertlich BEWUSSTE_AUSNAHME_WENDUNG -- dann
    gilt fehlendes strict=True als begruendete, sichtbare Entscheidung."""
    baum = ast.parse(quelltext, filename=dateiname)
    befunde: list[Befund] = []
    for node in ast.walk(baum):
        if not _ist_xfail_call(node):
            continue
        strict_ok = False
        reason_ok = False
        reason_text: str | None = None
        for kw in node.keywords:
            if kw.arg == "strict":
                try:
                    strict_ok = ast.literal_eval(kw.value) is True
                except ValueError:
                    strict_ok = False
            elif kw.arg == "reason":
                reason_text = _reason_text(kw.value)
                if reason_text is not None:
                    reason_ok = bool(reason_text.strip())
                else:
                    # dynamisch zusammengesetzter reason-Text (z.B. f-String)
                    # -- Praesenz genuegt; die Wendungspruefung kann ihn
                    # dann nicht lesen und die Ausnahme greift nicht.
                    reason_ok = True

        if not strict_ok and reason_text and BEWUSSTE_AUSNAHME_WENDUNG in reason_text:
            strict_ok = True  # begruendete, sichtbare Ausnahme -- kein Befund

        fehlt = []
        if not strict_ok:
            fehlt.append("strict=True")
        if not reason_ok:
            fehlt.append("reason=")
        if fehlt:
            befunde.append(Befund(
                dateiname, node.lineno,
                f"xfail ohne {' und '.join(fehlt)} -- nachtragen, sonst bleibt "
                f"ein XPASS an dieser Stelle unbemerkt",
            ))
    return befunde


def _test_funktionen_und_xfail_status(baum: ast.Module) -> list[tuple[str, int, bool]]:
    """Liste (name, zeile, ist_xfail) fuer alle top-level test_*-Funktionen."""
    marker_namen = _xfail_marker_namen(baum)

    def _dekoriert_mit_xfail(dec: ast.expr) -> bool:
        if _ist_xfail_call(dec):
            return True
        if isinstance(dec, ast.Name) and dec.id in marker_namen:
            return True
        return False

    ergebnis = []
    for node in baum.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            xfail = any(_dekoriert_mit_xfail(d) for d in node.decorator_list)
            ergebnis.append((node.name, node.lineno, xfail))
    return ergebnis


def _praedikat_b(quelltext: str, dateiname: str) -> list[Befund]:
    """Eine Datei mit xfail-Tests braucht mindestens einen nicht-xfail-Test."""
    baum = ast.parse(quelltext, filename=dateiname)
    tests = _test_funktionen_und_xfail_status(baum)
    if not tests:
        return []
    xfail_tests = [t for t in tests if t[2]]
    if xfail_tests and len(xfail_tests) == len(tests):
        erste_zeile = min(z for _, z, _ in tests)
        return [Befund(
            dateiname, erste_zeile,
            f"alle {len(tests)} Test(s) in dieser Datei sind xfail -- "
            f"mindestens einen nicht-xfail Test ergaenzen, sonst misst das "
            f"Gate nur sich selbst",
        )]
    return []


def _alle_testdateien(ausschluss: set[str] = frozenset()) -> list[Path]:
    return sorted(
        p for p in TESTS_DIR.glob("test_*.py") if p.name not in ausschluss
    )


# ---------------------------------------------------------------------------
# Selbsttest: synthetische Quelltexte, sauber und verletzend.
# Ein Pruefstein, der nur die Wirklichkeit kennt, ist selbst ungeprueft.
# ---------------------------------------------------------------------------

_SAUBER = textwrap.dedent('''
    """Ein Kommentar erwaehnt xfail, das darf nicht treffen -- # xfail
    genauso wenig wie hier im Docstring."""
    import pytest

    @pytest.mark.xfail(strict=True, reason="belegter Grund")
    def test_erwartet_rot():
        assert False

    def test_positivfall():
        assert True
''')

_VERLETZT_KEIN_STRICT = textwrap.dedent('''
    import pytest

    @pytest.mark.xfail(reason="kein strict gesetzt")
    def test_erwartet_rot():
        assert False

    def test_positivfall():
        assert True
''')

_VERLETZT_KEIN_REASON = textwrap.dedent('''
    import pytest

    @pytest.mark.xfail(strict=True)
    def test_erwartet_rot():
        assert False

    def test_positivfall():
        assert True
''')

_GRENZFALL_STRICT_OHNE_REASON = textwrap.dedent('''
    import pytest

    @pytest.mark.xfail(strict=True)
    def test_erwartet_rot():
        assert False

    def test_positivfall():
        assert True
''')

_GRENZFALL_REASON_OHNE_STRICT = textwrap.dedent('''
    import pytest

    @pytest.mark.xfail(reason="nur ein Grund, kein strict")
    def test_erwartet_rot():
        assert False

    def test_positivfall():
        assert True
''')

_NUR_XFAIL_TESTS = textwrap.dedent('''
    import pytest

    @pytest.mark.xfail(strict=True, reason="belegter Grund")
    def test_erwartet_rot_eins():
        assert False

    @pytest.mark.xfail(strict=True, reason="belegter Grund")
    def test_erwartet_rot_zwei():
        assert False
''')

_BEWUSST_NICHT_STRICT_MIT_WENDUNG = textwrap.dedent('''
    import pytest

    @pytest.mark.xfail(reason=(
        "Der Aufbau fehlt noch. Bewusst NICHT strict: soll gruen werden "
        "duerfen, sobald er steht."), strict=False)
    def test_erwartet_rot():
        assert False

    def test_positivfall():
        assert True
''')

_BEWUSST_NICHT_STRICT_OHNE_WENDUNG = textwrap.dedent('''
    import pytest

    @pytest.mark.xfail(reason="Der Aufbau fehlt noch.", strict=False)
    def test_erwartet_rot():
        assert False

    def test_positivfall():
        assert True
''')

_WENDUNG_NUR_IM_KOMMENTAR = textwrap.dedent('''
    import pytest

    # Bewusst NICHT strict -- dieser Kommentar darf nicht als Ausnahme zaehlen.
    @pytest.mark.xfail(reason="Der Aufbau fehlt noch.", strict=False)
    def test_erwartet_rot():
        """Bewusst NICHT strict -- auch dieser Docstring nicht."""
        assert False

    def test_positivfall():
        assert True
''')

_VARIABLEN_MARKER_MIT_POSITIVFALL = textwrap.dedent('''
    import pytest

    WARTET = pytest.mark.xfail(strict=True, reason="belegter Grund")

    @WARTET
    def test_erwartet_rot():
        assert False

    def test_positivfall():
        assert True
''')


def test_negativfall_sauberer_quelltext_ohne_befund():
    """Positivkontrolle: korrekt markiertes xfail + ein nicht-xfail Test darf
    nicht anschlagen -- weder Praedikat A noch B."""
    assert _praedikat_a(_SAUBER, "sauber.py") == []
    assert _praedikat_b(_SAUBER, "sauber.py") == []


def test_verletzender_fall_ohne_strict_wird_erkannt():
    befunde = _praedikat_a(_VERLETZT_KEIN_STRICT, "verletzt.py")
    assert len(befunde) == 1
    assert "strict=True" in befunde[0].was
    assert befunde[0].zeile == 4


def test_verletzender_fall_ohne_reason_wird_erkannt():
    befunde = _praedikat_a(_VERLETZT_KEIN_REASON, "verletzt.py")
    assert len(befunde) == 1
    assert "reason=" in befunde[0].was


def test_grenzfall_strict_ohne_reason_ist_ein_befund():
    """@pytest.mark.xfail(strict=True) OHNE reason muss beanstandet werden."""
    befunde = _praedikat_a(_GRENZFALL_STRICT_OHNE_REASON, "grenzfall.py")
    assert len(befunde) == 1 and "reason=" in befunde[0].was


def test_grenzfall_reason_ohne_strict_ist_ein_befund():
    """@pytest.mark.xfail(reason="x") OHNE strict muss beanstandet werden."""
    befunde = _praedikat_a(_GRENZFALL_REASON_OHNE_STRICT, "grenzfall.py")
    assert len(befunde) == 1 and "strict=True" in befunde[0].was


def test_falschtreffer_wort_in_kommentar_und_docstring_schlaegt_nicht_an():
    """Das Wort 'xfail' in Kommentar/Docstring darf keinen Befund erzeugen --
    genau der Fehler, den Zeilen-Regex haette und AST nicht hat."""
    assert _praedikat_a(_SAUBER, "sauber.py") == []


def test_positivfall_wendung_im_reason_entschuldigt_fehlendes_strict():
    """reason= traegt woertlich 'Bewusst NICHT strict' -- kein Befund."""
    assert _praedikat_a(_BEWUSST_NICHT_STRICT_MIT_WENDUNG, "bewusst.py") == []


def test_rotprobe_ohne_wendung_ist_wieder_ein_befund():
    """Dieselbe Konstellation OHNE die Wendung im reason= -- muss beanstanden.
    Rot-Probe: entfernt man die Wendung testweise, schlaegt der Pruefstein an."""
    befunde = _praedikat_a(_BEWUSST_NICHT_STRICT_OHNE_WENDUNG, "unbewusst.py")
    assert len(befunde) == 1 and "strict=True" in befunde[0].was


def test_grenzfall_wendung_nur_in_kommentar_oder_docstring_zaehlt_nicht():
    """Die Wendung muss im reason=-Argument stehen -- im Kommentar oder
    Docstring daneben ist sie wirkungslos, sonst waere jede Begruendung per
    Kommentar statt per reason= moeglich und der Zwang zur Angabe am Ort
    entfiele."""
    befunde = _praedikat_a(_WENDUNG_NUR_IM_KOMMENTAR, "kommentar.py")
    assert len(befunde) == 1 and "strict=True" in befunde[0].was


def test_datei_nur_aus_xfail_tests_ist_ein_befund():
    befunde = _praedikat_b(_NUR_XFAIL_TESTS, "nur_xfail.py")
    assert len(befunde) == 1
    assert "2 Test(s)" in befunde[0].was


def test_variablen_marker_mit_positivfall_kein_befund():
    """`WARTET = pytest.mark.xfail(...)` gefolgt von `@WARTET` muss erkannt
    werden -- wie in tests/test_stammformen.py verwendet."""
    assert _praedikat_a(_VARIABLEN_MARKER_MIT_POSITIVFALL, "variablen.py") == []
    assert _praedikat_b(_VARIABLEN_MARKER_MIT_POSITIVFALL, "variablen.py") == []


def test_variablen_marker_ohne_positivfall_ist_befund_b():
    quelltext = _VARIABLEN_MARKER_MIT_POSITIVFALL.replace(
        "def test_positivfall():\n    assert True\n", ""
    )
    befunde = _praedikat_b(quelltext, "variablen_ohne_positiv.py")
    assert len(befunde) == 1


# ---------------------------------------------------------------------------
# Wirklichkeit: tests/*.py dieses Repos.
# ---------------------------------------------------------------------------

def test_wirklichkeit_praedikat_a_nur_bekannte_ausnahme():
    """Ueber alle tests/*.py (ausser der fremden Arbeitskopie
    test_alle_selftests.py und dieser Datei selbst): jede xfail-Markierung
    traegt strict=True und reason=, oder der reason=-Text traegt woertlich
    BEWUSSTE_AUSNAHME_WENDUNG (siehe Modul-Docstring)."""
    befunde: list[Befund] = []
    for pfad in _alle_testdateien(AUSGESCHLOSSEN):
        befunde.extend(_praedikat_a(pfad.read_text(encoding="utf-8"), pfad.name))
    assert not befunde, "Verstoesse gegen strict=True/reason=:\n" + "\n".join(
        f"  tests/{b.datei}:{b.zeile} -- {b.was}" for b in befunde
    )


def test_wirklichkeit_praedikat_b_kein_gate_ohne_positivfall():
    """Ueber alle tests/*.py (ausser test_alle_selftests.py und dieser Datei):
    keine Datei besteht ausschliesslich aus xfail-Tests."""
    befunde: list[Befund] = []
    for pfad in _alle_testdateien(AUSGESCHLOSSEN):
        befunde.extend(_praedikat_b(pfad.read_text(encoding="utf-8"), pfad.name))
    assert not befunde, "Gates ohne Positivfall:\n" + "\n".join(
        f"  tests/{b.datei}:{b.zeile} -- {b.was}" for b in befunde
    )


def test_negativkontrolle_keine_treffer_fuer_pytest_xfail_aufrufform():
    """Beleg fuer die Entscheidung im Modul-Docstring: die Aufrufform
    pytest.xfail(...) (kein Marker) kommt heute in tests/*.py nicht vor --
    sonst waere die bewusste Nicht-Pruefung eine blinde Flecken-Behauptung."""
    treffer = []
    for pfad in _alle_testdateien(AUSGESCHLOSSEN | {"test_alle_selftests.py"}):
        baum = ast.parse(pfad.read_text(encoding="utf-8"), filename=pfad.name)
        for node in ast.walk(baum):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "xfail"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "pytest"
            ):
                treffer.append(f"{pfad.name}:{node.lineno}")
    assert not treffer, (
        "pytest.xfail(...)-Aufrufform gefunden, die Entscheidung im Modul-"
        f"Docstring (nicht mitgeprueft) trifft nicht mehr zu: {treffer}"
    )
