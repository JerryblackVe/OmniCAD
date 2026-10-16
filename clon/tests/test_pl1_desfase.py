# -*- coding: utf-8 -*-
"""PL1 (brechas_plasticity.md): «Desfase», un comando que actúa según lo elegido (caras, aristas o curvas de boceto)."""
import os

import numpy as np
import pytest

from omnicad import api
from omnicad.nucleo import geometria as g
from omnicad.nucleo import referencias as refs
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva


@pytest.fixture(scope="module", autouse=True)
def app_qt():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _doc_caja():
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="20 mm", largo="20 mm", alto="20 mm"))
    return doc


def _hit(doc, tipo, medio):
    from omnicad.ui.comando import hit_desde_ref
    forma = doc.estado_final.cuerpos["op1.c1"].forma
    clave = "medio" if tipo == "arista" else "centro"
    sub = next(s for s in refs.subformas(forma, tipo) if np.allclose(refs.firma(s)[clave], medio, atol=1e-6))
    return hit_desde_ref(refs.referencia("op1.c1", sub, forma), doc.estado_final)


def _valores(cmd, ctx, **v):
    base = {c.clave: (list(c.defecto) if isinstance(c.defecto, list) else c.defecto) for c in cmd.campos(ctx)}
    base.update(v)
    return base


def _cara_de_arriba(doc):
    return _hit(doc, "cara", (10, 10, 20))


def _aristas_de_arriba(doc):
    return [_hit(doc, "arista", m) for m in ((10, 0, 20), (20, 10, 20), (10, 20, 20), (0, 10, 20))]


def test_el_comando_esta_en_el_catalogo_y_en_la_cinta():
    from omnicad.ui.cinta import SOLIDO
    from omnicad.ui.comandos import CATALOGO
    from omnicad.ui.comandos.modificar import Desfase
    assert CATALOGO["desfase"] is Desfase and "desfase_cara" in CATALOGO     # el viejo sigue para Shift+D y para editar
    menu = next(items for titulo, _rapidos, items in SOLIDO if titulo == "MODIFICAR")
    claves = [it[2] for it in menu if isinstance(it, tuple) and len(it) > 2]
    assert "desfase" in claves and "desfase_cara" not in claves             # un solo botón en el menú


def test_con_una_cara_mueve_la_cara():
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.modificar import Desfase
    doc, cmd = _doc_caja(), Desfase()
    ctx = ContextoComando(doc)
    op = cmd.construir(_valores(cmd, ctx, objetos=[_cara_de_arriba(doc)], distancia="5 mm"), ctx)
    assert op.TIPO == "desfase_cara" and op.nombre == "Desfase de cara1"
    assert doc.agregar(op).estado in ("ok", "aviso")
    assert g.volumen(doc.estado_final.cuerpos["op1.c1"].forma) == pytest.approx(20 * 20 * 25)


def test_con_aristas_crea_curvas_nuevas_sin_tocar_el_cuerpo():
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.modificar import Desfase
    doc, cmd = _doc_caja(), Desfase()
    volumen = g.volumen(doc.estado_final.cuerpos["op1.c1"].forma)
    ctx = ContextoComando(doc)
    op = cmd.construir(_valores(cmd, ctx, objetos=_aristas_de_arriba(doc), distancia="3 mm", esquinas="vivas"), ctx)
    assert op.TIPO == "desfase_aristas" and op.nombre == "Desfase de aristas1"
    assert doc.agregar(op).estado in ("ok", "aviso")
    assert g.volumen(doc.estado_final.cuerpos["op1.c1"].forma) == pytest.approx(volumen)
    boceto = doc.estado_final.bocetos[op.id]
    assert len(boceto.perfiles) == 1 and boceto.perfiles[0].area == pytest.approx(26 * 26)


def test_la_arista_sola_con_plano_elegido_y_simetrico():
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.modificar import Desfase
    doc, cmd = _doc_caja(), Desfase()
    ctx = ContextoComando(doc)
    una = _hit(doc, "arista", (10, 0, 20))
    op = cmd.construir(_valores(cmd, ctx, objetos=[una], plano=[_cara_de_arriba(doc)], distancia="2 mm",
                                simetrico=True), ctx)
    assert op.p["simetrico"] is True and op.p["plano"]["tipo"] == "cara"
    assert doc.agregar(op).estado in ("ok", "aviso")
    assert len(doc.estado_final.bocetos[op.id].boceto.curvas) == 2        # dos rectas, una a cada lado: aún sin perfil


def test_mezclar_caras_con_aristas_o_no_elegir_nada_avisa():
    from omnicad.ui.comando import ContextoComando, ErrorComando
    from omnicad.ui.comandos.modificar import Desfase
    doc, cmd = _doc_caja(), Desfase()
    ctx = ContextoComando(doc)
    with pytest.raises(ErrorComando, match="solo caras"):
        cmd.construir(_valores(cmd, ctx, objetos=[_cara_de_arriba(doc), _hit(doc, "arista", (10, 0, 20))]), ctx)
    with pytest.raises(ErrorComando, match="Seleccioná"):
        cmd.construir(_valores(cmd, ctx), ctx)


def test_el_panel_cambia_solo_segun_lo_elegido():
    from omnicad.ui.comando import ContextoComando, Info
    from omnicad.ui.comandos.modificar import Desfase
    doc, cmd = _doc_caja(), Desfase()
    ctx = ContextoComando(doc)
    campos = {c.clave: c for c in cmd.campos(ctx)}

    def visibles(v):
        return {k for k, c in campos.items() if c.visible_si is None or c.visible_si(v)}
    nada, caras, aristas = {"objetos": []}, {"objetos": [_cara_de_arriba(doc)]}, {"objetos": _aristas_de_arriba(doc)}
    assert visibles(nada) == {"objetos", "distancia", "modo"}
    assert visibles(caras) == {"objetos", "distancia", "tangente", "modo"}
    assert visibles(aristas) == {"objetos", "plano", "distancia", "simetrico", "esquinas", "modo"}
    assert isinstance(campos["modo"], Info)
    assert "Elegí caras" in campos["modo"].funcion(nada, ctx)
    assert "mueve las caras" in campos["modo"].funcion(caras, ctx)
    assert "no corta el cuerpo" in campos["modo"].funcion(aristas, ctx)
    assert "caras" in cmd.AYUDA and "aristas" in cmd.AYUDA          # la ayuda dice qué hace en cada caso


def test_editar_un_desfase_de_aristas_vuelve_al_mismo_comando():
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos import comando_para
    from omnicad.ui.comandos.modificar import Desfase
    doc, cmd = _doc_caja(), Desfase()
    ctx = ContextoComando(doc)
    op = cmd.construir(_valores(cmd, ctx, objetos=_aristas_de_arriba(doc), distancia="3 mm"), ctx)
    doc.agregar(op)
    assert comando_para(op) is Desfase
    ctx = ContextoComando(doc, op=op)
    valores = cmd.desde_op(op, ctx)
    assert len(valores["objetos"]) == 4 and valores["distancia"] == "3 mm" and valores["plano"] == []
    nuevo = cmd.construir(dict(_valores(cmd, ctx), **dict(valores, distancia="4 mm")), ctx)
    assert nuevo.id == op.id and nuevo.p["distancia"] == "4 mm"


def test_sin_cuerpos_ni_bocetos_no_se_puede_usar():
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.modificar import Desfase
    assert "cuerpo o un boceto" in Desfase().verificar(ContextoComando(Documento()))
    assert Desfase().verificar(ContextoComando(_doc_caja())) is None


# ---------------------------------------------------------------- API de caras
def test_offset_faces_mueve_la_cara_y_deja_un_paso_editable():
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 20, "width": 20, "height": 20})["ok"]
    r = api.llamar(s, "offset_faces", {"faces": ">Z", "distance": 5})
    assert r["ok"], r
    assert r["result"]["feature"]["type"] == "desfase_cara" and r["result"]["faces_moved"] == 1
    assert r["result"]["bodies_modified"][0]["volume"] == pytest.approx(20 * 20 * 25)
    r = api.llamar(s, "offset_faces", {"faces": ">Z", "distance": -10, "tangent": False})
    assert r["result"]["bodies_modified"][0]["volume"] == pytest.approx(20 * 20 * 15)
    assert api.llamar(s, "offset_faces", {"faces": ">Z", "distance": -100})["ok"] is False      # más que el espesor
