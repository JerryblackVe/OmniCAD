"""B-385: Barrido, Solevación y Nervio se configuran y reabren desde la ventana."""
import math

import pytest
from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QComboBox

from omnicad import api
from omnicad.api.herramientas_boceto import boceto_activo, seleccionar_perfiles
from omnicad.nucleo import geometria as geo
from omnicad.timeline.operaciones import OpExtrusion
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos.crear import Barrido, Nervio, Red, Solevacion
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


def _llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], (nombre, args, r)
    return r["result"]


def _escena(tipo):
    s = api.Sesion()
    if tipo in ("barrido", "solevacion"):
        _llamar(s, "create_sketch", plane="XY", name="Perfil")
        _llamar(s, "draw_circle", radius=2 if tipo == "barrido" else 10)
    if tipo == "barrido":
        for nombre, x, alto in (("Ruta", 0, 10), ("Carril", 5, 6)):
            _llamar(s, "create_sketch", plane="XZ", name=nombre)
            _llamar(s, "draw_line", start_x=x, start_y=0, end_x=x, end_y=alto)
    elif tipo == "solevacion":
        _llamar(s, "create_construction_plane", plane="XY", offset=10, name="Arriba")
        _llamar(s, "create_construction_point", type="tres_planos", references=["XZ", "YZ", "Arriba"], name="Punta")
    else:
        _llamar(s, "create_box", length=40, width=60, height=5, x=0, y=-30, z=0, anchor="corner")
        _llamar(s, "create_box", length=5, width=60, height=50, x=0, y=-30, z=0, anchor="corner", operation="join")
        _llamar(s, "create_sketch", plane="XZ", name="Nervio")
        _llamar(s, "draw_line", start_x=35, start_y=5, end_x=5, end_y=45)
    return s


@pytest.fixture
def ventana(tmp_path, request):
    s = _escena(request.param)
    app = QApplication.instance() or QApplication([])
    v = VentanaPrincipal(s.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    try:
        v.resize(1280, 800)
        v.show()
        yield s, v
    finally:
        if v.panel is not None:
            v.panel.cancelar()
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()


def _elegir_opcion(p, clave, dato):
    """Clic en el botón de la fila, o flechas del desplegable hasta la opción."""
    w = p.widgets[clave]
    if isinstance(w, QComboBox):
        _flechas(w, dato)
    else:
        QTest.mouseClick(w.grupo.button(w.findData(dato)), Qt.LeftButton)
    assert p.valores[clave] == dato


def _flechas(w, dato):
    assert w.findData(dato) >= 0, f"Falta la opción {dato}"
    w.setFocus()
    tecla = Qt.Key_Down if w.findData(dato) > w.currentIndex() else Qt.Key_Up
    while w.currentData() != dato:
        QTest.keyClick(w, tecla)


def _tocar(p, s, clave, ref):
    p._activar(next(c for c in p.campos if c.clave == clave))
    p._elegida(hit_desde_ref(ref, s.doc.estado_final))


def _perfil(s):
    op = s.paso("Perfil")
    sop, br = boceto_activo(s, op.id)
    return {"tipo": "perfil", "boceto": op.id, **OpExtrusion.referencia_perfil(seleccionar_perfiles(br, sop, 0)[0])}


def _curva(s, nombre):
    op = s.paso(nombre)
    _, br = boceto_activo(s, op.id)
    return {"tipo": "curva_boceto", "boceto": op.id, "curva": next(iter(br.boceto.curvas))}


def _teclear(p, clave, texto):
    w = p.widgets[clave]
    QTest.mouseClick(w, Qt.LeftButton)
    QTest.keyClick(w, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClicks(w, texto)
    QTest.keyClick(w, Qt.Key_Tab)
    assert p.valores[clave] == texto


def _aceptar(s, v, p):
    antes = len(s.doc.operaciones)
    QTest.mouseClick(p.boton_ok, Qt.LeftButton)
    assert v.panel is None, p.mensaje.text()
    assert len(s.doc.operaciones) == antes + 1
    forma = list(s.doc.estado_final.cuerpos.values())[-1].forma
    assert geo.es_valida(forma)
    return s.doc.operaciones[-1], geo.volumen(forma)


@pytest.mark.parametrize("ventana", ["barrido"], indirect=True)
@pytest.mark.parametrize("extension,fraccion,volumen", [
    ("perpendicular", "1", math.pi * 4 * 6),
    ("completa", "1", 152.47),
    ("completa", "0.5", 207.76),
])
def test_barrido_con_carril_extension_y_fraccion_reabren(ventana, extension, fraccion, volumen):
    s, v = ventana
    p = v.ejecutar_comando(Barrido())
    _elegir_opcion(p, "tipo", "ruta_carril")
    assert "extension" in p.widgets, "Falta Extensión en el barrido con rail"
    w = p.widgets["extension"]
    assert w.isVisible() and w.currentData() == "perpendicular"
    assert [w.itemText(i) for i in range(w.count())] == ["Perpendicular a la ruta", "Extensión completa"]
    assert not p.widgets["distancia_carril"].isVisible()
    _elegir_opcion(p, "extension", "completa")
    assert p.widgets["distancia_carril"].isVisible()
    _teclear(p, "distancia_carril", fraccion)
    _elegir_opcion(p, "extension", extension)
    _tocar(p, s, "perfiles", _perfil(s))
    _tocar(p, s, "ruta", _curva(s, "Ruta"))
    _tocar(p, s, "carril", _curva(s, "Carril"))
    _elegir_opcion(p, "operacion", "nuevo")
    op, obtenido = _aceptar(s, v, p)
    assert obtenido == pytest.approx(volumen, rel=1e-3)
    v.editar_operacion(op.id)
    q = v.panel
    assert q.widgets["extension"].currentData() == extension
    assert q.valores["distancia_carril"] == fraccion
    assert q.widgets["distancia_carril"].isVisible() == (extension == "completa")


@pytest.mark.parametrize("ventana", ["solevacion"], indirect=True)
def test_solevacion_punto_tangente_crea_cupula_y_reabre(ventana):
    s, v = ventana
    p = v.ejecutar_comando(Solevacion())
    _tocar(p, s, "secciones", _perfil(s))
    _tocar(p, s, "secciones", {"tipo": "punto", "id": s.paso("Punta").id})
    tabla = p.widgets["secciones"].tabla
    QTest.mouseClick(tabla.viewport(), Qt.LeftButton, pos=tabla.visualItemRect(tabla.item(1, 0)).center())
    w = tabla.cellWidget(1, 1)
    assert [w.itemText(i) for i in range(w.count())] == ["Aguda", "Tangente"]
    _flechas(w, "punto_tangente")
    assert p.widgets["peso_fin"].isVisible()
    campo = next(c for c in p.campos if c.clave == "peso_fin")
    assert campo.etiqueta_si(p.valores) == "Peso de tangencia"
    _teclear(p, "peso_fin", "1")
    _elegir_opcion(p, "operacion", "nuevo")
    op, volumen = _aceptar(s, v, p)
    assert volumen == pytest.approx(math.pi * 10 ** 2 * 10 / 2, rel=1e-3)   # B-464: paraboloide de Fusion, π·r²·h/2
    assert op.p["condicion_fin"] == {"tipo": "punto_tangente", "angulo": "0 deg", "peso": "1"}
    v.editar_operacion(op.id)
    q = v.panel
    assert q.widgets["secciones"].tabla.cellWidget(1, 1).currentData() == "punto_tangente"
    assert q.valores["peso_fin"] == "1" and q.widgets["peso_fin"].isVisible()


@pytest.mark.parametrize("ventana", ["nervio"], indirect=True)
def test_nervio_radio_empalme_e_invertir_extraccion_reabren(ventana):
    s, v = ventana
    p = v.ejecutar_comando(Nervio())
    assert p.widgets["radio_empalme"].isVisible(), "Falta Radio del empalme en Nervio"
    assert "invertir_desmoldeo" in p.widgets and p.widgets["invertir_desmoldeo"].isVisible()
    _tocar(p, s, "curvas", _curva(s, "Nervio"))
    _teclear(p, "espesor", "2 mm")
    _teclear(p, "radio_empalme", "0 mm")
    op, sin_empalme = _aceptar(s, v, p)
    assert sin_empalme == pytest.approx(26700, rel=1e-6)
    v.editar_operacion(op.id)
    q = v.panel
    _teclear(q, "radio_empalme", "1 mm")
    QTest.mouseClick(q.widgets["invertir_desmoldeo"], Qt.LeftButton, pos=QPoint(8, 7))
    assert q.valores["invertir_desmoldeo"] is True
    QTest.mouseClick(q.boton_ok, Qt.LeftButton)
    assert v.panel is None, q.mensaje.text()
    forma = list(s.doc.estado_final.cuerpos.values())[-1].forma
    assert geo.es_valida(forma) and geo.volumen(forma) > sin_empalme + 1
    v.editar_operacion(op.id)
    q = v.panel
    assert q.valores["radio_empalme"] == "1 mm" and q.widgets["invertir_desmoldeo"].isChecked()
    q.cancelar()
    p = v.ejecutar_comando(Red())
    assert p.widgets["radio_empalme"].isVisible()
    assert not p.widgets["invertir_desmoldeo"].isVisible()
