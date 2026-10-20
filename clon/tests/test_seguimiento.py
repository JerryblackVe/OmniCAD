"""Las tablas de docs/seguimiento/ (bugs, faltantes, mejoras) no se contradicen ni prometen sin evidencia.

Reglas en docs/seguimiento/README.md: IDs únicos, estados y dificultades de la lista cerrada, y todo lo
«Corregido» o «Hecho» nombra su evidencia; si la evidencia es un test, el test existe.
"""
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
CARPETA = REPO / "docs" / "seguimiento"
ESTADOS = {
    "bugs.md": {"Abierto", "Parcial", "Corregido", "No reproducido", "Retirado", "Sin verificar"},
    "faltantes.md": {"Abierto", "Parcial", "Hecho", "Bloqueado", "Descartado", "Sin verificar"},
    "mejoras.md": {"Abierto", "Parcial", "Hecho", "Bloqueado", "Descartado", "Sin verificar"},
}
DIFICULTADES = {"Baja", "Media", "Alta", "Muy alta", "—"}
CERRADOS = {"Corregido", "Hecho"}


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


TODAS = [f for nombre in ESTADOS for f in _filas(nombre)]


def test_hay_filas_en_cada_archivo():
    for nombre in ESTADOS:
        assert _filas(nombre), f"{nombre} no tiene ninguna fila de 7 columnas"


def test_ids_unicos():
    vistos = {}
    for donde, ident, *_ in TODAS:
        assert ident not in vistos, f"{ident} está dos veces: {vistos.get(ident)} y {donde}"
        vistos[ident] = donde


@pytest.mark.parametrize("donde, ident, que, estado, dificultad, queda, evidencia, fecha", TODAS)
def test_fila_valida(donde, ident, que, estado, dificultad, queda, evidencia, fecha):
    archivo = donde.split(":")[0]
    assert estado in ESTADOS[archivo], f"{donde}: estado «{estado}» no vale; usar {sorted(ESTADOS[archivo])}"
    assert dificultad in DIFICULTADES, f"{donde}: dificultad «{dificultad}» no vale"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", fecha), f"{donde}: «Verificado» tiene que ser una fecha AAAA-MM-DD"
    if estado in CERRADOS:
        assert evidencia not in {"", "—"}, f"{donde}: {ident} está «{estado}» sin evidencia"
        assert dificultad == "—", f"{donde}: {ident} está «{estado}» y todavía tiene dificultad"
    for ruta in re.findall(r"tests/[\w/]+\.py", evidencia):
        assert (REPO / "clon" / ruta).is_file(), f"{donde}: {ruta} no existe"
    for ruta, nombre in re.findall(r"(tests/[\w/]+\.py)::(\w+)", evidencia):
        archivo_test = REPO / "clon" / ruta
        assert archivo_test.is_file(), f"{donde}: {ruta} no existe"
        assert re.search(rf"^\s*(?:async\s+)?(?:def|class)\s+{nombre}\b", archivo_test.read_text(encoding="utf-8"),
                         re.M), f"{donde}: {ruta} no tiene {nombre}"
