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
