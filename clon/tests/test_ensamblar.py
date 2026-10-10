# -*- coding: utf-8 -*-
"""ENSAMBLAR: componentes, uniones (posición y movimiento), grupos rígidos, vínculos e insertar diseños."""
import copy
import os

import numpy as np
import pytest

from omnicad.nucleo import geometria as g
from omnicad.nucleo import referencias as refs
from omnicad.timeline import entidades as ent
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva
from omnicad.timeline.ops_ensamblar import (OpComponente, OpGrupoRigido, OpInsertarDiseno, OpOrigenUnion, OpUnion,
                                            OpVinculoMovimiento, marco_de)


@pytest.fixture(scope="module", autouse=True)
def app_qt():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _cara(doc, cid, centro):
    f = doc.estado_final.cuerpos[cid].forma
    sub = next(s for s in refs.subformas(f, "cara") if np.allclose(refs.firma_cara(s)["centro"], centro))
    return refs.referencia(cid, sub, f)


def _doc_dos_cajas():
    """Base 40×40×10 en el origen (componente fijo) y un bloque 10×10×10 lejos (componente móvil)."""
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="40", largo="40", alto="10"))
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="10", largo="10", alto="10", x="100", y="50"))
    doc.agregar(OpComponente(doc.nuevo_id(), "Base", cuerpos=["op1.c1"], fijo=True))
    doc.agregar(OpComponente(doc.nuevo_id(), "Bloque", cuerpos=["op2.c1"]))
    return doc


def _caja(doc, cid="op2.c1"):
    return g.caja_envolvente(doc.estado_final.cuerpos[cid].forma)


def test_union_rigida_apoya_el_bloque_sobre_la_base():
    doc = _doc_dos_cajas()
    # cara de abajo del bloque contra la cara de arriba de la base: quedan enfrentadas (como en Fusion)
    doc.agregar(OpUnion(doc.nuevo_id(), "Unión1", tipo="rigida", origen1=_cara(doc, "op2.c1", (105, 55, 0)),
                        origen2=_cara(doc, "op1.c1", (20, 20, 10))))
    (x0, y0, z0), (x1, y1, z1) = _caja(doc)
    assert (x0, y0, z0, x1, y1, z1) == pytest.approx((15, 15, 10, 25, 25, 20))
    assert doc.estado_final.componentes["op4"]["nombre"] == "Bloque"


def test_union_de_revolucion_gira_y_se_acciona():
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.ensamblar import AccionarUniones
    doc = _doc_dos_cajas()
    op = OpUnion(doc.nuevo_id(), "Unión1", tipo="revolucion", origen1=_cara(doc, "op2.c1", (105, 55, 0)),
                 origen2=_cara(doc, "op1.c1", (20, 20, 10)), dx="10 mm", giro="0 deg")
    doc.agregar(op)
    (x0, y0, _), (x1, y1, _) = _caja(doc)
    assert (x0, x1) == pytest.approx((25, 35)) or (y0, y1) == pytest.approx((25, 35))
    cmd = AccionarUniones()
    ctx = ContextoComando(doc)
    cmd.aplicar({"union": op.id, "giro": "180 deg", "desliz": "0 mm"}, ctx)
    (x0, y0, _), (x1, y1, _) = _caja(doc)
    assert (min(x0, y0), max(x1, y1)) == pytest.approx((5, 25), abs=1e-6)    # giró 180° alrededor del centro
    assert doc.estado_final.uniones[op.id]["valores"]["giro"] == pytest.approx(180)


def test_componente_fijo_no_se_mueve_y_limites():
    doc = _doc_dos_cajas()
    res = doc.agregar(OpUnion(doc.nuevo_id(), "Mal", tipo="rigida", origen1=_cara(doc, "op1.c1", (20, 20, 10)),
                              origen2=_cara(doc, "op2.c1", (105, 55, 0))))
    assert res.estado == "error" and "fijo" in res.mensaje
    doc = _doc_dos_cajas()
    doc.agregar(OpUnion(doc.nuevo_id(), "Desliz", tipo="deslizante", eje_desliz="Z", desliz="50 mm", maximo="5 mm",
                        origen1=_cara(doc, "op2.c1", (105, 55, 0)), origen2=_cara(doc, "op1.c1", (20, 20, 10))))
    (_, _, z0), _ = _caja(doc)
    assert z0 == pytest.approx(15)               # el límite máximo cortó el deslizamiento en 5 mm


def test_union_como_esta_e_insertar_diseno():
    doc = _doc_dos_cajas()
    doc.agregar(OpUnion(doc.nuevo_id(), "Giro", tipo="revolucion", como_esta=True, giro="90 deg",
                        origen1=_cara(doc, "op2.c1", (105, 55, 10))))
    (x0, y0, z0), (x1, y1, z1) = _caja(doc)
    assert (x0, x1, y0, y1, z0, z1) == pytest.approx((100, 110, 50, 60, 0, 10))   # giró sobre su propio centro
    otro = Documento()
    otro.agregar(OpPrimitiva(otro.nuevo_id(), forma="cilindro", radio="3", alto="20"))
    doc.agregar(OpInsertarDiseno(doc.nuevo_id(), "Insertar pasador", archivo="pasador", receta=otro.a_dict()))
    ins = [c for c in doc.estado_final.cuerpos.values() if c.componente == doc.operaciones[-1].id]
    assert len(ins) == 1 and g.volumen(ins[0].forma) == pytest.approx(np.pi * 9 * 20)
    assert Documento.desde_dict(doc.a_dict()).estado_final.componentes


def test_union_con_tapa_de_revolucion_no_da_vuelta_la_pieza():
    """La tapa plana de una revolución tiene ejes indirectos: su normal hacia afuera es −eje. Antes la unión
    rígida tomaba +eje y daba vuelta la pantalla de una lámpara (cúpula apuntando para abajo)."""
    from omnicad.api import Sesion, llamar
    s = Sesion()
    llamar(s, "sketch_from_spec", {"plane": "XZ", "entities": [
        {"type": "arc", "id": "ext", "center": [0, 0], "start": [50, 0], "sweep": 90},
        {"type": "line", "id": "eje", "start": [0, 50], "end": [0, 48]},
        {"type": "arc", "id": "int", "center": [0, 0], "start": [48, 0], "sweep": 90},
        {"type": "line", "id": "borde", "start": [48, 0], "end": [50, 0]}],
        "constraints": [{"type": "coincident", "entities": ["ext.end", "eje.start"]},
                        {"type": "coincident", "entities": ["eje.end", "int.end"]},
                        {"type": "coincident", "entities": ["int.start", "borde.start"]},
                        {"type": "coincident", "entities": ["borde.end", "ext.start"]}]})
    assert llamar(s, "revolve", {"sketch": "op1", "profile": 0, "axis": "sketch_y"})["ok"]
    assert llamar(s, "create_cylinder", {"radius": 5, "height": 10, "z": -10})["ok"]
    doc = s.doc
    aro = _cara(doc, "op2.c1", (0, 0, 0))
    assert refs.firma_cara(next(x for x in refs.subformas(doc.estado_final.cuerpos["op2.c1"].forma, "cara")
                                if refs.firma_cara(x)["geom"] == "plano"))["normal"] == pytest.approx([0, 0, -1])
    doc.agregar(OpComponente(doc.nuevo_id(), "Soporte", cuerpos=["op3.c1"], fijo=True))
    doc.agregar(OpComponente(doc.nuevo_id(), "Pantalla", cuerpos=["op2.c1"]))
    doc.agregar(OpUnion(doc.nuevo_id(), "Unión1", tipo="rigida", origen1=aro, origen2=_cara(doc, "op3.c1", (0, 0, 0))))
    assert doc.resultados[-1].estado == "ok"
    caja = g.caja_envolvente(doc.estado_final.cuerpos["op2.c1"].forma)
    assert caja[0][2] == pytest.approx(0, abs=1e-3) and caja[1][2] == pytest.approx(50, abs=1e-3)
    assert g.es_valida(doc.estado_final.cuerpos["op2.c1"].forma)


# ---------------------------------------------------------------- hallazgos de las pruebas de uso (P08)
def _cara_donde(doc, cid, condicion):
    f = doc.estado_final.cuerpos[cid].forma
    sub = next(s for s in refs.subformas(f, "cara") if condicion(refs.firma_cara(s)))
    return refs.referencia(cid, sub, f)


def _es_cilindro(f):
    return f["geom"] == "cilindro"


def _sin_version_marco(receta):
    """La receta como la guardaba un OmniCAD anterior: uniones sin «version_marco», vínculos sin
    «version_vinculo»."""
    receta = copy.deepcopy(receta)
    for d in receta["operaciones"]:
        if d["tipo"] in ("union", "origen_union", "vinculo_movimiento"):
            d["params"].pop("version_vinculo" if d["tipo"] == "vinculo_movimiento" else "version_marco")
    return receta


def test_union_sobre_cara_con_agujeros_engancha_el_centro_del_contorno():
    """La tapa se corría 0,1 mm: el origen era el centroide de ÁREA de la cara agujereada. Fusion engancha
    el centro del contorno exterior."""
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="40", largo="40", alto="10"))
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="40", largo="40", alto="3", x="100"))
    for x, y in (("108", "8"), ("130", "10")):
        doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="cilindro", radio="2", alto="3", x=x, y=y, operacion="cortar",
                                objetivo="op2.c1"))
    doc.agregar(OpComponente(doc.nuevo_id(), "Base", cuerpos=["op1.c1"], fijo=True))
    doc.agregar(OpComponente(doc.nuevo_id(), "Tapa", cuerpos=["op2.c1"]))
    abajo = _cara_donde(doc, "op2.c1", lambda f: f.get("normal") == pytest.approx([0, 0, -1]))
    res = doc.agregar(OpUnion(doc.nuevo_id(), "Unión1", tipo="rigida", origen1=abajo,
                              origen2=_cara(doc, "op1.c1", (20, 20, 10))))
    assert res.estado == "ok"
    (x0, y0, z0), (x1, y1, z1) = _caja(doc, "op2.c1")
    assert (x0, y0, z0, x1, y1, z1) == pytest.approx((0, 0, 10, 40, 40, 13), abs=1e-6)
    assert g.es_valida(doc.estado_final.cuerpos["op2.c1"].forma)
    (x0, y0, _), _ = _caja(Documento.desde_dict(_sin_version_marco(doc.a_dict())), "op2.c1")
    assert abs(x0) + abs(y0) > 0.1            # una receta vieja conserva su marco (no cambia al abrirla)


def test_marco_de_un_cilindro_no_depende_del_sentido_de_su_eje():
    """El eje de un agujero (−Z) y el de un saliente (+Z) daban marcos opuestos, con la X dada vuelta: la
    manivela quedaba girada 180°. Ahora el eje y la X son los del mundo y el origen está en el eje."""
    saliente = g.cilindro(5, 10)
    agujero = g.booleano(g.caja(40, 40, 10, (-20, -20, 0)), g.cilindro(5, 10, base=(0, 0, 10), eje=(0, 0, -1)),
                         "cortar")
    for forma in (saliente, agujero):
        cara = next(s for s in refs.subformas(forma, "cara") if _es_cilindro(refs.firma_cara(s)))
        e = ent.Entidad("cara", forma=cara, cuerpo="x", plano=g.plano_de_cara(cara))
        F = marco_de(e, "centro", 2)
        assert F[:3, 2] == pytest.approx([0, 0, 1]) and F[:3, 0] == pytest.approx([1, 0, 0])
        assert F[:3, 3] == pytest.approx([0, 0, 5], abs=1e-9)                  # medio del cilindro, sobre el eje
        assert marco_de(e, "inicio", 2)[:3, 3] == pytest.approx([0, 0, 0], abs=1e-9)
        assert marco_de(e, "fin", 2)[:3, 3] == pytest.approx([0, 0, 10], abs=1e-9)
        arista = next(a for a in refs.subformas(forma, "arista") if refs.firma_arista(a)["geom"] == "circulo"
                      and refs.firma_arista(a)["centro"][2] == pytest.approx(10))
        Fa = marco_de(ent.Entidad("arista", forma=arista, cuerpo="x"), "centro", 2)
        assert Fa[:3, 2] == pytest.approx([0, 0, 1]) and Fa[:3, 0] == pytest.approx([1, 0, 0])
        assert Fa[:3, 3] == pytest.approx([0, 0, 10], abs=1e-9)
    cara = next(s for s in refs.subformas(agujero, "cara") if _es_cilindro(refs.firma_cara(s)))
    viejo = marco_de(ent.Entidad("cara", forma=cara, cuerpo="x"), "centro", 1)
    assert viejo[:3, 2] == pytest.approx([0, 0, -1])                            # el marco de las recetas viejas


def _doc_perno_y_placa():
    """Placa 40×40×10 fija con un agujero Ø10 en el origen y un perno Ø10×20 lejos, unidos de revolución."""
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="40", largo="40", alto="10", x="-20", y="-20"))
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="cilindro", radio="5", alto="10", operacion="cortar",
                            objetivo="op1.c1"))
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="cilindro", radio="5", alto="20", x="100"))
    doc.agregar(OpComponente(doc.nuevo_id(), "Placa", cuerpos=["op1.c1"], fijo=True))
    doc.agregar(OpComponente(doc.nuevo_id(), "Perno", cuerpos=["op3.c1"]))
    doc.agregar(OpUnion(doc.nuevo_id(), "Unión1", tipo="revolucion", origen1=_cara_donde(doc, "op3.c1", _es_cilindro),
                        origen2=_cara_donde(doc, "op1.c1", _es_cilindro)))
    return doc


def test_perno_en_agujero_no_gira_ni_se_da_vuelta():
    doc = _doc_perno_y_placa()
    assert doc.resultados[-1].estado == "ok"
    M = np.asarray(doc.estado_final.componentes["op5"]["matriz"])
    assert M[:3, :3] == pytest.approx(np.identity(3), abs=1e-9)
    assert M[:3, 3] == pytest.approx([-100, 0, -5], abs=1e-9)          # el medio del perno, al medio del agujero
    assert g.es_valida(doc.estado_final.cuerpos["op3.c1"].forma)
    vieja = Documento.desde_dict(_sin_version_marco(doc.a_dict()))
    R = np.asarray(vieja.estado_final.componentes["op5"]["matriz"])[:3, :3]
    assert R == pytest.approx(np.diag([1.0, -1.0, -1.0]), abs=1e-9)    # la receta vieja abre igual que antes


def test_editar_una_union_vieja_conserva_su_marco():
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.ensamblar import Union
    vieja = Documento.desde_dict(_sin_version_marco(_doc_perno_y_placa().a_dict()))
    op = vieja.operacion("op6")
    assert op.p["version_marco"] == 1
    cmd, ctx = Union(), ContextoComando(vieja, op=op)
    v = cmd.desde_op(op, ctx)
    assert cmd.construir(v, ctx).p["version_marco"] == 1
    assert cmd.construir(v, ContextoComando(vieja)).p["version_marco"] == 2       # una unión nueva: marco nuevo


def test_union_que_da_vuelta_el_componente_avisa():
    doc = _doc_dos_cajas()
    res = doc.agregar(OpUnion(doc.nuevo_id(), "Arriba", tipo="rigida", origen1=_cara(doc, "op2.c1", (105, 55, 10)),
                              origen2=_cara(doc, "op1.c1", (20, 20, 10))))
    assert res.estado == "aviso" and "Voltear" in res.mensaje
    res = doc.reemplazar("op5", OpUnion("op5", "Arriba", **dict(doc.operacion("op5").p, voltear=True)))
    assert res.estado == "ok"


def test_union_como_esta_sigue_al_componente_padre():
    """La unión «como está» guardaba comp2 = raíz: el perno no seguía a la manivela al accionarla."""
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="100", largo="100", alto="10"))
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="10", largo="10", alto="10", x="45", y="45", z="10"))
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="4", largo="4", alto="10", x="52", y="48", z="20"))
    doc.agregar(OpComponente(doc.nuevo_id(), "Base", cuerpos=["op1.c1"], fijo=True))
    doc.agregar(OpComponente(doc.nuevo_id(), "Manivela", cuerpos=["op2.c1"]))
    doc.agregar(OpComponente(doc.nuevo_id(), "Perno", cuerpos=["op3.c1"]))
    giro = OpUnion(doc.nuevo_id(), "Giro", tipo="revolucion", origen1=_cara(doc, "op2.c1", (50, 50, 10)),
                   origen2=_cara(doc, "op1.c1", (50, 50, 10)))
    doc.agregar(giro)
    res = doc.agregar(OpUnion(doc.nuevo_id(), "Perno", tipo="rigida", como_esta=True,
                              origen1=_cara(doc, "op3.c1", (54, 50, 30)), origen2={"tipo": "cuerpo", "cuerpo": "op2.c1"}))
    assert res.estado == "ok" and doc.estado_final.uniones["op8"]["comp2"] == "op5"
    (x0, y0, z0), (x1, y1, z1) = _caja(doc, "op3.c1")
    assert (x0, y0, z0, x1, y1, z1) == pytest.approx((52, 48, 20, 56, 52, 30), abs=1e-6)     # queda donde está
    doc.reemplazar("op7", OpUnion("op7", "Giro", **dict(giro.p, giro="90 deg")))
    (x0, y0, z0), (x1, y1, z1) = _caja(doc, "op3.c1")
    assert (x0, y0, z0, x1, y1, z1) == pytest.approx((48, 52, 20, 52, 56, 30), abs=1e-6)     # giró con la manivela
    assert g.es_valida(doc.estado_final.cuerpos["op3.c1"].forma)


def test_comando_union_como_esta_pide_el_componente_2():
    from omnicad.ui.comando import ContextoComando, ErrorComando, hit_desde_ref
    from omnicad.ui.comandos.ensamblar import UnionComoEsta
    doc = _doc_dos_cajas()
    cmd, ctx = UnionComoEsta(), ContextoComando(doc)
    assert "origen2" in [c.clave for c in cmd.campos(ctx)]
    v = dict(OpUnion.PARAMS, origen1=[hit_desde_ref(_cara(doc, "op2.c1", (105, 55, 10)), doc.estado_final)], origen2=[])
    with pytest.raises(ErrorComando):
        cmd.construir(v, ctx)
    v["origen2"] = [hit_desde_ref({"tipo": "cuerpo", "cuerpo": "op1.c1"}, doc.estado_final)]
    op = cmd.construir(v, ctx)
    assert op.p["como_esta"] and op.p["origen2"] == {"tipo": "cuerpo", "cuerpo": "op1.c1"}
    assert doc.agregar(op).estado == "ok" and doc.estado_final.uniones[op.id]["comp2"] == "op3"


def _doc_mecanismo():
    """Base fija, manivela de revolución a 60° y pistón deslizante a 50 mm (como el mecanismo de las pruebas)."""
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="100", largo="100", alto="10"))
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="10", largo="10", alto="10", x="200"))
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="10", largo="10", alto="10", x="300"))
    doc.agregar(OpComponente(doc.nuevo_id(), "Base", cuerpos=["op1.c1"], fijo=True))
    doc.agregar(OpComponente(doc.nuevo_id(), "Manivela", cuerpos=["op2.c1"]))
    doc.agregar(OpComponente(doc.nuevo_id(), "Piston", cuerpos=["op3.c1"]))
    arriba = _cara(doc, "op1.c1", (50, 50, 10))
    doc.agregar(OpUnion(doc.nuevo_id(), "J1", tipo="revolucion", giro="60 deg", origen1=_cara(doc, "op2.c1", (205, 5, 0)),
                        origen2=arriba))
    doc.agregar(OpUnion(doc.nuevo_id(), "J2", tipo="deslizante", eje_desliz="X", desliz="50 mm",
                        origen1=_cara(doc, "op3.c1", (305, 5, 0)), origen2=arriba))
    return doc


def test_vinculo_de_movimiento_reemplaza_el_valor_de_la_union_2():
    """Con factor 0,2 y la manivela a 60°, el pistón tiene que quedar a 12 mm: antes sumaba 12 sobre los 50."""
    doc = _doc_mecanismo()
    assert _caja(doc, "op3.c1")[0][0] == pytest.approx(95)
    res = doc.agregar(OpVinculoMovimiento(doc.nuevo_id(), "V", union1="op7", union2="op8", factor="0.2"))
    assert res.estado == "ok"
    assert _caja(doc, "op3.c1")[0][0] == pytest.approx(57)
    assert doc.estado_final.uniones["op8"]["valores"]["desliz"] == pytest.approx(12)
    assert doc.estado_en(doc.indice("op9")).uniones["op8"]["valores"]["desliz"] == pytest.approx(50)   # sin pisar
    vieja = Documento.desde_dict(_sin_version_marco(doc.a_dict()))
    assert _caja(vieja, "op3.c1")[0][0] == pytest.approx(107)        # la receta vieja abre igual que antes


def test_grupo_rigido_acepta_nombres_y_lista_los_componentes():
    doc = _doc_mecanismo()
    res = doc.agregar(OpGrupoRigido(doc.nuevo_id(), "G", componentes=["manivela", "PISTON"]))
    assert res.estado == "ok" and doc.estado_final.grupos_rigidos[-1] == ["op5", "op6"]
    assert {"op5", "op6"} <= doc.operacion("op9").dependencias()
    assert doc.operacion("op9").p["componentes"] == ["manivela", "PISTON"]
    res = doc.agregar(OpGrupoRigido(doc.nuevo_id(), "G2", componentes=["Manivela", "Nada"]))
    assert res.estado == "error" and "«Nada»" in res.mensaje and "Base (op4)" in res.mensaje


def test_limite_de_la_union_avisa_cuando_recorta():
    doc = _doc_dos_cajas()
    res = doc.agregar(OpUnion(doc.nuevo_id(), "Giro", tipo="revolucion", giro="200 deg", maximo="120 deg",
                              origen1=_cara(doc, "op2.c1", (105, 55, 0)), origen2=_cara(doc, "op1.c1", (20, 20, 10))))
    assert res.estado == "aviso" and res.mensaje.count("límite") == 1 and "120" in res.mensaje
    assert doc.estado_final.uniones["op5"]["valores"]["giro"] == pytest.approx(120)


def test_editar_union_como_esta_usa_su_dialogo_y_no_la_convierte():
    """El doble clic en una unión «como está» abría el diálogo de Unión: aceptar sin cambios la convertía en
    una unión normal (con un cuerpo como origen 2) y el paso quedaba en error."""
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos import comando_para
    from omnicad.ui.comandos.ensamblar import Union, UnionComoEsta
    doc = _doc_dos_cajas()
    doc.agregar(OpUnion(doc.nuevo_id(), "Como está", tipo="revolucion", como_esta=True, giro="90 deg",
                        origen1=_cara(doc, "op2.c1", (105, 55, 10)), origen2={"tipo": "cuerpo", "cuerpo": "op1.c1"}))
    op = doc.operacion("op5")
    assert comando_para(op) is UnionComoEsta and comando_para(OpUnion("x", tipo="rigida")) is Union
    cmd, ctx = UnionComoEsta(), ContextoComando(doc, op=op)
    nueva = cmd.construir(cmd.desde_op(op, ctx), ctx)
    assert nueva.p["como_esta"] and nueva.p["origen2"] == {"tipo": "cuerpo", "cuerpo": "op1.c1"}
    res = doc.reemplazar("op5", nueva)
    assert res.estado == "ok" and doc.estado_final.uniones["op5"]["comp2"] == "op3"
    (x0, y0, z0), (x1, y1, z1) = _caja(doc)
    assert (x0, x1, y0, y1, z0, z1) == pytest.approx((100, 110, 50, 60, 0, 10))
    assert g.es_valida(doc.estado_final.cuerpos["op2.c1"].forma)


def test_perno_contra_un_origen_de_union_queda_igual_que_contra_el_agujero():
    """El «Origen de unión» sobre el agujero se guardaba como plano y perdía que es un eje: el perno quedaba
    dado vuelta 180° (con aviso), mientras que contra el agujero directo quedaba derecho."""
    directa = np.asarray(_doc_perno_y_placa().estado_final.componentes["op5"]["matriz"])
    doc = _doc_perno_y_placa()
    doc.eliminar("op6")
    doc.agregar(OpOrigenUnion(doc.nuevo_id(), "Origen agujero", origen=_cara_donde(doc, "op1.c1", _es_cilindro)))
    res = doc.agregar(OpUnion(doc.nuevo_id(), "Unión1", tipo="revolucion",
                              origen1=_cara_donde(doc, "op3.c1", _es_cilindro), origen2={"tipo": "plano", "id": "op7"}))
    assert res.estado == "ok"
    assert np.asarray(doc.estado_final.componentes["op5"]["matriz"]) == pytest.approx(directa, abs=1e-9)
    assert g.es_valida(doc.estado_final.cuerpos["op3.c1"].forma)


def test_version_de_calculo_mal_formada_nombra_el_campo():
    """version_marco / version_vinculo con algo que no es 1 ni 2 daban «Error inesperado: invalid literal for
    int()…» sin decir qué campo estaba mal."""
    doc = _doc_mecanismo()
    cuerpo = {"tipo": "cuerpo", "cuerpo": "op2.c1"}
    for valor in ("abc", [2], None, 3, True):
        for op in (OpUnion(doc.nuevo_id(), "U", version_marco=valor, origen1=cuerpo, origen2=cuerpo),
                   OpOrigenUnion(doc.nuevo_id(), "O", version_marco=valor, origen=cuerpo),
                   OpVinculoMovimiento(doc.nuevo_id(), "V", union1="op7", union2="op8", version_vinculo=valor)):
            res = doc.agregar(op)
            assert res.estado == "error" and res.mensaje.startswith("Parámetro mal formado «version_"), res.mensaje
            assert repr(valor) in res.mensaje
            doc.eliminar(op.id)


def test_union_como_esta_no_deshace_el_movimiento_del_componente_1():
    """Con 1 = la manivela ya girada por otra unión y 2 = el perno, la unión «como está» la devolvía a la
    posición modelada (deshacía el giro) sin avisar."""
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="100", largo="100", alto="10"))
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="10", largo="40", alto="10", x="45", y="45", z="10"))
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="4", largo="4", alto="10", x="52", y="48", z="20"))
    doc.agregar(OpComponente(doc.nuevo_id(), "Base", cuerpos=["op1.c1"], fijo=True))
    doc.agregar(OpComponente(doc.nuevo_id(), "Manivela", cuerpos=["op2.c1"]))
    doc.agregar(OpComponente(doc.nuevo_id(), "Perno", cuerpos=["op3.c1"]))
    doc.agregar(OpUnion(doc.nuevo_id(), "Giro", tipo="revolucion", giro="90 deg",
                        origen1=_cara(doc, "op2.c1", (50, 65, 10)), origen2=_cara(doc, "op1.c1", (50, 50, 10))))
    antes = _caja(doc, "op2.c1")
    zmax = antes[1][2]
    assert np.ravel(antes) != pytest.approx([45, 45, 10, 55, 85, 20], abs=1e-3)     # el giro la movió
    res = doc.agregar(OpUnion(doc.nuevo_id(), "Al revés", tipo="rigida", como_esta=True,
                              origen1=_cara_donde(doc, "op2.c1", lambda f: np.isclose(f["centro"][2], zmax)),
                              origen2={"tipo": "cuerpo", "cuerpo": "op3.c1"}))
    assert res.estado == "aviso" and "componente 1" in res.mensaje
    assert np.ravel(_caja(doc, "op2.c1")) == pytest.approx(np.ravel(antes), abs=1e-6)
    assert g.es_valida(doc.estado_final.cuerpos["op2.c1"].forma)


def test_perno_contra_un_eje_de_construccion_queda_igual_que_contra_el_agujero():
    """El eje de construcción no era un marco de eje: el perno quedaba dado vuelta (R diag [-1,1,-1])."""
    from omnicad.timeline.ops_construir import OpEje
    doc = _doc_perno_y_placa()
    doc.eliminar("op6")
    doc.agregar(OpEje(doc.nuevo_id(), "Eje agujero", tipo="cilindro", refs=[_cara_donde(doc, "op1.c1", _es_cilindro)]))
    res = doc.agregar(OpUnion(doc.nuevo_id(), "Unión1", tipo="revolucion",
                              origen1=_cara_donde(doc, "op3.c1", _es_cilindro), origen2={"tipo": "eje", "id": "op7"}))
    assert res.estado == "ok", res.mensaje
    R = np.asarray(doc.estado_final.componentes["op5"]["matriz"])[:3, :3]
    assert R == pytest.approx(np.identity(3), abs=1e-9)
    assert g.es_valida(doc.estado_final.cuerpos["op3.c1"].forma)


def test_insertar_diseno_fijo_no_se_mueve():
    """«Fijar» también vale para un diseño insertado (antes su componente quedaba siempre libre)."""
    otro = Documento()
    otro.agregar(OpPrimitiva(otro.nuevo_id(), forma="caja", ancho="10", largo="10", alto="10"))
    doc = _doc_dos_cajas()
    doc.agregar(OpInsertarDiseno(doc.nuevo_id(), "Insertar pieza", archivo="pieza", receta=otro.a_dict(), fijo=True))
    assert doc.estado_final.componentes["op5"]["fijo"] is True
    res = doc.agregar(OpUnion(doc.nuevo_id(), "Mal", tipo="rigida", origen1=_cara(doc, "op5.c1", (5, 5, 0)),
                              origen2=_cara(doc, "op1.c1", (20, 20, 10))))
    assert res.estado == "error" and "fijo" in res.mensaje


def test_comando_fijar_un_diseno_insertado_conserva_sus_cuerpos():
    """«Fijar / liberar componente» sobre un diseño insertado lo rehacía como OpComponente vacío: los cuerpos
    insertados desaparecían. Ahora conserva la clase del paso."""
    from omnicad.ui.comando import ContextoComando, hit_desde_ref
    from omnicad.ui.comandos.ensamblar import FijarComponente
    otro = Documento()
    otro.agregar(OpPrimitiva(otro.nuevo_id(), forma="caja", ancho="10", largo="10", alto="10"))
    doc = _doc_dos_cajas()
    doc.agregar(OpInsertarDiseno(doc.nuevo_id(), "Insertar pieza", archivo="pieza", receta=otro.a_dict()))
    cid = next(k for k, c in doc.estado_final.cuerpos.items() if c.componente == "op5")
    ctx = ContextoComando(doc)
    FijarComponente().aplicar({"cuerpos": [hit_desde_ref({"tipo": "cuerpo", "cuerpo": cid}, doc.estado_final)]}, ctx)
    assert isinstance(doc.operacion("op5"), OpInsertarDiseno)
    assert doc.estado_final.componentes["op5"]["fijo"] is True
    assert g.volumen(doc.estado_final.cuerpos[cid].forma) == pytest.approx(1000.0)
