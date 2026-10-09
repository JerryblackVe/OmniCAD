# -*- coding: utf-8 -*-
"""INSERTAR › Insertar fijación: biblioteca normalizada, colocación en agujeros y comando con diálogo."""
import math
import os

import numpy as np
import pytest

from omnicad.nucleo import fijaciones as fj
from omnicad.nucleo import geometria as g
from omnicad.nucleo import referencias as refs
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva, operacion_desde_dict
from omnicad.timeline.ops_fijacion import OpFijacion


@pytest.fixture(scope="module", autouse=True)
def app_qt():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _caja(forma):
    (x0, y0, z0), (x1, y1, z1) = g.caja_envolvente(forma)
    return np.array([x0, y0, z0, x1, y1, z1])


def _placa(*agujeros, radio=3.3, espesor=10):
    """Placa de 60x40x`espesor` con agujeros pasantes de `radio` en los (x, y) dados."""
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="60 mm", largo="40 mm", alto=f"{espesor} mm"))
    for x, y in agujeros:
        doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="cilindro", radio=f"{radio} mm", alto=f"{espesor} mm",
                                x=f"{x} mm", y=f"{y} mm", operacion="cortar", objetivo="op1.c1"))
    return doc


def _hit_circulo(doc, centro, cid="op1.c1"):
    from omnicad.ui.comando import hit_desde_ref
    forma = doc.estado_final.cuerpos[cid].forma
    sub = next(a for a in refs.subformas(forma, "arista") if refs.firma(a).get("geom") == "circulo"
               and np.allclose(refs.firma(a)["centro"], centro, atol=1e-6))
    return hit_desde_ref(refs.referencia(cid, sub, forma), doc.estado_final)


def _hit_cilindro(doc, cid="op1.c1"):
    from omnicad.ui.comando import hit_desde_ref
    forma = doc.estado_final.cuerpos[cid].forma
    sub = next(c for c in refs.subformas(forma, "cara") if refs.firma(c)["geom"] == "cilindro")
    return hit_desde_ref(refs.referencia(cid, sub, forma), doc.estado_final)


def _ejecutar(doc, **valores):
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.fijacion import InsertarFijacion
    cmd = InsertarFijacion()
    ctx = ContextoComando(doc)
    v = {c.clave: (list(c.defecto) if isinstance(c.defecto, list) else c.defecto) for c in cmd.campos(ctx)}
    v.update(valores)
    op = cmd.construir(v, ctx)
    res = doc.agregar(op)
    assert res.estado in ("ok", "aviso"), res.mensaje
    return op, res


def _fijaciones(doc, op):
    return [c for c in doc.estado_final.cuerpos.values() if c.op_id == op.id]


# ---------------------------------------------------------------- biblioteca
def test_iso4762_m6x20_medidas_reales():
    s = fj.generar("tornillo", "ISO 4762", "M6", 20)
    assert g.es_valida(s)
    assert _caja(s) == pytest.approx([-5, -5, -20, 5, 5, 6])          # cabeza Ø10 × 6, vástago de 20 hacia −Z
    # volumen: cabeza + vástago con chaflán de 45° en la punta − allen 5 × 3 con fondo de broca a 118°
    c, rb = 0.61343, 0.98 * 2.5
    solido = math.pi * 25 * 6 + math.pi * 9 * (20 - c) + math.pi * c / 3 * (9 + 3 * (3 - c) + (3 - c) ** 2)
    allen = math.sqrt(3) / 2 * 25 * 3 + math.pi * rb ** 2 * (rb / math.tan(math.radians(59))) / 3
    assert g.volumen(s) == pytest.approx(solido - allen, rel=1e-6)
    # las 6 caras del hexágono allen están a 2,5 mm del eje (entrecaras 5)
    planas = []
    for cara in g.caras(s):
        f = refs.firma_cara(cara)
        if f["geom"] == "plano" and abs(f["normal"][2]) < 1e-9:
            planas.append(abs(np.dot(f["centro"][:2], f["normal"][:2])))
    assert len(planas) == 6 and planas == pytest.approx([2.5] * 6)


def test_tuerca_iso4032_m8_y_arandela():
    t = fj.generar("tuerca", "ISO 4032", "M8")
    assert g.es_valida(t)
    x0, y0, z0, x1, y1, z1 = _caja(t)
    assert (x1 - x0, z0, z1) == pytest.approx((13, 0, 6.8))         # s = 13, m = 6,8
    assert y1 - y0 == pytest.approx(13 / math.cos(math.radians(30)))  # entre esquinas e = s / cos 30°
    agujero = [refs.firma_cara(c)["radio"] for c in g.caras(t) if refs.firma_cara(c)["geom"] == "cilindro"]
    assert agujero == pytest.approx([fj.datos("ISO 4032", "M8")["diametro_menor"] / 2])
    a = fj.generar("arandela", "ISO 7089", "M8")
    assert g.volumen(a) == pytest.approx(math.pi * (8 ** 2 - 4.2 ** 2) * 1.6)
    assert _caja(a) == pytest.approx([-8, -8, 0, 8, 8, 1.6])


def test_otras_normas_validas_y_en_posicion_canonica():
    v = fj.generar("varilla", "DIN 976", "M8", 100)
    assert _caja(v) == pytest.approx([-4, -4, -100, 4, 4, 0])
    e = fj.generar("esparrago", "ISO 4026", "M6", 10)
    assert _caja(e) == pytest.approx([-3, -3, -10, 3, 3, 0])
    av = fj.generar("tornillo", "ISO 10642", "M6", 20)                # avellanado: z = 0 al ras de la cabeza
    assert _caja(av) == pytest.approx([-6.72, -6.72, -20, 6.72, 6.72, 0])
    hx = fj.generar("tornillo", "ISO 4017", "M10", 30)
    x0, y0, z0, x1, y1, z1 = _caja(hx)
    assert (x1 - x0, z0, z1) == pytest.approx((16, -30, 6.4))
    for familia, norma, tam, largo in (("tornillo", "ISO 7380", "M5", 12), ("tornillo", "ISO 7045", "M4", 10),
                                       ("tuerca", "ISO 10511", "M6", None), ("tuerca", "ISO 4035", "M10", None),
                                       ("arandela", "ISO 7090", "M6", None), ("arandela", "ISO 7092", "M4", None)):
        s = fj.generar(familia, norma, tam, largo)
        assert g.es_valida(s) and g.volumen(s) > 0, norma
    with pytest.raises(g.ErrorGeometria):
        fj.generar("tuerca", "ISO 4762", "M6", 20)


def test_tablas_tamano_automatico_y_correcciones():
    assert fj.largos("ISO 4762", "M6")[0] == 10 and fj.largos("ISO 4762", "M6")[-1] == 60
    assert fj.largos("ISO 4032", "M6") == []
    assert fj.tamano_para_agujero("ISO 4762", 6.6) == ("M6", "paso libre medio")
    assert fj.tamano_para_agujero("ISO 4762", 5.0) == ("M6", "broca de roscar")
    assert fj.tamano_para_agujero("ISO 10642", 13.44) == ("M6", "avellanado")
    assert fj.tamano_para_agujero("ISO 4032", 8.0, interior=False) == ("M8", "nominal")
    assert fj.tamano_para_agujero("ISO 4762", 7.3) == ("M6", None)      # sin calce: el mayor que entra
    assert fj.corregir("ISO 7380", "M2", 20) == ("M3", 12, ["ISO 7380 no tiene M2: se usó M3.",
                                                         "ISO 7380 M3 no viene de 20 mm: se usó 12 mm."])
    assert fj.designacion("ISO 4762", "M6", 20) == "ISO 4762 M6x20"
    assert fj.designacion("ISO 4032", "M8") == "ISO 4032 M8"
    assert fj.largo_roscado("ISO 4762", "M6", 50) == 24 and fj.largo_roscado("ISO 4014", "M6", 40) == 18


def test_rosca_modelada_corta_el_filete():
    c = fj.generar("tornillo", "ISO 4762", "M6", 16)
    m = fj.generar("tornillo", "ISO 4762", "M6", 16, rosca="modelada")
    assert g.es_valida(m) and len(g.solidos(m)) == 1
    assert _caja(m) == pytest.approx(_caja(c))
    # surco del perfil básico ISO de 60° en M6x1: 5,318 mm³ por mm, desde la punta (medio chaflán) hasta la
    # salida de rosca medio paso bajo la cabeza (menos medio ancho del surco, que termina en fuga)
    w = 7 / 8 + 0.2 * math.tan(math.radians(30))
    largo = 16 - 0.5 - w / 2 - 0.61343 / 2
    assert g.volumen(c) - g.volumen(m) == pytest.approx(5.318 * largo, rel=0.03)


def test_tuerca_con_rosca_modelada():
    c = fj.generar("tuerca", "ISO 4032", "M8")
    m = fj.generar("tuerca", "ISO 4032", "M8", rosca="modelada")
    assert g.es_valida(m) and len(g.solidos(m)) == 1
    # hueco del filete interior M8x1,25 (anchos P/8 y 3P/4, alto 5H/8): 6,66 mm³ por mm en los 6,8 mm
    assert g.volumen(c) - g.volumen(m) == pytest.approx(6.66 * 6.8, rel=0.03)


# ---------------------------------------------------------------- operación y comando
def test_tornillo_en_agujero_de_placa_queda_coaxial_y_apoyado():
    doc = _placa((20, 20))
    op, res = _ejecutar(doc, posiciones=[_hit_circulo(doc, (20, 20, 10))], largo="20")
    assert res.estado == "ok" and op.nombre == "Fijación1"
    assert op.p["norma"] == "ISO 4762" and op.p["tamano"] == "auto"
    (cuerpo,) = _fijaciones(doc, op)
    assert cuerpo.nombre == "ISO 4762 M6x20" and cuerpo.tipo == "solido" and cuerpo.material == "Acero"
    assert _caja(cuerpo.forma) == pytest.approx([15, 15, -10, 25, 25, 16])   # cabeza sobre la cara de arriba
    assert g.volumen(cuerpo.forma) == pytest.approx(g.volumen(fj.generar("tornillo", "ISO 4762", "M6", 20)))
    # largo automático: el menor de la norma que atraviesa los 10 mm de placa
    doc2 = _placa((20, 20))
    op2, _ = _ejecutar(doc2, posiciones=[_hit_circulo(doc2, (20, 20, 10))])
    assert _fijaciones(doc2, op2)[0].nombre == "ISO 4762 M6x10"


def test_dos_aristas_dos_tornillos_y_similares():
    doc = _placa((15, 20), (45, 20))
    op, _ = _ejecutar(doc, posiciones=[_hit_circulo(doc, (15, 20, 10)), _hit_circulo(doc, (45, 20, 10))],
                      similares=False, largo="16")
    cuerpos = _fijaciones(doc, op)
    assert sorted(c.nombre for c in cuerpos) == ["ISO 4762 M6x16:1", "ISO 4762 M6x16:2"]
    centros = sorted(round(float((_caja(c.forma)[0] + _caja(c.forma)[3]) / 2), 6) for c in cuerpos)
    assert centros == [15, 45]
    doc2 = _placa((15, 20), (45, 20))                                       # «Seleccionar similares»
    op2, _ = _ejecutar(doc2, posiciones=[_hit_circulo(doc2, (15, 20, 10))], similares=True,
                       familia="arandela", norma_arandela="ISO 7089")
    arandelas = _fijaciones(doc2, op2)
    assert len(arandelas) == 2 and arandelas[0].nombre.startswith("ISO 7089 M6")
    assert all(_caja(a.forma)[2] == pytest.approx(10) and _caja(a.forma)[5] == pytest.approx(11.6) for a in arandelas)


def test_cara_cilindrica_voltear_punto_y_tuerca_abajo():
    doc = _placa((20, 20))
    op, _ = _ejecutar(doc, posiciones=[_hit_cilindro(doc)], familia="tornillo", norma_tornillo="ISO 4017",
                      largo="16")
    assert _caja(_fijaciones(doc, op)[0].forma)[[2, 5]] == pytest.approx([-6, 14])      # boca de arriba
    doc = _placa((20, 20))
    op, _ = _ejecutar(doc, posiciones=[_hit_cilindro(doc)], voltear=True, familia="tuerca",
                      norma_tuerca="ISO 4032")
    (tuerca,) = _fijaciones(doc, op)
    assert tuerca.nombre == "ISO 4032 M6" and _caja(tuerca.forma)[[2, 5]] == pytest.approx([-5.2, 0])
    doc = Documento()
    from omnicad.ui.comando import hit_desde_ref
    origen = hit_desde_ref({"tipo": "punto", "id": "O"}, doc.estado_final)
    eje_x = hit_desde_ref({"tipo": "eje", "id": "X"}, doc.estado_final)
    op, res = _ejecutar(doc, posiciones=[origen], direccion=[eje_x], tamano="M8", largo="30")
    assert res.estado == "ok"
    assert _caja(_fijaciones(doc, op)[0].forma) == pytest.approx([-30, -6.5, -6.5, 8, 6.5, 6.5])


def test_valores_no_validos_se_corrigen_con_aviso_y_receta():
    doc = _placa((20, 20))
    op, res = _ejecutar(doc, posiciones=[_hit_circulo(doc, (20, 20, 10))], norma_tornillo="ISO 7380",
                        tamano="M2", largo="300")
    assert res.estado == "aviso" and "no tiene M2" in res.mensaje and "no viene de 300 mm" in res.mensaje
    assert _fijaciones(doc, op)[0].nombre == "ISO 7380 M3x12"
    copia = operacion_desde_dict(op.a_dict())
    assert isinstance(copia, OpFijacion) and copia.p == op.p and copia.dependencias() == {"op1"}
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.fijacion import InsertarFijacion, _propiedades
    ctx = ContextoComando(doc, op=op)
    v = InsertarFijacion().desde_op(op, ctx)
    assert v["norma_tornillo"] == "ISO 7380" and len(v["posiciones"]) == 1
    doc2 = _placa((20, 20))
    texto = _propiedades({"posiciones": [_hit_circulo(doc2, (20, 20, 10))], "familia": "tornillo",
                          "norma_tornillo": "ISO 4762", "tamano": "auto", "largo": "20"}, ContextoComando(doc2))
    assert texto.startswith("ISO 4762 M6x20") and "paso libre medio" in texto and "allen 5" in texto


def test_sin_posicion_avisa_en_el_dialogo():
    from omnicad.ui.comando import ContextoComando, ErrorComando
    from omnicad.ui.comandos.fijacion import InsertarFijacion
    doc = _placa((20, 20))
    cmd = InsertarFijacion()
    ctx = ContextoComando(doc)
    v = {c.clave: (list(c.defecto) if isinstance(c.defecto, list) else c.defecto) for c in cmd.campos(ctx)}
    with pytest.raises(ErrorComando):
        cmd.construir(v, ctx)
