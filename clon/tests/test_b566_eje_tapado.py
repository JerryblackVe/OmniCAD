"""B-566 (gemelo de B-542): un eje tapado por un cuerpo no se ve (se dibuja con profundidad), así que el clic no lo
elige; la parte que asoma fuera del cuerpo sí, y con «Seleccionar otro» se elige a través."""
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
    estado.nuevo_cuerpo("op1", g.caja(20, 20, 10, origen=(-10, -10, 0)))     # el eje Z la atraviesa por el medio
    v = Visor3D()
    v.resize(800, 600)
    v.set_modelo(estado)
    v.config.origen = {"z": True}
    v.vista("frente")                 # ninguna arista del cuerpo cae sobre el eje
    v.distancia = 150                 # el eje se dibuja con un largo proporcional a la distancia
    yield v
    v.close()


def test_eje_tapado_no_se_elige(visor):
    adentro = visor.proyectar((0, 0, 5))
    assert visor.elegir_entidad(adentro, {"eje"}) is None
    hit = visor.elegir_entidad(adentro, {"eje"}, a_traves=True)
    assert hit is not None and hit["ref"] == {"tipo": "eje", "id": "Z"}


def test_eje_a_la_vista_se_elige(visor):
    largo = visor._tam_planos() * 1.4           # largo con que se dibuja el eje del origen
    assert largo > 15
    hit = visor.elegir_entidad(visor.proyectar((0, 0, (10 + largo) / 2)), {"eje"})
    assert hit is not None and hit["ref"] == {"tipo": "eje", "id": "Z"}
