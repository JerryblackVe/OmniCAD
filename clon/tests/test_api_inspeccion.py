# -*- coding: utf-8 -*-
import json
import struct

import pytest

from omnicad import api
from omnicad.ejemplo import crear_documento_ejemplo

FIRMA_PNG = b"\x89PNG\r\n\x1a\n"


@pytest.fixture
def s():
    return api.Sesion(crear_documento_ejemplo())


def ok(r):
    assert r["ok"], r
    return r["result"]


@pytest.fixture
def dos_cajas():
    """Dos cajas de 20 mm que se superponen 10 mm en X: volumen común 10 × 20 × 20 = 4000 mm³."""
    sesion = api.Sesion()
    caja(sesion, "A", "0")
    caja(sesion, "B", "10 mm")
    return sesion


def caja(sesion, nombre, x):
    """Caja de 20 mm en X = x, con el cuerpo renombrado (`name` de run_operation nombra el PASO, no el cuerpo)."""
    nuevo = ok(api.llamar(sesion, "run_operation", {"type": "primitiva", "params": {"x": x}}))["new_bodies"][0]
    ok(api.llamar(sesion, "rename", {"target": nuevo, "new_name": nombre, "kind": "body"}))


def dimensiones_png(imagen):
    assert imagen.png[:8] == FIRMA_PNG and imagen.png[12:16] == b"IHDR"
    return struct.unpack(">II", imagen.png[16:24])


def test_imagen_del_ejemplo_es_png_del_tamano_pedido_y_rapida(s):
    r = ok(api.llamar(s, "get_viewport_image", {"view": "iso", "width": 640, "height": 480}))
    assert dimensiones_png(r["image"]) == (640, 480) == (r["image"].ancho, r["image"].alto)
    assert r["view"] == "iso" and r["bodies"] == ["op2.c1", "op6.c1"]
    print(f"get_viewport_image 640x480 del ejemplo: {r['seconds']} s")
    assert r["seconds"] < 6.0          # objetivo 2 s en una máquina libre; el margen evita falsos rojos en CI


@pytest.mark.parametrize("vista", ["front", "back", "top", "bottom", "left", "right"])
def test_todas_las_vistas_dan_imagen(s, vista):
    r = ok(api.llamar(s, "get_viewport_image", {"view": vista, "width": 160, "height": 120}))
    assert dimensiones_png(r["image"]) == (160, 120) and r["view"] == vista


def test_imagen_direccion_propia_cuerpos_y_encuadre(s):
    todo = ok(api.llamar(s, "get_viewport_image", {"width": 160, "height": 120}))
    uno = ok(api.llamar(s, "get_viewport_image", {"width": 160, "height": 120, "bodies": ["Cuerpo1"], "direction": [1, 1, 1]}))
    assert uno["view"] == "custom" and uno["bodies"] == ["op2.c1"]
    assert uno["image"].png != todo["image"].png
    fijo = ok(api.llamar(s, "get_viewport_image", {"width": 160, "height": 120, "bodies": ["Cuerpo1"], "fit": False}))
    ajustado = ok(api.llamar(s, "get_viewport_image", {"width": 160, "height": 120, "bodies": ["Cuerpo1"]}))
    assert fijo["image"].png != ajustado["image"].png      # fit=False deja el encuadre de toda la escena


def test_imagen_no_es_toda_del_mismo_color(s):
    from io import BytesIO

    from PIL import Image
    img = Image.open(BytesIO(ok(api.llamar(s, "get_viewport_image", {"width": 160, "height": 120}))["image"].png))
    assert len(img.convert("RGB").getcolors(maxcolors=100000)) > 50      # hay un modelo dibujado, no un fondo liso


def test_errores_de_la_imagen(s):
    r = api.llamar(api.Sesion(), "get_viewport_image", {})
    assert not r["ok"] and r["error_kind"] == "NOTHING_TO_RENDER"
    for args in ({"width": 8}, {"height": 5000}, {"direction": [0, 0, 0]}, {"direction": [1, 2]}, {"view": "arriba"}):
        r = api.llamar(s, "get_viewport_image", args)
        assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS", args
    assert api.llamar(s, "get_viewport_image", {"bodies": ["nada"]})["error_kind"] == "BODY_NOT_FOUND"


def test_propiedades_coinciden_con_la_escena(s):
    escena = {b["id"]: b for b in ok(api.llamar(s, "get_scene_info"))["bodies"]}
    p = ok(api.llamar(s, "get_physical_properties"))
    assert len(p["bodies"]) == 2
    for b in p["bodies"]:
        e = escena[b["id"]]
        assert b["volume"] == e["volume"] and b["area"] == e["area"] and b["bounding_box"] == e["bounding_box"]
        assert b["mass_g"] is None and len(b["center_of_mass"]) == 3
    assert p["total"]["volume"] == pytest.approx(sum(e["volume"] for e in escena.values()), abs=1e-3)
    assert p["total"]["mass_g"] is None and p["total"]["center_of_mass_basis"] == "volume"
    assert p["total"]["bounding_box"]["min"] == pytest.approx([-86, -86, 0], abs=1e-3)
    assert p["total"]["bounding_box"]["max"] == pytest.approx([86, 86, 20], abs=1e-3)
    assert api.llamar(s, "get_physical_properties", {})["avisos"]      # avisa que falta la densidad
    json.dumps(p)


def test_masa_con_densidad_y_con_material(s):
    d = ok(api.llamar(s, "get_physical_properties", {"bodies": ["op2.c1"], "density": 2.7}))
    assert d["bodies"][0]["mass_g"] == pytest.approx(d["bodies"][0]["volume"] * 2.7e-3, rel=1e-6)
    assert d["total"]["mass_g"] == pytest.approx(d["bodies"][0]["mass_g"], rel=1e-6)
    assert d["total"]["center_of_mass_basis"] == "mass"
    s.doc.set_propiedad(["op2.c1"], "material", "Acero")
    m = ok(api.llamar(s, "get_physical_properties", {"bodies": ["op2.c1"]}))
    assert m["bodies"][0]["material"] == "Acero" and m["bodies"][0]["density_g_cm3"] == pytest.approx(7.85)
    assert m["bodies"][0]["mass_g"] == pytest.approx(m["bodies"][0]["volume"] * 7.85e-3, rel=1e-6)
    for malo in (0, -1):
        assert api.llamar(s, "get_physical_properties", {"density": malo})["error_kind"] == "INVALID_ARGUMENTS"
    assert api.llamar(api.Sesion(), "get_physical_properties", {})["error_kind"] == "NOTHING_TO_MEASURE"


def test_centro_de_masa_de_una_caja(dos_cajas):
    p = ok(api.llamar(dos_cajas, "get_physical_properties", {"bodies": ["A"], "density": 1.0}))
    assert p["bodies"][0]["center_of_mass"] == pytest.approx([10, 10, 10], abs=1e-6)
    assert p["bodies"][0]["volume"] == pytest.approx(8000, abs=1e-6) and p["total"]["mass_g"] == pytest.approx(8.0)


def test_medir_cuerpo_a_punto_y_entre_puntos(s):
    r = ok(api.llamar(s, "measure_distance", {"a": "op2.c1", "b": [100, 0, 0]}))
    assert r["distance"] == pytest.approx(40.0, abs=1e-4)
    assert r["point_a"] == pytest.approx([60, 0, 0], abs=1e-4) and r["point_b"] == [100, 0, 0]
    assert r["delta"] == pytest.approx([40, 0, 0], abs=1e-4) and r["a"]["kind"] == "body" and r["b"]["kind"] == "point"
    r = ok(api.llamar(s, "measure_distance", {"a": [0, 0, 0], "b": [3, 4, 0]}))
    assert r["distance"] == pytest.approx(5.0) and r["intersecting"] is False


def test_medir_entre_cuerpos(dos_cajas):
    caja(dos_cajas, "C", "50 mm")
    r = ok(api.llamar(dos_cajas, "measure_distance", {"a": "A", "b": "C"}))
    assert r["distance"] == pytest.approx(30.0, abs=1e-4) and r["intersecting"] is False
    assert r["point_a"][0] == pytest.approx(20.0, abs=1e-4) and r["point_b"][0] == pytest.approx(50.0, abs=1e-4)
    assert ok(api.llamar(dos_cajas, "measure_distance", {"a": "A", "b": "B"}))["intersecting"] is True


def test_medir_errores(s):
    assert api.llamar(s, "measure_distance", {"a": "no_existe", "b": [0, 0, 0]})["error_kind"] == "BODY_NOT_FOUND"
    for malo in ([1, 2], [1, 2, "x"], []):
        assert api.llamar(s, "measure_distance", {"a": malo, "b": [0, 0, 0]})["error_kind"] == "INVALID_ARGUMENTS"
    assert api.llamar(s, "measure_distance", {"a": 5, "b": [0, 0, 0]})["error_kind"] == "INVALID_ARGUMENTS"


def test_interferencia_del_ejemplo_no_hay(s):
    r = ok(api.llamar(s, "check_interference"))
    assert r["checked"] == 2 and r["count"] == 0 and r["pairs"] == [] and r["interference"] is False


def test_interferencia_de_dos_cajas(dos_cajas):
    r = ok(api.llamar(dos_cajas, "check_interference"))
    assert r["count"] == 1 and r["interference"] is True
    par = r["pairs"][0]
    assert {par["a"]["name"], par["b"]["name"]} == {"A", "B"} and par["volume"] == pytest.approx(4000, abs=1e-3)
    assert par["bounding_box"]["min"] == pytest.approx([10, 0, 0], abs=1e-4)
    assert par["bounding_box"]["max"] == pytest.approx([20, 20, 20], abs=1e-4)
    uno = api.llamar(dos_cajas, "check_interference", {"bodies": ["A"]})
    assert uno["ok"] and uno["result"]["count"] == 0 and uno["avisos"]


def test_inspeccion_no_modifica_el_documento(s):
    antes = json.dumps(s.doc.a_dict(), sort_keys=True), len(s.doc._deshacer)
    for nombre, args in (("get_viewport_image", {"width": 64, "height": 48}), ("get_physical_properties", {}),
                         ("measure_distance", {"a": "op2.c1", "b": [0, 0, 0]}), ("check_interference", {})):
        ok(api.llamar(s, nombre, args))
    assert (json.dumps(s.doc.a_dict(), sort_keys=True), len(s.doc._deshacer)) == antes


# ViewCube de Fusion con Z arriba (el mismo que el de la app, ui/superposiciones.CARAS). Filas de R de la cámara:
# derecha de la imagen, arriba de la imagen y hacia el ojo (dónde está la cámara respecto del modelo).
_VIEWCUBE = {"front": ((1, 0, 0), (0, 0, 1), (0, -1, 0)), "back": ((-1, 0, 0), (0, 0, 1), (0, 1, 0)),
             "right": ((0, 1, 0), (0, 0, 1), (1, 0, 0)), "left": ((0, -1, 0), (0, 0, 1), (-1, 0, 0)),
             "top": ((1, 0, 0), (0, 1, 0), (0, 0, 1)), "bottom": ((1, 0, 0), (0, -1, 0), (0, 0, -1))}


@pytest.mark.parametrize("vista", sorted(_VIEWCUBE))
def test_vistas_estandar_como_el_viewcube_de_fusion(vista):
    """«right» mostró la trasera de un auto con el frente hacia -X: las vistas llevan el nombre de los ejes del
    mundo, como el ViewCube de Fusion (right = cámara en +X, se ve la cara +X), no del frente de la pieza."""
    import numpy as np
    from omnicad.api import herramientas_inspeccion as hi
    cam, _ = hi._camara(hi._VISTAS[vista], hi._esquinas([((0.0, 0.0, 0.0), (10.0, 10.0, 10.0))]), 4 / 3, 40.0)
    assert np.allclose(cam["R"], _VIEWCUBE[vista], atol=1e-12)


def test_vista_iso_es_la_isometrica_del_visor():
    """La «iso» de la API tenía 30° de elevación y la del visor (y la esquina del ViewCube) 35,26°."""
    import math

    import numpy as np
    from omnicad.api import herramientas_inspeccion as hi
    cam, _ = hi._camara(hi._VISTAS["iso"], hi._esquinas([((0.0, 0.0, 0.0), (10.0, 10.0, 10.0))]), 4 / 3, 40.0)
    atras = np.asarray(cam["R"])[2]
    assert math.degrees(math.asin(atras[2])) == pytest.approx(35.264, abs=1e-3)       # visor3d.VISTAS["iso"]
    assert math.degrees(math.atan2(atras[1], atras[0])) == pytest.approx(-45.0)        # esquina frente-derecha


@pytest.mark.parametrize("vista", ["iso", "front", "top", "right"])
def test_encuadre_contiene_toda_la_caja(vista):
    """Regresión: la cámara se ajustaba con 2 esquinas de la caja y un soporte en L salía recortado."""
    import numpy as np
    from omnicad.api import herramientas_inspeccion as hi
    from omnicad.nucleo import render_cpu as rc
    caja = ((0.0, 0.0, 0.0), (80.0, 8.0, 40.0))
    cam, _ = hi._camara(hi._VISTAS[vista], hi._esquinas([caja]), 4 / 3, 40.0)
    proy, vista_m = rc.matrices_camara(cam, 4 / 3)
    p = np.c_[hi._esquinas([caja]), np.ones(8)] @ (proy @ vista_m).T
    ndc = p[:, :2] / p[:, 3:4]
    assert np.all(np.abs(ndc) <= 1.0 + 1e-9)
