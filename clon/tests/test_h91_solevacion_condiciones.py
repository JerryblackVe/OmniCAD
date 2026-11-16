"""H-91: en la solevación sólida, las condiciones de borde se combinan con el carril y la línea central, y son exactas
(fijan la derivada de salida) en los pasos nuevos; cerrada y reglada dan un error claro."""
import math

import pytest
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeVertex, BRepBuilderAPI_MakeWire
from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
from OCP.gp import gp_Ax2, gp_Circ, gp_Dir, gp_Pnt

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_crear as sc
from omnicad.timeline.ops_solido import OpSolevacion

DIRECCION = {"tipo": "direccion", "angulo": 30.0}
CILINDRO = math.pi * 10 ** 2 * 30


def circulo(r, z=0.0):
    borde = BRepBuilderAPI_MakeEdge(gp_Circ(gp_Ax2(gp_Pnt(0, 0, z), gp_Dir(0, 0, 1)), r)).Edge()
    return BRepBuilderAPI_MakeWire(borde).Wire()


def seg(a, b):
    return BRepBuilderAPI_MakeEdge(gp_Pnt(*a), gp_Pnt(*b)).Edge()


def _lateral():
    """Cara lateral de un cilindro r 10 que termina en z = 0: su borde de arriba es el primer perfil (Tangente, Suave)."""
    cil = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(0, 0, -20), gp_Dir(0, 0, 1)), 10, 20).Shape()
    return next(c for c in geo.caras(cil) if geo.area(c) > 1000)


def _solevar(**kw):
    forma = sc.solevar(**kw)
    assert geo.es_valida(forma)
    return geo.volumen(forma), geo.caja_envolvente(forma)[1]


@pytest.mark.parametrize("guia, cond, volumen", [
    ("carril", DIRECCION, 14068.3), ("carril_exacta", DIRECCION, 11721.7), ("central", DIRECCION, 14603.7),
    ("carril", "tangente", 8281.3), ("carril_exacta", "tangente", 7929.5), ("central", "tangente", 8348.2),
    ("carril", "suave", 8540.8), ("carril_exacta", "suave", 8188.1), ("central", "suave", 8639.4),
])
def test_la_condicion_se_combina_con_el_carril_y_la_linea_central(guia, cond, volumen):
    """Antes: «Las condiciones de borde no se combinan con carriles, línea central…». Fusion las combina."""
    fin = 10.0 if isinstance(cond, dict) else 8.0
    kw = ({"carriles": [seg((10, 0, 0), (fin, 0, 30))]} if guia.startswith("carril")
          else {"linea_central": seg((0, 0, 0), (0, 0, 30))})
    condicion = cond if isinstance(cond, dict) else {"tipo": cond, "cara": _lateral()}
    v, _ = _solevar(secciones=[circulo(10), circulo(fin, 30)], condicion_inicio=condicion,
                    condicion_exacta=guia.endswith("exacta"), **kw)
    sin_condicion, _ = _solevar(secciones=[circulo(10), circulo(fin, 30)], **kw)
    assert v == pytest.approx(volumen, rel=0.02) and abs(v - sin_condicion) > 100     # la condición se nota


@pytest.mark.parametrize("guia, volumen", [({"carriles": [seg((10, 0, 0), (10, 0, 30))]}, 9671.1),
                                           ({"linea_central": seg((0, 0, 0), (0, 0, 30))}, 9706.6)])
def test_direccion_en_una_seccion_intermedia_con_carril_o_linea_central(guia, volumen):
    v, caja = _solevar(secciones=[circulo(10), circulo(10, 15), circulo(10, 30)], condiciones_medias={1: DIRECCION}, **guia)
    assert v == pytest.approx(volumen, rel=0.02) and caja[1] > 11                      # se abre en el medio


def test_punto_tangente_con_carril():
    punta = BRepBuilderAPI_MakeVertex(gp_Pnt(0, 0, 30)).Vertex()
    v, _ = _solevar(secciones=[circulo(10), punta], carriles=[seg((10, 0, 0), (0, 0, 30))],
                    condicion_fin={"tipo": "punto_tangente"})
    assert CILINDRO / 3 < v < CILINDRO                                                 # entre el cono y el cilindro


def test_la_condicion_exacta_fija_la_salida_y_la_receta_vieja_no_cambia():
    """Exacta: la derivada sale con la dirección pedida, sin pasar por secciones auxiliares (menos abultada). Una receta
    vieja (sin `condicion_exacta`) da lo mismo que antes; la API y la ventana crean pasos exactos."""
    aprox, caja_aprox = _solevar(secciones=[circulo(10), circulo(10, 30)], condicion_inicio=DIRECCION)
    exacta, caja_exacta = _solevar(secciones=[circulo(10), circulo(10, 30)], condicion_inicio=DIRECCION, condicion_exacta=True)
    assert aprox == pytest.approx(14156.9, rel=1e-3) and exacta == pytest.approx(11982.9, rel=1e-3)
    assert caja_exacta[0] < caja_aprox[0]
    tangente, caja = _solevar(secciones=[circulo(10), circulo(8, 30)], condicion_exacta=True,
                              condicion_inicio={"tipo": "tangente", "cara": _lateral()})
    assert caja[0] == pytest.approx(10, abs=0.01) and tangente == pytest.approx(7958.1, rel=0.02)   # sube vertical

    s = api.Sesion()
    for nombre, z in (("Base", 0), ("Tapa", 30)):
        plano = "XY" if z == 0 else api.llamar(s, "create_construction_plane", {"plane": "XY", "offset": z})["result"]["plane"]["id"]
        assert api.llamar(s, "create_sketch", {"plane": plano, "name": nombre})["ok"]
        assert api.llamar(s, "draw_circle", {"radius": 10, "sketch": nombre})["ok"]
    r = api.llamar(s, "loft", {"sketches": ["Base", "Tapa"], "start_condition": {"type": "direction", "angle": 30}})
    assert r["ok"], r
    op = next(o for o in s.doc.operaciones if isinstance(o, OpSolevacion))
    assert op.p["condicion_exacta"] is True
    (cuerpo,) = s.doc.estado_final.cuerpos.values()
    assert geo.volumen(cuerpo.forma) == pytest.approx(exacta, rel=1e-3)
    assert OpSolevacion.PARAMS["condicion_exacta"] is False                           # receta vieja: auxiliares


@pytest.mark.parametrize("kw, mensaje", [
    ({"secciones": [circulo(10), circulo(12, 15), circulo(10, 30)], "cerrada": True}, "^Cerrada: sin condición de borde"),
    ({"secciones": [circulo(10), circulo(10, 30)], "reglada": True}, "^Tramos rectos: sin condición de borde"),
])
def test_cerrada_y_reglada_con_condicion_dicen_por_que(kw, mensaje):
    with pytest.raises(geo.ErrorGeometria, match=mensaje) as e:
        sc.solevar(condicion_inicio=DIRECCION, **kw)
    assert len(str(e.value)) <= 40                                                   # regla 14: un renglón


def test_punto_tangente_con_linea_central_dice_por_que():
    punta = BRepBuilderAPI_MakeVertex(gp_Pnt(0, 0, 30)).Vertex()
    with pytest.raises(geo.ErrorGeometria, match="^Punto tangente: sin línea central") as e:
        sc.solevar([circulo(10), punta], linea_central=seg((0, 0, 0), (0, 0, 30)), condicion_fin={"tipo": "punto_tangente"})
    assert len(str(e.value)) <= 40


@pytest.mark.parametrize("vieja", [True, False])
def test_reabrir_el_paso_conserva_el_modo_de_la_receta(vieja):
    """Editar una receta vieja (aproximada) no la vuelve exacta: aceptar el diálogo sin tocar nada no cambia el volumen."""
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.crear import Solevacion
    s = api.Sesion()
    for nombre, z in (("Base", 0), ("Tapa", 30)):
        plano = "XY" if z == 0 else api.llamar(s, "create_construction_plane", {"plane": "XY", "offset": z})["result"]["plane"]["id"]
        assert api.llamar(s, "create_sketch", {"plane": plano, "name": nombre})["ok"]
        assert api.llamar(s, "draw_circle", {"radius": 10, "sketch": nombre})["ok"]
    assert api.llamar(s, "loft", {"sketches": ["Base", "Tapa"], "start_condition": {"type": "direction", "angle": 30}})["ok"]
    op = next(o for o in s.doc.operaciones if isinstance(o, OpSolevacion))
    op.p["condicion_exacta"] = not vieja
    cmd, ctx = Solevacion(), ContextoComando(s.doc, op=op)
    assert cmd.construir(cmd.desde_op(op, ctx), ctx).p["condicion_exacta"] is (not vieja)


@pytest.mark.parametrize("peso, fusion", [(0.2, 11352.4), (0.5, 12828.8), (1, 15708.3), (2, 23037.5), (5, 57588.1)])
def test_punto_tangente_da_lo_mismo_que_fusion(peso, fusion):
    """Círculo r 10 → punto a 100 mm con Punto tangente: volúmenes medidos en Fusion por E11 (2026-11-14)."""
    punta = BRepBuilderAPI_MakeVertex(gp_Pnt(0, 0, 100)).Vertex()
    v, _caja = _solevar(secciones=[circulo(10), punta], condicion_fin={"tipo": "punto_tangente", "peso": peso},
                        condicion_exacta=True)
    assert v == pytest.approx(fusion, rel=5e-4)


def test_direccion_exacta_da_lo_mismo_que_fusion():
    """Dos círculos r 10 a 60 mm con Dirección −30° / 30°: Fusion da 19644,7 mm³ (E11, 2026-11-14)."""
    v, _caja = _solevar(secciones=[circulo(10), circulo(10, 60)], condicion_inicio={"tipo": "direccion", "angulo": -30},
                        condicion_fin={"tipo": "direccion", "angulo": 30}, condicion_exacta=True)
    assert v == pytest.approx(19644.7, rel=2e-3)
