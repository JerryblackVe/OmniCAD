# -*- coding: utf-8 -*-
"""Valores raros del comando de boceto «sk_incluir_3d» (Include 3D Geometry de Fusion).

La ayuda de Fusion (`docs/fusion_docs/.../include-3d-geometry-*.md`) solo pide elegir caras, aristas y puntos:
la tarjeta de Incluir geometría 3D no tiene campos numéricos donde tipear. Los campos del comando son los de
`include_3d_geometry` —edges, faces, vertices, body, sketch, construction y link—, mapeados desde la clave UI en
`test_cobertura_ui_api.py`. Acá se prueban todos en vacío, 0, negativo, enorme, con unidades y con expresión:
ninguno cierra la app, deja el boceto roto ni contesta con un mensaje de más de un renglón.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad import api  # noqa: E402

RAROS = ("", "0", "-5", "1e9", "10 mm", "2*3")
CAMPOS_TEXTO = ("edges", "faces", "body", "sketch")
CAMPOS_BOOL = ("construction", "link")


def _llamar(sesion, nombre, **args):
    """`api.llamar` nunca lanza: si algo revienta adentro, el test lo ve como `ok=False` inesperado."""
    r = api.llamar(sesion, nombre, args)
    assert isinstance(r, dict) and isinstance(r.get("ok"), bool), r
    return r


@pytest.fixture(scope="module")
def app_qt():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def sesion(app_qt):
    """Caja de 40×40×10 con un boceto «B», como el modelo de `test_faltantes_bocetos.py`."""
    assert app_qt is not None
    s = api.Sesion()
    assert _llamar(s, "create_box", length=40, width=40, height=10)["ok"]
    assert _llamar(s, "create_sketch", plane="XY", name="B")["ok"]
    return s


def _sin_rotura(sesion, r, antes):
    """La app sigue viva y el boceto legible; lo rechazado no lo toca y avisa en un solo renglón."""
    assert QApplication.instance() is not None, "la app se cerró"
    despues = _llamar(sesion, "get_sketch", sketch="B")
    assert despues["ok"], "el boceto quedó roto"
    if not r["ok"]:
        assert despues["result"] == antes, "un valor rechazado cambió el boceto"
        assert isinstance(r.get("mensaje"), str) and r["mensaje"], r
        assert "\n" not in r["mensaje"] and "\r" not in r["mensaje"], r["mensaje"]


# ---------------------------------------------------------------- CAMPOS DE SELECCIÓN Y DE NOMBRE
@pytest.mark.parametrize("campo", CAMPOS_TEXTO)
@pytest.mark.parametrize("valor", RAROS)
def test_cada_campo_de_texto_con_valor_raro(sesion, campo, valor):
    """Vacío, 0, negativo, enorme, unidades y expresión: se rechazan (o se toman por defecto) sin romper nada."""
    antes = _llamar(sesion, "get_sketch", sketch="B")["result"]
    args = {"faces": [">Z"]} if campo in ("body", "sketch") else {}
    r = _llamar(sesion, "include_3d_geometry", **{**args, campo: valor})
    _sin_rotura(sesion, r, antes)
    if campo in ("body", "sketch"):
        # Los nombres vacíos significan «el único cuerpo» / «el último boceto» (docstring de la herramienta).
        assert r["ok"] if valor == "" else not r["ok"], r
        if not r["ok"]:
            assert r["error_kind"] == ("BODY_NOT_FOUND" if campo == "body" else "SKETCH_NOT_FOUND"), r
    else:
        assert not r["ok"] and r["error_kind"] == "INVALID_SELECTOR", r


# ---------------------------------------------------------------- VÉRTICES
@pytest.mark.parametrize("vertices", [
    [], [[0, 0, 0]], [[-5, -5, -5]], [[1e9, 1e9, 1e9]],
    [["10 mm", 0, 0]], [["2*3", 0, 0]],
])
def test_vertices_con_valor_raro(sesion, vertices):
    """Coordenadas raras: cero y negativo no son vértices, 1 km sale del rango, unidades y expresión no son números."""
    antes = _llamar(sesion, "get_sketch", sketch="B")["result"]
    r = _llamar(sesion, "include_3d_geometry", vertices=vertices)
    _sin_rotura(sesion, r, antes)
    assert not r["ok"], r


# ---------------------------------------------------------------- BOOLEANOS
@pytest.mark.parametrize("campo", CAMPOS_BOOL)
@pytest.mark.parametrize("valor", RAROS)
def test_campos_booleanos_con_valor_raro(sesion, campo, valor):
    """`construction` y `link` son booleanos: un texto, aunque sea una expresión válida, se rechaza nombrando el campo."""
    antes = _llamar(sesion, "get_sketch", sketch="B")["result"]
    r = _llamar(sesion, "include_3d_geometry", faces=[">Z"], **{campo: valor})
    _sin_rotura(sesion, r, antes)
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS", r
    assert campo in r["mensaje"] and "boolean" in r["mensaje"], r


# ---------------------------------------------------------------- CASOS VÁLIDOS "RAROS"
def test_un_valor_por_defecto_vacio_y_booleanos_validos_siguen_incluyendo(sesion):
    """El nombre vacío es «automático» y los booleanos correctos incluyen el borde sin tocar otros campos."""
    antes = _llamar(sesion, "get_sketch", sketch="B")["result"]
    r = _llamar(sesion, "include_3d_geometry", faces=[">Z"], body="", sketch="", construction=True, link=False)
    assert r["ok"] and len(r["result"]["entities"]) == 4, r
    assert QApplication.instance() is not None
    assert _llamar(sesion, "get_sketch", sketch="B")["result"] != antes
