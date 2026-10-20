"""Estado persistente del visor para agentes, sin ventana ni Qt."""
import copy
import math
from typing import Literal

import numpy as np

from ..nucleo import geometria as geo
from ..nucleo import render_cpu as rc
from ..timeline import ops_chapa
from .errores import error
from .herramientas_inspeccion import _VISTAS, _camara, _cuerpos, _es_malla, _esquinas
from .registro import herramienta


def _datos(sesion):
    return copy.deepcopy(sesion.doc.espacios.get("visor") or {})


def _vista_guardada(sesion, nombre):
    if nombre not in sesion.doc.vistas:
        raise error("INVALID_ARGUMENTS", f"No existe la vista «{nombre}».", f"Vistas estándar: {', '.join(_VISTAS)}.",
                    f"Vistas guardadas: {', '.join(sesion.doc.vistas) or 'ninguna'}.")
    d = sesion.doc.vistas[nombre]
    return rc.camara(d["R"], d["objetivo"], d["distancia"], d.get("fov", 40.0),
                     d.get("camara") == "ortografica")


def _encuadrar(sesion, view="iso", direction=None, bodies=None, aspecto=4 / 3):
    if direction is None and view not in _VISTAS:
        return _vista_guardada(sesion, view)
    atras = direction if direction is not None else _VISTAS[view]
    if len(atras) != 3 or not all(math.isfinite(x) for x in atras) or not any(atras):
        raise error("INVALID_ARGUMENTS", "direction necesita tres números finitos no todos cero.")
    atras = np.asarray(atras, float) / max(abs(x) for x in atras)
    cajas = [c.forma.caja() if _es_malla(c) else geo.caja_envolvente(c.forma) for c in _cuerpos(sesion, bodies)]
    if not any(cajas):
        raise error("NOTHING_TO_RENDER", "No hay cuerpos para encuadrar.")
    return _camara(atras, _esquinas([c for c in cajas if c]), aspecto, 40.0)[0]


@herramienta("set_view", "inspeccion", "Guarda la cámara del visor: vista, órbita, proyección, zoom y objetivo. "
             "Admite deshacer y clear vuelve al encuadre automático.", modifica=True)
def set_view(sesion, view: str = "iso", direction: list[float] | None = None,
             projection: Literal["perspective", "orthographic"] = "perspective",
             azimuth: float = 0, elevation: float = 0, zoom: float = 1,
             look_at: list[float] | None = None, bodies: list[str] | None = None, clear: bool = False):
    """
    view: vista estándar o nombre de una vista guardada.
    direction: vector [x, y, z] hacia la cámara; reemplaza a view.
    projection: perspective u orthographic.
    azimuth: órbita horizontal en grados relativa a la vista indicada.
    elevation: órbita vertical en grados relativa a la vista indicada.
    zoom: factor positivo sobre la distancia de encuadre; mayor que uno acerca.
    look_at: objetivo [x, y, z] en mm; vacío usa el centro de los cuerpos.
    bodies: cuerpos a encuadrar por nombre o id; vacío encuadra todos.
    clear: borra la cámara guardada y vuelve al encuadre automático.
    """
    datos = _datos(sesion)
    cam = None
    if not clear:
        if not all(math.isfinite(x) for x in (azimuth, elevation, zoom)) or zoom <= 0:
            raise error("INVALID_ARGUMENTS", "La órbita necesita ángulos finitos y zoom debe ser finito y positivo.")
        if look_at and (len(look_at) != 3 or not all(math.isfinite(x) for x in look_at)):
            raise error("INVALID_ARGUMENTS", "look_at necesita tres números finitos [x, y, z].")
        cam = _encuadrar(sesion, view, direction, bodies)
        if azimuth or elevation:
            b = np.asarray(cam["R"])[2]
            a = math.atan2(b[1], b[0]) + math.radians(azimuth)
            e = max(-math.pi / 2, min(math.pi / 2, math.asin(float(np.clip(b[2], -1, 1))) + math.radians(elevation)))
            cam = _encuadrar(sesion, direction=[math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)],
                             bodies=bodies)
        cam["distancia"] /= zoom
        if not math.isfinite(cam["distancia"]) or cam["distancia"] <= 0:
            raise error("INVALID_ARGUMENTS", "El zoom deja una distancia de cámara fuera de rango.")
        if look_at:
            cam["objetivo"] = list(look_at)
        cam["ortografica"] = projection == "orthographic"
    datos["camara"] = cam
    sesion.doc.espacios["visor"] = datos
    return {"camera": copy.deepcopy(cam)}


@herramienta("manage_named_views", "inspeccion", "Lista, guarda, aplica, renombra o elimina vistas con nombre "
             "compatibles con el navegador de la ventana. Como en la ventana, no entran en deshacer.", modifica=True)
def manage_named_views(sesion, action: Literal["list", "save", "apply", "rename", "delete"],
                       name: str = "", new_name: str = ""):
    """
    action: list, save, apply, rename o delete.
    name: nombre de la vista guardada.
    new_name: nombre nuevo para rename.
    """
    name, new_name = name.strip(), new_name.strip()
    vistas = sesion.doc.vistas
    if action != "list":
        if not name or (action != "save" and name not in vistas):
            raise error("INVALID_ARGUMENTS", "Indicá el nombre de una vista válida.")
        if action == "save":
            if name in vistas or name in _VISTAS:
                raise error("INVALID_ARGUMENTS", "Ese nombre de vista ya está en uso.")
            cam = _datos(sesion).get("camara") or _encuadrar(sesion)
            vistas[name] = {**copy.deepcopy(cam), "camara": "ortografica" if cam["ortografica"] else "perspectiva"}
        elif action == "apply":
            datos = _datos(sesion)
            datos["camara"] = _vista_guardada(sesion, name)
            sesion.doc.espacios["visor"] = datos
        else:
            if action == "rename" and (not new_name or new_name in vistas or new_name in _VISTAS):
                raise error("INVALID_ARGUMENTS", "El nombre nuevo está vacío o ya está en uso.")
            cam = vistas.pop(name)
            if action == "rename":
                vistas[new_name] = cam
        sesion.doc.modificado = True
    return {"views": [{"name": n, "camera": _vista_guardada(sesion, n)} for n in vistas], "count": len(vistas)}


@herramienta("set_grid", "inspeccion", "Guarda mostrar rejilla, forzar a la rejilla y cuatro vistas. "
             "La imagen dibuja la rejilla del suelo cuando está visible.", modifica=True)
def set_grid(sesion, show: bool | None = None, snap: bool | None = None, four_views: bool | None = None):
    """
    show: muestra u oculta la rejilla del suelo.
    snap: activa o desactiva forzar a la rejilla.
    four_views: activa o desactiva la opción de cuatro vistas.
    """
    datos = _datos(sesion)
    rejilla = {"mostrar": False, "forzar": False, "cuatro_vistas": False, **datos.get("rejilla", {})}
    for clave, valor in (("mostrar", show), ("forzar", snap), ("cuatro_vistas", four_views)):
        if valor is not None:
            rejilla[clave] = valor
    datos["rejilla"] = rejilla
    sesion.doc.espacios["visor"] = datos
    return {"show": rejilla["mostrar"], "snap": rejilla["forzar"], "four_views": rejilla["cuatro_vistas"]}


@herramienta("set_flat_pattern_view", "chapa", "Activa solo el desarrollo de chapa o vuelve al modelo plegado. "
             "Admite deshacer.", modifica=True)
def set_flat_pattern_view(sesion, active: bool = True, body: str | None = None):
    """
    active: true activa el patrón plano; false termina su visualización.
    body: cuerpo de chapa o su patrón por nombre o id; vacío elige el último patrón.
    """
    elegido = None
    if active:
        cid = sesion.cuerpo(body).id if body else None
        patrones = [c for c in sesion.doc.estado_final.cuerpos.values() if ops_chapa.es_patron_plano(c)
                    and (cid is None or c.id == cid or c.chapa.get("patron_de") == cid)]
        if not patrones:
            raise error("INVALID_ARGUMENTS", "No hay un patrón plano para ese cuerpo o diseño.",
                        "Creá el desarrollo con create_flat_pattern.")
        elegido = patrones[-1].id
    datos = _datos(sesion)
    datos["patron_activo"] = elegido
    sesion.doc.espacios["visor"] = datos
    return {"active": elegido is not None, "body": elegido}
