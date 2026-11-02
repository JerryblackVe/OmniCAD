# -*- coding: utf-8 -*-
"""Semántica de los patrones de SÓLIDO (rectangular, circular, en ruta, en puntos y multitransformación): posiciones
medidas, identificadores estables de las instancias suprimidas, simetría por dirección, avisos de lo que no se
aplica y recetas viejas. Cada prueba mide posiciones o volúmenes: no alcanza con que no haya excepción."""
import math

import numpy as np
import pytest

from omnicad.nucleo import geometria as g
from omnicad.nucleo import solidos_crear as sc
from omnicad.restricciones import Boceto
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpBoceto, OpPrimitiva, operacion_desde_dict
from omnicad.timeline.ops_solido import OpMultitransformar, OpPatron

EJE_X, EJE_Y, EJE_Z = ({"tipo": "eje", "id": e} for e in "XYZ")


def _ok(doc, op):
    r = doc.agregar(op)
    assert r.estado in ("ok", "aviso"), r.mensaje
    return r


def _cubo(lado=10.0):
    doc = Documento()
    _ok(doc, OpPrimitiva(doc.nuevo_id(), forma="caja", ancho=str(lado), largo=str(lado), alto=str(lado)))
    return doc


def _esquinas(doc, prefijo):
    """Esquinas mínimas (x, y, z) de los cuerpos del paso `prefijo` (y del original op1.c1), ordenadas."""
    pts = []
    for cid, c in doc.estado_final.cuerpos.items():
        if cid.startswith(prefijo) or cid == "op1.c1":
            pts.append(tuple(round(v, 6) for v in g.caja_envolvente(c.forma)[0]))
    return sorted(pts)


def _patron(doc, **p):
    op = OpPatron(doc.nuevo_id(), cuerpos=["op1.c1"], **p)
    return op, _ok(doc, op)


# ---------------------------------------------------------------- rectangular
def test_rectangular_3x2_extension_20_por_5_son_seis_posiciones_con_pasos_10_y_5():
    doc = _cubo()
    op, _ = _patron(doc, forma_patron="rectangular", dir1=EJE_X, n1=3, d1="20 mm", dir2=EJE_Y, n2=2, d2="5 mm")
    assert _esquinas(doc, op.id) == [(0, 0, 0), (0, 5, 0), (10, 0, 0), (10, 5, 0), (20, 0, 0), (20, 5, 0)]


def test_rectangular_dos_direcciones_con_simetria_independiente():
    doc = _cubo()
    op, _ = _patron(doc, forma_patron="rectangular", dir1=EJE_X, n1=3, d1="20 mm", dir2=EJE_Y, n2=2, d2="30 mm",
                    distribucion="espaciado", simetrico=True, simetrico2=False)
    # dirección 1 simétrica (−20, 0, 20) y la 2 de un solo lado (0, 30): 3 × 2 = 6, y nada en y < 0
    assert _esquinas(doc, op.id) == [(-20, 0, 0), (-20, 30, 0), (0, 0, 0), (0, 30, 0), (20, 0, 0), (20, 30, 0)]
    doc2 = _cubo()
    op2, _ = _patron(doc2, forma_patron="rectangular", dir1=EJE_X, n1=2, d1="20 mm", dir2=EJE_Y, n2=3, d2="30 mm",
                     distribucion="espaciado", simetrico=False, simetrico2=True)
    assert _esquinas(doc2, op2.id) == [(0, -30, 0), (0, 0, 0), (0, 30, 0), (20, -30, 0), (20, 0, 0), (20, 30, 0)]


def test_receta_vieja_la_simetria_global_vale_para_las_dos_direcciones():
    doc = _cubo()
    op, _ = _patron(doc, forma_patron="rectangular", dir1=EJE_X, n1=2, d1="20 mm", dir2=EJE_Y, n2=2, d2="30 mm",
                    distribucion="espaciado", simetrico=True, version_simetria=1)      # sin simetrico2: como antes
    assert len(_esquinas(doc, op.id)) == 9
    assert op.p["simetrico2"] is None


def test_cantidad_2_sin_direccion_2_se_avisa_y_con_la_derivada_se_usa():
    doc = _cubo()
    op, r = _patron(doc, forma_patron="rectangular", dir1=EJE_X, n1=2, d1="20 mm", n2=3, d2="15 mm",
                    distribucion="espaciado")                           # receta vieja: sin dir2_derivada
    assert r.estado == "aviso" and "falta la dirección 2" in r.mensaje
    assert _esquinas(doc, op.id) == [(0, 0, 0), (20, 0, 0)]             # el resultado de antes no cambia
    doc = _cubo()
    op, r = _patron(doc, forma_patron="rectangular", dir1=EJE_X, n1=2, d1="20 mm", n2=3, d2="15 mm",
                    distribucion="espaciado", dir2_derivada=True)
    assert r.estado == "ok"
    assert _esquinas(doc, op.id) == [(0, 0, 0), (0, 15, 0), (0, 30, 0), (20, 0, 0), (20, 15, 0), (20, 30, 0)]


@pytest.mark.parametrize("eje, esperado", [(EJE_X, (0, 15, 0)), (EJE_Y, (-15, 0, 0)), (EJE_Z, (15, 0, 0))])
def test_la_direccion_derivada_es_perpendicular_y_estable(eje, esperado):
    doc = _cubo()
    op, _ = _patron(doc, forma_patron="rectangular", dir1=eje, n1=1, d1="20 mm", n2=2, d2="15 mm",
                    distribucion="espaciado", dir2_derivada=True)
    copia = [p for p in _esquinas(doc, op.id) if p != (0, 0, 0)]
    assert copia == [esperado]


def test_la_direccion_derivada_de_una_linea_de_boceto_queda_en_el_plano_del_boceto():
    doc = _cubo()
    b = Boceto()
    b.agregar_linea((0, 0), (10, 0))
    sk = OpBoceto(doc.nuevo_id(), plano="XZ", boceto=b)
    _ok(doc, sk)
    curva = next(iter(b.curvas))
    ref = {"tipo": "curva_boceto", "boceto": sk.id, "curva": curva}
    op, _ = _patron(doc, forma_patron="rectangular", dir1=ref, n1=1, d1="10 mm", n2=2, d2="15 mm",
                    distribucion="espaciado", dir2_derivada=True)
    copia = [p for p in _esquinas(doc, op.id) if p != (0, 0, 0)][0]
    assert copia[1] == pytest.approx(0)                       # el plano XZ no tiene Y: la copia sube o baja en Z
    assert abs(copia[2]) == pytest.approx(15)


def test_direcciones_paralelas_o_nulas_dan_un_error_claro():
    doc = _cubo()
    r = doc.agregar(OpPatron(doc.nuevo_id(), cuerpos=["op1.c1"], forma_patron="rectangular", dir1=EJE_X, n1=2,
                             d1="10 mm", dir2=EJE_X, n2=2, d2="10 mm", distribucion="espaciado"))
    assert r.estado == "error" and "paralelas" in r.mensaje
    with pytest.raises(g.ErrorGeometria, match="no puede ser cero"):
        sc.transformaciones_rectangulares((1, 0, 0), 3, 0.0)
    with pytest.raises(g.ErrorGeometria, match="nula"):
        sc.transformaciones_rectangulares((0, 0, 0), 3, 10.0)


def test_direcciones_oblicuas_se_aceptan():
    ts = sc.transformaciones_rectangulares((1, 0, 0), 2, 10.0, (1, 1, 0), 2, 10.0, distribucion="espaciado")
    assert len(ts) == 4
    p = sc.a_matriz(ts[-1])[:3, 3]
    assert p == pytest.approx([10 + 10 / math.sqrt(2), 10 / math.sqrt(2), 0])


def test_distancia_negativa_y_cantidad_uno():
    doc = _cubo()
    op, _ = _patron(doc, forma_patron="rectangular", dir1=EJE_X, n1=3, d1="-10 mm", distribucion="espaciado")
    assert _esquinas(doc, op.id) == [(-20, 0, 0), (-10, 0, 0), (0, 0, 0)]
    doc = _cubo()
    op = OpPatron(doc.nuevo_id(), cuerpos=["op1.c1"], forma_patron="rectangular", dir1=EJE_X, n1=1, d1="10 mm")
    r = _ok(doc, op)
    assert "no crea copias" in r.mensaje and len(doc.estado_final.cuerpos) == 1


# ---------------------------------------------------------------- supresión: identificadores estables
def test_suprimir_una_copia_fuera_de_la_primera_fila():
    doc = _cubo()
    op, _ = _patron(doc, forma_patron="rectangular", dir1=EJE_X, n1=3, d1="20 mm", dir2=EJE_Y, n2=2, d2="5 mm",
                    suprimir=[[2, 1]])
    esq = _esquinas(doc, op.id)
    assert len(esq) == 5 and (20, 5, 0) not in esq and (20, 0, 0) in esq and (10, 5, 0) in esq


def test_la_exclusion_conserva_su_posicion_al_cambiar_cantidades_y_distancias():
    doc = _cubo()
    op, _ = _patron(doc, forma_patron="rectangular", dir1=EJE_X, n1=3, d1="20 mm", dir2=EJE_Y, n2=2, d2="5 mm",
                    distribucion="espaciado", suprimir=[[1, 1]])
    assert (20, 5, 0) not in _esquinas(doc, op.id) and (20, 0, 0) in _esquinas(doc, op.id)
    for n1, d1, falta in ((4, "30 mm", (30, 5, 0)), (3, "40 mm", (40, 5, 0))):
        nueva = op.copia()
        nueva.p.update(n1=n1, d1=d1)
        doc.reemplazar(op.id, nueva)
        esq = _esquinas(doc, op.id)
        assert falta not in esq and len(esq) == n1 * 2 - 1, (n1, d1)


def test_exclusion_fuera_del_patron_se_conserva_se_avisa_y_no_se_reasigna():
    doc = _cubo()
    op, _ = _patron(doc, forma_patron="rectangular", dir1=EJE_X, n1=3, d1="20 mm", distribucion="espaciado",
                    suprimir=[2])                                  # el entero 2 es (2, 0): la tercera copia
    assert (40, 0, 0) not in _esquinas(doc, op.id)
    nueva = op.copia()
    nueva.p["n1"] = 2                                             # la copia (2, 0) ya no existe
    r = doc.reemplazar(op.id, nueva)
    assert r.estado == "aviso" and "ya no existen" in r.mensaje and "[2, 0]" in r.mensaje
    assert _esquinas(doc, op.id) == [(0, 0, 0), (20, 0, 0)]       # (20, 0, 0) NO se suprimió en lugar de (40, 0, 0)
    assert doc.operaciones[1].p["suprimir"] == [2]                # el pedido se conserva
    nueva = doc.operaciones[1].copia()
    nueva.p["n1"] = 3
    doc.reemplazar(op.id, nueva)
    assert (40, 0, 0) not in _esquinas(doc, op.id)                # al volver a 3 vuelve a valer


def test_exclusion_con_simetria_es_por_lado_y_el_original_no_se_suprime():
    ts = sc.instancias_rectangulares((1, 0, 0), 3, 10.0, distribucion="espaciado", simetrico1=True,
                                     suprimir=[(-1, 0), (0, 0), 1])
    estados = {i: sup for i, _, sup in ts}
    assert estados == {(0, 0): False, (-1, 0): True, (1, 0): True, (-2, 0): False, (2, 0): False}
    sin = sc.transformaciones_rectangulares((1, 0, 0), 3, 10.0, distribucion="espaciado", simetrico1=False,
                                            suprimir=[(-1, 0)])
    assert len(sin) == 3                                          # sin simetría no hay copia (−1, 0): no suprime otra


def test_suprimir_mal_formado_es_un_error_claro():
    doc = _cubo()
    r = doc.agregar(OpPatron(doc.nuevo_id(), cuerpos=["op1.c1"], forma_patron="rectangular", dir1=EJE_X, n1=3,
                             d1="10 mm", suprimir=[[1, 2, 3]]))
    assert r.estado == "error" and "suprimir" in r.mensaje


# ---------------------------------------------------------------- circular
def _angulos(doc, op, centro=(0, 0)):
    """Ángulos (grados, 0..360) del centro de cada cuerpo del paso respecto del eje Z por `centro`."""
    res = []
    for cid, c in doc.estado_final.cuerpos.items():
        if cid.startswith(op.id) or cid == "op1.c1":
            (a, b, _), (x, y, _z) = g.caja_envolvente(c.forma)
            res.append(round(math.degrees(math.atan2((b + y) / 2 - centro[1], (a + x) / 2 - centro[0])) % 360, 4))
    return sorted(res)


def _cubo_a_distancia():
    doc = Documento()
    _ok(doc, OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="2", largo="2", alto="2", x="20", y="-1"))
    return doc                                                    # centro del cubo en (21, 0): ángulo 0°


def test_circular_completo_de_seis_separa_60_grados_sin_duplicar_el_cierre():
    doc = _cubo_a_distancia()
    op, _ = _patron(doc, forma_patron="circular", eje=EJE_Z, n=6, distribucion="completo")
    assert _angulos(doc, op, (0, 0))[:1] == [0.0] and len(doc.estado_final.cuerpos) == 6
    a = _angulos(doc, op)
    assert np.diff(a) == pytest.approx([60.0] * 5, abs=0.05) and 360 - a[-1] == pytest.approx(60, abs=0.1)


def test_circular_completo_ignora_el_angulo_guardado():
    doc = _cubo_a_distancia()
    op, _ = _patron(doc, forma_patron="circular", eje=EJE_Z, n=4, distribucion="completo", angulo="90 deg")
    assert np.diff(_angulos(doc, op)) == pytest.approx([90.0] * 3, abs=0.05)


def test_circular_parcial_de_tres_sobre_120_grados_es_0_60_y_120():
    doc = _cubo_a_distancia()
    op, _ = _patron(doc, forma_patron="circular", eje=EJE_Z, n=3, distribucion="parcial", angulo="120 deg")
    assert _angulos(doc, op) == pytest.approx([0, 60, 120], abs=0.05)
    assert sc.paso_angular(3, 120.0, "completa", False) == pytest.approx(60.0)     # lo mismo que usa el asa


def _x_rectangular(doc, **p):
    op, _ = _patron(doc, forma_patron="rectangular", dir1=EJE_X, simetrico=True, n2=1, **p)
    return [x for x, _y, _z in _esquinas(doc, op.id)]


# PAT-1: tabla medida en Fusion real (evidencias/fusion_2026-11-01/p5.py y p6.py).
@pytest.mark.parametrize("n, esperado", [(2, [0, 50]), (3, [-50, 0, 50]), (4, [-50, 0, 50, 100]), (5, [-100, -50, 0, 50, 100])])
def test_rectangular_simetrico_la_cantidad_es_el_total_y_la_de_mas_va_al_lado_positivo(n, esperado):
    assert _x_rectangular(_cubo(), n1=n, d1="50 mm", distribucion="espaciado") == pytest.approx(esperado)


def test_rectangular_simetrico_en_extension_mide_por_lado():
    assert _x_rectangular(_cubo(), n1=3, d1="100 mm", distribucion="extension") == pytest.approx([-100, 0, 100])
    assert _x_rectangular(_cubo(), n1=5, d1="100 mm", distribucion="extension") == pytest.approx([-100, -50, 0, 50, 100])


@pytest.mark.parametrize("n, esperado", [(3, [0, 45, 315]), (4, [0, 30, 300, 330]), (2, [0, 270])])
def test_circular_simetrico_el_angulo_es_el_total_y_la_de_mas_va_al_lado_negativo(n, esperado):
    doc = _cubo_a_distancia()
    op, _ = _patron(doc, forma_patron="circular", eje=EJE_Z, n=n, distribucion="simetrico", angulo="90 deg")
    assert _angulos(doc, op) == pytest.approx(esperado, abs=0.1)


def test_receta_vieja_de_circular_simetrico_abre_y_da_lo_mismo():
    doc = _cubo_a_distancia()
    op, _ = _patron(doc, forma_patron="circular", eje=EJE_Z, n=3, distribucion="simetrico", angulo="90 deg")
    datos = doc.a_dict()
    del datos["operaciones"][-1]["params"]["version_simetria"]
    viejo = Documento.desde_dict(datos)
    assert viejo.operaciones[-1].p["version_simetria"] == 1
    assert _angulos(viejo, viejo.operaciones[-1]) == pytest.approx([0, 45, 90, 270, 315], abs=0.1)   # n a cada lado


def test_receta_vieja_de_rectangular_simetrico_y_de_multitransformacion_dan_lo_mismo():
    doc = _cubo()
    _patron(doc, forma_patron="rectangular", dir1=EJE_X, n1=2, d1="20 mm", distribucion="espaciado", simetrico=True)
    multi = OpMultitransformar(doc.nuevo_id(), cuerpos=["op1.c1"], transformaciones=[
        {"tipo": "rectangular", "dir1": EJE_Y, "n1": 2, "d1": "30 mm", "distribucion": "espaciado", "simetrico": True}])
    _ok(doc, multi)
    nuevos = sorted(round(g.caja_envolvente(c.forma)[0][1], 6) for c in doc.estado_final.cuerpos.values())
    assert nuevos == [0, 0, 30]                          # total 2: 0 y +30, además del patrón en x
    datos = doc.a_dict()
    for o in datos["operaciones"]:
        o["params"].pop("version_simetria", None)
    viejo = Documento.desde_dict(datos)
    assert sorted(round(g.caja_envolvente(c.forma)[0][0], 6) for c in viejo.estado_final.cuerpos.values()) == [-20, 0, 0, 0, 20]
    assert sorted(round(g.caja_envolvente(c.forma)[0][1], 6) for c in viejo.estado_final.cuerpos.values()) == [-30, 0, 0, 0, 30]


def test_editar_en_el_panel_un_patron_viejo_conserva_su_reparto():
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.crear import PatronRectangular
    doc = _cubo()
    op, _ = _patron(doc, forma_patron="rectangular", dir1=EJE_X, n1=2, d1="20 mm", distribucion="espaciado", simetrico=True,
                    version_simetria=1)
    cmd, ctx = PatronRectangular(), ContextoComando(doc, op=op)
    nueva = cmd.construir(cmd.desde_op(op, ctx), ctx)
    assert nueva.p["version_simetria"] == 1
    assert OpPatron("x").p["version_simetria"] == 2


def test_circular_sentido_cantidades_uno_y_dos_y_limites():
    doc = _cubo_a_distancia()
    op, _ = _patron(doc, forma_patron="circular", eje=EJE_Z, n=3, distribucion="parcial", angulo="-120 deg")
    assert _angulos(doc, op) == pytest.approx([0, 240, 300], abs=0.05)
    doc = _cubo_a_distancia()
    op, _ = _patron(doc, forma_patron="circular", eje=EJE_Z, n=2, distribucion="parcial", angulo="180 deg")
    assert _angulos(doc, op) == pytest.approx([0, 180], abs=0.05)
    doc = _cubo_a_distancia()
    op = OpPatron(doc.nuevo_id(), cuerpos=["op1.c1"], forma_patron="circular", eje=EJE_Z, n=1, distribucion="parcial",
                  angulo="90 deg")
    r = _ok(doc, op)
    assert len(doc.estado_final.cuerpos) == 1 and "no crea copias" in r.mensaje
    for ang in ("0 deg", "380 deg"):                              # degenerados: error claro, no se esconde
        r = doc.agregar(OpPatron(doc.nuevo_id(), cuerpos=["op1.c1"], forma_patron="circular", eje=EJE_Z, n=3,
                                 distribucion="parcial", angulo=ang))
        assert r.estado == "error" and "una vuelta" in r.mensaje, ang


def test_circular_eje_que_atraviesa_el_objeto_y_objeto_lejos_del_eje():
    doc = Documento()
    _ok(doc, OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="20", largo="2", alto="2", x="-10", y="-1"))
    op, _ = _patron(doc, forma_patron="circular", eje=EJE_Z, n=2, distribucion="parcial", angulo="180 deg")
    cajas = [g.caja_envolvente(c.forma) for cid, c in doc.estado_final.cuerpos.items() if cid.startswith(op.id)]
    assert len(cajas) == 1 and cajas[0][0] == pytest.approx((-10, -1, 0), abs=1e-6)   # el giro de 180° cae sobre sí mismo
    doc = Documento()
    _ok(doc, OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="2", largo="2", alto="2", x="500", y="500"))
    op, _ = _patron(doc, forma_patron="circular", eje=EJE_Z, n=4, distribucion="completo")
    assert len(doc.estado_final.cuerpos) == 4
    assert all(g.es_valida(c.forma) for c in doc.estado_final.cuerpos.values())


def test_circular_receta_vieja_extension_y_espaciado_siguen_igual():
    doc = _cubo_a_distancia()
    op, _ = _patron(doc, forma_patron="circular", eje=EJE_Z, n=3, distribucion="extension", angulo="120 deg")
    assert _angulos(doc, op) == pytest.approx([0, 60, 120], abs=0.05)
    doc = _cubo_a_distancia()
    op, _ = _patron(doc, forma_patron="circular", eje=EJE_Z, n=3, distribucion="espaciado", angulo="45 deg")
    assert _angulos(doc, op) == pytest.approx([0, 45, 90], abs=0.05)
    doc = _cubo()
    r = doc.agregar(OpPatron(doc.nuevo_id(), cuerpos=["op1.c1"], forma_patron="rectangular", dir1=EJE_X, n1=3,
                             d1="10 mm", distribucion="completo"))
    assert r.estado == "error" and "solo existe en el patrón circular" in r.mensaje


# ---------------------------------------------------------------- ruta
def _doc_ruta(puntos, cerrada=False):
    """Cubo de 2 mm en el origen y un boceto XY con la polilínea `puntos` (líneas encadenadas)."""
    doc = Documento()
    _ok(doc, OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="2", largo="2", alto="2", x="-1", y="-1"))
    b = Boceto()
    seg = list(zip(puntos, puntos[1:] + ([puntos[0]] if cerrada else []), strict=False))
    for a, c in seg:
        b.agregar_linea(a, c)
    sk = OpBoceto(doc.nuevo_id(), plano="XY", boceto=b)
    _ok(doc, sk)
    return doc, [{"tipo": "curva_boceto", "boceto": sk.id, "curva": c} for c in b.curvas]


def _centros(doc, op):
    out = []
    for cid, c in doc.estado_final.cuerpos.items():
        if cid.startswith(op.id) or cid == "op1.c1":
            lo, hi = g.caja_envolvente(c.forma)
            out.append(tuple(round((a + b) / 2, 4) for a, b in zip(lo, hi, strict=True)))
    return sorted(out)


def test_ruta_compuesta_reparte_sobre_la_longitud_de_toda_la_cadena():
    doc, ruta = _doc_ruta([(0, 0), (10, 0), (10, 10)])
    assert len(ruta) == 2
    op, _ = _patron(doc, forma_patron="ruta", ruta=ruta, n1=3, d1="20 mm")           # largo total de la cadena: 20
    assert _centros(doc, op) == [(0, 0, 1), (10, 0, 1), (10, 10, 1)]
    largo, cerrada, s0, paso = sc.recorrido_ruta([_forma(doc, r) for r in ruta], 3, 20.0)
    assert (largo, s0, paso) == pytest.approx((20.0, 0.0, 10.0)) and cerrada is False


def _forma(doc, ref):
    from omnicad.timeline import entidades as ent
    return ent.resolver(ref, doc.estado_final).forma


def test_ruta_insuficiente_crea_menos_y_lo_dice():
    doc, ruta = _doc_ruta([(0, 0), (20, 0)])
    op, r = _patron(doc, forma_patron="ruta", ruta=ruta, n1=5, d1="10 mm", distribucion="espaciado")
    assert r.estado == "aviso" and "no alcanza" in r.mensaje and "2 instancia" in r.mensaje
    assert _centros(doc, op) == [(0, 0, 1), (10, 0, 1), (20, 0, 1)]                   # 3 de las 5: no se extrapola
    assert sc.instancias_en_ruta(_forma(doc, ruta[0]), 5, 10.0, distribucion="espaciado")[-1][2] == "fuera"


def test_ruta_inicio_intermedio_y_cuerpo_lejos_de_la_curva_conserva_su_posicion_relativa():
    doc = Documento()
    _ok(doc, OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="2", largo="2", alto="2", x="-1", y="30"))   # lejos de la ruta
    b = Boceto()
    b.agregar_linea((0, 0), (40, 0))
    sk = OpBoceto(doc.nuevo_id(), plano="XY", boceto=b)
    _ok(doc, sk)
    ruta = [{"tipo": "curva_boceto", "boceto": sk.id, "curva": next(iter(b.curvas))}]
    op, _ = _patron(doc, forma_patron="ruta", ruta=ruta, n1=3, d1="10 mm", distribucion="espaciado", inicio="0.5")
    # el original está en el 50 % (x = 20): la copia k se traslada (k · 10) y el cuerpo NO se centra sobre la curva
    assert _centros(doc, op) == [(0, 31, 1), (10, 31, 1), (20, 31, 1)]


def test_ruta_cerrada_vuelta_completa_positiva_y_negativa_no_duplica_el_cierre():
    cuadrado = [(0, 0), (40, 0), (40, 40), (0, 40)]
    for signo in (1, -1):
        doc, ruta = _doc_ruta(cuadrado, cerrada=True)
        op, r = _patron(doc, forma_patron="ruta", ruta=ruta, n1=4, d1=f"{signo * 160} mm")
        c = _centros(doc, op)
        assert len(c) == 4 and len(set(c)) == 4, signo                                # 4 distintos: el cierre no se repite
        assert r.estado == "ok", r.mensaje
        assert set(c) == {(0, 0, 1), (40, 0, 1), (40, 40, 1), (0, 40, 1)}


def test_ruta_orientacion_idéntica_y_direccion_de_ruta():
    doc, ruta = _doc_ruta([(0, 0), (20, 0), (20, 20)])
    forma = _forma(doc, ruta[0])
    from omnicad.timeline import entidades as ent  # noqa: F401
    ts_i = sc.transformaciones_en_ruta([_forma(doc, r) for r in ruta], 3, 40.0, orientacion="identica")
    ts_d = sc.transformaciones_en_ruta([_forma(doc, r) for r in ruta], 3, 40.0, orientacion="direccion_ruta")
    assert np.allclose(sc.a_matriz(ts_i[-1])[:3, :3], np.eye(3))                       # solo se traslada
    m = sc.a_matriz(ts_d[-1])[:3, :3]
    assert m @ [1, 0, 0] == pytest.approx([0, 1, 0], abs=1e-6)                         # el último tramo va hacia +Y
    assert m @ [0, 0, 1] == pytest.approx([0, 0, 1], abs=1e-6)                         # sin giros inesperados: Z sigue en Z
    assert forma is not None


def test_ruta_simetrica_y_supresion():
    doc, ruta = _doc_ruta([(0, 0), (40, 0)])
    op, _ = _patron(doc, forma_patron="ruta", ruta=ruta, n1=2, d1="10 mm", distribucion="espaciado", simetrico=True,
                    inicio="0.5", suprimir=[-1])
    # el original está en x = 20; la copia +1 queda 10 mm más allá y la −1 (suprimida) no existe
    assert _centros(doc, op) == [(0, 0, 1), (10, 0, 1)]


def test_ruta_con_el_boceto_cambiado_el_patron_sigue_a_la_ruta():
    doc, ruta = _doc_ruta([(0, 0), (20, 0)])
    op, r = _patron(doc, forma_patron="ruta", ruta=ruta, n1=3, d1="10 mm", distribucion="espaciado", inicio="0.5")
    assert r.estado == "aviso" and _centros(doc, op) == [(0, 0, 1), (10, 0, 1)]        # x = 10, 20; la de x = 30 no entra
    sk = doc.operaciones[1]
    largo = Boceto()
    largo.agregar_linea((0, 0), (60, 0))
    assert next(iter(largo.curvas)) == ruta[0]["curva"]                                  # misma curva, otro largo
    r = doc.reemplazar(sk.id, OpBoceto(sk.id, sk.nombre, plano="XY", boceto=largo))
    assert _centros(doc, op) == [(0, 0, 1), (10, 0, 1), (20, 0, 1)] and "no alcanza" not in (r.mensaje or "")


# ---------------------------------------------------------------- puntos
def test_patron_en_puntos_traslacion_igual_a_destino_menos_referencia():
    ref, destinos = (3.0, 4.0, 5.0), [(10.0, 0.0, 0.0), (-7.5, 2.25, 9.0)]
    ts = sc.transformaciones_en_puntos(destinos, ref)
    for t, d in zip(ts[1:], destinos, strict=True):
        assert sc.a_matriz(t)[:3, 3] == pytest.approx(np.array(d) - ref, abs=1e-12)
        assert np.allclose(sc.a_matriz(t)[:3, :3], np.eye(3))


def test_patron_en_puntos_destinos_repetidos_coincidentes_y_supresion():
    inst = sc.instancias_en_puntos([(10, 0, 0), (0, 0, 0), (10, 0, 0), (5, 5, 5)], (0, 0, 0), suprimir=[4])
    assert [(k, e) for k, _, e in inst] == [(0, "ok"), (1, "ok"), (2, "repetida"), (3, "repetida"), (4, "suprimida")]
    doc = _cubo()
    op, r = _patron(doc, forma_patron="puntos", coordenadas=[[30, 0, 0], [0, 0, 0], [30, 0, 0], [0, 40, 0]],
                    suprimir=[4])
    assert r.estado == "aviso" and "caerían sobre otra" in r.mensaje
    assert _esquinas(doc, op.id) == [(0, 0, 0), (30, 0, 0)]


def test_patron_en_puntos_referencia_xyz_lleva_ese_punto_a_cada_destino():
    doc = _cubo()
    op, _ = _patron(doc, forma_patron="puntos", coordenadas=[[50, 20, 0]], referencia_xyz=[5, 5, 0])
    assert _esquinas(doc, op.id) == [(0, 0, 0), (45, 15, 0)]


def test_patron_en_puntos_un_boceto_entero_toma_solo_sus_puntos_sueltos():
    doc = _cubo()
    b = Boceto()
    b.agregar_punto(30, 0)
    b.agregar_linea((0, 20), (10, 20))                  # los extremos de una curva no son puntos sueltos
    sk = OpBoceto(doc.nuevo_id(), plano="XY", boceto=b)
    _ok(doc, sk)
    op, _ = _patron(doc, forma_patron="puntos", puntos=[{"tipo": "boceto", "boceto": sk.id}])
    assert _esquinas(doc, op.id) == [(0, 0, 0), (30, 0, 0)]


def test_patron_en_puntos_sigue_al_punto_del_boceto_si_se_mueve():
    doc = _cubo()
    b = Boceto()
    pid = b.agregar_punto(30, 0)
    sk = OpBoceto(doc.nuevo_id(), plano="XY", boceto=b)
    _ok(doc, sk)
    op, _ = _patron(doc, forma_patron="puntos", puntos=[{"tipo": "punto_boceto", "boceto": sk.id, "punto": pid}])
    assert _esquinas(doc, op.id)[-1] == (30, 0, 0)
    b2 = Boceto()
    b2.agregar_punto(0, 0)
    pid2 = next(iter(b2.puntos))
    b2.puntos[pid2].x, b2.puntos[pid2].y = 55.0, 12.0
    doc.reemplazar(sk.id, OpBoceto(sk.id, sk.nombre, plano="XY", boceto=b2))
    nueva = operacion_desde_dict(op.a_dict())
    nueva.p["puntos"] = [{"tipo": "punto_boceto", "boceto": sk.id, "punto": pid2}]
    doc.reemplazar(op.id, nueva)
    assert _esquinas(doc, op.id)[-1] == (55, 12, 0)


# ---------------------------------------------------------------- multitransformación (receta)
def test_multitransformar_conserva_simetria_y_supresion_en_cada_transformacion():
    doc = _cubo()
    t1 = {"tipo": "rectangular", "dir1": EJE_X, "n1": 5, "d1": "20 mm", "dir2": EJE_Y, "n2": 2, "d2": "30 mm",
          "distribucion": "espaciado", "simetrico": True, "simetrico2": False, "suprimir": [[1, 1], 2]}
    op = OpMultitransformar(doc.nuevo_id(), cuerpos=["op1.c1"], transformaciones=[t1])
    _ok(doc, op)
    # 5 posiciones en X × 2 en Y = 10, menos las suprimidas (1, 1) y (2, 0)
    assert len(doc.estado_final.cuerpos) == 10 - 2


# ---------------------------------------------------------------- modos de cálculo del patrón de operaciones
def test_identico_y_optimizado_dan_lo_mismo_y_ajustar_omite_las_copias_que_no_tocan():
    from omnicad.timeline.ops_solido import OpAgujero

    def placa():
        doc = Documento()
        _ok(doc, OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="100", largo="60", alto="10"))
        b = Boceto()
        pid = b.agregar_punto(10, 10)
        sk = OpBoceto(doc.nuevo_id(), plano="XY", boceto=b)
        _ok(doc, sk)
        agujero = OpAgujero(doc.nuevo_id(), posiciones=[{"tipo": "punto_boceto", "boceto": sk.id, "punto": pid}],
                            diametro="6 mm", extension="todo", invertir=True)
        _ok(doc, agujero)
        return doc, agujero

    resultados = {}
    for calculo in ("identico", "optimizado", "ajustar"):
        doc, agujero = placa()
        op = OpPatron(doc.nuevo_id(), objeto="operaciones", pasos=[agujero.id], calculo=calculo, forma_patron="rectangular",
                      dir1=EJE_X, n1=4, d1="40 mm", distribucion="espaciado")
        r = _ok(doc, op)                                  # la 4.ª copia cae en x = 130: fuera de la placa de 100
        resultados[calculo] = (round(g.volumen(doc.estado_final.cuerpos["op1.c1"].forma), 6), r.mensaje or "")
    assert resultados["identico"] == resultados["optimizado"]                        # el mismo resultado: se documenta así
    assert resultados["identico"][1] == "" and "Ajustar: 1 copia(s) no tocan al cuerpo" in resultados["ajustar"][1]
    assert resultados["ajustar"][0] == resultados["identico"][0]                     # y el cuerpo queda igual de agujereado


def _placa_con_paso(medidas, extra=None):
    """Placa de 100 × 100 × 5 y la primitiva `medidas`, que la corta o se le une."""
    doc = Documento()
    _ok(doc, OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="100", largo="100", alto="5", **(extra or {})))
    herramienta = OpPrimitiva(doc.nuevo_id(), **medidas)
    _ok(doc, herramienta)
    return doc, herramienta


def _cuerpo_con_calculo(calculo, paso, extra=None, escalon=None, **patron):
    doc, herramienta = _placa_con_paso(paso, extra)
    if escalon:
        _ok(doc, OpPrimitiva(doc.nuevo_id(), forma="caja", operacion="unir", **escalon))
    _ok(doc, OpPatron(doc.nuevo_id(), objeto="operaciones", pasos=[herramienta.id], calculo=calculo, **patron))
    c = doc.estado_final.cuerpos["op1.c1"].forma
    assert g.es_valida(c)
    return c


def _medidas(calculo, paso, **patron):
    c = _cuerpo_con_calculo(calculo, paso, **patron)
    return round(g.volumen_exacto(c), 4), len(g.caras(c))


@pytest.fixture
def espia_caras(monkeypatch):
    """Lo que devolvió cada `patronear_caras`: una forma = se patronearon las caras; None = fue por la herramienta."""
    devueltos, original = [], sc.patronear_caras

    def espia(*args, **kwargs):
        devueltos.append(original(*args, **kwargs))
        return devueltos[-1]
    monkeypatch.setattr(sc, "patronear_caras", espia)
    return devueltos


AGUJERO = {"forma": "cilindro", "radio": "3", "alto": "7", "x": "10", "y": "10", "z": "-1", "operacion": "cortar"}
BOSS = {"forma": "cilindro", "radio": "3", "alto": "8", "x": "10", "y": "10", "z": "4", "operacion": "unir"}
CIEGO = {"forma": "cilindro", "radio": "3", "alto": "5", "x": "10", "y": "10", "z": "2", "operacion": "cortar"}
EN_GRILLA = {"forma_patron": "rectangular", "dir1": EJE_X, "n1": 5, "d1": "20 mm", "dir2": EJE_Y, "n2": 5, "d2": "20 mm",
             "distribucion": "espaciado"}


@pytest.mark.parametrize("paso, caras", [(AGUJERO, 31), (BOSS, 56), (CIEGO, 56)], ids=["pasante", "saliente", "ciego"])
def test_optimizado_patronea_caras_y_da_lo_mismo_que_identico(espia_caras, paso, caras):
    """5 × 5 sobre la placa: una booleana sola para la primera copia y el mismo cuerpo que con la herramienta unida."""
    optimizado = _medidas("optimizado", paso, **EN_GRILLA)
    assert espia_caras and espia_caras[0] is not None
    assert optimizado == _medidas("identico", paso, **EN_GRILLA) and optimizado[1] == caras


def test_optimizado_quita_lo_que_dice_la_cuenta(espia_caras):
    c = _cuerpo_con_calculo("optimizado", AGUJERO, **EN_GRILLA)
    assert espia_caras[0] is not None
    assert g.volumen_exacto(c) == pytest.approx(100 * 100 * 5 - 25 * math.pi * 3 ** 2 * 5, rel=1e-9)


def test_optimizado_con_copias_giradas_gira_el_hueco(espia_caras):
    """Ranura de 6 × 3 a 30 mm del eje Z, 4 copias alrededor: la copia a 90° tiene el lado largo sobre Y."""
    placa = {"x": "-50", "y": "-50"}
    ranura = {"forma": "caja", "ancho": "6", "largo": "3", "alto": "7", "x": "27", "y": "-1.5", "z": "-1", "operacion": "cortar"}
    giro = {"forma_patron": "circular", "eje": {"tipo": "eje", "id": "Z"}, "n": 4, "angulo": "360 deg", "distribucion": "completo"}
    c = _cuerpo_con_calculo("optimizado", ranura, extra=placa, **giro)
    assert espia_caras[0] is not None
    assert g.volumen_exacto(c) == pytest.approx(100 * 100 * 5 - 4 * 6 * 3 * 5, rel=1e-9)
    assert not g.punto_toca(c, (0.5, 32, 2.5)) and g.punto_toca(c, (2.5, 30, 2.5))
    assert (round(g.volumen_exacto(c), 4), len(g.caras(c))) == _medidas("identico", ranura, extra=placa, **giro)


@pytest.mark.parametrize("patron", [
    pytest.param({"forma_patron": "rectangular", "dir1": EJE_X, "n1": 5, "d1": "30 mm", "distribucion": "espaciado"},
                 id="se_sale_de_la_placa"),
    pytest.param({"forma_patron": "rectangular", "dir1": EJE_X, "n1": 2, "d1": "88 mm", "distribucion": "espaciado"},
                 id="cruza_el_borde"),
    pytest.param({"forma_patron": "rectangular", "dir1": EJE_X, "n1": 3, "d1": "4 mm", "distribucion": "espaciado"},
                 id="copias_solapadas"),
])
def test_optimizado_cae_a_la_herramienta_si_las_copias_no_son_intercambiables(espia_caras, patron):
    """La «operación dividida» de Fusion: acá no da error, da lo mismo que «Idéntico» sin patronear caras."""
    optimizado = _medidas("optimizado", AGUJERO, **patron)
    assert espia_caras == [None]
    assert optimizado == _medidas("identico", AGUJERO, **patron)


def test_optimizado_una_copia_bajo_un_escalon_no_se_patronea(espia_caras):
    """Una copia del agujero ciego cae bajo un escalón: repetir sus caras dejaría un agujero que el escalón tapa."""
    escalon = {"ancho": "20", "largo": "20", "alto": "5", "x": "40", "y": "0", "z": "5"}
    patron = {"forma_patron": "rectangular", "dir1": EJE_X, "n1": 3, "d1": "40 mm", "distribucion": "espaciado"}
    optimizado = _medidas("optimizado", CIEGO, escalon=escalon, **patron)
    assert espia_caras == [None]
    assert optimizado == _medidas("identico", CIEGO, escalon=escalon, **patron)


@pytest.mark.parametrize("paso, caras", [
    ({"forma": "cilindro", "radio": "3", "alto": "5", "x": "10", "y": "10", "z": "0", "operacion": "cortar"}, 31),
    ({"forma": "cilindro", "radio": "3", "alto": "3", "x": "10", "y": "10", "z": "2", "operacion": "cortar"}, 56),
    ({"forma": "cilindro", "radio": "3", "alto": "8", "x": "10", "y": "10", "z": "5", "operacion": "unir"}, 56),
], ids=["pasante", "ciego", "saliente"])
def test_optimizado_con_la_herramienta_al_ras_de_la_cara(espia_caras, paso, caras):
    """El caso común: extruir desde la cara, con la tapa de la herramienta sobre el mismo plano que la cara."""
    optimizado = _medidas("optimizado", paso, **EN_GRILLA)
    assert espia_caras and espia_caras[0] is not None
    assert optimizado == _medidas("identico", paso, **EN_GRILLA) and optimizado[1] == caras


def test_optimizado_con_un_agujero_abocardado_de_verdad(espia_caras):
    from omnicad.timeline.ops_solido import OpAgujero

    def con(calculo):
        doc = Documento()
        _ok(doc, OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="100", largo="100", alto="10"))
        b = Boceto()
        pid = b.agregar_punto(10, 10)
        sk = OpBoceto(doc.nuevo_id(), plano="XY", boceto=b)
        _ok(doc, sk)
        agujero = OpAgujero(doc.nuevo_id(), posiciones=[{"tipo": "punto_boceto", "boceto": sk.id, "punto": pid}], tipo="abocardado",
                            diametro="6 mm", diam_abocardado="10 mm", prof_abocardado="3 mm", profundidad="6 mm", invertir=True)
        _ok(doc, agujero)
        _ok(doc, OpPatron(doc.nuevo_id(), objeto="operaciones", pasos=[agujero.id], calculo=calculo, **EN_GRILLA))
        c = doc.estado_final.cuerpos["op1.c1"].forma
        assert g.es_valida(c)
        return round(g.volumen_exacto(c), 4), len(g.caras(c))
    optimizado = con("optimizado")
    assert espia_caras[0] is not None and optimizado == con("identico")


def test_optimizado_conserva_el_aviso_de_un_objetivo_que_no_se_toca():
    """Con dos cuerpos elegidos y uno sin tocar, «Idéntico» avisa: «Optimizado» tiene que decir lo mismo."""
    mensajes = {}
    for calculo in ("identico", "optimizado"):
        doc = Documento()
        _ok(doc, OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="100", largo="100", alto="5"))
        _ok(doc, OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="10", largo="10", alto="5", x="200"))
        corte = OpPrimitiva(doc.nuevo_id(), objetivo=["op1.c1", "op2.c1"], **AGUJERO)
        _ok(doc, corte)
        mensajes[calculo] = _ok(doc, OpPatron(doc.nuevo_id(), objeto="operaciones", pasos=[corte.id], calculo=calculo,
                                              forma_patron="rectangular", dir1=EJE_X, n1=3, d1="20 mm",
                                              distribucion="espaciado")).mensaje
    assert "no le cortó nada" in mensajes["identico"]
    assert mensajes["optimizado"] == mensajes["identico"]


def _trasladadas(*desplazamientos):
    return [sc._traslacion(np.array([x, 0.0, 0.0])) for x in desplazamientos]


def test_patronear_caras_con_ubicacion_y_con_un_vacio_interior():
    """El cuerpo llega con ubicación (copia ligera) y una segunda cáscara: queda cerrado y da la cuenta."""
    con_vacio = g.booleano(g.caja(100, 100, 10), g.caja(10, 10, 2, (45, 45, 4)), "cortar")
    placa = sc.instanciar(con_vacio, sc._traslacion(np.array([5.0, 0, 0])))
    herramienta = g.cilindro(3, 12, (20, 20, -1))
    trsfs = _trasladadas(20.0, 40.0)
    r = sc.patronear_caras(placa, [sc.aplicar(herramienta, t) for t in trsfs], trsfs, "cortar")
    assert r is not None and g.es_valida(r)
    assert g.volumen_exacto(r) == pytest.approx(100 * 100 * 10 - 10 * 10 * 2 - 2 * math.pi * 9 * 10, rel=1e-9)


def test_patronear_caras_rechaza_una_simetria_y_un_cuerpo_de_dos_solidos():
    from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt, gp_Trsf
    espejo = gp_Trsf()
    espejo.SetMirror(gp_Ax2(gp_Pnt(40, 0, 0), gp_Dir(1, 0, 0)))
    placa, herramienta = g.caja(100, 100, 10), g.cilindro(3, 12, (20, 20, -1))
    assert sc.patronear_caras(placa, [sc.aplicar(herramienta, espejo)], [espejo], "cortar") is None
    t = _trasladadas(30.0)
    dos = g.compuesto([placa, g.caja(100, 100, 10, (200, 0, 0))])
    assert sc.patronear_caras(dos, [sc.aplicar(herramienta, t[0])], t, "cortar") is None


def test_patronear_caras_el_cuerpo_se_sigue_editando_y_exportando(tmp_path):
    """Las caras copiadas pasan por el kernel: chaflán en un agujero copiado, malla y STEP de ida y vuelta."""
    from omnicad.nucleo import intercambio, solidos_modificar as sm
    trsfs = _trasladadas(20.0, 40.0, 60.0)
    herramienta = g.cilindro(3, 7, (20, 20, -1))
    placa = g.booleano(g.caja(100, 100, 5), herramienta, "cortar")
    r = sc.patronear_caras(placa, [sc.aplicar(herramienta, t) for t in trsfs], trsfs, "cortar")
    assert r is not None
    esperado = 100 * 100 * 5 - 4 * math.pi * 9 * 5
    assert g.volumen(r) == pytest.approx(esperado, rel=1e-3)                  # pasa por la malla
    circulo = next(g.TopoDS.Edge(a) for a in g._explorar(r, g.TopAbs_EDGE) if g.punto_toca(a, (83, 20, 5)))
    biselado = sm.chaflan(r, [{"aristas": [circulo], "tipo": "distancia_igual", "distancia": 0.5}])
    assert g.es_valida(biselado) and g.volumen_exacto(biselado) < g.volumen_exacto(r)
    ruta = str(tmp_path / "patron.step")
    intercambio.escribir_step(r, ruta)
    assert g.volumen_exacto(intercambio.leer_step(ruta)) == pytest.approx(esperado, rel=1e-6)


def test_optimizado_deja_la_herramienta_para_un_patron_del_patron(espia_caras):
    """El registro de herramientas sigue sirviendo: un patrón que repite el «Optimizado» corre todas sus copias."""
    doc, herramienta = _placa_con_paso(AGUJERO)
    fila = OpPatron(doc.nuevo_id(), objeto="operaciones", pasos=[herramienta.id], calculo="optimizado",
                    forma_patron="rectangular", dir1=EJE_X, n1=3, d1="20 mm", distribucion="espaciado")
    _ok(doc, fila)
    _ok(doc, OpPatron(doc.nuevo_id(), objeto="operaciones", pasos=[herramienta.id, fila.id], calculo="optimizado",
                      forma_patron="rectangular", dir1=EJE_Y, n1=2, d1="30 mm", distribucion="espaciado"))
    c = doc.estado_final.cuerpos["op1.c1"].forma
    assert espia_caras[0] is not None and g.es_valida(c)
    assert g.volumen_exacto(c) == pytest.approx(100 * 100 * 5 - 6 * math.pi * 3 ** 2 * 5, rel=1e-9)


def test_optimizado_guarda_reabre_y_deshace_con_el_mismo_cuerpo():
    doc, herramienta = _placa_con_paso(AGUJERO)
    antes = g.volumen_exacto(doc.estado_final.cuerpos["op1.c1"].forma)
    _ok(doc, OpPatron(doc.nuevo_id(), objeto="operaciones", pasos=[herramienta.id], calculo="optimizado", **EN_GRILLA))
    despues = g.volumen_exacto(doc.estado_final.cuerpos["op1.c1"].forma)
    reabierto = Documento.desde_dict(doc.a_dict())
    assert g.volumen_exacto(reabierto.estado_final.cuerpos["op1.c1"].forma) == pytest.approx(despues, rel=1e-9)
    doc.deshacer()
    assert g.volumen_exacto(doc.estado_final.cuerpos["op1.c1"].forma) == pytest.approx(antes, rel=1e-9)


# ---------------------------------------------------------------- eje circular desde un círculo, deshacer y guardar
def test_circular_con_el_eje_de_un_circulo_de_boceto():
    doc = _cubo()
    b = Boceto()
    b.agregar_circulo((100, 0), 5)                    # su eje: la recta por (100, 0) normal al plano XY
    sk = OpBoceto(doc.nuevo_id(), plano="XY", boceto=b)
    _ok(doc, sk)
    eje = {"tipo": "curva_boceto", "boceto": sk.id, "curva": next(iter(b.curvas))}
    op, _ = _patron(doc, forma_patron="circular", eje=eje, n=2, distribucion="parcial", angulo="180 deg")
    # el cubo (centro en (5, 5)) girado 180° alrededor de (100, 0): su centro pasa a (195, −5)
    assert _esquinas(doc, op.id) == [(0, 0, 0), (190, -10, 0)]


def test_un_patron_se_deshace_y_rehace_de_una_vez_y_sobrevive_a_guardar_y_reabrir(tmp_path):
    from omnicad.io_archivos import proyecto
    doc = _cubo()
    op, _ = _patron(doc, forma_patron="rectangular", dir1=EJE_X, n1=5, d1="20 mm", dir2=EJE_Y, n2=2, d2="30 mm",
                    distribucion="espaciado", simetrico=True, simetrico2=False, dir2_derivada=True, suprimir=[[1, 1], -1])
    esquinas = _esquinas(doc, op.id)
    assert len(esquinas) == 10 - 2
    doc.deshacer()                                                           # un solo paso de deshacer por operación
    assert len(doc.estado_final.cuerpos) == 1 and len(doc.operaciones) == 1
    doc.rehacer()
    assert _esquinas(doc, op.id) == esquinas
    ruta = proyecto.guardar(doc, tmp_path / "patron")
    reabierto = proyecto.abrir(ruta)
    assert _esquinas(reabierto, op.id) == esquinas
    p = reabierto.operaciones[1].p
    assert p["suprimir"] == [[1, 1], [-1, 0]] or p["suprimir"] == [[1, 1], -1]
    assert p["simetrico2"] is False and p["dir2_derivada"] is True


# ---------------------------------------------------------------- instancias iguales ≠ cuerpos que se tocan
def test_cuerpos_que_se_intersectan_por_su_tamano_siguen_siendo_instancias_distintas():
    doc = _cubo(10.0)
    op, _ = _patron(doc, forma_patron="rectangular", dir1=EJE_X, n1=3, d1="5 mm", distribucion="espaciado")
    assert _esquinas(doc, op.id) == [(0, 0, 0), (5, 0, 0), (10, 0, 0)]       # se pisan entre sí, pero son tres
    assert sc.a_matriz(sc.componer_transformaciones([sc.transformaciones_rectangulares((1, 0, 0), 2, 10.0, distribucion="espaciado")] * 2)[-1])[0, 3] == 20.0
    doc = _cubo(10.0)
    t = {"tipo": "rectangular", "dir1": EJE_X, "n1": 2, "d1": "10 mm", "distribucion": "espaciado"}
    op = OpMultitransformar(doc.nuevo_id(), cuerpos=["op1.c1"], transformaciones=[t, dict(t)])
    _ok(doc, op)
    # 0, 10 y 10 + 10: la instancia (10) que sale de dos caminos es UNA sola (misma transformación) y no se duplica
    assert _esquinas(doc, op.id) == [(0, 0, 0), (10, 0, 0), (20, 0, 0)]
