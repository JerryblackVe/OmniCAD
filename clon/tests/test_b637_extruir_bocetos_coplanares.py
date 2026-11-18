# -*- coding: utf-8 -*-
"""B-637: Extruir acepta perfiles de bocetos distintos si son coplanares (Fusion › Extrude › Profiles:
«Select coplanar sketch profiles»). No pide que sean del mismo boceto; si los planos no coinciden, lo dice claro."""
import pytest

from omnicad import api
from omnicad.api.herramientas_boceto import boceto_activo, seleccionar_perfiles
from omnicad.nucleo import geometria as geo
from omnicad.timeline.operaciones import OpExtrusion
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos.comunes import perfiles_a_params


def _llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], (nombre, args, r)
    return r["result"]


def _ref(s, nombre):
    """Referencia guardada de un perfil, con el boceto al que pertenece."""
    sop, br = boceto_activo(s, s.paso(nombre).id)
    perfil = seleccionar_perfiles(br, sop, 0)[0]
    return dict(OpExtrusion.referencia_perfil(perfil), boceto=sop.id)


def _sesion(plano_b="XY"):
    s = api.Sesion()
    _llamar(s, "create_sketch", name="A", plane="XY")
    _llamar(s, "draw_rectangle", sketch="A", x1=0, y1=0, x2=20, y2=10)          # 200 mm²
    _llamar(s, "create_sketch", name="B", plane=plano_b)
    _llamar(s, "draw_rectangle", sketch="B", x1=10, y1=0, x2=30, y2=10)         # 200 mm², se pisan 100
    return s


def test_dos_bocetos_coplanares_dan_un_cuerpo():
    s = _sesion()
    op = OpExtrusion(s.doc.nuevo_id(), "Extrusion", boceto=s.paso("A").id,
                     perfiles=[_ref(s, "A"), _ref(s, "B")], distancia="5 mm")
    s.doc.agregar(op)
    cerrados = [c for c in s.doc.estado_final.cuerpos.values() if getattr(c, "tipo", "solido") == "solido"]
    assert len(cerrados) == 1                                                   # 300 mm² × 5 mm
    assert geo.es_valida(cerrados[0].forma)
    assert geo.volumen_exacto(cerrados[0].forma) == pytest.approx(1500.0)


def test_bocetos_de_planos_distintos_da_error_claro():
    s = _sesion("XZ")                                                           # B en otro plano
    op = OpExtrusion(s.doc.nuevo_id(), "Extrusion", boceto=s.paso("A").id,
                     perfiles=[_ref(s, "A"), _ref(s, "B")], distancia="5 mm")
    resultado = s.doc.agregar(op)
    assert resultado.estado == "error"
    assert "Los perfiles tienen que estar en el mismo plano" in resultado.mensaje
    assert not [c for c in s.doc.estado_final.cuerpos.values() if getattr(c, "tipo", "solido") == "solido"]


def test_el_panel_acepta_perfiles_de_dos_bocetos_coplanares():
    """La causa del mensaje viejo «Los perfiles deben ser del mismo boceto» está en preparar los parámetros."""
    s = _sesion()
    estado = s.doc.estado_final
    hits = [hit_desde_ref({"tipo": "perfil", **_ref(s, nombre)}, estado) for nombre in ("A", "B")]
    boceto, perfiles, caras = perfiles_a_params(hits)
    assert not caras and len(perfiles) == 2
    assert {p["boceto"] for p in perfiles} == {s.paso("A").id, s.paso("B").id}
    assert boceto == s.paso("A").id
