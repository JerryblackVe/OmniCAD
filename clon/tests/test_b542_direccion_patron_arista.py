"""B-542: en Patrón › Dirección, el clic sobre una arista del cuerpo toma la arista, como Fusion, y no la curva del
boceto que quedó tapada detrás del cuerpo (el visor la dibuja con profundidad: no se ve). Una curva a la vista sí se
sigue eligiendo."""
import os

import pytest

from omnicad import api
from omnicad.api.sesion import Sesion
from omnicad.ui.comandos.crear import DIRECCION

# soporte en L del reporte (PERFIL_L sobre XY, extruido 40): puntos medios de las aristas de abajo, que coinciden con
# las líneas del boceto
L = [(0, 0), (80, 0), (80, 5), (5, 5), (5, 50), (0, 50)]
MEDIOS = [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 0.0) for a, b in zip(L, L[1:] + L[:1], strict=True)]


@pytest.fixture(scope="module")
def sesion_visor():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from omnicad.ui.visor3d import Visor3D
    QApplication.instance() or QApplication([])
    s = Sesion()
    assert api.llamar(s, "create_sketch", {"plane": "XY", "name": "PERFIL_L"})["ok"]
    for a, b in zip(L, L[1:] + L[:1], strict=True):
        assert api.llamar(s, "draw_line", {"start_x": a[0], "start_y": a[1], "end_x": b[0], "end_y": b[1]})["ok"]
    assert api.llamar(s, "extrude", {"sketch": "PERFIL_L", "profile": "largest", "distance": "40"})["ok"]
    v = Visor3D()
    v.resize(1200, 800)
    v.set_modelo(s.doc.estado_final)
    yield s, v
    v.close()


@pytest.mark.parametrize("vista", ["iso", "frente", "arriba", "derecha"])
def test_direccion_no_toma_la_curva_tapada(sesion_visor, vista):
    _s, v = sesion_visor
    v.vista(vista)
    for m in MEDIOS:
        hit = v.elegir_entidad(v.proyectar(m), DIRECCION)
        assert hit is None or hit["tipo"] != "curva_boceto", (vista, m, hit and hit["ref"])


def test_curva_a_la_vista_se_sigue_eligiendo(sesion_visor):
    _s, v = sesion_visor
    v.vista("abajo")                    # desde abajo el boceto queda sobre la cara de la base: se ve
    hit = v.elegir_entidad(v.proyectar((40, 0, 0)), {"curva_boceto"})
    assert hit is not None and hit["tipo"] == "curva_boceto"
