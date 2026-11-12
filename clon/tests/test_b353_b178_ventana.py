"""B-353: B-178 (lo creado después de una unión la sigue) también desde la ventana y al editar: editar un componente hijo y
aceptar sin cambios no lo separa del padre; el Agujero de la ventana guarda la pose y al editarlo no la pierde; una unión
«como está» del hijo con su padre no da el aviso falso de «otra unión ya mueve el componente»."""
import numpy as np
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.api import selectores as sl
from omnicad.nucleo import geometria as g
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos import CATALOGO
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


def _ll(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], (nombre, args, r)
    return r["result"]


def _centro_xy(s, cid):
    (x0, y0, _), (x1, y1, _) = g.caja_envolvente(s.cuerpo(cid).forma)
    return [(x0 + x1) / 2, (y0 + y1) / 2]


def _escena():
    """Base fija y «Bloque» (bloque + marca escondida a x = 103) con una revolución sobre la cara de arriba, a 30°."""
    s = api.Sesion()
    base = _ll(s, "create_box", length=40, width=40, height=10)["bodies_created"][0]["id"]
    bloque = _ll(s, "create_box", length=10, width=10, height=10, x=100, y=50)["bodies_created"][0]["id"]
    marca = _ll(s, "create_box", length=2, width=2, height=6, x=103, y=50)["bodies_created"][0]["id"]
    _ll(s, "create_component", bodies=[base], name="Base", grounded=True)
    _ll(s, "create_component", bodies=[bloque, marca], name="Bloque")
    jid = _ll(s, "create_as_built_joint", origin=">Z", body=bloque, component2="Base", joint_type="revolute")["joint"]["id"]
    _ll(s, "drive_joint", joint=jid, rotation=30)
    return s, bloque, marca, jid


@pytest.fixture
def ventana(tmp_path):
    app = QApplication.instance() or QApplication([])
    ventanas = []

    def abrir(doc):
        v = VentanaPrincipal(doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
        v.resize(1280, 800)
        v.show()
        ventanas.append(v)
        return v
    yield abrir
    for v in ventanas:
        if v.panel is not None:
            v.panel.cancelar()
        v.doc.modificado = False
        v.close()
        v.deleteLater()
    app.processEvents()


def test_editar_el_hijo_y_aceptar_sin_cambios_no_lo_separa_del_padre(ventana):
    s, bloque, marca, jid = _escena()
    x, y = _centro_xy(s, marca)
    hijo = _ll(s, "create_box", length=2, width=2, height=2, x=x, y=y, z=10)["bodies_created"][0]["id"]
    _ll(s, "create_component", bodies=[hijo], name="Hijo", parent="Bloque")
    _ll(s, "drive_joint", joint=jid, rotation=60)
    assert _centro_xy(s, hijo) == pytest.approx(_centro_xy(s, marca), abs=1e-6)
    v = ventana(s.doc)
    v.editar_operacion(s.paso("Hijo").id)
    v.panel.aceptar()                              # sin tocar nada
    for giro in (60, 0):
        _ll(api.Sesion(v.doc), "drive_joint", joint=jid, rotation=giro)
        s2 = api.Sesion(v.doc)
        assert _centro_xy(s2, hijo) == pytest.approx(_centro_xy(s2, marca), abs=1e-6), giro


def test_el_agujero_de_la_ventana_sigue_la_union_y_al_editarlo_no_pierde_la_pose(ventana):
    s, bloque, marca, jid = _escena()
    v = ventana(s.doc)
    cuerpo, cara = sl.elegir(s, ">Z", "cara", bloque)[0]
    hit = hit_desde_ref(sl.referencia(cuerpo, cara), v.doc.estado_final)
    x, y = _centro_xy(s, marca)
    hit["punto"] = [x, y, 10.0]
    p = v.ejecutar_comando(CATALOGO["agujero"]())
    campo = next(c for c in p.campos if c.clave == "colocacion")
    p._activar(campo)
    p._elegida(hit)
    punto = list(p.valores["colocacion"][0]["punto"])            # el comando lo ajusta (se pega a un borde): se usa el que quedó
    p._activar(next(c for c in p.campos if c.clave == "objetivos"))
    p._elegida(hit_desde_ref({"tipo": "cuerpo", "cuerpo": bloque}, v.doc.estado_final))       # solo el bloque, no la marca
    p.set_valor("punta", "plana")
    p.set_valor("diametro", "1 mm")
    p.set_valor("profundidad", "3 mm")
    p.aceptar()
    assert v.panel is None, (p.mensaje.text()[-60:], {k: p.ultima_op.p.get(k) for k in ("objetivos", "punta", "puntos_cara", "profundidad", "extension", "tipo")} if p.ultima_op else None)
    op = next(o for o in v.doc.operaciones if o.TIPO == "agujero")
    assert op.p["puntos_cara"] and op.p["puntos_cara"][0].get("pose") is not None

    comp = v.doc.estado_final.cuerpos[bloque].componente
    m0 = np.asarray(v.doc.estado_final.componentes[comp]["matriz"], float)

    def comprobar():
        s2 = api.Sesion(v.doc)
        for giro in (60, 0):
            _ll(s2, "drive_joint", joint=jid, rotation=giro)
            ahora = np.asarray(s2.doc.estado_final.componentes[comp]["matriz"], float)
            esperado = (ahora @ np.linalg.inv(m0) @ np.append(punto, 1.0))[:2]      # el punto va con el componente
            (cil,) = _ll(s2, "find_faces", body=bloque, selector="%CYLINDER")["faces"]
            assert cil["center"][:2] == pytest.approx(esperado, abs=0.4), giro      # el agujero cae en el borde: media cara
    comprobar()
    v.editar_operacion(op.id)
    v.panel.aceptar()                              # editar sin cambios conserva la pose
    assert next(o for o in v.doc.operaciones if o.TIPO == "agujero").p["puntos_cara"][0].get("pose") is not None
    comprobar()


def test_la_union_como_esta_del_hijo_con_su_padre_no_da_el_aviso_falso():
    s, bloque, marca, jid = _escena()
    x, y = _centro_xy(s, marca)
    hijo = _ll(s, "create_box", length=2, width=2, height=2, x=x, y=y, z=10)["bodies_created"][0]["id"]
    _ll(s, "create_component", bodies=[hijo], name="Hijo", parent="Bloque")
    _ll(s, "create_as_built_joint", origin=">Z", body=hijo, component2="Bloque", joint_type="revolute", name="J2")
    _ll(s, "drive_joint", joint=jid, rotation=60)
    pasos = {p["name"]: p for p in _ll(s, "get_timeline", include_params=False)["steps"]}
    assert pasos["J2"]["status"] == "ok", pasos["J2"]
    assert _centro_xy(s, hijo) == pytest.approx(_centro_xy(s, marca), abs=1e-6)         # sin doble giro del padre
