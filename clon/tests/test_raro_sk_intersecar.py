# -*- coding: utf-8 -*-
"""Valores raros en cada campo del diálogo «Intersecar» (`sk_intersecar`): Filtro (Selection Filter),
Geometría (lo que corta el plano) y Vínculo de proyección (Projection Link, propio de OmniCAD). La ayuda de
Fusion (`docs/fusion_docs`: `reference-intersect-dialog` e `intersect-geometry`) fija que el diálogo solo pide
la geometría a intersecar y el filtro: no hay números libres, unidades ni expresiones. Igual se les mete vacío,
0, negativo, enorme, con unidades y con expresión; nada puede cerrar la app, dejar el boceto roto ni soltar un
mensaje de más de un renglón."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.nucleo import geometria as geo  # noqa: E402
from omnicad.restricciones import Boceto, resolver  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui import editor_boceto, modo_boceto  # noqa: E402

CAMPOS = ("filtro_proyectar", "geometria", "vinculo_proyeccion")
VALORES = [pytest.param("", id="vacio"), pytest.param(0, id="cero"), pytest.param(-5, id="negativo"),
           pytest.param(10**9, id="enorme"), pytest.param("20 mm", id="unidades"),
           pytest.param("1+1", id="expresion")]
LIMITE = 120


@pytest.fixture
def lienzo():
    app = QApplication.instance() or QApplication([])
    lz = editor_boceto.Lienzo(Boceto(), TablaParametros().evaluar, plano=geo.Plano("XY"))
    lz.resize(800, 600)
    lz.ajustar_grilla = False
    lz.show()
    lz.set_herramienta("intersecar")
    mensajes = []
    lz.mensaje.connect(mensajes.append)
    yield lz, mensajes
    lz.close()
    lz.deleteLater()
    app.processEvents()


def _elegir_cilindro(lz):
    """Selección válida: un cilindro R5 que corta el plano XY en una circunferencia."""
    lz._elegidos_proy = [{"tipo": "forma", "forma": geo.cilindro(5, 10, (0, 0, -5))}]


def _inyectar(lz, campo, valor):
    if campo == "geometria":
        lz._elegidos_proy = [] if valor == "" else [valor]
    else:
        lz.opciones[campo] = valor


def _sin_rotura(lz, mensajes, antes, fallos, acepto):
    """Ninguna excepción, app y lienzo abiertos, boceto resoluble y avisos de un renglón."""
    assert QApplication.instance() is not None and lz.isVisible()
    assert not fallos, fallos
    assert resolver(lz.b).ok
    for texto in mensajes:
        assert "\n" not in texto and "\r" not in texto and len(texto) <= LIMITE, texto
    if not acepto:                          # rechazado: no tocó el boceto
        assert lz.b.a_dict() == antes, "el valor raro cambió el boceto sin Aceptar"


def test_el_dialogo_tiene_solo_esos_tres_campos():
    """Si Intersecar gana un campo nuevo, este barrido tiene que cubrirlo también."""
    assert {clave for clave, _et, _ops in modo_boceto.OPCIONES_HERRAMIENTA["intersecar"]} == {"filtro_proyectar"}
    assert {clave for clave, _et in modo_boceto.CASILLAS_HERRAMIENTA["intersecar"]} == {"vinculo_proyeccion"}
    assert "intersecar" not in modo_boceto.NUMEROS_HERRAMIENTA
    assert "intersecar" not in modo_boceto.ENTEROS_HERRAMIENTA


@pytest.mark.parametrize("campo", CAMPOS)
@pytest.mark.parametrize("valor", VALORES)
def test_campo_raro_no_cierra_app_ni_deja_boceto_roto(lienzo, campo, valor):
    lz, mensajes = lienzo
    _elegir_cilindro(lz)
    antes = lz.b.a_dict()
    fallos = []
    _inyectar(lz, campo, valor)
    acepto = False
    try:
        lz.cambiar_opcion_proyeccion()      # recalcula la tarjeta al cambiar el filtro o el vínculo
        lz._emitir_proyeccion()             # lo mismo que al elegir geometría
        acepto = lz.aceptar_proyeccion()    # y lo que pasa si la persona aprieta Aceptar
        QApplication.processEvents()
    except Exception as exc:                # noqa: BLE001 — cualquier excepción aquí tumbaría la app
        fallos.append(f"{type(exc).__name__}: {exc}")
    _sin_rotura(lz, mensajes, antes, fallos, acepto)


def test_valores_validos_si_cortan_el_cilindro(lienzo):
    """Control: con los valores normales, Intersecar sí dibuja la circunferencia del corte."""
    lz, _ = lienzo
    _elegir_cilindro(lz)
    estado = lz.estado_proyeccion()
    assert estado["valido"] and [p[0] for p in estado["prims"]] == ["circulo"]
    assert lz.aceptar_proyeccion()
    (curva,) = [c for c in lz.b.curvas.values() if c.id > 0]
    assert lz.b.radio(curva.id) == pytest.approx(5)
