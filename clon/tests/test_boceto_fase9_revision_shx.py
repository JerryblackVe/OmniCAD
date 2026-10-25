# -*- coding: utf-8 -*-
"""Revisión de la Fase 9: archivos .shx hostiles no tiran la lista de fuentes ni cuelgan, y el contorno giratorio
sigue dando lo mismo con muchas aristas."""
import math
import struct
import time

from omnicad import api
from omnicad.nucleo import contorno_giro, shx

_A = bytes([2, 8, 0, 0, 1, 8, 5, 21, 8, 5, 256 - 21, 2, 8, 0, 0, 8, 14, 0])


def _unifont(glifos, above=21, below=7):
    cuerpo0 = b"MIFUENTE\0" + bytes([above, below, 2, 0, 0, 0])
    datos = b"AutoCAD-86 unifont 1.0\r\n\x1a" + struct.pack("<I", len(glifos) + 1) + struct.pack("<H", len(cuerpo0))
    datos += cuerpo0
    for cod, cmds in glifos.items():
        cuerpo = b"\0" + cmds + b"\0"
        datos += struct.pack("<HH", cod, len(cuerpo)) + cuerpo
    return datos


def _shapes(glifos, above=0, below=0):
    cuerpos = {0: b"MIFUENTE\0" + bytes([above, below, 0, 0])}
    cuerpos |= {c: b"\0" + cm + b"\0" for c, cm in glifos.items()}
    claves = sorted(cuerpos)
    datos = b"AutoCAD-86 shapes 1.1\r\n\x1a" + struct.pack("<HHH", claves[0], claves[-1], len(claves))
    datos += b"".join(struct.pack("<HH", c, len(cuerpos[c])) for c in claves)
    return datos + b"".join(cuerpos[c] for c in claves)


_BANDERAS = bytes([0x0E] * 3000) + bytes([2, 8, 5, 5, 1, 8, 4, 0])      # 3000 «0E» seguidos
_FRACCION_CORTA = bytes([1, 0x0B, 1, 2, 3])                              # 0B con 3 operandos de 5
_ESCALA = bytes([4, 255] * 3000) + bytes([1, 0x10])                      # la escala se va a infinito
# forma 1: círculo (61 puntos); formas 2..8: 20 llamadas a la anterior → explosión de puntos
_CIRCULO = bytes([1, 0x0A, 1, 0x08])


def _puntos_explosivos():
    glifos = {1: _CIRCULO}
    for k in range(2, 9):
        glifos[k] = bytes([7, 0, k - 1] * 20)
    return glifos


def _todos_finitos(trazos):
    return all(math.isfinite(c) for t in trazos for p in t for c in p)


def test_shx_hostil_flag_0e_no_recursa_y_0b_corto_no_lanza():
    f = shx.leer_bytes(_unifont({65: _BANDERAS, 66: _FRACCION_CORTA, 67: _A}))
    t0 = time.perf_counter()
    assert f.glifo(65) is not None                      # antes: RecursionError
    assert f.glifo(66)[0] == []                         # antes: ValueError al desempacar
    assert f.glifo(67)[0] == [[(0.0, 0.0), (5.0, 21.0), (10.0, 0.0)]]
    assert time.perf_counter() - t0 < 2


def test_shx_0e_sigue_silenciando_solo_el_comando_siguiente():
    f = shx.leer_bytes(_unifont({65: bytes([2, 8, 5, 0, 1, 0x0E, 0x20, 0x34])}))
    # «2 al este» se lee pero no se dibuja; el que sigue va 3 al norte desde (5, 0)
    assert f.glifo(65)[0] == [[(5.0, 0.0), (5.0, 3.0)]]


def test_shx_puntos_topados_y_escala_finita():
    f = shx.leer_bytes(_unifont(_puntos_explosivos() | {70: _ESCALA}))
    t0 = time.perf_counter()
    trazos, _avance = f.glifo(8)
    assert 0 < sum(len(t) for t in trazos) <= shx.TOPE_PUNTOS
    trazos_e, avance = f.glifo(70)
    assert _todos_finitos(trazos_e) and math.isfinite(avance)
    assert time.perf_counter() - t0 < 2


def test_shx_roto_no_tira_las_otras_fuentes(tmp_path):
    (tmp_path / "buena.shx").write_bytes(_unifont({65: _A}))
    # shapes sin cabecera de altura: leer() mide las mayúsculas H/E/I/T, ahí estaba el RecursionError
    (tmp_path / "hostil.shx").write_bytes(_shapes({72: _BANDERAS, 69: _FRACCION_CORTA, 73: _BANDERAS, 84: _BANDERAS}))
    s = api.Sesion()
    api.llamar(s, "create_sketch", {"plane": "XY", "name": "B"})
    t0 = time.perf_counter()
    assert api.llamar(s, "add_font_folder", {"path": str(tmp_path)})["ok"]
    nombres = [f["name"] for f in api.llamar(s, "list_fonts", {"query": "shx"})["result"]["families"]]
    assert "buena SHX" in nombres
    assert api.llamar(s, "add_text", {"text": "A", "font": str(tmp_path / "buena.shx"), "height": 10})["ok"]
    assert time.perf_counter() - t0 < 2


def test_contorno_giro_muchas_aristas_rapido_y_correcto():
    # escalera de N peldaños: la envolvente es la escalera misma
    n = 4000
    prims = []
    for k in range(n):
        prims.append(("linea", None, (float(k), float(k + 1)), (float(k + 1), float(k + 1))))
        prims.append(("linea", None, (float(k + 1), float(k + 1)), (float(k + 1), float(k + 2))))
    t0 = time.perf_counter()
    res = contorno_giro.contorno_exterior(prims, ((0.0, 0.0), (1.0, 0.0)))
    assert time.perf_counter() - t0 < 2
    assert res and math.isclose(max(max(p[2][1], p[3][1]) for p in res), n + 1)


def test_boc32_shx_puntos_acumulados_por_fuente(monkeypatch):
    monkeypatch.setattr(shx, "TOPE_PUNTOS_FUENTE", 500_000, raising=False)
    glifos = _puntos_explosivos() | {c: bytes([7, 0, 8]) for c in range(100, 160)}
    f = shx.leer_bytes(_unifont(glifos))
    t0 = time.perf_counter()
    primero = f.glifo(100)
    assert primero[0]
    acumulados = sum(len(t) for t in primero[0])
    vacios = 0
    for codigo in range(101, 160):
        glifo = f.glifo(codigo)
        if acumulados > shx.TOPE_PUNTOS_FUENTE:
            assert glifo == ([], 0.0)
            assert f.glifo(codigo) is glifo
            vacios += 1
        else:
            assert glifo[0]
        acumulados += sum(len(t) for t in glifo[0])
        assert acumulados <= shx.TOPE_PUNTOS_FUENTE + shx.TOPE_PUNTOS
    assert vacios > 0
    assert f.glifo(100) is primero
    assert time.perf_counter() - t0 < 5
