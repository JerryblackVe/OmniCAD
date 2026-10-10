# -*- coding: utf-8 -*-
"""Atajos: `new`, `info`, `export`, `render`, `run` y `batch`. Ninguno reimplementa nada: todos llaman a
herramientas del catálogo (new_document, save_document, get_scene_info, export, get_viewport_image,
execute_code) o a la que diga cada paso del batch."""
import json
import re
from pathlib import Path

from . import util
from .cmd_llamar import correr


# ---------------------------------------------------------------- new
def nuevo(ns):
    sesion = util.api().Sesion()
    ruta = Path(ns.archivo)
    # Como en Fusion, el documento se llama como el archivo: save_document le pone ese nombre.
    r = util.api().llamar(sesion, "new_document", {"name": ruta.stem})
    if r["ok"]:
        r = util.api().llamar(sesion, "save_document", {"path": str(ruta), "overwrite": ns.overwrite})
    util.mostrar("new", r, ns.json)
    return util.codigo(r)


# ---------------------------------------------------------------- info / export / render
def info(ns):
    return correr("get_scene_info", {}, ns.archivo, ns.json, guardar=False)


def exportar(ns):
    args = {"path": ns.salida, "overwrite": ns.overwrite}
    if ns.bodies:
        args["bodies"] = ns.bodies
    return correr("export", args, ns.archivo, ns.json, guardar=False)


def _tamano(texto):
    m = re.fullmatch(r"(\d+)[xX](\d+)", texto.strip())
    if not m:
        raise util.UsoError(f"--size tiene que ser ANCHOxALTO (p. ej. 800x600), no '{texto}'.")
    return int(m.group(1)), int(m.group(2))


def render(ns):
    ancho, alto = _tamano(ns.size)
    if Path(ns.salida).suffix.lower() != ".png":
        raise util.UsoError(f"La salida de render tiene que ser un .png, no '{ns.salida}'.")
    vistas = util.exigir_herramienta("get_viewport_image", util.indice_catalogo())["esquema"]["properties"]["view"]
    if ns.view not in vistas.get("enum", [ns.view]):
        raise util.UsoError(f"Vista inválida: '{ns.view}'.", [f"Vistas: {', '.join(vistas['enum'])}."])
    return correr("get_viewport_image", {"view": ns.view, "width": ancho, "height": alto},
                  ns.archivo, ns.json, guardar=False, image_out=ns.salida)


# ---------------------------------------------------------------- run
def ejecutar_script(ns):
    ruta = Path(ns.script)
    if not ruta.is_file():
        raise util.UsoError(f"No existe el script: {ruta}")
    if ns.save and not ns.doc:
        raise util.UsoError("--save necesita --doc: no hay archivo donde guardar.")
    codigo = ruta.read_text(encoding="utf-8-sig")
    return correr("execute_code", {"code": codigo, "timeout": None}, ns.doc, ns.json, guardar=ns.save)


# ---------------------------------------------------------------- batch
def _leer_pasos(ruta):
    ruta = Path(ruta)
    if not ruta.is_file():
        raise util.UsoError(f"No existe el archivo de pasos: {ruta}")
    pasos = []
    for n, linea in enumerate(ruta.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not linea.strip():
            continue
        try:
            paso = json.loads(linea)
        except ValueError as e:
            raise util.UsoError(f"{ruta.name}, línea {n}: no es JSON válido ({e}). Nada se ejecutó.") from None
        if not isinstance(paso, dict) or not isinstance(paso.get("tool"), str) \
                or not isinstance(paso.get("args", {}), dict) or set(paso) - {"tool", "args"}:
            raise util.UsoError(f'{ruta.name}, línea {n}: cada línea es {{"tool": "nombre", "args": {{...}}}}. Nada se ejecutó.')
        pasos.append((n, paso["tool"], paso.get("args", {})))
    if not pasos:
        raise util.UsoError(f"{ruta.name} no tiene pasos.")
    return pasos


def batch(ns):
    pasos = _leer_pasos(ns.pasos)
    indice = util.indice_catalogo()
    for n, nombre, _ in pasos:     # una herramienta inexistente es error de uso: se detecta antes de tocar nada
        if nombre not in indice:
            util.exigir_herramienta(nombre, indice)
    sesion, abierto, previos, falla = util.abrir_sesion(ns.doc)
    if falla is not None:
        util.mostrar("open_document", falla, ns.json)
        return 1
    resultados, hubo_cambios, fallo = [], False, None
    for n, nombre, args in pasos:
        r = util.api().llamar(sesion, nombre, args)
        if r["ok"]:
            r["result"] = util.sacar_imagenes(r["result"])
            hubo_cambios = hubo_cambios or indice[nombre]["modifica"]
        resultados.append((n, nombre, r))
        if not r["ok"] and not ns.continue_on_error:
            fallo = (n, nombre, r)
            break
    errores = [x for x in resultados if not x[2]["ok"]]
    guardado = None
    if hubo_cambios and fallo is None and not ns.no_save and util.puede_guardar(sesion, abierto):
        falla, guardado = util.guardar(sesion)
        if falla is not None:
            resultados.append((0, "save_document", falla))
            errores.append(resultados[-1])
    if ns.json:
        print(util.a_json([r for _, _, r in resultados]))
    else:
        for a in previos:
            util.decir(f"aviso: {a}", error=True)
        for i, (n, nombre, r) in enumerate(resultados, 1):
            if r["ok"]:
                util.decir(f"paso {i} (línea {n}) OK {nombre}")
            else:
                util.decir(f"paso {i} (línea {n}) ERROR [{r['error_kind']}] {nombre}: {r['mensaje']}", error=True)
                for p in r.get("pistas", []):
                    util.decir(f"  pista: {p}", error=True)
        if fallo:
            util.decir(f"Se detuvo en el paso {len(resultados)} de {len(pasos)}: NO se guardó nada.", error=True)
        elif guardado:
            util.decir(f"guardado: {guardado}")
        util.decir(f"{len(resultados) - len(errores)} ok, {len(errores)} con error, de {len(pasos)} paso(s).")
    return 1 if errores else 0


# ---------------------------------------------------------------- registro
def registrar(sub, comun):
    p = sub.add_parser("new", parents=[comun], help="crea un proyecto vacío",
                       description="Crea un proyecto .omnicad vacío (herramientas new_document + save_document). El documento se llama como el archivo.")
    p.add_argument("archivo", metavar="archivo.omnicad")
    p.add_argument("--overwrite", action="store_true", help="reemplazar el archivo si ya existe")
    p.set_defaults(func=nuevo)

    p = sub.add_parser("info", parents=[comun], help="resumen de un proyecto (get_scene_info)",
                       description="Cuerpos, bocetos, pasos y parámetros de un proyecto. No modifica el archivo.")
    p.add_argument("archivo", metavar="archivo.omnicad")
    p.set_defaults(func=info)

    p = sub.add_parser("export", parents=[comun], help="exporta cuerpos a STL, STEP, OBJ... (herramienta export)",
                       description="Exporta los cuerpos de un proyecto; el formato sale de la extensión de la salida "
                                   "(.stl .obj .3mf .ply .step .stp .iges .igs .brep .glb .gltf; .dxf: patrón plano de chapa).")
    p.add_argument("archivo", metavar="archivo.omnicad")
    p.add_argument("salida", metavar="salida.stl|.step|...")
    p.add_argument("--bodies", "-b", nargs="+", metavar="CUERPO", help="ids o nombres de los cuerpos (por defecto, todos)")
    p.add_argument("--overwrite", action="store_true", help="reemplazar la salida si ya existe")
    p.set_defaults(func=exportar)

    p = sub.add_parser("render", parents=[comun], help="renderiza una vista a PNG (get_viewport_image)",
                       description="Dibuja el modelo y escribe un PNG (nunca base64 por consola).")
    p.add_argument("archivo", metavar="archivo.omnicad")
    p.add_argument("salida", metavar="salida.png")
    p.add_argument("--view", "-v", default="iso", metavar="V", help="iso, front, back, top, bottom, left o right (defecto iso)")
    p.add_argument("--size", "-s", default="800x600", metavar="ANCHOxALTO", help="tamaño en píxeles (defecto 800x600)")
    p.set_defaults(func=render)

    p = sub.add_parser("run", parents=[comun], help="ejecuta un script Python con api, sesion, doc y llamar",
                       description="Ejecuta un script Python con `api`, `sesion`, `doc` y `llamar(nombre, args)` ya definidos "
                                   "(herramienta execute_code: atómico, `result = ...` devuelve un valor, print va a stdout). "
                                   "Sin --save el archivo no se toca.")
    p.add_argument("script", metavar="script.py")
    p.add_argument("--doc", metavar="archivo.omnicad", help="proyecto sobre el que corre el script (sin él, un documento vacío)")
    p.add_argument("--save", action="store_true", help="guardar el proyecto de vuelta si el script salió bien (exige --doc)")
    p.set_defaults(func=ejecutar_script)

    p = sub.add_parser("batch", parents=[comun], help="corre muchos pasos (JSONL) en un solo proceso",
                       description='Cada línea del archivo es {"tool": "nombre", "args": {...}}. Todo corre en una sola sesión; '
                                   "al final se guarda el --doc UNA vez. Si un paso falla y no hay --continue-on-error, "
                                   "se detiene, informa cuál falló y NO guarda nada. Con --json, la salida es la lista "
                                   "de resultados de los pasos ejecutados.")
    p.add_argument("pasos", metavar="pasos.jsonl")
    p.add_argument("--doc", metavar="archivo.omnicad", help="proyecto sobre el que se trabaja (tiene que existir)")
    p.add_argument("--continue-on-error", action="store_true", help="seguir con los pasos siguientes si uno falla")
    p.add_argument("--no-save", action="store_true", help="no guardar el archivo")
    p.set_defaults(func=batch)
