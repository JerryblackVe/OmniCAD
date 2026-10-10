# -*- coding: utf-8 -*-
"""CHAPA (Sheet Metal): reglas, pestañas, dobladillo, plegar, desplegar/replegar, patrón plano exacto con el
factor K, DXF, convertir, desgarro y unir plegando — por los diálogos de comando y el timeline."""
import json
import math
import os

import numpy as np
import pytest

from omnicad.io_archivos.dxf import leer_dxf
from omnicad.nucleo import chapa
from omnicad.nucleo import geometria as g
from omnicad.nucleo import referencias as refs
from omnicad.restricciones import Boceto
from omnicad.timeline import ops_chapa  # noqa: F401  (registra las operaciones)
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import EstadoModelo, OpBoceto, OpExtrusion, OpPrimitiva

T, R, K = 2.0, 2.0, 0.44
BA90 = math.pi / 2 * (R + K * T)          # longitud desarrollada de un pliegue de 90°


@pytest.fixture(scope="module", autouse=True)
def app_qt():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _h(doc, ref, punto=None):
    from omnicad.ui.comando import hit_desde_ref
    h = hit_desde_ref(ref, doc.estado_final)
    if punto is not None:
        h["punto"] = np.asarray(punto, float)
    return h


def _ejecutar(doc, clase, **valores):
    from omnicad.ui.comando import ContextoComando
    cmd, ctx = clase(), ContextoComando(doc)
    v = {c.clave: (list(c.defecto) if isinstance(c.defecto, list) else c.defecto) for c in cmd.campos(ctx)}
    v.update(valores)
    if cmd.SIN_OP:
        cmd.mostrar(v, ctx)
        cmd.aplicar(v, ctx)
        return None
    op = cmd.construir(v, ctx)
    res = doc.agregar(op)
    assert res.estado in ("ok", "aviso"), res.mensaje
    return op


def _boceto(doc, plano="XY", rect=None, lineas=(), marco=None):
    b = Boceto()
    ids = [b.agregar_linea(a, c) for a, c in lineas]
    if rect:
        ids += b.agregar_rectangulo(*rect)
    op = OpBoceto(doc.nuevo_id(), plano=plano, boceto=b, marco=marco)
    doc.agregar(op)
    return op.id, ids


def _perfil(doc, bid, i=0):
    perfil = doc.estado_final.bocetos[bid].perfiles[i]
    return _h(doc, {"tipo": "perfil", "boceto": bid, **OpExtrusion.referencia_perfil(perfil)})


def _curvas(doc, bid, ids):
    return [_h(doc, {"tipo": "curva_boceto", "boceto": bid, "curva": i}) for i in ids]


def _cuerpo(doc, cid=None):
    cuerpos = doc.estado_final.cuerpos
    return cuerpos[cid] if cid else list(cuerpos.values())[-1]


def _sub(doc, tipo, punto, cid=None):
    """Selección de la arista (por su punto medio) o de la cara (por su centro) del cuerpo."""
    c = _cuerpo(doc, cid)
    clave = "medio" if tipo == "arista" else "centro"
    sub = next(s for s in refs.subformas(c.forma, tipo) if np.allclose(refs.firma(s)[clave], punto, atol=1e-6))
    return _h(doc, refs.referencia(c.id, sub, c.forma), punto if tipo == "cara" else None)


def _cara(doc, punto, cid=None):
    """Selección de la cara plana que contiene `punto` (como un clic ahí: la selección lleva el punto)."""
    from OCP.BRepClass import BRepClass_FaceClassifier
    from OCP.gp import gp_Pnt
    from OCP.TopAbs import TopAbs_IN
    c = _cuerpo(doc, cid)
    sub = next(s for s in refs.subformas(c.forma, "cara") if refs.firma(s)["geom"] == "plano" and
               BRepClass_FaceClassifier(s, gp_Pnt(*map(float, punto)), 1e-6).State() == TopAbs_IN)
    return _h(doc, refs.referencia(c.id, sub, c.forma), punto)


def _doc_placa(regla="Acero 2 mm", **valores):
    """Pestaña base de 100 × 50 sobre XY con la regla dada."""
    from omnicad.ui.comandos.chapa import Pestana
    doc = Documento()
    bid, _ = _boceto(doc, rect=((0, 0), (100, 50)))
    _ejecutar(doc, Pestana, tipo="base", perfiles=[_perfil(doc, bid)], regla=regla, **valores)
    return doc


def _doc_pestana(**valores):
    from omnicad.ui.comandos.chapa import Pestana
    doc = _doc_placa()
    _ejecutar(doc, Pestana, tipo="arista", aristas=[_sub(doc, "arista", (50, 50, 2))], altura="20 mm", **valores)
    return doc


def _caja(forma):
    return tuple(tuple(round(x, 6) for x in p) for p in g.caja_envolvente(forma))


def _plana(caja):
    return [x for p in caja for x in p]


# ---------------------------------------------------------------- reglas
def test_reglas_predefinidas_y_ajustes():
    assert set(chapa.REGLAS) == {"Acero 1 mm", "Acero 2 mm", "Aluminio 1.5 mm", "Acero inoxidable 1.2 mm"}
    r = chapa.regla("Aluminio 1.5 mm")
    assert (r["espesor"], r["radio"], r["k"], r["alivio_ancho"], r["alivio_profundidad"]) == (1.5, 1.5, 0.44, 1.5, 0.75)
    r = chapa.regla("Acero 1 mm", espesor=3.0)              # lo que depende del espesor lo sigue
    assert (r["espesor"], r["radio"], r["separacion"]) == (3.0, 3.0, 3.0)
    assert chapa.regla("Acero 1 mm", espesor=3.0, radio=5.0)["radio"] == 5.0
    assert chapa.longitud_pliegue(90, R, T, K) == pytest.approx(BA90)
    with pytest.raises(g.ErrorGeometria):
        chapa.regla("Acero 1 mm", k=1.5)
    json.dumps(r)                                            # la regla es serializable


# ---------------------------------------------------------------- pestaña base
def test_pestana_base_volumen_regla_y_orientacion():
    doc = _doc_placa()
    c = _cuerpo(doc)
    assert ops_chapa.es_chapa(c) and g.es_valida(c.forma)
    assert g.volumen(c.forma) == pytest.approx(10000)
    assert c.chapa["regla"]["espesor"] == 2.0 and c.chapa["op_regla"] == "op2"
    assert _caja(c.forma) == ((0, 0, 0), (100, 50, 2))
    json.dumps(c.chapa)                                      # el modelo de la pieza es JSON
    assert _caja(_cuerpo(_doc_placa(orientacion="lado2")).forma) == ((0, 0, -2), (100, 50, 0))
    assert _caja(_cuerpo(_doc_placa(orientacion="centro")).forma) == ((0, 0, -1), (100, 50, 1))


def test_estado_copia_conserva_la_chapa():
    doc = _doc_placa()
    copia = doc.estado_final.copia()
    c = copia.cuerpos["op2.c1"]
    assert isinstance(c, ops_chapa.CuerpoChapa) and c.chapa is doc.estado_final.cuerpos["op2.c1"].chapa
    assert ops_chapa.modelo_actual(c) is c.chapa            # forma intacta: no hay nada que incorporar
    assert isinstance(EstadoModelo().copia(), EstadoModelo)


# ---------------------------------------------------------------- pestaña de arista y patrón plano exacto
def test_pestana_de_arista_desarrollo_exacto_con_factor_k():
    doc = _doc_pestana()
    c = _cuerpo(doc)
    assert doc.operaciones[-1].nombre == "Pestaña2" and g.es_valida(c.forma)
    # Interior + altura a las caras exteriores: las medidas exteriores quedan 100 × 50 × 20.
    assert _caja(c.forma) == ((0, 0, 0), (100, 50, 20))
    assert g.volumen(c.forma) == pytest.approx(100 * 46 * T + math.pi / 2 * T * (R + T / 2) * 100 + 100 * 16 * T)
    desarrollo = 50 + 20 + BA90 - 2 * (R + T)               # 66,524 mm
    cont = chapa.contorno_plano(c.chapa)
    (x0, y0), (x1, y1) = cont["caja"]
    assert (x1 - x0, y1 - y0) == pytest.approx((100, desarrollo))
    assert cont["area"] == pytest.approx(100 * desarrollo)
    assert g.volumen(chapa.patron_plano(c.chapa)) == pytest.approx(100 * desarrollo * T)


@pytest.mark.parametrize("posicion, referencia, y_max, z_max, desarrollo", [
    ("exterior", "exterior", 52, 20, 48 + BA90 + 16),
    ("adyacente", "exterior", 54, 20, 50 + BA90 + 16),
    ("tangente", "exterior", 50, 20, 46 + BA90 + 16),
    ("interior", "interior", 50, 22, 46 + BA90 + 18),
    ("interior", "tangente", 50, 20, 46 + BA90 + 16),
])
def test_posicion_del_pliegue_y_referencia_de_altura(posicion, referencia, y_max, z_max, desarrollo):
    c = _cuerpo(_doc_pestana(posicion=posicion, referencia=referencia))
    assert _caja(c.forma)[1] == pytest.approx((100, y_max, z_max))
    assert chapa.contorno_plano(c.chapa)["caja"][1][1] - chapa.contorno_plano(c.chapa)["caja"][0][1] == \
        pytest.approx(desarrollo)


def test_pestana_angosta_con_alivio_angulo_e_invertir():
    c = _cuerpo(_doc_pestana(ancho="simetrico", ancho_distancia="40 mm"))
    # Alivio redondo (ancho 2, 1 mm más allá del pliegue) a cada lado: la base pierde 40 × 4 del pliegue y
    # 2 × (2 × 4 + π/2) de alivios.
    assert chapa.contorno_plano(c.chapa)["area"] == pytest.approx(5000 - 160 - 2 * (8 + math.pi / 2) +
                                                                  40 * (BA90 + 16))
    assert g.es_valida(c.forma)
    c = _cuerpo(_doc_pestana(angulo="45 deg", invertir=True))
    (_, _, z0), (_, y1, _) = g.caja_envolvente(c.forma)
    assert z0 < -10 and y1 > 50


def test_cuatro_pestanas_cierran_una_bandeja_con_alivio_de_esquina():
    from omnicad.ui.comandos.chapa import Pestana
    doc = _doc_placa()
    aristas = [_sub(doc, "arista", p) for p in ((50, 50, 2), (100, 25, 2), (50, 0, 2), (0, 25, 2))]
    _ejecutar(doc, Pestana, tipo="arista", aristas=aristas, altura="20 mm")
    c = _cuerpo(doc)
    assert g.es_valida(c.forma) and _caja(c.forma) == ((0, 0, 0), (100, 50, 20))
    assert chapa.contorno_plano(c.chapa)["piezas"] == 1


def test_pestana_sobre_una_pestana_y_error_en_cuerpo_comun():
    from omnicad.ui.comandos.chapa import Pestana
    doc = _doc_pestana()
    _ejecutar(doc, Pestana, tipo="arista", aristas=[_sub(doc, "arista", (50, 48, 20))], altura="15 mm")
    c = _cuerpo(doc)
    assert g.es_valida(c.forma) and len(c.chapa["pliegues"]) == 2
    # La primera pestaña pierde 4 mm (posición interior de la segunda): 46 + BA + 12 + BA + 11.
    assert chapa.contorno_plano(c.chapa)["caja"][1][1] == pytest.approx(69 + 2 * BA90)
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="100", largo="50", alto="2"))
    from omnicad.ui.comando import ContextoComando
    op = Pestana().construir({"tipo": "arista", "aristas": [_sub(doc, "arista", (50, 50, 2))], "altura": "20 mm",
                              "angulo": "90 deg", "referencia": "exterior", "posicion": "interior",
                              "ancho": "completo", "ancho_distancia": "20 mm", "ancho1": "1 mm", "ancho2": "1 mm",
                              "invertir": False}, ContextoComando(doc))
    res = doc.agregar(op)
    assert res.estado == "error" and "no es un cuerpo de chapa" in res.mensaje


# ---------------------------------------------------------------- DXF, desplegar, patrón plano
def _lazo_cerrado_y_area(prims):
    """¿Los extremos de líneas y arcos se juntan de a dos? y área (fórmula del área con arcos)."""
    extremos, area = [], 0.0
    for p in prims:
        if p[0] == "linea":
            a, b = p[1], p[2]
            area += (a[0] * b[1] - b[0] * a[1]) / 2
        else:
            (cx, cy), r, a0, a1 = p[1], p[2], p[3], p[4]
            a, b = (cx + r * math.cos(a0), cy + r * math.sin(a0)), (cx + r * math.cos(a1), cy + r * math.sin(a1))
        extremos += [a, b]
    cerrado = all(sum(1 for q in extremos if math.dist(p, q) < 1e-4) == 2 for p in extremos)
    return cerrado, abs(area)


def test_dxf_del_patron_plano_cierra_y_mide_lo_desarrollado(tmp_path):
    from omnicad.ui.comandos.chapa import ExportarDXFPatron
    doc = _doc_pestana()
    ruta = tmp_path / "patron.dxf"
    _ejecutar(doc, ExportarDXFPatron, cuerpo=[_h(doc, {"tipo": "cuerpo", "cuerpo": "op2.c1"})], archivo=str(ruta))
    assert ruta.is_file()
    capas = {}
    for capa, prim in leer_dxf(ruta, con_capas=True):
        capas.setdefault(capa, []).append(prim)
    cerrado, area = _lazo_cerrado_y_area(capas["CONTORNO_EXTERIOR"])
    assert cerrado and area == pytest.approx(100 * (62 + BA90), rel=1e-6)
    (pliegue,) = capas["LINEAS_PLIEGUE"]
    assert pliegue[1][1] == pytest.approx(46 + BA90 / 2) and abs(pliegue[2][0] - pliegue[1][0]) == pytest.approx(100)


def test_desplegar_y_volver_a_plegar_conservan_el_volumen():
    from omnicad.ui.comandos.chapa import Desplegar, Replegar
    doc = _doc_pestana()
    c = _cuerpo(doc)
    v0, caja0 = g.volumen(c.forma), _caja(c.forma)
    op = _ejecutar(doc, Desplegar, cara=[_cara(doc, (50, 40, 2))])
    plano = _cuerpo(doc)
    desarrollo = 50 + 20 + BA90 - 8
    assert g.volumen(plano.forma) == pytest.approx(100 * desarrollo * T)
    assert _plana(_caja(plano.forma)) == pytest.approx([0, 0, 0, 100, desarrollo, 2])   # la base quedó quieta
    assert op.nombre == "Desplegado1"
    op = _ejecutar(doc, Replegar, cuerpo=[_h(doc, {"tipo": "cuerpo", "cuerpo": "op2.c1"})])
    assert op.nombre == "Replegado1"
    otra = _cuerpo(doc)
    assert g.volumen(otra.forma) == pytest.approx(v0) and _plana(_caja(otra.forma)) == pytest.approx(_plana(caja0))


def test_patron_plano_como_cuerpo_aparte():
    from omnicad.ui.comandos.chapa import PatronPlano
    doc = _doc_pestana()
    _ejecutar(doc, PatronPlano, cara=[_cara(doc, (50, 40, 2))])
    patron = _cuerpo(doc)
    assert patron.id != "op2.c1" and patron.chapa["patron_de"] == "op2.c1"
    assert g.volumen(patron.forma) == pytest.approx(100 * (62 + BA90) * T)
    (x0, _, z0), (_, _, z1) = g.caja_envolvente(patron.forma)
    assert x0 == pytest.approx(110) and (z0, z1) == pytest.approx((0, 2))      # al lado, sin tocar la pieza
    assert not ops_chapa.es_chapa(patron)


# ---------------------------------------------------------------- dobladillo y contorno
@pytest.mark.parametrize("tipo, valores, volumen, caja_max", [
    ("cerrado", {}, 10000 + math.pi * T ** 2 / 2 * 100 + 8 * 100 * T, (100, 52, 4)),
    ("abierto", {"separacion": "1 mm"}, 10000 + math.pi * T * (0.5 + 1) * 100 + 7.5 * 100 * T, (100, 52.5, 5)),
    ("lagrima", {"separacion": "1 mm", "radio": "2 mm"}, None, (100, 54, 8)),
])
def test_dobladillos(tipo, valores, volumen, caja_max):
    from omnicad.ui.comandos.chapa import Dobladillo
    doc = _doc_placa()
    _ejecutar(doc, Dobladillo, aristas=[_sub(doc, "arista", (50, 50, 2))], tipo=tipo, longitud="10 mm", **valores)
    c = _cuerpo(doc)
    assert g.es_valida(c.forma) and _caja(c.forma)[1] == pytest.approx(caja_max)
    if volumen is not None:
        assert g.volumen(c.forma) == pytest.approx(volumen)
    else:                     # lágrima: pasa de 180° y la punta queda a 1 mm de la cara de arriba
        b = next(iter(c.chapa["pliegues"].values()))
        assert b["angulo"] > 180
        punta = [refs.firma(e)["medio"] for e in refs.subformas(c.forma, "arista") if refs.firma(e)["geom"] == "linea"]
        assert min(p[2] for p in punta if p[1] < 45 and p[2] > 2.5) == pytest.approx(3.0, abs=1e-6)


def test_pestana_de_contorno_en_l_con_radio_de_la_regla():
    from omnicad.ui.comandos.chapa import PestanaContorno
    doc = Documento()
    bid, ids = _boceto(doc, plano="XZ", lineas=[((0, 0), (50, 0)), ((50, 0), (50, 30))])
    op = _ejecutar(doc, PestanaContorno, curvas=_curvas(doc, bid, ids), distancia="40 mm", regla="Acero 2 mm")
    c = _cuerpo(doc)
    assert op.p["tipo"] == "contorno" and g.es_valida(c.forma)
    # Lado 1 (adentro del giro): tramos de 46 y 26 mm + el pliegue de radio 2.
    assert g.volumen(c.forma) == pytest.approx((46 + 26) * 40 * T + math.pi / 2 * T * (R + T / 2) * 40)
    (x0, x1), (y0, y1) = (lambda cj: ((cj[0][0], cj[1][0]), (cj[0][1], cj[1][1])))(chapa.contorno_plano(c.chapa)["caja"])
    assert (x1 - x0, y1 - y0) == pytest.approx((40, 72 + BA90))
    assert _caja(c.forma) == ((0, -40, 0), (50, 0, 30))
    from omnicad.ui.comandos import comando_para
    assert comando_para(op).__name__ == "PestanaContorno"


# ---------------------------------------------------------------- convertir, agujeros, plegar
def test_convertir_placa_y_error_honesto():
    from omnicad.ui.comandos.chapa import ConvertirChapa, Pestana
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="100", largo="50", alto="3"))
    _ejecutar(doc, ConvertirChapa, cara=[_cara(doc, (50, 25, 3))], regla="Acero 1 mm")
    c = _cuerpo(doc)
    assert c.id == "op1.c1" and c.chapa["regla"]["espesor"] == pytest.approx(3) and c.chapa["regla"]["radio"] == 3
    _ejecutar(doc, Pestana, tipo="arista", aristas=[_sub(doc, "arista", (50, 50, 3))], altura="20 mm")
    assert g.es_valida(_cuerpo(doc).forma) and _caja(_cuerpo(doc).forma)[1] == pytest.approx((100, 50, 20))
    doc = Documento()                                         # una L no es una placa plana
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="100", largo="50", alto="2"))
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="100", largo="2", alto="20", operacion="unir",
                            objetivo="op1.c1"))
    from omnicad.ui.comando import ContextoComando
    cara = next(s for s in refs.subformas(_cuerpo(doc).forma, "cara") if refs.firma(s).get("normal") == [0, 0, -1])
    op = ConvertirChapa().construir({"cara": [_h(doc, refs.referencia("op1.c1", cara, _cuerpo(doc).forma))],
                                     "regla": "Acero 2 mm"}, ContextoComando(doc))
    res = doc.agregar(op)
    assert res.estado == "error" and "placa plana de espesor constante" in res.mensaje


def test_agujero_hecho_con_otra_herramienta_entra_al_patron_plano():
    doc = _doc_pestana()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="cilindro", radio="5 mm", alto="10 mm", x="50", y="20", z="-3",
                            operacion="cortar", objetivo="op2.c1"))
    from omnicad.ui.comandos.chapa import Desplegar
    _ejecutar(doc, Desplegar, cara=[_cara(doc, (50, 40, 2))])
    c = _cuerpo(doc)
    assert g.volumen(c.forma) == pytest.approx((100 * (62 + BA90) - math.pi * 25) * T)
    assert len(chapa.contorno_plano(c.chapa)["interiores"]) == 1


def test_plegar_por_una_linea_de_boceto():
    from omnicad.ui.comandos.chapa import Plegar
    doc = _doc_placa()
    plano = g.plano_de_cara(next(s for s in refs.subformas(_cuerpo(doc).forma, "cara")
                                 if np.allclose(refs.firma(s)["centro"], (50, 25, 2))))
    bid, ids = _boceto(doc, plano="cara", marco=plano.marco(), lineas=[((60, 0), (60, 50))])
    _ejecutar(doc, Plegar, cara=[_cara(doc, (20, 25, 2))], lineas=_curvas(doc, bid, ids), angulo="90 deg")
    c = _cuerpo(doc)
    assert g.es_valida(c.forma)
    assert g.volumen(c.forma) == pytest.approx(10000 - BA90 * 50 * T + math.pi / 2 * T * (R + T / 2) * 50)
    ini = 60 - BA90 / 2                                      # línea en el centro del pliegue
    assert _caja(c.forma)[1] == pytest.approx((ini + R + T, 50, 100 - ini - BA90 + R + T))
    assert chapa.contorno_plano(c.chapa)["area"] == pytest.approx(5000)


# ---------------------------------------------------------------- desgarro, unir plegando, reglas
def test_desgarro_por_pliegue_y_por_puntos():
    from omnicad.ui.comandos.chapa import Desgarro
    doc = _doc_pestana()
    cil = next(s for s in refs.subformas(_cuerpo(doc).forma, "cara") if refs.firma(s)["geom"] == "cilindro")
    _ejecutar(doc, Desgarro, modo="cara", cara=[_h(doc, refs.referencia("op2.c1", cil, _cuerpo(doc).forma))])
    vols = sorted(g.volumen(c.forma) for c in doc.estado_final.cuerpos.values())
    assert vols == pytest.approx([100 * 16 * T, 100 * 46 * T])
    doc = _doc_placa()                                       # ranura de 1 mm de x = 30, de borde a borde
    plano = g.plano_de_cara(next(s for s in refs.subformas(_cuerpo(doc).forma, "cara")
                                 if np.allclose(refs.firma(s)["centro"], (50, 25, 2))))
    b = Boceto()
    pts = [b.agregar_punto(30, 0), b.agregar_punto(30, 50)]
    op = OpBoceto(doc.nuevo_id(), plano="cara", marco=plano.marco(), boceto=b)
    doc.agregar(op)
    _ejecutar(doc, Desgarro, modo="puntos", cara=[_cara(doc, (50, 25, 2))], separacion="1 mm",
              puntos=[_h(doc, {"tipo": "punto_boceto", "boceto": op.id, "punto": i}) for i in pts])
    vols = sorted(g.volumen(c.forma) for c in doc.estado_final.cuerpos.values())
    assert vols == pytest.approx([29.5 * 50 * T, 69.5 * 50 * T])
    assert all(ops_chapa.es_chapa(c) for c in doc.estado_final.cuerpos.values())


def test_unir_plegando_dos_chapas():
    from omnicad.ui.comandos.chapa import Pestana, UnirPlegando
    doc = _doc_placa()
    # Placa vertical de 2 mm entre y = 58 y 60, de z = 10 a 40: queda separada de la base.
    plano = g.Plano.desde_marco((0, 60, 0), (0, -1, 0), (1, 0, 0))
    bid, _ = _boceto(doc, plano="cara", marco=plano.marco(), rect=((0, 10), (100, 40)))
    _ejecutar(doc, Pestana, tipo="base", perfiles=[_perfil(doc, bid)], regla="Acero 2 mm")
    b = _cuerpo(doc)
    assert _caja(b.forma) == ((0, 58, 10), (100, 60, 40))
    _ejecutar(doc, UnirPlegando, aristas=[_sub(doc, "arista", (50, 50, 2), "op2.c1"),
                                          _sub(doc, "arista", (50, 58, 10), b.id)])
    cuerpos = doc.estado_final.cuerpos
    assert list(cuerpos) == ["op2.c1"]
    c = cuerpos["op2.c1"]
    # Las líneas medias se cruzan en (y 59, z 1): la base se alarga a 56 y la otra baja hasta z = 4.
    assert g.volumen(c.forma) == pytest.approx(100 * 56 * T + 100 * 36 * T + math.pi / 2 * T * (R + T / 2) * 100)
    assert _plana(_caja(c.forma)) == pytest.approx([0, 0, 0, 100, 60, 40])
    assert chapa.contorno_plano(c.chapa)["caja"][1][1] == pytest.approx(56 + BA90 + 36)


def test_reglas_de_chapa_cambian_el_espesor_y_recalculan_todo():
    from omnicad.ui.comandos.chapa import ReglasChapa
    doc = _doc_pestana()
    _ejecutar(doc, ReglasChapa, cuerpo=[_h(doc, {"tipo": "cuerpo", "cuerpo": "op2.c1"})], espesor="3 mm", k="0.5")
    assert doc.operacion("op2").p["ajustes"] == {"espesor": "3 mm", "k": "0.5"}
    assert all(r.estado == "ok" for r in doc.resultados), doc.resultados
    c = _cuerpo(doc, "op2.c1")
    r = c.chapa["regla"]
    assert (r["espesor"], r["radio"], r["k"]) == (3.0, 3.0, 0.5)
    ba = math.pi / 2 * (3 + 0.5 * 3)
    assert chapa.contorno_plano(c.chapa)["caja"][1][1] == pytest.approx(50 + 20 + ba - 2 * 6)
    from omnicad.ui.comando import ContextoComando, ErrorComando
    cmd = ReglasChapa()
    with pytest.raises(ErrorComando):
        cmd.aplicar({"cuerpo": [_h(doc, {"tipo": "cuerpo", "cuerpo": "op2.c1"})], "k": "2"}, ContextoComando(doc))


def test_editar_pestana_conserva_las_selecciones_y_deshacer():
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos import comando_para
    doc = _doc_pestana(posicion="exterior")
    op = doc.operaciones[-1]
    clase = comando_para(op)
    ctx = ContextoComando(doc, op=op)
    cmd = clase()
    v = {c.clave: (list(c.defecto) if isinstance(c.defecto, list) else c.defecto) for c in cmd.campos(ctx)}
    v.update(cmd.desde_op(op, ctx))
    v["altura"] = "30 mm"
    nueva = cmd.construir(v, ctx)
    assert nueva.id == op.id and nueva.p["aristas"] == op.p["aristas"] and nueva.p["posicion"] == "exterior"
    doc.reemplazar(op.id, nueva)
    assert _caja(_cuerpo(doc).forma)[1] == pytest.approx((100, 52, 30))
    doc.deshacer()
    assert _caja(_cuerpo(doc).forma)[1] == pytest.approx((100, 52, 20))


def test_contorno_con_arco_y_choque_con_error_claro():
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.chapa import Pestana, PestanaContorno
    doc = Documento()
    b = Boceto()
    ids = [b.agregar_linea((0, 0), (50, 0)), b.agregar_arco_centro((50, 10), (50, 0), (60, 10)),
           b.agregar_linea((60, 10), (60, 40))]
    op = OpBoceto(doc.nuevo_id(), boceto=b)
    doc.agregar(op)
    _ejecutar(doc, PestanaContorno, curvas=_curvas(doc, op.id, ids), distancia="20 mm", regla="Acero 2 mm")
    c = _cuerpo(doc)
    # El arco (radio 10 en el boceto, material del lado de adentro) es un pliegue de radio interior 8.
    (b1,) = c.chapa["pliegues"].values()
    assert (b1["radio"], b1["angulo"]) == pytest.approx((8, 90))
    caja = chapa.contorno_plano(c.chapa)["caja"]
    assert caja[1][1] - caja[0][1] == pytest.approx(50 + math.pi / 2 * (8 + K * T) + 30)
    # Dos pestañas a 150° sobre una tira de 10 mm se cruzan: error claro, no un sólido roto.
    doc = Documento()
    bid, _ = _boceto(doc, rect=((0, 0), (100, 10)))
    _ejecutar(doc, Pestana, tipo="base", perfiles=[_perfil(doc, bid)], regla="Acero 2 mm")
    v = {c.clave: c.defecto for c in Pestana().campos(ContextoComando(doc))}
    v.update(tipo="arista", aristas=[_sub(doc, "arista", (50, 10, 2)), _sub(doc, "arista", (50, 0, 2))],
             altura="30 mm", angulo="150 deg", referencia="tangente", posicion="adyacente")
    res = doc.agregar(Pestana().construir(v, ContextoComando(doc)))
    assert res.estado == "error" and "se superponen" in res.mensaje


# ---------------------------------------------------------------- material de la regla, API y patrón plano
def _desgarro_del_pliegue(doc):
    """Operación Desgarro (modo cara) sobre el pliegue de la pestaña de `_doc_pestana`, sin agregarla."""
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.chapa import Desgarro
    c = _cuerpo(doc, "op2.c1")
    cil = next(s for s in refs.subformas(c.forma, "cara") if refs.firma(s)["geom"] == "cilindro")
    cmd, ctx = Desgarro(), ContextoComando(doc)
    v = {x.clave: (list(x.defecto) if isinstance(x.defecto, list) else x.defecto) for x in cmd.campos(ctx)}
    v.update(modo="cara", cara=[_h(doc, refs.referencia("op2.c1", cil, c.forma))])
    return cmd.construir(v, ctx)


def test_la_regla_asigna_su_material_fisico():
    from omnicad import api
    from omnicad.nucleo import analisis as an
    from omnicad.ui.administrar import filas_bom
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.chapa import ConvertirChapa, PatronPlano
    from omnicad.ui.comandos.inspeccionar import CentroMasa
    assert all(r["material"] in an.TABLA_MATERIALES for r in chapa.REGLAS.values())
    assert chapa.regla("Acero 2 mm", espesor=3.0)["material"] == "Acero"
    doc = _doc_placa("Aluminio 1.5 mm")
    c = _cuerpo(doc)
    assert c.material == "Aluminio 6061" and g.es_valida(c.forma)
    masa = 100 * 50 * 1.5 * 2.70e-3                          # mm³ · g/cm³ · 1e-3 = g
    r = api.llamar(api.Sesion(doc), "get_physical_properties", {})
    assert r["ok"] and not r["avisos"], r
    (info,) = r["result"]["bodies"]
    assert info["material"] == "Aluminio 6061" and info["mass_g"] == pytest.approx(masa, rel=1e-4)
    assert filas_bom(doc)[0][3] == "Aluminio 6061" and filas_bom(doc)[0][4] == pytest.approx(masa)
    assert CentroMasa()._calcular({}, ContextoComando(doc))[1] == pytest.approx(masa)
    # «Acero 2 mm» (el caso del hallazgo): acero, 10 000 mm³ → 78,5 g. El patrón plano hereda el material.
    doc = _doc_pestana()
    _ejecutar(doc, PatronPlano, cara=[_cara(doc, (50, 40, 2))])
    assert [x.material for x in doc.estado_final.cuerpos.values()] == ["Acero", "Acero"]
    assert _cuerpo(_doc_placa()).material == "Acero"
    r = api.llamar(api.Sesion(_doc_placa()), "get_physical_properties", {})
    assert r["result"]["bodies"][0]["mass_g"] == pytest.approx(78.5)
    doc.agregar(_desgarro_del_pliegue(doc))                  # las partes del desgarro también lo heredan
    assert len(doc.estado_final.cuerpos) == 3
    assert {x.material for x in doc.estado_final.cuerpos.values()} == {"Acero"}
    doc = Documento()                                         # convertir: el material de la regla plantilla
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="100", largo="50", alto="3"))
    assert _cuerpo(doc).material is None
    _ejecutar(doc, ConvertirChapa, cara=[_cara(doc, (50, 25, 3))], regla="Acero inoxidable 1.2 mm")
    assert _cuerpo(doc).material == "Acero inoxidable"
    doc.propiedades["op1.c1"] = {"material": "Latón"}         # el Material físico asignado a mano sigue mandando
    assert filas_bom(doc)[0][3] == "Latón"


def test_export_de_la_api_escribe_el_dxf_del_patron_plano(tmp_path):
    from omnicad import api
    s = api.Sesion(_doc_pestana())
    ruta = tmp_path / "p.dxf"
    r = api.llamar(s, "export", {"path": str(ruta)})          # sin bodies: el único cuerpo de chapa
    assert r["ok"], r
    assert r["result"]["format"] == "dxf" and r["result"]["bodies"] == ["op2.c1"] and r["result"]["size_bytes"] > 0
    capas = {}
    for capa, prim in leer_dxf(ruta, con_capas=True):
        capas.setdefault(capa, []).append(prim)
    cerrado, area = _lazo_cerrado_y_area(capas["CONTORNO_EXTERIOR"])
    assert cerrado and area == pytest.approx(100 * (62 + BA90), rel=1e-6)
    assert len(capas["LINEAS_PLIEGUE"]) == 1
    s.doc.agregar(OpPrimitiva(s.doc.nuevo_id(), forma="caja", ancho="10", largo="10", alto="10", x="300"))
    r = api.llamar(s, "export", {"path": str(tmp_path / "caja.dxf"), "bodies": ["op4.c1"]})
    assert not r["ok"] and r["error_kind"] == "INVALID_FORMAT" and "no es de chapa" in r["mensaje"]
    r = api.llamar(s, "export", {"path": str(ruta), "bodies": ["op2.c1"], "overwrite": True})
    assert r["ok"] and r["result"]["bodies"] == ["op2.c1"]
    s.doc.agregar(_desgarro_del_pliegue(s.doc))               # dos cuerpos de chapa: hay que elegir uno
    r = api.llamar(s, "export", {"path": str(tmp_path / "dos.dxf")})
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS"
    s = api.Sesion(Documento())
    s.doc.agregar(OpPrimitiva(s.doc.nuevo_id(), forma="caja"))
    r = api.llamar(s, "export", {"path": str(tmp_path / "nada.dxf")})
    assert not r["ok"] and r["error_kind"] == "NOTHING_TO_EXPORT"


def test_patron_plano_al_lado_no_cae_sobre_otros_cuerpos():
    from omnicad.ui.comandos.chapa import PatronPlano
    doc = _doc_pestana()
    # Una caja justo donde caía el patrón (x 110..210): el patrón la saltea y queda 10 mm más allá.
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="40", largo="50", alto="10", x="105"))
    _ejecutar(doc, PatronPlano, cara=[_cara(doc, (50, 40, 2), "op2.c1")])
    patron = _cuerpo(doc)
    assert patron.chapa["patron_de"] == "op2.c1" and g.es_valida(patron.forma)
    assert g.volumen(patron.forma) == pytest.approx(100 * (62 + BA90) * T)
    (x0, _, z0), (x1, _, z1) = g.caja_envolvente(patron.forma)
    assert (x0, x1, z0, z1) == pytest.approx((155, 255, 0, 2))
    for otro in doc.estado_final.cuerpos.values():
        if otro is not patron:
            (a0, *_), (a1, *_) = g.caja_envolvente(otro.forma)
            assert a1 < x0 or a0 > x1                         # no se solapa con ningún cuerpo


def test_desgarro_avisa_una_sola_vez_desde_execute_code():
    from omnicad import api
    s = api.Sesion(_doc_pestana())
    params = _desgarro_del_pliegue(s.doc).a_dict()["params"]
    codigo = (f"import json\nr = llamar('run_operation', {{'type': 'desgarro', 'params': "
              f"json.loads({json.dumps(json.dumps(params))})}})\nresult = r['avisos']")
    r = api.llamar(s, "execute_code", {"code": codigo})
    assert r["ok"], r
    assert sum("La chapa quedó en 2 cuerpos" in a for a in r["avisos"]) == 1, r["avisos"]
    assert sum("La chapa quedó en 2 cuerpos" in a for a in r["result"]["result"]) == 1
    # Una llamada anidada no borra los avisos que juntaron las anteriores del mismo código, y dos llamadas anidadas
    # con el mismo aviso devuelven cada una el suyo (de solo lectura y de las que modifican).
    caja = OpPrimitiva(s.doc.nuevo_id(), forma="caja", x="300")
    s.doc.agregar(caja)
    codigo = (f"a = llamar('get_physical_properties', {{'bodies': ['{caja.id}.c1']}})\n"
              "b = llamar('get_parameters')\n"
              f"c = llamar('get_physical_properties', {{'bodies': ['{caja.id}.c1']}})\n"
              "result = [a['avisos'], b['avisos'], c['avisos']]")
    r = api.llamar(s, "execute_code", {"code": codigo})
    assert r["ok"], r
    (sin_densidad,), otros, repetido = r["result"]["result"]
    assert "Sin densidad" in sin_densidad and otros == [] and repetido == [sin_densidad]
    assert r["avisos"] == [sin_densidad]
    codigo = ("result = [llamar('create_box', {'length': 5, 'width': 5, 'height': 5, 'x': x, "
              f"'operation': 'new_body', 'target': '{caja.id}.c1'}})['avisos'] for x in (500, 900)]")
    r = api.llamar(s, "execute_code", {"code": codigo})
    assert r["ok"], r
    ignorado = ["«target» se ignora con operation=new_body: el cuerpo es nuevo."]
    assert r["result"]["result"] == [ignorado, ignorado] and r["avisos"] == ignorado
