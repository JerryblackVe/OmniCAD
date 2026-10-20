"""Las listas de docs/seguimiento/ (bugs, faltantes, mejoras) tienen solo lo que falta resolver y no se contradicen.

Reglas en docs/seguimiento/README.md: lo resuelto se borra (no hay estados de cerrado), IDs únicos, estados y
dificultades de la lista cerrada, y si la evidencia nombra un test, el test existe. Las tablas del README solo
nombran IDs que siguen en las listas.
"""
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
CARPETA = REPO / "docs" / "seguimiento"
LISTAS = ("bugs.md", "faltantes.md", "mejoras.md")
ESTADOS = {"Abierto", "Parcial", "Bloqueado", "Sin verificar"}
DIFICULTADES = {"Baja", "Media", "Alta", "Muy alta"}


def _filas(nombre):
    """Filas de las tablas de seguimiento: las que tienen 7 celdas y no son encabezado ni separador."""
    filas = []
    for n, linea in enumerate((CARPETA / nombre).read_text(encoding="utf-8").splitlines(), 1):
        if not linea.startswith("| "):
            continue
        celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
        if len(celdas) != 7 or celdas[0] == "ID" or set(celdas[0]) <= {"-", ":"}:
            continue
        filas.append((f"{nombre}:{n}", *celdas))
    return filas


TODAS = [f for nombre in LISTAS for f in _filas(nombre)]


def test_hay_filas_en_cada_archivo():
    for nombre in LISTAS:
        assert _filas(nombre), f"{nombre} no tiene ninguna fila de 7 columnas"


def test_ids_unicos():
    vistos = {}
    for donde, ident, *_ in TODAS:
        assert ident not in vistos, f"{ident} está dos veces: {vistos.get(ident)} y {donde}"
        vistos[ident] = donde


@pytest.mark.parametrize("donde, ident, que, estado, dificultad, queda, evidencia, fecha", TODAS)
def test_fila_valida(donde, ident, que, estado, dificultad, queda, evidencia, fecha):
    assert estado in ESTADOS, (f"{donde}: estado «{estado}» no vale; usar {sorted(ESTADOS)}. "
                               "Lo resuelto se borra de la lista (docs/seguimiento/README.md).")
    assert dificultad in DIFICULTADES, f"{donde}: dificultad «{dificultad}» no vale"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", fecha), f"{donde}: «Verificado» tiene que ser una fecha AAAA-MM-DD"
    for ruta in re.findall(r"tests/[\w/]+\.py", evidencia):
        assert (REPO / "clon" / ruta).is_file(), f"{donde}: {ruta} no existe"
    for ruta, nombre in re.findall(r"(tests/[\w/]+\.py)::(\w+)", evidencia):
        texto = (REPO / "clon" / ruta).read_text(encoding="utf-8")
        assert re.search(rf"^\s*(?:async\s+)?(?:def|class)\s+{nombre}\b", texto, re.M), f"{donde}: {ruta} no tiene {nombre}"


def test_el_readme_solo_nombra_ids_que_siguen_en_las_listas():
    vivos = {f[1] for f in TODAS}
    for linea in (CARPETA / "README.md").read_text(encoding="utf-8").splitlines():
        if linea.startswith("| ") and "·" in linea:
            for ident in linea.strip().strip("|").split("|")[-1].split("·"):
                assert ident.strip() in vivos, f"README.md nombra {ident.strip()}, que ya no está en las listas"
