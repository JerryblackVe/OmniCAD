"""Cámaras, vistas guardadas y modos del visor sin Qt."""
import copy
import io
import json
import math

import numpy as np
import pytest
from PIL import Image

from omnicad import api
from omnicad.api import herramientas_inspeccion as hi
from omnicad.nucleo import geometria as geo


def llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def falla(s, nombre, kind="INVALID_ARGUMENTS", **args):
    antes = json.dumps(s.doc.a_dict(), sort_keys=True)
    r = api.llamar(s, nombre, args)
    assert not r["ok"] and r["error_kind"] == kind, r
    assert json.dumps(s.doc.a_dict(), sort_keys=True) == antes
    return r


@pytest.fixture
def s():
    sesion = api.Sesion()
    llamar(sesion, "create_box", length=20, width=20, height=20)
    assert geo.es_valida(next(iter(sesion.doc.estado_final.cuerpos.values())).forma)
    return sesion


def imagen(s, **args):
    return np.array(Image.open(io.BytesIO(llamar(s, "get_viewport_image", width=128, height=128, **args)["image"].png)))


def test_set_view_direccion_zoom_objetivo_orbita_y_deshacer(s):
    cam = llamar(s, "set_view", view="front")["camera"]
    assert cam["R"][2] == [0, -1, 0]
    distancia = cam["distancia"]
    assert distancia == pytest.approx((10 + 10 / math.tan(math.radians(20))) * 1.06)
    n = len(s.doc._deshacer)
    giro = llamar(s, "set_view", view="front", azimuth=90, elevation=30, zoom=2, look_at=[1, 2, 3])["camera"]
    assert giro["R"][2] == pytest.approx([math.sqrt(3) / 2, 0, 0.5], abs=1e-12)
    assert giro["objetivo"] == [1, 2, 3] and len(s.doc._deshacer) == n + 1
    base = llamar(s, "set_view", direction=giro["R"][2])["camera"]
    assert base["distancia"] == pytest.approx(giro["distancia"] * 2)
    llamar(s, "undo")
    assert s.doc.espacios["visor"]["camara"] == giro
    llamar(s, "set_view", clear=True)
    assert s.doc.espacios["visor"]["camara"] is None
    llamar(s, "undo")
    assert s.doc.espacios["visor"]["camara"] == giro
    assert distancia > 20


@pytest.mark.parametrize("args", [{"zoom": 0}, {"zoom": float("inf")}, {"direction": [0, 0, 0]},
                                {"look_at": [1, 2]}, {"view": "inexistente"}, {"bodies": ["nada"]}])
def test_set_view_errores_atomicos(s, args):
    falla(s, "set_view", kind="BODY_NOT_FOUND" if "bodies" in args else "INVALID_ARGUMENTS", **args)


def test_vistas_guardadas_compatibles_imagen_y_deshacer(s):
    cam = llamar(s, "set_view", view="front", projection="orthographic")["camera"]
    antes = imagen(s)
    assert llamar(s, "manage_named_views", action="save", name="Frontal")["count"] == 1
    assert s.doc.vistas["Frontal"]["camara"] == "ortografica"
    assert s.doc.vistas["Frontal"]["R"] == cam["R"]
    llamar(s, "set_view", view="top")
    assert np.array_equal(imagen(s, view="Frontal"), antes)
    llamar(s, "manage_named_views", action="apply", name="Frontal")
    assert np.array_equal(imagen(s), antes)
    llamar(s, "manage_named_views", action="rename", name="Frontal", new_name="Guardada")
    assert llamar(s, "manage_named_views", action="list")["count"] == 1
    llamar(s, "manage_named_views", action="delete", name="Guardada")
    assert not s.doc.vistas
    # como en la ventana, las vistas guardadas se guardan con el proyecto pero no entran en deshacer
    pasos = len(s.doc._deshacer)
    llamar(s, "manage_named_views", action="save", name="Guardada")
    assert len(s.doc._deshacer) == pasos                       # ni un Ctrl+Z que no deshace nada
    falla(s, "manage_named_views", action="save", name="Guardada")
    falla(s, "manage_named_views", action="apply", name="Ausente")
    falla(s, "manage_named_views", action="rename", name="Guardada", new_name="iso")
    falla(s, "get_viewport_image", view="Ausente")


def test_ortografica_ancho_de_silueta_medido_en_pixeles(s):
    cam = llamar(s, "set_view", view="front", projection="orthographic")["camera"]
    img = imagen(s)
    # En la fila central no hay sombras del suelo; el fondo se mide en sus extremos.
    fila = img[64].astype(float)
    fondo = np.linspace(fila[0], fila[-1], len(fila))
    xs = np.flatnonzero(np.linalg.norm(fila - fondo, axis=1) > 25)
    escala = 128 / (2 * cam["distancia"] * math.tan(math.radians(cam["fov"]) / 2))
    assert xs[-1] - xs[0] + 1 == pytest.approx(20 * escala, abs=3)
    assert np.count_nonzero(imagen(s, camera="perspective") != img) > 100
    falla(s, "get_viewport_image", camera="otra")


def test_rejilla_agrega_pixeles_guarda_opciones_y_deshace(s):
    antes = imagen(s, view="iso")
    estado = llamar(s, "set_grid", show=True, snap=True, four_views=True)
    assert sum(estado.values()) == 3
    assert np.count_nonzero(imagen(s, view="iso") != antes) > 100
    llamar(s, "set_grid", snap=False)
    assert s.doc.espacios["visor"]["rejilla"] == {"mostrar": True, "forzar": False, "cuatro_vistas": True}
    llamar(s, "undo")
    assert llamar(s, "set_grid")["snap"] is True
    falla(s, "set_grid", show="sí")


def test_aislar_restaurar_y_deshacer(s):
    segundo = llamar(s, "create_box", length=10, width=10, height=10, x=50)["bodies_created"][0]["id"]
    primero = next(iter(s.doc.estado_final.cuerpos))
    assert llamar(s, "isolate_bodies", bodies=[segundo])["count"] == 1
    assert s.doc.propiedad("__navegador__", "ocultos") == [primero]
    assert llamar(s, "get_viewport_image", width=32, height=32)["bodies"] == [segundo]
    assert llamar(s, "isolate_bodies", restore=True)["count"] == 2
    llamar(s, "undo")
    assert s.doc.propiedad("__navegador__", "ocultos") == [primero]
    falla(s, "isolate_bodies")
    falla(s, "isolate_bodies", kind="BODY_NOT_FOUND", bodies=["ausente"])


def test_colores_componente_cambian_pixeles_y_sueltos_conservan_color(s):
    cid = next(iter(s.doc.estado_final.cuerpos))
    assert np.array_equal(imagen(s), imagen(s, component_colors=True))
    llamar(s, "create_component", bodies=[cid], name="Pieza")
    normal, colores = imagen(s), imagen(s, component_colors=True)
    assert np.count_nonzero(normal != colores) > 100
    objetos = hi._objetos_render(s, [s.cuerpo(cid)], colores_componente=True)
    assert objetos[0]["color"] == (0.62, 0.68, 0.76)


def test_patron_plano_muestra_solo_desarrollo_y_deshace(s):
    cid = next(iter(s.doc.estado_final.cuerpos))
    llamar(s, "convert_to_sheet_metal", face=">Z", body=cid)
    patron = llamar(s, "create_flat_pattern", face=">Z", body=cid, location="beside")["bodies_created"][0]["id"]
    assert geo.es_valida(s.cuerpo(patron).forma)
    caja = geo.caja_envolvente(s.cuerpo(patron).forma)
    llamar(s, "set_flat_pattern_view", body=cid)
    r = llamar(s, "get_viewport_image", view="top", width=64, height=64)
    assert r["bodies"] == [patron]
    esperado = imagen(s, view="top")
    llamar(s, "set_flat_pattern_view", active=False)
    assert llamar(s, "get_viewport_image", width=32, height=32)["bodies"] == [cid]
    llamar(s, "undo")
    assert s.doc.espacios["visor"]["patron_activo"] == patron
    assert np.array_equal(imagen(s, view="top"), esperado)
    assert np.subtract(caja[1], caja[0]) == pytest.approx([20, 20, 20], abs=1e-5)
    falla(s, "set_flat_pattern_view", kind="BODY_NOT_FOUND", body="ausente")
    vacia = api.Sesion()
    r = falla(vacia, "set_flat_pattern_view")
    assert "create_flat_pattern" in " ".join(r["pistas"])


def test_estado_visor_serializable_y_lectura_no_modifica(s):
    llamar(s, "set_view", direction=[1e300, -1e300, 1e300])
    llamar(s, "manage_named_views", action="save", name="Grande")
    antes = copy.deepcopy(s.doc.a_dict())
    imagen(s)
    assert s.doc.a_dict() == antes
    json.dumps(antes, allow_nan=False)
