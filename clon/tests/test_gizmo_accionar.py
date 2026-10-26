"""Accionar uniones: vista previa en vivo, un valor imposible se rechaza con el panel abierto (ASM-4) y las asas
del ángulo y de la distancia."""
import numpy as np
import pytest
from test_ensamblar import _caja, _cara, _doc_dos_cajas
from test_manipuladores import _arrastrar, _panel, app_qt  # noqa: F401  (fixture)

from omnicad.timeline.ops_ensamblar import OpUnion
from omnicad.ui import manipuladores as mp
from omnicad.ui.comando import ContextoComando
from omnicad.ui.comandos.ensamblar import AccionarUniones


def _doc_union(tipo="revolucion", **extra):
    doc = _doc_dos_cajas()
    op = OpUnion(doc.nuevo_id(), "Unión1", tipo=tipo, origen1=_cara(doc, "op2.c1", (105, 55, 0)),
                 origen2=_cara(doc, "op1.c1", (20, 20, 10)), dx="10 mm", **extra)
    doc.agregar(op)
    return doc, op


def _abrir(doc, op, **valores):
    p, visor, estados = _panel(AccionarUniones(), doc, {"union": op.id, "giro": "0 deg", "desliz": "0 mm", **valores})
    visor.vista("iso")
    p._calcular_previa()
    p.manipuladores.actualizar()
    return p, estados


def test_la_vista_previa_muestra_el_mecanismo_movido_y_no_toca_el_documento(app_qt):  # noqa: F811
    doc, op = _doc_union()
    antes = _caja(doc)
    recibidos = []
    p, _ = _abrir(doc, op)
    p.previa.connect(recibidos.append)
    p.set_valor("giro", "90 deg")
    p._calcular_previa()
    assert recibidos and recibidos[-1] is not None
    assert np.allclose(_caja(doc), antes)                        # el documento sigue igual hasta aceptar
    from omnicad.nucleo import geometria as g
    en_previa = g.caja_envolvente(recibidos[-1].cuerpos["op2.c1"].forma)
    assert not np.allclose(en_previa, antes, atol=1e-3)           # pero la vista previa ya giró el bloque
    p.cancelar()


def test_un_valor_enorme_se_rechaza_sin_cerrar_el_panel_ni_romper_la_union(app_qt):  # noqa: F811
    doc, op = _doc_union()
    p, _ = _abrir(doc, op, giro="1e9 deg")
    p.aceptar()
    assert p.mensaje.text() and "1e+09" in p.mensaje.text().replace(",", ".")      # el mensaje dice por qué
    assert doc.estado_final.uniones[op.id]["valores"].get("giro", 0) == 0
    assert doc.resultados[doc.indice(op.id)].estado != "error"
    p.cancelar()


def test_aceptar_aplica_el_valor_con_ctx_sin_ventana(app_qt):  # noqa: F811
    doc, op = _doc_union()
    AccionarUniones().aplicar({"union": op.id, "giro": "180 deg", "desliz": "0 mm"}, ContextoComando(doc))
    assert doc.estado_final.uniones[op.id]["valores"]["giro"] == pytest.approx(180)


def test_asa_de_giro_gira_y_la_de_distancia_desliza(app_qt):  # noqa: F811
    doc, op = _doc_union()
    p, _ = _abrir(doc, op)
    gm = p.manipuladores
    arco = next(m for m in gm.manips if isinstance(m, mp.Angulo))
    objetivo = arco.centro + (arco.u * np.cos(np.radians(70)) + arco.v * np.sin(np.radians(70))) * arco._r(gm)
    xy, ok = gm.pantalla([arco.asa(gm), objetivo])
    assert ok.all()
    _arrastrar(p.visor, *xy)
    assert gm.valor("giro") == pytest.approx(70, abs=2)
    p.cancelar()
    doc, op = _doc_union("deslizante", eje_desliz="Z")
    p, _ = _abrir(doc, op)
    gm = p.manipuladores
    f = next(m for m in gm.manips if isinstance(m, mp.Flecha))
    a, b = f.puntos(gm)
    xy, ok = gm.pantalla([(a + b) / 2, (a + b) / 2 + f.direccion * 6])
    _arrastrar(p.visor, *xy)
    assert gm.valor("desliz") == pytest.approx(6, abs=0.5)
    p.cancelar()


def test_una_union_rigida_no_tiene_asas(app_qt):  # noqa: F811
    doc, op = _doc_union("rigida")
    p, _ = _abrir(doc, op)
    assert p.manipuladores.manips == []
    p.cancelar()


def test_la_union_que_sigue_a_un_vinculo_se_rechaza_en_el_panel_y_no_tiene_asas(app_qt):  # noqa: F811
    from omnicad.timeline.ops_ensamblar import OpVinculoMovimiento
    doc, op = _doc_union()
    otra = OpUnion(doc.nuevo_id(), "Unión2", tipo="revolucion", origen1=op.p["origen1"], origen2=op.p["origen2"], dx="10 mm")
    doc.agregar(otra)
    doc.agregar(OpVinculoMovimiento(doc.nuevo_id(), "Vínculo1", union1=op.id, union2=otra.id, factor="2"))
    p, _ = _abrir(doc, otra, giro="10 deg")
    assert p.manipuladores.manips == []
    p.aceptar()
    assert "Vínculo1" in p.mensaje.text()
    p.cancelar()
