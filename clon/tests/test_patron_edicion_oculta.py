"""BOC-60: al editar un patrón, sus copias viejas no se dibujan ni se agarran mientras dura el panel (la vista previa
trae las nuevas); al aceptar o cancelar vuelven."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui import editor_boceto  # noqa: E402


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


def _patron(lz):
    original = lz.b.agregar_circulo((20, 0), 2)
    lz.b.patron_rectangular([original], 3, 20, modo="espaciado")
    lz.resolver()
    registro = lz.b.patrones[0]
    copias = {i for ids in registro["copias"].values() for i in ids if i in lz.b.curvas}
    return original, copias


def test_las_copias_viejas_se_ocultan_mientras_dura_el_panel_y_vuelven_al_cancelar(lz):
    original, copias = _patron(lz)
    assert len(copias) == 2 and all(lz._visible(lz.b.curvas[i]) for i in copias)
    assert lz.editar_patron(lz.b.patrones[0]["id"])
    assert lz.copias_en_edicion >= copias and lz._visible(lz.b.curvas[original])
    assert not any(lz._visible(lz.b.curvas[i]) for i in copias)
    assert set(copias) <= lz._ocultos()[0]                                   # tampoco se pueden capturar
    assert lz._curva_cercana(lz.a_px(60, 2)) is None and lz._curva_cercana(lz.a_px(22, 0)) == original
    textos = dict(lz.patron.textos)
    textos["cantidad1"] = "2"                                                # la vista previa ya no tiene la copia de x = 40
    lz.patron.recibir(textos)
    dibujadas = []
    original_dibujo = lz._dibujar_polilinea
    lz._dibujar_polilinea = lambda p, pts, *a, **k: (dibujadas.append(max(q[0] for q in pts)),
                                                     original_dibujo(p, pts, *a, **k))[1]
    lz.grab()
    assert any(abs(x - 22) < 0.1 for x in dibujadas)                         # el original se dibuja
    assert not any(abs(x - 62) < 0.1 for x in dibujadas)                     # la copia vieja de x = 60 ya no
    lz.patron.cancelar()
    assert lz.copias_en_edicion == frozenset() and all(lz._visible(lz.b.curvas[i]) for i in copias)
    assert lz._curva_cercana(lz.a_px(60, 2)) in copias


def test_al_aceptar_con_otra_cantidad_las_copias_nuevas_se_ven(lz):
    original, copias = _patron(lz)
    assert lz.editar_patron(lz.b.patrones[0]["id"])
    textos = dict(lz.patron.textos)
    textos["cantidad1"] = "4"
    lz.patron.recibir(textos)
    assert lz.copias_en_edicion >= copias                                     # mientras se edita siguen ocultas
    assert lz.patron.aceptar()
    nuevas = [c for c in lz.b.curvas.values() if c.tipo == "circulo"]
    assert len(nuevas) == 4 and lz.copias_en_edicion == frozenset() and all(lz._visible(c) for c in nuevas)
