# -*- coding: utf-8 -*-
"""PREP del comando ENSAMBLAR › Fijar / liberar componente (clave `fijar_componente`) contra la ayuda de Fusion.

Según `docs/fusion_docs/contenido/fusion-assemble/ground-and-unground-components-4f6dfb32c22.md` y
`ground-to-parent-51e769f75a1.md`: Ground fija el componente y una unión no puede moverlo (si es el primero elegido
al crearla, Fusion lo libera); Unground lo devuelve a estar sujeto a las uniones. Solo se puede fijar un componente.
No cambia código de la app: fija lo que ya hace y avisa si deja de hacerlo.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad import api
from omnicad.nucleo import geometria as g


def llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def centro(s, cid):
    caja = [round(v, 4) + 0.0 for p in g.caja_envolvente(s.cuerpo(cid).forma) for v in p]
    return [(caja[i] + caja[i + 3]) / 2 for i in range(3)]


def grounded(s, nombre):
    return next(c["grounded"] for c in llamar(s, "get_assembly")["components"] if c["name"] == nombre)


def _documento_con_componentes():
    """Base fija en el origen y bloque componente a 300 mm sobre X, todavía sin fijar."""
    s = api.Sesion()
    base = llamar(s, "create_box", length=100, width=100, height=10)["bodies_created"][0]["id"]
    bloque = llamar(s, "create_box", length=10, width=10, height=10, x=300)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[base], name="Base", grounded=True)
    llamar(s, "create_component", bodies=[bloque], name="Bloque")
    return s, base, bloque


def _fijar(s, cuerpo):
    """Ejecuta el comando de interfaz FijarComponente como lo arma el panel: selección de un cuerpo."""
    from omnicad.ui.comando import ContextoComando, hit_desde_ref
    from omnicad.ui.comandos.ensamblar import FijarComponente

    ctx = ContextoComando(s.doc)
    FijarComponente().aplicar({"cuerpos": [hit_desde_ref({"tipo": "cuerpo", "cuerpo": cuerpo}, ctx.estado)]}, ctx)


def test_fijar_componente_fija_la_posicion_numerica_y_la_union_no_lo_mueve():
    """Fusion: Ground mantiene al componente donde está; al liberarlo, la unión lo mueve a la base."""
    s, base, bloque = _documento_con_componentes()
    assert centro(s, bloque) == pytest.approx([300, 0, 5], abs=1e-4)
    assert grounded(s, "Bloque") is False

    _fijar(s, bloque)
    assert grounded(s, "Bloque") is True
    assert centro(s, bloque) == pytest.approx([300, 0, 5], abs=1e-4)

    union = {"origin1": "<Z", "body1": bloque, "origin2": ">Z", "body2": base}
    r = api.llamar(s, "create_joint", union)
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS" and "fijo" in r["mensaje"]
    assert centro(s, bloque) == pytest.approx([300, 0, 5], abs=1e-4)

    _fijar(s, bloque)
    assert grounded(s, "Bloque") is False
    llamar(s, "create_joint", **union)
    assert centro(s, bloque) == pytest.approx([0, 0, 15], abs=1e-4)


def test_fijar_componente_borde_cuerpo_sin_componente_se_rechaza():
    """Fusion: solo se puede fijar un componente; un cuerpo suelto no tiene ese comando."""
    from omnicad.ui.comando import ContextoComando, ErrorComando, hit_desde_ref
    from omnicad.ui.comandos.ensamblar import FijarComponente

    s, _base, _bloque = _documento_con_componentes()
    suelto = llamar(s, "create_box", length=5, width=5, height=5, x=500)["bodies_created"][0]["id"]
    antes = len(s.doc.operaciones)
    ctx = ContextoComando(s.doc)
    with pytest.raises(ErrorComando, match="no está en un componente"):
        FijarComponente().aplicar({"cuerpos": [hit_desde_ref({"tipo": "cuerpo", "cuerpo": suelto}, ctx.estado)]}, ctx)
    assert len(s.doc.operaciones) == antes
