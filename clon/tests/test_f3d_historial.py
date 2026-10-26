# -*- coding: utf-8 -*-
"""Informe de cobertura del historial de un .f3d (CL8): lo que no se traduce se declara al abrir.

El flujo de diseño de Fusion trae una tabla de tipos «<largo u32><DcXxxMetaType><cantidad u64>»; acá se arma una igual."""
import struct

from test_f3d_nativo import _CARPETA, _sab, _sab_cubo, _zip_f3d
from test_f3d_bocetos import _sab_perfiles

from omnicad import api
from omnicad.io_archivos import f3d_historial, f3d_nativo
from omnicad.io_archivos.abrir_externo import documento_desde_archivo

_FLUJO = "FusionAssetName[Active]/FusionDesignSegmentType1/BulkStream.dat"
_VIEJO = "FusionAssetName[Active]/Design1/BulkStream.dat"


def _tabla(**tipos):
    """Una tabla como la del flujo de Fusion, rodeada de basura binaria."""
    cuerpo = b"".join(struct.pack("<I", len(f"Dc{t}MetaType")) + f"Dc{t}MetaType".encode() + struct.pack("<Q", n)
                      for t, n in tipos.items())
    return b"\x01\x02\x03" * 5 + struct.pack("<I", len(tipos)) + cuerpo + b"\xff" * 12


def test_la_tabla_de_tipos_da_las_operaciones_con_su_cantidad():
    assert f3d_historial.operaciones(_tabla(ExtrudeFeature=44, Sketch=10, FilletEdgeFeature=14)) \
        == [("ExtrudeFeature", 44), ("Sketch", 10), ("FilletEdgeFeature", 14)]
    assert f3d_historial.operaciones(b"sin tabla") == []
    assert f3d_historial.operaciones(_tabla(Sketch=2**40)) == []                  # un contador imposible no es una tabla


def test_el_aviso_dice_que_no_se_traduce_y_cuenta_los_bocetos():
    texto = f3d_historial.aviso([("ExtrudeFeature", 44), ("Sketch", 10), ("RaroFeature", 3)], 9, "BINCHA.f3d")
    assert "BINCHA.f3d" in texto and "NO se traduce" in texto
    assert "44 × Extruir" in texto and "3 × RaroFeature" in texto and "× Boceto" not in texto   # los bocetos van aparte
    assert "Fusion cuenta 10 bocetos y se importaron 9" in texto
    assert f3d_historial.aviso([], 0) is None


def _f3d(tmp_path, tabla, nombre_flujo=_FLUJO):
    return _zip_f3d(tmp_path / "pieza.f3d", [(_CARPETA + "BREP.aaaa.smbh", _sab(_sab_cubo().r)),
                                             (_CARPETA + "BREP.bbbb.smb", _sab(_sab_perfiles().r)),
                                             (nombre_flujo, tabla)])


def test_abrir_un_f3d_con_historial_avisa_lo_que_no_se_tradujo(tmp_path):
    doc, avisos = documento_desde_archivo(_f3d(tmp_path, _tabla(ExtrudeFeature=3, Sketch=1, ChamferFeature=1)))
    aviso, = [a for a in avisos if "historial de Fusion" in a]
    assert "3 × Extruir" in aviso and "1 × Chaflán" in aviso and "Fusion cuenta 1 bocetos y se importaron 1" in aviso
    assert [o.TIPO for o in doc.operaciones] == ["operacion_base", "boceto"]          # el historial no se inventa


def test_el_formato_viejo_tambien_da_el_historial(tmp_path):
    resumen = {}
    f3d_nativo.leer_componentes(_f3d(tmp_path, _tabla(ExtrudeFeature=2), _VIEJO), resumen)
    assert resumen["historial"] == [("ExtrudeFeature", 2)]


def test_sin_flujo_de_diseno_no_hay_aviso_de_historial(tmp_path):
    f3d = _zip_f3d(tmp_path / "solo.f3d", [(_CARPETA + "BREP.aaaa.smbh", _sab(_sab_cubo().r))])
    _, avisos = documento_desde_archivo(f3d)
    assert not any("historial" in a for a in avisos)


def test_inspect_f3d_lista_el_historial(tmp_path):
    r = api.llamar(api.Sesion(), "inspect_f3d", {"path": str(_f3d(tmp_path, _tabla(ExtrudeFeature=44, Sketch=10)))})
    assert r["ok"], r
    assert r["result"]["history"] == {"operations": [{"type": "ExtrudeFeature", "name": "Extruir", "count": 44},
                                                     {"type": "Sketch", "name": "Boceto", "count": 10}],
                                      "translated": False}
