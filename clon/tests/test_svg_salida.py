# -*- coding: utf-8 -*-
"""Salida a SVG: arcos del boceto del lado correcto (se comprueba dibujando el archivo con Qt) y el SVG de líneas
ocultas del dibujo (PL9, `io_archivos/svg_salida.py`)."""
import math
import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QColor, QImage, QPainter  # noqa: E402
from PySide6.QtSvg import QSvgRenderer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.io_archivos import svg, svg_salida  # noqa: E402

ESCALA = 20          # px por mm en las imágenes de prueba


def _dibujar(ruta, ancho_mm, alto_mm):
    QApplication.instance() or QApplication([])      # con QApplication: otras pruebas del archivo crean ventanas
    img = QImage(int(ancho_mm * ESCALA), int(alto_mm * ESCALA), QImage.Format_ARGB32)
    img.fill(QColor("white"))
    pintor = QPainter(img)
    QSvgRenderer(str(ruta)).render(pintor)
    pintor.end()
    return img


def _hay_trazo(img, x_mm, y_mm, alto_mm, x0=0.0, y0=0.0):
    """¿Hay algo oscuro cerca del punto (x, y) del dibujo (Y hacia arriba)? (x0, y0): esquina inferior izquierda del
    dibujo, que el archivo pone en su origen."""
    px, py = int((x_mm - x0) * ESCALA), int((alto_mm - (y_mm - y0)) * ESCALA)
    return any(img.pixelColor(px + dx, py + dy).red() < 200 for dx in range(-3, 4) for dy in range(-3, 4))


def test_el_arco_del_boceto_sale_del_lado_correcto(tmp_path):
    """Arco antihorario de 0° a 90° con centro en el origen: pasa por (7,07; 7,07) y no por (2,93; 2,93)."""
    ruta = tmp_path / "arco.svg"
    ancho, alto = svg.escribir_svg(ruta, [("arco", 1, (0.0, 0.0), 10.0, 0.0, math.pi / 2),
                                          ("linea", 2, (0.0, 0.0), (10.0, 0.0))])
    img = _dibujar(ruta, ancho, alto)
    assert _hay_trazo(img, 7.07, 7.07, alto) and not _hay_trazo(img, 2.93, 2.93, alto)


def test_un_arco_de_mas_de_media_vuelta_tambien_(tmp_path):
    """270° (de 0° a 270°, antihorario): pasa por (−7,07; 7,07) y no por el cuadrante de 270° a 360°."""
    ruta = tmp_path / "arco270.svg"
    ancho, alto = svg.escribir_svg(ruta, [("arco", 1, (0.0, 0.0), 10.0, 0.0, 1.5 * math.pi)])
    img = _dibujar(ruta, ancho, alto)
    assert _hay_trazo(img, -7.07, 7.07, alto, -10, -10) and not _hay_trazo(img, 7.07, -7.07, alto, -10, -10)


# ---------------------------------------------------------------- SVG de las primitivas del dibujo (PL9)
CAPAS = {"VISIBLE": {"grosor": 0.5, "tipo": "continua", "color": 7},
         "OCULTA": {"grosor": 0.25, "tipo": "trazos", "color": 8}}


def test_las_ocultas_van_en_trazos_y_las_visibles_continuas():
    texto = svg_salida.a_texto_svg([("VISIBLE", ("linea", (0, 0), (10, 0))), ("OCULTA", ("linea", (0, 5), (10, 5)))],
                                   CAPAS, 20, 10)
    assert 'id="VISIBLE"' in texto and 'id="OCULTA"' in texto
    visible = texto.split('id="VISIBLE"')[1].split("</g>")[0]
    oculta = texto.split('id="OCULTA"')[1].split("</g>")[0]
    assert "stroke-dasharray" not in visible and 'stroke-dasharray="3 1.5"' in oculta
    assert 'width="20mm" height="10mm" viewBox="0 0 20 10"' in texto
    assert '<line x1="0" y1="10" x2="10" y2="10"/>' in visible          # la Y del dibujo (arriba) se da vuelta


def test_el_svg_del_dibujo_se_ve_igual_que_el_dibujo(tmp_path):
    prims = [("VISIBLE", ("circulo", (10, 10), 5)), ("VISIBLE", ("arco", (10, 10), 8, 0.0, math.pi / 2)),
             ("OCULTA", ("polilinea", [(2, 2), (18, 2), (18, 18)], False)), ("VISIBLE", ("linea", (2, 18), (6, 18)))]
    ruta = svg_salida.escribir_svg(tmp_path / "dibujo.svg", prims, CAPAS, 20, 20)
    img = _dibujar(ruta, 20, 20)
    assert _hay_trazo(img, 15, 10, 20) and _hay_trazo(img, 10, 15, 20)                    # círculo
    assert _hay_trazo(img, 10 + 8 * math.cos(math.pi / 4), 10 + 8 * math.sin(math.pi / 4), 20)       # arco antihorario
    assert not _hay_trazo(img, 10 - 8 * math.cos(math.pi / 4), 10 - 8 * math.sin(math.pi / 4), 20)
    assert _hay_trazo(img, 18, 10, 20) and _hay_trazo(img, 4, 18, 20)                    # polilínea y línea


def test_todas_las_primitivas_y_el_texto_con_caracteres_raros():
    prims = [("linea", (0, 0), (1, 1)), ("polilinea", [(0, 0), (1, 0), (1, 1)], True), ("spline", [(0, 0), (1, 1), (2, 0)]),
             ("circulo", (5, 5), 2), ("arco", (5, 5), 3, 0.0, 1.0), ("elipse", (5, 5), (3, 0), 0.5, 0.0, 2 * math.pi),
             ("texto", (1, 1), 3.5, "A<B & \"C\"", 30.0, "centro"), ("solido", [(0, 0), (1, 0), (1, 1), (0, 1)])]
    texto = svg_salida.a_texto_svg(prims)
    # polígonos: la polilínea cerrada, la elipse completa y el sólido; polilínea: la spline
    assert texto.count("<polygon") == 3 and texto.count("<polyline") == 1 and "A&lt;B &amp; \"C\"" in texto
    assert 'text-anchor="middle"' in texto and "rotate(-30" in texto
    from xml.etree import ElementTree
    ElementTree.fromstring(texto)                       # XML bien formado
    with pytest.raises(ValueError, match="desconocida"):
        svg_salida.a_texto_svg([("desconocida", (0, 0))], None, 10, 10)
    with pytest.raises(ValueError, match="nada"):
        svg_salida.a_texto_svg([])


def test_sin_tamano_la_hoja_es_la_caja_mas_margen():
    texto = svg_salida.a_texto_svg([("linea", (10, 20), (30, 25))])
    assert 'width="30mm" height="15mm"' in texto
    assert np.isclose(float(texto.split('viewBox="')[1].split()[0]), 5.0)


# ---------------------------------------------------------------- API: SVG de líneas ocultas (PL9)
def _pieza_con_agujero():
    from omnicad import api
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 40, "width": 30, "height": 20})["ok"]
    assert api.llamar(s, "create_hole", {"face": ">Z", "diameter": 10, "through_all": True})["ok"]
    return s


def _exportar(s, ruta, **args):
    from omnicad import api
    return api.llamar(s, "export_hidden_line_svg", {"path": str(ruta), **args})


def test_el_svg_de_lineas_ocultas_trae_el_agujero_en_trazos(tmp_path):
    s = _pieza_con_agujero()
    r = _exportar(s, tmp_path / "frente.svg", view="front")
    assert r["ok"], r
    r = r["result"]
    assert r["view"] == "front" and r["visible_lines"] >= 4 and r["hidden_lines"] >= 2
    assert r["size_mm"] == pytest.approx([50.0, 30.0], abs=0.01)                   # 40 × 20 más 5 mm de margen por lado
    texto = (tmp_path / "frente.svg").read_text(encoding="utf-8")
    oculta = texto.split('id="OCULTA"')[1].split("</g>")[0]
    assert 'stroke-dasharray="3 1.5"' in texto.split('id="OCULTA"')[1].split(">")[0] and oculta.count("<") >= 2
    visible = texto.split('id="VISIBLE"')[1].split("</g>")[0]
    assert "stroke-dasharray" not in texto.split('id="VISIBLE"')[1].split(">")[0] and visible.count("<") >= 4
    from xml.etree import ElementTree
    ElementTree.fromstring(texto)


def test_desde_arriba_el_agujero_es_visible_y_sin_ocultas(tmp_path):
    s = _pieza_con_agujero()
    r = _exportar(s, tmp_path / "arriba.svg", view="top")["result"]
    assert r["hidden_lines"] == 0 and r["size_mm"] == pytest.approx([50.0, 40.0], abs=0.01)
    img = _dibujar(tmp_path / "arriba.svg", r["size_mm"][0], r["size_mm"][1])
    # el agujero de Ø10 centrado: su borde pasa por (+5, 0) del modelo = (25 + 5, 20 + 0) del archivo
    assert _hay_trazo(img, 30.0, 20.0, r["size_mm"][1]) and not _hay_trazo(img, 25.0, 20.0, r["size_mm"][1])


def test_sin_ocultas_y_con_escala(tmp_path):
    s = _pieza_con_agujero()
    r = _exportar(s, tmp_path / "sin.svg", view="front", hidden="none", scale=0.5)["result"]
    assert r["hidden_lines"] == 0 and r["scale"] == 0.5 and r["size_mm"] == pytest.approx([30.0, 20.0], abs=0.01)   # 40 × 20 al 50 % más 10 de margen
    assert 'id="OCULTA"' not in (tmp_path / "sin.svg").read_text(encoding="utf-8")


def test_las_siete_vistas_dan_svg(tmp_path):
    s = _pieza_con_agujero()
    for vista in ("front", "back", "top", "bottom", "right", "left", "iso"):
        r = _exportar(s, tmp_path / f"{vista}.svg", view=vista)
        assert r["ok"] and r["result"]["visible_lines"] > 0, vista


def test_errores_del_svg_de_lineas_ocultas(tmp_path):
    from omnicad import api
    s = _pieza_con_agujero()
    assert _exportar(s, tmp_path / "x.dxf")["error_kind"] == "INVALID_FORMAT"
    assert _exportar(s, tmp_path / "x.svg", scale=0)["error_kind"] == "INVALID_ARGUMENTS"
    assert _exportar(s, tmp_path / "no_existe" / "x.svg")["error_kind"] == "FILE_NOT_FOUND"
    assert _exportar(s, tmp_path / "x.svg", bodies=["nada"])["ok"] is False
    assert _exportar(api.Sesion(), tmp_path / "vacio.svg")["error_kind"] == "NOTHING_TO_EXPORT"
    assert _exportar(s, tmp_path / "y.svg")["ok"]
    assert _exportar(s, tmp_path / "y.svg")["error_kind"] == "FILE_EXISTS"
    assert _exportar(s, tmp_path / "y.svg", overwrite=True)["ok"]


def test_la_hoja_del_dibujo_se_exporta_a_svg(tmp_path):
    QApplication.instance() or QApplication([])
    from omnicad.timeline.documento import Documento
    from omnicad.timeline.operaciones import OpPrimitiva
    from omnicad.ui.dibujo import VentanaDibujo
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="40", largo="30", alto="20"))
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="cilindro", radio="6", alto="40", x="20", y="15", z="-5",
                            operacion="cortar"))
    v = VentanaDibujo(doc)
    v.dibujo.agregar_vista_base(["op1.c1"], "frontal", posicion=(120, 180), escala=2)
    v.redibujar()
    texto = v.exportar_svg(tmp_path / "hoja.svg").read_text(encoding="utf-8")
    for capa in ("VISIBLE", "OCULTA", "MARCO", "CAJETIN"):
        assert f'id="{capa}"' in texto, capa
    assert f'width="{v.dibujo.ancho:g}mm" height="{v.dibujo.alto:g}mm"' in texto       # la hoja entera, en mm
    assert "dibujar_svg" not in texto and v.acciones["exportar_svg"].text() == "Exportar hoja como SVG…"
    v.deleteLater()
