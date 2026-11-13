"""ASM-17 › Alinear (Restricción de componentes, `constrain_components`): planos coplanares con la orientación que
menos gira, ejes concéntricos, puntos coincidentes, el componente fijo no se mueve y los errores claros."""
import json

from PySide6.QtCore import Qt

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


# ---------------------------------------------------------------- Centro
def test_centro_una_cara_queda_a_medio_camino_de_las_dos_del_otro(dos):
    s, a, b = dos
    r = _ll(s, "constrain_components", type="center", geometry1="<X", body1=b, geometry2="<X", body2=a, geometry2b=">X", body2b=a)
    assert _caja(s, b) == [0, 25, 7, 10, 35, 17]                         # la cara <X de B en x=0, entre x=-10 y x=10; y, z iguales
    assert [c["name"] for c in r["moved_components"]] == ["CB"] and _caja(s, a) == [-10, -10, 0, 10, 10, 10]


def test_centro_entre_dos_caras_de_cada_lado_hace_coincidir_los_planos_medios(dos):
    s, a, b = dos
    _ll(s, "constrain_components", type="center", geometry1="<Z", geometry1b=">Z", body1=b, body1b=b,
        geometry2="<Z", geometry2b=">Z", body2=a, body2b=a)
    assert _caja(s, b) == [45, 25, 0, 55, 35, 10]                        # el plano medio de B (z=12) baja al de A (z=5)


def test_centro_si_el_componente_1_esta_fijo_se_mueve_el_2(dos):
    s, a, b = dos
    _ll(s, "constrain_components", type="center", geometry1="<X", body1=a, geometry2="<X", body2=b, geometry2b=">X", body2b=b)
    assert _caja(s, b) == [-15, 25, 7, -5, 35, 17] and _caja(s, a) == [-10, -10, 0, 10, 10, 10]


def test_centro_flip_invierte_la_orientacion(dos):
    s, a, b = dos
    args = dict(type="center", geometry1=">Z", body1=b, geometry2="<Z", geometry2b=">Z", body2=a, body2b=a)
    _ll(s, "constrain_components", **args)
    assert _caja(s, b)[2::3] == [-5, 5]                                  # sin flip no gira (menos giro): la tapa de B en z=5
    _ll(s, "undo")
    _ll(s, "constrain_components", flip=True, **args)
    assert _caja(s, b)[2::3] == [5, 15]                                  # con flip gira 180°: B queda encima del plano medio


def test_centro_errores_claros_y_el_documento_no_cambia(dos):
    s, a, b = dos
    base = dict(type="center", geometry1="<X", body1=b, geometry2="<X", body2=a)
    _falla(s, "constrain_components", "OPERATION_FAILED", **base)                                   # los dos «simple»
    _falla(s, "constrain_components", "OPERATION_FAILED", geometry2b=">Y", body2b=a, **base)       # caras no paralelas
    _falla(s, "constrain_components", "OPERATION_FAILED", geometry2b=">X", body2b=b, **base)       # la 2.ª cara es de otro componente
    _falla(s, "constrain_components", "INVALID_ARGUMENTS", **dict(base, type="align"), geometry2b=">X", body2b=a)


def test_el_comando_de_la_ventana_arma_el_centro_y_se_edita(dos, tmp_path):
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
        p = v.ejecutar_comando(CATALOGO["restriccion_componentes"]())
        estado = v.doc.estado_final
        p.set_valor("tipo", "centro")
        assert p.widgets["desfase"].isHidden() and p.widgets["angulo"].isHidden() and p.widgets["ref2b"].isHidden()
        p.set_valor("modo2", "entre_caras")
        assert not p.widgets["ref2b"].isHidden() and p.widgets["ref1b"].isHidden()
        for campo, sel, cuerpo in (("ref1", "<X", b), ("ref2", "<X", a), ("ref2b", ">X", a)):
            c, cara = sl.elegir(s, sel, "cara", cuerpo)[0]
            p._activar(next(x for x in p.campos if x.clave == campo))
            p._elegida(hit_desde_ref(sl.referencia(c, cara), estado))
        p.aceptar()
        assert v.panel is None
        assert _caja(api.Sesion(v.doc), b) == [0, 25, 7, 10, 35, 17]
        v.editar_operacion(next(o.id for o in v.doc.operaciones if o.TIPO == "restriccion"))
        assert v.panel.valores["tipo"] == "centro" and v.panel.valores["modo2"] == "entre_caras" and len(v.panel.valores["ref2b"]) == 1
        v.panel.cancelar()
    finally:
        if v.panel is not None:
            v.panel.cancelar()
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()


# ---------------------------------------------------------------- Tangente
def _cilindro_y_caja(grounded_cil):
    """Cilindro A (radio 10, alto 20, eje Z en el origen) y caja B (10×10×10 en 45..55, 25..35, 7..17)."""
    s = api.Sesion()
    a = _ll(s, "create_cylinder", radius=10, height=20, name="A")["bodies_created"][0]["id"]
    b = _ll(s, "create_box", length=10, width=10, height=10, x=50, y=30, z=7, name="B")["bodies_created"][0]["id"]
    _ll(s, "create_component", bodies=[a], name="CA", grounded=grounded_cil)
    _ll(s, "create_component", bodies=[b], name="CB", grounded=not grounded_cil)
    return s, a, b


def test_tangente_dos_caras_planas_se_apoyan_enfrentadas_y_flip_las_deja_al_ras(dos):
    s, a, b = dos
    args = dict(type="tangent", geometry1="<X", body1=b, geometry2=">X", body2=a)
    _ll(s, "constrain_components", **args)
    assert _caja(s, b) == [10, 25, 7, 20, 35, 17]                        # la cara <X de B toca la >X de A, sin correrse en y ni z
    _ll(s, "undo")
    _ll(s, "constrain_components", flip=True, **args)
    assert _caja(s, b)[0::3] == [0, 10]                                  # al ras: B se da vuelta y queda del lado de A


@pytest.mark.parametrize("grounded_cil", [True, False])
def test_tangente_plano_y_cilindro_el_plano_roza_del_lado_en_que_esta(grounded_cil):
    s, a, b = _cilindro_y_caja(grounded_cil)
    _ll(s, "constrain_components", type="tangent", geometry1="<X", body1=b, geometry2="%CYLINDER", body2=a)
    (x0, y0, z0), (x1, y1, z1) = g.caja_envolvente(s.cuerpo(b).forma)
    (a0, _, _), (a1, _, _) = g.caja_envolvente(s.cuerpo(a).forma)
    assert (x0 - (a0 + a1) / 2) == pytest.approx(10, abs=1e-6)           # la cara <X de la caja a un radio del eje del cilindro
    assert (y1 - y0, z1 - z0) == pytest.approx((10, 10), abs=1e-6)


def test_tangente_plano_y_cilindro_flip_pasa_al_otro_lado():
    s, a, b = _cilindro_y_caja(True)
    _ll(s, "constrain_components", type="tangent", geometry1="<X", body1=b, geometry2="%CYLINDER", body2=a, flip=True)
    assert _caja(s, b)[0] == pytest.approx(-10)                          # la cara de B en x=-10 con el cilindro del otro lado


def test_tangente_dos_cilindros_se_tocan_por_fuera_y_flip_por_dentro():
    s = api.Sesion()
    a = _ll(s, "create_cylinder", radius=10, height=20, name="A")["bodies_created"][0]["id"]
    b = _ll(s, "create_cylinder", radius=4, height=10, x=60, y=-30, name="B")["bodies_created"][0]["id"]
    _ll(s, "create_component", bodies=[a], name="CA", grounded=True)
    _ll(s, "create_component", bodies=[b], name="CB")
    args = dict(type="tangent", geometry1="%CYLINDER", geometry2="%CYLINDER", body1=b, body2=a)

    def centro_b():
        (x0, y0, _), (x1, y1, _) = g.caja_envolvente(s.cuerpo(b).forma)
        return ((x0 + x1) / 2, (y0 + y1) / 2)

    u = (2 / 5 ** 0.5, -1 / 5 ** 0.5)
    _ll(s, "constrain_components", **args)
    assert centro_b() == pytest.approx((14 * u[0], 14 * u[1]), abs=1e-6)  # distancia entre ejes = 10 + 4, en la misma dirección
    _ll(s, "undo")
    _ll(s, "constrain_components", flip=True, **args)
    assert centro_b() == pytest.approx((6 * u[0], 6 * u[1]), abs=1e-6)   # por dentro: 10 − 4


def test_tangente_errores_claros_y_el_documento_no_cambia():
    s, a, b = _cilindro_y_caja(True)
    _falla(s, "constrain_components", "OPERATION_FAILED", type="tangent", geometry1=">Z", body1=b, geometry2="%CYLINDER", body2=a)  # plano ⟂ eje


def test_el_comando_de_la_ventana_arma_la_tangente_y_se_edita(dos, tmp_path):
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
        p = v.ejecutar_comando(CATALOGO["restriccion_componentes"]())
        estado = v.doc.estado_final
        p.set_valor("tipo", "tangente")
        assert p.widgets["desfase"].isHidden() and p.widgets["angulo"].isHidden() and p.widgets["ref1b"].isHidden()
        for campo, sel, cuerpo in (("ref1", "<X", b), ("ref2", ">X", a)):
            c, cara = sl.elegir(s, sel, "cara", cuerpo)[0]
            p._activar(next(x for x in p.campos if x.clave == campo))
            p._elegida(hit_desde_ref(sl.referencia(c, cara), estado))
        p.aceptar()
        assert v.panel is None
        assert _caja(api.Sesion(v.doc), b) == [10, 25, 7, 20, 35, 17]
        v.editar_operacion(next(o.id for o in v.doc.operaciones if o.TIPO == "restriccion"))
        assert v.panel.valores["tipo"] == "tangente" and len(v.panel.valores["ref2"]) == 1
        v.panel.cancelar()
    finally:
        if v.panel is not None:
            v.panel.cancelar()
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()


def test_tangente_y_centro_rechazan_un_desfase_que_no_usan(dos):
    s, a, b = dos
    _falla(s, "constrain_components", "OPERATION_FAILED", type="tangent", geometry1="<X", body1=b, geometry2=">X", body2=a, offset=3)


# ---------------------------------------------------------------- Tangente: esferas, aristas, vértices, conos y «Todas las caras»
def _centro_caja(s, cid):
    (x0, y0, z0), (x1, y1, z1) = g.caja_envolvente(s.cuerpo(cid).forma)
    return ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)


def test_tangente_esfera_con_plano_cilindro_y_esfera():
    s = api.Sesion()
    a = _ll(s, "create_box", length=20, width=20, height=10, name="A")["bodies_created"][0]["id"]
    b = _ll(s, "create_sphere", radius=4, x=50, y=30, z=30, name="B")["bodies_created"][0]["id"]
    _ll(s, "create_component", bodies=[a], name="CA", grounded=True)
    _ll(s, "create_component", bodies=[b], name="CB")
    _ll(s, "constrain_components", type="tangent", geometry1="%SPHERE", body1=b, geometry2=">Z", body2=a)
    assert _centro_caja(s, b)[2] == pytest.approx(14)                    # el centro a un radio (4) sobre la tapa z=10; x e y no se tocan
    assert _centro_caja(s, b)[:2] == pytest.approx((50, 30))
    c = _ll(s, "create_sphere", radius=6, x=-40, y=0, z=5, name="C")["bodies_created"][0]["id"]
    _ll(s, "create_component", bodies=[c], name="CC")
    _ll(s, "constrain_components", type="tangent", geometry1="%SPHERE", body1=c, geometry2="%SPHERE", body2=b)
    d = ((_centro_caja(s, c)[0] - _centro_caja(s, b)[0]) ** 2 + (_centro_caja(s, c)[1] - _centro_caja(s, b)[1]) ** 2
         + (_centro_caja(s, c)[2] - _centro_caja(s, b)[2]) ** 2) ** 0.5
    assert d == pytest.approx(10)                                        # 4 + 6 entre centros


def test_tangente_vertice_sobre_un_plano_y_arista_recta_sobre_un_cilindro():
    s, a, b = _cilindro_y_caja(True)
    _ll(s, "constrain_components", type="tangent", geometry1=[45, 25, 7], geometry2="%CYLINDER", body2=a)
    k = 10 / (45 ** 2 + 25 ** 2) ** 0.5
    assert _caja(s, b)[0:3] == pytest.approx([45 * k, 25 * k, 7], abs=1e-4)   # el vértice (45,25,7) a un radio del eje, en línea con él; z no se toca
    s, a, b = _cilindro_y_caja(True)
    arista = next(e["id"] for e in _ll(s, "find_edges", body=b)["edges"] if abs(abs(e["direction"][2]) - 1) < 1e-9 and e["center"][0] < 50 and e["center"][1] < 30)
    _ll(s, "constrain_components", type="tangent", geometry1=arista, body1=b, geometry2="%CYLINDER", body2=a)
    assert _caja(s, b)[0:3] == pytest.approx([45 * k, 25 * k, 7], abs=1e-4)   # la arista vertical (45,25) roza el cilindro, igual que el vértice


def test_tangente_cono_con_un_plano_sin_la_inclinacion_da_error_claro_y_con_ella_apoya_en_el_vertice():
    s = api.Sesion()
    _ll(s, "create_sketch", plane="XY", name="S1")
    _ll(s, "draw_circle", radius=10)
    a = _ll(s, "extrude", sketch="S1", distance=20, taper_angle=-10)["bodies_created"][0]["id"]
    _ll(s, "create_component", bodies=[a], name="CA", grounded=True)
    plano = _ll(s, "create_box", length=10, width=10, height=10, x=50, y=0, z=7, name="P")["bodies_created"][0]["id"]
    _ll(s, "create_component", bodies=[plano], name="CP")
    _falla(s, "constrain_components", "OPERATION_FAILED", type="tangent", geometry1="<X", body1=plano, geometry2="%CONE", body2=a)  # plano vertical
    _ll(s, "create_sketch", plane="XY", name="S2", body=None)
    _ll(s, "draw_rectangle", x1=60, y1=-10, x2=80, y2=10)
    t = _ll(s, "extrude", sketch="S2", distance=20, taper_angle=-10)["bodies_created"][0]["id"]
    _ll(s, "create_component", bodies=[t], name="CT")
    _ll(s, "constrain_components", type="tangent", geometry1="<X", body1=t, geometry2="%CONE", body2=a)
    import numpy as np

    from omnicad.api import selectores as sl
    from omnicad.nucleo import consultas
    v = consultas.cono_de(sl.elegir(s, "%CONE", "cara", a)[0][1].sub)[0]
    cara = _ll(s, "find_faces", body=t, selector="<X")["faces"][0]
    assert abs(float((v - np.array(cara["center"])) @ np.array(cara["normal"]))) == pytest.approx(0, abs=0.01)   # el vértice quedó en el plano (find_faces redondea normal y centro)


def test_tangente_todas_las_caras_apagado_pide_que_las_caras_se_toquen(dos):
    s, a, b = dos
    args = dict(type="tangent", geometry1="<X", body1=b, geometry2=">X", body2=a)
    _falla(s, "constrain_components", "OPERATION_FAILED", all_faces=False, **args)   # B queda en x=10..20 pero y=25..35 no llega a A (|y|<=10)
    _ll(s, "constrain_components", all_faces=True, **args)
    assert _caja(s, b) == [10, 25, 7, 20, 35, 17]
    s2 = api.Sesion()
    a2 = _ll(s2, "create_box", length=20, width=20, height=10, name="A")["bodies_created"][0]["id"]
    b2 = _ll(s2, "create_box", length=10, width=10, height=10, x=50, y=0, z=7, name="B")["bodies_created"][0]["id"]
    _ll(s2, "create_component", bodies=[a2], name="CA", grounded=True)
    _ll(s2, "create_component", bodies=[b2], name="CB")
    _ll(s2, "constrain_components", all_faces=False, type="tangent", geometry1="<X", body1=b2, geometry2=">X", body2=a2)   # ahora se solapan en y
    assert _caja(s2, b2)[0] == 10
    _falla(s, "constrain_components", "INVALID_ARGUMENTS", all_faces=False, type="align", geometry1=">Z", geometry2=">Z", body1=b, body2=a)


def test_tangente_toro_y_circulo_con_un_plano():
    s = api.Sesion()
    a = _ll(s, "create_box", length=20, width=20, height=10, name="A")["bodies_created"][0]["id"]
    t = _ll(s, "create_torus", major_radius=10, minor_radius=3, x=50, y=30, z=40, name="T")["bodies_created"][0]["id"]
    c = _ll(s, "create_cylinder", radius=4, height=10, x=-50, y=-30, z=30, name="C")["bodies_created"][0]["id"]
    _ll(s, "create_component", bodies=[a], name="CA", grounded=True)
    _ll(s, "create_component", bodies=[t], name="CT")
    _ll(s, "create_component", bodies=[c], name="CC")
    _ll(s, "constrain_components", type="tangent", geometry1="%TORUS", body1=t, geometry2=">Z", body2=a)
    assert _caja(s, t)[2] == pytest.approx(10)                           # el toro apoyado sobre la tapa (eje ⟂ plano): su parte baja en z=10
    _ll(s, "constrain_components", type="tangent", geometry1="%TORUS", body1=t, geometry2=">X", body2=a)
    assert _caja(s, t)[0] == pytest.approx(10)                           # y de canto (eje ∥ plano): el aro roza a R + r = 13 del centro; 23 − 13 = 10
    arista = next(e["id"] for e in _ll(s, "find_edges", body=c)["edges"] if e["center"][2] == 40 and "direction" not in e)   # el círculo de arriba (las rectas traen dirección)
    _ll(s, "constrain_components", type="tangent", geometry1=arista, body1=c, geometry2=">Z", body2=a)
    assert _caja(s, c)[5] == pytest.approx(10)                           # la arista circular de arriba (eje ⟂ plano) queda en el plano de la tapa
    _falla(s, "constrain_components", "OPERATION_FAILED", type="tangent", geometry1="%TORUS", body1=t, geometry2="%CYLINDER", body2=c)


# ---------------------------------------------------------------- tabla de filas (conjunto de restricciones)
def test_un_conjunto_de_filas_se_cumple_a_la_vez(dos):
    s, a, b = dos
    r = _ll(s, "constrain_components", geometry1=">Z", geometry2=">Z", body1=b, body2=a,
            rows=[{"geometry1": "<X", "geometry2": ">X", "body1": b, "body2": a, "offset": 2}])
    assert _caja(s, b) == [12, 25, 0, 22, 35, 10]                        # tapa al ras en z y apoyada a 2 mm de la cara +X de A; y no se toca
    assert len([o for o in s.doc.operaciones if o.TIPO == "restriccion"]) == 1 and [c["name"] for c in r["moved_components"]] == ["CB"]
    _ll(s, "undo")
    assert _caja(s, b) == [45, 25, 7, 55, 35, 17]                        # un solo paso de deshacer para todo el conjunto


def test_un_conjunto_con_el_componente_1_fijo_mueve_el_2(dos):
    s, a, b = dos
    _ll(s, "constrain_components", geometry1=">Z", geometry2=">Z", body1=a, body2=b,
        rows=[{"geometry1": ">X", "geometry2": "<X", "body1": a, "body2": b, "offset": 2}])
    assert _caja(s, b) == [12, 25, 0, 22, 35, 10] and _caja(s, a) == [-10, -10, 0, 10, 10, 10]


def test_filas_que_se_contradicen_dan_error_claro_y_el_documento_no_cambia(dos):
    s, a, b = dos
    r = _falla(s, "constrain_components", "OPERATION_FAILED", geometry1=">Z", geometry2=">Z", body1=b, body2=a,
               rows=[{"geometry1": ">Z", "geometry2": ">Z", "body1": b, "body2": a, "offset": 5}])
    assert "se contradicen" in r["mensaje"] and "filas 1, 2" in r["mensaje"]
    r = _falla(s, "constrain_components", "OPERATION_FAILED", geometry1=">Z", geometry2=">Z", body1=b, body2=a,
               rows=[{"geometry1": ">X", "geometry2": "<X", "body1": a, "body2": b}])               # del 2 al 1: otro orden
    assert "mismo componente 1" in r["mensaje"]


def test_cada_fila_lleva_su_nombre_y_su_desfase_y_un_parametro_de_una_fila_extra_recalcula_el_paso(dos):
    s, a, b = dos
    _ll(s, "create_parameter", name="hueco", expression="2 mm")
    _ll(s, "constrain_components", geometry1=">Z", geometry2=">Z", body1=b, body2=a, row_name="tapa",
        rows=[{"geometry1": "<X", "geometry2": ">X", "body1": b, "body2": a, "offset": "hueco", "name": "lado"}])
    op = next(o for o in s.doc.operaciones if o.TIPO == "restriccion")
    assert op.p["nombre_fila"] == "tapa" and op.p["filas"][0]["nombre_fila"] == "lado"
    assert "hueco" in op.expresiones() and s.doc.parametros_usados()["hueco"] == {op.nombre}
    assert _caja(s, b)[0] == 12                                           # a 2 mm de la cara +X de A (que llega a x = 10)
    _ll(s, "set_parameter", name="hueco", expression="5 mm")              # el parámetro solo lo cita el desfase de la fila extra
    assert _caja(s, b)[0] == 15
    _ll(s, "set_parameter", name="hueco", new_name="aire")                # renombrar lo actualiza dentro de la fila
    assert next(o for o in s.doc.operaciones if o.TIPO == "restriccion").p["filas"][0]["desfase"] == "aire"
    r = _falla(s, "constrain_components", "OPERATION_FAILED", geometry1=">Z", geometry2=">Z", body1=b, body2=a, row_name="tapa",
               rows=[{"geometry1": ">Z", "geometry2": ">Z", "body1": b, "body2": a, "offset": 5, "name": "alto"}])
    assert "1 «tapa», 2 «alto»" in r["mensaje"]                           # el error nombra las filas


def test_limites_de_desfase_recortan_avisan_y_con_apoyo_fallan(dos):
    s, a, b = dos
    _ll(s, "create_parameter", name="tope", expression="5 mm")
    args = dict(geometry1="<X", geometry2=">X", body1=b, body2=a)
    r = api.llamar(s, "constrain_components", dict(offset=8, offset_max="tope", **args))   # a x = 10 llega la cara de A: 8 mm pasa del tope de 5
    assert r["ok"] and _caja(s, b)[0] == 15 and any("fuera de los límites" in w for w in r["avisos"]), r
    _ll(s, "set_parameter", name="tope", expression="6 mm")                         # el tope es una expresión: recalcula
    assert _caja(s, b)[0] == 16
    _ll(s, "undo")                                                                  # el parámetro
    _ll(s, "undo")                                                                  # y la restricción
    _ll(s, "constrain_components", offset=1, offset_min=3, **args)                  # por debajo del mínimo sube a 3
    assert _caja(s, b)[0] == 13
    _ll(s, "undo")
    _ll(s, "constrain_components", offset=4, offset_min=3, offset_max=6, offset_as_rest=True, **args)   # dentro: sin cambios
    assert _caja(s, b)[0] == 14
    _ll(s, "undo")
    r = _falla(s, "constrain_components", "OPERATION_FAILED", offset=8, offset_max=5, offset_as_rest=True, **args)
    assert "apoyo" in r["mensaje"]
    r = _falla(s, "constrain_components", "OPERATION_FAILED", offset=4, offset_min=6, offset_max=5, **args)
    assert "mayor que el máximo" in r["mensaje"]
    _falla(s, "constrain_components", "OPERATION_FAILED", type="angle", offset=30, offset_max=45, **args)      # el ángulo pide referencia
    _falla(s, "constrain_components", "INVALID_ARGUMENTS", type="tangent", offset_max=5, **args)
    _falla(s, "constrain_components", "INVALID_ARGUMENTS", offset_as_rest=True, **args)                         # sin límites
    r = api.llamar(s, "constrain_components", dict(offset=0, geometry1=">Z", geometry2=">Z", body1=b, body2=a,
                                                   rows=[dict(args, offset=9, offset_max=5)]))                               # los límites también valen en cada fila extra
    assert _caja(s, b)[0] == 15
    assert len([w for w in r["avisos"] if "fuera de los límites" in w]) == 1       # el aviso no se repite por cada pasada del conjunto


def test_las_filas_validan_sus_claves(dos):
    s, a, b = dos
    _falla(s, "constrain_components", "INVALID_ARGUMENTS", geometry1=">Z", geometry2=">Z", body1=b, body2=a, rows=[{"geometry1": ">Z"}])
    _falla(s, "constrain_components", "INVALID_ARGUMENTS", geometry1=">Z", geometry2=">Z", body1=b, body2=a,
           rows=[{"geometry1": ">Z", "geometry2": ">Z", "foo": 1}])


def test_el_comando_de_la_ventana_arma_el_conjunto_con_la_tabla_de_filas_y_se_edita(dos, tmp_path):
    from PySide6.QtCore import QSettings
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QPushButton

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
        p = v.ejecutar_comando(CATALOGO["restriccion_componentes"]())
        estado = v.doc.estado_final

        def elegir(campo, sel, cuerpo):
            c, cara = sl.elegir(s, sel, "cara", cuerpo)[0]
            p._activar(next(x for x in p.campos if x.clave == campo))
            p._elegida(hit_desde_ref(sl.referencia(c, cara), estado))

        boton = lambda texto: next(x for x in p.findChildren(QPushButton) if x.text().startswith(texto))  # noqa: E731
        QTest.mouseClick(boton("+ Agregar"), Qt.LeftButton)                  # sin geometría: avisa y no agrega
        assert not p.valores["filas"]
        elegir("ref1", ">Z", b)
        elegir("ref2", ">Z", a)
        QTest.mouseClick(boton("+ Agregar"), Qt.LeftButton)
        assert len(p.valores["filas"]) == 1 and not p.valores["ref1"] and p._lista_filas.item(0).text() == "1. Alinear · cara–cara"
        p._lista_filas.setCurrentRow(0)                                      # editar la fila guardada: su nombre y su desfase
        p._edit_nombre.setText("tapa")
        p._edit_nombre.editingFinished.emit()
        p._edit_desfase.setText("1 mm")
        p._edit_desfase.editingFinished.emit()
        assert p.valores["filas"][0]["nombre_fila"] == "tapa" and p.valores["filas"][0]["desfase"] == "1 mm"
        assert p._lista_filas.item(0).text() == "1. tapa · cara–cara"
        elegir("ref1", "<X", b)
        elegir("ref2", ">X", a)
        p.set_valor("desfase", "2 mm")
        p.aceptar()
        assert v.panel is None
        assert _caja(api.Sesion(v.doc), b) == [12, 25, 1, 22, 35, 11]   # la primera fila quedó a 1 mm de la tapa
        op = next(o for o in v.doc.operaciones if o.TIPO == "restriccion")
        assert len(op.p["filas"]) == 1 and len([o for o in v.doc.operaciones if o.TIPO == "restriccion"]) == 1
        v.editar_operacion(op.id)
        p = v.panel
        assert len(p.valores["filas"]) == 1 and p.valores["desfase"] == "1 mm" and p._lista_filas.count() == 1
        p._lista_filas.setCurrentRow(0)
        QTest.mouseClick(boton("✕ Quitar"), Qt.LeftButton)
        assert not p.valores["filas"] and p._lista_filas.count() == 0
        p.cancelar()
    finally:
        if v.panel is not None:
            v.panel.cancelar()
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()


# ---------------------------------------------------------------- conflictos con las uniones
def test_una_restriccion_que_mueve_un_componente_unido_avisa_con_el_nombre_de_la_union(dos):
    s, a, b = dos
    r = api.llamar(s, "constrain_components", dict(geometry1=">Z", geometry2=">Z", body1=b, body2=a))
    assert r["ok"] and not any("unido" in w for w in r["avisos"])               # sin unión no hay nada que avisar
    _ll(s, "undo")
    union = _ll(s, "create_joint", origin1="<Z", body1=b, origin2=">Z", body2=a)["feature"]["name"]
    r = api.llamar(s, "constrain_components", dict(geometry1="<X", geometry2=">X", body1=b, body2=a, offset=30))
    texto = " ".join(r["avisos"])
    assert r["ok"] and f"«{union}»" in texto and "«CB»" in texto and "«CA»" in texto and "dejar de cumplirse" in texto, r


def test_la_vista_previa_al_pasar_el_cursor_muestra_el_componente_2_sin_elegirlo(dos, tmp_path):
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
        p = v.ejecutar_comando(CATALOGO["restriccion_componentes"]())
        estado = v.doc.estado_final
        hit = lambda sel, cuerpo: hit_desde_ref(sl.referencia(*(lambda c, cara: (c, cara))(*sl.elegir(s, sel, "cara", cuerpo)[0])), estado)  # noqa: E731
        p._activar(next(x for x in p.campos if x.clave == "ref2"))
        p._sobre(hit(">Z", a))                                                   # sin el componente 1 definido no hay previa
        assert not p._sobre_activo
        p._activar(next(x for x in p.campos if x.clave == "ref1"))
        p._elegida(hit(">Z", b))
        p._activar(next(x for x in p.campos if x.clave == "ref2"))
        p._sobre(hit(">Z", a))                                                   # el cursor sobre la tapa de A: la previa la usa…
        assert p._sobre_activo and p._previa_ok and p.ultima_op is not None and not p.valores["ref2"]   # …sin elegirla
        p._sobre(hit(">Z", b))                                                   # geometría del mismo componente: no sirve, no se muestra
        assert not p._sobre_activo and p.ultima_op is None
        p._sobre(hit(">Z", a))
        p._sobre(None)                                                           # el cursor se va: vuelve a lo elegido
        assert not p._sobre_activo and p.ultima_op is None
        p.cancelar()
    finally:
        if v.panel is not None:
            v.panel.cancelar()
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()
