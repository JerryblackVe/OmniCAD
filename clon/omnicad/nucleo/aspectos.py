# -*- coding: utf-8 -*-
"""
Aspectos (Fusion › MODIFICAR › Aspecto): la ficha de cada aspecto, la biblioteca, «Mis aspectos» y los favoritos.
Sin Qt y sin documento: lo que se guarda con el diseño vive en `timeline/aspectos_doc.py`.

Un aspecto es un dict con lo que muestra el «Editor de materiales» de Fusion: color, reflectancia, aspereza,
translucidez (profundidad y color del grosor), emisividad (luminancia y color de filtro), patrón de relieve y de
corte (una imagen cada uno) y los controles avanzados de resaltes. El render usa color, metálico, aspereza,
transparencia, barniz y patrón (`acabado_de`); lo demás se guarda con el aspecto.

La biblioteca junta los 45 aspectos del render (`render_cpu.BIBLIOTECA_ASPECTOS`) con otros propios, repartidos en
las familias de la biblioteca de Fusion. «Mis aspectos» y los favoritos se guardan en «aspectos_usuario.json» de la
carpeta de datos (o en la ruta de la variable OMNICAD_ASPECTOS), como los materiales propios.
"""
import copy
import json
import math
import os
import tempfile
from pathlib import Path

import numpy as np

from .. import carpeta_datos
from . import geometria as geo
from . import render_cpu as rc

CATEGORIAS = ("Acondicionamiento del terreno", "Cristal", "Espejo", "Hormigón", "Líquido", "Madera",
              "Madera (sólido)", "Metal", "Otro", "Piedra", "Pintura", "Plástico")
FORMAS_RESALTE = ("Difuminación larga", "Difuminación corta", "Nítida")
TOPE_IMAGEN = 8 * 1024 * 1024        # base64 del relieve y del corte: un aspecto de otro no llena la memoria
TOPE_TEXTO = 80

RESALTE_DEFECTO = {"anisotropia": 0.0, "orientacion": 0.0, "color": [1.0, 1.0, 1.0], "forma": FORMAS_RESALTE[0]}
PREDETERMINADO = {
    "nombre": "Aspecto", "categoria": "Otro", "color": [0.8, 0.8, 0.8],
    "reflectancia": 0.05, "aspereza": 0.4, "metalico": 0.0, "transparencia": 0.0, "barniz": 0.0, "patron": "",
    "color2": None,
    "translucidez": False, "profundidad": 0.18, "grosor_color": [0.0, 0.92, 0.8],
    "emisividad": False, "luminancia": 0.0, "color_filtro": [1.0, 1.0, 1.0],
    "relieve": None, "corte": None, "resalte": RESALTE_DEFECTO,
}
# Lo que el render entiende del aspecto (`render_cpu.ACABADO_DEFECTO`); lo demás se guarda con el aspecto.
CLAVES_ACABADO = ("nombre", "categoria", "metalico", "transparencia", "barniz", "patron", "color2")


def _num(valor, que, minimo=0.0, maximo=1.0):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor):
        raise geo.ErrorGeometria(f"{que} tiene que ser un número (llegó {valor!r}).")
    return float(min(maximo, max(minimo, valor)))


def _color(valor, que):
    if (not isinstance(valor, (list, tuple)) or len(valor) != 3
            or not all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in valor)):
        raise geo.ErrorGeometria(f"{que} tiene que ser [r, g, b] de 0 a 1 (llegó {valor!r}).")
    escala = 255.0 if any(x > 1 for x in valor) else 1.0
    return [float(min(1.0, max(0.0, x / escala))) for x in valor]


def _imagen(valor, que):
    """Relieve o corte: None, o {"archivo", "imagen" (base64), "cantidad"}."""
    if valor is None or valor == {}:
        return None
    if not isinstance(valor, dict) or not isinstance(valor.get("imagen"), str) or not valor["imagen"]:
        raise geo.ErrorGeometria(f"{que} es una imagen: {{\"archivo\", \"imagen\" en base64}} (o vacío).")
    if len(valor["imagen"]) > TOPE_IMAGEN:
        raise geo.ErrorGeometria(f"La imagen de {que} supera {TOPE_IMAGEN // (1024 * 1024)} MB.")
    return {"archivo": str(valor.get("archivo") or "")[:TOPE_TEXTO], "imagen": valor["imagen"],
            "cantidad": _num(valor.get("cantidad", 1.0), f"La cantidad de {que}", 0.0, 10.0)}


def normalizar(datos):
    """Aspecto completo y acotado a partir de uno a medias. Un valor que no es lo que dice ser falla con
    `geo.ErrorGeometria`; uno fuera de rango se acota (como los deslizadores del editor)."""
    if not isinstance(datos, dict):
        raise geo.ErrorGeometria("Un aspecto es un diccionario de propiedades.")
    d = copy.deepcopy(PREDETERMINADO)
    d.update({k: copy.deepcopy(v) for k, v in datos.items() if k in PREDETERMINADO})
    d["nombre"] = str(d["nombre"]).strip()[:TOPE_TEXTO] or "Aspecto"
    d["categoria"] = d["categoria"] if d["categoria"] in CATEGORIAS else "Otro"
    for clave in ("color", "grosor_color", "color_filtro"):
        d[clave] = _color(d[clave], clave)
    d["color2"] = None if d["color2"] is None else _color(d["color2"], "color2")
    for clave in ("reflectancia", "aspereza", "metalico", "transparencia", "barniz"):
        d[clave] = _num(d[clave], clave)
    d["profundidad"] = _num(d["profundidad"], "profundidad", 0.0, 1000.0)
    d["luminancia"] = _num(d["luminancia"], "luminancia", 0.0, 1e6)
    d["translucidez"], d["emisividad"] = bool(d["translucidez"]), bool(d["emisividad"])
    d["patron"] = str(d["patron"] or "")[:TOPE_TEXTO]
    d["relieve"], d["corte"] = _imagen(d["relieve"], "relieve"), _imagen(d["corte"], "corte")
    r = dict(RESALTE_DEFECTO)
    if isinstance(datos.get("resalte"), dict):
        r.update({k: v for k, v in datos["resalte"].items() if k in RESALTE_DEFECTO})
    d["resalte"] = {"anisotropia": _num(r["anisotropia"], "anisotropía"),
                    "orientacion": _num(r["orientacion"], "orientación", -360.0, 360.0),
                    "color": _color(r["color"], "el color del resalte"),
                    "forma": r["forma"] if r["forma"] in FORMAS_RESALTE else FORMAS_RESALTE[0]}
    return d


def mezclar(aspecto, cambios):
    """`aspecto` con `cambios` encima; el resalte se mezcla clave por clave (cambiar solo la anisotropía no borra el
    color del resalte). Devuelve un dict sin normalizar."""
    mezcla = dict(aspecto, **cambios)
    if isinstance(cambios.get("resalte"), dict):
        mezcla["resalte"] = dict(aspecto.get("resalte") or RESALTE_DEFECTO, **cambios["resalte"])
    return mezcla


def acabado_de(aspecto):
    """El `acabado` que se guarda en las propiedades de un cuerpo o de una cara: lo que entiende el render."""
    a = normalizar(aspecto)
    return {"nombre": a["nombre"], "categoria": a["categoria"], "metalico": a["metalico"],
            "rugosidad": a["aspereza"], "transparencia": a["transparencia"], "barniz": a["barniz"],
            "patron": a["patron"], "color2": a["color2"]}


# ---------------------------------------------------------------- biblioteca
_CATEGORIA_DEL_RENDER = {"Vidrio": "Cristal", "Goma": "Otro"}


def _del_render(nombre, datos):
    a = datos["acabado"]
    return normalizar({"nombre": nombre, "categoria": _CATEGORIA_DEL_RENDER.get(datos["categoria"], datos["categoria"]),
                       "color": list(datos["color"]), "metalico": a["metalico"], "aspereza": a["rugosidad"],
                       "transparencia": a["transparencia"], "barniz": a["barniz"], "patron": a["patron"],
                       "color2": a["color2"], "reflectancia": 0.9 if a["metalico"] >= 0.5 else 0.05})


def _propio(categoria, nombre, color, aspereza, metalico=0.0, transparencia=0.0, reflectancia=0.05, patron="",
            color2=None, barniz=0.0):
    return nombre, normalizar({"nombre": nombre, "categoria": categoria, "color": color, "aspereza": aspereza,
                               "metalico": metalico, "transparencia": transparencia, "reflectancia": reflectancia,
                               "patron": patron, "color2": color2, "barniz": barniz})


_PROPIOS = [
    _propio("Acondicionamiento del terreno", "Césped - Verde", (0.22, 0.45, 0.12), 0.95),
    _propio("Acondicionamiento del terreno", "Tierra - Seca", (0.42, 0.31, 0.20), 0.95),
    _propio("Acondicionamiento del terreno", "Asfalto - Liso", (0.12, 0.12, 0.13), 0.85),
    _propio("Espejo", "Espejo - Plata", (0.96, 0.96, 0.97), 0.01, 1.0, reflectancia=1.0),
    _propio("Espejo", "Espejo - Bronce", (0.62, 0.46, 0.32), 0.02, 1.0, reflectancia=0.95),
    _propio("Hormigón", "Hormigón - Liso", (0.62, 0.62, 0.60), 0.80),
    _propio("Hormigón", "Hormigón - Rugoso", (0.52, 0.52, 0.50), 0.95),
    _propio("Hormigón", "Hormigón - Pulido", (0.68, 0.68, 0.66), 0.45),
    _propio("Líquido", "Agua - Clara", (0.82, 0.92, 0.96), 0.0, transparencia=0.88, reflectancia=0.1),
    _propio("Líquido", "Aceite - Ámbar", (0.80, 0.52, 0.10), 0.02, transparencia=0.70, reflectancia=0.08),
    _propio("Líquido", "Leche", (0.97, 0.97, 0.94), 0.05, transparencia=0.15, reflectancia=0.06),
    _propio("Madera (sólido)", "Madera sólida - Cerezo", (0.66, 0.38, 0.22), 0.45, patron="madera",
            color2=(0.42, 0.22, 0.12)),
    _propio("Madera (sólido)", "Madera sólida - Caoba", (0.45, 0.21, 0.14), 0.40, patron="madera",
            color2=(0.27, 0.11, 0.07)),
    _propio("Otro", "Cerámica - Blanca", (0.94, 0.94, 0.92), 0.12, reflectancia=0.08, barniz=1.0),
    _propio("Otro", "Cuero - Marrón", (0.35, 0.20, 0.11), 0.65),
    _propio("Otro", "Tela - Algodón (beige)", (0.80, 0.74, 0.62), 0.95),
    _propio("Piedra", "Granito - Gris", (0.45, 0.45, 0.46), 0.35),
    _propio("Piedra", "Mármol - Blanco", (0.93, 0.93, 0.91), 0.15, reflectancia=0.07),
    _propio("Piedra", "Pizarra - Negra", (0.14, 0.15, 0.16), 0.60),
    _propio("Piedra", "Arenisca - Dorada", (0.76, 0.62, 0.42), 0.85),
]

BIBLIOTECA = {**{n: _del_render(n, d) for n, d in rc.BIBLIOTECA_ASPECTOS.items()}, **dict(_PROPIOS)}


def categorias_con_aspectos(aspectos):
    """{categoría: [nombres]} en el orden de CATEGORIAS, sin las vacías."""
    return {c: [n for n, a in aspectos.items() if a["categoria"] == c]
            for c in CATEGORIAS if any(a["categoria"] == c for a in aspectos.values())}


# ---------------------------------------------------------------- «Mis aspectos» y favoritos
def ruta_usuario():
    ruta = os.environ.get("OMNICAD_ASPECTOS")
    return Path(ruta) if ruta else carpeta_datos() / "aspectos_usuario.json"


def cargar_usuario():
    """{"mis": {nombre: aspecto}, "favoritos": [nombres]} del archivo del usuario. Un archivo ausente, dañado o con
    un aspecto que no vale no tumba a nadie: se salta lo que no sirve."""
    salida = {"mis": {}, "favoritos": []}
    try:
        datos = json.loads(ruta_usuario().read_text(encoding="utf-8"))
    except (OSError, ValueError, RecursionError):
        return salida
    if not isinstance(datos, dict):
        return salida
    for nombre, a in (datos.get("mis") or {}).items() if isinstance(datos.get("mis"), dict) else ():
        try:
            salida["mis"][nombre] = normalizar(a)
        except geo.ErrorGeometria:
            continue
    favoritos = datos.get("favoritos")
    salida["favoritos"] = [n for n in favoritos if isinstance(n, str)] if isinstance(favoritos, list) else []
    return salida


def guardar_usuario(datos):
    """Escritura atómica (archivo temporal + reemplazo): un corte a mitad no deja el archivo a medias."""
    ruta = ruta_usuario()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fd, temporal = tempfile.mkstemp(suffix=".json", dir=str(ruta.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(json.dumps(datos, ensure_ascii=False, indent=1).encode("utf-8"))
        os.replace(temporal, ruta)
    except BaseException:
        if os.path.exists(temporal):
            os.remove(temporal)
        raise


def agregar_mio(aspecto, reemplazar=False):
    """Guarda `aspecto` en «Mis aspectos». Devuelve el aspecto guardado. Un nombre repetido pide `reemplazar`."""
    a = normalizar(aspecto)
    datos = cargar_usuario()
    if a["nombre"] in BIBLIOTECA:
        raise geo.ErrorGeometria(f"«{a['nombre']}» es un aspecto de la biblioteca: elegí otro nombre.")
    if a["nombre"] in datos["mis"] and not reemplazar:
        raise geo.ErrorGeometria(f"Ya hay un aspecto tuyo llamado «{a['nombre']}».")
    datos["mis"][a["nombre"]] = a
    guardar_usuario(datos)
    return a


def nombre_para_mio(nombre):
    """`nombre`, o «nombre (1)», «nombre (2)»… si ya lo tiene la biblioteca o «Mis aspectos»: copiar uno en «Mis
    aspectos» nunca falla ni pisa a otro (como en Fusion, la copia lleva el número)."""
    usados = {n.casefold() for n in (*BIBLIOTECA, *cargar_usuario()["mis"])}
    candidato, n = nombre, 1
    while candidato.casefold() in usados:
        candidato, n = f"{nombre} ({n})", n + 1
    return candidato


def quitar_mio(nombre):
    datos = cargar_usuario()
    if nombre not in datos["mis"]:
        return False
    del datos["mis"][nombre]
    datos["favoritos"] = [n for n in datos["favoritos"] if n != nombre]
    guardar_usuario(datos)
    return True


def marcar_favorito(nombre, favorito=True):
    datos = cargar_usuario()
    datos["favoritos"] = [n for n in datos["favoritos"] if n != nombre] + ([nombre] if favorito else [])
    guardar_usuario(datos)
    return datos["favoritos"]


def buscar(nombre):
    """El aspecto de la biblioteca o de «Mis aspectos» con ese nombre (sin distinguir mayúsculas), o None."""
    texto = str(nombre).strip().casefold()
    mis = cargar_usuario()["mis"]
    for tabla in (BIBLIOTECA, mis):
        for n, a in tabla.items():
            if n.casefold() == texto:
                return copy.deepcopy(a)
    return None


# ---------------------------------------------------------------- miniaturas
def miniatura_rgba(aspecto, tam=48):
    """Esfera iluminada con el aspecto (RGBA uint8, tam × tam): la miniatura de «En este diseño» y de la biblioteca."""
    a = normalizar(aspecto)
    y, x = np.mgrid[0:tam, 0:tam]
    u, v = (x + 0.5) / tam * 2 - 1, 1 - (y + 0.5) / tam * 2
    r2 = u * u + v * v
    dentro = r2 <= 1.0
    n = np.stack([u, v, np.sqrt(np.clip(1 - r2, 0, 1))], axis=-1)
    luz = np.array([-0.45, 0.55, 0.70])
    luz /= np.linalg.norm(luz)
    medio = luz + np.array([0.0, 0.0, 1.0])
    medio /= np.linalg.norm(medio)
    difusa = np.clip(n @ luz, 0, 1)
    brillo = np.clip(n @ medio, 0, 1) ** (4 + (1 - a["aspereza"]) ** 2 * 160)
    color = np.array(a["color"])
    base = color * (0.22 + 0.78 * difusa)[..., None] * (1 - 0.65 * a["metalico"])
    reflejo = np.array([1.0, 1.0, 1.0]) * (1 - a["metalico"]) + color * a["metalico"]
    intensidad = (0.12 + 0.9 * a["metalico"] + a["reflectancia"]) * (1.1 - 0.7 * a["aspereza"])
    rgb = base + (brillo * intensidad)[..., None] * reflejo
    if a["emisividad"] and a["luminancia"] > 0:
        rgb = rgb + np.array(a["color_filtro"]) * color * min(1.0, a["luminancia"] / 1000.0)
    alfa = np.where(dentro, 255 * (1 - 0.65 * a["transparencia"]), 0)
    salida = np.zeros((tam, tam, 4), np.uint8)
    salida[..., :3] = (np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)
    salida[..., 3] = alfa.astype(np.uint8)
    return salida
