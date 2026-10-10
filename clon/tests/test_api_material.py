# -*- coding: utf-8 -*-
"""Herramientas del grupo "material" (api/herramientas_material.py) y la tabla de materiales físicos
(nucleo/analisis.py): gomas, silicona y TPU de fábrica, materiales propios guardados en la biblioteca del usuario,
asignar material (masa exacta) y aspecto."""
import json

import pytest

from omnicad import api
from omnicad.nucleo import analisis as an
from omnicad.nucleo import render_cpu as rc
from omnicad.timeline.operaciones import propiedades_cuerpo


@pytest.fixture(autouse=True)
def biblioteca(tmp_path, monkeypatch):
    """La biblioteca de materiales del usuario va a un archivo temporal y la tabla se restaura al final."""
    monkeypatch.setenv(an.VAR_MATERIALES, str(tmp_path / "materiales.json"))
    copia = dict(an.TABLA_MATERIALES)
    yield tmp_path / "materiales.json"
    an.TABLA_MATERIALES.clear()
    an.TABLA_MATERIALES.update(copia)


def ok(r):
    assert r["ok"], r
    return r["result"]


def llamar(s, nombre, **args):
    return ok(api.llamar(s, nombre, args))


def falla(s, nombre, kind, **args):
    receta = json.dumps(s.doc.a_dict(), sort_keys=True)
    r = api.llamar(s, nombre, args)
    assert not r["ok"] and r["error_kind"] == kind, r
    assert json.dumps(s.doc.a_dict(), sort_keys=True) == receta
    return r


def cubo(s, lado=10, x=0):
    return llamar(s, "create_box", length=lado, width=lado, height=lado, x=x)["bodies_created"][0]["id"]


def test_gomas_silicona_y_tpu_de_fabrica_dan_masa():
    s = api.Sesion()
    mats = {m["name"]: m for m in llamar(s, "list_materials")["materials"]}
    for nombre, densidad in (("Goma natural", 0.93), ("Goma EPDM", 1.15), ("Neopreno", 1.23), ("Silicona", 1.15),
                             ("TPU", 1.21), ("Acero", 7.85)):
        assert mats[nombre]["density_g_cm3"] == densidad and mats[nombre]["custom"] is False
    assert [m["name"] for m in llamar(s, "list_materials", query="goma")["materials"]] == ["Goma natural", "Goma EPDM"]
    junta, cable = cubo(s), cubo(s, x=50)
    r = llamar(s, "set_material", bodies=[junta], material="silicona")       # sin distinguir mayúsculas
    assert r["bodies"] == [{"id": junta, "name": "Cuerpo1", "material": "Silicona", "density_g_cm3": 1.15,
                            "mass_g": 1.15}]
    llamar(s, "set_material", bodies=[cable], material="TPU")
    props = api.llamar(s, "get_physical_properties", {})
    assert props["ok"] and not props["avisos"]
    assert props["result"]["total"]["mass_g"] == pytest.approx(1.15 + 1.21)   # antes: «null» por falta de densidad
    r = falla(s, "set_material", "MATERIAL_NOT_FOUND", bodies=[junta], material="silicon")
    assert "Silicona" in " ".join(r["pistas"])
    llamar(s, "set_material", bodies=[junta], material=None)                  # quita la asignación
    assert llamar(s, "list_materials")["bodies"][0]["material"] is None
    llamar(s, "undo")
    assert llamar(s, "list_materials")["bodies"][0]["material"] == "Silicona"


def test_material_propio_se_guarda_se_usa_y_se_borra(biblioteca):
    s = api.Sesion()
    r = llamar(s, "define_material", name="Espuma EVA", density=0.12, color="#ff8800")
    assert r["material"] == {"name": "Espuma EVA", "density_g_cm3": 0.12, "color": "#ff8800", "custom": True}
    assert r["saved"] and json.loads(biblioteca.read_text(encoding="utf-8"))["materiales"]["Espuma EVA"] == {
        "densidad": 0.12, "color": [1.0, 136 / 255, 0.0]}
    falla(s, "define_material", "NAME_EXISTS", name="espuma eva", density=0.2)
    falla(s, "define_material", "NAME_EXISTS", name="ACERO", density=7)
    falla(s, "define_material", "INVALID_ARGUMENTS", name="Nada", density=0)
    falla(s, "define_material", "INVALID_ARGUMENTS", name="Nada", density=1, color="#12")
    falla(s, "define_material", "INVALID_ARGUMENTS", name="Nada", density=1, color=[2, 300, 0])
    pieza = cubo(s, 20)
    llamar(s, "set_material", bodies=[pieza], material="espuma eva")
    masa = llamar(s, "get_physical_properties", bodies=[pieza])["bodies"][0]
    assert masa["material"] == "Espuma EVA" and masa["mass_g"] == pytest.approx(8000 * 0.12e-3)
    # El visor y el render lo pintan con su color (cuerpo sin aspecto propio).
    c = s.cuerpo(pieza)
    color, _ = rc.color_y_acabado(c, propiedades_cuerpo(s.doc.propiedades, c))
    assert color == pytest.approx([1.0, 136 / 255, 0.0])
    r = llamar(s, "define_material", name="Espuma EVA", density=0.2, overwrite=True)
    assert r["replaced"] and llamar(s, "get_physical_properties", bodies=[pieza])["bodies"][0]["mass_g"] == \
        pytest.approx(1.6)
    # Próxima sesión: se carga del .json.
    del an.TABLA_MATERIALES["Espuma EVA"]
    assert an.cargar_materiales_propios() == ["Espuma EVA"] and an.TABLA_MATERIALES["Espuma EVA"]["densidad"] == 0.2
    r = api.llamar(s, "delete_material", {"name": "espuma EVA"})
    assert r["ok"] and r["result"] == {"deleted": "Espuma EVA", "bodies_using_it": [pieza]} and r["avisos"]
    assert json.loads(biblioteca.read_text(encoding="utf-8"))["materiales"] == {}
    falla(s, "delete_material", "INVALID_ARGUMENTS", name="Acero")
    falla(s, "delete_material", "MATERIAL_NOT_FOUND", name="Espuma EVA")
    r = api.llamar(s, "get_physical_properties", {"bodies": [pieza]})
    assert r["result"]["bodies"][0]["mass_g"] is None and "Sin densidad" in r["avisos"][0]


def test_material_solo_de_la_sesion_no_toca_el_archivo(biblioteca):
    s = api.Sesion()
    r = llamar(s, "define_material", name="Resina", density=1.1, save=False)
    assert r["saved"] is False and "library_file" not in r and not biblioteca.exists()
    assert "Resina" in an.TABLA_MATERIALES


def test_aspecto_de_biblioteca_y_color_propio():
    s = api.Sesion()
    pieza = cubo(s)
    r = llamar(s, "set_appearance", bodies=[pieza], appearance="aluminio - anodizado (rojo)")
    color, acabado = rc.aspecto("Aluminio - Anodizado (rojo)")
    assert r["bodies"][0]["appearance"] == "Aluminio - Anodizado (rojo)"
    assert s.doc.propiedad(pieza, "apariencia") == pytest.approx(color)
    assert s.doc.propiedad(pieza, "acabado")["metalico"] == acabado["metalico"]
    r = llamar(s, "set_appearance", bodies=[pieza], color=[255, 0, 0])
    assert r["bodies"][0]["color"] == "#ff0000" and s.doc.propiedad(pieza, "apariencia") == [1, 0, 0]
    assert s.doc.propiedad(pieza, "acabado") is None
    llamar(s, "set_appearance", bodies=[pieza], appearance="Goma - Negra", color="#00ff00")
    assert s.doc.propiedad(pieza, "apariencia") == [0, 1, 0]
    assert s.doc.propiedad(pieza, "acabado")["nombre"] == "Goma - Negra"
    r = llamar(s, "set_appearance", bodies=[pieza])
    assert r["cleared"] and s.doc.propiedad(pieza, "apariencia") is None and s.doc.propiedad(pieza, "acabado") is None
    llamar(s, "undo")                                                   # cada llamada es UN paso de deshacer
    assert s.doc.propiedad(pieza, "acabado")["nombre"] == "Goma - Negra"
    falla(s, "set_appearance", "NOT_FOUND", bodies=[pieza], appearance="Plutonio pulido")
    falla(s, "set_appearance", "INVALID_ARGUMENTS", bodies=[], color="#ffffff")
    aspectos = llamar(s, "list_materials")["appearances"]
    assert "Goma - Negra" in aspectos["Goma"] and set(aspectos) == set(rc.CATEGORIAS)


def test_lista_de_materiales_agrupa_piezas_iguales(tmp_path):
    s = api.Sesion()
    rueda = cubo(s)
    llamar(s, "create_component", bodies=[rueda], name="Rueda")
    llamar(s, "set_material", bodies=[rueda], material="Goma natural")
    llamar(s, "rectangular_pattern", bodies=[rueda], x_count=4, x_spacing=20)          # 4 ruedas iguales
    chasis = cubo(s, 20, x=200)                                                          # sin material: Acero
    r = llamar(s, "get_bill_of_materials", csv_path=str(tmp_path / "bom.csv"))
    filas = {f["name"]: f for f in r["rows"]}
    assert filas["Rueda"] == dict(filas["Rueda"], quantity=4, material="Goma natural", default_material=False,
                                  mass_g=0.93, volume=1000)
    assert filas["Cuerpo5"]["bodies"] == [chasis] and filas["Cuerpo5"]["default_material"] is True
    assert filas["Cuerpo5"]["mass_g"] == pytest.approx(8000 * 7.85e-3)
    assert r["pieces"] == 5 and r["total_mass_g"] == pytest.approx(4 * 0.93 + 62.8)
    lineas = (tmp_path / "bom.csv").read_text(encoding="utf-8").splitlines()
    assert lineas[0].startswith("N.º,Nombre,Cantidad") and len(lineas) == 3
    falla(s, "get_bill_of_materials", "FILE_EXISTS", csv_path=str(tmp_path / "bom.csv"))
