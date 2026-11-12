"""Gizmos del Barrido (sólido y de superficie): asa del largo sobre la ruta y arco de la torsión."""
import numpy as np
import pytest
from test_manipuladores import _arrastrar, _doc_rectangulo, _panel, app_qt  # noqa: F401  (fixture)

from omnicad.ui import manipuladores as mp
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos import CATALOGO


def _abrir(clave):
    doc = _doc_rectangulo()
    curva = next(iter(doc.estado_final.bocetos["op1"].boceto.curvas))
    ruta = hit_desde_ref({"tipo": "curva_boceto", "boceto": "op1", "curva": curva}, doc.estado_final)
    p, visor, _ = _panel(CATALOGO[clave](), doc, {"ruta": [ruta]})
    visor.vista("iso")
    p.manipuladores.actualizar()
    return p


def test_barrido_asa_del_largo_por_la_ruta_y_arco_de_torsion(app_qt):  # noqa: F811
    p = _abrir("barrido")
    gm = p.manipuladores
    asa = next(m for m in gm.manips if isinstance(m, mp.AsaRuta))
    assert asa.clave == "distancia" and gm.valor("distancia") == 1
    xy, ok = gm.pantalla([asa.asa(gm), asa.puntos_ruta[40]])                         # a la mitad de la ruta
    assert ok.all()
    _arrastrar(p.visor, *xy)
    assert gm.valor("distancia") == pytest.approx(0.5, abs=0.03)
    p.set_valor("distancia", "0.25")
    nueva = next(m for m in gm.manips if isinstance(m, mp.AsaRuta))
    assert np.allclose(nueva.asa(gm), nueva.puntos_ruta[20], atol=0.3)              # teclear mueve el asa
    arco = next(m for m in gm.manips if isinstance(m, mp.Angulo))
    objetivo = arco.centro + (arco.u * np.cos(np.radians(50)) + arco.v * np.sin(np.radians(50))) * arco._r(gm)
    xy, ok = gm.pantalla([arco.asa(gm), objetivo])
    _arrastrar(p.visor, *xy)
    assert gm.valor("torsion") == pytest.approx(50, abs=2)
    p.cancelar()


def test_barrido_de_superficie_tiene_el_asa_del_largo_y_el_arco_de_torsion(app_qt):  # noqa: F811
    p = _abrir("sup_barrido")
    gm = p.manipuladores
    assert sorted(type(m).__name__ for m in gm.manips) == ["AnilloAngulo", "AsaRuta"]      # P-139: la torsión es el anillo de Fusion
    asa = next(m for m in gm.manips if isinstance(m, mp.AsaRuta))
    xy, ok = gm.pantalla([asa.asa(gm), asa.puntos_ruta[40]])
    assert ok.all()
    _arrastrar(p.visor, *xy)
    assert gm.valor("distancia") == pytest.approx(0.5, abs=0.03)
    p._calcular_previa()
    assert p._previa_ok or "perfil" in p.mensaje.text().lower()                       # sin perfil elegido no hay previa
    p.cancelar()


def test_b372_teclear_una_conicidad_que_no_entra_en_la_s_da_error_y_aceptar_no_acepta(app_qt):  # noqa: F811
    """B-372: en una ruta en S (curvas de radio 15) un perfil de r = 5 admite hasta 12° de conicidad. Tecleando 30 en el
    campo, la previa queda en rojo con el máximo y Aceptar no crea nada; con 10 se acepta."""
    import math

    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    from omnicad import api
    from omnicad.timeline.operaciones import OpExtrusion
    s, k = api.Sesion(), 15 * math.sqrt(0.5)
    assert api.llamar(s, "sketch_from_spec", {"name": "P", "plane": "XY", "entities": [
        {"type": "circle", "center": [0, 0], "radius": 5}]})["ok"]
    assert api.llamar(s, "sketch_from_spec", {"name": "R", "plane": "XZ", "entities": [
        {"type": "arc", "start": [0, 0], "mid": [15 - k, k], "end": [15, 15]},
        {"type": "arc", "start": [15, 15], "mid": [15 + k, 30 - k], "end": [30, 30]}]})["ok"]
    doc = s.doc
    perfil, ruta = (doc.estado_final.bocetos[b] for b in list(doc.estado_final.bocetos)[:2])
    hp = hit_desde_ref({"tipo": "perfil", "boceto": doc.operaciones[0].id,
                        **OpExtrusion.referencia_perfil(perfil.perfiles[0])}, doc.estado_final)
    curva = next(iter(ruta.boceto.curvas))
    hr = hit_desde_ref({"tipo": "curva_boceto", "boceto": doc.operaciones[1].id, "curva": curva}, doc.estado_final)
    p, *_ = _panel(CATALOGO["barrido"](), doc, {"perfiles": [hp], "ruta": [hr]})
    p.seccion.boton.setChecked(True)                                   # «Más opciones», donde está la conicidad
    campo = p.widgets["conicidad"]
    for texto, sale in (("30", False), ("10", True)):
        QTest.mouseClick(campo, Qt.LeftButton)
        QTest.keyClick(campo, Qt.Key_A, Qt.ControlModifier)
        QTest.keyClicks(campo, texto)
        QTest.keyClick(campo, Qt.Key_Tab)
        p._t_previa.stop()
        p._calcular_previa()
        assert p._previa_ok is sale, p.mensaje.text()
        if not sale:
            assert "como máximo 12.0°" in p.mensaje.text()
            pasos = len(doc.operaciones)
            QTest.mouseClick(p.boton_ok, Qt.LeftButton)
            assert len(doc.operaciones) == pasos                       # Aceptar no deja pasar la forma gigante
    p.cancelar()
