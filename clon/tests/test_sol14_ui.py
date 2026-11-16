# -*- coding: utf-8 -*-
"""SOL-14 en los diálogos de Patrón y Simetría: caras, componentes, geometría de construcción y cálculo."""
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
from omnicad.ui.comandos.crear import PatronRectangular, Simetria  # noqa: E402


@pytest.fixture
def doc():
    QApplication.instance() or QApplication([])
    d = Documento()
    d.agregar(OpPrimitiva(d.nuevo_id(), forma="caja", ancho="20", largo="20", alto="10"))
    return d


def _valores(cmd, ctx):
    return {c.clave: (list(c.defecto) if isinstance(c.defecto, list) else c.defecto) for c in cmd.campos(ctx)}


def _hit_cara(doc, selector):
    c, e = sl.elegir_uno(api.Sesion(doc), selector, "cara")
    return hit_desde_ref(sl.referencia(c, e), doc.estado_final)


def _ejecutar(doc, cmd, **valores):
    ctx = ContextoComando(doc)
    v = _valores(cmd, ctx)
    v.update(valores)
    op = cmd.construir(v, ctx)
    doc.agregar(op)
    return op


def test_simetria_de_caras_en_el_dialogo(doc):
    plano = hit_desde_ref({"tipo": "plano", "id": "YZ"}, doc.estado_final)
    cmd, ctx = Simetria(), ContextoComando(doc)
    v = _valores(cmd, ctx)
    v.update(objeto="caras", plano=[plano])
    with pytest.raises(ErrorComando, match="caras"):
        cmd.construir(v, ctx)                                                   # sin caras elegidas
    op = _ejecutar(doc, cmd, objeto="caras", caras=[_hit_cara(doc, ">Z")], plano=[plano])
    sup = [c for c in doc.estado_final.cuerpos.values() if c.tipo == "superficie"]
    assert len(sup) == 1 and geo.area(sup[0].forma) == pytest.approx(400)
    assert cmd.desde_op(op, ContextoComando(doc, op=op))["objeto"] == "caras"


def _componente_taco(doc):
    r = api.llamar(api.Sesion(doc), "create_component", {"bodies": ["op1.c1"], "name": "Taco"})
    assert r["ok"], r
    return doc.estado_final.cuerpos["op1.c1"].componente


def test_patron_de_componentes_y_de_construccion_en_el_dialogo(doc):
    k = _componente_taco(doc)
    eje = hit_desde_ref({"tipo": "eje", "id": "X"}, doc.estado_final)
    cmd = PatronRectangular()
    ctx = ContextoComando(doc)
    v = _valores(cmd, ctx)
    v.update(objeto="componentes", dir1=[eje], n1=3, d1="40 mm")
    with pytest.raises(ErrorComando, match="Seleccioná los componentes"):
        cmd.construir(v, ctx)
    taco = hit_desde_ref({"tipo": "componente", "componente": k}, doc.estado_final)   # B-600: clic en el navegador
    op = _ejecutar(doc, cmd, objeto="componentes", componentes=[taco], dir1=[eje], n1=3, d1="40 mm")
    assert len(doc.estado_final.componentes) == 3
    assert sum(geo.volumen(c.forma) for c in doc.estado_final.cuerpos.values()) == pytest.approx(3 * 4000)
    assert [h["ref"] for h in cmd.desde_op(op, ContextoComando(doc, op=op))["componentes"]] == [taco["ref"]]
    plano = hit_desde_ref({"tipo": "plano", "id": "XY"}, doc.estado_final)
    _ejecutar(doc, cmd, objeto="construccion", construccion=[plano], dir1=[eje], n1=3, d1="40 mm")
    assert len([k for k in doc.estado_final.planos if "_k" in k]) == 2


def test_patron_de_operaciones_con_calculo_ajustar_en_el_dialogo(doc):
    api.llamar(api.Sesion(doc), "create_hole", {"face": ">Z", "diameter": 4, "depth": 5, "points": [[2, 0]]})
    eje = hit_desde_ref({"tipo": "eje", "id": "X"}, doc.estado_final)
    cmd = PatronRectangular()
    ctx = ContextoComando(doc)
    assert {"calculo", "caras", "componentes", "construccion"} <= {c.clave for c in cmd.campos(ctx)}
    paso = next(o.nombre for o in doc.operaciones if o.TIPO == "agujero")
    op = cmd.construir(dict(_valores(cmd, ctx), objeto="operaciones", pasos=paso, calculo="ajustar", dir1=[eje],
                            n1=3, d1="15 mm", distribucion="espaciado"), ctx)
    assert op.p["calculo"] == "ajustar"
    r = doc.agregar(op)
    assert r.estado == "aviso" and "no tocan al cuerpo" in r.mensaje


def test_tocar_un_cuerpo_en_la_vista_elige_su_componente(doc):
    """B-600: con «Tipo de objeto» Componentes, el clic en un cuerpo de la vista elige su componente (como Fusion);
    un cuerpo sin componente no vale y lo dice."""
    from omnicad.ui.comandos.patrones import Multitransformar
    k = _componente_taco(doc)
    cuerpo = hit_desde_ref({"tipo": "cuerpo", "cuerpo": "op1.c1"}, doc.estado_final)
    ctx = ContextoComando(doc)
    for cmd in (PatronRectangular(), Simetria(), Multitransformar()):
        campo = next(c for c in cmd.campos(ctx) if c.clave == "componentes")
        assert cmd.ajustar_hit(campo, cuerpo, ctx, None)["ref"] == {"tipo": "componente", "componente": k}
    eje = hit_desde_ref({"tipo": "eje", "id": "X"}, doc.estado_final)
    cmd = PatronRectangular()
    op = _ejecutar(doc, cmd, objeto="componentes", componentes=[cuerpo], dir1=[eje], n1=2, d1="40 mm")
    assert op.p["componentes"] == [k]
    api.llamar(api.Sesion(doc), "create_box", {"length": 5, "width": 5, "height": 5, "name": "Suelto"})
    suelto = next(c for c, cu in doc.estado_final.cuerpos.items() if cu.nombre == "Suelto")
    v = dict(_valores(cmd, ContextoComando(doc)), objeto="componentes", dir1=[eje], n1=2, d1="10 mm",
             componentes=[hit_desde_ref({"tipo": "cuerpo", "cuerpo": suelto}, doc.estado_final)])
    with pytest.raises(ErrorComando, match="«Suelto» no está en un componente"):
        cmd.construir(v, ContextoComando(doc))


def test_construccion_y_caras_vuelven_a_cargarse_al_editar(doc):
    eje = hit_desde_ref({"tipo": "eje", "id": "X"}, doc.estado_final)
    plano = hit_desde_ref({"tipo": "plano", "id": "XY"}, doc.estado_final)
    cmd = PatronRectangular()
    op = _ejecutar(doc, cmd, objeto="construccion", construccion=[plano], dir1=[eje], n1=2, d1="40 mm")
    v = cmd.desde_op(op, ContextoComando(doc, op=op))
    assert v["objeto"] == "construccion" and [h["ref"]["id"] for h in v["construccion"]] == ["XY"]
    assert cmd.construir(v, ContextoComando(doc, op=op)).p["construccion"] == op.p["construccion"]
    op2 = _ejecutar(doc, cmd, objeto="caras", caras=[_hit_cara(doc, ">Z")], dir1=[eje], n1=2, d1="30 mm")
    v2 = cmd.desde_op(op2, ContextoComando(doc, op=op2))
    assert v2["objeto"] == "caras" and len(v2["caras"]) == 1
    assert cmd.construir(v2, ContextoComando(doc, op=op2)).p["caras"] == op2.p["caras"]


def test_origen_del_solido_envolvente_en_el_dialogo(doc):
    from omnicad.ui.comandos.crear import SolidoEnvolvente
    cmd, ctx = SolidoEnvolvente(), ContextoComando(doc)
    cuerpo = hit_desde_ref({"tipo": "cuerpo", "cuerpo": "op1.c1"}, doc.estado_final)
    op = _ejecutar(doc, cmd, cuerpos=[cuerpo], componente=True, origen="esquina")
    assert op.p["origen"] == "esquina"
    assert cmd.desde_op(op, ContextoComando(doc, op=op))["origen"] == "esquina"
    sin = cmd.construir(dict(_valores(cmd, ctx), cuerpos=[cuerpo], origen="centro"), ctx)
    assert sin.p["origen"] == "modelo"                                          # sin componente nuevo no hay origen
