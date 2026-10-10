# -*- coding: utf-8 -*-
"""Abrir .f3d de Fusion SIN Fusion: descompresor Zstandard, lector SAB (ACIS/ShapeManager) y paso a OpenCascade.

Las piezas se arman acá mismo (un cubo y un cilindro escritos en SAB, metidos en un ZIP como los de Fusion): las
pruebas no dependen de archivos de nadie."""
import base64
import hashlib
import math
import struct
import zipfile
import zlib

import pytest

from omnicad import api
from omnicad.io_archivos import acis_occ, f3d_nativo, puente_fusion, sab, zstd_puro
from omnicad.io_archivos.abrir_externo import documento_desde_archivo
from omnicad.nucleo import geometria as g

# ---------------------------------------------------------------- Zstandard
# Texto determinista comprimido con la referencia (Python 3.14, compression.zstd, nivel 19): trae bloques
# comprimidos con literales Huffman y secuencias FSE.
_ZSTD_B64 = "".join([
    "KLUv/WAIJa1KAKZiWBmAqR1g/GbFT9vwBnwC04SspUiymy+dkFUJWgBVAEkA9stIyvYrVuLYHwU4xvGAt//06DDSAbHWVAVlAbT+YOgYyUKKY/",
    "FJgCBThzr2yR9MrTeVEkLsFwjwxw51+MRc9VCDXwH7hZL1x5TCSD5Ry5BxDMFChwRiaqkkqXfmkS++65eq6PvpzDqaTfxHPqmzXlEKb0HkASUz",
    "+fSHhRLnE8Qwe7dnfqxQOonDFPKGkgMZAbss6aqD4w2/1g/sj5GogaECMtRP6iQjgViKcHw6BMjMi1bQFXWbebvVTLtz8217s5eSebeGU/MTtn",
    "HkOflU8dI0mzO9u4vZqc+GH0H0koi9xwW7sH/6wqb4+kuTeWVPncs6e/MZvfbqWGjT9oq5RN7m7EtD47pcTHPv7a5JVm1XL2iwHbc1NU0W5zZt",
    "xqj1JY1zK7Pnbrq5bDdrusibs3Y2nnvusV4enpUsmXqIrNcBhFSoo02IFUlSkFSmzSMgIGDQMCGSwTwt+gEjADGIE8AEwjOWCIY1VBoDTSt8mW",
    "Mq9eP0oeSxOGaPVrdV+PyJjaNaKQy0i2ly99A0sM8GSyRLl8TrLdGjBi//onMrWjymXpxx0fb7wliBjFfaX/XIVsnwPosWdtZpX+6taVYDc43M",
    "QtIe5rPO0RgdOq/EkZUD6zlmw8eXhjebh/TIOhV7BKWsUMbFMthHwXoLAnUkgDBaCvh7wkkC6V/4T3Aw5yNgLfTsY9BS9xQ8EAF7iqqVsJ3zCy",
    "sU/Fwaz/OXYrmWL3cgVQLjM6T1qpqb0a844j6KixL+CKuSua/I8tmsqKJdxa+VsrMDC2vDPOmXpn4vGRgIOSwU6MyzZ+SWudWUuQtfae+bHKOL",
    "jqqVG3iDP0UutIafzNpYpsZOvMwHtg19HjyCvEAm519019s1btmj74UD1v5SohzV4OMHFDkex7EhSDT+QlUGhgqjvy3IYs1UhRFLg60nC/7EYH",
    "qwFWvsyQ+iB23BzygnBDrDi/F252vI+YIELGZI6ynQ98aBOIPeccAus4INxyfMMhx59kEkQlAGCcgRwdeYc8vu4hRaucAeGBNQvUf9rxco3G12",
    "rjbuWwOcOjmZSp5Yf0IYKnZTr1iNc675R2cuuWR3ZsmFvpBGA/+/mZ8sWRhAwRUtrnd3eQOEDSj0yQoyJ8yKdUf0JadGqFenxjKKC8q4TJ52gp",
    "uLrAc/aEZHT0lHS2o53yCaK/be81ynBauqjhSErFhNxpbPONPKQsorSi+3K/jRPRwQydxDtVfBN9fXYjPViJREEGPTb910DcphAbOjeIRjiAz5",
    "m0WMdM/l0S9x6ruI+iJg1mIE02jJFF6+AvV5G0VugwnORykj0JGZa4J2UZsQcvN69PRSj3HeTfVXiA6NVswS0nJV2EIk00BZxyl1PCe0ZWhqG9",
    "mO8fAMjoC1AIzim/WI6siG9QjXyt9sY7DyM3P/Le+1M8EZ9xAl2AGDcZi3L9sO4jPf3NsiN6FBRPKke6Vh84mm1aheLYmRqHv0nVrj6CFs0TJG",
    "N4YMBq3VlX01XECARsw2Ly+54OfAjMY7JlrcZeuLtR2MMjREaGjJ9GKjYULive1lDXSwJQ5yq6VthYapFUuiT76y6+iXgGKSyMnkboUtQ2HW5n",
    "+Lkwt1RtcQUTdHJgnSKbWQp1vLmEqDhDOeFwGbMU0i6D3oaFFMMERdbbVoFydiE2Fj5IPT8EMwHrpYhvsbRFk52Q5tTJu1jdQelYZBZHGF/Tv6",
    "jhPGG540bBBEQ2ujPk/ycEQ5LKHqeuvevk4LALstMkzLuH65ZZcgMsYHZQmaKi92rzzwmTBF1XAgOaa483JSUnJmQ7GQekXybO3UeUWI7rrVDj",
    "jdEiR6dYa8TJ3qKPJ30miFxVVALu69gqCwcBiSU0wqkDkFYPP/NrJuZ547vrmow8zoJ8E0TtE1wCyFLCJx3WwEoNqq/72H7BeQWKIgIT/aB4Po",
    "cpjQ5zuvq7w82uaBKlhFM9OGyNvE0pI1KnrtQTgiGCpj65xWDBmkiuW7HZfbsvn91pMAPF0QK5agyi8+g/hv9fyI+0QwnrkmJokoFFNgxWGkOm",
    "E8yptus1rffkjG4tCkr71x5k1x+j24TheqhqlSlDO9fhDEBlJYZ1xBD2JdhDg4ZWlyTffE5ec4C3A1+XrPvBohW8Sx/YyAvGuqZc7kV2DQ5O0V",
    "faMqEsW/aUQQJZRzjq+VVNm3tD7nU885wXVwESsMxH21IKXALWjf4/y6gFPAldOd3CCvpKOEuErQBUiwd/rq0KaF5fXvQJxwYhHmgfA7S8fN5q",
    "IJ7cU/6WzeLHhAcM4vVPUWZXko/usDYQA4gIg6rG/KJowZXCZro6NewHVTF3JvCSx49c0TpL02r7Hpodkuv+ys50LAXYfJPA2qQfn6z3F9CG2U",
    "b4JMMwCH8tO08Ap3TZbLuzCDzEep4H4ypeXSyykgrlbIWvuKZiKMoYFlkSuC2PvKfMhZEpZv0m3dAdTAujFqCLsYaSCDW4cliNXRDOGk1wPkOy",
    "aaZKd6I34kgu5KdAQYpDEuo9IJExkdazMhww0eMompmS7RxQGSpjHSw4b4Fab2O5FTkJnACOQQnzFDL37BKaMdV58jwyOgeES89gYEaVUmr0MI",
    "oF0GoB5m0a3ZEhmp57rD6TH4ZKFTklrQ34T5oAMIHHE9PpNDLvnja69RqyqAv3A1y8srFjNkfaa9BlJEGnOvjjeO3ROOELMAiw0iLm6YUJinB7",
    "EkjIDnZcajHKms1YXCQTlGV5LAQ3BYClTh/bJ5XNat6gThsygDrVAFQ6pgbyFIDI9Ff08YdoaCyLaFAU1pWyn3vEdHY3+DXsQKIkgJADKnlsVl",
    "kZsOA8KGEqeGph7GkCQH6A4bOSuWBliQkrJKWCtyjnjOWqmbE61lyrrFrMc4RRYAaMmiXnAScwV0ma0GdCz0z6PKGmx7AZ6rjJ18qkF+sc2Bgn",
    "/H65Dqvd7YgA4sqRLyOHnIlU0vmR7k9A6n+hK5RWP4ugRc3mtgb2VwZ417Y2YYXNG6bjdrzQuXShoLRblAD+WDD4b2fnwKHz7TBSPTgVHVms88",
    "X7iRqMnDRN6mmFOHK7/pB4KvLYcn8DyYHaABp/nbqVTLeU/S+TcA8WLRq7pR4cBLCtVg2YAYED6cZexNqSjnxaDj06sCSi1IyMSl1VkinRaW4x",
    "cfeipGaVc=",
])
_ZSTD_SHA256 = "5753cd8eac6ed21f3deb4fd4c3d85987fd6cbf9a1e02f1584b2394e377a1fd06"


def _texto_fixture():
    palabras = ("sello rotativo cartera gotica abanico varilla tira nucleo eje tapon horquilla mango aro perno pared base "
                "asa dragon garra cabeza boca ojo diente cola ala pata cuerpo cara arista vertice lazo curva superficie "
                "plano cono esfera toro spline").split()
    x, salida = 12345, []
    for _ in range(1500):
        x = (x * 1103515245 + 12345) % 2147483648
        w = palabras[(x >> 16) % len(palabras)]
        if (x >> 8) % 11 == 0:
            w += str((x >> 4) % 1000)
        salida.append(w)
    return " ".join(salida).encode()


def _trama_cruda(datos, rle=None):
    """Trama Zstandard hecha a mano: un bloque crudo (y opcionalmente uno RLE: (byte, veces))."""
    cab = struct.pack("<I", zstd_puro.MAGICO) + bytes([0x20 | 0x80]) + struct.pack("<I", len(datos) + (rle[1] if rle else 0))
    ultimo = 0 if rle else 1
    bloques = struct.pack("<I", ultimo | (0 << 1) | (len(datos) << 3))[:3] + datos
    if rle:
        bloques += struct.pack("<I", 1 | (1 << 1) | (rle[1] << 3))[:3] + bytes([rle[0]])
    return cab + bloques


def test_zstd_igual_a_la_referencia():
    comprimido = base64.b64decode(_ZSTD_B64)
    salida = zstd_puro._descomprimir_puro(comprimido)
    assert salida == _texto_fixture()
    assert hashlib.sha256(salida).hexdigest() == _ZSTD_SHA256
    assert zstd_puro.descomprimir(comprimido) == salida            # con o sin la biblioteca estándar


def test_zstd_bloques_crudos_rle_y_errores():
    assert zstd_puro._descomprimir_puro(_trama_cruda(b"hola ")) == b"hola "
    assert zstd_puro._descomprimir_puro(_trama_cruda(b"ab", rle=(ord("z"), 5))) == b"abzzzzz"
    assert zstd_puro._descomprimir_puro(_trama_cruda(b"x") + _trama_cruda(b"y")) == b"xy"   # dos tramas seguidas
    with pytest.raises(zstd_puro.ErrorZstd, match="mágico"):
        zstd_puro._descomprimir_puro(b"no es zstd")


# ---------------------------------------------------------------- escritor SAB mínimo (solo para las pruebas)
class _Ptr(int):
    pass


class _Enum(int):
    pass


def _valor(v):
    if isinstance(v, bool):
        return b"\x0a" if v else b"\x0b"
    if isinstance(v, _Ptr):
        return b"\x0c" + struct.pack("<i", v)
    if isinstance(v, _Enum):
        return b"\x15" + struct.pack("<i", v)
    if isinstance(v, int):
        return b"\x04" + struct.pack("<i", v)
    if isinstance(v, float):
        return b"\x06" + struct.pack("<d", v)
    if isinstance(v, tuple):
        return b"\x13" + struct.pack("<3d", *v)
    if isinstance(v, str):
        return b"\x07" + bytes([len(v)]) + v.encode()
    if isinstance(v, list):                                  # subtipo: ["nombre", valores…]
        return b"\x0f\x0d" + bytes([len(v[0])]) + v[0].encode() + b"".join(_valor(x) for x in v[1:]) + b"\x10"
    raise TypeError(v)


def _nombre(tipo):
    partes = tipo.split("-")
    return b"".join(b"\x0e" + bytes([len(p)]) + p.encode() for p in partes[:-1]) + b"\x0d" + bytes(
        [len(partes[-1])]) + partes[-1].encode()


def _sab(registros):
    """Bloque SAB de ShapeManager 232 con `registros` = [(tipo, [campos…]), …] (punteros = índices en la lista)."""
    cab = b"ASM BinaryFile4" + struct.pack("<4I", 23200, 0, 1, 0)
    cab += b"".join(_valor(v) for v in ("Autodesk Neutron", "ASM 232.4.0.65535 NT", "hoy", 10.0, 1e-6, 1e-10))
    cuerpo = b"".join(_nombre(t) + b"".join(_valor(v) for v in campos) + b"\x11" for t, campos in registros)
    return cab + cuerpo + b"\x0e\x03End\x0e\x02of\x0e\x03ASM\x0d\x04data"


class _Modelo:
    """Arma registros ACIS con la disposición de ShapeManager 232: atributo, id, extra y los datos."""
    N = _Ptr(-1)

    def __init__(self):
        self.r = [("asmheader", [self.N, -1, "232.4.0.65535"])]

    def nuevo(self, tipo, *datos, atributo=None):
        self.r.append((tipo, [_Ptr(atributo if atributo is not None else -1), -1, self.N, *datos]))
        return _Ptr(len(self.r) - 1)

    def poner(self, ptr, k, valor):
        self.r[ptr][1][k] = valor


def _cuerpo_vacio(m, con_marca=True):
    body = m.nuevo("body", m.N, m.N, m.N)
    if con_marca:
        at = len(m.r)
        m.r.append(("ATTRIB_CUSTOM-attrib", [m.N, -1, m.N, m.N, body, "Timestamp_attrib_def", 1, 1.79e15]))
        m.poner(body, 0, _Ptr(at))
    lump = m.nuevo("lump", m.N, m.N, body)
    shell = m.nuevo("shell", m.N, m.N, m.N, m.N, lump)
    m.poner(body, 3, lump)
    m.poner(lump, 4, shell)
    return body, shell


def _caras(m, shell, caras):
    """`caras` = [(superficie, al_revés, [[(arista, coedge_al_revés), …] por lazo])]. Enlaza todo."""
    previa = None
    for superficie, al_reves, lazos in caras:
        face = m.nuevo("face", m.N, m.N, shell, m.N, superficie, al_reves, False)
        if previa is None:
            m.poner(shell, 5, face)
        else:
            m.poner(previa, 3, face)
        previa = face
        loop_prev = None
        for lazo in lazos:
            loop = m.nuevo("loop", m.N, m.N, face)
            if loop_prev is None:
                m.poner(face, 4, loop)
            else:
                m.poner(loop_prev, 3, loop)
            loop_prev = loop
            coedges = [m.nuevo("coedge", m.N, m.N, m.N, arista, rev, loop, 0, m.N) for arista, rev in lazo]
            m.poner(loop, 4, coedges[0])
            for i, co in enumerate(coedges):
                m.poner(co, 3, coedges[(i + 1) % len(coedges)])
                m.poner(co, 4, coedges[i - 1])
                arista = lazo[i][0]
                otro = m.r[arista][1][7]                     # el coedge ya anotado en la arista
                if otro == -1:
                    m.poner(arista, 7, co)
                else:
                    m.poner(co, 5, otro)
                    m.poner(otro, 5, co)


def _vertice(m, p):
    punto = m.nuevo("point", p)
    return m.nuevo("vertex", m.N, 0, punto)


def _sab_cubo(lado=1.0, con_marca=True):
    """Cubo de `lado` cm con 6 planos, 12 rectas y 8 vértices."""
    m = _Modelo()
    _, shell = _cuerpo_vacio(m, con_marca)
    p = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]
    p = [tuple(float(c) * lado for c in q) for q in p]
    vs = [_vertice(m, q) for q in p]
    aristas = {}

    def arista(a, b):
        i, j = min(a, b), max(a, b)
        if (i, j) not in aristas:
            d = tuple((p[j][k] - p[i][k]) / lado for k in range(3))
            recta = m.nuevo("straight-curve", p[i], d, False, False)
            e = m.nuevo("edge", vs[i], 0.0, vs[j], lado, m.N, recta, False, "unknown")
            for v in (vs[i], vs[j]):
                if m.r[v][1][3] == -1:
                    m.poner(v, 3, e)
            aristas[(i, j)] = e
        return aristas[(i, j)], a > b

    caras = []
    for quad, normal in (((0, 3, 2, 1), (0, 0, -1)), ((4, 5, 6, 7), (0, 0, 1)), ((0, 1, 5, 4), (0, -1, 0)),
                         ((2, 3, 7, 6), (0, 1, 0)), ((0, 4, 7, 3), (-1, 0, 0)), ((1, 2, 6, 5), (1, 0, 0))):
        u = tuple((p[quad[1]][k] - p[quad[0]][k]) / lado for k in range(3))
        plano = m.nuevo("plane-surface", p[quad[0]], tuple(float(c) for c in normal), u, False, False, False, False, False)
        caras.append((plano, False, [[arista(quad[i], quad[(i + 1) % 4]) for i in range(4)]]))
    _caras(m, shell, caras)
    return m


def _sab_cilindro(radio=0.5, alto=1.0):
    """Cilindro de ACIS: cara lateral (cono con seno 0) con dos lazos circulares y sin costura, como lo guarda Fusion."""
    m = _Modelo()
    _, shell = _cuerpo_vacio(m)
    circulos = []
    for z in (0.0, alto):
        v = _vertice(m, (radio, 0.0, z))
        curva = m.nuevo("ellipse-curve", (0.0, 0.0, z), (0.0, 0.0, 1.0), (radio, 0.0, 0.0), 1.0, False, False)
        e = m.nuevo("edge", v, 0.0, v, 2 * math.pi, m.N, curva, False, "unknown")
        m.poner(v, 3, e)
        circulos.append(e)
    abajo, arriba = circulos
    lateral = m.nuevo("cone-surface", (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), (radio, 0.0, 0.0), 1.0, False, False, 0.0, 1.0,
                      radio, False, False, False, False, False)
    piso = m.nuevo("plane-surface", (0.0, 0.0, 0.0), (0.0, 0.0, -1.0), (1.0, 0.0, 0.0), False, False, False, False, False)
    techo = m.nuevo("plane-surface", (0.0, 0.0, alto), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0), False, False, False, False, False)
    _caras(m, shell, [(piso, False, [[(abajo, True)]]), (techo, False, [[(arriba, False)]]),
                      (lateral, False, [[(abajo, False)], [(arriba, True)]])])
    return m


def _zip_f3d(ruta, bloques, zstd=True):
    """ZIP como el de Fusion: cada bloque en `Breps.BlobParts/` (con Zstandard, método 93, como Fusion)."""
    locales, central, pos = b"", b"", 0
    for nombre, datos in bloques:
        nombre_b = nombre.encode()
        guardado = _trama_cruda(datos) if zstd else datos
        metodo = 93 if zstd else 0
        crc = zlib.crc32(datos)
        local = struct.pack("<IHHHHHIIIHH", 0x04034B50, 63, 0, metodo, 0, 0, crc, len(guardado), len(datos),
                            len(nombre_b), 0) + nombre_b + guardado
        central += struct.pack("<IHHHHHHIIIHHHHHII", 0x02014B50, 63, 63, 0, metodo, 0, 0, crc, len(guardado), len(datos),
                               len(nombre_b), 0, 0, 0, 0, 0, pos) + nombre_b
        locales += local
        pos += len(local)
    fin = struct.pack("<IHHHHIIH", 0x06054B50, 0, 0, len(bloques), len(bloques), len(central), pos, 0)
    ruta.write_bytes(locales + central + fin)
    return ruta


_CARPETA = "FusionAssetName[Active]/Breps.BlobParts/"


# ---------------------------------------------------------------- lector SAB
def test_sab_lee_registros_punteros_y_subtipos():
    m = _sab_cubo()
    m.r.append(("intcurve-curve", [_Ptr(-1), -1, _Ptr(-1), False, ["exact_int_cur", 23100, _Enum(0)], False, False]))
    m.r.append(("intcurve-curve", [_Ptr(-1), -1, _Ptr(-1), False, ["ref", 0], False, False]))
    archivo = sab.leer(_sab(m.r))
    assert archivo.cabecera["producto"] == "Autodesk Neutron" and archivo.cabecera["escala"] == 10.0
    assert len(archivo.de_tipo("face")) == 6 and len(archivo.de_tipo("edge")) == 12
    assert len(archivo.de_tipo("vertex")) == 8 and len(archivo.de_tipo("plane-surface")) == 6
    cara = archivo.de_tipo("face")[0]
    assert isinstance(cara.campos[4], sab.Puntero) and archivo.entidad(cara.campos[4]).tipo == "loop"
    definida, referida = [e.campos[4] for e in archivo.de_tipo("intcurve-curve")]
    assert definida.nombre == "exact_int_cur" and isinstance(definida.items[1], sab.Enumerado)
    assert archivo.resolver(referida) is definida                       # { ref 0 } → el subtipo 0
    with pytest.raises(sab.ErrorSAB):
        sab.leer(b"no es un bloque SAB")


# ---------------------------------------------------------------- ACIS → OpenCascade
def test_cubo_de_acis_a_solido_en_mm():
    partes, avisos = acis_occ.convertir(sab.leer(_sab(_sab_cubo().r)))
    assert avisos == [] and len(partes) == 1
    forma, tipo, marca = partes[0]
    assert tipo == "solido" and marca == 1.79e15 and g.es_valida(forma)
    assert g.volumen(forma) == pytest.approx(1000.0, rel=1e-9)            # 1 cm³ de Fusion = 1000 mm³
    (x0, y0, z0), (x1, y1, z1) = g.caja_envolvente(forma)
    assert (x1 - x0, y1 - y0, z1 - z0) == pytest.approx((10, 10, 10), abs=1e-6)
    assert len(g.caras(forma)) == 6


def test_cilindro_sin_costura_queda_cerrado():
    partes, _ = acis_occ.convertir(sab.leer(_sab(_sab_cilindro().r)))
    forma, tipo, _ = partes[0]
    assert tipo == "solido" and g.es_valida(forma)
    assert g.volumen(forma) == pytest.approx(math.pi * 25 * 10, rel=1e-6)
    assert g.area(forma) == pytest.approx(2 * math.pi * 25 + 2 * math.pi * 5 * 10, rel=1e-6)


def test_cuerpos_auxiliares_sin_marca_quedan_afuera():
    m = _sab_cubo()
    aux = _sab_cubo(lado=0.5, con_marca=False)                         # otro cuerpo, sin marca de tiempo
    base = len(m.r)

    def mover(v):
        return _Ptr(v + base - 1) if isinstance(v, _Ptr) and v > 0 else v
    m.r += [(t, [mover(v) for v in campos]) for t, campos in aux.r[1:]]
    partes, _ = acis_occ.convertir(sab.leer(_sab(m.r)))
    assert len(partes) == 1 and g.volumen(partes[0][0]) == pytest.approx(1000.0, rel=1e-9)


# ---------------------------------------------------------------- .f3d completo
def test_f3d_nativo_lee_el_zip_de_fusion(tmp_path):
    f3d = _zip_f3d(tmp_path / "pieza.f3d", [
        (_CARPETA + "BREP.aaaa.smbh", _sab(_sab_cubo().r)),
        (_CARPETA + "BREP.bbbb.smb", b"boceto: no se importa"),
        ("Properties.dat", b"x"),
    ])
    partes, avisos = f3d_nativo.leer(f3d)
    assert len(partes) == 1 and partes[0][1] == "solido" and avisos == []
    assert g.volumen(partes[0][0]) == pytest.approx(1000.0, rel=1e-9)


def test_f3d_con_componente_repetido_no_duplica(tmp_path):
    """El mismo componente guardado dos veces (versión vieja y actual) entra una sola vez."""
    f3d = _zip_f3d(tmp_path / "pieza.f3d", [(_CARPETA + "BREP.a.smbh", _sab(_sab_cubo().r)),
                                            (_CARPETA + "BREP.b.smbh", _sab(_sab_cubo().r))])
    partes, _ = f3d_nativo.leer(f3d)
    assert len(partes) == 1


def test_f3d_sin_geometria_o_danado(tmp_path):
    vacio = _zip_f3d(tmp_path / "vacio.f3d", [("Properties.dat", b"x")], zstd=False)
    with pytest.raises(f3d_nativo.ErrorF3D, match="no trae geometría"):
        f3d_nativo.leer(vacio)
    roto = tmp_path / "roto.f3d"
    roto.write_bytes(b"PK no es un zip")
    with pytest.raises(f3d_nativo.ErrorF3D, match="no es un archivo de Fusion válido"):
        f3d_nativo.leer(roto)


def test_f3z_toma_el_diseno_principal(tmp_path):
    principal = _zip_f3d(tmp_path / "principal.f3d", [(_CARPETA + "BREP.a.smbh", _sab(_sab_cubo().r))])
    otro = _zip_f3d(tmp_path / "otro.f3d", [(_CARPETA + "BREP.b.smbh", _sab(_sab_cilindro().r))])
    import json
    descripcion = {"designDescription": {"designGraphs": [{"designObjects": [
        {"id": "1", "contentType": "f3d", "relativePath": "principal.f3d", "references": [{"ids": ["2"]}]},
        {"id": "2", "contentType": "f3d", "relativePath": "otro.f3d"}]}]}}
    f3z = tmp_path / "paquete.f3z"
    with zipfile.ZipFile(f3z, "w") as z:
        z.writestr("DesignDescription.json", json.dumps(descripcion))
        z.write(principal, "principal.f3d")
        z.write(otro, "otro.f3d")
    partes, _ = f3d_nativo.leer(f3z)
    assert len(partes) == 1 and g.volumen(partes[0][0]) == pytest.approx(1000.0, rel=1e-9)


def test_abrir_e_insertar_f3d_sin_fusion(tmp_path, monkeypatch):
    monkeypatch.setenv(puente_fusion.VARIABLE_CARPETA, str(tmp_path / "sin_fusion"))   # Fusion cerrado
    f3d = _zip_f3d(tmp_path / "soporte.f3d", [(_CARPETA + "BREP.a.smbh", _sab(_sab_cubo().r)),
                                              (_CARPETA + "BREP.b.smbh", _sab(_sab_cilindro(alto=2.0).r))])
    doc, avisos = documento_desde_archivo(f3d)
    cuerpos = list(doc.estado_final.cuerpos.values())
    assert doc.operaciones[0].TIPO == "operacion_base" and len(cuerpos) == 2
    assert sorted(c.nombre for c in cuerpos) == ["soporte (1)", "soporte (2)"]
    assert any("sin Fusion" in a for a in avisos)
    sesion = api.Sesion()
    r = api.llamar(sesion, "open_document", {"path": str(f3d)})
    assert r["ok"] and len(r["result"]["bodies"]) == 2
    r = api.llamar(sesion, "insert_file", {"path": str(f3d)})
    assert r["ok"] and len(r["result"]["new_bodies"]) == 2
