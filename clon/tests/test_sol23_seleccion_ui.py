# -*- coding: utf-8 -*-
"""SOL-23 en la ventana: Seleccionar por límite, Semilla y límite y conjuntos de selección, como los usa una persona."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QInputDialog  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.api import selectores as sl  # noqa: E402
from omnicad.timeline.documento import Documento  # noqa: E402
from omnicad.timeline.operaciones import OpPrimitiva  # noqa: E402


@pytest.fixture(scope="module")
def ventana(tmp_path_factory):
    app = QApplication.instance() or QApplication([])
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    ruta = tmp_path_factory.mktemp("prefs") / "preferencias.ini"
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(ruta), QSettings.IniFormat)))
    v.resize(1280, 800)
    v.show()
    QTest.qWait(1)
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    QTest.qWait(1)
    assert app


@pytest.fixture
def v(ventana):
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="10", largo="10", alto="10"))
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="10", largo="10", alto="10", x="100"))
    ventana.set_documento(doc)
    return ventana


def _respuestas(monkeypatch, items, numeros):
    """Hace de persona: contesta los diálogos de entrada en orden."""
    items, numeros = list(items), list(numeros)
    monkeypatch.setattr(QInputDialog, "getItem", lambda *_a, **_k: (items.pop(0), True))
    monkeypatch.setattr(QInputDialog, "getDouble", lambda *_a, **_k: (numeros.pop(0), True))


def test_seleccion_por_limite_con_esfera_elige_el_cuerpo_cercano(v, monkeypatch):
    v._seleccionar(v._hits_cuerpos(["op1.c1"]))                       # el cuerpo del centro
    _respuestas(monkeypatch, ["Esfera", "Dentro del límite", "Cuerpos"], [30])
    v.acciones["seleccion_limite"].trigger()
    assert [h["ref"]["cuerpo"] for h in v.seleccion] == ["op1.c1"]
    v._seleccionar(v._hits_cuerpos(["op1.c1"]))
    _respuestas(monkeypatch, ["Esfera", "Fuera del límite", "Cuerpos"], [30])
    v.acciones["seleccion_limite"].trigger()
    assert [h["ref"]["cuerpo"] for h in v.seleccion] == ["op2.c1"]


def test_seleccion_por_limite_sin_cuerpo_elegido_avisa_y_no_cambia_nada(v):
    v._seleccionar([])
    v.acciones["seleccion_limite"].trigger()                          # no hay diálogo: solo el mensaje
    assert v.seleccion == []


def test_semilla_y_limite_elige_lateral_y_fondo(v):
    ses = api.Sesion(v.doc)
    lateral = [e for c, e in sl.elegir(ses, "|X or #Z", "cara", "op1.c1")]
    tapa = sl.elegir(ses, ">Z", "cara", "op1.c1")[0][1]
    refs = [sl.referencia(sl.cuerpo_objetivo(ses, "op1.c1"), tapa), sl.referencia(sl.cuerpo_objetivo(ses, "op1.c1"), lateral[0])]
    v.seleccionar_entidades(refs)                                     # límite = tapa, semilla = una lateral
    v.acciones["seleccion_semilla"].trigger()
    assert len(v.seleccion) == 5                                      # las 5 caras de la caja menos la tapa


def test_conjuntos_de_seleccion_guardar_y_volver_a_elegir(v, monkeypatch):
    v._seleccionar(v._hits_cuerpos(["op2.c1"]))
    monkeypatch.setattr(QInputDialog, "getText", lambda *_a, **_k: ("Lejano", True))
    v.acciones["conjunto_seleccion"].trigger()
    assert "Lejano" in v.doc.espacios["conjuntos_seleccion"]
    v._seleccionar([])
    monkeypatch.setattr(QInputDialog, "getItem", lambda *_a, **_k: ("Lejano", True))
    v.acciones["elegir_conjunto"].trigger()
    assert [h["ref"]["cuerpo"] for h in v.seleccion] == ["op2.c1"]
    v._seleccionar([])
    v.acciones["conjunto_seleccion"].trigger()                        # sin selección: avisa, no crea nada
    assert list(v.doc.espacios["conjuntos_seleccion"]) == ["Lejano"]


def test_sol36_el_navegador_lista_los_conjuntos_y_los_elige_y_actualiza(v, monkeypatch):
    v._seleccionar(v._hits_cuerpos(["op2.c1"]))
    monkeypatch.setattr(QInputDialog, "getText", lambda *_a, **_k: ("Lejano", True))
    v.acciones["conjunto_seleccion"].trigger()
    fila = v.navegador.item("sel:Lejano")
    assert fila is not None and fila.parent().text(0) == "Conjuntos de selección"
    v._seleccionar([])
    v.navegador._clic(fila, 0)                                        # clic = Elegir
    assert [h["ref"]["cuerpo"] for h in v.seleccion] == ["op2.c1"]
    v._seleccionar(v._hits_cuerpos(["op1.c1"]))
    v._accion_navegador("actualizar_conjunto", "sel:Lejano")          # menú › Actualizar con la selección
    assert [r["cuerpo"] for r in v.doc.espacios["conjuntos_seleccion"]["Lejano"]] == ["op1.c1"]
