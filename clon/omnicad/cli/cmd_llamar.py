# -*- coding: utf-8 -*-
"""Subcomando `call` y el motor que comparten los atajos: abrir → llamar → (guardar) → mostrar."""
from . import util


def correr(nombre, args, doc, como_json, guardar=True, image_out=None):
    """Una llamada completa: abre `doc` (si hay), llama la herramienta, guarda si modifica y sale ok."""
    indice = util.indice_catalogo()
    h = util.exigir_herramienta(nombre, indice)
    sesion, abierto, previos, falla = util.abrir_sesion(doc)
    if falla is not None:
        util.mostrar("open_document", falla, como_json)
        return 1
    r = util.api().llamar(sesion, nombre, args)
    guardado = None
    if r["ok"]:
        r["result"] = util.sacar_imagenes(r["result"], image_out)
        if h["modifica"] and guardar and util.puede_guardar(sesion, abierto):
            falla, guardado = util.guardar(sesion)
            r = falla or r
    util.mostrar(nombre, r, como_json, previos, guardado)
    return util.codigo(r)


def llamar(ns):
    h = util.exigir_herramienta(ns.herramienta, util.indice_catalogo())
    args = util.construir_args(ns, h)
    return correr(ns.herramienta, args, ns.doc, ns.json, guardar=not ns.no_save, image_out=ns.image_out)


def registrar(sub, comun):
    p = sub.add_parser(
        "call", parents=[comun], help="llama a cualquier herramienta del catálogo",
        description="Llama a una herramienta. Con --doc abre ese archivo; si la herramienta modifica y sale bien, "
                    "lo guarda de vuelta (atómico) salvo --no-save. Los argumentos van como --args '{json}', "
                    "--args-file f.json (o - para stdin) y/o clave=valor (el valor es JSON si se puede: "
                    "números, listas, true/false; si no, texto). Si se repiten, clave=valor gana.",
        epilog="Las imágenes nunca salen en base64: se escriben a --image-out (o a un temporal) y la salida trae la ruta.\n"
               "Salida: 0 ok, 1 la herramienta falló, 2 error de uso (herramienta inexistente, JSON inválido, archivo inexistente).")
    p.add_argument("herramienta", help="nombre de la herramienta (omnicad tools)")
    p.add_argument("pares", nargs="*", metavar="clave=valor", help="argumentos de la herramienta")
    p.add_argument("--doc", metavar="archivo.omnicad", help="proyecto sobre el que se trabaja (tiene que existir)")
    grupo = p.add_mutually_exclusive_group()
    grupo.add_argument("--args", metavar="JSON", help="argumentos como objeto JSON")
    grupo.add_argument("--args-file", metavar="f.json", help="argumentos desde un archivo JSON ('-' = stdin)")
    p.add_argument("--no-save", action="store_true", help="no guardar el archivo aunque la herramienta modifique")
    p.add_argument("--image-out", metavar="ruta.png", help="dónde escribir la imagen del resultado (si no, un temporal)")
    p.set_defaults(func=llamar)
