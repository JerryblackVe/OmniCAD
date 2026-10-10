# -*- coding: utf-8 -*-
"""Comandos de SÓLIDO › MODIFICAR: del diálogo al timeline, con referencias que sobreviven al recálculo."""
import math
import os

import numpy as np
import pytest

from omnicad.nucleo import geometria as g
from omnicad.nucleo import referencias as refs
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva
from omnicad.timeline.parametros import TablaParametros


@pytest.fixture(scope="module", autouse=True)
def app_qt():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _doc_caja(lado="20"):
    doc = Documento()
    doc.parametros.agregar("lado", f"{lado} mm")
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="lado", largo="lado", alto="lado"))
    return doc


def _cuerpo(doc, cid="op1.c1"):
    return doc.estado_final.cuerpos[cid]


def _hit_sub(doc, tipo, medio, cid="op1.c1"):
    """Selección de la arista o cara cuyo centro está en `medio`."""
    from omnicad.ui.comando import hit_desde_ref
    forma = _cuerpo(doc, cid).forma
    clave = "medio" if tipo == "arista" else "centro"
    sub = next(s for s in refs.subformas(forma, tipo) if np.allclose(refs.firma(s)[clave], medio, atol=1e-6))
    return hit_desde_ref(refs.referencia(cid, sub, forma), doc.estado_final)


def _hit(doc, ref):
    from omnicad.ui.comando import hit_desde_ref
    return hit_desde_ref(ref, doc.estado_final)


def _ejecutar(doc, clase, **valores):
    from omnicad.ui.comando import ContextoComando
    cmd = clase()
    ctx = ContextoComando(doc)
    v = {c.clave: (list(c.defecto) if isinstance(c.defecto, list) else c.defecto) for c in cmd.campos(ctx)}
    v.update(valores)
    if cmd.SIN_OP:
        cmd.aplicar(v, ctx)
        return None
    op = cmd.construir(v, ctx)
    res = doc.agregar(op)
    assert res.estado in ("ok", "aviso"), res.mensaje
    return op


def test_empalme_y_su_referencia_sigue_al_parametro():
    from omnicad.ui.comandos.modificar import Empalme
    doc = _doc_caja()
    op = _ejecutar(doc, Empalme, aristas=[_hit_sub(doc, "arista", (10, 0, 20))], radio="2 mm")
    assert op.nombre == "Empalme1"
    assert g.volumen(_cuerpo(doc).forma) == pytest.approx(8000 - (4 - math.pi) * 20)
    t = TablaParametros.desde_lista(doc.parametros.a_lista())
    t.modificar("lado", "30 mm")                      # la arista de arriba-adelante sigue ahí, más larga
    doc.aplicar_parametros(t)
    assert doc.resultado(op.id).estado == "ok"
    assert g.volumen(_cuerpo(doc).forma) == pytest.approx(27000 - (4 - math.pi) * 30)


def test_chaflan_vaciado_y_desfase_de_cara():
    from omnicad.ui.comandos.modificar import CaraDesfase, Chaflan, Vaciado
    doc = _doc_caja()
    _ejecutar(doc, Chaflan, aristas=[_hit_sub(doc, "arista", (10, 0, 20))], distancia="1 mm")
    assert g.volumen(_cuerpo(doc).forma) == pytest.approx(8000 - 0.5 * 20)
    doc = _doc_caja()
    _ejecutar(doc, Vaciado, caras=[_hit_sub(doc, "cara", (10, 10, 20))], espesor_interior="2 mm")
    assert g.volumen(_cuerpo(doc).forma) == pytest.approx(8000 - 16 * 16 * 18)
    doc = _doc_caja()
    _ejecutar(doc, CaraDesfase, caras=[_hit_sub(doc, "cara", (10, 10, 20))], distancia="5 mm")
    assert g.volumen(_cuerpo(doc).forma) == pytest.approx(8000 + 400 * 5)


def test_pulsar_tirar_decide_por_lo_elegido():
    from omnicad.ui.comandos.modificar import PulsarTirar
    doc = _doc_caja()
    op = _ejecutar(doc, PulsarTirar, objetos=[_hit_sub(doc, "cara", (10, 10, 20))], distancia="3 mm")
    assert op.TIPO == "desfase_cara" and op.nombre == "Desfase de cara1"
    op = _ejecutar(doc, PulsarTirar, objetos=[_hit_sub(doc, "arista", (10, 0, 23))], distancia="1 mm")
    assert op.TIPO == "empalme"


def test_mover_copiar_y_alinear():
    from omnicad.ui.comandos.modificar import Alinear, MoverCopiar
    doc = _doc_caja()
    cuerpo = _hit(doc, {"tipo": "cuerpo", "cuerpo": "op1.c1"})
    _ejecutar(doc, MoverCopiar, cuerpos=[cuerpo], tipo="libre", dx="30 mm", copiar=True)
    assert len(doc.estado_final.cuerpos) == 2
    (x0, _, _), _ = g.caja_envolvente(doc.estado_final.cuerpos["op2.c1"].forma)
    assert x0 == pytest.approx(30)
    _ejecutar(doc, MoverCopiar, cuerpos=[cuerpo], tipo="rotacion", eje=[_hit(doc, {"tipo": "eje", "id": "Z"})],
              angulo="90 deg")
    (x0, y0, _), (x1, y1, _) = g.caja_envolvente(_cuerpo(doc).forma)
    assert (x0, x1, y0, y1) == pytest.approx((-20, 0, 0, 20))
    # Alinear: la cara de abajo de la caja girada contra el plano a z = 50
    doc2 = _doc_caja()
    from omnicad.timeline.operaciones import OpPlano
    doc2.agregar(OpPlano(doc2.nuevo_id(), "Plano1", base="XY", distancia="50 mm"))
    _ejecutar(doc2, Alinear, cuerpos=[_hit(doc2, {"tipo": "cuerpo", "cuerpo": "op1.c1"})],
              origen=[_hit_sub(doc2, "cara", (10, 10, 20))], destino=[_hit(doc2, {"tipo": "plano", "id": "op2"})])
    (_, _, z0), (_, _, z1) = g.caja_envolvente(_cuerpo(doc2).forma)
    assert (z0, z1) == pytest.approx((50, 70))      # cara superior apoyada sobre el plano: queda del otro lado


def test_dividir_cuerpo_escala_y_quitar():
    from omnicad.ui.comandos.modificar import DividirCuerpo, Escala, Quitar
    doc = _doc_caja()
    with pytest.raises(AssertionError, match="no divide"):   # el plano YZ (x = 0) no corta la caja de 0 a 20
        _ejecutar(doc, DividirCuerpo, cuerpo=[_hit(doc, {"tipo": "cuerpo", "cuerpo": "op1.c1"})],
                  herramienta=[_hit(doc, {"tipo": "plano", "id": "YZ"})])
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="20", largo="20", alto="20", x="-10"))
    op = _ejecutar(doc, DividirCuerpo, cuerpo=[_hit(doc, {"tipo": "cuerpo", "cuerpo": "op1.c1"})],
                   herramienta=[_hit(doc, {"tipo": "plano", "id": "YZ"})])
    vols = sorted(g.volumen(c.forma) for c in doc.estado_final.cuerpos.values())
    assert vols == pytest.approx([4000, 4000]) and f"{op.id}.c1" in doc.estado_final.cuerpos
    _ejecutar(doc, Escala, cuerpos=[_hit(doc, {"tipo": "cuerpo", "cuerpo": "op1.c1"})], factor="2")
    assert g.volumen(_cuerpo(doc).forma) == pytest.approx(32000)
    _ejecutar(doc, Quitar, cuerpos=[_hit(doc, {"tipo": "cuerpo", "cuerpo": "op1.c1"})])
    assert list(doc.estado_final.cuerpos) == [f"{op.id}.c1"]


def test_suprimir_borra_el_paso_creador_o_quita():
    from omnicad.ui.comandos.modificar import Suprimir
    doc = _doc_caja()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="cilindro", radio="3", alto="40", x="50"))
    _ejecutar(doc, Suprimir, objetos=[_hit(doc, {"tipo": "cuerpo", "cuerpo": "op2.c1"})])
    assert [o.id for o in doc.operaciones] == ["op1"]           # nadie lo usaba: se borró el paso
    from omnicad.ui.comandos.modificar import Empalme
    _ejecutar(doc, Empalme, aristas=[_hit_sub(doc, "arista", (10, 0, 20))], radio="1 mm")
    _ejecutar(doc, Suprimir, objetos=[_hit(doc, {"tipo": "cuerpo", "cuerpo": "op1.c1"})])
    assert doc.operaciones[-1].TIPO == "quitar" and not doc.estado_final.cuerpos


def test_combinar_y_aspecto_material():
    from omnicad.ui.comandos.modificar import Aspecto, Combinar, MaterialFisico
    doc = _doc_caja()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="20", largo="20", alto="20", x="10"))
    _ejecutar(doc, Combinar, objetivo=[_hit(doc, {"tipo": "cuerpo", "cuerpo": "op1.c1"})],
              herramientas=[_hit(doc, {"tipo": "cuerpo", "cuerpo": "op2.c1"})], operacion="unir")
    assert g.volumen(_cuerpo(doc).forma) == pytest.approx(12000)
    _ejecutar(doc, Aspecto, cuerpos=[_hit(doc, {"tipo": "cuerpo", "cuerpo": "op1.c1"})], hex="#ff0000")
    assert doc.propiedad("op1.c1", "apariencia") == [1.0, 0.0, 0.0]
    _ejecutar(doc, MaterialFisico, cuerpos=[_hit(doc, {"tipo": "cuerpo", "cuerpo": "op1.c1"})], material="Aluminio 6061")
    assert doc.propiedad("op1.c1", "material") == "Aluminio 6061"
    doc.deshacer()
    assert doc.propiedad("op1.c1", "material") is None
    otro = Documento.desde_dict(doc.a_dict())
    assert otro.propiedad("op1.c1", "apariencia") == [1.0, 0.0, 0.0]


def test_desmoldeo_y_dividir_cara():
    from omnicad.ui.comandos.modificar import Desmoldeo, DividirCara
    doc = _doc_caja()
    _ejecutar(doc, Desmoldeo, plano=[_hit_sub(doc, "cara", (10, 10, 0))], caras=[_hit_sub(doc, "cara", (10, 0, 10))],
              angulo="5 deg")
    assert g.volumen(_cuerpo(doc).forma) == pytest.approx(8000 - 0.5 * 20 * 20 * 20 * math.tan(math.radians(5)),
                                                          rel=1e-4)
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="20", largo="20", alto="20", x="-10"))
    _ejecutar(doc, DividirCara, caras=[_hit_sub(doc, "cara", (0, 10, 20))],
              herramienta=[_hit(doc, {"tipo": "plano", "id": "YZ"})])
    assert len(refs.subformas(_cuerpo(doc).forma, "cara")) == 7     # la cara de arriba quedó partida en dos


def test_mover_gira_una_malla_alrededor_de_su_centro():
    """El pivote por defecto de Mover usaba geo.caja_envolvente también sobre mallas (y fallaba con un cuerpo vacío):
    ahora una malla girada 90° alrededor de Z queda con su centro en el mismo lugar."""
    from omnicad.timeline.ops_malla import OpTeselar
    from omnicad.timeline.ops_modificar import OpMover
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), "Caja", forma="caja", ancho="10 mm", largo="20 mm", alto="5 mm",
                            x="30 mm"))
    doc.agregar(OpTeselar(doc.nuevo_id(), cuerpos=["op1.c1"], mantener=False))
    malla = next(iter(doc.estado_final.cuerpos.values()))
    (a0, b0) = malla.forma.caja()
    doc.agregar(OpMover(doc.nuevo_id(), cuerpos=[malla.id], rz="90 deg"))
    assert [r.estado for r in doc.resultados] == ["ok"] * 3, [r.mensaje for r in doc.resultados]
    (a1, b1) = doc.estado_final.cuerpos[malla.id].forma.caja()
    assert np.allclose((np.array(a0) + b0) / 2, (np.array(a1) + b1) / 2, atol=1e-6)
    assert np.allclose(np.array(b1) - a1, (np.array(b0) - a0)[[1, 0, 2]], atol=1e-6)   # ancho y largo cambiados
