# -*- coding: utf-8 -*-
"""Subcomandos `tools` y `describe`: explorar el catálogo (siempre dinámico: nada de listas fijas)."""
import sys
import textwrap
from pathlib import Path

from . import util


def _primera_linea(texto, largo=78):
    linea = texto.strip().splitlines()[0] if texto.strip() else ""
    punto = linea.find(". ")
    if punto != -1:
        linea = linea[:punto + 1]
    return linea if len(linea) <= largo else linea[:largo - 1].rstrip() + "…"


def _tipo(prop):
    if "enum" in prop:
        return "|".join(str(v) for v in prop["enum"])
    t = prop.get("type") or ("cualquiera" if "anyOf" not in prop else "|".join(str(p.get("type", "?")) for p in prop["anyOf"]))
    texto = "|".join(t) if isinstance(t, list) else t
    if texto == "array" and isinstance(prop.get("items"), dict) and prop["items"].get("type"):
        texto = f"array[{prop['items']['type']}]"
    return texto


def _markdown(ns, todo):
    """`tools --markdown`: el catálogo entero como Markdown (la fuente de docs/agentes/herramientas.md)."""
    if ns.group or ns.json:
        raise util.UsoError("--markdown documenta todo el catálogo: no se combina con --group ni con --json.")
    from ..api import doc_markdown
    texto = doc_markdown.catalogo_a_markdown(todo)
    if not ns.output:
        sys.stdout.write(texto)
        return 0
    destino = Path(ns.output)
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        with open(destino, "w", encoding="utf-8", newline="\n") as f:   # siempre UTF-8 y "\n", sin importar el sistema
            f.write(texto)
    except OSError as e:
        raise util.UsoError(f"No se pudo escribir {destino}: {e}") from None
    util.decir(f"escrito: {destino.resolve()} ({len(todo)} herramientas)")
    return 0


def tools(ns):
    todo = util.api().catalogo()
    if ns.output and not ns.markdown:
        raise util.UsoError("--output solo se usa con --markdown.")
    if ns.markdown:
        return _markdown(ns, todo)
    grupos = sorted({h["grupo"] for h in todo})
    if ns.group and ns.group not in grupos:
        raise util.UsoError(f"No existe el grupo '{ns.group}'.", [f"Grupos: {', '.join(grupos)}."])
    lista = [h for h in todo if not ns.group or h["grupo"] == ns.group]
    if ns.json:
        print(util.a_json([{k: h[k] for k in ("nombre", "grupo", "modifica", "descripcion")} for h in lista]))
        return 0
    ancho = max((len(h["nombre"]) for h in lista), default=0)
    anchog = max((len(h["grupo"]) for h in lista), default=0)
    for h in lista:
        util.decir(f"{h['nombre']:<{ancho}}  {h['grupo']:<{anchog}}  {'M' if h['modifica'] else '-'}  "
                   f"{_primera_linea(h['descripcion'])}")
    util.decir(f"\n{len(lista)} herramienta(s). M = modifica el documento. Detalle: omnicad describe <herramienta>")
    return 0


def describe(ns):
    h = util.exigir_herramienta(ns.herramienta, util.indice_catalogo())
    if ns.json:
        print(util.a_json(h))
        return 0
    util.decir(f"{h['nombre']}  [{h['grupo']}]  {'modifica el documento' if h['modifica'] else 'solo lee'}")
    util.decir(textwrap.fill(h["descripcion"], 100))
    props, req = h["esquema"]["properties"], h["esquema"]["required"]
    if not props:
        util.decir("\nSin parámetros.")
    else:
        util.decir("\nparámetros:")
        for nombre, p in props.items():
            marca = "obligatorio" if nombre in req else f"opcional, por defecto {p.get('default')!r}"
            util.decir(f"  {nombre}  ({_tipo(p)}; {marca})")
            if p.get("description"):
                util.decir(textwrap.fill(p["description"], 100, initial_indent="      ", subsequent_indent="      "))
    util.decir(f"\nUso: omnicad call {h['nombre']} --doc archivo.omnicad "
               + " ".join(f"{n}=…" for n in req))
    return 0


def registrar(sub, comun):
    p = sub.add_parser("tools", parents=[comun], help="lista las herramientas del catálogo",
                       description="Lista el catálogo de herramientas: nombre, grupo, si modifica (M) y su primera línea.")
    p.add_argument("--group", "-g", metavar="G", help="solo las de este grupo (documento, parametros, boceto, solido, ...)")
    p.add_argument("--markdown", action="store_true",
                   help="el catálogo entero como Markdown (así se genera docs/agentes/herramientas.md)")
    p.add_argument("--output", "-o", metavar="ruta.md",
                   help="con --markdown: escribir en este archivo (UTF-8, saltos \\n) en vez de la salida estándar")
    p.set_defaults(func=tools)
    p = sub.add_parser("describe", parents=[comun], help="descripción completa y parámetros de una herramienta",
                       description="Muestra la descripción y los parámetros (nombre, tipo, obligatorio, defecto) de una herramienta.")
    p.add_argument("herramienta", help="nombre exacto, p. ej. create_parameter")
    p.set_defaults(func=describe)
