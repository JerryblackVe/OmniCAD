"""B-561: Tangente entre una línea y un círculo cuando el extremo de la línea ya está sobre el círculo (la V de Gerardo,
dibujada con clic sobre el círculo). La forma «distancia al centro = radio» era singular justo en el contacto: los GDL no
bajaban y el editor la quitaba como sobrante. Ahora la línea queda perpendicular al radio en ese extremo, como Fusion."""
import math
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.restricciones import Boceto, resolver  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402

CX, CY, R = 0.0, -40.5, 29.09


def _v(circulo_fijo):
    b = Boceto()
    c = b.agregar_circulo((CX, CY), R)
    if circulo_fijo == "proyectado":
        b.curvas[c].proyectada = True
    else:
        b.agregar_restriccion("fijo", [c])
    a, z = (math.radians(225), math.radians(318))
    l1 = b.agregar_linea((CX + R * math.cos(a), CY + R * math.sin(a)), (0, -77.3))
    l2 = b.agregar_linea((0, -77.3), (CX + R * math.cos(z), CY + R * math.sin(z)))
    b.agregar_restriccion("coincidente", [b.curvas[l1].p2, b.curvas[l2].p1])
    b.agregar_restriccion("coincidente", [b.curvas[l1].p1, c])
    b.agregar_restriccion("coincidente", [b.curvas[l2].p2, c])
    return b, c, l1


def _distancia_al_centro(b, l):
    (x1, y1), (x2, y2) = b.coords(b.curvas[l].p1), b.coords(b.curvas[l].p2)
    return abs((x2 - x1) * (y1 - CY) - (x1 - CX) * (y2 - y1)) / math.hypot(x2 - x1, y2 - y1)


@pytest.mark.parametrize("circulo", ["fijo", "proyectado"])
def test_la_tangente_baja_un_grado_de_libertad(circulo):
    b, c, l1 = _v(circulo)
    antes = resolver(b).gdl
    b.agregar_restriccion("tangente", [l1, c])
    r = resolver(b)
    assert r.ok and r.gdl == antes - 1
    assert _distancia_al_centro(b, l1) == pytest.approx(R, abs=1e-6)


@pytest.mark.parametrize("circulo", ["fijo", "proyectado"])
def test_el_comando_tangente_la_deja_y_mueve_la_linea(circulo):
    from omnicad.ui import editor_boceto
    QApplication.instance() or QApplication([])
    b, c, l1 = _v(circulo)
    lz = editor_boceto.Lienzo(b, TablaParametros().evaluar)
    lz.resolver()
    mensajes = []
    lz.mensaje.connect(mensajes.append)
    lz.set_herramienta("r_tangente")
    assert lz.aplicar_restriccion("tangente", [l1, c]), mensajes
    assert any(r.tipo == "tangente" for r in lz.b.restricciones.values())
    assert _distancia_al_centro(lz.b, l1) == pytest.approx(R, abs=1e-6)
    assert mensajes[-1] == "Restricción agregada: Tangente."
    lz.close()


def test_gemelo_elipse_con_el_extremo_encima():
    b = Boceto()
    e = b.agregar_elipse((0, 0), (20, 0), 10)
    b.agregar_restriccion("fijo", [e])
    ang = math.radians(250)
    l = b.agregar_linea((20 * math.cos(ang), 10 * math.sin(ang)), (5, -25))
    b.agregar_restriccion("coincidente", [b.curvas[l].p1, e])
    antes = resolver(b).gdl
    b.agregar_restriccion("tangente", [l, e])
    r = resolver(b)
    assert r.ok and r.gdl == antes - 1
    (x1, y1), (x2, y2) = b.coords(b.curvas[l].p1), b.coords(b.curvas[l].p2)
    normal = (x1 / 400, y1 / 100)                         # ∇(x²/a² + y²/b²) en el extremo
    assert abs((x2 - x1) * normal[0] + (y2 - y1) * normal[1]) < 1e-6
    assert (x1 / 20) ** 2 + (y1 / 10) ** 2 == pytest.approx(1)


def test_con_clics_tangente_linea_y_circulo():
    """Como Gerardo: herramienta Tangente, clic en la línea, clic en el círculo (eventos simulados, nunca el cursor)."""
    from test_boceto_interaccion import _clic, _lienzo
    app = QApplication.instance() or QApplication([])
    b, c, l1 = _v("fijo")
    lz = _lienzo(app, b)
    lz.resolver()
    lz.encuadrar()
    lz.set_herramienta("r_tangente")
    (x1, y1), (x2, y2) = b.coords(b.curvas[l1].p1), b.coords(b.curvas[l1].p2)
    _clic(lz, (x1 + x2) / 2, (y1 + y2) / 2)
    _clic(lz, CX, CY + R)                                   # arriba del círculo, lejos de las líneas
    assert any(r.tipo == "tangente" and set(r.entidades) == {l1, c} for r in lz.b.restricciones.values())
    assert _distancia_al_centro(lz.b, l1) == pytest.approx(R, abs=1e-6)
