# -*- coding: utf-8 -*-
"""SÓLIDO › CREAR por los diálogos: barrido, solevación, agujero, rosca, bobina, tubería, patrones, simetría,
relleno de contorno y sólido envolvente."""
import math
import os

import numpy as np
import pytest

from omnicad.nucleo import geometria as g
from omnicad.nucleo import referencias as refs
from omnicad.restricciones import Boceto
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpBoceto, OpExtrusion, OpPlano, OpPrimitiva


@pytest.fixture(scope="module", autouse=True)
def app_qt():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _h(doc, ref):
    from omnicad.ui.comando import hit_desde_ref
    return hit_desde_ref(ref, doc.estado_final)


def _ejecutar(doc, clase, **valores):
    from omnicad.ui.comando import ContextoComando
    cmd, ctx = clase(), ContextoComando(doc)
    v = {c.clave: (list(c.defecto) if isinstance(c.defecto, list) else c.defecto) for c in cmd.campos(ctx)}
    v.update(valores)
    op = cmd.construir(v, ctx)
    res = doc.agregar(op)
    assert res.estado in ("ok", "aviso"), res.mensaje
    return op


def _boceto(doc, plano="XY", circulo=None, rect=None, lineas=()):
    b = Boceto()
    ids = []
    if circulo:
        ids.append(b.agregar_circulo(*circulo))
    if rect:
        ids += b.agregar_rectangulo(*rect)
    ids += [b.agregar_linea(a, c) for a, c in lineas]
    op = OpBoceto(doc.nuevo_id(), plano=plano, boceto=b)
    doc.agregar(op)
    return op.id, ids


def _perfil(doc, bid, i=0):
    perfil = doc.estado_final.bocetos[bid].perfiles[i]
    return _h(doc, {"tipo": "perfil", "boceto": bid, **OpExtrusion.referencia_perfil(perfil)})


def _curvas(doc, bid, ids):
    return [_h(doc, {"tipo": "curva_boceto", "boceto": bid, "curva": i}) for i in ids]


def _ultimo(doc):
    return list(doc.estado_final.cuerpos.values())[-1]


def test_barrido_y_solevacion():
    from omnicad.ui.comandos.crear import Barrido, Solevacion
    doc = Documento()
    bp, _ = _boceto(doc, plano="XY", circulo=((0, 0), 2))
    br, ids = _boceto(doc, plano="XZ", lineas=[((0, 0), (0, 10))])
    _ejecutar(doc, Barrido, perfiles=[_perfil(doc, bp)], ruta=_curvas(doc, br, ids))
    assert g.volumen(_ultimo(doc).forma) == pytest.approx(math.pi * 4 * 10, rel=1e-4)
    doc = Documento()
    b1, _ = _boceto(doc, rect=((-5, -5), (5, 5)))
    doc.agregar(OpPlano(doc.nuevo_id(), "Plano1", base="XY", distancia="20 mm"))
    b = Boceto()
    b.agregar_rectangulo((-5, -5), (5, 5))
    op2 = OpBoceto(doc.nuevo_id(), plano=doc.operaciones[-1].id, boceto=b)
    doc.agregar(op2)
    _ejecutar(doc, Solevacion, secciones=[_perfil(doc, b1), _perfil(doc, op2.id)])
    assert g.volumen(_ultimo(doc).forma) == pytest.approx(100 * 20, rel=1e-4)


def test_agujero_en_cara_y_desde_boceto_roscado():
    from omnicad.ui.comandos.crear import Agujero
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="40", largo="40", alto="10"))
    forma = doc.estado_final.cuerpos["op1.c1"].forma
    arriba = next(s for s in refs.subformas(forma, "cara") if np.allclose(refs.firma_cara(s)["centro"], (20, 20, 10)))
    hit = _h(doc, refs.referencia("op1.c1", arriba, forma))
    hit["punto"] = np.array([10.0, 10.0, 10.0])
    _ejecutar(doc, Agujero, colocacion=[hit], extension="todo", diametro="6 mm")
    assert g.volumen(doc.estado_final.cuerpos["op1.c1"].forma) == pytest.approx(16000 - math.pi * 9 * 10, rel=1e-4)
    b = Boceto()
    b.agregar_punto(30, 30)
    sk = OpBoceto(doc.nuevo_id(), plano="cara", marco=g.plano_de_cara(arriba).marco(), boceto=b)
    doc.agregar(sk)
    pid = next(iter(b.puntos))
    antes = g.volumen(doc.estado_final.cuerpos["op1.c1"].forma)
    _ejecutar(doc, Agujero, colocacion=[_h(doc, {"tipo": "punto_boceto", "boceto": sk.id, "punto": pid})],
              profundidad="8 mm", rosca="modelada", designacion="M6")
    despues = g.volumen(doc.estado_final.cuerpos["op1.c1"].forma)
    assert 0 < antes - despues < math.pi * 9 * 10                     # roscado M6 ciego: menos que un Ø6 pasante
    assert g.es_valida(doc.estado_final.cuerpos["op1.c1"].forma)


def test_rosca_cosmetica_bobina_y_tuberia():
    from omnicad.ui.comandos.crear import Bobina, Rosca, Tuberia
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="cilindro", radio="5", alto="20"))
    forma = doc.estado_final.cuerpos["op1.c1"].forma
    lateral = next(s for s in refs.subformas(forma, "cara") if refs.firma_cara(s)["geom"] == "cilindro")
    v0 = g.volumen(forma)
    _ejecutar(doc, Rosca, caras=[_h(doc, refs.referencia("op1.c1", lateral, forma))], modelada=False)
    assert g.volumen(doc.estado_final.cuerpos["op1.c1"].forma) == pytest.approx(v0)
    _ejecutar(doc, Bobina, diametro="30 mm", tipo="rev_altura", revoluciones="3", altura="30 mm", tamano="2 mm")
    vol = g.volumen(_ultimo(doc).forma)
    largo = 3 * math.hypot(math.pi * 30, 10)
    assert vol == pytest.approx(math.pi * 1 * largo, rel=0.05)
    br, ids = _boceto(doc, plano="XZ", lineas=[((50, 0), (50, 40))])
    _ejecutar(doc, Tuberia, ruta=_curvas(doc, br, ids), tamano="4 mm")
    assert g.volumen(_ultimo(doc).forma) == pytest.approx(math.pi * 4 * 40, rel=1e-4)


def test_patrones_simetria_envolvente_y_relleno():
    from omnicad.ui.comandos.crear import (PatronCircular, PatronRectangular, RellenoContorno, Simetria,
                                               SolidoEnvolvente)
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="5", largo="5", alto="5", x="20"))
    c = _h(doc, {"tipo": "cuerpo", "cuerpo": "op1.c1"})
    op = _ejecutar(doc, PatronRectangular, cuerpos=[c], dir1=[_h(doc, {"tipo": "eje", "id": "Y"})], n1=3, d1="20 mm")
    assert sum(1 for k in doc.estado_final.cuerpos if k.startswith(op.id)) == 2
    op = _ejecutar(doc, PatronCircular, cuerpos=[c], eje=[_h(doc, {"tipo": "eje", "id": "Z"})], n=4)
    xs = sorted(round(g.centro_masa(doc.estado_final.cuerpos[k].forma)[0], 3) for k in doc.estado_final.cuerpos
                if k.startswith(op.id))
    assert xs == pytest.approx([-22.5, -2.5, 2.5])                # centro (22,5; 2,5) girado 90°, 180° y 270°
    _ejecutar(doc, Simetria, cuerpos=[c], plano=[_h(doc, {"tipo": "plano", "id": "YZ"})])
    assert g.centro_masa(_ultimo(doc).forma)[0] == pytest.approx(-22.5)
    todos = [_h(doc, {"tipo": "cuerpo", "cuerpo": k}) for k in doc.estado_final.cuerpos]
    _ejecutar(doc, SolidoEnvolvente, cuerpos=todos)
    (x0, _, _), (x1, _, _) = g.caja_envolvente(_ultimo(doc).forma)
    assert (x0, x1) == pytest.approx((-25, 25))
    doc2 = Documento()
    doc2.agregar(OpPrimitiva(doc2.nuevo_id(), forma="cilindro", radio="10", alto="10"))
    forma = doc2.estado_final.cuerpos["op1.c1"].forma
    from omnicad.timeline.ops_superficie import OpDescoser
    doc2.agregar(OpDescoser(doc2.nuevo_id(), cuerpos=["op1.c1"]))
    sup = [_h(doc2, {"tipo": "cuerpo", "cuerpo": k}) for k in doc2.estado_final.cuerpos]
    _ejecutar(doc2, RellenoContorno, herramientas=sup, celdas="1")
    assert g.volumen(_ultimo(doc2).forma) == pytest.approx(g.volumen(forma), rel=1e-4)


def _placa_con_punto(z_plano):
    """Placa 40×40×2 (z 0..2, cuerpo op1.c1) y un boceto con un punto en (20, 20) sobre el plano z = `z_plano`."""
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="40", largo="40", alto="2"))
    plano = OpPlano(doc.nuevo_id(), "Plano", base="XY", distancia=f"{z_plano} mm")
    doc.agregar(plano)
    b = Boceto()
    pid = b.agregar_punto(20, 20)
    sk = OpBoceto(doc.nuevo_id(), plano=plano.id, boceto=b)
    doc.agregar(sk)
    return doc, _h(doc, {"tipo": "punto_boceto", "boceto": sk.id, "punto": pid})


def _alto_placa(doc):
    """(z mínima, z máxima) de la placa con su saliente; antes revisa que la forma sea válida."""
    forma = doc.estado_final.cuerpos["op1.c1"].forma
    assert g.es_valida(forma)
    (_, _, z0), (_, _, z1) = g.caja_envolvente(forma)
    return z0, z1


def test_saliente_crece_hacia_afuera_del_material():
    """L136: con el boceto sobre la cara de arriba de la placa, la columna salía hacia abajo (−normal del plano) y
    atravesaba la placa. Como el Boss de Fusion, crece hacia afuera del material; «Invertir» la da vuelta."""
    from omnicad.ui.comandos.crear import Saliente
    doc, punto = _placa_con_punto(2)
    op = _ejecutar(doc, Saliente, posiciones=[punto], altura="10 mm")
    assert op.p["sentido"] == "auto"
    assert _alto_placa(doc) == pytest.approx((0, 12))
    columna = math.pi * (4 ** 2 - 1.5 ** 2) * 10                     # Ø8 con agujero Ø3, 10 mm sobre la placa
    assert g.volumen(doc.estado_final.cuerpos["op1.c1"].forma) == pytest.approx(40 * 40 * 2 + columna, rel=1e-6)
    doc, punto = _placa_con_punto(2)
    _ejecutar(doc, Saliente, posiciones=[punto], altura="10 mm", invertir=True)
    assert _alto_placa(doc) == pytest.approx((-8, 2))
    doc, punto = _placa_con_punto(0)                                 # sobre la cara de abajo: crece hacia abajo
    _ejecutar(doc, Saliente, posiciones=[punto], altura="10 mm")
    assert _alto_placa(doc) == pytest.approx((-10, 2))
    doc, punto = _placa_con_punto(20)                                # en el aire, sin altura: baja hasta la placa
    _ejecutar(doc, Saliente, posiciones=[punto])
    assert _alto_placa(doc) == pytest.approx((0, 20))


def test_saliente_de_una_receta_vieja_conserva_su_sentido():
    """Una receta guardada antes del sentido automático (sin «sentido») abre igual que antes: −normal del plano.
    Editar ese paso no lo cambia; un saliente nuevo usa el automático."""
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.crear import Saliente
    doc, punto = _placa_con_punto(2)
    _ejecutar(doc, Saliente, posiciones=[punto], altura="10 mm")
    receta = doc.a_dict()
    del receta["operaciones"][-1]["params"]["sentido"]
    vieja = Documento.desde_dict(receta)
    op = vieja.operaciones[-1]
    assert op.p["sentido"] == "plano" and vieja.resultados[-1].estado == "ok"
    assert _alto_placa(vieja) == pytest.approx((-8, 2))
    assert vieja.a_dict()["operaciones"][-1]["params"]["sentido"] == "plano"
    cmd, ctx = Saliente(), ContextoComando(vieja, op=op)
    assert cmd.construir(cmd.desde_op(op, ctx), ctx).p["sentido"] == "plano"
    assert cmd.construir(cmd.desde_op(op, ctx), ContextoComando(vieja)).p["sentido"] == "auto"
