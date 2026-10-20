# -*- coding: utf-8 -*-
"""Guardar como malla: controles compartidos por archivo, agentes e interfaz."""
import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialogButtonBox

from omnicad import api
from omnicad.io_archivos import exportar as ex
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import malla
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva
from omnicad.ui.guardar_malla import DialogoGuardarMalla


def _cuerpo(forma=None, nombre="Pieza", identificador="c1"):
    return SimpleNamespace(forma=geo.caja(10, 20, 30) if forma is None else forma,
                           nombre=nombre, id=identificador)


def _extension(formato):
    return "stl" if formato.startswith("stl_") else formato


@pytest.mark.parametrize("formato", ex.FORMATOS_MALLA)
def test_formatos_ida_y_vuelta(tmp_path, formato):
    c = _cuerpo()
    ruta = tmp_path / f"pieza.{_extension(formato)}"
    n = ex.exportar_malla([c], ruta, formato=formato)
    leida = malla.leer(ruta)
    assert n == len(leida.caras) == 12
    assert leida.es_cerrada() and leida.volumen() == pytest.approx(6000)
    assert geo.es_valida(c.forma) and geo.volumen(c.forma) == pytest.approx(6000)
    if formato == "stl_ascii":
        assert ruta.read_bytes().startswith(b"solid")
    if formato == "stl_binario":
        assert len(ruta.read_bytes()) == 84 + 50 * n


@pytest.mark.parametrize("formato", ex.FORMATOS_MALLA)
@pytest.mark.parametrize("unidad,factor", [("mm", 1), ("cm", 0.1), ("m", 0.001),
                                           ("in", 1 / 25.4), ("ft", 1 / 304.8)])
def test_unidades_escalan_coordenadas_y_3mf_declara_unidad(tmp_path, formato, unidad, factor):
    ruta = tmp_path / f"pieza.{_extension(formato)}"
    ex.exportar_malla([_cuerpo()], ruta, formato=formato, unidades=unidad)
    # Forzar mm en el lector deja ver las coordenadas numéricas del archivo, también en 3MF.
    leida = malla.leer(ruta, unidades="mm")
    assert np.subtract(*leida.caja()[::-1]) == pytest.approx(np.array([10, 20, 30]) * factor, rel=1e-6)
    if formato == "3mf":
        assert malla.leer(ruta).volumen() == pytest.approx(6000)


@pytest.mark.parametrize("formato", ex.FORMATOS_MALLA)
def test_uno_por_cuerpo_nombres_seguros_y_sin_colisiones(tmp_path, formato):
    cuerpos = [_cuerpo(nombre="../Pieza:1"), _cuerpo(geo.caja(2, 3, 4), "../Pieza:1", "c2")]
    ruta = tmp_path / f"modelo.{_extension(formato)}"
    n = ex.exportar_malla(cuerpos, ruta, formato=formato, estructura="uno_por_cuerpo")
    rutas = ex.rutas_malla(cuerpos, ruta, formato=formato, estructura="uno_por_cuerpo")
    assert n == 24 and len(set(rutas)) == 2 and not ruta.exists()
    assert all(p.parent == tmp_path and p.is_file() for p in rutas)
    assert [malla.leer(p).volumen() for p in rutas] == pytest.approx([6000, 24])
    rutas[0].unlink()
    anterior = rutas[1].read_bytes()
    with pytest.raises(FileExistsError):
        ex.exportar_malla(cuerpos, ruta, formato=formato, estructura="uno_por_cuerpo", sobrescribir=False)
    assert not rutas[0].exists() and rutas[1].read_bytes() == anterior


def test_un_archivo_3mf_y_obj_conserva_cuerpos(tmp_path):
    cuerpos = [_cuerpo(), _cuerpo(geo.caja(2, 3, 4, (40, 0, 0)), identificador="c2")]
    for ext in ("3mf", "obj"):
        ruta = tmp_path / f"dos.{ext}"
        assert ex.exportar_malla(cuerpos, ruta) == 24
        leida = malla.leer(ruta)
        assert len(np.unique(leida.grupos)) == 2
        assert leida.es_cerrada() and leida.volumen() == pytest.approx(6024)


def test_refinado_alto_supera_bajo_sin_reutilizar_malla_del_visor(tmp_path):
    c = _cuerpo(geo.esfera(10))
    visor, _ = geo.teselar(c.forma, 0.05)
    alto = ex.exportar_malla([c], tmp_path / "alto.stl", refinamiento="alto")
    bajo = ex.exportar_malla([c], tmp_path / "bajo.stl", refinamiento="bajo")
    assert alto > bajo > 12
    assert bajo == ex.exportar_malla([_cuerpo(geo.esfera(10))], tmp_path / "sin_visor.stl", refinamiento="bajo")
    assert len(geo.teselar(c.forma, 0.05)[0]) == len(visor)
    assert geo.es_valida(c.forma)
    assert geo.volumen(c.forma) == pytest.approx(4 / 3 * math.pi * 1000)


def test_personalizado_desviacion_y_angulo(tmp_path):
    c = _cuerpo(geo.esfera(10))
    gruesa = ex.exportar_malla([c], tmp_path / "gruesa.stl", desviacion=1, angulo=40)
    fina = ex.exportar_malla([c], tmp_path / "fina.stl", desviacion=0.01, angulo=8)
    assert fina > gruesa


@pytest.mark.parametrize("longitud,aspecto", [(2, 0), (0, 3), (2, 3)])
def test_arista_y_aspecto_en_brep_y_malla_sin_perder_volumen(longitud, aspecto):
    forma = geo.caja(8, 2, 2)
    base = malla.desde_brep(forma)
    refinada = malla.desde_brep(forma, longitud_maxima=longitud, relacion_aspecto=aspecto)
    otra = ex.preparar_mallas([_cuerpo(base)], longitud_maxima=longitud, relacion_aspecto=aspecto)[0]
    for m in (refinada, otra):
        t = m.triangulos()
        mayor = np.linalg.norm(t[:, [1, 2, 0]] - t, axis=2).max(1)
        if longitud:
            assert mayor.max() <= longitud * (1 + 1e-12)
        if aspecto:
            assert np.max(mayor ** 2 / (2 * m.areas_caras())) <= aspecto * (1 + 1e-12)
        assert m.es_cerrada() and m.volumen() == pytest.approx(32)
    assert geo.es_valida(forma) and geo.volumen(forma) == pytest.approx(32)
    assert len(base.caras) == 12


@pytest.mark.parametrize("opciones", [{"desviacion": 0}, {"desviacion": float("nan")}, {"angulo": 180},
                                       {"longitud_maxima": -1}, {"longitud_maxima": float("inf")},
                                       {"relacion_aspecto": 1}, {"relacion_aspecto": float("nan")}])
def test_controles_invalidos_no_escriben(tmp_path, opciones):
    ruta = tmp_path / "no.stl"
    with pytest.raises(geo.ErrorGeometria):
        ex.exportar_malla([_cuerpo()], ruta, **opciones)
    assert not ruta.exists()


def test_limites_excesivos_fallan_sin_escribir(tmp_path, monkeypatch):
    monkeypatch.setattr(malla, "TRIANGULOS_MAXIMOS_REMALLADO", 20)
    with pytest.raises(geo.ErrorGeometria, match="triángulos"):
        ex.exportar_malla([_cuerpo()], tmp_path / "no.stl", longitud_maxima=0.01)
    assert not (tmp_path / "no.stl").exists()


def _sesion():
    doc = Documento()
    for x in (0, 20):
        r = doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="8", largo="2", alto="2", x=str(x)))
        assert r.estado == "ok"
    return api.Sesion(doc)


def test_api_con_todos_los_parametros_y_proteccion_de_destinos(tmp_path):
    sesion = _sesion()
    args = dict(path=str(tmp_path / "subcarpeta" / "modelo.stl"), bodies=["op1.c1", "op2.c1"],
                format="stl_ascii", units="cm", structure="uno_por_cuerpo", refinement="personalizado",
                surface_deviation=0.03, normal_deviation=15, maximum_edge_length=2, aspect_ratio=3,
                overwrite=False, create_folders=True)
    r = api.llamar(sesion, "export_mesh", args)
    assert r["ok"], r
    resultado = r["result"]
    assert len(resultado["paths"]) == 2 and resultado["triangles"] > 24 and resultado["units"] == "cm"
    for p in resultado["paths"]:
        assert Path(p).read_bytes().startswith(b"solid")
        assert malla.leer(p).volumen() == pytest.approx(0.032)
    assert api.llamar(sesion, "export_mesh", args)["error_kind"] == "FILE_EXISTS"
    assert api.llamar(sesion, "export_mesh", dict(args, overwrite=True))["ok"]
    assert api.llamar(sesion, "export_mesh", dict(args, path=str(tmp_path / "no" / "m.stl"),
                                               create_folders=False))["error_kind"] == "FILE_NOT_FOUND"
    esquema = next(h["esquema"] for h in api.catalogo() if h["nombre"] == "export_mesh")
    assert set(args) == set(esquema["properties"])
    assert all(p.get("description") for p in esquema["properties"].values())


@pytest.mark.parametrize("formato", ex.FORMATOS_MALLA)
def test_api_todos_los_formatos(tmp_path, formato):
    ruta = tmp_path / f"modelo.{_extension(formato)}"
    r = api.llamar(_sesion(), "export_mesh", {"path": str(ruta), "format": formato, "refinement": "alto"})
    assert r["ok"], r
    assert len(malla.leer(ruta).caras) == r["result"]["triangles"]


def test_dialogo_recuento_cambia_con_refinado_y_seleccion():
    app = QApplication.instance() or QApplication([])
    caja = DialogoGuardarMalla([_cuerpo(geo.esfera(10)), _cuerpo(identificador="c2")], ["c1"])
    caja.show()
    assert caja.windowTitle() == "Guardar como malla" and caja.triangulos > 0
    assert str(caja.triangulos) in caja.recuento.text()
    assert len(caja.campos) == 4 and caja.formato.count() == 4 and caja.unidad.count() == 5
    caja.refinamiento.setCurrentIndex(caja.refinamiento.findData("bajo"))
    QTest.qWait(250)
    bajo = caja.triangulos
    assert not caja.personalizado.isEnabled() and bajo > 0
    caja.refinamiento.setCurrentIndex(caja.refinamiento.findData("alto"))
    QTest.qWait(250)
    assert caja.triangulos > bajo and str(caja.triangulos) in caja.recuento.text()
    alto = caja.triangulos
    caja.objetos.item(1).setCheckState(Qt.Checked)
    QTest.qWait(250)
    assert caja.triangulos == alto + 12
    caja.objetos.item(0).setCheckState(Qt.Unchecked)
    caja.objetos.item(1).setCheckState(Qt.Unchecked)
    QTest.qWait(250)
    assert caja.triangulos == 0 and not caja.botones.button(QDialogButtonBox.Ok).isEnabled()
    caja.close()
    app.processEvents()
