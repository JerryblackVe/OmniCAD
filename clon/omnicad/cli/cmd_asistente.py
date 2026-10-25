# -*- coding: utf-8 -*-
"""Atajo `assistant_ask`: un pedido al Asistente IA sin ventana (herramienta assistant_ask del grupo `asistente`)."""
from .cmd_llamar import correr


def preguntar(ns):
    return correr("assistant_ask", {"prompt": ns.prompt, "mode": ns.mode}, ns.doc, ns.json, guardar=not ns.no_save)


def registrar(sub, comun):
    p = sub.add_parser("assistant_ask", parents=[comun], help="pedido al Asistente IA, sin ventana (gasta en la API)",
                       description="Corre un pedido al Asistente IA con el proveedor de Preferencias › Asistente IA "
                                   "(omnicad call get_assistant_config lo muestra). GASTA en la API elegida; la clave "
                                   "sale de la variable de entorno del proveedor. Con --doc trabaja sobre ese proyecto y "
                                   "lo guarda de vuelta si salió bien (salvo --no-save); todo el pedido es UN paso de "
                                   "deshacer. En guiar y hacer los cambios se aprueban solos (no hay tarjeta de plan).",
                       epilog='ejemplo:\n  omnicad assistant_ask "hacé una caja de 40 mm con empalme de 3" --doc pieza.omnicad')
    p.add_argument("prompt", help="el pedido, en lenguaje natural")
    p.add_argument("--mode", "-m", default="hacer", choices=("explicar", "mostrar", "guiar", "hacer"),
                   help="explicar y mostrar no cambian el documento (defecto hacer)")
    p.add_argument("--doc", metavar="archivo.omnicad", help="proyecto sobre el que se trabaja (sin él, un documento vacío)")
    p.add_argument("--no-save", action="store_true", help="no guardar el proyecto aunque el pedido lo cambie")
    p.set_defaults(func=preguntar)
