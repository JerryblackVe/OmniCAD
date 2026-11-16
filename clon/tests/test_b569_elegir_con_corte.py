"""B-569: con el «Corte» del boceto (o un análisis de sección) la mitad de adelante del cuerpo no se dibuja; el clic
elige lo que se ve en el corte y no lo que quedó cortado."""
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
    estado.nuevo_cuerpo("op1", g.caja(20, 20, 10, origen=(-10, -10, -5)))    # el plano XY la corta por el medio
    v = Visor3D()
    v.resize(800, 600)
    v.set_modelo(estado)
    v.config.origen = {"x": True}
    v.distancia = 150                 # el eje se dibuja con un largo proporcional a la distancia
    yield v
    v.close()


@pytest.fixture(params=["boceto", "seccion"])
def corte(request, visor):
    if request.param == "boceto":
        visor.set_plano_boceto(g.Plano("XY"), {"corte": True})
    else:
        visor.cortes = [((0.0, 0.0, 1.0), (0.0, 0.0, 0.0))]
    yield
    visor.set_plano_boceto(None)
    visor.cortes = []


def test_eje_en_el_corte_se_elige(visor, corte):
    visor.vista("arriba")             # el eje X queda sobre el plano del corte, dentro del cuerpo
    hit = visor.elegir_entidad(visor.proyectar((5, 0, 0)), {"eje"})
    assert hit is not None and hit["ref"] == {"tipo": "eje", "id": "X"}


def test_eje_sin_corte_sigue_tapado(visor):
    visor.vista("arriba")
    assert visor.elegir_entidad(visor.proyectar((5, 0, 0)), {"eje"}) is None


@pytest.mark.parametrize("esquina", [(-10, -10, 5), (10, -10, 5), (10, 10, 5), (-10, 10, 5)])
def test_vertice_cortado_no_se_elige(visor, corte, esquina):
    visor.vista("iso")
    hit = visor.elegir_entidad(visor.proyectar(esquina), {"vertice"})
    assert hit is None or hit["punto"][2] < 0


def test_cara_sobre_el_plano_del_corte_se_elige(visor):
    """Boceto sobre la cara de arriba con el corte: la cara del boceto se sigue eligiendo, no la de abajo."""
    visor.set_plano_boceto(g.Plano("XY", 5), {"corte": True})
    try:
        for vista in ("arriba", "iso"):
            visor.vista(vista)
            hit = visor.elegir_entidad(visor.proyectar((3, 2, 5)), {"cara"})
            assert hit is not None and abs(hit["punto"][2] - 5) < 1e-6, vista
    finally:
        visor.set_plano_boceto(None)
