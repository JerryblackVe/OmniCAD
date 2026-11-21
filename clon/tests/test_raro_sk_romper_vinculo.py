# -*- coding: utf-8 -*-
"""Valores raros del comando de boceto «sk_romper_vinculo» (Fusion: Break Link).

La ayuda de Fusion (`docs/fusion_docs/contenido/fusion-sketch/break-link-and-association-to-projected-geometry-*.md`)
no tiene campos numéricos: se elige la geometría proyectada y se rompe su asociación con el modelo. En OmniCAD los
«campos» son los de `break_projection_link` —projection (id) y sketch (nombre)—, mapeados desde la clave UI en
`test_cobertura_ui_api.py`, y en el lienzo la «selección». Acá se prueban vacío, 0, negativo, enorme, con unidades
y con expresión: ninguno cierra la app, deja el boceto roto ni contesta con un mensaje de más de un renglón.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.nucleo import geometria as geo  # noqa: E402
from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui import editor_boceto  # noqa: E402

RAROS = ("", "0", "-5", "1e9", "10 mm", "2*3")
SELECCIONES_RARAS = ([], [""], [0], [-5], [10 ** 9], ["10 mm"], ["2*3"])
REF = {"tipo": "cuerpo", "cuerpo": "op1.c1"}


def llamar(sesion, nombre, **args):
    """`api.llamar` nunca lanza: si algo revienta adentro, el test lo ve como `ok=False` inesperado."""
    r = api.llamar(sesion, nombre, args)
    assert isinstance(r, dict) and isinstance(r.get("ok"), bool), r
    return r


@pytest.fixture(scope="module")
def app_qt():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def sesion(app_qt):
    """Caja 20×10×10, boceto «B» en XY y una proyección con vínculo (id 1)."""
    assert app_qt is not None
    s = api.Sesion()
    assert llamar(s, "create_box", length=20, width=10, height=10)["ok"]
    assert llamar(s, "create_sketch", plane="XY", name="B")["ok"]
    assert llamar(s, "project_to_sketch", bodies=["Cuerpo1"])["ok"]
    return s


@pytest.fixture
def lienzo_xy(app_qt):
    """Lienzo con una proyección, como el que ve el comando de la cinta."""
    assert app_qt is not None
    lz = editor_boceto.Lienzo(Boceto(), TablaParametros().evaluar, plano=geo.Plano("XY"))
    lz.resize(800, 600)
    lz.ajustar_grilla = False
    lz.proyectar_forma(geo.caja(20, 10, 10), "proyectar", REF)
    lz.show()
    yield lz
    lz.close()
    lz.deleteLater()
    app_qt.processEvents()


def _sin_rotura(sesion, r, antes):
    """La app sigue viva y el boceto legible; lo rechazado no lo toca y avisa en un solo renglón."""
    assert QApplication.instance() is not None, "la app se cerró"
    despues = llamar(sesion, "get_sketch", sketch="B")
    assert despues["ok"], "el boceto quedó roto"
    if not r["ok"]:
        assert despues["result"] == antes, "un valor rechazado cambió el boceto"
        assert isinstance(r.get("mensaje"), str) and r["mensaje"], r
        assert "\n" not in r["mensaje"] and "\r" not in r["mensaje"], r["mensaje"]


# ---------------------------------------------------------------- CAMPOS DE LA HERRAMIENTA
@pytest.mark.parametrize("valor", RAROS)
def test_projection_con_valor_raro_no_rompe_la_app(sesion, valor):
    """Vacío, cero, negativo, enorme, unidades y expresión: el id no es un entero y se rechaza sin tocar nada."""
    antes = llamar(sesion, "get_sketch", sketch="B")["result"]
    r = llamar(sesion, "break_projection_link", projection=valor)
    _sin_rotura(sesion, r, antes)
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS", r


@pytest.mark.parametrize("id_raro", (0, -5, 10 ** 9, 999999))
def test_projection_id_inexistente_no_rompe_la_app(sesion, id_raro):
    """Un id entero que no existe se rechaza nombrándolo, con mensaje de un renglón y sin cambiar el boceto."""
    antes = llamar(sesion, "get_sketch", sketch="B")["result"]
    r = llamar(sesion, "break_projection_link", projection=id_raro)
    _sin_rotura(sesion, r, antes)
    assert not r["ok"] and r["error_kind"] == "ENTITY_NOT_FOUND", r


@pytest.mark.parametrize("valor", RAROS)
def test_sketch_con_valor_raro_no_rompe_la_app(sesion, valor):
    """El nombre del boceto: vacío es «el último» y rompe el vínculo; cualquier otro texto raro se rechaza."""
    antes = llamar(sesion, "get_sketch", sketch="B")["result"]
    r = llamar(sesion, "break_projection_link", projection=1, sketch=valor)
    _sin_rotura(sesion, r, antes)
    if valor == "":
        assert r["ok"], r
    else:
        assert not r["ok"] and r["error_kind"] == "SKETCH_NOT_FOUND", r


def test_valor_valido_rompe_el_vinculo_y_deja_geometria_editable(sesion):
    """El caso válido «raramente simple» (id 1, nombre vacío) deja la geometría normal y legible."""
    r = llamar(sesion, "break_projection_link", projection=1, sketch="")
    assert r["ok"], r
    assert QApplication.instance() is not None
    info = llamar(sesion, "get_sketch", sketch="B")["result"]
    assert "projections" not in info
    assert all(e["state"] != "fixed" for e in info["entities"])


# ---------------------------------------------------------------- SELECCIÓN DEL LIENZO
@pytest.mark.parametrize("seleccion", SELECCIONES_RARAS)
def test_seleccion_rara_no_rompe_el_lienzo(lienzo_xy, seleccion):
    """La selección rara no cierra la app, no deja el boceto roto y avisa en un solo renglón."""
    lz = lienzo_xy
    mensajes = []
    lz.mensaje.connect(mensajes.append)
    lz.seleccion = list(seleccion)
    try:
        assert lz.romper_vinculo() is False
    except Exception as e:  # noqa: BLE001
        pytest.fail(f"romper_vinculo con selección {seleccion!r} crasheó: {type(e).__name__}: {e}")
    finally:
        try:
            lz.mensaje.disconnect(mensajes.append)
        except (RuntimeError, TypeError):
            pass
    assert QApplication.instance() is not None
    assert lz.isVisible()
    assert mensajes and all("\n" not in m and "\r" not in m for m in mensajes), mensajes
    assert len(lz.b.proyecciones) == 1
    try:
        from omnicad.restricciones import resolver
        resolver(lz.b)
    except Exception as e:  # noqa: BLE001
        pytest.fail(f"el boceto quedó roto con selección {seleccion!r}: {e}")


def test_seleccion_valida_rompe_el_vinculo_en_el_lienzo(lienzo_xy):
    """Seleccionando la curva proyectada, el comando la deja editable sin cerrar el lienzo."""
    lz = lienzo_xy
    lz.seleccion = list(lz.b.proyecciones[0]["ids"])
    assert lz.romper_vinculo() is True
    assert QApplication.instance() is not None and lz.isVisible()
    assert lz.b.proyecciones == []
    assert all(not getattr(c, "proyectada", False) for c in lz.b.curvas.values())
