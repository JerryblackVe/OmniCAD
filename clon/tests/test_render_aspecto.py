# -*- coding: utf-8 -*-
"""Aspecto en el espacio RENDERIZAR: el mismo panel y la misma biblioteca que en Diseño, todo lo que se aplica pasa por
`timeline/aspectos_doc.py` (un paso de deshacer, entra en «En este diseño»), «Aplicar a: Caras» y la vista previa de lo
que se edita sin escribirlo."""
import os
import sys

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad import api
from omnicad.api import selectores as sl
from omnicad.nucleo import aspectos as asp
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import render_cpu as rc
from omnicad.timeline import aspectos_doc as ad

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QToolButton

ROJO = "Pintura - Brillante (Rojo)"


@pytest.fixture(autouse=True)
def usuario(tmp_path, monkeypatch):
    monkeypatch.setenv("OMNICAD_ASPECTOS", str(tmp_path / "aspectos.json"))


@pytest.fixture(scope="module")
def app_qt():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def vr(app_qt):
    """(ventana de Render, sesión, id del cuerpo con la caja)."""
    from omnicad.ui.render import VentanaRender
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 100, "width": 60, "height": 20})["ok"]
    assert api.llamar(s, "create_cylinder", {"height": 30, "radius": 10, "x": 90})["ok"]
    v = VentanaRender(s.doc)
    v.lienzo.resize(640, 480)
    v.lienzo.encuadrar()
    yield v, s, list(s.doc.estado_final.cuerpos)[0]
    s.doc.modificado = False
    v.close()


def _cara_superior(s, cid):
    (c, e), = sl.elegir(s, ">Z", "cara", cid)
    return sl.referencia(c, e)


@pytest.mark.parametrize("clave", ["aspecto", "escena"])
def test_paneles_de_render_abren_con_clic_y_se_reubican_sin_error(vr, monkeypatch, clave):
    v, _s, _cid = vr
    errores = []
    monkeypatch.setattr(sys, "excepthook", lambda *args: errores.append(args))
    v.show()
    QTest.qWait(10)
    boton = next(b for b in v.cinta.findChildren(QToolButton) if b.defaultAction() is v.acciones[clave])
    QTest.mouseClick(boton, Qt.LeftButton)
    assert errores == []
    panel = v.panel_aspecto if clave == "aspecto" else v.panel_escena
    assert v.area.panel is panel and panel.isVisible()
    v.resize(1024, 640)
    QTest.qWait(10)
    assert errores == [] and panel.isVisible()
    assert panel.parent() is v.area and panel.x() < v.area.width()


def test_aplicar_en_render_pasa_por_aspectos_del_diseno(vr):
    v, s, cid = vr
    doc = s.doc
    assert v.aplicar_aspecto("Latón - Pulido", [cid])
    lista = ad.lista(doc)
    assert [a["nombre"] for a in lista] == ["Latón - Pulido"]                  # entró en «En este diseño»
    assert doc.propiedades[cid]["aspecto"] == lista[0]["id"]
    assert v.panel_aspecto.aspectos.diseno == lista and not v.panel_aspecto.pendiente()
    assert v.lienzo.objetos[cid]["acabado"]["nombre"] == "Latón - Pulido"
    otro = list(doc.estado_final.cuerpos)[1]
    assert v.aplicar_aspecto("Latón - Pulido", [otro])
    assert len(ad.lista(doc)) == 1 and ad.usos(doc, lista[0]["id"])[0] == [cid, otro]    # se reusa, no se duplica
    doc.deshacer()                                                              # UN paso por aplicar
    assert ad.usos(doc, lista[0]["id"])[0] == [cid]
    doc.deshacer()
    assert not ad.lista(doc) and cid not in doc.propiedades
    v.actualizar()
    assert v.panel_aspecto.aspectos.diseno == [] and v.lienzo.objetos[cid]["acabado"]["nombre"] == rc.ASPECTO_DEFECTO


def test_aplicar_acepta_el_aspecto_como_dict_o_nombre_de_mis_aspectos(vr):
    v, s, cid = vr
    mio = asp.agregar_mio(dict(asp.buscar("Acero - Pulido"), nombre="Mi acero"))
    assert v.aplicar_aspecto("mi acero", [cid])
    assert ad.lista(s.doc)[0]["origen"] == "mis" and s.doc.propiedades[cid]["acabado"]["nombre"] == "Mi acero"
    aid = ad.lista(s.doc)[0]["id"]
    v.panel_aspecto.aspectos.cambiar(aid, {"aspereza": 0.77})                   # editado en el panel, sin escribir
    assert v.aplicar_aspecto("Mi acero", [cid]) and len(ad.lista(s.doc)) == 1    # por nombre usa lo editado: no suma otro
    assert ad.lista(s.doc)[0]["aspereza"] == 0.77
    assert not v.aplicar_aspecto("No existe", [cid])
    assert not v.aplicar_aspecto(mio, [])                                      # sin destino no aplica nada
    assert len(ad.lista(s.doc)) == 1


def test_aplicar_a_caras_se_ve_en_el_lienzo_y_se_puede_quitar(vr):
    v, s, cid = vr
    doc = s.doc
    ref = _cara_superior(s, cid)
    entero = len(v.lienzo.triangulos_cuerpo(cid))
    assert v.aplicar_aspecto(ROJO, caras=[(cid, ref)])
    cara_doc, = doc.propiedades[cid]["caras"]
    assert cara_doc["aspecto"] == ad.lista(doc)[0]["id"] and "apariencia" not in doc.propiedades[cid]
    mallas = [m for m in v.lienzo._mallas if m["id"] == cid]
    assert len(mallas) == 2 and sum(len(m["v"]) for m in mallas) == entero == len(v.lienzo.triangulos_cuerpo(cid))
    pintada = min(mallas, key=lambda m: len(m["v"]))
    assert list(pintada["color"]) == pytest.approx(asp.BIBLIOTECA[ROJO]["color"])
    assert np.allclose(pintada["v"][:, 2], pintada["v"][0, 2])                  # la cara superior, plana
    assert sum(1 for o in v.lienzo.objetos_render()) == 3                       # resto + cara + el cilindro
    doc.deshacer()
    v.actualizar()
    assert len([m for m in v.lienzo._mallas if m["id"] == cid]) == 1
    v.aplicar_aspecto(ROJO, caras=[(cid, ref)])
    v.quitar_aspecto(caras=[(cid, ref)])
    assert "caras" not in doc.propiedades.get(cid, {}) and len([m for m in v.lienzo._mallas if m["id"] == cid]) == 1


def test_elegir_una_cara_con_el_panel_en_modo_caras(vr):
    v, s, cid = vr
    v.mostrar_aspecto()
    assert v.lienzo.filtro == {"cuerpo"}
    v.panel_aspecto.radios.r_caras.setChecked(True)
    assert v.lienzo.filtro == {"cara"} and v.panel_aspecto.modo() == "caras"
    ref = _cara_superior(s, cid)
    cara = ad.cara_de(s.doc.estado_final, ref)
    centro = geo.teselar(cara)[0].mean(axis=0)
    hit = v.lienzo.elegir_entidad(v.lienzo.proyectar(centro).toPoint())
    assert hit["tipo"] == "cara" and hit["cuerpo"] == cid and ad.cara_de(s.doc.estado_final, hit["ref"]).IsSame(cara)
    v._clic_cuerpo(hit)                                                         # sin aspecto elegido: la elige
    assert [x[:2] for x in v.caras_elegidas] == [(cid, hit["ref"])]
    v._clic_cuerpo(hit)
    assert [x[:2] for x in v.caras_elegidas] == [(cid, hit["ref"])]            # sin Ctrl no la alterna
    v.panel_aspecto._seleccionar(ROJO)
    assert v.panel_aspecto.elegido() == ROJO
    v.panel_aspecto.b_aplicar.click()                                           # «Aplicar a la selección»
    assert len(s.doc.propiedades[cid]["caras"]) == 1
    v.panel_aspecto.cerrar()
    assert v.lienzo.filtro == {"cuerpo"}
    v.seleccionar([cid])
    v.mostrar_escena()
    v.panel_escena.cerrar()
    assert v.seleccion == [cid]                                                 # cerrar otro panel no suelta lo elegido


def test_lo_editado_se_ve_sin_escribir_y_se_escribe_al_salir(vr):
    v, s, cid = vr
    doc = s.doc
    v.aplicar_aspecto("Latón - Pulido", [cid])
    aid = ad.lista(doc)[0]["id"]
    original = ad.lista(doc)[0]["color"]
    v.panel_aspecto.aspectos.cambiar(aid, {"color": [0.1, 0.2, 0.9]})          # como el selector rápido
    assert v.panel_aspecto.pendiente()
    assert v.lienzo.objetos[cid]["color"] == pytest.approx([0.1, 0.2, 0.9])    # se ve al instante
    assert ad.lista(doc)[0]["color"] == original and doc.propiedades[cid]["apariencia"] != [0.1, 0.2, 0.9]
    v.close()                                                                   # al salir se escribe, en un paso
    assert ad.lista(doc)[0]["color"] == [0.1, 0.2, 0.9] and doc.propiedades[cid]["apariencia"] == [0.1, 0.2, 0.9]
    doc.deshacer()
    assert ad.lista(doc)[0]["color"] == original and doc.propiedades[cid]["apariencia"] == original


def test_cerrar_el_panel_escribe_lo_editado_y_otro_cambio_descarta_lo_pendiente(vr):
    v, s, cid = vr
    doc = s.doc
    v.aplicar_aspecto("Latón - Pulido", [cid])
    aid = ad.lista(doc)[0]["id"]
    v.mostrar_aspecto()
    v.panel_aspecto.aspectos.cambiar(aid, {"aspereza": 0.9})
    v.panel_aspecto.cerrar()
    assert ad.lista(doc)[0]["aspereza"] == 0.9 and not v.panel_aspecto.pendiente()
    v.panel_aspecto.aspectos.cambiar(aid, {"aspereza": 0.3})
    doc.deshacer()                                                              # cambió por otro lado: lo pendiente ya no vale
    v.actualizar()
    assert not v.panel_aspecto.pendiente() and v.panel_aspecto.aspectos.diseno == ad.lista(doc)


def test_nuevo_en_el_panel_se_escribe_con_su_id_al_aplicar(vr):
    v, s, cid = vr
    v.aplicar_aspecto("Latón - Pulido", [cid])
    copia = v.panel_aspecto.aspectos.duplicar(ad.lista(s.doc)[0]["id"])       # «Duplicar» del menú de «En este diseño»
    assert copia["id"].startswith("nuevo") and v.panel_aspecto.pendiente()
    v.panel_aspecto.aspectos.elegir(copia["id"])
    assert v.aplicar_aspecto(v.panel_aspecto.aspectos.elegido, [cid])
    lista = ad.lista(s.doc)
    assert [a["id"] for a in lista] == ["asp1", "asp2"] and s.doc.propiedades[cid]["aspecto"] == "asp2"
    assert v.panel_aspecto.aspectos.elegido["id"] == "asp2" and v.panel_aspecto.aspectos.diseno == lista


def test_el_panel_usa_la_misma_biblioteca_que_diseno(vr):
    from omnicad.ui.aspectos_ui import PanelAspectos
    v, _s, _cid = vr
    w = v.panel_aspecto.aspectos
    assert type(w) is PanelAspectos and w.pestanas.count() == 3
    hojas = sum(w.arbol.topLevelItem(i).childCount() for i in range(w.arbol.topLevelItemCount()))
    assert hojas == len(asp.BIBLIOTECA) > 45
    assert w.arbol.topLevelItemCount() == len(asp.categorias_con_aspectos(asp.BIBLIOTECA))


def test_propiedades_con_es_una_vista_previa_que_no_toca_el_documento(vr):
    v, s, cid = vr
    doc = s.doc
    v.aplicar_aspecto("Latón - Pulido", [cid])
    lista = ad.lista(doc)
    assert ad.propiedades_con(doc, lista) is doc.propiedades
    lista[0]["color"] = [0.0, 1.0, 0.0]
    previa = ad.propiedades_con(doc, lista)
    assert previa is not doc.propiedades and previa[cid]["apariencia"] == [0.0, 1.0, 0.0]
    assert doc.propiedades[cid]["apariencia"] != [0.0, 1.0, 0.0]


def test_malla_suave_aparte_parte_la_malla_sin_perder_triangulos():
    forma = geo.caja(10, 10, 10)
    v, n = rc.malla_suave(forma, 0.05)
    arriba = max(geo.caras(forma), key=lambda c: geo.teselar(c)[0][:, 2].mean())
    resto_v, resto_n, partes = rc.malla_suave_aparte(forma, [arriba])
    (cv, cn), = partes
    assert len(resto_v) + len(cv) == len(v) and len(resto_n) + len(cn) == len(n) and len(cv) == 6
    assert np.allclose(cv[:, 2], cv[0, 2]) and np.allclose(cn, [0, 0, 1])
    assert rc.malla_suave_aparte(forma, [])[2] == [] and len(rc.malla_suave_aparte(forma, [])[0]) == len(v)


def test_la_imagen_de_las_herramientas_dibuja_cada_cara_con_su_aspecto(vr):
    from omnicad.api.herramientas_inspeccion import _objetos_render
    _v, s, cid = vr
    cuerpos = list(s.doc.estado_final.cuerpos.values())
    assert len(_objetos_render(s, cuerpos)) == 2
    ad.asignar(s.doc, asp.buscar(ROJO), [], [(cid, _cara_superior(s, cid))])
    objetos = _objetos_render(s, cuerpos)
    assert len(objetos) == 3
    rojos = [o for o in objetos if list(o["color"]) == pytest.approx(asp.BIBLIOTECA[ROJO]["color"])]
    assert len(rojos) == 1 and len(rojos[0]["v"]) < 12
    assert api.llamar(s, "get_viewport_image", {"width": 48, "height": 36})["ok"]
