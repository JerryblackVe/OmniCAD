# -*- coding: utf-8 -*-
"""B-183: el render final respeta el Análisis de sección: corta con el mismo plano que el visor y dibuja su tapa."""
import io

import numpy as np
from PIL import Image

from omnicad import api


def _llamar(sesion, nombre, **argumentos):
    respuesta = api.llamar(sesion, nombre, argumentos)
    assert respuesta["ok"], respuesta
    return respuesta["result"]


def _pixeles(resultado):
    with Image.open(io.BytesIO(resultado["image"].png)) as imagen:
        return np.asarray(imagen.convert("RGB")).astype(int)


def _sesion():
    """Una caja de 40³ (de z = 0 a z = 40), con fondo liso y cámara de frente ortográfica."""
    s = api.Sesion()
    _llamar(s, "create_box", length=40, width=40, height=40)
    _llamar(s, "set_render_scene", background="color", background_color=[0.2, 0.2, 0.2], ground=False,
            reflections=False, shadows=False, ambient_occlusion=False, camera_type="orthographic")
    _llamar(s, "set_render_camera", view="front")
    return s


def test_el_render_corta_con_el_mismo_plano_que_el_visor():
    """La sección a la mitad deja la mitad de arriba sin un solo píxel de la pieza."""
    s = _sesion()
    entera = _pixeles(_llamar(s, "render_image", width=64, height=64, quality="draft"))
    _llamar(s, "section_view", plane="XY", offset=20)              # la caja va de z = 0 a 40: corte a la mitad
    cortada = _pixeles(_llamar(s, "render_image", width=64, height=64, quality="draft"))
    fondo = entera[0, 0]
    distintos = int((np.abs(entera - cortada).sum(axis=2) > 12).sum())
    assert distintos > 0.05 * entera.shape[0] * entera.shape[1]       # más del 5 % de los píxeles cambian
    filas = np.nonzero((np.abs(entera - fondo).sum(axis=2) > 12).any(axis=1))[0]
    assert len(filas) > 40                                          # la pieza llena la altura de la imagen
    mitad = (filas[0] + filas[-1]) // 2
    arriba = np.abs(cortada - fondo).sum(axis=2) > 12
    assert not arriba[:mitad - 3].any()                              # la mitad de arriba: ni un píxel de la pieza
    assert arriba[mitad + 3:].any()                                 # la mitad de abajo: la pieza está


def test_con_la_seccion_oculta_el_render_sale_igual_que_sin_seccion():
    s = _sesion()
    entera = _pixeles(_llamar(s, "render_image", width=64, height=64, quality="draft"))
    nombre = _llamar(s, "section_view", plane="XY", offset=20)["analysis"]["name"]
    _llamar(s, "manage_analysis", action="hide", name=nombre)
    assert np.array_equal(_pixeles(_llamar(s, "render_image", width=64, height=64, quality="draft")), entera)


def test_la_seccion_invertida_corta_del_otro_lado():
    """Con flip la sección se queda con la otra mitad: el render corta igual que el visor."""
    s = _sesion()
    entera = _pixeles(_llamar(s, "render_image", width=64, height=64, quality="draft"))
    _llamar(s, "section_view", plane="XY", offset=20, flip=True)
    imagen = _pixeles(_llamar(s, "render_image", width=64, height=64, quality="draft"))
    fondo = entera[0, 0]
    filas = np.nonzero((np.abs(entera - fondo).sum(axis=2) > 12).any(axis=1))[0]
    mitad = (filas[0] + filas[-1]) // 2
    pieza = np.abs(imagen - fondo).sum(axis=2) > 12
    assert pieza[:mitad - 3].any()                                    # la pieza queda arriba
    assert not pieza[mitad + 3:].any()                                # la mitad de abajo: nada


def test_el_render_dibuja_la_tapa_del_corte():
    """Desde la isométrica se ve la tapa del corte, del color de la sección (como en el visor)."""
    s = api.Sesion()
    _llamar(s, "create_box", length=40, width=40, height=40)
    _llamar(s, "set_render_scene", background="color", background_color=[0.2, 0.2, 0.2], ground=False,
            reflections=False, shadows=False, ambient_occlusion=False)
    _llamar(s, "set_render_camera", view="iso")
    _llamar(s, "section_view", plane="XY", offset=20)
    imagen = _pixeles(_llamar(s, "render_image", width=64, height=64, quality="draft"))
    rojas = ((imagen[..., 0] > imagen[..., 1] + 60) & (imagen[..., 0] > imagen[..., 2] + 60)).sum()
    assert rojas > 50                                                # la tapa de la sección
