# -*- coding: utf-8 -*-
"""CF-11: Buscar subrestringidos (Find Under-Constrained) y Calcular boceto (Compute Sketch) en la Paleta de boceto,
como en Fusion 360. La lista sale de los grados de libertad que ya calcula el solver (lo que no está en
`resultado.determinadas`); las dos cosas también están en el catálogo del MCP/CLI."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QPushButton, QToolButton  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui import editor_boceto, modo_boceto  # noqa: E402


@pytest.fixture
def sesion():
    s = api.Sesion()
    api.llamar(s, "create_sketch", {"plane": "XY", "name": "B"})
    api.llamar(s, "draw_rectangle", {"sketch": "B", "x1": 0, "y1": 0, "x2": 40, "y2": 20})
    return s


def test_api_buscar_subrestringidos_lista_lo_que_se_mueve_y_vacia_al_restringir(sesion):
    """Un rectángulo suelto está subrestringido; con todo fijo, la lista queda vacía."""
    r = api.llamar(sesion, "find_underconstrained", {"sketch": "B"})
    assert r["ok"], r
    r = r["result"]
    assert r["status"] == "under_constrained" and r["dof"] > 0
    assert r["count"] == len(r["entities"]) + len(r["points"]) > 0
    info = api.llamar(sesion, "get_sketch", {"sketch": "B"})["result"]
    libres = {e["id"] for e in info["entities"] if e["state"] == "free"}
    assert {e["id"] for e in r["entities"]} == libres          # los mismos ids y el mismo criterio que get_sketch

    for cid in [c["id"] for c in r["entities"]]:
        api.llamar(sesion, "add_constraint", {"sketch": "B", "type": "fix", "entities": [cid]})
    r = api.llamar(sesion, "find_underconstrained", {"sketch": "B"})
    assert r["ok"], r
    r = r["result"]
    assert r["count"] == 0, r
    assert r["status"] == "fully_constrained"


def test_api_calcular_boceto_cuenta_fijas_y_libres(sesion):
    """Compute Sketch resuelve de nuevo y parte la geometría en fija y libre; el total es el del boceto."""
    r = api.llamar(sesion, "compute_sketch", {"sketch": "B"})
    assert r["ok"], r
    r = r["result"]
    assert r["status"] == "under_constrained" and r["dof"] > 0
    info = api.llamar(sesion, "get_sketch", {"sketch": "B"})["result"]
    assert r["constrained"] + r["free"] == len(info["points"]) + len(info["entities"])
    assert r["free"] > 0


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
    app.processEvents()


def test_lienzo_buscar_subrestringidos_resalta_acerca_y_borra(lienzo):
    """El lienzo lista lo subrestringido, lleva la vista a la entidad elegida y la borra en un paso de deshacer."""
    lz = lienzo
    arriba = lz.b.agregar_rectangulo((0, 0), (40, 20))[0]
    lz.b.agregar_rectangulo((100, 0), (140, 20))
    lz.resolver()
    filas = lz.subrestringidas()
    assert {i for i, _t in filas} >= {arriba}
    assert all(t for _i, t in filas)

    lz.resaltar([arriba])
    assert lz.seleccion == [arriba]
    c = lz.b.curvas[arriba]
    (ax, ay), (bx, by) = lz.b.coords(c.p1), lz.b.coords(c.p2)
    assert lz.centro == pytest.approx([(ax + bx) / 2, (ay + by) / 2])     # la vista fue a esa curva

    lz.borrar_ids([arriba])
    assert arriba not in lz.b.curvas
    assert len(lz.historial) == 1                                # un solo paso de deshacer
    lz.deshacer()
    assert arriba in lz.b.curvas


def test_paleta_muestra_la_lista_y_sus_botones_emiten(app):
    """La Paleta de boceto tiene los dos botones y la lista: elegir una fila emite resaltar y su ✕ emite borrar."""
    paleta = modo_boceto.PaletaBoceto()
    paleta.show()
    assert paleta.b_buscar_sub.text() == "Buscar subrestringidos"
    assert paleta.b_calcular.text() == "Calcular boceto"
    assert not paleta.lista_sub.isVisible()

    paleta.mostrar_subrestringidos([(7, "línea 7")])
    assert paleta.lista_sub.isVisible()
    fila = paleta.lista_sub.findChildren(QPushButton)[0]
    assert fila.text() == "línea 7"
    vistos = []
    paleta.resaltar.connect(vistos.append)
    paleta.borrar_sub.connect(vistos.append)
    fila.click()
    paleta.lista_sub.findChildren(QToolButton)[0].click()
    assert vistos == [7, 7]

    paleta.mostrar_subrestringidos([])                            # totalmente restringido
    assert "Totalmente restringido" in paleta.lista_sub.findChildren(type(paleta.estado))[0].text()
    paleta.close()
    paleta.deleteLater()
    app.processEvents()
