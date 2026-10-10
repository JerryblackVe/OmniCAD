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
    todos = list(sesion.doc.estado_final.cuerpos.values())
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
def _objetos_render(sesion, cuerpos, deflexion):
    """Los mismos objetos que arma el render de la app (`render_cpu.malla_suave` y `color_y_acabado`)."""
    objetos = []
    for c in cuerpos:
        v, n = rc.malla_suave(c.forma, deflexion)
        if not len(v):
            continue
        color, acabado = rc.color_y_acabado(c, propiedades_cuerpo(sesion.doc.propiedades, c))
        objetos.append({"v": v, "n": n, "color": color, "acabado": acabado,
                        "opacidad": float(sesion.doc.propiedad(c.id, "opacidad", 1.0))})
    return objetos


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
             "suelo) desde una vista estándar o una dirección propia. Es la forma de VER el resultado.")
def get_viewport_image(sesion, view: Literal["iso", "front", "back", "top", "bottom", "left", "right"] = "iso",
                       width: int = 640, height: int = 480, bodies: list[str] | None = None, fit: bool = True,
                       direction: list[float] | None = None):
    """
    view: vista estándar: las caras del ViewCube de Fusion con Z arriba, nombradas por los ejes del MUNDO (no por
        el frente de la pieza). "front": cámara en -Y, se ve la cara -Y con +X a la derecha; "back": cámara en +Y;
        "right": cámara en +X, se ve la cara +X con +Y a la derecha; "left": cámara en -X; "top": cámara en +Z,
        X a la derecha e Y hacia arriba; "bottom": cámara en -Z; "iso": esquina frente-derecha-arriba. Si la
        pieza mira hacia otro eje, usá direction.
    width: ancho de la imagen en píxeles (16 a 2048).
    height: alto de la imagen en píxeles (16 a 2048).
    bodies: ids o nombres de los cuerpos a dibujar; vacío = todos.
    fit: true encuadra los cuerpos dibujados; false encuadra TODA la escena aunque se dibuje solo una parte
        (sirve para comparar imágenes con el mismo encuadre).
    direction: [x, y, z] vector desde el modelo HACIA la cámara (Z es arriba); si se pasa, reemplaza a view.
    """
    for nombre, valor in (("width", width), ("height", height)):
        if not _LADO_MINIMO <= valor <= _LADO_MAXIMO:
            raise error("INVALID_ARGUMENTS", f"{nombre} tiene que estar entre {_LADO_MINIMO} y {_LADO_MAXIMO} píxeles.")
    atras, vista = _VISTAS[view], view
    if direction is not None:
        if len(direction) != 3 or not all(math.isfinite(x) for x in direction) or not any(direction):
            raise error("INVALID_ARGUMENTS", "direction tiene que ser [x, y, z] con números y no todos cero.")
        atras, vista = direction, "custom"
    cuerpos = _cuerpos(sesion, bodies)
    todos = list(sesion.doc.estado_final.cuerpos.values())
    caja = [geo.caja_envolvente(c.forma) if not _es_malla(c) else c.forma.caja() for c in (cuerpos if fit else todos)]
    caja = [b for b in caja if b]
    if not cuerpos or not caja:
        raise error("NOTHING_TO_RENDER", "No hay cuerpos para dibujar.")
    pts = _esquinas(caja)
    t0 = time.perf_counter()
    diagonal = float(np.linalg.norm(pts.max(0) - pts.min(0)))
    objetos = _objetos_render(sesion, cuerpos, max(0.05, diagonal / 2000))
    if not objetos:
        raise error("NOTHING_TO_RENDER", "Los cuerpos elegidos no tienen caras para dibujar.")
    escena = rc.escena_normalizada(None)
    cam, _ = _camara(atras, pts, width / height, rc.focal_a_fov(escena["focal"]))
    z_suelo = min(float(o["v"][:, 2].min()) for o in objetos)
    k = min(2.0, max(1.0, math.sqrt(_PIXELES_RENDER / (width * height))))
    w, h = round(width * k), round(height * k)
    res = int(min(2048, max(512, 2 ** math.ceil(math.log2(max(w, h) * 1.5)))))
    rgba = rc.renderizar(objetos, cam, escena, w, h, supermuestreo=1, z_suelo=z_suelo, res_sombras=res, mosaico=2048)
    from PIL import Image                            # Pillow: ya lo usa render_cpu.guardar_png
    imagen = Image.fromarray(np.ascontiguousarray(rgba[..., :3]), "RGB")
    if (w, h) != (width, height):
        imagen = imagen.resize((width, height), Image.LANCZOS)
    buf = io.BytesIO()
    imagen.save(buf, "PNG", compress_level=3)
    return {"image": Imagen(buf.getvalue(), width, height), "view": vista, "bodies": [c.id for c in cuerpos],
            "seconds": round(time.perf_counter() - t0, 2)}


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
             "distancia (mm), los dos puntos más cercanos y el desfase XYZ de a hacia b.")
def measure_distance(sesion, a: str | list[float], b: str | list[float], body: str | None = None):
    """
    a: cuerpo (id o nombre), cara o arista (id "Cuerpo1/F3" o selector ">Z", "edges:|Z") o punto [x, y, z] en mm.
    b: cuerpo (id o nombre), cara o arista (id "Cuerpo1/F3" o selector ">Z", "edges:|Z") o punto [x, y, z] en mm.
    body: id o nombre del cuerpo donde se evalúan los selectores de a y b; vacío = el único cuerpo. Los ids y los nombres de cuerpo no lo necesitan.
    """
    ea, da = _resolver_ref(sesion, a, body)
    eb, db = _resolver_ref(sesion, b, body)
    m = an.medir(ea, eb)
    return {"distance": _r(m["distancia"]), "point_a": [_r(x) for x in m["punto_a"]],
            "point_b": [_r(x) for x in m["punto_b"]], "delta": [_r(x) for x in m["delta"]],
            "intersecting": m["distancia"] < 1e-6, "a": da, "b": db}


# ---------------------------------------------------------------- interferencias
@herramienta("check_interference", "inspeccion", "Busca pares de cuerpos sólidos que se superponen y devuelve cada par "
             "con el volumen común (mm³) y su caja envolvente. Los que solo se tocan por una cara no cuentan.")
def check_interference(sesion, bodies: list[str] | None = None):
    """
    bodies: ids o nombres de los cuerpos a comparar entre sí; vacío = todos los sólidos.
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
    for i in an.interferencias({c.id: c.forma for c in solidos}):
        caja = geo.caja_envolvente(i["forma"])
        pares.append({"a": _nombre_y_id(sesion, por_id[i["a"]]), "b": _nombre_y_id(sesion, por_id[i["b"]]),
                      "volume": _r(i["volumen"]),
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
