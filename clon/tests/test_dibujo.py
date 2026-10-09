# -*- coding: utf-8 -*-
"""Espacio DIBUJO: proyecciones con líneas ocultas, vistas (base, proyectadas, sección, detalle), cotas,
cajetín, lista de piezas, persistencia y la ventana (PDF, DXF, herramienta de cota, actualización)."""
import json
import math
import os
import re

import numpy as np
import pytest

from omnicad.io_archivos import dxf
from omnicad.nucleo import dibujo as nd
from omnicad.nucleo import geometria as geo


@pytest.fixture(scope="module")
def caja():
    return geo.caja(10, 20, 30)


@pytest.fixture(scope="module")
def pieza_agujero():
    """Caja 10×20×30 con un agujero pasante vertical de radio 3 en (5, 10)."""
    return geo.booleano(geo.caja(10, 20, 30), geo.cilindro(3, 30, base=(5, 10, 0)), "cortar")


@pytest.fixture(scope="module")
def tubo():
    return geo.booleano(geo.cilindro(10, 30), geo.cilindro(6, 30), "cortar")


def _dibujo(formas, tamano="A3"):
    d = nd.Dibujo(tamano)
    d.actualizar(formas, {k: f"Pieza {k}" for k in formas})
    return d


# ---------------------------------------------------------------- proyecciones
def test_frontal_de_caja_es_rectangulo_10x30(caja):
    p = nd.proyectar(caja, nd.marco_orientacion("frontal"))
    assert geo.es_valida(caja)
    assert len(p["visibles"]) == 4
    assert nd.caja_2d(p["visibles"]) == pytest.approx((0, 0, 10, 30))
    assert not p["ocultas"] and not p["silueta_oculta"] and not p["tangentes"]
    d = _dibujo({"c": caja})
    v = d.agregar_vista_base(["c"], "frontal", posicion=(100, 100), escala=0.5)
    x0, y0, x1, y1 = v.caja_hoja(0.0)
    assert (x1 - x0, y1 - y0) == pytest.approx((5.0, 15.0))       # en la hoja, a escala 1:2
    assert (x0 + x1) / 2 == pytest.approx(100) and (y0 + y1) / 2 == pytest.approx(100)


def test_agujero_pasante_da_ocultas_en_la_lateral(pieza_agujero):
    assert geo.es_valida(pieza_agujero)
    p = nd.proyectar(pieza_agujero, nd.marco_orientacion("derecha"))
    assert nd.caja_2d(p["visibles"]) == pytest.approx((0, 0, 20, 30))
    ocultas = p["ocultas"] + p["silueta_oculta"]
    assert sorted(round(float(pl[:, 0].mean()), 6) for pl in ocultas) == [7.0, 13.0]   # 10 ± 3
    for pl in ocultas:
        assert np.ptp(pl[:, 1]) == pytest.approx(30.0)


def test_ocultas_superpuestas_no_se_dibujan(pieza_agujero):
    p = nd.proyectar(pieza_agujero, nd.marco_orientacion("superior"))
    assert p["ocultas"] == []      # la circunferencia de abajo cae sobre la de arriba
    assert len(p["visibles"]) == 5


def test_isometrica_coincide_con_la_proyeccion_de_los_vertices(caja):
    m = nd.marco_orientacion("iso_se")
    p = nd.proyectar(caja, m)
    esq = m.a_2d([[x, y, z] for x in (0, 10) for y in (0, 20) for z in (0, 30)])
    assert nd.caja_2d(p["visibles"]) == pytest.approx((*esq.min(0), *esq.max(0)))
    assert len(p["visibles"]) == 9 and len(p["ocultas"]) == 3


def test_metodo_rapido_da_el_mismo_contorno(pieza_agujero):
    p = nd.proyectar(pieza_agujero, nd.marco_orientacion("derecha"), metodo="rapido")
    assert nd.caja_2d(p["visibles"]) == pytest.approx((0, 0, 20, 30), abs=1e-3)
    assert len(p["ocultas"] + p["silueta_oculta"]) >= 2


def test_tangentes_de_un_empalme():
    from OCP.BRepFilletAPI import BRepFilletAPI_MakeFillet
    from OCP.TopAbs import TopAbs_EDGE
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS
    b = geo.caja(40, 30, 20)
    mk = BRepFilletAPI_MakeFillet(b)
    ex = TopExp_Explorer(b, TopAbs_EDGE)
    while ex.More():
        mk.Add(3.0, TopoDS.Edge(ex.Current()))
        ex.Next()
    p = nd.proyectar(mk.Shape(), nd.marco_orientacion("iso_se"))
    assert len(p["tangentes"]) > 0 and len(p["silueta"]) > 0


def test_marcas_y_lineas_de_centro(pieza_agujero):
    circ = nd.circulos_de_frente(pieza_agujero, nd.marco_orientacion("superior"))
    assert len(circ) == 1
    centro, r, completo = circ[0]
    assert centro == pytest.approx((5, 10)) and r == pytest.approx(3) and completo
    ejes = nd.ejes_de_cilindros(pieza_agujero, nd.marco_orientacion("frontal"))
    assert len(ejes) == 1
    a, b = ejes[0]
    assert sorted([tuple(np.round(a, 6)), tuple(np.round(b, 6))]) == [(5.0, 0.0), (5.0, 30.0)]
    prims = nd.dibujar_marca_centro((0, 0), 3)
    assert all(c == "CENTRO" for c, _ in prims)
    assert max(abs(q) for _, pr in prims for pt in pr[1:] for q in pt) == pytest.approx(3 + nd.SOBREPASO_EJE)


# ---------------------------------------------------------------- vistas proyectadas
def _iguales(m1, m2):
    return all(np.allclose(getattr(m1, k), getattr(m2, k)) for k in ("e", "x", "y"))


def test_proyectadas_en_primer_y_tercer_diedro():
    frente = nd.marco_orientacion("frontal")
    assert _iguales(nd.marco_proyectado(frente, (1, 0), "tercero"), nd.marco_orientacion("derecha"))
    assert _iguales(nd.marco_proyectado(frente, (1, 0), "primero"), nd.marco_orientacion("izquierda"))
    assert _iguales(nd.marco_proyectado(frente, (0, -1), "primero"), nd.marco_orientacion("superior"))
    assert _iguales(nd.marco_proyectado(frente, (0, 1), "tercero"), nd.marco_orientacion("superior"))
    assert _iguales(nd.marco_proyectado(frente, (0, -1), "tercero"), nd.marco_orientacion("inferior"))
    assert _iguales(nd.marco_proyectado(frente, (1, 1), "tercero"), nd.marco_orientacion("iso_se"))
    assert nd.direccion_proyectada(10, 1) == (1, 0) and nd.direccion_proyectada(10, 9) == (1, 1)


def test_vista_proyectada_alineada_con_la_base(caja):
    d = _dibujo({"c": caja})
    base = d.agregar_vista_base(["c"], "frontal", posicion=(100, 200), escala=1)
    derecha = d.agregar_vista_proyectada(base.id, (200, 215))      # el clic quedó 15 mm más arriba
    assert derecha.direccion == (1, 0) and derecha.escala == 1
    assert derecha.posicion[1] == pytest.approx(200)               # alineada en altura con la base
    x0, y0, x1, y1 = derecha.caja_hoja(0.0)
    assert (x1 - x0, y1 - y0) == pytest.approx((20, 30))           # 1.er diedro: se ve desde la izquierda
    d.mover(derecha.id, (30, 40))                                  # solo se corre en horizontal
    assert derecha.posicion == pytest.approx((230, 200))
    d.mover(base.id, (0, -10))                                     # la padre arrastra a sus proyectadas
    assert derecha.posicion == pytest.approx((230, 190))
    assert base.posicion == pytest.approx((100, 190))


# ---------------------------------------------------------------- sección y detalle
def test_seccion_de_tubo_da_dos_rectangulos_rayados(tubo):
    d = _dibujo({"t": tubo})
    base = d.agregar_vista_base(["t"], "frontal", posicion=(150, 180), escala=1)
    s = d.agregar_vista_seccion(base.id, base.a_hoja((0, -5)), base.a_hoja((0, 35)), (300, 170))
    assert s.etiqueta == "A" and s.lado == -1 and not s.error
    assert s.posicion[1] == pytest.approx(180)                      # alineada con la padre
    assert len(s.regiones) == 2
    for reg in s.regiones:
        assert len(reg) == 1
        assert abs(nd.area_lazo(reg[0])) == pytest.approx(4 * 30, rel=1e-6)
        x0, y0, x1, y1 = nd.caja_2d(reg)
        assert (x1 - x0, y1 - y0) == pytest.approx((4, 30))
    assert len(s.rayado) >= 18                 # ~ (4 + 30)/√2 / 2,5 ≈ 9,6 líneas por franja
    cajas = [nd.caja_2d(reg) for reg in s.regiones]
    for seg in s.rayado:
        m = seg.mean(0)
        assert any(c[0] - 1e-6 <= m[0] <= c[2] + 1e-6 and c[1] - 1e-6 <= m[1] <= c[3] + 1e-6 for c in cajas)
        dv = seg[1] - seg[0]
        assert abs(abs(math.degrees(math.atan2(dv[1], dv[0]))) - 45) < 1e-6
    prims = d.primitivas_vista(s)
    assert sum(1 for c, _ in prims if c == "RAYADO") == len(s.rayado)
    assert any(p[0] == "texto" and p[3] == "A-A" for _, p in prims)
    forma, _, _ = nd.cortar_por_linea(tubo, base.marco, (0, -5), (0, 35), lado=-1)
    assert geo.es_valida(forma)
    assert geo.volumen(forma) == pytest.approx(math.pi * (100 - 36) * 30 / 2)


def test_rayado_respeta_agujeros():
    cuadrado = np.array([(0, 0.5), (10, 0.5), (10, 10.5), (0, 10.5)], float)
    hueco = np.array([(4, 4.5), (6, 4.5), (6, 6.5), (4, 6.5)], float)
    segs = nd.rayado([cuadrado, hueco], 0.0, 1.0)            # horizontales en y = 1 … 10
    largo = sum(float(np.linalg.norm(s[1] - s[0])) for s in segs)
    assert largo == pytest.approx(10 * 10 - 2 * 2)            # 10 líneas; 2 cruzan el hueco de 2 mm
    assert len(segs) == 12


def test_detalle_recorta_y_amplia(pieza_agujero):
    d = _dibujo({"c": pieza_agujero})
    base = d.agregar_vista_base(["c"], "frontal", posicion=(100, 150), escala=1)
    det = d.agregar_vista_detalle(base.id, base.a_hoja((5, 30)), 4, (250, 150))
    assert det.escala == 2 and det.radio_detalle == pytest.approx(4) and det.etiqueta == "A"
    puntos = np.concatenate([pl for c in nd.CATEGORIAS for pl in det.lineas[c]])
    assert np.linalg.norm(puntos - (5, 30), axis=1).max() <= 4 + 1e-9
    assert np.linalg.norm(det.a_hoja(puntos) - det.posicion, axis=1).max() <= 8 + 1e-9
    recorte = nd.recortar_a_circulo([np.array([(-10.0, 3.0), (10.0, 3.0)])], (0, 0), 5)
    assert np.linalg.norm(recorte[0][-1] - recorte[0][0]) == pytest.approx(8.0)   # cuerda 2·√(25−9)
    textos = [p[3] for _, p in d.primitivas_vista(det) if p[0] == "texto"]
    assert "A (2:1)" in textos


# ---------------------------------------------------------------- cotas
def test_cotas_miden_el_modelo_y_no_la_hoja(pieza_agujero):
    d = _dibujo({"c": pieza_agujero})
    b = d.agregar_vista_base(["c"], "frontal", posicion=(100, 150), escala=2)
    sup = d.agregar_vista_proyectada(b.id, (100, 60))
    h = d.agregar_cota("horizontal", b.id, [b.a_hoja((0, 0)), b.a_hoja((10, 0))], b.a_hoja((5, -6)))
    v = d.agregar_cota("vertical", b.id, [b.a_hoja((10, 0)), b.a_hoja((10, 30))], b.a_hoja((16, 15)))
    a = d.agregar_cota("alineada", b.id, [b.a_hoja((0, 0)), b.a_hoja((10, 30))], b.a_hoja((0, 20)))
    assert d.texto_cota(h) == "10" and d.texto_cota(v) == "30"
    assert d.valor_cota(a) == pytest.approx(math.sqrt(1000))
    c, r, _ = sup.circulos[0]
    radio = d.agregar_cota("radio", sup.id, [sup.a_hoja(c)], sup.a_hoja(c) + (12, 8), radio=r * sup.escala)
    diam = d.agregar_cota("diametro", sup.id, [sup.a_hoja(c)], sup.a_hoja(c) + (12, 8), radio=r * sup.escala)
    assert d.texto_cota(radio) == "R3" and d.texto_cota(diam) == "⌀6"
    ang = d.agregar_cota("angulo", b.id, [b.a_hoja((0, 0)), b.a_hoja((10, 0)), b.a_hoja((0, 0)), b.a_hoja((0, 30))],
                         b.a_hoja((4, 4)))
    assert d.valor_cota(ang) == pytest.approx(90) and d.texto_cota(ang) == "90°"
    ox = d.agregar_cota("ordenada_x", b.id, [b.a_hoja((0, 0)), b.a_hoja((10, 30))], b.a_hoja((10, 40)))
    oy = d.agregar_cota("ordenada_y", b.id, [b.a_hoja((0, 0)), b.a_hoja((10, 30))], b.a_hoja((20, 30)))
    assert d.valor_cota(ox) == pytest.approx(10) and d.valor_cota(oy) == pytest.approx(30)
    prims = d.primitivas_anotacion(h)
    assert sum(1 for _, p in prims if p[0] == "solido") == 2
    antes = np.array(prims[-1][1][1])
    d.mover(b.id, (7, 0))                                     # la cota acompaña a su vista
    assert np.array(d.primitivas_anotacion(h)[-1][1][1]) == pytest.approx(antes + (7, 0))
    assert d.texto_cota(h) == "10"
    with pytest.raises(geo.ErrorGeometria):
        d.agregar_cota("angulo", b.id, [b.a_hoja((0, 0)), b.a_hoja((10, 0)), b.a_hoja((0, 5)), b.a_hoja((10, 5))],
                       b.a_hoja((4, 4)))


def test_sector_angular_elige_el_angulo_del_cursor():
    v, t0, barrido = nd.sector_angular((0, 0), (10, 0), (0, 0), (10, 10), (5, 1))
    assert v == pytest.approx((0, 0)) and math.degrees(barrido) == pytest.approx(45)
    _, t0, barrido = nd.sector_angular((0, 0), (10, 0), (0, 0), (10, 10), (-5, 1))
    assert math.degrees(barrido) == pytest.approx(135) and math.degrees(t0) == pytest.approx(45)
    _, t0, barrido = nd.sector_angular((0, 0), (10, 0), (0, 0), (10, 10), (1, -5))
    assert math.degrees(barrido) == pytest.approx(135) and math.degrees(t0) == pytest.approx(225)
    prims, grados = nd.dibujar_cota_angular((0, 0), (10, 0), (0, 0), (10, 10), (-5, 1))
    assert grados == pytest.approx(135) and prims[-1][1][3] == "135°"


# ---------------------------------------------------------------- hoja, cajetín, lista de piezas
def test_hojas_y_escalas():
    assert nd.tamano_hoja("A4") == (297, 210)
    assert nd.tamano_hoja("A0", "vertical") == (841, 1189)
    assert nd.tamano_hoja("ANSI B") == pytest.approx((431.8, 279.4))
    with pytest.raises(geo.ErrorGeometria):
        nd.tamano_hoja("A7")
    assert nd.leer_escala("1:2") == 0.5 and nd.leer_escala("2:1") == 2 and nd.leer_escala("0,25") == 0.25
    assert nd.leer_escala("1/5") == pytest.approx(0.2)
    with pytest.raises(geo.ErrorGeometria):
        nd.leer_escala("doble")
    assert nd.texto_escala(0.5) == "1:2" and nd.texto_escala(5) == "5:1"
    assert nd.escala_automatica(400, 100, 400, 250) == 0.2      # 400 mm en 40 % de 400 mm → 1:5


def test_cajetin_y_marco():
    d = nd.Dibujo("A3")
    d.cajetin.update(titulo="Soporte", numero_pieza="FC-001", autor="Gerardo", material="Acero")
    prims = d.primitivas_hoja()
    textos = [p[3] for _, p in prims if p[0] == "texto"]
    for t in ("Soporte", "FC-001", "Gerardo", "Acero", "A3", "1 / 1", "Título", "Material"):
        assert t in textos
    for t in [str(i) for i in range(1, 9)] + list("ABCDEF"):   # zonas de un A3 (ISO 5457): 8 × 6
        assert textos.count(t) == 2
    marco = [p for c, p in prims if c == "MARCO"]
    assert marco[0][1] == [(10, 10), (410, 10), (410, 287), (10, 287)]
    x0, y0, x1, y1 = nd.caja_cajetin(420, 297)
    assert (x1 - x0, y1 - y0) == (nd.ANCHO_CAJETIN, nd.ALTO_CAJETIN) and x1 == 410 and y0 == 10


def test_lista_de_piezas_y_globos():
    a, b = geo.caja(10, 10, 10), geo.caja(10, 10, 10, origen=(30, 0, 0))
    d = nd.Dibujo("A3")
    d.actualizar({"a": a, "b": b}, {"a": "Base", "b": "Tapa"})
    v = d.agregar_vista_base(["a", "b"], "frontal", posicion=(150, 150), escala=1)
    filas = d.lista_piezas()
    assert filas[0][0] == "ELEMENTO" and [f[2] for f in filas[1:]] == ["Base", "Tapa"]
    g = d.agregar_globo(v.id, v.a_hoja((35, 5)), v.a_hoja((45, 20)))
    assert g["numero"] == "2"
    t = d.agregar_tabla((300, 250))
    prims = d.primitivas_anotacion(t)
    assert sum(1 for _, p in prims if p[0] == "texto") == 3 * 4


# ---------------------------------------------------------------- actualización y persistencia
def test_actualizar_recalcula_si_cambia_el_modelo(caja):
    d = _dibujo({"c": caja})
    v = d.agregar_vista_base(["c"], "frontal", posicion=(100, 100), escala=1)
    assert d.actualizar({"c": caja}) is False
    assert d.actualizar({"c": geo.caja(25, 20, 30)}) is True
    x0, _, x1, _ = v.caja_hoja(0.0)
    assert x1 - x0 == pytest.approx(25)
    d.actualizar({})
    assert "ya no existen" in v.error


def test_dibujo_ida_y_vuelta_por_dict(pieza_agujero):
    d = _dibujo({"c": pieza_agujero})
    d.cajetin["titulo"] = "Prueba"
    b = d.agregar_vista_base(["c"], "frontal", posicion=(100, 180), escala=2)
    sup = d.agregar_vista_proyectada(b.id, (100, 80))
    d.agregar_vista_seccion(sup.id, sup.a_hoja((-2, 10)), sup.a_hoja((12, 10)), (250, 80))
    d.agregar_vista_detalle(b.id, b.a_hoja((5, 30)), 6, (300, 200))
    d.agregar_cota("horizontal", b.id, [b.a_hoja((0, 0)), b.a_hoja((10, 0))], b.a_hoja((5, -6)))
    d.agregar_texto((30, 270), "Nota")
    d.agregar_nota(b.a_hoja((10, 30)), b.a_hoja((20, 40)), "Arista viva", b.id)
    d.agregar_linea_centro(b.id, b.a_hoja((0, 15)), b.a_hoja((10, 15)))
    d.agregar_marca_centro(sup.id, sup.a_hoja((5, 10)), 6)
    d.girar(sup.id, 90)
    datos = json.loads(json.dumps(d.a_dict()))
    otro = nd.Dibujo.desde_dict(datos)
    otro.actualizar({"c": pieza_agujero}, {"c": "Pieza c"})
    capas = lambda prims: sorted((c, p[0]) for c, p in prims)  # noqa: E731
    assert capas(otro.primitivas()) == capas(d.primitivas())
    assert otro.a_dict() == datos
    with pytest.raises(geo.ErrorGeometria):
        nd.Dibujo.desde_dict({"version": 99})


def test_borrar_vista_borra_sus_hijas_y_anotaciones(caja):
    d = _dibujo({"c": caja})
    b = d.agregar_vista_base(["c"], "frontal", posicion=(100, 180), escala=1)
    p = d.agregar_vista_proyectada(b.id, (100, 80))
    d.agregar_cota("horizontal", p.id, [p.a_hoja((0, 0)), p.a_hoja((10, 0))], p.a_hoja((5, -6)))
    d.agregar_texto((30, 270), "queda")
    d.borrar(b.id)
    assert d.vistas == [] and [a["tipo"] for a in d.anotaciones] == ["texto"]


# ---------------------------------------------------------------- ventana (Qt offscreen)
@pytest.fixture(scope="module")
def app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _documento(ancho="40"):
    from omnicad.timeline.documento import Documento
    from omnicad.timeline.operaciones import OpPrimitiva
    doc = Documento()
    doc.nombre = "Soporte"
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho=ancho, largo="30", alto="20"))
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="cilindro", radio="6", alto="40", x="20", y="15", z="-5",
                            operacion="cortar"))
    return doc


def test_ventana_exporta_pdf_a_escala_real(app, tmp_path):
    from omnicad.ui.dibujo import VentanaDibujo
    v = VentanaDibujo(_documento())
    v.dibujo.agregar_vista_base(["op1.c1"], "frontal", posicion=(120, 180), escala=2)
    v.redibujar()
    ruta = v.exportar_pdf(tmp_path / "plano.pdf")
    datos = (tmp_path / "plano.pdf").read_bytes()
    assert datos.startswith(b"%PDF") and len(datos) > 2000
    caja = re.search(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]", datos)
    assert caja, "el PDF no declara su MediaBox"
    ancho_mm, alto_mm = (float(x) * 25.4 / 72 for x in caja.groups())
    assert (ancho_mm, alto_mm) == pytest.approx((420, 297), abs=0.5)     # A3 horizontal, 1:1
    assert str(ruta).endswith("plano.pdf")


def test_ventana_cota_por_clics_y_dxf(app, tmp_path):
    from omnicad.ui.dibujo import HerrCota, VentanaDibujo
    v = VentanaDibujo(_documento())
    b = v.dibujo.agregar_vista_base(["op1.c1"], "frontal", posicion=(120, 180), escala=2)
    v.redibujar()
    h = HerrCota(v)
    v.usar(h)
    p1, p2 = b.a_hoja((0, 0)), b.a_hoja((40, 0))
    h.clic(p1 + (0.3, 0.2), None)            # el enganche lleva al vértice
    h.clic(p2 - (0.2, 0.3), None)
    h.clic(p1 + (40, -15), None)             # debajo de la arista: cota horizontal
    cotas = [a for a in v.dibujo.anotaciones if a["tipo"] == "cota"]
    assert len(cotas) == 1 and cotas[0]["subtipo"] == "horizontal" and v.dibujo.texto_cota(cotas[0]) == "40"
    v.exportar_dxf(tmp_path / "plano.dxf")
    leido = dxf.leer_dxf(tmp_path / "plano.dxf", con_capas=True)
    capas = {c for c, _ in leido}
    assert {"VISIBLE", "OCULTA", "CENTRO", "COTAS", "MARCO", "CAJETIN"} <= capas
    assert ("COTAS", "40") in {(c, p[3]) for c, p in leido if p[0] == "texto"}
    visibles = [p for c, p in leido if c == "VISIBLE" and p[0] == "linea"]
    largos = sorted(round(math.dist(p[1], p[2]), 6) for p in visibles)
    assert largos == [40.0, 40.0, 80.0, 80.0]            # el rectángulo 40×20 a escala 2:1
    v.deshacer()
    assert not [a for a in v.dibujo.anotaciones if a["tipo"] == "cota"]
    v.rehacer()
    assert len(v.dibujo.anotaciones) == 1


def test_ventana_herramientas_por_clics(app):
    from omnicad.ui.dibujo import HerrProyectada, HerrSeccion, HerrSeleccion, VentanaDibujo
    v = VentanaDibujo(_documento())
    d = v.dibujo
    b = d.agregar_vista_base(["op1.c1"], "frontal", posicion=(100, 200), escala=1)
    v.redibujar()
    h = HerrProyectada(v)
    v.usar(h)
    h.clic(b.posicion, None)                         # elige la vista padre
    for q in ((200, 206), (100, 110)):               # a la derecha y abajo
        q = np.array(q, float)
        h.mover(q, None)
        h.clic(q, None)
    v.usar_seleccion()
    der, sup = d.vistas[1], d.vistas[2]
    assert der.direccion == (1, 0) and sup.direccion == (0, -1)
    assert der.posicion == pytest.approx((200, 200)) and sup.posicion == pytest.approx((100, 110))
    assert np.allclose(der.marco.e, (-1, 0, 0))     # ISO: a la derecha va la vista desde la izquierda
    h = HerrSeccion(v)
    v.usar(h)
    h.clic(sup.posicion, None)
    for q in (sup.a_hoja((-5, 15)), sup.a_hoja((45, 15.5))):   # casi horizontal: se endereza
        h.clic(q, None)
    q = np.array((100.0, 40.0))
    h.mover(q, None)
    h.clic(q, None)
    s = d.vistas[-1]
    assert s.tipo == "seccion" and s.linea[0][1] == pytest.approx(s.linea[1][1])
    assert len(s.regiones) == 2 and len(v._deshacer) == 3
    sel = HerrSeleccion(v)
    v.usar(sel)
    sel.clic(der.posicion, None)
    sel.mover(der.posicion + (10, 25), None)
    sel.soltar(der.posicion + (10, 25), None)
    assert d.vista(der.id).posicion == pytest.approx((210, 200))     # alineada: solo se corre en x
    v.aplicar_hoja(norma="ASME", tamano="A2")
    assert d.diedro == "tercero" and (d.ancho, d.alto) == (594, 420)
    assert np.allclose(d.vista(der.id).marco.e, (1, 0, 0))          # ASME: desde la derecha


def test_ventana_sigue_al_modelo_y_persiste(app):
    from omnicad.timeline.operaciones import OpPrimitiva
    from omnicad.ui.dibujo import VentanaDibujo
    doc = _documento()
    v = VentanaDibujo(doc)
    b = v.dibujo.agregar_vista_base(["op1.c1"], "frontal", posicion=(120, 180), escala=1)
    v.redibujar()
    doc.reemplazar("op1", OpPrimitiva("op1", forma="caja", ancho="60", largo="30", alto="20"))
    v.actualizar()
    x0, _, x1, _ = v.dibujo.vista(b.id).caja_hoja(0.0)
    assert x1 - x0 == pytest.approx(60)
    datos = v.a_dict()
    otra = VentanaDibujo(doc)
    otra.desde_dict(datos)
    assert otra.a_dict() == datos
    assert set(otra.items) == set(v.items)
    v.modificar(lambda: v.dibujo.borrar(b.id))
    assert v.dibujo.vistas == []
    v.deshacer()
    assert len(v.dibujo.vistas) == 1 and v.dibujo.vistas[0].lineas["visibles"]
    assert len(v.cinta.no_disponibles) >= 5
