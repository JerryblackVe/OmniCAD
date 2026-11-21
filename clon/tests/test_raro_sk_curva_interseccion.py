# -*- coding: utf-8 -*-
"""Valores raros en cada campo del diálogo «sk_curva_interseccion» (Intersection Curve):
`curvas` y `caras` (en la herramienta equivalente, `curves` y `faces`). La ayuda de Fusion
(`docs/fusion_docs`: `intersection-curve` y `reference-intersection-curve-dialog`) fija que el
diálogo toma geometría de boceto y caras/curvas donde cortar: son selecciones, no números libres.

Cada campo se prueba vacío, 0, negativo, enorme, con unidades y con expresión. Ningún valor puede
cerrar la app (la llamada no tumba el proceso), dejar el boceto roto (sigue resoluble y sin curvas
3D nuevas) ni devolver un mensaje de más de un renglón. Los valores inválidos se rechazan con un
`error_kind` estable."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad import api  # noqa: E402


def _llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert isinstance(r, dict) and "ok" in r, (nombre, r)   # api.llamar nunca lanza: no cierra la app
    return r


def _sesion():
    """Caja + boceto «Fuente» con un círculo + boceto «Destino» vacío donde caen las curvas."""
    s = api.Sesion()
    _llamar(s, "create_box", length=40, width=40, height=10)
    _llamar(s, "create_sketch", plane="XY", name="Fuente")
    curva = _llamar(s, "draw_circle", center_x=0, center_y=0, radius=5)["result"]["entities"][0]["id"]
    _llamar(s, "create_sketch", plane="XY", name="Destino")
    return s, {"sketch": "Fuente", "curve": curva}


def _validos(curva):
    """Los otros dos campos quedan válidos para que el fallo sea atribuible al campo probado."""
    return {"faces": [">Z"], "curves": [curva], "sketch": "Destino"}


# Los dos campos del diálogo y su argumento en la API (test_comandos.py verifica que diálogo y MCP
# construyen el mismo origen).
CAMPOS = [pytest.param("curvas", "curves", id="curvas"),
          pytest.param("caras", "faces", id="caras")]

VALORES = [
    pytest.param([], id="vacio"),
    pytest.param([0], id="cero"),
    pytest.param([-1], id="negativo"),
    pytest.param([10**9], id="enorme"),
    pytest.param(["20 mm"], id="unidades"),
    pytest.param(["1+1"], id="expresion"),
]


def test_el_dialogo_tiene_solo_esos_dos_campos():
    """Si el diálogo gana un campo nuevo, este barrido tiene que cubrirlo también."""
    from omnicad.ui.comandos import CATALOGO

    cmd = CATALOGO["sk_curva_interseccion"]()
    assert {c.clave for c in cmd.campos(None)} == {"curvas", "caras"}


@pytest.mark.parametrize("campo,arg", CAMPOS)
@pytest.mark.parametrize("valor", VALORES)
def test_campo_raro_no_cierra_app_ni_deja_boceto_roto(campo, arg, valor):
    s, curva = _sesion()
    args = _validos(curva)
    args[arg] = valor
    pasos = len(_llamar(s, "get_timeline")["result"]["steps"])

    r = _llamar(s, "intersect_curves", **args)

    # Sigue vivo: la sesión responde y no se agregó ningún paso al timeline.
    assert len(_llamar(s, "get_timeline")["result"]["steps"]) == pasos, (campo, valor, r)
    # El boceto no quedó roto: sigue resoluble y ningún valor raro dibujó curvas 3D.
    g = _llamar(s, "get_sketch", sketch="Destino")
    assert g["ok"] and g["result"]["status"] != "error", (campo, valor, g)
    assert not g["result"].get("entities_3d"), (campo, valor, g)

    if r["ok"]:
        # Un valor que se aceptara tiene que dibujar curvas de verdad, no quedar en silencio.
        assert r["result"]["entities"], (campo, valor, r)
        return
    mensaje = r.get("mensaje")
    assert isinstance(mensaje, str) and mensaje, (campo, valor, r)
    assert "\n" not in mensaje and "\r" not in mensaje, (campo, valor, mensaje)
    assert r.get("error_kind"), (campo, valor, r)


def test_valores_validos_si_dibujan_la_curva():
    """Control: con valores normales la herramienta sí crea la curva; el barrido no rechaza todo por azar."""
    s, curva = _sesion()
    r = _llamar(s, "intersect_curves", **_validos(curva))
    assert r["ok"] and r["result"]["entities"], r
    g = _llamar(s, "get_sketch", sketch="Destino")
    assert g["ok"] and g["result"].get("entities_3d"), g
