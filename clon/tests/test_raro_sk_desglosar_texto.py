"""Valores raros del comando de boceto «sk_desglosar_texto» (Fusion: Explode Text).

La ayuda de Fusion no tiene diálogo: se elige un texto y se convierte en curvas fijas. En OmniCAD los campos son
los de `explode_text` —entity (id) y sketch (nombre)—, mapeados desde la clave UI en `test_cobertura_ui_api.py`.
Acá se prueban vacío, cero, negativo, enorme, con unidades y con expresión: ninguno cierra la app, deja el boceto
roto ni contesta con un mensaje de más de un renglón.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.restricciones import Boceto, resolver
from omnicad.timeline.parametros import TablaParametros
from omnicad.ui import editor_boceto

RAROS = ("", "0", "-5", "1e9", "10 mm", "2*3")
IDS_RAROS = (0, -5, 10 ** 9, 999999)
SELECCIONES_RARAS = ("", 0, -5, 10 ** 9, "10 mm", "2*3")


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
    """Boceto «B» con un texto «I»."""
    assert app_qt is not None
    s = api.Sesion()
    assert _llamar(s, "create_sketch", plane="XY", name="B")["ok"]
    r = _llamar(s, "add_text", sketch="B", text="I", height=10)
    assert r["ok"], r
    return s, r["result"]["entities"][0]["id"]


@pytest.fixture
def lienzo(app_qt):
    """Lienzo con un texto y una línea, como el que ve el comando de la cinta."""
    assert app_qt is not None
    b = Boceto()
    b.agregar_texto((0, 0), "I", altura=10)
    b.agregar_linea((20, 0), (30, 0))
    lz = editor_boceto.Lienzo(b, TablaParametros().evaluar)
    lz.set_herramienta("desglosar_texto")
    lz.resize(800, 600)
    lz.show()
    yield lz
    lz.close()
    lz.deleteLater()
    app_qt.processEvents()


def _sin_rotura(sesion, r, antes):
    """La app sigue viva y el boceto legible; lo rechazado no lo toca y avisa en un solo renglón."""
    assert QApplication.instance() is not None, "la app se cerró"
    despues = _llamar(sesion, "get_sketch", sketch="B")
    assert despues["ok"], "el boceto quedó roto"
    if not r["ok"]:
        assert despues["result"] == antes, "un valor rechazado cambió el boceto"
        assert isinstance(r.get("mensaje"), str) and r["mensaje"], r
        assert "\n" not in r["mensaje"] and "\r" not in r["mensaje"], r["mensaje"]


@pytest.mark.parametrize("valor", RAROS)
def test_entity_con_valor_raro_no_rompe_la_app(sesion, valor):
    """Vacío, cero, negativo, enorme, unidades y expresión: el id no es un entero y se rechaza sin tocar nada."""
    s, _ = sesion
    antes = _llamar(s, "get_sketch", sketch="B")["result"]
    r = _llamar(s, "explode_text", entity=valor)
    _sin_rotura(s, r, antes)
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS", r


@pytest.mark.parametrize("entity", IDS_RAROS)
def test_entity_inexistente_no_rompe_la_app(sesion, entity):
    """Un id entero que no existe se rechaza nombrándolo, con mensaje de un renglón y sin cambiar el boceto."""
    s, _ = sesion
    antes = _llamar(s, "get_sketch", sketch="B")["result"]
    r = _llamar(s, "explode_text", entity=entity)
    _sin_rotura(s, r, antes)
    assert not r["ok"] and r["error_kind"] == "ENTITY_NOT_FOUND", r


@pytest.mark.parametrize("valor", RAROS)
def test_sketch_con_valor_raro_no_rompe_la_app(sesion, valor):
    """El nombre del boceto: vacío es «el último»; cualquier otro texto raro se rechaza sin tocar el boceto."""
    s, tid = sesion
    antes = _llamar(s, "get_sketch", sketch="B")["result"]
    r = _llamar(s, "explode_text", entity=tid, sketch=valor)
    _sin_rotura(s, r, antes)
    if valor == "":
        assert r["ok"], r
    else:
        assert not r["ok"] and r["error_kind"] == "SKETCH_NOT_FOUND", r


@pytest.mark.parametrize("sketch", (0, -5, 10 ** 9))
def test_sketch_con_tipo_raro_no_rompe_la_app(sesion, sketch):
    """El nombre del boceto es texto: cero, negativo y enorme como número se rechazan nombrando el campo."""
    s, tid = sesion
    antes = _llamar(s, "get_sketch", sketch="B")["result"]
    r = _llamar(s, "explode_text", entity=tid, sketch=sketch)
    _sin_rotura(s, r, antes)
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS", r


def test_valor_valido_desglosa_el_texto_y_deja_curvas_fijas(sesion):
    """El caso válido desglosa el texto, deja geometría editable y no cierra la app."""
    s, tid = sesion
    r = _llamar(s, "explode_text", entity=tid, sketch="B")
    assert r["ok"], r
    assert QApplication.instance() is not None
    info = _llamar(s, "get_sketch", sketch="B")["result"]
    assert info["entities"] and all(e["type"] != "text" for e in info["entities"])
    assert any(c["type"] == "fix" for c in info["constraints"])


@pytest.mark.parametrize("cid", SELECCIONES_RARAS)
def test_seleccion_rara_no_rompe_el_lienzo(lienzo, cid):
    """Una selección rara avisa en un renglón, deja el boceto intacto y no cierra la app."""
    lz = lienzo
    mensajes = []
    lz.mensaje.connect(mensajes.append)
    antes = {k: (c.tipo, getattr(c, "pts", None), getattr(c, "texto", None)) for k, c in lz.b.curvas.items()}
    try:
        lz.agregar_pick(cid, (0, 0))
    except Exception as e:
        pytest.fail(f"desglosar_texto con selección {cid!r} crasheó: {type(e).__name__}: {e}")
    finally:
        try:
            lz.mensaje.disconnect(mensajes.append)
        except (RuntimeError, TypeError):
            pass
    assert QApplication.instance() is not None
    assert lz.isVisible()
    assert mensajes and all("\n" not in m and "\r" not in m for m in mensajes), mensajes
    assert {k: (c.tipo, getattr(c, "pts", None), getattr(c, "texto", None))
            for k, c in lz.b.curvas.items()} == antes
    assert resolver(lz.b).ok


def test_seleccion_sobre_una_linea_no_rompe_el_lienzo(lienzo):
    """El comando solo admite texto: elegir una línea avisa en un renglón y no desglosa nada."""
    lz = lienzo
    mensajes = []
    lz.mensaje.connect(mensajes.append)
    linea = next(c.id for c in lz.b.curvas.values() if c.tipo == "linea")
    lz.agregar_pick(linea, (25, 0))
    assert QApplication.instance() is not None
    assert lz.isVisible()
    assert mensajes and all("\n" not in m and "\r" not in m for m in mensajes), mensajes
    assert any(c.tipo == "texto" for c in lz.b.curvas.values())
    assert resolver(lz.b).ok
