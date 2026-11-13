# -*- coding: utf-8 -*-
"""P-149: Preferencias › Asas y superposiciones. Color, tamaño y opacidad de lo que se dibuja sobre el visor: la página, la
vista al instante, «Restablecer», Cancelar y las herramientas de la API."""
import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from test_manipuladores import _doc_rectangulo, _manip, _panel, _perfil, app_qt  # noqa: E402, F401

from omnicad.ui import estilo_asas, manipuladores as mp  # noqa: E402


@pytest.fixture(scope="module")
def ventana(tmp_path_factory):
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    carpeta = tmp_path_factory.mktemp("p149")
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(carpeta / "preferencias.ini"), QSettings.IniFormat)))
    v.show()
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    QTest.qWait(1)


@pytest.fixture(autouse=True)
def _de_fabrica():
    yield
    estilo_asas.aplicar(estilo_asas.DEFECTOS)          # que ninguna prueba deje su estilo a la siguiente


def _estilo(**cambios):
    """Aplica el estilo con los valores dados (clave sin «asas/») sobre los de fábrica."""
    estilo_asas.aplicar({**estilo_asas.DEFECTOS, **{f"asas/{k}": v for k, v in cambios.items()}})


def test_las_claves_de_fabrica_son_las_mismas_en_la_interfaz_y_en_la_api():
    from omnicad.api.herramientas_preferencias import _OPCIONES
    from omnicad.ui.preferencias import DEFECTOS
    assert estilo_asas.CLAVES and set(estilo_asas.CLAVES) <= set(DEFECTOS) and set(estilo_asas.CLAVES) <= set(_OPCIONES)
    for k, v in estilo_asas.DEFECTOS.items():
        assert DEFECTOS[k] == v and _OPCIONES[k][0] == v
    assert estilo_asas.rgb("flechas") == mp.AMARILLO and estilo_asas.rgb("previa_corte") == mp.ROJO_PREVIA


def test_con_los_valores_de_fabrica_el_dibujo_queda_igual():
    prims = [("lineas", np.zeros((2, 3)), mp.AMARILLO, 3.0), ("tris", np.zeros((3, 3)), mp.ROJO_PREVIA, 0.45)]
    contornos, dibujo = mp._con_estilo(prims, "flechas")
    assert dibujo == prims and contornos == mp._contornos(prims)


def test_color_propio_y_opacidad_se_aplican_al_dibujo_y_al_contorno():
    _estilo(flechas_color="#ff0000", flechas_opacidad_pct=50)
    prims = [("lineas", np.zeros((2, 3)), mp.AMARILLO, 3.0), ("lineas", np.zeros((2, 3)), mp.AMARILLO_ACTIVO, 3.0),
             ("tris", np.zeros((3, 3)), (0.5, 0.5, 0.5), 0.8)]
    contornos, dibujo = mp._con_estilo(prims, "flechas")
    assert dibujo[0][2] == (1.0, 0.0, 0.0, 0.5)                              # el color elegido, a media opacidad
    assert dibujo[1][2][:3] == mp._aclarar((1.0, 0.0, 0.0)) and dibujo[1][2][3] == 0.5     # el de «activa», más claro
    assert dibujo[2][2] == (0.5, 0.5, 0.5) and dibujo[2][3] == pytest.approx(0.4)        # lo ajeno no cambia de color
    assert len(contornos) == 2 and all(c[2][3] == 0.5 for c in contornos)             # el contorno oscuro sigue la opacidad


def test_el_anillo_toma_su_propio_color_y_no_el_de_las_flechas():
    _estilo(anillo_color="#00ff00")
    prims = [("lineas", np.zeros((2, 3)), mp.AnilloAngulo.AZUL, 2.0), ("lineas", np.zeros((2, 3)), mp.AMARILLO, 3.0)]
    contornos, dibujo = mp._con_estilo(prims, "anillo")
    assert dibujo[0][2] == (0.0, 1.0, 0.0) and dibujo[1][2] == mp.AMARILLO
    assert len(contornos) == 1                                               # el anillo va sin contorno, como en Fusion


def test_el_tamano_agranda_la_flecha_en_pantalla(app_qt):  # noqa: F811
    doc = _doc_rectangulo()
    from omnicad.ui.comandos.solido import Extruir
    panel, visor, _ = _panel(Extruir(), doc, {"perfiles": [_perfil(doc)], "distancia": "10 mm"})
    try:
        flecha = _manip(panel, "flecha:distancia")
        a, b = flecha.puntos(panel.manipuladores)
        largo = np.linalg.norm(b - a)
        _estilo(flechas_tamano_pct=200)
        a2, b2 = flecha.puntos(panel.manipuladores)
        assert np.linalg.norm(b2 - a2) == pytest.approx(2 * largo)
        panel.manipuladores.redibujar()
        assert any(p[2] is not None for p in visor._capas["manipuladores"])
    finally:
        panel.cancelar()
        panel.deleteLater()
        visor.deleteLater()


def test_la_flecha_dibujada_lleva_el_color_elegido(app_qt):  # noqa: F811
    doc = _doc_rectangulo()
    from omnicad.ui.comandos.solido import Extruir
    panel, visor, _ = _panel(Extruir(), doc, {"perfiles": [_perfil(doc)], "distancia": "10 mm"})
    try:
        _estilo(flechas_color="#ff0000", flechas_opacidad_pct=40)
        panel.manipuladores.redibujar()
        colores = {tuple(p[2]) for p in visor._capas["manipuladores"] if p[2] is not None}
        assert (1.0, 0.0, 0.0, 0.4) in colores and mp.AMARILLO not in colores
    finally:
        panel.cancelar()
        panel.deleteLater()
        visor.deleteLater()


def test_la_pagina_cambia_las_preferencias_al_instante_y_restablece(ventana):
    from PySide6.QtTest import QSignalSpy
    from omnicad.ui.preferencias import CampoColor, DialogoPreferencias
    dlg = DialogoPreferencias(ventana.prefs, ventana, "asas")
    dlg.asas_cambiadas.connect(ventana._aplicar_estilo_asas)
    try:
        pagina = dlg.pagina_asas
        color, tam, op = (dlg.controles[f"asas/flechas_{p}"] for p in ("color", "tamano_pct", "opacidad_pct"))
        assert isinstance(color, CampoColor) and color.boton._texto == ""      # una muestra que se toca: sin texto ni código
        aviso = QSignalSpy(dlg.asas_cambiadas)
        color.setValue("#112233")
        tam.setValue(150)
        op.setValue(60)
        assert aviso.count() == 3
        assert ventana.prefs["asas/flechas_color"] == "#112233" and ventana.prefs["asas/flechas_tamano_pct"] == 150
        assert estilo_asas.rgb("flechas") == pytest.approx(estilo_asas.hex_a_rgb("#112233"))
        assert estilo_asas.tamano("flechas") == 1.5 and estilo_asas.opacidad("flechas") == 0.6
        pagina.restablecer.click()
        assert ventana.prefs["asas/flechas_color"] == "" and ventana.prefs["asas/flechas_opacidad_pct"] == 100
        assert estilo_asas.rgb("flechas") == mp.AMARILLO and tam.value() == 100 and pagina.tam_global.value() == 100
    finally:
        dlg.reject()
        dlg.deleteLater()


def test_los_ajustes_globales_mueven_las_asas_y_la_vista_previa_cambia(ventana):
    from omnicad.ui.preferencias import DialogoPreferencias
    dlg = DialogoPreferencias(ventana.prefs, ventana, "asas")
    dlg.asas_cambiadas.connect(ventana._aplicar_estilo_asas)
    try:
        pagina = dlg.pagina_asas
        pagina.tam_global.setValue(170)
        pagina.color_global.setValue("#e0245e")
        for g in ("flechas", "anillo", "puntos", "cajas"):
            assert ventana.prefs[f"asas/{g}_tamano_pct"] == 170 and ventana.prefs[f"asas/{g}_color"] == "#e0245e"
        assert ventana.prefs["asas/seleccion_color"] == ""                  # lo que no es asa no se toca
        gestor = pagina.vista.gestor                                        # la vista previa usa las asas reales
        assert {type(m).__name__ for m in gestor.manips} == {"Flecha", "AnilloAngulo", "AsaRadial"}
        colores = {tuple(p[2]) for p in pagina.vista.visor._capas["manipuladores"] if p[2] is not None}
        assert any(c[:3] == pytest.approx(estilo_asas.hex_a_rgb("#e0245e")) for c in colores if len(c) >= 3)
        pagina.vista.resaltar("anillo")
        assert gestor._hover == ("angulo:angulo", "asa")                   # pasar por la fila resalta ese elemento
    finally:
        dlg.reject()
        dlg.deleteLater()


def test_el_viewcube_toma_el_color_y_la_opacidad_elegidos():
    from omnicad.ui.superposiciones import ViewCube
    assert ViewCube._cian(255).name() == "#35d0ee"
    _estilo(viewcube_color="#ff0000", viewcube_opacidad_pct=50)
    c = ViewCube._cian(200)
    assert c.name() == "#ff0000" and c.alpha() == 100


def test_cancelar_vuelve_al_estilo_que_habia(ventana):
    from omnicad.ui.preferencias import DialogoPreferencias
    ventana.prefs["asas/seleccion_color"] = "#aa5500"
    dlg = DialogoPreferencias(ventana.prefs, ventana, "asas")
    dlg.asas_cambiadas.connect(ventana._aplicar_estilo_asas)
    dlg.controles["asas/seleccion_color"].setValue("#00aa55")
    assert ventana.prefs["asas/seleccion_color"] == "#00aa55"
    dlg.reject()
    assert ventana.prefs["asas/seleccion_color"] == "#aa5500"
    assert estilo_asas.rgb("seleccion") == pytest.approx(estilo_asas.hex_a_rgb("#aa5500"))
    ventana.prefs["asas/seleccion_color"] = ""


def test_la_pagina_tiene_cada_grupo_con_lo_que_le_aplica(ventana):
    from omnicad.ui.preferencias import DialogoPreferencias
    dlg = DialogoPreferencias(ventana.prefs, ventana, "asas")
    try:
        for grupo, (_t, _c, tam, op, _d) in estilo_asas.GRUPOS.items():
            assert estilo_asas.clave(grupo, "color") in dlg.controles
            assert (estilo_asas.clave(grupo, "tamano_pct") in dlg.controles) == tam
            assert (estilo_asas.clave(grupo, "opacidad_pct") in dlg.controles) == op
    finally:
        dlg.deleteLater()


def test_la_api_valida_guarda_y_restablece(tmp_path, monkeypatch):
    from omnicad import api
    from omnicad.ejemplo import crear_documento_ejemplo
    monkeypatch.setenv("OMNICAD_AJUSTES_INI", str(tmp_path / "a.ini"))
    sesion = api.Sesion(crear_documento_ejemplo())

    def llamar(nombre, **args):
        return api.llamar(sesion, nombre, args)

    def valores():
        r = llamar("get_preferences", keys=["asas/anillo_color", "asas/flechas_tamano_pct"])
        return [p["value"] for p in r["result"]["preferences"]]

    r = llamar("set_preference", key="asas/anillo_color", value="#FF8800")
    assert r["ok"] and r["result"]["value"] == "#ff8800"
    assert llamar("set_preference", key="asas/flechas_tamano_pct", value=150)["ok"]
    for clave, valor in (("asas/anillo_color", "rojo"), ("asas/flechas_tamano_pct", 49), ("asas/flechas_tamano_pct", 201),
                         ("asas/flechas_opacidad_pct", 5), ("asas/cajas_opacidad_pct", 50)):
        r = llamar("set_preference", key=clave, value=valor)
        assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS", clave
    assert valores() == ["#ff8800", 150]
    r = llamar("reset_overlay_style")
    assert r["ok"] and set(r["result"]["reset"]) == set(estilo_asas.CLAVES)
    assert valores() == ["", 100]
