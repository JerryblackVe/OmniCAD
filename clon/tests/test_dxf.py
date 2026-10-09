# -*- coding: utf-8 -*-
"""DXF: escritor R2000/R12 y lector básico (ida y vuelta, bulges, splines, bloques, unidades, OCS)."""
import math

import pytest

from omnicad.io_archivos import dxf

ENTIDADES = [
    ("VISIBLE", ("linea", (0.0, 0.0), (10.0, 5.0))),
    ("VISIBLE", ("circulo", (5.0, 5.0), 2.5)),
    ("OCULTA", ("arco", (1.0, -2.0), 4.0, math.radians(30), math.radians(120))),
    ("CENTRO", ("polilinea", [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)], False)),
    ("CENTRO", ("polilinea", [(0.0, 0.0), (4.0, 0.0), (4.0, 3.0), (0.0, 3.0)], True)),
    ("TEXTO", ("texto", (1.0, 2.0), 3.5, "⌀10 ñandú 45° ±0,1 %", 90.0, "centro")),
]
CAPAS = {"VISIBLE": {"color": 7, "tipo": "continua", "grosor": 0.5},
         "OCULTA": {"color": 8, "tipo": "trazos", "grosor": 0.25},
         "CENTRO": {"color": 1, "tipo": "trazo_punto", "grosor": 0.18}}


def _cerca(a, b):
    return all(x == pytest.approx(y, abs=1e-6) for x, y in zip(a, b, strict=True))


@pytest.mark.parametrize("version", ["2000", "R12"])
def test_ida_y_vuelta_conserva_cantidad_y_medidas(tmp_path, version):
    ruta = dxf.escribir_dxf(tmp_path / f"prueba_{version}.dxf", ENTIDADES, CAPAS, version)
    leido = dxf.leer_dxf(ruta, con_capas=True)
    assert len(leido) == len(ENTIDADES)
    for (capa, orig), (capa2, prim) in zip(ENTIDADES, leido, strict=True):
        assert capa == capa2 and orig[0] == prim[0]
    (_, linea), (_, circ), (_, arco), (_, abierta), (_, cerrada), (_, texto) = leido
    assert _cerca(linea[1], (0, 0)) and _cerca(linea[2], (10, 5))
    assert _cerca(circ[1], (5, 5)) and circ[2] == pytest.approx(2.5)
    assert _cerca(arco[1], (1, -2)) and arco[2] == pytest.approx(4)
    assert arco[3] == pytest.approx(math.radians(30)) and arco[4] == pytest.approx(math.radians(120))
    assert len(abierta[1]) == 3 and abierta[2] is False and _cerca(abierta[1][2], (10, 10))
    assert len(cerrada[1]) == 4 and cerrada[2] is True
    assert _cerca(texto[1], (1, 2)) and texto[2] == pytest.approx(3.5)
    assert texto[3] == "⌀10 ñandú 45° ±0,1 %"
    assert len(texto) == 4


def test_cabecera_capas_y_tipos_de_linea():
    t = dxf.a_texto_dxf(ENTIDADES, CAPAS, "2000")
    assert "AC1015" in t and "$INSUNITS\n 70\n4" in t
    assert "\n  2\nDASHED\n" in t and "\n  2\nCENTER\n" in t
    bloque_oculta = t.split("\n  2\nOCULTA\n", 1)[1].split("\n  0\n", 1)[0]
    assert "\n  6\nDASHED" in bloque_oculta and "370\n25" in bloque_oculta
    semilla = int(t.split("$HANDSEED\n  5\n", 1)[1].split("\n", 1)[0], 16)
    resto = t.split("CLASSES", 1)[1]                  # después de la cabecera (que tiene el propio $HANDSEED)
    handles = [int(x.split("\n", 1)[0], 16) for x in resto.split("\n  5\n")[1:]]
    assert semilla > max(handles)
    assert len(handles) == len(set(handles))          # cada objeto con su handle propio
    assert t.rstrip().endswith("EOF")


def test_elipse_spline_y_solido_se_leen_como_polilineas():
    ents = [("elipse", (20.0, 0.0), (5.0, 0.0), 0.5, 0.0, 2 * math.pi),
            ("spline", [(0.0, 0.0), (1.0, 1.0), (2.0, 0.0)]),
            ("solido", [(0.0, 0.0), (3.0, 0.5), (3.0, -0.5)])]
    for version in ("2000", "R12"):
        elipse, spline, solido = dxf.leer_dxf_texto(dxf.a_texto_dxf(ents, version=version))
        assert elipse[0] == "polilinea" and elipse[2] is True
        xs = [p[0] for p in elipse[1]]
        ys = [p[1] for p in elipse[1]]
        assert (min(xs), max(xs)) == pytest.approx((15, 25), abs=1e-6)
        assert (min(ys), max(ys)) == pytest.approx((-2.5, 2.5), abs=0.02)
        assert spline[1] == [(0.0, 0.0), (1.0, 1.0), (2.0, 0.0)]
        assert solido[2] is True and len(solido[1]) == 3


def _dxf(*entidades, cabecera=""):
    cuerpo = "".join(entidades)
    return f"0\nSECTION\n2\nHEADER\n{cabecera}0\nENDSEC\n0\nSECTION\n2\nENTITIES\n{cuerpo}0\nENDSEC\n0\nEOF\n"


def test_lwpolyline_con_bulge_es_un_semicirculo():
    # de (0,0) a (10,0) con bulge 1 = media vuelta antihoraria, centro (5,0), radio 5
    texto = _dxf("0\nLWPOLYLINE\n8\nA\n90\n2\n70\n0\n10\n0\n20\n0\n42\n1\n10\n10\n20\n0\n")
    (prim,) = dxf.leer_dxf_texto(texto)
    assert prim[0] == "polilinea" and len(prim[1]) > 10
    for x, y in prim[1]:
        assert math.hypot(x - 5, y) == pytest.approx(5)
        assert y <= 1e-9                     # antihoraria de (0,0) a (10,0): pasa por abajo
    assert _cerca(prim[1][-1], (10, 0))


def test_unidades_en_pulgadas_pasan_a_mm():
    texto = _dxf("0\nLINE\n8\n0\n10\n0\n20\n0\n11\n1\n21\n2\n", "0\nCIRCLE\n8\n0\n10\n1\n20\n1\n40\n0.5\n",
                 cabecera="9\n$INSUNITS\n70\n1\n")
    linea, circ = dxf.leer_dxf_texto(texto)
    assert _cerca(linea[2], (25.4, 50.8)) and circ[2] == pytest.approx(12.7)
    linea_cruda, _ = dxf.leer_dxf_texto(texto, a_mm=False)
    assert _cerca(linea_cruda[2], (1, 2))


def test_insert_expande_el_bloque_con_escala_y_rotacion():
    texto = ("0\nSECTION\n2\nBLOCKS\n0\nBLOCK\n2\nPIEZA\n10\n1\n20\n0\n"
             "0\nLINE\n8\n0\n10\n1\n20\n0\n11\n3\n21\n0\n"
             "0\nARC\n8\n0\n10\n1\n20\n0\n40\n1\n50\n0\n51\n90\n0\nENDBLK\n0\nENDSEC\n"
             "0\nSECTION\n2\nENTITIES\n0\nINSERT\n8\nX\n2\nPIEZA\n10\n10\n20\n10\n41\n2\n42\n2\n50\n90\n"
             "0\nENDSEC\n0\nEOF\n")
    linea, arco = dxf.leer_dxf_texto(texto)
    assert _cerca(linea[1], (10, 10)) and _cerca(linea[2], (10, 14))   # (2,0)·2 girado 90°
    assert _cerca(arco[1], (10, 10)) and arco[2] == pytest.approx(2)
    assert arco[3] == pytest.approx(math.pi / 2) and arco[4] == pytest.approx(math.pi)


def test_arco_con_extrusion_negativa_se_espeja():
    texto = _dxf("0\nARC\n8\n0\n10\n2\n20\n1\n40\n1\n50\n0\n51\n90\n210\n0\n220\n0\n230\n-1\n")
    (arco,) = dxf.leer_dxf_texto(texto)
    assert _cerca(arco[1], (-2, 1))
    assert arco[3] == pytest.approx(math.pi / 2) and arco[4] == pytest.approx(math.pi)


def test_spline_por_nudos_y_textos():
    # B-spline cuadrática fijada con 3 puntos de control: en u = 0,5 vale ¼P0 + ½P1 + ¼P2
    spline = ("0\nSPLINE\n8\n0\n70\n8\n71\n2\n72\n6\n73\n3\n40\n0\n40\n0\n40\n0\n40\n1\n40\n1\n40\n1\n"
              "10\n0\n20\n0\n10\n2\n20\n4\n10\n4\n20\n0\n")
    texto = "0\nTEXT\n8\n0\n10\n1\n20\n2\n40\n2.5\n1\n%%c20 %%p0.1\n"
    mtexto = "0\nMTEXT\n8\n0\n10\n0\n20\n0\n40\n3\n1\n{\\fArial|b1;Hola}\\PMundo\n"
    s, t, m = dxf.leer_dxf_texto(_dxf(spline, texto, mtexto))
    puntos = s[1]
    assert _cerca(puntos[0], (0, 0)) and _cerca(puntos[-1], (4, 0))
    medio = puntos[len(puntos) // 2]
    assert _cerca(medio, (2, 2))
    assert t[3] == "⌀20 ±0.1" and t[2] == pytest.approx(2.5)
    assert m[3] == "Hola\nMundo"


def test_errores_claros(tmp_path):
    malo = tmp_path / "malo.dxf"
    malo.write_text("hola\nmundo\n", encoding="ascii")
    with pytest.raises(dxf.ErrorDXF):
        dxf.leer_dxf(malo)
    binario = tmp_path / "bin.dxf"
    binario.write_bytes(b"AutoCAD Binary DXF\r\n\x1a\x00")
    with pytest.raises(dxf.ErrorDXF, match="binario"):
        dxf.leer_dxf(binario)
    with pytest.raises(dxf.ErrorDXF):
        dxf.leer_dxf_texto("0\nSECTION\n2\nENTITIES\nX\nLINE\n")
    with pytest.raises(dxf.ErrorDXF):
        dxf.a_texto_dxf([("raro", 1)])
