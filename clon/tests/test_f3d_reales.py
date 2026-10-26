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


@pytest.mark.skipif(not (EJEMPLOS / "BINCHA.f3d").is_file(), reason="falta BINCHA.f3d")
@pytest.mark.lento
def test_bincha_abre_rapido_y_con_las_mallas_ocultas(tmp_path):
    """Antes tardaba 5 minutos (ShapeFix sobre una malla convertida de 18 716 caras: acis_occ.CARAS_SIN_ARREGLO) y
    mostraba dos mallas que Fusion no muestra. La escena trae 6 cuerpos con las mismas caras que los 6 del B-rep (366
    del sólido visible, el único con malla; 18 716, 3 708, 3 516, 3 516 y 88 de las mallas convertidas, sin malla =
    ocultas): entran los seis y cinco quedan con el ojo cerrado."""
    import time

    from omnicad.io_archivos.abrir_externo import documento_desde_archivo
    from omnicad.nucleo import geometria as geo
    copia = tmp_path / "BINCHA.f3d"
    shutil.copyfile(EJEMPLOS / "BINCHA.f3d", copia)
    t = time.perf_counter()
    doc, _ = documento_desde_archivo(copia)
    assert time.perf_counter() - t < 90
    cuerpos = list(doc.estado_final.cuerpos.values())
    ocultos = set(doc.propiedades["__navegador__"]["ocultos"])
    assert len(cuerpos) == 6 and len(ocultos) == 5
    solido, = [c for c in cuerpos if c.tipo == "solido"]
    assert solido.id not in ocultos and geo.es_valida(solido.forma)
    assert geo.volumen(solido.forma) == pytest.approx(6014.0, rel=1e-3)
    d = _inspeccionar("BINCHA.f3d", tmp_path)
    assert (d["bodies_stored"], d["bodies_placed"], d["bodies_hidden"], d["discarded_bodies"]) == (6, 6, 5, 0)


@pytest.mark.skipif(not (EJEMPLOS / "BINCHA.f3d").is_file(), reason="falta BINCHA.f3d")
@pytest.mark.lento
def test_bincha_trae_sus_diez_bocetos(tmp_path):
    """Fusion cuenta 10 bocetos (DcSketch en el flujo de diseño) y los perfiles del .smb dan exactamente 10 sin las
    tapas repetidas de las extrusiones: el contorno de la bincha (63 mm de radio, patas hasta y = -81), tres bocetos
    de letras, el recorte pequeño y el triángulo suelto. Dos sobre z = -5 (cara) y el resto sobre XY."""
    from omnicad.io_archivos.abrir_externo import documento_desde_archivo
    copia = tmp_path / "BINCHA.f3d"
    shutil.copyfile(EJEMPLOS / "BINCHA.f3d", copia)
    doc, _ = documento_desde_archivo(copia)
    bocetos = [o for o in doc.operaciones if o.TIPO == "boceto"]
    assert len(bocetos) == 10 and [o.nombre for o in bocetos] == [f"Boceto{k}" for k in range(1, 11)]
    assert sorted(o.p["plano"] for o in bocetos).count("cara") == 2 and all(r.estado == "ok" for r in doc.resultados)
    assert sum(len(o.boceto.curvas) for o in bocetos) == 55 + 96 + 539
    y_min = min(p.y for o in bocetos for p in o.boceto.puntos.values())
    assert y_min == pytest.approx(-81.1, abs=0.3)                       # las patas de la bincha


@pytest.mark.skipif(not (EJEMPLOS / "BINCHA.f3d").is_file(), reason="falta BINCHA.f3d")
@pytest.mark.lento
def test_bincha_declara_su_historial_de_fusion_sin_traducirlo(tmp_path):
    """La tabla de tipos del flujo de diseño: 10 bocetos (los 10 que se importan), 44 extrusiones, 14 empalmes, 9
    chaflanes… El historial no se traduce y el aviso de apertura lo dice con esas cifras."""
    from omnicad.io_archivos.abrir_externo import documento_desde_archivo
    copia = tmp_path / "BINCHA.f3d"
    shutil.copyfile(EJEMPLOS / "BINCHA.f3d", copia)
    _, avisos = documento_desde_archivo(copia)
    aviso, = [a for a in avisos if "historial de Fusion" in a]
    for texto in ("44 × Extruir", "14 × Empalme", "9 × Chaflán", "10 × Eliminar cuerpo", "1 × Convertir malla",
                  "Fusion cuenta 10 bocetos y se importaron 10", "NO se traduce"):
        assert texto in aviso, texto
    d = _inspeccionar("BINCHA.f3d", tmp_path)
    assert {o["type"]: o["count"] for o in d["history"]["operations"]}["ExtrudeFeature"] == 44
    assert d["history"]["translated"] is False and d["sketches"]["count"] == 10
