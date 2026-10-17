"""Gizmo de calcomanía: eventos reales al widget, parámetros, UV y receta (sin mover el cursor del sistema)."""
import math

import numpy as np
import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QHelpEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QToolTip

from omnicad import api
from omnicad.io_archivos import proyecto
from omnicad.ui import manipuladores as mp
from test_manipuladores import _arrastrar, _raton
from test_p23_calcomania import decal as decal, imagen as imagen, llamar
from test_p23_navegador import ventana as ventana


@pytest.fixture
def panel(decal, ventana):
    s, ident = decal
    ventana.set_documento(s.doc)
    ventana.visor.vista("arriba")
    ventana.editar_operacion(ident)
    p = ventana.panel
    p._calcular_previa()
    p.manipuladores.actualizar()
    yield p
    if ventana.panel is not None:
        ventana.panel.cancelar()


def control(p, clave):
    if clave == "libre":
        return next(m for m in p.manipuladores.manips if isinstance(m, mp.PosicionCalcomania))
    return next(m for m in p.manipuladores.manips if getattr(m, "clave", None) == clave)


def punto_control(p, clave):
    m, g = control(p, clave), p.manipuladores
    if clave == "libre":
        return m.punto
    if clave == "angulo":
        return m.asa(g)
    if clave in ("voltear", "voltear_v"):
        return m._geom(g)[0]
    a, b = m.puntos(g)
    return b if clave == "ancho" else (a + b) / 2


def arrastrar(p, clave, destino):
    g = p.manipuladores
    xy, ok = g.pantalla([punto_control(p, clave), destino])
    assert ok.all()
    tocado = g._tocado(QPointF(*xy[0]))
    assert tocado is not None and tocado[0] is control(p, clave)
    _arrastrar(p.visor, *xy)
    p._calcular_previa()
    assert p._previa_ok


def estado_previo(p):
    return p.ctx.doc.previsualizar(p.ultima_op, p.ctx.indice)[0].lienzos[p.ultima_op.id]


def test_rotacion_por_manija_cambia_angulo_y_uv_sin_mover_centro(panel):
    p = panel
    m = control(p, "angulo")
    desde = m.asa(p.manipuladores) - m.centro
    a = math.radians(30)
    destino = m.centro + desde * math.cos(a) + np.cross(m.eje, desde) * math.sin(a)
    uv = estado_previo(p)["malla"]["uv"].copy()
    arrastrar(p, "angulo", destino)
    assert p.manipuladores.valor("angulo") == pytest.approx(30, abs=0.1)
    assert (p.manipuladores.valor("dx"), p.manipuladores.valor("dy")) == (0, 0)
    assert not np.allclose(uv, estado_previo(p)["malla"]["uv"])


@pytest.mark.parametrize("clave,otra", [("dx", "dy"), ("dy", "dx")])
def test_flecha_mueve_solo_su_eje(panel, clave, otra):
    p = panel
    m = control(p, clave)
    destino = punto_control(p, clave) + m.u * 6 + m.v * 4
    arrastrar(p, clave, destino)
    esperado = 6 if clave == "dx" else 4
    assert p.manipuladores.valor(clave) == pytest.approx(esperado, abs=0.02)
    assert p.manipuladores.valor(otra) == 0
    assert estado_previo(p)[clave] == pytest.approx(esperado, abs=0.02)
    assert p.widgets[clave].text() == p.valores[clave]


def test_cuadrado_mueve_libre_las_dos_coordenadas(panel):
    p = panel
    m = control(p, "libre")
    arrastrar(p, "libre", m.punto + m.u * 3 - m.v * 2)
    d = estado_previo(p)
    assert (d["dx"], d["dy"]) == pytest.approx((3, -2), abs=0.02)
    p.aceptar()
    d = list(p.ctx.doc.estado_final.lienzos.values())[-1]
    assert (d["dx"], d["dy"]) == pytest.approx((3, -2), abs=0.02)


@pytest.mark.parametrize("proporcion", [True, False])
def test_codo_escala_uniforme_y_caja_editable(panel, proporcion):
    p = panel
    p.set_valor("mantener_proporcion", proporcion)
    p.set_valor("alto", "13 mm" if not proporcion else "18 mm")
    p._calcular_previa()
    ancho, alto = (estado_previo(p)[k] for k in ("ancho", "alto"))
    m = control(p, "ancho")
    caja = p.manipuladores.cajas["escala"]
    assert caja.text() == "1.00"
    arrastrar(p, "ancho", m.origen + (punto_control(p, "ancho") - m.origen) * 1.5)
    d = estado_previo(p)
    assert (d["ancho"], d["alto"]) == pytest.approx((ancho * 1.5, alto * 1.5), abs=0.01)
    assert p.manipuladores.valor("escala") == pytest.approx(1.5, abs=0.001)
    assert caja.text() == "1.50"
    caja.setText("2.00")
    QTest.keyClick(caja, Qt.Key_Return)
    p._calcular_previa()
    assert p.valores["escala"] == p.widgets["escala"].text() == "2.00"
    assert estado_previo(p)["alto"] == pytest.approx(alto * 2)
    caja.setText("0")
    assert not p.manipuladores.aplicar_caja(caja)
    assert p.valores["escala"] == "2.00"


@pytest.mark.parametrize("clave,eje", [("voltear", 0), ("voltear_v", 1)])
def test_clic_volteo_ida_y_vuelta(panel, clave, eje):
    p, g = panel, panel.manipuladores
    uv = estado_previo(p)["malla"]["uv"].copy()
    for esperado in (True, False):
        xy = g.pantalla([punto_control(p, clave)])[0][0]
        _raton(p.visor, QEvent.MouseButtonPress, xy, Qt.LeftButton, Qt.LeftButton)
        _raton(p.visor, QEvent.MouseButtonRelease, xy, Qt.LeftButton, Qt.NoButton)
        p._calcular_previa()
        assert p.valores[clave] is esperado
        assert p.widgets[clave].isChecked() is esperado
        resultado = uv.copy()
        if esperado:
            resultado[:, eje] = 1 - resultado[:, eje]
        assert np.allclose(estado_previo(p)["malla"]["uv"], resultado)


@pytest.mark.parametrize("clave", ["libre", "dx", "dy", "angulo", "ancho", "voltear", "voltear_v"])
def test_resaltado_tooltip_y_dibujo_en_plano(panel, clave):
    p, g = panel, panel.manipuladores
    m = control(p, clave)
    xy = g.pantalla([punto_control(p, clave)])[0][0]
    _raton(p.visor, QEvent.MouseMove, xy, Qt.NoButton, Qt.NoButton)
    assert g._hover[0] == m.ident
    antes, despues = m.dibujar(g, None), m.dibujar(g, g._hover[1])
    assert any(a[2] != b[2] for a, b in zip(antes, despues, strict=True))
    centro, normal = control(p, "libre").punto, control(p, "libre").normal
    assert all(np.allclose((pr[1] - centro) @ normal, 0, atol=1e-8) for pr in antes)
    local = QPointF(*xy).toPoint()
    QApplication.sendEvent(p.visor, QHelpEvent(QEvent.ToolTip, local, p.visor.mapToGlobal(local)))
    assert QToolTip.text() == m.ayuda
    QToolTip.hideText()
    assert not any(type(m) is vieja for m in g.manips for vieja in (mp.Posicion, mp.Flecha, mp.AsaRadial))


def test_api_escala_parametrica_receta_y_compatibilidad(decal, tmp_path):
    s, ident = decal
    llamar(s, "create_parameter", name="factor", expression=1.5)
    llamar(s, "set_decal", feature=ident, keep_aspect=False, width=20, height=7, scale="factor")
    d = s.doc.estado_final.lienzos[ident]
    assert (d["ancho"], d["alto"]) == pytest.approx((30, 10.5))
    llamar(s, "set_parameter", name="factor", expression=2)
    assert s.doc.estado_final.lienzos[ident]["alto"] == 14
    ruta = proyecto.guardar(s.doc, tmp_path / "escala.omnicad")
    abierto = proyecto.abrir(ruta)
    assert abierto.estado_final.lienzos[ident]["ancho"] == 40
    antes = s.doc.a_dict()
    for valor in (0, -1, "NaN", "1e309"):
        assert not api.llamar(s, "set_decal", {"feature": ident, "scale": valor})["ok"]
        assert s.doc.a_dict() == antes
    datos = s.doc.a_dict()
    next(op for op in datos["operaciones"] if op["id"] == ident)["params"].pop("escala")
    s.doc._cargar(datos)
    assert s.doc.estado_final.lienzos[ident]["ancho"] == 20


def test_cli_expone_y_aplica_scale(decal, tmp_path, capsys):
    from omnicad.cli import main
    s, ident = decal
    ruta = proyecto.guardar(s.doc, tmp_path / "cli.omnicad")
    assert main(["call", "set_decal", "--doc", str(ruta), f"feature={ident}", "scale=2"]) == 0
    assert proyecto.abrir(ruta).estado_final.lienzos[ident]["ancho"] == 72
    assert main(["describe", "set_decal", "--json"]) == 0
    assert '"scale"' in capsys.readouterr().out
