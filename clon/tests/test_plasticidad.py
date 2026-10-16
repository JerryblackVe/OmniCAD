# -*- coding: utf-8 -*-
"""PL4 (Plasticity › «Fillet Order of Operations»): el error de empalme enseña el orden correcto
(de lo grande a lo chico) y move_feature deja reordenar los pasos para seguir la pista."""
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo.solidos_modificar import empalme
from omnicad.timeline.operaciones import OpPrimitiva


def _caja(doc):
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="40", largo="40", alto="20"))
    return doc.estado_final.cuerpos["c1"].forma


def test_el_empalme_imposible_ensenia_el_orden_de_lo_grande_a_lo_chico():
    from omnicad.nucleo import referencias as refs
    caja = geo.caja(40, 40, 20)
    aristas = refs.subformas(caja, "arista")[:4]
    with pytest.raises(geo.ErrorGeometria) as e:
        empalme(caja, [{"aristas": aristas, "tipo": "constante", "radio": 500.0}])
    assert "radio MAYOR" in str(e.value) and "de lo grande a lo chico" in str(e.value)
    assert "reordená los empalmes" in str(e.value)


def test_la_pista_llega_por_la_api_y_move_feature_reordena():
    sesion = api.Sesion()
    doc = sesion.doc
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="40", largo="40", alto="20"))
    r = api.llamar(sesion, "fillet", {"edges": "|Z", "radius": 500})
    assert not r["ok"] and "de lo grande a lo chico" in r["mensaje"]

    # move_feature (la herramienta nueva que hace la pista accionable): el primitivo pasa al final.
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="esfera", radio="5"))
    r = api.llamar(sesion, "move_feature", {"feature": "op1", "index": 1})
    assert r["ok"] and r["result"]["before"] == 0 and r["result"]["now"] == 1
    assert doc.operaciones[0].TIPO == "primitiva" and "op1" != doc.operaciones[0].id
    r = api.llamar(sesion, "move_feature", {"feature": "no-hay", "index": 0})
    assert not r["ok"] and r["error_kind"] == "FEATURE_NOT_FOUND"


# ---------------------------------------------------------------- PL2: teclas a la vista
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="module")
def ventana(tmp_path_factory):
    QApplication.instance() or QApplication([])
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    ruta = tmp_path_factory.mktemp("prefs") / "preferencias.ini"
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(ruta), QSettings.IniFormat)))
    v.show()
    QTest.qWait(50)
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    QTest.qWait(10)


def test_shift_r_repite_el_ultimo_comando(ventana, monkeypatch):
    from omnicad.ui.comandos import CATALOGO
    assert ventana.acciones["repetir"].shortcut().toString().endswith("R")
    ventana._ultimo_comando = CATALOGO["caja"]
    llamados = []
    monkeypatch.setattr(ventana, "ejecutar_comando", lambda comando: llamados.append(comando))
    ventana.repetir_ultimo()
    assert len(llamados) == 1 and isinstance(llamados[0], CATALOGO["caja"])
    ventana._ultimo_comando = None
    ventana.repetir_ultimo()                       # sin último comando no hace nada ni revienta
    assert len(llamados) == 1


def test_el_panel_del_comando_muestra_las_teclas_al_pie(ventana, monkeypatch):
    from omnicad.ui.comandos import CATALOGO
    panel = ventana.ejecutar_comando(CATALOGO["caja"]())
    assert panel is not None
    QTest.qWait(20)
    texto = panel.pie_teclas.text()
    assert "Enter: aceptar" in texto and "Esc: cancelar" in texto
    # un comando con teclas propias las muestra primero
    monkeypatch.setattr(CATALOGO["caja"], "MODIFICADORES", {"Mayús": "centrado"})
    panel2 = ventana.ejecutar_comando(CATALOGO["caja"]())
    QTest.qWait(20)
    assert "Mayús: centrado" in panel2.pie_teclas.text()
    panel2.cancelar()
    monkeypatch.setattr(CATALOGO["caja"], "MODIFICADORES", {})   # panel 1 ya lo cerró ejecutar_comando


# ---------------------------------------------------------------- PL3: boceto sobre la cara con Espacio
def test_espacio_arranca_el_boceto_sobre_la_cara_ya_elegida(ventana):
    from omnicad.nucleo import geometria as geo
    assert ventana.acciones["boceto_cara"].shortcut().toString() == "Space"
    ventana.seleccion = [{"tipo": "cara", "plano": geo.Plano("XY"),
                          "ref": {"tipo": "plano", "id": "XY"}, "marco": None, "cara_ref": None}]
    try:
        ventana.boceto_sobre_cara_elegida()
        assert ventana.modo_boceto.activo                 # arrancó el boceto, sin elección de plano
    finally:
        ventana.seleccion = []
        if ventana.modo_boceto.activo:
            ventana.modo_boceto.cancelar()


def test_espacio_sin_cara_elegida_avisa_y_no_arranca(ventana):
    ventana.seleccion = [{"tipo": "arista"}]
    ventana.boceto_sobre_cara_elegida()
    assert not ventana.modo_boceto.activo
    ventana.seleccion = []


# ---------------------------------------------------------------- PL11: buscador del navegador
def test_el_buscador_del_navegador_filtra_por_nombre(ventana):
    from omnicad.ejemplo import crear_documento_ejemplo
    ventana.set_documento(crear_documento_ejemplo())
    nav, arbol = ventana.navegador, ventana.navegador.arbol
    QTest.qWait(30)
    top = arbol.topLevelItem(0)
    assert top is not None and top.childCount() > 0

    nav.filtro.setText("zzz-nada-de-nada")                     # nada coincide: todo oculto
    assert all(arbol.topLevelItem(i).isHidden() for i in range(arbol.topLevelItemCount()))
    nav.filtro.setText("")                                     # filtro vacío: vuelve todo
    assert not top.isHidden()
    nav.filtro.setText("cuerpo")                               # busca por nombre, sin distinguir mayúsculas
    assert not top.isHidden()                                  # tiene un hijo que coincide
    nav.filtro.setText("")


# ---------------------------------------------------------------- PL6: quitar empalmes
def test_quitar_empalmes_vuelve_a_la_caja_original_y_no_toca_agujeros():
    from omnicad.nucleo import referencias as refs
    from omnicad.nucleo.solidos_crear import agujero
    from omnicad.nucleo.solidos_modificar import caras_de_empalme, empalme, quitar_empalmes
    caja = geo.caja(30, 20, 10)
    largas = [e for e in refs.subformas(caja, "arista")
              if refs.firma_arista(e)["geom"] == "linea" and abs(refs.firma_arista(e)["largo"] - 30) < 1e-6]
    redonda = empalme(caja, [{"aristas": largas, "tipo": "constante", "radio": 2.0}])
    assert len(caras_de_empalme(redonda, 3.0)) == 4              # 4 caras de empalme R2
    assert len(caras_de_empalme(redonda, 1.0)) == 0              # el filtro por radio funciona
    nueva, radios = quitar_empalmes(redonda, 3.0)
    assert radios == [(2.0, 4)]
    assert geo.es_valida(nueva) and abs(geo.volumen(nueva) - geo.volumen(caja)) < 1e-6
    assert len(refs.subformas(nueva, "cara")) == len(refs.subformas(caja, "cara")) == 6

    taladrada = agujero(caja, (0, 0, 10), (0, 0, -1), diametro=4, profundidad=10)
    assert len(caras_de_empalme(taladrada, 3.0)) == 0           # el agujero r2 NO es un empalme


def test_api_remove_fillets_y_el_comando_del_catalogo():
    from omnicad.ui.comandos import CATALOGO
    sesion = api.Sesion()
    api.llamar(sesion, "create_box", {"length": 30, "width": 20, "height": 10})
    api.llamar(sesion, "fillet", {"edges": "|Z", "radius": 2})
    con_empalme = sesion.doc.estado_final.cuerpos["op1.c1"].forma
    assert abs(geo.volumen(con_empalme) - 6000) > 1             # el empalme sacó material

    r = api.llamar(sesion, "remove_fillets", {"body": "op1.c1", "max_radius": 3})
    assert r["ok"] and r["result"]["fillets_removed"] == 4     # las 4 caras de empalme R2
    assert r["result"]["bodies_modified"] and abs(
        r["result"]["bodies_modified"][0]["volume"] - 6000) < 1e-6   # volvió a la caja
    assert sesion.doc.operaciones[-1].TIPO == "quitar_empalmes"

    r = api.llamar(sesion, "remove_fillets", {"body": "op1.c1", "max_radius": 3})
    assert not r["ok"] and r["error_kind"] == "OPERATION_FAILED"  # sin empalmes: falla y no cambia nada
    assert "No se encontraron empalmes" in r["mensaje"]

    comando = CATALOGO["quitar_empalmes"]
    assert comando.CLASE_OP.TIPO == "quitar_empalmes" and comando.ICONO == "quitar_empalmes"
