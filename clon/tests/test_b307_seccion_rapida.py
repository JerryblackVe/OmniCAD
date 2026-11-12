# -*- coding: utf-8 -*-
"""B-307: el Análisis de sección colgaba la ventana 12–14 s en cada cambio de desfase con una rosca modelada (el corte
exacto del filete en el kernel). La tapa y el contorno que se dibujan salen ahora de la malla de visualización."""
import math
import time

import numpy as np
import pytest

from omnicad import api
from omnicad.timeline import analisis_vista as av


def _llamar(sesion, nombre, **argumentos):
    r = api.llamar(sesion, nombre, argumentos)
    assert r["ok"], r
    return r["result"]


def _area_tapa(datos):
    tris = np.concatenate([t[1] for t in datos["capas"] if t[0] == "tris"]).reshape(-1, 3, 3)
    return float(np.linalg.norm(np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]), axis=1).sum() / 2)


def _seccion(s, plano, desfase):
    return av.calcular("seccion", {"plano": {"tipo": "plano", "id": plano}, "desfase_mm": desfase, "rayado": True},
                       s.doc.estado_final, s.doc.propiedades)


def test_la_tapa_de_una_caja_agujereada_tiene_el_area_y_el_hueco():
    s = api.Sesion()
    _llamar(s, "create_box", length=40, width=40, height=20, name="Caja")
    _llamar(s, "create_cylinder", height=20, radius=5, operation="cut", target="Caja")
    datos = _seccion(s, "XY", 10)
    assert _area_tapa(datos) == pytest.approx(40 * 40 - math.pi * 25, rel=2e-3)
    assert sum(t[0] == "lineas" for t in datos["capas"]) == 2          # contorno y rayado


def test_la_seccion_de_una_rosca_modelada_sale_en_menos_de_tres_segundos():
    s = api.Sesion()
    _llamar(s, "create_cylinder", height=20, radius=4, name="Eje")
    _llamar(s, "create_thread", faces="%CYLINDER", body="Eje", thread="M8", modeled=True)
    inicio = time.perf_counter()
    datos = _seccion(s, "YZ", 0)              # por el eje: antes 12–32 s en BRepAlgoAPI_Section
    assert time.perf_counter() - inicio < 3
    assert _area_tapa(datos) == pytest.approx(142.909, rel=5e-3)        # el corte exacto (an.seccion) da 142,909 mm²


def test_en_la_ventana_cada_cambio_de_desfase_responde_rapido(tmp_path):
    """Como Gerardo: abre Análisis de sección sobre el eje roscado y teclea varias distancias (antes 12–14 s cada una)."""
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication

    from omnicad.ui.comando import hits
    from omnicad.ui.comandos.inspeccionar import Seccion
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    s = api.Sesion()
    _llamar(s, "create_cylinder", height=20, radius=4, name="Eje")
    _llamar(s, "create_thread", faces="%CYLINDER", body="Eje", thread="M8", modeled=True)
    app = QApplication.instance() or QApplication([])
    v = VentanaPrincipal(s.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.show()
    try:
        p = v.ejecutar_comando(Seccion(), valores={"plano": hits([{"tipo": "plano", "id": "YZ"}], s.doc.estado_final)})
        for texto in ("0 mm", "0,5 mm", "1.5", "-2 mm"):
            p.set_valor("desfase", texto)
            p._t_previa.stop()
            inicio = time.perf_counter()
            p._calcular_previa()
            assert time.perf_counter() - inicio < 3, texto
            assert any(t[0] == "tris" for t in v.visor._capas.get("analisis", [])), texto       # la tapa se ve
        p.cancelar()
    finally:
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()
