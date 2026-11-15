"""P-158: los mensajes de los paneles de Bocetos y Sólido son de 1 renglón (regla 14 de CLAUDE.md).

Límite medido: el panel «simple» mide 320 px (`formulario.ANCHOS`); descontando 44 px de márgenes y el símbolo quedan
276 px, y con la fuente por defecto (Sans Serif 9 pt, unos 6,3 px por letra) entran unos 44 caracteres.
Trinquete: cada archivo tiene el tope de mensajes que todavía pasan el límite. Solo puede bajar: un mensaje largo nuevo
falla, y acortar uno obliga a bajar el tope. La lista completa está en `docs/auditoria_mensajes_paneles.md`."""
import ast
import re
from pathlib import Path

import pytest

LIMITE = 45
HUECO = 6        # lo que ocupa un valor «{}» al mostrarse (p. ej. «36,26 mm»)
RAIZ = Path(__file__).resolve().parent.parent / "omnicad"
NOMBRES = {"ErrorGeometria", "ErrorOperacion", "ErrorComando", "ErrorBoceto", "exigir", "_mostrar"}
TOPES = {
    "nucleo/solidos_crear.py": 146,
    "nucleo/solidos_modificar.py": 49,
    "timeline/ops_solido.py": 46,
    "restricciones/boceto.py": 95,
    "ui/comandos/crear.py": 9,
    "ui/comandos/modificar.py": 12,
    "ui/comandos/solido.py": 6,
    "ui/comandos/primitivas.py": 2,
    "ui/comandos/patrones.py": 2,
    "ui/manipuladores.py": 0,
    "nucleo/superficies.py": 0,
    "timeline/ops_superficie.py": 0,
    "ui/comandos/superficie.py": 0,
}


def _textos(n):
    if isinstance(n, ast.Constant) and isinstance(n.value, str):
        yield n.value
    elif isinstance(n, ast.JoinedStr):
        yield "".join(v.value if isinstance(v, ast.Constant) else "{}" for v in n.values)
    elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "format":
        yield from _textos(n.func.value)


def largos(archivo):
    """Los mensajes de errores y avisos de `archivo` que pasan del límite: [(línea, largo, texto)]."""
    arbol = ast.parse((RAIZ / archivo).read_text(encoding="utf-8"))
    salida = []
    for n in ast.walk(arbol):
        if isinstance(n, ast.Call) and n.args:
            f = n.func
            if (f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else "") in NOMBRES:
                for t in _textos(n.args[0]):
                    largo = len(re.sub(r"\{[^}]*\}", "x" * HUECO, t))
                    if largo > LIMITE:
                        salida.append((n.lineno, largo, t))
    return salida


@pytest.mark.parametrize("archivo", TOPES)
def test_mensajes_de_panel_de_1_renglon(archivo):
    n = len(largos(archivo))
    assert n <= TOPES[archivo], (f"{archivo}: {n} mensajes pasan de {LIMITE} caracteres (tope {TOPES[archivo]}): "
                                 f"acortá el nuevo; ejemplos: {largos(archivo)[:2]}")
    assert n == TOPES[archivo], f"{archivo}: ahora son {n}; bajá el tope a {n} en TOPES"


def test_el_empalme_de_gerardo_ya_no_tiene_6_renglones():
    """El caso de Gerardo (2026-11-15): «el asa frena en 36.26 mm… reordená los empalmes del timeline…»."""
    fuente = (RAIZ / "nucleo/solidos_modificar.py").read_text(encoding="utf-8")
    assert "reordená los" not in fuente
    assert "Con más:" not in (RAIZ / "ui/manipuladores.py").read_text(encoding="utf-8")
