# -*- coding: utf-8 -*-
"""PREP: opción «Familia tipográfica y Filtro de fuentes» del panel Carácter del boceto.

La ayuda de Fusion («Reference: Text dialog», docs/fusion_docs/contenido/fusion-sketch/
reference-text-dialog-852d1147165.md) describe Font como una lista desplegable y Height como unidades del
diseño; Character Spacing es un porcentaje del espaciado que trae la fuente (0 % = el de la fuente).
Acá se fija que elegir familia recalcula ese espaciado en mm con una altura numérica de 10 mm, y el borde
de que el filtro deje afuera la familia en uso: no debe hacerla desaparecer de la lista.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad.nucleo import fuentes  # noqa: E402
from omnicad.ui import modo_boceto  # noqa: E402


@pytest.fixture
def panel():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    p = modo_boceto.PanelCaracter()
    yield p
    p.deleteLater()
    app.processEvents()


def test_elegir_familia_recalcula_el_espaciado_en_mm_con_altura_10(panel):
    """Con Height = 10 mm y 100 % de interletraje, cambiar de familia emite su nombre y los mm que le tocan."""
    cambios = []
    panel.cambio.connect(lambda k, v: cambios.append((k, v)))
    panel.cargar({"fuente": panel.fuente.itemText(0), "altura_texto": 10.0})
    panel.interletraje.setValue(100.0)
    cambios.clear()

    idx = 1
    familia = panel.fuente.itemText(idx)
    panel.fuente.setCurrentIndex(idx)

    assert [k for k, _ in cambios] == ["fuente", "espaciado"]
    assert cambios[0] == ("fuente", familia)
    negrita, cursiva = modo_boceto._ESTILO_BC[panel.estilo.currentData()]
    esperado = fuentes.espaciado_cien(familia, 10.0, negrita, cursiva)
    assert cambios[1][1] == pytest.approx(esperado)
    assert 0.0 < esperado < 10.0                              # un avance por letra, no una altura ni cero


def test_filtro_que_excluye_la_familia_en_uso_la_mantiene_en_la_lista(panel):
    """Borde: si el filtro no incluye la fuente elegida, se agrega igual al principio y no cambia la selección."""
    todas = set(modo_boceto._fuentes())
    elegido = None
    for filtro, _ in modo_boceto.FILTROS_FUENTE[1:]:
        permitidas = set(modo_boceto.familias_filtradas(filtro))
        if permitidas and permitidas < todas:
            elegido = (filtro, next(n for n in modo_boceto._fuentes() if n not in permitidas))
            break
    if elegido is None:
        pytest.skip("en este equipo ningún filtro excluye familias")

    filtro, familia = elegido
    cambios = []
    panel.cambio.connect(lambda k, v: cambios.append((k, v)))
    panel.cargar({"fuente": familia, "altura_texto": 10.0})
    assert panel.fuente.currentText() == familia
    cambios.clear()

    panel.filtro.setCurrentIndex(panel.filtro.findData(filtro))

    visibles = [panel.fuente.itemText(i) for i in range(panel.fuente.count())]
    assert visibles[0] == familia                              # la en uso queda, aunque el filtro la excluya
    assert set(visibles) == permitidas | {familia}
    assert panel.fuente.currentText() == familia               # no se dispara un cambio de fuente
    assert cambios == []
