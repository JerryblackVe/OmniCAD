# -*- coding: utf-8 -*-
"""Los .f3d/.f3z reales de Fusion 360 (P11.a) abren con los números medidos: cuerpos, volumen, componentes movidos y
cuerpos sin ubicar. Los ejemplos viven fuera del repo (en el escritorio de la PC de desarrollo): sin esa carpeta (otra
PC, CI) estas pruebas se saltean. Se trabaja siempre sobre COPIAS en `tmp_path`: los originales no se tocan."""
import shutil
from pathlib import Path

import pytest

from omnicad import api

EJEMPLOS = Path.home() / "Desktop" / "f3z"

pytestmark = pytest.mark.skipif(not EJEMPLOS.is_dir(), reason=f"faltan los ejemplos de Fusion en {EJEMPLOS}")
LENTOS = {"CARTERA GOTICA v2.f3d", "EXTRUSOR SHERPA MINI MOD v6.f3d", "EXTRUSOR XOX.f3z"}      # más de 10 s cada uno

# archivo: (cuerpos guardados, cuerpos colocados, volumen colocado en mm³, componentes movidos, sin ubicar)
# Tabla medida en la tanda «upgrades3» sin los cuerpos viejos del historial que Fusion deja en cada bloque y la escena no
# muestra (privado/reportes/upgrades3/item4_ejemplos.md). Abiertos en Fusion: Tela 21 cuerpos, Cartera 11, Sherpa 50
# (los 2 de más son los «sin ubicar»), Corazón 10, Sin guardar 1. Volumen (ítem 6: aros y soporte como sólidos):
# Tela 301 934,2 en Fusion, Cartera 395 155,5.
ESPERADO = {
    "(Sin guardar).f3d": (1, 1, 1005.7, 0, 0),
    "ABANICO CORAZON PLANTILLA v1.f3d": (10, 10, 68606.7, 0, 0),
    "ABANICO TELA  CAE v1.f3d": (21, 21, 301935.5, 0, 0),
    "CARTERA GOTICA v2.f3d": (10, 11, 395336.1, 10, 0),
    "EXTRUSOR SHERPA MINI MOD v6.f3d": (32, 50, 36090.6, 31, 0),
    "EXTRUSOR XOX.f3z": (72, 111, 173767.6, 64, 3),
}


def _inspeccionar(nombre, tmp_path):
    copia = tmp_path / nombre
    shutil.copyfile(EJEMPLOS / nombre, copia)
    r = api.llamar(api.Sesion(), "inspect_f3d", {"path": str(copia)})
    assert r["ok"], r
    return r["result"]


@pytest.mark.parametrize("nombre", [pytest.param(n, marks=pytest.mark.lento) if n in LENTOS else n for n in sorted(ESPERADO)])
def test_el_ejemplo_abre_con_los_numeros_medidos(nombre, tmp_path):
    if not (EJEMPLOS / nombre).is_file():
        pytest.fail(f"falta el ejemplo {nombre} en {EJEMPLOS}")
    guardados, colocados, volumen, movidos, sin_ubicar = ESPERADO[nombre]
    d = _inspeccionar(nombre, tmp_path)
    assert d["bodies_stored"] == guardados
    assert d["bodies_placed"] == colocados
    assert d["volume_placed_mm3"] == pytest.approx(volumen, rel=1e-3)
    assert d["components_moved"] == movidos
    assert d["unplaced_bodies"] == sin_ubicar
