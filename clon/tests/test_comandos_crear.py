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


def _caja_y_cara_de_arriba(alto=10):
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="40", largo="40", alto=str(alto)))
    forma = doc.estado_final.cuerpos["op1.c1"].forma
    arriba = next(s for s in refs.subformas(forma, "cara") if np.allclose(refs.firma_cara(s)["centro"], (20, 20, alto)))
    return doc, forma, arriba


def _clic(doc, forma, cara, punto):
    hit = _h(doc, refs.referencia("op1.c1", cara, forma))
    hit["punto"] = np.array(punto, float)
    return hit


def _volumen(doc):
    forma = doc.estado_final.cuerpos["op1.c1"].forma
    assert g.es_valida(forma)
    return g.volumen(forma)


def test_agujero_con_holgura_iso_273_y_conico():
    from omnicad.ui.comandos.crear import Agujero
    doc, forma, arriba = _caja_y_cara_de_arriba()
    op = _ejecutar(doc, Agujero, colocacion=[_clic(doc, forma, arriba, (10, 10, 10))], extension="todo",
                   rosca="holgura", tam_holgura="M8", ajuste="normal")
    assert (op.p["rosca"], op.p["designacion"], op.p["ajuste"]) == ("holgura", "M8", "normal")
    assert _volumen(doc) == pytest.approx(16000 - math.pi * 4.5 ** 2 * 10, rel=1e-6)      # ISO 273 M8 media: Ø9
    antes = _volumen(doc)
    op = _ejecutar(doc, Agujero, colocacion=[_clic(doc, forma, arriba, (30, 30, 10))], rosca="conico",
                   tipo_conica="bsp_conica", tam_bsp_conica="1/4", profundidad="8 mm", punta="plana")
    assert op.p["designacion"] == "R1/4"
    r0 = (13.157 - 2 * 2 / 3 * 0.960491 * 25.4 / 19) / 2                                    # Ø menor en la boca
    r1 = r0 - 8 / 32                                                                        # conicidad 1:16
    assert antes - _volumen(doc) == pytest.approx(math.pi * 8 / 3 * (r0 * r0 + r0 * r1 + r1 * r1), rel=1e-4)
    assert any("cónico" in r.mensaje for r in doc.resultados if r.mensaje)


def test_agujero_roscado_con_tipo_tamano_designacion_y_clase():
    from omnicad.nucleo import solidos_crear as sc
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.crear import Agujero
    doc, forma, arriba = _caja_y_cara_de_arriba()
    i = sc.tamanos_rosca("iso_metrica").index("M8")
    op = _ejecutar(doc, Agujero, colocacion=[_clic(doc, forma, arriba, (20, 20, 10))], profundidad="8 mm",
                   rosca="modelada", tipo_rosca="iso_metrica", tam_iso_metrica="M8", **{f"des_iso_metrica_{i}": "M8x1"},
                   clase_iso_metrica="6H")
    assert (op.p["designacion"], op.p["clase_rosca"]) == ("M8x1", "6H")
    ctx = ContextoComando(doc, op=op)
    cmd = Agujero()
    v = cmd.desde_op(op, ctx)
    assert (v["tipo_rosca"], v["tam_iso_metrica"], v[f"des_iso_metrica_{i}"], v["clase_iso_metrica"]) == (
        "iso_metrica", "M8", "M8x1", "6H")
    texto = cmd._info(v, ctx)
    assert "M8x1" in texto and "6H" in texto and "ISO 965-1" in texto
    otra = cmd.construir({c.clave: c.defecto for c in cmd.campos(ctx)} | v, ctx)
    assert {k: otra.p[k] for k in ("designacion", "clase_rosca", "rosca")} == {
        "designacion": "M8x1", "clase_rosca": "6H", "rosca": "modelada"}


def test_agujero_hasta_una_cara_por_referencias_y_desde_boceto():
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.crear import Agujero
    doc, forma, arriba = _caja_y_cara_de_arriba(alto=20)
    plano = OpPlano(doc.nuevo_id(), "Plano", base="XY", distancia="5 mm")
    doc.agregar(plano)
    op = _ejecutar(doc, Agujero, colocacion=[_clic(doc, forma, arriba, (10, 10, 20))], extension="hasta",
                   hasta=[_h(doc, {"tipo": "plano", "id": plano.id})], diametro="4 mm", punta="plana")
    assert op.p["extension"] == "hasta"
    assert 32000 - _volumen(doc) == pytest.approx(math.pi * 4 * 15, rel=1e-6)            # de z = 20 a z = 5
    forma = doc.estado_final.cuerpos["op1.c1"].forma
    arriba = next(s for s in refs.subformas(forma, "cara") if refs.firma_cara(s)["geom"] == "plano"
                  and np.allclose(refs.firma_cara(s)["centro"][2], 20))
    aristas = [s for s in refs.subformas(forma, "arista") if refs.firma_arista(s)["geom"] == "linea"
               and np.allclose(refs.firma_arista(s)["medio"][2], 20)]
    x40 = next(s for s in aristas if np.allclose([p[0] for p in refs.firma_arista(s)["extremos"]], 40))
    y0 = next(s for s in aristas if np.allclose([p[1] for p in refs.firma_arista(s)["extremos"]], 0))
    hits = {k: [_h(doc, refs.referencia("op1.c1", s, forma))] for k, s in
            (("ref_cara", arriba), ("ref_arista1", x40), ("ref_arista2", y0))}
    antes = _volumen(doc)
    op = _ejecutar(doc, Agujero, posicion="referencias", ref_distancia1="6 mm", ref_distancia2="9 mm",
                   diametro="3 mm", profundidad="4 mm", punta="plana", **hits)
    assert op.p["ref_cara"] and len(op.p["ref_aristas"]) == 2
    assert antes - _volumen(doc) == pytest.approx(math.pi * 2.25 * 4, rel=1e-6)
    ctx = ContextoComando(doc, op=op)
    (punto, direccion), = op._colocaciones(ctx.estado, ctx)
    assert punto == pytest.approx([34, 9, 20]) and direccion == pytest.approx([0, 0, -1])
    assert Agujero().desde_op(op, ctx)["posicion"] == "referencias"
    b = Boceto()
    pids = [b.agregar_punto(5, 35), b.agregar_punto(35, 35)]
    sk = OpBoceto(doc.nuevo_id(), plano="cara", marco=g.plano_de_cara(arriba).marco(), boceto=b)
    doc.agregar(sk)
    antes = _volumen(doc)
    op = _ejecutar(doc, Agujero, posicion="boceto", diametro="2 mm", profundidad="3 mm", punta="plana",
                   puntos_boceto=[_h(doc, {"tipo": "punto_boceto", "boceto": sk.id, "punto": p}) for p in pids])
    assert antes - _volumen(doc) == pytest.approx(2 * math.pi * 3, rel=1e-6)
    assert Agujero().desde_op(op, ContextoComando(doc, op=op))["posicion"] == "boceto"


def test_agujero_de_una_receta_vieja_da_el_mismo_volumen():
    """Una receta de antes de la clase, la holgura y la extensión «hasta» (sin esas claves) se calcula igual."""
    from omnicad.nucleo import solidos_crear as sc
    from omnicad.timeline.operaciones import operacion_desde_dict
    doc, forma, arriba = _caja_y_cara_de_arriba()
    vieja = {"tipo": "agujero", "id": "op2", "nombre": "Agujero1", "params": {
        "posiciones": [], "puntos_cara": [{"cara": refs.referencia("op1.c1", arriba, forma), "punto": [20, 20, 10]}],
        "tipo": "simple", "diametro": "6 mm", "extension": "distancia", "profundidad": "4 mm", "punta": "angulo",
        "angulo_punta": "118 deg", "diam_abocardado": "10 mm", "prof_abocardado": "4 mm", "diam_avellanado": "12 mm",
        "angulo_avellanado": "90 deg", "rosca": "modelada", "designacion": "M6", "invertir": False, "objetivos": []}}
    doc.agregar(operacion_desde_dict(vieja))
    herramienta = sc.herramienta_agujero((20, 20, 10), (0, 0, -1), profundidad=4, roscado="M6", diametro=6)
    esperado = g.volumen(g.booleano(forma, herramienta, "cortar"))
    assert _volumen(doc) == pytest.approx(esperado, rel=1e-9)


def test_rosca_dialogo_tipo_tamano_designacion_clase_y_recordar():
    from omnicad.nucleo import solidos_crear as sc
    from omnicad.timeline.ops_solido import OpRosca
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.crear import Rosca
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="cilindro", radio="10", alto="20"))
    forma = doc.estado_final.cuerpos["op1.c1"].forma
    lateral = next(s for s in refs.subformas(forma, "cara") if refs.firma_cara(s)["geom"] == "cilindro")
    cara = [_h(doc, refs.referencia("op1.c1", lateral, forma))]
    Rosca._recuerdo = {}
    op = _ejecutar(doc, Rosca, caras=cara, tipo_rosca="trapezoidal", tam_trapezoidal="Tr20", recordar=True,
                   largo_completo=False, longitud="12 mm")
    assert (op.p["designacion"], op.p["familia"], op.p["clase_rosca"]) == ("Tr20x4", "trapezoidal", "")
    d1 = sc.datos_rosca("Tr20x4")["diametro_menor"]
    quitado = math.pi * 100 * 20 - _volumen(doc)
    assert quitado == pytest.approx(0.5 * math.pi * (100 - (d1 / 2) ** 2) * 12, rel=0.03)  # perfil simétrico de 30°
    ctx = ContextoComando(doc)
    campos = {c.clave: c for c in Rosca().campos(ctx)}
    assert campos["tipo_rosca"].defecto == "trapezoidal" and campos["tam_trapezoidal"].defecto == "Tr20"
    assert campos["recordar"].defecto is True
    v = Rosca().desde_op(op, ContextoComando(doc, op=op))
    assert (v["tipo_rosca"], v["tam_trapezoidal"]) == ("trapezoidal", "Tr20")
    Rosca._recuerdo = {}
    # métrica automática según la cara con clase 6g: la clase llega al paso y a la información del diálogo
    doc2 = Documento()
    doc2.agregar(OpPrimitiva(doc2.nuevo_id(), forma="cilindro", radio="5", alto="12"))
    forma2 = doc2.estado_final.cuerpos["op1.c1"].forma
    lat2 = next(s for s in refs.subformas(forma2, "cara") if refs.firma_cara(s)["geom"] == "cilindro")
    caras2 = [_h(doc2, refs.referencia("op1.c1", lat2, forma2))]
    op = _ejecutar(doc2, Rosca, caras=caras2, clase_iso_metrica="6g", largo_completo=False, longitud="6 mm")
    assert (op.p["designacion"], op.p["clase_rosca"]) == ("", "6g") and op.roscas[0]["designacion"] == "M10x1.5"
    v = {c.clave: c.defecto for c in Rosca().campos(ContextoComando(doc2))} | {"caras": caras2, "tam_iso_metrica": "M10",
                                                                             "clase_iso_metrica": "6g"}
    assert "9.732–9.968" in Rosca()._info(v, ContextoComando(doc2))
    # receta vieja (sin familia ni clase): el diálogo la muestra sin clase, para no cambiar su geometría al editar
    vieja = OpRosca("op9", "Rosca9", caras=[c["ref"] for c in caras2], designacion="M10")
    v = Rosca().desde_op(vieja, ContextoComando(doc2))
    assert v["clase_iso_metrica"] == "" and v["tipo_rosca"] == "iso_metrica"


def test_paneles_de_agujero_y_rosca_cambian_campos_y_calculan_la_vista_previa():
    """El panel real: cada tipo de rosca muestra sus campos (tamaño por tipo, designación por tamaño) y la vista
    previa sale sin error."""
    from omnicad.ui.comando import ContextoComando, PanelComando
    from omnicad.ui.comandos.crear import Agujero, Rosca
    from omnicad.ui.visor3d import Visor3D
    doc, forma, arriba = _caja_y_cara_de_arriba()
    visor = Visor3D()
    visor.set_modelo(doc.estado_final)
    panel = PanelComando(Agujero(), ContextoComando(doc), visor, {"colocacion": [_clic(doc, forma, arriba, (20, 20, 10))]})

    def visibles():
        return {c.clave for c in panel.campos if panel._visible(c)}
    assert {"colocacion", "diametro"} <= visibles() and "tam_holgura" not in visibles()
    for rosca, deben, no in (("holgura", {"tam_holgura", "ajuste", "info_rosca"}, {"diametro", "tipo_rosca"}),
                             ("modelada", {"tipo_rosca", "tam_iso_metrica", "clase_iso_metrica", "holgura_3d"},
                              {"diametro", "tam_holgura"}),
                             ("cosmetica", {"tipo_rosca", "diametro"}, {"clase_iso_metrica", "holgura_3d"}),
                             ("conico", {"tipo_conica", "tam_bsp_conica"}, {"tipo_rosca"})):
        panel.set_valor("rosca", rosca)
        panel._calcular_previa()
        assert deben <= visibles() and not (no & visibles()), rosca
        assert panel.ultima_op is not None and panel._previa_ok, (rosca, panel.mensaje.text())
    panel.set_valor("rosca", "modelada")
    panel.set_valor("tipo_rosca", "unificada")
    assert {"tam_unificada", "clase_unificada"} <= visibles() and "tam_iso_metrica" not in visibles()
    panel.set_valor("posicion", "referencias")
    assert {"ref_cara", "ref_arista1", "ref_distancia1"} <= visibles() and "colocacion" not in visibles()
    panel.set_valor("extension", "hasta")
    assert {"hasta", "desfase_hasta"} <= visibles()
    panel.cancelar()
    doc2 = Documento()
    doc2.agregar(OpPrimitiva(doc2.nuevo_id(), forma="cilindro", radio="5", alto="12"))
    forma2 = doc2.estado_final.cuerpos["op1.c1"].forma
    lateral = next(s for s in refs.subformas(forma2, "cara") if refs.firma_cara(s)["geom"] == "cilindro")
    panel = PanelComando(Rosca(), ContextoComando(doc2), visor,
                         {"caras": [_h(doc2, refs.referencia("op1.c1", lateral, forma2))], "modelada": False})
    panel.set_valor("tipo_rosca", "iso_metrica")
    panel.set_valor("tam_iso_metrica", "M10")
    panel._calcular_previa()
    assert "M10x1.5" in panel.widgets["info_rosca"].text() and "6g" in panel.widgets["info_rosca"].text()
    from omnicad.nucleo import solidos_crear as sc
    i = sc.tamanos_rosca("iso_metrica").index("M10")
    assert f"des_iso_metrica_{i}" in visibles()                       # M10 tiene tres pasos: hay que elegir
    panel.cancelar()


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


def _placa_y_agujero():
    """Placa 100 × 60 × 10 (op1), boceto «Puntos» con un punto en (10, 10) (op2) y «Agujero1» Ø6 pasante ahí (op3)."""
    from omnicad.timeline.ops_solido import OpAgujero
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="100", largo="60", alto="10"))
    b = Boceto()
    pid = b.agregar_punto(10, 10)
    sk = OpBoceto(doc.nuevo_id(), "Puntos", plano="XY", boceto=b)
    doc.agregar(sk)
    punto = {"tipo": "punto_boceto", "boceto": sk.id, "punto": pid}
    doc.agregar(OpAgujero(doc.nuevo_id(), "Agujero1", posiciones=[punto], diametro="6 mm", extension="todo",
                          invertir=True))
    return doc, punto


def test_patron_de_operaciones_y_en_puntos_por_el_dialogo():
    """Tipo de objeto «Operaciones»: el agujero (por su nombre en el timeline) se repite sobre la placa."""
    from omnicad.ui.comando import ContextoComando, ErrorComando
    from omnicad.ui.comandos import comando_para
    from omnicad.ui.comandos.crear import PatronRectangular
    from omnicad.ui.comandos.patrones import PatronPuntos
    doc, punto = _placa_y_agujero()
    agujero = math.pi * 9 * 10
    op = _ejecutar(doc, PatronRectangular, objeto="operaciones", pasos="Agujero1",
                   dir1=[_h(doc, {"tipo": "eje", "id": "X"})], n1=3, d1="20 mm", distribucion="espaciado")
    assert (op.p["objeto"], op.p["pasos"], op.p["cuerpos"]) == ("operaciones", ["op3"], [])
    forma = doc.estado_final.cuerpos["op1.c1"].forma
    assert g.es_valida(forma) and g.volumen(forma) == pytest.approx(60000 - 3 * agujero, rel=1e-9)
    editar = ContextoComando(doc, op=op)
    v = PatronRectangular().desde_op(op, editar)
    assert v["objeto"] == "operaciones" and v["pasos"] == "Agujero1"
    assert PatronRectangular().construir(v, editar).p == op.p
    ctx = ContextoComando(doc)
    with pytest.raises(ErrorComando, match="no deja una herramienta"):
        PatronRectangular().construir(dict(v, pasos="Puntos"), ctx)
    with pytest.raises(ErrorComando, match="No hay un paso"):
        PatronRectangular().construir(dict(v, pasos="Agujero9"), ctx)
    # en puntos: los puntos sueltos de otro boceto; la referencia es el punto del agujero
    b = Boceto()
    b.agregar_punto(90, 50)
    b.agregar_punto(90, 10)
    sk = OpBoceto(doc.nuevo_id(), plano="XY", boceto=b)
    doc.agregar(sk)
    op = _ejecutar(doc, PatronPuntos, objeto="operaciones", pasos="op3",
                   puntos=[_h(doc, {"tipo": "boceto", "boceto": sk.id})], referencia=[_h(doc, punto)])
    assert op.p["forma_patron"] == "puntos" and comando_para(op) is PatronPuntos
    assert g.volumen(doc.estado_final.cuerpos["op1.c1"].forma) == pytest.approx(60000 - 5 * agujero, rel=1e-9)
    editar = ContextoComando(doc, op=op)
    v = PatronPuntos().desde_op(op, editar)
    assert PatronPuntos().construir(v, editar).p == op.p
    with pytest.raises(ErrorComando, match="los puntos"):
        PatronPuntos().construir(dict(v, puntos=[]), ContextoComando(doc))


def test_patron_en_ruta_con_giro_y_multitransformar_por_el_dialogo():
    from omnicad.timeline.ops_solido import OpMultitransformar
    from omnicad.ui.comando import ContextoComando, ErrorComando
    from omnicad.ui.comandos import comando_para
    from omnicad.ui.comandos.crear import PatronRuta
    from omnicad.ui.comandos.patrones import Multitransformar
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="2", largo="2", alto="20", x="-1", y="-1"))
    br, ids = _boceto(doc, plano="XY", lineas=[((0, 0), (100, 0))])
    c = _h(doc, {"tipo": "cuerpo", "cuerpo": "op1.c1"})
    op = _ejecutar(doc, PatronRuta, cuerpos=[c], ruta=_curvas(doc, br, ids), n1=3, d1="100 mm", giro="90 deg")
    assert op.p["giro"] == "90 deg"
    (x0, y0, z0), (x1, y1, z1) = g.caja_envolvente(doc.estado_final.cuerpos[f"{op.id}.c2"].forma)
    assert (x1 - x0, y1 - y0, z1 - z0) == pytest.approx((2, 20, 2))            # acostada: giró 90° sobre la ruta
    # multitransformación: patrón de 3 en Y + simetría en YZ = 6 instancias (5 cuerpos nuevos)
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="5", largo="5", alto="5", x="10"))
    caja = _h(doc, {"tipo": "cuerpo", "cuerpo": doc.operaciones[-1].id + ".c1"})
    op = _ejecutar(doc, Multitransformar, cuerpos=[caja], t1_tipo="rectangular",
                   t1_dir=[_h(doc, {"tipo": "eje", "id": "Y"})], t1_n=3, t1_d="20 mm", t1_distribucion="espaciado",
                   t2_tipo="simetria", t2_plano=[_h(doc, {"tipo": "plano", "id": "YZ"})])
    assert [t["tipo"] for t in op.p["transformaciones"]] == ["rectangular", "simetria"]
    nuevos = [k for k in doc.estado_final.cuerpos if k.startswith(op.id)]
    assert len(nuevos) == 5 and all(g.volumen(doc.estado_final.cuerpos[k].forma) == pytest.approx(125) for k in nuevos)
    assert comando_para(op) is Multitransformar
    editar = ContextoComando(doc, op=op)
    v = Multitransformar().desde_op(op, editar)
    assert (v["t1_tipo"], v["t2_tipo"], v["t3_tipo"]) == ("rectangular", "simetria", "ninguna")
    assert Multitransformar().construir(v, editar).p == op.p
    with pytest.raises(ErrorComando, match="seleccioná el eje"):
        Multitransformar().construir(dict(v, t1_tipo="circular", t1_eje=[]), editar)
    # una multitransformación de la API con una transformación que el diálogo no edita: Aceptar la conserva
    api_op = OpMultitransformar(doc.nuevo_id(), cuerpos=[caja["ref"]["cuerpo"]], transformaciones=[
        {"tipo": "puntos", "coordenadas": [[0, 0, 50]]}])
    assert doc.agregar(api_op).estado == "ok"
    editar = ContextoComando(doc, op=api_op)
    v = Multitransformar().desde_op(api_op, editar)
    assert v["_fijas"] and Multitransformar().construir(v, editar).p == api_op.p


def test_panel_de_multitransformar_y_patron_de_operaciones():
    """El panel real (un visor sin ventana): las ranuras de transformación aparecen de a una, «Tipo de objeto» cambia
    cuerpos por operaciones y la vista previa arma el paso."""
    from omnicad.ui.comando import ContextoComando, PanelComando
    from omnicad.ui.comandos.crear import PatronCircular
    from omnicad.ui.comandos.patrones import Multitransformar
    from omnicad.ui.visor3d import Visor3D

    class Ventana:
        def __init__(self, doc, visor):
            self.doc, self.visor = doc, visor

        def info_seleccion(self, texto):
            pass

    doc, _ = _placa_y_agujero()
    visor = Visor3D()
    visor.set_modelo(doc.estado_final)
    ctx = ContextoComando(doc, Ventana(doc, visor))
    panel = PanelComando(Multitransformar(), ctx, visor)
    campos = {c.clave: c for c in panel.campos}
    visibles = lambda: {k for k, c in campos.items() if panel._visible(c)}  # noqa: E731
    assert {"cuerpos", "t1_tipo", "t1_dir", "t1_n", "t1_d", "t2_tipo"} <= visibles()
    assert not {"pasos", "t2_plano", "t3_tipo", "fijas"} & visibles()
    panel.set_valor("t2_tipo", "simetria")
    panel.set_valor("objeto", "operaciones")
    assert {"t2_plano", "t3_tipo", "pasos"} <= visibles() and not {"cuerpos", "combinar"} & visibles()
    panel.cancelar()
    panel = PanelComando(PatronCircular(), ctx, visor, {"objeto": "operaciones", "pasos": "Agujero1",
                                                        "eje": [_h(doc, {"tipo": "eje", "id": "Z"})], "n": 4})
    panel._calcular_previa()
    assert panel.ultima_op is not None and panel.ultima_op.p["pasos"] == ["op3"]
    panel.cancelar()


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


def test_engranaje_par_con_ensamblaje_y_eje_por_dialogo():
    """CREAR › Engranaje: el campo Medidas calcula antes de crear; con «Par de engranajes» y «Crear unión y vínculo»,
    al aceptar se agregan componentes, uniones y vínculo en el mismo paso de deshacer. CREAR › Eje: tabla de tramos."""
    from PySide6.QtWidgets import QApplication

    from omnicad.nucleo import engranajes as en
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos import CATALOGO, comando_para
    from omnicad.ui.comandos.engranaje import Eje, Engranaje
    assert CATALOGO["engranaje"] is Engranaje and CATALOGO["eje_escalonado"] is Eje
    doc = Documento()
    cmd, ctx = Engranaje(), ContextoComando(doc)
    campos = {c.clave: c for c in cmd.campos(ctx)}
    v = {k: (list(c.defecto) if isinstance(c.defecto, list) else c.defecto) for k, c in campos.items()}
    v.update(par=True, ancho="4 mm")
    texto = campos["medidas"].funcion(v, ctx)
    assert "Ø primitivo 40 · exterior 44 · fondo 35" in texto and "Distancia entre centros 60 mm" in texto
    assert campos["dientes2"].visible_si(v) and not campos["alto"].visible_si(v)
    op = cmd.construir(v, ctx)
    cmd.al_cerrar(ctx)                    # como al aceptar: el ensamblaje espera a que la ventana agregue el paso
    pila = len(doc._deshacer)
    assert doc.agregar(op).estado == "ok"
    QApplication.processEvents()
    assert [o.TIPO for o in doc.operaciones] == ["engranaje", "componente", "componente", "union", "union",
                                                 "vinculo_movimiento"]
    assert all(r.estado == "ok" for r in doc.resultados) and len(doc._deshacer) == pila + 1
    cancelado = cmd.construir(v, ctx)                 # un diálogo cancelado: su paso nunca entró al documento
    assert Engranaje.ensamblar_si_aceptado(ctx, cancelado) is None and len(doc.operaciones) == 6
    assert comando_para(op) is Engranaje
    editar = ContextoComando(doc, op=op)
    assert "ensamblar" not in {c.clave for c in Engranaje().campos(editar)}
    v2 = Engranaje().desde_op(op, editar)
    assert Engranaje().construir(v2, editar).p == op.p
    # rueda de cadena y cremallera por el mismo diálogo
    texto = campos["medidas"].funcion(dict(v, tipo="rueda_cadena", cadena="08B", dientes="20", par=False), ctx)
    assert "ancho de diente ISO 7.208 mm" in texto
    op = _ejecutar(doc, Engranaje, tipo="cremallera", dientes="4", ancho="3 mm")
    assert op.p["tipo"] == "cremallera" and _ultimo(doc).nombre == "Cremallera m2"
    # eje escalonado: 2 tramos con chaflán al final del segundo
    op = _ejecutar(doc, Eje, n=2, d1="10 mm", l1="8 mm", ini1="ninguno", d2="6 mm", l2="20 mm", fin2="chaflan",
                   mf2="0.5 mm")
    assert len(op.p["tramos"]) == 2
    tramos = [{"diametro": 10, "largo": 8}, {"diametro": 6, "largo": 20, "fin": "chaflan", "medida_fin": 0.5}]
    assert g.volumen(_ultimo(doc).forma) == pytest.approx(en.volumen_eje(tramos), rel=1e-9)
    v3 = Eje().desde_op(op, ContextoComando(doc, op=op))
    assert v3["n"] == 2 and (v3["d2"], v3["fin2"], v3["mf2"]) == ("6 mm", "chaflan", "0.5 mm")
