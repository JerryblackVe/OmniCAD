# -*- coding: utf-8 -*-
"""P-138: el clic de otro rol pasa al campo que lo acepta (eje, ruta) y el campo obligatorio que aparece vacío
(«Hasta objeto», «Inicio: Objeto») se activa solo. Clics simulados en el visor de la ventana."""
import numpy as np
import pytest
from PySide6.QtCore import QPoint, QPointF, QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.timeline.operaciones import OpExtrusion
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos import CATALOGO
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


@pytest.fixture
def ventana(tmp_path):
    """Boceto en XY: un rectángulo (perfil) y, aparte, una línea vertical en x = 0 (eje o ruta)."""
    app = QApplication.instance() or QApplication([])
    s = api.Sesion()
    r = api.llamar(s, "sketch_from_spec", {"entities": [
        {"type": "rectangle", "corner1": [10, 0], "corner2": [20, 10]},
        {"type": "line", "start": [0, -5], "end": [0, 15]}]})
    assert r["ok"], r
    v = VentanaPrincipal(s.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.resize(1280, 800)
    v.show()
    QTest.qWait(100)
    yield v, s.doc.operaciones[-1].id
    if v.panel is not None:
        v.panel.cancelar()
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app.processEvents()


def _abrir_con_perfil(v, boceto, clave):
    p = v.ejecutar_comando(CATALOGO[clave]())
    br = v.doc.estado_final.bocetos[boceto]
    p._elegida(hit_desde_ref({"tipo": "perfil", "boceto": boceto, **OpExtrusion.referencia_perfil(br.perfiles[0])},
                             p.ctx.estado))
    assert p.activa.clave == "perfiles"
    return p


def _clic_en_la_linea(v):
    """Clic simulado sobre la línea x = 0, en un punto que no es perfil."""
    vis = v.visor
    for y in np.linspace(-4, 14, 19):
        q, ok = vis._a_pantalla(np.array([[0.0, y, 0.0]]), vis.matriz_mvp())
        pos = QPointF(*q[0])
        if ok[0] and vis.elegir_entidad(pos, {"perfil", "cara_plana"}) is None and vis.elegir_entidad(pos, {"eje"}):
            QTest.mouseClick(vis, Qt.LeftButton, Qt.NoModifier, QPoint(int(q[0][0]), int(q[0][1])))
            return
    raise AssertionError("no se ve la línea")


@pytest.mark.parametrize("clave,destino", [("revolucion", "eje"), ("barrido", "ruta")])
def test_p138_el_clic_en_la_linea_va_al_eje_o_a_la_ruta(ventana, clave, destino):
    """Con «Perfil» activo, tocar la línea no se descarta: entra al campo que la acepta (antes había que tocar su fila)."""
    v, boceto = ventana
    p = _abrir_con_perfil(v, boceto, clave)
    _clic_en_la_linea(v)
    assert len(p.valores[destino]) == 1 and p.valores[destino][0]["ref"]["tipo"] == "curva_boceto"
    assert len(p.valores["perfiles"]) == 1


def test_p138_con_componentes_arrastrados_el_clic_no_se_desvia(ventana, monkeypatch):
    """Mientras se ven componentes fuera de su lugar el visor no elige nada (`_sin_capturar`): el desvío tampoco."""
    v, boceto = ventana
    p = _abrir_con_perfil(v, boceto, "revolucion")
    monkeypatch.setattr(type(v.visor), "_sin_capturar", property(lambda _s: True))
    _clic_en_la_linea(v)
    assert not p.valores.get("eje")


def test_p138_hasta_objeto_e_inicio_objeto_activan_su_campo(ventana):
    v, boceto = ventana
    p = _abrir_con_perfil(v, boceto, "extruir")
    p.set_valor("extension", "objeto")
    assert p.activa.clave == "hasta"
    p.set_valor("inicio", "objeto")
    assert p.activa.clave == "inicio_objeto"
    p.set_valor("operacion", "cortar")         # «Objetos» es optativo: no roba el foco
    assert p.activa.clave == "inicio_objeto"


def test_p138_un_clic_en_el_vacio_no_elige_el_perfil(ventana):
    """Sin cuerpos en la vista, el rayo que no toca ningún perfil daba t = inf y `inf <= inf` lo elegía igual: tocar el
    vacío metía (o sacaba) el rectángulo."""
    v, boceto = ventana
    p = v.ejecutar_comando(CATALOGO["extruir"]())
    antes = [h["ref"] for h in p.valores["perfiles"] or []]      # Fusion elige solo el único perfil
    vis = v.visor
    q, _ok = vis._a_pantalla(np.array([[60.0, 60.0, 0.0]]), vis.matriz_mvp())
    assert vis.elegir_entidad(QPointF(*q[0]), {"perfil", "cara_plana"}) is None
    QTest.mouseClick(vis, Qt.LeftButton, Qt.NoModifier, QPoint(int(q[0][0]), int(q[0][1])))
    assert [h["ref"] for h in p.valores["perfiles"] or []] == antes
