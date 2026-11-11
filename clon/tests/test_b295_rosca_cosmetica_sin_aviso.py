"""B-295: crear una rosca sin modelar no muestra la advertencia cosmética."""

from omnicad import api


def test_rosca_cosmetica_sin_aviso():
    sesion = api.Sesion()
    cilindro = api.llamar(sesion, "create_cylinder", {"radius": 5, "height": 12})
    assert cilindro["ok"], cilindro

    rosca = api.llamar(sesion, "create_thread", {
        "faces": "%CYLINDER", "thread": "M10x1.5", "modeled": False,
    })
    assert rosca["ok"], rosca
    assert not any("Fusion" in aviso or "Rosca cosmética" in aviso for aviso in rosca["avisos"]), rosca
