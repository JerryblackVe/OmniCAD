"""B-339: en Revolución lo de otro plano no se suma a «Perfil» (Fusion: «a coplanar sketch profile or face»): una cara de
otro plano pasa a ser el «Objeto límite» y un perfil de otro plano reemplaza al elegido; lo coplanar se suma."""
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.api import selectores as sl
from omnicad.api.herramientas_boceto import boceto_activo, seleccionar_perfiles
from omnicad.timeline.operaciones import OpExtrusion
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos.solido import Revolucion
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


def _llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], (nombre, args, r)
    return r["result"]


def _hit_perfil(s, estado, boceto, indice=0):
    op = s.paso(boceto)
    sop, br = boceto_activo(s, op.id)
    ref = OpExtrusion.referencia_perfil(seleccionar_perfiles(br, sop, indice)[0])
    return hit_desde_ref({"tipo": "perfil", "boceto": op.id, **ref}, estado)


@pytest.fixture
def panel(tmp_path):
    s = api.Sesion()
    _llamar(s, "create_sketch", name="A", plane="XY")
    _llamar(s, "draw_rectangle", sketch="A", x1=0, y1=0, x2=20, y2=10)
    _llamar(s, "create_sketch", name="B", plane="XY")                 # otro boceto, mismo plano: coplanar
    _llamar(s, "draw_rectangle", sketch="B", x1=30, y1=0, x2=40, y2=10)
    _llamar(s, "create_sketch", name="C", plane="XZ")                 # otro plano
    _llamar(s, "draw_rectangle", sketch="C", x1=40, y1=0, x2=60, y2=10)
    _llamar(s, "create_box", length=30, width=30, height=20, x=-100, name="Caja")
    app = QApplication.instance() or QApplication([])
    v = VentanaPrincipal(s.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    try:
        v.resize(1280, 800)
        v.show()
        p = v.ejecutar_comando(Revolucion())
        yield s, p
    finally:
        if v.panel is not None:
            v.panel.cancelar()
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()


def _tocar(p, hit):
    p._activar(next(c for c in p.campos if c.clave == "perfiles"))
    p._elegida(hit)


def test_un_perfil_coplanar_se_suma_y_uno_de_otro_plano_reemplaza(panel):
    s, p = panel
    estado = p.ctx.estado
    _tocar(p, _hit_perfil(s, estado, "A"))
    _tocar(p, _hit_perfil(s, estado, "B"))
    assert [h["ref"]["boceto"] for h in p.valores["perfiles"]] == [s.paso("A").id, s.paso("B").id]
    _tocar(p, _hit_perfil(s, estado, "C"))
    assert [h["ref"]["boceto"] for h in p.valores["perfiles"]] == [s.paso("C").id]


def test_una_cara_de_otro_plano_pasa_a_ser_el_objeto_limite(panel):
    s, p = panel
    estado = p.ctx.estado
    _tocar(p, _hit_perfil(s, estado, "A"))
    cuerpo, cara = sl.elegir(s, ">X", "cara")[0]
    _tocar(p, hit_desde_ref(sl.referencia(cuerpo, cara), estado))
    assert [h["ref"]["tipo"] for h in p.valores["perfiles"]] == ["perfil"]
    assert p.valores["extension"] == "objeto" and len(p.valores["hasta"]) == 1
