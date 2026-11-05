# -*- coding: utf-8 -*-
"""Espacio RENDERIZAR para agentes, con persistencia compatible con la ventana y sin Qt."""
import copy
import io
import math
import time
from pathlib import Path
from typing import Literal

import numpy as np

from ..nucleo import geometria as geo
from ..nucleo import render_cpu as rc
from ..timeline.ops_insertar import calcomanias_vigentes
from .errores import error
from .herramientas_inspeccion import _VISTAS, _camara, _con_analisis, _cuerpos, _es_malla, _esquinas, _objetos_render
from .registro import Imagen, herramienta


_CLAVES = {
    "environment": "entorno", "brightness": "brillo", "rotation": "rotacion", "background": "fondo",
    "background_color": "color_fondo", "ground": "suelo", "reflections": "reflejos",
    "ground_roughness": "rugosidad_suelo", "shadows": "sombras", "ambient_occlusion": "oclusion",
    "camera_type": "camara", "focal_length": "focal", "exposure": "exposicion",
}
# Mismos tamaños y supermuestreos que ui/render.py; sin importarlo para mantener la API sin Qt.
_PRESETS = {"web": (1024, 768), "hd": (1280, 720), "full_hd": (1920, 1080)}
_CALIDADES = {"draft": 1, "standard": 2, "final": 3}
# Tope de píxeles que se calculan en un render (el supermuestreo los multiplica): es el presupuesto de memoria del
# render por CPU de la API. La ventana de RENDERIZAR usa la placa y tiene su propio límite.
TOPE_PIXELES = 25_000_000
_SUPERMUESTREOS = (3, 2, 1.5, 1)     # escalones del supermuestreo: si el pedido no entra, se baja de escalón en escalón
# Mosaico del renderizador (el mismo que usa la ventana): con 2048 el render grande pide el doble de memoria
# (los temporales del mosaico) y no entra en el tope.
_MOSAICO = 1024


def _datos(sesion):
    """Copia del espacio con los valores iniciales del lienzo, sin modificar el documento al leer."""
    datos = copy.deepcopy(sesion.doc.espacios.get("render") or {})
    datos.setdefault("version", 1)
    datos.setdefault("escena", {})
    datos.setdefault("camara", None)
    datos["lienzo"] = {"alta_calidad": False, "supermuestreo": 2, **(datos.get("lienzo") or {})}
    return datos


@herramienta("list_render_environments", "render", "Lista la biblioteca de entornos del render y el entorno inicial.")
def list_render_environments(sesion):
    return {"environments": [{"id": clave, "name": nombre, "top_color": list(arriba),
                              "bottom_color": list(abajo), "intensity": intensidad}
                             for clave, (nombre, arriba, abajo, intensidad) in rc.ENTORNOS.items()],
            "default": rc.ESCENA_DEFECTO["entorno"]}


@herramienta("get_render_scene", "render", "Devuelve la escena, las opciones del lienzo y la cámara guardada.")
def get_render_scene(sesion):
    datos = _datos(sesion)
    escena = rc.escena_normalizada(datos.get("escena"))
    resultado = {ingles: escena[clave] for ingles, clave in _CLAVES.items()}
    resultado["background"] = "environment" if escena["fondo"] == "entorno" else "color"
    resultado["camera_type"] = "orthographic" if escena["camara"] == "ortografica" else "perspective"
    resultado["canvas"] = {"high_quality": bool(datos["lienzo"]["alta_calidad"]),
                           "supersampling": int(datos["lienzo"]["supermuestreo"])}
    resultado["saved_camera"] = datos["camara"]
    resultado["preset"] = rc.preset_de(escena)
    return resultado


@herramienta("set_render_scene", "render", "Cambia solo las propiedades indicadas de la escena del render.", modifica=True)
def set_render_scene(sesion, environment: str | None = None, brightness: float | None = None,
                     rotation: float | None = None, background: Literal["environment", "color"] | None = None,
                     background_color: list[float] | None = None, ground: bool | None = None,
                     reflections: bool | None = None, ground_roughness: float | None = None,
                     shadows: bool | None = None, ambient_occlusion: bool | None = None,
                     camera_type: Literal["perspective", "orthographic"] | None = None,
                     focal_length: float | None = None, exposure: float | None = None,
                     canvas_high_quality: bool | None = None, canvas_supersampling: int | None = None,
                     preset: Literal["performance", "basic", "product", "interior", "jewelry"] | None = None):
    """
    environment: id del entorno de list_render_environments.
    brightness: intensidad de las luces, acotada a 0..4.
    rotation: giro del entorno en grados, normalizado a 0..360.
    background: fondo del entorno (environment) o color uniforme (color).
    background_color: tres componentes sRGB, acotadas a 0..1.
    ground: activa el plano de suelo.
    reflections: activa los reflejos sobre el suelo.
    ground_roughness: rugosidad del suelo, acotada a 0..1.
    shadows: activa las sombras.
    ambient_occlusion: activa la oclusión ambiental.
    camera_type: proyección perspectiva (perspective) u ortográfica (orthographic).
    focal_length: distancia focal en mm, acotada a 8..300.
    exposure: exposición en EV, acotada a -6..6.
    canvas_high_quality: activa la alta calidad en el lienzo.
    canvas_supersampling: supermuestreo del lienzo, de 1 a 3.
    preset: preajuste de KeyShot (performance, basic, product, interior, jewelry); se aplica primero y los demás
        valores indicados lo pisan. get_render_scene dice cuál coincide con la escena, o custom.
    """
    valores = locals()
    cambios = {clave: valores[ingles] for ingles, clave in _CLAVES.items() if valores[ingles] is not None}
    if not cambios and canvas_high_quality is None and canvas_supersampling is None and preset is None:
        raise error("INVALID_ARGUMENTS", "Indicá al menos una propiedad de la escena o del lienzo.")
    if environment is not None and environment not in rc.ENTORNOS:
        raise error("INVALID_ARGUMENTS", f"Entorno desconocido: {environment}.",
                    "Entornos válidos: " + ", ".join(rc.ENTORNOS))
    if background_color is not None and len(background_color) != 3:
        raise error("INVALID_ARGUMENTS", "background_color necesita tres componentes [r, g, b].")
    for clave, valor in cambios.items():
        numeros = valor if isinstance(valor, list) else [valor]
        if any(isinstance(n, (int, float)) and not math.isfinite(n) for n in numeros):
            raise error("INVALID_ARGUMENTS", f"{clave} necesita números finitos.")
    if canvas_supersampling is not None and not 1 <= canvas_supersampling <= 3:
        raise error("INVALID_ARGUMENTS", "canvas_supersampling tiene que estar entre 1 y 3.")
    if background is not None:
        cambios["fondo"] = "entorno" if background == "environment" else "color"
    if camera_type is not None:
        cambios["camara"] = "ortografica" if camera_type == "orthographic" else "perspectiva"
    datos = _datos(sesion)
    escena = {**(datos.get("escena") or {}), **rc.PRESETS_RENDER.get(preset, {}), **cambios}
    normalizada = rc.escena_normalizada(escena)
    for ingles, clave in _CLAVES.items():
        if clave in cambios and cambios[clave] != normalizada[clave]:
            sesion.avisar(f"{ingles} se ajustó de {cambios[clave]} a {normalizada[clave]}.")
    datos["escena"] = {**escena, **normalizada}
    if canvas_high_quality is not None:
        datos["lienzo"]["alta_calidad"] = canvas_high_quality
    if canvas_supersampling is not None:
        datos["lienzo"]["supermuestreo"] = canvas_supersampling
    sesion.doc.espacios["render"] = datos
    return get_render_scene(sesion)


def _cajas(cuerpos):
    cajas = {c.id: c.forma.caja() if _es_malla(c) else geo.caja_envolvente(c.forma) for c in cuerpos}
    if not cuerpos or not any(cajas.values()):
        raise error("NOTHING_TO_RENDER", "No hay cuerpos para renderizar.")
    return cajas


def _encuadrar(escena, cajas, aspecto, view, direction, distance=None):
    atras, vista = _VISTAS[view or "iso"], view or "iso"
    if direction is not None:
        if len(direction) != 3 or not all(math.isfinite(x) for x in direction) or not any(direction):
            raise error("INVALID_ARGUMENTS", "direction necesita tres números finitos no todos cero.")
        # Escalar antes de normalizar evita desbordar con componentes finitas muy grandes.
        atras, vista = np.asarray(direction) / max(abs(x) for x in direction), "custom"
    cam, _ = _camara(atras, _esquinas([c for c in cajas.values() if c]), aspecto, rc.focal_a_fov(escena["focal"]))
    if distance is not None:
        if not math.isfinite(distance) or distance <= 0:
            raise error("INVALID_ARGUMENTS", "distance tiene que ser finita y mayor que cero (mm).")
        cam["distancia"] = distance
    cam["ortografica"] = escena["camara"] == "ortografica"
    return cam, vista


@herramienta("set_render_camera", "render", "Guarda o borra la cámara del espacio RENDERIZAR.", modifica=True)
def set_render_camera(sesion, view: Literal["iso", "front", "back", "top", "bottom", "left", "right"] = "iso",
                      direction: list[float] | None = None, bodies: list[str] | None = None,
                      distance: float | None = None, clear: bool = False):
    """
    view: vista estándar desde la que encuadrar los cuerpos.
    direction: vector [x, y, z] hacia la cámara; reemplaza a view.
    bodies: ids o nombres de los cuerpos a encuadrar; vacío = todos.
    distance: distancia al objetivo en mm; vacío = encuadre automático.
    clear: true borra la cámara guardada y vuelve al encuadre automático.
    """
    datos = _datos(sesion)
    escena = rc.escena_normalizada(datos.get("escena"))
    cam, vista = (None, None) if clear else _encuadrar(
        escena, _cajas(_cuerpos(sesion, bodies)), 16 / 9, view, direction, distance)
    datos["escena"] = {**(datos.get("escena") or {}), **escena}
    datos["camara"] = cam
    sesion.doc.espacios["render"] = datos
    return {"camera": cam, "view": vista}


def _reducir(rgba, width, height, transparente):
    """Baja la grilla de muestras al tamaño final promediando los bloques (filtro de caja de Pillow). Con fondo
    transparente el color va premultiplicado al promediar, para que el borde de las piezas no se oscurezca."""
    from PIL import Image
    if not transparente:
        return np.asarray(Image.fromarray(rgba[..., :3], "RGB").resize((width, height), Image.BOX))
    alfa = rgba[..., 3:4]
    premultiplicado = np.concatenate([rgba[..., :3].astype(np.int32) * alfa // 255, alfa], axis=2).astype(np.uint8)
    salida = np.asarray(Image.fromarray(premultiplicado, "RGBA").resize((width, height), Image.BOX)).astype(np.int32)
    a = salida[..., 3:4]
    rgb = np.where(a > 0, np.minimum(255, salida[..., :3] * 255 // np.maximum(a, 1)), 0)
    return np.concatenate([rgb, a], axis=2).astype(np.uint8)


def _multiplicador(width, height, quality):
    """(multiplicador, aviso): el supermuestreo que entra en el tope de 25 Mpx para la calidad pedida.

    Es el mayor posible (3×, 2×, 1,5× o 1×) sin pasarse del tope; el aviso dice si hubo que bajarlo.
    (None, None) si el tamaño no entra ni a 1×."""
    pedido = _CALIDADES[quality]
    for candidato in _SUPERMUESTREOS:
        if candidato <= pedido and width * height * candidato ** 2 <= TOPE_PIXELES:
            texto = f"{candidato:g}".replace(".", ",")
            aviso = None if candidato == pedido else f"Se bajó el suavizado a {texto}x para no pasar 25 Mpx"
            return candidato, aviso
    return None, None


def _tamano(width, height, preset, quality):
    """Resuelve los presets y ajusta el supermuestreo al tope de memoria antes de renderizar."""
    if preset is not None:
        width, height = _PRESETS[preset]
    if width * height > TOPE_PIXELES:
        raise error("INVALID_ARGUMENTS", "El render supera 25 millones de píxeles; reduci el tamaño.")
    if not all(16 <= lado <= 4096 for lado in (width, height)):
        raise error("INVALID_ARGUMENTS", "Cada lado tiene que estar entre 16 y 4096 píxeles.")
    ss, aviso = _multiplicador(width, height, quality)
    return width, height, ss, aviso


@herramienta("render_image", "render", "Renderiza un PNG por CPU con la escena y la cámara guardadas del documento. "
             "Respeta el Análisis de sección visible: corta con el mismo plano que el visor y dibuja su tapa.")
def render_image(sesion, width: int = 1280, height: int = 720,
                 preset: Literal["web", "hd", "full_hd"] | None = None,
                 quality: Literal["draft", "standard", "final"] = "standard",
                 transparent_background: bool = False, path: str | None = None, overwrite: bool = False,
                 view: Literal["iso", "front", "back", "top", "bottom", "left", "right"] | None = None,
                 direction: list[float] | None = None, bodies: list[str] | None = None):
    """
    width: ancho de la imagen, de 16 a 4096 píxeles.
    height: alto de la imagen, de 16 a 4096 píxeles.
    preset: tamaño predefinido web, hd o full_hd; reemplaza a width y height.
    quality: draft (1×), standard (2×) o final (3×) de supermuestreo; si el tamaño no entra en el tope de 25
        megapíxeles, se baja el supermuestreo lo justo (nunca menos de 1×) y se avisa.
    transparent_background: true genera un PNG RGBA con fondo transparente.
    path: ruta .png opcional, en una carpeta existente.
    overwrite: true permite reemplazar un archivo existente.
    view: vista estándar; reemplaza la cámara guardada solo para esta imagen.
    direction: vector [x, y, z] hacia la cámara; reemplaza a view y a la cámara guardada.
    bodies: ids o nombres de los cuerpos a renderizar; vacío = todos.
    """
    width, height, ss, aviso = _tamano(width, height, preset, quality)
    if aviso:
        sesion.avisar(aviso)
    # La grilla de muestras: con multiplicador entero (1×, 2× o 3×) el renderizador promedia los bloques; con 1,5× la
    # grilla es un 50% más fina y el promedio sale al bajar la imagen (_reducir).
    if ss == int(ss):
        ancho_muestra, alto_muestra, ss_render = width, height, int(ss)
    else:
        ancho_muestra, alto_muestra, ss_render = round(width * ss), round(height * ss), 1
    ruta = Path(path) if path is not None else None
    if ruta is not None:
        if ruta.suffix.lower() != ".png":
            raise error("INVALID_ARGUMENTS", "La ruta tiene que terminar en .png.")
        if not ruta.parent.is_dir():
            raise error("FILE_NOT_FOUND", f"No existe la carpeta: {ruta.parent}.")
        if ruta.exists() and not overwrite:
            raise error("FILE_EXISTS", f"Ya existe el archivo: {ruta}.")
    t0 = time.perf_counter()
    datos = _datos(sesion)
    escena = rc.escena_normalizada(datos.get("escena"))
    cuerpos = _cuerpos(sesion, bodies)
    cajas = _cajas(cuerpos)
    cam = datos["camara"]
    if not cam or view is not None or direction is not None:
        cam, _ = _encuadrar(escena, cajas, ancho_muestra / alto_muestra, view, direction)
    cam = {**cam, "fov": rc.focal_a_fov(escena["focal"]), "ortografica": escena["camara"] == "ortografica"}
    objetos = _objetos_render(sesion, cuerpos, cam, alto_muestra, cajas)
    if not objetos:
        raise error("NOTHING_TO_RENDER", "Los cuerpos elegidos no tienen caras para renderizar.")
    z_suelo = min(float(o["v"][:, 2].min()) for o in objetos)
    # El Análisis de sección visible corta la escena con el mismo plano que el visor y dibuja su tapa.
    objetos, _cortes, _aplicados = _con_analisis(sesion, objetos, cam, alto_muestra, None, tipos=("seccion",))
    if not objetos:
        raise error("NOTHING_TO_RENDER", "El corte de la sección dejó la escena vacía.")
    ids = {c.id for c in cuerpos}
    calcomanias = [d for _i, d in calcomanias_vigentes(sesion.doc, sesion.doc.estado_final)
                   if d.get("calcomania") and d.get("cuerpo") in ids]
    res = int(min(2048, max(512, 2 ** math.ceil(math.log2(max(width, height) * ss * 1.5)))))
    rgba = rc.renderizar(objetos, cam, escena, ancho_muestra, alto_muestra, supermuestreo=ss_render,
                         cielo=rc.cielo_de(escena["entorno"]), fondo_transparente=transparent_background,
                         z_suelo=z_suelo, res_sombras=res,
                         mosaico=_MOSAICO, calcomanias=calcomanias)
    if ss_render != ss:
        rgba = _reducir(rgba, width, height, transparent_background)
    from PIL import Image
    buf = io.BytesIO()
    Image.fromarray(np.ascontiguousarray(rgba if transparent_background else rgba[..., :3])).save(
        buf, "PNG", compress_level=3)
    png = buf.getvalue()
    if ruta is not None:
        # La creación exclusiva también evita pisar un archivo creado mientras se calculaba la imagen.
        with ruta.open("wb" if overwrite else "xb") as archivo:
            archivo.write(png)
    return {"image": Imagen(png, width, height), "width": width, "height": height,
            "seconds": round(time.perf_counter() - t0, 3), "path": str(ruta) if ruta is not None else None}
