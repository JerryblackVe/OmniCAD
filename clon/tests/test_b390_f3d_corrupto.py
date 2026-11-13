# -*- coding: utf-8 -*-
"""B-390: un .f3d corrupto da un error de importación claro, sin excepciones internas."""
from pathlib import Path
import struct
import zipfile

import pytest

from omnicad import api
from omnicad.io_archivos import f3d_nativo


@pytest.mark.parametrize("nombre", [
    "b390_f3d_seek_negativo.f3d",
    "b390_f3d_zip_version.f3d",
])
def test_inspect_f3d_corrupto_da_error_en_espanol(nombre):
    ruta = Path(__file__).parent / "corpus_caza" / nombre
    respuesta = api.llamar(api.Sesion(), "inspect_f3d", {"path": str(ruta)})

    assert respuesta["ok"] is False, respuesta
    assert respuesta["error_kind"] == "IMPORT_FAILED", respuesta
    assert any(texto in respuesta["mensaje"] for texto in ("dañado", "no es un archivo de Fusion válido")), respuesta


@pytest.mark.parametrize("metodo", [zipfile.ZIP_STORED, 93])
@pytest.mark.parametrize("desplazamiento", [-1, 1, 30, 31])
def test_miembro_rechaza_cabecera_fuera_del_archivo(metodo, desplazamiento):
    datos = b"PK\x03\x04" + b"\x00" * 26
    info = zipfile.ZipInfo("componente")
    info.compress_type = metodo
    info.header_offset = desplazamiento

    with pytest.raises(f3d_nativo.ErrorF3D, match="ZIP dañado"):
        f3d_nativo.miembro(datos, info)


@pytest.mark.parametrize("largo_nombre,largo_extra,tamano", [(1, 0, 0), (0, 1, 0), (0, 0, 1), (0, 0, -1)])
def test_miembro_zstd_rechaza_contenido_fuera_del_archivo(largo_nombre, largo_extra, tamano):
    datos = b"PK\x03\x04" + b"\x00" * 22 + struct.pack("<HH", largo_nombre, largo_extra)
    info = zipfile.ZipInfo("componente")
    info.compress_type = 93
    info.header_offset = 0
    info.compress_size = tamano

    with pytest.raises(f3d_nativo.ErrorF3D, match="ZIP dañado"):
        f3d_nativo.miembro(datos, info)
