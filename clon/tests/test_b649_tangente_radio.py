"""B-649: un círculo tangente a una línea no cambia de radio al aplicar la tangente ni al arrastrar su centro (Fusion
mueve la línea y el círculo queda del mismo tamaño). El caso es el del video de Gerardo del 19/11: círculo de r60 en el
origen, una vertical desde el centro y una línea inclinada que comparte el extremo de arriba con la vertical."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.restricciones import Boceto, resolver  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402


def _video(conectada=True):
    b = Boceto()
    b.asegurar_referencias([Boceto.ORIGEN])
    k = b.agregar_circulo((0, 0), 60)
    l = b.agregar_linea((-50, 47), (-5, 100))
    v = b.agregar_linea((0, 0), (0, 97.5))
    b.agregar_restriccion("coincidente", [b.curvas[v].p1, b.curvas[k].centro])
    b.agregar_restriccion("vertical", [v])
    if conectada:
        b.agregar_restriccion("coincidente", [b.curvas[l].p2, b.curvas[v].p2])
    return b, k, l


def test_el_comando_tangente_no_cambia_el_radio():
    from omnicad.ui import editor_boceto
    QApplication.instance() or QApplication([])
    b, k, l = _video()
    lz = editor_boceto.Lienzo(b, TablaParametros().evaluar)
    lz.resolver()
    lz.set_herramienta("r_tangente")
    assert lz.aplicar_restriccion("tangente", [l, k])
    assert lz.resultado.ok and b.curvas[k].radio == pytest.approx(60)


@pytest.mark.parametrize("conectada", [True, False])
def test_arrastrar_el_centro_no_cambia_el_radio(conectada):
    b, k, l = _video(conectada)
    b.deslizar_a_tangente(l, k)
    b.agregar_restriccion("tangente", [l, k])
    r = resolver(b, {})
    assert r.ok
    centro = b.curvas[k].centro
    for i in range(1, 11):                     # como `_mover_punto`: cada evento del ratón resuelve solo esa parte
        b.puntos[centro].x, b.puntos[centro].y = 2.0 * i, -1.0 * i
        r = resolver(b, {}, centro, r)
        assert r.ok
    assert resolver(b, {}).ok                  # soltar
    assert b.curvas[k].radio == pytest.approx(60)
    assert b.coords(centro) == pytest.approx((20, -10))
