# -*- coding: utf-8 -*-
"""
Herramientas de aspectos (MODIFICAR › Aspecto de Fusion): la biblioteca, «Mis aspectos», los favoritos, los aspectos del
diseño («En este diseño») y su editor de materiales. `set_appearance` (herramientas_material.py) los asigna a cuerpos
o a caras; el panel Aspecto de la ventana usa estas mismas herramientas.

Cada aspecto se describe con:
  color «#rrggbb»; reflectance, roughness, metallic, transparency y varnish de 0 a 1; translucency {enabled, depth_mm,
  color}; emissive {enabled, luminance_cd_m2, filter_color}; bump {file, amount} y cutout {file} (imágenes embebidas);
  highlights {anisotropy, orientation_deg, color, shape}. El render usa color, metallic, roughness, transparency,
  varnish y el patrón de madera; lo demás se guarda con el aspecto.
"""
import base64
import difflib
import io
from pathlib import Path
from typing import Literal

from PIL import Image

from ..nucleo import aspectos as asp
from ..nucleo import geometria as geo
from ..timeline import aspectos_doc as ad
from .errores import error
from .herramientas_material import _hex, color_rgb
from .registro import herramienta

_ALCANCES = Literal["design", "library", "mine", "favorites", "all"]


def _a_json(a):
    """Un aspecto para la API (nombres en inglés, color en «#rrggbb»)."""
    r = a["resalte"]
    salida = {"name": a["nombre"], "category": a["categoria"], "color": _hex(a["color"]),
              "reflectance": round(a["reflectancia"], 4), "roughness": round(a["aspereza"], 4),
              "metallic": round(a["metalico"], 4), "transparency": round(a["transparencia"], 4),
              "varnish": round(a["barniz"], 4), "pattern": a["patron"] or None,
              "translucency": {"enabled": a["translucidez"], "depth_mm": round(a["profundidad"], 4),
                               "color": _hex(a["grosor_color"])},
              "emissive": {"enabled": a["emisividad"], "luminance_cd_m2": round(a["luminancia"], 4),
                           "filter_color": _hex(a["color_filtro"])},
              "bump": None if a["relieve"] is None else {"file": a["relieve"]["archivo"],
                                                         "amount": a["relieve"]["cantidad"]},
              "cutout": None if a["corte"] is None else {"file": a["corte"]["archivo"]},
              "highlights": {"anisotropy": round(r["anisotropia"], 4), "orientation_deg": round(r["orientacion"], 4),
                             "color": _hex(r["color"]), "shape": r["forma"]}}
    if "id" in a:
        salida["id"] = a["id"]
    return salida


def _leer_imagen(ruta, que):
    """{"archivo", "imagen" (base64)} de un PNG/JPG/BMP/TIFF: el relieve y el corte viajan dentro del diseño."""
    p = Path(ruta)
    if not p.is_file():
        raise error("FILE_NOT_FOUND", f"No encuentro la imagen de {que}: {ruta}")
    if p.stat().st_size > 6 * 1024 * 1024:
        raise error("INVALID_ARGUMENTS", f"La imagen de {que} supera 6 MB.")
    datos = p.read_bytes()
    try:
        with Image.open(io.BytesIO(datos)) as img:
            img.verify()
    except (OSError, ValueError, Image.DecompressionBombError):
        raise error("INVALID_ARGUMENTS", f"La imagen de {que} está dañada o no es compatible.") from None
    return {"archivo": p.name, "imagen": base64.b64encode(datos).decode("ascii")}


def _cambios(color=None, reflectance=None, roughness=None, metallic=None, transparency=None, varnish=None,
             translucency=None, translucency_depth=None, translucency_color=None, emissive=None, luminance=None,
             filter_color=None, bump_image=None, bump_amount=None, cutout_image=None, anisotropy=None,
             orientation=None, highlight_color=None, highlight_shape=None, category=None):
    """Las propiedades pedidas, con los nombres de `nucleo.aspectos`. Lo que viene en None no cambia."""
    c = {}
    pares = {"reflectancia": reflectance, "aspereza": roughness, "metalico": metallic, "transparencia": transparency,
             "barniz": varnish, "translucidez": translucency, "profundidad": translucency_depth,
             "emisividad": emissive, "luminancia": luminance, "categoria": category}
    c.update({k: v for k, v in pares.items() if v is not None})
    for clave, valor in (("color", color), ("grosor_color", translucency_color), ("color_filtro", filter_color)):
        if valor is not None:
            c[clave] = color_rgb(valor, clave)
    for clave, ruta, cantidad in (("relieve", bump_image, bump_amount), ("corte", cutout_image, None)):
        if ruta is not None:
            c[clave] = _leer_imagen(ruta, clave) if ruta else None          # "" lo quita
            if cantidad is not None and c[clave] is not None:
                c[clave]["cantidad"] = cantidad
        elif cantidad is not None:
            c["_cantidad_relieve"] = cantidad
    resalte = {k: v for k, v in (("anisotropia", anisotropy), ("orientacion", orientation), ("forma", highlight_shape))
               if v is not None}
    if highlight_color is not None:
        resalte["color"] = color_rgb(highlight_color, "highlight_color")
    if resalte:
        c["resalte"] = resalte
    return c


def _buscar_fuera_del_diseno(texto):
    a = asp.buscar(texto)
    if a is None:
        todos = list(asp.BIBLIOTECA) + list(asp.cargar_usuario()["mis"])
        parecidos = difflib.get_close_matches(str(texto), todos, n=3, cutoff=0.4)
        raise error("NOT_FOUND", f"No existe el aspecto «{texto}» (ni en el diseño, ni en la biblioteca, ni en Mis aspectos).",
                    *([f"¿Quisiste decir: {', '.join(parecidos)}?"] if parecidos else []),
                    "list_appearances muestra los de cada lugar.")
    return a


def aspecto_por_nombre(doc, texto):
    """Un aspecto del diseño o, si no hay, de «Mis aspectos» o de la biblioteca (para `set_appearance`)."""
    return ad.buscar(doc, texto) or _buscar_fuera_del_diseno(texto)


@herramienta("list_appearances", "material", "Lista aspectos con todas sus propiedades: los del diseño («En este "
             "diseño», con id y quién los usa), los de la biblioteca (por familia: Metal, Plástico, Cristal, Madera, "
             "Piedra, Hormigón…), «Mis aspectos» o los favoritos. No cambia el documento.")
def list_appearances(sesion, scope: _ALCANCES = "design", query: str | None = None):
    """
    scope: design (En este diseño), library (biblioteca de OmniCAD), mine (Mis aspectos), favorites o all.
    query: texto a buscar en el nombre o la familia (sin distinguir mayúsculas); vacío = todos.
    """
    q = (query or "").strip().casefold()
    usuario = asp.cargar_usuario()
    mine, favs = usuario["mis"], set(usuario["favoritos"])
    salida = []

    def agregar(origen, a, extra=None):
        if q and q not in a["nombre"].casefold() and q not in a["categoria"].casefold():
            return
        salida.append(dict(_a_json(a), scope=origen, favorite=a["nombre"] in favs, **(extra or {})))

    if scope in ("design", "all"):
        for a in ad.lista(sesion.doc):
            cuerpos, caras = ad.usos(sesion.doc, a["id"])
            agregar("design", a, {"bodies": cuerpos, "faces": len(caras)})
    if scope in ("library", "all"):
        for a in asp.BIBLIOTECA.values():
            agregar("library", a)
    if scope in ("mine", "all"):
        for a in mine.values():
            agregar("mine", a)
    if scope == "favorites":
        for nombre in usuario["favoritos"]:
            a = asp.buscar(nombre)
            if a is not None:
                agregar("mine" if nombre in mine else "library", a)
    return {"appearances": salida, "categories": list(asp.CATEGORIAS), "library_file": str(asp.ruta_usuario())}


def _crear(doc, appearance, scope, base, name, cambios):
    """edit_appearance con create=true: un aspecto nuevo en el diseño o en Mis aspectos."""
    existente = ad.buscar(doc, appearance) if scope == "design" else asp.cargar_usuario()["mis"].get(appearance)
    if existente is not None:
        raise error("NAME_EXISTS", f"Ya existe el aspecto «{appearance}».")
    nuevo = dict(asp.mezclar(aspecto_por_nombre(doc, base) if base else {}, cambios), nombre=(name or appearance))
    if scope == "mine":
        return {"appearance": _a_json(asp.agregar_mio(nuevo)), "scope": "mine", "saved": True}
    return {"appearance": _a_json(ad.agregar(doc, nuevo, "nuevo")), "scope": "design"}


def _editar_mio(appearance, name, cambios):
    mis = asp.cargar_usuario()["mis"]
    if appearance not in mis:
        raise error("NOT_FOUND", f"«{appearance}» no está en Mis aspectos.")
    nuevo = dict(asp.mezclar(mis[appearance], cambios), nombre=(name or appearance))
    guardado = asp.agregar_mio(nuevo, reemplazar=True)      # antes de borrar el viejo: si choca, no se pierde
    if guardado["nombre"] != appearance:
        asp.quitar_mio(appearance)
    return {"appearance": _a_json(guardado), "scope": "mine", "saved": True}


def _copiar_al_diseno(doc, appearance, name, cambios):
    """Editar uno de la biblioteca o de Mis aspectos deja una copia editada en el diseño; el original no cambia."""
    original = _buscar_fuera_del_diseno(appearance)
    origen = "mis" if original["nombre"] in asp.cargar_usuario()["mis"] else "biblioteca"
    entrada = ad.agregar(doc, dict(asp.mezclar(original, cambios), nombre=name or original["nombre"]), origen)
    return {"appearance": _a_json(entrada), "scope": "design", "copied_from": original["nombre"]}


@herramienta("edit_appearance", "material", "Edita un aspecto (el «Editor de materiales» de Fusion) o crea uno nuevo: "
             "color, reflectancia, aspereza, metálico, transparencia, translucidez, emisividad, relieve, corte y "
             "resaltes. En el diseño, todos los cuerpos y caras que lo usan se ven con el cambio al instante. Con un "
             "aspecto de la biblioteca o de Mis aspectos, hace una copia en el diseño («X (1)») sin tocar el original. "
             "create=true crea uno nuevo (partiendo de base). scope=mine lo guarda en Mis aspectos.", modifica=True)
def edit_appearance(sesion, appearance: str, scope: Literal["design", "mine"] = "design", create: bool = False,
                    base: str | None = None, name: str | None = None, color: str | list[float] | None = None,
                    reflectance: float | None = None, roughness: float | None = None, metallic: float | None = None,
                    transparency: float | None = None, varnish: float | None = None,
                    translucency: bool | None = None, translucency_depth: float | None = None,
                    translucency_color: str | list[float] | None = None, emissive: bool | None = None,
                    luminance: float | None = None, filter_color: str | list[float] | None = None,
                    bump_image: str | None = None, bump_amount: float | None = None,
                    cutout_image: str | None = None, anisotropy: float | None = None,
                    orientation: float | None = None, highlight_color: str | list[float] | None = None,
                    highlight_shape: Literal["Difuminación larga", "Difuminación corta", "Nítida"] | None = None,
                    category: str | None = None):
    """
    appearance: nombre o id del aspecto a editar (o el nombre del nuevo con create=true).
    scope: design (En este diseño, por defecto) o mine (Mis aspectos).
    create: true crea un aspecto nuevo llamado appearance; falla si ya existe.
    base: con create, el aspecto del que parte (diseño, Mis aspectos o biblioteca); vacío = gris liso.
    name: nombre nuevo (renombra).
    color: color «#rrggbb» o [r, g, b] (0..1 o 0..255).
    reflectance: reflectancia de 0 a 1 (Fresnel: 0,05 en plásticos).
    roughness: aspereza de 0 (espejo) a 1 (mate).
    metallic: 0 a 1.
    transparency: 0 (opaco) a 1 (transparente).
    varnish: capa de barniz de 0 a 1.
    translucency: activa la translucidez.
    translucency_depth: profundidad de la translucidez en mm.
    translucency_color: color del grosor translúcido.
    emissive: activa la emisividad (el material emite luz).
    luminance: luminancia en cd/m².
    filter_color: color de filtro de la emisividad.
    bump_image: ruta de la imagen del patrón de relieve; "" la quita.
    bump_amount: intensidad del relieve de 0 a 10.
    cutout_image: ruta de la imagen del patrón de corte; "" la quita.
    anisotropy: anisotropía de los resaltes de 0 a 1.
    orientation: orientación de los resaltes en grados.
    highlight_color: color de los resaltes.
    highlight_shape: forma del resalte: Difuminación larga, Difuminación corta o Nítida.
    category: familia de la biblioteca (Metal, Plástico, Cristal, Madera, Piedra, Hormigón, Otro…).
    """
    doc = sesion.doc
    cambios = _cambios(color, reflectance, roughness, metallic, transparency, varnish, translucency,
                       translucency_depth, translucency_color, emissive, luminance, filter_color, bump_image,
                       bump_amount, cutout_image, anisotropy, orientation, highlight_color, highlight_shape, category)
    cantidad = cambios.pop("_cantidad_relieve", None)
    if cantidad is not None:
        relieve = cambios.get("relieve")
        previo = relieve or (None if create else (aspecto_por_nombre(doc, appearance) or {}).get("relieve"))
        if previo is None:
            raise error("INVALID_ARGUMENTS", "bump_amount necesita un relieve: pasá también bump_image.")
        cambios["relieve"] = dict(previo, cantidad=cantidad)
    if name is not None and not str(name).strip():
        raise error("INVALID_ARGUMENTS", "El nombre del aspecto no puede estar vacío.")
    try:
        if create:
            return _crear(doc, appearance, scope, base, name, cambios)
        if scope == "mine":
            return _editar_mio(appearance, name, cambios)
        if ad.buscar(doc, appearance) is None:         # de la biblioteca o de Mis aspectos: copia en el diseño
            return _copiar_al_diseno(doc, appearance, name, cambios)
        if name is not None:
            cambios["nombre"] = str(name).strip()
        entrada = ad.editar(doc, appearance, cambios)
    except geo.ErrorGeometria as e:
        raise error("INVALID_ARGUMENTS", str(e)) from None
    cuerpos, caras = ad.usos(doc, entrada["id"])
    return {"appearance": _a_json(entrada), "scope": "design", "bodies_updated": cuerpos, "faces_updated": len(caras)}


@herramienta("manage_appearance", "material", "Administra un aspecto como el menú de «En este diseño» de Fusion: "
             "duplicate (copia con nombre «X (1)»), delete (Suprimir; si lo usan cuerpos o caras pide "
             "remove_users=true), rename, copy_to_mine (Copiar en Mis aspectos), add_favorite / remove_favorite "
             "(Añadir a Favoritos) y delete_mine (borra uno de Mis aspectos).", modifica=True)
def manage_appearance(sesion, action: Literal["duplicate", "delete", "rename", "copy_to_mine", "add_favorite",
                                              "remove_favorite", "delete_mine"],
                      appearance: str, name: str | None = None, remove_users: bool = False):
    """
    action: duplicate, delete, rename, copy_to_mine, add_favorite, remove_favorite o delete_mine.
    appearance: nombre o id del aspecto (del diseño; los favoritos y delete_mine usan el nombre de la biblioteca o de Mis aspectos).
    name: nombre nuevo (rename) o del duplicado (duplicate).
    remove_users: con delete, true saca también el aspecto de los cuerpos y caras que lo usan.
    """
    doc = sesion.doc
    try:
        if action in ("duplicate", "rename", "delete"):
            if ad.buscar(doc, appearance) is None:
                raise error("NOT_FOUND", f"El diseño no tiene un aspecto «{appearance}».",
                            "list_appearances(scope='design') muestra los del diseño.")
            if action == "duplicate":
                return {"appearance": _a_json(ad.duplicar(doc, appearance, name))}
            if action == "rename":
                if not name or not name.strip():
                    raise error("INVALID_ARGUMENTS", "rename necesita name.")
                return {"appearance": _a_json(ad.renombrar(doc, appearance, name.strip()))}
            anterior, cuerpos, caras = ad.suprimir(doc, appearance, remove_users)
            return {"deleted": anterior["nombre"], "bodies_cleared": cuerpos, "faces_cleared": len(caras)}
        if action == "copy_to_mine":
            a = ad.buscar(doc, appearance) or _buscar_fuera_del_diseno(appearance)
            guardado = asp.agregar_mio(dict(a, nombre=asp.nombre_para_mio(name or a["nombre"])))
            return {"appearance": _a_json(guardado), "scope": "mine", "saved": True}
        if action == "delete_mine":
            if not asp.quitar_mio(appearance):
                raise error("NOT_FOUND", f"«{appearance}» no está en Mis aspectos.")
            return {"deleted": appearance}
        a = asp.buscar(appearance) or ad.buscar(doc, appearance)
        if a is None:
            raise error("NOT_FOUND", f"No existe el aspecto «{appearance}».")
        favoritos = asp.marcar_favorito(a["nombre"], action == "add_favorite")
        return {"favorites": favoritos}
    except geo.ErrorGeometria as e:
        raise error("INVALID_ARGUMENTS", str(e)) from None
