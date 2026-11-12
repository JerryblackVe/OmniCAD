# -*- coding: utf-8 -*-
"""B-311: el Análisis de sección cortaba y rayaba los cuerpos ocultos en el navegador (Fusion solo corta lo visible)."""
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.timeline import analisis_vista as av
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


def _llamar(sesion, nombre, **argumentos):
    r = api.llamar(sesion, nombre, argumentos)
    assert r["ok"], r
    return r["result"]


@pytest.fixture
def sesion():
    s = api.Sesion()
    _llamar(s, "create_box", length=10, width=10, height=10, name="A")
    _llamar(s, "create_box", length=10, width=10, height=10, x=30, name="B")
    _llamar(s, "section_view", plane="XY", offset=5, name="Corte", hatch=True)
    return s


def _tapas(datos):
    """Las x de las tapas del corte dibujadas (una por cuerpo cortado)."""
    return sorted(round(float(t[1][:, 0].mean())) for t in datos["capas"] if t[0] == "tris")


def test_la_seccion_no_corta_un_cuerpo_oculto(sesion):
    doc = sesion.doc
    a = doc.analisis["Corte"]
    assert _tapas(av.calcular(a["tipo"], a["params"], doc.estado_final, doc.propiedades)) == [0, 30]
    b = next(c.id for c in doc.estado_final.cuerpos.values() if c.nombre == "B")
    doc.propiedades["__navegador__"] = {"ocultos": [b]}      # como lo guarda la ventana (la pieza de Gerardo)
    assert _tapas(av.calcular(a["tipo"], a["params"], doc.estado_final, doc.propiedades)) == [0]


def test_en_la_ventana_el_ojo_tachado_saca_el_cuerpo_del_corte(sesion, tmp_path):
    app = QApplication.instance() or QApplication([])
    v = VentanaPrincipal(sesion.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.show()
    try:
        capas = lambda: _tapas({"capas": v.visor._capas.get("analisis", [])})      # noqa: E731
        assert capas() == [0, 30]
        b = next(c.id for c in v.doc.estado_final.cuerpos.values() if c.nombre == "B")
        v._ojo(b)                                    # clic en el ojo del cuerpo en el navegador
        assert capas() == [0]
        v._ojo(b)
        assert capas() == [0, 30]
        v._ojo("__cuerpos__")                        # la carpeta Cuerpos entera oculta
        assert capas() == []
    finally:
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()
