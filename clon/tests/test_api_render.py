# -*- coding: utf-8 -*-
"""Escena y cámara persistentes del render para agentes, sin ventana y con PNG reales pequeños."""
import copy
import io
import json

import numpy as np
import pytest
from PIL import Image

from omnicad import api
from omnicad.api import herramientas_render as hr
from omnicad.api.herramientas_render import _CLAVES, _tamano
from omnicad.nucleo import render_cpu as rc


def _llamar(sesion, nombre, **argumentos):
    respuesta = api.llamar(sesion, nombre, argumentos)
    assert respuesta["ok"], respuesta
    return respuesta["result"]


@pytest.fixture()
def sesion():
    s = api.Sesion()
    _llamar(s, "create_box", length=20, width=20, height=10)
    return s


def test_catalogo_y_descripciones():
    herramientas = api.catalogo("render")
    assert {h["nombre"] for h in herramientas} == {
        "list_render_environments", "get_render_scene", "set_render_scene", "set_render_camera", "render_image"}
    for h in herramientas:
        assert h["modifica"] == (h["nombre"] in {"set_render_scene", "set_render_camera"})
        assert all(p.get("description") for p in h["esquema"]["properties"].values())


def test_entornos_y_escena_inicial():
    s = api.Sesion()
    biblioteca = _llamar(s, "list_render_environments")
    assert len(biblioteca["environments"]) == len(rc.ENTORNOS) == 7
    assert biblioteca["default"] == rc.ESCENA_DEFECTO["entorno"]
    for entorno in biblioteca["environments"]:
        nombre, arriba, abajo, intensidad = rc.ENTORNOS[entorno["id"]]
        assert entorno == {"id": entorno["id"], "name": nombre, "top_color": list(arriba),
                           "bottom_color": list(abajo), "intensity": intensidad}
    escena = _llamar(s, "get_render_scene")
    assert set(_CLAVES.values()) == set(rc.ESCENA_DEFECTO)
    for ingles, clave in _CLAVES.items():
        esperado = {"background": "environment", "camera_type": "perspective"}.get(ingles, rc.ESCENA_DEFECTO[clave])
        assert escena[ingles] == esperado
    assert escena["canvas"] == {"high_quality": False, "supersampling": 2}
    assert escena["saved_camera"] is None
    assert "render" not in s.doc.espacios


def test_escena_guarda_conserva_y_deshace_en_un_paso(sesion):
    cam = _llamar(sesion, "set_render_camera", view="front")["camera"]
    sesion.doc.espacios["render"]["extra"] = {"valor": 42}
    sesion.doc.espacios["render"]["lienzo"]["extra"] = True
    antes = copy.deepcopy(sesion.doc.espacios)
    parametros = {"environment": "rubicon", "brightness": 2, "rotation": 45, "background": "color",
                  "background_color": [1, 0, 0], "ground": False, "reflections": False, "ground_roughness": 0.7,
                  "shadows": False, "ambient_occlusion": False, "camera_type": "orthographic",
                  "focal_length": 80, "exposure": 1, "canvas_high_quality": True, "canvas_supersampling": 3}
    escena = _llamar(sesion, "set_render_scene", **parametros)
    assert escena == _llamar(sesion, "get_render_scene")
    assert all(escena[k] == v for k, v in parametros.items() if not k.startswith("canvas_"))
    assert escena["saved_camera"] == cam
    assert escena["canvas"] == {"high_quality": True, "supersampling": 3}
    assert sesion.doc.espacios["render"]["extra"] == {"valor": 42}
    assert sesion.doc.espacios["render"]["lienzo"]["extra"] is True
    _llamar(sesion, "undo")
    assert sesion.doc.espacios == antes
    _llamar(sesion, "redo")
    assert _llamar(sesion, "get_render_scene") == escena


def test_formato_de_la_ventana_y_camara(sesion):
    _llamar(sesion, "set_render_scene", camera_type="orthographic", focal_length=60)
    resultado = _llamar(sesion, "set_render_camera", direction=[2, -3, 1], distance=123)
    assert resultado["view"] == "custom"
    datos = sesion.doc.espacios["render"]
    assert set(datos) == {"version", "escena", "camara", "lienzo"}
    assert datos["version"] == 1 and set(datos["escena"]) == set(rc.ESCENA_DEFECTO)
    assert datos["lienzo"] == {"alta_calidad": False, "supermuestreo": 2}
    cam = datos["camara"]
    assert cam == rc.camara(cam["R"], cam["objetivo"], 123, rc.focal_a_fov(60), True)
    assert np.asarray(cam["R"]) @ np.asarray(cam["R"]).T == pytest.approx(np.eye(3))
    assert np.asarray(cam["R"])[2] == pytest.approx(np.array([2, -3, 1]) / np.linalg.norm([2, -3, 1]))
    assert json.loads(json.dumps(datos)) == datos
    assert _llamar(sesion, "get_render_scene")["saved_camera"] == cam
    assert _llamar(sesion, "set_render_camera", clear=True) == {"camera": None, "view": None}
    assert _llamar(sesion, "get_render_scene")["saved_camera"] is None


def test_normalizacion_avisa(sesion):
    r = api.llamar(sesion, "set_render_scene", {"brightness": 9, "rotation": -10, "background_color": [2, -1, 0.5],
                                              "ground_roughness": -1, "focal_length": 1, "exposure": 20})
    assert r["ok"], r
    assert len(r["avisos"]) == 6
    escena = r["result"]
    assert escena["brightness"] == 4 and escena["rotation"] == 350
    assert escena["background_color"] == [1, 0, 0.5] and escena["ground_roughness"] == 0
    assert escena["focal_length"] == 8 and escena["exposure"] == 6


@pytest.mark.parametrize("argumentos", [{}, {"environment": "inexistente"}, {"background_color": [1, 0]},
                                       {"brightness": float("nan")}, {"rotation": float("inf")},
                                       {"canvas_supersampling": 0}, {"canvas_supersampling": 4},
                                       {"background": "invalido"}, {"camera_type": "invalida"}])
def test_escena_invalida_no_modifica(sesion, argumentos):
    antes = copy.deepcopy(sesion.doc.espacios)
    r = api.llamar(sesion, "set_render_scene", argumentos)
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS", r
    assert sesion.doc.espacios == antes
    if "environment" in argumentos:
        assert all(clave in " ".join(r["pistas"]) for clave in rc.ENTORNOS)


@pytest.mark.parametrize("argumentos", [{"direction": [0, 0, 0]}, {"direction": [1, 2]},
                                       {"direction": [float("inf"), 0, 0]}, {"distance": 0},
                                       {"distance": float("nan")}])
def test_camara_invalida(sesion, argumentos):
    r = api.llamar(sesion, "set_render_camera", argumentos)
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS", r
    assert "render" not in sesion.doc.espacios


def test_png_real_fondo_guardado_transparencia_y_archivo(sesion, tmp_path):
    _llamar(sesion, "set_render_scene", background="color", background_color=[1, 0, 0], ground=False)
    _llamar(sesion, "set_render_camera", view="front")
    antes = copy.deepcopy(sesion.doc.espacios)
    ruta = tmp_path / "render.png"
    resultado = _llamar(sesion, "render_image", width=32, height=24, quality="draft", path=str(ruta))
    assert resultado["width"] == 32 and resultado["height"] == 24 and resultado["seconds"] >= 0
    assert resultado["image"].ancho == 32 and resultado["image"].alto == 24
    assert resultado["path"] == str(ruta)
    assert resultado["image"].png.startswith(b"\x89PNG\r\n\x1a\n")
    assert ruta.read_bytes() == resultado["image"].png
    with Image.open(io.BytesIO(resultado["image"].png)) as imagen:
        assert imagen.size == (32, 24) and imagen.getpixel((0, 0)) == (255, 0, 0)
        assert np.any(np.asarray(imagen) != [255, 0, 0])
    r = api.llamar(sesion, "render_image", {"width": 32, "height": 24, "path": str(ruta)})
    assert not r["ok"] and r["error_kind"] == "FILE_EXISTS", r
    assert ruta.read_bytes() == resultado["image"].png
    assert sesion.doc.espacios == antes
    _llamar(sesion, "set_render_scene", background_color=[0, 0, 1])
    azul = _llamar(sesion, "render_image", width=32, height=24, quality="standard", path=str(ruta), overwrite=True)
    assert azul["image"].png != resultado["image"].png
    with Image.open(ruta) as imagen:
        assert imagen.getpixel((0, 0)) == (0, 0, 255)
    transparente = _llamar(sesion, "render_image", width=32, height=24, quality="final", transparent_background=True)
    assert transparente["path"] is None
    with Image.open(io.BytesIO(transparente["image"].png)) as imagen:
        assert imagen.mode == "RGBA" and imagen.getpixel((0, 0))[3] == 0
        assert np.asarray(imagen)[..., 3].max() == 255


def test_render_usa_camara_escena_y_calcomanias(sesion, monkeypatch):
    cid = next(iter(sesion.doc.estado_final.cuerpos))
    _llamar(sesion, "set_render_camera", view="front", distance=120)
    _llamar(sesion, "set_render_scene", environment="azul_tranquilidad", camera_type="orthographic", focal_length=70)
    cam_guardada = copy.deepcopy(sesion.doc.espacios["render"]["camara"])
    calcomania = {"calcomania": True, "cuerpo": cid}
    monkeypatch.setattr(hr, "calcomanias_vigentes", lambda doc, estado: [
        (0, calcomania), (1, {"calcomania": True, "cuerpo": "otro"}), (2, {"cuerpo": cid})])
    llamadas = []

    def capturar(objetos, cam, escena, ancho, alto, **opciones):
        llamadas.append((cam, escena, opciones))
        assert objetos and opciones["z_suelo"] == pytest.approx(0, abs=1e-5)
        return np.zeros((alto, ancho, 4), dtype=np.uint8)

    monkeypatch.setattr(rc, "renderizar", capturar)
    _llamar(sesion, "render_image", width=32, height=24, bodies=[cid])
    cam, escena, opciones = llamadas[-1]
    assert cam["R"] == cam_guardada["R"] and cam["distancia"] == 120
    assert cam["ortografica"] and cam["fov"] == rc.focal_a_fov(70)
    assert escena == rc.escena_normalizada(sesion.doc.espacios["render"]["escena"])
    assert opciones["cielo"] == rc.cielo_de("azul_tranquilidad")
    assert opciones["calcomanias"] == [calcomania]
    assert opciones["supermuestreo"] == 2 and opciones["mosaico"] == 2048
    _llamar(sesion, "render_image", width=32, height=24, view="top", direction=[1, 0, 0])
    assert llamadas[-1][0]["R"][2] == [1, 0, 0]
    assert sesion.doc.espacios["render"]["camara"] == cam_guardada


def test_presets_sin_render_grande():
    assert _tamano(32, 24, "full_hd", "final") == (1920, 1080, 3)
    assert _tamano(32, 24, "hd", "standard") == (1280, 720, 2)
    assert _tamano(32, 24, "web", "draft") == (1024, 768, 1)


@pytest.mark.parametrize("argumentos", [{"width": 15}, {"height": 4097},
                                       {"width": 4096, "height": 4096, "quality": "standard"}])
def test_tamano_invalido(argumentos):
    r = api.llamar(api.Sesion(), "render_image", argumentos)
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS", r


def test_sin_cuerpos():
    s = api.Sesion()
    for nombre in ("render_image", "set_render_camera"):
        r = api.llamar(s, nombre, {})
        assert not r["ok"] and r["error_kind"] == "NOTHING_TO_RENDER", r
    assert _llamar(s, "set_render_camera", clear=True)["camera"] is None


def test_rutas_invalidas_antes_de_renderizar(sesion, tmp_path):
    for ruta, kind in ((tmp_path / "imagen.jpg", "INVALID_ARGUMENTS"),
                       (tmp_path / "no_existe" / "imagen.png", "FILE_NOT_FOUND")):
        r = api.llamar(sesion, "render_image", {"path": str(ruta), "width": 32, "height": 24})
        assert not r["ok"] and r["error_kind"] == kind, r
