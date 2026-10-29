# -*- coding: utf-8 -*-
"""Apariencia de la interfaz (Preferencias › Apariencia): tipografía, colores de texto y perfiles.

La hoja de estilo en sí (QSS) se prueba en test_temas.py. Acá va lo que llega a la ventana y al diálogo.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def app_qt():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def ventana(app_qt, tmp_path_factory):
    from omnicad.ui import temas
    from PySide6.QtCore import QSettings
    from PySide6.QtTest import QTest
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    carpeta = tmp_path_factory.mktemp("tipografia_ui")
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(carpeta / "preferencias.ini"), QSettings.IniFormat)))
    v.show()
    QTest.qWait(1)
    yield v
    temas.activar_tipografia()
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    QTest.qWait(1)


@pytest.fixture
def prefs(tmp_path):
    from PySide6.QtCore import QSettings
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui import temas
    temas.activar_tipografia()
    yield Preferencias(QSettings(str(tmp_path / "prefs.ini"), QSettings.IniFormat))
    temas.activar_tipografia()


# ---------------------------------------------------------------- F1: fuente y tamaño base
def test_aplicar_tema_replica_cuando_cambia_la_tipografia(ventana):
    from PySide6.QtWidgets import QApplication
    v = ventana
    v.prefs["interfaz/fuente"], v.prefs["interfaz/tamano_pct"] = "Arial", 130
    v.aplicar_tema()
    hoja = QApplication.instance().styleSheet()
    assert 'font-family: "Arial"' in hoja and "font-size: 11.7pt" in hoja
    v.prefs["interfaz/fuente"], v.prefs["interfaz/tamano_pct"] = "Segoe UI", 100
    v.aplicar_tema()
    hoja = QApplication.instance().styleSheet()
    assert 'font-family: "Segoe UI"' in hoja and "font-size: 9pt" in hoja


def test_la_cinta_recalcula_los_anchos_de_los_botones_al_cambiar_la_letra(ventana):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QToolButton
    v = ventana
    pagina = v.cinta.pila.currentWidget()
    try:
        pagina.setProperty("ancho_con_texto", 12345)      # medida vieja, de otra tipografía
        v.prefs["interfaz/tamano_pct"] = 150
        v.aplicar_tema()
        assert pagina.property("ancho_con_texto") != 12345
        for b in pagina.findChildren(QToolButton, "boton_cinta"):     # si muestra texto, el ancho le alcanza
            if b.isVisible() and b.toolButtonStyle() == Qt.ToolButtonTextUnderIcon:
                necesita = max(b.fontMetrics().horizontalAdvance(r) for r in b.text().split("\n")) + 14
                assert b.width() >= necesita, (b.text(), b.width(), necesita)
    finally:
        v.prefs["interfaz/tamano_pct"] = 100
        v.aplicar_tema()


# ---------------------------------------------------------------- F2: página Apariencia
def test_la_pagina_apariencia_tiene_fuente_tamano_y_restablecer(prefs):
    from PySide6.QtWidgets import QComboBox, QLabel, QSlider
    from omnicad.ui.preferencias import DialogoPreferencias
    dlg = DialogoPreferencias(prefs, inicial="apariencia")
    fuente = dlg.controles["interfaz/fuente"]
    tamano = dlg.controles["interfaz/tamano_pct"]
    assert isinstance(fuente, QComboBox) and fuente.findData("Segoe UI") >= 0
    assert isinstance(tamano, QSlider) and (tamano.minimum(), tamano.maximum()) == (80, 150)
    assert (tamano.singleStep(), tamano.value()) == (5, 100)
    etiqueta = dlg.findChild(QLabel, "valor_porcentaje")
    assert etiqueta is not None and etiqueta.text() == "100 %"
    assert dlg.b_restablecer_apariencia.text() == "Restablecer apariencia"


def test_apariencia_se_previsualiza_al_instante_y_cancelar_vuelve(prefs):
    from omnicad.ui.preferencias import DialogoPreferencias
    dlg = DialogoPreferencias(prefs, inicial="apariencia")
    avisos = []
    dlg.apariencia_cambiada.connect(lambda: avisos.append(tuple(prefs[k] for k in ("interfaz/fuente",
                                                                                 "interfaz/tamano_pct"))))
    dlg.controles["interfaz/tamano_pct"].setValue(130)
    assert prefs["interfaz/tamano_pct"] == 130 and avisos[-1][1] == 130
    fuente = dlg.controles["interfaz/fuente"]
    fuente.setCurrentIndex((fuente.currentIndex() + 1) % fuente.count())
    assert prefs["interfaz/fuente"] == fuente.currentData()
    dlg.reject()
    assert prefs["interfaz/tamano_pct"] == 100 and prefs["interfaz/fuente"] == "Segoe UI"
    assert avisos[-1] == ("Segoe UI", 100)


def test_restablecer_apariencia_vuelve_a_los_defectos_sin_tocar_el_tema(prefs):
    from omnicad.ui.preferencias import DialogoPreferencias
    prefs["interfaz/fuente"], prefs["interfaz/tamano_pct"], prefs["general/tema"] = "Arial", 140, "clasico"
    dlg = DialogoPreferencias(prefs, inicial="apariencia")
    dlg.b_restablecer_apariencia.click()
    assert prefs["interfaz/fuente"] == "Segoe UI" and prefs["interfaz/tamano_pct"] == 100
    assert prefs["general/tema"] == "clasico"                 # el tema no se toca
    assert dlg.controles["interfaz/tamano_pct"].value() == 100


# ---------------------------------------------------------------- F4: colores de texto sobre el tema
def test_colores_de_texto_que_no_conservan_el_contraste_se_rechazan():
    from omnicad.ui import temas
    colores = temas.INCLUIDOS["oscuro_moderno"]["colores"]
    aplicables, rechazos = temas.colores_texto(colores, {"texto": "#ffffff", "texto_tenue": "#111111"})
    assert aplicables == {"texto": "#ffffff"}
    assert [token for token, *_ in rechazos] == ["texto_tenue"]
    assert rechazos[0][2] and rechazos[0][2][0][1] < temas.MIN_CONTRASTE
    # el color del propio tema siempre vale y un valor inválido se avisa con texto
    aplicables, rechazos = temas.colores_texto(colores, {"texto": colores["texto"], "acento": "rojo"})
    assert aplicables == {} and rechazos[0][2] == "no es un color #rrggbb"


def test_aplicar_colores_texto_pisa_el_tema_activo_sin_tocar_el_archivo():
    from omnicad.ui import temas
    temas.activar("claro_moderno")
    rechazos = temas.aplicar_colores_texto({"texto": "#000000", "texto_tenue": "#eeeeee"})
    assert rechazos and temas.color("texto") == "#000000"     # el válido entra; el ilegible se queda en el tema
    assert temas.color("texto_tenue") == temas.INCLUIDOS["claro_moderno"]["colores"]["texto_tenue"]
    assert temas.INCLUIDOS["claro_moderno"]["colores"]["texto"] == "#1f2933"    # el archivo del tema no cambia
    temas.activar("claro_moderno")                           # volver a activar borra lo pisado
    assert temas.color("texto") == "#1f2933"


def test_la_ventana_aplica_los_colores_de_texto_y_descarta_los_ilegibles(ventana):
    from PySide6.QtWidgets import QApplication
    from omnicad.ui import temas
    v = ventana
    v.prefs["general/tema"] = "claro_moderno"
    v.prefs["interfaz/color_texto"] = "#000000"
    v.aplicar_tema()
    assert temas.color("texto") == "#000000" and "color: #000000" in QApplication.instance().styleSheet()
    v.prefs["interfaz/color_texto"] = "#eeeeee"              # casi blanco sobre blanco: no se aplica
    v.aplicar_tema()
    assert temas.color("texto") == temas.INCLUIDOS["claro_moderno"]["colores"]["texto"]
    v.prefs["interfaz/color_texto"] = ""
    v.prefs["general/tema"] = "oscuro_moderno"
    v.aplicar_tema()


def test_dialogo_avisa_el_color_de_texto_rechazado_y_quitar_vuelve_al_tema(prefs):
    from omnicad.ui import temas
    from omnicad.ui.preferencias import CampoColor, DialogoPreferencias
    temas.activar("oscuro_moderno")
    dlg = DialogoPreferencias(prefs, inicial="apariencia")
    campo = dlg.controles["interfaz/color_texto"]
    assert isinstance(campo, CampoColor) and campo.value() == "" and not campo.quitar.isEnabled()
    campo.setValue("#000000")                                # negro sobre oscuro: no se puede leer
    assert prefs["interfaz/color_texto"] == "#000000" and "contraste" in dlg.aviso_apariencia.text()
    campo.setValue("#ffffff")
    assert prefs["interfaz/color_texto"] == "#ffffff" and "contraste" not in dlg.aviso_apariencia.text()
    campo.quitar.click()
    assert campo.value() == "" and prefs["interfaz/color_texto"] == "" and not campo.quitar.isEnabled()


# ---------------------------------------------------------------- F5: texto del boceto
def test_la_pagina_apariencia_tiene_la_fuente_y_el_tamano_de_las_cotas(prefs):
    from PySide6.QtWidgets import QComboBox, QSlider
    from omnicad.ui.preferencias import DialogoPreferencias
    dlg = DialogoPreferencias(prefs, inicial="apariencia")
    fuente = dlg.controles["boceto/fuente_cotas"]
    tamano = dlg.controles["boceto/tamano_cotas_pct"]
    assert isinstance(fuente, QComboBox) and fuente.itemData(0) == "" and fuente.itemText(0) == "La de la interfaz"
    assert isinstance(tamano, QSlider) and (tamano.minimum(), tamano.maximum(), tamano.value()) == (70, 200, 100)


def test_las_cotas_del_boceto_usan_la_fuente_elegida_y_el_recuadro_crece(app_qt):
    from omnicad.nucleo import geometria as g
    from omnicad.restricciones import Boceto
    from omnicad.timeline.parametros import TablaParametros
    from omnicad.ui import temas
    from omnicad.ui.editor_boceto import Lienzo

    b = Boceto()
    linea = b.agregar_linea((0, 0), (60, 0))
    b.agregar_cota("distancia", [linea], "60")

    def alto_zona():
        lz = Lienzo(b, TablaParametros().evaluar, plano=g.Plano("XY"))
        lz.ajustar_grilla = False
        lz.resize(800, 600)
        lz.show()
        lz.grab()
        alto = next(iter(lz._zonas_cotas.values())).height()
        lz.close()
        lz.deleteLater()
        return alto

    try:
        temas.activar_tipografia()
        base = alto_zona()
        temas.activar_tipografia({"fuente_cotas": "", "tamano_cotas_pct": 200})
        doble = alto_zona()
        assert doble > base * 1.5            # el recuadro de agarre mide el texto real, no un alto fijo
    finally:
        temas.activar_tipografia()


# ---------------------------------------------------------------- F6: MCP y CLI
def test_api_preferencias_de_apariencia_validan_fuente_color_y_rangos(tmp_path, monkeypatch):
    monkeypatch.setenv("OMNICAD_AJUSTES_INI", str(tmp_path / "ajustes.ini"))
    from omnicad import api
    s = api.Sesion()

    def llamar(nombre, **args):
        return api.llamar(s, nombre, args)

    def ok(nombre, **args):
        r = llamar(nombre, **args)
        assert r["ok"], r
        return r["result"]

    def falla(nombre, **args):
        r = llamar(nombre, **args)
        assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS", r
        assert r["mensaje"] and "español" not in r["mensaje"]

    claves = ["interfaz/fuente", "interfaz/tamano_pct", "interfaz/color_texto", "boceto/fuente_cotas",
              "boceto/tamano_cotas_pct"]
    por = {p["key"]: p for p in ok("get_preferences", keys=claves)["preferences"]}
    assert por["interfaz/fuente"]["default"] == "Segoe UI" and por["interfaz/fuente"]["options"] == []
    assert por["interfaz/tamano_pct"]["options"] == list(range(80, 151, 5))
    assert por["boceto/tamano_cotas_pct"]["options"] == list(range(70, 201, 5))
    assert ok("set_preference", key="interfaz/fuente", value="Cascadia Mono")["value"] == "Cascadia Mono"
    assert ok("set_preference", key="interfaz/color_texto", value="#AABBCC")["value"] == "#aabbcc"
    assert ok("set_preference", key="interfaz/color_texto", value="")["value"] == ""
    assert ok("set_preference", key="boceto/fuente_cotas", value="")["value"] == ""
    assert ok("set_preference", key="boceto/tamano_cotas_pct", value=200)["value"] == 200
    falla("set_preference", key="interfaz/fuente", value="   ")
    falla("set_preference", key="interfaz/fuente", value=3)
    falla("set_preference", key="interfaz/fuente", value='Arial"; color: red')
    falla("set_preference", key="interfaz/color_texto", value="rojo")
    falla("set_preference", key="interfaz/color_texto", value="#abc")
    falla("set_preference", key="interfaz/tamano_pct", value=151)
    falla("set_preference", key="boceto/tamano_cotas_pct", value=65)


# ---------------------------------------------------------------- F7: perfiles de apariencia
def test_perfil_de_apariencia_fija_la_letra_y_tocarlo_pasa_a_personalizado(prefs):
    from omnicad.ui.preferencias import DialogoPreferencias
    dlg = DialogoPreferencias(prefs, inicial="apariencia")
    perfil = dlg.controles["interfaz/perfil"]
    perfil.setCurrentIndex(perfil.findData("lectura_comoda"))
    assert prefs["interfaz/perfil"] == "lectura_comoda"
    assert prefs["interfaz/tamano_pct"] == 120 and prefs["boceto/tamano_cotas_pct"] == 120
    assert dlg.controles["interfaz/tamano_pct"].value() == 120
    dlg.controles["interfaz/tamano_pct"].setValue(130)        # tocar una clave del perfil
    assert prefs["interfaz/perfil"] == "personalizado" and perfil.currentData() == "personalizado"
    perfil.setCurrentIndex(perfil.findData("normal"))         # «Normal» vuelve a los valores de fábrica
    assert prefs["interfaz/tamano_pct"] == 100 and prefs["boceto/tamano_cotas_pct"] == 100


def test_la_ventana_aplica_el_perfil_y_lo_pasa_a_personalizado_al_tocarlo(ventana):
    from PySide6.QtWidgets import QApplication
    v = ventana
    try:
        v.prefs["interfaz/perfil"] = "lectura_comoda"
        v.aplicar_preferencias()
        assert v.prefs["interfaz/tamano_pct"] == 120 and v.prefs["boceto/tamano_cotas_pct"] == 120
        assert "font-size: 10.8pt" in QApplication.instance().styleSheet()
        v.prefs["interfaz/tamano_pct"] = 130
        v.aplicar_preferencias()
        assert v.prefs["interfaz/perfil"] == "personalizado" and v.prefs["interfaz/tamano_pct"] == 130
        v.prefs["interfaz/perfil"] = "normal"
        v.aplicar_preferencias()
        assert v.prefs["interfaz/tamano_pct"] == 100
    finally:
        v.prefs["interfaz/perfil"] = "personalizado"
        v.prefs["interfaz/tamano_pct"] = 100
        v.prefs["boceto/tamano_cotas_pct"] = 100
        v.aplicar_preferencias()


def test_api_perfil_fija_las_claves_y_tocar_una_lo_pasa_a_personalizado(tmp_path, monkeypatch):
    monkeypatch.setenv("OMNICAD_AJUSTES_INI", str(tmp_path / "ajustes.ini"))
    from omnicad import api
    s = api.Sesion()

    def llamar(nombre, **args):
        return api.llamar(s, nombre, args)

    r = llamar("set_preference", key="interfaz/perfil", value="lectura_comoda")
    assert r["ok"] and r["result"]["updated"]["interfaz/tamano_pct"] == 120
    assert r["result"]["updated"]["boceto/tamano_cotas_pct"] == 120
    assert llamar("get_preferences", keys=["interfaz/tamano_pct"])["result"]["preferences"][0]["value"] == 120
    r = llamar("set_preference", key="interfaz/tamano_pct", value=130)
    assert r["ok"] and r["result"]["updated"]["interfaz/perfil"] == "personalizado"
    r = llamar("set_preference", key="interfaz/perfil", value="normal")
    assert r["ok"] and r["result"]["updated"]["boceto/tamano_cotas_pct"] == 100


# ---------------------------------------------------------------- F8: fuentes de lectura fácil
def test_el_combo_de_fuentes_pone_primero_la_lectura_facil_si_esta_instalada(app_qt):
    from omnicad.ui.preferencias import _combo_fuentes
    c = _combo_fuentes("Segoe UI", familias=["Arial", "OpenDyslexic", "Segoe UI", "Atkinson Hyperlegible"])
    textos = [c.itemText(i) for i in range(c.count())]
    assert textos[0] == "Lectura fácil" and not c.model().item(0).isEnabled()
    assert c.itemData(1) == "OpenDyslexic" and c.itemData(2) == "Atkinson Hyperlegible"
    assert c.findData("Atkinson Hyperlegible") < c.findData("Arial")       # el grupo va antes que el resto
    assert c.currentData() == "Segoe UI"


def test_sin_fuentes_de_lectura_facil_el_grupo_no_aparece(app_qt):
    from omnicad.ui.preferencias import _combo_fuentes
    c = _combo_fuentes("Segoe UI", familias=["Arial", "Segoe UI"])
    textos = [c.itemText(i) for i in range(c.count())]
    assert "Lectura fácil" not in textos and textos == ["Arial", "Segoe UI"]
    c = _combo_fuentes("", "La de la interfaz", familias=["Arial"])
    assert c.itemData(0) == "" and c.itemText(0) == "La de la interfaz"


def test_las_etiquetas_de_apariencia_no_se_cortan_con_ningun_tamano_de_letra(app_qt, prefs):
    from omnicad.ui import temas
    from omnicad.ui.preferencias import DialogoPreferencias
    from PySide6.QtWidgets import QLabel
    temas.activar("oscuro_moderno")
    temas.activar_tipografia({"tamano_pct": 100})
    temas.aplicar_a_app(app_qt)
    dlg = DialogoPreferencias(prefs, None, "apariencia")
    dlg.show()
    try:
        for pct in (100, 118, 143, 150, 80, 100):             # con el diálogo abierto, como mover el deslizador
            temas.activar_tipografia({"tamano_pct": pct})
            temas.aplicar_a_app(app_qt)
            app_qt.processEvents()
            cortadas = [(e.text(), e.height(), e.heightForWidth(e.width())) for e in dlg.findChildren(QLabel)
                        if e.wordWrap() and e.isVisible() and e.text() and e.height() < e.heightForWidth(e.width()) - 1]
            assert cortadas == [], (pct, cortadas)
    finally:
        dlg.close()
        temas.activar_tipografia()
        temas.aplicar_a_app(app_qt)
