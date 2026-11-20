# -*- coding: utf-8 -*-
"""B-753/B-754/B-755: extruir un perfil dibujado sobre la cara de un cuerpo (Fusion): abre en «Unir» con la distancia en 0,
no avisa «compartiendo solo una cara» (también lejos del origen, donde la malla float32 se corre ~1e-6) y oculta el boceto."""
import time

import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.timeline.operaciones import OpExtrusion
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos.solido import Extruir
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


def llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


@pytest.fixture(params=[(20, 20, 10), (412.7, 233.3, 187.9)], ids=["chica", "lejos_del_origen"])
def panel(request, tmp_path):
    """Panel de Extruir sobre un círculo dibujado en la cara de arriba de una caja."""
    app = QApplication.instance() or QApplication([])
    s = api.Sesion()
    largo, ancho, alto = request.param
    llamar(s, "create_box", length=largo, width=ancho, height=alto, anchor="corner")
    cara = next(c["id"] for c in llamar(s, "find_faces", body="Cuerpo1")["faces"] if c["normal"] == [0.0, 0.0, 1.0])
    llamar(s, "create_sketch", name="S", plane=cara)
    llamar(s, "draw_circle", sketch="S", center_x=7.3, center_y=6.1, radius=3.2)
    perfil = s.doc.operaciones[-1].id
    v = VentanaPrincipal(s.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.show()
    p = v.ejecutar_comando(Extruir())
    br = s.doc.estado_final.bocetos[perfil]
    p._elegida(hit_desde_ref({"tipo": "perfil", "boceto": perfil, **OpExtrusion.referencia_perfil(br.perfiles[0])},
                             p.ctx.estado))
    yield s, v, p, perfil
    if v.panel is not None:
        v.panel.cancelar()
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app.processEvents()


def esperar(p, segundos=6):
    """Corre las previas (también la exacta que llega de un proceso aparte) hasta que no queda ninguna."""
    fin = time.time() + segundos
    while time.time() < fin:
        QApplication.processEvents()
        if p._t_previa.isActive():
            p._t_previa.stop()
            p._calcular_previa()
        elif p._hijo_previa is None and p.comando._hijo is None:
            break


def teclear(p, texto):
    campo = p.widgets["distancia"]
    QTest.mouseClick(campo, Qt.LeftButton)
    QTest.keyClick(campo, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClicks(campo, texto)
    QTest.keyClick(campo, Qt.Key_Tab)
    esperar(p)


def test_abre_en_unir_con_distancia_cero(panel):
    _, _, p, _ = panel
    assert p.valores["operacion"] == "unir" and p.widgets["operacion"].currentText() == "Unir"      # B-753
    teclear(p, "0")                         # valor raro: sigue en Unir y pide una distancia
    assert p.valores["operacion"] == "unir" and p.ultima_op is None


def test_a_mano_la_operacion_queda_fija(panel):
    _, _, p, _ = panel
    p.set_valor("operacion", "nuevo")
    p.comando._fija = True
    teclear(p, "5")
    assert p.valores["operacion"] == "nuevo"


def test_aceptar_une_sin_aviso_y_oculta_el_boceto(panel):
    s, v, p, perfil = panel
    teclear(p, "5")
    assert p.mensaje.text() == "" and p.valores["operacion"] == "unir"          # B-754: sin «solo una cara»
    QTest.mouseClick(p.boton_ok, Qt.LeftButton)
    fin = time.time() + 6
    while v.panel is not None and time.time() < fin:
        QApplication.processEvents()
    assert v.panel is None
    ultimo = llamar(s, "get_timeline", include_params=False)["steps"][-1]
    assert ultimo["status"] != "warning", ultimo
    assert len(s.doc.estado_final.cuerpos) == 1
    assert perfil in v.ocultos and perfil in v.doc.propiedades["__navegador__"]["ocultos"]    # B-755


def test_deshacer_la_extrusion_vuelve_a_mostrar_el_boceto(panel):
    """B-755: Ctrl+Z saca la extrusión y el boceto que había ocultado vuelve a verse; Ctrl+Y lo oculta otra vez. La cara de un
    cuerpo elegida como perfil (sin boceto) sigue abriendo en «Cuerpo nuevo» con 0 mm: test_b338_… en test_cuerpos_partidos."""
    s, v, p, perfil = panel
    teclear(p, "5")
    QTest.mouseClick(p.boton_ok, Qt.LeftButton)
    fin = time.time() + 6
    while v.panel is not None and time.time() < fin:
        QApplication.processEvents()
    assert perfil in v.ocultos
    pasos = len(s.doc.operaciones)
    v._deshacer()
    assert len(s.doc.operaciones) == pasos - 1 and perfil not in v.ocultos
    assert perfil not in (v.doc.propiedades.get("__navegador__") or {}).get("ocultos", [])
    v._rehacer()
    assert len(s.doc.operaciones) == pasos and perfil in v.ocultos
