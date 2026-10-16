# -*- coding: utf-8 -*-
"""PL4 (Plasticity › «Fillet Order of Operations»): el error de empalme enseña el orden correcto
(de lo grande a lo chico) y move_feature deja reordenar los pasos para seguir la pista."""
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo.solidos_modificar import empalme
from omnicad.timeline.operaciones import OpPrimitiva


def _caja(doc):
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="40", largo="40", alto="20"))
    return doc.estado_final.cuerpos["c1"].forma


def test_el_empalme_imposible_ensenia_el_orden_de_lo_grande_a_lo_chico():
    from omnicad.nucleo import referencias as refs
    caja = geo.caja(40, 40, 20)
    aristas = refs.subformas(caja, "arista")[:4]
    with pytest.raises(geo.ErrorGeometria) as e:
        empalme(caja, [{"aristas": aristas, "tipo": "constante", "radio": 500.0}])
    assert "radio MAYOR" in str(e.value) and "de lo grande a lo chico" in str(e.value)
    assert "reordená los empalmes" in str(e.value)


def test_la_pista_llega_por_la_api_y_move_feature_reordena():
    sesion = api.Sesion()
    doc = sesion.doc
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="40", largo="40", alto="20"))
    r = api.llamar(sesion, "fillet", {"edges": "|Z", "radius": 500})
    assert not r["ok"] and "de lo grande a lo chico" in r["mensaje"]

    # move_feature (la herramienta nueva que hace la pista accionable): el primitivo pasa al final.
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="esfera", radio="5"))
    r = api.llamar(sesion, "move_feature", {"feature": "op1", "index": 1})
    assert r["ok"] and r["result"]["before"] == 0 and r["result"]["now"] == 1
    assert doc.operaciones[0].TIPO == "primitiva" and "op1" != doc.operaciones[0].id
    r = api.llamar(sesion, "move_feature", {"feature": "no-hay", "index": 0})
    assert not r["ok"] and r["error_kind"] == "FEATURE_NOT_FOUND"


# ---------------------------------------------------------------- PL2: teclas a la vista
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="module")
def ventana(tmp_path_factory):
    QApplication.instance() or QApplication([])
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    ruta = tmp_path_factory.mktemp("prefs") / "preferencias.ini"
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(ruta), QSettings.IniFormat)))
    v.show()
    QTest.qWait(50)
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    QTest.qWait(10)


def test_shift_r_repite_el_ultimo_comando(ventana, monkeypatch):
    from omnicad.ui.comandos import CATALOGO
    assert ventana.acciones["repetir"].shortcut().toString().endswith("R")
    ventana._ultimo_comando = CATALOGO["caja"]
    llamados = []
    monkeypatch.setattr(ventana, "ejecutar_comando", lambda comando: llamados.append(comando))
    ventana.repetir_ultimo()
    assert len(llamados) == 1 and isinstance(llamados[0], CATALOGO["caja"])
    ventana._ultimo_comando = None
    ventana.repetir_ultimo()                       # sin último comando no hace nada ni revienta
    assert len(llamados) == 1


def test_el_panel_del_comando_muestra_las_teclas_al_pie(ventana, monkeypatch):
    from omnicad.ui.comandos import CATALOGO
    panel = ventana.ejecutar_comando(CATALOGO["caja"]())
    assert panel is not None
    QTest.qWait(20)
    texto = panel.pie_teclas.text()
    assert "Enter: aceptar" in texto and "Esc: cancelar" in texto
    # un comando con teclas propias las muestra primero
    monkeypatch.setattr(CATALOGO["caja"], "MODIFICADORES", {"Mayús": "centrado"})
    panel2 = ventana.ejecutar_comando(CATALOGO["caja"]())
    QTest.qWait(20)
    assert "Mayús: centrado" in panel2.pie_teclas.text()
    panel2.cancelar()
    monkeypatch.setattr(CATALOGO["caja"], "MODIFICADORES", {})   # panel 1 ya lo cerró ejecutar_comando
