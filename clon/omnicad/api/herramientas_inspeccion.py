# -*- coding: utf-8 -*-
"""Herramientas del grupo "inspeccion": ver el modelo (imagen), propiedades físicas, medir e interferencias.

Todo sin Qt: la imagen sale de `nucleo.render_cpu` (rasterizador por software) y los números del núcleo
(`nucleo.analisis`, `nucleo.geometria`). Unidades: mm, mm², mm³, g (densidades en g/cm³) y grados.
"""
import io
import math
import time
from typing import Literal

import numpy as np

from ..nucleo import analisis as an
from ..nucleo import geometria as geo
from ..nucleo import render_cpu as rc
from ..nucleo import render_estilos as rs
from ..timeline import aspectos_doc as ad
from ..timeline import ops_chapa
from ..timeline.operaciones import propiedades_cuerpo
from . import selectores as sl
from .errores import ErrorAPI, error
from .herramientas_documento import _info_cuerpo, _r
from .registro import Imagen, herramienta

_LADO_MAXIMO = 2048
_LADO_MINIMO = 16
# Presupuesto de píxeles que se calculan por imagen (~1,5 s en CPU para el ejemplo): las imágenes chicas se
# calculan más grandes y se reducen (antialias); las grandes se calculan a su tamaño.
_PIXELES_RENDER = 450_000

# Dirección HACIA la cámara (desde el modelo) de cada vista, con Z hacia arriba, como las vistas del visor
# (ui/visor3d.VISTAS). «iso» es la isométrica verdadera (elevación 35,26°, la esquina del ViewCube).
_VISTAS = {"iso": (1.0, -1.0, 1.0), "front": (0.0, -1.0, 0.0), "back": (0.0, 1.0, 0.0),
           "right": (1.0, 0.0, 0.0), "left": (-1.0, 0.0, 0.0), "top": (0.0, 0.0, 1.0), "bottom": (0.0, 0.0, -1.0)}


# ---------------------------------------------------------------- cuerpos
def _cuerpos(sesion, bodies):
    """Cuerpos pedidos por id o nombre (sin repetir); sin lista = todos los del final del timeline."""
    todos = ops_chapa.cuerpos_del_modelo(sesion.doc.estado_final)     # el patrón plano no es del modelo
    if not bodies:
        return todos
    elegidos = {}
    for ref in bodies:
        c = sesion.cuerpo(ref)
        elegidos[c.id] = c
    return list(elegidos.values())


def _es_malla(c):
    return getattr(c, "tipo", "solido") == "malla"


def _es_solido(c):
    return getattr(c, "tipo", "solido") == "solido"


def _nombre_y_id(sesion, c):
    return {"id": c.id, "name": sesion.nombre_cuerpo(c)}


# ---------------------------------------------------------------- imagen
def _objetos_render(sesion, cuerpos, cam=None, alto=600, cajas=None, colores_componente=False):
    """Los mismos objetos que arma el render de la app (`render_cpu.malla_suave` y `color_y_acabado`,
    con deflexión automática por pieza y, si hay cámara, por tamaño en píxeles)."""
    objetos = []
    # Misma paleta que ui.visor3d, sin importar Qt en la API.
    paleta = [(0.62, 0.68, 0.76), (0.80, 0.62, 0.45), (0.55, 0.75, 0.58),
              (0.75, 0.58, 0.78), (0.85, 0.80, 0.50), (0.55, 0.72, 0.82)]
    colores = {cid: paleta[i % len(paleta)] for i, cid in enumerate(sesion.doc.estado_final.componentes)}
    for c in cuerpos:
        inicio = len(objetos)
        props = propiedades_cuerpo(sesion.doc.propiedades, c)
        pintadas = [(cara, p) for r, p in ad.caras_propias(props)
                    if (cara := ad.cara_de(sesion.doc.estado_final, r)) is not None]
        caja = cajas.get(c.id) if cajas is not None else None
        fina = 0.05 if _es_malla(c) else rc.deflexion_para(c.forma, caja=caja)
        deflexion = fina if _es_malla(c) else rc.deflexion_para(c.forma, cam=cam, alto=alto, caja=caja)
        angular = min(0.5, 0.25 * math.sqrt(deflexion / fina))
        v, n, partes = rc.malla_suave_aparte(c.forma, [cara for cara, _p in pintadas], deflexion, angular,
                                           independiente=cam is not None)
        opacidad = float(sesion.doc.propiedad(c.id, "opacidad", 1.0))
        if len(v):
            color, acabado = rc.color_y_acabado(c, props)
            objetos.append({"v": v, "n": n, "color": color, "acabado": acabado, "opacidad": opacidad, "cuerpo": c.id})
        for (_cara, p), (cv, cn) in zip(pintadas, partes, strict=True):       # cada cara con aspecto propio, aparte
            if len(cv):
                color, acabado = rc.color_y_acabado_cara(c, props, p)
                objetos.append({"v": cv, "n": cn, "color": color, "acabado": acabado, "opacidad": opacidad,
                                "cuerpo": c.id})
        if colores_componente and c.componente in colores:
            for objeto in objetos[inicio:]:
                objeto["color"] = colores[c.componente]
    return objetos


def _con_analisis(sesion, objetos, cam, alto, analisis):
    """Los objetos con los análisis dibujados como los dibuja la ventana: mallas de colores que reemplazan a un cuerpo,
    colores que dependen de la cámara (cebra, mapa de entorno), recorte por planos y capas (tapas, líneas).
    `analisis`: nombres, [] ninguno, None = los visibles del documento. Devuelve (objetos, cortes, nombres)."""
    from ..timeline import analisis_vista as av
    doc = sesion.doc
    explicitos = analisis is not None
    nombres = list(analisis) if explicitos else [n for n, a in doc.analisis.items() if a.get("visible", True)]
    for n in nombres:
        if n not in doc.analisis:
            raise error("INVALID_ARGUMENTS", f"No existe el análisis «{n}».",
                        f"Existen: {', '.join(doc.analisis) or 'ninguno'}.")
    resultados, aplicados = [], []
    for n in nombres:
        a = doc.analisis[n]
        try:
            resultados.append(av.calcular(a["tipo"], a["params"], doc.estado_final))
            aplicados.append(n)
        except Exception as e:  # noqa: BLE001 — como la ventana: un análisis cuya referencia se perdió no rompe la imagen
            if explicitos:
                raise error("OPERATION_FAILED", f"No se pudo calcular el análisis «{n}»: {e}") from e
            sesion.avisar(f"Análisis «{n}» omitido: {e}")
    if not resultados:
        return objetos, [], []
    datos = av.combinar(resultados)
    salida = []
    for o in objetos:
        if o.get("cuerpo") in datos["mallas"]:
            continue
        if datos["colores"] is not None:
            o = dict(o, colores=np.asarray(datos["colores"](np.asarray(o["n"], float), np.asarray(cam["R"], float)[2]),
                                           float))
        salida.append(o)
    for cid, (v, n, c) in datos["mallas"].items():
        base = next((o for o in objetos if o.get("cuerpo") == cid), None)
        if base is not None and len(v):
            salida.append(dict(base, v=v, n=n, colores=c, acabado={}))
    cortes = datos["cortes"]
    if cortes:
        salida = rs.recortar(salida, cortes)
    return salida + rs.capas_a_objetos(datos["capas"], cam, alto), cortes, aplicados


def _esquinas(cajas):
    """Las 8 esquinas de cada caja ((mín), (máx)): con solo dos esquinas opuestas la proyección no acota la caja
    y la imagen sale recortada."""
    return np.array([(x, y, z) for c0, c1 in cajas for x in (c0[0], c1[0]) for y in (c0[1], c1[1])
                     for z in (c0[2], c1[2])], float)


def _camara(atras, puntos, aspecto, fov):
    """Cámara perspectiva mirando al centro de `puntos` desde la dirección `atras` (hacia el ojo), con la
    distancia justa para que entren todos los puntos (cada uno se proyecta y se exige que caiga dentro de
    la pirámide de visión; 6 % de margen)."""
    atras = np.asarray(atras, float)
    atras = atras / np.linalg.norm(atras)
    derecha = np.cross((0.0, 0.0, 1.0), atras)
    if np.linalg.norm(derecha) < 1e-9:           # vista cenital o nadir: el «arriba» de la imagen es +Y
        derecha = np.array([1.0, 0.0, 0.0])
    derecha = derecha / np.linalg.norm(derecha)
    R = np.array([derecha, np.cross(atras, derecha), atras])
    centro = (puntos.min(0) + puntos.max(0)) / 2
    p = (puntos - centro) @ R.T                     # x: derecha, y: arriba, z: hacia el ojo
    tan_v = math.tan(math.radians(fov) / 2)
    tan_h = tan_v * aspecto
    distancia = float(np.max(p[:, 2] + np.maximum(np.abs(p[:, 0]) / tan_h, np.abs(p[:, 1]) / tan_v)))
    return rc.camara(R, centro, max(distancia, 1.0) * 1.06, fov), centro


@herramienta("get_viewport_image", "inspeccion", "Renderiza el modelo y devuelve una imagen PNG (sombreado, sombras y "
             "suelo) desde una vista estándar o una dirección propia. Usa Rust si está disponible, con respaldo "
             "Python (OMNICAD_SIN_RUST=1 lo fuerza). Es la forma de VER el resultado.")
def get_viewport_image(sesion, view: str | None = None,
                       width: int = 640, height: int = 480, bodies: list[str] | None = None, fit: bool = True,
                       direction: list[float] | None = None,
                       lighting: Literal["three_point", "key_only"] = "three_point",
                       camera: Literal["perspective", "orthographic"] | None = None, component_colors: bool = False,
                       style: Literal["shaded", "shaded_hidden_edges", "shaded_visible_edges", "wireframe",
                                      "wireframe_hidden_edges", "wireframe_visible_edges"] | None = None,
                       analysis: list[str] | None = None):
    """
    view: vista estándar: las caras del ViewCube de Fusion con Z arriba, nombradas por los ejes del MUNDO (no por
        el frente de la pieza). "front": cámara en -Y, se ve la cara -Y con +X a la derecha; "back": cámara en +Y;
        "right": cámara en +X, se ve la cara +X con +Y a la derecha; "left": cámara en -X; "top": cámara en +Z,
        X a la derecha e Y hacia arriba; "bottom": cámara en -Z; "iso": esquina frente-derecha-arriba. Si la
        pieza mira hacia otro eje, usá direction. También acepta nombres de vistas guardadas; omitida usa set_view o iso.
    width: ancho de la imagen en píxeles (16 a 2048).
    height: alto de la imagen en píxeles (16 a 2048).
    bodies: ids o nombres de los cuerpos a dibujar (también los ocultos); vacío = todos los visibles.
    fit: true encuadra los cuerpos dibujados; false encuadra TODA la escena aunque se dibuje solo una parte
        (sirve para comparar imágenes con el mismo encuadre).
    direction: [x, y, z] vector desde el modelo HACIA la cámara (Z es arriba); si se pasa, reemplaza a view.
    lighting: "three_point" (por defecto) = iluminación de tres puntos (luz principal, relleno y contorno);
        "key_only" = solo la luz principal. No depende de Preferencias › Gráficos › «Iluminación de la vista»
        (esa opción es la del visor de la ventana).
    camera: perspective u orthographic; omitida conserva la cámara guardada o usa perspectiva.
    component_colors: pinta cada componente con un color de la paleta del visor; las piezas sueltas conservan su aspecto.
    style: estilo visual (los seis de Fusion: shaded, shaded_hidden_edges, shaded_visible_edges, wireframe, wireframe_hidden_edges, wireframe_visible_edges); omitido usa el de set_visual_style (shaded de fábrica). Las aristas son las exactas de los cuerpos: una malla no las tiene.
    analysis: nombres de los análisis a dibujar (manage_analysis los lista); [] ninguno; omitido dibuja los visibles del documento, como la ventana.
    """
    for nombre, valor in (("width", width), ("height", height)):
        if not _LADO_MINIMO <= valor <= _LADO_MAXIMO:
            raise error("INVALID_ARGUMENTS", f"{nombre} tiene que estar entre {_LADO_MINIMO} y {_LADO_MAXIMO} píxeles.")
    from .herramientas_visor import _vista_guardada
    datos = sesion.doc.espacios.get("visor") or {}
    cam_guardada = datos.get("camara")
    atras, vista = _VISTAS.get(view or "iso", _VISTAS["iso"]), view or ("custom" if cam_guardada else "iso")
    if view is not None and view not in _VISTAS and direction is None:
        cam_guardada = _vista_guardada(sesion, view)
    elif view is not None or direction is not None:
        cam_guardada = None
    if direction is not None:
        if len(direction) != 3 or not all(math.isfinite(x) for x in direction) or not any(direction):
            raise error("INVALID_ARGUMENTS", "direction tiene que ser [x, y, z] con números y no todos cero.")
        atras, vista = np.asarray(direction) / max(abs(x) for x in direction), "custom"
    cuerpos = _cuerpos(sesion, bodies)
    if datos.get("patron_activo") in sesion.doc.estado_final.cuerpos:
        cuerpos = [sesion.doc.estado_final.cuerpos[datos["patron_activo"]]]
    elif not bodies:                                # los cuerpos pedidos por nombre se dibujan aunque estén ocultos
        ocultos = set(sesion.doc.propiedad("__navegador__", "ocultos", []))
        cuerpos = [c for c in cuerpos if c.id not in ocultos and c.componente not in ocultos]
    todos = list(sesion.doc.estado_final.cuerpos.values())
    cajas = {c.id: geo.caja_envolvente(c.forma) if not _es_malla(c) else c.forma.caja()
             for c in (cuerpos if fit else todos)}
    if not cuerpos or not any(cajas.values()):
        raise error("NOTHING_TO_RENDER", "No hay cuerpos para dibujar.")
    pts = _esquinas([b for b in cajas.values() if b])
    t0 = time.perf_counter()
    from .herramientas_analisis import estilo_guardado
    guardado = estilo_guardado(sesion)
    escena = rc.escena_normalizada(({"entorno": guardado["entorno"]} if guardado["entorno"] else {}) | guardado["efectos"])
    cielo = rc.cielo_de(escena["entorno"]) if guardado["entorno"] else None
    estilo = style or guardado["estilo"]
    cam = dict(cam_guardada) if cam_guardada else _camara(atras, pts, width / height, rc.focal_a_fov(escena["focal"]))[0]
    if camera is not None:
        cam["ortografica"] = camera == "orthographic"
    objetos = _objetos_render(sesion, cuerpos, cam, height, cajas, component_colors)
    if not objetos:
        raise error("NOTHING_TO_RENDER", "Los cuerpos elegidos no tienen caras para dibujar.")
    objetos, cortes, aplicados = _con_analisis(sesion, objetos, cam, height, analysis)
    if not objetos:
        raise error("NOTHING_TO_RENDER", "Los cortes de los análisis dejaron la escena vacía.")
    z_suelo = min(float(o["v"][:, 2].min()) for o in objetos)
    if datos.get("rejilla", {}).get("mostrar"):
        objetos.append(_rejilla(cam, z_suelo, height))
    k = min(2.0, max(1.0, math.sqrt(_PIXELES_RENDER / (width * height))))
    w, h = round(width * k), round(height * k)
    res = int(min(2048, max(512, 2 ** math.ceil(math.log2(max(w, h) * 1.5)))))
    from ..timeline.ops_insertar import calcomanias_vigentes
    ids = {c.id for c in cuerpos}
    calcomanias = [d for _i, d in calcomanias_vigentes(sesion.doc, sesion.doc.estado_final)
                  if d.get("calcomania") and d.get("cuerpo") in ids]
    opciones = dict(z_suelo=z_suelo, res_sombras=res, mosaico=2048, n_luces=1 if lighting == "key_only" else 3,
                    calcomanias=calcomanias)
    if estilo == "shaded":
        rgba = rc.renderizar(objetos, cam, escena, w, h, supermuestreo=1, cielo=cielo, **opciones)
    else:
        aristas = rs.segmentos_de_polilineas([p for c in cuerpos if not _es_malla(c)
                                              for p in geo.polilineas_aristas(c.forma)])
        rgba = rs.aplicar_estilo(estilo, objetos, rs.recortar_segmentos(aristas, cortes) if cortes else aristas, cam,
                                 escena, w, h, cielo=cielo, **opciones)
    from PIL import Image                            # Pillow: ya lo usa render_cpu.guardar_png
    imagen = Image.fromarray(np.ascontiguousarray(rgba[..., :3]), "RGB")
    if (w, h) != (width, height):
        imagen = imagen.resize((width, height), Image.LANCZOS)
    buf = io.BytesIO()
    imagen.save(buf, "PNG", compress_level=3)
    return {"image": Imagen(buf.getvalue(), width, height), "view": vista, "bodies": [c.id for c in cuerpos],
            "style": estilo, "analyses": aplicados, "seconds": round(time.perf_counter() - t0, 2)}


def _rejilla(cam, suelo, alto):
    """Franjas finas sobre el suelo: el rasterizador resuelve su oclusión por las piezas."""
    paso = 10 ** math.floor(math.log10(cam["distancia"] / 5))
    centro = np.round(np.asarray(cam["objetivo"][:2]) / paso) * paso
    radio = 20 * paso
    fino = cam["distancia"] * math.tan(math.radians(cam["fov"]) / 2) / alto * 0.4
    z = suelo + paso * 1e-5
    vertices = []
    for eje in (0, 1):
        for i in range(-20, 21):
            a, b = centro.copy(), centro.copy()
            a[eje] += i * paso
            b[eje] += i * paso
            a[1 - eje] -= radio
            b[1 - eje] += radio
            d = np.zeros(2)
            d[eje] = fino
            p = [(float(x), float(y), z) for x, y in (a - d, b - d, b + d, a + d)]
            vertices.extend([p[0], p[1], p[2], p[0], p[2], p[3]])
    v = np.asarray(vertices)
    return {"v": v, "n": np.tile([0., 0., 1.], (len(v), 1)), "color": (0.45, 0.48, 0.52), "acabado": {}}


# ---------------------------------------------------------------- propiedades físicas
def _centro_malla(malla):
    """Centro de masa (volumétrico) de una malla cerrada; si no tiene volumen, el centro de sus vértices."""
    t = malla.vertices[malla.caras]
    vol = np.einsum("ij,ij->i", t[:, 0], np.cross(t[:, 1], t[:, 2])) / 6.0
    if abs(vol.sum()) < 1e-12:
        return malla.vertices.mean(0)
    return ((t.sum(1) / 4.0) * vol[:, None]).sum(0) / vol.sum()


def _centro(c):
    if _es_malla(c):
        return np.asarray(_centro_malla(c.forma), float)
    return np.asarray(geo.centro_masa(c.forma, superficie=not _es_solido(c)), float)


def _densidad(sesion, c, densidad):
    """(material, densidad g/cm³ o None) de un cuerpo con volumen."""
    material = sesion.doc.propiedad(c.id, "material") or getattr(c, "material", None)
    if densidad is not None:
        return material, float(densidad)
    if material in an.TABLA_MATERIALES:
        return material, an.TABLA_MATERIALES[material]["densidad"]
    return material, None


@herramienta("get_physical_properties", "inspeccion", "Volumen (mm³), área (mm²), masa (g), centro de masa y caja "
             "envolvente de cada cuerpo y del total. La masa necesita una densidad: la que se pasa, o la del material "
             "físico asignado al cuerpo.")
def get_physical_properties(sesion, bodies: list[str] | None = None, density: float | None = None):
    """
    bodies: ids o nombres de los cuerpos; vacío = todos.
    density: densidad en g/cm³ para todos los cuerpos con volumen; vacío = la de su material físico.
    """
    if density is not None and not density > 0:
        raise error("INVALID_ARGUMENTS", "density tiene que ser un número mayor que cero (g/cm³).")
    cuerpos = _cuerpos(sesion, bodies)
    if not cuerpos:
        raise error("NOTHING_TO_MEASURE", "No hay cuerpos para medir.")
    por_cuerpo, sin_masa = [], []
    for c in cuerpos:
        info = _info_cuerpo(sesion, c)
        material, rho = _densidad(sesion, c, density)
        info.update(material=material, density_g_cm3=rho, mass_g=None,
                    center_of_mass=[_r(x) for x in _centro(c)])
        if info["volume"] is not None and rho is not None:
            info["mass_g"] = _r(info["volume"] * rho * 1e-3)
        elif info["volume"] is not None:
            sin_masa.append(info["name"])
        por_cuerpo.append(info)
    if sin_masa:
        sesion.avisar(f"Sin densidad (pasá density o asignale un material): {', '.join(sin_masa)}.")
    conmasa = [i for i in por_cuerpo if i["mass_g"] is not None]
    volumenes = [i for i in por_cuerpo if i["volume"]]
    todo_con_masa = len(conmasa) == len(volumenes) and bool(conmasa)
    # Centro total: ponderado por masa si todos los cuerpos con volumen tienen densidad; si no, por volumen.
    pesos = [(i["mass_g"] if todo_con_masa else i["volume"], i) for i in volumenes]
    total_peso = sum(p for p, _ in pesos)
    centro = (np.sum([np.array(i["center_of_mass"]) * p for p, i in pesos], axis=0) / total_peso
              if total_peso > 0 else None)
    cajas = [i["bounding_box"] for i in por_cuerpo if i["bounding_box"]]
    caja = None
    if cajas:
        mn, mx = np.min([b["min"] for b in cajas], axis=0), np.max([b["max"] for b in cajas], axis=0)
        caja = {"min": [_r(x) for x in mn], "max": [_r(x) for x in mx], "size": [_r(x) for x in mx - mn]}
    return {"bodies": por_cuerpo,
            "total": {"volume": _r(sum(i["volume"] or 0.0 for i in por_cuerpo)),
                      "area": _r(sum(i["area"] or 0.0 for i in por_cuerpo)),
                      "mass_g": _r(sum(i["mass_g"] for i in conmasa)) if todo_con_masa else None,
                      "center_of_mass": None if centro is None else [_r(x) for x in centro],
                      "center_of_mass_basis": "mass" if todo_con_masa else "volume", "bounding_box": caja},
            "units": {"volume": "mm3", "area": "mm2", "mass": "g", "density": "g/cm3", "length": "mm"}}


# ---------------------------------------------------------------- medir
def _resolver_ref(sesion, ref, body=None):
    """(entidad para `analisis.medir`, descripción) de una referencia: cara o arista (id de find_faces / find_edges
    o selector, que se evalúa sobre `body` o el único cuerpo), cuerpo (id o nombre) o punto [x, y, z]. Un selector
    suelto se evalúa sobre las caras; para aristas, `edges:<selector>` o un id."""
    if isinstance(ref, str):
        if sl.es_id(ref) or sl._PREFIJO.match(ref):
            return _elemento(sesion, ref, body)
        try:
            c = sesion.cuerpo(ref)
        except ErrorAPI as e:
            if e.error_kind == "BODY_NOT_FOUND" and sl.parece_selector(ref):
                return _elemento(sesion, ref, body)
            raise
        if _es_malla(c):
            raise error("UNSUPPORTED_BODY_TYPE", f"«{sesion.nombre_cuerpo(c)}» es una malla: todavía no se puede medir "
                        "contra mallas.", "Convertí la malla a sólido o medí contra puntos [x, y, z].")
        return c.forma, dict(_nombre_y_id(sesion, c), kind="body")
    if len(ref) != 3 or not all(isinstance(x, (int, float)) and math.isfinite(x) for x in ref):
        raise error("INVALID_ARGUMENTS", f"Un punto tiene que ser [x, y, z] con 3 números (mm): {ref!r}.",
                    "Un cuerpo se indica por su id o nombre (get_scene_info los lista); una cara o arista por su id "
                    "(find_faces / find_edges) o un selector.")
    return np.array(ref, float), {"kind": "point", "position": [_r(x) for x in ref]}


def _elemento(sesion, ref, body=None):
    cuerpo, e = sl.elegir_uno(sesion, ref, body=body)
    return e.sub, {"kind": "face" if e.tipo == "cara" else "edge", "id": sl.emitir_id(sesion, cuerpo, e),
                   "body": _nombre_y_id(sesion, cuerpo)}


@herramienta("measure_distance", "inspeccion", "Distancia mínima entre dos cosas, cada una un cuerpo, una cara, una arista "
             "o un punto. Caras y aristas se dan por id (find_faces / find_edges) o por selector (>Z elige sobre las caras; "
             "edges:|Z sobre las aristas; con varios cuerpos, body dice en cuál se evalúan los selectores). Devuelve la "
             "distancia (mm), los dos puntos más cercanos y el desfase XYZ de a hacia b; con center_to_center, la de centro a centro.")
def measure_distance(sesion, a: str | list[float], b: str | list[float], body: str | None = None,
                     center_to_center: bool = False):
    """
    a: cuerpo (id o nombre), cara o arista (id "Cuerpo1/F3" o selector ">Z", "edges:|Z") o punto [x, y, z] en mm.
    b: cuerpo (id o nombre), cara o arista (id "Cuerpo1/F3" o selector ">Z", "edges:|Z") o punto [x, y, z] en mm.
    body: id o nombre del cuerpo donde se evalúan los selectores de a y b; vacío = el único cuerpo. Los ids y los nombres de cuerpo no lo necesitan.
    center_to_center: true mide de centro a centro (opción «Centro a centro» de Fusion): a y b tienen que ser círculos, arcos o cilindros; distance y los puntos son entonces los de los centros, y se agrega center_to_center con las distancias mínima y máxima según los diámetros.
    """
    ea, da = _resolver_ref(sesion, a, body)
    eb, db = _resolver_ref(sesion, b, body)
    try:
        m = an.medir(ea, eb, centro_a_centro=center_to_center)
    except geo.ErrorGeometria as e:
        raise error("INVALID_ARGUMENTS", str(e)) from None
    centros = {"center_to_center": {k: ([_r(x) for x in v] if isinstance(v, (list, tuple)) else _r(v))
                                    for k, v in m["centro_a_centro"].items()}} if "centro_a_centro" in m else {}
    return {**centros, "distance": _r(m["distancia"]), "point_a": [_r(x) for x in m["punto_a"]],
            "point_b": [_r(x) for x in m["punto_b"]], "delta": [_r(x) for x in m["delta"]],
            "intersecting": m["distancia"] < 1e-6, "a": da, "b": db}


# ---------------------------------------------------------------- interferencias
@herramienta("check_interference", "inspeccion", "Busca pares de cuerpos sólidos que se superponen y devuelve cada par "
             "con el volumen común (mm³) y su caja envolvente. Los que solo se tocan por una cara no cuentan, salvo con coincident_faces.")
def check_interference(sesion, bodies: list[str] | None = None, coincident_faces: bool = False):
    """
    bodies: ids o nombres de los cuerpos a comparar entre sí; vacío = todos los sólidos.
    coincident_faces: true también informa los pares que solo se tocan por caras coincidentes (opción «Incluir caras coincidentes»): volume 0, area de contacto y coincident=true.
    """
    cuerpos = _cuerpos(sesion, bodies)
    solidos = [c for c in cuerpos if _es_solido(c)]
    omitidos = [sesion.nombre_cuerpo(c) for c in cuerpos if not _es_solido(c)]
    if omitidos:
        sesion.avisar(f"Se omitieron los cuerpos que no son sólidos: {', '.join(omitidos)}.")
    if len(solidos) < 2:
        sesion.avisar("Hacen falta al menos 2 cuerpos sólidos para buscar interferencias.")
    por_id = {c.id: c for c in solidos}
    pares = []
    for i in an.interferencias({c.id: c.forma for c in solidos}, caras_coincidentes=coincident_faces):
        caja = geo.caja_envolvente(i["forma"])
        pares.append({"a": _nombre_y_id(sesion, por_id[i["a"]]), "b": _nombre_y_id(sesion, por_id[i["b"]]),
                      "volume": _r(i["volumen"]), "coincident": i["coincidente"],
                      **({"area": _r(i["area"])} if i["coincidente"] else {}),
                      "bounding_box": None if not caja else {"min": [_r(x) for x in caja[0]],
                                                              "max": [_r(x) for x in caja[1]]}})
    return {"checked": len(solidos), "count": len(pares), "pairs": pares, "interference": bool(pares)}


# ---------------------------------------------------------------- caras y aristas (selectores)
def _buscar(sesion, tipo, body, selector):
    cuerpos = [sl.cuerpo_objetivo(sesion, body)] if body else [c for c in sesion.doc.estado_final.cuerpos.values()
                                                               if not _es_malla(c)]
    if not cuerpos:
        raise error("BODY_NOT_FOUND", "El documento no tiene cuerpos con caras o aristas.",
                    "Creá un cuerpo antes (create_box, extrude…).")
    total, elementos, fallo = 0, [], None
    for c in cuerpos:
        todos = sl.listar(c.forma, tipo)
        total += len(todos)
        try:
            elegidos = todos if selector is None else sl.evaluar(selector, todos, tipo, sesion.nombre_cuerpo(c))
        except ErrorAPI as e:
            if e.error_kind != "NO_MATCH" or len(cuerpos) == 1:
                raise
            fallo = fallo or e
            continue
        elementos += [(c, e) for e in elegidos]
    if not elementos:
        raise fallo or error("NO_MATCH", "No hay elementos.")
    lista = [sl.info_elemento(sesion, c, e) for c, e in elementos[:sl.MAX_ELEMENTOS]]
    if len(elementos) > sl.MAX_ELEMENTOS:
        sesion.avisar(f"Hay {len(elementos)} elementos: se devuelven los primeros {sl.MAX_ELEMENTOS}. Afiná el selector.")
    return {"selector": selector, "count": len(elementos), "total": total,
            "faces" if tipo == "cara" else "edges": lista, "truncated": len(elementos) > sl.MAX_ELEMENTOS}


_SELECTOR = ("Selector estilo CadQuery: >Z <Z (centro más alto/bajo), |Z (aristas paralelas al eje; caras con la "
             "normal paralela), #Z (perpendicular), +Z -Z (normal de caras planas), |Z~3 #Z~3 (lo mismo con 3° de "
             "tolerancia, para lo apenas inclinado, p. ej. tras un desmoldeo), %PLANE %CYLINDER %CIRCLE %LINE "
             "(tipo), nearest:[x,y,z], combinables con and, or, not y paréntesis (get_guide topic=selectores). ")
_EFIMERO = ("Cada elemento trae un id corto (p. ej. 'Cuerpo1/F3') VÁLIDO HASTA EL PRÓXIMO CAMBIO DEL DOCUMENTO "
            "(un id viejo da STALE_ID); fillet, chamfer, shell, create_hole y create_sketch lo aceptan, o aceptan el "
            "selector directamente. Sin coincidencias da NO_MATCH. ")


@herramienta("find_faces", "inspeccion", "Lista las caras de un cuerpo (o de todos), opcionalmente filtradas por un "
             "selector. " + _SELECTOR + _EFIMERO + "Cada cara trae tipo (plane, cylinder, cone, sphere, torus, "
             "bspline), área (mm²), centro, normal (planas) o eje (cilindros y conos), radio y, en las planas, "
             "center_uv: el centro en los ejes x,y de un boceto sobre esa cara.")
def find_faces(sesion, body: str | None = None, selector: str | None = None):
    """
    body: id o nombre del cuerpo; vacío = todos los cuerpos.
    selector: filtro estilo CadQuery, p. ej. ">Z" (la tapa), "#Z" (las laterales), "%CYLINDER"; vacío = todas.
    """
    return _buscar(sesion, "cara", body, selector)


@herramienta("find_edges", "inspeccion", "Lista las aristas de un cuerpo (o de todos), opcionalmente filtradas por "
             "un selector. " + _SELECTOR + _EFIMERO + "Cada arista trae tipo (line, circle, ellipse, bspline), largo "
             "(mm), centro, dirección (rectas) y radio (círculos).")
def find_edges(sesion, body: str | None = None, selector: str | None = None):
    """
    body: id o nombre del cuerpo; vacío = todos los cuerpos.
    selector: filtro estilo CadQuery, p. ej. "|Z" (las verticales), ">Z" (las de arriba), "%CIRCLE"; vacío = todas.
    """
    return _buscar(sesion, "arista", body, selector)


@herramienta("measure_angle", "inspeccion", "Ángulo (grados) entre dos caras planas, dos aristas rectas, o una cara y una "
             "arista. Cara-cara: ángulo entre las normales exteriores (0 a 180; dos caras de una caja que se tocan en "
             "una arista dan 90), más acute_angle (0 a 90). Arista-arista y cara-arista: ángulo agudo (0 a 90), porque "
             "una arista no tiene sentido. Cada lado es un id de find_faces / find_edges o un selector (sobre caras; "
             "edges:|Z para aristas) que elija UNA sola; con varios cuerpos, body dice en cuál se evalúan los selectores.")
def measure_angle(sesion, a: str, b: str, body: str | None = None):
    """
    a: cara o arista: id ("Cuerpo1/F3") o selector (">Z", "edges:|Z").
    b: cara o arista: id ("Cuerpo1/F3") o selector (">X", "edges:|X").
    body: id o nombre del cuerpo donde se evalúan los selectores de a y b; vacío = el único cuerpo. Los ids no lo necesitan.
    """
    (ca, ea), (cb, eb) = sl.elegir_uno(sesion, a, body=body), sl.elegir_uno(sesion, b, body=body)
    for e in (ea, eb):
        if e.vector is None:
            raise error("UNSUPPORTED_ELEMENT", f"No se puede medir el ángulo de {'una cara' if e.tipo == 'cara' else 'una arista'} "
                        f"de tipo {e.geom}: hace falta una cara plana o una arista recta.",
                        "find_faces(selector='%PLANE') y find_edges(selector='%LINE') las listan.")
    c = float(np.clip(ea.vector @ eb.vector, -1.0, 1.0))
    entre_vectores = math.degrees(math.acos(c))
    agudo = min(entre_vectores, 180.0 - entre_vectores)
    if ea.tipo == "cara" and eb.tipo == "cara":
        kind, angulo = "face-face", entre_vectores
    elif ea.tipo == "arista" and eb.tipo == "arista":
        kind, angulo = "edge-edge", agudo
    else:                                              # recta con plano: complemento del ángulo con la normal
        kind, angulo = "face-edge", 90.0 - agudo

    def desc(cuerpo, e):
        return {"id": sl.emitir_id(sesion, cuerpo, e), "type": e.geom.lower(), "vector": [_r(x) + 0.0 for x in e.vector]}
    return {"angle": _r(angulo), "acute_angle": _r(min(angulo, 180.0 - angulo)), "kind": kind,
            "a": desc(ca, ea), "b": desc(cb, eb)}


# ---------------------------------------------------------------- de dónde viene una cara o arista
@herramienta("get_entity_origin", "inspeccion", "De dónde viene una cara o arista: qué paso del timeline la creó "
             "(created_by) y cuáles la modificaron (modified_by, en orden). Es la misma respuesta que la app da al "
             "elegir algo en la vista (el paso se resalta en amarillo) y sirve para saber qué paso editar si algo "
             "no salió como se esperaba. Se calcula comparando el modelo antes y después de cada paso, así que una "
             "cara que un paso deja idéntica a otra no se distingue; known=false si no se puede saber. Una cara que "
             "entra de otro cuerpo (la herramienta de un Combinar) se atribuye al paso que la trajo.")
def get_entity_origin(sesion, entity: str, body: str | None = None):
    """
    entity: UNA cara o arista: id de find_faces / find_edges ("Cuerpo1/F3", "Cuerpo1/E7"), o un selector que elija una sola ('>Z', 'edges:|X and >Y', 'nearest:[x,y,z]').
    body: id o nombre del cuerpo donde se evalúa un selector; vacío = el único cuerpo.
    """
    from ..timeline.origen import origen_de
    cuerpo, elem = sl.elegir_uno(sesion, entity, body=body)
    ref = sl.referencia(cuerpo, elem)
    o = origen_de(sesion.doc, ref)

    def paso(op_id):
        op = sesion.doc.operacion(op_id)
        return {"id": op.id, "name": op.nombre, "type": op.TIPO}
    base = {"entity": sl.emitir_id(sesion, cuerpo, elem), "type": "face" if elem.tipo == "cara" else "edge",
            "body": {"id": cuerpo.id, "name": sesion.nombre_cuerpo(cuerpo)}}
    if o is None:
        sesion.avisar("No se pudo rastrear de dónde viene: no se encuentra en los pasos anteriores del timeline.")
        return {**base, "known": False, "created_by": None, "modified_by": []}
    return {**base, "known": True, "created_by": paso(o["creo"]), "modified_by": [paso(i) for i in o["modificaron"]]}
