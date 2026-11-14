# -*- coding: utf-8 -*-
"""B-363: el Fusion nuevo (ASM 231) guarda los cuerpos en `.smb` y ya no escribe `.smbh`: el .f3d se abre igual."""
import io
import zipfile
from pathlib import Path

from omnicad.io_archivos import f3d_nativo
from omnicad.nucleo import geometria as geo

SMB = Path(__file__).parent / "datos" / "b363_cuerpo_smb.smb"        # un sólido real de la Prusa Core One (2,4 KB)


def _f3d(nombre_bloque):
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"FusionAssetName[Active]/Breps.BlobParts/{nombre_bloque}", SMB.read_bytes())
    return salida.getvalue()


def test_f3d_sin_smbh_lee_los_cuerpos_de_los_smb():
    componentes, _ = f3d_nativo.leer_componentes_bytes(_f3d("BREP.x.smb"), "nuevo")
    assert [c["tipo"] for c in componentes] == ["solido"]
    assert geo.es_valida(componentes[0]["forma"]) and geo.volumen_exacto(componentes[0]["forma"]) > 0


def test_f3d_sin_ningun_bloque_brep_sigue_diciendo_que_no_trae_geometria():
    import pytest
    with pytest.raises(f3d_nativo.ErrorF3D, match="no trae geometría 3D"):
        f3d_nativo.leer_componentes_bytes(_f3d("otro.dat"), "vacio")
