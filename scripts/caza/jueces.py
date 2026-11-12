# -*- coding: utf-8 -*-
"""Jueces automáticos de la caza: dicen si un paso que dio `ok` dejó bien la pieza, sin que nadie la mire.

Cada juez devuelve None o un dict {"juez", "kind", "detalle"}. Reusan las herramientas del catálogo: nada de chequeos
propios de geometría (`check_geometry` ya es `nucleo/revision.py`)."""
import math
import re
import sys
from pathlib import Path

TOOL_MEMORIA = 4            # identificador libre de sys.monitoring
TOL = 1e-6                 # relativa, para lo que debería dar idéntico
TOL_FORMATO = 1e-3         # relativa: un STEP reimportado pasa por otra representación
INGLES = re.compile(r"\b(the|is|not|cannot|failed|error|object|invalid|must|has no|with)\b", re.I)
ID = re.compile(r"^[\w .-]+/[EFV]\d+$|^op\d+\.c\d+$")


# Firmas que son lo pedido, no un error.
ADMITIDOS = {"geometria|reverse_mesh_normals|invalido": "dar vuelta una malla cerrada la deja con volumen negativo"}


MEMORIA = []                # MemoryError vistos desde el último control, aunque la app los haya atrapado
TOPE_CASO_MB = 1500         # MB de más sobre lo que usaba el proceso al empezar: muy por encima de cualquier caso normal


def vigilar_memoria():
    """Anota todo MemoryError al lanzarse. El tope de `turno.py` convierte un desborde en un MemoryError que la app
    puede atrapar y seguir: sin esto, el tope esconde el error (el arco de 1e9 grados pasaba así)."""
    m = sys.monitoring

    def al_lanzar(codigo, _instruccion, excepcion):
        if isinstance(excepcion, MemoryError):
            cuadro = sys._getframe(1)
            while cuadro.f_back and "omnicad" not in cuadro.f_code.co_filename:      # la línea propia, no la de numpy
                cuadro = cuadro.f_back
            propio = cuadro.f_code if "omnicad" in cuadro.f_code.co_filename else codigo
            MEMORIA.append(f"{Path(propio.co_filename).name}:{propio.co_qualname}")
    m.use_tool_id(TOOL_MEMORIA, "caza")
    m.register_callback(TOOL_MEMORIA, m.events.RAISE, al_lanzar)
    m.set_events(TOOL_MEMORIA, m.events.RAISE)


def juez_memoria(op, pico_inicial=None, pico=None):
    """Falla si hubo un MemoryError, atrapado o no, o si el caso subió más que TOPE_CASO_MB."""
    if MEMORIA:
        lugar = MEMORIA[0]
        MEMORIA.clear()
        return {**fallo("memoria", f"MemoryError@{lugar}", "se quedó sin memoria, aunque el error se haya atrapado"), "op": op}
    if pico_inicial is not None and pico - pico_inicial > TOPE_CASO_MB:
        return {**fallo("memoria", "pico", f"{pico_inicial:.0f} → {pico:.0f} MB"), "op": op}
    return None


def finito(x):
    return isinstance(x, (int, float)) and math.isfinite(x)


def fallo(juez, kind, detalle=""):
    return {"juez": juez, "kind": kind, "detalle": str(detalle)[:300]}


def refrescar(api, s):
    """La API no confía en un id de cara o arista leído antes del último cambio: se vuelven a leer."""
    api.llamar(s, "find_faces", {})
    api.llamar(s, "find_edges", {})


def juez_contrato(respuesta, invalido=None, exito=False):
    """La respuesta cumple el contrato de `api.llamar`: dict, error con kind y mensaje en español, nada suelto."""
    if not isinstance(respuesta, dict) or "ok" not in respuesta:
        return fallo("contrato", "respuesta_rara", repr(respuesta)[:200])
    if respuesta["ok"]:
        return fallo("contrato", "acepta_invalido", f"aceptó {invalido}") if invalido else None
    kind, mensaje = respuesta.get("error_kind"), respuesta.get("mensaje")
    if not kind:
        return fallo("contrato", "sin_error_kind", respuesta)
    if kind == "INTERNAL_ERROR":
        return fallo("contrato", kind, mensaje)
    if not mensaje or not mensaje.strip():
        return fallo("contrato", "sin_mensaje", kind)
    if INGLES.search(mensaje) and not re.search(r"[áéíóúñ¿]| (el|la|de|no|un|una|que|en|con|se) ", mensaje):
        return fallo("contrato", "mensaje_en_ingles", mensaje)
    if exito:
        return fallo("esperado", "rechaza_valido", f"{kind}: {mensaje}")
    return None


def foto(api, s):
    """Volumen, área y caja de cada cuerpo, por nombre (los ids pueden cambiar al reabrir)."""
    r = api.llamar(s, "get_scene_info", {}).get("result") or {}
    salida = {}
    for c in r.get("bodies") or []:
        caja = c.get("bounding_box") or {}
        salida[c["name"]] = {"id": c["id"], "tipo": c.get("type"), "v": c.get("volume"), "a": c.get("area"),
                             "min": caja.get("min"), "max": caja.get("max")}
    return salida


def _plano(c):
    return [c["v"], c["a"], *(c["min"] or ()), *(c["max"] or ())]


def distintas(a, b, tol=TOL):
    """Qué cambió entre dos fotos; None si son la misma pieza."""
    if set(a) != set(b):
        return f"cuerpos {sorted(a)} → {sorted(b)}"
    for nombre in a:
        for x, y in zip(_plano(a[nombre]), _plano(b[nombre]), strict=False):
            if x is None or y is None:
                if x is not y:
                    return f"{nombre}: {x} → {y}"
            elif abs(x - y) > tol * max(abs(x), abs(y), 1.0):
                return f"{nombre}: {x:.6g} → {y:.6g}"
    return None


def juez_numeros(f):
    for nombre, c in f.items():
        for clave, x in (("v", c["v"]), ("a", c["a"])):
            if x is not None and not finito(x):
                return fallo("numeros", f"{clave}_no_finito", f"{nombre}: {x}")
        if c["tipo"] == "solid" and c["v"] is not None and c["v"] <= 0:
            return fallo("numeros", "volumen_no_positivo", f"{nombre}: {c['v']}")
        if c["min"] and c["max"]:
            if not all(map(finito, (*c["min"], *c["max"]))):
                return fallo("numeros", "caja_no_finita", nombre)
            if any(p > q for p, q in zip(c["min"], c["max"], strict=True)):
                return fallo("numeros", "caja_imposible", nombre)
    return None


def defectos(api, s, autointersecciones=True, solidos=False):
    """Defectos de `check_geometry`; `solidos` exige conservar sólidos en las cadenas de pieza real."""
    r = api.llamar(s, "check_geometry", {"self_intersection": autointersecciones}).get("result") or {}
    salida = {}
    for c in r.get("bodies") or []:
        # «invalido» va al final: el juez nombra el primero que crece, y desde B-173 `valid` también cae por autointersección.
        salida[c["name"]] = {"abierto": int(c.get("type") == "solid" and not c.get("closed", True)),
                             "aristas_libres": c.get("free_edges") or 0 if c.get("type") == "solid" else 0,
                             "no_manifold": c.get("non_manifold_edges") or 0,
                             "autointersecciones": c.get("self_intersections") or 0,
                             "invalido": int(not c.get("valid", True))}
        if solidos:
            salida[c["name"]]["no_solido"] = int(c.get("type") != "solid")
    return salida


def juez_geometria(antes, ahora):
    for nombre, d in ahora.items():
        previo = antes.get(nombre, {})
        for clave, n in d.items():
            if n > previo.get(clave, 0):
                return fallo("geometria", clave, f"{nombre}: {previo.get(clave, 0)} → {n}")
    return None


def _cuerpo(f, ref):
    return next((c for nombre, c in f.items() if ref in (nombre, c["id"])), None)


def _sobresale(antes, ahora, tol=1e-6):
    """La caja de todo creció: un empalme o un chaflán nunca saca material fuera de la caja."""
    cajas = [c for c in antes.values() if c["min"]]
    nuevas = [c for c in ahora.values() if c["min"]]
    if not cajas or not nuevas:
        return None
    for i in range(3):
        for extremo, signo in ((min, -1), (max, 1)):
            clave = "min" if signo < 0 else "max"
            a, b = extremo(c[clave][i] for c in cajas), extremo(c[clave][i] for c in nuevas)
            if (b - a) * signo > tol * max(abs(a), 1.0) + 1e-6:
                return f"eje {i}: {a:.6g} → {b:.6g}"
    return None


def juez_esperado(tool, args, antes, ahora):
    """Lo que cada operación no puede hacer, sea cual sea la pieza."""
    if tool in ("fillet", "chamfer"):
        d = _sobresale(antes, ahora)
        return fallo("esperado", "caja_crece", d) if d else None
    total = lambda f: sum(c["v"] or 0 for c in f.values())  # noqa: E731
    va, vd = total(antes), total(ahora)
    margen = TOL * max(va, 1.0)
    if tool == "boolean_operation":
        objetivo = _cuerpo(antes, args.get("target"))
        herramientas = [_cuerpo(antes, t) for t in args.get("tools") or ()]
        if objetivo is None or None in herramientas or not all(c["v"] for c in (objetivo, *herramientas)):
            return None
        queda = _cuerpo(ahora, args["target"])
        v = queda["v"] if queda and queda["v"] else 0.0
        op = args.get("operation", "join")
        if op == "cut" and v > objetivo["v"] + margen:
            return fallo("esperado", "cortar_agranda", f"{objetivo['v']:.6g} → {v:.6g}")
        if op == "join" and v < max(c["v"] for c in (objetivo, *herramientas)) - margen:
            return fallo("esperado", "unir_achica", f"{objetivo['v']:.6g} → {v:.6g}")
        if op == "intersect" and v > min(c["v"] for c in (objetivo, *herramientas)) + margen:
            return fallo("esperado", "intersecar_agranda", f"{objetivo['v']:.6g} → {v:.6g}")
    if tool == "create_hole" or (tool == "shell" and args.get("direction", "inside") == "inside"):
        if vd > va + margen:
            return fallo("esperado", "quitar_agranda", f"{va:.6g} → {vd:.6g}")
    return None


def juez_recalcular(api, s, f):
    r = api.llamar(s, "recompute_all", {})
    if not r.get("ok") or (r.get("result") or {}).get("failed_steps"):
        return fallo("recalcular", "paso_falla", r.get("mensaje") or r.get("result"))
    d = distintas(f, foto(api, s))
    return fallo("recalcular", "cambia", d) if d else None


def juez_deshacer(api, s, antes, f):
    if not api.llamar(s, "undo", {}).get("ok"):
        return fallo("deshacer", "undo_falla")
    d = distintas(antes, foto(api, s))
    if d:
        return fallo("deshacer", "undo_no_vuelve", d)
    if not api.llamar(s, "redo", {}).get("ok"):
        return fallo("deshacer", "redo_falla")
    d = distintas(f, foto(api, s))
    return fallo("deshacer", "redo_no_repite", d) if d else None


def juez_guardar(api, s, f, carpeta):
    ruta = str(Path(carpeta) / "guardar.omnicad")
    r = api.llamar(s, "save_document", {"path": ruta, "overwrite": True})
    if not r.get("ok"):
        return fallo("guardar", "no_guarda", r.get("mensaje"))
    otra = api.Sesion()
    r = api.llamar(otra, "open_document", {"path": ruta})
    if not r.get("ok"):
        return fallo("guardar", "no_reabre", r.get("mensaje"))
    d = distintas(f, foto(api, otra))
    return fallo("guardar", "reabrir_cambia", d) if d else None


def juez_exportar(api, s, f, carpeta):
    solidos = {n: c for n, c in f.items() if c["tipo"] == "solid" and c["v"]}
    if not solidos:
        return None
    ruta = str(Path(carpeta) / "exportar.step")
    r = api.llamar(s, "export", {"path": ruta, "bodies": [c["id"] for c in solidos.values()], "overwrite": True})
    if not r.get("ok"):
        return None if r.get("error_kind") != "INTERNAL_ERROR" else fallo("exportar", "INTERNAL_ERROR", r.get("mensaje"))
    otra = api.Sesion()
    if not api.llamar(otra, "open_document", {"path": ruta}).get("ok"):
        return fallo("exportar", "no_reimporta")
    v0, v1 = sum(c["v"] for c in solidos.values()), sum(c["v"] or 0 for c in foto(api, otra).values())
    if abs(v0 - v1) > TOL_FORMATO * v0:
        return fallo("exportar", "volumen_cambia", f"{v0:.6g} → {v1:.6g}")
    return None


def juez_editar(api, s, f):
    """Sube 25 % la primera cota del último paso que tenga una y la vuelve: tiene que quedar la misma pieza."""
    pasos = (api.llamar(s, "get_timeline", {}).get("result") or {}).get("steps") or []
    for paso in reversed(pasos):
        for clave, v in (paso.get("values") or {}).items():
            if finito(v) and v > 0:
                original = paso["params"].get(clave, v)
                if not api.llamar(s, "edit_feature", {"feature": paso["id"], "params": {clave: v * 1.25}}).get("ok"):
                    return None
                r = api.llamar(s, "edit_feature", {"feature": paso["id"], "params": {clave: original}})
                if not r.get("ok"):
                    return fallo("editar", "no_vuelve", r.get("mensaje"))
                d = distintas(f, foto(api, s))
                return fallo("editar", "otra_pieza", d) if d else None
    return None


def movible(args):
    """El paso se refiere solo a ids y números: mover la pieza no le cambia el sentido (un plano o un punto, sí)."""
    def sirve(x):
        if isinstance(x, (list, tuple)):
            return all(map(sirve, x))
        return isinstance(x, (int, float)) or (isinstance(x, str) and bool(ID.match(x)))
    return bool(args) and any(isinstance(v, (list, tuple)) or (isinstance(v, str) and ID.match(v)) for v in args.values()) \
        and all(sirve(v) for v in args.values())


def juez_mover(api, rehacer, tool, args, f):
    """Mover la pieza entera antes del paso no le cambia el volumen."""
    if not movible(args) or not f:
        return None
    otra = rehacer()
    if not api.llamar(otra, "move_body", {"body": [c["id"] for c in foto(api, otra).values()],
                                          "translate": [13.7, -7.3, 5.1]}).get("ok"):
        return None
    refrescar(api, otra)
    if not api.llamar(otra, tool, args).get("ok"):         # un rechazo con mensaje claro no es este juez
        return None
    v0, v1 = sum(c["v"] or 0 for c in f.values()), sum(c["v"] or 0 for c in foto(api, otra).values())
    if abs(v0 - v1) > 1e-5 * max(abs(v0), 1.0):
        return fallo("mover", "volumen_cambia", f"{v0:.6g} → {v1:.6g}")
    return None


def juez_identidad(api, rehacer, args, antes, f):
    """V(A∪B) + V(A∩B) = V(A) + V(B), con cada booleana calculada aparte."""
    op, herramientas = args.get("operation", "join"), args.get("tools") or ()
    a, b = _cuerpo(antes, args.get("target")), _cuerpo(antes, herramientas[0]) if len(herramientas) == 1 else None
    if op == "cut" or a is None or b is None or not (a["v"] and b["v"]) or a is b:
        return None
    resto = lambda g: sum(c["v"] or 0 for c in g.values()) - sum(c["v"] or 0 for c in antes.values()) + a["v"] + b["v"]  # noqa: E731
    v_op = resto(f) - (b["v"] if args.get("keep_tools") else 0.0)
    otra = rehacer()
    r = api.llamar(otra, "boolean_operation", {**args, "operation": "intersect" if op == "join" else "join",
                                               "keep_tools": False})
    v_otra = resto(foto(api, otra)) if r.get("ok") else 0.0 if op == "join" else None
    if v_otra is None:
        return None
    if not math.isclose(v_op + v_otra, a["v"] + b["v"], rel_tol=1e-5):
        return fallo("identidad", "no_cierra", f"{v_op:.6g} + {v_otra:.6g} ≠ {a['v']:.6g} + {b['v']:.6g}")
    return None
