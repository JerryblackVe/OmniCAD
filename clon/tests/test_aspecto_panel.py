# -*- coding: utf-8 -*-
"""Panel ASPECTO (MODIFICAR › Aspecto): lo que se elige se ve en el modelo al instante, Cancelar lo descarta y Aceptar lo
escribe en UN paso de deshacer; cuerpos y caras; «En este diseño» con su menú; selector rápido y Editor de materiales."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad import api
from omnicad.api import selectores as sl
from omnicad.nucleo import aspectos as asp
from omnicad.timeline import aspectos_doc as ad

from PySide6.QtCore import QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication


@pytest.fixture(autouse=True)
def usuario(tmp_path, monkeypatch):
    monkeypatch.setenv("OMNICAD_ASPECTOS", str(tmp_path / "aspectos.json"))


@pytest.fixture(scope="module")
def app_qt():
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def ventana(app_qt, tmp_path_factory):
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    ruta = tmp_path_factory.mktemp("aspecto") / "preferencias.ini"
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(ruta), QSettings.IniFormat)))
    v.resize(1500, 900)
    v.show()
    QTest.qWait(1)
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    QTest.qWait(1)


@pytest.fixture
def v(ventana):
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 100, "width": 60, "height": 20})["ok"]
    assert api.llamar(s, "create_cylinder", {"height": 30, "radius": 10, "x": 90})["ok"]
    ventana.set_documento(s.doc)
    s.doc.modificado = False
    QTest.qWait(20)
    ventana.sesion_aspecto = s
    yield ventana
    if ventana.panel is not None:
        ventana.panel.cancelar()
    ventana._previa_aspecto = {}
    ventana.doc.modificado = False


def _abrir(v):
    from omnicad.ui.comandos import CATALOGO
    v.ejecutar_comando(CATALOGO["aspecto"]())
    assert v.panel is not None and v.panel.comando.CLAVE == "aspecto"
    return v.panel, v.panel.widgets["aspecto"]


def _hit_cuerpo(v, cid):
    from omnicad.ui.comando import hit_desde_ref
    return hit_desde_ref({"tipo": "cuerpo", "cuerpo": cid}, v.doc.estado_final)


def _hit_cara(v, selector, cuerpo):
    from omnicad.ui.comando import hit_desde_ref
    (c, e), = sl.elegir(v.sesion_aspecto, selector, "cara", cuerpo)
    return hit_desde_ref(sl.referencia(c, e), v.doc.estado_final)


def _color_en_el_visor(v, cid):
    return v._apariencias(v.doc.estado_final).get(cid)


def _previsualizar(p):
    p._t_previa.stop()
    p._calcular_previa()


# ---------------------------------------------------------------- el panel
def test_el_panel_trae_biblioteca_pestanas_buscador_y_en_este_diseno(v):
    p, w = _abrir(v)
    assert {"aplicar_a", "cuerpos", "caras", "aspecto"} <= set(p.widgets)
    familias = [w.arbol.topLevelItem(i).text(0) for i in range(w.arbol.topLevelItemCount())]
    assert familias[:3] == ["Acondicionamiento del terreno", "Cristal", "Espejo"] and "Hormigón" in familias
    assert w.pestanas.count() == 3 and [w.pestanas.tabText(i) for i in (1, 2)] == ["Mis aspectos", "Favoritos"]
    w.buscador.setText("granito")                                     # el buscador filtra por nombre y por familia
    nombres = [w.arbol.topLevelItem(i).child(j).text(0) for i in range(w.arbol.topLevelItemCount())
               for j in range(w.arbol.topLevelItem(i).childCount())]
    assert nombres == ["Granito - Gris"]
    w.buscador.setText("")
    w.pestanas.setCurrentIndex(1)
    assert w.arbol.topLevelItemCount() == 0                           # Mis aspectos: todavía nada
    w.favorito(asp.BIBLIOTECA["Cromo - Pulido"], True)
    w.pestanas.setCurrentIndex(2)
    assert w.arbol.topLevelItem(0).child(0).text(0) == "Cromo - Pulido"
    assert w.lista.count() == 0                                       # un diseño sin aspectos: la lista está vacía
    assert not p.grab().isNull() and not w.arbol.topLevelItem(0).child(0).icon(0).isNull()


def test_lo_elegido_se_ve_al_instante_y_cancelar_lo_descarta(v):
    p, w = _abrir(v)
    p.valores["cuerpos"] = [_hit_cuerpo(v, "op1.c1")]
    antes = _color_en_el_visor(v, "op1.c1")
    w.elegir(asp.buscar("Hormigón - Liso"), desde_biblioteca=True)
    _previsualizar(p)
    assert _color_en_el_visor(v, "op1.c1") == pytest.approx(asp.BIBLIOTECA["Hormigón - Liso"]["color"])
    assert "apariencia" not in v.doc.propiedades.get("op1.c1", {}) and not v.doc.modificado   # el documento no se tocó
    w.elegir(asp.buscar("Granito - Gris"), desde_biblioteca=True)                           # otro: cambia sin Aceptar
    _previsualizar(p)
    assert _color_en_el_visor(v, "op1.c1") == pytest.approx(asp.BIBLIOTECA["Granito - Gris"]["color"])
    p.cancelar()
    assert _color_en_el_visor(v, "op1.c1") == antes and v._previa_aspecto == {}
    assert ad.lista(v.doc) == [] and not v.doc.modificado and v.panel is None


def test_aceptar_aplica_a_los_cuerpos_en_un_solo_paso_de_deshacer(v):
    p, w = _abrir(v)
    p.valores["cuerpos"] = [_hit_cuerpo(v, "op1.c1"), _hit_cuerpo(v, "op2.c1")]
    w.elegir(asp.buscar("Mármol - Blanco"), desde_biblioteca=True)
    p.aceptar()
    assert v.panel is None and v._previa_aspecto == {}
    cuerpos, caras = ad.usos(v.doc, "asp1")
    assert sorted(cuerpos) == ["op1.c1", "op2.c1"] and ad.buscar(v.doc, "asp1")["nombre"] == "Mármol - Blanco"
    assert _color_en_el_visor(v, "op2.c1") == pytest.approx(asp.BIBLIOTECA["Mármol - Blanco"]["color"])
    v.doc.deshacer()                                                   # todo lo que hizo Aceptar, de una
    assert ad.lista(v.doc) == [] and "apariencia" not in v.doc.propiedades.get("op1.c1", {})


def test_aplicar_a_caras_pinta_solo_la_cara_en_vivo_y_al_aceptar(v):
    p, w = _abrir(v)
    p.widgets["aplicar_a"].set_valor("caras")
    p.valores["caras"] = [_hit_cara(v, ">Z", "op1.c1")]
    assert v.panel.valores["aplicar_a"] == "caras"
    w.elegir(asp.buscar("Pintura - Brillante (Rojo)"), desde_biblioteca=True)
    _previsualizar(p)
    rojo = tuple(asp.BIBLIOTECA["Pintura - Brillante (Rojo)"]["color"])
    assert [(c, color) for c, _v, _n, color in v.visor.caras_pintadas] == [("op1.c1", pytest.approx(rojo))]
    assert len(v.visor.caras_pintadas[0][1]) > 0 and _color_en_el_visor(v, "op1.c1") is None        # el cuerpo no cambió
    p.aceptar()
    caras = v.doc.propiedades["op1.c1"]["caras"]
    assert len(caras) == 1 and "apariencia" not in {k for k in v.doc.propiedades["op1.c1"] if k != "caras"}
    assert len(v.visor.caras_pintadas) == 1                              # la cara sigue pintada ya sin el panel
    v.doc.deshacer()
    assert v.visor.caras_pintadas == []


def test_caras_elegidas_antes_de_abrir_abren_en_caras_y_se_pintan(v):
    """B-198: con caras preseleccionadas, Aspecto abría en «Cuerpos» y escondía las caras (Aceptar pedía cuerpos)."""
    v._seleccionar([_hit_cara(v, ">Z", "op1.c1")])
    p, w = _abrir(v)
    assert p.valores["aplicar_a"] == "caras" and p.widgets["aplicar_a"].r_caras.isChecked()
    assert p._a_la_vista(p._por_clave["caras"]) and not p._a_la_vista(p._por_clave["cuerpos"])
    w.elegir(asp.buscar("Pintura - Brillante (Rojo)"), desde_biblioteca=True)
    p.aceptar()
    assert v.panel is None and len(v.doc.propiedades["op1.c1"]["caras"]) == 1


def _ventana_en_el_visor(visor, desde, hasta):
    """Arrastre con el botón izquierdo como una persona: apretar, varios movimientos, soltar (eventos al widget)."""
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent

    def ev(tipo, p, boton, botones):
        p = QPointF(*p)
        QApplication.sendEvent(visor, QMouseEvent(tipo, p, visor.mapToGlobal(p), boton, botones, Qt.NoModifier))
    ev(QEvent.MouseButtonPress, desde, Qt.LeftButton, Qt.LeftButton)
    for k in range(1, 6):
        ev(QEvent.MouseMove, [a + (b - a) * k / 5 for a, b in zip(desde, hasta, strict=True)], Qt.NoButton, Qt.LeftButton)
    ev(QEvent.MouseButtonRelease, hasta, Qt.LeftButton, Qt.NoButton)


def test_ventana_dentro_de_aspecto_elige_todas_las_caras_o_cuerpos(v):
    """H-72: en Fusion, arrastrar una ventana dentro del comando elige de una lo que encierra (no hace falta un clic
    por cara: en el video del 2026-11-05 hicieron ~30 para pintar cinco letras)."""
    v.visor.encuadrar()
    QTest.qWait(10)
    esquinas = ((3, 3), (v.visor.width() - 3, v.visor.height() - 3))
    p, w = _abrir(v)
    assert v.visor.ventana_en_comando                    # el campo Cuerpos admite varios: arrastrar hace la ventana
    _ventana_en_el_visor(v.visor, *esquinas)
    assert sorted(h["ref"]["cuerpo"] for h in p.valores["cuerpos"]) == ["op1.c1", "op2.c1"]
    p.widgets["aplicar_a"].set_valor("caras")
    _ventana_en_el_visor(v.visor, *esquinas)
    caras = p.valores["caras"]
    assert len(caras) == 9 and {h["tipo"] for h in caras} == {"cara"}       # 6 de la caja + 3 del cilindro
    _ventana_en_el_visor(v.visor, *esquinas)                                  # otra vez: no duplica ni quita
    assert len(p.valores["caras"]) == 9
    w.elegir(asp.buscar("Pintura - Brillante (Rojo)"), desde_biblioteca=True)
    p.aceptar()
    assert len(v.doc.propiedades["op1.c1"]["caras"]) == 6 and not v.visor.ventana_en_comando


def test_seleccion_de_pintura_dentro_de_aspecto_suma_lo_que_toca(v):
    """H-72: SELECCIONAR › Selección de pintura (tecla 3) también anda con el comando abierto: elige para su campo."""
    import numpy as np
    v.visor.encuadrar()
    QTest.qWait(10)
    p, _w = _abrir(v)
    v.acciones["sel_pintura"].trigger()
    assert v.visor.modo == "sel_pintura"
    (a, b), _ok = v.visor.puntos_pantalla(np.array([[0, 0, 20.0], [90, 0, 30.0]]))   # arriba de la caja y del cilindro
    _ventana_en_el_visor(v.visor, tuple(map(float, a)), tuple(map(float, b)))
    assert sorted(h["ref"]["cuerpo"] for h in p.valores["cuerpos"]) == ["op1.c1", "op2.c1"]
    v.acciones["sel_pintura"].trigger()                                       # otra vez: vuelve a la selección común
    assert v.visor.modo is None


def _clic_en_el_visor(visor, pos, doble=False):
    """Clic izquierdo como una persona. Doble: Qt manda press, release, press, doble clic y release (registro del
    2026-11-05: cada doble clic de Gerardo dejó dos «clic»)."""
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent

    def ev(tipo, boton, botones):
        q = QPointF(*pos)
        QApplication.sendEvent(visor, QMouseEvent(tipo, q, visor.mapToGlobal(q), boton, botones, Qt.NoModifier))
    ev(QEvent.MouseMove, Qt.NoButton, Qt.NoButton)
    ev(QEvent.MouseButtonPress, Qt.LeftButton, Qt.LeftButton)
    ev(QEvent.MouseButtonRelease, Qt.LeftButton, Qt.NoButton)
    if doble:
        ev(QEvent.MouseButtonPress, Qt.LeftButton, Qt.LeftButton)
        ev(QEvent.MouseButtonDblClick, Qt.LeftButton, Qt.LeftButton)
        ev(QEvent.MouseButtonRelease, Qt.LeftButton, Qt.NoButton)


def test_placa_con_letras_caras_elegidas_todas_blancas_y_despues_el_cuerpo_entero_negro(v):
    """B-200 y H-73, el caso de Gerardo (2026-11-05): placa con letras unidas y sueltas. En «Caras» se pintan TODAS las
    caras elegidas, también las elegidas con doble clic (antes el segundo clic la soltaba y quedaba sin pintar). En
    «Cuerpos» el cuerpo queda ENTERO del color nuevo: ninguna cara conserva otro color."""
    import numpy as np
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 120, "width": 40, "height": 2, "name": "Placa"})["ok"]
    for i, x in enumerate((-40, -20, 0, 20, 40)):                # unidas las pares, sueltas las impares
        extra = {"operation": "join", "target": "Placa"} if i % 2 == 0 else {}
        assert api.llamar(s, "create_box", {"length": 10, "width": 16, "height": 4, "z": 2, "x": x, **extra})["ok"]
    v.set_documento(s.doc)
    QTest.qWait(20)
    v.visor.encuadrar()
    QTest.qWait(10)
    arriba = v.visor.puntos_pantalla(np.array([[x, 0, 6.0] for x in (-40, -20, 0, 20, 40)]))[0]
    p, w = _abrir(v)
    p.widgets["aplicar_a"].set_valor("caras")
    for k, pos in enumerate(arriba):                              # la cara de arriba de cada letra
        _clic_en_el_visor(v.visor, tuple(map(float, pos)), doble=k % 2 == 1)
    assert len(p.valores["caras"]) == 5
    w.elegir(asp.buscar("Plástico - Brillante (Blanco)"), desde_biblioteca=True)
    p.aceptar()
    pintadas = ad.caras_con_aspecto(v.doc, v.doc.estado_final)
    blanco = pytest.approx(asp.BIBLIOTECA["Plástico - Brillante (Blanco)"]["color"])
    assert len(pintadas) == 5 and all(rgb == blanco for _c, _r, rgb in pintadas)
    assert len(v.visor.caras_pintadas) == 5
    p, w = _abrir(v)                                              # ahora la placa entera en negro
    _clic_en_el_visor(v.visor, tuple(map(float, v.visor.puntos_pantalla(np.array([[0, -17, 2.0]]))[0][0])))
    assert [h["ref"]["cuerpo"] for h in p.valores["cuerpos"]] == ["op1.c1"]
    w.elegir(asp.buscar("Plástico - Brillante (Negro)"), desde_biblioteca=True)
    _previsualizar(p)
    assert {c for c, *_r in v.visor.caras_pintadas} == {"op3.c1", "op5.c1"}   # la previa ya muestra la placa entera
    p.aceptar()
    assert "caras" not in v.doc.propiedades["op1.c1"]
    assert {c for c, _r, _rgb in ad.caras_con_aspecto(v.doc, v.doc.estado_final)} == {"op3.c1", "op5.c1"}
    v.doc.deshacer()                                              # deshacer devuelve las letras blancas de la placa
    assert len(v.doc.propiedades["op1.c1"]["caras"]) == 3


def test_ventana_y_pintura_no_pasan_el_maximo_del_campo(v):
    """Revisión de H-72: un campo de 2 no recibe 9 caras de una ventana."""
    v.visor.encuadrar()
    QTest.qWait(10)
    p, _w = _abrir(v)
    p.widgets["aplicar_a"].set_valor("caras")
    p._por_clave["caras"].maximo = 2
    try:
        _ventana_en_el_visor(v.visor, (3, 3), (v.visor.width() - 3, v.visor.height() - 3))
        assert len(p.valores["caras"]) == 2
    finally:
        p._por_clave["caras"].maximo = None


def test_material_fisico_desde_la_ventana_da_masa_y_color(v):
    """MODIFICAR › Material físico como una persona: elegir el cuerpo, el material en la lista y Aceptar. La masa sale de
    la densidad y, sin aspecto propio, el cuerpo se ve del color del material."""
    from PySide6.QtCore import Qt
    from omnicad.nucleo.analisis import TABLA_MATERIALES
    from omnicad.ui.comandos import CATALOGO
    v._seleccionar([_hit_cuerpo(v, "op1.c1")])
    v.ejecutar_comando(CATALOGO["material_fisico"]())
    p = v.panel
    lista = p.widgets["material"]
    lista.setCurrentIndex(lista.findData("ABS"))                      # lo que hace elegir en la lista desplegable
    QTest.mouseClick(p.boton_ok, Qt.LeftButton)
    assert v.panel is None and v.doc.propiedad("op1.c1", "material") == "ABS"
    r = api.llamar(api.Sesion(v.doc), "get_physical_properties", {"bodies": ["op1.c1"]})["result"]["bodies"][0]
    assert r["mass_g"] == pytest.approx(100 * 60 * 20 * 1.06e-3, rel=1e-6)
    assert _color_en_el_visor(v, "op1.c1") == pytest.approx(TABLA_MATERIALES["ABS"]["color"])
    v.doc.deshacer()
    assert v.doc.propiedad("op1.c1", "material") is None


def test_ocultar_el_cuerpo_oculta_su_cara_pintada(v):
    _ = api.llamar(v.sesion_aspecto, "set_appearance", {"faces": ">Z", "body": "op1.c1", "color": "#ff0000"})
    v._refrescar_visibilidad()
    assert [c for c, *_r in v.visor.caras_pintadas] == ["op1.c1"]
    v._ojo("op1.c1")
    assert v.visor.caras_pintadas == []
    v._ojo("op1.c1")
    assert len(v.visor.caras_pintadas) == 1


def test_editar_en_este_diseno_cambia_el_color_en_vivo_y_aceptar_lo_guarda(v):
    api.llamar(v.sesion_aspecto, "set_appearance", {"bodies": ["op1.c1"], "appearance": "Plástico - Mate (Gris)"})
    original = _color_en_el_visor(v, "op1.c1")
    p, w = _abrir(v)
    assert w.lista.count() == 1 and w.usados == {"asp1"}
    selector = w.editar("asp1")
    selector.cambiado.emit({"color": [0.0, 0.5, 1.0]})                   # lo que hace el espectro o los RGB
    _previsualizar(p)
    assert _color_en_el_visor(v, "op1.c1") == pytest.approx([0.0, 0.5, 1.0])          # lo ven los cuerpos que lo usan
    assert ad.buscar(v.doc, "asp1")["color"] == list(original)                      # el diseño todavía no cambió
    p.aceptar()
    assert ad.buscar(v.doc, "asp1")["color"] == [0.0, 0.5, 1.0] and v.doc.propiedad("op1.c1", "apariencia") == [0.0, 0.5, 1.0]
    v.doc.deshacer()
    assert v.doc.propiedad("op1.c1", "apariencia") == pytest.approx(original)


def test_editar_cancelar_vuelve_atras(v):
    api.llamar(v.sesion_aspecto, "set_appearance", {"bodies": ["op1.c1"], "appearance": "Goma - Negra"})
    original = _color_en_el_visor(v, "op1.c1")
    p, w = _abrir(v)
    w.editar("asp1").cambiado.emit({"color": [1.0, 1.0, 0.0]})
    _previsualizar(p)
    assert _color_en_el_visor(v, "op1.c1") == pytest.approx([1.0, 1.0, 0.0])
    p.cancelar()
    assert _color_en_el_visor(v, "op1.c1") == pytest.approx(original)
    assert v.doc.propiedad("op1.c1", "apariencia") == list(original)


def test_menu_de_en_este_diseno_duplicar_suprimir_copiar_y_favoritos(v):
    api.llamar(v.sesion_aspecto, "set_appearance", {"bodies": ["op1.c1"], "appearance": "Hormigón - Liso"})
    p, w = _abrir(v)
    copia = w.duplicar("asp1")
    assert copia["nombre"] == "Hormigón - Liso (1)" and copia["id"].startswith("nuevo") and w.lista.count() == 2
    assert w.suprimir("asp1") is False                                   # lo usa op1.c1: no se puede sacar
    assert w.suprimir(copia["id"]) is True and w.lista.count() == 1
    assert w.copiar_en_mis(w.entrada("asp1")) == "Hormigón - Liso (1)"     # el nombre de la biblioteca ya está tomado
    assert "Hormigón - Liso (1)" in asp.cargar_usuario()["mis"]
    assert w.copiar_en_mis(w.entrada("asp1")) == "Hormigón - Liso (2)"     # y una copia nunca pisa a otra
    w.favorito(w.entrada("asp1"), True)
    assert asp.cargar_usuario()["favoritos"] == ["Hormigón - Liso"]
    copia = w.duplicar("asp1")
    p.valores["cuerpos"] = [_hit_cuerpo(v, "op2.c1")]
    w.elegir(copia["id"])
    p.aceptar()                                                          # el duplicado entra al diseño y se asigna
    assert [a["nombre"] for a in ad.lista(v.doc)] == ["Hormigón - Liso", "Hormigón - Liso (1)"]
    assert v.doc.propiedad("op2.c1", "aspecto") == "asp2"


def test_quitar_y_suprimir_saca_el_aspecto_de_todos_y_lo_borra_en_un_paso(v):
    """H-74: «Unassign and Delete» de Fusion (clic derecho › Quitar y suprimir): el aspecto se saca de todos los cuerpos
    y caras que lo usan y se borra del diseño, en UN paso de deshacer."""
    api.llamar(v.sesion_aspecto, "set_appearance", {"bodies": ["op1.c1"], "appearance": "Hormigón - Liso"})
    antes = list(v.doc.propiedad("op1.c1", "apariencia"))
    p, w = _abrir(v)
    assert w.usados == {"asp1"} and w.suprimir("asp1") is False          # Suprimir sigue gris: lo usa op1.c1
    assert w.quitar_y_suprimir("asp1") is True and w.lista.count() == 0
    _previsualizar(p)
    assert _color_en_el_visor(v, "op1.c1") is None                        # la vista ya lo saca
    assert ad.buscar(v.doc, "asp1") is not None and v.doc.propiedad("op1.c1", "apariencia") == pytest.approx(antes)
    p.aceptar()
    assert ad.lista(v.doc) == [] and not v.doc.propiedades.get("op1.c1", {}).get("apariencia")
    assert _color_en_el_visor(v, "op1.c1") is None
    v.doc.deshacer()                                                      # un solo paso de deshacer para las dos cosas
    assert ad.buscar(v.doc, "asp1") is not None and ad.usos(v.doc, "asp1")[0] == ["op1.c1"]
    assert v.doc.propiedad("op1.c1", "apariencia") == pytest.approx(antes)


def test_el_menu_de_en_este_diseno_ofrece_quitar_y_suprimir(v):
    api.llamar(v.sesion_aspecto, "set_appearance", {"bodies": ["op1.c1"], "appearance": "Hormigón - Liso"})
    _p, w = _abrir(v)
    acciones = {a.text(): a for a in w._menu_de_diseno("asp1").actions()}
    assert acciones["Suprimir"].isEnabled() is False and acciones["Quitar y suprimir"].isEnabled() is True


def test_editar_uno_de_la_biblioteca_deja_una_copia_en_el_diseno(v):
    p, w = _abrir(v)
    selector = w.editar_de_biblioteca(asp.buscar("Acero - Pulido"))
    assert selector is not None and w.elegido["id"].startswith("nuevo") and w.lista.count() == 1
    selector.cambiado.emit({"color": [0.2, 0.2, 0.9], "nombre": "Acero azul"})
    assert w.elegido["nombre"] == "Acero azul" and w.elegido["color"] == [0.2, 0.2, 0.9]
    assert asp.BIBLIOTECA["Acero - Pulido"]["color"] != [0.2, 0.2, 0.9]
    p.valores["cuerpos"] = [_hit_cuerpo(v, "op1.c1")]
    p.aceptar()
    assert ad.buscar(v.doc, "Acero azul")["origen"] == "biblioteca" and v.doc.propiedad("op1.c1", "aspecto") == "asp1"


def test_aceptar_sin_nada_elegido_avisa_y_no_cierra(v):
    p, w = _abrir(v)
    p.aceptar()
    assert v.panel is p and "Elegí un aspecto" in p.mensaje.text()
    w.elegir(asp.buscar("Goma - Gris"), desde_biblioteca=True)
    p.aceptar()
    assert v.panel is p and "Seleccioná los cuerpos" in p.mensaje.text()


def test_el_color_hex_de_siempre_sigue_funcionando(v):
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos import CATALOGO
    cmd = CATALOGO["aspecto"]()
    ctx = ContextoComando(v.doc)
    valores = {c.clave: c.defecto for c in cmd.campos(ctx)} | {"cuerpos": [_hit_cuerpo(v, "op1.c1")], "hex": "#ff0000"}
    cmd.aplicar(valores, ctx)
    assert v.doc.propiedad("op1.c1", "apariencia") == [1.0, 0.0, 0.0] and ad.lista(v.doc) == []
    with pytest.raises(Exception, match="#rrggbb"):
        cmd.aplicar(valores | {"hex": "rojo"}, ctx)


# ---------------------------------------------------------------- selector rápido y Editor de materiales
def test_selector_rapido_espectro_rgb_y_deslizadores_emiten_cambios(v):
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from omnicad.ui.aspectos_ui import SelectorRapido
    sel = SelectorRapido()
    sel.cargar(asp.BIBLIOTECA["Plástico - Brillante (Azul)"])
    vistos = []
    sel.cambiado.connect(vistos.append)
    sel.rgb[0].setValue(200)
    assert vistos[-1]["color"][0] == pytest.approx(200 / 255)
    sel.aspereza.numero.setValue(0.8)
    sel.reflectancia.barra.setValue(500)
    assert vistos[-2] == {"aspereza": 0.8} and vistos[-1]["reflectancia"] == pytest.approx(0.5)
    sel.profundidad.numero.setValue(1.5)
    assert vistos[-1] == {"profundidad": 1.5, "translucidez": True}
    sel.menu_colores.actions()[0].trigger()                                 # «Bibliotecas de color» › Blanco
    assert vistos[-1]["color"] == [1.0, 1.0, 1.0] and [c.value() for c in sel.rgb] == [255, 255, 255]
    sel.show()
    sel.resize(sel.sizeHint())
    evento = QMouseEvent(QMouseEvent.MouseButtonPress, QPointF(40, 30), QPointF(40, 30), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    sel.espectro.mousePressEvent(evento)                                    # un clic en el cuadrado del espectro
    sel.espectro.mouseReleaseEvent(evento)
    assert vistos[-1]["color"] != [1.0, 1.0, 1.0] and len(vistos[-1]["color"]) == 3
    avanzada = []
    sel.avanzada.connect(lambda: avanzada.append(1))
    sel.b_avanzada.click()
    assert avanzada == [1]
    sel.close()


@pytest.mark.parametrize("escrito,esperado", [("0.25", 0.25), ("0,25", 0.25), ("1", 1.0)])
def test_los_numeros_del_aspecto_aceptan_punto_y_coma_tecleando(v, escrito, esperado):
    """B-202: con la PC en español, «0.25» tecleado en Aspereza quedaba en 0 (solo entraba la coma)."""
    from PySide6.QtCore import Qt
    from omnicad.ui.aspectos_ui import EditorMateriales, SelectorRapido
    sel = SelectorRapido()
    sel.cargar(asp.BIBLIOTECA["Plástico - Brillante (Azul)"])
    ed = EditorMateriales(asp.BIBLIOTECA["Plástico - Mate (Gris)"])
    ed.g_transl.setChecked(True)                            # la profundidad se escribe con la translucidez prendida
    sel.show()
    ed.show()
    for campo in (sel.aspereza.numero, ed.reflectancia.numero, ed.profundidad):
        campo.setFocus()
        campo.selectAll()                                   # el número (sin el sufijo): lo tipeado lo reemplaza
        QTest.keyClicks(campo, escrito)
        QTest.keyClick(campo, Qt.Key_Tab)
        assert campo.value() == pytest.approx(esperado)
    sel.close()
    ed.close()


def test_editor_de_materiales_en_vivo_aplicar_y_cancelar(v, tmp_path):
    from PIL import Image
    from omnicad.ui.aspectos_ui import EditorMateriales
    ed = EditorMateriales(asp.BIBLIOTECA["Plástico - Mate (Gris)"])
    vistos = []
    ed.cambiado.connect(vistos.append)
    ed.reflectancia.numero.setValue(0.25)
    ed.g_transl.setChecked(True)
    ed.profundidad.setValue(0.4)
    ed.g_emi.setChecked(True)
    ed.luminancia.setValue(300)
    ed.forma.setCurrentText("Nítida")
    ed.anisotropia.numero.setValue(0.5)
    assert {k for d in vistos for k in d} >= {"reflectancia", "translucidez", "profundidad", "emisividad", "luminancia",
                                            "resalte"}
    assert ed.a["resalte"]["forma"] == "Nítida" and ed.a["resalte"]["anisotropia"] == 0.5 and ed.a["luminancia"] == 300
    png = tmp_path / "relieve.png"
    Image.new("L", (8, 8), 90).save(png)
    ed.elegir_imagen("relieve", str(png))
    assert ed.a["relieve"]["archivo"] == "relieve.png" and ed.imagenes["relieve"][0].isChecked()
    ed.aplicar()                                                             # «Aplicar»: este es el punto de vuelta
    ed.reflectancia.numero.setValue(0.9)
    revertidos = []
    ed.revertido.connect(revertidos.append)
    ed.cancelar()                                                            # «Cancelar»: vuelve al último «Aplicar»
    assert revertidos[0]["reflectancia"] == 0.25 and ed.reflectancia.valor() == 0.25 and ed.a["relieve"] is not None
    ed.poner_imagen("relieve", None)
    assert ed.a["relieve"] is None and ed.imagenes["relieve"][1].text() == "(ninguna imagen seleccionada)"


def test_el_editor_abierto_desde_el_selector_cambia_el_modelo_al_instante(v):
    api.llamar(v.sesion_aspecto, "set_appearance", {"bodies": ["op1.c1"], "appearance": "Plástico - Mate (Gris)"})
    p, w = _abrir(v)
    w.editar("asp1").avanzada.emit()
    assert w.editor is not None
    w.editor.color.set_color([0.9, 0.1, 0.1])
    w.editor.cambiado.emit({"color": [0.9, 0.1, 0.1]})
    _previsualizar(p)
    assert _color_en_el_visor(v, "op1.c1") == pytest.approx([0.9, 0.1, 0.1])
    w.editor.cancelar()
    p.cancelar()
    assert v.doc.propiedad("op1.c1", "apariencia") != [0.9, 0.1, 0.1]


def test_el_editor_no_lee_una_imagen_gigante_ni_una_que_no_es_imagen(v, tmp_path, monkeypatch):
    from omnicad.ui.aspectos_ui import EditorMateriales
    ed = EditorMateriales(asp.BIBLIOTECA["Goma - Gris"])
    grande = tmp_path / "enorme.png"
    with open(grande, "wb") as f:
        f.truncate(7 * 1024 * 1024)                                        # 7 MB: pasa el tope sin llenar el disco
    ed.elegir_imagen("relieve", str(grande))
    falsa = tmp_path / "falsa.png"
    falsa.write_bytes(b"esto no es una imagen")
    ed.elegir_imagen("corte", str(falsa))
    assert ed.a["relieve"] is None and ed.a["corte"] is None
