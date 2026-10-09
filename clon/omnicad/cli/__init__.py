# -*- coding: utf-8 -*-
"""
CLI `omnicad`: todo el catálogo de la API única (`omnicad.api`) desde la terminal, pensada para agentes IA
(salida predecible, `--json`, códigos de salida fijos) y usable por una persona.

Códigos de salida: 0 ok · 1 la herramienta devolvió un error (ok False) · 2 error de uso (argumentos, archivo
inexistente).

Cómo se suma un subcomando (p. ej. `dev` o `setup`): crear `cli/cmd_<nombre>.py` con
`registrar(subparsers, comun)`; cada subcomando define `parser.set_defaults(func=manejador)` y
`manejador(ns) -> int`. Se descubre solo (no hay que tocar este archivo). Regla: los módulos `cmd_*` importan
solo cosas livianas al tope (`omnicad.api` tarda ~2 s: importarlo dentro del manejador, vía `util.api()`),
porque `omnicad --version` y `--help` tienen que arrancar al instante.
"""
import argparse
import importlib
import pkgutil
import re
import sys

from .. import VERSION
from . import util

_BASE = ("cmd_catalogo", "cmd_llamar", "cmd_atajos")   # orden de la ayuda; el resto se descubre solo

_TRADUCCIONES = [
    (r"the following arguments are required: ", "faltan argumentos obligatorios: "),
    (r"unrecognized arguments: ", "argumentos no reconocidos: "),
    (r"invalid choice: (.*) \(choose from (.*)\)", r"opción inválida: \1 (opciones: \2)"),
    (r"expected one argument", "falta el valor del argumento"),
    (r"argument (.*): not allowed with argument (.*)", r"el argumento \1 no se puede usar junto con \2"),
    (r"invalid int value: (.*)", r"no es un entero: \1"),
]

EPILOGO = """\
ejemplos:
  omnicad new pieza.omnicad
  omnicad call create_parameter --doc pieza.omnicad name=ancho expression="60 mm"
  omnicad call create_box --doc pieza.omnicad --args '{"length": "ancho", "width": 30, "height": 10}'
  omnicad info pieza.omnicad --json
  omnicad render pieza.omnicad vista.png --view iso --size 800x600
  omnicad export pieza.omnicad pieza.stl
  omnicad batch pasos.jsonl --doc pieza.omnicad
  omnicad tools --group documento        (todo el catálogo: omnicad tools; un detalle: omnicad describe <herramienta>)

códigos de salida: 0 ok, 1 la herramienta devolvió un error (con --json trae error_kind), 2 error de uso.
Las herramientas que modifican guardan el archivo de vuelta (atómico) salvo --no-save.
"""


class _Formato(argparse.RawDescriptionHelpFormatter):
    def add_usage(self, usage, actions, groups, prefix=None):
        super().add_usage(usage, actions, groups, "uso: " if prefix is None else prefix)


class Parser(argparse.ArgumentParser):
    """ArgumentParser con la ayuda y los errores en español."""

    def __init__(self, *args, **kw):
        kw.setdefault("formatter_class", _Formato)
        kw["add_help"] = False
        super().__init__(*args, **kw)
        self._positionals.title, self._optionals.title = "argumentos", "opciones"
        self.add_argument("-h", "--help", action="help", default=argparse.SUPPRESS,
                          help="muestra esta ayuda y sale")

    def error(self, message):
        for patron, texto in _TRADUCCIONES:
            message = re.sub(patron, texto, message)
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def _modulos():
    nombres = list(_BASE)
    nombres += sorted(m.name for m in pkgutil.iter_modules(__path__)
                      if m.name.startswith("cmd_") and m.name not in _BASE)
    return [importlib.import_module(f"{__name__}.{n}") for n in nombres]


def construir_parser():
    parser = Parser(prog="omnicad", epilog=EPILOGO,
                    description="OmniCAD desde la terminal: todo el catálogo de herramientas de la API, "
                                "pensado para agentes IA y para personas.")
    parser.add_argument("--version", action="version", version=f"omnicad {VERSION}",
                        help="muestra la versión y sale")
    comun = argparse.ArgumentParser(add_help=False)
    comun.add_argument("--json", action="store_true",
                       help="salida JSON exacta (la que devuelve api.llamar) en vez de texto corto")
    sub = parser.add_subparsers(dest="comando", metavar="<comando>", parser_class=Parser,
                                title="comandos", help="qué hacer")
    for modulo in _modulos():
        modulo.registrar(sub, comun)
    return parser


def main(argv=None) -> int:
    """Punto de entrada. Devuelve el código de salida (0, 1 o 2); nunca deja escapar excepciones esperables."""
    util.usar_utf8()
    parser = construir_parser()
    ns = None
    try:
        ns, sobrantes = parser.parse_known_args(argv)
        # `clave=valor` puede ir mezclado con las opciones (argparse solo toma un tramo de posicionales).
        pares = [s for s in sobrantes if re.match(r"^[A-Za-z_]\w*=", s)]
        sobrantes = [s for s in sobrantes if s not in pares]
        if sobrantes or (pares and not hasattr(ns, "pares")):
            parser.error(f"argumentos no reconocidos: {' '.join(sobrantes or pares)}")
        if pares:
            ns.pares = list(ns.pares or []) + pares
        if not getattr(ns, "func", None):
            parser.print_help()
            return 2
        return ns.func(ns)
    except SystemExit as e:                      # --help / --version (0) y errores de argparse (2)
        return e.code if isinstance(e.code, int) else (0 if e.code is None else 2)
    except util.UsoError as e:
        if ns is not None and getattr(ns, "json", False):
            print(util.a_json({"ok": False, "error_kind": "CLI_USAGE", "mensaje": e.mensaje, "pistas": e.pistas}))
        else:
            util.decir(f"error: {e.mensaje}", error=True)
            for p in e.pistas:
                util.decir(f"  pista: {p}", error=True)
        return 2
    except KeyboardInterrupt:
        return 130
