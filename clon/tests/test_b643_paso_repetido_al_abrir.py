"""B-643: un .omnicad con el último paso repetido idéntico («La receta repite el id de paso op305») se abre sin el repetido."""
import json
import zipfile

import pytest

from omnicad.ejemplo import crear_documento_ejemplo
from omnicad.io_archivos import proyecto
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import ErrorOperacion


def _receta_con_repetido():
    datos = crear_documento_ejemplo().a_dict()
    datos["operaciones"].append(dict(datos["operaciones"][-1]))
    return datos


def test_paso_repetido_identico_se_quita_con_aviso():
    datos = _receta_con_repetido()
    doc = Documento.desde_dict(datos)
    assert len(doc.operaciones) == len(datos["operaciones"]) - 1
    assert doc.avisos_apertura and "repetido" in doc.avisos_apertura[0]
    assert doc.modificado        # al guardar, el archivo queda arreglado
    assert doc.estado_final.cuerpos


def test_mismo_id_con_datos_distintos_sigue_rechazado():
    datos = _receta_con_repetido()
    datos["operaciones"][-1] = {**datos["operaciones"][-1], "nombre": "otro"}
    with pytest.raises(ErrorOperacion, match="repite el id"):
        Documento.desde_dict(datos)


def test_abrir_el_archivo_con_el_paso_repetido(tmp_path):
    ruta = tmp_path / "pieza.omnicad"
    proyecto.guardar(crear_documento_ejemplo(), ruta)
    with zipfile.ZipFile(ruta) as z:
        miembros = {n: z.read(n) for n in z.namelist()}
    receta = json.loads(miembros["receta.json"])
    receta["operaciones"].append(dict(receta["operaciones"][-1]))
    miembros["receta.json"] = json.dumps(receta).encode()
    with zipfile.ZipFile(ruta, "w") as z:
        for n, b in miembros.items():
            z.writestr(n, b)
    doc = proyecto.abrir(ruta)
    assert len(doc.operaciones) == len(receta["operaciones"]) - 1 and doc.avisos_apertura
