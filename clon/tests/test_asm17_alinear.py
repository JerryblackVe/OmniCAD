"""ASM-17 › Alinear (Restricción de componentes, `constrain_components`): planos coplanares con la orientación que
menos gira, ejes concéntricos, puntos coincidentes, el componente fijo no se mueve y los errores claros."""
import json

import pytest

from omnicad import api
from omnicad.nucleo import geometria as g


def _ll(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], (nombre, args, r)
    return r["result"]


def _falla(s, nombre, kind, **args):
    receta = json.dumps(s.doc.a_dict(), sort_keys=True)
    r = api.llamar(s, nombre, args)
    assert not r["ok"] and r["error_kind"] == kind, r
    assert json.dumps(s.doc.a_dict(), sort_keys=True) == receta          # atómica
    return r


def _caja(s, cid):
    return [round(v, 4) + 0.0 for p in g.caja_envolvente(s.cuerpo(cid).forma) for v in p]


@pytest.fixture
def dos():
    """A 20×20×10 fija en el origen (x, y −10..10, z 0..10) y B 10×10×10 en (45..55, 25..35, 7..17)."""
    s = api.Sesion()
    a = _ll(s, "create_box", length=20, width=20, height=10, name="A")["bodies_created"][0]["id"]
    b = _ll(s, "create_box", length=10, width=10, height=10, x=50, y=30, z=7, name="B")["bodies_created"][0]["id"]
    _ll(s, "create_component", bodies=[a], name="CA", grounded=True)
    _ll(s, "create_component", bodies=[b], name="CB")
    return s, a, b


def test_dos_caras_hacia_el_mismo_lado_quedan_al_ras_sin_mover_en_el_plano(dos):
    s, a, b = dos
    r = _ll(s, "constrain_components", geometry1=">Z", geometry2=">Z", body1=b, body2=a)
    assert _caja(s, b) == [45, 25, 0, 55, 35, 10]                        # la tapa de B al nivel de la de A, x e y iguales
    assert [c["name"] for c in r["moved_components"]] == ["CB"] and _caja(s, a) == [-10, -10, 0, 10, 10, 10]


def test_dos_caras_enfrentadas_se_apoyan_con_su_desfase(dos):
    s, a, b = dos
    _ll(s, "constrain_components", geometry1="<X", geometry2=">X", body1=b, body2=a, offset=2)
    assert _caja(s, b) == [12, 25, 7, 22, 35, 17]                        # a 2 mm de la cara +X de A, sin girar y sin correrse en y ni z
    assert g.volumen(s.cuerpo(b).forma) == pytest.approx(1000)


def test_flip_invierte_la_orientacion(dos):
    s, a, b = dos
    _ll(s, "constrain_components", geometry1=">Z", geometry2=">Z", body1=b, body2=a, flip=True)
    assert _caja(s, b)[2:3] + _caja(s, b)[5:6] == [10, 20]               # B queda boca abajo sobre la tapa de A


def test_dos_cilindros_quedan_concentricos():
    s = api.Sesion()
    a = _ll(s, "create_cylinder", radius=10, height=20, name="A")["bodies_created"][0]["id"]
    b = _ll(s, "create_cylinder", radius=4, height=10, x=60, y=-30, name="B")["bodies_created"][0]["id"]
    _ll(s, "create_component", bodies=[a], name="CA", grounded=True)
    _ll(s, "create_component", bodies=[b], name="CB")
    _ll(s, "constrain_components", geometry1="%CYLINDER", geometry2="%CYLINDER", body1=b, body2=a)
    (x0, y0, z0), (x1, y1, z1) = g.caja_envolvente(s.cuerpo(b).forma)
    assert ((x0 + x1) / 2, (y0 + y1) / 2) == pytest.approx((0, 0), abs=1e-6)
    assert (z1 - z0) == pytest.approx(10) and g.volumen(s.cuerpo(b).forma) == pytest.approx(3.141592653589793 * 16 * 10, rel=1e-6)


def test_dos_vertices_coinciden(dos):
    s, a, b = dos
    _ll(s, "constrain_components", geometry1=[45, 25, 7], geometry2=[10, 10, 10], body1=b, body2=a)
    assert _caja(s, b) == [10, 10, 10, 20, 20, 20]


def test_si_el_componente_1_esta_fijo_se_mueve_el_2(dos):
    s, a, b = dos
    r = _ll(s, "constrain_components", geometry1=">Z", geometry2=">Z", body1=a, body2=b)      # A está fija
    assert [c["name"] for c in r["moved_components"]] == ["CB"]
    assert _caja(s, a) == [-10, -10, 0, 10, 10, 10] and _caja(s, b)[5] == 10


def test_errores_claros_y_el_documento_no_cambia(dos):
    s, a, b = dos
    _falla(s, "constrain_components", "OPERATION_FAILED", geometry1=">Z", geometry2="<Z", body1=a, body2=a)   # mismo componente
    _falla(s, "constrain_components", "INVALID_ARGUMENTS", geometry1=">Z", geometry2=">Z", type="angle", body1=b, body2=a)
    arista = _ll(s, "find_edges", body=a)["edges"][0]["id"]
    r = _falla(s, "constrain_components", "OPERATION_FAILED", geometry1=">Z", geometry2=arista, body1=b)       # cara con arista
    assert "combinación plano–eje" in r["mensaje"]


def test_deshacer_y_el_paso_queda_en_el_timeline(dos):
    s, a, b = dos
    antes = _caja(s, b)
    _ll(s, "constrain_components", geometry1=">Z", geometry2=">Z", body1=b, body2=a, name="Al ras")
    assert any(p["name"] == "Al ras" and p["status"] == "ok" for p in _ll(s, "get_timeline", include_params=False)["steps"])
    _ll(s, "undo")
    assert _caja(s, b) == antes


# ---------------------------------------------------------------- el comando de la ventana
def test_el_comando_de_la_ventana_alinea_y_se_edita(dos, tmp_path):
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication

    from omnicad.api import selectores as sl
    from omnicad.ui.comando import hit_desde_ref
    from omnicad.ui.comandos import CATALOGO
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal

    s, a, b = dos
    app = QApplication.instance() or QApplication([])
    v = VentanaPrincipal(s.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    try:
        v.resize(1280, 800)
        v.show()
        assert "restriccion_componentes" in CATALOGO
        p = v.ejecutar_comando(CATALOGO["restriccion_componentes"]())
        estado = v.doc.estado_final
        for campo, cuerpo in (("ref1", b), ("ref2", a)):
            c, cara = sl.elegir(s, ">Z", "cara", cuerpo)[0]
            p._activar(next(x for x in p.campos if x.clave == campo))
            p._elegida(hit_desde_ref(sl.referencia(c, cara), estado))
        p.set_valor("desfase", "3 mm")
        p.aceptar()
        assert v.panel is None
        assert _caja(api.Sesion(v.doc), b) == [45, 25, 3, 55, 35, 13]                    # tapa de B a 3 mm sobre la de A
        v.editar_operacion(next(o.id for o in v.doc.operaciones if o.TIPO == "restriccion"))
        assert v.panel.valores["desfase"] == "3 mm" and len(v.panel.valores["ref1"]) == 1
        v.panel.set_valor("desfase", "0 mm")
        v.panel.aceptar()
        assert _caja(api.Sesion(v.doc), b)[5] == 10
    finally:
        if v.panel is not None:
            v.panel.cancelar()
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()
