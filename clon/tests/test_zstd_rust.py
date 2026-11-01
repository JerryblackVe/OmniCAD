"""RS-R1: el descompresor Zstandard de Rust da los mismos bytes y los mismos errores que `zstd_puro` (referencia y respaldo)."""
import base64
import hashlib
import struct
import zipfile
from pathlib import Path

import pytest
from test_f3d_nativo import _ZSTD_B64, _ZSTD_SHA256, _trama_cruda

from omnicad import nativo
from omnicad.io_archivos import zstd_puro


@pytest.fixture
def rs(monkeypatch):
    monkeypatch.delenv("OMNICAD_SIN_RUST", raising=False)
    motor = nativo.disponible()
    if not hasattr(motor, "zstd_descomprimir"):
        pytest.skip("Extensión Rust opcional no compilada (o vieja) en este entorno.")
    return motor


def _bomba():
    """32 bloques RLE de 128 KiB (el máximo legal) que se expanden a 4 MiB desde 140 bytes."""
    rle = ((1 << 17) << 3) | (1 << 1)
    return (struct.pack("<I", zstd_puro.MAGICO) + bytes([0x20 | 0x80]) + struct.pack("<I", 32 << 17)
            + (struct.pack("<I", rle)[:3] + b"z") * 31 + struct.pack("<I", rle | 1)[:3] + b"z")


def _salteable(carga=b"meta"):
    return struct.pack("<II", 0x184D2A50, len(carga)) + carga


def _vectores():
    return {
        "huffman_fse": base64.b64decode(_ZSTD_B64),
        "cruda": _trama_cruda(b"hola "),
        "rle": _trama_cruda(b"ab", rle=(ord("z"), 5)),
        "dos_tramas": _trama_cruda(b"x") + _trama_cruda(b"y"),
        "con_salteable": _trama_cruda(b"x") + _salteable() + _trama_cruda(b"y") + _salteable(b""),
        "vacio": b"",
    }


@pytest.mark.parametrize("nombre", list(_vectores()))
def test_bytes_identicos_a_la_referencia(rs, nombre):
    datos = _vectores()[nombre]
    assert rs.zstd_descomprimir(datos) == zstd_puro._descomprimir_puro(datos)
    assert rs.zstd_descomprimir(datos, 1 << 30) == zstd_puro._descomprimir_puro(datos)


def test_vector_grande_con_hash_conocido(rs):
    salida = rs.zstd_descomprimir(base64.b64decode(_ZSTD_B64))
    assert hashlib.sha256(salida).hexdigest() == _ZSTD_SHA256


@pytest.mark.parametrize("datos,tope,texto", [
    (b"no es zstd", None, "mágico"),
    (struct.pack("<I", zstd_puro.MAGICO)[:3], None, "truncada"),
    (_trama_cruda(b"0123456789"), 9, "tope"),
    (_bomba(), 10, "tope"),
    (base64.b64decode(_ZSTD_B64)[:-40], None, "inválido|truncada"),          # trama cortada a la mitad de un bloque
    (_salteable(b"corta")[:-2], None, "truncada"),
])
def test_mismos_errores_que_la_referencia(rs, datos, tope, texto):
    with pytest.raises(ValueError, match=texto):
        rs.zstd_descomprimir(datos, tope)
    with pytest.raises(zstd_puro.ErrorZstd):
        zstd_puro._descomprimir_puro(datos, tope)


def test_tope_justo_no_falla(rs):
    assert rs.zstd_descomprimir(_trama_cruda(b"0123456789"), 10) == b"0123456789"


def test_descomprimir_traduce_el_error_a_errorzstd(rs):
    with pytest.raises(zstd_puro.ErrorZstd, match="tope"):
        zstd_puro.descomprimir(_bomba(), tope=10)


def test_respaldo_en_python_sin_el_modulo_nativo(monkeypatch):
    monkeypatch.setenv("OMNICAD_SIN_RUST", "1")
    assert nativo.disponible() is None
    datos = base64.b64decode(_ZSTD_B64)
    assert zstd_puro.descomprimir(datos, tope=1 << 30) == zstd_puro._descomprimir_puro(datos)
    with pytest.raises(zstd_puro.ErrorZstd, match="tope"):
        zstd_puro.descomprimir(_bomba(), tope=10)


def test_pyd_viejo_sin_la_funcion_cae_a_python(monkeypatch):
    monkeypatch.setattr(nativo, "disponible", lambda: object())
    assert zstd_puro.descomprimir(_trama_cruda(b"hola"), tope=100) == b"hola"


_F3Z = Path.home() / "Desktop" / "f3z"


@pytest.mark.skipif(not _F3Z.is_dir(), reason="Sin los .f3d reales de ~/Desktop/f3z")
def test_miembros_zstd_de_un_f3d_real_identicos_a_la_referencia(rs):
    ruta = min(_F3Z.glob("*.f3d"), key=lambda p: p.stat().st_size)
    datos = ruta.read_bytes()
    with zipfile.ZipFile(ruta) as z:
        miembros = [i for i in z.infolist() if i.compress_type == zstd_puro.METODO_ZIP_ZSTD]
        assert miembros, "el .f3d de prueba no trae miembros Zstandard"
        for info in miembros:
            nombre, extra = struct.unpack_from("<HH", datos, info.header_offset + 26)
            ini = info.header_offset + 30 + nombre + extra
            comprimido = datos[ini:ini + info.compress_size]
            nativo_ = rs.zstd_descomprimir(comprimido, info.file_size)
            assert hashlib.sha256(nativo_).digest() == hashlib.sha256(zstd_puro._descomprimir_puro(comprimido, info.file_size)).digest()
