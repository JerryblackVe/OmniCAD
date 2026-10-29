# -*- coding: utf-8 -*-
"""Texto con todas las fuentes y opciones, Insertar SVG/DXF en el boceto activo y vectorizar imágenes
(núcleo, herramientas del MCP/CLI y comandos de la interfaz)."""
import math
import os

import pytest

from omnicad import api
from omnicad.io_archivos.boceto_archivos import boceto_desde_primitivas, caja_primitivas
from omnicad.nucleo import fuentes


def ok(r):
    assert r["ok"], r
    return r["result"]


def falla(r, kind):
    assert not r["ok"] and r["error_kind"] == kind, r
    return r


def caja(prims):
    xs, ys = [], []
    for p in prims:
        pts = [p[2], p[3]] if p[0] == "linea" else p[2]
        xs += [q[0] for q in pts]
        ys += [q[1] for q in pts]
    return min(xs), min(ys), max(xs), max(ys)


hay_arial = pytest.mark.skipif(fuentes.buscar_fuente("Arial") is None, reason="No hay Arial instalada")


# ---------------------------------------------------------------- núcleo: catálogo y contornos
@hay_arial
def test_catalogo_ve_familias_y_elige_peso_y_cursiva():
    assert len(fuentes.familias()) > 5
    normal, negrita = fuentes.buscar_fuente("Arial"), fuentes.buscar_fuente("arial", negrita=True)
    assert normal["peso"] < negrita["peso"] and normal["ruta"] != negrita["ruta"]
    assert fuentes.buscar_fuente("Arial", cursiva=True)["cursiva"] is True
    assert fuentes.buscar_fuente("esta fuente no existe 123") is None
    # también por ruta directa a un archivo
    assert fuentes.buscar_fuente(normal["ruta"])["familia"] == "Arial"


@hay_arial
def test_contornos_iguales_a_los_de_opencascade():
    from omnicad.nucleo import perfiles
    nuevo = fuentes.contornos_texto("Hola Mundo", "Arial", 10)
    viejo = perfiles._contornos_occ("Hola Mundo", "Arial", 10, False, False)
    assert len(nuevo) == len(viejo)
    assert caja(nuevo) == pytest.approx(caja(viejo), abs=0.02)


@hay_arial
def test_opciones_de_composicion():
    base = caja(fuentes.contornos_texto("Hola", "Arial", 10))
    ancho = base[2] - base[0]
    # espaciado: 3 letras de separación + 3 mm cada una
    sp = caja(fuentes.contornos_texto("Hola", "Arial", 10, espaciado=3))
    assert sp[2] - sp[0] == pytest.approx(ancho + 9, abs=0.05)
    # dos líneas: más alto; el interlineado lo estira
    dos = caja(fuentes.contornos_texto("Hola\nHola", "Arial", 10))
    mas = caja(fuentes.contornos_texto("Hola\nHola", "Arial", 10, interlineado=2))
    assert dos[1] < base[1] - 9 and mas[1] < dos[1] - 5
    # alineación: la línea corta queda centrada o a la derecha respecto de la larga
    izq = caja(fuentes.contornos_texto("Hola mundo largo\nHi", "Arial", 10))
    der = caja(fuentes.contornos_texto("Hola mundo largo\nHi", "Arial", 10, alineacion="der"))
    assert izq[2] == pytest.approx(der[2], abs=0.01) and der[0] == pytest.approx(izq[0], abs=0.5)
    # caja con ajuste de línea: ninguna línea pasa del ancho pedido
    cj = caja(fuentes.contornos_texto("uno dos tres cuatro cinco seis", "Arial", 10, ancho_caja=40))
    assert cj[2] <= 40.5 and cj[1] < base[1] - 15
    # anclaje arriba: el texto cuelga por debajo del punto
    arriba = caja(fuentes.contornos_texto("Hola", "Arial", 10, ancla_v="arriba"))
    assert arriba[3] <= 0.0 and arriba[1] < -6
    # volteo horizontal: mismo ancho, en espejo
    vh = caja(fuentes.contornos_texto("Hola", "Arial", 10, voltear_h=True))
    assert vh[2] - vh[0] == pytest.approx(ancho, abs=0.05)


def test_opciones_invalidas_y_fuente_inexistente():
    with pytest.raises(fuentes.ErrorFuente):
        fuentes.contornos_texto("Hola", "no-existe-xyz", 10)
    if fuentes.buscar_fuente("Arial") is not None:
        with pytest.raises(fuentes.ErrorFuente):
            fuentes.contornos_texto("Hola", "Arial", 10, alineacion="diagonal")


def test_fuente_desde_un_archivo_de_usuario(tmp_path):
    reg = fuentes.buscar_fuente("Arial")
    if reg is None:
        pytest.skip("No hay Arial instalada")
    import shutil
    copia = tmp_path / "MiFuente.ttf"
    shutil.copy(reg["ruta"], copia)
    n = fuentes.agregar_carpeta(tmp_path)
    try:
        assert n >= 1
        assert fuentes.buscar_fuente(str(copia)) is not None
        assert fuentes.contornos_texto("Hi", str(copia), 5)
    finally:
        fuentes.CARPETAS_EXTRA.clear()
        fuentes.catalogo(forzar=True)


# ---------------------------------------------------------------- boceto: texto
@hay_arial
def test_texto_serializa_solo_lo_que_cambia_y_carga_los_viejos():
    from omnicad.restricciones import Boceto
    b = Boceto()
    t1 = b.agregar_texto((0, 0), "A", altura=7)
    t2 = b.agregar_texto((0, 20), "B", altura=7, alineacion="centro", interlineado=1.5, voltear_h=True)
    d = b.a_dict()
    c1 = next(c for c in d["curvas"] if c["id"] == t1)
    c2 = next(c for c in d["curvas"] if c["id"] == t2)
    assert "alineacion" not in c1 and "espaciado" not in c1 and "voltear_h" not in c1       # igual que antes
    assert c2["alineacion"] == "centro" and c2["interlineado"] == 1.5 and c2["voltear_h"] is True
    b2 = Boceto.desde_dict(d)
    assert b2.curvas[t2].alineacion == "centro" and b2.curvas[t1].interlineado == 1.0
    assert len(b2.geometria()) == len(b.geometria())


def test_agregar_texto_valida_las_opciones():
    from omnicad.restricciones import Boceto, ErrorBoceto
    b = Boceto()
    for mal in ({"alineacion": "x"}, {"ancla_v": "x"}, {"interlineado": 0}, {"ancho_caja": -1}, {"foo": 1}):
        with pytest.raises(ErrorBoceto):
            b.agregar_texto((0, 0), "A", **mal)


# ---------------------------------------------------------------- herramientas MCP / CLI
@pytest.fixture
def s():
    sesion = api.Sesion()
    ok(api.llamar(sesion, "create_sketch", {"plane": "XY"}))
    return sesion


@hay_arial
def test_list_fonts_y_add_font_folder(s, tmp_path):
    r = ok(api.llamar(s, "list_fonts", {"query": "arial", "include_styles": True}))
    assert any(f["name"] == "Arial" and f["styles"] for f in r["families"]) and r["total_fonts"] > 5
    assert ok(api.llamar(s, "list_fonts", {"limit": 3}))["families"].__len__() == 3
    falla(api.llamar(s, "list_fonts", {"limit": 0}), "INVALID_ARGUMENTS")
    assert ok(api.llamar(s, "add_font_folder", {"path": str(tmp_path)}))["added_fonts"] == 0
    falla(api.llamar(s, "add_font_folder", {"path": str(tmp_path / "no_existe")}), "FILE_NOT_FOUND")
    fuentes.CARPETAS_EXTRA.clear()


@hay_arial
def test_add_text_edit_text_y_explode_text(s):
    r = ok(api.llamar(s, "add_text", {"text": "I", "height": 10, "font": "Arial", "letter_spacing": 1,
                                      "align": "center", "anchor": "top", "box_width": 30}))
    assert r["profiles"] == 1 and r["entities"][0]["type"] == "text"
    tid = r["entities"][0]["id"]
    t = next(c for c in ok(api.llamar(s, "get_sketch", {}))["entities"] if c["id"] == tid)
    assert t["font"] == "Arial" and t["align"] == "center" and t["anchor"] == "top" and t["box_width"] == 30
    r = ok(api.llamar(s, "edit_text", {"entity": tid, "text": "II", "x": 5, "y": 5, "bold": True,
                                       "line_spacing": 2}))
    assert r["profiles"] == 2
    t = next(c for c in ok(api.llamar(s, "get_sketch", {}))["entities"] if c["id"] == tid)
    assert t["text"] == "II" and t["bold"] is True and t["position"] == [5.0, 5.0] and t["line_spacing"] == 2
    ex = ok(api.llamar(s, "explode_text", {"entity": tid}))
    assert ex["profiles"] == 2 and all(e["type"] != "text" for e in ex["entities"]) and len(ex["entities"]) >= 8
    falla(api.llamar(s, "explode_text", {"entity": tid}), "ENTITY_NOT_FOUND")


@hay_arial
def test_add_text_errores(s):
    falla(api.llamar(s, "add_text", {"text": "A", "font": "fuente-que-no-existe"}), "INVALID_ARGUMENTS")
    falla(api.llamar(s, "add_text", {"text": "  "}), "INVALID_GEOMETRY")
    falla(api.llamar(s, "add_text", {"text": "A", "height": -1}), "INVALID_GEOMETRY")
    falla(api.llamar(s, "add_text", {"text": "A", "align": "justify"}), "INVALID_ARGUMENTS")
    falla(api.llamar(s, "edit_text", {"entity": 9999, "text": "x"}), "ENTITY_NOT_FOUND")


# ---------------------------------------------------------------- SVG / DXF
SVG = """<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" width="100mm" height="50mm" viewBox="0 0 100 50">
  <defs><circle id="rueda" cx="0" cy="0" r="5"/></defs>
  <g inkscape:label="corte" stroke="#ff0000" fill="none">
    <rect x="10" y="10" width="40" height="20"/>
    <use xlink:href="#rueda" x="75" y="25"/>
  </g>
  <g id="grabado" style="stroke:#0000ff;fill:none"><path d="M 60 45 L 90 45 L 75 35 Z"/></g>
  <g style="display:none"><rect x="0" y="0" width="5" height="5"/></g>
</svg>"""


@pytest.fixture
def svg(tmp_path):
    ruta = tmp_path / "dibujo.svg"
    ruta.write_text(SVG, encoding="utf-8")
    return ruta


def test_svg_capas_colores_use_y_ocultos(svg):
    from omnicad.io_archivos.svg import leer_svg, listar_capas_svg
    info = listar_capas_svg(svg)
    assert info["capas"] == {"corte": 2, "grabado": 3} and info["colores"] == {"#ff0000": 2, "#0000ff": 3}
    assert len(leer_svg(svg)) == 5                                   # el grupo con display:none no entra
    assert [p[0] for p in leer_svg(svg, capas=["GRABADO"])] == ["linea"] * 3
    assert sorted(p[0] for p in leer_svg(svg, colores=["#f00"])) == ["circulo", "polilinea"]
    with pytest.raises(ValueError):
        leer_svg(svg, capas=["no-existe"])


def test_inspect_svg_e_insert_svg_en_boceto_nuevo_y_existente(s, svg):
    r = ok(api.llamar(s, "inspect_svg", {"path": str(svg)}))
    assert r["layers"] == {"corte": 2, "grabado": 3} and r["size_mm"][0] == pytest.approx(80, abs=0.5)
    # boceto nuevo sobre un plano
    n = ok(api.llamar(s, "insert_svg", {"path": str(svg), "plane": "XZ", "layers": ["corte"], "name": "Logo"}))
    assert n["sketch"]["name"] == "Logo" and n["entities_added"] >= 5 and n["profiles"] == 2
    # sumado al boceto ya existente (el primero), ajustado a 40 mm de ancho y girado
    e = ok(api.llamar(s, "insert_svg", {"path": str(svg), "sketch": "Boceto1", "width": 40, "x": 100, "angle": 90}))
    assert e["entities_added"] >= 7 and e["sketch"]["name"] == "Boceto1"
    sk = ok(api.llamar(s, "get_sketch", {"sketch": "Boceto1"}))
    xs = [v[0] for c in sk["entities"] if c["type"] == "line" for v in (c["start"], c["end"])]
    assert max(xs) < 101 and min(xs) > 59                            # 40 mm de ancho en x, girado 90° y movido
    ok(api.llamar(s, "undo"))
    assert len(ok(api.llamar(s, "get_sketch", {"sketch": "Boceto1"}))["entities"]) == 0


def test_insert_svg_volteo_y_errores(s, svg, tmp_path):
    a = ok(api.llamar(s, "insert_svg", {"path": str(svg), "sketch": "Boceto1", "layers": ["grabado"]}))
    ok(api.llamar(s, "create_sketch", {"plane": "XY"}))
    b = ok(api.llamar(s, "insert_svg", {"path": str(svg), "sketch": "Boceto2", "layers": ["grabado"],
                                        "flip_v": True}))
    assert a["profiles"] == b["profiles"] == 1
    cy = [sum(v[1] for v in (c["start"], c["end"])) / 2 for c in
          ok(api.llamar(s, "get_sketch", {"sketch": "Boceto2"}))["entities"] if c["type"] == "line"]
    cy0 = [sum(v[1] for v in (c["start"], c["end"])) / 2 for c in
           ok(api.llamar(s, "get_sketch", {"sketch": "Boceto1"}))["entities"] if c["type"] == "line"]
    assert sorted(cy) != sorted(cy0)                                 # el espejo cambió el orden vertical
    falla(api.llamar(s, "insert_svg", {"path": str(tmp_path / "no.svg"), "sketch": "Boceto1"}), "FILE_NOT_FOUND")
    falla(api.llamar(s, "insert_svg", {"path": str(svg), "layers": ["nada"]}), "IMPORT_FAILED")
    falla(api.llamar(s, "insert_svg", {"path": str(svg), "scale": 0}), "INVALID_ARGUMENTS")
    otro = tmp_path / "x.txt"
    otro.write_text("hola")
    falla(api.llamar(s, "insert_svg", {"path": str(otro)}), "UNSUPPORTED_FILE_TYPE")


def test_insert_dxf_en_boceto_existente(s, tmp_path):
    from omnicad.io_archivos.boceto_archivos import primitivas_dxf_de_boceto
    from omnicad.io_archivos.dxf import escribir_dxf
    from omnicad.restricciones import Boceto
    b = Boceto()
    b.agregar_rectangulo((0, 0), (30, 20))
    ruta = tmp_path / "placa.dxf"
    escribir_dxf(ruta, primitivas_dxf_de_boceto(b))
    r = ok(api.llamar(s, "insert_dxf", {"path": str(ruta), "width": 60, "x": 5}))
    assert r["entities_added"] == 4 and r["profiles"] == 1 and r["source_size_mm"] == [30.0, 20.0]
    sk = ok(api.llamar(s, "get_sketch", {}))
    xs = [v[0] for c in sk["entities"] if c["type"] == "line" for v in (c["start"], c["end"])]
    assert min(xs) == pytest.approx(5) and max(xs) == pytest.approx(65)


def test_boceto_desde_primitivas_voltea_y_ajusta_ancho():
    prims = [("polilinea", [(0, 0), (10, 0), (10, 4), (0, 4)], True), ("arco", (5, 4), 3, 0.0, math.pi)]
    assert caja_primitivas(prims) == ((0, 0), (10, pytest.approx(7)))
    b = boceto_desde_primitivas(prims, ancho=20, voltear_h=True)
    ys = [p.y for p in b.puntos.values()]
    xs = [p.x for p in b.puntos.values()]
    assert min(xs) == pytest.approx(0) and max(xs) == pytest.approx(20) and max(ys) == pytest.approx(8, abs=0.01)
    with pytest.raises(ValueError):
        boceto_desde_primitivas(prims, escala=0)
    with pytest.raises(ValueError):
        boceto_desde_primitivas([], escala=1)


# ---------------------------------------------------------------- imagen → vector
@pytest.fixture
def anillo(tmp_path):
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (200, 120), "white")
    d = ImageDraw.Draw(img)
    d.ellipse((10, 10, 110, 110), fill="black")
    d.ellipse((35, 35, 85, 85), fill="white")
    d.rectangle((140, 30, 190, 90), fill="black")
    ruta = tmp_path / "anillo.png"
    img.save(ruta)
    return ruta


def test_vectorizar_imagen_da_contornos_con_agujero(anillo):
    from omnicad.io_archivos.vectorizar import ErrorVectorizar, vectorizar_imagen
    prims = vectorizar_imagen(anillo)
    assert len(prims) == 3                                           # disco, agujero y rectángulo
    caja_px = caja_primitivas([("polilinea", p[1], True) for p in prims])
    assert caja_px[1][0] - caja_px[0][0] == pytest.approx(180, abs=2)
    assert caja_px[1][1] == pytest.approx(110, abs=2)                # Y hacia arriba: el borde de arriba está en 110
    curvas = vectorizar_imagen(anillo, curvas=True)
    # disco y agujero son splines; el rectángulo (pocos vértices) queda polígono: un spline cerrado por 4 a 8 vértices se
    # pasaba de largo en las esquinas (T-10 de la prueba de tortura)
    assert sorted(p[0] for p in curvas) == ["curva", "curva", "polilinea"]
    from PIL import Image
    blanca = anillo.parent / "blanca.png"
    Image.new("RGB", (40, 40), "white").save(blanca)
    with pytest.raises(ErrorVectorizar, match="nada para vectorizar"):
        vectorizar_imagen(blanca)
    with pytest.raises(ErrorVectorizar):
        vectorizar_imagen(anillo, umbral=0)


def test_trace_image_en_boceto(s, anillo, tmp_path):
    r = ok(api.llamar(s, "trace_image", {"path": str(anillo), "width": 90}))
    assert r["entities_added"] > 10 and r["profiles"] == 3           # anillo, disco interior y rectángulo
    assert r["source_size_mm"][0] > 40
    sk = ok(api.llamar(s, "get_sketch", {}))
    xs = [v[0] for c in sk["entities"] if c["type"] == "line" for v in (c["start"], c["end"])]
    assert max(xs) - min(xs) == pytest.approx(90, abs=0.5)
    # splines: una entidad por contorno redondo; el rectángulo queda en líneas (ver arriba)
    ok(api.llamar(s, "create_sketch", {"plane": "XY"}))
    c = ok(api.llamar(s, "trace_image", {"path": str(anillo), "sketch": "Boceto2", "width": 90, "curves": True,
                                         "name": "x"}))
    assert 3 < c["entities_added"] < r["entities_added"] and c["profiles"] == 3
    # invertir: la tinta pasa a ser el fondo, y queda otra cantidad de contornos
    i = ok(api.llamar(s, "trace_image", {"path": str(anillo), "plane": "XY", "invert": True, "dpi": 25.4}))
    assert i["sketch"]["name"] == "Boceto3"
    falla(api.llamar(s, "trace_image", {"path": str(anillo), "threshold": 255}), "IMPORT_FAILED")
    falla(api.llamar(s, "trace_image", {"path": str(anillo), "dpi": 0}), "INVALID_ARGUMENTS")


# ---------------------------------------------------------------- comandos de la interfaz
@pytest.fixture(scope="module")
def app_qt():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_comandos_insertar_svg_con_filtro_y_vectorizar_imagen(app_qt, svg, anillo):
    from omnicad.timeline.documento import Documento
    from omnicad.ui.comando import ContextoComando, hit_desde_ref
    from omnicad.ui.comandos import CATALOGO
    from omnicad.ui.comandos.insertar import InsertarSVG, VectorizarImagen
    assert "vectorizar_imagen" in CATALOGO
    doc = Documento()
    ctx = ContextoComando(doc)
    hit = hit_desde_ref({"tipo": "plano", "id": "XY"}, doc.estado_final)
    cmd = InsertarSVG()
    v = {c.clave: c.defecto for c in cmd.campos(ctx)}
    v.update(plano=[hit], archivo=str(svg), capas="corte", voltear_h=True)
    op = cmd.construir(v, ctx)
    doc.agregar(op)
    assert len(doc.estado_final.bocetos[op.id].perfiles) == 2
    v.update(capas="grabado")                                        # otro filtro: se vuelve a leer el archivo
    assert len(cmd.construir(v, ctx).boceto.curvas) == 3
    cmd2 = VectorizarImagen()
    v = {c.clave: c.defecto for c in cmd2.campos(ctx)}
    v.update(plano=[hit], archivo=str(anillo), ancho="90 mm")
    op2 = cmd2.construir(v, ctx)
    doc.agregar(op2)
    assert len(doc.estado_final.bocetos[op2.id].perfiles) == 3


# ---------------------------------------------------------------- fx: parámetros dentro del texto
def test_expresiones_en_el_texto_helpers():
    from omnicad.restricciones.boceto import expresiones_de_texto, sustituir_expresiones
    assert expresiones_de_texto("Ancho {ancho} x {largo / 2:.1f} mm {}") == ["ancho", "largo / 2"]
    valores = {"ancho": 60.0, "largo": 25.0}
    r = sustituir_expresiones("A={ancho} L={largo / 2:.1f} Z={ancho:05.0f}", lambda e: eval(e, {}, valores))
    assert r == "A=60 L=12.5 Z=00060"
    assert sustituir_expresiones("sin llaves", lambda e: 1 / 0) == "sin llaves"


@hay_arial
def test_texto_con_parametro_se_actualiza_y_protege_el_parametro(s):
    ok(api.llamar(s, "create_parameter", {"name": "ancho", "expression": "60 mm"}))
    r = ok(api.llamar(s, "add_text", {"text": "W={ancho}", "height": 8}))
    tid = r["entities"][0]["id"]
    doc = s.doc
    op = doc.operaciones[0]
    assert doc.estado_final.bocetos[op.id].boceto.curvas[tid].texto == "W=60"
    assert op.boceto.curvas[tid].texto == "W={ancho}"                 # lo guardado conserva la expresión
    n60 = len(doc.estado_final.bocetos[op.id].boceto.geometria())
    ok(api.llamar(s, "set_parameter", {"name": "ancho", "expression": "7 mm"}))
    assert doc.estado_final.bocetos[op.id].boceto.curvas[tid].texto == "W=7"
    assert len(doc.estado_final.bocetos[op.id].boceto.geometria()) < n60       # «7» tiene menos trazos que «60»
    falla(api.llamar(s, "delete_parameter", {"name": "ancho"}), "PARAMETER_IN_USE")
    # un parámetro que no existe: avisa pero no rompe el boceto
    r2 = ok(api.llamar(s, "add_text", {"text": "{no_existe}", "x": 0, "y": 20}))
    assert doc.estado_final.bocetos[op.id].boceto.curvas[r2["entities"][0]["id"]].texto == "{no_existe}"
    # explode_text congela el valor de ahora
    ex = ok(api.llamar(s, "explode_text", {"entity": tid}))
    assert all(e["type"] != "text" for e in ex["entities"])


# ---------------------------------------------------------------- exportar el boceto
@hay_arial
def test_export_sketch_svg_y_dxf_ida_y_vuelta(s, tmp_path):
    ok(api.llamar(s, "draw_rectangle", {"x1": 0, "y1": 0, "x2": 40, "y2": 20}))
    ok(api.llamar(s, "draw_circle", {"radius": 5, "center_x": 20, "center_y": 10}))
    ok(api.llamar(s, "draw_line", {"start_x": 0, "start_y": 30, "end_x": 40, "end_y": 30, "construction": True}))
    ok(api.llamar(s, "add_text", {"text": "I", "x": 5, "y": 25, "height": 6}))
    svg_ruta = tmp_path / "salida.svg"
    r = ok(api.llamar(s, "export_sketch", {"path": str(svg_ruta)}))
    assert r["format"] == "svg" and r["size_mm"][0] == pytest.approx(40, abs=0.01)
    texto = svg_ruta.read_text(encoding="utf-8")
    assert "<circle" in texto and "construccion" not in texto and 'width="40mm"' in texto
    r = ok(api.llamar(s, "export_sketch", {"path": str(tmp_path / "con.svg"), "include_construction": True}))
    assert 'id="construccion"' in (tmp_path / "con.svg").read_text(encoding="utf-8")
    # ida y vuelta: lo exportado se vuelve a insertar con los mismos perfiles
    ok(api.llamar(s, "create_sketch", {"plane": "XY"}))
    v = ok(api.llamar(s, "insert_svg", {"path": str(svg_ruta), "sketch": "Boceto2"}))
    assert v["profiles"] == len(ok(api.llamar(s, "get_sketch", {"sketch": "Boceto1"}))["profiles"]) >= 3
    d = ok(api.llamar(s, "export_sketch", {"path": str(tmp_path / "salida.dxf")}))
    assert d["format"] == "dxf" and d["size_bytes"] > 100
    falla(api.llamar(s, "export_sketch", {"path": str(svg_ruta)}), "FILE_EXISTS")
    ok(api.llamar(s, "export_sketch", {"path": str(svg_ruta), "overwrite": True}))
    falla(api.llamar(s, "export_sketch", {"path": str(tmp_path / "x.png")}), "INVALID_FORMAT")
    falla(api.llamar(s, "export_sketch", {"path": str(tmp_path / "nada" / "x.svg")}), "FILE_NOT_FOUND")


def test_export_sketch_de_boceto_vacio(s, tmp_path):
    falla(api.llamar(s, "export_sketch", {"path": str(tmp_path / "v.svg")}), "NOTHING_TO_EXPORT")


# ---------------------------------------------------------------- texto en curva
def _circulo(r=30.0, n=720):
    return [(r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n)) for k in range(n)] + [(r, 0.0)]


def _puntos(prims):
    return [q for p in prims for q in ([p[2], p[3]] if p[0] == "linea" else p[2])]


@hay_arial
def test_contornos_en_camino_circulo_y_linea():
    arriba = _puntos(fuentes.contornos_en_camino("TOP", _circulo(), "Arial", 6, lado="der", posicion=0.25))
    assert min(y for _x, y in arriba) > 20 and min(math.hypot(x, y) for x, y in arriba) > 29.5   # afuera y arriba
    adentro = _puntos(fuentes.contornos_en_camino("bot", _circulo(), "Arial", 6, lado="izq", posicion=0.75))
    assert max(y for _x, y in adentro) < -20 and max(math.hypot(x, y) for x, y in adentro) < 30.2  # adentro y abajo
    # sobre una recta horizontal da lo mismo que el texto recto (corrido para centrarlo)
    recta = [(0.0, 0.0), (100.0, 0.0)]
    en_recta = caja(fuentes.contornos_en_camino("Hola", recta, "Arial", 10, alineacion="izq", posicion=0.0))
    recto = caja(fuentes.contornos_texto("Hola", "Arial", 10))
    assert en_recta == pytest.approx(recto, abs=1e-6)
    # ajustar: el texto ocupa todo el largo
    aj = caja(fuentes.contornos_en_camino("AB", recta, "Arial", 10, ajustar=True))
    assert aj[0] < 5 and aj[2] > 95
    # desfase: la línea base se separa de la curva hacia el lado de las letras
    d = caja(fuentes.contornos_en_camino("Hola", recta, "Arial", 10, posicion=0.0, alineacion="izq", desfase=4))
    assert d[1] == pytest.approx(recto[1] + 4, abs=1e-6)
    with pytest.raises(fuentes.ErrorFuente):
        fuentes.contornos_en_camino("x", recta, "Arial", 10, lado="arriba")
    with pytest.raises(fuentes.ErrorFuente):
        fuentes.contornos_en_camino("x", [(0, 0), (0, 0)], "Arial", 10)


@hay_arial
def test_texto_en_curva_en_el_boceto():
    from omnicad.restricciones import Boceto, ErrorBoceto
    b = Boceto()
    circ = b.agregar_circulo((0, 0), 30)
    t = b.agregar_texto((0, 0), "ABC", altura=6, camino=circ, camino_lado="der", camino_pos=0.25,
                        alineacion="centro", camino_desfase=1)
    pts = _puntos(b.primitivas(t))
    assert all(math.hypot(x, y) > 30 for x, y in pts) and min(y for _x, y in pts) > 20
    d = next(c for c in b.a_dict()["curvas"] if c["id"] == t)
    assert d["camino"] == circ and d["camino_lado"] == "der" and "camino_ajustar" not in d
    b2 = Boceto.desde_dict(b.a_dict())
    assert _puntos(b2.primitivas(t)) == pytest.approx(pts)
    # mover la curva arrastra al texto
    b.transformar([circ], dx=100)
    assert min(x for x, _y in _puntos(b.primitivas(t))) > 60
    # escalar la curva con el texto escala también el desfase
    b.escalar([circ, t], (100, 0), 2)
    assert b.curvas[t].camino_desfase == 2 and b.curvas[t].altura == 12
    # borrar la curva deja el texto recto
    b.eliminar(circ)
    assert b.curvas[t].camino is None and b.primitivas(t)
    with pytest.raises(ErrorBoceto):
        b.agregar_texto((0, 0), "x", camino=t)                        # un texto no puede ser camino
    with pytest.raises(ErrorBoceto):
        b.agregar_texto((0, 0), "x", camino=12345)
    with pytest.raises(ErrorBoceto):
        b.agregar_texto((0, 0), "x", camino_lado="arriba")


@hay_arial
def test_add_text_en_curva_por_api(s):
    c = ok(api.llamar(s, "draw_circle", {"radius": 30}))["entities"][0]["id"]
    r = ok(api.llamar(s, "add_text", {"text": "OMNICAD", "height": 6, "path_entity": c, "path_side": "right",
                                      "path_position": 0.25}))
    tid = next(e["id"] for e in r["entities"] if e["type"] == "text")
    t = next(e for e in ok(api.llamar(s, "get_sketch", {}))["entities"] if e["id"] == tid)
    assert t["path_entity"] == c and t["path_side"] == "right" and t["align"] == "center"
    ok(api.llamar(s, "edit_text", {"entity": tid, "fit_path": True, "path_offset": 2}))
    t = next(e for e in ok(api.llamar(s, "get_sketch", {}))["entities"] if e["id"] == tid)
    assert t["fit_path"] is True and t["path_offset"] == 2
    ok(api.llamar(s, "edit_text", {"entity": tid, "path_entity": 0}))
    t = next(e for e in ok(api.llamar(s, "get_sketch", {}))["entities"] if e["id"] == tid)
    assert "path_entity" not in t
    falla(api.llamar(s, "add_text", {"text": "x", "path_entity": c, "path_position": 2}), "INVALID_ARGUMENTS")
    falla(api.llamar(s, "add_text", {"text": "x", "path_entity": 999}), "INVALID_GEOMETRY")


@hay_arial
def test_herramienta_texto_sobre_una_curva_en_la_interfaz(app_qt):
    from omnicad.nucleo.geometria import Plano
    from omnicad.restricciones import Boceto
    from omnicad.timeline.parametros import TablaParametros
    from omnicad.ui.editor_boceto import Lienzo
    b = Boceto()
    circ = b.agregar_circulo((0, 0), 30)
    lz = Lienzo(b, TablaParametros().evaluar, plano=Plano("XY"))
    lz.ajustar_grilla = False
    lz.opciones["camino_lado"] = "der"
    lz.set_herramienta("texto")
    lz.clics.append((None, (0.0, 30.0)))                              # clic arriba, sobre el círculo
    lz._procesar_clics()
    lz.entrada.aceptado.emit(["TOP", "6", "0"])
    t = next(c for c in lz.b.curvas.values() if c.tipo == "texto")
    assert t.camino == circ and t.camino_lado == "der" and t.camino_pos == pytest.approx(0.25, abs=0.01)
    assert min(y for _x, y in _puntos(lz.b.primitivas(t.id))) > 20


@hay_arial
def test_texto_con_cuadro_del_ratón_y_cambios_en_vivo(app_qt):
    """Como Fusion: dos esquinas dan el cuadro (alto = altura de la letra, ancho = caja) y lo escrito se ve en vivo."""
    from omnicad.nucleo.geometria import Plano
    from omnicad.restricciones import Boceto
    from omnicad.timeline.parametros import TablaParametros
    from omnicad.ui.editor_boceto import Lienzo
    b = Boceto()
    lz = Lienzo(b, TablaParametros().evaluar, plano=Plano("XY"))
    lz.ajustar_grilla = False
    lz.set_herramienta("texto")
    lz.clics.append((None, (10.0, 5.0)))
    lz._procesar_clics()
    assert lz.entrada is None and len(lz.clics) == 1         # espera la esquina opuesta
    lz.clics.append((None, (70.0, 25.0)))
    lz._procesar_clics()
    assert lz.entrada is not None
    assert lz.entrada.campos[1].text() == "20"                # altura = alto del cuadro
    ancho_antes = max(x for poli in lz._previa_polis for x, _y in poli)
    assert lz._previa_polis and ancho_antes <= 70.0 + 1e-6
    lz.entrada.campos[0].setText("OJO")                       # cambio en vivo: otro texto, otros contornos
    assert lz._previa_polis
    lz.entrada.campos[1].setText("10")
    alto = max(y for poli in lz._previa_polis for _x, y in poli) - min(y for poli in lz._previa_polis for _x, y in poli)
    assert alto <= 10.5
    assert not b.curvas                                       # nada se crea hasta aceptar
    lz.entrada.aceptado.emit(["OJO", "10", "0", "0", "1"])
    t = next(c for c in b.curvas.values() if c.tipo == "texto")
    assert t.ancho_caja == pytest.approx(60.0) and t.ancla_v == "arriba" and t.texto == "OJO"
    assert t.punto is not None and lz._previa_polis == []


@hay_arial
def test_un_texto_se_agarra_desde_cualquier_parte_de_su_caja(app_qt):
    """Antes había que acertarle al borde de una letra: ahora vale toda la caja, resalta y se arrastra."""
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from omnicad.nucleo.geometria import Plano
    from omnicad.restricciones import Boceto
    from omnicad.timeline.parametros import TablaParametros
    from omnicad.ui.editor_boceto import Lienzo
    b = Boceto()
    tid = b.agregar_texto((0, 0), "HOLA", 20, 0, "Arial")
    lz = Lienzo(b, TablaParametros().evaluar, plano=Plano("XY"))
    lz.resize(800, 600)
    lz.ajustar_grilla = False
    lz._camara()
    pts = _puntos(b.primitivas(tid))
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    centro = (sum(xs) / len(xs), (min(ys) + max(ys)) / 2)
    # el centro de la «O»: está lejos de cualquier trazo de letra (más de 6 px) y aun así es el texto
    hueco = lz.a_px(*centro)
    assert lz._curva_cercana(hueco) == tid
    assert lz._curva_cercana(lz.a_px(max(xs) + 50, centro[1])) is None      # lejos de la caja: nada
    lz._actualizar_sobre(hueco)
    assert lz._sobre == tid
    lz._actualizar_sobre(lz.a_px(max(xs) + 50, centro[1]))
    assert lz._sobre is None
    # arrastrarlo desde ese lugar lo mueve (texto suelto)
    x0, y0 = b.coords(b.curvas[tid].punto)
    lz._presionar_seleccion(hueco, Qt.NoModifier)
    assert lz._arrastre == ("curva", tid, "mover")
    destino = lz.a_px(centro[0] + 15, centro[1] + 10)
    lz.mouseMoveEvent(QMouseEvent(QEvent.Type.MouseMove, QPointF(destino), QPointF(destino), Qt.NoButton, Qt.LeftButton, Qt.NoModifier))
    lz.mouseReleaseEvent(QMouseEvent(QEvent.Type.MouseButtonRelease, QPointF(destino), QPointF(destino), Qt.LeftButton, Qt.NoButton,
                                     Qt.NoModifier))
    x1, y1 = b.coords(b.curvas[tid].punto)
    assert (x1 - x0, y1 - y0) == pytest.approx((15.0, 10.0), abs=0.5)


def test_zonas_de_agarre_generosas_y_resaltado_de_manijas_y_circulos(app_qt):
    from PySide6.QtCore import QPointF
    from omnicad.nucleo.geometria import Plano
    from omnicad.restricciones import Boceto
    from omnicad.timeline.parametros import TablaParametros
    from omnicad.ui.editor_boceto import Lienzo
    b = Boceto()
    cid = b.agregar_circulo((0, 0), 15)                # un círculo chico en pantalla (60 px de radio)
    lin = b.agregar_linea((40, 0), (80, 0))
    lz = Lienzo(b, TablaParametros().evaluar, plano=Plano("XY"))
    lz.resize(800, 600)
    lz.ajustar_grilla = False
    lz._camara()
    # circulo chico: se agarra desde adentro (lejos del trazo y del centro)
    dentro = lz.a_px(8.0, 4.0)
    assert lz.entidad_en(dentro) == cid
    # un círculo grande no: su interior sigue libre para la ventana de selección
    b2 = Boceto()
    b2.agregar_circulo((0, 0), 60)
    lz2 = Lienzo(b2, TablaParametros().evaluar, plano=Plano("XY"))
    lz2.resize(800, 600)
    lz2.ajustar_grilla = False
    lz2._camara()
    assert lz2.entidad_en(lz2.a_px(20.0, 10.0)) is None
    # un punto se agarra desde 10 px (antes 8)
    p = next(iter(b.puntos))
    q = lz.a_px(*b.coords(p))
    assert lz._punto_cercano(QPointF(q.x() + 10, q.y())) == p
    # marco: al elegir algo, pasar sobre una manija la resalta
    lz.seleccion = [cid, lin]
    caja = lz._caja_marco()
    m = lz._manijas_marco(caja)["escala0"]
    lz._actualizar_sobre(QPointF(m.x() + 3, m.y() + 3))
    assert lz._manija_sobre == "escala0" and lz._sobre is None


@hay_arial
def test_arrastrar_un_texto_en_curva_lo_desliza_por_la_curva(app_qt):
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from omnicad.nucleo.geometria import Plano
    from omnicad.restricciones import Boceto
    from omnicad.timeline.parametros import TablaParametros
    from omnicad.ui.editor_boceto import Lienzo
    b = Boceto()
    circ = b.agregar_circulo((0, 0), 30)
    tid = b.agregar_texto((0, 0), "ARRIBA", 6, 0, "Arial", camino=circ, camino_pos=0.25, alineacion="centro")
    lz = Lienzo(b, TablaParametros().evaluar, plano=Plano("XY"))
    lz.resize(800, 600)
    lz.ajustar_grilla = False
    lz._camara()
    t = b.curvas[tid]
    x, y = _puntos(b.primitivas(tid))[0]                      # un punto de las letras
    ini = lz.a_px(x, y)
    lz._presionar_seleccion(ini, Qt.NoModifier)
    assert lz._arrastre == ("curva", tid, "deslizar")
    # arrastrar un cuarto de vuelta por el círculo: del tope (0°) hacia un costado
    destino = lz.a_px(x + 30, y - 30)
    lz.mouseMoveEvent(QMouseEvent(QEvent.Type.MouseMove, QPointF(destino), QPointF(destino), Qt.NoButton, Qt.LeftButton, Qt.NoModifier))
    lz.mouseReleaseEvent(QMouseEvent(QEvent.Type.MouseButtonRelease, QPointF(destino), QPointF(destino), Qt.LeftButton, Qt.NoButton,
                                     Qt.NoModifier))
    assert t.camino_pos != pytest.approx(0.25, abs=0.02)      # se deslizó
    nuevo = t.camino_pos
    lz.deshacer()
    assert b.curvas[tid].camino_pos == pytest.approx(0.25) and nuevo != 0.25


@hay_arial
def test_el_texto_pendiente_no_se_pierde_con_clic_derecho_ni_al_cambiar_de_herramienta(app_qt):
    """Bug: con el cuadro abierto, el clic derecho (menú radial › Aceptar) descartaba el texto escrito."""
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from omnicad.nucleo.geometria import Plano
    from omnicad.restricciones import Boceto
    from omnicad.timeline.parametros import TablaParametros
    from omnicad.ui.editor_boceto import Lienzo

    def nuevo():
        b = Boceto()
        lz = Lienzo(b, TablaParametros().evaluar, plano=Plano("XY"))
        lz.ajustar_grilla = False
        lz.set_herramienta("texto")
        for xy in ((0.0, 0.0), (60.0, 20.0)):
            lz.clics.append((None, xy))
            lz._procesar_clics()
        lz.entrada.campos[0].setText("HOLA")
        return b, lz

    def textos(b):
        return [c.texto for c in b.curvas.values() if c.tipo == "texto"]

    b, lz = nuevo()                                           # clic derecho
    lz.mousePressEvent(QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(5, 5), QPointF(5, 5), Qt.RightButton,
                                   Qt.RightButton, Qt.NoModifier))
    assert textos(b) == ["HOLA"] and lz.entrada is None
    b, lz = nuevo()                                           # cambiar de herramienta
    lz.set_herramienta("linea")
    assert textos(b) == ["HOLA"]
    b, lz = nuevo()                                           # terminar el boceto
    lz.confirmar_texto_pendiente()
    assert textos(b) == ["HOLA"]


@hay_arial
def test_el_texto_se_escribe_directo_en_el_cuadro(app_qt):
    """Las teclas escriben en el lienzo (no en la barra): Enter = línea nueva, Ctrl+Enter acepta, Esc cancela."""
    from PySide6.QtCore import QEvent, QPoint, Qt
    from PySide6.QtGui import QKeyEvent
    from omnicad.nucleo.geometria import Plano
    from omnicad.restricciones import Boceto
    from omnicad.timeline.parametros import TablaParametros
    from omnicad.ui.editor_boceto import Lienzo
    b = Boceto()
    lz = Lienzo(b, TablaParametros().evaluar, plano=Plano("XY"))
    lz.ajustar_grilla = False

    def tecla(k, texto="", mod=Qt.NoModifier):
        lz.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, k, mod, texto))

    lz.set_herramienta("texto")
    for xy in ((0.0, 0.0), (60.0, 20.0)):
        lz.clics.append((None, xy))
        lz._procesar_clics()
    assert lz.entrada.campos[0].isHidden()                    # el campo «Texto» ya no está en la barra
    # cursor parpadeante: en el cuadro (arriba a la izquierda, tras el «Texto» de relleno sale a su derecha)
    assert lz._caret is not None and lz._t_caret.isActive()
    antes = lz._caret_on
    lz._parpadeo()
    assert lz._caret_on is not antes
    # la barra se mueve arrastrándola
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QMouseEvent
    lz.resize(3000, 900)                                       # la barra no sale del lienzo
    barra = lz.entrada
    p0 = barra.pos()
    barra.mousePressEvent(QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(0, 0), QPointF(0, 0), Qt.LeftButton, Qt.LeftButton,
                                      Qt.NoModifier))
    barra.mouseMoveEvent(QMouseEvent(QEvent.Type.MouseMove, QPointF(5, 7), QPointF(5, 7), Qt.NoButton, Qt.LeftButton, Qt.NoModifier))
    barra.mouseReleaseEvent(QMouseEvent(QEvent.Type.MouseButtonRelease, QPointF(5, 7), QPointF(5, 7), Qt.LeftButton, Qt.NoButton,
                                        Qt.NoModifier))
    assert barra.pos() == p0 + QPoint(5, 7) and barra._arrastre is None
    for ch in "AB":
        tecla(ord(ch), ch)
    assert lz.entrada.campos[0].text() == "AB"                # la 1.ª tecla reemplazó el «Texto» de relleno
    tecla(Qt.Key_Return)
    tecla(ord("C"), "C")
    assert lz.entrada.campos[0].text() == "AB\\nC" and lz._previa_polis
    tecla(Qt.Key_Backspace)
    tecla(Qt.Key_Backspace)
    assert lz.entrada.campos[0].text() == "AB"
    tecla(Qt.Key_Return, mod=Qt.ControlModifier)              # Ctrl+Enter acepta
    t = next(c for c in b.curvas.values() if c.tipo == "texto")
    assert t.texto == "AB" and lz.entrada is None
    # Esc cancela sin crear nada
    lz.set_herramienta("texto")
    for xy in ((0.0, 40.0), (30.0, 50.0)):
        lz.clics.append((None, xy))
        lz._procesar_clics()
    tecla(ord("Z"), "Z")
    tecla(Qt.Key_Escape)
    assert lz.entrada is None and len([c for c in b.curvas.values() if c.tipo == "texto"]) == 1


@hay_arial
def test_editar_un_texto_muestra_sus_opciones_en_la_paleta(app_qt):
    """Doble clic sobre un texto con «Seleccionar»: la paleta enseña Fuente/Negrita/Alineación y después vuelve."""
    from omnicad.nucleo.geometria import Plano
    from omnicad.restricciones import Boceto
    from omnicad.timeline.parametros import TablaParametros
    from omnicad.ui.editor_boceto import Lienzo
    from PySide6.QtWidgets import QFormLayout
    from omnicad.ui.modo_boceto import PaletaBoceto, PanelCaracter
    b = Boceto()
    tid = b.agregar_texto((0, 0), "HOLA", 10, 0, "Arial", True, False)
    lz = Lienzo(b, TablaParametros().evaluar, plano=Plano("XY"))
    paleta = PaletaBoceto()
    lz.texto_en_edicion.connect(
        lambda: paleta.set_herramienta("texto", lz.lados, lz.opcion_cota, lz.opciones))
    lz.herramienta_cambiada.connect(
        lambda h: paleta.set_herramienta(h, lz.lados, lz.opcion_cota, lz.opciones))
    assert lz.herramienta == "seleccionar"
    lz.editar_texto(tid, lz.rect().center())
    etiquetas = [paleta.form_contexto.itemAt(i, QFormLayout.ItemRole.LabelRole).widget().text()
                 for i in range(paleta.form_contexto.rowCount())]
    assert etiquetas == []                                    # la paleta ya no mezcla opciones de texto
    assert lz.opciones["negrita"] is True                     # parte de lo que ya tiene el texto
    # la fuente, el estilo y lo demás están en el panel «Carácter», que arranca con lo que ya tiene el texto
    panel = PanelCaracter()
    panel.cargar(lz.opciones)
    assert panel.fuente.currentText() == "Arial" and panel.estilo.currentData() == "negrita"
    assert panel.alineacion.currentData() == lz.opciones["alineacion"] == "izq"
    lz._cerrar_entrada()
    assert paleta.form_contexto.rowCount() == 0               # «Seleccionar» no tiene opciones propias


@hay_arial
def test_panel_caracter_cambia_las_opciones_y_se_carga_sin_emitir(app_qt):
    """El panel «Carácter»: cada control emite (clave, valor); `cargar` lo llena sin emitir nada."""
    from omnicad.ui.modo_boceto import PanelCaracter, familias_filtradas
    panel = PanelCaracter()
    cambios = []
    panel.cambio.connect(lambda k, v: cambios.append((k, v)))
    panel.cargar({"fuente": "Arial", "negrita": True, "cursiva": True, "kerning": False, "subrayado": "doble",
                  "tachado": "simple", "grosor_decoracion": 0.4, "desfase_base": 1.5, "inclinacion": 12.0,
                  "escala_h": 150.0, "escala_v": 80.0, "capitalizacion": "versalitas", "sin_division": True})
    assert cambios == []
    assert panel.estilo.currentData() == "negrita_cursiva" and not panel.b_kerning.isChecked()
    assert panel.subrayado.currentData() == "doble" and panel.tachado.currentData() == "simple"
    assert panel.grosor.value() == pytest.approx(0.4) and panel.escala_h.value() == pytest.approx(150.0)
    assert panel.capitalizacion.currentData() == "versalitas" and panel.sin_division.isChecked()
    panel.escala_v.setValue(120.0)
    panel.subrayado.setCurrentIndex(panel.subrayado.findData("simple"))
    panel.estilo.setCurrentIndex(panel.estilo.findData("cursiva"))
    panel.b_kerning.setChecked(True)
    assert ("escala_v", 120.0) in cambios and ("subrayado", "simple") in cambios
    assert ("negrita", False) in cambios and ("cursiva", True) in cambios and ("kerning", True) in cambios
    # el filtro de familias: «Todo» las trae todas; «Con cursiva» solo las que tienen cursiva real
    todas = familias_filtradas("todo")
    assert "Arial" in todas and "Arial" in familias_filtradas("cursiva")
    assert set(familias_filtradas("variables")) <= set(todas)


# ---------------------------------------------------------------- escribir y mover el cursor dentro del texto
def _lienzo_con_cuadro(texto="", clics=((0.0, 0.0), (80.0, 20.0)), resize=(800, 600)):
    """Lienzo con la herramienta Texto y el cuadro abierto (con `texto` escrito, o el de relleno si va vacío)."""
    from omnicad.nucleo.geometria import Plano
    from omnicad.restricciones import Boceto
    from omnicad.timeline.parametros import TablaParametros
    from omnicad.ui.editor_boceto import Lienzo
    b = Boceto()
    lz = Lienzo(b, TablaParametros().evaluar, plano=Plano("XY"))
    lz.ajustar_grilla = False
    lz.resize(*resize)
    lz.set_herramienta("texto")
    for xy in clics:
        lz.clics.append((None, xy))
        lz._procesar_clics()
    if texto:
        lz.entrada.campos[0].setText(texto.replace("\n", "\\n"))
        lz._previa_texto["reemplazar"] = False
        lz._previa_texto["ancla"] = None
        lz._previa_texto["cursor"] = len(texto)
        lz._actualizar_cursor()
    return b, lz


def _tecla(lz, k, texto="", mod=None):
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent
    lz.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, k, mod if mod is not None else Qt.NoModifier, texto))


def _escribir(lz, cadena):
    for ch in cadena:
        _tecla(lz, ord(ch.upper()), ch)


@hay_arial
def test_el_cursor_se_mueve_con_las_flechas_y_se_edita_en_cualquier_parte(app_qt):
    """Bug: el cursor no se movía y solo se podía agregar o borrar al final. Ahora se edita donde está el cursor."""
    from PySide6.QtCore import Qt
    b, lz = _lienzo_con_cuadro()
    texto = lambda: lz._texto_real()  # noqa: E731
    _escribir(lz, "HOLA")
    assert texto() == "HOLA" and lz._previa_texto["cursor"] == 4
    _tecla(lz, Qt.Key_Left)
    _tecla(lz, Qt.Key_Left)
    _tecla(lz, ord("X"), "X")                                  # en el medio, no al final
    assert texto() == "HOXLA" and lz._previa_texto["cursor"] == 3
    _tecla(lz, Qt.Key_Home)
    _tecla(lz, ord("1"), "1")
    assert texto() == "1HOXLA" and lz._previa_texto["cursor"] == 1
    _tecla(lz, Qt.Key_Delete)                                  # borra la letra de la derecha
    assert texto() == "1OXLA"
    _tecla(lz, Qt.Key_Backspace)                               # y la de la izquierda
    assert texto() == "OXLA" and lz._previa_texto["cursor"] == 0
    _tecla(lz, Qt.Key_Backspace)                               # al principio no hace nada
    assert texto() == "OXLA"
    _tecla(lz, Qt.Key_End)
    _tecla(lz, Qt.Key_Left, mod=Qt.ShiftModifier)              # selecciona lo de la izquierda
    _tecla(lz, Qt.Key_Left, mod=Qt.ShiftModifier)
    assert lz._seleccion_texto() == (2, 4) and len(lz._sel_texto) == 1
    _tecla(lz, ord("Z"), "Z")                                  # escribir reemplaza la selección
    assert texto() == "OXZ" and lz._seleccion_texto() is None
    _tecla(lz, Qt.Key_Left, mod=Qt.ControlModifier)            # Ctrl+← salta la palabra
    assert lz._previa_texto["cursor"] == 0
    _tecla(lz, Qt.Key_A, "a", Qt.ControlModifier)              # Ctrl+A
    assert lz._seleccion_texto() == (0, 3)
    _tecla(lz, Qt.Key_Backspace)
    assert texto() == ""
    _tecla(lz, Qt.Key_Z, "z", Qt.ControlModifier)              # Ctrl+Z vuelve atrás
    assert texto() == "OXZ"
    assert lz._caret is not None                               # el cursor se dibuja donde está


@hay_arial
def test_el_cursor_sube_y_baja_entre_lineas_y_acepta_el_texto_editado(app_qt):
    from PySide6.QtCore import Qt
    b, lz = _lienzo_con_cuadro("AAAA\nBBBB\nCC")
    d = lz._previa_texto
    assert d["cursor"] == 12
    _tecla(lz, Qt.Key_Up)                                      # de la 3.ª línea a la 2.ª, misma columna (≈ al final de CC)
    assert 5 <= d["cursor"] <= 9
    _tecla(lz, Qt.Key_Home)
    assert d["cursor"] == 5                                    # principio de la línea 2
    _tecla(lz, Qt.Key_End)
    assert d["cursor"] == 9                                    # final de la línea 2 (antes del salto)
    _tecla(lz, Qt.Key_Up)
    _tecla(lz, Qt.Key_Up)                                      # ya en la primera línea: va al principio
    assert d["cursor"] == 0
    _tecla(lz, Qt.Key_Down)
    assert 5 <= d["cursor"] <= 9
    _tecla(lz, Qt.Key_Return)                                  # Enter parte la línea en el cursor
    assert lz._texto_real().count("\n") == 3
    _tecla(lz, Qt.Key_Return, mod=Qt.ControlModifier)          # Ctrl+Enter acepta
    t = next(c for c in b.curvas.values() if c.tipo == "texto")
    assert t.texto.count("\n") == 3 and t.texto.replace("\n", "") == "AAAABBBBCC"


@hay_arial
def test_clic_arrastre_y_doble_clic_mueven_el_cursor_y_seleccionan(app_qt):
    """Con el ratón: clic = cursor ahí, arrastrar = selección, doble clic = palabra; clic afuera = aceptar."""
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    b, lz = _lienzo_con_cuadro("HOLA MUNDO", clics=((-30.0, 0.0), (60.0, 20.0)))
    lz.show()
    d = lz._previa_texto
    paradas = d["mapa"]["paradas"]

    def ev(tipo, xy, boton=Qt.LeftButton, botones=Qt.LeftButton):
        pos = QPointF(lz.a_px(*xy))
        return QMouseEvent(tipo, pos, pos, boton, botones, Qt.NoModifier)

    def centro(i):
        a, c = paradas[i]
        return ((a[0] + c[0]) / 2, (a[1] + c[1]) / 2)
    # clic justo en el borde de la 4.ª letra («A»): el cursor queda en la posición 3
    lz.mousePressEvent(ev(QEvent.Type.MouseButtonPress, centro(3)))
    lz.mouseReleaseEvent(ev(QEvent.Type.MouseButtonRelease, centro(3), botones=Qt.NoButton))
    assert d["cursor"] == 3 and d["ancla"] is None and lz.entrada is not None
    # arrastrar de la posición 1 a la 4 selecciona 1..4
    lz.mousePressEvent(ev(QEvent.Type.MouseButtonPress, centro(1)))
    lz.mouseMoveEvent(ev(QEvent.Type.MouseMove, centro(4), boton=Qt.NoButton))
    lz.mouseReleaseEvent(ev(QEvent.Type.MouseButtonRelease, centro(4), botones=Qt.NoButton))
    assert lz._seleccion_texto() == (1, 4)
    # doble clic dentro de «MUNDO» elige la palabra entera
    lz.mouseDoubleClickEvent(ev(QEvent.Type.MouseButtonDblClick, centro(7)))
    assert lz._seleccion_texto() == (5, 10)
    # clic bien lejos del texto: lo acepta
    lz.mousePressEvent(ev(QEvent.Type.MouseButtonPress, (-30.0, 150.0)))
    assert lz.entrada is None
    assert any(c.tipo == "texto" and c.texto == "HOLA MUNDO" for c in b.curvas.values())


@hay_arial
def test_editar_un_texto_existente_pone_el_cursor_donde_se_hizo_doble_clic(app_qt):
    from omnicad.nucleo.geometria import Plano
    from omnicad.restricciones import Boceto
    from omnicad.timeline.parametros import TablaParametros
    from omnicad.ui.editor_boceto import Lienzo
    b = Boceto()
    tid = b.agregar_texto((0, 0), "ABCDEF", 10, 0, "Arial")
    lz = Lienzo(b, TablaParametros().evaluar, plano=Plano("XY"))
    lz.ajustar_grilla = False
    lz.resize(800, 600)
    lz._camara()
    # el borde entre la 3.ª y la 4.ª letra
    prim = b.primitivas(tid)
    xs = sorted({round(q[0], 3) for p in prim for q in ([p[2], p[3]] if p[0] == "linea" else p[2])})
    lz.editar_texto(tid, lz.a_px(xs[0], 5.0))                  # a la izquierda de todo: cursor al principio
    assert lz._previa_texto["cursor"] == 0
    lz._cerrar_entrada()
    lz.editar_texto(tid, lz.a_px(xs[-1] + 1.0, 5.0))           # a la derecha de todo: cursor al final
    assert lz._previa_texto["cursor"] == 6
    # y se escribe ahí
    _tecla(lz, 0x20, " ")
    assert lz._texto_real() == "ABCDEF "


@hay_arial
def test_el_cursor_sigue_al_texto_girado_y_con_inclinacion(app_qt):
    """El cursor es un segmento sobre la letra, girado con el texto e inclinado con el sesgo."""
    from omnicad.restricciones.boceto import Texto, paradas_cursor
    t = Texto(1, (0.0, 0.0), "HOLA", "Arial", 10.0, 0.0)
    recto = paradas_cursor(t, (0.0, 0.0))
    assert len(recto["paradas"]) == 5 and recto["lineas"] == [(0, 4)]
    (ax, ay), (bx, by) = recto["paradas"][0]
    assert ax == pytest.approx(bx) and by > ay                 # vertical y de abajo hacia arriba
    t.angulo = 90.0
    (ax, ay), (bx, by) = paradas_cursor(t, (0.0, 0.0))["paradas"][0]
    assert ay == pytest.approx(by) and bx < ax                 # girado 90°: horizontal, hacia la izquierda
    t.angulo, t.inclinacion = 0.0, 30.0
    (ax, ay), (bx, by) = paradas_cursor(t, (0.0, 0.0))["paradas"][0]
    assert bx - ax == pytest.approx((by - ay) * math.tan(math.radians(30)), rel=1e-6)
    # texto en curva: un segmento por posición, pegado a la curva
    t2 = Texto(2, (0.0, 0.0), "HOLA", "Arial", 10.0, 0.0, camino=3)
    info = paradas_cursor(t2, (0, 0), ("linea", 3, (0.0, 0.0), (100.0, 0.0)))
    assert len(info["paradas"]) == 5 and info["linea_de"] == [0] * 5
    xs = [seg[0][0] for seg in info["paradas"]]
    assert xs == sorted(xs) and xs[-1] - xs[0] > 10


# ---------------------------------------------------------------- opciones del panel «Carácter» (núcleo)
@hay_arial
def test_kerning_inclinacion_y_escalas_del_texto():
    base = caja(fuentes.contornos_texto("AVAVA", "Arial", 10))
    sin = caja(fuentes.contornos_texto("AVAVA", "Arial", 10, kerning=False))
    assert sin[2] - sin[0] > (base[2] - base[0]) + 0.5          # sin kerning, «AV» queda más ancho
    h = caja(fuentes.contornos_texto("HHH", "Arial", 10))
    inclinado = caja(fuentes.contornos_texto("HHH", "Arial", 10, inclinacion=20))
    assert inclinado[2] - inclinado[0] == pytest.approx((h[2] - h[0]) + (h[3] - h[1]) * math.tan(math.radians(20)),
                                                        abs=0.05)
    assert inclinado[1] == pytest.approx(h[1], abs=1e-6) and inclinado[3] == pytest.approx(h[3], abs=1e-6)
    ancho = caja(fuentes.contornos_texto("HHH", "Arial", 10, escala_h=200))
    assert ancho[2] - ancho[0] == pytest.approx(2 * (h[2] - h[0]), rel=0.01) and ancho[3] == pytest.approx(h[3])
    bajo = caja(fuentes.contornos_texto("HHH", "Arial", 10, escala_v=50))
    assert bajo[3] - bajo[1] == pytest.approx((h[3] - h[1]) / 2, rel=0.01) and bajo[2] == pytest.approx(h[2])
    sube = caja(fuentes.contornos_texto("HHH", "Arial", 10, desfase_base=3.0))
    assert sube[1] == pytest.approx(h[1] + 3.0) and sube[2] == pytest.approx(h[2])


@hay_arial
def test_capitalizacion_del_texto():
    mayus = fuentes.contornos_texto("hola mundo", "Arial", 10, capitalizacion="mayusculas")
    assert caja(mayus) == pytest.approx(caja(fuentes.contornos_texto("HOLA MUNDO", "Arial", 10)))
    minus = fuentes.contornos_texto("HOLA", "Arial", 10, capitalizacion="minusculas")
    assert caja(minus) == pytest.approx(caja(fuentes.contornos_texto("hola", "Arial", 10)))
    titulo = fuentes.contornos_texto("hola MUNDO", "Arial", 10, capitalizacion="titulo")
    assert caja(titulo) == pytest.approx(caja(fuentes.contornos_texto("Hola Mundo", "Arial", 10)))
    # versalitas: la «h» y la «a» salen como mayúsculas más chicas que la «H» de adelante
    versa = caja(fuentes.contornos_texto("Hh", "Arial", 10, capitalizacion="versalitas"))
    grande = caja(fuentes.contornos_texto("HH", "Arial", 10))
    assert versa[3] == pytest.approx(grande[3]) and versa[2] < grande[2] - 0.5
    with pytest.raises(fuentes.ErrorFuente):
        fuentes.contornos_texto("a", "Arial", 10, capitalizacion="raro")


@hay_arial
def test_subrayado_y_tachado_son_barras_cerradas_que_forman_perfiles():
    base = fuentes.contornos_texto("HI", "Arial", 10)
    sub = fuentes.contornos_texto("HI", "Arial", 10, subrayado="simple", grosor_decoracion=0.8)
    assert len(sub) == len(base) + 4                           # un rectángulo cerrado por línea
    barra = sub[len(base):]
    assert all(p[0] == "linea" for p in barra)
    ys = sorted({round(q[1], 6) for p in barra for q in (p[2], p[3])})
    assert len(ys) == 2 and ys[1] - ys[0] == pytest.approx(0.8) and ys[1] < 0      # debajo de la línea base
    assert caja(barra)[0] == 0.0 and caja(barra)[2] >= caja(base)[2]               # de lado a lado del texto
    assert len(fuentes.contornos_texto("HI", "Arial", 10, subrayado="doble", tachado="doble")) == len(base) + 16
    tach = caja(fuentes.contornos_texto("HI", "Arial", 10, tachado="simple")[len(base):])
    assert 1.5 < (tach[1] + tach[3]) / 2 < 4.5                 # a media altura de la letra
    dos = fuentes.contornos_texto("HI\nHI", "Arial", 10, subrayado="simple")
    assert len(dos) == len(fuentes.contornos_texto("HI\nHI", "Arial", 10)) + 8        # una barra por línea
    with pytest.raises(fuentes.ErrorFuente):
        fuentes.contornos_texto("a", "Arial", 10, subrayado="triple")


@hay_arial
def test_sin_division_y_mapa_de_posiciones():
    largo = "uno dos tres cuatro cinco seis"
    partido = caja(fuentes.contornos_texto(largo, "Arial", 10, ancho_caja=40))
    entero = caja(fuentes.contornos_texto(largo, "Arial", 10, ancho_caja=40, sin_division=True))
    assert partido[1] < entero[1] - 10 and entero[2] > 40      # sin división no parte la línea
    m = fuentes.mapa_texto("ab\ncde", "Arial", 10)
    assert len(m["paradas"]) == 7 and m["lineas"] == [(0, 2), (3, 6)] and m["linea_de"] == [0, 0, 0, 1, 1, 1, 1]
    xs = [p[0] for p in m["paradas"][:3]]
    assert xs[0] == 0.0 and xs == sorted(xs)
    assert m["paradas"][3][0] == 0.0 and m["paradas"][3][1] < m["paradas"][0][1]       # 2.ª línea, más abajo
    # con caja que parte líneas, cada posición cae en la línea donde se ve
    m = fuentes.mapa_texto(largo, "Arial", 10, ancho_caja=40)
    assert len(m["lineas"]) > 1 and m["linea_de"][len(largo)] == len(m["lineas"]) - 1
    assert m["paradas"][len(largo)][1] < m["paradas"][0][1]
    assert fuentes.mapa_texto("", "Arial", 10)["paradas"] == [(0.0, 0.0)]


@hay_arial
def test_opciones_de_caracter_por_api_se_guardan_y_cargan(s):
    r = ok(api.llamar(s, "add_text", {"text": "Hola", "height": 8, "kerning": False, "skew": 10, "scale_x": 120,
                                      "scale_y": 90, "baseline_shift": 2, "case": "upper", "underline": "double",
                                      "strikethrough": "single", "decoration_thickness": 0.5, "no_wrap": True,
                                      "box_width": 50}))
    tid = r["entities"][0]["id"]
    t = next(c for c in ok(api.llamar(s, "get_sketch", {}))["entities"] if c["id"] == tid)
    assert (t["kerning"], t["skew"], t["scale_x"], t["scale_y"], t["baseline_shift"]) == (False, 10, 120, 90, 2)
    assert (t["case"], t["underline"], t["strikethrough"], t["decoration_thickness"], t["no_wrap"]) == \
        ("upper", "double", "single", 0.5, True)
    assert r["profiles"] > 4                                   # letras y barras
    ok(api.llamar(s, "edit_text", {"entity": tid, "underline": "none", "case": "none", "skew": 0}))
    t = next(c for c in ok(api.llamar(s, "get_sketch", {}))["entities"] if c["id"] == tid)
    assert t["underline"] == "none" and t["case"] == "none" and t["skew"] == 0 and t["strikethrough"] == "single"
    # los valores por defecto no ensucian el archivo
    from omnicad.restricciones import Boceto
    b = Boceto()
    b.agregar_texto((0, 0), "A", altura=5)
    d = b.a_dict()["curvas"][0]
    assert not {"kerning", "inclinacion", "escala_h", "escala_v", "subrayado", "tachado", "capitalizacion"} & set(d)
    b.agregar_texto((0, 10), "B", altura=5, subrayado="simple", escala_h=150.0)
    b2 = Boceto.desde_dict(b.a_dict())
    a, c = list(b2.curvas.values())
    assert (a.subrayado, c.subrayado, c.escala_h) == ("ninguno", "simple", 150.0)


@hay_arial
def test_opciones_de_caracter_por_api_validan(s):
    for mal, kind in (({"case": "raro"}, "INVALID_ARGUMENTS"), ({"underline": "triple"}, "INVALID_ARGUMENTS"),
                      ({"scale_x": 0}, "INVALID_GEOMETRY"), ({"skew": 90}, "INVALID_GEOMETRY"),
                      ({"decoration_thickness": -1}, "INVALID_GEOMETRY"), ({"scale_y": float("nan")},
                                                                           "INVALID_ARGUMENTS")):
        falla(api.llamar(s, "add_text", {"text": "A"} | mal), kind)
    circulo = ok(api.llamar(s, "draw_circle", {"radius": 20}))["entities"][0]["id"]
    r = api.llamar(s, "add_text", {"text": "Curva", "path_entity": circulo, "underline": "single"})
    assert r["ok"] and any("curva" in a for a in r["avisos"])


# ---------------------------------------------------------------- bocetos grandes (fase 7)
def test_boceto_grande_sin_restricciones_no_arma_un_sistema_gigante():
    """Antes, 3000 curvas sueltas pedían una matriz de (18 000)² en el solver y fallaba por memoria."""
    from omnicad.restricciones import Boceto, grados_de_libertad, resolver
    b = Boceto()
    for k in range(3000):
        b.agregar_linea((k, 0.0), (k + 0.5, 1.0))
    # una parte restringida aparte: un rectángulo con dos cotas
    r = b.agregar_rectangulo((0, 10), (20, 20))
    lineas = [i for i in r if b.tipo_de(i) == "linea"]
    b.agregar_cota("distancia", [lineas[0]], "30")
    res = resolver(b, {k: 30.0 for k in b.cotas})
    assert res.ok and res.gdl == 3000 * 4 + 3                         # 4 por línea suelta + 3 del rectángulo
    assert grados_de_libertad(b, {k: 30.0 for k in b.cotas}) == res.gdl
    assert lineas[0] not in res.determinadas


def test_detectar_perfiles_con_cache_y_aristas_partidas():
    from omnicad.nucleo.geometria import Plano
    from omnicad.nucleo.perfiles import detectar
    from omnicad.restricciones import Boceto
    b = Boceto()
    b.agregar_rectangulo((0, 0), (20, 10))
    b.agregar_linea((0, 0), (20, 10))                                 # diagonal: parte el rectángulo
    b.agregar_circulo((30, 5), 3)
    p1 = detectar(b.geometria(), Plano("XY"))
    p2 = detectar(b.geometria(), Plano("XY"))                         # sale del caché, igual
    assert [round(p.area, 6) for p in p1] == [round(p.area, 6) for p in p2]
    assert sorted(round(p.area, 4) for p in p1) == [round(math.pi * 9, 4), 100.0, 100.0]
    assert all(p.firma for p in p1)                                   # cada región sabe de qué curvas salió


# ---------------------------------------------------------------- unir, restar, intersecar y desfasar (fase 6)
def _dos_cuadrados(s):
    ok(api.llamar(s, "draw_rectangle", {"x1": 0, "y1": 0, "x2": 10, "y2": 10}))
    ok(api.llamar(s, "draw_rectangle", {"x1": 5, "y1": 5, "x2": 15, "y2": 15}))
    perfiles = ok(api.llamar(s, "get_sketch", {}))["profiles"]
    assert len(perfiles) == 3                                          # dos «L» y el cuadrado común
    return perfiles


def _area_total(s):
    return sum(p["area"] for p in ok(api.llamar(s, "get_sketch", {}))["profiles"])


def test_combine_profiles_union_resta_e_interseccion():
    for operacion, area in (("union", 175.0), ("intersect", 25.0)):
        s = api.Sesion()
        ok(api.llamar(s, "create_sketch", {"plane": "XY"}))
        _dos_cuadrados(s)
        if operacion == "union":
            r = ok(api.llamar(s, "combine_profiles", {"profiles": "all"}))
        else:                                                          # cuadrado 1 ∩ cuadrado 2, por regiones
            sk = ok(api.llamar(s, "get_sketch", {}))
            uno = [p["index"] for p in sk["profiles"] if max(p["centroid"]) < 10]
            dos = [p["index"] for p in sk["profiles"] if min(p["centroid"]) > 5]
            r = ok(api.llamar(s, "combine_profiles", {"profiles": uno, "operation": "intersect",
                                                      "tool_profiles": dos}))
        assert r["result_area"] == pytest.approx(area) and r["profiles"] >= 1
        if operacion == "union":
            assert r["profiles"] == 1 and _area_total(s) == pytest.approx(175.0)
            assert r["entities_added"] == 8 and r["entities_deleted"] == 8       # contorno limpio, sin internas


def test_combine_profiles_resta_y_errores(s):
    ok(api.llamar(s, "draw_rectangle", {"x1": 0, "y1": 0, "x2": 20, "y2": 20}))
    ok(api.llamar(s, "create_sketch", {"plane": "XY"}))
    ok(api.llamar(s, "draw_rectangle", {"x1": 0, "y1": 0, "x2": 20, "y2": 20}))
    ok(api.llamar(s, "draw_circle", {"radius": 5, "center_x": 10, "center_y": 10}))
    sk = ok(api.llamar(s, "get_sketch", {}))
    disco = next(p["index"] for p in sk["profiles"] if p["area"] < 100)
    anillo = next(p["index"] for p in sk["profiles"] if p["area"] > 100)
    r = ok(api.llamar(s, "combine_profiles", {"profiles": [anillo, disco], "operation": "subtract",
                                              "tool_profiles": [disco]}))
    assert r["result_area"] == pytest.approx(400 - math.pi * 25, rel=1e-6)
    falla(api.llamar(s, "combine_profiles", {"profiles": [0], "operation": "subtract"}), "INVALID_ARGUMENTS")
    falla(api.llamar(s, "combine_profiles", {"profiles": [99]}), "PROFILE_NOT_FOUND")


def test_offset_profiles_circulo_cuadrado_y_texto(s):
    ok(api.llamar(s, "draw_circle", {"radius": 10}))
    r = ok(api.llamar(s, "offset_profiles", {"profiles": [0], "distance": 2}))
    sk = ok(api.llamar(s, "get_sketch", {}))
    radios = sorted(c["radius"] for c in sk["entities"] if c["type"] == "circle")
    assert radios == pytest.approx([10, 12]) and r["profiles"] == 2
    ok(api.llamar(s, "create_sketch", {"plane": "XY"}))
    ok(api.llamar(s, "draw_rectangle", {"x1": 0, "y1": 0, "x2": 10, "y2": 10}))
    ok(api.llamar(s, "offset_profiles", {"profiles": [0], "distance": 1, "corners": "sharp", "keep_original": False}))
    assert _area_total(s) == pytest.approx(144.0)
    ok(api.llamar(s, "create_sketch", {"plane": "XY"}))
    ok(api.llamar(s, "draw_rectangle", {"x1": 0, "y1": 0, "x2": 10, "y2": 10}))
    ok(api.llamar(s, "offset_profiles", {"profiles": [0], "distance": -2, "keep_original": False}))
    assert _area_total(s) == pytest.approx(36.0)
    falla(api.llamar(s, "offset_profiles", {"profiles": [0], "distance": 0}), "INVALID_ARGUMENTS")
    if fuentes.buscar_fuente("Arial") is not None:
        ok(api.llamar(s, "create_sketch", {"plane": "XY"}))
        ok(api.llamar(s, "add_text", {"text": "O", "height": 20}))
        r = ok(api.llamar(s, "offset_profiles", {"profiles": "all", "distance": 0.5}))
        assert r["entities_added"] >= 2 and r["profiles"] >= 3


def test_transform_sketch_mueve_escala_gira_espeja_y_copia(s):
    ok(api.llamar(s, "draw_rectangle", {"x1": 1, "y1": 1, "x2": 11, "y2": 5}))
    arco = ok(api.llamar(s, "draw_arc", {"center_x": 20, "center_y": 0, "start_x": 25, "start_y": 0,
                                         "sweep_angle": 90}))["entities"][0]["id"]

    def caja_lineas():
        sk = ok(api.llamar(s, "get_sketch", {}))
        pts = [v for c in sk["entities"] if c["type"] == "line" for v in (c["start"], c["end"])]
        return min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)
    lineas = [c["id"] for c in ok(api.llamar(s, "get_sketch", {}))["entities"] if c["type"] == "line"]
    ok(api.llamar(s, "transform_sketch", {"entities": lineas, "scale": 2}))          # alrededor de su centro (6, 3)
    assert caja_lineas() == pytest.approx((-4, -1, 16, 7))
    ok(api.llamar(s, "transform_sketch", {"entities": lineas, "dx": 5, "dy": 2}))
    assert caja_lineas() == pytest.approx((1, 1, 21, 9))
    ok(api.llamar(s, "transform_sketch", {"entities": lineas, "angle": 90}))         # gira alrededor de (11, 5)
    assert caja_lineas() == pytest.approx((7, -5, 15, 15))
    # espejo de un arco: sigue siendo un cuarto de círculo, ahora del otro lado
    ok(api.llamar(s, "transform_sketch", {"entities": [arco], "mirror": "horizontal", "center_x": 20,
                                          "center_y": 0}))
    a = next(c for c in ok(api.llamar(s, "get_sketch", {}))["entities"] if c["id"] == arco)
    assert a["radius"] == pytest.approx(5) and max(a["start"][0], a["end"][0]) == pytest.approx(20, abs=1e-6)
    assert min(a["start"][0], a["end"][0]) == pytest.approx(15, abs=1e-6)
    # copia: el original queda
    n = len(ok(api.llamar(s, "get_sketch", {}))["entities"])
    ok(api.llamar(s, "transform_sketch", {"entities": lineas, "dx": 100, "copy": True}))
    assert len(ok(api.llamar(s, "get_sketch", {}))["entities"]) == n + 4
    falla(api.llamar(s, "transform_sketch", {"entities": [999], "dx": 1}), "ENTITY_NOT_FOUND")
    falla(api.llamar(s, "transform_sketch", {"scale": 0}), "INVALID_ARGUMENTS")


# ---------------------------------------------------------------- marco de control en el boceto (fase 5)
def _lienzo_con_dos_lineas(app_qt):
    from omnicad.nucleo.geometria import Plano
    from omnicad.restricciones import Boceto
    from omnicad.timeline.parametros import TablaParametros
    from omnicad.ui.editor_boceto import Lienzo
    b = Boceto()
    l1 = b.agregar_linea((0, 0), (10, 0))
    l2 = b.agregar_linea((0, 5), (10, 5))
    lz = Lienzo(b, TablaParametros().evaluar, plano=Plano("XY"))
    lz.resize(800, 600)
    lz.ajustar_grilla = False
    lz.escala, lz.centro = 10.0, [5.0, 2.5]
    lz.set_herramienta("seleccionar")
    lz.seleccion = [l1, l2]
    return lz


def _arrastrar(lz, manija, destino_mm, shift=False):
    q = lz._manijas_marco(lz._caja_marco())[manija]
    assert lz._presionar_marco(q)
    lz._marco.update(actual=destino_mm, px_actual=lz.a_px(*destino_mm), shift=shift)
    lz.grab()                                                         # dibuja la vista previa sin romperse
    lz._soltar_marco()


def _caja_boceto(b):
    xs = [p.x for p in b.puntos.values()]
    ys = [p.y for p in b.puntos.values()]
    return min(xs), min(ys), max(xs), max(ys)


def test_marco_de_control_escala_gira_mueve_y_espeja(app_qt):
    lz = _lienzo_con_dos_lineas(app_qt)
    assert lz._caja_marco() == pytest.approx((0, 0, 10, 5))
    lz.grab()
    _arrastrar(lz, "escala2", (20, 10))                               # esquina sup. der. desde la inf. izq.: ×2
    assert _caja_boceto(lz.b) == pytest.approx((0, 0, 20, 10))
    _arrastrar(lz, "mover", (15, 10))                                 # del centro (10, 5) a (15, 10)
    assert _caja_boceto(lz.b) == pytest.approx((5, 5, 25, 15))
    _arrastrar(lz, "rotar", (5, 10.2), shift=True)                    # hacia la izquierda del centro: 90° exactos
    assert _caja_boceto(lz.b) == pytest.approx((10, 0, 20, 20))
    antes = {k: (p.x, p.y) for k, p in lz.b.puntos.items()}
    _arrastrar(lz, "espejo_h", lz.a_mm(lz._manijas_marco(lz._caja_marco())["espejo_h"]))       # clic: espeja
    despues = {k: (p.x, p.y) for k, p in lz.b.puntos.items()}
    assert _caja_boceto(lz.b) == pytest.approx((10, 0, 20, 20)) and despues != antes
    assert all(despues[k] == pytest.approx((30 - x, y)) for k, (x, y) in antes.items())
    # un clic sin mover en una esquina no cambia nada; con una sola línea elegida no hay marco
    _arrastrar(lz, "escala0", lz.a_mm(lz._manijas_marco(lz._caja_marco())["escala0"]))
    assert {k: (p.x, p.y) for k, p in lz.b.puntos.items()} == pytest.approx(despues)
    lz.seleccion = lz.seleccion[:1]
    assert lz._caja_marco() is None


# ---------------------------------------------------------------- limpiar y editar nodos
def test_clean_sketch_duplicados_huecos_y_colineales(s):
    from omnicad.restricciones import Boceto
    b = Boceto()
    # cuadrado de 4 lados, uno partido en 3 tramos alineados, con un hueco de 0,005 mm y una línea repetida
    b.agregar_linea((0, 0), (4, 0))
    b.agregar_linea((4, 0), (7, 0))
    b.agregar_linea((7, 0), (10, 0))
    b.agregar_linea((10, 0), (10, 10))
    b.agregar_linea((10, 10), (0, 10))
    b.agregar_linea((0, 10), (0, 0.005))
    b.agregar_linea((10, 0), (10, 10))
    hecho = b.limpiar(0.01)
    assert hecho == {"duplicadas": 1, "huecos": 6, "colineales": 2}   # 5 extremos que coincidían sin estar unidos + el hueco
    assert len(b.curvas) == 4
    from omnicad.nucleo.geometria import Plano
    from omnicad.nucleo.perfiles import detectar
    assert [round(p.area, 1) for p in detectar(b.geometria(), Plano("XY"))] == [100.0]
    # por la API, con lo que viene de un DXF partido
    for (x1, y1, x2, y2) in ((0, 0, 5, 0), (5, 0, 10, 0), (10, 0, 10, 10), (10, 10, 0, 10), (0, 10, 0, 0)):
        ok(api.llamar(s, "draw_line", {"start_x": x1, "start_y": y1, "end_x": x2, "end_y": y2}))
    r = ok(api.llamar(s, "clean_sketch", {"tolerance": 0.01}))
    assert r["lines_merged"] == 1 and r["gaps_closed"] >= 0
    falla(api.llamar(s, "clean_sketch", {"tolerance": 0}), "INVALID_ARGUMENTS")


def test_move_sketch_point_y_delete_sketch_entities(s):
    lid = ok(api.llamar(s, "draw_line", {"start_x": 0, "start_y": 0, "end_x": 10, "end_y": 0}))["entities"][0]["id"]
    linea = next(e for e in ok(api.llamar(s, "get_sketch", {}))["entities"] if e["id"] == lid)
    ok(api.llamar(s, "move_sketch_point", {"point": linea["points"][1], "x": 10, "y": 5}))
    linea = next(e for e in ok(api.llamar(s, "get_sketch", {}))["entities"] if e["id"] == lid)
    assert linea["end"] == [10.0, 5.0]
    falla(api.llamar(s, "move_sketch_point", {"point": 999, "x": 0, "y": 0}), "ENTITY_NOT_FOUND")
    r = ok(api.llamar(s, "delete_sketch_entities", {"entities": [lid]}))
    assert r["deleted"] == [lid] and not ok(api.llamar(s, "get_sketch", {}))["entities"]
    falla(api.llamar(s, "delete_sketch_entities", {"entities": [lid]}), "ENTITY_NOT_FOUND")


def test_dibujar_muchas_curvas_usa_cache(app_qt):
    import time

    from omnicad.nucleo.geometria import Plano
    from omnicad.restricciones import Boceto
    from omnicad.timeline.parametros import TablaParametros
    from omnicad.ui.editor_boceto import Lienzo
    b = Boceto()
    for k in range(1500):
        b.agregar_spline([(k, 0), (k + 0.3, 1), (k + 0.6, -1), (k + 1, 0)], modo="control")
    lz = Lienzo(b, TablaParametros().evaluar, plano=Plano("XY"))
    lz.resize(900, 600)
    lz.grab()
    t = time.time()
    lz.grab()
    assert time.time() - t < 1.0                                      # sin caché tardaba ~0,3 s cada 1000 splines


# ---------------------------------------------------------------- interletraje, kerning de pares e interlineado
@hay_arial
def test_kerning_a_mano_entre_dos_letras_y_por_api(s):
    base = caja(fuentes.contornos_texto("HHH", "Arial", 10))
    uno = caja(fuentes.contornos_texto("HHH", "Arial", 10, ajustes_kerning=[(1, 2.0)]))   # entre la 1.ª y la 2.ª
    assert uno[2] - uno[0] == pytest.approx(base[2] - base[0] + 2.0, abs=0.01)
    assert caja(fuentes.contornos_texto("HHH", "Arial", 10, ajustes_kerning=[(2, -1.0)]))[2] == \
        pytest.approx(base[2] - 1.0, abs=0.01)
    m0, m1 = fuentes.mapa_texto("HHH", "Arial", 10), fuentes.mapa_texto("HHH", "Arial", 10, ajustes_kerning=[(1, 2.0)])
    assert m1["paradas"][0] == m0["paradas"][0]
    assert m1["paradas"][1][0] == pytest.approx(m0["paradas"][1][0] + 2.0)       # lo anterior no se mueve
    with pytest.raises(fuentes.ErrorFuente):
        fuentes.contornos_texto("HHH", "Arial", 10, ajustes_kerning=[(-1, 1.0)])
    r = ok(api.llamar(s, "add_text", {"text": "HHH", "height": 10, "kerning_pairs": [[1, 2.0]]}))
    tid = r["entities"][0]["id"]
    t = next(c for c in ok(api.llamar(s, "get_sketch", {}))["entities"] if c["id"] == tid)
    assert t["kerning_pairs"] == [[1, 2.0]]
    ok(api.llamar(s, "edit_text", {"entity": tid, "kerning_pairs": []}))
    t = next(c for c in ok(api.llamar(s, "get_sketch", {}))["entities"] if c["id"] == tid)
    assert t["kerning_pairs"] == []
    r = api.llamar(s, "add_text", {"text": "A", "kerning_pairs": [[-3, 1]]})
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS"


@hay_arial
def test_panel_y_barra_comparten_tamano_interletraje_interlineado_y_kerning_del_cursor(app_qt):
    from PySide6.QtCore import Qt
    from omnicad.ui.modo_boceto import PanelCaracter
    b, lz = _lienzo_con_cuadro("HHH")
    panel = PanelCaracter()
    lz.texto_valores.connect(panel.mostrar_valores)
    lz.refrescar_previa_texto()
    assert panel.interletraje.value() == 0.0 and panel.interlineado.value() == 1.0 and panel.par.isEnabled()
    # panel → barra del texto
    lz.aplicar_opcion_texto("espaciado", 1.5)
    lz.aplicar_opcion_texto("interlineado", 2.0)
    assert lz.entrada.campos[3].text() == "1.5" and lz.entrada.campos[4].text() == "2"
    assert panel.interletraje.value() == pytest.approx(1.5) and panel.interlineado.value() == pytest.approx(2.0)
    # barra → panel
    lz.entrada.campos[1].setText("12")
    assert panel.altura.value() == pytest.approx(12.0) and lz.opciones["altura_texto"] == 5.0   # cuadro dibujado: no pisa el tamaño base
    # kerning de un par: entre las letras que rodean al cursor (posición 2)
    _tecla(lz, Qt.Key_Left)                                        # cursor en 2
    lz.ajustar_kerning_par(0.8)
    assert lz.opciones["ajustes_kerning"] == [[2, 0.8]] and panel.par.value() == pytest.approx(0.8)
    _tecla(lz, Qt.Key_Right, mod=Qt.AltModifier)                   # Alt+→ suma un paso
    assert lz.opciones["ajustes_kerning"][0][1] > 0.8
    _tecla(lz, Qt.Key_Home)
    assert panel.par.value() == 0.0                                # en otro lugar, sin ajuste
    # escribir antes de la letra ajustada la corre junto con ella
    _tecla(lz, ord("X"), "X")
    assert lz.opciones["ajustes_kerning"][0][0] == 3
    lz.entrada.aceptado.emit(["XHHH", "12", "0", "1.5", "2"])
    t = next(c for c in b.curvas.values() if c.tipo == "texto")
    assert t.espaciado == 1.5 and t.interlineado == 2.0 and t.altura == 12.0 and t.ajustes_kerning[0][0] == 3
    assert lz.opciones["ajustes_kerning"] == []                    # el kerning a mano es de ese texto


def test_panel_caracter_se_agranda_arrastrando_la_esquina_y_los_controles_lo_siguen(app_qt):
    from omnicad.ui.modo_boceto import PanelCaracter
    panel = PanelCaracter()
    panel.show()
    ancho0, alto0 = panel.width(), panel.height()
    panel.set_tamano_usuario(ancho0 + 150, alto0 + 80)
    assert panel.width() == ancho0 + 150 and panel.height() == alto0 + 80
    assert panel.fuente.width() > 150 and panel.interletraje.width() > 150     # los campos se estiran con el panel
    panel.set_tamano_usuario(50, 0)                                            # no baja de lo que hace falta
    assert panel.width() >= panel.cuerpo.minimumWidth() and panel.height() < alto0 + 80
    panel.close()                      # una ventana suelta se queda con el ratón de los tests siguientes
    panel.deleteLater()


@hay_arial
def test_repujar_texto_en_dos_caras_a_la_vez_trae_todas_las_letras_y_no_lo_copia(s):
    """Las piezas del texto se tocan entre sí (letra y contraforma): no se pueden pasar como un compuesto a la
    booleana (salían la mitad). El texto se proyecta en su lugar: cae entero sobre la primera cara y la otra no
    recibe una copia."""
    ok(api.llamar(s, "create_box", {"length": 60, "width": 10, "height": 90}))
    ok(api.llamar(s, "create_box", {"length": 60, "width": 10, "height": 90, "x": 100}))
    ok(api.llamar(s, "create_sketch", {"plane": "XZ", "name": "T"}))
    # las cajas van de x -30 a 30 y de 70 a 130 (z de 0 a 90): el texto (40 x 65 mm) cae entero sobre la primera
    ok(api.llamar(s, "add_text", {"text": "Hola\nsoy\nvale", "height": 20, "font": "Arial", "x": -25, "y": 70,
                                  "sketch": "T"}))
    sk = ok(api.llamar(s, "get_sketch", {"sketch": "T"}))
    texto = sum(p["area"] for p in sk["profiles"])
    v0 = sum(b["volume"] for b in ok(api.llamar(s, "get_scene_info", {}))["bodies"])
    ok(api.llamar(s, "run_operation", {"type": "repujado", "params": {
        "perfiles": [{"sketch": "T", "profile": "all"}], "profundidad": "1 mm",
        "caras": [{"body": "Cuerpo1", "faces": ">Y"}, {"body": "Cuerpo2", "faces": ">Y"}]}}))
    cuerpos = {b["name"]: b["volume"] for b in ok(api.llamar(s, "get_scene_info", {}))["bodies"]}
    assert sum(cuerpos.values()) - v0 == pytest.approx(texto, rel=0.01)    # todas las letras (1 mm), una sola vez
    assert cuerpos["Cuerpo2"] == pytest.approx(60 * 10 * 90)              # el otro cuerpo no recibe copia


# ---------------------------------------------------------------- elegir el texto entero (letras sin sus huecos)
def _boceto_hola(s):
    """Boceto «Boceto1» (el de la fixture) con el texto «Hola»: 6 perfiles, 4 letras y los huecos de la o y la a."""
    ok(api.llamar(s, "add_text", {"text": "Hola", "height": 20, "font": "Arial"}))
    sk = ok(api.llamar(s, "get_sketch", {"sketch": "Boceto1"}))
    texto = next(e["id"] for e in sk["entities"] if e["type"] == "text")
    return sk, texto


@hay_arial
def test_letras_de_texto_deja_afuera_los_huecos(s):
    from omnicad.nucleo.perfiles import letras_de_texto
    sk, texto = _boceto_hola(s)
    br = s.doc.estado_final.bocetos[s.paso("Boceto1").id]
    assert len(br.perfiles) == 6
    letras = letras_de_texto(br.perfiles, [texto])
    assert len(letras) == 4                                          # H, o, l, a (sin los dos huecos)
    huecos = [p for p in br.perfiles if p not in letras]
    assert all(h.area < min(p.area for p in letras if p.area > 30) for h in huecos)


@hay_arial
def test_extrude_profile_text_elige_las_letras_sin_rellenar_los_huecos(s):
    _sk, texto = _boceto_hola(s)
    br = s.doc.estado_final.bocetos[s.paso("Boceto1").id]
    from omnicad.nucleo.perfiles import letras_de_texto
    area = sum(p.area for p in letras_de_texto(br.perfiles, [texto]))
    r = ok(api.llamar(s, "extrude", {"sketch": "Boceto1", "profile": "text", "distance": 2}))
    vol = sum(b["volume"] for b in ok(api.llamar(s, "get_scene_info", {}))["bodies"])
    assert vol == pytest.approx(2 * area, rel=1e-3) and r
    assert vol < 2 * sum(p.area for p in br.perfiles) - 1          # con «all» se rellenaban la o y la a
    ok(api.llamar(s, "undo"))
    ok(api.llamar(s, "extrude", {"sketch": "Boceto1", "profile": f"text:{texto}", "distance": 2}))
    r = api.llamar(s, "extrude", {"sketch": "Boceto1", "profile": "text:999", "distance": 2})
    assert not r["ok"] and r["error_kind"] == "PROFILE_NOT_FOUND"


@hay_arial
def test_clic_en_una_letra_elige_y_quita_el_texto_entero(app_qt, s):
    from omnicad.timeline.operaciones import OpExtrusion
    from omnicad.ui.comando import ContextoComando, PanelComando, hit_desde_ref
    from omnicad.ui.comandos import CATALOGO
    from omnicad.ui.visor3d import Visor3D
    _sk, _texto = _boceto_hola(s)
    # un cuerpo DEBAJO del texto (el abanico): el clic en el hueco de la «o» no tiene que elegir su cara
    caja = ok(api.llamar(s, "create_box", {"length": 200, "width": 200, "height": 3}))
    ok(api.llamar(s, "move_body", {"body": caja["bodies_created"][0]["id"], "translate": [0, 0, -20]}))
    estado = s.doc.estado_final
    bid = s.paso("Boceto1").id
    visor = Visor3D()
    visor.resize(800, 600)
    visor.set_modelo(estado)
    panel = PanelComando(CATALOGO["extruir"](), ContextoComando(s.doc, None), visor, {})
    campo = next(c for c in panel.campos if c.clave == "perfiles")
    panel.show()
    panel._activar(campo)
    assert visor.texto_entero
    perfiles = estado.bocetos[bid].perfiles
    letra = max(perfiles, key=lambda p: p.area)                       # la H
    hit = hit_desde_ref({"tipo": "perfil", "boceto": bid, **OpExtrusion.referencia_perfil(letra)}, estado)
    panel._elegida(hit)
    assert len(panel.valores["perfiles"]) == 4                        # las 4 letras, sin los huecos
    panel._elegida(hit)                                               # otro clic en una letra: sale el texto
    assert panel.valores["perfiles"] == []
    hueco = min(perfiles, key=lambda p: p.area)                       # el hueco de una letra no se elige nunca
    hit_hueco = hit_desde_ref({"tipo": "perfil", "boceto": bid, **OpExtrusion.referencia_perfil(hueco)}, estado)
    assert visor.es_hueco_texto(hit_hueco) and not visor.es_hueco_texto(hit)
    panel._elegida(hit_hueco)
    assert panel.valores["perfiles"] == []
    # y el visor no lo da al hacer clic: en su lugar sale lo de atrás (acá nada)
    import numpy as np
    from PySide6.QtCore import QPointF

    from omnicad.nucleo import geometria as geo
    visor.vista("arriba")
    visor.encuadrar()
    px = visor.puntos_pantalla(np.array([geo.centro_masa(hueco.cara, superficie=True)], float))[0][0]
    # ni el hueco ni la cara de atrás (Extruir y Repujado aceptan caras planas como perfil)
    assert visor.elegir_entidad(QPointF(float(px[0]), float(px[1])), {"perfil", "cara_plana"}) is None
    assert visor.elegir_entidad(QPointF(float(px[0]), float(px[1])), {"cara"}) is not None    # sin perfiles, sí
    letra_px = visor.puntos_pantalla(np.array([geo.centro_masa(letra.cara, superficie=True)], float))[0][0]
    assert visor.elegir_entidad(QPointF(float(letra_px[0]), float(letra_px[1])), {"perfil"}) is not None
    panel.cancelar()
    # también en el Repujado
    panel = PanelComando(CATALOGO["repujado"](), ContextoComando(s.doc, None), visor, {})
    panel.show()
    panel._activar(next(c for c in panel.campos if c.clave == "perfiles"))
    panel._elegida(hit)
    assert len(panel.valores["perfiles"]) == 4
    panel.cancelar()
    visor.deleteLater()


@hay_arial
def test_al_editar_un_repujado_se_sacan_los_huecos_que_tenia_elegidos(app_qt, s):
    """Un repujado guardado con el hueco de la «o» elegido (antes se podía): al editarlo, el hueco sale solo."""
    from omnicad.timeline.operaciones import OpExtrusion
    from omnicad.ui.comando import ContextoComando, PanelComando, hit_desde_ref
    from omnicad.ui.comandos import CATALOGO
    from omnicad.ui.visor3d import Visor3D
    _boceto_hola(s)
    estado = s.doc.estado_final
    bid = s.paso("Boceto1").id
    todos = [hit_desde_ref({"tipo": "perfil", "boceto": bid, **OpExtrusion.referencia_perfil(p)}, estado)
             for p in estado.bocetos[bid].perfiles]
    visor = Visor3D()
    visor.resize(400, 300)
    visor.set_modelo(estado)
    panel = PanelComando(CATALOGO["extruir"](), ContextoComando(s.doc, None), visor, {"perfiles": todos})
    assert len(panel.valores["perfiles"]) == 4                        # de 6: quedan las letras
    panel.cancelar()
    visor.deleteLater()


@hay_arial
def test_huecos_de_un_texto_en_un_plano_lejos_del_origen():
    """Bug: en un plano de construcción a z = 177,77 todos los perfiles salían «letra» (la malla en float32 corría el
    punto de prueba fuera de la caja del anillo) y el hueco de la «o» entraba al repujado."""
    from omnicad.nucleo.perfiles import letras_de_texto
    s = api.Sesion()
    ok(api.llamar(s, "create_construction_plane", {"plane": "XY", "offset": 177.77, "name": "Alto"}))
    ok(api.llamar(s, "create_sketch", {"plane": "Alto", "name": "T"}))
    ok(api.llamar(s, "add_text", {"text": "hola\nhola", "height": 30, "font": "Arial", "sketch": "T"}))
    br = s.doc.estado_final.bocetos[s.paso("T").id]
    textos = [c.id for c in br.boceto.curvas.values() if c.tipo == "texto"]
    assert len(br.perfiles) == 12
    assert len(letras_de_texto(br.perfiles, textos)) == 8                # h, o, l, a dos veces; sin los 4 huecos
