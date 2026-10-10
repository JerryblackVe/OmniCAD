# -*- coding: utf-8 -*-
import json
import math
import struct
import zipfile

import pytest
from OCP.BRep import BRep_Tool
from OCP.TopLoc import TopLoc_Location

from omnicad.ejemplo import crear_documento_ejemplo
from omnicad.io_archivos import exportar as ex
from omnicad.io_archivos import proyecto
from omnicad.nucleo import geometria as g
from omnicad.nucleo import intercambio
from omnicad.restricciones import Boceto
from omnicad.timeline import documento
from omnicad.timeline.documento import Documento, ErrorDocumento
from omnicad.timeline.operaciones import ErrorOperacion, OpBoceto, OpCombinar, OpImportarSTEP, OpPrimitiva


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


def test_glb_y_gltf_del_ejemplo(doc, tmp_path):
    """Archivo › Exportar › glTF: un nodo por cuerpo bajo la raíz (Y arriba), en metros y con un material por aspecto."""
    cuerpos = list(doc.estado_final.cuerpos.values())
    n = ex.exportar(cuerpos, tmp_path / "m.glb", doc.propiedades)
    datos = (tmp_path / "m.glb").read_bytes()
    assert datos[:4] == b"glTF" and struct.unpack_from("<I", datos, 8)[0] == len(datos)
    largo = struct.unpack_from("<I", datos, 12)[0]
    js = json.loads(datos[20:20 + largo])
    assert len(js["nodes"]) == len(cuerpos) + 1 and js["nodes"][0]["children"] == list(range(1, len(cuerpos) + 1))
    indices = [js["accessors"][m["primitives"][0]["indices"]]["count"] for m in js["meshes"]]
    assert sum(indices) == 3 * n and n > 1000
    caja = [(a["min"], a["max"]) for m in js["meshes"] for a in [js["accessors"][m["primitives"][0]["attributes"]["POSITION"]]]]
    for (mn, mx), c in zip(caja, cuerpos, strict=True):           # posiciones en metros: la caja del sólido / 1000
        (a, b) = g.caja_envolvente(c.forma)
        assert mn == pytest.approx([x / 1000 for x in a], abs=5e-5) and mx == pytest.approx([x / 1000 for x in b], abs=5e-5)
    assert ex.exportar(cuerpos, tmp_path / "m.gltf", doc.propiedades) == n
    assert json.loads((tmp_path / "m.gltf").read_text(encoding="utf-8"))["buffers"][0]["uri"].startswith("data:")


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


# ---------------------------------------------------------------- caché de pasos lentos (abrir sin recalcular)
_VOLUMEN_LENTO = 40 * 30 * 10 - math.pi * 4 ** 2 * 10 + 5 * 5 * 10


def _doc_lento():
    """Placa (ancho = parámetro), agujero cortado en automático, boceto, taco y Combinar › Unir. Con
    _SEGUNDOS_CACHE = 0 van a la caché todos los pasos que solo cambian cuerpos; el boceto no (cambia bocetos)."""
    doc = Documento()
    doc.parametros.agregar("ancho", "40 mm")
    doc.agregar(OpPrimitiva(doc.nuevo_id(), "Placa", forma="caja", ancho="ancho", largo="30 mm", alto="10 mm"))
    doc.agregar(OpPrimitiva(doc.nuevo_id(), "Agujero", forma="cilindro", radio="4 mm", alto="30 mm", x="20 mm",
                            y="15 mm", z="-10 mm", operacion="cortar"))
    b = Boceto()
    b.agregar_punto(5, 5)
    doc.agregar(OpBoceto(doc.nuevo_id(), plano="XY", boceto=b))
    doc.agregar(OpPrimitiva(doc.nuevo_id(), "Taco", forma="caja", ancho="5 mm", largo="5 mm", alto="20 mm", x="35 mm"))
    doc.agregar(OpCombinar(doc.nuevo_id(), objetivo="op1.c1", herramientas=["op4.c1"], operacion="unir"))
    assert [r.estado for r in doc.resultados] == ["ok"] * 5
    return doc


def _pasos_en_cache(ruta):
    with zipfile.ZipFile(ruta) as z:
        if "cache/pasos.json" not in z.namelist():
            return None
        return [p["op"] for p in json.loads(z.read("cache/pasos.json"))["pasos"]]


def _no_recalcular(monkeypatch):
    """Si abrir ejecuta una primitiva o un combinar, el paso da error: así se ve que salió de la caché."""
    def falla(self, estado, ctx):
        raise ErrorOperacion("se recalculó un paso que estaba en la caché")
    monkeypatch.setattr(OpPrimitiva, "ejecutar", falla)
    monkeypatch.setattr(OpCombinar, "ejecutar", falla)


def test_abrir_toma_los_pasos_lentos_de_la_cache_sin_recalcularlos(tmp_path, monkeypatch):
    """Antes abrir recalculaba el timeline entero aunque guardara cache/cuerpos.brep (una caja con roscas modeladas:
    4,6 s guardando y 4,6 s abriendo). Ahora los pasos lentos salen de la caché: mismos cuerpos, resultados,
    parámetros leídos y dependencias; el boceto (que no va a la caché) se calcula como siempre."""
    monkeypatch.setattr(documento, "_SEGUNDOS_CACHE", 0)
    doc = _doc_lento()
    ruta = proyecto.guardar(doc, tmp_path / "lento")
    assert _pasos_en_cache(ruta) == ["op1", "op2", "op4", "op5"]
    with monkeypatch.context() as m:
        _no_recalcular(m)
        abierto = proyecto.abrir(ruta)
        assert [(r.estado, r.mensaje) for r in abierto.resultados] == [("ok", "")] * 5
        assert list(abierto.estado_final.cuerpos) == ["op1.c1"]
        cuerpo = abierto.estado_final.cuerpos["op1.c1"]
        assert g.es_valida(cuerpo.forma) and cuerpo.nombre == doc.estado_final.cuerpos["op1.c1"].nombre
        assert g.volumen(cuerpo.forma) == pytest.approx(_VOLUMEN_LENTO, rel=1e-9)
        assert [list(abierto.estado_en(i).cuerpos) for i in range(6)] == [list(doc.estado_en(i).cuerpos) for i in range(6)]
        assert list(abierto.estado_final.bocetos) == ["op3"]
        assert abierto._usados == doc._usados and abierto._usados[0] == {"ancho"}
        assert [o.dependencias() for o in abierto.operaciones] == [o.dependencias() for o in doc.operaciones]
        assert abierto.operacion("op2").dependencias() == {"op1"}   # cortó en automático: lo anotó al ejecutarse
        with pytest.raises(ErrorDocumento):
            abierto.eliminar("op1")
        assert abierto._cache == {} and abierto.modificado is False
        # volver a guardar lo abierto conserva la caché
        assert _pasos_en_cache(proyecto.guardar(abierto, tmp_path / "otra")) == ["op1", "op2", "op4", "op5"]
    # editar después de abrir recalcula desde el paso editado
    r = abierto.reemplazar("op4", OpPrimitiva("op4", "Taco", forma="caja", ancho="5 mm", largo="5 mm", alto="30 mm",
                                              x="35 mm"))
    assert r.estado == "ok" and abierto.resultados[4].estado == "ok"
    assert g.volumen(abierto.estado_final.cuerpos["op1.c1"].forma) == pytest.approx(_VOLUMEN_LENTO + 250, rel=1e-9)


def test_la_cache_de_otra_receta_o_danada_se_ignora(tmp_path, monkeypatch):
    """Receta editada a mano (la huella no coincide) o BREP roto: se recalcula todo y vale la receta."""
    monkeypatch.setattr(documento, "_SEGUNDOS_CACHE", 0)
    ruta = proyecto.guardar(_doc_lento(), tmp_path / "lento")
    with zipfile.ZipFile(ruta) as z:
        entradas = {n: z.read(n) for n in z.namelist()}
    receta = json.loads(entradas["receta.json"])
    receta["parametros"][0]["expresion"] = "50 mm"
    casos = {"editada": dict(entradas, **{"receta.json": json.dumps(receta).encode()}),
             "brep_roto": dict(entradas, **{"cache/cuerpos.brep": b"no soy un BREP"})}
    volumenes = {"editada": _VOLUMEN_LENTO + 10 * 30 * 10, "brep_roto": _VOLUMEN_LENTO}
    for caso, contenido in casos.items():
        otra = tmp_path / f"{caso}.omnicad"
        with zipfile.ZipFile(otra, "w") as z:
            for n, datos in contenido.items():
                z.writestr(n, datos)
        abierto = proyecto.abrir(otra)
        assert [r.estado for r in abierto.resultados] == ["ok"] * 5, caso
        assert g.volumen(abierto.estado_final.cuerpos["op1.c1"].forma) == pytest.approx(volumenes[caso], rel=1e-9), caso


def test_la_cache_brep_no_guarda_la_malla_del_visor(tmp_path, monkeypatch):
    """El visor malla cada cara para dibujarla y OCC guardaba esa malla en cache/cuerpos.brep (el doble de tamaño). El
    visor la rehace siempre: el BREP ya no la lleva, y la geometría sigue igual."""
    monkeypatch.setattr(documento, "_SEGUNDOS_CACHE", math.inf)     # en el BREP, solo los cuerpos finales
    doc = crear_documento_ejemplo()
    for c in doc.estado_final.cuerpos.values():
        assert len(g.teselar(c.forma)[0]) > 0
    ruta = proyecto.guardar(doc, tmp_path / "mallado")
    with zipfile.ZipFile(ruta) as z:
        z.extract("cache/cuerpos.brep", tmp_path)
    partes = intercambio.partes_de_brep(tmp_path / "cache" / "cuerpos.brep")
    assert len(partes) == len(doc.estado_final.cuerpos)
    for parte, c in zip(partes, doc.estado_final.cuerpos.values(), strict=True):
        assert g.es_valida(parte) and g.volumen(parte) == pytest.approx(g.volumen(c.forma), rel=1e-9)
        assert all(BRep_Tool.Triangulation_s(cara, TopLoc_Location()) is None for cara in g.caras(parte))


def test_guardar_y_abrir_con_un_cuerpo_de_malla(tmp_path):
    """Antes guardar con un cuerpo de malla (Teselar) fallaba con TypeError armando cache/cuerpos.brep."""
    from omnicad.timeline.operaciones import operacion_desde_dict
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), "Caja", forma="caja", ancho="10 mm", largo="10 mm", alto="10 mm"))
    doc.agregar(operacion_desde_dict({"tipo": "teselar", "id": doc.nuevo_id(),
                                      "params": {"cuerpos": ["op1.c1"], "mantener": True}}))
    assert [r.estado for r in doc.resultados] == ["ok", "ok"]
    assert any(getattr(c, "tipo", "") == "malla" for c in doc.estado_final.cuerpos.values())
    abierto = proyecto.abrir(proyecto.guardar(doc, tmp_path / "malla"))
    assert [r.estado for r in abierto.resultados] == ["ok", "ok"]
    assert len(abierto.estado_final.cuerpos) == len(doc.estado_final.cuerpos)
