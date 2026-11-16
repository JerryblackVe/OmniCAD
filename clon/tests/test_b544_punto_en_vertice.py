"""B-544: Punto en vértice, como Fusion: un clic cerca de un vértice visible toma el vértice, no un punto de la arista,
aunque el vértice esté en una cara inclinada (la prueba de profundidad lo daba por tapado). Uno tapado no se elige."""
import os

import numpy as np
import pytest
from PySide6.QtCore import QCoreApplication, QPointF

from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva

ESQUINAS = [(x, y, z) for x in (0, 30) for y in (0, 20) for z in (0, 20)]


@pytest.fixture(scope="module")
def visor():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from omnicad.ui.visor3d import Visor3D
    QApplication.instance() or QApplication([])
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="30", largo="20", alto="20"))
    v = Visor3D()
    v.resize(800, 600)
    v.set_modelo(doc.estado_final)
    v.vista("iso")
    v.encuadrar()
    v.show()
    for _ in range(3):
        QCoreApplication.processEvents()
    yield v
    v.close()


def _profundidad(v, p):
    o, d = v.rayo(v.proyectar(p))
    return float((np.asarray(p, float) - o) @ d)


@pytest.mark.parametrize("px", [4, 8])
def test_cerca_de_un_vertice_visible_gana_el_vertice(visor, px):
    from omnicad.ui.comandos.construir import PUNTO
    tapada = max(ESQUINAS, key=lambda p: _profundidad(visor, p))
    centro = visor.proyectar((15, 10, 10))
    for esquina in ESQUINAS:
        if esquina == tapada:
            continue
        pv = visor.proyectar(esquina)
        paso = np.array([centro.x() - pv.x(), centro.y() - pv.y()])
        paso *= px / np.linalg.norm(paso)
        h = visor.elegir_entidad(QPointF(pv.x() + paso[0], pv.y() + paso[1]), PUNTO)
        assert h is not None and h["tipo"] == "vertice", (esquina, h and h["tipo"])
        assert np.allclose(h["punto"], esquina)


def test_el_vertice_tapado_no_se_elige(visor):
    from omnicad.ui.comandos.construir import PUNTO
    tapada = max(ESQUINAS, key=lambda p: _profundidad(visor, p))
    h = visor.elegir_entidad(visor.proyectar(tapada), PUNTO)
    assert h is None or not np.allclose(h["punto"], tapada)


@pytest.mark.parametrize("centro", [(15, 10, 20), (30, 10, 10), (15, 0, 10)])
def test_cerca_del_centro_de_una_cara_inclinada_gana_el_centro(visor, centro):
    """Gemelo: el punto de forzado del centro de cara pasaba por la misma prueba y a 8 px no se elegía nada."""
    from omnicad.ui.comandos.construir import PUNTO
    pc = visor.proyectar(centro)
    for dx, dy in [(0, 8), (-8, 3)]:
        h = visor.elegir_entidad(QPointF(pc.x() + dx, pc.y() + dy), PUNTO)
        assert h is not None and h["ref"].get("modo") == "centro_cara" and np.allclose(h["punto"], centro), (dx, dy)
