# -*- coding: utf-8 -*-
"""Cobertura del comando buscar_similares según «Find similar components» de Fusion.

Fuente: docs/fusion_docs/contenido/fusion-model/find-similar-components-18d9e2e11a4.md.
Las etiquetas duplicate/highly_similar/similar son las que muestra Fusion; sus umbrales numéricos son propios de OmniCAD.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad import api
from omnicad.ui.comando import ContextoComando
from omnicad.ui.comandos import CATALOGO


def _llamar(sesion, nombre, **args):
    resultado = api.llamar(sesion, nombre, args)
    assert resultado["ok"], resultado
    return resultado["result"]


def _escena():
    sesion = api.Sesion()
    _llamar(sesion, "create_box", length=20, width=10, height=5, name="A")
    _llamar(sesion, "create_box", length=20, width=10, height=5, name="B", x=50)
    _llamar(sesion, "move_body", body="B", rotate=[0, 0, 90], pivot="center")
    _llamar(sesion, "create_box", length=20.2, width=10, height=5, name="C", x=100)
    _llamar(sesion, "create_box", length=30, width=10, height=5, name="D", x=150)
    for nombre in "ABCD":
        _llamar(sesion, "create_component", bodies=[nombre], name="Comp" + nombre)
    return sesion


def test_buscar_similares_muestra_dos_coincidencias_numericas_ordenadas():
    """La caja de 20×10×5 tiene una copia girada y otra 1 % más larga; la de 30 mm queda afuera."""
    sesion = _escena()
    comando = CATALOGO["buscar_similares"]()
    valores = {"cuerpo": [{"ref": {"tipo": "cuerpo", "cuerpo": sesion.cuerpo("A").id}}]}

    texto = comando._resultado(valores, ContextoComando(sesion.doc))

    assert texto.splitlines() == ["CompB: duplicado", "CompC: muy similar"]
    assert len(texto.splitlines()) == 2


@pytest.mark.xfail(reason="B-708: se acepta un componente con hijos, que Fusion no admite", strict=True)
def test_buscar_similares_rechaza_un_componente_con_hijos_como_fusion():
    """Caso borde explícito de la ayuda: el componente de origen no puede tener componentes hijos."""
    sesion = api.Sesion()
    _llamar(sesion, "create_box", length=20, width=10, height=5, name="A")
    _llamar(sesion, "create_component", bodies=["A"], name="Padre")
    _llamar(sesion, "create_component", name="Hijo", parent="Padre")

    resultado = api.llamar(sesion, "find_similar_components", {"component": "Padre"})

    assert not resultado["ok"], resultado
    assert resultado["error_kind"] == "INVALID_ARGUMENTS"
    assert "hijos" in resultado["mensaje"]
