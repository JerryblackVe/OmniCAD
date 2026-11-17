"""Reglas homogéneas (CLAUDE.md, regla 19): cada número clave vive en una fuente y nadie más trae otro valor.

Lee el número de su fuente única y falla si un documento, script, hook o memoria dice otra cosa.
Corre cada noche con la suite (`scripts/suite_noche.sh`).
"""
import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DOCS = ["CLAUDE.md", "AGENTS.md", "docs/coordinacion.md", "docs/brief.md", ".claude/hooks/inicio.sh",
        ".claude/skills/omnicad/SKILL.md", ".claude/skills/omnicad-test/SKILL.md"]
# La memoria de la máquina (si existe) también tiene que coincidir: solo enlaza, nunca trae otro número.
MEMORIA = sorted((Path.home() / ".claude/projects/-home-mosos-OmniCAD/memory").glob("*.md"))


def texto(ruta):
    return (RAIZ / ruta).read_text(encoding="utf-8")


def todos():
    return [(r, texto(r)) for r in DOCS] + [(str(m), m.read_text(encoding="utf-8")) for m in MEMORIA]


def uno(patron, ruta):
    """El número de la fuente única: exactamente una aparición."""
    hallados = re.findall(patron, texto(ruta))
    assert len(hallados) == 1, f"{ruta}: se esperaba 1 fuente para {patron!r}, hay {len(hallados)}"
    return hallados[0]


def distintos(patron, valor):
    """(archivo, valor) de cada aparición del patrón con un valor distinto al de la fuente."""
    return [(r, v) for r, t in todos() for v in re.findall(patron, t, flags=re.I) if v != valor]


def test_tope_de_corridas_de_opencode_una_fuente_y_el_vigia_igual():
    n = uno(r"Tope: hasta (\d+) corridas a la vez", "docs/coordinacion.md")
    vigia = re.search(r"^MAX=\$\{VIGIA_MAX:-(\d+)\}", texto("scripts/vigia_opencode.sh"), re.M).group(1)
    assert vigia == n, f"vigia_opencode.sh MAX={vigia}, el Protocolo dice {n}"
    otros = [r for r, t in todos() if r != "docs/coordinacion.md" and re.search(r"\d+ corridas a la vez", t)]
    assert not otros, f"repiten el número de corridas (tienen que enlazar al Protocolo): {otros}"


def test_topes_de_contexto_iguales_en_claude_md_y_en_el_hook():
    coord, e, aviso = uno(r"Tope: (\d+) % de contexto para el chat maestro y el\s+coordinador, (\d+) % para E1–E11; "
                          r"aviso al (\d+) %", "CLAUDE.md")
    hook = re.search(r"AVISO, TOPE_E, TOPE_COORD = (\d+), (\d+), (\d+)", texto(".claude/hooks/ctx25.py")).groups()
    assert hook == (aviso, e, coord), f"ctx25.py {hook} contra CLAUDE.md {(aviso, e, coord)}"


def test_turnos_de_tests_un_solo_valor():
    n = uno(r"Tests de a (\d+) con `scripts/turno.py`", "CLAUDE.md")
    assert not distintos(r"OMNICAD_TURNOS=(\d+)", n)
    ajustes = Path.home() / ".claude/settings.json"
    if ajustes.exists():  # solo en la VPS
        valor = json.loads(ajustes.read_text(encoding="utf-8")).get("env", {}).get("OMNICAD_TURNOS")
        assert valor in (None, n), f"~/.claude/settings.json OMNICAD_TURNOS={valor}, CLAUDE.md dice {n}"


def test_minutos_del_vigia_iguales_en_el_script_su_crontab_y_el_protocolo():
    n = uno(r"`scripts/vigia_opencode.sh` en la crontab de la VPS, cada (\d+) min", "docs/coordinacion.md")
    script = texto("scripts/vigia_opencode.sh")
    assert re.search(r"cada (\d+) min", script).group(1) == n
    assert re.search(r"^# Línea de crontab: \*/(\d+) ", script, re.M).group(1) == n
    assert not distintos(r"vigía[^.\n]{0,60}cada (\d+) min", n)


def test_limites_de_iteraciones_e_intentos_una_sola_fuente():
    it = uno(r"como mucho \*\*(\d+) iteraciones\*\*", "CLAUDE.md")
    intentos = uno(r"\*\*(\d+) intentos de prueba\*\*", "CLAUDE.md")
    assert not distintos(r"(\d+) iteraciones", it)
    assert not distintos(r"(\d+) intentos (?:de prueba|por problema)", intentos)


def test_umbral_de_grupos_de_tests_afectados_igual_a_la_regla_4():
    n = uno(r"\*\*Si `tests_afectados.py` elige más de (\d+) grupos\*\*", "CLAUDE.md")
    assert re.search(r"^MAX_GRUPOS = (\d+)", texto("scripts/tests_afectados.py"), re.M).group(1) == n
    assert not distintos(r"más de (\d+) grupos", n)
