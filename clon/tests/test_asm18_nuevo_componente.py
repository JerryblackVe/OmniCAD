# -*- coding: utf-8 -*-
"""ASM-18: Nuevo componente con las opciones de Fusion: vacío, «A partir de cuerpos» y nombre (Padre ya estaba)."""
import pytest

from omnicad import api


def _ll(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], (nombre, args, r)
    return r["result"]


def _falla(s, nombre, kind, **args):
    r = api.llamar(s, nombre, args)
    assert not r["ok"] and r["error_kind"] == kind, r
    return r


@pytest.fixture
def tres():
    s = api.Sesion()
    ids = [_ll(s, "create_box", length=10, width=10, height=10, x=40 * i, name=n)["bodies_created"][0]["id"]
           for i, n in enumerate(("Base", "Tapa", "Eje"))]
    return s, ids


def test_un_componente_vacio_se_crea_sin_cuerpos_y_acepta_nombre_y_padre(tres):
    s, (base, *_resto) = tres
    r = _ll(s, "create_component", name="Carcasa")
    assert r["component"]["name"] == "Carcasa" and r["component"]["bodies"] == []
    hijo = _ll(s, "create_component", name="Tornillos", parent="Carcasa")["component"]
    assert hijo["parent"] == r["component"]["id"] and hijo["bodies"] == []
    _ll(s, "create_component", bodies=[base], name="ConBase", parent="Carcasa")                # y se llena igual que antes
    assert [c["name"] for c in _ll(s, "get_assembly")["components"] if c["bodies"]] == ["ConBase"]
    _ll(s, "undo")
    _ll(s, "undo")
    assert [c["name"] for c in _ll(s, "get_assembly")["components"]] == ["Carcasa"]


def test_a_partir_de_cuerpos_crea_un_componente_por_cuerpo_en_un_solo_deshacer(tres):
    s, (base, tapa, eje) = tres
    r = _ll(s, "create_component", bodies=[base, tapa, eje], from_bodies=True)
    assert [c["name"] for c in r["components"]] == ["Base", "Tapa", "Eje"]                    # cada uno con el nombre de su cuerpo
    assert [[b["name"] for b in c["bodies"]] for c in r["components"]] == [["Base"], ["Tapa"], ["Eje"]]
    _ll(s, "undo")                                                                          # un solo paso de deshacer para los tres
    assert _ll(s, "get_assembly")["components"] == []
    r = _ll(s, "create_component", bodies=[base, tapa], from_bodies=True, name="Pieza", grounded=True)
    assert [c["name"] for c in r["components"]] == ["Pieza1", "Pieza2"] and all(c["grounded"] for c in r["components"])


def test_a_partir_de_cuerpos_sin_cuerpos_y_nombre_repetido_fallan_sin_tocar_nada(tres):
    s, (base, *_resto) = tres
    _falla(s, "create_component", "INVALID_ARGUMENTS", from_bodies=True)
    _ll(s, "create_component", name="Uno")
    _falla(s, "create_component", "INVALID_ARGUMENTS", name="Uno")
    assert [c["name"] for c in _ll(s, "get_assembly")["components"]] == ["Uno"]


def test_el_comando_crea_un_componente_vacio_con_nombre_y_rechaza_un_nombre_usado(tres):
    from omnicad.ui.comando import ContextoComando, ErrorComando
    from omnicad.ui.comandos.ensamblar import NuevoComponente
    s, (base, *_resto) = tres
    ctx = ContextoComando(s.doc)
    campos = {c.clave: c for c in NuevoComponente().campos(ctx)}
    assert campos["nombre"].defecto == "" and campos["cuerpos"].minimo == 0 and campos["nombre"].visible_si({}) is True
    op = NuevoComponente().construir({"cuerpos": [], "fijo": False, "padre": "", "nombre": "  Carcasa "}, ctx)
    assert op.nombre == "Carcasa" and op.p["cuerpos"] == [] and s.doc.agregar(op).estado == "ok"
    assert s.doc.estado_final.componentes[op.id]["nombre"] == "Carcasa"
    vacio = NuevoComponente().construir({"cuerpos": [], "fijo": False, "padre": ""}, ctx)         # sin nombre: Componente<n>
    assert vacio.nombre == "Componente1"
    with pytest.raises(ErrorComando, match="Ya hay un paso llamado"):
        NuevoComponente().construir({"cuerpos": [], "fijo": False, "padre": "", "nombre": "Carcasa"}, ctx)
    editando = ContextoComando(s.doc, op=op)                                                       # al editar, el nombre no se ofrece
    assert {c.clave: c for c in NuevoComponente().campos(editando)}["nombre"].visible_si({}) is False
