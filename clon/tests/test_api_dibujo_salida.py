# -*- coding: utf-8 -*-
"""Herramientas de salida del dibujo (B-80 / MCP-20 y MCP-21): export_drawing a DXF, SVG y PDF, y la hoja como
imagen (get_drawing_image). Sin ventana: DXF, SVG y PDF salen de las primitivas del plano."""
import io
import re
import xml.etree.ElementTree as ET

import numpy as np
import pytest
from PIL import Image

from omnicad import api
from omnicad.io_archivos import pdf_salida


@pytest.fixture(scope="module")
def sesion():
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 40, "width": 20, "height": 10, "name": "Caja"})["ok"]
    assert api.llamar(s, "create_drawing", {"bodies": ["Caja"], "title": "Soporte ⌀8"})["ok"]
    return s


def _ok(s, nombre, args=None):
    r = api.llamar(s, nombre, args or {})
    assert r["ok"], r
    return r["result"]


def test_exportar_svg_a_escala_de_hoja(sesion, tmp_path):
    r = _ok(sesion, "export_drawing", {"path": str(tmp_path / "plano.svg")})
    assert r["format"] == "svg" and r["sheet"]["size"] == "A3" and r["size_bytes"] > 1000
    raiz = ET.fromstring((tmp_path / "plano.svg").read_text(encoding="utf-8"))
    assert raiz.get("width") == "420mm" and raiz.get("height") == "297mm"
    capas = {g.get("id") for g in raiz.iter("{http://www.w3.org/2000/svg}g")}
    assert {"VISIBLE", "MARCO", "CAJETIN"} <= capas


def test_exportar_dxf_con_capas(sesion, tmp_path):
    r = _ok(sesion, "export_drawing", {"path": str(tmp_path / "plano.dxf")})
    assert r["format"] == "dxf"
    texto = (tmp_path / "plano.dxf").read_text(encoding="ascii", errors="replace")
    assert "AC1015" in texto and "VISIBLE" in texto and "EOF" in texto
    r = _ok(sesion, "export_drawing", {"path": str(tmp_path / "r12.dxf"), "dxf_version": "R12"})
    assert "AC1009" in (tmp_path / "r12.dxf").read_text(encoding="ascii", errors="replace")


def test_exportar_pdf_es_valido_y_a_escala_real(sesion, tmp_path):
    r = _ok(sesion, "export_drawing", {"path": str(tmp_path / "plano.pdf")})
    datos = (tmp_path / "plano.pdf").read_bytes()
    assert r["format"] == "pdf" and datos.startswith(b"%PDF-1.4") and datos.rstrip().endswith(b"%%EOF")
    caja = re.search(rb"/MediaBox \[0 0 ([\d.]+) ([\d.]+)\]", datos)
    assert float(caja.group(1)) == pytest.approx(420 * 72 / 25.4, abs=0.01)       # A3 horizontal, en puntos
    assert float(caja.group(2)) == pytest.approx(297 * 72 / 25.4, abs=0.01)
    inicio = int(re.search(rb"startxref\n(\d+)", datos).group(1))
    assert datos[inicio:inicio + 4] == b"xref"                                    # el índice apunta bien
    for n, desplazamiento in enumerate(re.findall(rb"(\d{10}) 00000 n", datos), 1):
        assert datos[int(desplazamiento):].startswith(b"%d 0 obj" % n)            # y cada objeto está donde dice


def test_pdf_dibuja_las_primitivas():
    prims = [("MARCO", ("linea", (0, 0), (10, 10))), ("VISIBLE", ("circulo", (5, 5), 2)),
             ("VISIBLE", ("arco", (5, 5), 3, 0.0, 1.5)), ("TEXTO", ("texto", (1, 1), 3.5, "Ø8 ± (1)\\", 90.0, "centro")),
             ("COTAS", ("solido", [(0, 0), (1, 0), (0, 1)])), ("OCULTA", ("polilinea", [(0, 0), (4, 0), (4, 4)], True))]
    pdf = pdf_salida.a_bytes_pdf(prims, {"OCULTA": {"grosor": 0.25, "tipo": "trazos"}}, 100, 80, "T")
    assert pdf.startswith(b"%PDF-1.4")
    assert pdf_salida._ancho_texto(b"HOLA", 3.5) > pdf_salida._ancho_texto(b"HO", 3.5) > 0
    assert len(pdf_salida._ANCHOS) == 95


def test_errores_de_exportar(sesion, tmp_path):
    destino = tmp_path / "a" / "b" / "plano.svg"
    r = api.llamar(sesion, "export_drawing", {"path": str(destino), "create_folders": False})
    assert not r["ok"] and r["error_kind"] == "FILE_NOT_FOUND"
    assert _ok(sesion, "export_drawing", {"path": str(destino)})["format"] == "svg"          # crea las carpetas
    r = api.llamar(sesion, "export_drawing", {"path": str(destino)})
    assert not r["ok"] and r["error_kind"] == "FILE_EXISTS"
    assert _ok(sesion, "export_drawing", {"path": str(destino), "overwrite": True})["format"] == "svg"
    r = api.llamar(sesion, "export_drawing", {"path": str(tmp_path / "x.png")})
    assert not r["ok"] and r["error_kind"] == "INVALID_FORMAT"
    r = api.llamar(sesion, "export_drawing", {"path": str(tmp_path)})
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS"
    # sin extensión: se la agrega según format
    r = _ok(sesion, "export_drawing", {"path": str(tmp_path / "sinext"), "format": "dxf"})
    assert r["path"].endswith("sinext.dxf") and (tmp_path / "sinext.dxf").is_file()


def test_sin_dibujo_o_sin_vistas_no_exporta(tmp_path):
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 10, "width": 10, "height": 10})["ok"]
    for nombre in ("export_drawing", "get_drawing_image"):
        args = {"path": str(tmp_path / "x.svg")} if nombre == "export_drawing" else {}
        r = api.llamar(s, nombre, args)
        assert not r["ok"] and r["error_kind"] == "DRAWING_NOT_FOUND"
    assert api.llamar(s, "create_drawing", {})["ok"]                                  # hoja sin vistas
    for nombre, args in (("get_drawing_image", {}), ("export_drawing", {"path": str(tmp_path / "x.svg")})):
        r = api.llamar(s, nombre, args)
        assert not r["ok"] and r["error_kind"] == "NOTHING_TO_RENDER"


def test_imagen_de_la_hoja(sesion):
    r = _ok(sesion, "get_drawing_image", {"width": 840})
    assert (r["width"], r["height"]) == (840, 594) and r["views"] == 1          # 420 × 297 mm a 2 px/mm
    img = Image.open(io.BytesIO(r["image"].png)).convert("L")
    assert img.size == (840, 594) and r["image"].png.startswith(b"\x89PNG")
    negros = int((np.asarray(img) < 128).sum())
    assert 500 < negros < img.width * img.height * 0.2                        # hay dibujo, y la hoja es sobre todo blanca
    # el marco de la hoja está a 10 mm del borde: 20 px en la imagen
    fila = [img.getpixel((x, 297)) for x in range(0, 40)]
    assert min(fila) < 128 and fila[0] == 255
    for malo in (100, 5000):
        r = api.llamar(sesion, "get_drawing_image", {"width": malo})
        assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS"
