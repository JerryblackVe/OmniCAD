# -*- coding: utf-8 -*-
"""INSERTAR DXF/SVG como bocetos y guardar un boceto como DXF."""
import math
import os

import pytest

from omnicad.io_archivos.boceto_archivos import boceto_desde_primitivas, primitivas_dxf_de_boceto
from omnicad.io_archivos.dxf import escribir_dxf, leer_dxf
from omnicad.io_archivos.svg import leer_svg
from omnicad.restricciones import Boceto
from omnicad.timeline.documento import Documento


@pytest.fixture(scope="module", autouse=True)
def app_qt():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="100mm" height="50mm" viewBox="0 0 100 50">
  <rect x="10" y="10" width="40" height="20"/>
  <circle cx="75" cy="25" r="10"/>
  <g transform="translate(0,0)"><path d="M 60 45 C 70 35, 80 35, 90 45 Z"/></g>
</svg>"""


def test_svg_a_boceto_con_perfiles(tmp_path):
    ruta = tmp_path / "dibujo.svg"
    ruta.write_text(SVG, encoding="utf-8")
    prims = leer_svg(ruta)
    tipos = sorted(p[0] for p in prims)
    assert tipos.count("circulo") == 1 and "bezier" in tipos and "polilinea" in tipos
    b = boceto_desde_primitivas(prims)
    from omnicad.nucleo.geometria import Plano
    from omnicad.nucleo.perfiles import detectar
    perfiles = detectar(b.geometria(), Plano("XY"))
    areas = sorted(round(p.area, 1) for p in perfiles)
    assert 800.0 in areas and round(math.pi * 100, 1) in areas and len(perfiles) == 3
    rect = max(perfiles, key=lambda p: p.area if p.area == 800 else 0)
    assert rect.centroide_uv[1] == pytest.approx(30)              # Y dada vuelta: el rectángulo queda arriba


def test_dxf_ida_y_vuelta_y_comando(tmp_path):
    b = Boceto()
    b.agregar_rectangulo((0, 0), (30, 20))
    b.agregar_circulo((15, 10), 4)
    ruta = tmp_path / "placa.dxf"
    escribir_dxf(ruta, primitivas_dxf_de_boceto(b))
    prims = leer_dxf(ruta)
    assert sorted(p[0] for p in prims).count("linea") == 4
    from omnicad.ui.comando import ContextoComando, hit_desde_ref
    from omnicad.ui.comandos.insertar import InsertarDXF
    doc = Documento()
    cmd, ctx = InsertarDXF(), ContextoComando(doc)
    v = {c.clave: c.defecto for c in cmd.campos(ctx)}
    v.update(plano=[hit_desde_ref({"tipo": "plano", "id": "XZ"}, doc.estado_final)], archivo=str(ruta), escala="2")
    op = cmd.construir(v, ctx)
    doc.agregar(op)
    br = doc.estado_final.bocetos[op.id]
    assert len(br.perfiles) == 2 and op.nombre == "Boceto1"
    assert max(p.area for p in br.perfiles) == pytest.approx(60 * 40 - math.pi * 64, rel=1e-6)


def test_lienzo_con_imagen_y_ancho_real(tmp_path):
    from PySide6.QtGui import QColor, QImage

    from omnicad.ui.comando import ContextoComando, hit_desde_ref
    from omnicad.ui.comandos.insertar import Lienzo
    from omnicad.ui.visor3d import Visor3D
    img = QImage(200, 100, QImage.Format_RGB32)
    img.fill(QColor("red"))
    ruta = tmp_path / "ref.png"
    img.save(str(ruta))
    doc = Documento()
    cmd, ctx = Lienzo(), ContextoComando(doc)
    v = {c.clave: c.defecto for c in cmd.campos(ctx)}
    v.update(plano=[hit_desde_ref({"tipo": "plano", "id": "XY"}, doc.estado_final)], archivo=str(ruta),
             ancho="80 mm", dx="10 mm")
    op = cmd.construir(v, ctx)
    doc.agregar(op)
    datos = doc.estado_final.lienzos[op.id]
    assert datos["alto"] == pytest.approx(40) and op.nombre == "Lienzo1"
    esquinas = Visor3D.esquinas_lienzo(datos)
    assert [tuple(round(c, 6) for c in p[:2]) for p in esquinas] == [(-30, -20), (50, -20), (50, 20), (-30, 20)]
    assert Documento.desde_dict(doc.a_dict()).estado_final.lienzos[op.id]["ancho"] == pytest.approx(80)
