# -*- coding: utf-8 -*-
"""Generador de la caza: piezas semilla, medidas relativas a la pieza y argumentos armados desde el esquema del catálogo.

Lo que no está en EXCLUIDAS entra solo: `llenar` lee el esquema de `api.catalogo()`, así una herramienta nueva se prueba
sin tocar este archivo. Corre dentro del trabajador."""
import re

# Herramientas que no se corren nunca, con su razón (red, gasto, procesos o datos fuera de la carpeta temporal).
EXCLUIDAS = {
    "assistant_ask": "abre red y gasta la API paga del proveedor configurado",
    "list_assistant_models": "consulta por red a los proveedores del Asistente",
    "set_assistant_config": "cambia el proveedor y las claves del Asistente del usuario",
    "run_checks": "lanza ruff y pytest: no se corre una suite desde un caso",
    "run_bench": "lanza mediciones pesadas en procesos aparte",
    "app_screenshot": "captura la pantalla del usuario",
    "set_geometry_engine": "cambia el motor de todo el proceso y contamina los casos siguientes",
    "execute_code": "corre Python arbitrario: el generador no arma código, y su caja tiene pruebas propias",
    "export_animation_video": "lanza ffmpeg y tarda minutos por caso",
}
# Reemplazan el documento o manejan el historial: en una cadena romperían la historia. Se prueban en la capa A.
FUERA_DE_CADENA = {"new_document", "open_document", "recover_document", "apply_recipe", "undo", "redo"}
# Valores fijos porque el otro camino sale de la carpeta temporal (abre la utilidad de impresión del usuario).
FIJOS = {"export_mesh": {"purpose": "export"}}

EPS = 1e-3
FACTORES = {"0.5m": 0.5, "m-e": 1 - EPS, "m": 1.0, "m+e": 1 + EPS, "1.1m": 1.1, "2m": 2.0, "10m": 10.0}
FALTA = object()          # no hay nada en el documento para ese parámetro

MEDIDAS = {"radius", "distance", "thickness", "depth", "diameter"}
RUTA = re.compile(r"\bruta\b|\barchivo\b|\bcarpeta\b", re.I)
ENTRECOMILLADO = re.compile(r'"([a-z][a-z_0-9]*)"')
SALIDAS = (".step", ".stl", ".dxf", ".svg", ".3mf", ".omnicad", ".obj")
CUERPO = {"body", "target", "surface", "reference", "ref_body", "body1", "body2", "axis_body"}
CUERPOS = {"bodies", "tools"}
CURVAS = {"entity", "curve", "entity1", "entity2", "line1", "line2", "axis"}
PRINCIPALES = CUERPO | CUERPOS | {"sketch", "edges", "faces", "face", "feature", "radius", "distance", "thickness", "angle",
                                   "height", "length", "width", "depth", "diameter", "scale", "profile"}


def es_nucleo(h):
    """Operaciones sobre la pieza con una medida que depende de ella: donde más rinden las medidas relativas."""
    props = h["esquema"]["properties"]
    return h["modifica"] and h["grupo"] == "solido" and bool(MEDIDAS & set(props)) and bool({"edges", "faces"} & set(props))


def tipos(prop):
    """Tipos JSON que acepta un parámetro del esquema."""
    t = prop.get("type")
    if t:
        return {t} if isinstance(t, str) else set(t)
    salida = set()
    for p in prop.get("anyOf", ()):
        salida |= tipos(p)
    return salida


class Contexto:
    """Lo que hay en el documento ahora: de acá salen las referencias y las medidas."""

    def __init__(self, sesion, llamar):
        self.sesion, self.llamar = sesion, llamar
        leer = lambda nombre, clave: (llamar(sesion, nombre, {}).get("result") or {}).get(clave) or []  # noqa: E731
        escena = llamar(sesion, "get_scene_info", {}).get("result") or {}
        self.cuerpos = escena.get("bodies") or []
        self.bocetos = escena.get("sketches") or []
        self.componentes = escena.get("components") or []
        self.aristas = leer("find_edges", "edges")
        self.caras = leer("find_faces", "faces")
        self.pasos = leer("get_timeline", "steps")
        self.medidas = medidas(self.cuerpos, self.aristas, self.caras)
        self.salidas = 0

    def curvas(self, boceto):
        r = self.llamar(self.sesion, "get_sketch", {"sketch": boceto}).get("result") or {}
        return [c["id"] for c in r.get("entities") or [] if c.get("type") != "point"]

    def punto(self, rng, n=3):
        cajas = [c["bounding_box"] for c in self.cuerpos if c.get("bounding_box")]
        if not cajas:
            return [round(rng.uniform(-20, 20), 3) for _ in range(n)]
        caja = rng.choice(cajas)
        return [round(rng.uniform(caja["min"][i], caja["max"][i]), 3) for i in range(n)]

    def ruta(self, rng):
        self.salidas += 1
        return f"{{TMP}}/salida_{self.salidas}{rng.choice(SALIDAS)}"


def medidas(cuerpos, aristas, caras):
    """Medidas propias de la pieza: pared (caras planas enfrentadas), arista, radio y caja."""
    pared, radios = set(), set()
    planas = [c for c in caras if c.get("normal") and c.get("type") == "plane"]
    for i, a in enumerate(planas):
        for b in planas[i + 1:]:
            if a["body"] == b["body"] and sum(x * y for x, y in zip(a["normal"], b["normal"], strict=True)) < -0.999:
                d = abs(sum((p - q) * n for p, q, n in zip(a["center"], b["center"], a["normal"], strict=True)))
                if d > 1e-6:
                    pared.add(round(d, 6))
    for c in (*aristas, *caras):
        if c.get("radius"):
            radios.add(round(c["radius"], 6))
    largos = sorted(a["length"] for a in aristas if a.get("length"))
    tamanos = sorted(t for c in cuerpos if c.get("bounding_box") for t in c["bounding_box"]["size"] if t > 0)
    grupos = {"pared": sorted(pared)[:3], "radio": sorted(radios)[:3],
              "arista": largos[:1] + largos[len(largos) // 2:len(largos) // 2 + 1], "caja": tamanos[:1]}
    return {k: v for k, v in grupos.items() if v} or {"caja": [10.0]}


def medida(ctx, rng, clase):
    """Valor de la clase pedida, relativo a una medida de la pieza («1.1m» = 1,1 veces esa medida)."""
    if clase in FACTORES:
        return round(rng.choice(ctx.medidas[rng.choice(sorted(ctx.medidas))]) * FACTORES[clase], 6)
    return {"0": 0.0, "1e-6": 1e-6, "1e6": 1e6}.get(clase, -round(rng.choice(ctx.medidas[min(ctx.medidas)]), 6))


def _exterior(x, cuerpos):
    """Arista o cara que toca la caja de su cuerpo: lo de afuera de la pieza, no lo de una cavidad."""
    caja = next((c.get("bounding_box") for c in cuerpos if c["id"] == x.get("body")), None)
    return bool(caja) and any(abs(x["center"][i] - caja[lado][i]) < 1e-6 for i in range(3) for lado in ("min", "max"))


def _ids(lista, rng, cuerpos, cuerpo=None):
    """De 1 a 3 ids de aristas o caras del mismo cuerpo, la mitad de las veces de su exterior."""
    if cuerpo:
        lista = [x for x in lista if x.get("body") == cuerpo] or lista
    if not lista:
        return FALTA
    if rng.random() < 0.5:
        lista = [x for x in lista if _exterior(x, cuerpos)] or lista
    return [x["id"] for x in rng.sample(lista, min(rng.choice((1, 1, 1, 2, 3)), len(lista)))]


def valor(nombre, prop, ctx, rng, clase, args):
    """Un valor plausible para el parámetro, o FALTA si el documento no tiene de dónde sacarlo."""
    tip = tipos(prop)
    desc = prop.get("description", "")
    cuerpo = args.get("body") if isinstance(args.get("body"), str) else None
    if "enum" in prop:
        return rng.choice(prop["enum"])
    if nombre in CUERPO and "string" in tip:
        return rng.choice([c["id"] for c in ctx.cuerpos]) if ctx.cuerpos else FALTA
    if nombre in CUERPOS:
        return [rng.choice(ctx.cuerpos)["id"]] if ctx.cuerpos else FALTA
    if nombre == "edges" or nombre in ("edge", "edge1", "edge2"):
        ids = _ids(ctx.aristas, rng, ctx.cuerpos, cuerpo)
        return ids if ids is FALTA or nombre == "edges" else ids[0]
    if nombre in ("faces", "face", "seed"):
        ids = _ids(ctx.caras, rng, ctx.cuerpos, cuerpo)
        return ids if ids is FALTA or nombre == "faces" else ids[0]
    if nombre in ("sketch", "source_sketch"):
        return rng.choice(ctx.bocetos)["id"] if ctx.bocetos else FALTA
    if nombre == "feature":
        return rng.choice(ctx.pasos)["id"] if ctx.pasos else FALTA
    if nombre == "component":
        return rng.choice(ctx.componentes)["id"] if ctx.componentes else FALTA
    if nombre in CURVAS and "integer" in tip and args.get("sketch"):
        curvas = ctx.curvas(args["sketch"])
        return rng.choice(curvas) if curvas else FALTA
    if "string" in tip and "number" not in tip and (nombre in ("path", "source_path", "export") or RUTA.search(desc)):
        return ctx.ruta(rng)
    if nombre == "plane":
        return rng.choice(("XY", "XZ", "YZ"))
    if nombre in ("axis", "direction") and "string" in tip:
        return rng.choice(("X", "Y", "Z"))
    if nombre in ("origin1", "origin2", "origin1b", "origin2b", "a", "b", "geometry"):
        return rng.choice(ctx.caras)["id"] if ctx.caras else FALTA
    if "number" in tip or "integer" in tip:
        if "integer" in tip and "number" not in tip or nombre in ("teeth", "teeth1", "teeth2", "sides"):
            return rng.choice((2, 3, 4, 6, 12, 24)) if nombre != "index" else 0
        if nombre == "module":
            return rng.choice((0.5, 1, 2))
        if "grados" in desc or "ángulo" in desc:
            return rng.choice((-30, 15, 30, 45, 90, 135, 180, 270, 360))
        if nombre in ("x", "y", "z", "start_x", "start_y", "end_x", "end_y"):
            return ctx.punto(rng, 1)[0]
        return medida(ctx, rng, clase)
    if "array" in tip:
        if "[x, y, z]" in desc or "[dx, dy, dz]" in desc:
            return ctx.punto(rng)
        if "[x, y]" in desc or "[dx, dy]" in desc:
            return ctx.punto(rng, 2)
        return FALTA
    if "boolean" in tip:
        return rng.random() < 0.5
    if "string" in tip:
        opciones = ENTRECOMILLADO.findall(desc)
        if opciones:
            return rng.choice(opciones)
        return "Caza"
    return FALTA


def llenar(herramienta, ctx, rng, clase):
    """Argumentos para una herramienta del catálogo; None si no se pueden armar en este documento."""
    esquema = herramienta["esquema"]
    args = dict(FIJOS.get(herramienta["nombre"], ()))
    requeridos = set(esquema["required"])
    # Primero el cuerpo y el boceto: las aristas y las curvas se eligen dentro de ellos.
    for nombre, prop in sorted(esquema["properties"].items(), key=lambda kv: kv[0] not in ("body", "sketch")):
        if nombre in args or nombre == "name":
            continue
        if nombre in requeridos or rng.random() < (0.95 if nombre in PRINCIPALES else 0.03):
            v = valor(nombre, prop, ctx, rng, clase, args)
            if v is not FALTA:
                args[nombre] = v
            elif nombre in requeridos:
                return None
    return args


# ---------------------------------------------------------------- piezas semilla
def _caja(r):
    return "create_box", {"length": r.choice((40, 60, 80)), "width": r.choice((30, 50, 60)), "height": r.choice((20, 40))}


def _solido(r):
    return [r.choice((_caja(r), ("create_cylinder", {"radius": r.choice((10, 25)), "height": r.choice((30, 60))}),
                      ("create_sphere", {"radius": r.choice((10, 20))})))]


def _boceto(r):
    return [("create_sketch", {"plane": r.choice(("XY", "XZ", "YZ"))}), ("draw_rectangle", {"x1": 0, "y1": 0, "x2": 60, "y2": 40}),
            ("draw_circle", {"center_x": 30, "center_y": 20, "radius": 8})]


def _extruido(r):
    return [*_boceto(r), ("extrude", {"sketch": "Boceto1", "profile": "all", "distance": r.choice((20, 45)), "taper_angle": r.choice((0, -5, -30))})]


def _vaciado(r):
    return [*r.choice((_extruido, lambda q: [_caja(q)]))(r),
            ("shell", {"body": "Cuerpo1", "thickness": r.choice((1, 2, 3)), "faces": r.choice((">Z", "<Z", ">X"))})]


def _chapa(r):
    return [("create_sketch", {"plane": "XY"}), ("draw_rectangle", {"x1": 0, "y1": 0, "x2": 80, "y2": 50}),
            ("create_base_flange", {"sketch": "Boceto1", "thickness": r.choice((1, 2))})]


def _malla(r):
    return [_caja(r), ("tessellate", {"bodies": "Cuerpo1", "keep_original": False})]


def _superficie(r):
    return [("create_surface_box", {"length": 40, "width": 30, "height": 20})] if r.random() < 0.5 else [
        ("create_sketch", {"plane": "XY"}), ("draw_circle", {"center_x": 0, "center_y": 0, "radius": 20}),
        ("create_surface_extrude", {"profiles": {"sketch": "Boceto1", "curve": 1}, "distance": 30})]


def _ensamble(r):
    return [_caja(r), ("create_box", {"length": 30, "width": 30, "height": 30, "x": 100}),
            ("create_component", {"bodies": ["Cuerpo1"]}), ("create_component", {"bodies": ["Cuerpo2"]}),
            ("create_joint", {"origin1": ">Z", "body1": "Cuerpo1", "origin2": "<Z", "body2": "Cuerpo2",
                              "joint_type": r.choice(("rigid", "revolute", "slider"))})]


def _contrato(r):
    """Un documento con algo de cada cosa, para que la mayoría de las herramientas tenga con qué trabajar."""
    return [*_boceto(r), ("extrude", {"sketch": "Boceto1", "profile": "all", "distance": 20}), ("create_box", {"length": 30, "width": 30, "height": 30, "x": 100}),
            ("create_drawing", {}), ("create_storyboard", {"name": "Caza"})]


PIEZAS = {"contrato": _contrato, "solido": _solido, "extruido": _extruido, "vaciado": _vaciado, "chapa": _chapa, "malla": _malla,
          "superficie": _superficie, "ensamble": _ensamble}


def _extruido_con_empalmes():
    pasos = [("create_box", {"length": 120, "width": 80, "height": 12}), ("create_sketch", {"plane": "XY"})]
    pasos += [("draw_circle", {"center_x": -48 + 16 * i, "center_y": -24 + 16 * k, "radius": 4}) for i in range(7) for k in range(4)]
    return [*pasos, ("extrude", {"sketch": "Boceto1", "profile": "all", "distance": 12, "operation": "cut", "target": "Cuerpo1"}),
            ("fillet", {"edges": "|Z", "radius": 3, "body": "Cuerpo1"}), ("shell", {"body": "Cuerpo1", "faces": ">Z", "thickness": 2})]


# Capa E: recetas fijas, las mismas en cada corrida, para comparar contra la base guardada en esta PC.
RECETAS_FIJAS = {n: [{"tool": t, "args": a} for t, a in f()] for n, f in {
    "placa_agujeros": _extruido_con_empalmes,
    **{p: (lambda p=p: PIEZAS[p](__import__("random").Random(0))) for p in PIEZAS if p != "contrato"}}.items()}
