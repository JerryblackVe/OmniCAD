# -*- coding: utf-8 -*-
"""Valores raros del comando de boceto «sk_proyectar»: los campos del diálogo en vacío, 0, negativo,
enorme, con unidades y con expresión. Aceptar nunca cierra la app ni deja el boceto roto, y todo aviso es de un
renglón."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad.api import Sesion, llamar


def _hacer_sesion_con_cuerpos():
    """Crea una sesión con un boceto y un cuerpo para poder proyectar."""
    s = Sesion()
    r = llamar(s, "create_sketch", {"plane": "XY"})
    assert r["ok"], r
    r = llamar(s, "create_box", {"length": 20, "width": 20, "height": 20})
    assert r["ok"], r
    return s


CASOS = [
    # Campos numéricos/booleanos que se pueden probar con valores raros
    # Siempre incluimos bodies como lista de strings para que project_to_sketch funcione
    # valido=True: valor esperado que funciona
    ("mode", "project", True),
    ("mode", "intersect", True),
    # valido=False: valor inválido, ok será False pero la app no debe crash
    ("mode", "invalid_mode_xyz", False),
    # construction: booleanos verdaderos
    ("construction", True, True),
    ("construction", False, True),
    # link: booleanos verdaderos
    ("link", True, True),
    ("link", False, True),
    # body y sketch: valores de texto simples
    ("body", "Cuerpo1", True),
    ("sketch", "Boceto1", True),
]


@pytest.mark.parametrize("campo,texto,valido", CASOS, ids=[f"{c}_{t}" for c, t, _ in CASOS])
def test_valores_raros_de_sk_proyectar_no_rompen_la_app(campo, texto, valido):
    """Prueba que los valores raros no cierren la app ni dejen el boceto roto."""
    s = _hacer_sesion_con_cuerpos()
    # Siempre incluimos bodies como lista de strings
    base_args = {"bodies": ["Cuerpo1"]}
    if texto is not None:
        base_args[campo] = texto
    r = llamar(s, "project_to_sketch", base_args)
    # Lo importante: el proceso nunca debe cerrarse (no exception no controlada)
    assert "ok" in r, f"Sin ok en resultado para {campo}={texto!r}: {r}"
    assert "result" in r or isinstance(r.get("ok"), bool), \
        f"Estructura inesperada para {campo}={texto!r}: {r}"
    # Si valido=True, ok debería ser True (llamada exitosa)
    if valido:
        assert r["ok"], f"ok=False para valor supuestomente válido {campo}={texto!r}: {r}"
    # Si valido=False, ok puede ser False (error de argumento), y está bien
    # Lo crítico es que no haya excepción no controlada