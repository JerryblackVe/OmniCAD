# -*- coding: utf-8 -*-
"""P9 (segunda tanda): unidades del documento de verdad (mm, cm, m, in, ft; g, kg, lb). Solo cambian cómo se MUESTRAN
las medidas: el modelo, las expresiones y los números de la API siguen en mm y g."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.io_archivos import proyecto  # noqa: E402
from omnicad.nucleo import geometria as g  # noqa: E402
from omnicad.nucleo import referencias as refs  # noqa: E402
from omnicad.timeline.documento import Documento, ErrorDocumento  # noqa: E402
from omnicad.ui import formato  # noqa: E402


@pytest.fixture(autouse=True)
def _mm_al_terminar():
    yield
    formato.configurar_unidades("mm", "g")          # el formato es estado del módulo: no se filtra a otras pruebas


def _doc_con_caja():
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 10, "width": 20, "height": 30})["ok"]
    return s


# ---------------------------------------------------------------- documento y receta
def test_un_documento_nuevo_usa_mm_y_g_y_no_guarda_nada_extra():
    doc = Documento()
    assert doc.unidades == {"longitud": "mm", "masa": "g"} and "unidades" not in doc.a_dict()


def test_fijar_unidades_valida_avisa_y_marca_modificado():
    doc, avisos = Documento(), []
    doc.suscribir(lambda: avisos.append(1))
    doc.fijar_unidades(longitud="in")
    assert doc.unidades == {"longitud": "in", "masa": "g"} and doc.modificado and len(avisos) == 1
    doc.fijar_unidades(masa="lb")
    doc.fijar_unidades(masa="lb")                              # lo mismo otra vez: sin aviso ni cambios
    assert doc.unidades == {"longitud": "in", "masa": "lb"} and len(avisos) == 2
    with pytest.raises(ErrorDocumento, match="yd"):
        doc.fijar_unidades(longitud="yd")
    with pytest.raises(ErrorDocumento, match="stone"):
        doc.fijar_unidades(masa="stone")
    assert doc.unidades == {"longitud": "in", "masa": "lb"}


def test_las_unidades_se_guardan_con_el_proyecto_y_los_viejos_abren_en_mm_g(tmp_path):
    doc = _doc_con_caja().doc
    doc.fijar_unidades("ft", "kg")
    ruta = tmp_path / "pieza.omnicad"
    proyecto.guardar(doc, ruta)
    abierto = proyecto.abrir(ruta)
    assert abierto.unidades == {"longitud": "ft", "masa": "kg"}
    receta = doc.a_dict()
    receta.pop("unidades")                                       # un archivo anterior a esta función
    assert Documento.desde_dict(receta).unidades == {"longitud": "mm", "masa": "g"}


@pytest.mark.parametrize("basura", ["in", 5, ["in"], {"longitud": "yd", "masa": 3}, {"longitud": ["in"]}, None])
def test_unidades_ajenas_o_rotas_en_el_archivo_se_ignoran(basura):
    receta = Documento().a_dict()
    receta["unidades"] = basura
    assert Documento.desde_dict(receta).unidades == {"longitud": "mm", "masa": "g"}


def test_el_modelo_no_cambia_con_las_unidades():
    s = _doc_con_caja()
    antes = api.llamar(s, "get_physical_properties", {})["result"]["total"]["volume"]
    assert api.llamar(s, "set_document_units", {"length": "in", "mass": "lb"})["ok"]
    assert api.llamar(s, "get_physical_properties", {})["result"]["total"]["volume"] == antes == pytest.approx(6000)
    assert s.doc.parametros.evaluar("2 in", "longitud") == pytest.approx(50.8)


# ---------------------------------------------------------------- API
def test_set_document_units_y_get_scene_info():
    s = api.Sesion()
    info = api.llamar(s, "get_scene_info", {})["result"]
    assert info["units"] == {"length": "mm", "angle": "deg"} and info["display_units"] == {"length": "mm", "mass": "g"}
    r = api.llamar(s, "set_document_units", {"length": "cm"})
    assert r["ok"] and r["result"]["display_units"] == {"length": "cm", "mass": "g"}
    assert api.llamar(s, "set_document_units", {})["result"]["display_units"] == {"length": "cm", "mass": "g"}   # consulta
    info = api.llamar(s, "get_scene_info", {})["result"]
    assert info["units"]["length"] == "mm" and info["display_units"] == {"length": "cm", "mass": "g"}
    assert api.llamar(s, "set_document_units", {"length": "yd"})["error_kind"] == "INVALID_ARGUMENTS"


# ---------------------------------------------------------------- formato de pantalla
def test_conversiones_de_formato():
    formato.configurar_unidades("in", "lb")
    assert formato.longitud(25.4) == pytest.approx(1) and formato.longitud(645.16, 2) == pytest.approx(1)
    assert formato.longitud(16387.064, 3) == pytest.approx(1) and formato.masa(453.59237) == pytest.approx(1)
    assert (formato.sufijo(), formato.sufijo(2), formato.sufijo(3, True)) == ("in", "in²", "in^3")
    assert formato.tooltip_valor(25.4) == "= 1 in (25.4 mm)" and formato.tooltip_valor(90, angulo=True) == "= 90°"
    formato.configurar_unidades("mm", "g")
    assert formato.tooltip_valor(25.4) == "= 25.4 mm" and formato.longitud(7) == 7
    formato.configurar_unidades("yd", "stone")                     # lo desconocido cae a mm y g
    assert (formato.unidad_longitud(), formato.unidad_masa()) == ("mm", "g")


def test_medidas_de_lo_elegido_en_la_unidad_del_documento():
    from omnicad.ui.medidas import texto_medidas
    caja = g.caja(10, 20, 30)
    cara = max(g.caras(caja), key=g.area)
    larga = max(refs.subformas(caja, "arista"), key=g.longitud)
    formato.configurar_unidades("cm", "g")
    assert texto_medidas([{"tipo": "cara", "ref": {}, "forma": cara}]) == "1 Cara | Área: 6.000 cm^2"
    assert texto_medidas([{"tipo": "arista", "ref": {}, "forma": larga}]) == "1 Arista | Longitud: 3.000 cm"
    assert texto_medidas([{"tipo": "cuerpo", "ref": {}, "forma": caja}]) == "1 Cuerpo | Volumen: 6.000 cm^3"
    formato.configurar_unidades("in", "g")
    assert texto_medidas([{"tipo": "cuerpo", "ref": {}, "forma": caja}]) == "1 Cuerpo | Volumen: 0.366 in^3"


def test_lista_de_materiales_en_la_unidad_del_documento():
    from omnicad.ui.administrar import DialogoListaMateriales
    QApplication.instance() or QApplication([])
    doc = _doc_con_caja().doc
    en_g = DialogoListaMateriales(doc, nombre_de=lambda c: c.nombre).texto_csv().splitlines()
    formato.configurar_unidades("cm", "kg")
    dlg = DialogoListaMateriales(doc, nombre_de=lambda c: c.nombre)
    en_kg = dlg.texto_csv().splitlines()
    assert en_g[0].endswith("Masa (g),Volumen (mm³)") and en_kg[0].endswith("Masa (kg),Volumen (cm³)")
    masa_g, vol_mm3 = (float(x) for x in en_g[1].split(",")[-2:])
    masa_kg, vol_cm3 = (float(x) for x in en_kg[1].split(",")[-2:])
    assert masa_kg == pytest.approx(masa_g / 1000, abs=1e-3) and vol_cm3 == pytest.approx(vol_mm3 / 1000, abs=1e-3)
    dlg.deleteLater()


# ---------------------------------------------------------------- ventana
@pytest.fixture
def ventana(tmp_path):
    QApplication.instance() or QApplication([])
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.show()
    QTest.qWait(30)
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    QTest.qWait(10)


def test_el_menu_de_unidades_cambia_el_documento_el_boton_y_las_casillas(ventana):
    v = ventana
    assert v.timeline.unidades.text() == "Unidades: mm, g  ▾"
    assert all(a.isEnabled() for a in v._acciones_unidad.values())          # ya no hay unidades grisadas
    assert v._acciones_unidad[("longitud", "mm")].isChecked() and v._acciones_unidad[("masa", "g")].isChecked()
    v._acciones_unidad[("longitud", "in")].trigger()
    v._acciones_unidad[("masa", "lb")].trigger()
    assert v.doc.unidades == {"longitud": "in", "masa": "lb"} and formato.unidad_longitud() == "in"
    assert v.timeline.unidades.text() == "Unidades: in, lb  ▾"
    assert v._acciones_unidad[("longitud", "in")].isChecked() and not v._acciones_unidad[("longitud", "mm")].isChecked()
    assert v.doc.modificado
    assert v.navegador.item("__unidades__").text(0) == "Unidades: in, lb"       # el nodo del navegador también


def test_otro_documento_vuelve_a_sus_propias_unidades(ventana):
    v = ventana
    v.elegir_unidad("longitud", "ft")
    nuevo = Documento()
    v.set_documento(nuevo)
    assert v.timeline.unidades.text() == "Unidades: mm, g  ▾" and formato.unidad_longitud() == "mm"


def test_las_propiedades_de_un_cuerpo_salen_en_la_unidad_del_documento(ventana):
    v = ventana
    v.cargar_ejemplo()
    cid = next(iter(v.doc.estado_final.cuerpos))
    v.elegir_unidad("longitud", "cm")
    v._propiedades(cid)
    texto = v.timeline.estado.toolTip()                           # el aviso completo, sin recortar
    assert "volumen" in texto and "cm³" in texto and "cm²" in texto and "mm³" not in texto
    v.elegir_unidad("longitud", "mm")
    v._propiedades(cid)
    assert "mm³" in v.timeline.estado.toolTip()
