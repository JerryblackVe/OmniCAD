# -*- coding: utf-8 -*-
import json
import struct
import zipfile

import pytest

from omnicad.ejemplo import crear_documento_ejemplo
from omnicad.io_archivos import exportar as ex
from omnicad.io_archivos import proyecto
from omnicad.nucleo import geometria as g
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpImportarSTEP


@pytest.fixture(scope="module")
def doc():
    return crear_documento_ejemplo()


def test_stl_binario(doc, tmp_path):
    ruta = tmp_path / "m.stl"
    n = ex.exportar(doc.estado_final.cuerpos.values(), ruta)
    datos = ruta.read_bytes()
    assert struct.unpack("<I", datos[80:84])[0] == n
    assert len(datos) == 84 + 50 * n


def test_obj(doc, tmp_path):
    ruta = tmp_path / "m.obj"
    n = ex.exportar(doc.estado_final.cuerpos.values(), ruta)
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    assert sum(1 for x in lineas if x.startswith("f ")) == n
    assert sum(1 for x in lineas if x.startswith("o ")) == 2


def test_step_ida_y_vuelta(doc, tmp_path):
    ruta = tmp_path / "m.step"
    ex.exportar(doc.estado_final.cuerpos.values(), ruta)
    total = sum(g.volumen(c.forma) for c in doc.estado_final.cuerpos.values())
    texto = ex.leer_texto_step(ruta)
    d2 = Documento()
    r = d2.agregar(OpImportarSTEP(d2.nuevo_id(), archivo="m.step", contenido=texto))
    assert r.estado == "ok"
    vol = sum(g.volumen(c.forma) for c in d2.estado_final.cuerpos.values())
    assert vol == pytest.approx(total, rel=1e-6)


def test_formato_no_soportado(doc, tmp_path):
    with pytest.raises(ex.ErrorExportacion):
        ex.exportar(doc.estado_final.cuerpos.values(), tmp_path / "m.dwg")


def test_proyecto_guardar_y_abrir(doc, tmp_path):
    ruta = proyecto.guardar(doc, tmp_path / "ejemplo", miniatura_png=b"\x89PNG fake")
    assert ruta.suffix == ".omnicad"
    with zipfile.ZipFile(ruta) as z:
        assert {"manifiesto.json", "receta.json", "cache/cuerpos.brep", "miniatura.png"} <= set(z.namelist())
        assert json.loads(z.read("manifiesto.json"))["formato"] == proyecto.FORMATO
    abierto = proyecto.abrir(ruta)
    assert abierto.a_dict()["operaciones"] == doc.a_dict()["operaciones"]
    assert abierto.modificado is False
    assert proyecto.leer_miniatura(ruta) == b"\x89PNG fake"


def test_proyecto_del_nombre_anterior_se_abre_y_conserva_su_extension(doc, tmp_path):
    """Un .fclone guardado cuando el programa se llamaba FusionClone se abre, y al guardarlo no cambia de archivo."""
    nuevo = proyecto.guardar(doc, tmp_path / "pieza")
    viejo = tmp_path / "pieza.fclone"
    with zipfile.ZipFile(nuevo) as z, zipfile.ZipFile(viejo, "w") as w:
        for nombre in z.namelist():
            datos = z.read(nombre)
            if nombre == "manifiesto.json":
                m = json.loads(datos)
                m["formato"], m["aplicacion"] = "FusionClone-proyecto", "FusionClone"
                datos = json.dumps(m).encode()
            w.writestr(nombre, datos)
    abierto = proyecto.abrir(viejo)
    assert abierto.a_dict()["operaciones"] == doc.a_dict()["operaciones"]
    assert proyecto.guardar(abierto, viejo) == viejo


def test_proyecto_invalido(tmp_path):
    malo = tmp_path / "malo.omnicad"
    malo.write_bytes(b"no soy un zip")
    with pytest.raises(proyecto.ErrorProyecto):
        proyecto.abrir(malo)


def test_autoguardado_junto_al_proyecto(doc, tmp_path):
    ruta = proyecto.guardar(doc, tmp_path / "p.omnicad")
    doc.ruta = str(ruta)
    try:
        destino = proyecto.autoguardar(doc)
        assert destino.name == "p.autoguardado.omnicad" and destino.exists()
        assert proyecto.autoguardado_pendiente(ruta) == destino
        proyecto.borrar_autoguardado(doc)
        assert proyecto.autoguardado_pendiente(ruta) is None
    finally:
        doc.ruta = None
