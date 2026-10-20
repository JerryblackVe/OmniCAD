# -*- coding: utf-8 -*-
"""«Extruir cara»: extruye SOLO la cara elegida (hacia afuera o hacia adentro) y sale en la tira de sugerencias."""
import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad.nucleo import geometria as geo  # noqa: E402
from omnicad.nucleo import referencias as refs  # noqa: E402
from omnicad.timeline.documento import Documento  # noqa: E402
from omnicad.timeline.operaciones import OpPrimitiva  # noqa: E402


def _doc_caja():
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="20 mm", largo="20 mm", alto="20 mm"))
    return doc


def _doc_cilindro():
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="cilindro", radio="10 mm", alto="20 mm"))
    return doc


def _hit(doc, centro, cid="op1.c1"):
    """La cara de la caja cuyo centro es `centro` (arriba, abajo o un lateral)."""
    from omnicad.ui.comando import hit_desde_ref
    forma = doc.estado_final.cuerpos[cid].forma
    sub = next(s for s in refs.subformas(forma, "cara") if np.allclose(refs.firma(s)["centro"], centro, atol=1e-6))
    return hit_desde_ref(refs.referencia(cid, sub, forma), doc.estado_final)


def _hit_cara_curva(doc, cid="op1.c1"):
    """La cara cilíndrica de un cilindro (curva: no tiene plano)."""
    from omnicad.ui.comando import hit_desde_ref
    forma = doc.estado_final.cuerpos[cid].forma
    sub = next(s for s in refs.subformas(forma, "cara") if refs.firma(s).get("geom") == "cilindro")
    return hit_desde_ref(refs.referencia(cid, sub, forma), doc.estado_final)


def _valores(cmd, ctx, **v):
    base = {c.clave: (list(c.defecto) if isinstance(c.defecto, list) else c.defecto) for c in cmd.campos(ctx)}
    base.update(v)
    return base


def _aplicar(doc, cmd, ctx, **v):
    op = cmd.construir(_valores(cmd, ctx, **v), ctx)
    return op, doc.agregar(op)


def test_el_comando_esta_registrado():
    from omnicad.ui.comandos import CATALOGO
    from omnicad.ui.comandos.solido import ExtruirCara
    assert CATALOGO["extruir_cara"] is ExtruirCara
    assert ExtruirCara.TITULO == "Extruir cara" and ExtruirCara.CLASE_OP is None


def test_cara_de_arriba_hacia_afuera_agrega_material():
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.solido import ExtruirCara
    doc, cmd = _doc_caja(), ExtruirCara()
    ctx = ContextoComando(doc)
    op, res = _aplicar(doc, cmd, ctx, caras=[_hit(doc, (10, 10, 20))], sentido="afuera", distancia="5 mm")
    assert op.p["operacion"] == "unir" and op.p["invertir"] is False
    assert res.estado in ("ok", "aviso"), res.mensaje
    forma = doc.estado_final.cuerpos["op1.c1"].forma
    assert geo.volumen(forma) == pytest.approx(10000, abs=1e-6)
    assert geo.es_valida(forma)


def test_cara_de_arriba_hacia_adentro_corta_el_cuerpo():
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.solido import ExtruirCara
    doc, cmd = _doc_caja(), ExtruirCara()
    ctx = ContextoComando(doc)
    op, res = _aplicar(doc, cmd, ctx, caras=[_hit(doc, (10, 10, 20))], sentido="adentro", distancia="5 mm")
    assert op.p["operacion"] == "cortar" and op.p["invertir"] is True
    assert res.estado in ("ok", "aviso"), res.mensaje
    forma = doc.estado_final.cuerpos["op1.c1"].forma
    assert geo.volumen(forma) == pytest.approx(6000, abs=1e-6)
    assert geo.es_valida(forma)


def test_cara_de_abajo_crece_hacia_abajo():
    """La normal de la cara de abajo también es hacia afuera: el material crece hacia -Z."""
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.solido import ExtruirCara
    doc, cmd = _doc_caja(), ExtruirCara()
    ctx = ContextoComando(doc)
    op, res = _aplicar(doc, cmd, ctx, caras=[_hit(doc, (10, 10, 0))], sentido="afuera", distancia="5 mm")
    assert res.estado in ("ok", "aviso"), res.mensaje
    forma = doc.estado_final.cuerpos["op1.c1"].forma
    assert geo.volumen(forma) == pytest.approx(10000, abs=1e-6)
    (_, _, z0), (_, _, z1) = geo.caja_envolvente(forma)
    assert (z0, z1) == pytest.approx((-5, 20))


def test_una_cara_lateral_fusionada_deja_un_solo_cuerpo():
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.solido import ExtruirCara
    doc, cmd = _doc_caja(), ExtruirCara()
    ctx = ContextoComando(doc)
    op, res = _aplicar(doc, cmd, ctx, caras=[_hit(doc, (20, 10, 10))], sentido="afuera", distancia="5 mm")
    assert res.estado in ("ok", "aviso"), res.mensaje
    cuerpos = doc.estado_final.cuerpos
    assert len(cuerpos) == 1
    assert geo.volumen(cuerpos["op1.c1"].forma) == pytest.approx(10000, abs=1e-6)


def test_una_cara_cilindrica_no_entra_al_campo_ni_a_la_tira():
    from omnicad.ui.comando import ContextoComando, preseleccion
    from omnicad.ui.comandos import CATALOGO
    from omnicad.ui.comandos.solido import ExtruirCara
    from omnicad.ui.sugerencias import comandos_sugeridos, tipos_de_seleccion
    doc, cmd = _doc_cilindro(), ExtruirCara()
    ctx = ContextoComando(doc)
    hit = _hit_cara_curva(doc)
    assert hit.get("plano") is None
    assert not preseleccion(cmd.campos(ctx), [hit]).get("caras")
    tipos = tipos_de_seleccion([hit])
    assert "cara_plana" not in tipos
    assert "extruir_cara" not in comandos_sugeridos(tipos, CATALOGO)


def test_distancia_invalida_avisa():
    from omnicad.ui.comando import ContextoComando, ErrorComando
    from omnicad.timeline.parametros import ErrorExpresion
    from omnicad.ui.comandos.solido import ExtruirCara
    doc, cmd = _doc_caja(), ExtruirCara()
    ctx = ContextoComando(doc)
    cara = _hit(doc, (10, 10, 20))
    with pytest.raises(ErrorComando, match="mayor que cero"):
        cmd.construir(_valores(cmd, ctx, caras=[cara], distancia="0 mm"), ctx)
    with pytest.raises(ErrorExpresion):
        cmd.construir(_valores(cmd, ctx, caras=[cara], distancia="cinco mm"), ctx)


def test_la_flecha_apunta_hacia_afuera_o_hacia_adentro_de_la_cara():
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.solido import ExtruirCara
    doc, cmd = _doc_caja(), ExtruirCara()
    ctx = ContextoComando(doc)
    cara = _hit(doc, (10, 10, 20))
    for sentido, z in (("afuera", 1.0), ("adentro", -1.0)):
        (flecha,) = cmd.manipuladores(ctx, _valores(cmd, ctx, caras=[cara], sentido=sentido))
        assert flecha.clave == "distancia" and np.allclose(flecha.direccion, (0, 0, z))
    assert cmd.manipuladores(ctx, _valores(cmd, ctx)) == []                  # sin cara no hay flecha


def test_sin_cuerpos_no_se_puede_usar():
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.solido import ExtruirCara
    assert ExtruirCara().verificar(ContextoComando(Documento())) == "Este comando necesita un cuerpo."
    assert ExtruirCara().verificar(ContextoComando(_doc_caja())) is None


# ---------------------------------------------------------------- con la ventana
@pytest.fixture
def ventana(tmp_path):
    from PySide6.QtCore import QSettings
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.resize(1200, 800)
    v.show()
    v.cargar_ejemplo()
    QTest.qWait(30)
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    QTest.qWait(10)


def _hit_cara_plana(v):
    from omnicad.ui.comando import hit_desde_ref
    estado = v.doc.estado_final
    cid = next(iter(estado.cuerpos))
    forma = estado.cuerpos[cid].forma
    for cara in geo.caras(forma):
        hit = hit_desde_ref(refs.referencia(cid, cara, forma), estado)
        if hit.get("plano") is not None:
            return hit
    raise AssertionError("el ejemplo no tiene caras planas")


def test_la_tira_ofrece_extruir_cara_y_el_panel_acepta_la_cara(ventana):
    from PySide6.QtWidgets import QToolButton
    from omnicad.ui.comandos.solido import ExtruirCara
    v = ventana
    v._seleccionar([_hit_cara_plana(v)])
    assert v.tira.isVisible()
    botones = v.tira.findChildren(QToolButton)
    assert [b.text() for b in botones][0] == "Extruir cara"
    botones[0].click()
    assert v.panel is not None and isinstance(v.panel.comando, ExtruirCara)
    assert len(v.panel.valores["caras"]) == 1
    v.panel.cancelar()
