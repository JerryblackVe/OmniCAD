"""B-302: ayudas y errores propios explican su uso sin comparaciones con otro programa."""
import ast
from pathlib import Path
import re

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo, tolerancias
from omnicad.ui.comandos import CATALOGO


def test_ayudas_del_catalogo_sin_comparaciones():
    # La palabra completa distingue la marca de los verbos «Fusionar» y «Fusiona».
    assert not [clave for clave, comando in CATALOGO.items() if re.search(r"\bFusion\b", comando.AYUDA)]


@pytest.mark.parametrize("archivo", ["panel_timeline.py", "ventana.py", "comandos/modificar.py", "comandos/fijacion.py"])
def test_literales_de_la_interfaz_sin_comparaciones(archivo):
    ruta = Path(__file__).resolve().parents[1] / "omnicad" / "ui" / archivo
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    docstrings = {
        id(nodo.body[0].value)
        for nodo in ast.walk(arbol)
        if isinstance(nodo, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        and nodo.body and isinstance(nodo.body[0], ast.Expr)
        and isinstance(nodo.body[0].value, ast.Constant)
    }
    excepciones = {
        "Fusion 360 (*.f3d *.f3z)": "Filtro de importación .f3d/.f3z, excluido del pedido.",
        "Leyendo el archivo de Fusion…": "Progreso de importación .f3d, excluido del pedido.",
        "No se pudo abrir el archivo de Fusion": "Error de importación .f3d, excluido del pedido.",
        "</b><br>CAD 3D paramétrico libre, inspirado en el flujo de trabajo de Fusion 360.":
            "Texto de Acerca de, excluido expresamente del pedido.",
    } if archivo == "ventana.py" else {}
    menciones = [
        (nodo.lineno, nodo.value)
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str)
        and id(nodo) not in docstrings and re.search(r"\bFusion\b", nodo.value)
        and not any(nodo.value.startswith(prefijo) for prefijo in excepciones)
    ]
    assert not menciones, (archivo, menciones)


@pytest.mark.parametrize("herramienta", ["draw_spline", "sketch_from_spec"])
def test_error_de_spline_de_control_cerrada_sin_comparaciones(herramienta):
    sesion = api.Sesion()
    assert api.llamar(sesion, "create_sketch", {})["ok"]
    spline = {"points": [[0, 0], [1, 1], [2, 0], [3, 1]], "spline_type": "control_points", "closed": True}
    argumentos = spline if herramienta == "draw_spline" else {"entities": [{"type": "spline", **spline}]}
    respuesta = api.llamar(sesion, herramienta, argumentos)
    assert not respuesta["ok"] and respuesta["error_kind"] == "INVALID_ARGUMENTS", respuesta
    mensaje = respuesta["mensaje"]
    assert "Fusion" not in mensaje
    assert "no se puede cerrar" in mensaje and "fit_points con closed=true" in mensaje
    assert "uní los extremos con una línea o arco" in mensaje


def test_error_de_clase_sin_datos_sin_comparaciones():
    with pytest.raises(geo.ErrorGeometria) as fallo:
        tolerancias.limites_rosca("acme", 1.0, 0.1, "2G")
    mensaje = str(fallo.value)
    assert "Fusion" not in mensaje
    assert "clase 2G para este tamaño" in mensaje
    assert "usá la rosca sin clase o la «auto»" in mensaje
