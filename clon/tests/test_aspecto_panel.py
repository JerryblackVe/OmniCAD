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
    evento = QMouseEvent(QMouseEvent.MouseButtonPress, QPointF(40, 30), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    sel.espectro.mousePressEvent(evento)                                    # un clic en el cuadrado del espectro
    sel.espectro.mouseReleaseEvent(evento)
    assert vistos[-1]["color"] != [1.0, 1.0, 1.0] and len(vistos[-1]["color"]) == 3
    avanzada = []
    sel.avanzada.connect(lambda: avanzada.append(1))
    sel.b_avanzada.click()
    assert avanzada == [1]
    sel.close()


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
