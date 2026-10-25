"""SOL-22: retícula volumétrica (barras cross/x_cell como sólido; gyroid y Schwarz como malla)."""
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import reticula


def llamar(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"], r
    return r["result"]


def _cubo(lado=20):
    s = api.Sesion()
    llamar(s, "create_box", length=lado, width=lado, height=lado, name="Cubo", anchor="corner")
    return s


def _cuerpo(s):
    (c,) = s.doc.estado_final.cuerpos.values()
    return c


@pytest.mark.parametrize("forma", ["cross", "x_cell"])
def test_barras_dan_la_solidez_pedida(forma):
    s = _cubo()
    llamar(s, "create_volumetric_lattice", cell_shape=forma, cell_size=10, solidity=20)
    c = _cuerpo(s)
    assert c.tipo == "solido" and geo.es_valida(c.forma)
    assert geo.volumen(c.forma) / 8000 == pytest.approx(0.20, abs=0.03)


@pytest.mark.parametrize("forma", ["gyroid", "schwarz_p", "schwarz_d"])
def test_superficies_minimas_quedan_como_malla(forma):
    s = _cubo()
    llamar(s, "create_volumetric_lattice", cell_shape=forma, cell_size=10, solidity=30, resolution=16)
    c = _cuerpo(s)
    assert c.tipo == "malla" and len(c.forma.caras) > 100 and c.forma.es_cerrada()
    assert c.forma.volumen() / 8000 == pytest.approx(0.30, abs=0.06)               # la grilla afina las hojas delgadas


def test_no_uniforme_y_cuerpo_curvo():
    s = api.Sesion()
    llamar(s, "create_cylinder", radius=12, height=20, name="Cil")
    llamar(s, "create_volumetric_lattice", cell_shape="gyroid", cell_size=8, cell_size_y=10, cell_size_z=12, solidity=40)
    c = _cuerpo(s)
    assert c.tipo == "malla"
    volumen_cilindro = 3.14159265 * 144 * 20
    assert 0.25 < c.forma.volumen() / volumen_cilindro < 0.55


def test_deshacer_devuelve_el_cuerpo():
    s = _cubo()
    llamar(s, "create_volumetric_lattice", cell_shape="gyroid", cell_size=10, solidity=30)
    llamar(s, "undo")
    assert _cuerpo(s).tipo == "solido" and geo.volumen(_cuerpo(s).forma) == pytest.approx(8000)


def test_errores():
    s = _cubo()
    for args in ({"solidity": 0}, {"solidity": 100}, {"cell_size": 0}, {"resolution": 2}, {"cell_size": 0.2, "cell_shape": "cross"},
                 {"cell_shape": "no existe"}, {"cell_shape": "custom"}, {"cell_shape": "custom", "custom_bars": [[0, 0, 0, 2, 1, 1]]},
                 {"solidity_end": 50}, {"offset_solidity": 150}, {"cell_rotation": [1, 2]}):
        assert not api.llamar(s, "create_volumetric_lattice", args)["ok"], args
    assert not api.llamar(api.Sesion(), "create_volumetric_lattice", {})["ok"]


def _vertice(s, punto):
    """Índice (desde 1) del vértice del cubo en `punto`."""
    from omnicad.nucleo import referencias
    vs = referencias.subformas(_cuerpo(s).forma, "vertice")
    return 1 + next(i for i, v in enumerate(vs) if sum(abs(a - b) for a, b in zip(referencias.punto_de_vertice(v), punto, strict=True)) < 1e-6)


def _volumen_en(forma, x0, x1):
    return geo.volumen(geo.booleano(forma, geo.caja(x1 - x0, 20, 20, (x0, 0, 0)), "intersecar"))


@pytest.mark.parametrize("forma, extra", [("x_cell_25d", {}), ("custom", {"custom_bars": [[0, 0, 0, 1, 0, 0], [0, 0, 0, 0, 1, 0],
                                                                                         [0, 0, 0, 0, 0, 1]]})])
def test_celda_25d_y_a_medida(forma, extra):
    s = _cubo()
    llamar(s, "create_volumetric_lattice", cell_shape=forma, cell_size=10, solidity=20, cell_offset=[5, 5, 5], **extra)
    c = _cuerpo(s)
    assert c.tipo == "solido" and geo.es_valida(c.forma)
    assert geo.volumen(c.forma) / 8000 == pytest.approx(0.20, abs=0.03)
    if forma == "x_cell_25d":                                                      # paredes de alto completo: corte en Z igual
        (x0, y0, z0), (x1, y1, z1) = geo.caja_envolvente(c.forma)
        assert z1 - z0 == pytest.approx(20)


def test_solidez_en_gradiente_por_dos_puntos():
    s = _cubo()
    ruta = [{"body": _cuerpo(s).id, "vertex": _vertice(s, (0, 0, 0))}, {"body": _cuerpo(s).id, "vertex": _vertice(s, (20, 0, 0))}]
    llamar(s, "create_volumetric_lattice", cell_shape="cross", cell_size=10, solidity=10, solidity_end=40, gradient_path=ruta)
    c = _cuerpo(s)
    assert c.tipo == "solido" and geo.es_valida(c.forma)
    izquierda, derecha = _volumen_en(c.forma, 0, 10), _volumen_en(c.forma, 10, 20)
    assert derecha > 1.5 * izquierda                                                 # más material hacia el final de la ruta
    assert geo.volumen(c.forma) / 8000 == pytest.approx(0.25, abs=0.06)


def test_solidez_en_gradiente_por_una_arista():
    """La ruta es la arista vertical x = y = 0 (de punta a punta: los extremos dan el sentido de la arista)."""
    import numpy as np
    from omnicad.nucleo import referencias
    from omnicad.timeline.ops_solido import OpReticulaVolumetrica
    s = _cubo()
    c = _cuerpo(s)
    arista = next(a for a in referencias.subformas(c.forma, "arista")
                  if np.allclose(geo.polilinea_arista(a)[:, :2], 0, atol=1e-6))
    inicio = geo.polilinea_arista(arista)[0][2]
    op = OpReticulaVolumetrica(s.doc.nuevo_id(), cuerpo=c.id, forma_celda="cross", tamano="10 mm", solidez="10",
                               solidez_final="40", ruta=[referencias.referencia(c.id, arista, c.forma)])
    s.doc.agregar(op)
    assert s.doc.resultados[-1].estado == "ok", s.doc.resultados[-1].mensaje
    forma = _cuerpo(s).forma
    abajo, arriba = (geo.volumen(geo.booleano(forma, geo.caja(20, 20, 10, (0, 0, z)), "intersecar")) for z in (0, 10))
    final, comienzo = (abajo, arriba) if inicio > 10 else (arriba, abajo)
    assert geo.es_valida(forma) and final > 1.5 * comienzo                           # más material hacia el final de la ruta


@pytest.mark.parametrize("solidez, esperado", [(100, 0.64), (0, 0.15)])
def test_zona_de_desfase_en_las_paredes(solidez, esperado):
    """Desfase de 2 mm sobre todas las caras: macizo (cáscara de 2 mm + 30 % del interior) o vacío (solo el interior)."""
    s = _cubo()
    llamar(s, "create_volumetric_lattice", cell_shape="gyroid", cell_size=8, solidity=30, offset_distance=2,
           offset_solidity=solidez, resolution=8)
    assert _cuerpo(s).forma.volumen() / 8000 == pytest.approx(esperado, abs=0.07)


def test_zona_de_desfase_con_mezcla_en_barras():
    s = _cubo()
    llamar(s, "create_volumetric_lattice", cell_shape="cross", cell_size=10, solidity=10, offset_distance=0,
           offset_blend=10, offset_solidity=40)
    c = _cuerpo(s)
    assert geo.es_valida(c.forma) and 0.10 < geo.volumen(c.forma) / 8000 < 0.40


def test_mover_y_girar_las_celdas():
    s = _cubo()
    llamar(s, "create_volumetric_lattice", cell_shape="cross", cell_size=10, solidity=20, cell_offset=[5, 5, 5])
    c = _cuerpo(s)
    assert geo.es_valida(c.forma) and geo.volumen(c.forma) / 8000 == pytest.approx(0.20, abs=0.04)
    s2 = _cubo()
    llamar(s2, "create_volumetric_lattice", cell_shape="cross", cell_size=10, solidity=20, cell_rotation=[0, 0, 45])
    c2 = _cuerpo(s2)
    assert geo.es_valida(c2.forma) and geo.volumen(c2.forma) != pytest.approx(geo.volumen(c.forma), rel=0.01)
    assert geo.volumen(c2.forma) / 8000 == pytest.approx(0.20, abs=0.06)


@pytest.mark.parametrize("forma, tipo", [("gyroid", "malla"), ("cross", "solido")])
def test_sobre_una_malla_cerrada(forma, tipo):
    s = _cubo()
    llamar(s, "tessellate", bodies=_cuerpo(s).id, keep_original=False)
    assert _cuerpo(s).tipo == "malla"
    if tipo == "malla":
        llamar(s, "create_volumetric_lattice", cell_shape=forma, cell_size=10, solidity=30, resolution=16)
    else:      # por el timeline: el informe de la API (herramientas_solido._informe) falla si una malla pasa a sólido
        from omnicad.timeline.ops_solido import OpReticulaVolumetrica
        s.doc.agregar(OpReticulaVolumetrica(s.doc.nuevo_id(), cuerpo=_cuerpo(s).id, forma_celda=forma, tamano="10 mm",
                                            solidez="30"))
        assert s.doc.resultados[-1].estado == "ok", s.doc.resultados[-1].mensaje
    c = _cuerpo(s)
    assert c.tipo == tipo and (tipo == "malla" or geo.es_valida(c.forma))
    volumen = c.forma.volumen() if tipo == "malla" else geo.volumen(c.forma)
    assert volumen / 8000 == pytest.approx(0.30, abs=0.08)


def test_borde_interpolado_no_escalonado():
    """Con una zona de desfase maciza que cubre todo, la malla es el cilindro: con una grilla de 2 mm el borde cae sobre
    la pared (r = 12) y el volumen da, en vez de los escalones de 2 mm."""
    import numpy as np
    s = api.Sesion()
    llamar(s, "create_cylinder", radius=12, height=10, name="Cil")
    llamar(s, "create_volumetric_lattice", cell_shape="gyroid", cell_size=8, solidity=30, resolution=4,
           offset_distance=100, offset_solidity=100)
    m = _cuerpo(s).forma
    assert m.es_cerrada() and m.volumen() == pytest.approx(3.14159265 * 144 * 10, rel=0.05)     # los bordes vivos se achaflanan ~h
    v = m.vertices
    pared = np.hypot(v[:, 0], v[:, 1])[np.abs(v[:, 2] - 5) < 3]
    assert len(pared) > 20 and np.abs(pared - 12).max() < 0.4


def test_receta_vieja_sin_parametros_nuevos():
    from omnicad.timeline.documento import Documento
    from omnicad.timeline.operaciones import OpPrimitiva
    from omnicad.timeline.ops_solido import OpReticulaVolumetrica
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="20", largo="20", alto="20"))
    op = OpReticulaVolumetrica(doc.nuevo_id(), cuerpo="op1.c1", forma_celda="cross", tamano="10 mm", solidez="20")
    for k in ("barras", "solidez_final", "ruta", "zonas", "desfase", "mezcla", "mover_x", "girar_z"):
        op.p.pop(k)                                                                # como la leería una receta de antes
    doc.agregar(op)
    assert doc.resultados[-1].estado == "ok", doc.resultados[-1].mensaje
    (c,) = doc.estado_final.cuerpos.values()
    assert geo.volumen(c.forma) / 8000 == pytest.approx(0.20, abs=0.03)


def test_espesor_para_es_monotono():
    assert reticula.espesor_para("gyroid", 0.2) < reticula.espesor_para("gyroid", 0.5) < reticula.espesor_para("gyroid", 0.8)


def test_dialogo_de_la_reticula():
    from PySide6.QtWidgets import QApplication
    from omnicad.timeline.documento import Documento
    from omnicad.timeline.operaciones import OpPrimitiva
    from omnicad.ui.comando import ContextoComando, ErrorComando, hit_desde_ref
    from omnicad.ui.comandos.modificar import ReticulaVolumetrica
    QApplication.instance() or QApplication([])
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="20", largo="20", alto="20"))
    cmd, ctx = ReticulaVolumetrica(), ContextoComando(doc)
    v = {c.clave: c.defecto for c in cmd.campos(ctx)}
    with pytest.raises(ErrorComando):
        cmd.construir(v, ctx)                                                      # sin cuerpo
    v.update(cuerpo=[hit_desde_ref({"tipo": "cuerpo", "cuerpo": "op1.c1"}, doc.estado_final)], forma_celda="cross",
             tamano="10 mm", solidez="25")
    op = cmd.construir(v, ctx)
    doc.agregar(op)
    assert doc.resultados[-1].estado == "ok", doc.resultados[-1].mensaje
    assert cmd.desde_op(op, ContextoComando(doc, op=op))["forma_celda"] == "cross"
    # a medida, gradiente por dos vértices, desfase y celdas movidas: ida y vuelta por el diálogo
    vertices = [hit_desde_ref(r, doc.estado_final) for r in _refs_vertices(doc)]
    v.update(forma_celda="custom", barras="0 0 0 1 0 0; 0 0 0 0 1 0; 0 0 0 0 0 1", distribucion="gradiente", solidez="10",
             solidez_final="30", ruta=vertices, con_desfase=True, desfase="0 mm", mezcla="5 mm", solidez_desfase="30",
             mover_celdas=True, mover_x="5 mm", girar_z="0 deg")
    op2 = cmd.construir(v, ctx)
    assert op2.p["barras"][2] == [0, 0, 0, 0, 0, 1] and len(op2.p["ruta"]) == 2 and op2.p["mover_x"] == "5 mm"
    vuelta = cmd.desde_op(op2, ContextoComando(doc, op=op))
    assert vuelta["distribucion"] == "gradiente" and vuelta["con_desfase"] and vuelta["mover_celdas"]
    assert vuelta["barras"].startswith("0 0 0 1 0 0") and len(vuelta["ruta"]) == 2
    for malo in ({"barras": "0 0 0 1"}, {"barras": "0 0 0 2 0 0"}, {"tamano": "mucho"}, {"ruta": []}):
        with pytest.raises(Exception):
            cmd.construir(dict(v, **malo), ctx)


def _refs_vertices(doc):
    from omnicad.nucleo import referencias
    c = doc.estado_final.cuerpos["op1.c1"]
    vs = referencias.subformas(c.forma, "vertice")
    return [referencias.referencia(c.id, v, c.forma) for v in vs[:2]]


def test_malla_con_celda_de_barras_por_la_api():
    """`_informe` no pide el volumen B-rep de la malla anterior (antes: INTERNAL_ERROR)."""
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 20, "width": 20, "height": 20, "name": "Caja"})["ok"]
    assert api.llamar(s, "tessellate", {"bodies": "Caja", "keep_original": False})["ok"]
    r = api.llamar(s, "create_volumetric_lattice", {"cell_shape": "cross", "cell_size": 5, "solidity": 30})
    assert r["ok"], r
    assert r["result"]["bodies_modified"][0]["previous_volume"] is None
