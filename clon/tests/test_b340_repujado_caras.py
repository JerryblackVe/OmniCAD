"""B-340: en Repujado una cara de un cuerpo no es un «Perfil»: va a «Caras» aunque esté activa la fila «Perfiles»
(Fusion: perfiles de boceto y, aparte, las «Faces»); varias caras se suman y tocarla otra vez la saca."""
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.api import selectores as sl
from omnicad.api.herramientas_boceto import boceto_activo, seleccionar_perfiles
from omnicad.timeline.operaciones import OpExtrusion
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos import CATALOGO
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


def _ll(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], (nombre, args, r)
    return r["result"]


@pytest.fixture
def panel(tmp_path):
    s = api.Sesion()
    _ll(s, "create_sketch", name="Circ", plane="XY")
    _ll(s, "draw_circle", sketch="Circ", center_x=0, center_y=0, radius=3)
    _ll(s, "create_box", length=30, width=30, height=20, x=-100, name="Caja")
    app = QApplication.instance() or QApplication([])
    v = VentanaPrincipal(s.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    try:
        v.resize(1280, 800)
        v.show()
        yield s, v.ejecutar_comando(CATALOGO["repujado"]())
    finally:
        if v.panel is not None:
            v.panel.cancelar()
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()


def _tocar(p, hit):
    p._activar(next(c for c in p.campos if c.clave == "perfiles"))        # la fila «Perfiles» activa, como la deja el panel
    p._elegida(hit)


def _cara(s, p, selector):
    cuerpo, cara = sl.elegir(s, selector, "cara")[0]
    return hit_desde_ref(sl.referencia(cuerpo, cara), p.ctx.estado)


def test_las_caras_del_cuerpo_van_a_caras_y_no_a_perfiles(panel):
    s, p = panel
    op = s.paso("Circ")
    sop, br = boceto_activo(s, op.id)
    ref = OpExtrusion.referencia_perfil(seleccionar_perfiles(br, sop, 0)[0])
    _tocar(p, hit_desde_ref({"tipo": "perfil", "boceto": op.id, **ref}, p.ctx.estado))
    _tocar(p, _cara(s, p, ">Z"))
    _tocar(p, _cara(s, p, "<Z"))
    assert [h["ref"]["tipo"] for h in p.valores["perfiles"]] == ["perfil"]
    assert [h["ref"]["tipo"] for h in p.valores["caras"]] == ["cara", "cara"]           # se suman, no se reemplazan
    _tocar(p, _cara(s, p, ">Z"))                                                        # otra vez: la saca
    assert len(p.valores["caras"]) == 1 and len(p.valores["perfiles"]) == 1
