# -*- coding: utf-8 -*-
"""Subcomando `dev` (verificación para agentes): `dev check`, `dev screenshot` y `dev bench`.

Ninguno reimplementa nada: llaman a las herramientas `run_checks`, `app_screenshot` y `run_bench` del catálogo (grupo "dev"),
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
    util.decir("Acciones: `dev check`, `dev screenshot` y `dev bench`. Ayuda: omnicad dev <accion> --help", error=True)
    return 2


def check(ns):
    r = util.api().llamar(util.api().Sesion(), "run_checks", {"include_smoke": not ns.no_smoke})
    if ns.json:
        print(util.a_json(r))
        # Igual que sin --json: si algún paso falla, sale con 1 (aunque la llamada en sí haya andado).
        return util.codigo(r) if not r["ok"] else (0 if r["result"]["ok"] else 1)
    if not r["ok"]:
        util.mostrar("run_checks", r, False)
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
    if ns.theme:
        args["theme"] = ns.theme
    if ns.project:
        args["project"] = str(Path(ns.project).resolve())
    r = util.api().llamar(util.api().Sesion(), "app_screenshot", args)
    if r["ok"]:
        r["result"] = util.sacar_imagenes(r["result"], Path(ns.salida).resolve())
    if ns.json:
        print(util.a_json(r))
        return util.codigo(r)
    if not r["ok"]:
        util.mostrar("app_screenshot", r, False)
        return 1
    img = r["result"]["image"]
    util.decir(f"OK captura {img['path']}  {img['width']}x{img['height']}  {img['size_bytes']} bytes")
    return 0


def bench(ns):
    r = util.api().llamar(util.api().Sesion(), "run_bench",
                          {"repetitions": ns.repeticiones, "side": ns.lado, "frames": ns.cuadros,
                           **({"preset": ns.preset} if ns.preset else {})})
    if ns.json:
        print(util.a_json(r))
        return util.codigo(r)
    if not r["ok"]:
        util.mostrar("run_bench", r, False)
        return 1
    x = r["result"]
    g, m = x["giro"], x["modelo"]
    util.decir(f"Mediana de {x['repetitions']} corrida(s), gráficos «{x['preset']}»:")
    util.decir(f"  arranque         {x['arranque_s']} s  (importar: {x['importar_s']} s)")
    util.decir(f"  memoria          {x['memoria_inicio_mb']} MB al arrancar · {x['memoria_modelo_mb']} MB con el modelo "
               f"· pico {x['memoria_pico_mb']} MB")
    util.decir(f"  modelo grande    {m['pasos']} pasos, {x['triangulos']} triángulos")
    util.decir(f"  recálculo        todo {x['recalculo_completo_s']} s · último paso {x['recalculo_ultimo_paso_s']} s"
               f" · cambiar un parámetro {x['recalculo_parametro_s']} s"
               f" (uno que usa solo el último paso: {x.get('recalculo_parametro_final_s', '-')} s)")
    util.decir(f"  vista 3D         {g['ms_medio']} ms por cuadro ({g['fps_dibujo']} cuadros/s posibles) · "
               f"{g['fps_pantalla']} cuadros/s en pantalla")
    lejos = x.get("lejos")
    if lejos:
        util.decir(f"  de lejos         {lejos['triangulos']} triángulos, {lejos['ms_medio']} ms por cuadro (sin menos "
                   f"detalle a la distancia: {lejos['triangulos_sin_lod']} triángulos, {lejos['ms_medio_sin_lod']} ms)")
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
    s.add_argument("--theme", metavar="NOMBRE",
                   help="tema de la interfaz: oscuro_moderno (defecto), claro_moderno, azul_profesional, "
                        "minimalista, clasico o usuario:<archivo>")
    s.set_defaults(func=captura)
    b = acciones.add_parser("bench", parents=[comun], help="mide el rendimiento con la ventana real",
                            description="Abre la ventana real en otro proceso y mide arranque, memoria, recálculo de "
                                        "un modelo grande y cuadros por segundo al girar. Repite y da la mediana.")
    b.add_argument("--repeticiones", type=int, default=3, help="cuántas veces medir (defecto 3)")
    b.add_argument("--lado", type=int, default=8, help="agujeros por lado del modelo grande (defecto 8 → 64)")
    b.add_argument("--cuadros", type=int, default=120, help="cuadros de la órbita (defecto 120)")
    b.add_argument("--preset", choices=("rendimiento", "equilibrado", "calidad", "personalizar"),
                   help="valor predefinido de gráficos con el que medir (defecto: el de fábrica)")
    b.set_defaults(func=bench)
