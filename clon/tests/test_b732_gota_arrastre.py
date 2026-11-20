"""B-732: la gota (círculo de radio 33 en el origen + dos líneas tangentes que se juntan arriba). Arrastrar la punta
hasta adentro del círculo lo achica (tiene que hacerlo para seguir tangente) y antes quedaba chico para siempre: el
menor cambio se medía desde el evento anterior. Como Fusion (video de Gerardo del 20/11, 0:44-0:45), se mide desde el
comienzo del arrastre y el círculo vuelve a su tamaño cuando la punta sale."""
import math
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402


def _gota():
    from omnicad.ui import editor_boceto
    QApplication.instance() or QApplication([])
    b = Boceto()
    b.asegurar_referencias([Boceto.ORIGEN])
    k = b.agregar_circulo((0, 0), 33)
    b.agregar_restriccion("coincidente", [b.curvas[k].centro, Boceto.ORIGEN])
    l1, l2 = b.agregar_linea((-28, 17), (0, 78)), b.agregar_linea((0, 78), (29, 16))
    b.agregar_restriccion("coincidente", [b.curvas[l1].p2, b.curvas[l2].p1])
    for p in (b.curvas[l1].p1, b.curvas[l2].p2):
        b.agregar_restriccion("coincidente", [p, k])
    lz = editor_boceto.Lienzo(b, TablaParametros().evaluar)
    lz.resolver()
    lz.set_herramienta("r_tangente")
    for l in (l1, l2):
        assert lz.aplicar_restriccion("tangente", [l, k])
    lz.set_herramienta("seleccionar")
    return b, lz, k, l1


def _tangencias(b, k):
    """Distancia del centro a cada línea menos el radio (0 = tangente)."""
    (ox, oy), r = b.coords(b.curvas[k].centro), b.curvas[k].radio
    errores = []
    for c in b.curvas.values():
        if c.tipo == "linea" and not c.construccion:
            (ax, ay), (bx, by) = (b.coords(p) for p in c.puntos())
            errores.append(abs(abs((bx - ax) * (oy - ay) - (by - ay) * (ox - ax)) / math.hypot(bx - ax, by - ay) - r))
    return errores


def test_la_punta_entra_al_circulo_y_al_salir_vuelve_a_su_tamano():
    b, lz, k, l1 = _gota()
    punta = b.curvas[l1].p2
    camino = [(0, 78 - 70 * i / 35) for i in range(1, 36)] + [(0, 8 + 70 * i / 35) for i in range(1, 36)]
    lz._empezar_arrastre(punta, lz.a_px(*b.coords(punta)))
    radios = []
    for q in camino:
        lz._mover_punto(punta, q)
        lz._movio = True
        radios.append(b.curvas[k].radio)
        assert lz.resultado.ok and max(_tangencias(b, k)) < 1e-3
    assert min(radios) < 10                                  # con la punta adentro se achica (como Fusion)
    assert abs(radios[-1] - 33) < 0.01                       # antes: quedaba en ~7 mm para siempre
    lz.mouseReleaseEvent(_Soltar())
    assert lz.resultado.ok and abs(b.curvas[k].radio - 33) < 0.01


class _Soltar:
    """Evento de soltar el botón izquierdo en el origen (lo que lee `mouseReleaseEvent`)."""
    def position(self):
        from PySide6.QtCore import QPointF
        return QPointF(0, 0)

    def button(self):
        from PySide6.QtCore import Qt
        return Qt.LeftButton

    def modifiers(self):
        from PySide6.QtCore import Qt
        return Qt.NoModifier
