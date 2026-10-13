# -*- coding: utf-8 -*-
"""Apoyar en el plano (Z = 0): operación del timeline, herramienta drop_to_plane y comando de la interfaz."""
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


def ok(r):
    assert r["ok"], r
    return r["result"]


def _zmin(s, cuerpo=None):
    cs = s.doc.estado_final.cuerpos
    ids = [cuerpo] if cuerpo else list(cs)
    return min(geo.caja_envolvente(cs[i].forma)[0][2] for i in ids)


@pytest.fixture
def dos_cajas():
    s = api.Sesion()
    a = ok(api.llamar(s, "create_box", {"width": 10, "length": 10, "height": 10}))
    b = ok(api.llamar(s, "create_box", {"width": 10, "length": 10, "height": 20}))
    ida, idb = a["bodies_created"][0]["id"], b["bodies_created"][0]["id"]
    ok(api.llamar(s, "move_body", {"body": ida, "translate": [0, 0, -30]}))      # bajo el plano
    ok(api.llamar(s, "move_body", {"body": idb, "translate": [30, 0, 15]}))      # flotando
    return s, ida, idb


def test_apoya_un_cuerpo_que_quedo_bajo_el_plano(dos_cajas):
    s, ida, idb = dos_cajas
    assert _zmin(s, ida) == pytest.approx(-30)
    r = ok(api.llamar(s, "drop_to_plane", {"body": ida}))
    assert r["z_min"] == {"before": -30.0, "after": 0.0}
    assert _zmin(s, ida) == pytest.approx(0.0, abs=1e-6) and _zmin(s, idb) == pytest.approx(15)   # el otro no se toca


def test_juntos_conserva_la_posicion_relativa_y_separados_no(dos_cajas):
    s, ida, idb = dos_cajas
    ok(api.llamar(s, "drop_to_plane", {}))                       # todos, juntos: el más bajo (-30) toca Z = 0
    assert _zmin(s, ida) == pytest.approx(0, abs=1e-6) and _zmin(s, idb) == pytest.approx(45)
    ok(api.llamar(s, "drop_to_plane", {"keep_relative": False}))   # cada uno por su cuenta
    assert _zmin(s, idb) == pytest.approx(0, abs=1e-6)


def test_se_recalcula_con_el_modelo(dos_cajas):
    s, ida, _ = dos_cajas
    ok(api.llamar(s, "drop_to_plane", {"body": ida}))
    ok(api.llamar(s, "undo", {}))
    assert _zmin(s, ida) == pytest.approx(-30)


def test_sin_cuerpos_da_error():
    r = api.llamar(api.Sesion(), "drop_to_plane", {})
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS"


def test_guardar_y_reabrir_un_proyecto_con_apoyar(dos_cajas, tmp_path):
    """Bug: «Tipo de operación desconocido: apoyar» al abrir (la operación no estaba registrada)."""
    s, ida, _ = dos_cajas
    ok(api.llamar(s, "drop_to_plane", {"body": ida}))
    ruta = str(tmp_path / "apoyado.omnicad")
    ok(api.llamar(s, "save_document", {"path": ruta}))
    s2 = api.Sesion()
    ok(api.llamar(s2, "open_document", {"path": ruta}))
    assert any(op.TIPO == "apoyar" for op in s2.doc.operaciones)
    assert _zmin(s2, ida) == pytest.approx(0.0, abs=1e-6)


def test_toda_operacion_con_tipo_esta_registrada():
    """Una operación que no se registra se crea y se ve, pero el proyecto guardado no se vuelve a abrir."""
    import importlib
    import pkgutil

    import omnicad.timeline as tl
    from omnicad.timeline.operaciones import TIPOS_OPERACION, Operacion
    for m in pkgutil.iter_modules(tl.__path__):
        importlib.import_module(f"omnicad.timeline.{m.name}")

    def todas(c):
        for h in c.__subclasses__():
            yield h
            yield from todas(h)
    faltan = sorted({f"{c.__module__}.{c.__name__}" for c in todas(Operacion)
                     if "TIPO" in vars(c) and c.TIPO and TIPOS_OPERACION.get(c.TIPO) is not c})
    assert not faltan, f"sin registrar_operacion: {faltan}"
