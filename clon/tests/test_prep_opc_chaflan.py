# -*- coding: utf-8 -*-
"""PREP: test de la opción «Asa de distancia / distancias / ángulo» del comando «Chaflán (3 variantes)» del boceto.
Valida la cantidad de asas (handles) para los tres tipos de chaflán según Fusion docs."""
import pytest
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication

from omnicad.restricciones import Boceto
from omnicad.timeline.parametros import TablaParametros
from omnicad.ui import editor_boceto


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def lienzo(app):
    lz = editor_boceto.Lienzo(Boceto(), TablaParametros().evaluar)
    lz.resize(800, 600)
    lz.ajustar_grilla = False
    lz.show()
    yield lz
    lz.close()
    lz.deleteLater()
    QApplication.processEvents()


def _esquina(lz, herramienta):
    """Prepara la esquina para la herramienta de chaflán: dos líneas perpendiculares."""
    a = lz.b.agregar_linea((0, 0), (30, 0))
    b = lz.b.agregar_linea((0, 0), (0, 30))
    lz.set_herramienta(herramienta)
    lz.agregar_pick(a, (15.0, 0.0), QPointF(0, 0))
    lz.agregar_pick(b, (0.0, 15.0), QPointF(0, 0))
    lz.encuadrar()
    QApplication.processEvents()


# ---------------------------------------------------------------- ASAS DE CHAFLÁN


@pytest.mark.parametrize("herramienta,n_asas", [
    # distancia_igual: 1 asa (solo distancia)
    ("chaflan", 1),
    # dos_distancias: 2 asas (distancia y distancia2)
    ("chaflan_dos_dist", 2),
    # distancia_angulo: 2 asas (distancia y ángulo)
    ("chaflan_dist_angulo", 2),
])
def test_prep_opc_chaflan_cantidad_ases(lienzo, herramienta, n_asas):
    """Testa la cantidad de asas (handles) para los tres tipos de chaflán.
    Según Fusion docs: distancia_equal tiene 1 asa, dos_distances y distancia_angle tienen 2 cada uno."""
    lz = lienzo
    _esquina(lz, herramienta)
    # Verificar cantidad de asas
    assert len(lz._asas.asas) == n_asas, f"Esperaba {n_asas} asas para {herramienta}, got {len(lz._asas.asas)}"
    lz._cerrar_entrada()