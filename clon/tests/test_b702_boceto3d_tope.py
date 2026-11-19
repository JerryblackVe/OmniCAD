"""B-702: el Boceto 3D rechaza coordenadas por encima del tope de 1 km (como las cotas), con un aviso de 1 renglón y
el campo en rojo; el tope mismo y lo normal se admiten."""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from test_b572_puntos_3d_intro import _paleta, _teclear
from test_p23_navegador import v as v, ventana as ventana  # noqa: F401  (fixtures de la ventana en vivo)

from omnicad import api
from omnicad.restricciones import Boceto, ErrorBoceto
from omnicad.restricciones import boceto3d as b3


def test_el_nucleo_rechaza_coordenadas_enormes():
    b = Boceto()
    with pytest.raises(ErrorBoceto, match=r"Máximo 1\.000\.000 mm"):
        b3.agregar_linea(b, [0, 0, 0], [1e12, 0, 0])
    assert not b3.datos(b)["puntos"] and not b3.datos(b)["curvas"]       # no quedó nada a medias
    b3.agregar_linea(b, [0, 0, 0], [1e6, -1e6, 0])                       # el tope mismo se admite


def test_la_api_rechaza_el_punto_enorme_y_acepta_el_normal():
    s = api.Sesion()
    api.llamar(s, "create_sketch", {})
    r = api.llamar(s, "draw_point_3d", {"x": 1e12, "y": 0, "z": 0})
    assert not r["ok"] and "1 km" in r["mensaje"], r          # la API ya tenía su tope
    assert api.llamar(s, "draw_point_3d", {"x": 10, "y": 0, "z": 0})["ok"]


def test_el_panel_avisa_y_pinta_el_campo(v, tmp_path, monkeypatch):
    paleta = _paleta(v, tmp_path)
    lz = v.modo_boceto.lienzo
    avisos = []
    monkeypatch.setattr(v, "mensaje", lambda texto, ms=5000: avisos.append(texto))
    _teclear(paleta.puntos3d, "0,0,0; 1e12,0,0")
    assert not lz.b.geo3d.get("curvas") and paleta.puntos3d.styleSheet()
    (aviso,) = avisos
    assert "\n" not in aviso and "Máximo" in aviso, aviso
    QTest.keyClick(paleta.puntos3d, Qt.Key_Backspace)
    assert not paleta.puntos3d.styleSheet()
    avisos.clear()
    paleta.bloqueo3d.setCurrentIndex(paleta.bloqueo3d.findData("z"))     # con eje: el que se pasa es el «Largo»
    paleta.puntos3d.setText("0, 0, 0")
    _teclear(paleta.largo3d, "1e12")
    assert not lz.b.geo3d.get("curvas") and paleta.largo3d.styleSheet() and not paleta.puntos3d.styleSheet()
    assert "Máximo" in avisos[-1]
    _teclear(paleta.largo3d, "20")
    assert len(lz.b.geo3d["curvas"]) == 1
