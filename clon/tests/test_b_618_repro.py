"""B-618: la Solevación entre dos círculos de dos bocetos en planos perpendiculares (perfiles «Libre», sin raíles,
Cuerpo nuevo) da «se autointerseca (1)» y la previa sale manchada, aunque Fusion arma el codo sin error.

La pared sale estrujada (a media altura la sección deja de ser un círculo de R10) y el chequeo la rechaza. La
causa probable es la costura de las secciones, que no se alinea; ver `docs/seguimiento/preparado/B-618.md`.
"""
import pytest

from omnicad import api

RADIO = 10.0


def _llamar(sesion, nombre, **args):
    respuesta = api.llamar(sesion, nombre, args)
    assert respuesta["ok"], f"{nombre}: {respuesta.get('mensaje')}"
    return respuesta["result"]


@pytest.mark.xfail(strict=True, reason="B-618")
def test_solevacion_entre_dos_circulos_en_planos_perpendiculares():
    """Un codo de R10: un círculo en XY y otro en un plano a 90° con el centro 5 mm corrido (como la captura)."""
    sesion = api.Sesion()
    _llamar(sesion, "create_construction_plane", type="angle", references=["X"], angle=90, name="Codo")
    _llamar(sesion, "sketch_from_spec", name="B1", plane="XY",
            entities=[{"type": "circle", "center": [0, 0], "radius": RADIO}])
    _llamar(sesion, "sketch_from_spec", name="B2", plane="Codo",
            entities=[{"type": "circle", "center": [5, 30], "radius": RADIO}])
    # Fusion arma el codo; OmniCAD lo rechaza con «se autointerseca (1)».
    _llamar(sesion, "loft", sketches=["B1", "B2"], operation="new_body")
    cuerpo = _llamar(sesion, "get_physical_properties")["bodies"][0]
    assert cuerpo["volume"] > 0
