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
    _falla(s, "constrain_components", "INVALID_ARGUMENTS", geometry1=">Z", geometry2=">Z", type="tangent", body1=b, body2=a)
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


# ---------------------------------------------------------------- ASM-17 › Ángulo
def _grados_con_z(n):
    import math
    return math.degrees(math.acos(max(-1.0, min(1.0, n[2]))))


def _cara(s, cuerpo, etiqueta):
    """La cara por su etiqueta («B/F6»), con el id vigente: los de find_faces caducan con cada cambio (el índice no cambia)."""
    return next(f for f in _ll(s, "find_faces", body=cuerpo)["faces"] if f["id"] == etiqueta)


def _arista_x_de_la_tapa(s, cuerpo):
    return next(e["id"] for e in _ll(s, "find_edges", body=cuerpo)["edges"]
                if abs(abs(e["direction"][0]) - 1) < 1e-9 and e["center"][2] == 10)


def test_angulo_entre_dos_caras_es_el_de_sus_normales_y_gira_por_el_centro_de_la_cara(dos):
    s, a, b = dos
    tapa = _ll(s, "find_faces", body=b, selector=">Z")["faces"][0]["id"]
    centro = _cara(s, b, tapa)["center"]
    for grados in (30, 90):                                              # la segunda vez parte de donde quedó la primera
        _ll(s, "constrain_components", type="angle", geometry1=_cara(s, b, tapa)["id"], geometry2=">Z", body2=a, offset=grados)
        cara = _cara(s, b, tapa)
        assert _grados_con_z(cara["normal"]) == pytest.approx(grados, abs=0.01)
        assert cara["center"] == pytest.approx(centro, abs=1e-4)           # gira por el centro de la cara: ese punto no se mueve
    assert g.volumen(s.cuerpo(b).forma) == pytest.approx(1000)


def test_angulo_con_referencia_es_con_signo(dos):
    s, a, b = dos
    tapa = _ll(s, "find_faces", body=b, selector=">Z")["faces"][0]["id"]
    ys = []
    for grados in (30, -30):
        _ll(s, "constrain_components", type="angle", geometry1=_cara(s, b, tapa)["id"], geometry2=">Z", body2=a, offset=grados,
            angle_reference=_arista_x_de_la_tapa(s, a), reference_body=a)
        n = _cara(s, b, tapa)["normal"]
        assert _grados_con_z(n) == pytest.approx(30, abs=0.01) and n[0] == pytest.approx(0, abs=1e-4)
        ys.append(n[1])
    assert ys[0] == pytest.approx(-ys[1], abs=1e-4) and abs(ys[0]) == pytest.approx(0.5, abs=1e-3)       # los dos sentidos


def test_angulo_si_el_componente_1_esta_fijo_gira_el_2(dos):
    s, a, b = dos
    tapa = _ll(s, "find_faces", body=b, selector=">Z")["faces"][0]["id"]
    r = _ll(s, "constrain_components", type="angle", geometry1=">Z", geometry2=_cara(s, b, tapa)["id"], body1=a, offset=45)   # A está fija
    assert [c["name"] for c in r["moved_components"]] == ["CB"] and _caja(s, a) == [-10, -10, 0, 10, 10, 10]
    assert _grados_con_z(_cara(s, b, tapa)["normal"]) == pytest.approx(45, abs=0.01)


def test_angulo_con_un_punto_o_con_referencia_en_alinear_es_un_error_claro(dos):
    s, a, b = dos
    r = _falla(s, "constrain_components", "OPERATION_FAILED", type="angle", geometry1=[45, 25, 7], geometry2=">Z", body2=a, offset=10)
    assert "no tiene dirección" in r["mensaje"]
    _falla(s, "constrain_components", "INVALID_ARGUMENTS", type="align", geometry1=">Z", geometry2=">Z", body1=b, body2=a,
           angle_reference=">Z")


def test_el_comando_de_la_ventana_arma_el_angulo_con_referencia_y_se_edita(dos, tmp_path):
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication

    from omnicad.api import selectores as sl
    from omnicad.ui.comando import hit_desde_ref
    from omnicad.ui.comandos import CATALOGO
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal

    s, a, b = dos
    tapa = _ll(s, "find_faces", body=b, selector=">Z")["faces"][0]["id"]
    app = QApplication.instance() or QApplication([])
    v = VentanaPrincipal(s.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    try:
        v.resize(1280, 800)
        v.show()
        p = v.ejecutar_comando(CATALOGO["restriccion_componentes"]())
        estado = v.doc.estado_final
        p.set_valor("tipo", "angulo")
        assert not p.widgets["angulo"].isHidden() and p.widgets["desfase"].isHidden()
        c, cara = sl.elegir(s, ">Z", "cara", b)[0]
        c2, cara2 = sl.elegir(s, ">Z", "cara", a)[0]
        arista = next(e for e in _ll(s, "find_edges", body=a)["edges"] if abs(abs(e["direction"][0]) - 1) < 1e-9 and e["center"][2] == 10)
        for campo, ref in (("ref1", sl.referencia(c, cara)), ("ref2", sl.referencia(c2, cara2)),
                           ("ref_angulo", sl.referencia(*sl.elegir(s, arista["id"], "arista")[0]))):
            p._activar(next(x for x in p.campos if x.clave == campo))
            p._elegida(hit_desde_ref(ref, estado))
        p.set_valor("angulo", "30 deg")
        p.aceptar()
        assert v.panel is None
        s2 = api.Sesion(v.doc)
        n = _cara(s2, b, tapa)["normal"]
        assert _grados_con_z(n) == pytest.approx(30, abs=0.01) and abs(n[1]) == pytest.approx(0.5, abs=1e-3)
        v.editar_operacion(next(o.id for o in v.doc.operaciones if o.TIPO == "restriccion"))
        assert v.panel.valores["tipo"] == "angulo" and v.panel.valores["angulo"] == "30 deg" and len(v.panel.valores["ref_angulo"]) == 1
        v.panel.set_valor("angulo", "10 deg")
        v.panel.aceptar()
        assert _grados_con_z(_cara(api.Sesion(v.doc), b, tapa)["normal"]) == pytest.approx(10, abs=0.01)
    finally:
        if v.panel is not None:
            v.panel.cancelar()
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()
