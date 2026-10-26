"""Gizmos de CONSTRUIR: Plano y Punto sobre una ruta, Plano tangente (ángulo) y Plano perpendicular (distancia)."""
import numpy as np
import pytest
from test_manipuladores import _arrastrar, _doc_caja, _doc_rectangulo, _panel, app_qt  # noqa: F401  (fixture)

from omnicad import api
from omnicad.nucleo import geometria as g, referencias as refs
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva
from omnicad.ui import manipuladores as mp
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos import CATALOGO


def _linea_del_rectangulo(doc):
    curva = next(iter(doc.estado_final.bocetos["op1"].boceto.curvas))
    return hit_desde_ref({"tipo": "curva_boceto", "boceto": "op1", "curva": curva}, doc.estado_final)


def _abrir(clave, doc, valores):
    p, visor, _ = _panel(CATALOGO[clave](), doc, valores)
    visor.vista("iso")
    p.manipuladores.actualizar()
    return p


def _arrastrar_a(p, desde, hasta):
    gm = p.manipuladores
    xy, ok = gm.pantalla([desde, hasta])
    assert ok.all()
    _arrastrar(p.visor, *xy)


@pytest.mark.parametrize("clave", ["plano_ruta", "punto_ruta"])
def test_asa_de_ruta_se_desliza_y_puede_pasar_el_final(app_qt, clave):  # noqa: F811
    doc = _doc_rectangulo()
    p = _abrir(clave, doc, {"r0": [_linea_del_rectangulo(doc)]})
    gm = p.manipuladores
    asa = next(m for m in gm.manips if isinstance(m, mp.AsaRuta))
    assert gm.valor("posicion") == 0.5 and "posicion" in gm.cajas
    final = asa.puntos_ruta[np.searchsorted(asa.ts, 1.0)]                       # el extremo de la ruta
    _arrastrar_a(p, asa.asa(gm), final)
    assert gm.valor("posicion") == pytest.approx(1.0, abs=0.03)
    _arrastrar_a(p, asa.asa(gm), asa.puntos_ruta[-1])                           # más allá del final
    assert gm.valor("posicion") > 1.15
    _arrastrar_a(p, asa.asa(gm), asa.puntos_ruta[0])                            # y antes del inicio
    assert gm.valor("posicion") < -0.15
    p._calcular_previa()
    assert p._previa_ok
    p.cancelar()


def test_teclear_la_posicion_mueve_el_asa(app_qt):  # noqa: F811
    doc = _doc_rectangulo()
    p = _abrir("plano_ruta", doc, {"r0": [_linea_del_rectangulo(doc)]})
    gm = p.manipuladores
    asa = next(m for m in gm.manips if isinstance(m, mp.AsaRuta))
    antes = asa.asa(gm).copy()
    p.set_valor("posicion", "0.9")
    despues = next(m for m in gm.manips if isinstance(m, mp.AsaRuta)).asa(gm)
    assert not np.allclose(antes, despues)
    p.cancelar()


def test_muestras_de_ruta_prolongan_recto_fuera_del_largo():
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
    from OCP.gp import gp_Pnt

    from omnicad.nucleo import construccion as cs
    arista = BRepBuilderAPI_MakeEdge(gp_Pnt(0, 0, 0), gp_Pnt(10, 0, 0)).Edge()
    pts = cs.muestras_ruta(arista, [-0.5, 0, 0.5, 1, 1.5])
    assert pts[:, 0] == pytest.approx([-5, 0, 5, 10, 15])


def _doc_cilindro():
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="cilindro", radio="10", alto="30"))
    return doc


def _cara_lateral(doc):
    forma = doc.estado_final.cuerpos["op1.c1"].forma
    cara = next(c for c in refs.subformas(forma, "cara") if "eje" in refs.firma_cara(c))
    return hit_desde_ref(refs.referencia("op1.c1", cara, caja=g.caja_envolvente(forma)), doc.estado_final)


def test_plano_tangente_gira_con_el_asa_de_angulo(app_qt):  # noqa: F811
    doc = _doc_cilindro()
    p = _abrir("plano_tangente", doc, {"r0": [_cara_lateral(doc)]})
    gm = p.manipuladores
    m = next(m for m in gm.manips if isinstance(m, mp.Angulo))
    assert m.radio == pytest.approx(10, abs=1e-6) and np.allclose(abs(m.eje), (0, 0, 1))
    objetivo = m.centro + (m.u * np.cos(np.radians(70)) + m.v * np.sin(np.radians(70))) * m._r(gm)
    _arrastrar_a(p, m.asa(gm), objetivo)
    assert gm.valor("angulo") == pytest.approx(70, abs=2)
    p._calcular_previa()
    assert p._previa_ok
    p.cancelar()


def test_plano_perpendicular_tiene_distancia_con_flecha_y_el_plano_se_corre(app_qt):  # noqa: F811
    doc = _doc_caja()
    cara = next(c for c in refs.subformas(doc.estado_final.cuerpos["op1.c1"].forma, "cara")
                if np.allclose(g.centro_masa(c, True), (10, 10, 20)))
    forma = doc.estado_final.cuerpos["op1.c1"].forma
    hit_cara = hit_desde_ref(refs.referencia("op1.c1", cara, caja=g.caja_envolvente(forma)), doc.estado_final)
    vertice = refs.subformas(forma, "vertice")[0]
    hit_v = hit_desde_ref(refs.referencia("op1.c1", vertice, caja=g.caja_envolvente(forma)), doc.estado_final)
    p = _abrir("plano_perpendicular", doc, {"r0": [hit_cara], "r1": [hit_v]})
    gm = p.manipuladores
    flecha = next(m for m in gm.manips if isinstance(m, mp.Flecha))
    assert flecha.clave == "desfase"
    a, b = flecha.puntos(gm)
    _arrastrar_a(p, (a + b) / 2, (a + b) / 2 + flecha.direccion * 6)
    assert gm.valor("desfase") == pytest.approx(6, abs=0.5)
    p._calcular_previa()
    assert p._previa_ok
    p.cancelar()


def test_api_distance_corre_el_plano_perpendicular_y_sin_ella_nada_cambia():
    s = api.Sesion()
    api.llamar(s, "create_box", {"length": 20, "width": 20, "height": 20})
    base = api.llamar(s, "create_construction_plane", {"type": "perpendicular", "references": [">Z", [10, 10, 20]]})
    corrido = api.llamar(s, "create_construction_plane", {"type": "perpendicular", "references": [">Z", [10, 10, 20]],
                                                          "distance": 5})
    assert base["ok"] and corrido["ok"]
    o0, o1 = (np.array(r["result"]["origin"], float) for r in (base, corrido))
    assert np.linalg.norm(o1 - o0) == pytest.approx(5)
