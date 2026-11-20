# -*- coding: utf-8 -*-
"""Cobertura del comando INSPECCIONAR › Mapa de desviación (`mapa_desviacion`), que la tabla de
`docs/plan_boceto_perfecto.md` marcaba sin test automático. El núcleo y las herramientas `compare_to_mesh` y
`show_deviation_map` ya los prueba `test_comparar_malla.py`; acá falta el comando en sí.

La ayuda de Fusion no trae este comando en el espacio de diseño (buscado: se inspira en Mesh Section Analysis
y en los mapas de desviación de la ingeniería inversa, ver `nucleo/comparar_malla.py`), así que fija lo que ya
hace: un caso numérico (una caja corrida 2 mm: abajo sobra +2, arriba falta −2) y el caso borde (los argumentos
con los que no se puede pintar nada). No cambia código de la app.
"""
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.ui.comando import ContextoComando, ErrorComando, PanelComando
from omnicad.ui.comandos import CATALOGO


def _llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def _cajas(s):
    """Dos cajas de 20 mm: la referencia queda 2 mm más arriba (al cuerpo le sobra +2 abajo y le falta −2 arriba)."""
    a = _llamar(s, "create_box", length=20, width=20, height=20, z=-10)["bodies_created"][0]["id"]
    b = _llamar(s, "create_box", length=20, width=20, height=20, z=-8)["bodies_created"][0]["id"]
    return a, b


@pytest.fixture
def ventana(tmp_path_factory):
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    app = QApplication.instance() or QApplication([])
    prefs = QSettings(str(tmp_path_factory.mktemp("prep_desviacion") / "prefs.ini"), QSettings.IniFormat)
    v = VentanaPrincipal(prefs=Preferencias(prefs))
    v.resize(1280, 720)
    v.show()
    app.processEvents()
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app.processEvents()


def test_una_caja_corrida_2_mm_pinta_mas_2_y_menos_2_y_lo_dice_en_el_panel(ventana):
    """El caso numérico: la cara de abajo del cuerpo queda afuera de la referencia (+2, rojo: sobra material) y
    la de arriba adentro (−2, azul: falta); el panel muestra el mínimo y el máximo y la referencia no se dibuja
    (coincidiría con el cuerpo y taparía los colores, dice la ayuda del comando)."""
    s = api.Sesion()
    a, b = _cajas(s)
    ventana.set_documento(s.doc)
    cmd = CATALOGO["mapa_desviacion"]()
    ctx = ContextoComando(s.doc, ventana)
    valores = cmd.desde_params({"cuerpos": [a], "referencia": b, "tolerancia": 0.1}, ctx)
    panel = PanelComando(cmd, ctx, ventana.visor, valores)
    try:
        cmd.mostrar(panel.valores, ctx)
        assert cmd.pintado()
        assert cmd._valores.max() == pytest.approx(2.0, abs=0.05)
        assert cmd._valores.min() == pytest.approx(-2.0, abs=0.05)
        assert panel.widgets["extremos"].text() == "Mínimo -2 mm · Máximo 2 mm"
        mallas = ventana.visor.mallas_analisis
        assert len(mallas[a][0]) > 0 and len(mallas[b][0]) == 0
    finally:
        panel.cancelar()
        panel.deleteLater()


def test_el_mismo_cuerpo_de_referencia_y_la_tolerancia_mala_se_rechazan():
    """El caso borde: un cuerpo contra sí mismo no dice nada, y la tolerancia es una distancia, mayor que cero
    (la escala de colores la divide; con cero el mapa no tendría verde)."""
    s = api.Sesion()
    a, b = _cajas(s)
    ctx = ContextoComando(s.doc)
    cmd = CATALOGO["mapa_desviacion"]()
    mismo = cmd.desde_params({"cuerpos": [a], "referencia": a, "tolerancia": 0.1}, ctx)
    with pytest.raises(ErrorComando, match="mismo"):
        cmd.construir(mismo, ctx)
    for tolerancia in (0, -0.5):
        v = cmd.desde_params({"cuerpos": [a], "referencia": b, "tolerancia": tolerancia}, ctx)
        with pytest.raises(ErrorComando, match="mayor que cero"):
            cmd.construir(v, ctx)
