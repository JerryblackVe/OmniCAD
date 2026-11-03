# -*- coding: utf-8 -*-
"""SOL-13 y SOL-20 en los diálogos: Desmoldeo con línea de partición y modo de ángulo, y Patrón geométrico."""
import math
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.api import selectores as sl  # noqa: E402
from omnicad.nucleo import geometria as geo  # noqa: E402
from omnicad.timeline.documento import Documento  # noqa: E402
from omnicad.timeline.operaciones import OpPrimitiva  # noqa: E402
from omnicad.ui.comando import ContextoComando, ErrorComando, hit_desde_ref  # noqa: E402


@pytest.fixture
def doc():
    QApplication.instance() or QApplication([])
    d = Documento()
    d.agregar(OpPrimitiva(d.nuevo_id(), forma="caja", ancho="60", largo="60", alto="6"))
    return d


def _hit(doc, selector, tipo="cara"):
    ses = api.Sesion(doc)
    c, e = sl.elegir_uno(ses, selector, tipo)
    return hit_desde_ref(sl.referencia(c, e), doc.estado_final)


def _valores(cmd, ctx):
    return {c.clave: (list(c.defecto) if isinstance(c.defecto, list) else c.defecto) for c in cmd.campos(ctx)}


def test_patron_geometrico_dialogo_construye_y_corta(doc):
    from omnicad.ui.comandos.plastico import PatronGeometrico
    cmd, ctx = PatronGeometrico(), ContextoComando(doc)
    v = _valores(cmd, ctx)
    with pytest.raises(ErrorComando):
        cmd.construir(v, ctx)                                                  # sin caras
    v.update(caras=[_hit(doc, ">Z")], tamano1="4 mm", tamano2="4 mm", distancia="10 mm", operacion="cortar")
    op = cmd.construir(v, ctx)
    doc.agregar(op)
    cuerpo = next(iter(doc.estado_final.cuerpos.values()))
    assert 60 * 60 * 6 - geo.volumen(cuerpo.forma) == pytest.approx(25 * 2 / 3 * math.pi * 8, rel=1e-3)
    assert cmd.desde_op(op, ContextoComando(doc, op=op))["distribucion"] == "rectangular"
    v.update(tamano1="mucho")
    with pytest.raises(Exception):                                             # expresión inválida: rojo, no excepción en el slot
        cmd.construir(v, ctx)


def test_desmoldeo_dialogo_linea_de_particion_y_relativo(doc):
    from omnicad.ui.comandos.modificar import Desmoldeo
    cmd, ctx = Desmoldeo(), ContextoComando(doc)
    v = _valores(cmd, ctx)
    v.update(plano=[hit_desde_ref({"tipo": "plano", "id": "XY"}, doc.estado_final)], caras=[_hit(doc, ">X")],
             tipo="linea_particion", angulo="3 deg", lados="uno")
    with pytest.raises(ErrorComando):
        cmd.construir(v, ctx)                                                  # falta la herramienta de partición
    v["herramienta_particion"] = [hit_desde_ref({"tipo": "plano", "id": "XY"}, doc.estado_final)]
    op = cmd.construir(v, ctx)
    assert op.p["tipo"] == "linea_particion" and op.p["modo_angulo"] == "relativo" and op.p["herramienta_particion"]
    doc.agregar(op)
    assert doc.resultados[-1].estado == "ok", doc.resultados[-1].mensaje


def test_apoyo_dialogo_construye_reabre_y_valida(doc):
    """PLÁSTICO › Apoyo (comandos de plástico): sin perfiles el diálogo falla; construido y ejecutado sobre la
    caja vaciada rellena el hueco con el prisma del perfil (20×20 de 4 mm de aire) y `desde_op` lo devuelve igual."""
    from omnicad.timeline.operaciones import OpExtrusion
    from omnicad.ui.comandos.plastico import Apoyo
    s = api.Sesion(doc)
    cid = next(iter(doc.estado_final.cuerpos))
    assert api.llamar(s, "shell", {"body": cid, "faces": ">Z", "thickness": 2})["ok"]
    r = api.llamar(s, "create_sketch", {"plane": "XY"})
    assert r["ok"], r
    boceto = r["result"]["sketch"]["id"]
    for x1, y1, x2, y2 in [(10, 10, 30, 10), (30, 10, 30, 30), (30, 30, 10, 30), (10, 30, 10, 10)]:
        r = api.llamar(s, "draw_line", {"sketch": boceto, "start_x": x1, "start_y": y1, "end_x": x2, "end_y": y2})
        assert r["ok"], r
    perfil = doc.estado_final.bocetos[boceto].perfiles[0]
    hits = [hit_desde_ref({"tipo": "perfil", "boceto": boceto, **OpExtrusion.referencia_perfil(perfil)},
                          doc.estado_final)]
    cmd, ctx = Apoyo(), ContextoComando(doc)
    v = _valores(cmd, ctx)
    with pytest.raises(ErrorComando):
        cmd.construir(v, ctx)                                                  # sin perfiles ni cuerpo
    op = cmd.construir(dict(v, perfiles=hits, cuerpo=[hit_desde_ref({"tipo": "cuerpo", "cuerpo": cid},
                                                                    doc.estado_final)]), ctx)
    volumen_antes = geo.volumen(doc.estado_final.cuerpos[cid].forma)
    doc.agregar(op)
    assert doc.resultados[-1].estado == "ok", doc.resultados[-1].mensaje
    assert geo.volumen(doc.estado_final.cuerpos[cid].forma) == pytest.approx(volumen_antes + 20 * 20 * 4, rel=1e-6)
    vuelta = cmd.desde_op(op, ContextoComando(doc, op=op))
    assert len(vuelta["perfiles"]) == 1 and cmd.construir(vuelta, ContextoComando(doc)).p == op.p
