# -*- coding: utf-8 -*-
"""PREP del comando ENSAMBLAR › Anclar / desanclar componente (clave `anclar_componente`) contra la ayuda de Fusion.

Según `docs/fusion_docs/contenido/fusion-assemble/pin-2da901cfd02.md` y `pin-a-component-61fd666cb8f.md`: Pin fija el
componente en su ubicación actual (no lo devuelve al origen, como Ground To Parent), crea una feature en el timeline y
una unión no puede moverlo; Unpin crea otra feature y lo libera. No cambia código de la app: fija lo que ya hace y avisa
si deja de hacerlo.
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


def _documento_con_componentes():
    """Base fija y bloque componente a 300 mm sobre X, todavía sin anclar."""
    s = api.Sesion()
    base = llamar(s, "create_box", length=100, width=100, height=10)["bodies_created"][0]["id"]
    bloque = llamar(s, "create_box", length=10, width=10, height=10, x=300)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[base], name="Base", grounded=True)
    llamar(s, "create_component", bodies=[bloque], name="Bloque")
    return s, base, bloque


def _anclar(s, cuerpo, anclado):
    """Ejecuta el comando de interfaz AnclarComponente como lo arma el panel: selección + casilla Anclado."""
    from omnicad.ui.comando import ContextoComando, hit_desde_ref
    from omnicad.ui.comandos.ensamblar import AnclarComponente

    doc = s.doc
    ctx = ContextoComando(doc)
    cmd = AnclarComponente()
    valores = {c.clave: c.defecto for c in cmd.campos(ctx)}
    valores.update(cuerpos=[hit_desde_ref({"tipo": "cuerpo", "cuerpo": cuerpo}, doc.estado_final)], anclado=anclado)
    op = cmd.construir(valores, ctx)
    assert doc.agregar(op).estado == "ok"
    return op


def test_anclar_componente_fija_la_posicion_numerica_y_la_union_no_lo_mueve():
    """Fusion: Pin fija donde está (no vuelve al origen como Ground) y crea una feature en el timeline."""
    s, base, bloque = _documento_con_componentes()
    assert centro(s, bloque) == pytest.approx([300, 0, 5], abs=1e-4)

    op = _anclar(s, bloque, True)
    assert op.p["anclado"] is True
    assert s.doc.estado_final.componentes[op.p["componente"]]["anclado"] is True
    assert centro(s, bloque) == pytest.approx([300, 0, 5], abs=1e-4)
    assert [p["type"] for p in llamar(s, "get_timeline")["steps"]].count("anclar") == 1

    r = api.llamar(s, "create_joint", {"origin1": "<Z", "body1": bloque, "origin2": ">Z", "body2": base})
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS" and "fijo" in r["mensaje"]
    assert centro(s, bloque) == pytest.approx([300, 0, 5], abs=1e-4)


def test_desanclar_via_comando_libera_el_componente_y_deja_otro_paso():
    """Fusion: Unpin crea otra feature en el timeline y el componente vuelve a poder moverse con una unión."""
    s, base, bloque = _documento_con_componentes()
    _anclar(s, bloque, True)

    op = _anclar(s, bloque, False)
    assert op.p["anclado"] is False
    assert op.nombre == "Desanclar2"
    assert s.doc.estado_final.componentes[op.p["componente"]]["anclado"] is False
    assert [p["type"] for p in llamar(s, "get_timeline")["steps"]].count("anclar") == 2

    r = api.llamar(s, "create_joint", {"origin1": "<Z", "body1": bloque, "origin2": ">Z", "body2": base})
    assert r["ok"], r
    assert centro(s, bloque) == pytest.approx([0, 0, 15], abs=1e-4)
