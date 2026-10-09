# -*- coding: utf-8 -*-
"""Subcomando `dev` (verificación para agentes): `dev check` y `dev screenshot`.

Ninguno reimplementa nada: llaman a las herramientas `run_checks` y `app_screenshot` del catálogo (grupo "dev"),
o sea, la misma fuente que usa el servidor MCP."""
import re
from pathlib import Path

from . import util


def _tamano(texto):
    m = re.fullmatch(r"(\d+)[xX](\d+)", texto.strip())
    if not m:
        raise util.UsoError(f"--size tiene que ser ANCHOxALTO (p. ej. 1600x900), no '{texto}'.")
    return int(m.group(1)), int(m.group(2))


def _linea_paso(nombre, paso):
    if paso is None:
        return f"{nombre:<7} no se corrió"
    marca = "OK   " if paso["ok"] else "FALLA"
    return f"{nombre:<7} {marca} {paso['summary']}"


def sin_accion(ns):
    util.decir("Acciones: `dev check` y `dev screenshot`. Ayuda: omnicad dev <accion> --help", error=True)
    return 2


def check(ns):
    r = util.api().llamar(util.api().Sesion(), "run_checks", {"include_smoke": not ns.no_smoke})
    if ns.json:
        print(util.a_json(r))
        # Igual que sin --json: si algún paso falla, sale con 1 (aunque la llamada en sí haya andado).
        return util.codigo(r) if not r["ok"] else (0 if r["result"]["ok"] else 1)
    if not r["ok"]:
        util.mostrar("run_checks", r)
        return 1
    res = r["result"]
    util.decir(_linea_paso("ruff", res["ruff"]))
    util.decir(_linea_paso("pytest", res["pytest"]))
    if res["smoke"] is not None:
        util.decir(_linea_paso("humo", res["smoke"]))
    for linea in res["pytest"]["failed"] + (res["smoke"] or {}).get("failures", []):
        util.decir(f"  {linea}")
    util.decir(f"{'OK' if res['ok'] else 'FALLA'}: {res['seconds']} s")
    return 0 if res["ok"] else 1


def captura(ns):
    ancho, alto = _tamano(ns.size)
    if Path(ns.salida).suffix.lower() != ".png":
        raise util.UsoError(f"La salida tiene que ser un .png, no '{ns.salida}'.")
    if ns.example and ns.project:
        raise util.UsoError("Usá --example o --project, no los dos.")
    if ns.project and not Path(ns.project).is_file():
        raise util.UsoError(f"No existe el proyecto: {ns.project}", ["Pasá la ruta de un archivo .omnicad existente."])
    args = {"example": ns.example, "width": ancho, "height": alto}
    if ns.project:
        args["project"] = str(Path(ns.project).resolve())
    r = util.api().llamar(util.api().Sesion(), "app_screenshot", args)
    if r["ok"]:
        r["result"] = util.sacar_imagenes(r["result"], Path(ns.salida).resolve())
    if ns.json:
        print(util.a_json(r))
        return util.codigo(r)
    if not r["ok"]:
        util.mostrar("app_screenshot", r)
        return 1
    img = r["result"]["image"]
    util.decir(f"OK captura {img['path']}  {img['width']}x{img['height']}  {img['size_bytes']} bytes")
    return 0


def registrar(sub, comun):
    p = sub.add_parser("dev", help="verificación para agentes: checks del proyecto y captura de la ventana",
                       description="Herramientas de desarrollo. `check` corre ruff, pytest y la prueba de humo; "
                                   "`screenshot` captura la ventana real de OmniCAD a PNG.")
    p.set_defaults(func=sin_accion)
    acciones = p.add_subparsers(dest="accion", metavar="<accion>", parser_class=type(p), title="acciones")
    c = acciones.add_parser("check", parents=[comun], help="ruff + pytest + prueba de humo, con resumen",
                            description="Corre la verificación oficial (AGENTS.md): ruff con --select F,B023,B905, "
                                        "pytest y, salvo --no-smoke, la prueba de humo. Sale con 0 si todo pasa.")
    c.add_argument("--no-smoke", action="store_true",
                   help="no correr la prueba de humo (no abre la ventana; más rápido)")
    c.set_defaults(func=check)
    s = acciones.add_parser("screenshot", parents=[comun], help="captura la ventana real de OmniCAD a PNG",
                            description="Abre la ventana real en otro proceso, la captura entera y la cierra. "
                                        "No toca tus preferencias ni tus proyectos recientes.")
    s.add_argument("salida", metavar="salida.png", help="PNG donde guardar la captura")
    s.add_argument("--example", action="store_true", help="abrir el modelo de ejemplo")
    s.add_argument("--project", metavar="ruta.omnicad", help="abrir este proyecto")
    s.add_argument("--size", default="1600x900", metavar="ANCHOxALTO",
                   help="tamaño de la captura en píxeles (defecto 1600x900)")
    s.set_defaults(func=captura)
