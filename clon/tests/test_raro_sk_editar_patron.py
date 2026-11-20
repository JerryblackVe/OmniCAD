# -*- coding: utf-8 -*-
"""Valores raros en cada campo del panel de «Editar patrón» (`sk_editar_patron`).

La ayuda de Fusion (docs/fusion_docs/contenido/fusion-sketch/create-a-{rectangular,circular}-sketch-pattern-*.md)
dice que Cantidad es un entero, Distancia y Centro son longitudes y Ángulo se mide en grados. Acá los campos son
`QLineEdit` que se evalúan con las unidades y expresiones del documento (`ui/panel_patron.py`, `ui/patron_boceto.py`).
Este archivo fija que ningún valor raro cierre la app, deje el boceto roto ni produzca un mensaje de más de un
renglón. Los dos casos que sí fallan quedan xfail con su ID de seguimiento.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui import editor_boceto  # noqa: E402

VACIO = ""
CERO = "0"
NEGATIVO = "-5"
ENORME = "1e9"
UNIDADES = ("30 mm", "90 deg")
EXPRESIONES = ("10+20", "ang")
RAROS = (VACIO, CERO, NEGATIVO, ENORME, *UNIDADES, *EXPRESIONES)

CAMPOS = (
    ("rectangular", "cantidad1"), ("rectangular", "distancia1"), ("rectangular", "angulo1"),
    ("rectangular", "cantidad2"), ("rectangular", "distancia2"), ("rectangular", "angulo2"),
    ("circular", "cantidad"), ("circular", "angulo_total"), ("circular", "centro_x"), ("circular", "centro_y"),
)


@pytest.fixture
def lz():
    app = QApplication.instance() or QApplication([])
    lienzo = editor_boceto.Lienzo(Boceto(), TablaParametros().evaluar)
    lienzo.resize(900, 500)
    lienzo.ajustar_grilla = False
    lienzo.centro, lienzo.escala = [30.0, 0.0], 8.0
    lienzo.show()
    yield lienzo
    lienzo.close()
    lienzo.deleteLater()
    app.processEvents()


def _abrir(lz, tipo):
    """Crea un patrón de 6 ejemplares y abre su panel, como el doble clic en el glifo."""
    original = lz.b.agregar_circulo((20, 0), 2)
    if tipo == "rectangular":
        lz.b.patron_rectangular([original], 3, 20, 2, 10, modo="espaciado")
    else:
        lz.b.patron_circular([original], (0.0, 0.0), 6, 180.0)
    lz.resolver()
    assert lz.editar_patron(lz.b.patrones[0]["id"])
    return lz.b.patrones[0]["id"]


def _probar(lz, tipo, campo, valor, aplicar=False):
    """Escribe `valor`, comprueba los invariantes y cancela; devuelve el estado del panel."""
    pid = _abrir(lz, tipo)
    n_curvas, n_patrones = len(lz.b.curvas), len(lz.b.patrones)
    mensajes = []
    slot = mensajes.append
    lz.mensaje.connect(slot)
    try:
        textos = dict(lz.patron.textos)
        textos[campo] = valor
        lz.patron.recibir(textos)
        estado = lz.patron.estado()
        assert isinstance(estado["error"], str) and "\n" not in estado["error"], estado
        assert isinstance(estado["guia"], str) and "\n" not in estado["guia"], estado
        assert lz.patron.tipo == tipo, "el panel se cerró solo"
        if not estado["valido"]:
            lz.patron.enter()
        assert all("\n" not in m for m in mensajes), mensajes
        if aplicar and estado["valido"]:
            assert lz.patron.aceptar()
            assert len(lz.b.patrones) == n_patrones
            assert len(lz.b.curvas) == n_curvas
            lz.resolver()
        else:
            lz.patron.cancelar()
    finally:
        try:
            lz.mensaje.disconnect(slot)
        except (RuntimeError, TypeError):
            pass
    assert len(lz.b.curvas) == n_curvas
    assert len(lz.b.patrones) == n_patrones
    assert lz.b.patrones[0]["id"] == pid
    return estado


@pytest.mark.parametrize("tipo, campo", CAMPOS)
@pytest.mark.parametrize("valor", RAROS)
def test_cada_campo_con_valor_raro_no_rompe_ni_deja_el_boceto_roto(lz, tipo, campo, valor):
    """Vacío, cero, negativo, enorme, con unidades y con expresión: siempre mensaje de 1 renglón y el boceto vuelve."""
    _probar(lz, tipo, campo, valor)


@pytest.mark.parametrize("campo, valor", (
    ("distancia1", NEGATIVO), ("distancia1", "30 mm"), ("distancia1", "10+20"),
    ("angulo1", NEGATIVO), ("angulo1", "45 deg"), ("angulo1", "10+20"),
    ("cantidad", "3*2"), ("angulo_total", "90 deg"), ("centro_x", "30 mm"), ("centro_y", NEGATIVO),
))
def test_un_valor_raro_valido_se_puede_aplicar_sin_romper_el_boceto(lz, campo, valor):
    """Los valores raros que sí son válidos se aceptan y el patrón se regenera con el mismo número de copias."""
    tipo = "circular" if campo in ("cantidad", "angulo_total", "centro_x", "centro_y") else "rectangular"
    estado = _probar(lz, tipo, campo, valor, aplicar=True)
    assert estado["valido"]


@pytest.mark.parametrize("campo", ("cantidad1", "cantidad2", "cantidad"))
@pytest.mark.parametrize("valor", UNIDADES)
def test_la_cantidad_debe_rechazar_unidades_ajenas(lz, campo, valor):
    """Fusion: Quantity es un entero sin unidad. «30 mm» no puede crear 30 copias."""
    tipo = "circular" if campo == "cantidad" else "rectangular"
    estado = _probar(lz, tipo, campo, valor)
    assert not estado["valido"]
    assert campo in estado["malos"]
    assert estado["error"] and "\n" not in estado["error"]


@pytest.mark.parametrize("valor", ("ang", "2*", "90 deg"))
def test_el_centro_con_valor_no_evaluable_debe_marcarse_y_no_aplicarse(lz, valor):
    """Un nombre desconocido, una expresión rota o una unidad de ángulo no pueden ignorarse en silencio."""
    estado = _probar(lz, "circular", "centro_x", valor)
    assert not estado["valido"]
    assert "centro_x" in estado["malos"]
    assert estado["error"] and "\n" not in estado["error"]
