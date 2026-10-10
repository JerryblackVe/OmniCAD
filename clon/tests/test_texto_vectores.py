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
    assert all(p[0] == "curva" for p in curvas)
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
    # splines: una entidad por contorno
    ok(api.llamar(s, "create_sketch", {"plane": "XY"}))
    c = ok(api.llamar(s, "trace_image", {"path": str(anillo), "sketch": "Boceto2", "width": 90, "curves": True,
                                         "name": "x"}))
    assert c["entities_added"] == 3 and c["profiles"] == 3
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
    ok(api.llamar(s, "draw_rectangle", {"x1": 0, "y1": 0, "x2": 10, "y2": 4}))
    arco = ok(api.llamar(s, "draw_arc", {"center_x": 20, "center_y": 0, "start_x": 25, "start_y": 0,
                                         "sweep_angle": 90}))["entities"][0]["id"]

    def caja_lineas():
        sk = ok(api.llamar(s, "get_sketch", {}))
        pts = [v for c in sk["entities"] if c["type"] == "line" for v in (c["start"], c["end"])]
        return min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)
    lineas = [c["id"] for c in ok(api.llamar(s, "get_sketch", {}))["entities"] if c["type"] == "line"]
    ok(api.llamar(s, "transform_sketch", {"entities": lineas, "scale": 2}))          # alrededor de su centro (5, 2)
    assert caja_lineas() == pytest.approx((-5, -2, 15, 6))
    ok(api.llamar(s, "transform_sketch", {"entities": lineas, "dx": 5, "dy": 2}))
    assert caja_lineas() == pytest.approx((0, 0, 20, 8))
    ok(api.llamar(s, "transform_sketch", {"entities": lineas, "angle": 90}))         # gira alrededor de (10, 4)
    assert caja_lineas() == pytest.approx((6, -6, 14, 14))
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
