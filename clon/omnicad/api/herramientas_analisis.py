# -*- coding: utf-8 -*-
"""Análisis de INSPECCIONAR y estilo visual del visor, para agentes y sin ventana (B-80, MCP-26, MCP-44 y MCP-45).

  - `manage_analysis`: la carpeta «Análisis» del navegador (sección, cebra, mapa de entorno, desmoldeo, curvatura,
    peine, isocurvas, accesibilidad, radio mínimo y centro de masa): lista, agrega, edita, muestra, oculta y quita.
    `get_viewport_image` dibuja
    los visibles, igual que la ventana (`timeline/analisis_vista.py` los calcula en los dos lados).
  - `analyze_geometry`: lo MEDIDO de cada análisis (áreas, curvaturas, ángulos, porcentajes), sin guardar nada.
  - `section_view`: atajo de la sección: crea el análisis y devuelve su área y su contorno.
  - `set_visual_style`: estilo visual, entorno y efectos del visor (los usa `get_viewport_image`).
"""
import copy
from typing import Literal

import numpy as np

from ..nucleo import analisis as an
from ..nucleo import render_cpu as rc
from ..nucleo import render_estilos as re
from ..timeline import entidades as ent
from .errores import ErrorAPI, error
from .herramientas_construccion import _referencia
from .herramientas_modificar import _refs
from .registro import herramienta

TIPOS = {"section": "seccion", "zebra": "cebra", "environment_map": "mapa_entorno", "draft": "desmoldeo",
         "curvature": "curvatura", "comb": "peine", "isocurve": "isocurva", "accessibility": "accesibilidad",
         "min_radius": "radio_minimo", "center_of_mass": "centro_masa"}
SENTIDOS = {"direction_1": "dir1", "direction_2": "dir2", "both": "ambas"}
CURVATURAS = {"gaussian": "gaussiana", "mean": "media", "max": "maxima", "min": "minima"}
# Opciones que acepta cada tipo (el resto es un error: no se ignora en silencio).
OPCIONES = {"section": {"plane", "offset", "angle", "flip", "bodies", "body", "section_color", "custom_color", "hatch"},
            "zebra": {"frequency", "orientation", "bodies", "opacity", "lock_stripes", "high_quality"},
            "environment_map": {"bodies", "environment", "rotation", "mirror_finish"},
            "draft": {"direction", "min_angle", "max_angle", "flip", "bodies", "body", "gradient", "tolerance_min",
                      "tolerance_max", "opacity", "high_quality"},
            "curvature": {"curvature_type", "bodies", "display", "scale", "limit", "opacity", "high_quality"},
            "comb": {"edges", "density", "scale", "body"},
            "isocurve": {"density", "bodies", "isocurve_type", "combs", "comb_density", "comb_scale", "faces", "body"},
            "accessibility": {"direction", "flip", "bodies", "body", "change_direction", "opacity"},
            "min_radius": {"radius", "bodies", "min_radius", "sharp_edges", "opacity"},
            "center_of_mass": {"bodies", "components"}}


def _numero(valor, que, minimo=None, maximo=None):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not np.isfinite(valor):
        raise error("INVALID_ARGUMENTS", f"{que} tiene que ser un número finito: llegó {valor!r}.")
    if (minimo is not None and valor < minimo) or (maximo is not None and valor > maximo):
        raise error("INVALID_ARGUMENTS", f"{que} tiene que estar entre {minimo} y {maximo}: llegó {valor!r}.")
    return valor


def _direccion(sesion, valor, body):
    """Dirección de extracción o de acceso: "x", "y", "z" (ejes del origen), un eje, una arista recta o una cara plana."""
    if valor is None:
        return None
    if isinstance(valor, str) and valor.strip().lower() in ("x", "y", "z"):
        return {"tipo": "eje", "id": valor.strip().upper()}
    return _referencia(sesion, valor, {"eje", "arista", "curva_boceto", "cara", "plano"}, body, "direccion")


def _rgb_hex(valor):
    """«#RRGGBB» → [r, g, b] de 0 a 1."""
    t = valor.strip().lstrip("#") if isinstance(valor, str) else ""
    if len(t) != 6 or any(c not in "0123456789abcdefABCDEF" for c in t):
        raise error("INVALID_ARGUMENTS", f"custom_color: se espera un color «#RRGGBB», llegó {valor!r}.")
    return [round(int(t[i:i + 2], 16) / 255, 4) for i in (0, 2, 4)]


def _comunes_vista(p, dado):
    """Opacidad y Calidad alta: solo si se piden (un análisis sin ellas guarda lo mismo que antes)."""
    if dado.get("opacity") is not None:
        p["opacidad"] = int(_numero(dado["opacity"], "opacity", 0, 100))
    if dado.get("high_quality"):
        p["alta_calidad"] = True


def _parametros(sesion, tipo, dado):
    """Parámetros internos del análisis (los que guarda `doc.analisis`) a partir de las opciones de la API."""
    sobran = set(dado) - OPCIONES[tipo]
    if sobran:
        raise error("INVALID_ARGUMENTS", f"El análisis «{tipo}» no usa {', '.join(sorted(sobran))}.",
                    f"Opciones de {tipo}: {', '.join(sorted(OPCIONES[tipo])) or 'ninguna'}.")
    p, body = {}, dado.get("body")
    if dado.get("bodies"):
        p["cuerpos"] = [sesion.cuerpo(c).id for c in dado["bodies"]]
    if tipo == "section":
        if dado.get("plane") is None:
            raise error("INVALID_ARGUMENTS", "La sección necesita plane: XY, XZ, YZ, un plano de construcción o una cara plana.")
        p.update(plano=_referencia(sesion, dado["plane"], {"plano", "cara"}, body, "plano"),
                 desfase_mm=float(_numero(dado.get("offset", 0), "offset")), invertir=bool(dado.get("flip", False)))
        if dado.get("angle"):
            p["angulo"] = float(_numero(dado["angle"], "angle", -360, 360))
        modo = dado.get("section_color", "custom")
        if modo not in ("component", "custom"):
            raise error("INVALID_ARGUMENTS", "section_color es component (el color de cada cuerpo) o custom (uno elegido).")
        if modo == "component":
            if dado.get("custom_color") is not None:
                raise error("INVALID_ARGUMENTS", "custom_color solo se usa con section_color=custom.")
            p["color_modo"] = "componente"
        elif dado.get("custom_color") is not None:
            p["color"] = _rgb_hex(dado["custom_color"])
        if dado.get("hatch"):
            p["rayado"] = True
    elif tipo == "zebra":
        orientacion = dado.get("orientation", "horizontal")
        if orientacion not in ("horizontal", "vertical"):
            raise error("INVALID_ARGUMENTS", "orientation es horizontal o vertical.")
        p.update(frecuencia=int(_numero(dado.get("frequency", 8), "frequency", 1, 100)), orientacion=orientacion)
        _comunes_vista(p, dado)
        if dado.get("lock_stripes"):
            p["vista_fija"] = [0.0, -1.0, 0.0]                   # rayas fijas al cuerpo, las de la vista de frente
    elif tipo in ("draft", "accessibility"):
        p["direccion"] = _direccion(sesion, dado.get("direction"), body)
        p["invertir"] = bool(dado.get("flip", False))
        if p["direccion"] is None:
            del p["direccion"]                                   # sin dirección, +Z (la extracción de siempre)
        if tipo == "draft":
            lo, hi = (float(_numero(dado.get(k, d), k)) for k, d in (("min_angle", 0.0), ("max_angle", 3.0)))
            if hi < lo:
                raise error("INVALID_ARGUMENTS", "max_angle tiene que ser mayor o igual que min_angle.")
            p.update(angulo_min=lo, angulo_max=hi)
            _comunes_vista(p, dado)
            if dado.get("gradient"):
                p["degradado"] = True
            if dado.get("tolerance_min") is not None or dado.get("tolerance_max") is not None:
                t0, t1 = (float(_numero(dado.get(k), k)) for k in ("tolerance_min", "tolerance_max"))
                if t1 < t0:
                    raise error("INVALID_ARGUMENTS", "tolerance_max tiene que ser mayor o igual que tolerance_min.")
                p.update(degradado=True, tolerancia=[t0, t1])
        else:
            _comunes_vista(p, dado)
            if dado.get("change_direction") is not None:
                if dado["change_direction"] not in SENTIDOS:
                    raise error("INVALID_ARGUMENTS", f"change_direction: {', '.join(SENTIDOS)}.")
                p["sentido"] = SENTIDOS[dado["change_direction"]]
    elif tipo == "environment_map":
        entorno = dado.get("environment")
        if entorno is not None and entorno not in an.ENTORNOS_ANALISIS:
            raise error("INVALID_ARGUMENTS", f"Entorno desconocido «{entorno}».", f"Entornos: {', '.join(an.ENTORNOS_ANALISIS)}.")
        if entorno is not None:
            p["entorno"] = entorno
        if dado.get("rotation") is not None:
            p["rotacion"] = float(_numero(dado["rotation"], "rotation", -360, 360))
        if dado.get("mirror_finish") is not None:
            p["reflejo"] = bool(dado["mirror_finish"])
    elif tipo == "center_of_mass":
        from .herramientas_ensamble import componente
        if dado.get("components"):
            p["componentes"] = [componente(sesion, c) for c in dado["components"]]
    elif tipo == "curvature":
        t = dado.get("curvature_type", "gaussian")
        if t not in CURVATURAS:
            raise error("INVALID_ARGUMENTS", f"curvature_type: {', '.join(CURVATURAS)}.")
        p["tipo_curvatura"] = CURVATURAS[t]
        _comunes_vista(p, dado)
        if dado.get("display", "smooth") not in ("smooth", "bands"):
            raise error("INVALID_ARGUMENTS", "display es smooth o bands.")
        if dado.get("display") == "bands":
            p["bandas"] = True
        if dado.get("scale") is not None:
            p["escala"] = float(_numero(dado["scale"], "scale", 1e-6, 1e6))
        if dado.get("limit") is not None:
            p["limite"] = float(_numero(dado["limit"], "limit", 1e-9))
    elif tipo == "comb":
        if not dado.get("edges"):
            raise error("INVALID_ARGUMENTS", "El peine de curvatura necesita edges (selector o ids de find_edges).")
        p.update(aristas=_refs(sesion, dado["edges"], "arista", body)[0],
                 densidad=int(_numero(dado.get("density", 30), "density", 2, 500)),
                 escala=float(_numero(dado.get("scale", 1.0), "scale", 1e-6, 1e6)))
    elif tipo == "isocurve":
        sentidos = dado.get("isocurve_type", "both")
        if sentidos not in ("both", "u", "v"):
            raise error("INVALID_ARGUMENTS", "isocurve_type es both, u o v.")
        p["densidad"] = int(_numero(dado.get("density", 10), "density", 1, 100))
        if sentidos != "both":
            p["tipo_iso"] = sentidos
        if dado.get("combs"):
            p.update(peines=True, densidad_peine=int(_numero(dado.get("comb_density", 50), "comb_density", 3, 500)),
                     escala_peine=float(_numero(dado.get("comb_scale", 10.0), "comb_scale", 1e-6, 1e6)))
        if dado.get("faces"):
            p["caras"] = _refs(sesion, dado["faces"], "cara", body)[0]
    elif tipo == "min_radius":
        p["radio"] = float(_numero(dado.get("radius", 3.0), "radius", 1e-9))
        _comunes_vista(p, dado)
        if dado.get("min_radius") is not None:
            p["radio_minimo"] = float(_numero(dado["min_radius"], "min_radius", 0, p["radio"]))
        if dado.get("sharp_edges") is not None:
            p["aristas_vivas"] = bool(dado["sharp_edges"])
    return p


def _info(nombre, a):
    return {"name": nombre, "type": next(k for k, v in TIPOS.items() if v == a["tipo"]),
            "visible": bool(a.get("visible", True))}


def _nombre_existente(sesion, name):
    if name not in sesion.doc.analisis:
        raise error("INVALID_ARGUMENTS", f"No existe el análisis «{name}».",
                    f"Existen: {', '.join(sesion.doc.analisis) or 'ninguno'}.")


@herramienta("manage_analysis", "inspeccion", "Carpeta «Análisis» del documento: agrega, lista, muestra, oculta y quita "
             "análisis de INSPECCIONAR: sección, cebra, mapa de entorno, desmoldeo, curvatura, peine de curvatura, "
             "isocurvas, accesibilidad, radio mínimo y centro de masa. Los visibles se dibujan en get_viewport_image. Para los números "
             "(áreas, ángulos, curvaturas) usá analyze_geometry. Admite deshacer.", modifica=True)
def manage_analysis(sesion, action: Literal["list", "add", "edit", "remove", "show", "hide"] = "list",
                    type: Literal["section", "zebra", "environment_map", "draft", "curvature", "comb", "isocurve",
                                  "accessibility", "min_radius", "center_of_mass"] | None = None,
                    name: str | None = None, bodies: list[str] | None = None, plane: str | dict | None = None,
                    offset: float | None = None, flip: bool | None = None, frequency: int | None = None,
                    orientation: Literal["horizontal", "vertical"] | None = None,
                    direction: str | dict | None = None, min_angle: float | None = None,
                    max_angle: float | None = None, curvature_type: Literal["gaussian", "mean", "max", "min"] | None = None,
                    edges: str | list[str] | None = None, density: int | None = None, scale: float | None = None,
                    radius: float | None = None, body: str | None = None,
                    section_color: Literal["component", "custom"] | None = None, custom_color: str | None = None,
                    hatch: bool | None = None, opacity: int | None = None, lock_stripes: bool | None = None,
                    high_quality: bool | None = None, display: Literal["smooth", "bands"] | None = None,
                    limit: float | None = None, isocurve_type: Literal["both", "u", "v"] | None = None,
                    combs: bool | None = None, comb_density: int | None = None, comb_scale: float | None = None,
                    environment: str | None = None, rotation: float | None = None, mirror_finish: bool | None = None,
                    gradient: bool | None = None, tolerance_min: float | None = None, tolerance_max: float | None = None,
                    change_direction: Literal["direction_1", "direction_2", "both"] | None = None,
                    min_radius: float | None = None, sharp_edges: bool | None = None, faces: str | list[str] | None = None,
                    components: list[str] | None = None):
    """
    action: list (los del documento), add (crea uno), edit (reemplaza las opciones de name: lo que no se pase vuelve a su valor por defecto), remove, show o hide (por name).
    type: con add: section (corte con plano), zebra, environment_map, draft (desmoldeo), curvature, comb (peine de curvatura de aristas), isocurve, accessibility, min_radius (fresa) o center_of_mass.
    name: nombre del análisis (con add, vacío = automático, p. ej. «Sección1»).
    bodies: cuerpos que se analizan (id o nombre); vacío = todos los sólidos. Para todos menos comb.
    plane: section: XY, XZ, YZ, un plano de construcción (id o nombre) o una cara plana (selector).
    offset: section: desfase del plano en mm sobre su normal; 0 por defecto.
    flip: section: conserva el otro lado; draft y accessibility: invierte la dirección.
    frequency: zebra: cantidad de franjas (1 a 100); 8 por defecto.
    orientation: zebra: horizontal (por defecto) o vertical.
    direction: draft y accessibility: "x", "y", "z", un eje, una arista recta o una cara plana (hacia afuera del material); vacío = +Z.
    min_angle: draft: ángulo en grados bajo el cual la cara se pinta de rojo; 0 por defecto.
    max_angle: draft: ángulo en grados desde el cual la cara se pinta de verde; 3 por defecto.
    curvature_type: curvature: gaussian (por defecto), mean, max o min.
    edges: comb: aristas (selector o ids de find_edges, o lista).
    density: comb: púas por arista (30 por defecto); isocurve: curvas por dirección (10 por defecto).
    scale: comb: largo de las púas (1 por defecto); curvature: multiplica el degradé (1 por defecto).
    radius: min_radius: radio de la fresa en mm (3 por defecto).
    body: cuerpo donde se evalúan los selectores de plane, direction y edges; vacío = el único cuerpo.
    section_color: section: component (la tapa toma el color de cada cuerpo) o custom (un solo color para todo el corte); custom por defecto.
    custom_color: section con section_color=custom: color de la tapa como «#RRGGBB»; vacío = el rojo de siempre.
    hatch: section: true dibuja el rayado diagonal sobre las caras del corte; false por defecto.
    opacity: zebra, curvature, draft, accessibility y min_radius: opacidad del análisis sobre el cuerpo, 0 a 100 (100 por defecto).
    lock_stripes: zebra: true deja las rayas fijas al cuerpo; false (por defecto) siguen a la cámara.
    high_quality: zebra, curvature y draft: true calcula sobre una malla más fina.
    display: curvature: smooth (por defecto) o bands.
    limit: curvature: curvatura en 1/mm que llega al rojo (Límite de Principal mínima y máxima); vacío = automático.
    isocurve_type: isocurve: both (por defecto), u o v.
    combs: isocurve: true dibuja la curvatura en peines sobre cada isocurva.
    comb_density: isocurve: púas por isocurva (50 por defecto).
    comb_scale: isocurve: largo relativo de las púas (10 por defecto).
    environment: environment_map: entorno (campo, campo_nieve, claraboya, cruce, fotomaton, lecho_lago, luz_calida, luz_rejilla, luz_fria, luz_suave, plaza, resaltado_cerco o resaltado_nitido); vacío = el reflejo de siempre.
    rotation: environment_map: giro del entorno en grados, de -360 a 360.
    mirror_finish: environment_map: true (por defecto) acabado de espejo; false, sombreado.
    gradient: draft: true pinta un degradé continuo entre min_angle y max_angle en lugar de tres zonas.
    tolerance_min: draft: inicio de la Zona de tolerancia (amarilla), en grados; necesita tolerance_max.
    tolerance_max: draft: fin de la Zona de tolerancia, en grados; necesita tolerance_min.
    change_direction: accessibility: direction_1 (por defecto), direction_2 (al revés) o both.
    min_radius: min_radius: radio mínimo en mm: da el degradé de rojo a verde hasta radius, que pasa a ser el máximo.
    sharp_edges: min_radius: true (por defecto) marca los rincones sin empalme.
    faces: isocurve: caras (selector o ids de find_faces); se suman a bodies.
    components: center_of_mass: componentes (id o nombre) que entran con todos sus cuerpos.
    """
    doc = sesion.doc
    if action == "list":
        return {"analyses": [_info(n, a) for n, a in doc.analisis.items()], "count": len(doc.analisis)}
    if action in ("remove", "show", "hide"):
        if name is None:
            raise error("INVALID_ARGUMENTS", f"{action} necesita name.")
        _nombre_existente(sesion, name)
        if action == "remove":
            doc.quitar_analisis(name)
        elif bool(doc.analisis[name].get("visible", True)) != (action == "show"):
            doc._guardar_para_deshacer()
            doc.alternar_analisis(name)
        return {"analyses": [_info(n, a) for n, a in doc.analisis.items()], "count": len(doc.analisis)}
    if action == "edit":
        if name is None:
            raise error("INVALID_ARGUMENTS", "edit necesita name.")
        _nombre_existente(sesion, name)
        type = _info(name, doc.analisis[name])["type"]
    if type is None:
        raise error("INVALID_ARGUMENTS", "add necesita type.", f"Tipos: {', '.join(TIPOS)}.")
    dado = {k: v for k, v in dict(bodies=bodies, plane=plane, offset=offset, flip=flip, frequency=frequency,
                                  orientation=orientation, direction=direction, min_angle=min_angle,
                                  max_angle=max_angle, curvature_type=curvature_type, edges=edges, density=density,
                                  scale=scale, radius=radius, body=body, section_color=section_color,
                                  custom_color=custom_color, hatch=hatch, opacity=opacity, lock_stripes=lock_stripes,
                                  high_quality=high_quality, display=display, limit=limit, isocurve_type=isocurve_type,
                                  combs=combs, comb_density=comb_density, comb_scale=comb_scale, environment=environment,
                                  rotation=rotation, mirror_finish=mirror_finish, gradient=gradient,
                                  tolerance_min=tolerance_min, tolerance_max=tolerance_max,
                                  change_direction=change_direction, min_radius=min_radius, sharp_edges=sharp_edges,
                                  faces=faces, components=components).items() if v is not None}
    if action == "edit":
        doc.editar_analisis(name, _parametros(sesion, type, dado))
        return {"analysis": _info(name, doc.analisis[name]), "count": len(doc.analisis)}
    if name and name.strip() in doc.analisis:
        raise error("INVALID_ARGUMENTS", f"Ya existe un análisis llamado «{name.strip()}».")
    creado = doc.agregar_analisis(TIPOS[type], _parametros(sesion, type, dado), name.strip() if name else None)
    return {"analysis": _info(creado, doc.analisis[creado]), "count": len(doc.analisis)}


# ---------------------------------------------------------------- lo medido
def _cuerpos_de(sesion, bodies):
    todos = [c for c in sesion.doc.estado_final.cuerpos.values() if getattr(c, "tipo", "solido") != "malla"]
    elegidos = [sesion.cuerpo(b) for b in bodies] if bodies else todos
    elegidos = [c for c in elegidos if getattr(c, "tipo", "solido") != "malla"]
    if not elegidos:
        raise error("NOTHING_TO_MEASURE", "No hay cuerpos con geometría exacta para analizar.",
                    "Las mallas no se analizan: convertilas con convert_mesh.")
    return elegidos


def _estadisticas(valores, decimales=6):
    v = np.asarray(valores, float)
    return {"min": round(float(v.min()), decimales), "max": round(float(v.max()), decimales),
            "mean": round(float(v.mean()), decimales), "p5": round(float(np.percentile(v, 5)), decimales),
            "p95": round(float(np.percentile(v, 95)), decimales)}


def _porcentaje(mascara):
    return round(100.0 * float(np.mean(mascara)), 2)


def _medida(sesion, tipo, p, cuerpo):
    """Números del análisis `tipo` (parámetros internos `p`) sobre un cuerpo."""
    forma = cuerpo.forma
    estado = sesion.doc.estado_final
    if tipo == "section":
        plano = ent.como_plano(ent.resolver(p["plano"], estado)).desplazado(p["desfase_mm"]).girado(p.get("angulo", 0.0))
        datos = an.seccion(forma, plano)
        puntos = [q for linea in datos["polilineas"] for q in linea]
        caja = ({"min": np.min(puntos, 0).round(6).tolist(), "max": np.max(puntos, 0).round(6).tolist()}
                if puntos else None)
        return {"area_mm2": round(float(datos["area"]), 6), "contour_length_mm": round(float(datos["largo"]), 6),
                "contour_box": caja, "intersects": bool(puntos)}
    if tipo == "curvature":
        _v, _n, k = an.valores_curvatura(forma, tipo=p["tipo_curvatura"])
        return {"curvature_type": next(c for c, i in CURVATURAS.items() if i == p["tipo_curvatura"]),
                "unit": "1/mm²" if p["tipo_curvatura"] == "gaussiana" else "1/mm", **_estadisticas(k),
                "convex_percent": _porcentaje(k > 1e-9), "concave_percent": _porcentaje(k < -1e-9)}
    if tipo == "draft":
        from ..timeline.analisis_vista import _direccion as direccion_de
        d = direccion_de(p, estado)
        lo, hi = p["angulo_min"], p["angulo_max"]
        _v, _n, a = an.angulos_desmoldeo(forma, d)
        zona = {"tolerance_percent": _porcentaje((a >= p["tolerancia"][0]) & (a <= p["tolerancia"][1]))} if "tolerancia" in p else {}
        return {"angle_deg": _estadisticas(a, 3), "sufficient_percent": _porcentaje(a >= hi - 1e-6),
                "neutral_percent": _porcentaje((a > lo + 1e-6) & (a < hi - 1e-6)), **zona,
                "insufficient_percent": _porcentaje(a <= lo + 1e-6), "direction": [round(float(x), 6) for x in d]}
    if tipo == "accessibility":
        from ..timeline.analisis_vista import _direccion as direccion_de
        d = direccion_de(p, estado)
        d = -d if p.get("sentido") == "dir2" else d
        _v, _n, c = an.colores_accesibilidad(forma, d, ambos_sentidos=p.get("sentido") == "ambas")
        return {"accessible_percent": _porcentaje((np.asarray(c) == np.asarray(an.VERDE, np.float32)).all(1)),
                "direction": [round(float(x), 6) for x in d]}
    if tipo == "min_radius":
        _v, _n, c = an.colores_radio_minimo(forma, p["radio"], **{k: p[k] for k in ("radio_minimo", "aristas_vivas") if k in p})
        return {"tool_radius_mm": p["radio"],
                "blocked_percent": _porcentaje((np.asarray(c) == np.asarray(an.ROJO, np.float32)).all(1))}
    if tipo == "isocurve":
        datos = an.isocurvas(forma, n_u=p["densidad"], n_v=p["densidad"])
        return {"u_curves": len(datos["u"]), "v_curves": len(datos["v"])}
    raise error("INVALID_ARGUMENTS", f"«{tipo}» solo se ve en la imagen: no tiene números.",
                "Usá manage_analysis (add) y get_viewport_image.")


@herramienta("analyze_geometry", "inspeccion", "Mide con un análisis de INSPECCIONAR sin guardarlo: section (área y "
             "contorno), curvature (mínimo, máximo, media y percentiles), draft (ángulos y porcentaje de caras con "
             "desmoldeo suficiente), accessibility (porcentaje accesible), min_radius (porcentaje que la fresa no "
             "alcanza) e isocurve, por cuerpo; y center_of_mass, el punto y la masa de todo lo elegido. Los análisis "
             "puramente visuales (zebra, environment_map, comb) se ven con manage_analysis y get_viewport_image.")
def analyze_geometry(sesion, type: Literal["section", "curvature", "draft", "accessibility", "min_radius", "isocurve",
                                           "center_of_mass"],
                     bodies: list[str] | None = None, plane: str | dict | None = None, offset: float | None = None,
                     flip: bool | None = None, direction: str | dict | None = None, min_angle: float | None = None,
                     max_angle: float | None = None, curvature_type: Literal["gaussian", "mean", "max", "min"] | None = None,
                     density: int | None = None, radius: float | None = None, body: str | None = None,
                     tolerance_min: float | None = None, tolerance_max: float | None = None,
                     change_direction: Literal["direction_1", "direction_2", "both"] | None = None,
                     min_radius: float | None = None, sharp_edges: bool | None = None, components: list[str] | None = None):
    """
    type: section, curvature, draft, accessibility, min_radius, isocurve o center_of_mass.
    bodies: cuerpos a medir (id o nombre); vacío = todos los sólidos.
    plane: section: XY, XZ, YZ, un plano de construcción o una cara plana.
    offset: section: desfase del plano en mm; 0 por defecto.
    flip: draft y accessibility: invierte la dirección.
    direction: draft y accessibility: "x", "y", "z", un eje, una arista recta o una cara plana; vacío = +Z.
    min_angle: draft: ángulo en grados bajo el cual el desmoldeo es insuficiente; 0 por defecto.
    max_angle: draft: ángulo en grados desde el cual es suficiente; 3 por defecto.
    curvature_type: curvature: gaussian (por defecto), mean, max o min.
    density: isocurve: curvas por dirección; 10 por defecto.
    radius: min_radius: radio de la fresa en mm; 3 por defecto.
    body: cuerpo donde se evalúan los selectores de plane y direction; vacío = el único cuerpo.
    tolerance_min: draft: inicio de la Zona de tolerancia en grados: agrega tolerance_percent.
    tolerance_max: draft: fin de la Zona de tolerancia en grados.
    change_direction: accessibility: direction_1 (por defecto), direction_2 (al revés) o both.
    min_radius: min_radius: radio mínimo en mm; radius pasa a ser el máximo.
    sharp_edges: min_radius: true (por defecto) cuenta los rincones sin empalme.
    components: center_of_mass: componentes (id o nombre) que entran con todos sus cuerpos.
    """
    dado = {k: v for k, v in dict(plane=plane, offset=offset, flip=flip, direction=direction, min_angle=min_angle,
                                  max_angle=max_angle, curvature_type=curvature_type, density=density,
                                  radius=radius, body=body, tolerance_min=tolerance_min, tolerance_max=tolerance_max,
                                  change_direction=change_direction, min_radius=min_radius, sharp_edges=sharp_edges,
                                  components=components, bodies=bodies if type == "center_of_mass" else None).items()
            if v is not None}
    p = _parametros(sesion, type, dado)
    if type == "center_of_mass":
        from ..timeline.analisis_vista import centro_de_masa
        punto, masa = centro_de_masa(p, sesion.doc.estado_final, sesion.doc.propiedades)
        if punto is None:
            raise error("NOTHING_TO_MEASURE", "No hay cuerpos sólidos para calcular el centro de masa.")
        return {"type": type, "center_of_mass": [round(float(x), 6) for x in punto], "mass_g": round(float(masa), 6)}
    por_cuerpo = []
    for c in _cuerpos_de(sesion, bodies):
        try:
            por_cuerpo.append({"body": c.id, "name": sesion.nombre_cuerpo(c), **_medida(sesion, type, p, c)})
        except ErrorAPI:
            raise
        except Exception as e:  # noqa: BLE001 — el kernel o el cálculo fallaron en este cuerpo
            raise error("OPERATION_FAILED", f"No se pudo analizar «{c.id}»: {e}") from e
    return {"type": type, "bodies": por_cuerpo}


@herramienta("section_view", "inspeccion", "Análisis de sección: corta con un plano (XY, XZ, YZ, un plano de construcción "
             "o una cara plana), lo guarda en la carpeta «Análisis» y devuelve el área y el contorno de cada cuerpo. "
             "get_viewport_image dibuja la parte de atrás del plano con su tapa. show=false lo deja oculto; "
             "manage_analysis (hide o remove) lo apaga.", modifica=True)
def section_view(sesion, plane: str | dict, offset: float = 0, flip: bool = False, bodies: list[str] | None = None,
                 name: str | None = None, show: bool = True, body: str | None = None, angle: float = 0,
                 section_color: Literal["component", "custom"] = "custom", custom_color: str | None = None,
                 hatch: bool = False):
    """
    plane: XY, XZ, YZ, un plano de construcción (id o nombre) o una cara plana (selector).
    offset: desfase del plano en mm sobre su normal.
    angle: giro del plano en grados (entre −360 y 360) alrededor de su eje u, después del desfase.
    flip: true conserva el lado de la normal en vez del lado de atrás.
    bodies: cuerpos a cortar (id o nombre); vacío = todos los sólidos.
    name: nombre del análisis; vacío = automático (Sección1…).
    show: false deja el análisis creado pero oculto.
    body: cuerpo donde se evalúa el selector de plane; vacío = el único cuerpo.
    section_color: component (la tapa toma el color de cada cuerpo) o custom (un solo color para todo el corte).
    custom_color: con section_color=custom, el color de la tapa como «#RRGGBB»; vacío = el rojo de siempre.
    hatch: true dibuja el rayado diagonal sobre las caras del corte.
    """
    cuerpos = _cuerpos_de(sesion, bodies)
    p = _parametros(sesion, "section", {k: v for k, v in dict(plane=plane, offset=offset, angle=angle, flip=flip,
                                                              bodies=bodies, body=body, section_color=section_color,
                                                              custom_color=custom_color, hatch=hatch).items() if v is not None})
    medidas = [{"body": c.id, "name": sesion.nombre_cuerpo(c), **_medida(sesion, "section", p, c)} for c in cuerpos]
    doc = sesion.doc
    if name and name.strip() in doc.analisis:
        raise error("INVALID_ARGUMENTS", f"Ya existe un análisis llamado «{name.strip()}».")
    nombre = doc.agregar_analisis("seccion", p, name.strip() if name else None)
    if not show:
        doc.alternar_analisis(nombre)
    return {"analysis": _info(nombre, doc.analisis[nombre]), "bodies": medidas}


# ---------------------------------------------------------------- estilo visual
EFECTOS = {"shadows": "sombras", "reflections": "reflejos", "ambient_occlusion": "oclusion", "ground_plane": "suelo"}


def estilo_guardado(sesion):
    """Estilo guardado del visor: {"estilo" (clave de re.ESTILOS), "entorno", "efectos": {sombras, reflejos…}}."""
    datos = (sesion.doc.espacios.get("visor") or {}).get("estilo") or {}
    return {"estilo": datos.get("estilo", "shaded"), "entorno": datos.get("entorno"),
            "efectos": dict(datos.get("efectos") or {})}


@herramienta("set_visual_style", "inspeccion", "Guarda el estilo visual del visor: uno de los seis de Fusion (shaded, "
             "shaded_hidden_edges, shaded_visible_edges, wireframe, wireframe_hidden_edges, wireframe_visible_edges), "
             "el entorno de iluminación y los efectos (sombras, reflejos, oclusión ambiental y suelo). "
             "get_viewport_image lo usa cuando no se le pide otro estilo. Sin parámetros solo lo consulta; "
             "clear=true vuelve a los valores de fábrica. Admite deshacer.", modifica=True)
def set_visual_style(sesion, style: Literal["shaded", "shaded_hidden_edges", "shaded_visible_edges", "wireframe",
                                            "wireframe_hidden_edges", "wireframe_visible_edges"] | None = None,
                     environment: str | None = None, shadows: bool | None = None, reflections: bool | None = None,
                     ambient_occlusion: bool | None = None, ground_plane: bool | None = None, clear: bool = False):
    """
    style: shaded, shaded_hidden_edges (sombreado con aristas ocultas), shaded_visible_edges (sombreado con solo aristas visibles), wireframe, wireframe_hidden_edges o wireframe_visible_edges.
    environment: entorno de iluminación (clave de render_cpu.ENTORNOS, p. ej. fotomaton o tema).
    shadows: sombras del suelo.
    reflections: reflejos en el suelo.
    ambient_occlusion: oclusión ambiental.
    ground_plane: plano de suelo que recibe las sombras.
    clear: true borra el estilo guardado y vuelve a los valores de fábrica.
    """
    if style is not None and style not in re.ESTILOS:
        raise error("INVALID_ARGUMENTS", f"style: {', '.join(re.ESTILOS)}.")
    if environment is not None and environment not in rc.ENTORNOS:
        raise error("INVALID_ARGUMENTS", f"Entorno desconocido «{environment}».", f"Entornos: {', '.join(rc.ENTORNOS)}.")
    datos = copy.deepcopy(sesion.doc.espacios.get("visor") or {})
    if clear:
        datos.pop("estilo", None)
    cambios = dict(zip(EFECTOS.values(), (shadows, reflections, ambient_occlusion, ground_plane), strict=True))
    if any(v is not None for v in (style, environment, *cambios.values())):
        guardado = estilo_guardado(sesion) if not clear else {"estilo": "shaded", "entorno": None, "efectos": {}}
        if style is not None:
            guardado["estilo"] = style
        if environment is not None:
            guardado["entorno"] = environment
        guardado["efectos"].update({k: bool(v) for k, v in cambios.items() if v is not None})
        datos["estilo"] = guardado
    if datos != (sesion.doc.espacios.get("visor") or {}):
        sesion.doc.espacios["visor"] = datos
    actual = estilo_guardado(sesion)
    return {"style": actual["estilo"], "environment": actual["entorno"],
            "effects": {a: actual["efectos"].get(b) for a, b in EFECTOS.items()}}
