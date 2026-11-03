# -*- coding: utf-8 -*-
"""PLA-9, tercera parte: «Reemplazar con primitivas» (Fusion › Simplificar › Replace with Primitives): un cuerpo por
componente envuelto, una caja, un cilindro (eje X, Y o Z) o la esfera mínima, y los cuerpos originales se van, todo
en un solo paso del timeline."""
import math
import os

import numpy as np
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva
from omnicad.timeline.ops_solido import OpSolidoEnvolvente


@pytest.fixture(scope="module", autouse=True)
def app_qt():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _llamar(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"], r
    return r["result"]


def _cuerpos(sesion):
    return list(sesion.doc.estado_final.cuerpos.values())


def _dos_cajas():
    s = api.Sesion()
    _llamar(s, "create_box", length=20, width=20, height=20, name="A", anchor="corner")
    _llamar(s, "create_box", length=10, width=10, height=10, x=30, name="B", anchor="corner")   # de x=30 a 40: separada
    return s


def _doc_dos_cajas():
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="20", largo="20", alto="20"))
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="10", largo="10", alto="10", x="30"))
    return doc


def test_dos_cajas_quedan_en_una_caja_que_las_envuelve_y_deshacer_las_vuelve():
    s = _dos_cajas()
    res = _llamar(s, "replace_with_primitive", bodies=["A", "B"], shape="box")
    assert res["bodies_removed"] == ["op1.c1", "op2.c1"] and len(res["bodies_created"]) == 1
    assert len(_cuerpos(s)) == 1
    forma = _cuerpos(s)[0].forma
    assert geo.es_valida(forma)
    assert np.allclose(geo.caja_envolvente(forma), [(0, 0, 0), (40, 20, 20)], atol=1e-6)
    assert geo.volumen(forma) == pytest.approx(40 * 20 * 20)
    _llamar(s, "undo")
    assert sorted(c.id for c in _cuerpos(s)) == ["op1.c1", "op2.c1"]
    assert sorted(geo.volumen(c.forma) for c in _cuerpos(s)) == pytest.approx([1000, 8000])


def test_cilindro_con_eje_z_sale_con_el_mismo_volumen():
    s = api.Sesion()
    _llamar(s, "create_cylinder", radius=10, height=50, name="Eje")
    _llamar(s, "replace_with_primitive", bodies=["Eje"], shape="cylinder", axis="z")
    assert len(_cuerpos(s)) == 1
    forma = _cuerpos(s)[0].forma
    assert geo.es_valida(forma)
    assert geo.volumen(forma) == pytest.approx(math.pi * 10 ** 2 * 50, rel=1e-5)   # el cilindro se tesela y se rehace
    assert np.allclose(geo.caja_envolvente(forma), [(-10, -10, 0), (10, 10, 50)], atol=1e-3)   # eje Z


def test_caja_de_10_con_esfera_da_radio_cinco_raiz_de_tres():
    s = api.Sesion()
    _llamar(s, "create_box", length=10, width=10, height=10, name="Cubo", anchor="corner")
    _llamar(s, "replace_with_primitive", bodies=["Cubo"], shape="sphere")
    forma = _cuerpos(s)[0].forma
    assert geo.es_valida(forma)
    esquinas = [(5 - 5 * math.sqrt(3),) * 3, (5 + 5 * math.sqrt(3),) * 3]
    assert np.allclose(geo.caja_envolvente(forma), esquinas, atol=1e-6)
    assert geo.volumen(forma) == pytest.approx(4 / 3 * math.pi * (5 * math.sqrt(3)) ** 3, rel=1e-6)


def test_forma_invalida_y_eje_invalido_fallan_sin_tocar_el_documento():
    s = _dos_cajas()
    for args in ({"shape": "tube"}, {"shape": "cylinder", "axis": "w"}):
        r = api.llamar(s, "replace_with_primitive", {"bodies": ["A", "B"], **args})
        assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS", r
    assert len(_cuerpos(s)) == 2 and len(s.doc.operaciones) == 2


def test_dos_componentes_dejan_una_primitiva_en_cada_uno():
    """Como Fusion: con cuerpos de componentes distintos, cada componente conserva su volumen, ya envuelto."""
    s = _dos_cajas()
    _llamar(s, "create_component", bodies=["A"], name="P1")
    _llamar(s, "create_component", bodies=["B"], name="P2")
    _llamar(s, "replace_with_primitive", bodies=["A", "B"], shape="box")
    cuerpos = _cuerpos(s)
    assert len(cuerpos) == 2 and cuerpos[0].componente != cuerpos[1].componente
    assert max(geo.volumen(c.forma) for c in cuerpos) == pytest.approx(8000)    # sin una envolvente común de los dos
    assert sum(geo.volumen(c.forma) for c in cuerpos) == pytest.approx(20 ** 3 + 10 ** 3)


def test_comando_construye_y_se_reabre_del_timeline():
    from omnicad.ui.comando import ContextoComando, ErrorComando, hit_desde_ref
    from omnicad.ui.comandos import comando_para
    from omnicad.ui.comandos.modificar import ReemplazarPrimitivas
    doc = _doc_dos_cajas()
    cmd = ReemplazarPrimitivas()
    ctx = ContextoComando(doc)
    v = {c.clave: (list(c.defecto) if isinstance(c.defecto, list) else c.defecto) for c in cmd.campos(ctx)}
    cuerpos = [hit_desde_ref({"tipo": "cuerpo", "cuerpo": "op1.c1"}, doc.estado_final),
               hit_desde_ref({"tipo": "cuerpo", "cuerpo": "op2.c1"}, doc.estado_final)]
    op = cmd.construir({**v, "cuerpos": cuerpos, "tipo": "cilindro", "eje": "x"}, ctx)
    assert isinstance(op, OpSolidoEnvolvente) and op.p["reemplazar"] is True
    assert doc.agregar(op).estado in ("ok", "aviso")
    assert len(doc.estado_final.cuerpos) == 1
    assert comando_para(op) is ReemplazarPrimitivas                 # el doble clic en el timeline abre este comando
    v2 = ReemplazarPrimitivas().desde_op(op, ContextoComando(doc, op=op))
    assert [h["ref"]["cuerpo"] for h in v2["cuerpos"]] == ["op1.c1", "op2.c1"]
    assert (v2["tipo"], v2["eje"]) == ("cilindro", "x")
    assert comando_para(OpSolidoEnvolvente(doc.nuevo_id(), "Sólido envolvente1", cuerpos=["op1.c1"])) is not ReemplazarPrimitivas
    with pytest.raises(ErrorComando, match="Seleccioná los cuerpos"):
        ReemplazarPrimitivas().construir({**v, "cuerpos": []}, ContextoComando(doc))


def test_la_previa_dibuja_la_primitiva_translucida():
    from omnicad.ui.comando import ContextoComando, hit_desde_ref
    from omnicad.ui.comandos.modificar import ReemplazarPrimitivas
    doc = _doc_dos_cajas()
    cmd = ReemplazarPrimitivas()
    ctx = ContextoComando(doc)
    cuerpos = [hit_desde_ref({"tipo": "cuerpo", "cuerpo": c}, doc.estado_final) for c in ("op1.c1", "op2.c1")]
    v = {c.clave: (list(c.defecto) if isinstance(c.defecto, list) else c.defecto) for c in cmd.campos(ctx)}
    prims = cmd.previa_vista(ctx, {**v, "cuerpos": cuerpos, "tipo": "caja"}, None)
    assert len(prims) == 1 and prims[0][0] == "tris" and prims[0][3] < 1
    assert np.allclose(prims[0][1].min(axis=0), (0, 0, 0), atol=1e-6)
    assert np.allclose(prims[0][1].max(axis=0), (40, 20, 20), atol=1e-6)
    assert cmd.previa_vista(ctx, {**v, "cuerpos": [], "tipo": "caja"}, None) is None
    assert cmd.previa_vista(ctx, {**v, "cuerpos": cuerpos, "tipo": "caja", "margen": "("}, None) is None
