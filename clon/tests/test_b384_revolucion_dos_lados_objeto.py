"""B-384 / H-88: Revolución «A objeto» ofrece la Dirección como Fusion (Un lado o Dos lados, cada lado hasta su objeto);
Simétrica queda solo para el ángulo."""
import math

import pytest
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
from OCP.gp import gp_Pnt
from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QComboBox

from omnicad import api
from omnicad.api.herramientas_construccion import _referencia
from omnicad.api.herramientas_boceto import boceto_activo, seleccionar_perfiles
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import superficies as sf
from omnicad.timeline.operaciones import OpExtrusion
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos.solido import Revolucion
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal

Z = (0.0, 0.0, 1.0)
VERTICE_45 = [5, -5, 10]                       # a 45° del perfil, girando hacia -Y (el lado 2)


def _llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], (nombre, args, r)
    return r["result"]


def _perfil():
    """Rectángulo en XZ (x 10..20, z 0..5): gira alrededor de Z; el lado 1 va hacia +Y y el lado 2 hacia -Y."""
    s = api.Sesion()
    _llamar(s, "create_sketch", plane="XZ", name="Perfil")
    _llamar(s, "draw_rectangle", x1=10, y1=0, x2=20, y2=5)
    _llamar(s, "create_box", length=10, width=10, height=10, name="Tope")            # esquinas en (±5, ±5, 0..10)
    return s


def _sector(grados):
    return math.pi * (20 ** 2 - 10 ** 2) * 5 * grados / 360


def _volumen(s):
    return geo.volumen(list(s.doc.estado_final.cuerpos.values())[-1].forma)


def test_solido_dos_lados_gira_cada_lado_hasta_su_objeto():
    s = _perfil()
    _llamar(s, "revolve", sketch="Perfil", axis="z", to_object="YZ", direction="two_sides", to_object2=VERTICE_45,
            operation="new_body")
    assert _volumen(s) == pytest.approx(_sector(90 + 45), rel=1e-4)
    r = api.llamar(s, "revolve", {"sketch": "Perfil", "axis": "z", "to_object": "YZ", "direction": "two_sides"})
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS" and "to_object2" in str(r)


def test_superficie_dos_lados_gira_cada_lado_hasta_su_objeto():
    perfil = [BRepBuilderAPI_MakeEdge(gp_Pnt(10, 0, 0), gp_Pnt(10, 0, 10)).Edge()]
    completa = 2 * math.pi * 10 * 10
    dos = sf.revolver_superficie(perfil, (0, 0, 0), Z, 0, direccion="dos_lados", hasta=("punto", (0, 10, 5)),
                                 hasta2=("plano", geo.Plano("XZ")))
    assert geo.area(dos) == pytest.approx(completa * (90 + 180) / 360, rel=1e-6) and geo.es_valida(dos)
    with pytest.raises(geo.ErrorGeometria, match="lado 2"):
        sf.revolver_superficie(perfil, (0, 0, 0), Z, 0, direccion="dos_lados", hasta=("punto", (0, 10, 5)))


def test_api_de_superficie_pasa_el_objeto_del_lado_2():
    s = _perfil()
    _llamar(s, "create_surface_revolve", profiles={"sketch": "Perfil", "profile": 0}, axis="z", to_object="YZ",
            direction="two_sides", to_object2=VERTICE_45)
    paso = s.doc.operaciones[-1]
    assert paso.p["lados"] == "dos_lados" and paso.p["hasta2"] is not None


# ---------------------------------------------------------------- el panel, como lo usa una persona
@pytest.fixture
def ventana(tmp_path):
    s = _perfil()
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
    """Como la persona: clic en el botón de la fila, o flechas en el desplegable hasta la opción."""
    w = p.widgets[clave]
    if isinstance(w, QComboBox):
        w.setFocus()
        tecla = Qt.Key_Down if w.findData(dato) > w.currentIndex() else Qt.Key_Up
        while w.currentData() != dato:
            QTest.keyClick(w, tecla)
    else:
        QTest.mouseClick(w.grupo.button(w.findData(dato)), Qt.LeftButton)
    assert p.valores[clave] == dato


def _tocar(p, s, clave, ref):
    p._activar(next(c for c in p.campos if c.clave == clave))
    p._elegida(hit_desde_ref(ref, s.doc.estado_final))


def _hit_perfil(s):
    op = s.paso("Perfil")
    sop, br = boceto_activo(s, op.id)
    return {"tipo": "perfil", "boceto": op.id, **OpExtrusion.referencia_perfil(seleccionar_perfiles(br, sop, 0)[0])}


def test_panel_a_objeto_muestra_un_lado_y_dos_lados(ventana):
    s, v = ventana
    p = v.ejecutar_comando(Revolucion())
    if not p.valores.get("perfiles"):          # B-471: con un solo perfil Revolución ya lo trae elegido
        _tocar(p, s, "perfiles", _hit_perfil(s))
    _tocar(p, s, "eje", {"tipo": "eje", "id": "Z"})
    _elegir_opcion(p, "extension", "objeto")
    direccion = p.widgets["direccion"]
    assert direccion.isVisible(), "Fusion muestra la Dirección con «A objeto»"
    assert [direccion.itemData(i) for i in range(direccion.count())] == ["un_lado", "dos_lados"]
    assert not p.widgets["hasta2"].isVisible()
    _elegir_opcion(p, "direccion", "dos_lados")
    assert p.widgets["hasta2"].isVisible()
    _tocar(p, s, "hasta", {"tipo": "plano", "id": "YZ"})
    _tocar(p, s, "hasta2", _referencia(s, VERTICE_45, {"vertice"}, None))
    _elegir_opcion(p, "operacion", "nuevo")
    p.aceptar()
    op = s.doc.operaciones[-1]
    assert op.p["direccion"] == "dos_lados" and op.p["hasta2"] is not None
    assert _volumen(s) == pytest.approx(_sector(135), rel=1e-4)
    v.editar_operacion(op.id)                                                    # reabrir: vuelve lo elegido
    assert v.panel.valores["direccion"] == "dos_lados" and v.panel.valores["hasta2"]


def test_panel_con_angulo_sigue_ofreciendo_simetrica(ventana):
    s, v = ventana
    p = v.ejecutar_comando(Revolucion())
    _elegir_opcion(p, "extension", "angulo")
    direccion = p.widgets["direccion"]
    assert "simetrica" in [direccion.itemData(i) for i in range(direccion.count())]


def test_dos_lados_que_pasan_de_una_vuelta_dan_error():
    """90° hacia un lado y 300° hacia el otro: la superficie quedaba encimada (108 % de una vuelta) sin aviso."""
    perfil = [BRepBuilderAPI_MakeEdge(gp_Pnt(10, 0, 0), gp_Pnt(10, 0, 10)).Edge()]
    with pytest.raises(geo.ErrorGeometria, match="pasan de 360°"):
        sf.revolver_superficie(perfil, (0, 0, 0), Z, 0, direccion="dos_lados", hasta=("punto", (0, 10, 5)),
                               hasta2=("punto", (5, 8.660254, 5)))
    s = _perfil()
    _llamar(s, "create_box", length=10, width=10, height=10, y=3.660254, name="Tope60")   # esquina en (5, 8.66, 10): 60°
    r = api.llamar(s, "revolve", {"sketch": "Perfil", "axis": "z", "to_object": "YZ", "direction": "two_sides",
                                  "to_object2": [5, 8.660254, 10], "operation": "new_body"})
    assert not r["ok"] and "360°" in str(r)
