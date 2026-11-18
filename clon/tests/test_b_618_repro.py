"""B-618: la Solevación entre dos círculos de dos bocetos en planos perpendiculares (perfiles «Libre», sin raíles,
Cuerpo nuevo) daba «se autointerseca (1)» y la previa salía manchada, aunque Fusion arma el codo sin error.

La pared reglada se metía en la tapa del final; ahora sale lisa, como la de Fusion.
"""
from omnicad import api

RADIO = 10.0


def _llamar(sesion, nombre, **args):
    respuesta = api.llamar(sesion, nombre, args)
    assert respuesta["ok"], f"{nombre}: {respuesta.get('mensaje')}"
    return respuesta["result"]


def test_solevacion_entre_dos_circulos_en_planos_perpendiculares():
    """Un codo de R10: un círculo en XY y otro en un plano a 90° con el centro 5 mm corrido (como la captura)."""
    sesion = api.Sesion()
    _llamar(sesion, "create_construction_plane", type="angle", references=["X"], angle=90, name="Codo")
    _llamar(sesion, "sketch_from_spec", name="B1", plane="XY",
            entities=[{"type": "circle", "center": [0, 0], "radius": RADIO}])
    _llamar(sesion, "sketch_from_spec", name="B2", plane="Codo",
            entities=[{"type": "circle", "center": [5, 30], "radius": RADIO}])
    # Fusion arma el codo; antes OmniCAD lo rechazaba con «se autointerseca (1)».
    creado = _llamar(sesion, "loft", sketches=["B1", "B2"], operation="new_body")["bodies_created"][0]
    assert creado["volume"] > 0
    informe = _llamar(sesion, "check_geometry", body=creado["id"])["bodies"][0]
    assert informe["valid"] and informe["self_intersections"] == 0
