"""Fase 9 del boceto, grupo «Fuentes y perfiles»: BOC-21 (fuentes de una línea: minúsculas propias, más familias y
lectura de archivos .shx) y BOC-28 (texto largo)."""
import math
import struct
from pathlib import Path

import pytest

from omnicad import api
from omnicad.nucleo import fuentes, shx

TRAZO = "OmniCAD Trazo SHX"


def _pts(prims):
    return [q for p in prims for q in ((p[2], p[3]) if p[0] == "linea" else p[2])]


def _caja(texto, fuente=TRAZO, altura=10.0):
    pts = _pts(fuentes.contornos_texto(texto, fuente, altura))
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    return min(xs), min(ys), max(xs), max(ys)


# ---------------------------------------------------------------- BOC-21: minúsculas y familias propias
def test_boc21_minusculas_son_glifos_propios():
    a, mayus = fuentes.contornos_texto("a", TRAZO, 10), fuentes.contornos_texto("A", TRAZO, 10)
    assert a and a != mayus
    assert _caja("a")[3] == pytest.approx(10 * 0.45, rel=0.02)        # altura de x: 4,5 de 7 de la mayúscula
    assert _caja("A")[3] == pytest.approx(10 * 0.70, rel=0.02)
    assert _caja("b")[3] == pytest.approx(10 * 0.70, rel=0.02)        # asta ascendente
    assert _caja("g")[1] == pytest.approx(-10 * 0.20, rel=0.05)       # asta descendente
    assert _caja("x")[3] == pytest.approx(10 * 0.45, rel=0.02)


def test_boc21_todas_las_minusculas_y_acentos_tienen_glifo():
    alfabeto = "abcdefghijklmnopqrstuvwxyzáéíóúüñ"
    assert fuentes.glifos_faltantes(alfabeto, TRAZO) == []
    for ch in alfabeto:
        assert fuentes.contornos_texto(ch, TRAZO, 10), ch
    assert _caja("á")[3] > _caja("a")[3] + 10 * 0.1                   # la tilde sube sobre la letra


def test_boc21_hay_tres_familias_de_una_linea_con_distinto_aspecto():
    r = api.llamar(api.Sesion(), "list_fonts", {"query": "SHX"})["result"]
    nombres = [f["name"] for f in r["families"] if f["single_line"] and f["name"].startswith("OmniCAD")]
    assert len(nombres) >= 3
    anchos = {n: _caja("HOLA", n)[2] for n in nombres}
    assert len({round(v, 1) for v in anchos.values()}) == len(nombres)            # tres anchos distintos
    cursiva = next(n for n in nombres if "Cursiva" in n)
    x0, _, x1, _ = _caja("I", cursiva)
    pts = _pts(fuentes.contornos_texto("I", cursiva, 10))
    arriba = max(q[0] for q in pts if q[1] > 6.9)
    abajo = max(q[0] for q in pts if q[1] < 0.1)
    assert arriba > abajo + 1.0                                                   # inclinada a la derecha
    assert x1 > x0


# ---------------------------------------------------------------- BOC-21: lector de .shx
def _unifont(glifos, above=21, below=7):
    """Archivo SHX «unifont 1.0» mínimo: `glifos` = {código: bytes de comandos}."""
    cuerpo0 = b"MIFUENTE\0" + bytes([above, below, 2, 0, 0, 0])
    datos = b"AutoCAD-86 unifont 1.0\r\n\x1a" + struct.pack("<I", len(glifos) + 1) + struct.pack("<H", len(cuerpo0))
    datos += cuerpo0
    for cod, cmds in glifos.items():
        cuerpo = b"\0" + cmds + b"\0"
        datos += struct.pack("<HH", cod, len(cuerpo)) + cuerpo
    return datos


def _shapes(glifos, above=21, below=7, version=b"1.1"):
    """Archivo SHX «shapes 1.x» mínimo (subformas de 1 byte)."""
    cuerpos = {0: b"MIFUENTE\0" + bytes([above, below, 0, 0])}
    cuerpos |= {c: b"\0" + cm + b"\0" for c, cm in glifos.items()}
    claves = sorted(cuerpos)
    datos = b"AutoCAD-86 shapes " + version + b"\r\n\x1a" + struct.pack("<HHH", claves[0], claves[-1], len(claves))
    datos += b"".join(struct.pack("<HH", c, len(cuerpos[c])) for c in claves)
    return datos + b"".join(cuerpos[c] for c in claves)


def _s8(v):
    return v & 0xFF


# A: sube en diagonal a (5, 21), baja a (10, 0) y salta 14 hacia la derecha (el avance de la letra queda en 24).
_A = bytes([2, 8, 0, 0, 1, 8, _s8(5), 21, 8, _s8(5), _s8(-21), 2, 8, 0, 0, 8, 14, 0])


def test_boc21_shx_lee_trazos_y_avance(tmp_path):
    f = shx.leer_bytes(_unifont({65: _A}))
    assert (f.above, f.below) == (21, 7)
    trazos, avance = f.glifo(65)
    assert trazos == [[(0.0, 0.0), (5.0, 21.0), (10.0, 0.0)]]
    assert avance == pytest.approx(24.0)                              # 10 del trazo + 14 del salto final
    assert f.glifo(66) is None


def test_boc21_shx_formato_shapes_1_0_y_1_1():
    for version in (b"1.0", b"1.1"):
        f = shx.leer_bytes(_shapes({65: _A}, version=version))
        assert f.glifo(65)[0] == [[(0.0, 0.0), (5.0, 21.0), (10.0, 0.0)]]


def test_boc21_shx_vectores_escala_arcos_y_pila():
    d = shx.leer_bytes(_unifont({
        65: bytes([1, 0x20 | 0, 0x20 | 4]),                                 # vectores: 2 al este y 2 al norte
        66: bytes([4, 2, 1, 0x10 | 0, 3, 4, 0x10 | 4]),                    # ×2, 1 al este; ÷4 sobre el ×2 → ×0,5, 1 al norte
        67: bytes([2, 8, 10, 0, 1, 0x0A, 10, 0x04, 2]),                    # media luna de radio 10 desde el este (0°→180°)
        68: bytes([2, 8, 5, 5, 5, 1, 8, 4, 0, 6, 8, 0, 3]),                    # push, trazo, pop, trazo desde el punto guardado
        69: bytes([1, 0x0C, 10, 0, 127]),                                  # semicírculo por bulge (+127 = 1)
        71: bytes([2, 8, 0, 10, 1, 0x0A, 10, 0x80 | 0x24]),               # semicírculo horario desde el norte (bit 7 = horario)
        72: bytes([2, 8, 10, 0, 1, 0x0B, 0, 0, 0, 10, 0x08]),              # arco fraccionario: círculo entero de radio 10
        70: bytes([2, 7, 0, 65, 1, 7, 0, 65]),                             # subforma 65 dos veces (unifont: 2 bytes, el alto primero)
    })).glifo
    assert d(65)[0] == [[(0, 0), (2, 0), (2, 2)]]
    assert d(66)[0] == [[(0, 0), (2, 0), (2, 0.5)]]
    arco = d(67)[0][0]
    assert arco[0] == pytest.approx((10, 0)) and arco[-1] == pytest.approx((-10, 0), abs=1e-6)
    assert all(math.dist(p, (0, 0)) == pytest.approx(10, abs=1e-6) for p in arco) and len(arco) > 6
    assert max(p[1] for p in arco) == pytest.approx(10, abs=0.05)             # pasa por el norte
    assert d(68)[0] == [[(5, 5), (9, 5)], [(5, 5), (5, 8)]]
    bulge = d(69)[0][0]
    assert bulge[0] == pytest.approx((0, 0)) and bulge[-1] == pytest.approx((10, 0), abs=1e-6)
    assert all(math.dist(p, (5, 0)) == pytest.approx(5, abs=1e-6) for p in bulge)
    horario = d(71)[0][0]
    assert horario[0] == pytest.approx((0, 10)) and horario[-1] == pytest.approx((0, -10), abs=1e-6)
    assert max(p[0] for p in horario) == pytest.approx(10, abs=0.05) and min(p[0] for p in horario) >= -1e-9
    circulo = d(72)[0][0]
    assert circulo[0] == pytest.approx((10, 0)) and circulo[-1] == pytest.approx((10, 0), abs=1e-6)
    assert all(math.dist(p, (0, 0)) == pytest.approx(10, abs=1e-6) for p in circulo)
    assert d(70)[0] == [[(0, 0), (2, 0), (2, 2)], [(2, 2), (4, 2), (4, 4)]]


def test_boc21_shx_malos_archivos_no_cuelgan():
    for datos in (b"", b"no soy un shx", b"AutoCAD-86 bigfont 1.0\r\n\x1a" + b"\0" * 50, _unifont({65: _A})[:40]):
        with pytest.raises(shx.ErrorSHX):
            shx.leer_bytes(datos)
    ciclo = shx.leer_bytes(_unifont({65: bytes([7, 0, 65])}))                      # una subforma que se llama a sí misma
    assert ciclo.glifo(65) == ([], 0.0)
    truncado = shx.leer_bytes(_unifont({65: bytes([2, 8, 5])}))                    # operando que falta: se corta sin romper
    assert truncado.glifo(65)[0] == []


def test_boc21_shx_de_usuario_aparece_en_list_fonts_y_dibuja(tmp_path):
    (tmp_path / "miletra.shx").write_bytes(_unifont({65: _A, 32: bytes([2, 8, 20, 0])}))
    (tmp_path / "roto.shx").write_bytes(b"basura")
    s = api.Sesion()
    api.llamar(s, "create_sketch", {"plane": "XY", "name": "B"})
    r = api.llamar(s, "add_font_folder", {"path": str(tmp_path)})["result"]
    assert r["added_fonts"] == 1                                                   # el roto no cuenta ni rompe
    lista = api.llamar(s, "list_fonts", {"query": "miletra"})["result"]["families"]
    assert [(f["name"], f["single_line"]) for f in lista] == [("miletra SHX", True)]
    pts = _pts(fuentes.contornos_texto("A A", "miletra SHX", 10))
    assert all(p[0] == "linea" for p in fuentes.contornos_texto("A A", "miletra SHX", 10))
    # 21 unidades SHX de alto = 7 mm (0,7 de la altura 10); el avance de «A» son 24 unidades = 8 mm
    assert max(q[1] for q in pts) == pytest.approx(7.0, rel=1e-6)
    assert max(q[0] for q in pts) == pytest.approx(8 + 20 / 3 + 10 / 3, rel=1e-6)
    assert min(q[0] for q in pts) == pytest.approx(0.0)
    tid = api.llamar(s, "add_text", {"text": "A", "font": str(tmp_path / "miletra.shx"), "height": 10})
    assert tid["ok"], tid


_REALES = Path(r"D:\Autodesk\webdeploy\production\9c5312dfff2e4569cd1d269973ddf11cb999f782\FusionDocStream"
               r"\Autodesk\FusionDocAcad\Fonts")


@pytest.mark.skipif(not (_REALES / "romans.shx").is_file(), reason="sin las SHX reales de la instalación de Fusion")
def test_boc21_shx_real_de_autocad_romans():
    f = shx.leer(_REALES / "romans.shx")
    assert (f.above, f.below) == (21, 7)
    a, avance = f.glifo(ord("A"))
    ys = [p[1] for t in a for p in t]
    assert max(ys) == pytest.approx(21) and min(ys) == pytest.approx(0)
    assert 10 < avance < 30
    o, _ = f.glifo(ord("O"))
    assert len(o) == 1 and o[0][0] == pytest.approx(o[0][-1], abs=1e-6)            # la «O» es una curva cerrada
    for cp in range(32, 127):
        assert f.glifo(cp) is not None, cp


# ---------------------------------------------------------------- BOC-28: corte en perfiles de un texto largo
def _sesion_con_boceto():
    s = api.Sesion()
    api.llamar(s, "create_sketch", {"plane": "XY", "name": "B"})
    return s


def test_boc28_perfiles_de_curvas_que_se_cruzan_dan_areas_exactas():
    """Un círculo de radio 10 cortado por una recta: dos segmentos circulares cuyas áreas suman π·100."""
    s = _sesion_con_boceto()
    api.llamar(s, "draw_circle", {"radius": 10})
    api.llamar(s, "draw_line", {"start_x": -20, "start_y": 4, "end_x": 20, "end_y": 4})
    perfiles = api.llamar(s, "get_sketch", {})["result"]["profiles"]
    areas = sorted(p["area"] for p in perfiles)
    d = 4.0
    menor = 100 * math.acos(d / 10) - d * math.sqrt(100 - d * d)
    assert areas == pytest.approx(sorted([menor, math.pi * 100 - menor]), rel=1e-6)


def test_boc28_texto_largo_sobre_un_circulo_cuenta_y_tiempo():
    """200 «W» sobre un círculo de radio 20: ~14,8 mil perfiles. Medido: 4,7 s antes de BOC-28 (Python alrededor del
    Splitter) y 3,9 s después, en la misma PC y con la misma carga; el resto es OpenCascade. Tope holgado."""
    import time
    s = _sesion_con_boceto()
    c = api.llamar(s, "draw_circle", {"radius": 20})["result"]["entities"][0]["id"]
    t = time.perf_counter()
    r = api.llamar(s, "add_text", {"text": "W" * 200, "height": 5, "path_entity": c, "fit_path": True})["result"]
    assert 14000 < r["profiles"] < 15500
    assert time.perf_counter() - t < 25.0
