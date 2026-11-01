# -*- coding: utf-8 -*-
"""Proyectar: el caso del video (2026-10-31 20-16-59, cilindro R14 con boceto en su cara superior) y su tarjeta.

La proyección manual coincidía con el contorno automático: se descartaba por duplicada, no quedaba registro y la curva
seguía oculta, con «listo» en la barra de estado. Acá se prueba el modelo (`Boceto.agregar_proyeccion`) y el ciclo de la
ventana con clics y teclado: elegir, revisar, aceptar, cancelar, deshacer, guardar y reabrir."""
import math

import numpy as np
import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, QSettings, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QComboBox, QLabel, QPushButton, QToolButton

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo.perfiles import detectar, proyectar_forma
from omnicad.restricciones.boceto import Boceto, puntos_primitiva
from omnicad.ui import modo_boceto

CIRCULO = ("circulo", None, (0.0, 0.0), 14.0)
AUTO = {"modo": "project", "refs": [{"tipo": "cara", "cuerpo": "c"}], "auto": True}
CARA = {"modo": "project", "refs": [{"tipo": "cara", "cuerpo": "c"}]}
ARISTA = {"modo": "project", "refs": [{"tipo": "arista", "cuerpo": "c"}]}
CUADRADO = [("linea", None, (0, 0), (10, 0)), ("linea", None, (10, 0), (10, 10)),
            ("linea", None, (10, 10), (0, 10)), ("linea", None, (0, 10), (0, 0))]


def _curvas(b):
    return [c for c in b.curvas.values() if c.id > 0]


# ---------------------------------------------------------------- el modelo
def test_la_proyeccion_manual_sobre_el_contorno_automatico_lo_hace_visible_sin_duplicar():
    b = Boceto()
    cid = b.agregar_proyeccion([CIRCULO], origen=AUTO)[0]
    assert cid in b.ocultos_por_proyeccion_auto()[0]
    assert b.agregar_proyeccion([CIRCULO], origen=CARA) == [cid]
    assert len(_curvas(b)) == 1 and b.ocultos_por_proyeccion_auto() == (frozenset(), frozenset())
    manual = b.proyecciones[-1]
    assert not manual.get("auto") and manual["refs"] == CARA["refs"] and manual["ids"] == [cid]
    assert b.proyecciones[0].get("auto")                   # el registro automático sigue siendo automático


def test_lo_que_ya_estaba_proyectado_no_cambia_nada():
    b = Boceto()
    b.agregar_proyeccion([CIRCULO], origen=CARA)
    antes = b.a_dict()
    assert b.simular_proyecciones([([CIRCULO], (), False, ARISTA)])["cambia"] is False
    assert b.agregar_proyeccion([CIRCULO], origen=ARISTA) == [next(iter(b.curvas))]
    assert b.a_dict() == antes


def test_simular_no_toca_el_boceto_y_dice_lo_que_pasaria():
    b = Boceto()
    cid = b.agregar_proyeccion([CIRCULO], origen=AUTO)[0]
    antes = b.a_dict()
    r = b.simular_proyecciones([([CIRCULO, ("circulo", None, (30.0, 0.0), 5.0)], (), False, CARA)])
    assert b.a_dict() == antes
    assert r["cambia"] and r["visibles"] == [cid] and len(r["curvas"]) == 1 and r["reusadas"] == [cid]


def test_una_seleccion_que_se_superpone_queda_alineada_para_reproyectar():
    """Antes el registro no guardaba lo repetido y la proyección nacía «perdida»: reproyectar daba otra cantidad."""
    b = Boceto()
    borde = b.agregar_proyeccion(CUADRADO[:1], origen=ARISTA)[0]
    ids = b.agregar_proyeccion(CUADRADO, origen=CARA)
    assert ids[0] == borde and len(ids) == 4 and len(_curvas(b)) == 4
    corrido = [(t, x, (a[0] + 1, a[1]), (e[0] + 1, e[1])) for t, x, a, e in CUADRADO]
    assert b.reproyectar(b.proyecciones[-1], corrido, [])
    assert sorted(p.x for p in b.puntos.values() if p.id > 0) == pytest.approx([1, 1, 11, 11])


@pytest.mark.parametrize("prim", [("arco", None, (0.0, 0.0), 5.0, 0.0, 1.5),
                                  ("elipse", None, (0.0, 0.0), 8.0, 3.0, 0.4),
                                  ("arco_elipse", None, (0.0, 0.0), 8.0, 3.0, 0.4, 0.2, 2.0),
                                  ("spline", None, [(0.0, 0.0), (3.0, 4.0), (6.0, 0.0), (9.0, 4.0)],
                                   [0, 0, 0, 0, 1, 1, 1, 1], 3, None)])
def test_arcos_elipses_y_splines_tampoco_se_superponen(prim):
    b = Boceto()
    ids = b.agregar_proyeccion([prim, prim], origen=AUTO)
    assert len(ids) == len(_curvas(b)) == 1
    assert b.agregar_proyeccion([prim], origen=CARA) == ids and len(_curvas(b)) == 1
    assert b.ocultos_por_proyeccion_auto() == (frozenset(), frozenset())


def test_b110_una_cara_que_cambia_deja_una_sola_perdida_y_el_aviso_se_va_al_tratarla():
    s = api.Sesion()

    def L(nombre, **a):
        r = api.llamar(s, nombre, a)
        assert r["ok"], (nombre, a, r)
        return r["result"]

    def perdidas():
        return [p["id"] for p in L("get_sketch", sketch="Sobre")["projections"] if p["lost"]]

    L("create_sketch", name="Perfil", plane="XY")
    L("draw_arc", sketch="Perfil", start_x=40, start_y=0, mid_x=0, mid_y=40, end_x=-40, end_y=0)
    L("draw_arc", sketch="Perfil", start_x=20, start_y=0, mid_x=0, mid_y=20, end_x=-20, end_y=0)
    L("draw_line", sketch="Perfil", start_x=-40, start_y=0, end_x=-20, end_y=0)
    L("draw_line", sketch="Perfil", start_x=20, start_y=0, end_x=40, end_y=0)
    L("extrude", sketch="Perfil", profile=0, distance=10)
    L("create_sketch", name="Sobre", plane=">Z", project_edges=True)
    for _ in range(3):                                                         # repetir lo proyectado no apila nada
        assert L("project_to_sketch", faces=">Z", sketch="Sobre")["result"] == "unchanged"
    assert len(s.paso("Sobre").boceto.proyecciones) == 1 and perdidas() == []
    arco, linea = ((e["id"] for e in L("get_sketch", sketch="Perfil")["entities"] if e["type"] == t).__next__()
                   for t in ("arc", "line"))
    L("sketch_fillet", sketch="Perfil", entity1=linea, entity2=arco, radius=2)  # la cara gana una arista: perdida de verdad
    perdida = perdidas()
    assert len(perdida) == 1 and L("get_timeline")["steps"][2]["status"] == "warning"
    assert L("project_to_sketch", faces=">Z", sketch="Sobre")["result"] == "created"
    assert L("project_to_sketch", faces=">Z", sketch="Sobre")["result"] == "unchanged"
    L("recompute_all")
    assert len(s.paso("Sobre").boceto.proyecciones) == 2 and perdidas() == perdida
    L("manage_lost_projections", action="delete", sketch="Sobre")
    assert perdidas() == [] and L("get_timeline")["steps"][2]["status"] != "warning"


def test_el_arco_al_reves_es_el_mismo_arco_y_otra_elipse_no():
    b = Boceto()
    b.agregar_proyeccion([("arco", None, (0.0, 0.0), 5.0, 0.0, 1.5)])
    assert b.simular_proyecciones([([("arco", None, (0.0, 0.0), 5.0, 1.5, 0.0)], (), False, None)])["curvas"]
    b = Boceto()
    b.agregar_proyeccion([("elipse", None, (0.0, 0.0), 8.0, 3.0, 0.0)])
    assert b.simular_proyecciones([([("elipse", None, (0.0, 0.0), 8.0, 4.0, 0.0)], (), False, None)])["curvas"]


def test_un_registro_viejo_con_arcos_repetidos_no_se_pierde():
    b = Boceto()
    arco = ("arco", None, (0.0, 0.0), 5.0, 0.0, 1.5)
    primeras = b.agregar_proyeccion([arco, arco], origen=CARA, unir=False)     # lo que guardaban los proyectos anteriores
    assert len(primeras) == 2 and b.reproyectar(b.proyecciones[0], [arco, arco], [])


def test_el_vertice_del_contorno_automatico_queda_visible():
    b = Boceto()
    b.agregar_proyeccion(CUADRADO, origen=AUTO)
    pid = b.agregar_proyeccion([], [(10, 0)], origen=ARISTA)[0]
    assert pid in b.proyecciones[-1]["ids"] and pid not in b.ocultos_por_proyeccion_auto()[1]


def test_sin_vinculo_el_circulo_se_suelta_del_contorno_automatico():
    b = Boceto()
    cid = b.agregar_proyeccion([CIRCULO], origen=AUTO)[0]
    assert b.agregar_proyeccion([CIRCULO]) == [cid]
    assert b.proyecciones == [] and b.curvas[cid].proyectada         # independiente: nada lo reproyecta
    assert b.ocultos_por_proyeccion_auto() == (frozenset(), frozenset())


def test_sin_vinculo_un_lado_no_sigue_a_los_demas_ni_corre_el_registro():
    b = Boceto()
    ids = b.agregar_proyeccion(CUADRADO, origen=AUTO)
    assert b.agregar_proyeccion(CUADRADO[1:2]) == [ids[1]]
    r = b.proyecciones[0]
    assert r["ids"] == [ids[0], ids[2], ids[3]] and r["huecos"] == [1]
    otro = next(q for q in b.curvas[ids[1]].puntos())
    assert not any(otro in b.curvas[i].puntos() for i in r["ids"])       # puntos propios
    assert len(detectar(b.geometria(), geo.Plano("XY"))) == 1           # el perfil sigue cerrado por coincidencia
    corrido = [(t, x, (a[0] + 1, a[1]), (e[0] + 1, e[1])) for t, x, a, e in CUADRADO]
    assert b.reproyectar(r, corrido, [])
    assert b.coords(b.curvas[ids[1]].p1) == pytest.approx((10, 0))       # el suelto no se movió
    assert b.coords(b.curvas[ids[0]].p1) == pytest.approx((1, 0))        # los otros siguen al modelo
    copia = Boceto.desde_dict(b.a_dict())
    assert copia.proyecciones[0]["huecos"] == [1]


def test_sin_vinculo_lo_nuevo_no_comparte_puntos_con_lo_que_sigue_al_modelo():
    b = Boceto()
    b.agregar_proyeccion(CUADRADO, origen=AUTO)
    ids = b.agregar_proyeccion([("linea", None, (10, 10), (20, 20)), ("linea", None, (10, 10), (20, 0))])
    corrido = [(t, x, (a[0] + 1, a[1]), (e[0] + 1, e[1])) for t, x, a, e in CUADRADO]
    assert b.reproyectar(b.proyecciones[0], corrido, [])
    assert b.coords(b.curvas[ids[0]].p1) == pytest.approx((10, 10))
    assert b.curvas[ids[0]].p1 == b.curvas[ids[1]].p1                    # entre ellas siguen unidas


def test_romper_el_vinculo_manual_suelta_tambien_el_automatico():
    b = Boceto()
    cid = b.agregar_proyeccion([CIRCULO], origen=AUTO)[0]
    b.agregar_proyeccion([CIRCULO], origen=CARA)
    b.romper_vinculo(b.proyecciones[-1]["id"])
    assert b.proyecciones == [] and not b.curvas[cid].proyectada


def test_borrar_la_proyeccion_manual_devuelve_el_contorno_automatico():
    b = Boceto()
    cid = b.agregar_proyeccion([CIRCULO], origen=AUTO)[0]
    b.agregar_proyeccion([CIRCULO], origen=CARA)
    b.eliminar_proyeccion(b.proyecciones[-1]["id"])
    assert cid in b.curvas and cid in b.ocultos_por_proyeccion_auto()[0]


def test_la_construccion_pedida_gana_sobre_la_curva_que_se_reutiliza():
    b = Boceto()
    cid = b.agregar_proyeccion([CIRCULO], construccion=True, origen=AUTO)[0]
    assert not detectar(b.geometria(), geo.Plano("XY"))
    b.agregar_proyeccion([CIRCULO], origen=CARA)
    assert not b.curvas[cid].construccion and len(detectar(b.geometria(), geo.Plano("XY"))) == 1
    b.agregar_proyeccion([CIRCULO], construccion=True, origen=CARA)
    assert b.curvas[cid].construccion and not detectar(b.geometria(), geo.Plano("XY"))


# ---------------------------------------------------------------- la geometría, según el plano
def test_proyectar_sobre_un_plano_paralelo_desplazado_no_cambia_la_forma():
    prims, _ = proyectar_forma(geo.cilindro(14, 47), geo.Plano("XY", 100))
    circulos = [p for p in prims if p[0] == "circulo"]
    assert circulos and all(p[3] == pytest.approx(14) for p in circulos)
    assert circulos[0][2] == pytest.approx((0, 0))


def test_proyectar_sobre_un_plano_inclinado_da_la_elipse_exacta():
    angulo = math.radians(30)
    plano = geo.Plano("XY")
    plano.normal = np.array([0.0, -math.sin(angulo), math.cos(angulo)])
    plano.v = np.cross(plano.normal, plano.u)
    prims, _ = proyectar_forma(geo.cilindro(14, 47), plano)
    borde = [p for p in prims if p[0] == "spline"][0]              # B-spline racional: la proyección es exacta
    muestras = np.array(puntos_primitiva(borde, 256))
    centro = (muestras.max(axis=0) + muestras.min(axis=0)) / 2
    radios = np.linalg.norm(muestras - centro, axis=1)
    assert radios.max() == pytest.approx(14, abs=1e-3) and radios.min() == pytest.approx(14 * math.cos(angulo), abs=1e-3)


def test_proyectar_vertice_y_arista_recta():
    caja = geo.caja(10, 20, 30)
    plano = geo.Plano("XY", 5)
    prims, puntos = proyectar_forma(caja, plano)
    assert {p[0] for p in prims} == {"linea"} and not puntos
    from omnicad.nucleo import referencias as refs
    vertice = refs.subformas(caja, "vertice")[0]
    assert proyectar_forma(vertice, plano)[0] == [] and len(proyectar_forma(vertice, plano)[1]) == 1


# ---------------------------------------------------------------- MCP / CLI
@pytest.fixture
def sesion():
    s = api.Sesion()
    for nombre, args in (("create_parameter", {"name": "radio", "expression": "14 mm"}),
                         ("create_cylinder", {"radius": "radio", "height": 47, "name": "Cilindro"}),
                         ("create_sketch", {"plane": ">Z", "project_edges": True, "name": "Tapa"})):
        assert api.llamar(s, nombre, args)["ok"], nombre
    return s


def _llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def test_api_dice_que_paso_y_lo_repetido_no_deja_paso_de_deshacer(sesion):
    s = sesion
    r = _llamar(s, "project_to_sketch", sketch="Tapa", faces=">Z")
    assert r["result"] == "unchanged" and r["projection"] is None and r["entities"] == []
    pasos = len(s.doc._deshacer)
    assert _llamar(s, "project_to_sketch", sketch="Tapa", faces=">Z")["result"] == "unchanged"
    assert len(s.doc._deshacer) == pasos
    assert _llamar(s, "get_sketch", sketch="Tapa")["projections"][0]["automatic"] is False


def test_el_perfil_giratorio_repetido_tampoco_deja_paso_de_deshacer(sesion):
    s = sesion
    args = {"sketch": "Tapa", "edges": ">Z", "axis": "X"}
    primero = _llamar(s, "project_spun_profile", **args)
    assert primero["result"] == "created"
    pasos = len(s.doc._deshacer)
    r = _llamar(s, "project_spun_profile", **args)
    assert r["result"] == "unchanged" and r["projection"] is None and len(s.doc._deshacer) == pasos


def test_api_crea_y_reutiliza(sesion):
    s = sesion
    _llamar(s, "create_box", width=10, length=10, height=5, x=40, name="Caja")
    r = _llamar(s, "project_to_sketch", sketch="Tapa", bodies=["Caja"])
    assert r["result"] == "created" and len(r["entities"]) == 4


# ---------------------------------------------------------------- la ventana, con clics y teclado
@pytest.fixture(scope="module")
def ventana(tmp_path_factory):
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    app = QApplication.instance() or QApplication([])
    prefs = QSettings(str(tmp_path_factory.mktemp("proyectar") / "prefs.ini"), QSettings.IniFormat)
    v = VentanaPrincipal(prefs=Preferencias(prefs))
    v.resize(1280, 720)
    v.show()
    app.processEvents()
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app.processEvents()


@pytest.fixture
def v(ventana):
    """Cilindro R14 × 47 con un boceto recién creado sobre su cara superior, por el mismo camino que la persona."""
    s = api.Sesion()
    assert api.llamar(s, "create_parameter", {"name": "radio", "expression": "14 mm"})["ok"]
    assert api.llamar(s, "create_cylinder", {"radius": "radio", "height": 47, "name": "Cilindro"})["ok"]
    ventana.set_documento(s.doc)
    ventana.visor.encuadrar()
    QApplication.processEvents()
    ventana.crear_boceto()
    QTest.mouseClick(ventana.visor, Qt.LeftButton, Qt.NoModifier,
                     ventana.visor.proyectar(np.array([5.0, 5.0, 47.0])).toPoint())
    QApplication.processEvents()
    assert ventana.modo_boceto.activo
    yield ventana
    if ventana.modo_boceto.activo:
        ventana.modo_boceto.cancelar()


def _clic(v, punto):
    lz = v.modo_boceto.lienzo
    q = v.visor.mapToGlobal(v.visor.proyectar(np.array(punto, float)).toPoint())
    QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, lz.mapFromGlobal(q))
    QApplication.processEvents()


CARA_SUPERIOR, BORDE = (5.0, 5.0, 47.0), (14 * math.cos(1), 14 * math.sin(1), 47.0)      # el borde, lejos de su vértice


def _proyectar(v):
    v.modo_boceto.herramienta("proyectar")
    QApplication.processEvents()
    return v.modo_boceto.lienzo


def _visibles(lz):
    ocultas = lz.b.ocultos_por_proyeccion_auto()[0]
    return [c for c in _curvas(lz.b) if c.id not in ocultas]


def _tecla(lz, tecla, mod=Qt.NoModifier):
    QTest.keyClick(lz, tecla, mod)
    QApplication.processEvents()


def test_el_clic_no_confirma_y_enter_acepta_el_circulo_del_video(v):
    lz = _proyectar(v)
    tarjeta = v.modo_boceto.tarjeta
    antes, pasos = lz.b.a_dict(), len(lz.historial)
    assert tarjeta.isVisible() and not tarjeta.boton_ok.isEnabled()
    _clic(v, CARA_SUPERIOR)
    assert lz.b.a_dict() == antes and len(lz.historial) == pasos         # el clic no toca el boceto
    assert tarjeta.boton_ok.isEnabled() and "sin duplicar" in tarjeta.resultado.text()
    assert lz._previa_proy["prims"][0][3] == pytest.approx(14)            # la vista previa es el círculo real
    assert "proyeccion_elegida" in v.visor._capas or v.visor._capas      # lo elegido queda marcado en el modelo
    _tecla(lz, Qt.Key_Return)
    assert lz.herramienta == "seleccionar" and v.modo_boceto.activo       # el boceto sigue abierto
    curvas = _visibles(lz)
    assert len(curvas) == 1 == len(_curvas(lz.b)) and curvas[0].proyectada
    assert curvas[0].radio == pytest.approx(14) and lz.b.coords(curvas[0].centro) == pytest.approx((0, 0))
    assert len(lz.historial) == pasos + 1
    assert len(detectar(lz.b.geometria(), lz.plano)) == 1


def test_cancelar_y_esc_descartan_y_dejan_el_boceto_abierto(v):
    lz = _proyectar(v)
    antes, pasos = lz.b.a_dict(), len(lz.historial)
    _clic(v, CARA_SUPERIOR)
    _tecla(lz, Qt.Key_Escape)
    assert lz.herramienta == "seleccionar" and v.modo_boceto.activo
    assert lz.b.a_dict() == antes and len(lz.historial) == pasos and lz._elegidos_proy == []
    assert not v.modo_boceto.tarjeta.isVisible()
    lz = _proyectar(v)
    _clic(v, CARA_SUPERIOR)
    QTest.mouseClick(v.modo_boceto.tarjeta.boton_cancelar, Qt.LeftButton)
    assert lz.herramienta == "seleccionar" and lz.b.a_dict() == antes


def test_el_boton_aceptar_acepta_y_no_termina_el_boceto(v):
    lz = _proyectar(v)
    _clic(v, BORDE)
    assert lz._elegidos_proy[0]["tipo"] == "arista"
    QTest.mouseClick(v.modo_boceto.tarjeta.boton_ok, Qt.LeftButton)
    assert v.modo_boceto.activo and len(_visibles(lz)) == 1


def test_otro_clic_quita_y_la_x_de_la_referencia_tambien(v):
    lz = _proyectar(v)
    tarjeta = v.modo_boceto.tarjeta
    _clic(v, CARA_SUPERIOR)
    _clic(v, CARA_SUPERIOR)
    assert lz._elegidos_proy == [] and not tarjeta.boton_ok.isEnabled()
    _clic(v, CARA_SUPERIOR)
    _clic(v, BORDE)
    assert len(lz._elegidos_proy) == 2
    filas = [tarjeta._filas.itemAt(i).widget() for i in range(tarjeta._filas.count())]
    assert [f.findChild(QLabel).toolTip() for f in filas] == ["Cara plana · Cilindro", "Arista circular · Cilindro"]
    QApplication.processEvents()
    assert tarjeta.referencias.height() >= sum(f.sizeHint().height() for f in filas) > 20     # se leen, no quedan aplastadas
    fila = tarjeta.form_contexto.itemAt(1, tarjeta.form_contexto.ItemRole.FieldRole).geometry()
    assert fila.height() >= tarjeta.referencias.height()                                      # y su fila crece con ellas
    assert all(f.width() <= modo_boceto._Referencia.ANCHO_MAXIMO for f in filas)              # del ancho justo: sin franja
    QTest.mouseClick(filas[0].findChild(QToolButton), Qt.LeftButton)
    assert [e["tipo"] for e in lz._elegidos_proy] == ["arista"]


def test_cambiar_de_filtro_saca_lo_incompatible_y_lo_dice(v):
    lz = _proyectar(v)
    tarjeta = v.modo_boceto.tarjeta
    _clic(v, CARA_SUPERIOR)
    combo = next(c for c in tarjeta.contexto.findChildren(QComboBox) if c.findData("cuerpos") >= 0)
    combo.setCurrentIndex(combo.findData("cuerpos"))
    QApplication.processEvents()
    assert lz._elegidos_proy == [] and "sacó 1 referencia" in tarjeta.resultado.text()
    _clic(v, CARA_SUPERIOR)
    assert lz._elegidos_proy[0]["tipo"] == "cuerpo"
    _tecla(lz, Qt.Key_Return)
    assert len(_curvas(lz.b)) == 1 and len(_visibles(lz)) == 1            # el cilindro no duplica sus dos bordes


def test_lo_ya_proyectado_no_se_acepta_ni_deja_paso(v):
    lz = _proyectar(v)
    _clic(v, CARA_SUPERIOR)
    _tecla(lz, Qt.Key_Return)
    pasos, mensajes = len(lz.historial), []
    lz.mensaje.connect(mensajes.append)
    lz = _proyectar(v)
    _clic(v, BORDE)
    tarjeta = v.modo_boceto.tarjeta
    assert not tarjeta.boton_ok.isEnabled() and "Ya estaba proyectada" in tarjeta.resultado.text()
    _tecla(lz, Qt.Key_Return)
    assert len(lz.historial) == pasos and lz.herramienta == "proyectar" and "Ya estaba proyectada" in mensajes[-1]


def test_cambiar_a_construccion_actualiza_la_tarjeta_sin_volver_a_elegir(v):
    lz = _proyectar(v)
    _clic(v, CARA_SUPERIOR)
    _tecla(lz, Qt.Key_Return)
    lz = _proyectar(v)
    tarjeta = v.modo_boceto.tarjeta
    _clic(v, CARA_SUPERIOR)
    assert not tarjeta.boton_ok.isEnabled()
    v.modo_boceto.paleta.b_construccion.click()
    QApplication.processEvents()
    assert tarjeta.boton_ok.isEnabled()
    QTest.mouseClick(tarjeta.boton_ok, Qt.LeftButton)
    QApplication.processEvents()
    assert _visibles(lz)[0].construccion


def test_al_reeditar_un_boceto_viejo_vale_lo_que_se_ve_en_ese_paso(v):
    """Lo que un paso posterior cambió sigue siendo elegible: la vista está retrocedida al boceto."""
    op_ids = {o.id for o in v.doc.operaciones}
    assert v.modo_boceto.terminar()
    op = next(o for o in v.doc.operaciones if o.id not in op_ids)
    assert api.llamar(api.Sesion(v.doc), "remove_bodies", {"bodies": ["Cilindro"]})["ok"]
    assert not v.doc.estado_final.cuerpos
    v.editar_operacion(op.id)
    QApplication.processEvents()
    lz = _proyectar(v)
    tarjeta = v.modo_boceto.tarjeta
    _clic(v, BORDE)
    assert tarjeta.mensaje.isHidden() and tarjeta.boton_ok.isEnabled()
    _tecla(lz, Qt.Key_Return)
    assert len(_visibles(lz)) == 1 and op.boceto.proyecciones


def test_cambiar_de_herramienta_descarta_y_avisa(v):
    lz = _proyectar(v)
    mensajes = []
    lz.mensaje.connect(mensajes.append)
    antes = lz.b.a_dict()
    _clic(v, CARA_SUPERIOR)
    v.modo_boceto.herramienta("linea")
    assert lz.b.a_dict() == antes and lz._elegidos_proy == [] and "descartó" in mensajes[-1]


def test_terminar_el_boceto_no_acepta_lo_pendiente(v, monkeypatch):
    _proyectar(v)
    mensajes = []
    _clic(v, CARA_SUPERIOR)
    monkeypatch.setattr(v, "mensaje", lambda texto, *_a: mensajes.append(texto))
    op_ids = {o.id for o in v.doc.operaciones}
    assert v.modo_boceto.terminar()
    nuevo = next(o for o in v.doc.operaciones if o.id not in op_ids)
    assert "descartó" in mensajes[-1]                     # lo último que se lee en la barra de estado
    assert [bool(r.get("auto")) for r in nuevo.boceto.proyecciones] == [True]


def test_deshacer_rehacer_terminar_y_reeditar(v):
    lz = _proyectar(v)
    _clic(v, CARA_SUPERIOR)
    _tecla(lz, Qt.Key_Return)
    lz.deshacer()
    assert _visibles(lz) == [] and len(lz.b.proyecciones) == 1
    lz.rehacer()
    assert len(_visibles(lz)) == 1 and len(lz.b.proyecciones) == 2
    op_ids = {o.id for o in v.doc.operaciones}
    assert v.modo_boceto.terminar()
    op = next(o for o in v.doc.operaciones if o.id not in op_ids)
    v.editar_operacion(op.id)
    QApplication.processEvents()
    lz = v.modo_boceto.lienzo
    assert len(_visibles(lz)) == 1 == len(_curvas(lz.b)) and op.perdidas == []


def test_guardar_reabrir_y_seguir_al_modelo(v, tmp_path):
    lz = _proyectar(v)
    _clic(v, CARA_SUPERIOR)
    _tecla(lz, Qt.Key_Return)
    op_ids = {o.id for o in v.doc.operaciones}
    assert v.modo_boceto.terminar()
    op = next(o for o in v.doc.operaciones if o.id not in op_ids)
    s = api.Sesion(v.doc)
    ruta = str(tmp_path / "proyeccion.omnicad")
    assert api.llamar(s, "save_document", {"path": ruta})["ok"]
    otra = api.Sesion()
    assert api.llamar(otra, "open_document", {"path": ruta})["ok"]
    b = next(o for o in otra.doc.operaciones if o.id == op.id).boceto
    assert [bool(r.get("auto")) for r in b.proyecciones] == [True, False] and not b.ocultos_por_proyeccion_auto()[0]
    assert api.llamar(otra, "set_parameter", {"name": "radio", "expression": "20 mm"})["ok"]
    br = otra.doc.estado_final.bocetos[op.id]
    assert next(iter(c for c in br.boceto.curvas.values() if c.id > 0)).radio == pytest.approx(20)


def test_sin_vinculo_no_sigue_al_modelo(v):
    lz = _proyectar(v)
    casilla = next(c for c in v.modo_boceto.tarjeta.contexto.findChildren(modo_boceto.QCheckBox))
    casilla.setChecked(False)
    _clic(v, CARA_SUPERIOR)
    assert "sin duplicar" in v.modo_boceto.tarjeta.resultado.text()
    _tecla(lz, Qt.Key_Return)
    op_ids = {o.id for o in v.doc.operaciones}
    assert v.modo_boceto.terminar()
    op = next(o for o in v.doc.operaciones if o.id not in op_ids)
    assert op.boceto.proyecciones == []
    assert api.llamar(api.Sesion(v.doc), "set_parameter", {"name": "radio", "expression": "20 mm"})["ok"]
    assert next(c for c in v.doc.estado_final.bocetos[op.id].boceto.curvas.values() if c.id > 0).radio == pytest.approx(14)


@pytest.mark.parametrize("ancho,alto", [(1280, 720), (1024, 640), (800, 520)])
def test_tarjeta_y_paleta_no_se_tapan_y_se_ven_sus_acciones(v, ancho, alto):
    v.resize(ancho, alto)                                 # con la cinta del boceto, la ventana no baja de ~960 de ancho
    QApplication.processEvents()
    lz = _proyectar(v)
    QApplication.processEvents()
    modo, area = v.modo_boceto, v.area
    tarjeta, paleta = modo.tarjeta, modo.paleta
    visible = area.rect()
    assert tarjeta.isVisible() and paleta.isVisible()
    assert not tarjeta.geometry().intersects(paleta.geometry()), (tarjeta.geometry(), paleta.geometry(), visible)
    assert visible.contains(tarjeta.geometry()) and visible.contains(paleta.geometry())
    for boton in (tarjeta.boton_ok, tarjeta.boton_cancelar, paleta.b_terminar):
        punto = boton.mapTo(area, QPoint(boton.width() // 2, boton.height() // 2))
        assert visible.contains(punto)
    assert lz is modo.lienzo
    v.resize(1280, 720)
    QApplication.processEvents()


def test_la_tarjeta_se_mueve_y_no_se_sale_de_la_vista(v):
    _proyectar(v)
    tarjeta = v.modo_boceto.tarjeta
    cabecera = tarjeta.findChild(modo_boceto.CabeceraMovible)
    inicio = QPointF(30, 8)

    def evento(tipo, destino, boton):
        g = cabecera.mapToGlobal(inicio.toPoint()) + destino
        QApplication.sendEvent(cabecera, QMouseEvent(tipo, inicio, QPointF(g), boton, boton, Qt.NoModifier))
    x0, y0 = tarjeta.x(), tarjeta.y()
    evento(QEvent.MouseButtonPress, QPoint(0, 0), Qt.LeftButton)
    evento(QEvent.MouseMove, QPoint(-120, -20), Qt.LeftButton)
    assert (tarjeta.x(), tarjeta.y()) == (x0 - 120, y0 - 20)
    evento(QEvent.MouseMove, QPoint(-5000, 5000), Qt.LeftButton)
    QTest.mouseRelease(cabecera, Qt.LeftButton)
    assert v.area.rect().contains(tarjeta.geometry())


def test_el_aviso_flotante_no_tapa_terminar_boceto(v):
    v.aviso_flotante("Prueba")
    QApplication.processEvents()
    v.area.reubicar()
    assert not v.area.toast.geometry().intersects(v.modo_boceto.paleta.geometry())
    v.area.toast.hide()


CON_TARJETA = ["rectangulo", "circulo", "arco", "poligono_inscrito", "ranura_centro", "spline_control", "chaflan", "cota",
               "curva_fusion", "proyectar", "intersecar", "incluir_3d", "perfil_giratorio", "isoparametrica", "desfase"]


@pytest.mark.parametrize("h", CON_TARJETA)
def test_cada_herramienta_con_opciones_las_tiene_en_su_tarjeta(v, h):
    modo = v.modo_boceto
    modo.herramienta(h)
    QApplication.processEvents()
    assert modo.tarjeta.isVisible() and modo.tarjeta.form_contexto.rowCount() > 0
    assert modo_boceto.TARJETAS[h][0].upper() == modo.tarjeta.titulo.text()
    assert not modo.paleta.cuerpo.findChildren(QComboBox) or all(
        modo.paleta.panel3d.isAncestorOf(c) for c in modo.paleta.cuerpo.findChildren(QComboBox))
    assert modo.tarjeta.pie.isVisibleTo(modo.tarjeta) is (h in ("proyectar", "intersecar"))


@pytest.mark.parametrize("h", ["seleccionar", "linea", "punto", "texto"])
def test_sin_opciones_propias_no_hay_tarjeta(v, h):
    v.modo_boceto.herramienta(h)
    QApplication.processEvents()
    assert not v.modo_boceto.tarjeta.isVisible()


def test_tipo_de_la_tarjeta_cambia_la_herramienta_y_conserva_las_opciones(v):
    modo = v.modo_boceto
    modo.herramienta("poligono_inscrito")
    lados = next(c for c in modo.tarjeta.contexto.findChildren(modo_boceto.QSpinBox))
    lados.setValue(8)
    assert modo.lienzo.lados == 8
    combo = next(c for c in modo.tarjeta.contexto.findChildren(QComboBox) if c.findData("poligono_arista") >= 0)
    combo.setCurrentIndex(combo.findData("poligono_arista"))
    QApplication.processEvents()
    assert modo.lienzo.herramienta == "poligono_arista"
    assert next(c for c in modo.tarjeta.contexto.findChildren(modo_boceto.QSpinBox)).value() == 8


def test_intersecar_sigue_cortando_y_no_proyecta(v):
    lz = v.modo_boceto.lienzo
    v.modo_boceto.herramienta("intersecar")
    QApplication.processEvents()
    assert v.modo_boceto.tarjeta.titulo.text() == "INTERSECAR"
    prims = lz._tanda_proyeccion(geo.cilindro(5, 10, (40, 0, 42)), "intersecar", None)[0]
    assert [p[0] for p in prims] == ["circulo"] and prims[0][3] == pytest.approx(5)
    assert lz._tanda_proyeccion(geo.cilindro(5, 3, (40, 0, 0)), "intersecar", None)[0] == []      # no corta el plano
    assert lz._tanda_proyeccion(geo.cilindro(5, 3, (40, 0, 0)), "proyectar", None)[0]             # proyectar sí


def test_la_curva_de_otro_boceto_se_proyecta_con_clic_y_sigue_a_su_boceto(ventana):
    s = api.Sesion()
    assert api.llamar(s, "create_sketch", {"name": "Otro", "plane": "XY"})["ok"]
    circulo = api.llamar(s, "draw_circle", {"sketch": "Otro", "center_x": 40, "center_y": 0, "radius": 6})["result"]
    assert api.llamar(s, "create_sketch", {"name": "Destino", "plane": "XY"})["ok"]
    ventana.set_documento(s.doc)
    ventana.editar_operacion(s.paso("Destino").id)
    QApplication.processEvents()
    try:
        lz = _proyectar(ventana)
        _clic(ventana, (46.0, 0.0, 0.0))
        assert lz._elegidos_proy[0]["tipo"] == "curva_boceto"
        _tecla(lz, Qt.Key_Return)
        c = _visibles(lz)
        assert len(c) == 1 and c[0].radio == pytest.approx(6) and lz.b.coords(c[0].centro) == pytest.approx((40, 0))
        assert ventana.modo_boceto.terminar()
        destino = s.paso("Destino").id
        assert api.llamar(s, "set_circle_radius", {"sketch": "Otro", "curve": circulo["entities"][0]["id"], "radius": 9})["ok"]
        assert next(iter(k for k in s.doc.estado_final.bocetos[destino].boceto.curvas.values() if k.id > 0)).radio == pytest.approx(9)
    finally:
        if ventana.modo_boceto.activo:
            ventana.modo_boceto.cancelar()


def test_el_boceto_no_se_proyecta_sobre_si_mismo(ventana):
    s = api.Sesion()
    assert api.llamar(s, "create_sketch", {"name": "Solo", "plane": "XY"})["ok"]
    assert api.llamar(s, "draw_circle", {"sketch": "Solo", "center_x": 0, "center_y": 0, "radius": 6})["ok"]
    ventana.set_documento(s.doc)
    ventana.editar_operacion(s.paso("Solo").id)
    QApplication.processEvents()
    try:
        lz = _proyectar(ventana)
        _clic(ventana, (6.0, 0.0, 0.0))
        assert lz._elegidos_proy == []
    finally:
        if ventana.modo_boceto.activo:
            ventana.modo_boceto.cancelar()


def test_ningun_boton_de_la_tarjeta_toma_el_foco(v):
    _proyectar(v)
    assert all(b.focusPolicy() == Qt.NoFocus for b in v.modo_boceto.tarjeta.findChildren(QPushButton))
    assert all(c.focusPolicy() == Qt.NoFocus for c in v.modo_boceto.tarjeta.findChildren(QComboBox))
