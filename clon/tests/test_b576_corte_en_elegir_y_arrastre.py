"""B-576: con un análisis de sección (o el «Corte» del boceto) activo, elegir la cara de un boceto nuevo y agarrar un
componente miran lo que el corte deja dibujado, no la mitad que quedó cortada: lo mismo que B-569 en `elegir_entidad`."""
import os

import pytest

from omnicad.nucleo import geometria as g


@pytest.fixture(scope="module")
def visor():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from omnicad.timeline.operaciones import EstadoModelo
    from omnicad.ui.visor3d import Visor3D
    QApplication.instance() or QApplication([])
    estado = EstadoModelo()
    cid = estado.nuevo_cuerpo("op1", g.caja(20, 20, 10, origen=(-10, -10, -5)))    # el plano XY la corta por el medio
    v = Visor3D()
    v.resize(800, 600)
    v.set_modelo(estado)
    v.distancia = 150
    v.cid = cid
    yield v
    v.close()


@pytest.fixture(params=["boceto", "seccion"])
def corte(request, visor):
    if request.param == "boceto":
        visor.set_plano_boceto(g.Plano("XY"), {"corte": True})
    else:
        visor.cortes = [((0.0, 0.0, 1.0), (0.0, 0.0, 0.0))]
    visor.vista("arriba")
    yield
    visor.set_plano_boceto(None)
    visor.cortes = []


def test_elegir_cara_mira_el_corte(visor, corte):
    """Desde arriba se elige la cara del fondo (la que se ve en el corte), no la tapa que no se dibuja."""
    hit = visor.elegir(visor.proyectar((3, 2, 5)), planos=False)
    assert hit is not None and abs(hit["plano"].origen[2] + 5) < 1e-6


def test_cuerpo_bajo_cursor_mira_el_corte(visor, corte):
    """Al agarrar un componente se toma el punto que se ve (el fondo del corte), no la tapa cortada."""
    hit = visor.cuerpo_bajo_cursor(visor.proyectar((3, 2, 5)))
    assert hit is not None and hit[0] == visor.cid and abs(hit[1][2] + 5) < 1e-6
